# Fontes oficiais de referência

A base deve ser atualizada periodicamente com documentação oficial:

- AWS Glue release notes e matriz de versões.
- AWS Glue performance tuning.
- AWS Glue Spark UI e History Server.
- AWS Glue Observability e CloudWatch metrics.
- AWS Glue Iceberg integration e table optimizers.
- Amazon EMR release notes, matriz de versões e configuração de cluster on EC2.
- Apache Spark SQL performance tuning e AQE.
- Apache Iceberg Spark configuration, writes, maintenance e metadata tables.
- Superfície pública de PyDeequ e Great Expectations, e o artigo do Deequ que define o
  que uma suíte custa em passadas sobre o dado.
- Claude Code Skills e subagents.
- Devin Skills, subagents, perfis customizados e MCP.
- GitHub Copilot custom instructions, skills, agents e prompt files.

As Skills não devem tratar esta lista como substituta da documentação do runtime real.

## Vigilância automatizada do frescor

"Atualizada periodicamente" deixou de ser só intenção. `scripts/refresh_knowledge.py`
confere se alguma fonte oficial **citada por uma regra** mudou desde a última leitura,
e o workflow `.github/workflows/refresh-knowledge.yml` roda semanalmente (e sob demanda)
abrindo PR quando há o que reler. Ele **nunca commita em `main`**: conhecimento entra por
revisão humana, não por scraper.

A watchlist não é mantida à mão — é o conjunto de `sources[].url` do próprio catálogo,
então regra nova com fonte nova passa a ser vigiada sozinha. O estado fica em
[`knowledge/sources.lock.json`](knowledge/sources.lock.json): por URL, o hash do texto
normalizado, a data da conferência e **quais `rule_id` dependem daquela fonte** — o
relatório não diz "a doc mudou assim", diz "a doc mudou, e as regras X e Y dependem dela".

Fonte com versão no path (`docs/3.5.6/`, `apache-iceberg-1.0.0`) não é buscada: o conteúdo
é imutável e vigiá-la só produziria ruído. Hoje são 37 fontes, 33 móveis e 4 fixas.

**O que a watchlist não alcança, dito em voz alta.** Ela deriva das regras, então
conhecimento **sem regra que o cite** nunca entra — e é o caso de
[`knowledge/devin/agents-and-subagents.md`](knowledge/devin/agents-and-subagents.md), cujas
**24 URLs** de `docs.devin.ai` (coletadas em 2026-08-04) envelhecem sem alarme. É a
combinação mais cara possível, porque a própria fonte declara aquela superfície
**experimental** — *"format, behavior, and configuration options may change"*. A saída
barata seria escrever uma regra de catálogo só para as URLs entrarem, e ela é errada:
fabricaria diagnóstico sobre Spark que não existe, num catálogo que é dado julgado. A
saída certa é ampliar a watchlist para varrer também os rodapés `Fontes` de
`knowledge/**.md`, e é código que ninguém escreveu — está registrada como **dívida**, com
o custo medido, em [`docs/superpowers/STATUS.md`](docs/superpowers/STATUS.md). Até lá, toda
fase que tocar aquele mecanismo deve **reconferir a doc na data da entrega** (V-DV-6).

O que ele guarda é hash e procedência, nunca o texto das docs — copiar documentação de
terceiro para o repositório é decisão de licenciamento que ninguém tomou, e o diff de uma
página da AWS é quase todo ruído de navegação.

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
