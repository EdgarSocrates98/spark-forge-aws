# DEFINE: Checkpoint/resume/event journal (§31 P0 item 7)

> O estado do case passa a sobreviver a uma queda no meio da escrita, e todo verbo que muda estado deixa no journal um `started` e um `finished` encadeados, de onde o `resume` tira o que estava em voo.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHECKPOINT_RESUME_JOURNAL |
| **Date** | 2026-09-15 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O estado do case (`case.yaml`, os JSONL do blackboard, `plan.json`/`decision.json`/`submissions.jsonl` do debate) é gravado sem proteção contra queda, e uma última linha cortada ou um YAML truncado torna o case ilegível; e nada registra qual verbo estava rodando quando a sessão caiu, então o `resume` depende de um `in_flight` em texto livre que só existe se alguém lembrou de escrevê-lo.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador que retoma o case | Abre o case noutra sessão ou máquina e lê `resume`/`handoff.md` | O "em voo" é o que alguém escreveu, não o que rodou; depois de uma queda, `load_case` ou o blackboard podem levantar erro |
| Host que executa os verbos (Devin, Claude Code, `scripts/run_debate.py`) | Morre no meio de um verbo (kill, OOM, fim de sessão) | Uma escrita interrompida deixa blackboard ou debate ilegível e trava a retomada |
| Revisor do case | Audita a sequência de mudanças | Não há como conferir que nenhuma mudança foi apagada ou editada depois |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `sparkforge/durable.py`: `write_atomic` (temporário no mesmo diretório, `fsync`, `os.replace`; falha deixa o original intacto), `append_line` (sob trava de arquivo; cauda sem `\n` vai para `<arquivo>.torn` e o arquivo volta ao último `\n` antes do append) e `read_jsonl` (tolera só a cauda cortada e a devolve como `torn_tail`; linha inválida no meio é erro com o número da linha) |
| **MUST** | Escrita e leitura durável em `case.yaml` (`save_case`), `plan.json` e `decision.json` do debate, os 10 JSONL do blackboard e `submissions.jsonl` |
| **MUST** | Journal commitável em `<raiz>/.sparkforge/journal.jsonl`: evento `started` (`seq`, `prev`, `call`, `verb`, `port`, `args`, `at`) e `finished` (`seq`, `prev`, `started_seq`, `outcome`, `outputs` ou `outputs_unresolved`) |
| **MUST** | Gancho nas duas portas: `tools.call_tool` (MCP) e `cli._dispatch` (CLI); o conjunto de verbos é `readOnlyHint: false` menos `code_*` (27), e um teste trava a igualdade; na CLI, verbo → tool pelo `parity.yaml` |
| **MUST** | Raiz do journal = `args["repo"]` quando existe (24 de 27), senão `raiz_do_projeto()` (3 de 27) |
| **MUST** | `args` só como sha256 do valor canônico; literal apenas para a lista fechada (`rules`, `debate_id`, `sandbox`, `fail_on`, `format`) e só com valor que não seja caminho absoluto |
| **MUST** | `at` = o `now` que o verbo recebeu (18 de 27), senão `null`; nada lido do relógio |
| **MUST** | Regra 27: falha do journal não derruba o verbo; o resultado ganha `journal: "unrecorded"` com o motivo |
| **MUST** | `resume` ganha o bloco `journal` (`last_seq`, `open_calls`, `chain`, `torn_tail`) e `in_flight_source` (`caller`, `journal`, `none`); o texto do chamador continua aceito e vence |
| **MUST** | `sparkforge journal verify --repo <raiz>` (só CLI): `intact`, `broken` (com o `seq` da quebra), `torn_tail`, `absent`; exit 1 em `broken` |
| **SHOULD** | `handoff.md`, seção "Em voo na interrupcao", lista os `open_calls` com "sem finished (caiu ou ainda roda)" |
| **SHOULD** | Chamada recusada pela policy não grava evento (não executou) |
| **COULD** | Manual `docs/guia/usos/` do case ganha a seção do journal e do `verify` |

---

## Success Criteria

- [ ] 27 de 27 verbos que mudam estado gravam `started` e `finished` pela porta MCP, e 27 de 27 pela CLI; o conjunto é igual ao das anotações (teste)
- [ ] O mesmo verbo pelas duas portas grava `tool`, `outcome` e `outputs` iguais; `args` (e `call`) seguem o nome de argumento de cada porta (revisto no design: os nomes divergem em 27 de 27)
- [ ] 6 cenários sintéticos em `fixtures/journal/` (`sem_queda`, `started_sem_finished`, `cauda_cortada` em journal, blackboard e `submissions.jsonl`, `linha_removida`, `linha_alterada`, `case_yaml_intacto_apos_falha`) com saída esperada
- [ ] `journal verify` acerta 3 de 3: `intact` sem queda, `broken` com o `seq` certo para linha removida e para linha alterada
- [ ] Com `os.replace` sabotado, 2 de 2 arquivos (`case.yaml`, `plan.json`) continuam byte a byte iguais ao anterior
- [ ] 0 valor de argumento fora da lista fechada aparece literal no journal (varredura sobre os eventos dos 27 verbos)
- [ ] Os 13 goldens de `fixtures/debate/` passam sem regravação, e o `brief.json` de `retomada` fica igual byte a byte; o golden `fixtures/receipt/uniao_debate` também
- [ ] 0 `journal.jsonl` novo na árvore depois da suíte (`git status` limpo fora do que o build commitar)
- [ ] Tools continuam 103; suíte em 9 lotes com 0 falha; gates de lastro, números e superfície sem divergência; CI verde em `test (3.10)`

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Par pela CLI | Case sintético em `tmp` | `sparkforge case open` pela CLI | `journal.jsonl` com `started` (`seq` 1, `prev` nulo, `port: cli`, `at` = o `--now`) e `finished` (`seq` 2, `started_seq` 1, `outcome: ok`, `outputs` com o sha256 de `case.yaml`) |
| AT-002 | Par pelo MCP | O mesmo case | `call_tool("sparkforge_case_update", ...)` | Evento `started`/`finished` com `port: mcp`, `prev` = sha256 da linha anterior |
| AT-003 | Verbo de leitura | Case com journal | `sparkforge_resume`, `sparkforge_judge` | Nenhum evento novo |
| AT-004 | Conjunto travado | `TOOLS` | Teste de conjunto | Journalizados = `readOnlyHint: false` menos `code_*`; tool nova que grava sem entrar derruba o teste |
| AT-005 | Em voo | `fixtures/journal/started_sem_finished` (scan sem `finished`) | `resume` sem `in_flight` | `in_flight_source: journal`, `journal.open_calls` com o `seq`, o verbo e a porta; `handoff.md` diz "caiu ou ainda roda" |
| AT-006 | Texto do chamador vence | O mesmo fixture | `resume --in-flight "rodando scan"` | `in_flight` = o texto, `in_flight_source: caller`, `open_calls` continua no bloco |
| AT-007 | Cadeia íntegra | `fixtures/journal/sem_queda` | `journal verify` | `intact`, exit 0 |
| AT-008 | Linha removida | `fixtures/journal/linha_removida` | `journal verify` | `broken` com o `seq` do salto, exit 1 |
| AT-009 | Linha alterada | `fixtures/journal/linha_alterada` | `journal verify` | `broken` com o `seq` cujo `prev` não confere, exit 1 |
| AT-010 | Cauda cortada | `cauda_cortada` (journal, `claims.jsonl`, `submissions.jsonl`) | Ler, depois anexar | Leitura sem erro com `torn_tail`; append grava linha válida; os bytes cortados ficam em `<arquivo>.torn`; `debate next` devolve o brief |
| AT-011 | Linha ruim no meio | JSONL com linha inválida no meio | `read_jsonl` | Erro com o número da linha (não tolera) |
| AT-012 | Escrita atômica | `case.yaml` e `plan.json` existentes | `os.replace` sabotado para levantar | Os dois arquivos iguais byte a byte ao anterior; nenhum temporário sobrando |
| AT-013 | Journal indisponível | `.sparkforge/journal.jsonl` como diretório | Verbo de escrita | Verbo conclui; resultado com `journal: "unrecorded"` e motivo |
| AT-014 | Sem valor literal | Eventos dos 27 verbos com argumentos sintéticos de caminho absoluto, ARN e nome de job | Varredura | Nenhum desses valores aparece no journal |
| AT-015 | Recusa da policy | Policy que recusa a tool | `call_tool` | Nenhum evento gravado |
| AT-016 | Goldens intactos | `fixtures/debate/*`, `fixtures/receipt/uniao_debate` | Suíte | Passam sem regravação |

---

## Out of Scope

- AgentRuntime concreto e checkpoint do host (regra 23; `RuntimeCapabilities.checkpointing` é do host)
- Retomada de `scan`/`collect` do meio, por arquivo
- Ledger de spans gravando a cada chamada
- Tool MCP `sparkforge_journal_verify`; verbos `journal list/show`
- Rotação ou compactação do journal
- Chave ou assinatura na cadeia
- Escrita atômica em arquivos regeneráveis (resultado do `scan`, manifesto do `collect`, `report.json` do sandbox)
- Eventos do journal dentro do `traces.jsonl` do blackboard

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 27: registro nunca derruba a chamada | Falha do journal vira `journal: "unrecorded"` |
| Technical | Timestamp nunca gerado no pacote (`case/store.py`); id content-addressed sem hora | `at` só do `now` do verbo; ordem por `seq` e `prev` |
| Technical | Repositório público; "caso real nunca entra em arquivo" | Argumento só como hash, lista fechada de literais |
| Technical | CI em Windows e Linux | Trava com `msvcrt.locking` e `fcntl.flock`; Python 3.10 (`datetime.UTC` proibido) |
| Technical | `sparkforge_resume` está no golden de paridade MCP 1.29 (`fixtures/mcp_parity/tools_list_*.json`) | Campo novo no `outputSchema` vai para a exceção declarada |
| Technical | A CLI não passa por `call_tool` | Dois ganchos; mapa verbo → tool pelo `parity.yaml` |
| Technical | 24 arquivos rastreados em `fixtures/**/.sparkforge/` | Nenhum teste pode rodar verbo de escrita sobre a pasta da fixture sem copiar |
| Resource | A suíte inteira não cabe num processo | 9 lotes, um por vez |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/durable.py` (novo), `sparkforge/journal/` (novo), `sparkforge/case/{store,resume}.py`, `sparkforge/agentic/blackboard.py`, `sparkforge/agentic/executor/debate_run.py`, `sparkforge/adapters/{tools,cli,_core}.py` | Um módulo de escrita durável usado pelos donos de estado; journal com gancho nas duas portas |
| **KB Domains** | `genai` (`concepts/state-machines`, `patterns/agentic-workflow`) só como contexto; padrões do repositório: `receipt/` (content-addressed, sem chave), `debate_run` (estado só em arquivo), `policy/` (classe pela anotação, `raiz_do_projeto`) | Nenhum domínio do agentspec cobre journal ou escrita atômica |
| **IaC Impact** | None | |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O `receipt` não enumera `journal.jsonl` nem `*.torn` | O golden `uniao_debate` mudaria | [x] `receipt/build.py:144-189` só lista nomes de `_ENTITY_FILES` e `DEBATE_FILES` |
| A-002 | `tools.call_tool` é o despacho único do MCP | Chamada MCP fora do journal | [x] `tools.py:10252`, docstring: "`adapters/mcp.py` e qualquer outro chamador entram por aqui" |
| A-003 | Todo verbo de escrita tem o subcomando de CLI declarado no `parity.yaml` | Porta CLI sem mapa para parte dos 27 | [x] 27 de 27 no `parity.yaml`; o mapa é por capacidade, então o design usa a convenção `sparkforge_<comando>_<sub>`, que acerta 27 de 27 |
| A-004 | Nenhum teste roda verbo de escrita com `repo` na raiz do projeto ou na pasta de fixture sem copiar | Journal novo sujaria a árvore durante a suíte | [x] CAIU para os 3 sem `repo` (`report sign` roda com cwd na raiz em `test_adapters_report_signature.py:430`); design: raiz pelo ancestral com `case.yaml`, senão `sem_raiz_de_case`, e backstop no `conftest.py` |
| A-005 | `msvcrt.locking` e `fcntl.flock` funcionam nos jobs de CI (Windows e Linux) | Trava inoperante; `prev` disputado | [ ] stdlib nos dois sistemas; provado pelo teste de trava no CI |
| A-006 | `os.replace` no mesmo diretório troca o arquivo sem estado intermediário legível | Arquivo parcial visível | [x] atômico no POSIX pela doc do Python; no Windows o destino é o antigo ou o novo, e `PermissionError` com leitor aberto vira retry limitado (Decision 1 do design) |
| A-007 | `sparkforge_resume` está no golden MCP 1.29 | Exceção de paridade desnecessária | [x] 1 ocorrência em `tools_list_stdio.json` |
| A-008 | 18 dos 27 verbos recebem `now` | `at` quase sempre nulo | [x] medido nas `inputSchema` |
| A-009 | Gravar conteúdo igual por `write_atomic` não muda os goldens de debate | Regravação de 13 goldens | [ ] conferido pela suíte no build |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Dois defeitos medidos: escrita sem proteção e `in_flight` sem fonte |
| Users | 3 | Operador, host e revisor, cada um com a dor |
| Goals | 3 | MoSCoW com dez MUST |
| Success | 3 | Contagens, cenários e byte a byte |
| Scope | 2 | A-003 a A-006 abertos para o design |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-003 a A-006 são conferências de design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-15 | define-agent | Initial version, a partir de BRAINSTORM_CHECKPOINT_RESUME_JOURNAL.md; `finished` passa a carregar `started_seq` (duas chamadas iguais e concorrentes teriam o mesmo `call`) |
| 1.1 | 2026-09-15 | design-agent | SC2 revisto (argumentos seguem o nome de cada porta); A-003, A-004 e A-006 fechadas no design |
| 1.2 | 2026-09-15 | ship-agent | Shipped and archived (PR #71) |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_CHECKPOINT_RESUME_JOURNAL.md`
