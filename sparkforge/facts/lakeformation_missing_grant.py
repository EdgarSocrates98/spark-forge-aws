"""`lakeformation.missing_grant` -- a permissao que a operacao exigia e o grant
medido nao tinha, cruzada com a falha observada.

Derivacao pura sobre a UNIAO dos facts, no molde de `lakeformation.py` e
`timeout_diagnosis.py`: nao le artefato, e e chamada por `fuse()`.

## Por que ele existe

`ERR-LF-001` (`Insufficient Lake Formation permission(s) on`) declara
`lakeformation.missing_grant` em `evidence_required` desde antes de o motor ler
Lake Formation. A mensagem nomeia o RECURSO e nao a permissao; a permissao sai da
OPERACAO que o codigo faz, lida da tabela citada em
`knowledge/glue/lakeformation-permissions.yaml`. "Permissao exigida fora do
conjunto concedido" nao cabe nos seis comparadores de `rules/expr.py`, e por isso
e fact (regra 33 do CLAUDE.md).

## O modelo decide o lado (regras 31 e 32)

Sob FTA, a credencial do Lake Formation le e escreve: cobra-se o grant. Sob FGAC,
a leitura cobra o grant e a escrita cobra o IAM do runtime role. Escrita em alvo
REGISTRADO sob FGAC e o conflito declarado da secao 6 de
`knowledge/glue/lakeformation-fgac.md`, e sai recusa nomeada, sem lado escolhido.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.findings.models import Fact, sort_facts
from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

EXTRACTOR_ID = "lakeformation_missing_grant@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "lakeformation.missing_grant",
        "lakeformation.missing_grant.unresolved",
    }
)

# As operacoes que `_operacoes` produz. A tabela precisa ter ao menos uma linha
# para cada uma; `test_tabela_de_operacao_cita_fonte_e_cobre_o_extrator` cobra.
OPERACOES_MAPEADAS = ("read", "write", "overwrite", "create")

# So a mensagem de grant ausente dispara (D10). ERR-LF-002 a 005 nomeiam acao IAM ou
# validacao de seguranca e tem SF-ERR-014 a 017.
GATILHO = "ERR-LF-001"
SOURCE_KINDS = frozenset({"error.signature_match"})

IAM_ALLOWED_PRINCIPALS = "IAM_ALLOWED_PRINCIPALS"

# O texto do gatilho e um TRECHO: `sparkforge/errors/matcher.py` grava
# `matched_line = mensagem[:_TRECHO]` (200) e `sparkforge/facts/exception.py` grava
# `message_head[:200]`. A assinatura casou na mensagem INTEIRA; o trecho pode ter
# cortado o nome do recurso, ou a clausula toda.
_TETO_DO_TRECHO = 200

# A unica forma de clausula que o matcher entrega: a assinatura exige o literal
# "permission(s) on". Outra forma (": Required Describe on default") nao e lida e
# sai `recurso_nao_lido`, porque o token depois dela pode ser database.
_PREFIXO = r"permission\(s\)\s+on\s+"
# O token depois de `on` e LIDO por `_ler_nome`; o que ele nao le vira `recurso_nao_lido`.
_RECURSO_RE = re.compile(_PREFIXO + r"(\S+)", re.IGNORECASE)
_NAO_TABELA_RE = re.compile(
    _PREFIXO + r"['\"`]?((?:s3[an]?://|arn:)[^\s'\"`,;]*)", re.IGNORECASE
)
# Qualquer `on` depois de "permission(s)" conta como clausula: com ela, o atalho do
# candidato unico acusaria a tabela do pool no lugar da que a mensagem nomeia.
# Dois passos, e nao `permission\(s\).*?\bon\b`: esse recomeca em cada "permission(s)" do
# texto do artefato e fica quadratico.
_PERMISSAO_RE = re.compile(r"permission\(s\)", re.IGNORECASE)
_ON_RE = re.compile(r"\bon\b\s*\S*", re.IGNORECASE)
_NOME_RE = re.compile(r"[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)*")
_ASPAS = "'\"`"
# O que pode colar no fim do nome: pontuacao de frase, fecho de parentese e de JSON,
# e aspas.
_CAUDA = ",;:.)}" + _ASPAS

# `pyspark_ast` grava `mode` so para append/overwrite/overwritePartitions.
_MODOS_OVERWRITE = frozenset({"overwrite", "overwritepartitions"})
# `writeTo` sem `mode` termina em create/replace/createOrReplace/merge, e o fact nao
# carrega o terminal; `ambigua` (`write` e `writeTo` na mesma cadeia) e codigo que o
# parse nao entende. Sem `mode`, a operacao e desconhecida, nunca um `write` presumido.
# A chave e o `api` do fact; o valor sai em `writer_api` da recusa.
_TERMINAL_NAO_MEDIDO = {"dataframe_writer_v2": "writeTo", "ambigua": "ambigua"}

_SQL = {
    "insert_into": "write",
    "merge_into": "write",
    "update": "write",
    "insert_overwrite": "overwrite",
    "delete_from": "overwrite",
    "create_table": "create",
    "create_table_as": "create",
}

_DESTRAVA = {
    "recurso_ambiguo": (
        "o case tem mais de uma tabela com grant ou registro coletado que serve: a "
        "mensagem nao nomeia o recurso, ou o nome que ela da casa com mais de uma tabela "
        "qualificada (sem database, ou sem o catalogo que as separa); colete so a tabela "
        "da falha com `sparkforge collect lakeformation`"
    ),
    "trecho_truncado": (
        f"o trecho da mensagem que o matcher guarda tem {_TETO_DO_TRECHO} caracteres, e o "
        "corte caiu antes do nome do recurso ou pode ter caido dentro dele; o fact nao "
        "presume a tabela; colete a mensagem inteira do log"
    ),
    "recurso_nao_nomeado": (
        "a mensagem nao nomeia tabela e o case nao tem grant nem registro de onde "
        "inferir; colete os grants da tabela da falha com `sparkforge collect lakeformation`"
    ),
    "recurso_nao_lido": (
        "a mensagem nomeia um recurso numa forma que o extrator nao le; o fact nao presume "
        "a tabela"
    ),
    "recurso_nao_e_tabela": (
        "a mensagem nomeia localizacao S3 ou ARN, nao tabela do catalogo; o fact so cobre "
        "grant de tabela"
    ),
    "operacao_com_alvo_nao_resolvido": (
        "uma operacao deste tipo tem alvo que vem de variavel que o extrator de codigo nao "
        "resolve; ela nao foi avaliada"
    ),
    "terminal_de_escrita_nao_medido": (
        "a escrita nao tem modo medido e o terminal nao e lido: writeTo sem modo termina "
        "em create/replace/createOrReplace/merge, e API de escrita ambigua (write e "
        "writeTo na mesma cadeia) e codigo que o parse nao entende; o fact pyspark.write "
        "nao carrega a operacao"
    ),
    "catalogo_ambiguo": (
        "grants da mesma tabela em mais de um catalogo coletado (catalog_id vazio conta "
        "como um deles); colete so o catalogo da falha"
    ),
    "operacao_nao_medida": (
        "nenhum fact de operacao sobre o recurso; rode `sparkforge analyze pyspark` sobre o "
        "codigo do job e junte a saida ao case"
    ),
    "operacao_nao_ligada_ao_recurso": (
        "o codigo le ou escreve outros alvos literais e nenhum e o recurso da mensagem; "
        "confira se o alvo vem de variavel, que o extrator de codigo nao resolve"
    ),
    "modelo_both": (
        "o job declara FGAC e marcador de FTA juntos, e a AWS nao permite os dois no mesmo "
        "job; decida o modelo antes (secao 5 de knowledge/glue/lakeformation-fgac.md)"
    ),
    "modelo_ausente": (
        "nenhum modelo de acesso declarado; rode `sparkforge analyze terraform` sobre o job "
        "(argumento de FGAC ou confs de FTA)"
    ),
    "grant_nao_coletado": (
        "nenhum `lakeformation.grant` para o recurso; rode `sparkforge collect lakeformation` "
        "sobre ele"
    ),
    "principal_ambiguo": (
        "mais de um role na decisao de IAM, ou nenhuma decisao de IAM e grants de mais de "
        "um principal na tabela: nada diz qual e o role do job; rode "
        "`sparkforge collect iam-access` so para o runtime role"
    ),
    "principal_nao_coletado": (
        "sem decisao de IAM e sem grant de principal nomeado na tabela; colete a decisao "
        "de IAM do role do job com `sparkforge collect iam-access`"
    ),
    "permissao_de_database_nao_coletada": (
        "create exige permissao no DATABASE, e `collect lakeformation` coleta grant de tabela"
    ),
    "fta_escrita_em_alvo_nao_registrado": (
        "sob FTA, tabela nao registrada no Lake Formation e escrita pela credencial do "
        "runtime role, e nao pelo grant (secao 5 de knowledge/glue/lakeformation-fgac.md); "
        "rode `sparkforge collect iam-access` com s3:PutObject sobre o alvo"
    ),
    "operacao_sem_requisito_declarado": (
        "a tabela citada nao declara requisito para esta operacao neste modelo; nada e "
        "afirmado sem fonte"
    ),
}

_RELATIVE = "glue/lakeformation-permissions.yaml"
_CAMPOS = ("operation", "model", "side", "resource_level", "requires", "source", "quote")


def _path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _RELATIVE)


@lru_cache(maxsize=1)
def load_table() -> dict[str, Any]:
    """A tabela inteira, validada. Linha sem campo, ou com fonte fora de `fontes`,
    levanta `ValueError` -- a mesma guarda de `lakeformation_matrix.load`."""
    with _path().open("r", encoding="utf-8") as arquivo:
        documento = yaml.safe_load(arquivo) or {}
    fontes = documento.get("fontes") or {}
    problemas: list[str] = []
    for linha in documento.get("operacoes") or []:
        rotulo = f"{linha.get('operation')}/{linha.get('model')}"
        for campo in _CAMPOS:
            if not linha.get(campo):
                problemas.append(f"{rotulo}: sem `{campo}`")
        if linha.get("source") and linha["source"] not in fontes:
            problemas.append(f"{rotulo}: `source` {linha['source']!r} fora de `fontes`")
    if problemas:
        raise ValueError(
            "knowledge/glue/lakeformation-permissions.yaml invalido:\n  "
            + "\n  ".join(problemas)
        )
    return documento


def requirement(operation: str, model: str) -> dict[str, Any] | None:
    """A linha da tabela para (operacao, modelo), ou `None` quando a fonte nao a declara."""
    for linha in load_table().get("operacoes") or []:
        if linha["operation"] == operation and linha["model"] == model:
            return dict(linha)
    return None


def _prov(gatilho: Fact) -> dict[str, Any]:
    artefato = str((gatilho.provenance or {}).get("artifact") or "")
    return {"extractor": EXTRACTOR_ID, "artifact": artefato}


def _unresolved(
    reason: str, recurso: str, gatilho: Fact, **extra: Any
) -> Fact:
    # `matched` (o trecho que nao foi lido) entra no rotulo: sem ele, duas recusas de
    # gatilhos com textos diferentes colapsariam num id so.
    partes = (recurso, reason, *(str(extra.get(k) or "") for k in ("operation", "matched")))
    rotulo = "#".join(p for p in partes if p)
    return Fact(
        kind="lakeformation.missing_grant.unresolved",
        subject={"type": "table", "symbol": rotulo},
        measures={},
        attrs={
            "reason": reason,
            "resource": recurso,
            "signature_id": GATILHO,
            "unblocked_by": str(extra.pop("unblocked_by", "") or _DESTRAVA.get(reason, "")),
            "extractor": EXTRACTOR_ID,
            **extra,
        },
        provenance=_prov(gatilho),
    )


def _tabela_de(fact: Fact) -> str:
    return str((fact.subject or {}).get("symbol", "")).split("#", 1)[0]


def _texto(gatilho: Fact) -> str:
    attrs = gatilho.attrs or {}
    return str(attrs.get("matched_line") or attrs.get("matched_class") or "")


def _ler_nome(token: str) -> str | None:
    """O nome de tabela no token depois de `on`: cortado no "(", sem `_CAUDA` no fim e
    sem a aspa de abertura quando a mesma aspa saiu da cauda. O que sobra fora de
    `db.tabela` nao e lido."""
    bruto = token.split("(", 1)[0]
    nome = bruto.rstrip(_CAUDA)
    if nome[:1] in tuple(_ASPAS) and nome[0] in bruto[len(nome) :]:
        nome = nome[1:]
    return nome if _NOME_RE.fullmatch(nome) else None


def _recurso_da_mensagem(gatilho: Fact) -> str | None:
    casou = _RECURSO_RE.search(_texto(gatilho))
    return _ler_nome(casou.group(1)) if casou else None


def _clausula_e_fim(gatilho: Fact) -> tuple[str | None, bool]:
    """A clausula `permission(s) ... on <token>`, e se ela termina no fim do texto."""
    texto = _texto(gatilho)
    permissao = _PERMISSAO_RE.search(texto)
    if permissao is None:
        return None, False
    fim_da_linha = texto.find("\n", permissao.end())
    on = _ON_RE.search(
        texto, permissao.end(), len(texto) if fim_da_linha < 0 else fim_da_linha
    )
    if on is None:
        return None, False
    return texto[permissao.start() : on.end()], on.end() == len(texto)


def _no_teto(gatilho: Fact) -> bool:
    """O trecho gravado bateu no teto. Pela porta `message_head` o texto e
    `classe: cabeca`, e so a cabeca foi cortada."""
    attrs = gatilho.attrs or {}
    texto = _texto(gatilho)
    if attrs.get("matched_on") == "message_head":
        texto = texto.split(": ", 1)[-1]
    return len(texto) >= _TETO_DO_TRECHO


def _recurso_nao_tabela(gatilho: Fact) -> str | None:
    casou = _NAO_TABELA_RE.search(_texto(gatilho))
    return casou.group(1) if casou else None


def _tabelas_do_pool(facts: Sequence[Fact]) -> list[str]:
    tabelas = {
        _tabela_de(f)
        for f in facts
        if f.kind in {"lakeformation.grant", "lakeformation.registered_location"}
    }
    tabelas.discard("")
    return sorted(tabelas)


def _candidato_unico(facts: Sequence[Fact]) -> str | None:
    tabelas = _tabelas_do_pool(facts)
    return tabelas[0] if len(tabelas) == 1 else None


def _casa(alvo: str, recurso: str) -> bool:
    """Com os dois lados qualificados, casa pelo sufixo de segmentos
    (`glue_catalog.default.t` casa `default.t`, `staging.t` nao casa `default.t`); so
    pelo ultimo segmento quando um dos lados nao e qualificado. Sem caixa: o Glue Data
    Catalog guarda nomes em minusculas."""
    a, r = alvo.lower().split("."), recurso.lower().split(".")
    if len(a) > 1 and len(r) > 1:
        n = min(len(a), len(r))
        return a[-n:] == r[-n:]
    return a[-1] == r[-1]


def _canonizar(recurso: str, facts: Sequence[Fact]) -> tuple[str | None, list[str]]:
    """O recurso da mensagem contra as tabelas com grant ou registro no pool. Nome
    exato fica; uma unica qualificada que casa vira o recurso; mais de uma e ambigua
    (`None`, com as candidatas); nenhuma deixa o nome como veio."""
    tabelas = _tabelas_do_pool(facts)
    exatas = [t for t in tabelas if t.lower() == recurso.lower()]
    if len(exatas) == 1:
        return exatas[0], []
    casam = [t for t in tabelas if "." in t and _casa(t, recurso)]
    if len(casam) > 1:
        return None, casam
    return (casam[0] if casam else recurso), []


def _operacao_de_escrita(attrs: dict[str, Any]) -> str:
    modo = str(attrs.get("mode") or "").lower()
    if modo in _MODOS_OVERWRITE:
        return "overwrite"
    api = str(attrs.get("api") or "")
    if not modo and api in _TERMINAL_NAO_MEDIDO:
        return _TERMINAL_NAO_MEDIDO[api]
    return "write"


def _mapeada(operacao: str) -> str:
    """A operacao de `OPERACOES_MAPEADAS` de uma escrita de terminal nao medido."""
    return "write" if operacao in _TERMINAL_NAO_MEDIDO.values() else operacao


def _operacoes(
    recurso: str, facts: Sequence[Fact]
) -> tuple[list[tuple[str, Fact]], list[str]] | str:
    """As operacoes sobre o recurso, uma por tipo, e as operacoes sem alvo -- estas
    nunca sao presumidas sobre o recurso: saem recusadas, nunca caladas."""
    todas: list[tuple[str, str, Fact]] = []
    for f in facts:
        attrs = f.attrs or {}
        if f.kind == "pyspark.read":
            todas.append(("read", str(attrs.get("target") or ""), f))
        elif f.kind == "pyspark.write":
            todas.append((_operacao_de_escrita(attrs), str(attrs.get("target") or ""), f))
        elif f.kind == "sql.write_statement" and attrs.get("operation") in _SQL:
            todas.append((_SQL[attrs["operation"]], str(attrs.get("table") or ""), f))
    if not todas:
        return "operacao_nao_medida"
    escolhidas = [t for t in todas if t[1] and _casa(t[1], recurso)]
    sem_alvo = sorted({_mapeada(op) for op, alvo, _f in todas if not alvo})
    if not escolhidas and not sem_alvo:
        return "operacao_nao_ligada_ao_recurso"
    por_operacao: dict[str, Fact] = {}
    for op, _alvo, f in sorted(escolhidas, key=lambda t: (t[0], t[2].id)):
        por_operacao.setdefault(op, f)
    return sorted(por_operacao.items()), sem_alvo


def _modelo(facts: Sequence[Fact]) -> str:
    """D9: `access_model` so existe quando o argumento de FGAC e declarado; job so de
    FTA aparece como `filesystem` com o resolver do LF ou catalogo com LF ligado."""
    modelos = {
        str((f.attrs or {}).get("model"))
        for f in facts
        if f.kind == "lakeformation.access_model"
    }
    if "both" in modelos:
        return "modelo_both"
    if "fgac" in modelos:
        return "fgac"
    fta = any(
        (
            f.kind == "lakeformation.filesystem"
            and (f.attrs or {}).get("lf_credentials_resolver_declared")
        )
        or (
            f.kind == "lakeformation.iceberg_catalog"
            and (f.attrs or {}).get("lakeformation_enabled")
        )
        for f in facts
    )
    return "fta" if fta else "modelo_ausente"


def _principal(facts: Sequence[Fact], grants: Sequence[Fact]) -> tuple[str, list[str]]:
    """O principal do job, ou a razao da recusa com as candidatas: `("", [...])` e
    ambiguo, `("", [])` e nenhum coletado."""
    roles = {
        str((f.attrs or {}).get("role_arn") or "")
        for f in facts
        if f.kind == "iam.access_decision"
    }
    roles.discard("")
    # Mais de um role decidido: o grant de um principal unico nao diz qual deles e o
    # do job. O recurso aos grants so vale sem decisao de IAM nenhuma.
    if not roles:
        roles = {str((g.attrs or {}).get("principal") or "") for g in grants}
        roles -= {"", IAM_ALLOWED_PRINCIPALS}
    if len(roles) == 1:
        return roles.pop(), []
    return "", sorted(roles)


def _cobre(concedidas: Sequence[str], permissao: str) -> bool:
    return "ALL" in concedidas or permissao in concedidas


def _lado_lf(
    recurso: str, operacao: str, origem: Fact, linha: dict[str, Any], modelo: str,
    gatilho: Fact, facts: Sequence[Fact],
) -> list[Fact]:
    if linha["resource_level"] == "database":
        return [
            _unresolved(
                "permissao_de_database_nao_coletada", recurso, gatilho, operation=operacao
            )
        ]
    nao_registrada = any(
        f.kind == "lakeformation.registered_location"
        and _tabela_de(f) == recurso
        and (f.attrs or {}).get("registered") is False
        for f in facts
    )
    if modelo == "fta" and operacao in {"write", "overwrite"} and nao_registrada:
        return [
            _unresolved(
                "fta_escrita_em_alvo_nao_registrado", recurso, gatilho, operation=operacao
            )
        ]
    grants = [f for f in facts if f.kind == "lakeformation.grant" and _tabela_de(f) == recurso]
    if not grants:
        return [_unresolved("grant_nao_coletado", recurso, gatilho, operation=operacao)]
    # Vazio conta como catalogo distinto: "" ao lado de "222..." nao diz que sao o mesmo.
    catalogos = sorted({str((g.subject or {}).get("catalog_id") or "") for g in grants})
    if len(catalogos) > 1:
        return [
            _unresolved(
                "catalogo_ambiguo", recurso, gatilho, operation=operacao, catalog_ids=catalogos
            )
        ]
    # Tabela aberta a `IAM_ALLOWED_PRINCIPALS` com ALL e governada pelo IAM: falta de
    # grant do LF nao e a causa, e SF-LF-008 ja fala dela.
    if any(
        (g.attrs or {}).get("is_iam_allowed_principals") and (g.attrs or {}).get("has_all")
        for g in grants
    ):
        return []
    principal, candidatas = _principal(facts, grants)
    if not principal:
        razao = "principal_ambiguo" if candidatas else "principal_nao_coletado"
        return [
            _unresolved(razao, recurso, gatilho, operation=operacao, candidates=candidatas)
        ]
    do_principal = [g for g in grants if (g.attrs or {}).get("principal") == principal]
    concedidas = sorted(
        {str(p) for g in do_principal for p in (g.attrs or {}).get("permissions") or []}
    )
    faltam = [p for p in linha["requires"] if not _cobre(concedidas, p)]
    if not faltam:
        return []
    return [
        Fact(
            kind="lakeformation.missing_grant",
            subject={"type": "table", "symbol": f"{recurso}#{operacao}#lf"},
            measures={},
            attrs={
                "resource": recurso,
                "operation": operacao,
                "model": modelo,
                "side": "lf",
                "principal": principal,
                "requires": list(linha["requires"]),
                "missing": faltam,
                "granted": concedidas,
                "source": load_table()["fontes"][linha["source"]],
                "quote": linha["quote"],
                "signature_id": GATILHO,
                "evidence": sorted({gatilho.id, origem.id, *(g.id for g in do_principal)}),
                "extractor": EXTRACTOR_ID,
            },
            provenance=_prov(gatilho),
        )
    ]


def _lado_iam(
    recurso: str, operacao: str, origem: Fact, linha: dict[str, Any], modelo: str,
    gatilho: Fact, facts: Sequence[Fact],
) -> list[Fact]:
    return []


def _derivar(recurso: str, gatilho: Fact, facts: Sequence[Fact]) -> list[Fact]:
    resultado = _operacoes(recurso, facts)
    if isinstance(resultado, str):
        return [_unresolved(resultado, recurso, gatilho)]
    operacoes, sem_alvo = resultado
    saida: list[Fact] = [
        _unresolved("operacao_com_alvo_nao_resolvido", recurso, gatilho, operation=op)
        for op in sem_alvo
    ]
    # O modelo nao depende do alvo: a recusa dele sai tambem quando so ha operacao
    # sem alvo, e nao e calada pela recusa de alvo.
    modelo = _modelo(facts)
    if modelo not in {"fta", "fgac"}:
        return [*saida, _unresolved(modelo, recurso, gatilho)]
    for operacao, origem in operacoes:
        if operacao in _TERMINAL_NAO_MEDIDO.values():
            saida.append(
                _unresolved(
                    "terminal_de_escrita_nao_medido",
                    recurso,
                    gatilho,
                    operation=_mapeada(operacao),
                    writer_api=operacao,
                )
            )
            continue
        linha = requirement(operacao, modelo)
        if linha is None:
            saida.append(
                _unresolved(
                    "operacao_sem_requisito_declarado",
                    recurso,
                    gatilho,
                    operation=operacao,
                    model=modelo,
                )
            )
            continue
        lado = _lado_lf if linha["side"] == "lf" else _lado_iam
        saida.extend(lado(recurso, operacao, origem, linha, modelo, gatilho, facts))
    return saida


def _recurso(gatilho: Fact, lista: Sequence[Fact]) -> tuple[str | None, Fact | None]:
    """A tabela que o gatilho acusa, ou a recusa que diz por que ela nao sai."""
    bruto = _recurso_nao_tabela(gatilho)
    if bruto is not None:
        return None, _unresolved("recurso_nao_e_tabela", bruto, gatilho)
    nomeado = _recurso_da_mensagem(gatilho)
    clausula, no_fim = _clausula_e_fim(gatilho)
    if _no_teto(gatilho) and (clausula is None or no_fim):
        # O trecho bateu no teto e o nome, se ha, encosta no corte: ele pode ser o
        # prefixo de outro (`dim_cliente` de `dim_cliente_hist`), e sem clausula o
        # candidato unico acusaria a tabela do pool no lugar da que a mensagem nomeia.
        return None, _unresolved("trecho_truncado", "", gatilho, matched=_texto(gatilho))
    if nomeado is None and clausula is not None:
        # Ha `on` depois de "permission(s)" e o nome nao foi lido: o candidato
        # unico do pool nao e a tabela que a mensagem nomeia.
        return None, _unresolved("recurso_nao_lido", "", gatilho, matched=clausula)
    recurso, candidatas = (
        _canonizar(nomeado, lista)
        if nomeado
        else (_candidato_unico(lista), _tabelas_do_pool(lista))
    )
    if recurso is None:
        razao = "recurso_ambiguo" if candidatas else "recurso_nao_nomeado"
        return None, _unresolved(razao, nomeado or "", gatilho, candidates=candidatas)
    return recurso, None


def build_missing_grant(facts: Sequence[Fact]) -> list[Fact]:
    """Deriva `lakeformation.missing_grant` da uniao dos facts. Sem `ERR-LF-001` no
    pool, devolve lista vazia: sem falha observada nao ha permissao ausente a afirmar."""
    lista = list(facts)
    # Ordem por id (com o artefato e a linha para desempatar gatilhos de mesmo id): o
    # primeiro gatilho de cada recurso, ou de cada recusa, e quem da a proveniencia, e
    # a saida nao depende da ordem do pool.
    gatilhos = sorted(
        (
            f
            for f in lista
            if f.kind == "error.signature_match"
            and (f.attrs or {}).get("signature_id") == GATILHO
        ),
        key=lambda f: (f.id, str((f.provenance or {}).get("artifact") or ""), _texto(f)),
    )
    if not gatilhos:
        return []
    saida: dict[str, Fact] = {}
    recursos: dict[str, Fact] = {}
    for gatilho in gatilhos:
        recurso, recusa = _recurso(gatilho, lista)
        if recusa is not None:
            saida.setdefault(recusa.id, recusa)
        elif recurso is not None:
            recursos.setdefault(recurso, gatilho)
    for recurso, gatilho in recursos.items():
        for fact in _derivar(recurso, gatilho, lista):
            saida.setdefault(fact.id, fact)
    return sort_facts(list(saida.values()))


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "GATILHO",
    "OPERACOES_MAPEADAS",
    "SOURCE_KINDS",
    "build_missing_grant",
    "load_table",
    "requirement",
]
