# Receita — fatos determinísticos de código PySpark

**O quê:** `sparkforge-aws analyze pyspark --path <dir>` extrai facts por AST
— reads, writes, SQL, APIs — com provenance sha256 por artefato.
**Por que:** migração Spark 4 / Glue 6 começa por inventário factual, não
grep.
**Quando:** assessment offline de jobs; input de `judge`/playbooks.
**Quando não:** análise de runtime/EMR real — facts são estáticos; collectors
AWS são outro caminho (e pedem credencial).

## Problema

"O que este job lê, escreve e quais APIs usa — sem rodá-lo?"

## Pré-requisitos

`sparkforge-aws` instalado; um `.py` ou diretório com jobs PySpark.

## Passo a passo

```bash
sparkforge-aws analyze pyspark --path jobs/
```

## Saída esperada / interpretação

Facts JSON por arquivo: `api` (ex.: `dataframe_writer_v1`), `target`,
`provenance.extractor` + `artifact_sha256` — evidência citável. Saída real
observada em `the-forge task run` (delegação): extração em ~800ms com
`extractor: pyspark_ast@0.1.0`.

## Verificação

O campo `artifact_sha256` do fact casa com o sha256 do arquivo analisado —
re-rodar no mesmo input produz facts idênticos.

## Limitações

Extratores por *kind* — `analyze` cobre só os kinds com extractor
implementado (`analyze --help` lista). Sem fluxo de dados inter-arquivo.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `unknown kind` | kind sem extractor | `analyze --help` lista os válidos |
| facts vazios | path sem `.py` | aponte o dir com os jobs |

## Uso por agentes

Workflow `analyze-pyspark` do `forge.agentic.json` — o the-forge delega este
argv exato via `task run`.
