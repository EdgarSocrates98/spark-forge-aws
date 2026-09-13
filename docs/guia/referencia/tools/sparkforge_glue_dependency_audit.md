<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_glue_dependency_audit`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Lista as dependencias DECLARADAS de um job Glue -- pin de `requirements*.txt` (`mig.python_dep`, com `major` ja separado) e binario `.jar` (`mig.jar_binary`, com `scala_minor` ja separado) -- ao lado do que o catalogo julga sobre elas. `glue` nao tem default e nao e opcional: risco de ABI nao existe em abstrato, um `.jar` de Scala 2.12 e correto sob Glue 5.1 e quebra sob 6.0, e um piso de `pyarrow` so e piso a partir da versao de Spark que o exige. Nao constroi julgamento novo: e o mesmo `judge` sobre o mesmo catalogo, com a dependencia observada ao lado do achado que ela produziu.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `glue` | string | sim | Versao de Glue a auditar. |
| `path` | string | sim | Diretorio do job (requirements*.txt e .jar). |

## Na CLI

[`sparkforge glue dependency-audit`](../cli/glue.md)

## Capacidade

audit declared Python and Scala dependencies against a runtime

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
