# Receita — o que vale escanear neste repositório?

**O quê:** `sparkforge-aws scan` roda sozinho os `analyze` kinds que cabem
num repositório.
**Por que:** você não precisa saber quais extractors aplicar — o scan decide
pelos arquivos presentes.
**Quando:** primeiro contato com um repo legado Glue/EMR/Spark.
**Quando não:** você já sabe o kind — `analyze <kind>` direto é mais barato.

## Problema

"Repo desconhecido com jobs espalhados — por onde começo?"

## Passo a passo

```bash
sparkforge-aws scan --path .
```

## Saída esperada / interpretação

Facts agregados dos kinds detectados + quais analyzers rodaram — use para
decidir os próximos `analyze`/`judge` direcionados.

## Verificação

Cruzamento com `analyze <kind>` num subdiretório deve produzir subconjunto
consistente dos facts.

## Limitações

Descoberta por presença de arquivo — não executa nem infere runtime;
repos enormes pedem `--path` mais estreito.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| nenhum analyzer rodou | nenhum kind detectado | repo sem artefatos Spark/Glue |
| lento em monorepo | escopo amplo | `--path` num módulo |

## Uso por agentes

Primeiro passo barato de discovery; o relatório guia skills específicas
(`skills/` — glue, EMR, Spark 4, Iceberg…).
