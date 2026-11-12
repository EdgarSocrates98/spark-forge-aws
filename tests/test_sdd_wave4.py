"""Onda 4 do SDD: decisoes, requisitos, grafo de tarefas, recibos e convergencia.

Cada gate novo fica exercido por artefato: `decisions_ref` do explore,
`requirements` do define, `depends_on`/`write_scope` do plan, `receipts` do
build_report e `convergence` do ship, mais a convergencia read-only de
`sdd converge`. O perfil operator ganha um arquivo proprio
(`test_sdd_operator_wave4.py`) para os cenarios de robustez: sem `.git`,
estrutura copiada, raiz de evidencia independente, runtime ausente e
evidencia inconclusiva.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from sparkforge_aws.receipt._hash import text_sha256
from sparkforge_aws.sdd import DEFAULT_ROOT
from sparkforge_aws.sdd.checks import check
from sparkforge_aws.sdd.converge import converge
from sparkforge_aws.sdd.decisions import (
    load_decisions,
    next_open,
    reopen,
    validate_decisions,
)
from sparkforge_aws.sdd.load import split_frontmatter
from sparkforge_aws.sdd.receipts import load_receipt, validate_receipt
from sparkforge_aws.sdd.stamp import stamp
from sparkforge_aws.sdd.status import status
from sparkforge_aws.sdd.task_graph import topo_order

ROOT = Path(__file__).resolve().parents[1]
_LINHA_SHA = re.compile(r"^(?P<recuo>[ \t]+)sha256: ['\"]?(?P<hex>[0-9a-f]*)['\"]?$", re.M)


def _dump(meta: dict) -> str:
    texto = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return _LINHA_SHA.sub(lambda m: f'{m["recuo"]}sha256: "{m["hex"]}"', texto)


def _grava(repo: Path, feature: str, fase: str, meta: dict) -> Path:
    pasta = repo / DEFAULT_ROOT / feature
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{fase}.md"
    arquivo.write_bytes(("---\n" + _dump(meta) + "---\ncorpo livre\n").encode("utf-8"))
    return arquivo


def _upstream(repo: Path, anterior: Path) -> dict:
    return {"path": anterior.relative_to(repo).as_posix(), "sha256": text_sha256(anterior)}


def _reescreve(arquivo: Path, **mudancas) -> None:
    texto = arquivo.read_bytes().decode("utf-8")
    bloco, corpo = split_frontmatter(texto)
    meta = yaml.safe_load(bloco)
    for chave, valor in mudancas.items():
        if valor is None:
            meta.pop(chave, None)
        else:
            meta[chave] = valor
    arquivo.write_bytes(("---\n" + _dump(meta) + "---\n" + corpo).encode("utf-8"))


def _restampa(repo: Path, feature: str = "F1") -> None:
    for fase in ("design", "plan", "build_report", "ship"):
        if (repo / DEFAULT_ROOT / feature / f"{fase}.md").is_file():
            stamp(repo, f"{DEFAULT_ROOT}/{feature}/{fase}.md")


def _meta(arquivo: Path) -> dict:
    bloco, _ = split_frontmatter(arquivo.read_bytes().decode("utf-8"))
    return yaml.safe_load(bloco)


def _codigos(relatorio: dict) -> tuple[list[str], list[str]]:
    return (
        sorted(r["code"] for r in relatorio["refused"]),
        sorted(u["code"] for u in relatorio["unresolved"]),
    )


def _feature(repo: Path, feature: str = "F1") -> dict[str, Path]:
    """Feature dev inteira em `ready`, a partir da qual cada teste estraga uma coisa."""
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "test_alvo.py").write_bytes(b"def test_alvo():\n    assert True\n")
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src" / "existente.py").write_bytes(b"x = 1\n")
    comum = {"sdd": 1, "feature": feature, "profile": "dev", "status": "ready"}
    caminhos: dict[str, Path] = {}
    caminhos["define"] = _grava(repo, feature, "define", {
        **comum,
        "phase": "define",
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [{
            "id": "AC1",
            "statement": "s",
            "verified_by": {"kind": "test", "ref": "tests/test_alvo.py::test_alvo"},
        }],
        "success": [{"id": "SC1", "metric": "m", "source": "tests/test_alvo.py"}],
        "out_of_scope": [],
        "change_kinds": [],
    })
    caminhos["design"] = _grava(repo, feature, "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream(repo, caminhos["define"]),
        "files": [
            {"path": "src/novo.py", "action": "create", "reason": "r"},
            {"path": "src/existente.py", "action": "modify", "reason": "r"},
        ],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "git revert"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
    })
    caminhos["plan"] = _grava(repo, feature, "plan", {
        **comum,
        "phase": "plan",
        "upstream": _upstream(repo, caminhos["design"]),
        "tasks": [{
            "id": "T1",
            "files": ["src/novo.py"],
            "covers": ["AC1"],
            "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
        }],
    })
    caminhos["build_report"] = _grava(repo, feature, "build_report", {
        **comum,
        "phase": "build_report",
        "upstream": _upstream(repo, caminhos["plan"]),
        "tasks": [{
            "id": "T1",
            "status": "done",
            "red": {"command": "pytest tests/test_alvo.py::test_alvo", "exit": 1},
            "green": {"command": "pytest tests/test_alvo.py", "exit": 0},
        }],
        "claims": [{"text": "t", "evidence_ref": "tests/test_alvo.py::test_alvo"}],
    })
    caminhos["ship"] = _grava(repo, feature, "ship", {
        **comum,
        "phase": "ship",
        "upstream": _upstream(repo, caminhos["build_report"]),
        "hypothesis_outcome": "confirmed",
        "registries": [],
        "deviations": [],
    })
    return caminhos


def _com_explore(repo: Path, caminhos: dict, feature: str = "F1", ref: str | None = None) -> Path:
    """Grava o explore e costura a cadeia: o define passa a apontar para ele."""
    explore = _grava(repo, feature, "explore", {
        "sdd": 1, "feature": feature, "phase": "explore", "profile": "dev",
        "status": "ready",
        "approaches": [{"id": "A", "summary": "s"}],
        "chosen": "A",
        **({"decisions_ref": ref} if ref else {}),
    })
    _reescreve(caminhos["define"], upstream={
        "path": f"{DEFAULT_ROOT}/{feature}/explore.md", "sha256": "",
    })
    stamp(repo, f"{DEFAULT_ROOT}/{feature}/define.md")
    _restampa(repo, feature)
    return explore


def _arvore(repo: Path, feature: str, decisions: list[dict]) -> Path:
    caminho = repo / DEFAULT_ROOT / feature / "decisions.json"
    caminho.write_bytes(json.dumps({
        "schema": "forge/DecisionTree/v1",
        "feature": feature,
        "decisions": decisions,
    }).encode("utf-8"))
    return caminho


def _decisao(ident: str, status: str = "decided", **extras) -> dict:
    return {
        "id": ident,
        "question": f"pergunta de {ident}?",
        "type": "technical",
        "status": status,
        "alternatives": [
            {"id": "A", "label": "a"},
            {"id": "B", "label": "b"},
        ],
        "answer": "A" if status == "decided" else None,
        **extras,
    }


# -- decisoes -----------------------------------------------------------------


def test_load_decisions_json_quebrado(tmp_path):
    arquivo = tmp_path / "decisions.json"
    arquivo.write_bytes(b"{")
    arvore, erro = load_decisions(arquivo)
    assert arvore is None and "JSON invalido" in erro


def test_load_decisions_nao_objeto(tmp_path):
    arquivo = tmp_path / "decisions.json"
    arquivo.write_bytes(b"[1]")
    _, erro = load_decisions(arquivo)
    assert erro == "o arquivo precisa ser um objeto JSON"


def test_validate_decisions_decidida_sem_resposta():
    arvore = {
        "schema": "forge/DecisionTree/v1",
        "feature": "F1",
        "decisions": [_decisao("DEC-1", "decided", answer=None)],
    }
    [achado] = validate_decisions(arvore, "F1")
    assert achado.kind == "invalid" and "answer" in achado.detail


def test_validate_decisions_ciclo_e_dependencia_desconhecida():
    arvore = {
        "schema": "forge/DecisionTree/v1",
        "feature": "F1",
        "decisions": [
            _decisao("DEC-1", depends_on=["DEC-2"]),
            _decisao("DEC-2", depends_on=["DEC-1"]),
            _decisao("DEC-3", depends_on=["DEC-9"]),
        ],
    }
    kinds = {a.kind: a.decision for a in validate_decisions(arvore, "F1")}
    assert kinds["dep_unknown"] == "DEC-3"
    assert "cycle" in kinds


def test_validate_decisions_contradicao_com_rejeitada():
    arvore = {
        "schema": "forge/DecisionTree/v1",
        "feature": "F1",
        "decisions": [
            _decisao("DEC-1", "rejected"),
            _decisao("DEC-2", "decided", depends_on=["DEC-1"]),
        ],
    }
    [achado] = [a for a in validate_decisions(arvore, "F1") if a.kind == "contradicts"]
    assert achado.decision == "DEC-2" and "rejeitada" in achado.detail


def test_next_open_ordem_topologica():
    arvore = {
        "decisions": [
            _decisao("DEC-2", "open", depends_on=["DEC-1"]),
            _decisao("DEC-1", "open"),
            _decisao("DEC-3", "decided"),
        ]
    }
    assert next_open(arvore) == ["DEC-1", "DEC-2"]


def test_next_open_ciclo_no_fim():
    arvore = {
        "decisions": [
            _decisao("DEC-1", "open", depends_on=["DEC-2"]),
            _decisao("DEC-2", "open", depends_on=["DEC-1"]),
            _decisao("DEC-3", "open"),
        ]
    }
    ordem = next_open(arvore)
    assert ordem[0] == "DEC-3" and sorted(ordem[1:]) == ["DEC-1", "DEC-2"]


def test_reopen_devolve_copia_reaberta():
    arvore = {"decisions": [_decisao("DEC-1", "decided"), _decisao("DEC-2", "rejected")]}
    nova = reopen(arvore, "DEC-1")
    assert nova["decisions"][0]["status"] == "reopened"
    assert nova["decisions"][0]["answer"] == "A"
    assert arvore["decisions"][0]["status"] == "decided"
    # rejeitada nao reabre: quem rejeitou decide de novo, nao a arvore
    assert reopen(arvore, "DEC-2")["decisions"][1]["status"] == "rejected"


def test_gate_decisions_ref_ausente_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    _com_explore(tmp_path, caminhos, ref="docs/sdd/F1/decisions.json")
    _, lacunas = _codigos(check(tmp_path))
    assert "decisions_missing" in lacunas


def test_gate_decisions_aberta_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    _arvore(tmp_path, "F1", [_decisao("DEC-1", "open")])
    _com_explore(tmp_path, caminhos, ref="docs/sdd/F1/decisions.json")
    recusas, lacunas = _codigos(check(tmp_path))
    assert "decision_open" in lacunas and recusas == []


def test_gate_decisions_invalida_e_ciclo(tmp_path):
    caminhos = _feature(tmp_path)
    _arvore(tmp_path, "F1", [
        _decisao("DEC-1", "open", depends_on=["DEC-2"]),
        _decisao("DEC-2", "open", depends_on=["DEC-1"]),
    ])
    _com_explore(tmp_path, caminhos, ref="docs/sdd/F1/decisions.json")
    recusas, _ = _codigos(check(tmp_path))
    assert "decision_cycle" in recusas


def test_gate_decisions_ref_de_outra_feature(tmp_path):
    caminhos = _feature(tmp_path)
    # a arvore declara outra feature: arquivo certo, dono errado
    caminho = tmp_path / DEFAULT_ROOT / "F1" / "decisions.json"
    caminho.write_bytes(json.dumps({
        "schema": "forge/DecisionTree/v1",
        "feature": "OUTRA",
        "decisions": [_decisao("DEC-1")],
    }).encode("utf-8"))
    _com_explore(tmp_path, caminhos, ref="docs/sdd/F1/decisions.json")
    recusas, _ = _codigos(check(tmp_path))
    assert "decisions_invalid" in recusas


# -- requirements -------------------------------------------------------------


def _requisito(ident: str = "REQ-1", **extras) -> dict:
    return {
        "id": ident,
        "kind": "functional",
        "text": f"texto de {ident}",
        "acceptance": f"o teste em tests/test_alvo.py passa para {ident}",
        **extras,
    }


def test_requirement_duplicado_e_recusa(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["define"], requirements=[
        _requisito("REQ-1", text="texto unico A"),
        _requisito("REQ-1", text="texto unico B"),
        _requisito("REQ-2", text="texto unico A"),
    ])
    recusas, _ = _codigos(check(tmp_path))
    assert recusas.count("requirement_duplicate") == 2


def test_requirement_intestavel_e_metrica_sem_fonte(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["define"], requirements=[
        _requisito("REQ-1", acceptance="o sistema e bom e robusto"),
        _requisito("REQ-2", acceptance="latencia < 200ms no percentil 95"),
    ])
    recusas, lacunas = _codigos(check(tmp_path))
    assert "requirement_untestable" in lacunas
    assert "requirement_metric_without_source" in recusas


def test_requirement_metrica_com_fonte_passa(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["define"], requirements=[
        _requisito("REQ-1", acceptance="latencia < 200ms", source="benchmark do caso"),
    ])
    # cobre o REQ no plan para isolar o teste da cobertura
    plano = _meta(caminhos["plan"])
    plano["tasks"][0]["covers"] = ["AC1", "REQ-1"]
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    _restampa(tmp_path)
    recusas, lacunas = _codigos(check(tmp_path))
    assert "requirement_metric_without_source" not in recusas
    assert "requirement_untestable" not in lacunas


def test_requirement_contradiz_outro(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["define"], requirements=[
        _requisito("REQ-1", text="o job deve gravar tabela particionada por data no destino"),
        _requisito("REQ-2", text="o job nao deve gravar tabela particionada por data no destino"),
    ])
    _, lacunas = _codigos(check(tmp_path))
    assert lacunas.count("requirement_contradicts") == 1


def test_requirement_contradiz_o_escopo(tmp_path):
    caminhos = _feature(tmp_path)
    texto = "o job deve gravar tabela particionada por data no destino"
    _reescreve(caminhos["define"],
               out_of_scope=["gravar tabela particionada por data no destino final"],
               requirements=[_requisito("REQ-1", text=texto)])
    _, lacunas = _codigos(check(tmp_path))
    assert lacunas.count("requirement_contradicts") == 1


def test_requirement_critical_bloqueado_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["define"],
               unknowns=[{"id": "U1", "blocks": ["REQ-1"], "unlock": "u"}],
               requirements=[_requisito("REQ-1", critical=True)])
    _, lacunas = _codigos(check(tmp_path))
    assert "requirement_blocked" in lacunas


def test_requirement_decision_refs(tmp_path):
    caminhos = _feature(tmp_path)
    # sem arvore alguma: a referencia e desconhecida, recusa
    _reescreve(caminhos["define"], requirements=[_requisito("REQ-1", decision_refs=["DEC-1"])])
    recusas, _ = _codigos(check(tmp_path))
    assert "decision_ref_unknown" in recusas
    # com a arvore e a decisao aberta: lacuna do operador
    _arvore(tmp_path, "F1", [_decisao("DEC-1", "open")])
    _, lacunas = _codigos(check(tmp_path))
    assert "decision_open" in lacunas
    # decidida: some tudo
    _arvore(tmp_path, "F1", [_decisao("DEC-1", "decided")])
    plano = _meta(caminhos["plan"])
    plano["tasks"][0]["covers"] = ["AC1", "REQ-1"]
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    _restampa(tmp_path)
    recusas, lacunas = _codigos(check(tmp_path))
    assert "decision_ref_unknown" not in recusas and "decision_open" not in lacunas


def test_requirement_sem_cobertura_no_plan_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["define"], requirements=[_requisito("REQ-1")])
    _, lacunas = _codigos(check(tmp_path))
    assert "requirement_uncovered" in lacunas


# -- grafo de tarefas ---------------------------------------------------------


def _tarefa(ident: str, **extras) -> dict:
    return {
        "id": ident,
        "files": ["src/novo.py"],
        "covers": ["AC1"],
        "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
        **extras,
    }


def test_task_dep_desconhecida_e_ordem(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["plan"], tasks=[
        _tarefa("T1", depends_on=["T2"]),
        _tarefa("T2"),
        _tarefa("T3", depends_on=["T9"]),
    ])
    recusas, _ = _codigos(check(tmp_path))
    assert "task_dep_order" in recusas and "task_dep_unknown" in recusas


def test_task_dep_ciclo(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["plan"], tasks=[
        _tarefa("T1", depends_on=["T2"]),
        _tarefa("T2", depends_on=["T1"]),
    ])
    recusas, _ = _codigos(check(tmp_path))
    assert "task_dep_cycle" in recusas


def test_task_dep_dag_valido_e_ordem_no_status(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["plan"], tasks=[
        _tarefa("T1"),
        _tarefa("T2", depends_on=["T1"], risk="high", blocking=True),
    ])
    # T2 cobre outra parte; o build reporta so T1 e a convergencia veria
    # missing -- tiro o ship e o build para o teste ficar na plan-gate
    for fase in ("build_report", "ship"):
        caminhos[fase].unlink()
    _reescreve(caminhos["design"], status="ready")
    recusas, _ = _codigos(check(tmp_path))
    assert "task_dep_unknown" not in recusas and "task_dep_order" not in recusas
    [feature] = status(tmp_path)["features"]
    assert feature["graph"] == {"order": ["T1", "T2"]}


def test_task_parallel_sobreposto_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["plan"], tasks=[
        _tarefa("T1", parallel_safe=True, write_scope=["src/modulo"]),
        _tarefa("T2", parallel_safe=True, write_scope=["src/modulo/a.py"]),
        _tarefa("T3", parallel_safe=True, write_scope=["outro/lugar"]),
    ])
    _, lacunas = _codigos(check(tmp_path))
    assert "parallel_write_overlap" in lacunas


def test_topo_order_deterministica():
    tarefas = [
        _tarefa("T2", depends_on=["T1"]),
        _tarefa("T1"),
        _tarefa("T3"),
    ]
    assert topo_order(tarefas) == ["T1", "T2", "T3"]


# -- recibos de execucao ------------------------------------------------------


def _recibo(repo: Path, feature: str, saida: bytes | None = None, **extras) -> Path:
    (repo / DEFAULT_ROOT / feature).mkdir(parents=True, exist_ok=True)
    out = repo / DEFAULT_ROOT / feature / "run.out"
    out.write_bytes(saida if saida is not None else b"1 passed\n")
    recibo = {
        "schema": "forge/TestExecutionReceipt/v1",
        "executor": "teste",
        "command": ["python", "-m", "pytest", "tests/test_alvo.py", "-q"],
        "exit_code": 0,
        "baseline_sha": None,
        "baseline_reason": "primeira execucao",
        "tests": [{"name": "tests/test_alvo.py::test_alvo", "outcome": "passed"}],
        "output_path": out.relative_to(repo).as_posix(),
        "artifact_sha256": text_sha256(out),
        **extras,
    }
    caminho = repo / DEFAULT_ROOT / feature / "receipt.json"
    caminho.write_bytes(json.dumps(recibo).encode("utf-8"))
    return caminho


def _com_receipts(caminhos: dict, refs: list[str]) -> None:
    _reescreve(caminhos["build_report"], receipts=refs)


def test_receipt_ausente_e_recusa(tmp_path):
    caminhos = _feature(tmp_path)
    _com_receipts(caminhos, ["docs/sdd/F1/nao-existe.json"])
    recusas, _ = _codigos(check(tmp_path))
    assert "receipt_missing" in recusas


def test_receipt_invalido_e_schema(tmp_path):
    caminhos = _feature(tmp_path)
    caminho = tmp_path / DEFAULT_ROOT / "F1" / "receipt.json"
    caminho.write_bytes(b'{"schema": "forge/TestExecutionReceipt/v1"}')
    _com_receipts(caminhos, ["docs/sdd/F1/receipt.json"])
    recusas, _ = _codigos(check(tmp_path))
    assert "schema_invalid" in recusas


def test_receipt_com_falha_nao_prova_verde(tmp_path):
    caminhos = _feature(tmp_path)
    _recibo(tmp_path, "F1", tests=[
        {"name": "a", "outcome": "passed"},
        {"name": "b", "outcome": "failed"},
    ])
    _com_receipts(caminhos, ["docs/sdd/F1/receipt.json"])
    recusas, _ = _codigos(check(tmp_path))
    assert "receipt_failed" in recusas


def test_receipt_zero_testes_e_inconclusivo(tmp_path):
    caminhos = _feature(tmp_path)
    _recibo(tmp_path, "F1", exit_code=5, tests=[])
    _com_receipts(caminhos, ["docs/sdd/F1/receipt.json"])
    recusas, lacunas = _codigos(check(tmp_path))
    assert "receipt_inconclusive" in lacunas and "receipt_failed" not in recusas


def test_receipt_saida_adulterada_e_stale(tmp_path):
    caminhos = _feature(tmp_path)
    _recibo(tmp_path, "F1")
    _com_receipts(caminhos, ["docs/sdd/F1/receipt.json"])
    # a saida muda DEPOIS do recibo: o hash gravado nao bate mais
    (tmp_path / DEFAULT_ROOT / "F1" / "run.out").write_bytes(b"outra saida\n")
    recusas, _ = _codigos(check(tmp_path))
    assert "receipt_stale" in recusas


def test_receipt_saida_ausente_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    _recibo(tmp_path, "F1")
    (tmp_path / DEFAULT_ROOT / "F1" / "run.out").unlink()
    _com_receipts(caminhos, ["docs/sdd/F1/receipt.json"])
    _, lacunas = _codigos(check(tmp_path))
    assert "receipt_output_missing" in lacunas


def test_receipt_valido_passa(tmp_path):
    caminhos = _feature(tmp_path)
    _recibo(tmp_path, "F1")
    _com_receipts(caminhos, ["docs/sdd/F1/receipt.json"])
    recusas, lacunas = _codigos(check(tmp_path))
    assert "receipt_missing" not in recusas + lacunas
    assert "receipt_stale" not in recusas


def test_validate_receipt_sem_repo_nao_confere_hash(tmp_path):
    caminho = _recibo(tmp_path, "F1")
    recibo, _ = load_receipt(caminho)
    assert validate_receipt(recibo, None) == []


def test_baseline_null_exige_razao(tmp_path):
    caminho = _recibo(tmp_path, "F1", baseline_reason=None)
    recibo, _ = load_receipt(caminho)
    assert [a.kind for a in validate_receipt(recibo, tmp_path)] == ["invalid"]


# -- convergencia -------------------------------------------------------------


def test_converge_limpo_e_ok(tmp_path):
    _feature(tmp_path)
    relatorio = converge(tmp_path)
    assert relatorio["schema"] == "forge/ConvergenceReport/v1"
    assert relatorio["ok"] is True and relatorio["items"] == []
    assert relatorio["git"]["available"] is False


def test_converge_tarefa_a_mais_no_build_e_informacao(tmp_path):
    caminhos = _feature(tmp_path)
    build = _meta(caminhos["build_report"])
    build["tasks"].append({"id": "T2", "status": "skipped"})
    _reescreve(caminhos["build_report"], tasks=build["tasks"])
    _restampa(tmp_path)  # o upstream do ship refaz o hash, senao vira stale
    relatorio = converge(tmp_path)
    assert relatorio["ok"] is True
    [item] = relatorio["items"]
    assert item["class"] == "unrequested" and item["item"] == "T2"


def test_converge_tarefa_do_plan_sem_build_e_missing(tmp_path):
    caminhos = _feature(tmp_path)
    plano = _meta(caminhos["plan"])
    plano["tasks"].append(_tarefa("T2", covers=[]))
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    relatorio = converge(tmp_path)
    assert relatorio["ok"] is False
    assert any(i["class"] == "missing" and i["item"] == "T2" for i in relatorio["items"])


def test_converge_done_sem_green_e_unverified(tmp_path):
    caminhos = _feature(tmp_path)
    build = _meta(caminhos["build_report"])
    del build["tasks"][0]["green"]
    _reescreve(caminhos["build_report"], tasks=build["tasks"])
    relatorio = converge(tmp_path)
    assert any(i["class"] == "unverified" and i["item"] == "T1" for i in relatorio["items"])


def test_converge_done_com_green_ruim_contradiz(tmp_path):
    caminhos = _feature(tmp_path)
    build = _meta(caminhos["build_report"])
    build["tasks"][0]["green"]["exit"] = 1
    _reescreve(caminhos["build_report"], tasks=build["tasks"])
    relatorio = converge(tmp_path)
    assert any(i["class"] == "contradicts" and i["item"] == "T1" for i in relatorio["items"])


def test_converge_upstream_stale_aparece(tmp_path):
    caminhos = _feature(tmp_path)
    caminhos["plan"].write_bytes(caminhos["plan"].read_bytes() + b"\nmudou\n")
    relatorio = converge(tmp_path)
    assert any(
        i["class"] == "stale" and i["covered_by"] == "upstream_stale"
        for i in relatorio["items"]
    )


def test_converge_git_de_worktree_lido_por_arquivo(tmp_path):
    _feature(tmp_path)
    gitdir = tmp_path / "gitdir-real"
    gitdir.mkdir()
    (gitdir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (gitdir / "refs" / "heads").mkdir(parents=True)
    (gitdir / "refs" / "heads" / "main").write_text("a" * 40 + "\n", encoding="utf-8")
    (tmp_path / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    relatorio = converge(tmp_path)
    assert relatorio["git"]["available"] is True
    assert relatorio["git"]["head"] == "main"


def test_ship_sem_convergence_recebe_codigo_por_divergencia(tmp_path):
    caminhos = _feature(tmp_path)
    plano = _meta(caminhos["plan"])
    plano["tasks"].append(_tarefa("T2", covers=[]))
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    _restampa(tmp_path)
    recusas, _ = _codigos(check(tmp_path))
    assert "convergence_diverged" in recusas


def test_ship_convergence_gravada_que_bate_e_lacuna(tmp_path):
    caminhos = _feature(tmp_path)
    plano = _meta(caminhos["plan"])
    plano["tasks"].append(_tarefa("T2", covers=[]))
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    _restampa(tmp_path)
    vivas = converge(tmp_path, feature="F1")["items"]
    _reescreve(caminhos["ship"], convergence={
        "divergences": [
            {k: i[k] for k in ("class", "item", "path", "reason", "covered_by")}
            for i in vivas
        ]
    })
    _restampa(tmp_path)
    recusas, lacunas = _codigos(check(tmp_path))
    assert "convergence_open" in lacunas and "convergence_diverged" not in recusas


def test_ship_convergence_gravada_velha_e_stale(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["ship"], convergence={"divergences": [{
        "class": "missing", "item": "T9", "path": "x", "reason": "r",
    }]})
    _restampa(tmp_path)
    recusas, _ = _codigos(check(tmp_path))
    assert "convergence_stale" in recusas


def test_ship_done_nao_confere_convergencia(tmp_path):
    caminhos = _feature(tmp_path)
    _reescreve(caminhos["ship"], status="done")
    plano = _meta(caminhos["plan"])
    plano["tasks"].append(_tarefa("T2", covers=[]))
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    _restampa(tmp_path)
    recusas, lacunas = _codigos(check(tmp_path))
    assert "convergence_diverged" not in recusas and "convergence_open" not in lacunas


# -- persistencia -------------------------------------------------------------


def test_persistence_declarada_cobre_o_checklist(tmp_path):
    caminhos = _feature(tmp_path)
    define = _meta(caminhos["define"])
    define["change_kinds"] = ["data_persistence"]
    _reescreve(caminhos["define"], change_kinds=define["change_kinds"])
    _restampa(tmp_path)
    _, lacunas = _codigos(check(tmp_path))
    assert lacunas.count("persistence_undeclared") == 15 * 2  # design e plan


def test_persistence_respondida_fecha(tmp_path):
    caminhos = _feature(tmp_path)
    define = _meta(caminhos["define"])
    define["change_kinds"] = ["data_persistence"]
    _reescreve(caminhos["define"], change_kinds=define["change_kinds"])
    tratamento = {item: f"tratado no desenho ({item})" for item in (
        "atomicity", "isolation", "consistency", "idempotency", "concurrency",
        "versioning", "schema_evolution", "business_key", "reprocessing",
        "retry", "snapshot_commit_rollback", "recovery", "partial_update",
        "negative_tests", "functional_metrics",
    )}
    _reescreve(caminhos["design"], persistence=tratamento)
    _reescreve(caminhos["plan"], persistence=tratamento)
    _restampa(tmp_path)
    # ship lista o registro do kind
    _reescreve(caminhos["ship"], registries=["sdd_persistence_check"])
    _restampa(tmp_path)
    _, lacunas = _codigos(check(tmp_path))
    assert "persistence_undeclared" not in lacunas


def test_persistence_detectada_so_no_operator(tmp_path):
    caminhos = _feature(tmp_path)
    design = _meta(caminhos["design"])
    design["files"].append({
        "path": "etl/glue_job_loader.py", "action": "create", "reason": "r",
    })
    _reescreve(caminhos["design"], files=design["files"])
    _restampa(tmp_path)
    _, lacunas = _codigos(check(tmp_path))
    # dev: caminho com "glue" e codigo de ferramenta, nao escrita de dados
    assert "persistence_undeclared" not in lacunas


def test_persistence_operator_detecta_caminho(tmp_path):
    repo = tmp_path
    (repo / ".sparkforge_aws").mkdir(exist_ok=True)
    (repo / ".sparkforge_aws" / "case.yaml").write_bytes(b"case_id: C1\n")
    (repo / ".sparkforge_aws" / "sandbox" / "S1").mkdir(parents=True)
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_alvo.py").write_bytes(b"def test_alvo():\n    assert True\n")
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src" / "existente.py").write_bytes(b"x = 1\n")
    comum = {"sdd": 1, "feature": "F1", "profile": "operator", "status": "ready"}
    define = _grava(repo, "F1", "define", {
        **comum,
        "phase": "define",
        "case_id": "C1",
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [{
            "id": "AC1",
            "statement": "s",
            "verified_by": {"kind": "test", "ref": "tests/test_alvo.py::test_alvo"},
        }],
        "success": [],
        "out_of_scope": [],
        "change_kinds": [],
    })
    _grava(repo, "F1", "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream(repo, define),
        "files": [{"path": "etl/glue_job.py", "action": "create", "reason": "r"}],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "r"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
    })
    _, lacunas = _codigos(check(repo))
    assert "persistence_undeclared" in lacunas


# -- CLI ----------------------------------------------------------------------


def test_sdd_converge_cli_sai_1_com_divergencia(tmp_path, capsys):
    from sparkforge_aws.adapters.cli import main

    caminhos = _feature(tmp_path)
    plano = _meta(caminhos["plan"])
    plano["tasks"].append(_tarefa("T2", covers=[]))
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    assert main(["sdd", "converge", "--repo", str(tmp_path)]) == 1
    saida = json.loads(capsys.readouterr().out)
    assert saida["ok"] is False


def test_sdd_converge_cli_feature_desconhecida_sai_2(tmp_path):
    from sparkforge_aws.adapters.cli import main

    _feature(tmp_path)
    assert main(["sdd", "converge", "--repo", str(tmp_path), "--feature", "ZZ9"]) == 2


# -- templates versionados ------------------------------------------------------


def test_template_decisions_valida_como_arvore(tmp_path):
    arvore = json.loads(
        (ROOT / "docs/sdd/templates/decisions.json").read_bytes().decode("utf-8")
    )
    # template bom: nenhum erro estrutural; `open` e lacuna legitima de exemplo
    assert {f.kind for f in validate_decisions(arvore)} <= {"open"}


def test_template_receipt_casa_com_a_saida(tmp_path):
    """O recibo de exemplo precisa declarar o sha256 real do .out ao lado."""
    pasta = ROOT / "docs/sdd/templates"
    recibo = json.loads((pasta / "receipt-build.json").read_bytes().decode("utf-8"))
    out = pasta / "receipt-build.out"
    assert out.is_file()
    # o recibo aponta para docs/sdd/EXEMPLO/... — no repo dele, o arquivo e o
    # proprio template .out; aqui o que interessa e o hash do conteudo
    assert recibo["artifact_sha256"] == text_sha256(out)
    recibo["output_path"] = "receipt-build.out"
    assert validate_receipt(recibo, pasta) == []
