<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_emr_serverless`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de um dump JSON de application Amazon EMR Serverless (`get-application`): release, estado, arquitetura, capacidade pre-inicializada por worker type (`emrs.initial_capacity`), teto de recursos, propriedades de `runtimeConfiguration` (`emrs.configuration`) e destinos de log (`emrs.monitoring`). NAO chama a API do EMR Serverless -- so le o JSON ja salvo em disco (`sparkforge_collect_emr_serverless` ou `aws emr-serverless get-application` a mao fazem isso). LIMITE QUE VALE PARA TODO FACT DAQUI: `get-application` descreve o PADRAO da application, nao o que um job rodou -- a AWS declara que as configuracoes de `StartJobRun` sobrepoem as do nivel da application, inclusive removendo classificacao e destino de log. Nenhum achado desta area pode ser redigido como afirmacao sobre execucao. `emrs.monitoring` e o unico fact do modulo que aplica default documentado, e por necessidade: managed persistence tem default `true` e CloudWatch tem default `false`, entao `*_declared` acompanha cada destino para distinguir o que foi lido do que foi presumido. Auto-stop faz o oposto -- o default da AWS e o estado SEGURO, entao o campo ausente NAO e materializado e `auto_stop_declared` responde sobre o payload. Unidade de capacidade fora do conjunto documentado vira `emrs.unresolved` contado, nunca numero adivinhado.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo ou diretorio com dumps de application. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze emr-serverless`](../cli/analyze.md)

## Capacidade

extract facts from an EMR Serverless application dump

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
