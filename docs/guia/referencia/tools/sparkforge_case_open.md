<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_case_open`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Cria um case novo em .sparkforge/case.yaml, detectando o runtime Glue/EMR/Spark/Python/Iceberg a partir dos parametros informados. E o barramento de handoff entre sessoes (Devin, Claude Code): sem case, next-step e resume nao tem estado sobre o qual operar. `now` e obrigatorio e nunca lido do relogio pela ferramenta -- quem chama fornece o timestamp.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `case_id` | string | sim |  |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim | Raiz do repositorio analisado. |
| `athena` | string | não |  |
| `databricks` | string | não | Versao do Databricks Runtime ('15.4' ou '15.4.x-scala2.12'). DECLARACAO, nao observacao: perde para o event log, e discordar vira divergencia reportada em `runtime.divergences`. |
| `emr` | string | não | Release do EMR on EC2, nas duas grafias ('emr-7.5.0' ou '7.5.0'). DECLARACAO, nao observacao: perde para o event log e para um dump de describe-cluster, e discordar de um deles vira divergencia reportada em `runtime.divergences`, nunca valor substituido em silencio. |
| `facts_path` | string ou array de string | não | Facts ja extraidos: o runtime do case sai do que os extratores observaram, nao so das flags. |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `photon` | string: `on`, `off` | não | Photon ligado ou desligado no Databricks. Com 'on', regra de plano sai em skipped com databricks.photon.unresolved. |
| `python` | string | não |  |
| `reopen` | boolean | não | Recomeca do zero por cima de um case que ja existe. Omitido, abrir sobre um case existente e RECUSADO: sobrescrever apagaria fase, rigor e overrides gravados. O `strict_gates` do case atual e herdado -- `strict_gates` sobe o rigor, e nada o baixa por omissao. |
| `spark` | string | não |  |
| `strict_gates` | boolean | não | Grava no case que gate com produtor declarado bloqueia a transicao de fase. A escolha e do case, nao da chamada: vale pela investigacao inteira, e quem retoma noutra sessao herda o rigor de quem abriu. Omitido, o comportamento e o de sempre (gate advisory). |

## Na CLI

[`sparkforge case get`](../cli/case.md), [`sparkforge case open`](../cli/case.md), [`sparkforge case update`](../cli/case.md)

## Capacidade

maintain investigation state

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
