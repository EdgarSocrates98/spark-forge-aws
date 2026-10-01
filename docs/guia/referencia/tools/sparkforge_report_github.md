<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_report_github`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Projeta findings JA JULGADOS para o GitHub, sem ler artefato e sem rede: `sarif` (SARIF 2.1.0 para o Code Scanning), `summary_markdown` (para o `$GITHUB_STEP_SUMMARY` do PR) e `annotations` (linhas `::error file=,line=::` que viram anotacao no diff). So entra no SARIF o finding com LINHA num arquivo que existe no repositorio -- a do proprio `subject`, ou a de um fact de evidencia de codigo. O resto sai em `refused` com o motivo: `runtime` (job_run/table sem stage), `sem_linha`, `arquivo_fora_do_repo`, `caminho_ambiguo`, `evidencia_ausente`, `limite_do_github` ou, para stage, `callsite_ausente`, `callsite_sem_forma`, `callsite_nao_python` e `callsite_ambiguo`. Finding de stage com callsite no event log sai na linha da ACAO que originou o stage, com a ressalva de que ela nao e a causa. `subject.file` e relativo ao diretorio passado a cada `analyze --path`, entao informe esses diretorios em `source_roots`. `fail_on` so calcula `gate.tripped`; nada e gravado por esta tool -- a CLI `sparkforge report github` grava em .sparkforge/report/.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string ou array de string | sim | Um caminho, ou varios: a UNIAO dos facts do case. O fact de evidencia de codigo empresta a linha ao finding que nao tem a propria. |
| `findings_path` | string | sim | Saida de `sparkforge judge --out` (findings.json). |
| `repo` | string | sim | Raiz do repositorio git. |
| `as_of` | string | não | Dia de referencia do estado das fontes (AAAA-MM-DD). Default: hoje, UTC. |
| `category` | string | não | Categoria do upload no Code Scanning (automationDetails.id). |
| `fail_on` | string: `P0`, `P1` | não |  |
| `source_freshness` | boolean | não | Acrescenta `source_freshness` (estado de cada fonte citada: fixed, unverified, stale, aging, fresh ou unresolved, com o motivo e as datas) e `freshness_policy` (limiar declarado, `as_of` e contagem por estado). Calculado sobre knowledge/sources.lock.json: depende do lock e do dia. stale = a fonte mudou depois da data em que a regra a validou. |
| `source_roots` | array de string | não | Diretorios relativos a `repo` que foram passados aos `analyze --path`, na mesma ordem. Default: ['.']. |

## Na CLI

[`sparkforge report github`](../cli/report.md)

## Capacidade

show findings where the pull request is reviewed

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
