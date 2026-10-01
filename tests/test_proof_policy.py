"""A politica do Change Proof contra o catalogo real.

Tres travas, e todas sao lista derivada, nunca escrita a mao:
- todo eixo que alguma regra usa em `action.moves` tem entrada na politica, e
  nenhuma entrada sobra;
- toda fonte aponta para kind que algum extrator emite (`EMITTED_KINDS`), e toda
  medida de bench existe em `_RUN_MEASURES`;
- toda regra citada em `refuted_by`/`confounded_by` existe no catalogo.

Sem elas, eixo novo em `moves` sairia `unproven` com `eixo_sem_politica` em
producao, e a politica envelheceria calada.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from sparkforge.diagnosis.root_cause import _modulo_por_kind
from sparkforge.facts.benchmark import _RUN_MEASURES
from sparkforge.proof import PolicyError, load_policy, stable_key, validate_policy
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
KIND_POR_FONTE = {
    "funcval": ("funcval.analyzed", "funcval.check_delta"),
    "bench": ("bench.run_delta",),
}


@pytest.fixture(scope="module")
def politica():
    return load_policy()


@pytest.fixture(scope="module")
def regras():
    return load_catalog()


def eixos_usados(regras) -> set[str]:
    return {eixo for r in regras for eixo in ((r.get("action") or {}).get("moves") or [])}


def test_a_politica_real_carrega(politica):
    assert politica["policy_version"] == 1


def test_todo_eixo_de_moves_tem_entrada_e_nenhuma_sobra(politica, regras):
    usados = eixos_usados(regras)
    assert usados == set(politica["axes"])
    assert len(usados) == 23


def test_toda_fonte_aponta_para_kind_emitido(politica):
    emitidos = _modulo_por_kind()
    for nome, eixo in politica["axes"].items():
        for kind in KIND_POR_FONTE.get(eixo["source"], ()):
            assert kind in emitidos, f"{nome}: {kind} nao e emitido por nenhum extrator"


def test_toda_medida_de_bench_existe(politica):
    medidas = {nome for nome, *_ in _RUN_MEASURES}
    for nome, eixo in politica["axes"].items():
        if eixo["source"] == "bench":
            assert eixo["measure"] in medidas, nome


def test_toda_regra_citada_existe(politica, regras):
    ids = {r["id"] for r in regras}
    for nome, eixo in politica["axes"].items():
        for campo in ("refuted_by", "confounded_by"):
            for rule_id in eixo.get(campo, []):
                assert rule_id in ids, f"{nome}.{campo}: {rule_id}"


def test_todo_eixo_sem_comparador_diz_o_que_o_destravaria(politica):
    sem_fonte = [n for n, e in politica["axes"].items() if e["source"] == "none"]
    assert sem_fonte
    assert all(politica["axes"][n]["unlock"].strip() for n in sem_fonte)


def test_a_chave_estavel_cobre_todo_tipo_de_subject_dos_goldens(politica):
    padrao = str(ROOT / "fixtures" / "**" / "expected" / "findings.json")
    tipos = {
        finding["subject"].get("type")
        for caminho in glob.glob(padrao, recursive=True)
        for finding in json.loads(Path(caminho).read_text(encoding="utf-8"))
    }
    assert tipos <= set(politica["stable_keys"])


def test_a_chave_ignora_o_que_muda_sem_resolver(politica):
    chaves = politica["stable_keys"]
    antes = {"type": "source_location", "file": "job.py", "symbol": "principal", "line": 9,
             "col": 13, "end_line": 9, "snippet": "linhas = ativos.collect()"}
    depois = {**antes, "line": 42, "col": 4, "end_line": 42, "snippet": "outra coisa"}
    assert stable_key(antes, chaves) == stable_key(depois, chaves)
    assert stable_key({"type": "stage", "symbol": "s", "stage_id": 1}, chaves) == stable_key(
        {"type": "stage", "symbol": "s", "stage_id": 7}, chaves
    )


def test_job_run_sem_job_name_nao_tem_chave(politica):
    assert stable_key({"type": "job_run", "symbol": "jr_0001"}, politica["stable_keys"]) is None


def test_tipo_desconhecido_nao_tem_chave(politica):
    assert stable_key({"type": "outro", "symbol": "x"}, politica["stable_keys"]) is None


@pytest.mark.parametrize(
    "estrago, campo",
    [
        (lambda d: d["axes"]["scan.bytes_read"].update(source="benchmark"), "source"),
        (lambda d: d["axes"]["scan.bytes_read"].pop("measure"), "measure"),
        (lambda d: d["axes"]["cost.dpu_seconds"].update(unlock=" "), "unlock"),
        (lambda d: d.pop("policy_version"), "policy_version"),
        (lambda d: d["delta_sign_convention"].pop("reason"), "delta_sign_convention"),
    ],
)
def test_politica_malformada_e_recusada_com_o_campo(politica, estrago, campo):
    doc = json.loads(json.dumps(politica))
    estrago(doc)
    with pytest.raises(PolicyError, match=campo):
        validate_policy(doc)
