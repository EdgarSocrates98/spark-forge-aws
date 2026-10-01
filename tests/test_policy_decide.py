"""Decisao pura da policy, schema e geracao de `permissions.ask`."""
from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.policy.decide import (
    ALLOW,
    ASK,
    DENY,
    casa_caminho,
    decidir_bash,
    decidir_caminho,
    decidir_tool,
    dividir_comando,
)
from sparkforge.policy.load import PolicyError, Politica, Regra, carregar
from sparkforge.policy.schema import SCHEMA, validar
from sparkforge.policy.settings import regras_ask

ROOT = Path(__file__).resolve().parents[1]
R = [Regra("terraform destroy *", ASK, "x"), Regra("aws s3 rm *", DENY, "y")]


@pytest.mark.parametrize("comando,segmentos", [
    ("git status", ["git status"]),
    ("cd infra && terraform destroy -auto-approve",
     ["cd infra", "terraform destroy -auto-approve"]),
    ("a; b | c || d", ["a", "b", "c", "d"]),
    ('echo "$(aws s3 rm s3://x/y)"', ['echo " "', "aws s3 rm s3://x/y"]),
    ("FOO=1 BAR=2 sudo env timeout 30 terraform apply", ["terraform apply"]),
    ("bash -c 'terraform destroy'", ["terraform destroy"]),
    ("(cd x && terraform apply)", ["cd x", "terraform apply"]),
])
def test_dividir_comando(comando, segmentos):
    assert dividir_comando(comando) == segmentos


def test_bash_mais_estrita_vence():
    assert decidir_bash("terraform destroy && aws s3 rm s3://b/k", R).decision == DENY
    assert decidir_bash("terraform destroy", R).decision == ASK
    assert decidir_bash("terraform destroy-thing", R).decision == ALLOW
    assert decidir_bash("git status", R).decision == ALLOW


def test_caminho():
    assert casa_caminho("**/*.tf", "main.tf") and casa_caminho("**/*.tf", "infra/x/main.tf")
    assert casa_caminho("rules/catalog/**", "rules/catalog/a/b.yaml")
    assert not casa_caminho("rules/catalog/**", "rules/other.yaml")
    regras = [Regra("rules/catalog/**", DENY, "z")]
    assert decidir_caminho(str(ROOT / "rules/catalog/x.yaml"), regras, ROOT).decision == DENY
    assert decidir_caminho("docs/a.md", regras, ROOT).decision == ALLOW


def test_tool():
    politica = Politica(denied=("sparkforge_scan",), ask_classes=("CLOUD_MUTATION",))
    assert decidir_tool("sparkforge_scan", "LOCAL_MUTATION", politica).decision == DENY
    assert decidir_tool("sparkforge_collect_glue_job", "CLOUD_MUTATION", politica).decision == ASK
    assert decidir_tool("sparkforge_judge", "READ_ONLY", politica).decision == ALLOW


@pytest.mark.parametrize("dados", [
    {"version": 1},
    {"version": 1, "bash": [{"rule": "x *", "decision": "deny"}], "extra_roots": ["dados"]},
    {"version": 1,
     "tools": {"approvals": ["LOCAL_MUTATION"], "ask": {"classes": ["CLOUD_MUTATION"]}}},
    {"version": 2},
    {"version": 1, "bash": [{"rule": "x", "decision": "talvez"}]},
    {"version": 1, "tools": {"approvals": ["ROOT"]}},
    {"version": 1, "outra": 1},
    {"version": 1, "paths": [{"rule": "", "decision": "ask"}]},
    [],
])
def test_validacao_manual_concorda_com_o_json_schema(dados):
    jsonschema = pytest.importorskip("jsonschema")
    valido_formal = jsonschema.Draft202012Validator(SCHEMA).is_valid(dados)
    assert (validar(dados) == []) == valido_formal, validar(dados)


def test_policy_do_repositorio_e_valida_e_pede_ask_nos_destrutivos():
    politica = carregar(ROOT)
    assert politica is not None and not [r for r in politica.bash if r.decision == DENY]
    for cmd in ("terraform destroy", "terraform apply -auto-approve", "aws s3 rm s3://b/k",
                "aws lakeformation revoke-permissions --x y",
                "spark-sql -e 'CALL glue.system.expire_snapshots()'"):
        assert decidir_bash(cmd, politica.bash).decision == ASK, cmd


def test_policy_invalida_levanta(tmp_path):
    (tmp_path / ".sparkforge").mkdir()
    (tmp_path / ".sparkforge" / "policy.yaml").write_text("version: 1\nbash: 3\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="bash"):
        carregar(tmp_path)


def test_sem_arquivo_e_none(tmp_path):
    assert carregar(tmp_path) is None


def test_raiz_que_nao_e_diretorio_e_recusada(tmp_path):
    """A raiz vem de fora do processo (`CLAUDE_PROJECT_DIR`): so vale se existir."""
    with pytest.raises(PolicyError, match="nao e um diretorio"):
        carregar(tmp_path / "nao_existe")
    arquivo = tmp_path / "arquivo.txt"
    arquivo.write_text("x", encoding="utf-8")
    with pytest.raises(PolicyError, match="nao e um diretorio"):
        carregar(arquivo)


def test_regras_ask():
    politica = Politica(
        bash=(Regra("terraform destroy *", ASK), Regra("rm -rf *", DENY)),
        paths=(Regra("**/*.tf", ASK),),
        ask_classes=("CLOUD_MUTATION",), ask_names=("sparkforge_scan",), denied=("sparkforge_x",),
    )
    regras = regras_ask(politica, {"CLOUD_MUTATION": ["sparkforge_x", "sparkforge_collect_a"]})
    assert regras == [
        "Bash(terraform destroy *)", "Edit(**/*.tf)", "Write(**/*.tf)",
        "mcp__sparkforge__sparkforge_collect_a", "mcp__sparkforge__sparkforge_scan",
    ]


def test_settings_do_repositorio_em_dia_com_a_policy():
    from sparkforge.adapters import _core

    assert _core.policy_sync_settings(str(ROOT), check=True)["in_sync"] is True, (
        "rode: sparkforge policy sync-settings"
    )


def test_uma_raiz_decide_como_antes_e_varias_aceitam_a_extra(tmp_path):
    from sparkforge.agents.autonomy import _argumento_fora_da_raiz

    dentro, fora = tmp_path / "repo", tmp_path / "extra"
    dentro.mkdir()
    fora.mkdir()
    args = {"path": str(fora / "x.json")}
    assert _argumento_fora_da_raiz(args, dentro) is not None
    assert _argumento_fora_da_raiz(args, str(dentro)) is not None
    assert _argumento_fora_da_raiz(args, (dentro, fora)) is None
    assert _argumento_fora_da_raiz({"path": str(dentro / "a")}, dentro) is None
