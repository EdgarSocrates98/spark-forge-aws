"""O SDD no perfil operator (features SDD_OPERATOR e SDD_OPERATOR_DURAVEL).

O fluxo ponta a ponta usa as tools reais: `sparkforge_case_open` grava o case,
`sparkforge_change_sandbox` cria o sandbox cujo id vira `change_id`,
`sparkforge_change_propose` monta o pacote e `sparkforge_analyze_pyspark` da os
facts. Nada de `.sparkforge/` fabricado a mao -- isso o teste do nucleo ja faz.

A spec do operador mora em `.sparkforge/sdd` (`--root`), porque a varredura do
sandbox poda `.sparkforge` e a copia validada continua valendo.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from sparkforge.adapters.tools import call_tool
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd.checks import check
from sparkforge.sdd.stamp import stamp

ROOT = Path(__file__).resolve().parents[1]
FEATURE = "JOB_SHUFFLE"
RAIZ = ".sparkforge/sdd"
REGRA = "SF-PY-012"
_NOW = "2026-09-16T00:00:00Z"

_JOB = b'def configurar(spark):\n    spark.conf.set("spark.sql.shuffle.partitions", "800")\n'
_TESTE_DO_JOB = b"def test_configurar():\n    assert True\n"
_DIFF = (
    b"--- a/lib/job.py\n"
    b"+++ b/lib/job.py\n"
    b"@@ -1,2 +1,2 @@\n"
    b" def configurar(spark):\n"
    b'-    spark.conf.set("spark.sql.shuffle.partitions", "800")\n'
    b"+    return spark\n"
)

# a forma de `sparkforge/facts/funcval.py::_check_delta`
_DELTA = {
    "id": "d1",
    "kind": "funcval.check_delta",
    "subject": {"type": "table", "symbol": "db.vendas#row_count"},
    "measures": {"before": 10, "after": 10},
    "attrs": {"axis": "count", "check": "row_count", "comparison": "exact",
              "planned": True, "target": "db.vendas", "type": "bigint"},
    "provenance": {"artifact": "compare", "artifact_sha256": "", "extractor": "funcval"},
}


def _grava(repo: Path, fase: str, meta: dict, raiz: str) -> Path:
    pasta = repo / raiz / FEATURE
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{fase}.md"
    texto = "---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\ncorpo\n"
    arquivo.write_bytes(texto.encode("utf-8"))
    if "upstream" in meta:
        stamp(repo, f"{raiz}/{FEATURE}/{fase}.md", root=raiz)
    return arquivo


def _upstream(fase: str, raiz: str) -> dict:
    return {"path": f"{raiz}/{FEATURE}/{fase}.md", "sha256": ""}


def _repositorio_do_operador(repo: Path) -> Path:
    (repo / "lib").mkdir(parents=True)
    (repo / "lib" / "job.py").write_bytes(_JOB)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_job.py").write_bytes(_TESTE_DO_JOB)
    diff = repo.parent / "d.patch"
    diff.write_bytes(_DIFF)
    return diff


def _evidencias(repo: Path, raiz: str) -> Path:
    """Facts reais do job e a comparacao do funcval, na pasta da feature."""
    pasta = repo / raiz / FEATURE
    pasta.mkdir(parents=True, exist_ok=True)
    fatos = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
    assert "pyspark.conf_set" in {f["kind"] for f in fatos["items"]}, fatos
    (pasta / "facts.json").write_bytes(json.dumps({"items": fatos["items"]}).encode("utf-8"))
    comparacao = pasta / "compare.json"
    comparacao.write_bytes(json.dumps({"items": [_DELTA]}).encode("utf-8"))
    return comparacao


def _sha_do_relatorio(repo: Path, change_id: str) -> str:
    """O que o ship grava em evidence: o text_sha256 do relatorio que ele leu."""
    return text_sha256(repo / ".sparkforge" / "sandbox" / change_id / "report.json")


def _feature_operator(repo: Path, case_id: str, change_id: str, raiz: str = RAIZ) -> None:
    pasta = f"{raiz}/{FEATURE}"
    comum = {"sdd": 1, "feature": FEATURE, "profile": "operator", "status": "done"}
    _grava(repo, "define", {
        **comum,
        "phase": "define",
        "case_id": case_id,
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [
            {
                "id": "AC1",
                "statement": "o resultado nao muda",
                "verified_by": {"kind": "funcval", "ref": f"{pasta}/compare.json"},
            },
            {
                "id": "AC2",
                "statement": "o job pede a configuracao que a mudanca tira",
                "verified_by": {"kind": "fact", "ref": f"{pasta}/facts.json#kind:pyspark.conf_set"},
            },
        ],
        "success": [{"id": "SC1", "metric": "m", "source": f"{pasta}/compare.json"}],
        "out_of_scope": [],
        "change_kinds": ["tool_or_verb"],
    }, raiz)
    _grava(repo, "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream("define", raiz),
        "files": [{"path": "lib/job.py", "action": "modify", "reason": "r"}],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "rollback.patch"}],
        "covers": [{"part": "p", "acceptance": ["AC1", "AC2"]}],
    }, raiz)
    _grava(repo, "plan", {
        **comum,
        "phase": "plan",
        "upstream": _upstream("design", raiz),
        "tasks": [
            {
                "id": "T1",
                "files": ["lib/job.py"],
                "covers": ["AC1"],
                "test": {"path": "tests/test_job.py", "name": "test_configurar"},
            },
            {
                "id": "T2",
                "files": ["lib/job.py"],
                "covers": ["AC2"],
                "proof": {"kind": "finding", "ref": f"#{REGRA}"},
            },
        ],
    }, raiz)
    _grava(repo, "build_report", {
        **comum,
        "phase": "build_report",
        "upstream": _upstream("plan", raiz),
        "change_id": change_id,
        "tasks": [
            {
                "id": "T1",
                "status": "done",
                "red": {"command": "pytest tests/test_job.py", "exit": 1},
                "green": {"command": "pytest tests/test_job.py", "exit": 0},
            },
            {
                "id": "T2",
                "status": "done",
                "moved": {"change_id": change_id, "resolved": [REGRA]},
            },
        ],
        "claims": [{"text": "resultado igual", "evidence_ref": f"{pasta}/compare.json"}],
    }, raiz)
    _grava(repo, "ship", {
        **comum,
        "phase": "ship",
        "upstream": _upstream("build_report", raiz),
        "hypothesis_outcome": "confirmed",
        "registries": ["surface_lock", "generated_reference"],
        "deviations": [],
        "evidence": [
            {"change_id": change_id, "report_sha256": _sha_do_relatorio(repo, change_id)},
        ],
    }, raiz)


def _codigos(relatorio: dict) -> tuple[list[str], list[str]]:
    return (
        sorted(r["code"] for r in relatorio["refused"]),
        sorted(r["code"] for r in relatorio["unresolved"]),
    )


def _check(repo: Path) -> tuple[list[str], list[str]]:
    return _codigos(check(repo, root=RAIZ, feature=FEATURE))


def _reescreve_status(repo: Path, fase: str, status: str) -> None:
    arquivo = repo / RAIZ / FEATURE / f"{fase}.md"
    texto = arquivo.read_bytes().decode("utf-8")
    arquivo.write_bytes(texto.replace("status: done", f"status: {status}", 1).encode("utf-8"))


def _ship_done_sem_evidencia(repo: Path) -> None:
    """Ship em done e sem `evidence`; ele e a ultima fase, entao nada fica stale."""
    arquivo = repo / RAIZ / FEATURE / "ship.md"
    _, bloco, corpo = arquivo.read_bytes().decode("utf-8").split("---\n", 2)
    meta = yaml.safe_load(bloco)
    meta["status"] = "done"
    del meta["evidence"]
    arquivo.write_bytes(
        ("---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n" + corpo).encode("utf-8")
    )


def test_fluxo_operator_ponta_a_ponta(tmp_path):
    repo = tmp_path / "repo"
    diff = _repositorio_do_operador(repo)
    caso = call_tool("sparkforge_case_open", {"repo": str(repo), "case_id": "C-42", "now": _NOW})
    assert caso.get("case_id") == "C-42", caso
    sandbox = call_tool("sparkforge_change_sandbox", {"repo": str(repo), "diff_path": str(diff)})
    change_id = sandbox.get("id")
    assert change_id and (repo / ".sparkforge" / "sandbox" / change_id).is_dir(), sandbox
    assert REGRA in {r["rule_id"] for r in sandbox["resolved"]}, sandbox
    # o sandbox nunca escreve na arvore do operador
    assert (repo / "lib" / "job.py").read_bytes() == _JOB

    comparacao = _evidencias(repo, RAIZ)
    _feature_operator(repo, caso["case_id"], change_id)
    relatorio = check(repo, root=RAIZ, feature=FEATURE)
    assert _codigos(relatorio) == ([], []), relatorio
    assert relatorio["ok"] is True

    # a spec em .sparkforge/sdd nao desatualiza a copia validada
    proposta = call_tool("sparkforge_change_propose",
                         {"repo": str(repo), "sandbox_id": change_id, "now": _NOW})
    assert proposta["refused"] == [], proposta
    assert (repo / ".sparkforge" / "proposal" / change_id).is_dir()
    # com o ship done e os dois relatorios presentes, os dois casam com o hash
    # gravado: a proposal guarda a mesma serializacao do sandbox
    assert _check(repo) == ([], [])

    # comparacao sem nenhum check_delta nao e comparacao
    comparacao.write_bytes(json.dumps({"items": [{"id": "x", "kind": "funcval.analyzed"}]})
                           .encode("utf-8"))
    assert _check(repo) == (["funcval_not_comparison"], [])
    comparacao.write_bytes(json.dumps({"items": [_DELTA]}).encode("utf-8"))

    # sandbox limpo: o pacote de proposal guarda o id e o relatorio
    call_tool("sparkforge_change_sandbox", {"repo": str(repo), "clean": True})
    assert not (repo / ".sparkforge" / "sandbox" / change_id).exists()
    assert _check(repo) == ([], [])

    # sem nenhum dos dois e com outro case: o ship done deixa as referencias
    # historicas, sustentadas pelo hash que ele gravou
    shutil.rmtree(repo / ".sparkforge" / "proposal" / change_id)
    outro = call_tool("sparkforge_case_open",
                      {"repo": str(repo), "case_id": "C-43", "now": _NOW, "reopen": True})
    assert outro.get("case_id") == "C-43", outro
    assert _check(repo) == ([], [])
    # com o ship ainda aberto, tudo volta a ser conferido
    _reescreve_status(repo, "ship", "ready")
    assert _check(repo) == (
        ["case_missing", "change_missing", "moved_not_observed", "moved_not_observed"], []
    )
    # ship done sem ter gravado o que leu: nada sustenta a historia
    _ship_done_sem_evidencia(repo)
    assert _check(repo) == (["ship_evidence_missing"], [])


def test_spec_em_docs_sdd_desatualiza_o_sandbox(tmp_path):
    """O contraste de D1: a mesma spec em docs/sdd muda a arvore que o sandbox copiou."""
    repo = tmp_path / "repo"
    diff = _repositorio_do_operador(repo)
    caso = call_tool("sparkforge_case_open", {"repo": str(repo), "case_id": "C-42", "now": _NOW})
    sandbox = call_tool("sparkforge_change_sandbox", {"repo": str(repo), "diff_path": str(diff)})
    _evidencias(repo, "docs/sdd")
    _feature_operator(repo, caso["case_id"], sandbox["id"], raiz="docs/sdd")
    proposta = call_tool("sparkforge_change_propose",
                         {"repo": str(repo), "sandbox_id": sandbox["id"], "now": _NOW})
    assert [r["reason"] for r in proposta["refused"]] == ["sandbox_desatualizado"], proposta


COORDENADORES = (
    "spark-performance-architect",
    "glue-incremental-performance-architect",
    "glue-infra-reviewer",
    "pyspark-code-reviewer",
)


def test_coordenadores_apontam_o_sdd():
    # as sdd-* sao nao-despachaveis (scripts/sync_skills.py::NON_DISPATCHABLE_SKILLS):
    # o coordenador as cita na prosa e fica sem elas no `skills:`
    for nome in COORDENADORES:
        texto = (ROOT / "agents" / f"{nome}.md").read_text(encoding="utf-8")
        frente, corpo = texto.split("\n---\n", 1)
        assert "sdd-" not in frente, nome
        assert "`sdd-define`" in corpo and "`sdd-build`" in corpo, nome
        assert "sparkforge sdd check" in corpo, nome
        assert "sparkforge case open" in corpo, nome


_OPERADOR_DURAVEL = {
    "sdd-define": ("--root .sparkforge/sdd", "#kind:"),
    "sdd-plan": ("--root .sparkforge/sdd", "proof", "finding"),
    "sdd-build": ("--root .sparkforge/sdd", "moved", "--out", "--funcval", "--benchmark"),
    "sdd-ship": ("--root .sparkforge/sdd", "--funcval", "--benchmark", "done"),
}


def test_skills_ensinam_o_operador_duravel():
    for nome, trechos in _OPERADOR_DURAVEL.items():
        texto = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        operador = texto.split("## Perfil operator", 1)[1].split("\n## ", 1)[0]
        for trecho in trechos:
            assert trecho in operador, (nome, trecho)
    readme = (ROOT / "docs" / "sdd" / "README.md").read_text(encoding="utf-8")
    for trecho in ("--root .sparkforge/sdd", "sparkforge change sandbox",
                   "sparkforge change propose", "#kind:"):
        assert trecho in readme, trecho


def _skill_e_operador(nome: str) -> tuple[str, str]:
    texto = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
    return texto, texto.split("## Perfil operator", 1)[1].split("\n## ", 1)[0]


def test_skills_ensinam_a_evidencia_do_ship():
    """SDD_ENDURECIMENTO AC10: evidence, os codigos novos e o contrato vivo."""
    ship, ship_operador = _skill_e_operador("sdd-ship")
    for trecho in ("evidence", "report_sha256", "ship_evidence_missing",
                   "ship_evidence_mismatch"):
        assert trecho in ship_operador, trecho
    build, build_operador = _skill_e_operador("sdd-build")
    assert "moved_change_mismatch" in build_operador
    for texto in (ship, build):
        assert "docs/sdd/CONTRATO.md" in texto
    readme = (ROOT / "docs" / "sdd" / "README.md").read_text(encoding="utf-8")
    for trecho in ("evidence", "ship_evidence_missing", "moved_change_mismatch",
                   "CONTRATO.md"):
        assert trecho in readme, trecho
    congelado = (ROOT / "docs" / "superpowers" / "specs"
                 / "2026-09-16-sdd-nucleo-design.md").read_text(encoding="utf-8")
    assert "docs/sdd/CONTRATO.md" in "\n".join(congelado.splitlines()[:12])
