# O runtime do Glue 6.0

## A fonte é o YAML, não este documento

O que o Glue 6.0 empacota — Spark, Python, Scala, Java e Iceberg — vive em
[`../../../../knowledge/glue/runtime-matrix.yaml`](../../../../knowledge/glue/runtime-matrix.yaml),
com `sources` e `retrieved` por versão. A prosa que acompanha está em
[`../../../../knowledge/glue/runtime-matrix.md`](../../../../knowledge/glue/runtime-matrix.md).

Este documento **não repete nenhuma dessas versões**. A razão não é estilo: versão de
runtime é fato externo, muda por decisão da AWS e não deste repositório, e cada cópia dela
num documento é mais um lugar que envelhece sem que nada acuse. O YAML é o único lugar que
carrega fonte e data ao lado do valor.

O carregador é `sparkforge/facts/runtime_matrix.py`. Não existe mais matriz compilada em
Python: `tests/test_runtime_matrix.py::TestSemVersaoNoCodigo` proíbe versão de Glue escrita
no código fora do carregador.

## Forma longa de componente

Um componente pode ser escrito de duas formas no YAML:

- **Escalar** — `spark: "<versão>"`. Uma afirmação sem disputa.
- **Registro longo** — `status` mais `claims`, e cada claim carrega `value`, `source`,
  `source_type` e `retrieved`. Uma afirmação **com** a evidência que a sustenta, fonte a
  fonte.

O `status` é o que decide o que o motor faz com o componente:

| `status` | O que o carregador faz |
|---|---|
| `VERIFIED` | resolve para o valor único; estoura se as fontes registradas discordarem |
| `CONFLICTING` | **retém** o valor; estoura se as fontes registradas concordarem |
| `UNRESOLVED` | retém o valor |

`STALE` e `UNVERIFIED` são recusados de propósito: os dois afirmam frescor, e frescor
depende de TTL por domínio, que não existe neste repositório — ver
[`known-unknowns.md`](known-unknowns.md).

## O que a forma longa impede

**Impede escolher.** Quando duas fontes oficiais discordam sobre um componente, o carregador
não elege a mais autoritativa nem a mais recente: ele retém o valor. Componente retido não
resolve, `in_scope` reprova toda regra guardada por ele, e o motor reporta essas regras como
**puladas, com motivo**, em vez de julgá-las com um número que as fontes não confirmam
juntas. A consequência é medida por
`tests/test_runtime_matrix.py::TestComponenteEmDisputaNaoJulgaRegra`.

**Impede etiqueta sem consequência.** O ranking de autoridade de fonte
(`runtime_matrix.SOURCE_TYPES`, vocabulário fechado) *explica* a discordância; não a apaga.
Quem retém o valor continua sendo o `status`.

**Impede fonte inventada.** Toda URL citada por uma linha da matriz — na lista `sources` e
dentro de cada `claim` — precisa estar em `knowledge/sources.lock.json`, com data de
recuperação. É teste próprio, não convenção.

Vale ler o cabeçalho do próprio YAML antes de mexer nele: ele registra, no comentário do
componente `python` do Glue 6.0, uma divergência entre fontes que foi **procurada e não se
reproduziu** — as três fontes oficiais lidas concordam. O registro ficou `VERIFIED` com as
três, e não um `CONFLICTING` inventado para exercitar o mecanismo, que o próprio carregador
recusaria.

## O que a matriz alimenta

- **Guarda de versão das regras.** Todo `runtime_scope` de `rules/catalog/*.yaml` é
  comparado contra o que a matriz resolve. Regra guardada por `spark` e regra guardada por
  `glue` são coisas diferentes — ver [`spark4.md`](spark4.md).
- **Expansão do caminho de migração.** `sparkforge/migration/version_path.py:steps()` deriva
  os degraus da **ordem das versões na matriz**, sem par de versão escrito no código.
  Acrescentar uma versão muda o conjunto de degraus de todo par que a atravessa.
- **Avaliação por degrau.** `sparkforge/migration/assessment.py:assess()` chama o julgamento
  uma vez por degrau, com o runtime daquele degrau vindo da matriz, e agrega em `findings`,
  `by_step` e `report()`.

Antes de editar o YAML, leia a seção *Alterar `knowledge/glue/runtime-matrix.yaml`* de
[`../../../gates-por-mudanca.md`](../../../gates-por-mudanca.md): a lista de gates que uma
versão nova derruba não é óbvia a partir do diff.
