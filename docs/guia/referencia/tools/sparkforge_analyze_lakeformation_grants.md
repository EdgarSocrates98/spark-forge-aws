<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_lakeformation_grants`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai a PERMISSAO do Lake Formation ja coletada por `collect lakeformation`: grant por principal, registro da localizacao S3, e o data lake settings da conta. Aceita um artefato ou o DIRETORIO deles, porque um job que le de uma tabela e escreve noutra tem dois. TRES estados produzem a mesma lista vazia de grants -- tabela sem grant, sem permissao para LER os grants, e sem credencial --, e os tres viram `lakeformation.grants.unresolved` com a razao; colapsa-los faria acusar a tabela governada corretamente e a que ninguem inspecionou do mesmo jeito. `registered` da localizacao e TERNARIO: verdadeiro, falso, ou AUSENTE quando ninguem mediu -- e e exatamente sobre localizacao registrada que a documentacao da AWS se contradiz. Ele NAO decide se a permissao basta, NAO le policy de IAM e NAO estima nada: `SELECT` bastar ou nao depende da operacao e do modelo de acesso, e isso e juizo das regras `SF-LF`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Artefato gravado por `sparkforge collect lakeformation`, ou o diretorio deles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze glue-resource-link`](../cli/analyze.md), [`sparkforge analyze iam-access`](../cli/analyze.md), [`sparkforge analyze lakeformation-grants`](../cli/analyze.md)

## Capacidade

read who holds which Lake Formation permission on a table

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
