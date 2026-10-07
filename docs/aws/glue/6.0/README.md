# AWS Glue 6.0 no SparkForge

Porta de entrada para o que este repositório sabe sobre o Glue 6.0 — e, tão importante
quanto, para o que ele **não** sabe.

Nenhum número desta pasta é copiado de outro lugar. Onde houver uma versão, uma contagem ou
uma medição, o texto aponta para o arquivo que a sustenta. Número copiado apodrece em
silêncio; ponteiro não. Foi uma auditoria inteira de alegação sem lastro que fixou essa
regra aqui — ver [`../../../gates-por-mudanca.md`](../../../gates-por-mudanca.md).

## O que o SparkForge sabe hoje

O conhecimento sobre Glue 6.0 entra neste repositório em três formas, e a diferença entre
elas decide o que a ferramenta consegue fazer:

| Forma | Onde vive | O que ela permite |
|---|---|---|
| **Dado com fonte** | `knowledge/glue/runtime-matrix.yaml`, `knowledge/storage/iceberg-feature-support.yaml` | consulta programática, guarda de versão, gate que recusa afirmação sem procedência |
| **Prosa com fonte** | `knowledge/glue/*.md`, `knowledge/spark/spark4-migration.md`, `knowledge/storage/iceberg-v3.md` | leitura humana e contexto de agente; não é consultável nem gateada por si só |
| **Regra executável** | `rules/catalog/glue-migration.yaml`, `spark4.yaml`, `lakeformation.yaml` | julgamento determinístico sobre facts extraídos, com `rule_id`, severidade, guarda de versão e fonte |

Prosa que nunca virou dado nem regra continua sendo conhecimento — não capacidade. Essa
distinção é o eixo de [`known-unknowns.md`](known-unknowns.md).

## Mapa

| Documento | Responde |
|---|---|
| [`runtime.md`](runtime.md) | o que o Glue 6.0 empacota, de onde esse fato vem, e o que a forma longa de componente impede |
| [`spark4.md`](spark4.md) | a fronteira do Apache Spark 4 — o que é detectável estaticamente e o que só aparece em execução |
| [`iceberg.md`](iceberg.md) | Iceberg e a spec v3, com feature-da-spec separada de suporte-da-engine |
| [`lakeformation.md`](lakeformation.md) | FGAC: o que exige, o que proíbe, o que custa em capacidade |
| [`testing.md`](testing.md) | como este repositório **prova** o que afirma sobre Glue 6.0 |
| [`known-unknowns.md`](known-unknowns.md) | o que o SparkForge não sabe e não finge saber |
| [`decision-guide.md`](decision-guide.md) | migrar ou não, e como decidir sem escolher pela versão mais nova |

## Áreas de regra que julgam um alvo Glue 6.0

- `SF-MIG` — migração entre versões de Glue, em `rules/catalog/glue-migration.yaml`.
- `SF-SPARK4` — fronteira do Apache Spark 4, em `rules/catalog/spark4.yaml`, guardada por
  versão de **Spark**.
- `SF-LF` — Lake Formation com controle de acesso fino, em
  `rules/catalog/lakeformation.yaml`.
- `SF-ENV` — armadilhas entre serviços, incluindo a de formato de tabela contra consumidor.

O catálogo inteiro, com a contagem corrente por área, está em
[`../../../../rules/catalog/README.md`](../../../../rules/catalog/README.md). Esta página
não repete esse número: ele já apodreceu mais de uma vez em documento que o copiava.

## Registro de decisão

As decisões que produziram esta pasta — conhecimento como dado versionado, guarda por Spark
contra guarda por Glue, `UNKNOWN` por construção, e por que as skills de Glue 6 não foram
criadas — estão no ADR
[`../../../vnext/adrs/ADR-009-glue-6-spark-4-iceberg-v3.md`](../../../vnext/adrs/ADR-009-glue-6-spark-4-iceberg-v3.md).
