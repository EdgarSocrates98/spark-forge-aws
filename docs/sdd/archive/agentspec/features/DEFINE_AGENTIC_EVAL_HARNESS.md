# DEFINE: Agentic Eval Harness

> Pontuar, de forma determinística, transcripts de agentes rodados pelo host contra ground truth versionado, e comparar baseline com candidato por `k/N` sem inventar veredito.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AGENTIC_EVAL_HARNESS |
| **Date** | 2026-09-10 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

**Input:** `.claude/sdd/features/BRAINSTORM_AGENTIC_EVAL_HARNESS.md` (tipo `brainstorm_document`, Abordagem A confirmada pelo operador em 2026-09-10).

---

## Problem Statement

O nível de agente das evals do SparkForge (`evals/fase0.xml`, 10 pares) roda à mão e só deixa uma tabela de placar no README, sem transcript e sem registro de quais tools foram chamadas. Por isso nenhuma mudança agêntica (descrição de tool, protocolo, MCP v2, runtime, debate) consegue mostrar que não regrediu, e a regra 30 do `CLAUDE.md` bloqueia qualquer afirmação de ganho.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Mantenedor do SparkForge | Muda descrição de tool, `AGENT_PROTOCOL.md`, versão do MCP | Não sabe se a mudança fez os agentes errarem, chamarem a tool errada ou afirmarem onde deviam recusar |
| Operador que compara modelo ou host | Roda Haiku, Sonnet, Opus e Devin contra a suíte | Hoje compara por tabela manual (`evals/README.md`, 2026-07-30), sem transcript e sem distinguir mudança de ruído |
| Frentes futuras do roadmap (debate, AgentRuntime, MCP v2) | Consomem o baseline | Não têm contra o que medir, e a regra 30 as bloqueia até existir baseline |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1 — Extrator `host_transcript` lê o JSONL do Claude Code e emite facts de tool call (verbo canônico, ordem, bytes do resultado), resposta final e usage, com toda anomalia de forma recusada por nome |
| **MUST** | G2 — Ground truth agêntico em `evals/agentic/fase0/suite.yaml`, que referencia as 10 perguntas de `fase0.xml` sem alterar o XML e acrescenta `required_tools`, `order` e perguntas de abstention |
| **MUST** | G3 — `sparkforge eval grade` produz veredito por pergunta nas quatro medidas (resposta, abstention, tools, custo) e um `scorecard.json` sem nota composta |
| **MUST** | G4 — `sparkforge eval compare` lê N scorecards por lado e emite classes `pass`/`fail`/`mixed`, a matriz de transição por pergunta e as recusas `suite_mismatch`/`single_sample` |
| **MUST** | G5 — Fixtures sintéticas de transcript com golden test do extrator e do grader, sem nenhum transcript real no repo |
| **MUST** | G6 — Invariantes preservadas: `sparkforge/` não chama provider nem dispara processo de host (regra 23), e byte e token nunca se somam (regra 22) |
| **SHOULD** | G7 — Runner `scripts/run_agentic_eval.py`: uma pergunta por sessão `claude -p`, um JSONL por pergunta, gravado fora do repo |
| **SHOULD** | G8 — Primeiro baseline real registrado: scorecards commitados (só ids e números) e uma seção nova em `evals/README.md` |
| **COULD** | G9 — A varredura de superfície de agente passa a proibir citação de `evals/agentic/` em `skills/`, `agents/`, `knowledge/` e nos espelhos `.claude/` e `.agents/` |

---

## Success Criteria

- [ ] SC1 — ≥ 8 fixtures sintéticas em `fixtures/host_transcript/`, uma por desfecho (`correct`, `wrong`, `answer_absent`, `over_abstention`, `false_certainty`, tool faltando, ordem violada, envelope quebrado), e 100% delas produzem `scorecard.json` byte-idêntico ao `expected/` em 2 execuções consecutivas
- [ ] SC2 — 0 fixtures de envelope ou campo quebrado resultam em veredito `wrong`: todas saem `ungraded`, com a lacuna nomeada no scorecard
- [ ] SC3 — `suite.yaml` cobre 10/10 perguntas de `fase0.xml` com `required_tools` não vazio e acrescenta ≥ 3 perguntas com `expects_abstention: true`, cada uma ancorada num fact `*.unresolved` que o corpus realmente emite (conferido por teste que roda o extrator sobre a fixture citada)
- [ ] SC4 — `eval compare` sobre dois diretórios com hash de `suite.yaml` diferente sai com `suite_mismatch` e 0 transições emitidas; com N=1 em qualquer lado, o cabeçalho traz `single_sample: true`
- [ ] SC5 — `scripts/check_evals.py` continua passando e `fase0.xml` tem 0 linhas alteradas
- [ ] SC6 — o teste que varre imports segue verde: 0 ocorrências de `anthropic`, `openai`, `bedrock`, `litellm` e 0 de `subprocess` disparando `claude` sob `sparkforge/`
- [ ] SC7 — cada arquivo de teste novo cai em exatamente 1 lote de `tests/test_suite_batches.py::LOTES`, e o gate de lastro (`scripts/check_vnext_claims.py`) passa
- [ ] SC8 (SHOULD) — uma execução do runner com N ≥ 3 por pergunta gera 13 × N transcripts, o `eval grade` pontua 100% deles sem exceção não tratada, e o scorecard resultante é commitado

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Acerto | Transcript com `tool_use` de `analyze_pyspark` e `judge` nessa ordem, terminando com `ANSWER: SF-PY-005:2` | `eval grade` com a pergunta `fase0#1` | resposta `correct`, tools `ok`, custo com `tool_calls=2` e tokens do usage |
| AT-002 | Erro de resposta | Mesmo transcript, com `ANSWER: SF-PY-004:2` | `eval grade` | resposta `wrong`, tools `ok` (as medidas são independentes) |
| AT-003 | Sem linha de resposta | Transcript sem nenhuma linha `ANSWER:` | `eval grade` | resposta `answer_absent`, nunca `wrong` |
| AT-004 | Falsa certeza | Pergunta com `expects_abstention: true` e transcript terminando em `ANSWER: 42` | `eval grade` | abstention `false_certainty`; agregado `false_certainty/abstention_total` incrementa |
| AT-005 | Abstention correta | Mesma pergunta, com `ANSWER: unresolved` | `eval grade` | abstention `abstained` |
| AT-006 | Recusa indevida | Pergunta com valor esperado e transcript com `ANSWER: unresolved` | `eval grade` | resposta `over_abstention` |
| AT-007 | Tool faltando | `required_tools: [analyze_pyspark, judge]` e transcript só com `judge` | `eval grade` | tools `missing:[analyze_pyspark]` |
| AT-008 | Ordem violada | `order: [analyze_pyspark < judge]` e primeira ocorrência de `judge` antes da de `analyze_pyspark` | `eval grade` | tools `order_violated:[analyze_pyspark<judge]` |
| AT-009 | Tool extra | Transcript com as tools exigidas mais `rules_lookup` | `eval grade` | tools `ok`; `tool_calls` conta 3 |
| AT-010 | Normalização de canal | Um `tool_use` `mcp__sparkforge__sparkforge_judge` e outro Bash com `sparkforge judge ...` | `eval grade` | os dois viram o verbo canônico `judge` |
| AT-011 | Bash não reconhecido | Bash com `ls fixtures/` | `eval grade` | contado como `other`, sem influir em `required_tools` |
| AT-012 | Envelope quebrado | JSONL com linha não-JSON e `message` em forma de lista | `eval grade` | pergunta `ungraded`; lacunas `host_format_unknown`/`message_field_not_object` no scorecard; nenhuma exceção sobe |
| AT-013 | Sem usage | Transcript sem `usage` nas linhas de assistente | `eval grade` | custo com `tokens_unresolved`; `tool_result_bytes` e `tool_calls` presentes |
| AT-014 | Bytes separados de tokens | Qualquer scorecard | leitura do schema | `tool_result_bytes` e os campos de token são campos distintos e não existe nenhum campo que some os dois |
| AT-015 | Compare estável | A e B com N=3 cada, pergunta X `3/3` nos dois | `eval compare A B` | X classificada `pass→pass` |
| AT-016 | Compare com virada | A com X `3/3` e B com X `1/3` | `eval compare` | X `pass→mixed`, com `3/3` e `1/3` crus ao lado; nenhum rótulo agregado "piorou" |
| AT-017 | Suíte diferente | Scorecards de A e B com hash de `suite.yaml` diferente | `eval compare` | recusa `suite_mismatch`, 0 transições |
| AT-018 | Amostra única | A com N=1 | `eval compare` | executa e marca `single_sample: true` no cabeçalho |
| AT-019 | Host/modelo diferente | A com `model=X` e B com `model=Y` | `eval compare` | executa; a diferença aparece reportada, não recusada |
| AT-020 | Determinismo | Mesma fixture | `eval grade` duas vezes | saídas byte-idênticas |

---

## Out of Scope

- Tool MCP `sparkforge_eval_*` (evita mover `surface.lock` e os sete registros manuais)
- Gate de merge em PR e qualquer execução de agente no CI: o CI testa o grader, não os agentes
- Métricas de debate (root-cause accuracy, debate resolution, unnecessary debate), porque não há executor de debate
- Robustez a perturbação, stale-source, routing accuracy, intervenção humana, regressão introduzida
- Latência por tarefa
- Custo em dólar (regra 25)
- Formato de transcript do Devin ou de qualquer host que não seja Claude Code
- p-value, intervalo de confiança ou qualquer estatística inferencial
- Exportação OTel e backends externos (AgentCore Evaluations, Langfuse)
- LLM-as-judge em qualquer medida
- Todas as demais frentes de `prompt_new_evo.md`

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 23: `sparkforge/` não importa provider nem dispara host | Runner obrigatoriamente em `scripts/`; o pacote só lê arquivo |
| Technical | Regras 22 e 24: byte ≠ token; token só com transcript | Colunas separadas; sem usage sai `tokens_unresolved` |
| Technical | Regra 25: dólar exige `cost_basis` | Nenhum campo monetário no scorecard |
| Technical | Regra 27: medição nunca derruba a chamada | Linha ruim vira lacuna; pergunta sai `ungraded` e o resto segue |
| Technical | Regra 30: o harness não afirma ganho | O compare lista transições e não conclui |
| Technical | `fase0.xml` é recomputado por `scripts/check_evals.py` | Formato do XML intocado; ground truth novo em sidecar |
| Technical | Extrator novo entra nas duas listas manuais de teste e na medida de snippet | O Design precisa nomear os registros tocados |
| Technical | A suíte roda em lotes (`tests/test_suite_batches.py::LOTES`) | Todo arquivo de teste novo cai em exatamente 1 lote |
| Technical | Número publicado em `docs/vnext/` ou `docs/harness/` passa por `scripts/check_vnext_claims.py`; arquivo `.py` novo move alegações | Rodar o gate de lastro antes de cada commit |
| Security / Privacy | Caso real nunca entra em arquivo; o repo é público | Transcripts fora do repo; fixtures sintéticas; scorecard só com ids e números |
| Resource | Execução real gasta token do host | O runner nunca roda no CI; roda sob comando do operador |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/collect/host_transcript.py` (extrator, ao lado de `host_usage.py`); lógica de grade e compare em módulo novo sob `sparkforge/` (o Design decide entre `sparkforge/facts/` e `sparkforge/evals/`, no molde de `sparkforge/facts/benchmark.py`); verbo em `sparkforge/adapters/cli.py` (tabela de despacho perto da linha 3647, como `("benchmark", None): _cmd_benchmark`); runner em `scripts/run_agentic_eval.py`; ground truth em `evals/agentic/fase0/suite.yaml`; fixtures em `fixtures/host_transcript/<caso>/{input,expected}/` | Segue o padrão `collect *` para quem lê artefato de fora e o padrão `benchmark` para comparar dois lados |
| **KB Domains** | agentspec: `testing`, `python`, `pydantic`, `genai`. Repo: `evals/README.md`, `sparkforge/collect/host_usage.py`, `sparkforge/facts/benchmark.py`, `tests/test_evals_holdout.py`, `docs/agentic-evolution-report.md` | O KB do agentspec é genérico; os padrões decisivos estão no codebase |
| **IaC Impact** | None | Nada provisionado. O runner usa o binário `claude` local |

---

## Data Contract (if applicable)

N/A. Não há pipeline de dado. O "schema" relevante é o de artefato local (`suite.yaml`, `scorecard.json`), que o Design especifica.

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O transcript JSONL do Claude Code traz `tool_use` como bloco de `message.content` nas linhas `assistant`, com `name`/`input`/`id`, e `tool_result` nas linhas `user` | O extrator teria de ler outro formato | [x] Conferido em 2026-09-10 no transcript local desta sessão: 37 blocos `tool_use` com chaves `caller,id,input,name,type` e 36 `tool_result` em linhas `user`. Nada foi commitado |
| A-002 | `claude -p` produz transcript no mesmo formato de sessão, seja o arquivo persistido em `~/.claude/projects/` ou `--output-format stream-json` | O runner precisa de conversão, ou o extrator de um segundo formato recusado por nome | [ ] Validar no Design, antes do runner |
| A-003 | Um agente segue a instrução de terminar com `ANSWER: <valor>` em ≥ 90% das execuções | `answer_absent` dominaria e mascararia o resto; a instrução de formato precisaria ser revisada, nunca afrouxada no grader | [ ] Medido pelo próprio baseline (SC8) |
| A-004 | Existem ≥ 3 facts `*.unresolved` no corpus sobre os quais cabe uma pergunta cuja resposta certa é recusar (ex.: `pyspark.unresolved`, `attrs.reason: getattr`, em `dynamic_dispatch`) | SC3 não fecha; seria preciso fixture nova | [ ] Validar no Design, listando os candidatos |
| A-005 | O custo de N ≥ 3 execuções × 13 perguntas é aceitável para um baseline sob comando do operador | O baseline sai com N=1 e `single_sample` | [ ] Decisão do operador na primeira execução |
| A-006 | As 10 perguntas de `fase0.xml` citam fixtures visíveis e por isso medem uso correto de tool, não generalização | Leitura errada do que o baseline prova | [x] É o que `evals/README.md` declara ("mede se um agente usa as ferramentas corretamente") |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Uma frase, com a lacuna declarada no próprio repo (`evals/README.md:59`) e a regra que ela bloqueia |
| Users | 2 | Três personas com dor concreta, todas internas. Não há usuário externo, e isso é coerente com o recorte |
| Goals | 3 | Nove metas com MoSCoW, cada uma mapeada a um artefato |
| Success | 3 | Oito critérios com contagem ou igualdade byte-a-byte, e vinte testes de aceitação |
| Scope | 3 | Onze exclusões explícitas, herdadas do YAGNI confirmado |
| **Total** | **14/15** | |

---

## Open Questions

Nenhuma bloqueia o Design. Duas ficam como validação dentro dele:

1. A-002: formato exato do que `claude -p` grava, e se o runner lê o arquivo persistido ou o `stream-json`.
2. A-004: lista nominal das ≥ 3 perguntas de abstention e o fact de corpus que ancora cada uma.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-10 | define-agent | Versão inicial, derivada de `BRAINSTORM_AGENTIC_EVAL_HARNESS.md`; A-001 validada contra transcript local |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_AGENTIC_EVAL_HARNESS.md`
