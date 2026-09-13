<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_scan`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Roda sozinho os analyzes que cabem num repositorio e julga a uniao. Artefato coletado entra pelo `kind` do `.sparkforge/artifacts/manifest.json`, com sha256 conferido; codigo entra pela extensao (.py, .sql, .tf, .jsonl). Um analyze por arquivo; depois `fuse` e `judge`. Grava em `.sparkforge/scan/` (facts por analyze, facts.json, findings.json, summary.json) e, com `format: sarif`, o SARIF e o resumo de PR do `report github`. `dry_run` so devolve o plano. Toda recusa tem nome: sem_manifesto (JSON solto nunca e classificado pelo conteudo), sha256_divergente, kind_sem_analyze, exige_job_name, fora_da_raiz, analyze_falhou (um arquivo ruim nao derruba os outros). Sem rede: nao coleta nada.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio a varrer. |
| `athena` | string | não | Versao de athena para o judge. |
| `dry_run` | boolean | não | So o plano; nada roda. |
| `emr` | string | não | Versao de emr para o judge. |
| `fail_on` | string: `P0`, `P1` | não |  |
| `format` | string: `json`, `sarif` | não |  |
| `glue` | string | não | Versao de glue para o judge. |
| `iceberg` | string | não | Versao de iceberg para o judge. |
| `python` | string | não | Versao de python para o judge. |
| `spark` | string | não | Versao de spark para o judge. |

## Na CLI

[`sparkforge scan`](../cli/scan.md)

## Capacidade

run the analyzers that fit a repository and judge them

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
