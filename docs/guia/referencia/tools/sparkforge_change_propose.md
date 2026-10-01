<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_change_propose`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Autonomia L3 (§15, propose change): monta o pacote de um PR em `.sparkforge/proposal/<id>/` a partir de um sandbox JA rodado (`sandbox_id`, o id que `sparkforge_change_sandbox` devolveu): `change.patch` e `rollback.patch` provados contra a copia validada, `pr_body.md` assinado pelo `report sign` com os findings de `after/`, `commit_message.txt`, `branch.txt`, `commands.md` com os comandos git/gh que o HOST roda, `evidence/sandbox_report.json`, `evidence/receipt.json` e `manifest.json`. Recusa antes de gravar: sandbox_inexistente, sandbox_nao_aplicado, sandbox_desatualizado (a arvore mudou depois do sandbox) e achado_novo_bloqueante (o diff faz aparecer P0/P1). `benchmark_paths` e `funcval_path` anexam facts ja medidos; sem eles a medida sai PENDENTE no corpo. `now` entra no recibo: o mesmo `now` grava os mesmos bytes. O QUE ELA NAO FAZ: nao roda git, gh nem subprocess (`git_run: false`), nao toca a arvore principal, nao abre o PR e nao afirma ganho.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `now` | string | sim | Instante ISO 8601 do recibo. Entra no hash. |
| `repo` | string | sim | Raiz do repositorio. |
| `sandbox_id` | string | sim | O id que `sparkforge_change_sandbox` devolveu. |
| `benchmark_paths` | array de string | não | Arquivos de facts com `bench.*` de dois runs medidos. |
| `funcval_path` | string | não | Arquivo de facts com `funcval.*` do funcval compare. |

## Na CLI

[`sparkforge change plan`](../cli/change.md), [`sparkforge change propose`](../cli/change.md), [`sparkforge change sandbox`](../cli/change.md)

## Capacidade

produce a configuration change and try any diff in a sandbox copy

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
