# BRAINSTORM: Checkpoint/resume/event journal (§31 P0 item 7)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHECKPOINT_RESUME_JOURNAL |
| **Date** | 2026-09-15 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** §31 P0 item 7 de `prompt_new_evo.md`, "Checkpoint/resume/event journal". No prompt o item mora dentro do AgentRuntime (`resume`, `checkpoint`), e o runtime concreto fica fora do pacote pela regra 23. Segunda e última das duas frentes SDD que o operador escolheu para fechar o documento (a primeira, §11 Debate ROI Gate, foi mergeada no PR #70).

**Context Gathered:**
- `case/store.py::save_case` grava `case.yaml` com `write_text` direto: queda no meio deixa YAML truncado, e `load_case` levanta `CaseError` ("YAML inválido"). O case não guarda histórico de transição.
- `case/resume.py::resume` monta o payload de rehidratação a partir do case e dos findings; `in_flight` é texto livre passado pelo chamador (`--in-flight`, argumento da tool). Nada registra o que estava rodando.
- O blackboard (`agentic/blackboard.py`) tem 10 JSONL append-only; `_read_jsonl` faz `json.loads` por linha, então uma última linha cortada torna o blackboard inteiro ilegível.
- O debate (`agentic/executor/debate_run.py`) já guarda estado só em arquivo (golden `fixtures/debate/retomada`), mas `_escreve_json` grava `plan.json`/`decision.json` com `write_text`, e `_anexa_jsonl`/`_le_jsonl` têm o mesmo defeito de linha cortada.
- O ledger de spans (`observability/context_ledger.py`) acumula em buffer e só grava no `atexit`; `flush(final=False)` existe e nada o chama. Kill ou OOM perde os spans do run.
- `scan` roda um analyze por arquivo, tudo em memória, e grava no fim.
- `agentic/runtime.py::RuntimeCapabilities.checkpointing` é propriedade declarada do HOST (Devin `True`, Claude Code `False`), não do pacote.
- 103 tools, 36 com `readOnlyHint: false`; 9 delas são `code_*` (índice de code intelligence, cache reconstruível). Sobram 27 verbos que mudam estado do case ou do repositório. 24 dos 27 recebem `repo`; `funcval_plan`, `funcval_compare` e `report_sign` não.
- A CLI não passa por `tools.call_tool` (0 ocorrência em `cli.py`); tem despacho central em `cli.py::_dispatch`.
- `.gitignore`: política de `.sparkforge/` é "derivado pequeno pode ser commitado"; `case.yaml`, `handoff.md` e blackboard viajam no commit; `traces.db`, `cache/`, `local/`, `sandbox/`, `proposal/` são ignorados.
- `facts/secrets.py::redact` existe e é heurístico (nome de chave, entropia).
- `policy/load.py::raiz_do_projeto()` resolve a raiz por `CLAUDE_PROJECT_DIR` ou cwd.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/durable.py` (novo), `sparkforge/journal/` (novo), `case/{store,resume}.py`, `agentic/blackboard.py`, `agentic/executor/debate_run.py`, `adapters/{tools,cli,_core}.py` | Um módulo de escrita durável usado pelos donos de estado; journal com gancho nas duas portas |
| Relevant KB Domains | `genai` (`concepts/state-machines`, `patterns/agentic-workflow`) só como contexto; nenhum domínio do agentspec cobre journal ou escrita atômica | Padrões vêm do repositório: `receipt` (content-addressed, sem chave), `debate_run` (estado só em arquivo), policy (classe derivada da anotação) |
| IaC Patterns | N/A | Nada de infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual problema a frente resolve primeiro: journal, retomada de verbo longo, escrita à prova de queda, ou combinação? | (c) escrita à prova de queda + (a) journal de eventos | Defeito medido (linha cortada trava blackboard e debate) mais a fonte que o `resume` não tem; retomada de `scan`/`collect` fica fora |
| 2 | Quais verbos entram no journal? | Os 27 que mudam estado (sem `code_*` e sem os de leitura) | Journal registra mudança de estado; leitura já tem span no ledger (regra 22 limpa) |
| 3 | Forma do evento e ordem sem relógio? | Par `started`/`finished`, `seq`, cadeia por `prev`, trava de arquivo, hora só com `now` do verbo | `started` sem `finished` substitui o texto livre do `in_flight`; a cadeia deixa conferível que ninguém apagou evento |
| 4 | O journal viaja no commit, e o que dos argumentos entra? | Commitável; argumento como sha256 do valor canônico, literal só para lista fechada e valor não absoluto | O barramento do case é o commit; sha256 prova entrada igual sem expor valor; redator heurístico não é a única barreira em repo público |
| 5 | Que dado prova a frente? | Só sintético (`fixtures/journal/`, queda simulada pelo estado do arquivo) + teste de unidade com `os.replace` sabotado | Atomicidade provada sem matar processo; nada de caso real no repo |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/journal/` (novo) | ~6 | `sem_queda`, `started_sem_finished`, `cauda_cortada` (journal, blackboard, `submissions.jsonl`), `linha_removida`, `linha_alterada`, `case_yaml_intacto_apos_falha` |
| Output examples | `fixtures/debate/retomada/expected/brief.json` | 1 | Deve continuar igual byte a byte: escrita atômica não muda conteúdo |
| Ground truth | `fixtures/receipt/uniao_debate/expected/receipt.json` | 1 | Conferir se o recibo enumera arquivos de `.sparkforge/`; se sim, o journal o move |
| Related code | `tests/test_case_resume.py`, `tests/test_case_store.py`, `receipt/`, `debate_run.py`, `policy/load.py` | 5 | Moldes de payload de resume, cadeia content-addressed, estado em arquivo, raiz do projeto |

**How samples will be used:**

- Golden por cenário de queda, gravando o arquivo no estado exato em que ficaria depois de uma queda.
- Teste de unidade que troca `os.replace` para levantar exceção e confere o arquivo antigo íntegro.
- Goldens atuais de debate e resume como prova de que o conteúdo gravado não mudou.

---

## Approaches Explored

### Approach A: gancho nas duas portas, conjunto derivado das anotações ⭐ Recommended

**Description:** `sparkforge/durable.py` concentra `write_atomic` (temporário no mesmo diretório, `fsync`, `os.replace`), `append_line` (sob trava, com quarentena da cauda cortada) e `read_jsonl` (tolera só a cauda). `sparkforge/journal/` guarda `.sparkforge/journal.jsonl` e um context manager `recording(verbo, porta, args, raiz)` chamado em `tools.call_tool` (MCP) e em `cli._dispatch` (CLI). O conjunto de verbos sai das anotações (`readOnlyHint: false`, menos `code_*`), travado por teste. `resume` lê o journal; verbo `journal verify` confere a cadeia.

**Pros:**
- Dois pontos de gancho em vez de 27.
- A anotação já é a fonte da classe de autorização (§16): journal e policy não divergem, e tool nova que grava entra sem ninguém lembrar.

**Cons:**
- A CLI precisa de mapa de subcomando para nome de tool.
- A raiz do journal depende do argumento de cada verbo.

**Why Recommended:** caminho único para uma pergunta só, o mesmo princípio de `_arbitra_pares`/`open_debate_plans`; derivar da anotação já tem precedente na policy (confiança 0,80: padrão do código, sem domínio de KB).

---

### Approach B: chamada explícita nos 27 verbos de `_core`

**Description:** cada função chama `journal.recording(...)` com a própria raiz.

**Pros:**
- Raiz sempre certa, sem mapa de CLI.

**Cons:**
- 27 pontos de chamada; verbo novo que esquece fica fora em silêncio, e o teste que pega isso teria de ler o AST de `_core`.

---

### Approach C: "onde parou" derivado do que já existe

**Description:** `resume` lê mtime, manifesto do collect, `summary.json` do scan e `traces.jsonl` do blackboard.

**Pros:**
- Nenhum arquivo novo.

**Cons:**
- Sem `started`, queda no meio não deixa rastro; sem cadeia, nada a verificar. Não resolve o problema escolhido.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-15 |
| **Reasoning** | Dois ganchos, conjunto derivado da mesma anotação que a policy lê, e o `resume` passa a ter fonte para "em voo" |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Escopo = escrita à prova de queda + journal de eventos | Linha cortada trava blackboard e debate hoje; `in_flight` não tem fonte | Retomada de `scan`/`collect` por arquivo |
| 2 | Journal cobre os 27 verbos que mudam estado, conjunto derivado de `readOnlyHint: false` menos `code_*`, travado por teste | Registro de mudança de estado; leitura já tem ledger | Todo verbo (segundo ledger); só o barramento do case (perde `scan`, `change`, `collect`) |
| 3 | Evento = par `started`/`finished` com `seq`, `prev` (sha256 da linha anterior), `call` (sha256 de verbo+args canônicos), `verb`, `port`, `args`, `at`; `finished` com `outcome` e `outputs` | `started` sem `finished` é o dado de "em voo"; a cadeia prova ordem e ausência de remoção | Evento só no fim; par sem cadeia |
| 4 | Sem relógio: `at` é o `now` que o verbo recebeu, senão `null` | Timestamp nunca é gerado no pacote (`case/store.py`); id content-addressed não leva hora | Ler o relógio no gancho |
| 5 | Journal commitável em `<raiz>/.sparkforge/journal.jsonl`; raiz = `args["repo"]` (24 de 27), senão `raiz_do_projeto()` (3 de 27) | O case atravessa sessão pelo commit | Journal local ignorado pelo git |
| 6 | Argumento vira sha256 do valor canônico; literal só para lista fechada (`rules`, `debate_id`, `sandbox`, `fail_on`, `format`) e valor não absoluto | Repo público; "caso real nunca entra em arquivo"; `redact` é heurístico | Literal com `redact()` |
| 7 | `outputs` = sha256 dos arquivos que o verbo declara ter gravado; sem declaração sai `outputs_unresolved` | Recusa tem nome (regra 20); não inventar lista | Varrer `.sparkforge/` por mtime |
| 8 | Gravação sob trava de arquivo (`msvcrt.locking` no Windows, `fcntl.flock` no POSIX) | CLI e servidor MCP podem gravar ao mesmo tempo e disputariam o `prev`; append no Windows não é atômico por linha | Confiar em `O_APPEND` |
| 9 | Regra 27: falha do journal não derruba o verbo; resultado ganha `journal: "unrecorded"` com motivo | Medição/registro nunca quebra o produto | Falhar o verbo |
| 10 | `append_line` com cauda cortada move os bytes para `<arquivo>.torn` e volta o arquivo ao último `\n` antes de anexar | Sem isso, o append seguinte transforma a cauda em linha corrompida no meio; a quarentena preserva a evidência | Apagar a cauda; anexar por cima |
| 11 | `read_jsonl` tolera só a cauda e a devolve como `torn_tail`; linha inválida no meio é erro com número da linha | Queda corta a cauda; linha ruim no meio é outro defeito e não pode passar calada | Ignorar toda linha inválida |
| 12 | Escrita atômica vale para o que é lido como estado: `case.yaml`, `plan.json`, `decision.json`, JSONL do blackboard, `submissions.jsonl`, journal | O resto se regenera rodando o verbo de novo | Todo arquivo que o pacote grava |
| 13 | `resume` ganha bloco `journal` (`last_seq`, `open_calls`, `chain`, `torn_tail`) e `in_flight_source` (`caller`/`journal`/`none`); texto do chamador continua aceito | O dado substitui o texto livre sem quebrar quem já passa texto | Remover `--in-flight` |
| 14 | `open_calls` = "sem finished", nunca "caiu"; o `handoff.md` diz "caiu ou ainda roda" | Outro processo ainda rodando tem a mesma cara | Afirmar queda |
| 15 | Verbo `journal verify` só na CLI: `intact`, `broken` (com o `seq` da quebra), `torn_tail`, `absent`; exit 1 em `broken` | Auditoria, no molde de `receipt verify` | Tool MCP (tools continuam 103) |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Ledger gravando span por chamada | O ledger mede, não guarda estado; perder spans na queda não corrompe o case; custo de uma escrita SQLite por chamada não medido | Yes |
| Retomada de `scan`/`collect` por arquivo | Fora do escopo escolhido; nenhum scan lento medido | Yes |
| Tool MCP `sparkforge_journal_verify` | O `resume` já leva o "em voo" pela tool existente; verificar a cadeia é auditoria | Yes |
| Verbo `journal list/show` | O `resume` faz a leitura útil; o JSONL se lê direto | Yes |
| Rotação ou compactação do journal | Sem medida de tamanho; compactar quebraria a cadeia | Yes |
| Escrita atômica no resultado do `scan`, no manifesto do `collect` e no `report.json` do sandbox | Arquivos regeneráveis rodando o verbo de novo | Yes |
| Chave ou assinatura na cadeia | O `receipt` também é sem chave; a cadeia prova ordem e ausência de remoção, não autoria | Yes |
| Eventos do journal dentro do `traces.jsonl` do blackboard | Moveria o golden `fixtures/receipt/uniao_debate`; journal e blackboard respondem perguntas diferentes | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura, gancho nas duas portas, forma do evento | ✅ | "certo, segue" | No |
| Escrita durável, leitura tolerante, `resume`, `journal verify`, testes e riscos | ✅ | "certo, escreve o brainstorm" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O estado do case (`case.yaml`, blackboard, debate) é gravado sem proteção contra queda, e uma linha cortada ou um YAML truncado trava o case inteiro; e nada registra qual verbo estava rodando quando a sessão caiu, então o `resume` depende de texto livre para dizer onde a investigação parou.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador que retoma o case noutra sessão ou máquina | O "em voo" é o que alguém lembrou de escrever, não o que rodou |
| Host (Devin, Claude Code) que morre no meio de um verbo | Uma escrita interrompida deixa blackboard ou debate ilegível |
| Revisor do case | Não há como conferir que a sequência de mudanças não foi editada |

### Success Criteria (Draft)
- [ ] Os 27 verbos que mudam estado gravam `started` e `finished` pelas duas portas; o conjunto é igual ao das anotações (teste).
- [ ] `resume` sem `in_flight` do chamador devolve o `started` sem `finished` do journal, com `in_flight_source: journal`.
- [ ] `journal verify` devolve `broken` com o `seq` certo para linha removida e para linha alterada, e `intact` para o journal sem queda.
- [ ] Cauda cortada no journal, no blackboard e em `submissions.jsonl` é lida sem erro e reportada como `torn_tail`; o append seguinte grava linha válida e a cauda vai para `.torn`.
- [ ] Com `os.replace` falhando, `case.yaml` e `plan.json` antigos continuam íntegros byte a byte.
- [ ] Journal indisponível não derruba o verbo (`journal: "unrecorded"`).
- [ ] Nenhum valor de argumento fora da lista fechada aparece literal no journal (teste por varredura).
- [ ] Goldens de debate (`retomada` inclusive) sem regravação; tools continuam 103; suíte em 9 lotes com 0 falha; gates de lastro, números e superfície sem divergência.

### Constraints Identified
- Regra 27: registro nunca derruba a chamada.
- Timestamp nunca gerado no pacote; id content-addressed sem hora.
- Repositório público: journal commitável só com hash e lista fechada de literais.
- Windows e POSIX: trava de arquivo nos dois.
- `sparkforge_resume` está no golden de paridade MCP 1.29: campo novo vai para a exceção declarada.
- `receipt emit` também grava no journal: conferir se o recibo enumera arquivos de `.sparkforge/` (golden `uniao_debate`).
- Python 3.10 no CI (`datetime.UTC` proibido).

### Out of Scope (Confirmed)
- AgentRuntime concreto e checkpoint do host (regra 23).
- Retomada de `scan`/`collect` por arquivo.
- Ledger gravando por chamada.
- Tool MCP de verify, verbo de listagem, rotação, assinatura da cadeia.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_CHECKPOINT_RESUME_JOURNAL.md`
