<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_emr_cluster`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de um dump JSON de cluster EMR on EC2 (`describe-cluster` mais `list-instance-groups`/`list-instance-fleets`/`list-bootstrap-actions`/`get-managed-scaling-policy`/`get-auto-termination-policy`): release, aplicacoes com a versao observada, capacidade por papel (Spot/On-Demand, grupo OU fleet no mesmo kind), configuracoes nos DOIS niveis (cluster e grupo, com quem sobrepoe quem), bootstrap actions e a politica de managed scaling. NAO chama a API do EMR -- so le o JSON ja salvo em disco (`sparkforge_collect_emr_cluster` ou `aws emr ...` a mao fazem isso). Grupo cujo `Configurations` diverge de `LastSuccessfullyAppliedConfigurations` vira `emr.configuration.unapplied`: a reconfiguracao foi pedida e NAO aplicada, entao o cluster nao roda com o que o dump aparenta dizer, e toda regra que le configuracao daquele grupo precisa desse fact como guarda. Emite tambem um unico fact DERIVADO, `emr.yarn.am_node_label`, que decide a partir do `yarn-site` se o ApplicationMaster -- que em deploy-mode cluster E o driver -- esta preso a um rotulo de no seguro; ele so aparece quando o AM NAO esta provadamente solto, e e o guarda de SF-EMR-008.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo ou diretorio com dumps de cluster EMR. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze emr-cluster`](../cli/analyze.md)

## Capacidade

extract facts from an EMR on EC2 cluster dump

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
