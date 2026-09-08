"""Findings julgados viram `Claim`; os facts que os ancoram viram `Evidence`.

Este e o degrau que liga o motor deterministico a camada agentica, e ele nao
inventa nada: cada `Claim` sai de um `Finding` que `judge` ja produziu, e cada
`Evidence` sai de uma URL que a regra ja citava em `sources:`.

## As duas perguntas que nao se fundem

- `Evidence.authority` gradua a FONTE que sustenta o limiar da regra, pelo host
  declarado em `knowledge/source_authority.yaml`;
- `Evidence.measurement_ref` nomeia a MEDIDA que casou com o `when` da regra.

Os tiers T1-T6 graduam fonte de conhecimento, e nao existe tier para medida do
artefato do cliente. Fundir os dois num tier so produziria um numero que nao
mede nada -- a secao 3.4 do spec nomeia a lacuna em vez de resolve-la por
invencao.

## De onde o `confidence` vem, e de onde ele NAO vem

Ele NAO vem do score de `assess_claim`. O `CLAUDE.md` declara que os pesos
daquele score (evidencia 40%, autoridade 30%, especificidade 20%,
aplicabilidade 10%) sao convencao e que nenhum experimento os calibrou: eles
ordenam claims dentro de uma arbitragem, e o valor absoluto nao e confianca
medida. Publicar um numero de convencao como confianca seria exatamente o que a
regra 11 separa -- limiar e regra, valor proposto e escolha, e nenhum dos dois
vira medida por ser impresso com duas casas decimais.

O `confidence` vem de `confidence_for`, que e tabela conferivel campo a campo.
"""

from __future__ import annotations

from typing import Any

from sparkforge.agentic.executor.authority import in_scope, tier_for_url
from sparkforge.agentic.models import Claim, ClaimType, Evidence, EvidenceAuthority

# Ordem de forca, do mais forte para o mais fraco. Escrita explicita em vez de
# derivada da ordem de declaracao do enum: o enum e serializacao, e depender da
# ordem dele faria um membro novo inserido no meio mudar em silencio qual fonte
# ganha de qual.
_ORDEM_DE_TIER: tuple[EvidenceAuthority, ...] = (
    EvidenceAuthority.T1_OFFICIAL_DOCS,
    EvidenceAuthority.T2_SOURCE_CODE,
    EvidenceAuthority.T3_REPRODUCIBLE_BENCHMARK,
    EvidenceAuthority.T4_RECOGNIZED_AUTHORITY,
    EvidenceAuthority.T5_LLM_KNOWLEDGE,
    EvidenceAuthority.T6_CONJECTURE,
)

# Os dois tiers que a tabela nomeia como "fonte de referencia vigente".
_TIERS_DE_REFERENCIA = frozenset(
    {EvidenceAuthority.T1_OFFICIAL_DOCS, EvidenceAuthority.T2_SOURCE_CODE}
)

# "T4 ou pior", literalmente o que a tabela diz.
_TIERS_FRACOS = frozenset(
    {
        EvidenceAuthority.T4_RECOGNIZED_AUTHORITY,
        EvidenceAuthority.T5_LLM_KNOWLEDGE,
        EvidenceAuthority.T6_CONJECTURE,
    }
)


def confidence_for(
    tier: EvidenceAuthority,
    dentro_do_escopo: bool,
    medidas_presentes: bool,
) -> str:
    """A tabela de confianca, conferivel campo a campo.

    | `confidence` | condicao |
    |---|---|
    | `high` | T1/T2 vigente e no escopo de versao do case, medidas exigidas presentes |
    | `medium` | fonte com autoridade mas FORA do escopo de versao |
    | `low` | fonte T4 ou pior, OU medida exigida ausente |

    Tres decisoes que a tabela por si nao resolve, e que ficam declaradas aqui
    em vez de cairem por acidente num `else`:

    1. **A medida ausente decide primeiro.** Um finding que cita fact que nao
       veio nao esta ancorado, e o tier da fonte nao conserta isso: a fonte
       sustenta o LIMIAR, e o que falta e o lado medido da comparacao.
    2. **T3 sai `medium`.** Ele nao e "T1/T2 vigente" e nao e "T4 ou pior" --
       a tabela nao o nomeia. Fica no unico degrau que sobra. Hoje o ramo e
       inalcancavel por `claims_from_findings`, porque
       `knowledge/source_authority.yaml` nao emite T3 de proposito (host nao
       prova reprodutibilidade); ele existe para quem chamar `confidence_for`
       com um tier promovido a mao depois de reproduzir o benchmark.
    3. **"Nenhuma contradicao aberta" nao entra aqui.** A tabela do spec cita a
       condicao no ramo `high`, e esta funcao nao a recebe: contradicao e
       propriedade do CONJUNTO de findings, nao de um finding sozinho, e so o
       degrau de contradicao (secao 4 do spec) pode responde-la. Quem tiver a
       resposta rebaixa a claim depois; inventar aqui um `False` fixo diria
       "nao ha contradicao" sobre algo que esta funcao nunca olhou.
    """
    if not medidas_presentes:
        return "low"
    if tier in _TIERS_FRACOS:
        return "low"
    if tier in _TIERS_DE_REFERENCIA and dentro_do_escopo:
        return "high"
    return "medium"


def claims_from_findings(
    findings: list[dict],
    facts: list[dict],
    authority_map: dict,
    runtime: dict,
    created_at: str = "",
) -> tuple[list[Claim], list[Evidence]]:
    """Converte findings julgados em claims, e as fontes deles em evidencias.

    Um finding -> uma `Claim` de tipo `INFERENCE`. A claim afirma o DIAGNOSTICO
    derivado da medida, e nao a mudanca proposta: a mudanca mora em `action`,
    que e dado da regra e nao afirmacao do executor. Por isso `RECOMMENDATION`
    seria o tipo errado aqui -- ele viria depois, de uma `Decision`, e so
    quando o lastro da secao 5.2 do spec aprovar.

    Cada `sources[].url` -> uma `Evidence`, com `authority` do tier daquele host
    e `supports=[claim.id]`.

    Args:
        findings: findings ja julgados, no formato de `findings.json`.
        facts: facts do case, no formato de `facts.json`. So o `id` e lido.
        authority_map: saida de `load_authority_map`.
        runtime: o que o case mediu, ex. `{"glue": "5.0", "spark": "3.5.4"}`.
        created_at: ISO 8601 injetado pelo caller. Este modulo nao le relogio --
            gerar a hora aqui tornaria a saida irreprodutivel entre execucoes,
            e id content-addressed com hora dentro nao seria content-addressed.

    Returns:
        `(claims, evidences)`, na ordem dos findings de entrada.
    """
    ids_presentes = {
        str(f.get("id")) for f in (facts or []) if isinstance(f, dict) and f.get("id")
    }

    claims: list[Claim] = []
    evidences: list[Evidence] = []

    for finding in findings or []:
        rule_id = str(finding.get("rule_id") or "").strip()
        refs = _fact_ids_declarados(finding)

        # "Medida exigida presente" = todo id declarado pelo finding esta entre
        # os facts do case. Finding que nao declarou fact nenhum tambem cai aqui:
        # sem ancora nao ha o que conferir, e tratar a lista vazia como "todas
        # presentes" (que e o que `all([])` faz) daria alta confianca a uma
        # claim que nao mediu nada.
        medidas_presentes = bool(refs) and all(ref in ids_presentes for ref in refs)

        # `measurement_ref` e um campo so, e o finding pode declarar mais de um
        # fact. Nomeamos o PRIMEIRO declarado -- a ancora que a regra listou
        # primeiro -- e a lista inteira fica em `Claim.evidence_refs`. Juntar os
        # ids numa string composta produziria um ref que nao aponta para fact
        # nenhum, e o campo existe justamente para ser resolvivel.
        ancora = refs[0] if refs else ""

        escopo = finding.get("runtime_scope") or {}
        dentro = in_scope(escopo, runtime or {})

        fontes = _fontes_com_url(finding)
        tier = _melhor_tier(fontes, authority_map)

        claim = Claim(
            claimant=rule_id,
            claim_type=ClaimType.INFERENCE,
            statement=_statement(finding, rule_id),
            evidence_refs=refs,
            confidence=confidence_for(tier, dentro, medidas_presentes),
            created_at=created_at,
        )
        claims.append(claim)

        for fonte in fontes:
            evidences.append(
                Evidence(
                    source=str(fonte.get("url")).strip(),
                    authority=tier_for_url(str(fonte.get("url")), authority_map),
                    # `retrieved` e a data que a propria regra declara ter lido a
                    # pagina. E o unico dado de vigencia que existe no finding --
                    # inventar "hoje" aqui diria que a fonte foi conferida agora.
                    freshness=str(fonte.get("retrieved") or ""),
                    scope=_rotulo_de_escopo(escopo),
                    measurement_ref=ancora,
                    supports=[claim.id],
                )
            )

    return claims, evidences


def _fact_ids_declarados(finding: dict) -> list[str]:
    """Os `fact.id` que o finding declara como ancora, sem repetir.

    O finding real repete o mesmo id uma vez por medida conferida -- a fixture
    `folga_medida_sem_skew` cita `f_681614` quatro vezes, uma por condicao do
    `all`. Deduplicar preservando a ordem mantem "qual foi a primeira ancora
    declarada" respondivel, coisa que `sorted(set(...))` perderia.
    """
    vistos: list[str] = []
    for bruto in finding.get("evidence") or []:
        ref = str(bruto).strip()
        if ref and ref not in vistos:
            vistos.append(ref)
    return vistos


def _fontes_com_url(finding: dict) -> list[dict[str, Any]]:
    """As entradas de `sources:` que tem URL.

    Entrada sem `url` -- `origin: field-heuristic`, por exemplo -- nao vira
    evidencia. Nao e omissao: o tier sai do HOST, e heuristica de campo nao tem
    host. Deixa-la cair no `default` do mapa a promoveria a autoridade
    reconhecida (T4) sem que ninguem tivesse declarado isso, e o mapa existe
    para host desconhecido, nao para fonte sem host.
    """
    fontes: list[dict[str, Any]] = []
    for entrada in finding.get("sources") or []:
        if isinstance(entrada, dict) and str(entrada.get("url") or "").strip():
            fontes.append(entrada)
    return fontes


def _melhor_tier(
    fontes: list[dict[str, Any]], authority_map: dict
) -> EvidenceAuthority:
    """O melhor tier (menor numeral) entre as fontes do finding.

    Finding sem fonte com URL sai `T6_CONJECTURE`, e nao no `default` do mapa:
    o default responde "host que o mapa nao nomeia", e aqui nao ha host nenhum.
    Uma regra que nao citou fonte nao tem lastro de conhecimento -- T6 e a
    leitura literal disso, e ela leva o finding para `low` na tabela.
    """
    tiers = [tier_for_url(str(f.get("url")), authority_map) for f in fontes]
    if not tiers:
        return EvidenceAuthority.T6_CONJECTURE
    return min(tiers, key=_ORDEM_DE_TIER.index)


def _statement(finding: dict, rule_id: str) -> str:
    """O que a claim afirma: o diagnostico da regra, sobre o sujeito medido.

    O sujeito entra no texto porque `Claim` nao tem campo para ele, e duas
    ocorrencias da mesma regra sobre jobs diferentes produziriam a mesma frase.

    `Claim` recusa statement vazio. Um finding sem `title` cairia num
    `ValueError` que derrubaria o pacote inteiro por causa de um campo de
    apresentacao -- regra 27 ao contrario. O `rule_id` responde a mesma pergunta
    com menos elegancia e nenhuma invencao, entao ele e o fallback.
    """
    titulo = str(finding.get("title") or "").strip() or rule_id or "finding sem rule_id"
    sujeito = finding.get("subject") or {}
    simbolo = str(sujeito.get("symbol") or "").strip()
    if not simbolo:
        return titulo
    tipo = str(sujeito.get("type") or "").strip()
    return f"{titulo} -- {tipo} {simbolo}".replace("  ", " ").strip()


def _rotulo_de_escopo(runtime_scope: dict) -> str:
    """O `runtime_scope` da regra como texto estavel, para `Evidence.scope`.

    Ordenado por chave e por valor porque `scope` entra no id da evidencia: a
    mesma regra nao pode gerar dois ids conforme a ordem em que o YAML foi lido.

    O formato mantem o nome do componente legivel (`glue 4.0, 5.0`) porque
    `evidence.verify_evidence` procura a chave do runtime como SUBSTRING deste
    campo. Escopo vazio vira string vazia, e ali `verify_evidence` assume em
    escopo -- a mesma leitura que `authority.in_scope` faz de "nao declarei
    escopo".
    """
    if not runtime_scope:
        return ""
    partes: list[str] = []
    for chave in sorted(str(k) for k in runtime_scope):
        valores = runtime_scope[chave]
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        partes.append(f"{chave} {', '.join(sorted(str(v) for v in valores))}")
    return "; ".join(partes)
