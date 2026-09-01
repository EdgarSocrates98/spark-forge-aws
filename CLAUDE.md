# SparkForge AWS — Instruções do repositório

Ao trabalhar em código PySpark destinado ao AWS Glue:

1. Verifique a versão de Glue, Spark, Python e Iceberg antes de sugerir APIs ou configurações.
2. Não recomende tuning baseado somente no código; solicite ou produza plano físico e baseline quando possível.
3. Identifique o gargalo dominante: CPU, memória, GC, shuffle, skew, driver, S3, metadados, small files ou capacidade do cluster.
4. Priorize redução de trabalho e movimentação de dados antes de aumentar workers.
5. Prefira funções nativas Spark SQL a Python UDFs.
6. Não use `collect`, `toPandas`, `coalesce(1)`, `repartition` arbitrário ou `cache` indiscriminado.
7. Toda recomendação deve conter evidência, impacto esperado como hipótese, risco, validação e rollback.
8. Preserve semântica e valide contagens, schema, chaves, agregados e regras de negócio.
9. Para Iceberg, diferencie data files, delete files, manifests, snapshots e metadata files.
10. Nunca execute manutenção destrutiva sem confirmação explícita de escopo e retenção.

Use o agente `spark-performance-architect` para investigações abrangentes e as Skills específicas para tarefas focadas.

## Os verbos que compõem, e quando usar cada um

`analyze *` **extrai** de artefato. Os verbos de topo **compõem** sobre facts que
outro verbo já extraiu — nenhum deles lê artefato, e é por isso que não são um
`analyze`. Antes de responder de memória, veja se a pergunta já tem verbo:

| Pergunta do operador | Verbo | O que ele consome |
|---|---|---|
| Que tipo de workload é este job? | `workload` | scan, shuffle, spill e plano, mais `--history` dos runs anteriores |
| Qual a capacidade mais barata que cumpre o SLA? | `capacity` | `glue.job_run` e o SLA declarado em `workload.yaml` |
| Quanto custou, e onde está a alavanca? | `finops` | `glue.job_run`/`glue.run_cost`, o SLA, e os sintomas ao lado |
| Que valor de configuração a medida sustenta? | `tune` | `spark.stage.shuffle` medido, mais `spark.conf_effective`, `pyspark.conf_set` e `tf.spark_conf` |
| Quanto contexto esta execução consumiu? | `economy report` | os spans que `call_tool` grava por chamada, a superfície em repouso, e o transcript do host quando houver |
| Melhorou ou piorou entre dois runs? | `benchmark` | dois conjuntos de facts de event log |
| O resultado continua o mesmo? | `funcval plan` / `funcval compare` | os facts, a chave de negócio **declarada**, e os dois resultados que **você** mediu |

Regras que valem para todos eles:

11. **Custo é fact, limiar é regra, valor proposto não é nem um nem outro.**
    `glue.run_cost` é aritmética sobre `dpu_seconds` medido — entra no motor de
    regras. Um valor **proposto** de configuração é escolha (existe um alvo, e
    alvo é decisão) e por isso mora em `tune`, fora do catálogo.
12. **Nunca interpole entre capacidades observadas.** DPU-segundos não é
    invariante na troca entre mais recurso e mais tempo. Compare as capacidades
    que o job **já rodou**, lado a lado, e recuse extrapolar.
13. **Nunca atribua custo a uma causa, nem estime economia.** "Você
    desperdiçou X com spill" e "você economizaria Y" exigem o custo do run que
    **não** aconteceu. Nomeie o sintoma ao lado do custo, sem subtraí-lo dele.
14. **Sem `dpu_seconds` não há custo.** Sob Auto Scaling sem `DPUSeconds`,
    `number_of_workers` é teto e não uso: a resposta é
    `glue.run_cost.unresolved`, nunca custo zero.
15. **"Timeout" é quatro coisas.** Leia `spark.timeout.diagnosis.attrs.category`
    — `wall_clock`, `broadcast`, `network`, `heartbeat` — e o `also_seen` antes
    de tocar em configuração. O relógio do Glue é consequência, não causa.
    Aumentar o limite com skew, spill, GC ou executor perdido ao lado troca uma
    falha rápida por uma falha cara (`SF-TIMEOUT-001`). Sem sintoma nenhum,
    aumentar pode ser a decisão certa.
16. **A relação entre duas propriedades é conferível; o valor isolado não é.**
    `spark.network.timeout = 120s` não é certo nem errado sozinho;
    `heartbeatInterval >= network.timeout` é errado sempre (`SF-TIMEOUT-002`).
17. **Utilização baixa não é sinônimo de capacidade sobrando.** Com skew alto,
    o worker está ocioso **porque** uma task segura o stage, e reduzir workers
    não toca a causa (`SF-WASTE-002`). Só com as quatro medidas apontando junto
    — worker ocioso, memória e disco com folga, e sem skew — a pergunta de
    capacidade tem base (`SF-WASTE-001`).
18. **A versão muda o significado do número, não o número.** Com AQE default
    (Spark 3.2+, Glue 4.0 e 5.x), `spark.sql.shuffle.partitions` é o piso de
    paralelismo inicial que o motor coalesce; sem AQE (Glue 3.0), é o número
    final de partições. Recomendar "confie no AQE" para Glue 3.0 é erro de
    versão.
19. **Procedência responde quem PEDIU, não quem venceu.** `code`, `terraform`,
    `runtime_or_cluster`, `spark_default_explicit`, `unset`. A quarta é o
    sintoma a caçar: configuração escrita à mão com o valor do próprio default.
20. **Recusa tem nome.** Toda propriedade sem base medida sai em `refused` com a
    medida que a destravaria, e toda lacuna sai como `*.unresolved`. Listar a
    recusa é a diferença entre "não sei" e "não perguntei".
21. **Hipótese tem três partes e um desfecho.** `--hypothesis`,
    `--prediction` e `--experiment` são obrigatórios juntos; fechar é
    `--close-hypothesis` com `--hypothesis-outcome` (`confirmed`, `refuted`,
    `abandoned`). Fechar é acréscimo: nunca reescreva a afirmação para casar com
    o resultado.
22. **Byte e token são unidades diferentes, e nunca se somam.** Byte de
    payload é o que o SparkForge produziu; token de provider é o que o host
    gastou. Aparecem lado a lado no relatório, nunca num total comum — somar os
    dois dá um número que não mede nada.
23. **O projeto não chama provider nenhum.** Medido: `sparkforge/` não importa
    `anthropic`, `openai`, `bedrock` nem `litellm`. Quem gasta token é o host
    que executa os agents. Antes de propor "instrumentar a chamada de modelo",
    lembre que não existe chamada de modelo aqui para instrumentar.
24. **Token só com fonte.** `payload_bytes` é medido e sempre existe. Token de
    provider só aparece quando há transcript do host. Sem fonte sai
    `tokens_unresolved` — nunca um `len(conteúdo) // 4` vestido de token.
25. **Custo em dólar exige `cost_basis`.** Preço sem fonte nomeada é número
    inventado, e chamada de tool local não tem tabela de preço publicada.
26. **A superfície cresce declarando.** `docs/surface.lock.json` trava o peso de
    tools, skills e knowledge, com hash da composição — acrescentar tool não é
    proibido, é obrigado a **dizer de quanto foi**. Rode
    `python scripts/check_surface_lock.py --update` e declare o crescimento no
    commit.
27. **Medição nunca derruba a chamada.** Ledger indisponível, disco cheio, span
    que falha ao ser montado: a tool devolve o resultado do mesmo jeito.
    Instrumentação que quebra o produto é defeito, não observabilidade.
28. **Antes de afirmar que `detail_level` reduz, leia o número.** Essa frase
    esteve publicada por muito tempo sem medição. Hoje `economy report` traz
    `detail_level_effect` com os bytes de cada nível pedido — ele mostra os dois
    e não conclui por você.

## Verificação antes de fechar

A suíte inteira num processo só não sobrevive — rode em lotes (ver
`docs/gates-por-mudanca.md` para qual gate cada tipo de mudança toca). Área de
regra nova precisa de rota em `rules/catalog/routing.yaml` **e** de coordenador
que a declare; extrator novo entra nas duas listas manuais de teste e na medida
de snippet; fonte citada por regra nova precisa entrar em
`knowledge/sources.lock.json` via `python scripts/refresh_knowledge.py --offline
--update`. Número publicado em `docs/vnext/` ou `docs/harness/` passa pelo gate
de lastro (`python scripts/check_vnext_claims.py`), e remediá-lo é por lista de
ids tirada da saída do gate, nunca por varredura. Tool, skill ou documento de
`knowledge/` novo move a superfície e exige
`python scripts/check_surface_lock.py --update`, com o crescimento declarado no
commit.

A suíte inteira num processo só não sobrevive — rode em lotes, um por vez. **A
receita é executável e mora em `tests/test_suite_batches.py`, na constante
`LOTES`**; esta página aponta para ela em vez de repeti-la, e a razão é medida.

Enquanto a receita era prosa, `tests/test_fixtures_golden.py` — **90 testes** —
não caía em lote nenhum: o lote `f` se escrevia `ls tests/test_f*.py | grep -v
golden`, e o `grep` o excluía junto com os `test_fixtures_golden_*`, que ele não
é (falta o underscore). A suíte coletava 8662 e a receita somava 8572. Quem
seguisse o procedimento publicado fechava verde com 90 testes sem execução, e
nada acusava.

Hoje `test_suite_batches.py` trava três invariantes: todo arquivo cai em ao menos
um lote, nenhum cai em dois, e a soma dos lotes é o tamanho da suíte. Arquivo de
teste com nome que nenhum lote pega passa a derrubar o gate.

## Compressão de output

O ecossistema caveman está vendorizado em `vendor/` e ligado por padrão, com o modo
fixado em `full` por `.caveman/config.json`. No Claude Code ele se ativa sozinho.
Qualquer outro agente aplica o ruleset de `AGENTS.md`, seção *Output compression —
caveman mode*.

O que a compressão **não** toca: o schema `recommendation:`/`Finding` inteiro,
números, versões, `rule_id`, `fact_id`, strings de erro e blocos de código. Campo de
evidência apagado para economizar token é defeito, não compressão.

Créditos: [`vendor/CREDITS.md`](vendor/CREDITS.md).

## Investigação avançada

Para jobs com fluxos full/incremental, use primeiro o agente `glue-incremental-performance-architect` e leia `PROMPT_INICIAL_MESTRE.md`. Não faça tuning localizado antes de mapear a biblioteca, actions, batching, latest-per-key e OOM.

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
rtk uv run <cmd>        # Compact uv project command output
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->