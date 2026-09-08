"""Qual medida falta, e o que a obteria -- a secao 5.3 do spec.

Duas origens de `Unknown`, e as duas ja estao MEDIDAS no case:

1. **fact `*.unresolved`.** O motor emite 27 kinds terminados assim, um por
   familia de extrator, sempre com a razao em `attrs.reason`. Eles sao a recusa
   nomeada do produto -- regra 20: listar a recusa e a diferenca entre "nao sei"
   e "nao perguntei". Transforma-los em `Unknown` nao acrescenta informacao
   nova; da a lacuna a forma que o resto da camada agentica sabe manusear.
2. **finding cuja `evidence` cita fact que nao esta no case.** A claim daquele
   finding nao esta ancorada, e `claims.confidence_for` ja a rebaixa para `low`
   por isso. O `Unknown` diz QUAL ancora falta -- `low` sozinho nao diria.

## O que "bloqueante" decide, e por que ele nao e estilo

`blocking` decide quem vira experimento, entao ele precisa de criterio medido e
nao de gosto:

- fact `*.unresolved` **citado por algum finding** e bloqueante: um diagnostico
  do case depende daquela medida para concluir;
- fact `*.unresolved` que **nenhum finding cita** nao e: ele e lacuna do case, e
  nada esta parado esperando por ele. Sai como `Unknown` -- existe e e nomeado
  -- e nao gera experimento, porque propor um run para medir o que ninguem pediu
  seria custo sem pergunta;
- finding com ancora ausente e sempre bloqueante: a claim inteira depende dela.

A alternativa era `blocking=True` para tudo. Ela foi recusada porque tornaria
`blocking` um campo constante -- e campo que nunca varia nao decide nada, so
parece decidir.

## Medido sobre o corpus (253 fixtures com `facts.json` e `findings.json`)

**O denominador decide o numero, e ele sai junto.** A entrada do executor e a
UNIAO dos facts do case -- `input/facts.json` mais `expected/facts.json`, sem
`fact.id` repetido (secao 12.9 do spec). Sobre ela, remedido em 2026-09-08:
**61 `Unknown`, todos de origem 1, nenhum bloqueante, nenhum experimento.**

Sobre `expected/facts.json` sozinho saem 90, e os 29 de diferenca nao sao lacuna
a mais:

- **26 sao o mesmo `fact.id` contado duas vezes.** O corpus tem 92 ids repetidos
  dentro de `expected/facts.json`, e o mesmo id e uma medida so.
- **3 sao claims que PARECEM desancoradas e nao estao** -- `SF-UI-005` em
  `timeout/heartbeat_perdido` e em `timeout/heartbeat_vence_wall_clock`,
  `SF-UI-001` em `timeout/timeout_com_spill_e_skew`. As tres citam `fact.id` que
  mora no `input/facts.json` da propria fixture: `f_c77ad7` e o id
  content-addressed de `spark.executor.lost`. Errada estava a ENTRADA da medida,
  nao o corpus e nao o executor -- e uma medida anterior deste modulo as
  publicou como "claims desancoradas reais", o que era falso.

**Origem 2 nao tem caso no corpus de hoje, e isso sai escrito.** O ramo tem
teste sintetico e continua valendo; mecanismo sem caso e `unresolved` nomeado,
nunca funcionalidade entregue.

O zero que interessa e o mesmo de antes: **nenhum fact `*.unresolved` do corpus
e citado por finding nenhum**, e por isso nenhum deles e bloqueante. E o mesmo
achado que `conflict.py` registrou sobre as guardas `requires_absent` -- kind de
recusa diz *nao deu para ler*, e regra nao dispara sobre "nao li".

`test_no_corpus_nenhuma_recusa_e_citada_por_finding` trava essa medida. Se ela
cair, o corpus ganhou o caso que hoje nao tem, e a remediacao e atualizar a nota
-- nunca afrouxar o criterio de `blocking`.

## As tres amarras do experimento

- **`expected_results` fica VAZIO.** `design_experiment_for_unknown` o preenche
  com `"Answer to: <pergunta>"`, e mesmo esse texto ja e uma previsao de
  desfecho. Prever quanto vai melhorar e o que a regra 13 proibe, e o experimento
  aqui diz **o que medir**, ponto.
- **`cost_estimate` e `time_estimate` saem `"unresolved"`.** A entrega original
  da camada agentica fixava "1 Glue job run (DPU-hours)" e "15-30 minutes" em
  texto; a auditoria de 2026-09-03 pegou isso como um dos catorze defeitos.
  Havendo `glue.run_cost` de run comparavel eles poderiam ser medidos -- nao ha,
  e a recusa sai nomeada (regras 14 e 25). String vazia seria pior que
  `"unresolved"`: ela e ambigua entre "nao medi" e "custa zero".
- **`success_criteria` existe sempre**, e descreve a MEDIDA que fecha o
  `Unknown` -- nunca um alvo de melhora. E ele que separa experimento de desejo.

## Por que `variable` nomeia uma medida e nao um botao

Num experimento de tuning, `variable` e o que se muda. Aqui nao se muda nada: o
que falta e a medida. `variable` recebe o kind (ou o `fact.id` ausente), o
`baseline` diz que hoje nao ha medida, e o `rollback` diz explicitamente que nao
ha estado para reverter. Preencher `rollback` com "reverter para o baseline"
prometeria desfazer uma mudanca que este experimento nunca faz.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sparkforge.agentic.experiment import design_experiment_for_unknown
from sparkforge.agentic.models import Experiment, Unknown

# O sufixo que o motor usa para toda recusa de medida. Ele e convencao do
# catalogo de kinds, nao deste modulo -- por isso fica nomeado aqui em vez de
# aparecer literal no meio de um `endswith`.
SUFIXO_DE_RECUSA = ".unresolved"

# Quem propos. Sai em `Experiment.proposed_by` para que o experimento diga de
# onde veio sem que ninguem precise adivinhar pelo formato do texto.
_PROPONENTE = "sparkforge.agentic.executor.unknowns"

_ROLLBACK = (
    "nao aplica -- este experimento MEDE e nao muda configuracao; nao ha estado "
    "para reverter"
)


def unknowns_from(findings: list[dict], facts: list[dict]) -> list[Unknown]:
    """As lacunas do case, das duas origens da secao 5.3.

    Args:
        findings: findings julgados. So `rule_id` e `evidence` sao lidos.
        facts: facts do case. So `id`, `kind` e `attrs` sao lidos.

    Returns:
        Os `Unknown` na ordem dos facts (origem 1) seguidos dos findings
        (origem 2). Preservar a ordem de entrada, aqui como em
        `ordering.order_actions`, e o que nao inventa: ordenar por texto diria
        que uma lacuna vem antes da outra por alguma razao, e nao vem.

    Entrada degenerada devolve `[]` em vez de levantar -- regra 27, a mesma
    leitura de `conflict._acao` para finding sem bloco `action`.
    """
    facts_validos = [f for f in _iteravel(facts) if isinstance(f, dict)]
    findings_validos = [f for f in _iteravel(findings) if isinstance(f, dict)]

    ids_presentes = {
        str(f.get("id") or "").strip() for f in facts_validos if str(f.get("id") or "").strip()
    }
    citantes = _regras_por_fact(findings_validos)

    lacunas: list[Unknown] = []
    for fact in facts_validos:
        kind = str(fact.get("kind") or "").strip()
        fact_id = str(fact.get("id") or "").strip()
        if not kind.endswith(SUFIXO_DE_RECUSA) or not fact_id:
            continue
        lacunas.append(_da_recusa(kind, fact_id, fact.get("attrs"), citantes.get(fact_id, [])))

    for finding in findings_validos:
        rule_id = str(finding.get("rule_id") or "").strip()
        if not rule_id:
            continue
        for ref in _ancoras(finding):
            if ref not in ids_presentes:
                lacunas.append(_da_ancora_ausente(rule_id, ref))

    return lacunas


def experiments_from(unknowns: list[Unknown]) -> list[Experiment]:
    """Um `Experiment` por `Unknown` bloqueante, dizendo o que medir.

    Args:
        unknowns: saida de `unknowns_from`, ou qualquer lista de `Unknown`.

    Returns:
        Os experimentos na ordem dos unknowns bloqueantes. Nao bloqueante nao
        entra: veja a secao "o que blocking decide" no topo do modulo.

    O experimento sai de `design_experiment_for_unknown` e e AJUSTADO com
    `dataclasses.replace` -- `Experiment` e frozen. Reescrever a funcao de
    origem foi descartado: ela serve tambem ao caminho de hipotese, onde
    `expected_results` vem de um `expected_outcome` que alguem declarou, e ali o
    campo esta certo. O que muda e o uso, entao a correcao mora no uso.
    """
    experimentos: list[Experiment] = []
    for unknown in _iteravel(unknowns):
        if not isinstance(unknown, Unknown) or not unknown.blocking:
            continue

        medida = unknown.evidence_needed[0] if unknown.evidence_needed else unknown.question
        bruto = design_experiment_for_unknown(
            unknown_question=unknown.question,
            variable=medida,
            baseline=f"unresolved -- o case nao tem a medida de {medida}",
            evidence_needed=list(unknown.evidence_needed),
            proposed_by=_PROPONENTE,
        )

        experimentos.append(
            replace(
                bruto,
                # Vazio por decisao, nao por esquecimento: prever o resultado e
                # estimar ganho (regra 13).
                expected_results="",
                success_criteria=(
                    f"a medida de {medida} passa a existir no case, e o fact "
                    f"correspondente deixa de sair como recusa"
                ),
                failure_criteria=(
                    f"a coleta roda e {medida} continua sem medida; a razao "
                    f"declarada permanece a mesma"
                ),
                rollback=_ROLLBACK,
                # Nao ha `glue.run_cost` de run comparavel para sustentar
                # nenhum dos dois. Regras 14 e 25.
                cost_estimate="unresolved",
                time_estimate="unresolved",
            )
        )

    return experimentos


def _da_recusa(
    kind: str, fact_id: str, attrs: Any, citantes: list[str]
) -> Unknown:
    """Origem 1 -- o fact `*.unresolved` como `Unknown`.

    `owner` fica `None`. A tentacao e apontar o extrator de `provenance`, mas o
    extrator PRODUZIU a recusa; quem a resolve e quem tem o artefato que falta,
    e isso o case nao diz. Nomear o extrator como dono seria inventar
    responsavel.
    """
    razao = ""
    destrava: str | None = None
    if isinstance(attrs, dict):
        razao = str(attrs.get("reason") or "").strip()
        bruto = str(attrs.get("unblocked_by") or "").strip()
        destrava = bruto or None

    # A razao entra em `evidence_needed` DEPOIS do kind, e o kind e o item zero,
    # porque `experiments_from` usa o item zero como a medida a obter. Inverter
    # a ordem produziria um experimento cuja variavel e "reason: <codigo>", que
    # nao nomeia medida nenhuma.
    necessario = [kind]
    if razao:
        necessario.append(f"reason: {razao}")

    if citantes:
        impacto = f"citado por {', '.join(citantes)}"
    else:
        impacto = "nenhum finding do case cita este fact"

    return Unknown(
        question=f"{kind}: que medida fecha a lacuna do fact {fact_id}?",
        impact=impacto,
        blocking=bool(citantes),
        owner=None,
        evidence_needed=necessario,
        resolution_method=destrava,
    )


def _da_ancora_ausente(rule_id: str, fact_id: str) -> Unknown:
    """Origem 2 -- finding cuja evidencia nao esta no case.

    A pergunta comeca por `finding <rule_id>` porque a lacuna e da CLAIM, nao do
    fact: o fact pode existir noutro case, e o problema e este finding aqui ter
    concluido sobre uma medida que a entrega nao carrega.

    `resolution_method` fica `None` de proposito. O metodo obvio seria "rode a
    coleta que emite este fact", mas o `fact.id` e content-addressed e nao diz
    de qual extrator veio -- escrever o texto generico daria uma instrucao que
    nao aponta comando nenhum.
    """
    return Unknown(
        question=(
            f"finding {rule_id} cita o fact {fact_id}, que nao esta no case: "
            f"onde ele foi medido?"
        ),
        impact=f"a claim de {rule_id} nao esta ancorada",
        blocking=True,
        owner=None,
        evidence_needed=[fact_id],
        resolution_method=None,
    )


def _regras_por_fact(findings: list[dict]) -> dict[str, list[str]]:
    """Quais `rule_id` citam cada `fact.id`, sem repetir e na ordem de entrada."""
    citantes: dict[str, list[str]] = {}
    for finding in findings:
        rule_id = str(finding.get("rule_id") or "").strip()
        if not rule_id:
            continue
        for ref in _ancoras(finding):
            registro = citantes.setdefault(ref, [])
            if rule_id not in registro:
                registro.append(rule_id)
    return citantes


def _ancoras(finding: dict) -> list[str]:
    """Os `fact.id` que o finding declara, deduplicados na ordem de aparicao.

    Mesma leitura de `claims._fact_ids_declarados`, e pela mesma medida: a
    fixture `folga_medida_sem_skew` cita `f_681614` quatro vezes, uma por
    condicao do `all`. Sem deduplicar, um unico fact ausente viraria quatro
    `Unknown` identicos.
    """
    vistos: list[str] = []
    for bruto in finding.get("evidence") or []:
        ref = str(bruto).strip()
        if ref and ref not in vistos:
            vistos.append(ref)
    return vistos


def _iteravel(valor: Any) -> list[Any]:
    """A lista recebida, ou `[]` quando o caller mandou `None` ou outra coisa."""
    return list(valor) if isinstance(valor, (list, tuple)) else []
