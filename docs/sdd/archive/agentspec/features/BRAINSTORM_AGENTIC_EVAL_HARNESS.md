# BRAINSTORM: Agentic Eval Harness

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AGENTIC_EVAL_HARNESS |
| **Date** | 2026-09-10 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** `prompt_new_evo.md` — avaliação externa do SparkForge com ~30 frentes de evolução (Forge Pack, MCP v2, A2A, AgentRuntime, OTel GenAI, Scientific Debate, Execution Receipt, Change Proof, Fleet, Control Plane...). O §12 do prompt pede um "SparkForge Evaluation Lab": toda mudança agêntica testada contra um corpus versionado, com baseline contra candidato. O operador escolheu recortar o brainstorm em **uma** frente P0, e a frente escolhida foi o harness de eval agêntico.

**Context Gathered:**
- `evals/README.md:59` declara: "Não há harness automatizado de execução de agente neste repositório". O nível de agente de `evals/fase0.xml` (10 pares pergunta/resposta) roda hoje à mão, e das execuções de 2026-07-30 só sobrou a tabela de placar no README.
- Regra 30 do `CLAUDE.md`: sem benchmark da camada agêntica, nenhuma afirmação de ganho. Toda frente do prompt que promete ganho (runtime, debate, router, MCP v2) esbarra nessa regra antes de começar, e é isso que põe o harness à frente delas.
- Regra 23: `sparkforge/` não chama provider. O harness respeita isso por desenho: o host executa, o SparkForge só pontua arquivo.
- `sparkforge/collect/host_usage.py::read_host_usage` já lê o transcript JSONL do Claude Code, com lacunas nomeadas (`usage_field_absent`, `usage_value_malformed`, `usage_value_fractional`, `usage_value_negative`). Ele só soma usage e não extrai sequência de `tool_use` nem resposta final.
- `benchmark` e `funcval compare` já seguem o molde "compõe sobre dois conjuntos medidos e recusa o que não é comparável" — é o precedente da Abordagem A.
- O corpus de cenários retidos tem invariante provada por `tests/test_evals_holdout.py`: nenhum arquivo de `skills/`, `agents/`, `knowledge/` ou dos espelhos `.claude/` e `.agents/` cita um cenário retido nem o caminho do diretório. Este documento mora em `.claude/` e por isso também não o cita (o teste o pegou durante o build).
- Não existe fixture de transcript no repo. `tests/test_collect_host_usage.py` monta os seus inline.

**Afirmações do prompt que ficam fora deste documento, e por quê:**
- "MCP Python SDK v2 é a linha estável, spec `2026-07-28`": data posterior ao corte de conhecimento do modelo e sem fonte T1 conferida nesta sessão. Fica como T5 até alguém ler a fonte. Afeta a frente MCP v2, não esta.
- Capacidades do AgentCore Evaluations: mesma situação. Esse é o motivo de a Abordagem C não depender delas.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/collect/host_transcript.py` (extrator), verbo `eval` em `sparkforge/cli/`, runner em `scripts/run_agentic_eval.py`, ground truth em `evals/agentic/<suite>/suite.yaml`, fixtures em `fixtures/host_transcript/` | Extrator novo entra nas duas listas manuais de teste e na medida de snippet (`CLAUDE.md`, "Verificação antes de fechar") |
| Relevant KB Domains | agentspec `testing`, `genai`, `python`, `pydantic`; repo: `evals/README.md`, `docs/agentic-evolution-report.md`, `sparkforge/economy/` | O KB do agentspec é genérico e não tem padrão de eval de agente sobre transcript. A evidência decisiva é o padrão do próprio codebase |
| IaC Patterns | N/A | Nada provisionado. Runner local chamando `claude -p` headless |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Recorte do brainstorm: uma frente P0, roadmap, reposicionamento ou triagem do prompt? | Uma frente P0 | As outras ~29 frentes ficam fora e são registradas no YAGNI |
| 2 | Qual frente P0? | Eval harness agêntico | Não altera invariante (regra 23) e é pré-requisito da regra 30 para as demais |
| 3 | Quais medidas no MVP? | Resposta exata, sequência de tools, falsa certeza, custo por tarefa | Exige ground truth novo para tools e abstention. Resposta exata reusa `fase0.xml` |
| 4 | Quem produz o transcript? | Grader offline no pacote, runner fora do pacote (`scripts/`), sem execução no CI | O CI testa o grader com fixtures sintéticas. Gasto de token só quando o operador roda o runner |
| 5 | Que amostras existem? | Sintéticas, derivadas do formato já documentado em `host_usage` | Nenhum transcript real entra no repo. Fixtures escritas à mão por desfecho |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/host_transcript/` (a criar) | ~8 | JSONL sintético no formato Claude Code (`type: assistant`, `message.usage`, blocos `tool_use`/`tool_result`), um por desfecho: acerto, erro, `answer_absent`, `over_abstention`, `false_certainty`, tool faltando, ordem violada, envelope quebrado |
| Output examples | `fixtures/host_transcript/*/expected/scorecard.json` (a criar) | ~8 | Scorecard esperado por fixture, conferido por golden test |
| Ground truth | `evals/fase0.xml` (existe) + `evals/agentic/fase0/suite.yaml` (a criar) | 10 + ~3 | 10 respostas já recomputadas por `scripts/check_evals.py`. Abstention nova ancorada em `*.unresolved` que o corpus já produz (ex.: `pyspark.unresolved` com `attrs.reason: getattr` em `dynamic_dispatch`) |
| Related code | `sparkforge/collect/host_usage.py`, `tests/test_collect_host_usage.py`, verbo `benchmark`, `funcval compare`, `scripts/check_evals.py`, `tests/test_evals_holdout.py` | 6 | Leitor de transcript e validação de campo a estender. Molde de compare com recusa nomeada. Invariante de holdout a ampliar |

**How samples will be used:**

- Golden tests do extrator e do grader, nas duas direções (facts e scorecard), como `tests/test_fixtures_golden.py` faz para o resto do corpus
- Casos de borda do parser: envelope quebrado deve sair como lacuna nomeada e pergunta `ungraded`, nunca como `wrong`
- `suite.yaml` como referência de schema para o Define

---

## Approaches Explored

### Approach A: Verbo de composição `eval`, no molde de `benchmark` ⭐ Recommended

**Description:** O extrator `sparkforge/collect/host_transcript.py` estende o leitor de `host_usage` e emite os facts `host.tool_call` (verbo canônico, ordem, bytes do resultado), `host.final_answer` e `host.usage`, com lacunas nomeadas. `sparkforge eval grade --suite <dir> --transcripts <dir>` compõe sobre esses facts e o `suite.yaml` e produz veredito por pergunta e `scorecard.json`. `sparkforge eval compare A/ B/` lê N scorecards por lado e emite a matriz de transição `k/N`.

**Pros:**
- Determinístico, com CI testando o grader por fixtures sintéticas
- Reusa padrões com teste: leitor de transcript com lacunas, compare com recusa nomeada
- O scorecard vira artefato versionável (só ids e números), e isso é o baseline que a regra 30 exige

**Cons:**
- O extrator novo mexe nas listas manuais de teste e na medida de snippet
- Verbo novo de CLI entra no surface lock se tocar skill ou knowledge. Tool MCP ficou fora justamente para conter isso

**Why Recommended:** A evidência é do codebase (confiança 0,80): `host_usage.py` já resolve a parte difícil (ler o JSONL do host sem estourar em forma inesperada), e `benchmark`/`funcval compare` já fixaram o contrato de "comparar dois lados medidos e recusar o incomparável". Nenhuma das outras abordagens chega nas quatro medidas sem juiz LLM ou script solto.

---

### Approach B: Estender `scripts/check_evals.py`

**Description:** O script do repo passa a ler o transcript e a comparar com `fase0.xml`. Não entra verbo nem tool.

**Pros:**
- Superfície zero, sem nenhum registro manual movido
- Entrega mais rápida

**Cons:**
- Não chega ao operador pela CLI nem pelo MCP. Não é produto
- O compare baseline/candidato vira lógica solta de script, sem golden test. É o mesmo defeito da receita de lotes em prosa, que deixou 90 testes sem execução sem que nada acusasse

---

### Approach C: Exportar para avaliador externo (AgentCore Evaluations, Langfuse)

**Description:** O transcript vira trace OTel e um backend externo pontua, possivelmente com LLM-as-judge.

**Pros:**
- Dashboards e histórico prontos

**Cons:**
- CI não determinístico, dependência de vendor, conta AWS exigida
- LLM-as-judge é evidência T5, que nunca confirma uma claim sozinha
- Capacidades do backend citadas no prompt sem fonte conferida

---

## Data Engineering Context (if applicable)

N/A. O harness não processa dado de pipeline: lê transcript de agente e ground truth versionado.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-10, nesta sessão de brainstorm |
| **Reasoning** | Determinístico, reusa o padrão existente de leitura de transcript e de compare com recusa, e produz o baseline que destrava a regra 30 sem violar a regra 23 |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | O SparkForge pontua arquivo e nunca executa agente | Regra 23: nada em `sparkforge/` chama provider nem dispara host | Runner dentro do pacote com gate de PR |
| 2 | Uma pergunta por sessão, um JSONL por pergunta | Sequência de tools atribuível sem ambiguidade, sem vazamento de contexto entre perguntas | Uma sessão para a suíte inteira |
| 3 | Ground truth em sidecar `suite.yaml`, com `fase0.xml` intocado | `check_evals.py` recomputa o XML. Abstention nova mora só no YAML | Estender o formato XML |
| 4 | Resposta final exige última linha `ANSWER: <valor>` ou `ANSWER: unresolved` | O grader não interpreta prosa. Sem a linha, o veredito é `answer_absent`, distinto de `wrong` | Extrair resposta de texto livre |
| 5 | Nenhuma nota composta. Uma coluna por medida | Peso é convenção, não medida (o mesmo problema dos pesos de `assess_claim`) | Score ponderado único |
| 6 | `order` é ordem parcial sobre a primeira ocorrência. Tool extra conta, mas não penaliza | Sequência exata puniria caminhos válidos | Sequência completa exata; penalidade por tool extra |
| 7 | Nome de tool normalizado para o verbo canônico (MCP e Bash `sparkforge <verb>`). O que não casa vira `other` | O mesmo verbo tem dois canais. Nome não reconhecido é contado, nunca adivinhado | Heurística sobre qualquer Bash |
| 8 | `tool_result_bytes` (visto no transcript) é separado de `payload_bytes` (span), e nenhum dos dois se soma com token | Regra 22: byte e token são unidades diferentes. Os dois bytes medem pontos diferentes | Um "custo" único |
| 9 | Transcript ilegível sai como lacuna nomeada e pergunta `ungraded` | Regra 27: medição que falha não pode virar nota ruim | Contar como `wrong` |
| 10 | Compare por `k/N` com classes `pass`/`fail`/`mixed` e matriz de transição. Sem veredito agregado, sem significância | Um run por lado não separa mudança de ruído em sistema não determinístico | p-value e intervalo de confiança; delta percentual como veredito |
| 11 | Compare recusa `suite_mismatch` (hash do `suite.yaml` difere) e avisa `single_sample` (N=1). Host ou modelo diferente é reportado, não recusado | Mudar o ground truth e comparar notas é o `different_input_volume` do eval. Trocar modelo costuma ser o objetivo da comparação | Recusar quando o N está abaixo de um limiar |
| 12 | Transcripts ficam fora do repo. Commita-se fixture sintética e scorecard (ids e números) | Caso real nunca entra em arquivo, e o repo é público | Commitar transcripts de sessões reais |
| 13 | A invariante de holdout passa a cobrir `evals/agentic/` | Exemplo resolvido nas instruções é resposta disponível, não capacidade demonstrada | Suíte agêntica fora da proteção de holdout |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Tool MCP `sparkforge_eval_*` | Quem pontua é o operador, sobre um arquivo. Agente pontuando a si mesmo não é caso de uso, e cortar evita mover `surface.lock` e os sete registros manuais | Yes |
| Gate de merge em PR (`QUALITY GATE`) | O runner não roda no CI. O CI testa o grader, não os agentes | Yes |
| Root-cause accuracy, debate resolution accuracy, unnecessary debate rate | Não há executor de debate: falta o lado a medir | Yes, depois do executor de debate |
| Perturbation robustness, stale-source error rate, routing accuracy, human intervention rate, regression introduction rate | Cada uma exige ground truth que ainda não existe | Yes |
| Latência por tarefa | O timestamp do transcript existe, mas nenhuma decisão do MVP depende dele | Yes |
| Custo em dólar | Regra 25: dólar exige `cost_basis` | Yes, com `cost_basis` nomeado |
| Formato de transcript do Devin | `host_usage` só confirmou o formato Claude Code | Yes |
| p-value e intervalo de confiança | Com N pequeno viraria número vestido de ciência | Yes, com N declarado e método nomeado |
| Backend AgentCore Evaluations / Langfuse | Abordagem C rejeitada. Capacidades sem fonte conferida | Yes, como exportador opcional |
| As outras ~29 frentes do prompt (Forge Pack, MCP v2, A2A, AgentRuntime, OTel GenAI, Scientific Debate, Debate ROI Gate, Execution Receipt, Change Proof, Realized Gain Ledger, Fleet, Control Plane, Knowledge Drift Radar, Model Router, Reputation, Tournament...) | Fora do recorte decidido na Q1. Várias dependem deste harness para afirmar ganho (regra 30), e várias exigem chamar provider (regra 23) | Yes, cada uma com brainstorm próprio |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura e fluxo (sidecar, runner, uma sessão por pergunta, `ANSWER:`, transcript fora do repo, holdout) | ✅ | Confirmado | No |
| Semântica do `eval grade` (vereditos, normalização de tool, ordem parcial, bytes ≠ tokens, `ungraded`) | ✅ | Confirmado | No |
| Semântica do `eval compare` (`k/N`, matriz de transição, `suite_mismatch`, `single_sample`) | ✅ | Confirmado | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O nível de agente das evals do SparkForge roda à mão e não deixa registro reprodutível. Por isso nenhuma mudança agêntica (runtime, debate, MCP v2, prompt de tool) consegue mostrar que não regrediu, e a regra 30 bloqueia qualquer afirmação de ganho.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Mantenedor do SparkForge | Muda descrição de tool, protocolo ou versão de MCP sem saber se os agentes passaram a errar, chamar tool errada ou afirmar onde deviam recusar |
| Operador que avalia modelo ou host | Hoje compara Haiku, Sonnet, Opus e Devin por tabela manual no README, sem transcript nem sequência de tools |
| Frentes futuras (executor de debate, AgentRuntime, MCP v2) | Não têm baseline contra o qual medir, e a regra 30 as bloqueia |

### Success Criteria (Draft)
- [ ] `sparkforge eval grade` produz `scorecard.json` idêntico ao esperado para cada uma das ~8 fixtures sintéticas (golden test nas duas direções)
- [ ] Toda lacuna do extrator aparece nomeada no scorecard, e nenhuma fixture de envelope quebrado produz `wrong`
- [ ] `evals/agentic/fase0/suite.yaml` cobre as 10 perguntas de `fase0.xml` com `required_tools`/`order` e acrescenta ≥ 3 perguntas de abstention ancoradas em `*.unresolved` do corpus
- [ ] `sparkforge eval compare` recusa com `suite_mismatch` quando o hash da suíte difere e marca `single_sample` quando N=1 em algum lado
- [ ] `scripts/run_agentic_eval.py` gera um JSONL por pergunta a partir de `claude -p`, e uma execução real registra o primeiro baseline em `evals/README.md` (scorecard commitado, transcript não)
- [ ] `tests/test_evals_holdout.py` passa a cobrir `evals/agentic/`
- [ ] `sparkforge/` continua sem importar `anthropic`, `openai`, `bedrock` ou `litellm`, e sem disparar processo de host

### Constraints Identified
- Regra 23: nada em `sparkforge/` chama provider nem executa host. O runner mora em `scripts/`
- Regras 22 e 24: byte e token em colunas separadas. Token só com transcript, e sem ele sai `tokens_unresolved`
- Regra 25: nenhum dólar sem `cost_basis`
- Regra 27: falha de medição não derruba a chamada nem vira nota
- Regra 30: o harness produz o baseline, mas ele mesmo não afirma ganho de nenhuma arquitetura
- Caso real nunca entra em arquivo: transcripts fora do repo, fixtures sintéticas
- Extrator novo: duas listas manuais de teste e medida de snippet. Número publicado em `docs/vnext/` ou `docs/harness/` passa por `scripts/check_vnext_claims.py`
- A suíte roda em lotes (`tests/test_suite_batches.py::LOTES`), e arquivo de teste novo precisa cair em exatamente um lote

### Out of Scope (Confirmed)
- Tool MCP de eval, gate de merge em PR, execução de agente no CI
- Métricas de debate, robustez, stale-source, routing, intervenção humana, latência, dólar
- Transcript do Devin, estatística inferencial, backend externo de avaliação
- Todas as demais frentes de `prompt_new_evo.md`

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 discovery + 1 YAGNI + 3 validações |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 10 linhas (incluindo as ~29 frentes fora do recorte) |
| Validations Completed | 3 |
| Duration | Uma sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_AGENTIC_EVAL_HARNESS.md`
