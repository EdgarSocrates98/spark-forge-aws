"""Lake Formation Deterministic Permission Graph Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sparkforge.facts.lakeformation_missing_grant import casa_tabela


@dataclass
class PermissionEdge:
    source_node: str
    target_node: str
    permission_type: str  # iam, lf_grant, ram_share, s3_bucket_policy, kms_decrypt
    status: str  # granted, missing, blocking, uncertain
    evidence: str = ""


@dataclass
class PermissionGraphAnalysis:
    principal_arn: str
    target_table_arn: str
    is_accessible: bool
    effective_path: list[str]
    missing_permissions: list[PermissionEdge] = field(default_factory=list)
    blocking_permissions: list[PermissionEdge] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class LakeFormationPermissionGraph:
    """Traces access path: Principal -> IAM -> LF -> Catalog -> Resource Link
    -> RAM -> S3 -> KMS."""

    def evaluate_access(
        self,
        principal_arn: str,
        target_table: str,
        grants: list[dict[str, Any]],
        ram_shares: list[dict[str, Any]],
        kms_keys: list[dict[str, Any]],
        is_cross_account: bool = False,
    ) -> PermissionGraphAnalysis:
        effective_path = [principal_arn]
        missing: list[PermissionEdge] = []
        blocking: list[PermissionEdge] = []
        recommendations: list[str] = []

        # Check Lake Formation Catalog/Table grant
        has_table_grant = any(
            g.get("table", "") == target_table and "SELECT" in g.get("permissions", [])
            for g in grants
        )

        if has_table_grant:
            effective_path.append("lakeformation:TableGrant")
        else:
            edge = PermissionEdge(
                source_node=principal_arn,
                target_node=f"lakeformation:{target_table}",
                permission_type="lf_grant",
                status="missing",
                evidence=f"No SELECT grant found on {target_table}",
            )
            missing.append(edge)
            recommendations.append(
                f"Grant SELECT permission on Lake Formation table {target_table}"
            )

        # If cross-account, check RAM and Resource Link
        if is_cross_account:
            has_ram_share = any(r.get("status") == "ACCEPTED" for r in ram_shares)
            if has_ram_share:
                effective_path.append("ram:ResourceShare")
                effective_path.append("glue:ResourceLink")
            else:
                missing.append(
                    PermissionEdge(
                        source_node="ram:share",
                        target_node="consumer:account",
                        permission_type="ram_share",
                        status="missing",
                        evidence="RAM resource share not accepted in consumer account",
                    )
                )
                recommendations.append(
                    "Accept AWS RAM resource share in consumer account and create Glue resource "
                    "link."
                )

        # Check KMS access
        has_kms = any(k.get("allows_principal", False) for k in kms_keys) if kms_keys else True
        if has_kms:
            effective_path.append("kms:Decrypt")
        else:
            missing.append(
                PermissionEdge(
                    source_node=principal_arn,
                    target_node="kms:key",
                    permission_type="kms_decrypt",
                    status="missing",
                    evidence="Principal missing in KMS Key Policy",
                )
            )
            recommendations.append(
                "Add principal role ARN to KMS Key Policy `kms:Decrypt` statement."
            )

        is_accessible = len(missing) == 0

        return PermissionGraphAnalysis(
            principal_arn=principal_arn,
            target_table_arn=target_table,
            is_accessible=is_accessible,
            effective_path=effective_path if is_accessible else [],
            missing_permissions=missing,
            blocking_permissions=blocking,
            recommended_actions=recommendations,
        )


# --------------------------------------------------------------------------- #
# O grafo A PARTIR DE FACTS, e por que o caminho de cima não deve ser usado.
#
# O §13 do prompt de origem pede que o diagnóstico produza um GRAFO e não uma
# lista. `LakeFormationPermissionGraph.evaluate_access` já produzia um -- e era
# ÓRFÃO: medido em 2026-09-10, os únicos chamadores dele em todo o repositório
# eram o próprio teste e o `__init__.py` que o reexporta.
#
# E o motivo não era esquecimento. Ele é PIOR: a assinatura recebe `grants`,
# `ram_shares` e `kms_keys` como listas de dicionários, nenhum coletor deste
# repositório produz esse shape, e chamá-lo com lista vazia ACUSA. Medido:
#
#   evaluate_access(..., ram_shares=[], is_cross_account=True)
#     -> missing_permissions: [{permission_type: "ram_share", status: "missing"}]
#     -> recommended_actions: ["Accept AWS RAM resource share ..."]
#     -> is_accessible: False
#
# Ninguém coletou RAM share, e a resposta é "o compartilhamento não foi aceito".
# É acusação a partir de ausência de artefato -- exatamente o que a regra 20 do
# `CLAUDE.md` recusa, e o que torna aquele caminho inseguro de ligar como está.
#
# `build_access_graph` é a entrada que lê FACT. A diferença que ela introduz é um
# quarto status -- `unresolved` -- e um `is_accessible` TERNÁRIO: `None` quando
# alguma perna do caminho não foi medida. Sem o terceiro estado, "não sei" e "não
# tem" viram a mesma resposta.
# --------------------------------------------------------------------------- #

STATUS_GRANTED = "granted"
STATUS_MISSING = "missing"
STATUS_BLOCKING = "blocking"
STATUS_UNRESOLVED = "unresolved"
# `not_applicable` existe por um defeito que a primeira versao deste modulo teve:
# ela marcava `registered: False` como `missing`, e `is_accessible` saia `False`.
#
# LOCALIZACAO NAO REGISTRADA NAO E FALTA DE PERMISSAO -- e o oposto. Tabela fora
# do registro do Lake Formation e lida com a credencial do RUNTIME ROLE, direto;
# o registro nao e uma perna que faltou, e uma perna que nao participa. Marca-la
# `missing` acusava de negar acesso justamente o arranjo em que o acesso nao
# depende do Lake Formation.
STATUS_NOT_APPLICABLE = "not_applicable"

# As pernas do caminho de acesso que NENHUM coletor deste repositório produz.
# Elas saem `unresolved` sempre, com o que destravaria cada uma -- nunca
# `missing`.
_PERNAS_SEM_PRODUTOR = (
    (
        "ram_share",
        "ram:ResourceShare",
        "nenhum coletor produz o estado do compartilhamento AWS RAM; "
        "destravaria: `ram:GetResourceShares` num coletor novo",
    ),
    # `resource_link` SAIU desta lista em 2026-09-10: `sparkforge/collect/
    # glue_resource_link.py` produz `glue.resource_link` e
    # `glue.resource_link.target`, e a perna passou a ser medida. O que
    # destravaria estava escrito aqui -- "`glue:GetTable` sobre o link,
    # comparando o nome com o do recurso de origem" -- e e literalmente o que o
    # coletor faz.
    (
        "kms_decrypt",
        "kms:key",
        "nenhum coletor le a key policy do KMS; destravaria: `kms:GetKeyPolicy` "
        "num coletor novo",
    ),
)


def _aresta(origem: str, destino: str, tipo: str, status: str, evidencia: str) -> PermissionEdge:
    return PermissionEdge(
        source_node=origem,
        target_node=destino,
        permission_type=tipo,
        status=status,
        evidence=evidencia,
    )


def _attrs(fact: Any) -> dict[str, Any]:
    return dict(getattr(fact, "attrs", {}) or {})


def _subject(fact: Any) -> dict[str, Any]:
    return dict(getattr(fact, "subject", {}) or {})


def build_access_graph(
    facts: Any,
    principal_arn: str = "",
    target_table: str = "",
) -> dict[str, Any]:
    """O caminho de acesso como GRAFO, derivado de facts. Não acusa o que não mediu.

    Lê `lakeformation.grant`, `iam.access_decision`,
    `lakeformation.registered_location`, `glue.resource_link` e
    `glue.resource_link.target` -- os que têm produtor -- e devolve as pernas
    restantes (RAM share e key policy do KMS) como `unresolved`, com o que
    destravaria cada uma.

    `is_accessible` é TERNÁRIO:

      `True`   toda perna MEDIDA passou, e nenhuma ficou sem medida
      `False`  alguma perna medida falhou -- e aí a resposta é conclusiva
      `None`   nenhuma perna medida falhou, e alguma não foi medida

    O `None` é o estado que o caminho antigo não tinha, e é o que separa "o
    acesso funciona" de "o que eu consegui olhar não impede".

    `principal_arn` e `target_table` vazios são preenchidos a partir dos facts
    quando houver um só candidato; com mais de um, a função NÃO escolhe -- ela
    devolve `unresolved` nomeando a ambiguidade, porque escolher o primeiro
    produziria um grafo sobre um par que ninguém pediu.
    """
    lista = list(facts or [])
    grants = [f for f in lista if getattr(f, "kind", "") == "lakeformation.grant"]
    decisoes = [f for f in lista if getattr(f, "kind", "") == "iam.access_decision"]
    registros = [
        f for f in lista if getattr(f, "kind", "") == "lakeformation.registered_location"
    ]
    links = [f for f in lista if getattr(f, "kind", "") == "glue.resource_link"]
    alvos_de_link = [f for f in lista if getattr(f, "kind", "") == "glue.resource_link.target"]

    if not target_table:
        tabelas = {
            str(_subject(f).get("symbol", "")).split("#", 1)[0]
            for f in grants + registros + links
            if _subject(f).get("symbol")
        }
        tabelas.discard("")
        if len(tabelas) == 1:
            target_table = tabelas.pop()
        elif len(tabelas) > 1:
            return {
                "status": "unresolved",
                "reason": "mais_de_uma_tabela_no_case",
                "candidates": sorted(tabelas),
                "unblocked_by": "passe `target_table` para escolher qual grafo montar",
            }

    if not principal_arn:
        principais = {str(_attrs(f).get("principal", "")) for f in grants}
        principais |= {str(_attrs(f).get("role_arn", "")) for f in decisoes}
        principais.discard("")
        # `IAM_ALLOWED_PRINCIPALS` nao e um principal: e o marcador de que a
        # tabela esta aberta a quem tem IAM (ver SF-LF-008).
        principais = {p for p in principais if p != "IAM_ALLOWED_PRINCIPALS"}
        if len(principais) == 1:
            principal_arn = principais.pop()
        elif len(principais) > 1:
            return {
                "status": "unresolved",
                "reason": "mais_de_um_principal_no_case",
                "candidates": sorted(principais),
                "unblocked_by": "passe `principal_arn` para escolher qual grafo montar",
            }

    if not target_table or not principal_arn:
        return {
            "status": "unresolved",
            "reason": "sem_grant_nem_decisao_de_iam_no_case",
            "unblocked_by": (
                "rode `sparkforge collect lakeformation` e `sparkforge collect iam-access`"
            ),
        }

    arestas: list[PermissionEdge] = []
    caminho: list[str] = [principal_arn]

    # perna 1: concessao do Lake Formation (TEM produtor)
    do_par = [
        f
        for f in grants
        if str(_subject(f).get("symbol", "")).startswith(target_table + "#")
        and str(_attrs(f).get("principal", "")) == principal_arn
    ]
    alvo_lf = "lakeformation:" + target_table
    if not do_par:
        arestas.append(
            _aresta(
                principal_arn,
                alvo_lf,
                "lf_grant",
                STATUS_UNRESOLVED,
                "nenhum `lakeformation.grant` no case para este par; destravaria: "
                "`collect lakeformation` sobre " + target_table,
            )
        )
    elif faltas_do_par := [
        f
        for f in lista
        if getattr(f, "kind", "") == "lakeformation.missing_grant"
        and _attrs(f).get("side") == "lf"
        and casa_tabela(str(_attrs(f).get("resource", "")), target_table)
        and _attrs(f).get("principal") == principal_arn
    ]:
        # D8: com o fact de LF_GRANTS no case, o que a perna exige vem da OPERACAO
        # medida, e nao do SELECT fixo abaixo -- que acusaria leitura num job que
        # falhou escrevendo. O nome casa pela MESMA funcao do fact (`casa_tabela`: sem
        # caixa, e pelo sufixo de segmentos com os dois lados qualificados).
        exigidas = sorted(
            {
                f"{_attrs(f).get('operation')}: {', '.join(_attrs(f).get('missing') or [])}"
                for f in faltas_do_par
            }
        )
        arestas.append(
            _aresta(
                principal_arn,
                alvo_lf,
                "lf_grant",
                STATUS_MISSING,
                "grant medido nao cobre a operacao -- falta " + "; ".join(exigidas),
            )
        )
    elif any(_attrs(f).get("has_select") or _attrs(f).get("has_all") for f in do_par):
        caminho.append(alvo_lf)
        arestas.append(
            _aresta(
                principal_arn,
                alvo_lf,
                "lf_grant",
                STATUS_GRANTED,
                "grant medido com SELECT ou ALL",
            )
        )
    else:
        permissoes = sorted({p for f in do_par for p in (_attrs(f).get("permissions") or [])})
        arestas.append(
            _aresta(
                principal_arn,
                alvo_lf,
                "lf_grant",
                STATUS_MISSING,
                "grant medido e SEM SELECT nem ALL -- tem " + str(permissoes),
            )
        )

    # perna 2: decisao do IAM, SIMULADA (TEM produtor)
    if not decisoes:
        arestas.append(
            _aresta(
                principal_arn,
                "iam:decision",
                "iam",
                STATUS_UNRESOLVED,
                "nenhuma `iam.access_decision` no case; destravaria: `collect iam-access` "
                "-- e ele SIMULA, nunca faz parse de policy",
            )
        )
    else:
        negadas = [f for f in decisoes if not _attrs(f).get("allowed")]
        if negadas:
            for fact in negadas:
                a = _attrs(fact)
                arestas.append(
                    _aresta(
                        principal_arn,
                        "iam:" + str(a.get("action", "")),
                        "iam",
                        STATUS_BLOCKING,
                        "negado por "
                        + str(a.get("denied_by") or "razao nao nomeada")
                        + " sobre "
                        + str(a.get("resource", "")),
                    )
                )
        else:
            caminho.append("iam:allowed")
            arestas.append(
                _aresta(
                    principal_arn,
                    "iam:decision",
                    "iam",
                    STATUS_GRANTED,
                    str(len(decisoes)) + " acao(oes) simulada(s), nenhuma negada",
                )
            )

    # perna 3: registro da localizacao (TEM produtor, e e TERNARIO)
    do_registro = [f for f in registros if str(_subject(f).get("symbol", "")) == target_table]
    origem_s3 = "s3:" + target_table
    if not do_registro:
        arestas.append(
            _aresta(
                origem_s3,
                "lakeformation:registered_location",
                "s3_registration",
                STATUS_UNRESOLVED,
                "ninguem mediu o registro da localizacao S3",
            )
        )
    else:
        registrada = _attrs(do_registro[0]).get("registered")
        if registrada is None:
            arestas.append(
                _aresta(
                    origem_s3,
                    "lakeformation:registered_location",
                    "s3_registration",
                    STATUS_UNRESOLVED,
                    "`registered` e ternario e saiu nulo -- ninguem mediu",
                )
            )
        elif registrada:
            arestas.append(
                _aresta(
                    origem_s3,
                    "lakeformation:registered_location",
                    "s3_registration",
                    STATUS_GRANTED,
                    "`registered` medido: True -- a credencial do Lake Formation le e "
                    "escreve esta localizacao",
                )
            )
        else:
            arestas.append(
                _aresta(
                    origem_s3,
                    "lakeformation:registered_location",
                    "s3_registration",
                    STATUS_NOT_APPLICABLE,
                    "`registered` medido: False -- a localizacao NAO esta sob governanca "
                    "do Lake Formation, e o acesso passa a ser pelo IAM do runtime role. "
                    "Nao e permissao que faltou",
                )
            )

    # perna 4: resource link (TEM produtor desde 2026-09-10, e tem QUATRO saidas)
    #
    # Duas escolhas de status aqui nao sao obvias e sao de desenho:
    #
    #   objeto que NAO e link  -> `not_applicable`, pela mesma razao de
    #     `registered: False`: o acesso simplesmente nao passa por link, e
    #     marca-lo `missing` acusaria de defeito o arranjo em que ele nao
    #     participa.
    #
    #   alvo que respondeu `EntityNotFound` -> `unresolved` e NAO `blocking`.
    #     Sob Lake Formation esse codigo e a mesma resposta para recurso
    #     inexistente e para recurso nao autorizado, e escolher um dos dois
    #     sentidos seria chute com aparencia de medida.
    do_link = [f for f in links if str(_subject(f).get("symbol", "")) == target_table]
    destino_link = "glue:ResourceLink"
    if not do_link:
        arestas.append(
            _aresta(
                principal_arn,
                destino_link,
                "resource_link",
                STATUS_UNRESOLVED,
                "nenhum `glue.resource_link` no case para esta tabela; destravaria: "
                "`collect glue-resource-link` sobre " + target_table,
            )
        )
    else:
        a_link = _attrs(do_link[0])
        if not a_link.get("is_resource_link"):
            arestas.append(
                _aresta(
                    principal_arn,
                    destino_link,
                    "resource_link",
                    STATUS_NOT_APPLICABLE,
                    "medido: o objeto consultado NAO e resource link -- o acesso nao "
                    "passa por link, e isso nao e perna que faltou",
                )
            )
        elif a_link.get("name_matches_source") is False:
            arestas.append(
                _aresta(
                    principal_arn,
                    destino_link,
                    "resource_link",
                    STATUS_BLOCKING,
                    "link `"
                    + str(a_link.get("link_name", ""))
                    + "` aponta para `"
                    + str(a_link.get("source_resource_name", ""))
                    + "` -- nomes DIFERENTES. A AWS declara suportado apenas o nome "
                    "identico (SF-XACC-002); e limite de suporte declarado, nao "
                    "negacao observada",
                )
            )
        else:
            do_alvo = [
                f for f in alvos_de_link if str(_subject(f).get("symbol", "")) == target_table
            ]
            if not do_alvo:
                arestas.append(
                    _aresta(
                        principal_arn,
                        destino_link,
                        "resource_link",
                        STATUS_UNRESOLVED,
                        "link medido e com nome identico, e ninguem conferiu o recurso "
                        "de ORIGEM; destravaria: recoletar com `--verify-target`",
                    )
                )
            elif _attrs(do_alvo[0]).get("resolved"):
                caminho.append(destino_link)
                arestas.append(
                    _aresta(
                        principal_arn,
                        destino_link,
                        "resource_link",
                        STATUS_GRANTED,
                        "link com nome identico ao do recurso de origem, e a origem "
                        "respondeu",
                    )
                )
            else:
                arestas.append(
                    _aresta(
                        principal_arn,
                        destino_link,
                        "resource_link",
                        STATUS_UNRESOLVED,
                        "o recurso de ORIGEM respondeu `"
                        + str(_attrs(do_alvo[0]).get("aws_error_code", ""))
                        + "`, e sob Lake Formation esse codigo NAO distingue recurso "
                        "inexistente de recurso nao autorizado",
                    )
                )

    # pernas SEM produtor: `unresolved` SEMPRE, nunca `missing`
    for tipo, destino, destrava in _PERNAS_SEM_PRODUTOR:
        arestas.append(_aresta(principal_arn, destino, tipo, STATUS_UNRESOLVED, destrava))

    bloqueadas = [a for a in arestas if a.status in (STATUS_MISSING, STATUS_BLOCKING)]
    nao_medidas = [a for a in arestas if a.status == STATUS_UNRESOLVED]
    # `not_applicable` nao entra em nenhum dos dois: nao bloqueia e nao e lacuna
    # de medida -- e uma perna medida que nao participa do caminho.
    nao_aplicaveis = [a for a in arestas if a.status == STATUS_NOT_APPLICABLE]

    if bloqueadas:
        acessivel: bool | None = False
    elif nao_medidas:
        acessivel = None
    else:
        acessivel = True

    return {
        "status": "ok",
        "principal_arn": principal_arn,
        "target_table": target_table,
        # TERNARIO. `None` e "o que eu consegui olhar nao impede", e nao "funciona".
        "is_accessible": acessivel,
        "effective_path": caminho if acessivel is True else [],
        "edges": [dict(vars(e)) for e in arestas],
        "blocked": [dict(vars(e)) for e in bloqueadas],
        "unmeasured": [dict(vars(e)) for e in nao_medidas],
        "counts": {
            "edges": len(arestas),
            "granted": sum(1 for a in arestas if a.status == STATUS_GRANTED),
            "blocked": len(bloqueadas),
            "unresolved": len(nao_medidas),
            "not_applicable": len(nao_aplicaveis),
        },
        "refused": [
            {
                "what": "acusar_perna_sem_produtor",
                "why": (
                    "RAM share e key policy do KMS nao tem coletor neste repositorio -- "
                    "resource link SAIU desta lista em 2026-09-10, quando "
                    "`collect glue-resource-link` passou a produzir a medida. "
                    "`evaluate_access` (o caminho de dicionario) devolve "
                    "`missing` para eles quando recebe lista vazia, e isso e acusacao a "
                    "partir de ausencia de artefato."
                ),
                "unblocked_by": "; ".join(d for _, _, d in _PERNAS_SEM_PRODUTOR),
            },
        ],
    }
