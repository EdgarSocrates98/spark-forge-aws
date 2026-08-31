"""Testes do extrator de Amazon EMR on EKS (`emr-containers`)."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.emr_eks import (
    EMITTED_KINDS,
    extract_emr_eks,
    extract_emr_eks_path,
)


def _reasons(facts: list) -> list[str]:
    return sorted(f.attrs["reason"] for f in facts if f.kind == "emrc.unresolved")


def _kinds(facts: list) -> set[str]:
    return {f.kind for f in facts}


def test_payload_que_nao_e_dict_vira_unresolved_e_nao_excecao():
    facts = extract_emr_eks(["nao", "sou", "dict"], "x.json")
    assert _reasons(facts) == ["malformed_json"]
    assert "emrc.analyzed" in _kinds(facts)


def test_payload_sem_job_run_diz_qual_comando_falta():
    facts = extract_emr_eks({"virtualCluster": {"id": "abc"}}, "x.json")
    assert _reasons(facts) == ["missing_job_run"]
    assert "emrc.analyzed" in _kinds(facts)


def test_job_run_sem_id_nao_ancora_nada():
    facts = extract_emr_eks({"jobRun": {"name": "etl"}}, "x.json")
    assert _reasons(facts) == ["missing_job_run_id"]


def test_a_sentinela_sai_sempre_inclusive_quando_nada_pode_ser_lido():
    facts = extract_emr_eks({}, "x.json")
    sentinelas = [f for f in facts if f.kind == "emrc.analyzed"]
    assert len(sentinelas) == 1
    assert sentinelas[0].measures["unresolved_count"] == 1


def test_nenhum_kind_escapa_do_namespace_declarado():
    facts = extract_emr_eks({}, "x.json")
    assert {f.kind for f in facts} <= EMITTED_KINDS


def test_arquivo_ilegivel_vira_read_error(tmp_path: Path):
    alvo = tmp_path / "ausente.json"
    assert _reasons(extract_emr_eks_path(alvo, repo_root=tmp_path)) == ["read_error"]


def test_json_invalido_vira_malformed_json(tmp_path: Path):
    alvo = tmp_path / "quebrado.json"
    alvo.write_text("{isto nao e json", encoding="utf-8")
    assert _reasons(extract_emr_eks_path(alvo, repo_root=tmp_path)) == ["malformed_json"]
