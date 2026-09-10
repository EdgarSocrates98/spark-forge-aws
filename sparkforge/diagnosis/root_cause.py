"""Ordena os achados por consequencia e NOMEIA a lacuna. Nao inventa confianca.

O §24 do prompt de origem pede sete campos por candidato de causa raiz:
`ROOT CAUSE`, `CONFIDENCE`, `EVIDENCE`, `MISSING EVIDENCE`, `REMEDIATION`,
`SECURITY IMPACT`, `VERSION IMPACT`. Seis tem produtor neste repositorio. O
setimo -- `CONFIDENCE` -- tem produtor com uma ressalva que este modulo carrega
por escrito em vez de esconder.

## O que este modulo NAO faz, e e a metade que importa

**Nao calcula confianca.** `Finding.confidence` e campo DECLARADO por regra
(`high`, `medium`, `low`), com um significado publicado: os `low` sao a lista de
onde falta medida ou fonte. Ele nao e probabilidade, nao foi calibrado por
experimento nenhum, e nao muda de case para case. Este modulo o repassa como
`confidence_declared` -- o nome carrega a ressalva -- e NUNCA o combina com
severidade ou contagem de evidencia para produzir um numero novo. Os pesos de
`assess_claim` na arbitragem sao convencao e o `CLAUDE.md` proibe publica-los
como confianca medida; inventar aqui um segundo score seria o mesmo defeito com
outro nome.

**Nao e ranking por probabilidade.** A saida e uma ORDEM, e a chave dela e
declarada e deterministica: severidade primeiro (P0 antes de P1 antes de P2),
depois a QUANTIDADE de facts que ancoram o achado, depois `rule_id` para
desempate estavel. Nenhuma das tres e "chance de ser a causa" -- a primeira e a
consequencia que a regra declara, a segunda e quanto artefato sustenta o achado,
e a terceira existe so para a saida nao depender da ordem de entrada.

**Nao estima impacto de seguranca.** `security_posture` e classificacao por
NAMESPACE do `action.kind` -- `security.*` toca controle de acesso, o resto nao
esta indicado --, e ela vem acompanhada do `risks` da propria regra, verbatim.
Onde o raio da mudanca excede o job, quem diz e o texto da regra, nao este
modulo.

## O que ele acrescenta, e nao existia

`missing_evidence` e a metade que nenhum verbo publicava. Ela tem duas fontes,
as duas medidas:

  1. os facts `*.unresolved` -- lacuna que o proprio extrator nomeou, com
     `attrs.reason` e `attrs.unblocked_by` quando ele os declarou;
  2. as regras PULADAS por `requires_facts`, com o kind que falta E o modulo que
     o emite -- descoberto por varredura de `EMITTED_KINDS`, nunca por lista
     escrita a mao.

A segunda e o que transforma "esta regra nao disparou" em "colete isto e ela
dispara". Sem ela, silencio por falta de artefato e indistinguivel de silencio
por ausencia de defeito.
"""
from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable, Sequence
from functools import lru_cache
from typing import Any

from sparkforge.findings.models import SEVERITY_ORDER, Fact, Finding

# A ordem de gravidade, REUSADA de `sparkforge/findings/models.py` em vez de
# reescrita. A primeira versao deste modulo a declarou a mao como `P0..P3`, e o
# efeito era silencioso e errado: `Finding.__post_init__` valida `P0..P4`, entao
# um achado `P4` legitimo caia no balde de "severidade desconhecida" e ia para o
# FIM da ordem. Duas listas para o mesmo vocabulario e o defeito, e nao a
# divergencia entre elas -- a divergencia foi so o sintoma.
#
# `P0` e o pior. Severidade fora do vocabulario cai no fim e nao no comeco:
# ordenar um valor desconhecido como o mais grave faria a saida mentir na
# primeira linha, que e a que alguem le.
ORDEM_DE_SEVERIDADE: tuple[str, ...] = SEVERITY_ORDER

# O namespace de `action.kind` que toca controle de acesso. Classificacao por
# PREFIXO, e nada mais: ela responde "esta mudanca mexe em postura de seguranca?"
# e nao "qual e o impacto dela".
_NAMESPACE_DE_SEGURANCA = "security."

# Sufixo dos kinds de recusa. Todo extrator deste repositorio publica lacuna
# assim (regra 20 do `CLAUDE.md`), e e por isso que a varredura pode ser por
# sufixo em vez de lista.
_SUFIXO_DE_RECUSA = ".unresolved"


@lru_cache(maxsize=1)
def _modulo_por_kind() -> dict[str, str]:
    """`kind -> nome do modulo que o emite`, por varredura de `EMITTED_KINDS`.

    Varredura e nao lista: uma lista escrita a mao ficaria para tras do primeiro
    extrator novo, e o sintoma seria um `missing_evidence` sem dono -- pior que
    nao ter o campo, porque parece completo.

    `matcher` mora em `sparkforge/errors/` e nao em `sparkforge/facts/`, entao a
    varredura por diretorio nao o alcanca. Ele entra nomeado, e este e o mesmo
    recorte que `tests/test_rules_catalog_reachability.py` documenta.
    """
    from sparkforge import facts as pacote_de_facts

    mapa: dict[str, str] = {}

    def registrar(nome: str, modulo: Any) -> None:
        kinds = getattr(modulo, "EMITTED_KINDS", None)
        if not kinds:
            return
        for kind in kinds:
            mapa.setdefault(str(kind), nome)

    for info in pkgutil.iter_modules(pacote_de_facts.__path__):
        # O `except` engole de proposito, e a razao e a regra 27 do `CLAUDE.md`:
        # medicao nunca derruba a chamada. Um extrator que nao importa -- extra
        # opcional nao instalado, por exemplo -- nao tem kind a mapear, e
        # derrubar `root_cause` inteiro por isso trocaria a resposta do operador
        # por um traceback. O custo e um kind sem dono no `emitted_by`, e o campo
        # sai `""` dizendo isso.
        try:
            modulo = importlib.import_module(f"sparkforge.facts.{info.name}")
        except Exception:  # noqa: BLE001,S112 - ver comentario acima
            continue
        registrar(info.name, modulo)

    try:
        from sparkforge.errors import matcher

        registrar("errors.matcher", matcher)
    except Exception:  # noqa: BLE001,S110 - mesma razao do laco acima
        pass
    return mapa


def _ordem(finding: Finding) -> tuple[int, int, str]:
    severidade = str(finding.severity or "")
    posicao = (
        ORDEM_DE_SEVERIDADE.index(severidade)
        if severidade in ORDEM_DE_SEVERIDADE
        else len(ORDEM_DE_SEVERIDADE)
    )
    # `-len(evidence)`: mais facts ancorando vem primeiro DENTRO da mesma
    # severidade. Nao e "mais provavel" -- e mais artefato sustentando.
    return (posicao, -len(finding.evidence or []), str(finding.rule_id or ""))


def _postura_de_seguranca(finding: Finding) -> dict[str, Any]:
    acao = finding.action or {}
    kind = str(acao.get("kind") or "")
    toca = kind.startswith(_NAMESPACE_DE_SEGURANCA)
    return {
        # Dois valores, e o segundo NAO e "nao toca": e "nao indicado pelo
        # namespace da acao". A diferenca e a mesma de `not_declared` contra
        # `not_supported` na matriz de versao.
        "classification": "touches_access_control" if toca else "not_indicated",
        "action_kind": kind,
        "basis": "namespace do `action.kind`, e nao avaliacao de impacto",
        # O raio real, quando a regra o conhece, esta no texto dela. Repassado
        # verbatim: resumi-lo seria escrever a avaliacao que este modulo recusa.
        "rule_declared_risks": list(finding.risks or []),
    }


def _impacto_de_versao(finding: Finding, runtime: dict[str, str]) -> dict[str, Any]:
    escopo = dict(finding.runtime_scope or {})
    if not escopo:
        return {
            "scope": {},
            # `{}` e afirmacao e nao omissao: a regra declara que o defeito nao
            # depende de fronteira de versao. Ver a secao ESCOPO do cabecalho de
            # `rules/catalog/iceberg.yaml`.
            "reading": "a regra declara que nao depende de fronteira de versao",
            "runtime_observed": dict(runtime),
        }
    return {
        "scope": escopo,
        "reading": "a regra so se aplica dentro deste recorte de versao",
        "runtime_observed": dict(runtime),
    }


def _evidencia(finding: Finding, por_id: dict[str, Fact]) -> list[dict[str, Any]]:
    saida: list[dict[str, Any]] = []
    for fact_id in finding.evidence or []:
        fact = por_id.get(fact_id)
        if fact is None:
            # Achado que cita fact ausente do conjunto e defeito de chamador --
            # o mesmo que `validate_output` cobra para `benchmark_ref`. Nomeado
            # em vez de silenciado.
            saida.append({"fact_id": fact_id, "kind": "", "anchor": "", "status": "ausente"})
            continue
        subject = fact.subject or {}
        saida.append(
            {
                "fact_id": fact_id,
                "kind": fact.kind,
                "anchor": str(subject.get("symbol") or subject.get("file") or ""),
                "status": "presente",
            }
        )
    return saida


def _lacuna_dos_extratores(facts: Sequence[Fact]) -> list[dict[str, Any]]:
    """As recusas que os proprios extratores nomearam."""
    saida: list[dict[str, Any]] = []
    for fact in facts:
        if not fact.kind.endswith(_SUFIXO_DE_RECUSA):
            continue
        attrs = fact.attrs or {}
        saida.append(
            {
                "source": "extractor_refusal",
                "kind": fact.kind,
                "reason": str(attrs.get("reason") or ""),
                "unblocked_by": str(attrs.get("unblocked_by") or ""),
                "fact_id": fact.id,
            }
        )
    return sorted(saida, key=lambda item: (item["kind"], item["reason"], item["fact_id"]))


def _area(rule_id: str) -> str:
    """`SF-LF-003` -> `SF-LF`. Prefixo ate o ULTIMO hifen.

    A conta importa: `SF-EMR` e prefixo de `SF-EMRS` e de `SF-EMRK`, e comparar
    por `startswith` mediria a fronteira ao contrario -- o mesmo cuidado que o
    `README.md` documenta ao dizer "conte area com `area_of`, nunca somando lista
    escrita a mao".
    """
    partes = rule_id.rsplit("-", 1)
    return partes[0] if len(partes) == 2 else rule_id


def _lacuna_das_regras_puladas(
    skipped: Iterable[dict[str, Any]],
    areas_em_jogo: frozenset[str],
    todas: bool,
) -> tuple[list[dict[str, Any]], int]:
    """`(listadas, total)` das regras nao avaliadas por falta de kind.

    So `reason: requires_facts` entra. `runtime_scope` e `blocked_on` sao
    silencios de natureza diferente e nao se consertam coletando artefato: o
    primeiro diz que a regra nao se aplica a este runtime, o segundo que a
    capacidade nao existe ainda.

    O FILTRO POR AREA existe porque o total nao e leitura util. Num case de um
    artefato so, quase todo o catalogo fica pulado por `requires_facts` -- medido:
    130 num case de Terraform sozinho --, e uma lista de 130 itens esconde os dois
    que importam. O recorte e a AREA que ja tem achado: se `SF-LF` disparou, saber
    quais outras `SF-LF` ficaram mudas por falta de artefato e acionavel; saber
    que `SF-ATH-001` precisa de SQL que este case nao tem, nao e.

    O TOTAL SAI SEMPRE, ao lado da lista, e `todas=True` devolve tudo. Publicar a
    lista sem o total faria o recorte parecer o conjunto.
    """
    mapa = _modulo_por_kind()
    completa: list[dict[str, Any]] = []
    for item in skipped or []:
        if item.get("reason") != "requires_facts":
            continue
        rule_id = str(item.get("rule_id") or "")
        faltando = list(item.get("missing") or [])
        completa.append(
            {
                "source": "rule_not_evaluated",
                "rule_id": rule_id,
                "area": _area(rule_id),
                "missing_kinds": faltando,
                "emitted_by": {kind: mapa.get(kind, "") for kind in faltando},
            }
        )
    completa.sort(key=lambda item: item["rule_id"])
    if todas:
        return completa, len(completa)
    recortada = [item for item in completa if item["area"] in areas_em_jogo]
    return recortada, len(completa)


def rank_root_causes(
    facts: Sequence[Fact],
    findings: Sequence[Finding],
    skipped: Iterable[dict[str, Any]] | None = None,
    runtime: dict[str, str] | None = None,
    all_missing: bool = False,
) -> dict[str, Any]:
    """Ordena os achados por consequencia declarada e nomeia a lacuna.

    Nao produz achado novo, nao le artefato, nao calcula confianca e nao estima
    ganho. A ordem e declarada em `ordering`, junto com a frase que diz o que ela
    NAO e.
    """
    runtime = dict(runtime or {})
    por_id = {fact.id: fact for fact in facts}

    candidatos: list[dict[str, Any]] = []
    for posicao, finding in enumerate(sorted(findings, key=_ordem), start=1):
        candidatos.append(
            {
                "position": posicao,
                "root_cause": finding.title,
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                # O nome carrega a ressalva. Ver o docstring do modulo.
                "confidence_declared": finding.confidence,
                "status": finding.status,
                "subject": dict(finding.subject or {}),
                "evidence": _evidencia(finding, por_id),
                "evidence_count": len(finding.evidence or []),
                "remediation": list(finding.proposed_change or []),
                "security_posture": _postura_de_seguranca(finding),
                "version_impact": _impacto_de_versao(finding, runtime),
                "validation": list(finding.validation or []),
                "rollback": list(finding.rollback or []),
            }
        )

    areas_em_jogo = frozenset(_area(str(f.rule_id or "")) for f in findings)
    recusas = _lacuna_dos_extratores(facts)
    puladas, total_de_puladas = _lacuna_das_regras_puladas(
        skipped or [], areas_em_jogo, all_missing
    )
    lacunas = recusas + puladas

    return {
        "status": "ok",
        "candidate_count": len(candidatos),
        "candidates": candidatos,
        "missing_evidence": lacunas,
        "missing_evidence_count": len(lacunas),
        # O recorte declarado, e o total ao lado dele. Sem os dois numeros lado a
        # lado, a lista recortada seria lida como o conjunto.
        "missing_evidence_scope": {
            "extractor_refusals": len(recusas),
            "rules_not_evaluated_listed": len(puladas),
            "rules_not_evaluated_total": total_de_puladas,
            "areas_in_play": sorted(areas_em_jogo),
            "filter": (
                "todas as areas"
                if all_missing
                else "so as areas que ja tem achado; use `all_missing` para o resto"
            ),
        },
        "ordering": {
            "key": ["severity", "evidence_count_desc", "rule_id"],
            "severity_order": list(ORDEM_DE_SEVERIDADE),
            # A frase existe para nao ser lida como probabilidade, e ela e a
            # mesma recusa que o `CLAUDE.md` faz do score de arbitragem.
            "is_not": (
                "Esta e uma ORDEM por consequencia declarada, nao um ranking por "
                "probabilidade. `confidence_declared` e campo da REGRA, nao medida "
                "deste case, e nenhum numero novo e calculado a partir dele."
            ),
        },
        "refused": [
            {
                "what": "confidence_score",
                "why": (
                    "Nenhum experimento calibrou peso nenhum neste repositorio. "
                    "`confidence_declared` e repassado como declarado pela regra."
                ),
                "unblocked_by": (
                    "Um experimento que meça acerto por regra sobre um corpus de "
                    "casos com causa conhecida."
                ),
            },
            {
                "what": "security_impact_assessment",
                "why": (
                    "`security_posture` classifica pelo NAMESPACE do `action.kind` "
                    "e repassa o `risks` da regra verbatim. Avaliar impacto exige "
                    "conhecer o raio da mudança na conta, que nenhum artefato deste "
                    "motor carrega."
                ),
                "unblocked_by": (
                    "Um campo declarado por regra dizendo o raio da ação, ou a "
                    "coleta da política da organização."
                ),
            },
            {
                "what": "expected_gain",
                "why": "Exige o custo do run que não aconteceu (regra 13 do CLAUDE.md).",
                "unblocked_by": "",
            },
        ],
    }
