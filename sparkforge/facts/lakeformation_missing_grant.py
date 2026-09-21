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

_RECURSO_RE = re.compile(r"permission\(s\)\s+on\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE)

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
        "a mensagem nao nomeia o recurso e o case tem mais de uma tabela com grant ou "
        "registro coletado; colete so a tabela da falha com `sparkforge collect lakeformation`"
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
        "mais de um principal com grant na tabela e nenhuma decisao de IAM que diga qual e o "
        "role do job; rode `sparkforge collect iam-access` para o runtime role"
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
    rotulo = "#".join(p for p in (recurso, reason, str(extra.get("operation") or "")) if p)
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


def _recurso_da_mensagem(gatilho: Fact) -> str | None:
    attrs = gatilho.attrs or {}
    texto = str(attrs.get("matched_line") or attrs.get("matched_class") or "")
    casou = _RECURSO_RE.search(texto)
    return casou.group(1).rstrip(".") if casou else None


def _candidato_unico(facts: Sequence[Fact]) -> str | None:
    tabelas = {
        _tabela_de(f)
        for f in facts
        if f.kind in {"lakeformation.grant", "lakeformation.registered_location"}
    }
    tabelas.discard("")
    return tabelas.pop() if len(tabelas) == 1 else None


def _casa(alvo: str, recurso: str) -> bool:
    return alvo == recurso or alvo.split(".")[-1] == recurso.split(".")[-1]


def _operacoes(recurso: str, facts: Sequence[Fact]) -> list[tuple[str, Fact]] | str:
    todas: list[tuple[str, str, Fact]] = []
    for f in facts:
        attrs = f.attrs or {}
        if f.kind == "pyspark.read":
            todas.append(("read", str(attrs.get("target") or ""), f))
        elif f.kind == "pyspark.write":
            op = "overwrite" if attrs.get("mode") == "overwrite" else "write"
            todas.append((op, str(attrs.get("target") or ""), f))
        elif f.kind == "sql.write_statement" and attrs.get("operation") in _SQL:
            todas.append((_SQL[attrs["operation"]], str(attrs.get("table") or ""), f))
    if not todas:
        return "operacao_nao_medida"
    com_alvo = [t for t in todas if t[1]]
    escolhidas = [t for t in com_alvo if _casa(t[1], recurso)] if com_alvo else todas
    if not escolhidas:
        return "operacao_nao_ligada_ao_recurso"
    por_operacao: dict[str, Fact] = {}
    for op, _alvo, f in escolhidas:
        por_operacao.setdefault(op, f)
    return sorted(por_operacao.items())


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


def _principal(facts: Sequence[Fact], grants: Sequence[Fact]) -> str | None:
    roles = {
        str((f.attrs or {}).get("role_arn") or "")
        for f in facts
        if f.kind == "iam.access_decision"
    }
    roles.discard("")
    if len(roles) == 1:
        return roles.pop()
    principais = {str((g.attrs or {}).get("principal") or "") for g in grants}
    principais -= {"", IAM_ALLOWED_PRINCIPALS}
    return principais.pop() if len(principais) == 1 else None


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
    # Tabela aberta a `IAM_ALLOWED_PRINCIPALS` com ALL e governada pelo IAM: falta de
    # grant do LF nao e a causa, e SF-LF-008 ja fala dela.
    if any(
        (g.attrs or {}).get("is_iam_allowed_principals") and (g.attrs or {}).get("has_all")
        for g in grants
    ):
        return []
    principal = _principal(facts, grants)
    if principal is None:
        return [_unresolved("principal_ambiguo", recurso, gatilho, operation=operacao)]
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
    operacoes = _operacoes(recurso, facts)
    if isinstance(operacoes, str):
        return [_unresolved(operacoes, recurso, gatilho)]
    modelo = _modelo(facts)
    if modelo not in {"fta", "fgac"}:
        return [_unresolved(modelo, recurso, gatilho)]
    saida: list[Fact] = []
    for operacao, origem in operacoes:
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


def build_missing_grant(facts: Sequence[Fact]) -> list[Fact]:
    """Deriva `lakeformation.missing_grant` da uniao dos facts. Sem `ERR-LF-001` no
    pool, devolve lista vazia: sem falha observada nao ha permissao ausente a afirmar."""
    lista = list(facts)
    gatilhos = [
        f
        for f in lista
        if f.kind == "error.signature_match" and (f.attrs or {}).get("signature_id") == GATILHO
    ]
    if not gatilhos:
        return []
    saida: dict[str, Fact] = {}
    recursos: dict[str, Fact] = {}
    for gatilho in gatilhos:
        recurso = _recurso_da_mensagem(gatilho) or _candidato_unico(lista)
        if recurso is None:
            recusa = _unresolved("recurso_ambiguo", "", gatilho)
            saida[recusa.id] = recusa
            continue
        recursos.setdefault(recurso, gatilho)
    for recurso, gatilho in recursos.items():
        for fact in _derivar(recurso, gatilho, lista):
            saida[fact.id] = fact
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
