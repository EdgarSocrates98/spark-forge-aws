"""O footer do Parquet vira fact -- e a sobreposicao de min/max vira numero.

Le SO o artefato que `sparkforge/collect/parquet_footer.py` gravou. Nunca abre
arquivo Parquet, nunca importa pyarrow: quem roda `judge` sobre um artefato ja
coletado nao precisa da dependencia opcional, e e por isso que a leitura do
footer e a extracao de fact sao dois modulos.

## POR QUE ELE EXISTE, MEDIDO

`knowledge/storage/parquet-layout.md` §2 ja afirma o que decide performance:

> Estatistica min/max so e util se os valores estiverem AGRUPADOS. Dado
> ordenado aleatoriamente faz cada row group ter min/max cobrindo quase todo o
> dominio -> nenhum row group pode ser descartado -> pruning inutil apesar de
> existir estatistica.

Medido em 2026-09-09, antes deste modulo: ZERO kind `parquet.*` entre os 195 que
os extratores declaram. As cinco regras de `SF-PQ` julgavam por
`s3.prefix_summary` (tamanho de arquivo, da listagem) e por `plan.file_scan`
(filtros DECLARADOS no plano) -- nenhuma abria um arquivo. O conhecimento estava
escrito e o motor nao o media.

O modo de falha que isso produz e especifico e caro: arquivos de 512 MB passam
por `SF-PQ-001`, ha `PartitionFilters` no plano e passa por `SF-PQ-002`, e a
leitura le a tabela inteira -- porque os row groups nao podem ser descartados.

## `parquet.column_chunk` NAO EXISTE, e a ausencia e decisao

Um arquivo com 100 row groups e 50 colunas produziria 5000 facts que nao decidem
nada sozinhos, e `facts.json` e barramento de handoff COMMITADO. O que decide e
o perfil AGREGADO por coluna, no molde de `iceberg.files_summary` e de
`spark.job.spill_summary`.

## A medida, e o que ela NAO e

`avg_range_coverage` e a media, sobre os row groups, de
`(max_rg - min_rg) / (max_global - min_global)`:

  ~1/N  dado agrupado; cada row group cobre a sua fatia, e o pruning funciona
  ~1.0  dado espalhado; cada row group cobre quase todo o dominio, e NENHUM
        pode ser descartado -- pruning inutil apesar de a estatistica existir

`expected_row_groups_scanned` e ela vezes o numero de row groups: quantos um
predicado de igualdade NAO consegue descartar.

**Ela assume o predicado UNIFORMEMENTE DISTRIBUIDO sobre o dominio observado.**
E propriedade do LAYOUT, nao previsao do job: um filtro que sempre pede o ultimo
dia de uma tabela ordenada por data le pouco mesmo com cobertura alta. Ela
nomeia layout que NAO PODE podar, nunca job que VAI ler muito. Quem cruza a
medida com a coluna realmente filtrada e a regra, nao este modulo.

## As quatro recusas, e por que sao quatro

As quatro produzem a MESMA ausencia de `avg_range_coverage`, e colapsa-las numa
razao so seria uma recusa que nao nomeia nada (regra 20 do `CLAUDE.md`):

  tipo_sem_dominio_numerico  min/max lexicografico de string produziria um
                             numero com cara de medida e sem significado de
                             distancia
  estatistica_incompleta     falta min/max em ao menos um row group -- a media
                             sobre os que tem afirmaria sobre o arquivo inteiro
  row_group_unico            nao ha o que descartar, e sem esta razao o caso
                             cairia em cobertura 1.0, indistinguivel de dado
                             espalhado
  dominio_degenerado         coluna constante: largura zero, e a divisao nao
                             existe
"""

from __future__ import annotations

import json
import numbers
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "parquet_footer@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "parquet.file",
        "parquet.row_group",
        "parquet.column_profile",
        "parquet.footer_analyzed",
        "parquet.unresolved",
    }
)

# Razoes que o COLETOR grava em `status` e que este modulo traduz. Sao os
# estados que produzem a mesma lista vazia de arquivos e que o operador precisa
# distinguir -- mesmo desenho de `cloudwatch_logs.py`.
_RECUSA_DO_COLETOR = {
    "prefixo_inexistente": "o prefixo nao existe",
    "prefixo_vazio": "o prefixo existe e nao tem arquivo Parquet",
    "sem_permissao": "a leitura foi negada",
    "sem_credencial": "a requisicao nunca saiu",
    "pyarrow_indisponivel": "a dependencia opcional de leitura do footer falta",
}

# Tipos fisicos do Parquet cuja distancia entre dois valores e definida. A lista
# e do formato, nao heuristica: `BYTE_ARRAY` e `FIXED_LEN_BYTE_ARRAY` carregam
# string e binario, e para eles min/max ordenam mas nao MEDEM.
_TIPOS_COM_DOMINIO = frozenset(
    {"INT32", "INT64", "INT96", "FLOAT", "DOUBLE"}
)


def _provenance(path: str) -> dict[str, Any]:
    return {"extractor": EXTRACTOR_ID, "artifact": path}


def _unresolved(
    subject: dict[str, Any], reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="parquet.unresolved",
        subject=dict(subject),
        measures={},
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def extract_parquet_footer(payload: dict[str, Any], path: str) -> list[Fact]:
    """Extrai Facts do conteudo ja carregado de um artefato de footer."""
    provenance = _provenance(path)
    prefixo = str(payload.get("prefix") or "")
    arquivos = list(payload.get("files") or [])
    status = str(payload.get("status") or "ok")

    # `type: table` e nao um tipo proprio: o enum de `subject.type` do
    # `fact.schema.json` e FECHADO, e `s3.prefix_summary` -- o fact mais proximo
    # deste, tambem sobre um prefixo -- ja usa `table`. Um prefixo de dado E a
    # tabela, na pratica, e inventar um oitavo tipo para dizer a mesma coisa
    # dividiria a convencao em duas.
    escopo = {"type": "table", "symbol": prefixo, "file": path}
    facts: list[Fact] = []

    vistos = int(payload.get("files_seen") or 0)
    lidos = int(payload.get("files_read") or len(arquivos))
    # Codecs do PREFIXO, e nao de um arquivo. E aqui que a divergencia entre
    # arquivos e observavel: `parquet.column_profile` agrega sobre os row groups
    # de UM arquivo, e dois arquivos escritos por caminhos diferentes so se
    # comparam no escopo que os contem.
    codecs_do_prefixo = sorted(
        {
            str(coluna.get("compression") or "")
            for arquivo in arquivos
            for grupo in (arquivo.get("row_groups") or [])
            for coluna in (grupo.get("columns") or [])
            if coluna.get("compression")
        }
    )
    facts.append(
        Fact(
            kind="parquet.footer_analyzed",
            subject=dict(escopo),
            measures={
                "files_seen": float(vistos),
                "files_read": float(lidos),
                "row_groups_read": float(
                    sum(len(a.get("row_groups") or []) for a in arquivos)
                ),
                "distinct_codecs": float(len(codecs_do_prefixo)),
            },
            attrs={
                "prefix": prefixo,
                "codecs": codecs_do_prefixo,
                "sampling": payload.get("sampling"),
                "max_files": payload.get("max_files"),
                "status": status,
                # `partial` e derivado e nao copiado: o operador le UM booleano,
                # em vez de comparar dois numeros para descobrir se o censo
                # cobre a tabela.
                "partial": bool(vistos and lidos < vistos),
            },
            provenance=provenance,
        )
    )

    if status in _RECUSA_DO_COLETOR:
        facts.append(
            _unresolved(escopo, status, provenance, detail=_RECUSA_DO_COLETOR[status])
        )
        return sort_facts(facts)

    for arquivo in arquivos:
        facts.extend(_do_arquivo(arquivo, prefixo, path, provenance))
    return sort_facts(facts)


def _do_arquivo(
    arquivo: dict[str, Any], prefixo: str, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    nome = str(arquivo.get("path") or "")
    # `type: source_location` e nao `table`: aqui o sujeito e UM ARQUIVO, e o
    # molde e `mig.jar_binary`, que tambem aponta para um artefato binario no
    # disco. O prefixo que os contem e `table`, no censo -- os dois escopos
    # existem e sao diferentes.
    subject = {
        "type": "source_location",
        "file": nome,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }
    grupos = list(arquivo.get("row_groups") or [])
    facts: list[Fact] = [
        Fact(
            kind="parquet.file",
            subject=dict(subject),
            measures={
                "file_bytes": float(arquivo.get("file_bytes") or 0),
                "num_rows": float(arquivo.get("num_rows") or 0),
                "num_row_groups": float(len(grupos)),
                "num_columns": float(arquivo.get("num_columns") or 0),
            },
            attrs={
                "prefix": prefixo,
                "created_by": arquivo.get("created_by"),
                "format_version": arquivo.get("format_version"),
            },
            provenance=provenance,
        )
    ]

    for grupo in grupos:
        facts.append(
            Fact(
                kind="parquet.row_group",
                subject={**subject, "row_group": int(grupo.get("index") or 0)},
                measures={
                    "num_rows": float(grupo.get("num_rows") or 0),
                    "total_byte_size": float(grupo.get("total_byte_size") or 0),
                    "num_columns": float(len(grupo.get("columns") or [])),
                },
                # `total_byte_size` do Parquet e DESCOMPRIMIDO, e o split de
                # leitura do Spark fatia bytes do arquivo. O comprimido e a soma
                # das colunas, e mora em `attrs` de proposito: `Fact.id` e hash
                # de kind + subject + measures, e nenhum finding que cita row
                # group muda de evidencia por causa desta chave.
                attrs={
                    "prefix": prefixo,
                    "total_compressed_bytes": sum(
                        int(coluna.get("total_compressed_size") or 0)
                        for coluna in grupo.get("columns") or []
                    ),
                },
                provenance=provenance,
            )
        )

    facts.extend(_perfis(grupos, subject, prefixo, provenance))
    return facts


def _perfis(
    grupos: Sequence[dict[str, Any]],
    subject: dict[str, Any],
    prefixo: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    """Um `parquet.column_profile` por coluna, agregado sobre os row groups."""
    por_coluna: dict[str, list[dict[str, Any]]] = {}
    for grupo in grupos:
        for coluna in grupo.get("columns") or []:
            por_coluna.setdefault(str(coluna.get("path") or ""), []).append(coluna)

    facts: list[Fact] = []
    for nome, chunks in por_coluna.items():
        alvo = {**subject, "column": nome}
        total = len(chunks)
        comprimido = sum(float(c.get("total_compressed_size") or 0) for c in chunks)
        descomprimido = sum(float(c.get("total_uncompressed_size") or 0) for c in chunks)
        valores = sum(float(c.get("num_values") or 0) for c in chunks)
        nulos = sum(float(c.get("null_count") or 0) for c in chunks)

        measures: dict[str, float] = {
            "num_row_groups": float(total),
            "total_byte_size": comprimido,
            "stats_coverage": _fracao(chunks, lambda c: bool(c.get("is_stats_set"))),
            "min_max_coverage": _fracao(chunks, lambda c: bool(c.get("has_min_max"))),
            "dictionary_coverage": _fracao(
                chunks, lambda c: bool(c.get("has_dictionary_page"))
            ),
            # Page index sao DOIS indices, e um sem o outro nao serve: o column
            # index traz as estatisticas por pagina, o offset index diz onde
            # cada pagina comeca. Exigir os dois e o que o formato exige.
            "page_index_coverage": _fracao(
                chunks,
                lambda c: bool(c.get("has_column_index"))
                and bool(c.get("has_offset_index")),
            ),
            "bloom_coverage": _fracao(
                chunks, lambda c: c.get("bloom_filter_offset") is not None
            ),
        }
        if comprimido:
            measures["compression_ratio"] = descomprimido / comprimido
        if valores:
            measures["null_fraction"] = nulos / valores

        # Contagem como MEDIDA, e nao so a lista em `attrs`: o avaliador de
        # `expr` do catalogo nao aceita chamada de funcao (`len(...)` e no
        # `Call`, recusado por `rules/expr.py`), entao uma regra que precise
        # comparar "quantos codecs" precisa do numero pronto. E aritmetica sobre
        # o footer, nao juizo.
        codecs = sorted(
            {str(c.get("compression") or "") for c in chunks if c.get("compression")}
        )
        measures["distinct_codecs"] = float(len(codecs))

        cobertura, recusa = _cobertura_de_faixa(chunks)
        if cobertura is not None:
            measures["avg_range_coverage"] = cobertura
            measures["expected_row_groups_scanned"] = cobertura * total

        facts.append(
            Fact(
                kind="parquet.column_profile",
                subject=alvo,
                measures=measures,
                attrs={
                    "prefix": prefixo,
                    "column": nome,
                    "physical_type": chunks[0].get("physical_type"),
                    # Lista e nao string: mais de um codec na mesma coluna e
                    # sinal proprio, e achatar para o primeiro o apagaria. A
                    # CONTAGEM vai em `measures` porque e la que a regra a
                    # compara.
                    "codecs": codecs,
                    "encodings": sorted(
                        {e for c in chunks for e in (c.get("encodings") or [])}
                    ),
                },
                provenance=provenance,
            )
        )
        if recusa is not None:
            facts.append(_unresolved(alvo, recusa, provenance, column=nome))
    return facts


def _fracao(chunks: Sequence[dict[str, Any]], predicado) -> float:
    return sum(1 for c in chunks if predicado(c)) / len(chunks) if chunks else 0.0


def _cobertura_de_faixa(
    chunks: Sequence[dict[str, Any]],
) -> tuple[float | None, str | None]:
    """A medida do §2 do `knowledge/`, ou a razao de ela nao existir.

    A ORDEM das guardas e o contrato, e ela vai da propriedade mais estrutural
    para a mais dependente do dado: tipo primeiro (nao depende de valor nenhum),
    depois estatistica, depois contagem de row groups, e so entao o dominio.
    Invertida, um arquivo de uma coluna string com um row group so sairia como
    `row_group_unico` -- verdadeiro, e nao o que impede a medida.
    """
    tipo = str(chunks[0].get("physical_type") or "")
    if tipo not in _TIPOS_COM_DOMINIO:
        return None, "tipo_sem_dominio_numerico"
    if not all(c.get("has_min_max") and c.get("is_stats_set") for c in chunks):
        return None, "estatistica_incompleta"
    if len(chunks) < 2:
        return None, "row_group_unico"

    minimos = [c.get("min") for c in chunks]
    maximos = [c.get("max") for c in chunks]
    if not all(isinstance(v, numbers.Real) for v in (*minimos, *maximos)):
        # O tipo fisico diz numerico e o valor nao e: artefato de coletor de
        # outra versao, ou dump editado a mao. Recusa em vez de `TypeError`.
        return None, "estatistica_incompleta"

    largura = float(max(maximos)) - float(min(minimos))
    if largura <= 0:
        return None, "dominio_degenerado"

    coberturas = [
        (float(c.get("max")) - float(c.get("min"))) / largura for c in chunks
    ]
    return sum(coberturas) / len(coberturas), None


def extract_parquet_footer_path(path: Path) -> list[Fact]:
    """Le o artefato do disco e delega para `extract_parquet_footer`.

    Existe pela convencao do repositorio (`extract_*_path` em todo extrator de
    artefato) e por uma razao medida: `tests/test_harness_untrusted.py` varre os
    modulos de `facts/` procurando `extract*_path` e `extract*_tree` para
    exercitar a medida de snippet, e um extrator cuja unica funcao recebe
    `payload` fica de fora da varredura -- ele conta como "sem snippet" sem ter
    rodado nada.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return extract_parquet_footer(payload, str(path))


def extract_parquet_footer_tree(
    directory: Path, repo_root: Path | None = None
) -> list[Fact]:
    """Todos os `*.json` de um diretorio, na ordem do nome.

    Existe para o caso do operador que coletou VARIOS prefixos: os artefatos sao
    separados, e ler os dois e uma chamada so em vez de duas. Mesma forma de
    `extract_cloudwatch_logs_tree`.

    `iter_source_files` e nao `rglob` cru: a varredura da casa tem denylist e
    ordem estavel, e `tests/test_facts_scan.py` e o gate estrutural que impede a
    porta de entrada sem ela.
    """
    raiz = Path(repo_root or directory)
    facts: list[Fact] = []
    for arquivo in iter_source_files(directory, "*.json"):
        try:
            rel = str(arquivo.relative_to(raiz))
        except ValueError:
            rel = str(arquivo)
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
        facts.extend(extract_parquet_footer(payload, rel.replace("\\", "/")))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_parquet_footer",
    "extract_parquet_footer_path",
    "extract_parquet_footer_tree",
]
