"""Árbitro do protocolo de debate: valida e RECUSA. Não gera argumento.

O §27 do prompt de origem pede o protocolo
`OBSERVE → HYPOTHESIZE → CHALLENGE → EVIDENCE → REBUTTAL → CONSENSUS →
VERIFICATION`, e fecha com a frase que decide o desenho deste módulo:

    "Nenhum agente pode declarar root cause final apenas com hipótese.
     O Coordinator precisa exigir evidence."

## O que este módulo é, e o que ele NÃO é

**Ele não é o executor de debate, e o executor continua não existindo.** A regra
29 do `CLAUDE.md` diz isso, e a regra 23 diz por quê: nada em `sparkforge/`
chama provider nenhum. Gerar argumento, objeção e réplica exige um modelo, e
quem executa modelo é o host. Um "executor de debate" aqui teria de inventar as
falas, e falas inventadas não são debate — são texto.

**Ele é o árbitro**, e é essa a metade que se constrói sem provider: dado um
`Debate` cujas rodadas o host já preencheu, decidir DETERMINISTICAMENTE se o
protocolo foi respeitado e se um veredito declarado se sustenta. A garantia que o
§27 pede é uma RECUSA — "não pode declarar com hipótese" —, e recusa é
verificação, não geração.

A analogia é `judge`: ele não escreve o código do job, ele julga o que outro
extraiu. Aqui é o mesmo degrau, um nível acima.

## As quatro violações que ele nomeia

1. **Fechamento sobre hipótese.** Claim de `claim_type=HYPOTHESIS` sobrevivendo a
   um fechamento. É **literalmente** a frase do §27 — "nenhum agente pode
   declarar root cause final apenas com hipótese" —, e ela é mais estreita que a
   violação seguinte: uma hipótese com `evidence_refs` continua sendo hipótese.
   `ClaimType` já distinguia `observation`, `inference`, `hypothesis` e
   `recommendation`; nada lia essa distinção até aqui.
2. **Consenso sem evidência.** Claim sobrevivente cujo `evidence_refs` está
   vazio, de qualquer tipo. É a segunda metade da frase do §27: "o Coordinator
   precisa exigir evidence". Uma `inference` desancorada cai aqui e não em (1).
3. **Consenso sobre objeção viva.** Uma objeção sem réplica, e o debate declarado
   fechado. Consenso não é silêncio: é objeção respondida.
4. **Réplica órfã.** `Rebuttal.target_objection` que não existe em nenhuma
   rodada, ou `Objection.target_claim` que não existe. Referência pendurada é o
   modo de falha que faz um debate parecer completo sem ser.

## O que ele declara não medir

**`VERIFICATION` — o sétimo estágio — não tem campo no modelo.** `Debate` guarda
`verdict` como texto livre, e nada nele diz que o veredito foi VERIFICADO contra
execução. Este árbitro reporta o estágio como `not_modeled` em vez de assumir que
consenso é verificação: são coisas diferentes, e confundi-las publicaria como
verificado o que só foi acordado.

**`OBSERVE` também não tem campo**, e por uma razão diferente: ele acontece antes
do debate, nos facts que `judge` consumiu. O árbitro o marca `external`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.agentic.debate import Debate, DebateStatus

# Os sete estágios do §27, com o que os observa neste modelo de dados. A tupla é
# a ordem do protocolo, e ela é publicada na resposta para que o leitor veja
# quais estágios existem como DADO e quais não.
ESTAGIOS: tuple[tuple[str, str], ...] = (
    ("OBSERVE", "external"),
    ("HYPOTHESIZE", "DebateRound.claims"),
    ("CHALLENGE", "DebateRound.objections"),
    ("EVIDENCE", "Claim.evidence_refs / Objection.evidence_refs"),
    ("REBUTTAL", "DebateRound.rebuttals"),
    ("CONSENSUS", "Debate.status"),
    ("VERIFICATION", "not_modeled"),
)

# Os status que afirmam fechamento. `RESOLVED` entra junto com `CONSENSUS`: a
# arbitragem também fecha, e um veredito de arbitragem sem evidência tem o mesmo
# defeito de um de consenso sem evidência.
_STATUS_QUE_FECHAM = frozenset({DebateStatus.CONSENSUS, DebateStatus.RESOLVED})

VIOLACAO_HIPOTESE_FINAL = "fechamento_sobre_hipotese"
VIOLACAO_SEM_EVIDENCIA = "consenso_sem_evidencia"
VIOLACAO_OBJECAO_VIVA = "consenso_sobre_objecao_viva"
VIOLACAO_REFERENCIA_PENDURADA = "referencia_pendurada"


def _indice(debate: Debate) -> tuple[dict[str, Any], dict[str, Any], list[Any]]:
    """`(claims_por_id, objecoes_por_id, replicas)` achatados sobre as rodadas.

    O protocolo atravessa rodadas: uma objeção da rodada 1 pode receber réplica
    na rodada 2, e validar rodada a rodada perderia exatamente o caso que o
    debate existe para permitir.
    """
    claims: dict[str, Any] = {}
    objecoes: dict[str, Any] = {}
    replicas: list[Any] = []
    for rodada in debate.rounds:
        for claim in rodada.claims:
            claims[claim.id] = claim
        for objecao in rodada.objections:
            objecoes[objecao.id] = objecao
        replicas.extend(rodada.rebuttals)
    return claims, objecoes, replicas


def _superseded(claims: dict[str, Any]) -> frozenset[str]:
    """Claims que outra claim declara substituir, por `supersedes`.

    Claim substituída não é "sobrevivente": cobrar evidência dela puniria o
    debate por ter funcionado -- revisar a própria posição é o que o estágio de
    REVISION existe para permitir.
    """
    return frozenset(
        str(claim.supersedes) for claim in claims.values() if getattr(claim, "supersedes", "")
    )


def referee_verdict(debate: Debate) -> dict[str, Any]:
    """Valida o protocolo de um `Debate` e diz se o fechamento se sustenta.

    NÃO gera argumento, NÃO estima confiança e NÃO conclui debate nenhum: só
    responde se o que o host preencheu respeita o protocolo, e recusa o
    fechamento quando não.

    `upheld` é `False` quando há violação. Ele não é uma nota: é a resposta à
    pergunta "este veredito pode ser publicado?".
    """
    claims, objecoes, replicas = _indice(debate)
    saida = _arbitrar(
        claims,
        objecoes,
        replicas,
        fecha=debate.status in _STATUS_QUE_FECHAM,
        rodadas=len(debate.rounds),
    )
    saida["debate_id"] = debate.id
    saida["topic"] = debate.topic
    saida["status_declared"] = debate.status.value
    saida["source"] = "Debate"
    return saida


def _arbitrar(
    claims: dict[str, Any],
    objecoes: dict[str, Any],
    replicas: list[Any],
    fecha: bool,
    rodadas: int,
) -> dict[str, Any]:
    """O núcleo, sobre as três coleções e um booleano de fechamento.

    Separado de `referee_verdict` porque o blackboard NÃO guarda um `Debate`: ele
    guarda claims, objeções e réplicas em JSONL, e o que faz papel de "consenso
    declarado" ali é existir uma `Decision` registrada. Duplicar a validação para
    a segunda forma de entrada seria a mesma família de defeito que
    `ORDEM_DE_SEVERIDADE` teve por um dia -- duas cópias do mesmo julgamento.
    """
    substituidas = _superseded(claims)
    respondidas = {
        str(r.target_objection) for r in replicas if getattr(r, "target_objection", "")
    }

    violacoes: list[dict[str, Any]] = []

    # 1) referência pendurada -- vale em QUALQUER status, porque é defeito de
    #    forma e não de conclusão.
    for objecao in objecoes.values():
        alvo = str(getattr(objecao, "target_claim", ""))
        if alvo and alvo not in claims:
            violacoes.append(
                {
                    "kind": VIOLACAO_REFERENCIA_PENDURADA,
                    "what": f"objecao {objecao.id} aponta claim {alvo}, que nao existe",
                    "unblocked_by": "corrigir `target_claim`, ou incluir a claim numa rodada",
                }
            )
    for replica in replicas:
        alvo = str(getattr(replica, "target_objection", ""))
        if alvo and alvo not in objecoes:
            violacoes.append(
                {
                    "kind": VIOLACAO_REFERENCIA_PENDURADA,
                    "what": f"replica de {replica.rebuttal_by} aponta objecao {alvo}, "
                    f"que nao existe",
                    "unblocked_by": "corrigir `target_objection`, ou incluir a objecao",
                }
            )

    # 2) consenso sem evidencia -- A FRASE DO §27, e ela só se cobra no
    #    fechamento: durante o debate uma hipótese sem evidência é legítima.
    sobreviventes = [c for cid, c in claims.items() if cid not in substituidas]
    if fecha:
        # 2a) A FRASE DO §27, ao pe da letra: hipotese nao fecha root cause. E
        #     mais estreita que a checagem de evidencia logo abaixo -- hipotese
        #     COM `evidence_refs` continua sendo hipotese, e cai aqui.
        for claim in sobreviventes:
            if getattr(claim.claim_type, "value", str(claim.claim_type)) == "hypothesis":
                violacoes.append(
                    {
                        "kind": VIOLACAO_HIPOTESE_FINAL,
                        "what": f"claim de {claim.claimant} sobrevive ao fechamento como "
                        f"HIPOTESE: {claim.statement[:120]!r}",
                        "unblocked_by": (
                            "confirmar a hipotese e reclassifica-la como `observation` ou "
                            "`inference`, ou fechar como `deadlocked` com o experimento que "
                            "a decidiria"
                        ),
                    }
                )

        for claim in sobreviventes:
            if not list(getattr(claim, "evidence_refs", []) or []):
                violacoes.append(
                    {
                        "kind": VIOLACAO_SEM_EVIDENCIA,
                        "what": f"claim de {claim.claimant} sobrevive ao fechamento sem "
                        f"`evidence_refs`: {claim.statement[:120]!r}",
                        "unblocked_by": "ancorar a claim num fact, ou retira-la antes de fechar",
                    }
                )

        # 3) objecao viva
        for objecao in objecoes.values():
            if objecao.id not in respondidas:
                violacoes.append(
                    {
                        "kind": VIOLACAO_OBJECAO_VIVA,
                        "what": f"objecao de {objecao.objector} sem replica: "
                        f"{objecao.statement[:120]!r}",
                        "unblocked_by": "responder a objecao, ou fechar como `deadlocked`",
                    }
                )

    return {
        # A resposta, e ela é binária de propósito: o §27 pede uma recusa, e
        # recusa graduada não recusa.
        "upheld": not violacoes,
        "violations": violacoes,
        "violation_count": len(violacoes),
        "protocol": [
            {"stage": nome, "observed_in": fonte, "modeled": fonte != "not_modeled"}
            for nome, fonte in ESTAGIOS
        ],
        "counts": {
            "rounds": rodadas,
            "claims": len(claims),
            "claims_surviving": len(sobreviventes),
            "claims_superseded": len(substituidas),
            "objections": len(objecoes),
            "objections_answered": len(respondidas & set(objecoes)),
            "rebuttals": len(replicas),
        },
        "refused": [
            {
                "what": "generate_debate",
                "why": (
                    "Gerar claim, objecao e replica exige provider, e nada em "
                    "`sparkforge/` chama provider (regra 23 do CLAUDE.md). Este modulo "
                    "ARBITRA o que o host preencheu."
                ),
                "unblocked_by": "um `AgentRuntime` concreto, que mora fora deste pacote",
            },
            {
                "what": "verification_stage",
                "why": (
                    "O setimo estagio do §27 nao tem campo no modelo: `Debate.verdict` e "
                    "texto livre, e nada nele diz que o veredito foi verificado contra "
                    "execucao. Consenso e acordo, nao verificacao."
                ),
                "unblocked_by": (
                    "um campo que ligue o veredito a um run posterior -- no molde do "
                    "`benchmark_ref` que `validate_output` ja cobra para ganho"
                ),
            },
            {
                "what": "confidence_score",
                "why": (
                    "Nenhum experimento calibrou peso nenhum neste repositorio. `upheld` e "
                    "binario e vem de contagem de violacao, nunca de nota."
                ),
                "unblocked_by": "",
            },
        ],
    }

# --------------------------------------------------------------------------- #
# A segunda forma de entrada: o blackboard que `arbitrate` escreve.
# --------------------------------------------------------------------------- #

# Chaves de id nos registros JSONL do blackboard. `_append_jsonl` grava o dict
# da entidade mais o `id`, e e por ele que objecao e replica se ligam.
_ID = "id"


class _Registro:
    """Adaptador de dict JSONL para a interface que `_arbitrar` espera.

    Ele existe para que o nucleo NAO saiba se a entrada veio de um `Debate` em
    memoria ou de linha de JSONL. Sem ele, `_arbitrar` teria dois caminhos de
    leitura e a validacao poderia divergir entre as duas -- que e exatamente o
    defeito de duas copias do mesmo julgamento.
    """

    def __init__(self, bruto: dict[str, Any]) -> None:
        self._bruto = bruto

    def __getattr__(self, nome: str) -> Any:
        valor = self._bruto.get(nome)
        if nome == "claim_type" and isinstance(valor, str):
            return valor
        return valor if valor is not None else ""

    @property
    def id(self) -> str:
        return str(self._bruto.get(_ID, ""))


def referee_over_blackboard(root: Path | str) -> dict[str, Any]:
    """Arbitra o que `sparkforge arbitrate` escreveu no blackboard do case.

    **O que faz papel de "consenso declarado" aqui e existir uma `Decision`
    registrada**, e nao um campo de status: o blackboard nao guarda `Debate`, ele
    guarda entidades em JSONL. Uma decisao gravada afirma fechamento tanto quanto
    `status=CONSENSUS` afirma -- e por isso as mesmas quatro violacoes valem.

    Blackboard vazio devolve `upheld: True` com `closed: false` e a contagem em
    zero. Nao e aprovacao: e a resposta honesta para "nada a arbitrar". O campo
    `closed` e o que separa os dois casos, e ele sai sempre.
    """
    from sparkforge.agentic import blackboard as bb

    claims = {r[_ID]: _Registro(r) for r in bb.read_claims(root) if r.get(_ID)}
    objecoes = {r[_ID]: _Registro(r) for r in bb.read_objections(root) if r.get(_ID)}
    replicas = [_Registro(r) for r in bb.read_rebuttals(root)]
    decisoes = bb.read_decisions(root)

    saida = _arbitrar(claims, objecoes, replicas, fecha=bool(decisoes), rodadas=0)
    saida["source"] = "blackboard"
    saida["closed"] = bool(decisoes)
    saida["decision_count"] = len(decisoes)
    # `rounds: 0` no blackboard nao e "nenhuma rodada": e "o blackboard nao
    # guarda rodada". Nomear isso evita que a contagem seja lida como debate que
    # nao aconteceu.
    saida["counts"]["rounds"] = None
    saida["counts"]["rounds_note"] = "o blackboard nao modela rodada; use `Debate` para isso"
    return saida
