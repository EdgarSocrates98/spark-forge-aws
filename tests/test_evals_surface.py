"""`sparkforge-aws evals` + a classificacao §7.1 persistida no manifesto
forge/context/v1 (lf-0038, install-2.0 ciclo 5).

O que este arquivo prova, na ordem:

1. as 4 categorias do §7.1 existem e toda suite declarada carrega uma;
2. o manifesto registra a classificacao (`eval_suites[].kind` +
   `capabilities.evals.detail`) dentro do shape fechado (id, kind, command);
3. §7.3 — gabaritos selados nunca saem: nem `describe`, nem `list`, nem o
   manifesto ecoam conteudo de `expected/` ou de qualquer resposta; suites
   de host recusam execucao pela CLI (executor != avaliador); e toda suite
   declara o ambiente que a prova representa (simulado != real);
4. os runners deterministicos rodam e marcam o ambiente no resultado.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from sparkforge_aws import discovery_ops
from sparkforge_aws.evals import surface, taxonomy
from sparkforge_aws.install.lifecycle import _context_manifest

ROOT = Path(__file__).resolve().parents[1]
CLI = "sparkforge-aws"

_ITEM_ID_RE = re.compile(r"^[a-z0-9-_]{1,128}$")


# ---------------------------------------------------------------------------
# §7.1 — a classificacao existe, e completa
# ---------------------------------------------------------------------------


def test_all_suites_carry_a_declared_kind():
    kinds = set(taxonomy.KINDS)
    for suite in taxonomy.catalog():
        assert suite["kind"] in kinds, suite["id"]
        assert suite["environment"] in ("deterministic", "simulated", "host")
        assert _ITEM_ID_RE.match(suite["id"]), f"id fora do ITEM_ID_RE: {suite['id']}"


def test_the_four_categories_are_all_populated():
    counts = taxonomy.kind_counts()
    assert set(counts) == {
        "developer",
        "runtime-decision",
        "output-verification",
        "host-conformance",
    }
    assert all(v > 0 for v in counts.values()), counts


def test_listing_is_the_classified_inventory():
    payload = taxonomy.listing()
    assert payload["counts"] == taxonomy.kind_counts()
    assert {s["id"] for s in payload["suites"]} == set(taxonomy.suite_ids())
    for suite in payload["suites"]:
        # o que o inventario NAO traz: conteudo de gabarito, resposta, expected
        assert "answer" not in suite
        assert "expected" not in suite


# ---------------------------------------------------------------------------
# manifesto forge/context/v1 — classificacao persistida, schema fechado
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest():
    return _context_manifest(
        scope="project", profile="recommended", hosts=["claude"], components=None
    )


def test_manifest_eval_suites_are_classified(manifest):
    from sparkforge_aws import _forgecontext as fctx

    assert fctx.validate_manifest(manifest) == []
    suites = manifest["eval_suites"]
    assert {s["id"] for s in suites} == set(taxonomy.suite_ids())
    kinds = {s["kind"] for s in suites}
    assert kinds == set(taxonomy.KINDS), kinds
    for s in suites:
        assert s["kind"] in fctx.EVAL_KINDS
        # shape fechado (id, kind, command) — o command e o describe read-only
        assert set(s) == {"id", "kind", "command"}
        assert s["command"][:3] == [CLI, "evals", "describe"]


def test_manifest_evals_capability_detail(manifest):
    detail = manifest["capabilities"]["evals"]["detail"]
    for kind in taxonomy.KINDS:
        assert kind in detail


def test_manifest_declares_the_7_2_ops_as_commands(manifest):
    ids = {c["id"] for c in manifest["discovery"]["commands"]}
    for esperado in (
        "evals-list",
        "evals-describe",
        "evals-run",
        "evals-result",
        "verification-plan",
        "verification-run",
    ):
        assert esperado in ids
    # e o mapa de ops do §6.2 continua fechado — nenhum op §7.2 nele
    assert not any(
        op.startswith(("evals.", "verification.")) for op in manifest["discovery"]["ops"]
    )


def test_eval_commands_source_is_discovery_ops():
    comandos = discovery_ops.eval_commands()
    assert [c["id"] for c in comandos] == [
        "evals-list",
        "evals-describe",
        "evals-run",
        "evals-result",
        "verification-plan",
        "verification-run",
    ]
    for c in comandos:
        assert c["argv"][0] == CLI
        assert _ITEM_ID_RE.match(c["id"])
    assert set(discovery_ops.eval_ops_expanded()) == {
        "evals.list",
        "evals.describe",
        "evals.run",
        "evals.result",
        "verification.plan",
        "verification.run",
    }


# ---------------------------------------------------------------------------
# §7.3 — gabarito selado, executor != avaliador, simulado != real
# ---------------------------------------------------------------------------


def _fatias_de_resposta() -> list[str]:
    """Fatias de 40 chars do meio de cada arquivo de resposta conhecida — se
    qualquer uma aparecer num payload de describe/list/manifest, houve vazamento
    de gabarito (colisao de 40 chars e improvavel ao ponto de nao ser
    argumento)."""
    alvos = [
        *ROOT.glob("evals/holdout/*/expected/assessment.json"),
        ROOT / "evals" / "fase0.xml",
    ]
    fatias: list[str] = []
    for arquivo in alvos:
        texto = arquivo.read_text(encoding="utf-8")
        meio = len(texto) // 2
        fatias.append(texto[meio : meio + 40])
    assert len(fatias) >= 3
    return fatias


def test_describe_never_echoes_sealed_answers():
    """§7.3: o teste de exposicao — um agente pedindo `evals describe` de uma
    suite selada recebe metadados e hash, nunca bytes do gabarito."""
    for suite_id in taxonomy.suite_ids():
        payload = json.dumps(taxonomy.describe(suite_id), ensure_ascii=False)
        for fatia in _fatias_de_resposta():
            assert fatia not in payload, f"describe({suite_id}) vazou gabarito"


def test_listing_and_manifest_do_not_leak_answers(manifest):
    for payload in (
        json.dumps(taxonomy.listing(), ensure_ascii=False),
        json.dumps(manifest["eval_suites"], ensure_ascii=False),
        json.dumps(manifest["capabilities"]["evals"], ensure_ascii=False),
    ):
        for fatia in _fatias_de_resposta():
            assert fatia not in payload


def test_sealed_suites_mark_the_answers_as_not_emitted():
    seladas = [s for s in taxonomy.catalog() if s["sealed"]]
    assert seladas, "nenhuma suite selada — a postura §7.3 estaria vazia"
    for s in seladas:
        desc = taxonomy.describe(s["id"])
        assert desc["expected_answers"].startswith("sealed")
        assert desc["integrity"]["suite_sha256"] != "unresolved"


def test_evals_run_refuses_suites_that_only_a_host_executes():
    """§7.3: a CLI nao incorpora o agente avaliado — suites de host sao
    recusa nomeada, nao execucao sintetica."""
    for s in taxonomy.catalog():
        if s["environment"] != "host":
            continue
        with pytest.raises(taxonomy.TaxonomyError, match=taxonomy.E_HOST):
            surface.run(s["id"])


def test_evals_result_rejects_non_host_suites():
    with pytest.raises(taxonomy.TaxonomyError, match=taxonomy.E_UNAVAILABLE):
        surface.result("holdout", "qualquer")


def test_evals_result_rejects_run_name_traversal():
    """§13.1: --run nunca escapa do runs_root — traversal, absoluto e
    separadores viram recusa nomeada antes de tocar o filesystem."""
    for bad in ("../../x", "..", "/abs/path", "a/b", "C:\\runs\\x", ".hidden-ok?"):
        with pytest.raises(taxonomy.TaxonomyError, match=taxonomy.E_UNAVAILABLE):
            surface.result("agentic-recovery", bad)
    assert not Path("/abs/path/scorecard.json").exists()


def test_safe_run_dir_stays_under_root(tmp_path):
    root = tmp_path / "runs"
    root.mkdir()
    good = surface._safe_run_dir(root, "run-2026-10-22.a1")
    assert good.parent == root.resolve()
    with pytest.raises(taxonomy.TaxonomyError):
        surface._safe_run_dir(root, "../out")


def test_unknown_suite_is_a_named_refusal():
    with pytest.raises(taxonomy.TaxonomyError, match=taxonomy.E_SUITE):
        taxonomy.describe("suite-inexistente")


def test_every_suite_marks_the_environment_it_proves():
    """§7.3: simulado/deterministico nao e prova de ambiente real — marcado
    em todo describe."""
    for s in taxonomy.catalog():
        desc = taxonomy.describe(s["id"])
        if s["environment"] == "host":
            assert "real environment" in desc["proof"]
        else:
            assert "not real-environment proof" in desc["proof"]


# ---------------------------------------------------------------------------
# runners deterministicos — evidencia real, falhas explicitas
# ---------------------------------------------------------------------------


def test_evals_run_holdout_recomputes_the_goldens():
    payload = surface.run("holdout")
    assert payload["status"] == "pass"
    assert payload["environment"] == "deterministic"
    assert payload["real_environment_proof"] is False
    assert len(payload["scenarios"]) >= 2
    # o resultado nunca ecoa o arquivo expected — so o veredito do motor
    for fatia in _fatias_de_resposta()[:2]:
        assert fatia not in json.dumps(payload, ensure_ascii=False)


def test_evals_run_forge_lab_marks_simulated():
    payload = surface.run("forge-lab-golden20")
    assert payload["environment"] == "simulated"
    assert payload["real_environment_proof"] is False
    assert payload["status"] == "pass"


def test_evals_run_decision_plane():
    payload = surface.run("decision-plane")
    assert payload["status"] == "pass"
    assert payload["environment"] == "deterministic"


# ---------------------------------------------------------------------------
# CLI de verdade — os verbos existem e respondem
# ---------------------------------------------------------------------------


def _cli(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sparkforge_aws.adapters.cli", *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_cli_evals_list():
    proc = _cli("evals", "list")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["counts"] == taxonomy.kind_counts()


def test_cli_evals_describe_holdout_is_metadata_only():
    proc = _cli("evals", "describe", "--suite", "holdout")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["sealed"] is True
    for fatia in _fatias_de_resposta()[:2]:
        assert fatia not in proc.stdout


def test_cli_evals_run_host_suite_refuses():
    proc = _cli("evals", "run", "--suite", "agentic-fase0")
    assert proc.returncode == 2
    assert "EVALS-REQUIRES-HOST" in proc.stderr


def test_cli_verification_ops_exist():
    """§7.4: verification.plan/run sao os verbos funcval — o fluxo
    plan->run->evidence e invocavel pela CLI, com falhas explicitas."""
    plan = _cli("funcval", "plan", "--help")
    assert plan.returncode == 0
    compare = _cli("funcval", "compare", "--help")
    assert compare.returncode == 0
