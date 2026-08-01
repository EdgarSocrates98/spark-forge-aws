---
name: sparkforge-diagnose
description: Use quando o pedido for genérico e amplo — "meu job Glue tá lento", "por que esse pipeline ficou caro", "não sei por onde começar" — e ainda não há gargalo isolado nem skill específica escolhida. Use também como a primeira skill de qualquer investigação nova, antes de ter event log, plano físico ou qualquer fact coletado. Esta skill não analisa: ela abre o case, coleta o que está disponível, e deixa `sparkforge next-step` decidir a rota. Se você está prestes a escolher a próxima skill "pelo que parece óbvio", pare — rode `sparkforge next-step` em vez disso: a árvore de decisão vive em `rules/catalog/routing.yaml`, e escolher por julgamento próprio é exatamente o que a regra 2 do AGENT_PROTOCOL.md proíbe.
---

# SparkForge Diagnose

## Por que começar aqui

Sem case aberto, a investigação não é retomável entre sessões nem entre ferramentas (Devin, Claude Code, o que vier depois). Sem runtime confirmado, nenhum limiar do catálogo pode ser aplicado com segurança — divergência entre fontes é `SF-ENV-001` em P0 e trava qualquer conclusão dependente de versão. Esta skill não substitui as skills especializadas; ela é o ponto de entrada que garante que as duas coisas acima aconteçam antes de qualquer uma delas rodar.

## O loop

### 1. Detecte o runtime

```bash
sparkforge runtime detect
```

Rode assim, sem flag, antes de qualquer outra coisa — e leia a saída como um **retrato do que se sabe agora**, não como falha. Num repositório ainda sem facts extraídos, tudo volta vazio e `detected_from: []`: correto, porque nada foi observado ainda.

`runtime detect` aceita `--facts` (repetível), e é dele que a detecção real sai. As duas únicas fontes que o motor lê são as que algum extrator observou com artefato atrás: `glue_version` literal na raiz de um `aws_glue_job` (via `sparkforge analyze terraform`) e a versão declarada na primeira linha de um Spark event log (via `sparkforge analyze event-log`). Nada é deduzido de sintaxe de API, nome de bucket ou presença de import — isso seria palpite vestido de fato. Por isso este passo costuma render mais **depois** do passo 4, e vale repeti-lo lá.

As flags (`--glue`, `--spark`, `--python`, `--iceberg`, `--athena`) continuam existindo para você **declarar** uma versão que sabe de fonte confiável — o console, o `tfvars`, o job run. Não são campos a preencher por obrigação: uma versão inventada é pior que um campo vazio, porque o vazio pula a regra com motivo visível e o valor errado julga contra o limiar errado em silêncio.

### 2. Abra o case

```bash
sparkforge case open --repo <repo> --case-id <id> --now <ISO8601>
```

O case guarda o runtime da investigação inteira, e toda skill que ler o case depois herda o que estiver aqui — por isso vale abri-lo com a melhor detecção disponível, não com o que você digitou. Se já houver facts extraídos, `case open` também aceita `--facts` (repetível):

```bash
sparkforge case open --repo <repo> --case-id <id> --now <ISO8601> --facts .sparkforge/facts_tf.json
```

Se ainda não houver, abra o case mesmo assim — o loop não pode esperar pelo runtime, e `judge` refaz a detecção por conta própria a cada chamada.

### 3. Colete o que existir

```bash
sparkforge collect event-log --repo <repo> --job-run <id> --bucket <bucket> --prefix <prefix> --now <ISO8601>
sparkforge collect glue-job --repo <repo> --job-name <nome> --now <ISO8601>
sparkforge collect cloudwatch --repo <repo> --job-name <nome> --job-run <id> --start <ISO8601> --end <ISO8601> --now <ISO8601>
```

Nem tudo vai existir na primeira passada — o job pode não ter Spark UI habilitado (isso já é um achado, `SF-GLUE-002`), ou pode faltar credencial AWS. Não pare por isso: registre o que faltou e siga com o que tem. `sparkforge collect verify --repo <repo>` confirma presença e integridade de tudo que já está no manifesto do case.

### 4. Extraia facts do que foi coletado

```bash
sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json
sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id>.jsonl --out .sparkforge/facts_eventlog.json
sparkforge analyze terraform --path <dir.tf> --out .sparkforge/facts_tf.json
```

Use `analyze iceberg` e `analyze catalog-schema` quando o escopo incluir tabela Iceberg ou revisão de catálogo.

### 5. Julgue com --show-skipped

```bash
sparkforge judge --facts .sparkforge/facts.json --facts .sparkforge/facts_tf.json \
                 --facts .sparkforge/facts_eventlog.json --show-skipped
```

`--facts` é repetível, e passar tudo que o passo 4 extraiu numa chamada só é o que fecha o eixo de versão sem digitar nada: `judge` refaz a detecção a partir desses mesmos facts antes de filtrar as regras. Leia o campo `runtime` da saída — ele traz o contexto **efetivamente usado**, `detected_from` diz de onde veio, e `divergences` lista as fontes que discordam. Divergência não é detalhe: é `SF-ENV-001` em P0, e trava qualquer conclusão dependente de versão até ser resolvida.

`--show-skipped` não é opcional aqui, e agora tem dois motivos distintos para ler. Sem event log, todo `SF-UI-*` aparece em `skipped` por falta de fact — não por ausência de skew ou spill. Sem nenhuma fonte de versão, as oito regras versionadas (`SF-ENV-002`, `SF-ENV-003`, `SF-GLUE-001..006`) aparecem com `reason: runtime_scope` — não por estarem corretas, mas por não haver contexto para avaliá-las. Nos dois casos a confusão a evitar é a mesma, e é a mais cara desta skill: "nenhum problema" e "não coletei o dado que provaria o problema" são coisas diferentes.

Se `runtime.glue` voltar vazio e não houver `.tf` no repositório, aí sim declare: `--glue 5.1`, com a versão vinda de fonte confiável e registrada no case. Não preencha por hábito.

### 6. Deixe next-step decidir a rota

```bash
sparkforge next-step --repo <repo> --findings .sparkforge/findings.json
```

Rode de novo depois de **cada** rodada de achados novos, não uma vez só. `next-step` lê `rules/catalog/routing.yaml` e devolve a skill recomendada, alternativas com rank, e o que ainda falta coletar (`missing_artifacts`, `collect_commands`). Não escolha a skill seguinte pelo que parece o problema — é isso que faria o resultado divergir entre modelos e entre sessões.

### 7. Registre a skill usada e o resultado no case

```bash
sparkforge case update --repo <repo> --skill <nome-da-skill> --outcome "<resumo>" --now <ISO8601>
```

Regra 6 do protocolo: cada skill usada, o resultado, e por que as descartadas não foram usadas — tudo registrado no case, não só narrado na sua resposta.

### 8. Valide antes de apresentar

```bash
sparkforge validate --findings .sparkforge/findings.json
```

Ganho quantificado sem `benchmark_ref` é rejeitado pelo schema.

### 9. Pare em qualquer ponto, retome em qualquer ferramenta

```bash
sparkforge handoff --repo <repo> --findings .sparkforge/findings.json --unresolved <n> --in-flight "<o que estava em andamento>"
```

Escreve `.sparkforge/handoff.md` e devolve o mesmo payload em JSON. É o que permite a investigação parar aqui e continuar no Devin — ou o inverso — com o mesmo próximo passo, em vez de reconstruir contexto do zero. Ao retomar, `sparkforge resume --repo <repo> --findings <> --unresolved <n> --in-flight <>` rehidrata o case com o mesmo formato de payload.

## Vocabulário de gargalo, não checklist

Use estas categorias para nomear o gargalo dominante ao escrever o achado — elas não substituem o loop acima, e nenhuma delas é escolhida por inspeção visual: CPU-bound, memory/GC-bound, shuffle-bound, skew-bound, driver-bound, S3 I/O/listing-bound, small-files-bound, metadata-planning-bound, under-parallelized, over-partitioned, cluster-capacity, data-model/layout, dívida de manutenção Iceberg.

## Referência rápida

Como `next-step` decide, sem repetir a árvore inteira de `routing.yaml` — consulte o arquivo para a lista completa de 16 regras. Não decore condição nem skill; rode `next-step` e leia `evidence` e `reason` na saída.

| Situação no case | Regra de roteamento | Para onde manda |
|---|---|---|
| Runtime não confirmado, ou divergência entre fontes | `ROUTE-001` | de volta a esta skill — resolver runtime primeiro |
| Nenhum fact extraído ainda | `ROUTE-002` | `analyze-library-call-graph` |
| Dois entrypoints e fluxos não separados | `ROUTE-003` | `design-incremental-processing` |
| `SF-PY-004` presente (action/write em loop) | `ROUTE-004` | `analyze-batch-loop` |
| `SF-UI-005` presente (executor perdido) | `ROUTE-005` | `diagnose-oom` |
| `SF-UI-001` + `SF-UI-002` presentes | `ROUTE-006` | `diagnose-data-skew` |
| `SF-PQ-002` presente (pruning ausente) | `ROUTE-008` | `analyze-spark-plan` |
| `SF-PQ-001` ou `SF-ICE-001` presente | `ROUTE-009` | `optimize-parquet-layout` |
| `SF-ICE-002` ou `SF-ICE-003` presente | `ROUTE-010` | `optimize-iceberg-table` |
| Facts extraídos, zero findings | `ROUTE-014` | `review-glue-terraform` |
| Nenhuma regra casou | fallback | de volta a esta skill, registrando o que falta em `open_questions` |

## Quando NÃO usar

- Já isolou o gargalo dominante (skew, OOM, Iceberg, Terraform) e só falta a skill focada: vá direto — mas registre a escolha no case mesmo assim.
- Investigação com fluxos full + incremental, latest-per-key e batching: comece por `glue-incremental-performance-architect`, que orquestra este mesmo loop em maior escopo.
- Só quer revisar um trecho de código ou um PR isolado: use `optimize-pyspark-code` ou `review-pyspark-pr`.

## Red flags

- Pular a abertura do case porque "é só uma pergunta rápida" — sem `.sparkforge/case.yaml` não há retomada, nem para você na próxima mensagem.
- Escolher a skill seguinte pelo que parece óbvio em vez de rodar `next-step`.
- Julgar sem `--show-skipped` e reportar "nenhum problema encontrado" quando na prática nada foi coletado para aquela área.
- Recomendar mais workers ou mudar `spark.sql.shuffle.partitions` antes de ter baseline.
- Fechar a sessão sem `handoff` quando a investigação não terminou.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
