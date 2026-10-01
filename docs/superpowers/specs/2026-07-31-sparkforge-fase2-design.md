# SparkForge AWS — Fase 2 (executada): Desbloqueio Total do Catálogo

**Data do documento:** 2026-07-31
**Data da implementação:** 2026-07-31
**Status:** implementado
**Branch:** `feat/fase2-desbloqueios` · **Faixa:** `dc80efd` … `b44edd0` · **Merge:** `bc53865` (PR #1)
**Depende de:** [Fase 1](2026-07-30-sparkforge-fase1-design.md)

> **Documento retroativo**, reconstruído dos commits depois da entrega.

> **Aviso de nomenclatura.** Esta fase **não** é a Fase 2 do roadmap da §16 do
> spec da Fase 0. Aquele roadmap chama de Fase 2 a expansão do knowledge, o
> `refresh_knowledge` e a matriz de compatibilidade automatizada — nada disso foi
> feito, e continua em aberto (ver [`../STATUS.md`](../STATUS.md)). O que foi
> executado sob o nome "Fase 2" é o inverso: **zero regra nova**, e sim a
> construção dos extratores que faltavam para que as regras já committadas
> parem de ser inertes.

---

## 1. Problema

Ao fim da Fase 1 o catálogo tinha 43 regras e dois buracos de credibilidade:

**Buraco A — 5 regras com `blocked_on`.** SF-PQ-001, SF-PQ-003, SF-PQ-005,
SF-ENV-002 e SF-GLUE-005 não podiam disparar porque nenhum extrator produzia os
kinds que elas exigem. `blocked_on` é honesto — `judge --show-skipped` diz ao
operador que ninguém construiu a capacidade — mas uma regra que nunca rodou é
uma promessa, não uma verificação.

**Buraco B — 3 regras alcançáveis sem golden positivo.** SF-ENV-003,
SF-GLUE-003 e SF-GLUE-004 podiam disparar, mas nenhuma fixture provava que
disparam. Regra sem golden positivo nunca foi provada: pode ter limiar
invertido, `where` que não casa com fact real, ou `requires_facts`
contraditório.

O buraco B não era hipotético. **SF-GLUE-005 exigia `spark.stage.spill` em
`requires_facts` E em `absent:`** — e o motor exige a presença de todo kind de
`requires_facts`. A regra era uma contradição lógica; não podia disparar nunca.
O `blocked_on` escondeu isso por toda a Fase 1.

**Buraco C, descoberto durante a fase — toda chamada de tool MCP falhava.**
Os 25 tools declaravam `outputSchema` e o SDK exige `structuredContent` de quem
declara; `_call_tool` devolvia só `TextContent`. Qualquer `tools/call` respondia
`Output validation error: outputSchema defined but no structured output returned`,
em stdio e em HTTP, no Claude Code e no Devin. Nenhum teste pegava porque todos
exercitavam `tools.call_tool` direto — e essa função nunca esteve quebrada. O
que faltava era a camada do SDK entre ela e o cliente.

## 2. Objetivo

Zerar as duas contagens: **0 regras com `blocked_on`** e **43 de 43 regras com
uma fixture que as faz disparar**. E travar os dois invariantes, para que a
contagem não possa regredir em silêncio.

Depois desta fase, o que falta para uma regra disparar é sempre **coleta**,
nunca código.

## 3. Decisões

| # | Decisão | Alternativa rejeitada | Razão |
|---|---|---|---|
| F2-D1 | `s3_listing` agrupa por (formato, compressão) | Um sumário por prefixo | Prefixo real mistura Parquet, `_SUCCESS`, log `.gz` e CSV. Sumário único diluiria um `.gz` de 4 GB na média do Parquet e SF-PQ-003 nunca casaria |
| F2-D2 | `IsTruncated: true` **suprime** o sumário | Sumário da primeira página | `file_count`, `avg_file_bytes` e `max_file_bytes` sairiam de uma página apresentada como total. Mesma decisão de `spark_plan.py` para `... N more fields` |
| F2-D3 | Consumidores vêm de inventário **declarado** por pessoa | Derivar do histórico de queries do Athena | O histórico veria só o Athena, com retenção limitada; um consumidor Redshift ou EMR invisível viraria "sem consumidor" |
| F2-D4 | Tabela ausente do inventário **não** produz fact | Emitir "sem consumidor" | Ausência de declaração não é declaração de ausência. Sentinela `env.consumers_analyzed` distingue inventário vazio de inventário nunca lido |
| F2-D5 | `extract_terraform_diff` devolve só o lado DEPOIS | Devolver os dois lados | Devolver os dois faria toda regra contar cada recurso duas vezes e acusar o estado antigo, que ninguém pode mais consertar |
| F2-D6 | SF-GLUE-005 passa a usar `spark.job.spill_summary` | Corrigir só a contradição `requires_facts`/`absent` | Mesmo sem a contradição, `absent:` continuaria errado: `event_log` emite `spark.stage.spill` para todo stage analisado, zero byte inclusive. A ausência significaria "não analisei event log", não "não houve spill" |
| F2-D7 | Cada fixture positiva tem a negativa ao lado | Só o caso que dispara | Regra provada só disparando não foi provada. Falso positivo treina o operador a ignorar a saída (§17 da Fase 0) |
| F2-D8 | Fixture de correlação prova **uma** regra só | Uma fixture rica que dispara várias | Corpus de correlação é o mais fácil de contaminar; fixture que prova duas coisas ao mesmo tempo não prova nenhuma com clareza |

## 4. Entregas

### 4.1 Correção do MCP (`dc80efd`)

- Handler devolve o dict cru; o SDK preenche `structuredContent` e continua
  serializando o JSON em `content`, então cliente que só lê texto não regride.
- Erro de fronteira sai como `CallToolResult(isError=True)`, **não** como dict:
  `{"error", "exit_code"}` não casa com o `outputSchema` e a validação trocaria
  a mensagem acionável do adapter por uma queixa de schema.
- `/mcp` respondia **307**. `Mount("/mcp")` do Starlette só serve `/mcp/` e
  redireciona o resto — e httpx não segue redirect em POST por default, então o
  `serverUrl` documentado falharia no Devin Desktop com "não conecta" e nenhuma
  pista. `redirect_slashes=False` trocaria por 404, pior. A rota passa a ser
  resolvida no próprio handler comparando o caminho normalizado: `/mcp` e
  `/mcp/` servem, o resto é 404 explícito.
- Testes novos chamam o tool **através do handler do SDK** e dirigem o app ASGI
  direto, sem subir servidor.

### 4.2 Três extratores novos (`081a570`)

| extrator | kinds | desbloqueia |
|---|---|---|
| `s3_listing` | `s3.{prefix_summary,analyzed,unresolved}` | SF-PQ-001 (small files), SF-PQ-003 (texto gzip não splitável), SF-PQ-005 (cardinalidade de partição, junto com `catalog.table_partitions`) |
| `consumers` | `env.{consumer,consumers_analyzed,unresolved}` | SF-ENV-002 (armadilha do Iceberg format V3, que o Athena não lê) |
| `terraform.extract_terraform_diff` | reusa `tf.*` com `attrs.changed` e `previous_value` | revisão de PR de infra |

Mais dois kinds em `event_log.py` para SF-GLUE-005:
`spark.job.spill_summary` (responde no nível do job) e
`spark.executor.memory_usage` (de `SparkListenerStageExecutorMetrics`) —
afirmar que não há limitação de memória sem ter visto uma única medida de
memória é o mesmo erro, um passo adiante.

Corpora novos: `fixtures/s3/` (5), `fixtures/consumers/` (3), `fixtures/tfdiff/`
(2). Cada positivo com o negativo ao lado — prefixo saudável que não pode
disparar, V2 com o mesmo consumidor Athena, worker aumentado COM spill.

Superfície: `analyze s3-listing`, `analyze consumers` e `analyze terraform-diff`
na CLI e no MCP. **28 tools.**

### 4.3 As três regras sem golden positivo (`b44edd0`)

Corpus novo `fixtures/infra_code/`, com Terraform **e** código PySpark do mesmo
job no mesmo `input/` — porque duas das três regras fazem uma pergunta que
nenhum artefato responde sozinho.

| regra | pergunta | por que importa |
|---|---|---|
| SF-ENV-003 | `--enable-observability-metrics` ligado no Terraform sem `GlueContext` no código | As métricas do Glue são publicadas pelo GlueContext. Sem ele o argumento fica ligado, o operador acredita ter métrica, e o painel fica vazio — falha que só aparece quando alguém precisa dela |
| SF-GLUE-004 | `max_retries = 3` com escrita `append` | A retentativa reexecuta o job e `append` não é idempotente: cada tentativa soma os mesmos registros, o job é marcado como sucesso, e o dado sai duplicado sem erro no log |
| SF-GLUE-003 | bookmark habilitado com `max_concurrent_runs = 3` | Bookmark guarda progresso por JOB, não por execução: duas execuções concorrentes leem o mesmo ponto de partida e a última a terminar sobrescreve o marcador da outra |

As duas fixtures de `infra_code/` são a metade negativa uma da outra: a de
SF-ENV-003 não inicializa GlueContext e grava `overwrite` com `max_retries = 0`;
a de SF-GLUE-004 inicializa GlueContext e grava `append` com `max_retries = 3`.
Cada uma dispara exatamente uma regra, e um teste garante isso (F2-D8).

SF-GLUE-003 é de fonte única e entrou em `fixtures/terraform/`.

## 5. Invariantes travados

Em `tests/test_fixtures_kind_coverage.py`, ao lado do invariante de kinds:

1. Toda regra do catálogo precisa de uma fixture que a faça disparar.
2. Todo `rule_id` que aparece num golden precisa existir no catálogo.

As duas direções, porque as duas já quebraram. Junto com
`tests/test_rules_catalog_reachability.py` (regra sem extrator; `blocked_on`
obsoleto) e o golden bidirecional da Fase 0 (perder finding e inventar finding
falham igual), o catálogo passa a ter quatro guardas independentes.

`scripts/regen_fixtures.py` torna a regeneração dos goldens idempotente.

## 6. Resultado

| | Início da fase | Fim |
|---|---|---|
| Regras com `blocked_on` | 5 | **0** |
| Regras com golden que dispara | 40 de 43 | **43 de 43** |
| Tools MCP | 25 (todas quebradas na chamada) | **28**, funcionando nos dois transportes |
| Testes | 1621 | **1726** |
| Achados Snyk | 0 | 0 |

## 7. O que continua em aberto

Nada desta fase. O que segue aberto vem do roadmap da §16 do spec da Fase 0 e
está listado em [`../STATUS.md`](../STATUS.md) — principalmente
`refresh_knowledge`, a expansão do catálogo para as 18 skills, e as Fases 3 e 4.
