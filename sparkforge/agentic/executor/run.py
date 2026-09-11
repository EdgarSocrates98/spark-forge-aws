"""A orquestracao -- os seis degraus viram um verbo, e o que ele grava.

`run_executor` nao decide nada sozinho: ele chama `claims`, `conflict`,
`digest`, `unknowns` e `plan` na ordem da secao 7 do spec, arbitra os pares
que se contradizem, grava no blackboard do case e devolve o pacote.

A ordenacao ele NAO calcula: ela vem de `digest.plan_digest`, que e o mesmo
calculo que `sparkforge_judge` publica. Duas implementacoes da mesma ordem
divergiriam com o tempo, e o operador leria uma ordem no `judge` e outra no
`arbitrate` sobre o mesmo case.

## A entrada e a UNIAO dos facts do case

O executor recebe **o mesmo conjunto de facts que `judge` recebeu** para
produzir aqueles findings. Alimenta-lo com um subconjunto -- so os derivados de
um dominio, por exemplo -- fabrica claim desancorada que a execucao real nao
produz, e o gate de lastro da secao 5.2 reprova claim que esta ancorada. A
secao 12.9 do spec mediu isso sobre `fixtures/timeout/`: os tres findings que
pareciam citar fact inexistente citavam facts do `input/facts.json` da propria
fixture.

`fact.id` repetido na entrada e UMA medida. Deduplicar na porta evita que a
mesma lacuna vire dois `Unknown` -- medido: o corpus tem 92 ids repetidos
dentro de `expected/facts.json`, e sem a deduplicacao eles inflavam a contagem
de lacunas de 64 para 90 sem que nada de novo tivesse sido medido.

## Por que a condicional vira `Objection` e nao `Contradiction`

`Contradiction(claim_a, claim_b, ...)` liga **duas claims**. A contradicao
condicional liga **uma claim a uma MEDIDA**: a acao declara `requires_absent:
<kind>` e aquele kind esta medido no case. Enfia-la naquele modelo exigiria
inventar uma segunda claim para o lado que e um fact, e o registro passaria a
mentir sobre o tipo do que foi achado. `Objection(target_claim, objector,
statement, evidence_refs)` e a forma que ja existe para "alguem contesta esta
claim, e aqui esta a medida" -- o `fact.id` viaja em `evidence_refs`.

## O score de arbitragem nao sai na resposta

Os pesos de `assess_claim` (evidencia 40%, autoridade 30%, especificidade 20%,
aplicabilidade 10%) sao convencao e nenhum experimento os calibrou -- o
`CLAUDE.md` diz isso por escrito, e a docstring da propria funcao repete. Eles
ordenam claims **dentro** de uma arbitragem; o valor absoluto nao e confianca
medida. A resposta do verbo carrega o desfecho (`accept`, `escalate`,
`experiment`) e nunca o numero. O numero fica no trace do blackboard, ao lado
do rotulo que diz que ele e convencao -- e a secao 5.1 do spec manda
exatamente isso.

## `validate_autonomy_boundary` NAO e chamado, e a razao e o vocabulario

O perfil L0 declara `allowed_actions = [extract_facts, judge_rules,
validate_output]` e `forbidden_actions = [spawn_agent, debate, experiment,
modify_code]`. O que este verbo faz -- gravar claim, contradicao e decisao
PROPOSTA -- nao esta em nenhuma das duas listas. Chamar a funcao exigiria
escolher entre dois erros:

- passar `"debate"` ou `"experiment"`, que sao proibidos em L0 e devolveriam
  `False` para uma acao que o executor nao executa (ele **emite** o plano e
  propoe o experimento; quem debata ou rode e outro);
- passar um nome fora do vocabulario, que devolve `False` por nao estar em
  `allowed_actions` -- recusa correta pelo motivo errado.

Nos dois casos o resultado seria uma autorizacao (ou recusa) sobre uma acao que
nao e a deste verbo. A funcao existe para o chamador que PEDE acao de risco
declarando os guardrails que comprovou; este nao pede. O que a resposta faz e
declarar o nivel e o fato -- `applied_changes: False` -- para quem le o ADR
saber que ele e proposta, nao registro de coisa feita.

## Onde o ADR e gravado

Dentro do case, em `.sparkforge/blackboard/adr/`, ao lado do `decisions.jsonl`
que o gerou. **Nao** em `docs/vnext/adrs/`: aquele diretorio guarda as decisoes
de arquitetura DESTE repositorio, numeradas a mao e auditadas pelo gate de
lastro. Um verbo de runtime que escrevesse ali misturaria saida de case com
documentacao do produto, faria dois cases diferentes disputarem a mesma
numeracao, e mandaria o executor escrever fora do `root` que recebeu. ADR de
case viaja com o case.

## O relogio

Nenhuma entidade recebe `created_at`. Este modulo nao le hora, pela mesma razao
que `claims_from_findings` nao le: id content-addressed com hora dentro deixa de
ser content-addressed, e a mesma entrada passaria a produzir ids diferentes a
cada execucao -- com isso a revisao de claim viraria duplicata a cada run.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sparkforge.agentic.arbitration import ArbitrationResult, arbitrate
from sparkforge.agentic.blackboard import (
    append_claim,
    append_contradiction,
    append_decision,
    append_evidence,
    append_experiment,
    append_objection,
    append_trace,
    append_unknown,
    blackboard_path,
    init_blackboard,
    read_claims,
    read_contradictions,
    read_decisions,
    read_evidence,
    read_experiments,
    read_objections,
    read_unknowns,
)
from sparkforge.agentic.decision import (
    DecisionContext,
    generate_adr,
    is_significant_decision,
    make_decision,
)
from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import claims_from_findings
from sparkforge.agentic.executor.conflict import conditional_conflicts, direct_conflicts
from sparkforge.agentic.executor.digest import plan_digest
from sparkforge.agentic.executor.plan import debate_plan
from sparkforge.agentic.executor.unknowns import experiments_from, unknowns_from
from sparkforge.agentic.models import Claim, Contradiction, Decision, Objection

AGENTE = "sparkforge.agentic.executor"

# Nivel de autonomia deste verbo. Ele escreve decisao e NUNCA aplica mudanca --
# ver o cabecalho para por que `validate_autonomy_boundary` nao e chamado.
NIVEL_DE_AUTONOMIA = "L0"

# O diretorio do ADR, dentro do blackboard do case.
DIR_DE_ADR = "adr"

# Os desfechos de arbitragem que NAO fecham. `escalate` diz que nenhuma claim
# teve lastro suficiente; `experiment` diz que a diferenca entre elas nao se
# resolve com o que esta medido. Nos dois o executor emite plano de debate e
# para -- inventar vencedor aqui seria decidir por desempate arbitrario.
_NAO_FECHAM = frozenset({"escalate", "experiment"})

# Ordem de forca da confianca, do mais forte para o mais fraco.
_FORCA = ("high", "medium", "low")

_ROTULO_DE_CONVENCAO = (
    "os pesos de assess_claim (evidencia, autoridade, especificidade, "
    "aplicabilidade) sao CONVENCAO desta engine e nenhum experimento os "
    "calibrou: eles ordenam claims dentro desta arbitragem e nao sao confianca "
    "medida (CLAUDE.md, secao de arbitragem)"
)

_MOTIVOS_DE_NAO_FECHAR = {
    "escalate": (
        "a arbitragem nao elegeu vencedor com lastro suficiente entre as claims "
        "em disputa"
    ),
    "experiment": (
        "a arbitragem pediu medida nova para diferenciar as claims: o que esta "
        "medido no case nao separa uma da outra"
    ),
}

_MOTIVO_SEM_VENCEDOR = "a arbitragem nao devolveu claim vencedora"


def run_executor(
    findings: list[dict],
    facts: list[dict],
    root: Path | str,
    runtime: dict | None = None,
    budget: dict | None = None,
) -> dict:
    """Roda o executor sobre findings julgados e grava no blackboard do case.

    Args:
        findings: findings ja julgados, no formato de `findings.json`.
        facts: **a uniao** dos facts do case -- o mesmo conjunto que `judge`
            recebeu. Ver o cabecalho deste modulo.
        root: raiz do case; o blackboard fica em `<root>/.sparkforge/blackboard`.
        runtime: o que o case mediu, ex. `{"glue": "5.0", "spark": "3.5.4"}`.
        budget: o bloco `budget:` do `case.yaml`, ou `None`. **Nunca** o default
            do codigo -- sem bloco o plano de debate sai `unresolved` nomeando a
            lacuna.

    Returns:
        O pacote serializavel, com `claims`, `evidence`, `contradictions`,
        `objections`, `unknowns`, `experiments`, `decisions`, `debate_plans`,
        `order`, `autonomy`, `persisted` e `persistence`.

    A resposta e montada ANTES da gravacao e nao depende dela. Blackboard
    indisponivel, disco cheio ou append que levanta saem em
    `persistence.errors` com `persisted: False`, e o produto sai igual -- regra
    27: instrumentacao que quebra o produto e defeito, nao observabilidade.
    """
    findings_validos = [f for f in _iteravel(findings) if isinstance(f, dict)]
    facts_unicos = _facts_unicos(facts)
    contexto = dict(runtime or {})

    mapa = load_authority_map()

    claims, evidences = claims_from_findings(findings_validos, facts_unicos, mapa, contexto)

    # A ordenacao vem do digest, e nao de `order_actions` chamado aqui. E o
    # mesmo calculo que `sparkforge_judge` publica: duas implementacoes da mesma
    # ordem divergiriam com o tempo -- cada uma com o seu teste passando -- e o
    # operador veria o `judge` afirmar uma ordem e o `arbitrate` gravar outra
    # sobre o MESMO case. O `authority_map` ja carregado viaja junto para o
    # digest nao reler o YAML.
    bloco, _lastro = plan_digest(findings_validos, facts_unicos, contexto, authority_map=mapa)
    ordem = bloco["order"]
    restricoes = bloco["constraints"]
    ordem_unresolved = bloco["order_unresolved"]

    # Contradicoes e objecoes continuam vindo de `direct_conflicts` e
    # `conditional_conflicts` em forma de TUPLA de propositio. Aqui elas viram
    # `Contradiction(claim_a, claim_b, ...)` e `Objection(target_claim, ...)`, o
    # que exige os ids CRUS; o bloco os traz ja serializados em dicionario, e
    # reparsear dicionario para reconstruir a tupla seria pior que chamar a
    # funcao de novo. Mesma razao para `unknowns_from`: `experiments_from` e a
    # gravacao precisam dos objetos `Unknown`, nao da forma publicada.
    diretas = direct_conflicts(findings_validos)
    condicionais = conditional_conflicts(findings_validos, facts_unicos)
    lacunas = unknowns_from(findings_validos, facts_unicos)
    experimentos = experiments_from(lacunas)

    claims_por_regra = _claims_por_regra(claims)
    acoes = _acoes_por_regra(findings_validos)
    ancoras = _ancoras_por_regra(findings_validos)

    contradicoes: list[tuple[Contradiction, str, str, str]] = []
    decisoes: list[Decision] = []
    planos: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    for regra_a, regra_b, resultado, decisao, plano in _arbitra_pares(
        diretas, claims_por_regra, evidences, acoes, ancoras, findings_validos, lacunas,
        contexto, budget,
    ):
        traces.append(_trace_de_arbitragem(regra_a, regra_b, resultado))
        if decisao is not None:
            decisoes.append(decisao)
            resolucao: str | None = f"decision {decisao.id}"
        else:
            planos.append(plano)
            resolucao = None

        contradicoes.extend(
            _contradicoes_do_par(regra_a, regra_b, claims_por_regra, acoes, ancoras, resolucao)
        )

    objecoes = _objecoes(condicionais, claims_por_regra, acoes)

    resposta = _resposta(
        claims=claims,
        evidences=evidences,
        contradicoes=contradicoes,
        objecoes=objecoes,
        lacunas=lacunas,
        experimentos=experimentos,
        decisoes=decisoes,
        planos=planos,
        ordem=ordem,
        restricoes=restricoes,
        ordem_unresolved=ordem_unresolved,
    )

    gravacao = _persistir(
        root,
        claims=claims,
        evidences=evidences,
        contradicoes=contradicoes,
        objecoes=objecoes,
        lacunas=lacunas,
        experimentos=experimentos,
        decisoes=decisoes,
        traces=traces,
    )
    for entrada in resposta["claims"]:
        entrada["supersedes"] = gravacao["supersedes"].get(entrada["id"])
    resposta["persisted"] = gravacao["persisted"]
    resposta["persistence"] = gravacao["persistence"]
    return resposta


def open_debate_plans(
    findings: list[dict],
    facts: list[dict],
    runtime: dict | None = None,
    budget: dict | None = None,
) -> list[dict[str, Any]]:
    """Os `debate_plans` que `run_executor` emitiria, CALCULADOS e nunca gravados.

    Existe para o executor de debate congelar o plano de um par sem rodar o
    `arbitrate` de novo -- rodar o verbo gravaria claim, evidencia e trace no
    blackboard como efeito colateral de uma pergunta de leitura.

    O caminho e o MESMO de `run_executor` (`_arbitra_pares`), e nao uma copia:
    duas implementacoes de "este par fecha ou vira plano?" divergiriam com o
    tempo, e o debate congelaria um plano que o `arbitrate` do mesmo case nao
    emite.
    """
    findings_validos = [f for f in _iteravel(findings) if isinstance(f, dict)]
    facts_unicos = _facts_unicos(facts)
    contexto = dict(runtime or {})
    mapa = load_authority_map()

    claims, evidences = claims_from_findings(findings_validos, facts_unicos, mapa, contexto)
    lacunas = unknowns_from(findings_validos, facts_unicos)
    pares = _arbitra_pares(
        direct_conflicts(findings_validos),
        _claims_por_regra(claims),
        evidences,
        _acoes_por_regra(findings_validos),
        _ancoras_por_regra(findings_validos),
        findings_validos,
        lacunas,
        contexto,
        budget,
    )
    return [plano for _a, _b, _resultado, decisao, plano in pares if decisao is None]


# --------------------------------------------------------------------------
# Contradicao direta
# --------------------------------------------------------------------------


def _claims_por_regra(claims: list[Claim]) -> dict[str, list[Claim]]:
    """As claims agrupadas pela regra que as produziu, na ordem de entrada."""
    por_regra: dict[str, list[Claim]] = defaultdict(list)
    for claim in claims:
        por_regra[claim.claimant].append(claim)
    return por_regra


def _arbitra_pares(
    diretas: list[tuple[str, str]],
    claims_por_regra: dict[str, list[Claim]],
    evidences: list[Any],
    acoes: dict[str, dict[str, Any]],
    ancoras: dict[str, list[str]],
    findings: list[dict],
    lacunas: list[Any],
    contexto: dict[str, Any],
    budget: dict | None,
) -> list[tuple[str, str, ArbitrationResult, Decision | None, dict[str, Any] | None]]:
    """Arbitra cada par de contradicao direta: `(a, b, resultado, decisao, plano)`.

    Exatamente um de `decisao` e `plano` e `None`: o par fecha
    deterministicamente ou vira plano de debate, e nunca os dois. Puro -- nao
    grava nada --, e por isso serve tanto a `run_executor` quanto a
    `open_debate_plans`.
    """
    saida: list[tuple[str, str, ArbitrationResult, Decision | None, dict[str, Any] | None]] = []
    for regra_a, regra_b in diretas:
        disputantes = [*claims_por_regra.get(regra_a, ()), *claims_por_regra.get(regra_b, ())]
        if not disputantes:
            # Par de regras sem claim nenhuma: nao ha o que arbitrar. Nao
            # acontece com finding bem formado -- toda regra que entrou em
            # `direct_conflicts` tem finding --, mas gravar contradicao entre
            # claims que nao existem produziria linhagem quebrada.
            continue

        resultado = arbitrate(disputantes, evidences, target_runtime=contexto)

        decisao = None
        if _fecha(resultado):
            decisao = _decisao_do_par(
                regra_a, regra_b, resultado, disputantes, evidences, acoes, findings,
                lacunas, contexto,
            )
        plano = None
        if decisao is None:
            plano = {
                "rules": [regra_a, regra_b],
                "recommendation": resultado.recommendation,
                "reason": _motivo_de_nao_fechar(resultado),
                "plan": debate_plan(
                    [regra_a, regra_b],
                    {regra: ancoras.get(regra, []) for regra in (regra_a, regra_b)},
                    budget,
                ),
            }
        saida.append((regra_a, regra_b, resultado, decisao, plano))
    return saida


def _fecha(resultado: ArbitrationResult) -> bool:
    """A arbitragem fechou deterministicamente?

    Duas condicoes, e as duas sao necessarias: houve vencedora, e o desfecho nao
    e um dos dois que pedem mais alguem (`escalate`, `experiment`). Fechar sem
    vencedora seria decidir por desempate arbitrario; fechar com `escalate`
    seria ignorar a propria recusa da arbitragem.
    """
    return bool(resultado.winning_claim_id) and resultado.recommendation not in _NAO_FECHAM


def _motivo_de_nao_fechar(resultado: ArbitrationResult) -> str:
    """Por que o par parou, sem citar numero.

    `ArbitrationResult.reasoning` traz o score no meio da frase, entao ele nao
    viaja: publicar o texto inteiro publicaria a convencao como se fosse medida.
    O desfecho nomeado responde a mesma pergunta sem o numero.
    """
    if not resultado.winning_claim_id:
        return _MOTIVO_SEM_VENCEDOR
    return _MOTIVOS_DE_NAO_FECHAR.get(resultado.recommendation, _MOTIVO_SEM_VENCEDOR)


def _trace_de_arbitragem(
    regra_a: str, regra_b: str, resultado: ArbitrationResult
) -> dict[str, Any]:
    """O trace da arbitragem, com o numero e o rotulo que ele exige.

    A secao 5.1 do spec manda o score aparecer no trace **rotulado como
    convencao**, e nunca na resposta. Sem o rotulo ao lado, o numero seria lido
    como confianca medida por quem abrisse `traces.jsonl`.
    """
    corpo: dict[str, Any] = {
        "kind": "arbitration",
        "rules": [regra_a, regra_b],
        "winning_claim_id": resultado.winning_claim_id,
        "recommendation": resultado.recommendation,
        "disputed": resultado.disputed,
        "false_consensus_detected": resultado.false_consensus_detected,
        "convention_label": _ROTULO_DE_CONVENCAO,
        "convention_only_independence": resultado.independence_score,
        "convention_only_evidence_quality_winner": resultado.evidence_quality_winner,
        "convention_only_evidence_quality_loser": resultado.evidence_quality_loser,
        "decided_by": AGENTE,
    }
    # `append_trace` exige `id` e nao deduplica -- trace e evento, e dois runs
    # sao dois eventos. O id e content-addressed sobre o corpo pela mesma razao
    # que o das entidades: a MESMA arbitragem tem o mesmo id nos dois registros,
    # e um contador ou um relogio fariam duas gravacoes do mesmo evento
    # parecerem dois eventos diferentes.
    canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha1(canonico.encode("utf-8"), usedforsecurity=False).hexdigest()
    return {"id": "trace_" + digest[:8], **corpo}


def _contradicoes_do_par(
    regra_a: str,
    regra_b: str,
    claims_por_regra: dict[str, list[Claim]],
    acoes: dict[str, dict[str, Any]],
    ancoras: dict[str, list[str]],
    resolucao: str | None,
) -> list[tuple[Contradiction, str, str, str]]:
    """Uma `Contradiction` por par de claims das duas regras.

    Duas ocorrencias da mesma regra sobre sujeitos diferentes sao duas claims, e
    cada uma delas contradiz cada claim da outra regra. Gravar so o primeiro par
    deixaria de fora sujeitos que estao em conflito de verdade, e o produto
    cartesiano e o que nao perde nenhum.

    Os `fact.id` dos dois lados entram na DESCRICAO porque `Contradiction` liga
    dois claim_id e nao tem campo de fact -- e a secao 4 do spec exige as duas
    ancoras. Sem elas o relatorio diria que ha conflito sem dizer de que medida
    cada lado saiu.

    As duas regras e o alvo voltam ao lado da entidade, e nao dentro dela, pela
    mesma razao de `_objecoes`: a resposta precisa dos tres, `Contradiction` nao
    tem campo para nenhum, e reextrai-los da descricao rio abaixo seria parsear
    a propria saida.
    """
    alvo = str((acoes.get(regra_a) or {}).get("target") or "").strip()
    direcao_a = str((acoes.get(regra_a) or {}).get("direction") or "").strip()
    direcao_b = str((acoes.get(regra_b) or {}).get("direction") or "").strip()
    descricao = (
        f"{regra_a} propoe `{direcao_a}` e {regra_b} propoe `{direcao_b}` sobre o "
        f"mesmo target `{alvo}`; ancoras: {regra_a} em "
        f"{_ancoras_em_texto(ancoras.get(regra_a))}, {regra_b} em "
        f"{_ancoras_em_texto(ancoras.get(regra_b))}"
    )

    saida: list[tuple[Contradiction, str, str, str]] = []
    for claim_a in claims_por_regra.get(regra_a, ()):
        for claim_b in claims_por_regra.get(regra_b, ()):
            saida.append(
                (
                    Contradiction(
                        claim_a=claim_a.id,
                        claim_b=claim_b.id,
                        description=descricao,
                        detected_by=AGENTE,
                        resolution=resolucao,
                    ),
                    regra_a,
                    regra_b,
                    alvo,
                )
            )
    return saida


def _decisao_do_par(
    regra_a: str,
    regra_b: str,
    resultado: ArbitrationResult,
    disputantes: list[Claim],
    evidences: list[Any],
    acoes: dict[str, dict[str, Any]],
    findings: list[dict],
    lacunas: list[Any],
    contexto: dict[str, Any],
) -> Decision | None:
    """A decisao do par, com `rollback` obrigatorio.

    `confidence` sai no maximo `medium`, e isso e a tabela da secao 5.1 aplicada
    literalmente: `high` exige "nenhuma contradicao aberta", e uma contradicao
    direta tem duas claims por construcao. Uma claim vencedora `low` continua
    `low` -- a disputa resolvida nao promove lastro que nao existe.
    """
    vencedora = next((c for c in disputantes if c.id == resultado.winning_claim_id), None)
    if vencedora is None:  # pragma: no cover -- `_fecha` ja exigiu vencedora
        return None

    regra_vencedora = vencedora.claimant
    regra_perdedora = regra_b if regra_vencedora == regra_a else regra_a
    opcoes = [_opcao(regra_a, acoes), _opcao(regra_b, acoes)]
    escolhida = _opcao(regra_vencedora, acoes)

    contexto_de_decisao = DecisionContext(
        problem=(
            f"contradicao direta em `{str((acoes.get(regra_a) or {}).get('target') or '')}`: "
            f"{regra_a} e {regra_b} propoem direcoes opostas sobre o mesmo alvo"
        ),
        options=opcoes,
        evidence_by_option={
            escolhida: [e.id for e in evidences if vencedora.id in e.supports],
        },
        risks=_riscos(regra_vencedora, regra_perdedora, findings),
        assumptions=[
            "as duas acoes tocam o mesmo alvo em direcoes opostas: aplicar as "
            "duas e impossivel por construcao, e nao uma questao de ordem"
        ],
        unknowns=[u.id for u in lacunas if _fala_de(u, regra_a) or _fala_de(u, regra_b)],
        runtime=dict(contexto),
        decided_by=AGENTE,
    )

    return make_decision(
        contexto_de_decisao,
        selected_option=escolhida,
        confidence=_confianca_de_disputa(vencedora.confidence),
        validation=_validacao(regra_vencedora, findings),
        rollback=(
            f"desfazer a acao de {regra_vencedora} sobre "
            f"`{str((acoes.get(regra_vencedora) or {}).get('target') or '')}`, restaurando o "
            f"valor anterior do alvo. Nada foi aplicado por este verbo: a "
            f"autonomia e {NIVEL_DE_AUTONOMIA} e a decisao e proposta"
        ),
        falsification_condition=(
            f"{regra_perdedora} passa a ter fonte de referencia vigente no runtime "
            f"do case, ou a medida que ancora {regra_vencedora} deixa de casar com "
            f"o limiar da regra"
        ),
    )


def _confianca_de_disputa(confianca_da_claim: str) -> str:
    """A confianca da decisao, limitada a `medium` (tabela da secao 5.1).

    O teto nao e cautela: `high` exige, na propria tabela, "nenhuma contradicao
    aberta", e esta decisao existe **porque** havia contradicao. Publicar `high`
    aqui contradiria a linha que a autorizou.
    """
    if confianca_da_claim not in _FORCA:  # pragma: no cover -- `Claim` ja valida
        return "low"
    return "medium" if confianca_da_claim == "high" else confianca_da_claim


def _opcao(rule_id: str, acoes: dict[str, dict[str, Any]]) -> str:
    """A opcao como texto, derivada do bloco `action` daquela regra.

    Regra sem `action` nao chega aqui (`direct_conflicts` so ve quem tem), mas o
    fallback existe para que a opcao nunca saia vazia -- `make_decision` compara
    `selected_option` com `options` por igualdade de string, e duas opcoes
    vazias colidiriam.
    """
    acao = acoes.get(rule_id) or {}
    kind = str(acao.get("kind") or "").strip() or "acao nao declarada"
    alvo = str(acao.get("target") or "").strip() or "alvo nao declarado"
    direcao = str(acao.get("direction") or "").strip() or "direcao nao declarada"
    return f"{rule_id}: {kind} ({direcao}) em {alvo}"


def _riscos(regra_vencedora: str, regra_perdedora: str, findings: list[dict]) -> list[str]:
    """Os riscos da escolha: o que a regra vencedora declara, mais o que fica aberto.

    O primeiro item nao vem do catalogo, e e o risco que so existe por causa da
    escolha -- o achado da regra preterida continua de pe. Os demais sao os
    `risks` que a propria regra vencedora declara, copiados sem reescrita.
    """
    riscos = [
        f"o achado de {regra_perdedora} continua aberto: a acao dele nao e "
        f"aplicada, e a razao e a incompatibilidade com {regra_vencedora}"
    ]
    for finding in findings:
        if str(finding.get("rule_id") or "").strip() != regra_vencedora:
            continue
        for bruto in finding.get("risks") or []:
            texto = str(bruto).strip()
            if texto and texto not in riscos:
                riscos.append(texto)
    return riscos


def _validacao(regra_vencedora: str, findings: list[dict]) -> str:
    """Como conferir que o resultado nao mudou -- o `validation` da propria regra.

    Regra sem `validation` sai `unresolved` nomeando a lacuna em vez de uma
    frase generica: "validar o resultado" nao e conferivel por ninguem.
    """
    for finding in findings:
        if str(finding.get("rule_id") or "").strip() != regra_vencedora:
            continue
        itens = [str(b).strip() for b in finding.get("validation") or [] if str(b).strip()]
        if itens:
            return "; ".join(itens)
    return f"unresolved -- {regra_vencedora} nao declara `validation` no catalogo"


def _fala_de(lacuna: Any, rule_id: str) -> bool:
    """A lacuna cita esta regra, na pergunta ou no impacto?

    As duas origens de `Unknown` nomeiam a regra em campos diferentes: a de
    ancora ausente comeca a pergunta com `finding <rule_id>`, e a de recusa
    nomeia quem cita o fact em `impact`. Procurar nos dois e o que nao perde
    nenhuma das duas.
    """
    return rule_id in str(getattr(lacuna, "question", "")) or rule_id in str(
        getattr(lacuna, "impact", "")
    )


# --------------------------------------------------------------------------
# Contradicao condicional
# --------------------------------------------------------------------------


def _objecoes(
    condicionais: list[tuple[str, str, str]],
    claims_por_regra: dict[str, list[Claim]],
    acoes: dict[str, dict[str, Any]],
) -> list[tuple[Objection, str, str]]:
    """Uma `Objection` por (claim da regra, guarda medida).

    Devolve a objecao junto com o kind e o `fact.id` que a produziram, porque a
    resposta precisa dos dois e `Objection` nao tem campo para eles: o fact vive
    em `evidence_refs`, e o kind so aparece dentro do texto do `statement`.
    Reextrai-los do texto rio abaixo seria parsear a propria saida.
    """
    saida: list[tuple[Objection, str, str]] = []
    for rule_id, kind, fact_id in condicionais:
        alvo = str((acoes.get(rule_id) or {}).get("target") or "").strip()
        for claim in claims_por_regra.get(rule_id, ()):
            saida.append(
                (
                    Objection(
                        target_claim=claim.id,
                        objector=AGENTE,
                        statement=(
                            f"a acao de {rule_id} sobre `{alvo}` declara "
                            f"`requires_absent: {kind}`, e {kind} esta medido neste "
                            f"case (fact {fact_id})"
                        ),
                        evidence_refs=[fact_id],
                    ),
                    kind,
                    fact_id,
                )
            )
    return saida


# --------------------------------------------------------------------------
# A resposta
# --------------------------------------------------------------------------


def _resposta(
    claims: list[Claim],
    evidences: list[Any],
    contradicoes: list[tuple[Contradiction, str, str, str]],
    objecoes: list[tuple[Objection, str, str]],
    lacunas: list[Any],
    experimentos: list[Any],
    decisoes: list[Decision],
    planos: list[dict[str, Any]],
    ordem: list[str],
    restricoes: list[dict],
    ordem_unresolved: dict,
) -> dict[str, Any]:
    """O pacote serializavel, montado antes de qualquer gravacao.

    Nenhum campo carrega o score de arbitragem -- ver o cabecalho do modulo. O
    que sai de cada entidade e o id mais o que identifica o achado; o corpo
    inteiro fica no blackboard, que e onde ele e auditavel sem inflar a
    resposta.
    """
    return {
        "kind": "executor.run",
        "autonomy": {
            "level": NIVEL_DE_AUTONOMIA,
            "applied_changes": False,
            "note": (
                "o executor escreve decisao e nunca aplica mudanca; o ADR e "
                "proposta com rollback, nao registro de coisa feita"
            ),
        },
        "claims": [
            {
                "id": c.id,
                "claimant": c.claimant,
                "statement": c.statement,
                "confidence": c.confidence,
                "evidence_refs": list(c.evidence_refs),
                "supersedes": c.supersedes,
            }
            for c in claims
        ],
        "evidence": [
            {
                "id": e.id,
                "source": e.source,
                "authority": e.authority.value,
                "scope": e.scope,
                "measurement_ref": e.measurement_ref,
                "supports": list(e.supports),
            }
            for e in evidences
        ],
        "contradictions": [
            {
                "id": c.id,
                "claim_a": c.claim_a,
                "claim_b": c.claim_b,
                "rules": [regra_a, regra_b],
                "target": alvo,
                "description": c.description,
                "resolution": c.resolution,
            }
            for c, regra_a, regra_b, alvo in contradicoes
        ],
        "objections": [
            {
                "id": o.id,
                "target_claim": o.target_claim,
                "kind": kind,
                "fact_id": fact_id,
                "statement": o.statement,
            }
            for o, kind, fact_id in objecoes
        ],
        "unknowns": [
            {
                "id": u.id,
                "question": u.question,
                "impact": u.impact,
                "blocking": u.blocking,
                "evidence_needed": list(u.evidence_needed),
            }
            for u in lacunas
        ],
        "experiments": [
            {
                "id": x.id,
                "variable": x.variable,
                "success_criteria": x.success_criteria,
                "cost_estimate": x.cost_estimate,
                "time_estimate": x.time_estimate,
            }
            for x in experimentos
        ],
        "decisions": [
            {
                "id": d.id,
                "problem": d.problem,
                "selected_option": d.selected_option,
                "rejected_options": list(d.rejected_options),
                "confidence": d.confidence,
                "rollback": d.rollback,
                "validation": d.validation,
                "significant": is_significant_decision(d),
            }
            for d in decisoes
        ],
        "debate_plans": planos,
        "order": {
            "sequence": list(ordem),
            "constraints": restricoes,
            "unresolved": ordem_unresolved,
        },
        "persisted": False,
        "persistence": {},
    }


# --------------------------------------------------------------------------
# Gravacao
# --------------------------------------------------------------------------


def _persistir(
    root: Path | str,
    claims: list[Claim],
    evidences: list[Any],
    contradicoes: list[tuple[Contradiction, str, str, str]],
    objecoes: list[tuple[Objection, str, str]],
    lacunas: list[Any],
    experimentos: list[Any],
    decisoes: list[Decision],
    traces: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grava tudo, e nunca levanta.

    Regra 27. Toda falha vira uma entrada nomeada em `errors` -- a entidade que
    falhou, o tipo do erro e a mensagem -- e as demais continuam sendo gravadas.
    Abortar na primeira deixaria o blackboard pela metade sem dizer onde parou.

    Entidade cujo id ja esta no blackboard e PULADA, nao regravada. Rodar o
    verbo duas vezes sobre a mesma entrada nao acrescenta nada, e deixar o
    append levantar por duplicata transformaria idempotencia em falha.
    """
    erros: list[dict[str, str]] = []
    escritos: dict[str, int] = defaultdict(int)
    pulados: dict[str, int] = defaultdict(int)
    revisoes: dict[str, str] = {}
    adrs: list[str] = []

    try:
        init_blackboard(root)
        existentes = _ids_existentes(root)
        anteriores = _ultima_claim_por_afirmacao(root)
    except Exception as exc:
        return {
            "persisted": False,
            "supersedes": {},
            "persistence": {
                "root": str(root),
                "written": {},
                "skipped": {},
                "adrs": [],
                "errors": [_erro("blackboard", str(root), exc)],
            },
        }

    for claim in claims:
        if claim.id in existentes["claim"]:
            pulados["claims"] += 1
            continue
        anterior = anteriores.get((claim.claimant, claim.statement))
        # `supersedes` nao entra no payload do id, entao marcar a revisao aqui
        # nao move o id que a resposta ja publicou.
        gravavel = dataclasses.replace(claim, supersedes=anterior) if anterior else claim
        if _grava(append_claim, gravavel, root, "claim", claim.id, erros):
            escritos["claims"] += 1
            existentes["claim"].add(claim.id)
            anteriores[(claim.claimant, claim.statement)] = claim.id
            if anterior:
                revisoes[claim.id] = anterior

    for evidencia in evidences:
        _grava_unico(
            append_evidence, evidencia, root, "evidence", existentes, escritos, pulados, erros
        )
    for contradicao, _regra_a, _regra_b, _alvo in contradicoes:
        _grava_unico(
            append_contradiction,
            contradicao,
            root,
            "contradiction",
            existentes,
            escritos,
            pulados,
            erros,
        )
    for objecao, _kind, _fact_id in objecoes:
        _grava_unico(
            append_objection, objecao, root, "objection", existentes, escritos, pulados, erros
        )
    for lacuna in lacunas:
        _grava_unico(
            append_unknown, lacuna, root, "unknown", existentes, escritos, pulados, erros
        )
    for experimento in experimentos:
        _grava_unico(
            append_experiment,
            experimento,
            root,
            "experiment",
            existentes,
            escritos,
            pulados,
            erros,
        )
    for decisao in decisoes:
        if _grava_unico(
            append_decision, decisao, root, "decision", existentes, escritos, pulados, erros
        ):
            caminho = _grava_adr(decisao, root, erros)
            if caminho:
                adrs.append(caminho)

    for trace in traces:
        # Trace nao tem id content-addressed e por isso nao entra na checagem de
        # duplicata: ele registra que a arbitragem ACONTECEU, e duas execucoes
        # sao dois acontecimentos.
        try:
            append_trace(trace, root)
            escritos["traces"] += 1
        except Exception as exc:
            erros.append(_erro("trace", str(trace.get("rules")), exc))

    return {
        "persisted": not erros,
        "supersedes": revisoes,
        "persistence": {
            "root": str(root),
            "written": dict(escritos),
            "skipped": dict(pulados),
            "adrs": adrs,
            "errors": erros,
        },
    }


def _grava_unico(
    append: Any,
    entidade: Any,
    root: Path | str,
    tipo: str,
    existentes: dict[str, set[str]],
    escritos: dict[str, int],
    pulados: dict[str, int],
    erros: list[dict[str, str]],
) -> bool:
    """Grava a entidade se ela ja nao estiver la. Devolve se gravou."""
    if entidade.id in existentes[tipo]:
        pulados[tipo + "s"] += 1
        return False
    if not _grava(append, entidade, root, tipo, entidade.id, erros):
        return False
    existentes[tipo].add(entidade.id)
    escritos[tipo + "s"] += 1
    return True


def _grava(
    append: Any,
    entidade: Any,
    root: Path | str,
    tipo: str,
    entidade_id: str,
    erros: list[dict[str, str]],
) -> bool:
    try:
        append(entidade, root)
        return True
    except Exception as exc:
        erros.append(_erro(tipo, entidade_id, exc))
        return False


def _grava_adr(decisao: Decision, root: Path | str, erros: list[dict[str, str]]) -> str | None:
    """O ADR da decisao, em `<blackboard>/adr/`, quando ela e significativa.

    `is_significant_decision` aprova toda decisao que este verbo emite hoje --
    ela nunca sai `high`, e "confidence != high" e o primeiro criterio da funcao.
    O gate continua sendo chamado em vez de assumido: no dia em que uma decisao
    sair `high` sem risco declarado, a resposta muda sozinha, e uma condicao
    escrita a mao aqui teria envelhecido em silencio.
    """
    if not is_significant_decision(decisao):
        return None
    try:
        destino = blackboard_path(root) / DIR_DE_ADR
        destino.mkdir(parents=True, exist_ok=True)
        arquivo = destino / f"ADR-{decisao.id}.md"
        arquivo.write_text(generate_adr(decisao), encoding="utf-8")
        return str(arquivo)
    except Exception as exc:
        erros.append(_erro("adr", decisao.id, exc))
        return None


def _ids_existentes(root: Path | str) -> dict[str, set[str]]:
    """Os ids que ja estao no blackboard, por tipo."""
    return {
        "claim": {str(r.get("id")) for r in read_claims(root)},
        "evidence": {str(r.get("id")) for r in read_evidence(root)},
        "contradiction": {str(r.get("id")) for r in read_contradictions(root)},
        "objection": {str(r.get("id")) for r in read_objections(root)},
        "unknown": {str(r.get("id")) for r in read_unknowns(root)},
        "experiment": {str(r.get("id")) for r in read_experiments(root)},
        "decision": {str(r.get("id")) for r in read_decisions(root)},
    }


def _ultima_claim_por_afirmacao(root: Path | str) -> dict[tuple[str, str], str]:
    """A ultima claim gravada de cada `(claimant, statement)`.

    E o alvo de `supersedes`: a mesma regra afirmando a mesma coisa sobre o
    mesmo sujeito, agora com evidencia diferente, e REVISAO -- e a linhagem
    aponta para a versao mais recente, nao para a primeira. Encadear a partir da
    primeira faria a segunda revisao apontar para uma versao que a primeira ja
    havia substituido.
    """
    ultima: dict[tuple[str, str], str] = {}
    for registro in read_claims(root):
        chave = (str(registro.get("claimant") or ""), str(registro.get("statement") or ""))
        identificador = str(registro.get("id") or "")
        if identificador:
            ultima[chave] = identificador
    return ultima


def _erro(tipo: str, alvo: str, exc: Exception) -> dict[str, str]:
    """A falha, nomeada. Tipo, alvo, classe do erro e mensagem.

    Engolir a excecao em silencio seria o outro extremo da regra 27: o produto
    sairia inteiro e a lacuna deixaria de ser conferivel.
    """
    return {
        "entity": tipo,
        "target": alvo,
        "error": type(exc).__name__,
        "message": str(exc),
    }


# --------------------------------------------------------------------------
# Insumos
# --------------------------------------------------------------------------


def _facts_unicos(facts: list[dict]) -> list[dict]:
    """Os facts do case, sem `id` repetido e na ordem de entrada.

    O mesmo `fact.id` duas vezes e UMA medida -- o id e content-addressed sobre
    kind, subject e measures. Conta-lo duas vezes produziria dois `Unknown`
    identicos para uma lacuna so, e no blackboard o segundo seria recusado como
    duplicata.
    """
    vistos: set[str] = set()
    unicos: list[dict] = []
    for fact in _iteravel(facts):
        if not isinstance(fact, dict):
            continue
        fact_id = str(fact.get("id") or "").strip()
        if fact_id and fact_id in vistos:
            continue
        if fact_id:
            vistos.add(fact_id)
        unicos.append(fact)
    return unicos


def _acoes_por_regra(findings: list[dict]) -> dict[str, dict[str, Any]]:
    """O bloco `action` de cada regra, com o PRIMEIRO visto valendo.

    Duas ocorrencias da mesma regra sao dois findings e uma acao so -- a mesma
    leitura que `ordering.order_actions` faz.
    """
    acoes: dict[str, dict[str, Any]] = {}
    for finding in findings:
        rule_id = str(finding.get("rule_id") or "").strip()
        acao = finding.get("action")
        if rule_id and isinstance(acao, dict) and acao and rule_id not in acoes:
            acoes[rule_id] = acao
    return acoes


def _ancoras_por_regra(findings: list[dict]) -> dict[str, list[str]]:
    """Os `fact.id` que cada regra declara, deduplicados na ordem de aparicao."""
    ancoras: dict[str, list[str]] = defaultdict(list)
    for finding in findings:
        rule_id = str(finding.get("rule_id") or "").strip()
        if not rule_id:
            continue
        for bruto in finding.get("evidence") or []:
            fact_id = str(bruto).strip()
            if fact_id and fact_id not in ancoras[rule_id]:
                ancoras[rule_id].append(fact_id)
    return dict(ancoras)


def _ancoras_em_texto(ancoras: list[str] | None) -> str:
    """As ancoras como texto, ou a recusa nomeada quando nao ha nenhuma."""
    return ", ".join(ancoras) if ancoras else "nenhuma ancora declarada"


def _iteravel(valor: Any) -> list[Any]:
    """A lista recebida, ou `[]` quando o caller mandou `None` ou outra coisa."""
    return list(valor) if isinstance(valor, (list, tuple)) else []
