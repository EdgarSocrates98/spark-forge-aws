"""Portas de CLI que faltavam: `analyze workload`, utilizacao no `fuse`, `collect parquet-footer`.

Os tres extratores ja tinham golden; o que se prova aqui e a PORTA publica --
a mesma resposta pelo verbo que o operador roda, sem o teste chamar o extrator.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.collect import parquet_footer as collect_parquet
from sparkforge.collect.base import CollectorUnavailable
from sparkforge.scan.plan import plan

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / "fixtures" / "workload"
WASTE = ROOT / "fixtures" / "waste"
AGORA = "2026-09-14T00:00:00Z"


@pytest.mark.parametrize("caso", ["declared_only", "declared_source_not_observed"])
def test_analyze_workload_devolve_o_golden_do_extrator(caso):
    resultado = _core.analyze_workload(str(WORKLOAD / caso / "input" / "workload.yaml"), limit=None)
    esperado = json.loads((WORKLOAD / caso / "expected" / "facts.json").read_text(encoding="utf-8"))
    assert resultado["items"] == esperado


def test_analyze_workload_sem_arquivo_diz_o_comando(tmp_path):
    with pytest.raises(_core.AdapterError) as exc:
        _core.analyze_workload(str(tmp_path / "workload.yaml"))
    assert "sparkforge analyze workload" in str(exc.value) and exc.value.exit_code == 2


def test_analyze_workload_yaml_malformado_vira_unresolved(tmp_path):
    alvo = tmp_path / "workload.yaml"
    alvo.write_text("jobs: [\n", encoding="utf-8")
    resultado = _core.analyze_workload(str(alvo), limit=None)
    assert [f["attrs"]["reason"] for f in resultado["items"]] == ["read_error"]
    assert resultado["unresolved"] == 1


def _fundir_e_julgar(caso: str) -> list[dict]:
    entrada = json.loads((WASTE / caso / "input" / "facts.json").read_text(encoding="utf-8"))
    fundidos = [f.to_dict() for f in _core.run_fuse(_core._facts_from_dicts(entrada))]
    return list(_core.judge_findings(facts=fundidos, limit=None)["items"])


@pytest.mark.parametrize("caso", sorted(p.name for p in WASTE.iterdir() if p.is_dir()))
def test_fuse_mais_judge_reproduz_os_findings_de_waste(caso):
    esperado = json.loads((WASTE / caso / "expected" / "findings.json").read_text(encoding="utf-8"))
    obtido = _fundir_e_julgar(caso)
    chave = lambda f: (f["rule_id"], json.dumps(f["subject"], sort_keys=True))  # noqa: E731
    assert sorted(map(chave, obtido)) == sorted(map(chave, esperado))


def test_fuse_sem_glue_metric_nao_deriva_utilizacao():
    caminho = WASTE / "sem_cloudwatch" / "input" / "facts.json"
    entrada = json.loads(caminho.read_text(encoding="utf-8"))
    fundidos = _core.run_fuse(_core._facts_from_dicts(entrada))
    assert not [f for f in fundidos if f.kind.startswith("glue.utilization.")]


def _parquet(destino: Path) -> Path:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    destino.mkdir(parents=True)
    tabela = pa.table({"id": [1, 2, 3], "valor": ["a", "b", "c"]})
    pq.write_table(tabela, destino / "part-0.parquet")
    return destino


def test_collect_parquet_footer_registra_e_o_scan_pega(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    dados = _parquet(tmp_path / "dados")
    entrada = _core.collect_parquet_footer(str(repo), prefix=str(dados), now=AGORA)
    manifesto_path = repo / ".sparkforge" / "artifacts" / "manifest.json"
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    (registro,) = [e for e in manifesto if e["kind"] == "parquet_footer"]
    assert registro["path"] == entrada["path"]
    artefato = json.loads((repo / registro["path"]).read_text(encoding="utf-8"))
    assert artefato["status"] == "ok" and artefato["files_read"] == 1
    verificado = _core.collect_verify(str(repo))
    assert verificado["ok_count"] == verificado["total_count"] == 1
    entradas = [e.to_dict() for e in plan(repo).entradas]
    esperada = {"analyze": "parquet-footer", "path": registro["path"], "origin": "manifesto"}
    assert esperada in entradas


def test_collect_parquet_footer_sem_pyarrow_vira_status(tmp_path, monkeypatch):
    def sem_pyarrow():
        raise CollectorUnavailable("pyarrow nao disponivel. Instale com `pip install x`")

    monkeypatch.setattr(collect_parquet, "require_pyarrow", sem_pyarrow)
    repo = tmp_path / "repo"
    repo.mkdir()
    entrada = _core.collect_parquet_footer(str(repo), prefix=str(tmp_path), now=AGORA)
    artefato = json.loads((repo / entrada["path"]).read_text(encoding="utf-8"))
    assert artefato["status"] == collect_parquet.STATUS_PYARROW_INDISPONIVEL


def test_collect_parquet_footer_max_files_fora_da_faixa(tmp_path):
    with pytest.raises(_core.AdapterError) as exc:
        _core.collect_parquet_footer(str(tmp_path), prefix=str(tmp_path), now="x", max_files=0)
    assert "sparkforge collect parquet-footer" in str(exc.value) and exc.value.exit_code == 2


def test_scan_le_workload_yaml_so_na_raiz(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "workload.yaml").write_text("jobs: []\n", encoding="utf-8")
    assert not [e for e in plan(tmp_path).entradas if e.analyze == "workload"]
    (tmp_path / "workload.yaml").write_text("jobs: []\n", encoding="utf-8")
    (entrada,) = [e for e in plan(tmp_path).entradas if e.analyze == "workload"]
    assert (entrada.path, entrada.origem) == ("workload.yaml", "nome")
