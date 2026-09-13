<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_lakeformation_access_graph`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

O caminho de acesso a uma tabela governada como GRAFO, derivado de facts -- concessao do Lake Formation, decisao SIMULADA do IAM (com a camada que negou) e registro da localizacao S3. Use quando a pergunta for 'onde o caminho parou', e depois de `collect lakeformation` e `collect iam-access`. `is_accessible` e TERNARIO: `true` so quando toda perna medida passou E nenhuma ficou sem medida; `false` quando alguma perna MEDIDA barrou; `null` quando nada do que foi medido impede e alguma perna nao foi medida -- e `null` e 'o que eu consegui olhar nao impede', NUNCA 'funciona'. RAM share e key policy do KMS saem SEMPRE `unresolved`: nenhum coletor deste repositorio os produz, e devolver `missing` para eles seria acusacao a partir de ausencia de artefato. RESOURCE LINK saiu dessa lista em 2026-09-10 e tem QUATRO saidas medidas depois de `collect glue-resource-link`: `granted` (nome identico ao do recurso de origem e a origem respondeu), `blocking` (nome divergente -- limite de suporte declarado, nao negacao observada), `not_applicable` (o objeto nao e link) e `unresolved` (a origem respondeu `EntityNotFoundException`, que sob Lake Formation NAO distingue recurso inexistente de recurso nao autorizado). Localizacao NAO registrada sai `not_applicable` e nao `missing` -- tabela fora do registro e lida com a credencial do runtime role, e nao e permissao que faltou. Com mais de uma tabela ou mais de um principal no case a tool NAO escolhe: devolve `unresolved` com os candidatos.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | qualquer | sim |  |
| `principal_arn` | string | não |  |
| `target_table` | string | não |  |

## Na CLI

[`sparkforge lakeformation access-graph`](../cli/lakeformation.md)

## Capacidade

trace the access path to a governed table as a graph

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
