# SparkForge AWS — Instruções do repositório

## Antes de responder sobre artefato, rode o verbo

Pergunta sobre um artefato do repositório — código, plano, event log, custo, versão
ou regra — se responde pelo verbo do SparkForge, não pela leitura do arquivo. Chame a
tool MCP e cite na resposta o `fact_id` ou o `rule_id` que a sustenta. Ler o artefato
no olho vem depois do verbo, para conferir, nunca no lugar dele.

| Pergunta sobre | Tool MCP |
|---|---|
| código PySpark | `sparkforge_analyze_pyspark`, depois `sparkforge_judge` |
| plano físico (`explain`) | `sparkforge_analyze_plan`, depois `sparkforge_judge` |
| event log do Spark | `sparkforge_analyze_event_log`, depois `sparkforge_judge` |
| regra do catálogo | `sparkforge_rules_lookup` |
| versão e runtime | `sparkforge_runtime_detect` ou `sparkforge_release_describe` |
| custo de um run | `sparkforge_finops` |
| antes e depois entre dois runs | `sparkforge_benchmark` |

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

Este arquivo é carregado em toda sessão, então ele guarda **regra e ponteiro**, não
histórico. O texto datado que morava aqui (medidas antigas, narrativa de cada frente)
está em `docs/historico/instrucoes-arquivadas.md`, e `tests/test_bootstrap_budget.py`
trava o teto de tamanho.

## Os verbos que compõem, e quando usar cada um

`analyze *` **extrai** de artefato. Os verbos de topo **compõem** sobre facts que
outro verbo já extraiu — nenhum deles lê artefato, e é por isso que não são um
`analyze`. Antes de responder de memória, veja se a pergunta já tem verbo:

| Pergunta do operador | Verbo | O que ele consome |
|---|---|---|
| Que tipo de workload é este job? | `workload` | scan, shuffle, spill e plano, mais `--history` dos runs anteriores |
| Qual a capacidade mais barata que cumpre o SLA? | `capacity` | `glue.job_run` e o SLA declarado em `workload.yaml` |
| Quanto custou, e onde está a alavanca? | `finops` | `glue.job_run`/`glue.run_cost`, o SLA, e os sintomas ao lado |
| Que valor de configuração a medida sustenta? | `tune` | `spark.stage.shuffle`, `spark.executor.memory_usage`, `parquet.row_group`, `plan.join_side_stats`, `spark.sql.broadcast_exchange`, `spark.stage.slow_tasks`/`spark.executor.slow_node`, `spark.timeout.relation` e `spark.timeout.diagnosis` medidos, mais `spark.conf_effective`, `pyspark.conf_set` e `tf.spark_conf` |
| Quanto contexto esta execução consumiu? | `economy report` | os spans que `call_tool` grava por chamada, a superfície em repouso, e o transcript do host quando houver |
| Melhorou ou piorou entre dois runs? | `benchmark` | dois conjuntos de facts de event log |
| O resultado continua o mesmo? | `funcval plan` / `funcval compare` | os facts, a chave de negócio **declarada**, e os dois resultados que **você** mediu |
| A spec desta mudança está bem posta? | `sdd check` / `sdd status` / `sdd stamp` | o frontmatter de `docs/sdd/<FEATURE>/<fase>.md`; julga contrato, cascata por hash, cobertura e TDD declarado, nunca a prosa |
| O que estava rodando quando a sessão caiu? | `resume` (bloco `journal`) / `journal verify` | o `.sparkforge/journal.jsonl`, que `call_tool` e a CLI gravam — um `started` e um `finished` por verbo que muda estado, encadeados por hash. `started` sem `finished` é "caiu **ou** ainda roda", nunca só "caiu"; e a cadeia não detecta edição da **última** linha (quem a protege é o commit) |
| O agente acertou, com as tools certas, e recusou onde devia? | `python -m sparkforge.evals grade` / `compare` (fora da CLI `sparkforge`: o runtime não importa a avaliação) | facts `host.*` do transcript do host (`scripts/run_agentic_eval.py` gera; o pacote só lê) e o gabarito `evals/agentic/<suite>/suite.yaml`. Não conclui: lista `k/N` e transições (regra 30) |
| Como o revisor vê os findings no PR? | `report github` | findings de `judge` e a união dos facts; grava SARIF e resumo em `.sparkforge/report/`, com recusa nomeada para o que não tem linha no repositório |
| Como vejo as tools e a sessão no meu backend de tracing? | `telemetry export` | os spans que `call_tool` gravou no ledger e, com `--host-transcript`, o transcript do host; grava OTLP/JSON (`gen_ai.*`, `mcp.*`) em `.sparkforge/telemetry/` para o receiver `otlp_json_file` do Collector, com o provider declarado e recusa nomeada para span sem horário |
| Dois achados se contradizem — qual deles vale? | `arbitrate` | os findings que `judge` produziu e a **união** dos facts do case, mais o bloco `action:` de cada regra |
| Que mudança de arquivo esse valor vira, o que ela move nos achados, e como vira PR? | `change plan` / `change sandbox` / `change propose` | a procedência de `tf.spark_conf`/`pyspark.conf_set` (arquivo e linha) e o valor de `tune` ou do operador; no sandbox, um diff aplicado numa cópia em `.sparkforge/sandbox/<id>/`, julgada antes e depois pelo `scan`. Não aplica na árvore do operador nem afirma ganho (§15, `stage` próprio, fora do `AutonomyLevel`) |

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
    aumentar pode ser a decisão certa — e aí `tune` propõe
    `spark.sql.broadcastTimeout` pelo piso medido do broadcast que completou
    (com `--headroom` declarado), só com categoria `broadcast`, sem `also_seen`
    e com os limiares de sintoma lidos da própria `SF-TIMEOUT-001`.
    `wall_clock` e `heartbeat` nunca têm valor proposto.
16. **A relação entre duas propriedades é conferível; o valor isolado não é.**
    `spark.network.timeout = 120s` não é certo nem errado sozinho;
    `heartbeatInterval >= network.timeout` é errado sempre (`SF-TIMEOUT-002`).
    A relação QUEBRADA tem valor derivado: `tune` propõe
    `spark.network.timeout = heartbeat × 12` (a razão entre os defaults, 120s e
    10s), mantendo o heartbeat que alguém pediu. Com a relação de pé, sai
    `relacao_ok` e nenhum número.
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

## Economia: o que medir antes de afirmar que economizou

**106 tools, 38 com `detail_level`** (recontado em 2026-09-16). Os niveis sao `summary`,
`normal` e `full`, e a regra 28 vale para os tres. Num corpus pequeno o envelope fixo do
pacote domina, e `detail_level` quase nao move (medido em 2026-09-02: 1,3%).

**Número neste arquivo não passa por gate.** `scripts/check_vnext_claims.py` audita
`docs/vnext/` e `docs/harness/`, e mais nada. Aqui, aponte para o documento auditado em
vez de copiar o número — cópia envelhece sem que nada acuse.

### Antes de ler artefato no olho, rode o verbo

| Pergunta | Tool |
|---|---|
| onde esta X definido | `sparkforge_code_search` |
| quem chama X, e o que quebra se eu mudar | `sparkforge_code_symbol` |
| **como** X chega em Y | `sparkforge_code_path` |
| como este codigo esta organizado | `sparkforge_code_shape` |
| o pacote de contexto dentro de um teto de bytes | `sparkforge_code_context` |
| o trecho de fonte, com rotulo de conteudo nao confiavel | `sparkforge_code_read` |
| o indice esta fresco | `sparkforge_code_status` / `_sync` |
| o grafo no formato de extracao do Graphify | `sparkforge_code_export` |

**O denominador decide o sinal, e ele precisa sair junto.** Contra ler os arquivos o
índice economiza muito; contra um `grep` pelo nome, bem menos; contra um `grep`
cirúrgico pela definição ele custa mais. As três medidas estão, com data, na seção 10 de
`docs/harness/CODEINTEL-GAP.md` (auditada), e os dois primeiros números mudam a cada
arquivo `.py` novo. Citar só a primeira seria escolher o resultado.

### O gate que torna "economizou" conferivel

`python scripts/check_recall_economy.py` decide **uma** coisa e recusa outra:

- **recall nominal tem piso duro de 100%** — perguntado pelo nome do simbolo, o
  pacote entrega aquele simbolo. Economia que omite o simbolo necessario e falha;
- **recall conceitual e medido e nao tem piso** — o indice guarda NOME e o titulo
  de regra descreve DEFEITO;
- **a razao de economia sai `unresolved`** quando o corpus e menor que o envelope
  fixo do pacote. `estimated_tokens` e estimativa declarada e nunca entra numa razao.

## Desenvolver: o SDD próprio

Mudança não trivial neste repositório passa pelas skills `sdd-explore`, `sdd-define`,
`sdd-design`, `sdd-plan`, `sdd-build` e `sdd-ship`, com os artefatos em
`docs/sdd/<FEATURE>/` e cada fase conferida por `sparkforge sdd check --repo . --feature <F>`
(`sdd status`, `sdd stamp`). Elas substituem, aqui, o ciclo de spec, plano e TDD do
superpowers e o plugin AgentSpec (desligado em `.claude/settings.json`); debugging,
verificação e revisão do superpowers continuam valendo. `docs/superpowers/specs/` e
`plans/` estão congelados; o histórico do AgentSpec mora em `docs/sdd/archive/agentspec/`.
Fluxo: `docs/sdd/README.md`.

## Verificação antes de fechar

A suíte inteira num processo só não sobrevive — rode em lotes, **um por vez**. A receita
é executável e mora em `tests/test_suite_batches.py`, na constante `LOTES`, que trava três
invariantes: todo arquivo cai em ao menos um lote, nenhum cai em dois, e a soma dos lotes
é o tamanho da suíte. Qual gate cada tipo de mudança toca: `docs/gates-por-mudanca.md`.

- Área de regra nova precisa de rota em `rules/catalog/routing.yaml` **e** de coordenador
  que a declare.
- Extrator novo entra nas duas listas manuais de teste e na medida de snippet.
- Fonte citada por regra nova entra em `knowledge/sources.lock.json` via
  `python scripts/refresh_knowledge.py --offline --update`.
- Número publicado em `docs/vnext/` ou `docs/harness/` passa pelo gate de lastro
  (`python scripts/check_vnext_claims.py`); remedie pela lista de ids da saída do gate,
  nunca por varredura.
- Tool, skill ou documento de `knowledge/` novo move a superfície (regra 26).

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

## Skills AWS oficiais complementares

Onze skills de procedimento operacional AWS, adaptadas do `aws/agent-toolkit-for-aws`
(commit `10b28af8`): `provision-s3-tables-table`, `harden-s3-bucket`, `aws-storage`,
`aws-database`, `aws-serverless`, `aws-iam`, `aws-observability`,
`aws-billing-and-cost-management`, `aws-messaging-and-streaming`, `aws-security` e
`aws-sdk-python-usage`. São **não-despacháveis** — podem mutar infraestrutura AWS ao vivo,
e a fronteira `## Não faz` de cada uma exige confirmação explícita do operador por comando
de escrita. Use-as quando a pergunta for sobre o **serviço AWS** em si; diagnóstico de job
PySpark usa as skills SparkForge determinísticas (`analyze-*`, `benchmark`, `tune`,
`funcval`). As demais skills AWS ficam no nível usuário (`~/.agents/skills/`).

## Agentic Engineering Runtime

`sparkforge/agentic/` tem entidades de primeira classe (`Claim`, `Evidence`,
`Hypothesis`, `Experiment`, `Decision`, `Unknown`, `Contradiction`, `Objection`,
`Rebuttal`), o blackboard JSONL do case, debate, arbitragem, experimento, decisão com ADR,
memória, budget, segurança, autonomia L0–L5 e o grafo de execução.
`sparkforge/agentic/executor/` é o **produtor** determinístico: `authority`, `claims`,
`conflict`, `ordering`, `unknowns`, `plan`, `gate`, `digest`, `run`, `debate_run` e
`debate_evidence`. Status por componente em `docs/agentic-evolution-report.md`.

29. **A camada agêntica tem executor determinístico e executor de debate, e o
    debate não gera argumento dentro do pacote.** `sparkforge arbitrate` roda
    depois de `judge` e grava `Claim`/`Evidence`/`Contradiction`/`Unknown`/`Decision`
    no blackboard do case. Quando a arbitragem não fecha, emite um `DebatePlan`
    com `debate_gate` (§11): só o veredito `debater` abre debate — severidade em
    `rules/catalog/debate_gate.yaml`, ação com `reversible: false` em
    `action_kinds.yaml`, ou arbitragem sem lastro; lacuna mensurável citando o par
    recusa `gate_experimentar_antes`, par barato e reversível `gate_nao_debater`,
    sinal ausente `gate_unresolved`. `sparkforge debate start|next|submit` (tools
    `LOCAL_MUTATION`) é máquina de estados L0 sobre `.sparkforge/debate/<debate_id>/`:
    diz de quem é a vez, recusa por nome a submissão que fere o protocolo, só aceita
    evidência nova **reextraída** por extrator da allowlist, exige `budget:` declarado
    no case (`budget_undeclared`) e fecha **sempre** pelo `referee`. `sparkforge debate
    referee` só lê, e recusa hipótese que sobrevive ao fechamento, claim sem
    `evidence_refs`, objeção sem réplica e referência pendurada. Quem escreve o
    argumento é o host (skill `run-debate`, `scripts/run_debate.py`); nenhum
    `AgentRuntime` concreto mora neste pacote (regra 23). Os dois executores são
    **L0**: `applied_changes` sai sempre `false`, e o ADR é proposta com `rollback`
    obrigatório. **Alcance medido: um par** (`SF-GRAPH-005` × `SF-LF-001`), só na
    união de dois jobs.
30. **Não há benchmark da camada agêntica, e por isso não há afirmação de
    ganho.** Comparar arquitetura nova com antiga exige os dois lados rodando o
    mesmo caso bem posto; o único par que o catálogo produz só existe na união de
    dois jobs. Nenhuma medida de ganho de token, latência, custo ou qualidade foi
    publicada, e nenhuma pode ser até existir um caso bem posto rodando nos dois
    lados. Regra 28 vale aqui igual.
31. **Lake Formation são DOIS modelos, e a versão muda o significado.** FGAC e
    Full Table Access não coexistem no mesmo job, e a diferença que decide não é
    granularidade — é **quem vende a credencial**: sob FGAC a escrita usa IAM do
    runtime role; sob FTA a credencial do Lake Formation lê e escreve as tabelas
    **registradas**. Três fronteiras de versão mudam o diagnóstico: o Glue 5.0
    removeu FGAC via `GlueContext`/DynamicFrame, o 5.0 não escrevia sob FGAC e o
    5.1 escreve, e o 5.1 trocou o filesystem S3 default de EMRFS para **S3A** —
    o que quebra FTA calado, porque `fs.s3.credentialsResolverClass` é chave de
    EMRFS e sob S3A é ignorada sem erro. Afirmar "FGAC não escreve" sem dizer a
    versão é erro de versão. Eixo completo em
    `knowledge/glue/lakeformation-fgac.md` §0 e §5.
32. **Escrita em tabela REGISTRADA sob FGAC é conflito declarado, não resposta.**
    Quatro frases da documentação da AWS não fecham entre si (§6 do documento de
    conhecimento). Não escolha um lado: apresente as três saídas que a
    documentação sustenta. E **a API de escrita não é o caminho de
    autorização** — `writeTo`, `insertInto` e `INSERT INTO` falhando juntas é
    sinal de que a variável está em catálogo, filesystem, credencial ou
    permissão, nunca na API.
33. **Predicado que o `where` não alcança vira FACT, nunca um `expr` mais
    permissivo.** `sparkforge/rules/expr.py::_CMP_OPS` tem seis comparadores e
    nenhuma função — sem `startswith`, sem `in`, e `ast.Call` levanta `ExprError`
    por desenho de segurança. Quando a regra precisa de mais do que igualdade
    (por exemplo "o nome do catálogo dentro de `spark.sql.catalog.<nome>` é o
    session catalog?"), derive o predicado num extrator. Precedente medido:
    `sparkforge/facts/lakeformation.py`, 2026-09-09.

### CLI commands agênticos

```bash
sparkforge agents list           # lista agentes
sparkforge agents inspect <id>   # inspeciona agente
sparkforge blackboard summary    # resumo do blackboard
sparkforge blackboard list --type <tipo>  # lista entidades
sparkforge decisions list        # lista decisoes
sparkforge decisions explain <id>  # explica decisao
sparkforge budget show           # budget DECLARADO do case
sparkforge budget show --template  # defaults do codigo, rotulados
sparkforge autonomy show --level L3  # perfil de autonomia
sparkforge arbitrate --findings <path> --facts <path> --repo .  # ESCREVE
sparkforge debate start --rules A,B --findings <path> --facts <path> --repo .  # ESCREVE
sparkforge debate next --debate <id> --repo .    # ESCREVE (a Decision, no fechamento)
sparkforge debate submit --debate <id> --file <json> --repo .  # ESCREVE
sparkforge debate referee --repo .               # so le
```

`--facts` é **repetível, e a repetição é o contrato**: o executor recebe a UNIÃO dos facts
do case, o mesmo conjunto que `judge` recebeu (§12.9 do spec). Alimentá-lo com um
subconjunto fabrica claim desancorada. Ele **não estima ganho**, **não publica score como
confiança medida** e **não gera argumento de debate**. `budget show` lê o bloco `budget:`
do `case.yaml`; sem ele, `limits.status = "unresolved"` nomeando a lacuna, e consumo
aponta `economy report --run-id` (token exige transcript, regra 24; dólar exige
`cost_basis`, regra 25).

### Evidence Authority Tiers

T1 (docs oficial) > T2 (source/changelog) > T3 (benchmark reproduzível) >
T4 (autoridade reconhecida) >> T5 (LLM) > T6 (conjectura). T5 e T6 **nunca**
são suficientes sozinhos para confirmar uma claim de alta confiança.
`has_sufficient_authority` é só o tier; `has_fresh_in_scope` é tier **mais** vigência e
escopo — uma T1 fora da versão alvo tem autoridade e não sustenta a claim.

### Autonomy Levels

L0 deterministic → L1 specialist → L2 cooperative → L3 debate → L4 experimental
→ L5 autonomous engineering. **O perfil EXIGIR um guardrail não é o mesmo que tê-lo
obtido:** `validate_autonomy_boundary` recebe `guardrails_satisfied` do chamador e recusa
ação de alto risco enquanto o `required_validation` do nível não estiver coberto.

### Arbitragem: o que o score é, e o que ele não é

Os pesos de `assess_claim` (evidência 40%, autoridade 30%, especificidade 20%,
aplicabilidade 10%) são **convenção**, não medida — nenhum experimento os calibrou.
Eles ordenam claims dentro de uma mesma arbitragem; o valor absoluto não é confiança
medida e não deve ser publicado como tal. Uma claim avaliada sozinha não é arbitragem:
sai com `disputed=False`.

Spec: `docs/superpowers/specs/2026-09-03-sparkforge-agentic-evolution-design.md`
