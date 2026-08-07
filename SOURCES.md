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
confere se alguma fonte oficial **que este repositório cita** mudou desde a última leitura,
e o workflow `.github/workflows/refresh-knowledge.yml` roda semanalmente (e sob demanda)
abrindo PR quando há o que reler. Ele **nunca commita em `main`**: conhecimento entra por
revisão humana, não por scraper.

A watchlist não é mantida à mão, e tem **duas origens, as duas derivadas**: `sources[].url`
das regras do catálogo (campo `rules`) e as URLs dos blocos `Fontes` de `knowledge/**.md`
(campo `docs`). Regra nova com fonte nova, e página nova com fonte nova, passam a ser
vigiadas sozinhas. O estado fica em
[`knowledge/sources.lock.json`](knowledge/sources.lock.json): por URL, o hash do texto
normalizado, a data da conferência e **quem depende daquela fonte** — o relatório não diz
"a doc mudou assim", diz "a doc mudou, e as regras X e Y, e a página Z, dependem dela".

Fonte com versão no path (`docs/3.5.6/`, `apache-iceberg-1.0.0`) não é buscada: o conteúdo
é imutável e vigiá-la só produziria ruído. Hoje são **131 fontes, 123 móveis e 8 fixas** —
61 citadas por regra, 126 citadas por `knowledge/`, e 56 pelas duas.

**Por que a segunda origem existe.** Até 2026-08-05 a watchlist derivava só das regras, e
conhecimento **sem regra que o citasse** nunca entrava. O caso que fechou a dívida é
[`knowledge/devin/agents-and-subagents.md`](knowledge/devin/agents-and-subagents.md): ela
não sustenta regra nenhuma — sustenta **perfil de agente** —, e as suas **24 URLs** de
`docs.devin.ai` envelheciam sem alarme sobre uma superfície que a própria fonte declara
**experimental** (*"format, behavior, and configuration options may change"*). A saída
barata seria escrever uma regra de catálogo só para as URLs entrarem, e ela é errada:
fabricaria diagnóstico sobre Spark que não existe, num catálogo que é dado julgado.

O preço da segunda origem é o **vínculo de volta**, e ele é obrigatório: fonte vigiada que
ninguém cita é alarme sem endereço. Toda entrada do lock nomeia pelo menos um consumidor —
regra, página, ou as duas — e há teste que exige isso. URL citada pelas duas origens com
`retrieved` diferentes carrega **as duas datas**, para que a divergência apareça em vez de
ser resolvida por chute. Fonte nova entra **sem hash**, e a primeira conferência com rede a
relata como *NOVA*; alinhar o conjunto sem rede é
`python scripts/refresh_knowledge.py --update --offline`. Continua valendo o V-DV-6: fase
que tocar o mecanismo de subagentes do Devin **reconfere a doc na data da entrega**, porque
vigiar o hash diz que mudou, não o que mudou.

O que ele guarda é hash e procedência, nunca o texto das docs — copiar documentação de
terceiro para o repositório é decisão de licenciamento que ninguém tomou, e o diff de uma
página da AWS é quase todo ruído de navegação.

## Código de terceiro vendorizado

`knowledge/` guarda hash e procedência de documentação, **nunca o texto** — a seção acima
explica por quê. `vendor/` é o caso oposto e a exceção deliberada: ali estão **bytes de
código de terceiro**, commitados, sob licença MIT que permite explicitamente a
redistribuição com o aviso de copyright preservado.

O que está lá, e de quem é:

- **caveman** e **cavekit**, de [Julius Brussee](https://github.com/JuliusBrussee), MIT.
  Pinados por SHA em [`vendor/PINS.json`](vendor/PINS.json) e por sha256 de cada arquivo em
  `vendor/MANIFEST.sha256`. As licenças originais estão preservadas em
  `vendor/caveman/LICENSE` e `vendor/cavekit/LICENSE`.
- **cavemem** e **caveman-code**, do mesmo autor, MIT, **fora do repositório**: dependem de
  módulo nativo compilado por plataforma e só existem via npm. Não há `package.json` aqui —
  nenhum caminho padrão pode depender de `npm install` ou `npx`. A razão de cada um está em
  [`vendor/CREDITS.md`](vendor/CREDITS.md), e o crédito continua valendo mesmo sem o código.

A decisão de licenciamento aqui foi tomada, e é o que separa este caso do de documentação:
MIT autoriza a cópia, o aviso de copyright viaja junto, e o crédito está em
[`vendor/CREDITS.md`](vendor/CREDITS.md). Documentação da AWS não tem essa autorização — por
isso continua fora.

Atualizar é editar o `sha` em `PINS.json` e rodar `python scripts/vendor_caveman.py`. O gate
sem rede é `python scripts/vendor_caveman.py --check`.

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
