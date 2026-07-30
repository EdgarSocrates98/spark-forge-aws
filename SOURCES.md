# Fontes oficiais de referência

A base deve ser atualizada periodicamente com documentação oficial:

- AWS Glue release notes e matriz de versões.
- AWS Glue performance tuning.
- AWS Glue Spark UI e History Server.
- AWS Glue Observability e CloudWatch metrics.
- AWS Glue Iceberg integration e table optimizers.
- Apache Spark SQL performance tuning e AQE.
- Apache Iceberg Spark configuration, writes, maintenance e metadata tables.
- Claude Code Skills e subagents.
- Devin Skills.
- GitHub Copilot custom instructions, skills, agents e prompt files.

As Skills não devem tratar esta lista como substituta da documentação do runtime real.

## Rastreabilidade por entrada

`knowledge/` e `rules/catalog/` registram `url` e `retrieved` por entrada —
cada afirmação carrega de onde veio e quando foi confirmada, não uma
declaração solta no topo do arquivo. Quando não existe fonte documental para
uma regra (o comportamento foi inferido de observação de campo, não de
documentação oficial), a fonte é marcada `origin: field-heuristic` em vez de
forjar uma URL — uma fonte inventada é pior do que nenhuma fonte.

## Itens não reconfirmados na coleta de 2026-07-29

Os itens abaixo não foram reconfirmados contra documentação oficial atual
nesta coleta e devem ser tratados com cautela extra até revalidação:

- Disco (tipo e capacidade) para os worker types R.2X, R.4X e R.8X.
- As linhas de Hudi e Delta Lake para Glue 3.0 e 4.0 na matriz de runtime.
- O limite de partições do CTAS no Athena.
- O comportamento exato de `write.distribution-mode` por versão do Iceberg.
