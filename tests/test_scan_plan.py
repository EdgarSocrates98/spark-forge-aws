"""Plano do `sparkforge scan`: manifesto, extensao, recusas nomeadas."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from sparkforge.scan import KIND_PARA_ANALYZE, RECUSAS, ScanError, plan

ROOT = Path(__file__).resolve().parents[1]
ART = ".sparkforge/artifacts"


def _grava(raiz: Path, relativo: str, texto: str) -> Path:
    caminho = raiz / relativo
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return caminho


def _manifesto(raiz: Path, entradas: list[dict]) -> None:
    for e in entradas:
        if "sha256" not in e and (raiz / e["path"]).is_file():
            e["sha256"] = hashlib.sha256((raiz / e["path"]).read_bytes()).hexdigest()
    _grava(raiz, f"{ART}/manifest.json", json.dumps(entradas))


def _por_razao(plano) -> dict[str, list[str]]:
    saida: dict[str, list[str]] = {}
    for r in plano.recusas:
        saida.setdefault(r.reason, []).append(r.path)
    return saida


def test_codigo_por_extensao(tmp_path):
    _grava(tmp_path, "a.py", "x = 1\n")
    _grava(tmp_path, "b.sql", "SELECT 1\n")
    _grava(tmp_path, "c.tf", "\n")
    _grava(tmp_path, "d.jsonl", "{}\n")
    _grava(tmp_path, "notas.md", "nada\n")
    pares = {(e.analyze, e.path) for e in plan(tmp_path).entradas}
    assert pares == {
        ("pyspark", "a.py"), ("sql", "a.py"), ("sql", "b.sql"),
        ("terraform", "c.tf"), ("event-log", "d.jsonl"),
    }


def test_json_solto_e_recusado_sem_farejar(tmp_path):
    _grava(tmp_path, "dump.json", '{"Table": {}}')
    plano = plan(tmp_path)
    assert not plano.entradas
    assert _por_razao(plano) == {"sem_manifesto": ["dump.json"]}


def test_artefato_pelo_kind_do_manifesto(tmp_path):
    _grava(tmp_path, f"{ART}/iceberg/t.json", "{}")
    _manifesto(tmp_path, [{"kind": "iceberg_metadata", "path": f"{ART}/iceberg/t.json"}])
    [entrada] = plan(tmp_path).entradas
    assert (entrada.analyze, entrada.origem) == ("iceberg", "manifesto")


def test_sha256_divergente_e_ausente(tmp_path):
    _grava(tmp_path, f"{ART}/iceberg/t.json", "{}")
    _manifesto(tmp_path, [
        {"kind": "iceberg_metadata", "path": f"{ART}/iceberg/t.json", "sha256": "0" * 64},
        {"kind": "iceberg_metadata", "path": f"{ART}/iceberg/sumiu.json", "sha256": "0" * 64},
    ])
    plano = plan(tmp_path)
    assert not plano.entradas
    assert sorted(_por_razao(plano)["sha256_divergente"]) == [
        f"{ART}/iceberg/sumiu.json", f"{ART}/iceberg/t.json",
    ]


def test_kind_sem_analyze(tmp_path):
    _grava(tmp_path, f"{ART}/glue_job/j.json", "{}")
    _grava(tmp_path, f"{ART}/x/y.json", "{}")
    _manifesto(tmp_path, [
        {"kind": "terraform", "path": f"{ART}/glue_job/j.json"},
        {"kind": "inventado", "path": f"{ART}/x/y.json"},
    ])
    assert len(_por_razao(plan(tmp_path))["kind_sem_analyze"]) == 2


def test_glue_job_run_tira_o_job_do_source_e_agrupa_por_pasta(tmp_path):
    for run in ("jr_1", "jr_2"):
        _grava(tmp_path, f"{ART}/glue_job_run/job_x_{run}.json", "{}")
    _manifesto(tmp_path, [
        {"kind": "glue_job_run", "path": f"{ART}/glue_job_run/job_x_{r}.json",
         "source": f"glue:get_job_runs:job_x/{r}"} for r in ("jr_1", "jr_2")
    ])
    [entrada] = plan(tmp_path).entradas
    assert (entrada.analyze, entrada.path, entrada.job_name) == (
        "glue-job-runs", f"{ART}/glue_job_run", "job_x",
    )


def test_source_fora_da_forma_exige_job_name(tmp_path):
    _grava(tmp_path, f"{ART}/glue_job_run/r.json", "{}")
    _manifesto(tmp_path, [{"kind": "glue_job_run", "path": f"{ART}/glue_job_run/r.json",
                           "source": "glue:get_job:job_x"}])
    assert _por_razao(plan(tmp_path)) == {"exige_job_name": [f"{ART}/glue_job_run/r.json"]}


def test_caminho_fora_da_raiz_nunca_e_lido(tmp_path):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    _grava(tmp_path, "fora.json", "{}")
    _manifesto(raiz, [{"kind": "iceberg_metadata", "path": "../fora.json", "sha256": "0" * 64}])
    assert _por_razao(plan(raiz)) == {"fora_da_raiz": ["../fora.json"]}


def test_manifesto_ilegivel_e_erro(tmp_path):
    _grava(tmp_path, f"{ART}/manifest.json", "{nao e json")
    with pytest.raises(ScanError, match="manifesto ilegivel"):
        plan(tmp_path)


def test_varredura_pula_sparkforge_e_relata(tmp_path):
    _grava(tmp_path, f"{ART}/eventlog/x.jsonl", "{}\n")
    plano = plan(tmp_path)
    assert not plano.entradas
    assert {"path": ".sparkforge", "reason": "DIRECTORY_IGNORED"} in plano.pulos


def test_todo_kind_emitido_pelos_coletores_esta_no_mapa():
    """Coletor novo sem entrada no mapa faria o scan recusar tudo que ele grava."""
    emitidos = set()
    for fonte in sorted((ROOT / "sparkforge" / "collect").glob("*.py")):
        emitidos |= set(re.findall(r'kind="([a-z_]+)"', fonte.read_text(encoding="utf-8")))
    assert emitidos, "nenhum kind= encontrado nos coletores"
    assert emitidos <= set(KIND_PARA_ANALYZE), emitidos - set(KIND_PARA_ANALYZE)


def test_recusas_declaradas_na_tool_sao_as_do_modulo():
    from sparkforge.adapters.tools import TOOLS

    esquema = TOOLS["sparkforge_scan"]["outputSchema"]
    texto = json.dumps(esquema)
    assert all(r in texto for r in RECUSAS)
