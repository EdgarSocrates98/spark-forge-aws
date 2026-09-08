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

from sparkforge.rules.loader import CatalogError, _validate_action, catalog_dir, load_catalog

# Arquivos ainda sem `action`. Encolhe a cada lote; vazio ao fim da Fase 2.
PENDENTES = {
    "pyspark.yaml",
    "emr-infra.yaml",
    "controlm.yaml",
    "emr-serverless.yaml",
    "glue-infra.yaml",
    "graph.yaml",
    "spark-ui.yaml",
    "athena.yaml",
    "env.yaml",
    "funcval.yaml",
    "iceberg.yaml",
    "parquet.yaml",
    "benchmark.yaml",
    "data-quality.yaml",
    "emr-eks.yaml",
    "glue-migration.yaml",
    "spark-plan.yaml",
    "spark4.yaml",
    "glue-kms.yaml",
    "lakeformation.yaml",
    "timeout.yaml",
    "waste.yaml",
    "bridge.yaml",
    "callgraph.yaml",
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
