"""SC6: cada caso de `evals/agentic/debate/` e decidivel SO com o fact que o lado coleta.

A suite tem tres variantes do UNICO par de contradicao direta do catalogo
(`SF-GRAPH-005` x `SF-LF-001`, na uniao da regra 29). As tres partem da MESMA
uniao e do mesmo `case.yaml`; o que muda entre elas e um artefato so,
`artifacts/lakeformation/curated_arestas.json` -- o dump de `collect
lakeformation` da tabela. O fact que decide e `lakeformation.grant`, e ele NAO
esta na uniao: o lado precisa pedir ao executor que o reextraia pelo extrator
`lakeformation-grants`, que esta na allowlist de `debate_evidence`.

Por que `lakeformation.grant` e nao `lakeformation.access_model`: o
`access_model` sai de uma DERIVACAO (`sparkforge/facts/lakeformation.py`), e a
reextracao so roda extrator `extract*_path` sobre arquivo. O grant sai de um
extrator de arquivo, e o atributo que separa as duas acoes e
`is_iam_allowed_principals`:

  * `lf_vence` -- o grant e do runtime role, nao de IAM_ALLOWED_PRINCIPALS: o
    Lake Formation governa a tabela, o FGAC carrega peso, e fica o FGAC;
  * `graph_vence` -- o unico grant e IAM_ALLOWED_PRINCIPALS: quem decide o acesso
    e o IAM, derrubar o FGAC nao afrouxa nada, e fica o JAR;
  * `sem_fato` -- o dump e `sem_permissao`: o extrator emite
    `lakeformation.grants.unresolved` e nenhum grant. Nada medido separa as
    acoes, e o gabarito e `unresolved`.

## O que a prova prova, e o que ela nao prova

As submissoes sao GRAVADAS e deterministicas, e cada vez de lado e uma lista de
candidatas em ordem de preferencia -- o que o driver faz quando o executor
recusa: tenta a proxima. A candidata que cita o grant vem primeiro; a de
reserva e a jogada honesta de quem NAO tem o fact (nao replica). Rodando o
MESMO roteiro com e sem o artefato no case:

  * com o artefato, o grant e reextraido, a replica que o cita e aceita, toda
    objecao tem replica, e o `referee` aceita o vencedor do gabarito;
  * sem o artefato, a reextracao e recusada (`artifact_not_found`), a replica
    que cita o grant e recusada (`dangling_evidence_ref`), a objecao fica viva,
    e o `referee` troca o vencedor por `unresolved` -- MESMO com o outro lado
    concedendo, porque o roteiro concede nos dois casos.

A maquina NAO julga se a replica e boa: uma replica que citasse qualquer fact
citavel responderia a objecao igual. Isso nao e lacuna desta prova, e o que o
placar mede: `test_replica_desonesta_vira_false_resolution` roda exatamente
esse caso sobre `sem_fato` e mostra o grader chamando-o de `false_resolution`.
O que a maquina garante, e esta prova amarra, e que o fact decisivo nao pode
ser citado sem o artefato, e que objecao sem replica impede vencedor.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import run_debate
from sparkforge.adapters import _core
from sparkforge.agentic.executor.debate_evidence import EVIDENCE_EXTRACTORS, extract_evidence
from sparkforge.evals.debate_grade import (
    DEBATE_FACTS_FILE,
    RESULT_FILE,
    grade_case,
    load_expected,
    suite_cases,
)

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "agentic" / "debate"
CASOS = ("graph_vence", "lf_vence", "sem_fato")
ARTEFATO = "artifacts/lakeformation/curated_arestas.json"
PONTEIRO = {"extractor": "lakeformation-grants", "path": ARTEFATO}

# Ids da uniao: `graph.import`, `tf.resource` do job de grafo, os dois
# `tf.attribute` de FGAC e de `--extra-jars`, e o `lakeformation.unresolved` que
# nomeia os grants como nao coletados.
IMPORT, RECURSO, FGAC, JARS, LF_LACUNA = (
    "f_32bc0d",
    "f_d9303b",
    "f_55f5ac",
    "f_6ab9b2",
    "f_4d32fe",
)


def _claim(texto: str, refs: list[str], confianca: str = "high") -> dict[str, Any]:
    return {
        "claim_type": "inference",
        "statement": texto,
        "evidence_refs": refs,
        "confidence": confianca,
    }


# Lado A defende SF-GRAPH-005; lado B, SF-LF-001. `$grant` e o id do
# `lakeformation.grant` que o extrator produz sobre o artefato do caso;
# `@<seq>.<secao>.<i>`, o id que a submissao aceita `seq` produziu.
CLAIM_A = _claim("o job importa GraphFrames e o IaC nao entrega o JAR", [IMPORT, RECURSO])
CLAIM_B = _claim("o job declara FGAC e JAR adicional no mesmo aws_glue_job", [FGAC, JARS], "medium")

ROTEIRO_LF_VENCE: list[list[dict[str, Any]]] = [
    [{"claims": [CLAIM_A]}],
    [
        {
            "claims": [CLAIM_B],
            "objections": [
                {
                    "target_claim": "@1.claims.0",
                    "statement": "sob FGAC a AWS bloqueia JAR adicional",
                    "evidence_refs": [FGAC],
                }
            ],
            "evidence_artifacts": [PONTEIRO],
        },
        {
            "claims": [CLAIM_B],
            "objections": [
                {
                    "target_claim": "@1.claims.0",
                    "statement": "sob FGAC a AWS bloqueia JAR adicional",
                    "evidence_refs": [FGAC],
                }
            ],
        },
    ],
    [
        {
            "rebuttals": [
                {
                    "target_objection": "@2.objections.0",
                    "statement": "o bloqueio some se o FGAC sair; nada medido diz que ele "
                    "carrega peso",
                    "evidence_refs": [LF_LACUNA],
                }
            ],
            "objections": [
                {
                    "target_claim": "@2.claims.0",
                    "statement": "tirar o JAR quebra o import; FGAC so se justifica se o Lake "
                    "Formation governa a tabela",
                    "evidence_refs": [IMPORT, LF_LACUNA],
                }
            ],
        }
    ],
    [
        {
            "rebuttals": [
                {
                    "target_objection": "@3.objections.0",
                    "statement": "o grant e do runtime role e nao de IAM_ALLOWED_PRINCIPALS: o "
                    "Lake Formation governa a tabela e o FGAC carrega peso",
                    "evidence_refs": ["$grant"],
                }
            ],
            "claims": [
                _claim(
                    "o Lake Formation concede a tabela ao runtime role: derrubar o FGAC "
                    "afrouxa acesso medido",
                    ["$grant"],
                )
            ],
        },
        {},
    ],
    [{"concede": True}],
    [{}],
]

ROTEIRO_GRAPH_VENCE: list[list[dict[str, Any]]] = [
    [{"claims": [CLAIM_A], "evidence_artifacts": [PONTEIRO]}, {"claims": [CLAIM_A]}],
    [
        {
            "claims": [CLAIM_B],
            "objections": [
                {
                    "target_claim": "@1.claims.0",
                    "statement": "sob FGAC a AWS bloqueia JAR; manter o JAR exige derrubar o "
                    "FGAC e afrouxa o acesso",
                    "evidence_refs": [FGAC],
                }
            ],
        }
    ],
    [
        {
            "rebuttals": [
                {
                    "target_objection": "@2.objections.0",
                    "statement": "o unico grant e IAM_ALLOWED_PRINCIPALS: o acesso ja e do IAM, "
                    "e derrubar o FGAC nao afrouxa permissao do Lake Formation",
                    "evidence_refs": ["$grant"],
                }
            ],
            "claims": [
                _claim(
                    "a tabela nao e governada pelo Lake Formation: sai o FGAC, fica o JAR",
                    ["$grant"],
                )
            ],
        },
        {},
    ],
    [{"concede": True}],
]

ROTEIROS = {
    "lf_vence": ROTEIRO_LF_VENCE,
    "graph_vence": ROTEIRO_GRAPH_VENCE,
    # O mesmo roteiro de `lf_vence`: o lado B pede a reextracao e tenta citar o
    # grant. Aqui o extrator nao produz grant nenhum, e a candidata que o cita
    # nao tem o que citar.
    "sem_fato": ROTEIRO_LF_VENCE,
}


def _grant_id(ws: Path) -> str | None:
    """O id do `lakeformation.grant` que o extrator produz no case, ou `None`."""
    registros = extract_evidence(ws, [PONTEIRO]) if (ws / ARTEFATO).is_file() else []
    ids = [r["fact"]["id"] for r in registros if r["fact"]["kind"] == "lakeformation.grant"]
    return ids[0] if ids else None


def _resolve(valor: Any, aceitas: dict[int, dict[str, list[str]]], grant: str | None) -> Any:
    if isinstance(valor, str) and valor == "$grant":
        if grant is None:
            raise _SemFato
        return grant
    if isinstance(valor, str) and valor.startswith("@"):
        seq, secao, indice = valor[1:].split(".")
        return aceitas[int(seq)][secao][int(indice)]
    if isinstance(valor, list):
        return [_resolve(v, aceitas, grant) for v in valor]
    if isinstance(valor, dict):
        return {k: _resolve(v, aceitas, grant) for k, v in valor.items()}
    return valor


class _SemFato(Exception):
    """A candidata cita um fact que o case nao produz: o lado honesto a pula."""


def debater(
    ws: Path, roteiro: list[list[dict[str, Any]]], grant: str | None
) -> dict[str, Any]:
    """Roda o roteiro no workspace, como o driver: arbitrate, start, e as vezes.

    `grant` e o id que a candidata `$grant` cita. Sem o artefato no case ele
    continua sendo o id que o fact TERIA -- a replica o cita, e o executor a
    recusa por referencia pendurada, que e exatamente o que se quer medir.
    """
    preparo = run_debate.preparar(ws)
    assert preparo["arbitrate"]["debate_plans"] == 1
    inicio = preparo["start"]
    assert inicio["status"] == "started", inicio
    debate_id = inicio["debate_id"]

    aceitas: dict[int, dict[str, list[str]]] = {}
    tentativas: list[dict[str, Any]] = []
    for candidatas in roteiro:
        passo = _core.debate_next(str(ws), debate_id)
        if passo["status"] == "done":
            break
        lado, rodada = passo["brief"]["side"], passo["brief"]["round"]
        for candidata in candidatas:
            try:
                corpo = _resolve(candidata, aceitas, grant)
            except _SemFato:
                continue
            resposta = _core.debate_submit(
                str(ws), debate_id, payload={"side": lado, "round": rodada, **corpo}
            )
            tentativas.append(
                {"side": lado, "round": rodada, "status": resposta["status"],
                 "reason": resposta.get("reason")}
            )
            if resposta["status"] == "accepted":
                aceitas[resposta["seq"]] = resposta["entities"]
                break
        else:
            pytest.fail(f"nenhuma candidata aceita para o lado {lado} na rodada {rodada}")
    done = _core.debate_next(str(ws), debate_id)
    assert done["status"] == "done", done
    return {"done": done, "attempts": tentativas, "debate_id": debate_id}


def _workspace(tmp_path: Path, caso: str, com_artefato: bool = True) -> Path:
    ws = run_debate.montar_caso(SUITE / caso, tmp_path / "caso")
    if not com_artefato:
        (ws / ARTEFATO).unlink()
    return ws


def _esperado(caso: str) -> dict[str, Any]:
    return load_expected(SUITE / caso)


def _vencedor(done: dict[str, Any]) -> str | None:
    return done["winner_rule"] if done["outcome"] == "winner" else None


# --------------------------------------------------------------------------
# A forma da suite
# --------------------------------------------------------------------------


def test_a_suite_tem_exatamente_os_tres_casos():
    assert tuple(suite_cases(SUITE)) == CASOS
    assert set(run_debate.CASOS) == set(CASOS)


@pytest.mark.parametrize("caso", CASOS)
def test_o_caso_so_carrega_o_que_o_driver_copia_mais_o_gabarito(caso):
    """O que nao esta na allowlist do driver nunca chega ao lado -- e o que
    nao chega ao lado nao pode ser insumo do caso."""
    nomes = {p.name for p in (SUITE / caso).iterdir()}
    assert nomes == {*run_debate.ARQUIVOS_DO_CASO, *run_debate.DIRETORIOS_DO_CASO, "expected.yaml"}


def test_os_casos_so_diferem_no_artefato():
    """Mesmo `case.yaml`, mesmo nome de artefato: nada no workspace diz qual
    caso e -- o nome da pasta do gabarito fica fora (o driver usa `caso-<k>`)."""
    textos = {(SUITE / c / "case.yaml").read_text(encoding="utf-8") for c in CASOS}
    assert len(textos) == 1
    for caso in CASOS:
        arquivos = sorted(
            p.relative_to(SUITE / caso).as_posix()
            for p in (SUITE / caso / "artifacts").rglob("*")
            if p.is_file()
        )
        assert arquivos == [ARTEFATO]
    conteudos = {(SUITE / c / ARTEFATO).read_bytes() for c in CASOS}
    assert len(conteudos) == len(CASOS)


@pytest.mark.parametrize("caso", CASOS)
def test_o_case_declara_budget_com_max_rounds(caso):
    case = yaml.safe_load((SUITE / caso / "case.yaml").read_text(encoding="utf-8"))
    assert isinstance(case["budget"]["max_rounds"], int)
    assert 1 <= case["budget"]["max_rounds"] <= 10


@pytest.mark.parametrize("caso", CASOS)
def test_o_fact_decisivo_nao_esta_na_uniao_e_sai_de_extrator_da_allowlist(caso):
    esperado = _esperado(caso)
    decisivo = esperado["decided_by"]
    uniao = json.loads((SUITE / "uniao" / "facts.json").read_text(encoding="utf-8"))
    assert decisivo["kind"] not in {f["kind"] for f in uniao}
    assert decisivo["extractor"] in EVIDENCE_EXTRACTORS
    assert decisivo["artifact"] == ARTEFATO
    assert esperado["rules"] == list(run_debate.REGRAS)


@pytest.mark.parametrize("caso", CASOS)
def test_o_extrator_sobre_o_artefato_produz_o_que_o_gabarito_declara(caso, tmp_path):
    esperado = _esperado(caso)
    decisivo = esperado["decided_by"]
    ws = _workspace(tmp_path, caso)
    grants = [
        r["fact"]
        for r in extract_evidence(ws, [PONTEIRO])
        if r["fact"]["kind"] == decisivo["kind"]
    ]
    if decisivo.get("produced") is False:
        assert grants == []
    else:
        assert grants, caso
        assert {g["attrs"][decisivo["attr"]] for g in grants} == {decisivo["value"]}


# --------------------------------------------------------------------------
# Decidibilidade (SC6)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("caso", CASOS)
def test_com_o_fact_o_debate_chega_ao_gabarito(caso, tmp_path):
    esperado = _esperado(caso)
    ws = _workspace(tmp_path, caso)
    resultado = debater(ws, ROTEIROS[caso], _grant_id(ws))
    assert _vencedor(resultado["done"]) == esperado["winner"]
    if esperado["winner"] is not None:
        assert resultado["done"]["referee"]["upheld"] is True


@pytest.mark.parametrize("caso", CASOS)
def test_sem_o_fact_o_referee_devolve_unresolved(caso, tmp_path):
    grant = _grant_id(_workspace(tmp_path / "com", caso))
    ws = _workspace(tmp_path / "sem", caso, com_artefato=False)
    resultado = debater(ws, ROTEIROS[caso], grant)
    done = resultado["done"]
    assert done["outcome"] == "unresolved"
    motivos = [t["reason"] for t in resultado["attempts"] if t["status"] == "refused"]
    if grant is not None:
        # A recusa e a do fact, e so dela: a reextracao sem artefato e a
        # replica que cita o que nao foi reextraido.
        assert "artifact_not_found" in motivos
        assert "dangling_evidence_ref" in motivos
        assert set(motivos) <= {"artifact_not_found", "dangling_evidence_ref"}
        # O roteiro concede nos dois casos: o candidato teve vencedor, e foi o
        # referee que o recusou pela objecao sem replica.
        assert done["candidate"]["outcome"] == "winner"
        assert done["referee"]["upheld"] is False
        assert {v["kind"] for v in done["referee"]["violations"]} == {
            "consenso_sobre_objecao_viva"
        }


def test_trocar_so_o_artefato_torna_sem_fato_decidivel(tmp_path):
    """O fact e o que decide: com o dump de `lf_vence` no lugar do de
    `sem_fato`, o mesmo roteiro fecha com o vencedor de `lf_vence`."""
    ws = _workspace(tmp_path, "sem_fato")
    shutil.copyfile(SUITE / "lf_vence" / ARTEFATO, ws / ARTEFATO)
    resultado = debater(ws, ROTEIROS["sem_fato"], _grant_id(ws))
    assert _vencedor(resultado["done"]) == _esperado("lf_vence")["winner"]


# --------------------------------------------------------------------------
# O placar sobre os debates da suite
# --------------------------------------------------------------------------


def _grava_execucao(destino: Path, ws: Path, resultado: dict[str, Any]) -> Path:
    destino.mkdir(parents=True)
    (destino / RESULT_FILE).write_text(
        json.dumps({"status": "done", **resultado}), encoding="utf-8"
    )
    estado = ws / ".sparkforge" / "debate" / resultado["debate_id"] / "facts.jsonl"
    if estado.is_file():
        shutil.copyfile(estado, destino / DEBATE_FACTS_FILE)
    return destino


@pytest.mark.parametrize(
    ("caso", "desfecho"),
    [
        ("lf_vence", "correct_winner"),
        ("graph_vence", "correct_winner"),
        ("sem_fato", "correct_unresolved"),
    ],
)
def test_o_placar_do_roteiro_honesto(caso, desfecho, tmp_path):
    ws = _workspace(tmp_path, caso)
    resultado = debater(ws, ROTEIROS[caso], _grant_id(ws))
    execucao = _grava_execucao(tmp_path / "run" / caso, ws, resultado)
    linha = grade_case(caso, _esperado(caso), execucao)
    assert linha["status"] == "graded"
    assert linha["outcome"] == desfecho
    vence = desfecho == "correct_winner"
    assert linha["decisive_fact"] == {
        "kind": "lakeformation.grant",
        "extracted": vence,
        "cited_by_decision": vence,
    }


def test_sem_o_fact_o_placar_e_missed_resolution(tmp_path):
    grant = _grant_id(_workspace(tmp_path / "com", "lf_vence"))
    ws = _workspace(tmp_path / "sem", "lf_vence", com_artefato=False)
    resultado = debater(ws, ROTEIROS["lf_vence"], grant)
    linha = grade_case(
        "lf_vence", _esperado("lf_vence"), _grava_execucao(tmp_path / "run", ws, resultado)
    )
    assert linha["outcome"] == "missed_resolution"
    assert linha["refused_submissions"] == 2  # a reextracao e a replica que cita o grant
    assert linha["decisive_fact"]["extracted"] is False


def test_replica_desonesta_vira_false_resolution(tmp_path):
    """A maquina nao julga o merito da replica: citando o
    `lakeformation.grants.unresolved` reextraido -- a medida de que o grant NAO
    foi lido --, a replica e aceita e o debate elege vencedor. E o placar que
    chama isso de `false_resolution`."""
    ws = _workspace(tmp_path, "sem_fato")
    lacuna = next(
        r["fact"]["id"]
        for r in extract_evidence(ws, [PONTEIRO])
        if r["fact"]["kind"] == "lakeformation.grants.unresolved"
    )
    roteiro = json.loads(json.dumps(ROTEIRO_LF_VENCE).replace('"$grant"', json.dumps(lacuna)))
    resultado = debater(ws, roteiro, None)
    assert _vencedor(resultado["done"]) == "SF-LF-001"
    linha = grade_case(
        "sem_fato", _esperado("sem_fato"), _grava_execucao(tmp_path / "run", ws, resultado)
    )
    assert linha["outcome"] == "false_resolution"
    assert linha["decisive_fact"]["extracted"] is False
