"""Gate do campo `action`.

Duas direcoes, e as duas importam: toda regra executavel declara `action`, e
todo `kind` do vocabulario tem ao menos uma regra que o usa. Sem a segunda, o
vocabulario incha com entrada morta e ninguem percebe.

`PENDENTES` encolhe a cada lote da Fase 2 e chega a conjunto vazio na Tarefa 10.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sparkforge.findings.models import Finding
from sparkforge.rules.loader import CatalogError, _validate_action, catalog_dir, load_catalog

# Arquivos ainda sem `action`. Encolhe a cada lote; vazio ao fim da Fase 2.
PENDENTES = {
    "controlm.yaml",
    "athena.yaml",
    "env.yaml",
    "funcval.yaml",
    "iceberg.yaml",
    "parquet.yaml",
    "data-quality.yaml",
    "glue-migration.yaml",
    "spark4.yaml",
    "glue-kms.yaml",
    "lakeformation.yaml",
    "glue-cross-account.yaml",
    "glue-network.yaml",
}


def _vocabulary() -> dict:
    path = catalog_dir() / "action_kinds.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _rule_files() -> dict[str, str]:
    """rule_id -> nome do arquivo que o declara."""
    origem: dict[str, str] = {}
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        if path.name in {"routing.yaml", "action_kinds.yaml"}:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in data.get("rules") or []:
            origem[rule["id"]] = path.name
    return origem


class TestActionField:
    def test_toda_executavel_declara_action(self):
        origem = _rule_files()
        faltando = [
            r["id"]
            for r in load_catalog()
            if r.get("executable", True)
            and origem.get(r["id"]) not in PENDENTES
            and "action" not in r
        ]
        assert faltando == [], f"regras executaveis sem `action`: {faltando}"

    def test_kind_esta_no_vocabulario(self):
        vocab = set(_vocabulary()["kinds"])
        fora = [
            (r["id"], r["action"]["kind"])
            for r in load_catalog()
            if "action" in r and r["action"]["kind"] not in vocab
        ]
        assert fora == [], f"kind fora do vocabulario: {fora}"

    def test_todo_kind_do_vocabulario_tem_regra(self):
        if PENDENTES:
            return  # so vale com o catalogo inteiro preenchido
        vocab = set(_vocabulary()["kinds"])
        usados = {r["action"]["kind"] for r in load_catalog() if "action" in r}
        mortos = sorted(vocab - usados)
        assert mortos == [], f"kind no vocabulario sem regra que o use: {mortos}"

    def test_eixo_esta_no_vocabulario(self):
        """Sem vocabulario fechado de eixo, um lote escreve `runtime.wall_clock` e
        outro escreve `wall_clock`, e a restricao do executor -- duas acoes que
        compartilham eixo nao entram no mesmo run -- nunca dispara."""
        vocab = set(_vocabulary()["axes"])
        fora = [
            (r["id"], eixo)
            for r in load_catalog()
            if "action" in r
            for eixo in r["action"].get("moves") or []
            if eixo not in vocab
        ]
        assert fora == [], f"eixo fora do vocabulario: {fora}"

    def test_todo_eixo_do_vocabulario_tem_regra(self):
        if PENDENTES:
            return  # so vale com o catalogo inteiro preenchido
        vocab = set(_vocabulary()["axes"])
        usados = {
            eixo
            for r in load_catalog()
            if "action" in r
            for eixo in r["action"].get("moves") or []
        }
        mortos = sorted(vocab - usados)
        assert mortos == [], f"eixo no vocabulario sem regra que o mova: {mortos}"


class TestActionShape:
    def test_direction_invalida_recusa(self):
        with pytest.raises(CatalogError, match="direction"):
            _validate_action(
                "SF-X-001",
                {"action": {"kind": "k", "target": "t", "direction": "aumentar"}},
            )

    def test_chave_desconhecida_recusa(self):
        with pytest.raises(CatalogError, match="desconhecidas"):
            _validate_action(
                "SF-X-001",
                {
                    "action": {
                        "kind": "k",
                        "target": "t",
                        "direction": "increase",
                        "expected_gain": "-31%",
                    }
                },
            )

    def test_nao_executavel_com_action_recusa(self):
        with pytest.raises(CatalogError, match="nao executavel"):
            _validate_action(
                "SF-ARCH-001",
                {
                    "executable": False,
                    "action": {"kind": "k", "target": "t", "direction": "increase"},
                },
            )

    def test_ausencia_de_action_passa(self):
        _validate_action("SF-X-001", {})


class TestFindingCarregaAction:
    def test_finding_tem_campo_action(self):
        f = Finding(
            rule_id="SF-WASTE-001",
            title="t",
            severity="P2",
            confidence="medium",
            status="confirmed",
            subject={"job": "x"},
            evidence=["f_abc123"],
            action={
                "kind": "capacity.investigate_sizing",
                "target": "glue.number_of_workers",
                "direction": "investigate",
            },
        )
        assert f.to_dict()["action"]["direction"] == "investigate"

    def test_action_ausente_e_dict_vazio(self):
        f = Finding(
            rule_id="SF-X-001",
            title="t",
            severity="P2",
            confidence="medium",
            status="confirmed",
            subject={},
            evidence=["f_abc123"],
        )
        assert f.to_dict()["action"] == {}
