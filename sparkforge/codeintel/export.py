"""Exportacao do grafo de codigo no formato de EXTRACAO que a fonte publica.

## A medicao que decidiu a forma desta entrega

`prompt_evo_graph_economy.md` pede um `GraphifyJsonAdapter` que importe e exporte
o `graph.json` do Graphify. Medido em 2026-09-02, sobre a `v8` do repositorio
oficial:

| Fonte | O que ela diz sobre `graph.json` |
|---|---|
| `README.md` | *"the full graph -- query it anytime without re-reading your files"*. Sem schema. |
| `ARCHITECTURE.md` | Publica o schema da EXTRACAO, e diz literalmente que
  ele e o formato intermediario -- *"before `build()` processes it"* --, e
  nao o arquivo final |
| `pyproject.toml` | Apache-2.0, versao **0.9.53**, Python >=3.10 |

**O formato do arquivo final nao e publicado.** Escrever um adaptador contra ele
seria inventar o formato e chamar isso de compatibilidade -- e um JSON que a
ferramenta de destino nao le nao e compatibilidade, e um segundo formato com nome
emprestado.

Entao esta modulo exporta o que a fonte DE FATO publica: o formato de extracao,
com os campos que o `ARCHITECTURE.md` nomeia.

    no:     id, label, source_file, source_location
    aresta: source, target, relation, confidence

## O que este modulo NAO faz, e por que

**Nao importa.** Importar exigiria conhecer o formato de saida do Graphify, que e
o que a medicao acima nao achou. Um importador que aceitasse o formato de
extracao aceitaria um artefato que o Graphify nao produz como arquivo -- ele o
passa adiante para `build()`.

**Nao ha dependencia de `graphifyy`.** A versao 0.9.53 traz 29 dependencias
obrigatorias -- `networkx`, `numpy`, `rapidfuzz` e 26 gramaticas `tree-sitter` --
e 28 extras. O wheel minimo deste projeto tem DUAS. A compatibilidade aqui e de
FORMATO, nunca de codigo: nada e copiado, e nada e importado.

**`confidence` sai sempre `EXTRACTED`, e isso e afirmacao e nao preguica.** A
fonte publica dois valores, `EXTRACTED` (explicito no fonte) e `INFERRED`
(derivado por resolucao). Toda aresta que este indice guarda veio de
`resolve.resolver` sobre uma chamada que EXISTE no fonte -- o que ele nao
conseguiu resolver virou `unresolved_refs` e nao e aresta. Marcar `INFERRED`
alguma delas seria afirmar uma inferencia que nao houve.
"""

from __future__ import annotations

import json
import os
from typing import Any

from sparkforge.codeintel.db import abrir
from sparkforge.codeintel.graph import (
    _CALLS,
    _SQL_ARESTAS,
    _SQL_TODOS_OS_NOS,
    comunidades,
)

# A versao da fonte contra a qual os NOMES DE CAMPO abaixo foram conferidos.
# Fica no artefato exportado para que quem o leia daqui a um ano saiba contra o
# que a compatibilidade foi medida -- e para que uma divergencia futura tenha um
# ponto de partida em vez de uma discussao.
FONTE_CONFERIDA = "Graphify-Labs/graphify@v8, pyproject 0.9.53, lido 2026-09-02"

SCHEMA_VERSION = 1

# `EXTRACTED` para toda aresta, e a razao esta na docstring do modulo: o que a
# resolucao nao conseguiu ligar virou `unresolved_refs` e nao chegou aqui.
_CONFIANCA = "EXTRACTED"

# `calls` e o unico `relation` que este indice produz hoje. A tabela `edges` ja
# aceita outros tipos, e quando houver `imports` ele entra aqui -- por enquanto,
# declarar mais seria prometer aresta que nada emite.
_RELACAO = "calls"


def exportar(
    banco: str | os.PathLike[str],
    incluir_comunidades: bool = True,
    kind: str = _CALLS,
) -> dict[str, Any]:
    """O grafo no formato de extracao da fonte, mais o que este motor acrescenta.

    ## Os campos da fonte, e os deste motor, ficam SEPARADOS

    `nodes` e `edges` usam os nomes que o `ARCHITECTURE.md` publica, e nada mais.
    O que este motor sabe e a fonte nao nomeia -- `qualified_name`, `kind` de
    simbolo, a particao em comunidades -- vive em `sparkforge`, um bloco proprio.

    Misturar os dois produziria um artefato que se parece com o da fonte e nao e:
    quem o lesse assumiria que todo campo veio de la. A separacao e o que torna a
    tabela de compatibilidade conferivel em vez de prosa.

    ## `source_location` e a LINHA, e nao um intervalo

    A fonte escreve `"routing.py L2210"` no exemplo dela -- uma linha so. Este
    indice tem `start_line` e nada mais, entao os dois coincidem. Se um dia
    houver `end_line`, ele entra em `sparkforge` e nao aqui.
    """
    conexao = abrir(banco)
    try:
        linhas = conexao.execute(_SQL_TODOS_OS_NOS).fetchall()
        arestas = conexao.execute(_SQL_ARESTAS, (kind,)).fetchall()
    finally:
        conexao.close()

    por_no = {
        linha[0]: {
            # --- campos que a fonte nomeia ---
            "id": linha[0],
            "label": linha[1],
            "source_file": linha[4],
            "source_location": linha[5],
            # --- o que este motor sabe e a fonte nao nomeia ---
            "sparkforge": {
                "qualified_name": linha[2],
                "kind": linha[3],
            },
        }
        for linha in linhas
    }

    if incluir_comunidades:
        particao = comunidades(banco, kind=kind)
        for comunidade in particao.comunidades:
            for no in comunidade.nos:
                if no.node_id in por_no:
                    por_no[no.node_id]["sparkforge"]["community"] = comunidade.rotulo
        meta_particao: dict[str, Any] = {
            "algorithm": particao.algoritmo,
            "total": particao.total,
            "converged": particao.convergiu,
        }
    else:
        meta_particao = {"algorithm": None, "total": 0, "converged": None}

    return {
        "schema_version": SCHEMA_VERSION,
        # A ordem e `id`, que e determinista e nao depende do plano do SQLite.
        "nodes": [por_no[chave] for chave in sorted(por_no)],
        "edges": [
            {
                "source": str(origem),
                "target": str(destino),
                "relation": _RELACAO,
                "confidence": _CONFIANCA,
            }
            for origem, destino in sorted((str(a), str(b)) for a, b in arestas)
        ],
        "sparkforge": {
            "format": "graphify-extraction-compatible",
            # As DUAS metades da compatibilidade, na mesma estrutura: o que casa
            # e o que nao existe. Um artefato que so declarasse a primeira
            # metade convidaria quem o le a assumir a segunda.
            "source_checked": FONTE_CONFERIDA,
            "compatible_fields": {
                "nodes": ["id", "label", "source_file", "source_location"],
                "edges": ["source", "target", "relation", "confidence"],
            },
            "not_from_source": (
                "tudo dentro de `sparkforge`, em cada no e neste bloco: "
                "`qualified_name`, `kind` e `community` nao sao campos que a "
                "fonte nomeie"
            ),
            "not_implemented": (
                "importacao. O formato do `graph.json` FINAL do Graphify nao e "
                "publicado -- o README nao o especifica e o ARCHITECTURE.md diz "
                "que o schema que ele mostra e o da extracao, anterior a "
                "`build()`. Um importador exigiria adivinhar o formato de "
                "destino."
            ),
            "communities": meta_particao,
        },
    }


def exportar_json(
    banco: str | os.PathLike[str],
    incluir_comunidades: bool = True,
    kind: str = _CALLS,
) -> str:
    """`exportar` serializado de forma DETERMINISTICA.

    `sort_keys=True` porque o artefato pode entrar em golden: sem ele, a ordem
    das chaves seria a de insercao, e reordenar uma linha do `dict` mudaria os
    bytes sem mudar o conteudo.

    `ensure_ascii=False` porque um `label` acentuado -- e este repositorio tem
    nome de simbolo em portugues -- sairia como escape `\\uXXXX`, ilegivel para
    quem abrir o arquivo.
    """
    return json.dumps(
        exportar(banco, incluir_comunidades=incluir_comunidades, kind=kind),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


__all__ = [
    "FONTE_CONFERIDA",
    "SCHEMA_VERSION",
    "exportar",
    "exportar_json",
]
