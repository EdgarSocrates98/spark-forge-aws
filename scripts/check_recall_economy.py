#!/usr/bin/env python3
"""Gate de recall e economia do `ContextPack`.

## O que este gate decide, e o que ele recusa a decidir

`docs/harness/CODEINTEL-GAP.md` §14 marca tres linhas como NAO EXISTE -- corpus
de query, gold set com simbolo exigido, e gate de recall e economia -- e a linha
292 escreve a assimetria sem poder torna-la executavel:

    economia que omite o simbolo necessario e falha, nao sucesso

Este gate torna essa frase executavel. Ele decide UMA coisa e recusa outra:

- **DECIDE recall nominal.** Perguntado pelo nome do simbolo, o pack tem de
  entregar aquele simbolo. Piso duro em 100%. Se `buscar()` acha o no e o pack
  nao o entrega, o funil perdeu no caminho e isso e defeito.
- **REPORTA recall conceitual, sem piso.** Perguntado pelo titulo da regra --
  como um operador descreve o problema --, o pack recupera o simbolo? Medido em
  2026-09-02: **0 de 23**. O indice guarda NOME e o titulo descreve DEFEITO, e
  ninguem construiu a ponte entre os dois. Dar piso reprovaria capacidade que a
  SPEC nao promete; omitir esconderia o quanto falta.
- **RECUSA publicar razao de economia neste corpus.** Medido: o envelope fixo do
  pack e **840 bytes** e o corpus inteiro de uma fixture e **692**. Um pack nao
  pode custar menos que o proprio envelope, entao a razao que sairia daqui mede
  o piso do envelope e nao a economia do subsistema. Sai
  `economia.unresolved` com a medida que a destravaria -- e nao um numero
  vestido de veredito.

## Por que a recusa importa mais que o numero

Publicar "0.39x a favor de ler o arquivo" seria verdadeiro e enganoso: verdadeiro
porque foi medido, enganoso porque o denominador e um corpus de 692 bytes. A §10
daquele mesmo documento mediu **645x A FAVOR** do indice sobre um corpus de 479
arquivos. As duas medicoes nao se contradizem -- elas medem corpora de ordens de
grandeza diferentes, e citar uma sem a outra escolheria o resultado.

Uso:

    python scripts/check_recall_economy.py            # relatorio + gate
    python scripts/check_recall_economy.py --json     # so o JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sparkforge.economy.goldset import derivar_goldset, fora_do_alcance  # noqa: E402
from sparkforge.economy.recall import medir  # noqa: E402

# Piso de perguntas derivadas. E PISO e nao igualdade: cair significa que alguma
# regra perdeu ancoragem e e defeito; subir significa que uma regra nova ganhou
# fixture ancorada e e progresso. Igualdade pintaria de vermelho o proprio
# progresso -- e a armadilha que `check_surface_lock.py` resolve deixando
# crescer e obrigando a DECLARAR de quanto foi. O piso sobe no commit que o fez
# subir.
PISO_DE_PERGUNTAS = 27

# Recall nominal e 100%, sem excecao silenciosa.
RECALL_EXIGIDO = 1.0

# Recusas NOMEADAS, no molde de `SEM_MEDIDA` em `check_status_numbers.py`.
# Chave `<rule_id>@<fixture>`, valor `(razao, medida que destravaria)`.
#
# O gate falha nas DUAS direcoes: recall baixo fora desta lista, e item DESTA
# lista que passou. Recusa que curou e ninguem removeu e afirmacao falsa sobre o
# estado do sistema (regra 20).
SEM_RECALL: dict[str, tuple[str, str]] = {}

# O envelope fixo do pack, medido em 2026-09-02 sobre
# `fixtures/graph/connected_components_sem_checkpoint`: `index`, `query`,
# `metrics`, `security`, `unresolved`, `reductions`, `schema_version`,
# `runtime` e `rules` somam isto antes de qualquer simbolo entrar.
ENVELOPE_FIXO_BYTES = 840


def _relatorio() -> dict:
    perguntas = derivar_goldset()
    medidas = medir(perguntas)
    fora = fora_do_alcance()

    falhas_nominais = [m for m in medidas if not m.respondeu]
    curadas = [
        chave
        for chave in SEM_RECALL
        if any(m.chave == chave and m.respondeu for m in medidas)
    ]

    corpus_bytes = sum(m.bytes_arquivos for m in medidas)
    medivel = corpus_bytes > ENVELOPE_FIXO_BYTES * len(medidas)

    economia: dict[str, object] = {
        "bytes_pack": sum(m.bytes_pack for m in medidas),
        "bytes_arquivos": corpus_bytes,
        "bytes_grep": sum(m.bytes_grep for m in medidas),
        "bytes_por_nivel": {
            nivel: sum(m.bytes_por_nivel.get(nivel, 0) for m in medidas)
            for nivel in ("None", "summary", "full")
        },
        "envelope_fixo_bytes": ENVELOPE_FIXO_BYTES,
    }
    if not medivel:
        limiar = ENVELOPE_FIXO_BYTES * len(medidas)
        economia["limiar_bytes"] = limiar
        economia["razao_unresolved"] = (
            f"economia.unresolved -- o corpus do gold set tem {corpus_bytes} "
            f"bytes em {len(medidas)} fixtures, e o envelope fixo do pack custa "
            f"{ENVELOPE_FIXO_BYTES} bytes por chamada, {limiar} no total. Com "
            f"{corpus_bytes} < {limiar}, o pack nao pode custar menos que ler o "
            "corpus, porque o envelope sozinho ja o excede. Uma razao daqui "
            "mede o piso do envelope, nao a economia do subsistema."
        )
        economia["medida_que_destravaria"] = (
            "um corpus por fixture maior que o envelope -- ou a mesma medicao "
            "sobre a arvore do repositorio, como fez a secao 10 de "
            "docs/harness/CODEINTEL-GAP.md, que sobre 479 arquivos mediu 645x "
            "a favor do indice"
        )
    else:
        economia["contra_arquivos"] = round(
            corpus_bytes / max(economia["bytes_pack"], 1), 2
        )
        economia["contra_grep"] = round(
            economia["bytes_pack"] / max(economia["bytes_grep"], 1), 2
        )

    return {
        "perguntas": len(perguntas),
        "piso_de_perguntas": PISO_DE_PERGUNTAS,
        "regras_cobertas": len({p.rule_id for p in perguntas}),
        "recall_nominal": {
            "exigido": RECALL_EXIGIDO,
            "passou": len(medidas) - len(falhas_nominais),
            "de": len(medidas),
            "falhas": [
                {"chave": m.chave, "faltaram": list(m.faltaram), "erro": m.erro}
                for m in falhas_nominais
            ],
        },
        "recall_conceitual": {
            "piso": None,
            "passou": sum(1 for m in medidas if m.respondeu_conceitual),
            "de": len(medidas),
        },
        "economia": economia,
        "recusas_curadas": curadas,
        "fora_do_alcance": [
            {
                "chave": f"{f.rule_id}@{f.fixture}",
                "razao": f.razao,
                "extensoes": list(f.extensoes),
                "medida_que_destravaria": f.medida_que_destravaria,
            }
            for f in fora
        ],
    }


def _imprimir(rel: dict) -> None:
    print(f"perguntas derivadas .......... {rel['perguntas']} (piso {rel['piso_de_perguntas']})")
    print(f"regras cobertas .............. {rel['regras_cobertas']}")
    n = rel["recall_nominal"]
    print(f"recall NOMINAL (piso duro) ... {n['passou']}/{n['de']}")
    c = rel["recall_conceitual"]
    print(f"recall CONCEITUAL (sem piso) . {c['passou']}/{c['de']}")
    e = rel["economia"]
    if "razao_unresolved" in e:
        print("economia ..................... UNRESOLVED")
        print(f"  razao: {e['razao_unresolved']}")
        print(f"  destrava: {e['medida_que_destravaria']}")
    else:
        print(f"economia vs arquivos ......... {e['contra_arquivos']}x")
        print(f"economia vs grep ............. {e['contra_grep']}x")
    niveis = e["bytes_por_nivel"]
    print(f"bytes por detail_level ....... {niveis}")
    fora = rel["fora_do_alcance"]
    if fora:
        por_razao: dict[str, int] = {}
        for item in fora:
            por_razao[item["razao"]] = por_razao.get(item["razao"], 0) + 1
        print(f"fora do alcance .............. {len(fora)} {por_razao}")
    for falha in n["falhas"]:
        print(f"  FALHA {falha['chave']}: {falha['erro'] or falha['faltaram']}")
    for chave in rel["recusas_curadas"]:
        print(f"  RECUSA CURADA (remova de SEM_RECALL): {chave}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="so o JSON")
    args = parser.parse_args()

    rel = _relatorio()
    if args.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _imprimir(rel)

    problemas = 0
    if rel["perguntas"] < rel["piso_de_perguntas"]:
        print(
            f"\nERRO: {rel['perguntas']} perguntas, piso {rel['piso_de_perguntas']}. "
            "Alguma regra perdeu ancoragem de simbolo.",
            file=sys.stderr,
        )
        problemas += 1
    for falha in rel["recall_nominal"]["falhas"]:
        if falha["chave"] not in SEM_RECALL:
            print(
                f"\nERRO: recall nominal falhou em {falha['chave']} e ela NAO esta "
                "em SEM_RECALL. Ou o funil regrediu, ou a recusa precisa ser "
                "declarada com a razao e a medida que a destravaria.",
                file=sys.stderr,
            )
            problemas += 1
    for chave in rel["recusas_curadas"]:
        print(
            f"\nERRO: {chave} esta em SEM_RECALL e PASSOU. Recusa que curou e "
            "afirmacao falsa sobre o estado do sistema -- remova a entrada.",
            file=sys.stderr,
        )
        problemas += 1

    print(f"\n{problemas} problema(s).")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
