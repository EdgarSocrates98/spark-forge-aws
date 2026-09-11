"""Projecao de findings para o GitHub: localizacao, escape, gate e limites.

A projecao e pura: a existencia de arquivo entra como funcao, entao estes testes
nao precisam de arvore em disco -- exceto o invariante sobre o corpus inteiro de
`fixtures/`, que usa as arvores reais das fixtures.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from sparkforge.reporting import github
from sparkforge.reporting.github import (
    LIMITE_RESULTADOS,
    LIMITE_SUMARIO_BYTES,
    anotacao,
    gate_disparou,
    projetar,
)
from sparkforge.reporting.locate import Localizado, Recusa, localizar

ROOT = Path(__file__).resolve().parents[1]
ESQUEMA = ROOT / "fixtures" / "sarif" / "_schema" / "sarif-schema-2.1.0.json"


def _validador() -> jsonschema.Draft4Validator:
    return jsonschema.Draft4Validator(json.loads(ESQUEMA.read_text(encoding="utf-8")))


def _finding(**campos: Any) -> dict[str, Any]:
    base = {
        "rule_id": "SF-PY-004",
        "title": "Action dentro de loop",
        "severity": "P0",
        "confidence": "high",
        "status": "structural",
        "subject": {"type": "source_location", "file": "lib/job.py", "line": 2},
        "evidence": ["f_aaaaaa"],
    }
    base.update(campos)
    return base


def _existe(*caminhos: str):
    presentes = set(caminhos)
    return lambda rel: rel in presentes


class TestLocalizar:
    def test_subject_com_linha(self):
        assert localizar(_finding(), {}, ["."], _existe("lib/job.py")) == Localizado(
            "lib/job.py", 2, None
        )

    def test_raiz_declarada_prefixa_o_caminho(self):
        onde = localizar(_finding(), {}, ["jobs"], _existe("jobs/lib/job.py"))
        assert onde == Localizado("jobs/lib/job.py", 2, None)

    def test_caminho_em_duas_raizes_e_ambiguo(self):
        onde = localizar(_finding(), {}, ["a", "b"], _existe("a/lib/job.py", "b/lib/job.py"))
        assert onde == Recusa("caminho_ambiguo")

    def test_arquivo_ausente(self):
        assert localizar(_finding(), {}, ["."], _existe()) == Recusa("arquivo_fora_do_repo")

    def test_plan_node_fora_do_repo(self):
        f = _finding(subject={"type": "plan_node", "file": "plan.txt", "line": 29})
        assert localizar(f, {}, ["."], _existe()) == Recusa("arquivo_fora_do_repo")

    def test_runtime_e_so_para_quem_nao_tem_stage(self):
        f = _finding(subject={"type": "job_run", "symbol": "etl"}, evidence=["f_1"])
        fact = {"id": "f_1", "subject": {"type": "job_run", "symbol": "etl"}}
        assert localizar(f, {"f_1": fact}, ["."], _existe()) == Recusa("runtime")

    def test_stage_sem_callsite(self):
        f = _finding(subject={"type": "stage", "stage_id": 4}, evidence=["f_1"])
        fact = {"id": "f_1", "subject": {"type": "stage", "stage_id": 4}}
        assert localizar(f, {"f_1": fact}, ["."], _existe()) == Recusa("callsite_ausente")

    def test_sem_linha(self):
        f = _finding(subject={"type": "source_location", "file": "lib/job.py"}, evidence=[])
        assert localizar(f, {}, ["."], _existe("lib/job.py")) == Recusa("sem_linha")

    def test_localiza_pela_evidencia_de_codigo(self):
        f = _finding(subject={"type": "job_run", "symbol": "etl"}, evidence=["f_1", "f_2"])
        facts = {
            "f_1": {"subject": {"type": "table", "file": "dump.json", "line": 3}},
            "f_2": {"subject": {"type": "source_location", "file": "lib/job.py", "line": 9}},
        }
        assert localizar(f, facts, ["."], _existe("lib/job.py", "dump.json")) == Localizado(
            "lib/job.py", 9, None
        )

    def test_evidencia_ausente_da_uniao(self):
        f = _finding(subject={"type": "job_run"}, evidence=["f_sumiu"])
        assert localizar(f, {}, ["."], _existe()) == Recusa("evidencia_ausente")

    @pytest.mark.parametrize("linha", [0, -1, "3", True, None])
    def test_linha_invalida_nao_localiza(self, linha):
        subject = {"type": "source_location", "file": "lib/job.py", "line": linha}
        f = _finding(subject=subject, evidence=[])
        assert localizar(f, {}, ["."], _existe("lib/job.py")) == Recusa("sem_linha")

    def test_coluna_entra_quando_existe(self):
        subject = {"type": "source_location", "file": "lib/job.py", "line": 2, "col": 4}
        f = _finding(subject=subject)
        assert localizar(f, {}, ["."], _existe("lib/job.py")).col == 4


def _stage_fact(fid: str, stage_id: int, artefato: str) -> dict[str, Any]:
    return {
        "id": fid,
        "kind": "spark.stage.shuffle",
        "subject": {"type": "stage", "stage_id": stage_id},
        "provenance": {"artifact": artefato},
    }


def _callsite(
    fid: str, stage_id: int, artefato: str, *, path: str | None = None, line: int | None = None,
    symbol: str | None = None, reason: str | None = None, method: str = "collect",
) -> dict[str, Any]:
    resolvido = path is not None
    return {
        "id": fid,
        "kind": "spark.stage.callsite",
        "subject": {
            "type": "stage",
            "stage_id": stage_id,
            "symbol": symbol or (f"{method} at {path}:{line}" if resolvido else "stage_x"),
        },
        "measures": {"line": line} if resolvido else {},
        "attrs": (
            {"resolved": True, "method": method, "file": path.rsplit("/", 1)[-1], "path": path}
            if resolvido
            else {"resolved": False, "reason": reason or "sem_forma_de_callsite"}
        ),
        "provenance": {"artifact": artefato},
    }


def _facts(*facts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f["id"]: f for f in facts}


class TestCallsite:
    """Findings de stage localizados na linha da ACAO que originou o stage."""

    def test_stage_localizado_pelo_maior_sufixo(self):
        facts = _facts(
            _stage_fact("s1", 4, "ev.jsonl"),
            _callsite("c1", 4, "ev.jsonl", path="/opt/spark/work/jobs/lib/job.py", line=42),
        )
        f = _finding(subject={"type": "stage", "stage_id": 4}, evidence=["s1"])
        onde = localizar(f, facts, ["."], _existe("jobs/lib/job.py", "lib/job.py"))
        assert onde == Localizado(
            "jobs/lib/job.py", 42, None,
            "linha da acao `collect` que originou o stage 4 (nao e a causa)",
        )

    def test_job_run_pela_evidencia_de_stage(self):
        facts = _facts(
            _stage_fact("s3", 3, "ev.jsonl"),
            _callsite("c3", 3, "ev.jsonl", path="/opt/w/job.py", line=7),
        )
        f = _finding(subject={"type": "job_run", "symbol": "etl"}, evidence=["s3"])
        onde = localizar(f, facts, ["jobs"], _existe("jobs/job.py"))
        assert (onde.uri, onde.line) == ("jobs/job.py", 7)

    def test_dois_event_logs_nao_se_confundem(self):
        facts = _facts(
            _stage_fact("sa", 0, "a.jsonl"),
            _stage_fact("sb", 0, "b.jsonl"),
            _callsite("ca", 0, "a.jsonl", path="/w/um.py", line=1),
            _callsite("cb", 0, "b.jsonl", path="/w/dois.py", line=2),
        )
        existe = _existe("um.py", "dois.py")
        a = localizar(_finding(subject={"type": "stage", "stage_id": 0}, evidence=["sa"]),
                      facts, ["."], existe)
        b = localizar(_finding(subject={"type": "stage", "stage_id": 0}, evidence=["sb"]),
                      facts, ["."], existe)
        assert (a.uri, b.uri) == ("um.py", "dois.py")

    def test_empate_no_sufixo_nao_cai_para_o_nome_base(self):
        facts = _facts(
            _stage_fact("s1", 1, "ev"),
            _callsite("c1", 1, "ev", path="/opt/lib/job.py", line=5),
        )
        f = _finding(subject={"type": "stage", "stage_id": 1}, evidence=["s1"])
        onde = localizar(f, facts, ["a", "b"], _existe("a/lib/job.py", "b/lib/job.py", "a/job.py"))
        assert onde == Recusa("caminho_ambiguo")

    def test_nome_sintetico(self):
        facts = _facts(_stage_fact("s1", 1, "ev"), _callsite("c1", 1, "ev"))
        f = _finding(subject={"type": "stage", "stage_id": 1}, evidence=["s1"])
        assert localizar(f, facts, ["."], _existe()) == Recusa("callsite_sem_forma")

    def test_scala_no_repo(self):
        facts = _facts(
            _stage_fact("s1", 2, "ev"),
            _callsite("c1", 2, "ev", symbol="save at Etl.scala:120", reason="arquivo_nao_python"),
        )
        f = _finding(subject={"type": "stage", "stage_id": 2}, evidence=["s1"])
        onde = localizar(f, facts, ["src"], _existe("src/Etl.scala"))
        assert (onde.uri, onde.line) == ("src/Etl.scala", 120)
        assert "`save`" in onde.nota

    def test_scala_fora_do_repo(self):
        facts = _facts(
            _stage_fact("s1", 2, "ev"),
            _callsite("c1", 2, "ev", symbol="save at Etl.scala:120", reason="arquivo_nao_python"),
        )
        f = _finding(subject={"type": "stage", "stage_id": 2}, evidence=["s1"])
        assert localizar(f, facts, ["."], _existe()) == Recusa("callsite_nao_python")

    @pytest.mark.parametrize("simbolo", ["save at Etl.scala:0", "save at Etl.scala", "x at :3"])
    def test_scala_fora_do_padrao(self, simbolo):
        facts = _facts(
            _stage_fact("s1", 2, "ev"),
            _callsite("c1", 2, "ev", symbol=simbolo, reason="arquivo_nao_python"),
        )
        f = _finding(subject={"type": "stage", "stage_id": 2}, evidence=["s1"])
        assert localizar(f, facts, ["."], _existe("Etl.scala")) == Recusa("callsite_sem_forma")

    def test_sem_artefato_e_dois_callsites(self):
        facts = _facts(
            _callsite("ca", 0, "a.jsonl", path="/w/um.py", line=1),
            _callsite("cb", 0, "b.jsonl", path="/w/dois.py", line=2),
        )
        f = _finding(subject={"type": "stage", "stage_id": 0}, evidence=[])
        assert localizar(f, facts, ["."], _existe("um.py", "dois.py")) == Recusa(
            "callsite_ambiguo"
        )

    def test_sem_artefato_e_callsite_unico(self):
        facts = _facts(_callsite("ca", 0, "a.jsonl", path="/w/um.py", line=1))
        f = _finding(subject={"type": "stage", "stage_id": 0}, evidence=[])
        assert localizar(f, facts, ["."], _existe("um.py")).uri == "um.py"

    def test_a_nota_chega_ao_sarif_ao_resumo_e_a_anotacao(self):
        facts = _facts(
            _stage_fact("s1", 4, "ev"),
            _callsite("c1", 4, "ev", path="/w/job.py", line=9),
        )
        f = _finding(subject={"type": "stage", "stage_id": 4}, evidence=["s1"])
        p = projetar([f], facts, ["."], _existe("job.py"), versao="1.0")
        nota = "(nao e a causa)"
        assert nota in p.sarif["runs"][0]["results"][0]["message"]["text"]
        assert nota in p.annotations[0]
        assert nota in p.summary


class TestEscape:
    def test_os_cinco_caracteres(self):
        linha = anotacao("error", "a,b:c.py", 3, "T%1: x,y", "m%\r\nfim")
        assert linha == "::error file=a%2Cb%3Ac.py,line=3,title=T%251%3A x%2Cy::m%25%0D%0Afim"

    def test_mensagem_nao_escapa_dois_pontos(self):
        """`escapeData` nao troca `:` nem `,` -- so `escapeProperty` troca."""
        assert anotacao("note", "a.py", 1, "t", "x: y, z").endswith("::x: y, z")

    @pytest.mark.parametrize(
        ("level", "comando"), [("error", "error"), ("warning", "warning"), ("note", "notice")]
    )
    def test_comando_por_level(self, level, comando):
        assert anotacao(level, "a.py", 1, "t", "m").startswith(f"::{comando} ")


class TestGate:
    @pytest.mark.parametrize(
        ("severidades", "fail_on", "esperado"),
        [
            (["P0", "P1"], "P0", True),
            (["P0", "P1"], "P1", True),
            (["P1"], "P0", False),
            (["P1"], "P1", True),
            (["P2", "P3"], "P1", False),
            (["P0"], None, False),
            ([], "P0", False),
        ],
    )
    def test_fronteiras(self, severidades, fail_on, esperado):
        assert gate_disparou(severidades, fail_on) is esperado


class TestProjecao:
    def test_sarif_valido_e_deterministico(self):
        def em(arquivo: str, linha: int) -> dict[str, Any]:
            return {"type": "source_location", "file": arquivo, "line": linha}

        findings = [
            _finding(rule_id="SF-B", subject=em("b.py", 5)),
            _finding(rule_id="SF-A", subject=em("a.py", 9)),
            _finding(rule_id="SF-C", subject={"type": "job_run", "symbol": "j"}, evidence=[]),
        ]
        existe = _existe("a.py", "b.py")
        um = projetar(findings, {}, ["."], existe, versao="1.0", category="c", fail_on="P0")
        dois = projetar(list(reversed(findings)), {}, ["."], existe, versao="1.0", category="c",
                        fail_on="P0")
        assert json.dumps(um.sarif) == json.dumps(dois.sarif)
        assert um.summary == dois.summary
        assert not list(_validador().iter_errors(um.sarif))
        run = um.sarif["runs"][0]
        assert [r["ruleId"] for r in run["results"]] == ["SF-A", "SF-B"]
        assert [r["id"] for r in run["tool"]["driver"]["rules"]] == ["SF-A", "SF-B"]
        assert run["automationDetails"] == {"id": "c/"}
        assert um.recusas == ({"rule_id": "SF-C", "severity": "P0", "reason": "runtime",
                               "subject_type": "job_run"},)

    def test_sem_fingerprint_nem_security_severity(self):
        p = projetar([_finding()], {}, ["."], _existe("lib/job.py"), versao="1.0")
        texto = json.dumps(p.sarif)
        assert "partialFingerprints" not in texto and "security-severity" not in texto

    def test_limite_de_resultados_vira_recusa(self, monkeypatch):
        monkeypatch.setattr(github, "LIMITE_RESULTADOS", 2)
        findings = [
            _finding(subject={"type": "source_location", "file": "a.py", "line": n})
            for n in (1, 2, 3)
        ]
        p = projetar(findings, {}, ["."], _existe("a.py"), versao="1.0")
        assert p.localizados == 2
        assert [r["reason"] for r in p.recusas] == ["limite_do_github"]
        assert p.localizados + len(p.recusas) == p.total

    def test_limite_do_resumo_e_nomeado(self, monkeypatch):
        monkeypatch.setattr(github, "LIMITE_SUMARIO_BYTES", 2000)
        findings = [
            _finding(rule_id=f"SF-R-{n:03d}", subject={"type": "stage", "stage_id": n},
                     evidence=[])
            for n in range(80)
        ]
        p = projetar(findings, {}, ["."], _existe(), versao="1.0")
        assert len(p.summary.encode("utf-8")) <= 2000
        assert "limite_do_github" in p.summary
        assert len(p.recusas) == 80

    def test_limites_publicados(self):
        assert LIMITE_RESULTADOS == 5000
        assert LIMITE_SUMARIO_BYTES == 1_048_576


def _uniao_de_facts(caso: Path) -> dict[str, dict[str, Any]]:
    """`input/facts.json` (a uniao que o `judge` recebeu) + `expected/facts.json`."""
    por_id: dict[str, dict[str, Any]] = {}
    for arquivo in (caso / "input" / "facts.json", caso / "expected" / "facts.json"):
        if not arquivo.is_file():
            continue
        dado = json.loads(arquivo.read_text(encoding="utf-8"))
        for fact in dado if isinstance(dado, list) else dado.get("facts", []):
            if "id" in fact:
                por_id.setdefault(fact["id"], fact)
    return por_id


def _casos_com_findings() -> list[Path]:
    casos = []
    for arquivo in sorted((ROOT / "fixtures").rglob("expected/findings.json")):
        dado = json.loads(arquivo.read_text(encoding="utf-8"))
        if dado if isinstance(dado, list) else dado.get("findings"):
            casos.append(arquivo.parent.parent)
    return casos


def test_nenhum_finding_some_no_corpus_inteiro():
    """SARIF + recusa = total, fixture a fixture, sobre todos os goldens de `fixtures/`.

    E nenhum resultado do SARIF aponta arquivo que nao existe ou linha ausente.
    """
    validador = _validador()
    total = localizados = 0
    casos = _casos_com_findings()
    assert len(casos) >= 150
    for caso in casos:
        dado = json.loads((caso / "expected" / "findings.json").read_text(encoding="utf-8"))
        findings = dado if isinstance(dado, list) else dado["findings"]
        raiz = (caso / "input").resolve()

        def existe(rel: str, r: Path = raiz) -> bool:
            alvo = (r / rel).resolve()
            return alvo.is_relative_to(r) and alvo.is_file()

        p = projetar(findings, _uniao_de_facts(caso), ["."], existe, versao="t")
        assert p.localizados + len(p.recusas) == p.total == len(findings), caso
        assert not list(validador.iter_errors(p.sarif)), caso
        for resultado in p.sarif["runs"][0]["results"]:
            local = resultado["locations"][0]["physicalLocation"]
            assert existe(local["artifactLocation"]["uri"]), caso
            assert local["region"]["startLine"] >= 1, caso
        assert len(p.annotations) == p.localizados
        total += p.total
        localizados += p.localizados
    assert total >= 222
    assert 0 < localizados < total


def test_nenhum_finding_com_stage_sai_como_runtime():
    """Quem tem stage (no subject ou na evidencia) sai localizado ou com motivo `callsite_*`.

    O denominador medido em 2026-09-11: dos 28 findings de stage do corpus, 0
    sao localizados -- os event logs das fixtures tem nomes de stage sinteticos
    ou de Scala sem o `.scala` no repositorio. O ganho vive nos casos de
    `fixtures/sarif/stage_*`; aqui o que se cobra e que a recusa diga por que.
    """
    motivos_de_stage = set()
    for caso in _casos_com_findings():
        dado = json.loads((caso / "expected" / "findings.json").read_text(encoding="utf-8"))
        findings = dado if isinstance(dado, list) else dado["findings"]
        facts = _uniao_de_facts(caso)
        raiz = (caso / "input").resolve()

        def existe(rel: str, r: Path = raiz) -> bool:
            alvo = (r / rel).resolve()
            return alvo.is_relative_to(r) and alvo.is_file()

        for finding in findings:
            if (finding.get("subject") or {}).get("type") != "stage":
                continue
            onde = localizar(finding, facts, ["."], existe)
            assert onde != Recusa("runtime"), (caso, finding["rule_id"])
            if isinstance(onde, Recusa):
                motivos_de_stage.add(onde.motivo)
    assert motivos_de_stage <= {
        "callsite_ausente", "callsite_sem_forma", "callsite_nao_python", "callsite_ambiguo",
        "caminho_ambiguo", "arquivo_fora_do_repo",
    }
