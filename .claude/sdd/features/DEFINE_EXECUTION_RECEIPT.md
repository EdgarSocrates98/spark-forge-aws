# DEFINE: Execution Receipt

> Um recibo content-addressed de uma execucao do case. Ele amarra, por caminho e sha256 e sem copiar conteudo, o `case.yaml`, a uniao dos arquivos de facts, os findings, o report assinado, o blackboard, os ADRs, os debates e os spans de um `--run-id` declarado, mais o host e o modelo que o host declarou. Um `receipt verify` recalcula cada parte a partir do disco e diz qual divergiu. Sem chave: o recibo prova correspondencia, nunca autoria.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXECUTION_RECEIPT |
| **Date** | 2026-09-12 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Depois de uma sessao, o SparkForge deixa os artefatos de uma execucao espalhados em ate sete lugares: `case.yaml`, arquivos de facts, findings, report, `.sparkforge/blackboard/`, `.sparkforge/adr/` e `.sparkforge/debate/`. Os spans ficam num `traces.db` que nao vai para o git e nao carrega `case_id`. Nenhum artefato diz, de forma conferivel, quais desses pertencem a mesma execucao, com qual catalogo ela julgou, que tools chamou, que modelo o host declarou e que nada foi aplicado. O `report sign` prova a correspondencia do relatorio, nao a da execucao.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Revisor corporativo ou auditor | Recebe uma recomendacao e precisa aceita-la ou recusa-la | Nao consegue saber em que evidencia, com qual catalogo e com qual modelo declarado ela nasceu, nem se algum artefato mudou depois |
| Operador que herda o case | Retoma a investigacao de outra pessoa ou maquina | Nao tem como conferir que os arquivos recebidos sao os da execucao original |
| Agente que fecha a sessao (`sf-synthesizer`) | Ultimo passo do fluxo, depois de `report_sign` e `telemetry_export` | Nao tem onde registrar o fechamento da execucao inteira |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: modulo puro `sparkforge/receipt/` com `build` (monta o recibo a partir de caminhos e de um `now` injetado) e `verify` (recalcula e diagnostica), sem I/O de rede e sem importar provider |
| **MUST** | G2: `receipt_id` = `rcpt_` + sha256 do JSON canonico do recibo sem o proprio campo; o JSON canonico reutiliza um helper que ja existe no pacote, sem criar um setimo |
| **MUST** | G3: parte `case` com caminho, sha256 e `case_id` de `.sparkforge/case.yaml`; parte `evidence` com caminho, sha256 e `fact_count` de cada arquivo de `--facts` (repetivel, a uniao) e `fact_ids_sha256`; parte `judgment` com caminho e sha256 dos findings, `rule_ids`, `fact_ids`, `catalog_version` e `schema_version` (lidos pelo mesmo `_signature_parts` do `report sign`) e, com `--report`, caminho e `signature` do report |
| **MUST** | G4: sha256 de artefato de texto com CRLF normalizado para LF; a regra de normalizacao entra no hash via `receipt_version` |
| **MUST** | G5: parte `tools` com `run_id` e, por span do run, `name`, `status`, `outcome`, `payload_bytes`, `detail_level`, `start` e `end`, mais `spans_sha256`; `metadata_json` nunca entra; o span do proprio emit fica fora e aparece em `tools.excluded`; sem `--run-id`, ou com o `traces.db` indisponivel, a parte sai `unresolved` com a razao e o emit nao falha (regra 27) |
| **MUST** | G6: nenhum conteudo de caso no recibo: so caminho, hash, id, contagem, versao e as colunas escolhidas do span; nenhum valor de `measures` |
| **MUST** | G7: `refused` sempre com `authorship` (`content_addressed_sem_chave`) e `tool_io` (`span_sem_hash_de_io`), e `proves` com "correspondencia entre este recibo e estes artefatos -- nunca autoria" |
| **MUST** | G8: `receipt verify` na ordem fixa `version, integrity, case, evidence, judgment, decision, proof, tools, host`; cada item sai `match`, `diverged` ou `missing`; `integrity` recalcula o `receipt_id`; `valid` = integrity ok e nenhuma parte `diverged` ou `missing`; codigo 1 quando invalido e 2 em erro de uso (arquivo ilegivel, JSON invalido) |
| **MUST** | G9: `tools` no verify: com o run presente no `traces.db`, recalcula `spans_sha256`; com o banco ausente ou sem o run, sai `not_rechecked` com a razao, listado, sem derrubar `valid` |
| **MUST** | G10: `receipt_version` diferente da build: as partes que dependem de normalizacao saem `not_evaluable`, fora de `diverged` |
| **MUST** | G11: `emitted_at` vem de `--now` (obrigatorio) e entra no hash; mesma entrada e mesmo `--now` dao o mesmo `receipt_id` e o mesmo arquivo byte a byte |
| **MUST** | G12: CLI `sparkforge receipt emit` e `sparkforge receipt verify`; tools `sparkforge_receipt_emit` (LOCAL_MUTATION, grava so em `.sparkforge/receipts/<receipt_id>.json`, caminhos de entrada confinados ao repo) e `sparkforge_receipt_verify` (READ_ONLY) |
| **SHOULD** | G13: parte `host`: com `--host-transcript`, `transcript_sha256`, `agent` e `model` lidos pelos facts `host.*` de `extract_host_transcript_path`; `provider` so de `--provider`; sem transcript, `host.model` e `host.agent` saem `unresolved` (`transcript_ausente`); sem provider, `host.provider` sai `unresolved` (`provider_nao_declarado`); mais de um modelo sai `modelos_multiplos` |
| **SHOULD** | G14: parte `decision`: por arquivo de `.sparkforge/blackboard/*.jsonl` presente, caminho, sha256 e contagem; `decision_ids`; por ADR em `.sparkforge/blackboard/adr/`, caminho, sha256 e `rollback_present`; por debate em `.sparkforge/debate/<id>/`, id e sha256 do estado; sem nenhum deles, `unresolved` (`sem_arbitragem`) |
| **SHOULD** | G15: parte `proof`: fact_ids `funcval.*` em `tests` e fact_ids de benchmark em `before_after`, so os presentes na uniao; nenhuma comparacao e nenhum ganho; sem nenhum, `unresolved` (`sem_prova_funcional`, `sem_benchmark`); no verify, fact_id citado que nao esta na uniao declarada faz a parte divergir |
| **SHOULD** | G16: parte `actions` fixa: `autonomy: L0`, `applied_changes: false`, `items: []` |
| **SHOULD** | G17: `sf-synthesizer` ganha o passo de emitir o recibo depois de `report_sign` e `telemetry_export`, com o `run_id` do processo; `parity.yaml` ganha a capacidade "prove what an execution used and decided" |
| **COULD** | G18: `docs/execution-receipt.md` com o schema, o que o recibo prova e o que ele recusa, e como assinar o arquivo fora do pacote (`cosign attest-blob`) para quem precisa de autoria |

---

## Success Criteria

- [ ] SC1: golden `fixtures/receipt/expected/receipt.json` sobre a uniao `fixtures/graph/import_sem_jar_no_iac` + `fixtures/infra_code/fgac_com_jar_extra` bate byte a byte com `--now` fixo; duas emissoes seguidas dao o mesmo `receipt_id`.
- [ ] SC2: adulteracao de cada uma das 6 partes com artefato (`case`, `evidence`, `judgment`, `decision`, `proof`, `host`) faz o verify devolver `diverged` contendo exatamente aquela parte, e nenhuma outra.
- [ ] SC3: apagar um artefato declarado faz a parte sair `missing` e `valid: false`; editar um byte do recibo da `integrity` divergente; `receipt_version` alterado da `not_evaluable`.
- [ ] SC4: sem `traces.db`, ou com o run ausente, o verify devolve `tools: not_rechecked` e `valid: true` quando o resto confere; com o run presente e um span alterado, `tools` diverge.
- [ ] SC5: varredura V2 sobre o golden: 0 ocorrencias de valores de `measures` dos 60 facts da uniao, e 0 de `metadata_json`.
- [ ] SC6: sem `--host-transcript` e sem `--provider`, `unresolved` contem `host.model`, `host.agent` e `host.provider` com as razoes nomeadas; sem `--run-id`, contem `tools`.
- [ ] SC7: o mesmo artefato com LF e com CRLF da o mesmo sha256.
- [ ] SC8: o span do proprio `receipt_emit` nao aparece em `tools.spans` e aparece em `tools.excluded`.
- [ ] SC9: as 2 tools novas validam contra o proprio `outputSchema` com amostra real; os 7 registros de tool nova atualizados; `check_surface_lock --update` com o crescimento em bytes declarado no commit; claims de `len(TOOLS)` remediadas pela lista de ids da saida do gate.
- [ ] SC10: gates (`check_vnext_claims`, `check_status_numbers --strict`, `check_surface_lock`, `check_evals`, `ruff`) e suite por lotes com 0 falhas; o golden de paridade MCP so aceita as 2 tools como adicao.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Emissao completa | Case sintetico com a uniao, findings, report assinado, blackboard e ADR do `arbitrate`, `traces.db` com um run e transcript sintetico | `receipt emit` com `--now` fixo | Arquivo em `.sparkforge/receipts/rcpt_<sha>.json` igual ao golden; `unresolved` so com o que nao foi fornecido |
| AT-002 | Deterministico | A mesma entrada | Duas emissoes com o mesmo `--now` | Mesmo `receipt_id`, arquivo byte a byte |
| AT-003 | Verify limpo | Recibo do AT-001, nada alterado | `receipt verify` | `valid: true`, `diverged: []`, exit 0 |
| AT-004 | Facts adulterado | Um byte trocado num arquivo de facts | `receipt verify` | `diverged: ["evidence"]`, exit 1 |
| AT-005 | Findings adulterado | Um finding a mais | `receipt verify` | `diverged: ["judgment"]` |
| AT-006 | Artefato apagado | ADR removido | `receipt verify` | `decision` com o item `missing`, `valid: false` |
| AT-007 | Recibo editado | Um campo do recibo alterado a mao | `receipt verify` | `integrity` divergente, exit 1 |
| AT-008 | Outra maquina | Recibo e artefatos copiados, sem `traces.db` | `receipt verify` | `tools: not_rechecked` com a razao, `valid: true` |
| AT-009 | Span adulterado | Run presente, `payload_bytes` de um span alterado no banco | `receipt verify` | `diverged: ["tools"]` |
| AT-010 | Sem host | Emit sem `--host-transcript` e sem `--provider` | `receipt emit` | `host.model`, `host.agent` e `host.provider` em `unresolved` com as razoes |
| AT-011 | Sem run | Emit sem `--run-id` | `receipt emit` | `tools` em `unresolved`, exit 0 |
| AT-012 | Versao futura | `receipt_version` = 2 num recibo lido por esta build | `receipt verify` | Partes de normalizacao `not_evaluable`, fora de `diverged` |
| AT-013 | Line endings | Arquivo de facts reescrito com CRLF | `receipt verify` | `evidence` `match` |
| AT-014 | Prova fora da uniao | Recibo cita um fact_id `funcval.*` que nao esta nos facts declarados | `receipt verify` | `diverged: ["proof"]` |
| AT-015 | Caminho fora do repo | `--facts ../fora/facts.json` pela tool MCP | `sparkforge_receipt_emit` | Recusa por caminho fora do repo, nada gravado |
| AT-016 | Erro de uso | Recibo com JSON invalido | `receipt verify` | Exit 2 com a dica do comando |

---

## Out of Scope

- Assinatura com chave ou identidade (autoria); quem precisa, assina o arquivo fora do pacote.
- Hash de entrada e de saida por chamada de tool; mudar a instrumentacao de spans.
- Recibo automatico por verbo, cadeia de recibos (hash do anterior) e arvore de Merkle.
- Bundle autocontido que copie facts, findings ou spans.
- Comparacao antes/depois ou ganho estimado dentro do recibo (regras 13 e 30).
- Deduzir modelo, agente ou provider (regra 23).
- Poda do `traces.db`: nao existe hoje e nao nasce aqui.
- Mudar `Finding`, o catalogo, o `report sign` ou o `telemetry export`.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 20: toda lacuna tem nome | `unresolved`, `refused`, `not_rechecked` e `not_evaluable` sempre com razao; nunca `{}` calado |
| Technical | Regra 23: o pacote nao chama provider | Host, agente e modelo so por declaracao (`--host-transcript`, `--provider`) |
| Technical | Regras 13 e 30 | `proof` so aponta fact_ids; nenhum delta, nenhum ganho |
| Technical | Regra 26 | Duas tools movem a superficie; crescimento declarado no commit |
| Technical | Regra 27: medicao nunca derruba a chamada | `traces.db` indisponivel deixa `tools` `unresolved`, e o emit segue |
| Technical | Caso real nunca entra em arquivo | Fixture sintetica; o recibo, commitavel pela politica de `.sparkforge/`, nao carrega conteudo |
| Technical | Modulo novo em `sparkforge/` | `iter_source_files` em vez de `Path.glob` (`test_facts_scan`); `git add` antes dos lotes; nenhum `def` aninhado repetido (codeintel) |
| Technical | Windows e Linux | Caminhos relativos em POSIX no recibo; CRLF normalizado (G4) |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/receipt/` (modulo novo); `adapters/_core.py`, `adapters/cli.py`, `adapters/tools.py`; `agents/executors/sf-synthesizer.md` e espelhos; `parity.yaml`; `manifest.json`; `fixtures/receipt/`; testes em `tests/test_receipt_*.py` | Nenhum recurso de nuvem |
| **KB Domains** | Proveniencia e integridade (content addressing, JSON canonico), testing (golden byte a byte, adulteracao por parte, relogio injetado), observabilidade (spans do `traces.db`) | Contratos de referencia: `report sign`/`verify` e `telemetry export` |
| **IaC Impact** | None | — |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | A uniao `fixtures/graph/import_sem_jar_no_iac` + `fixtures/infra_code/fgac_com_jar_extra` existe com `expected/facts.json` e `expected/findings.json`, e o `arbitrate` sobre ela gera blackboard e ADR | Sem bloco `decision` nao vazio no golden; seria preciso outra fixture | [x] arquivos presentes; saida do `arbitrate` medida em 2026-09-08 (3 claims, 1 contradicao) |
| A-002 | O transcript do host vira facts `host.*` com modelo por `extract_host_transcript_path`, o mesmo leitor do `telemetry export` | O bloco `host` precisaria de leitor proprio | [x] `adapters/_core.py:4693` |
| A-003 | Os spans nao carregam `case_id` e nao guardam hash de I/O | Se carregassem, a ligacao case-run poderia ser conferida em vez de declarada | [x] zero ocorrencias em `sparkforge/observability/` |
| A-004 | Nenhum codigo poda o `traces.db`; ele so fica ausente em outra maquina e no CI por estar no gitignore | Se existisse poda, `not_rechecked` teria mais uma razao | [x] nenhum `DELETE FROM` em `observability/`; o BRAINSTORM dizia "podavel por desenho" e foi corrigido |
| A-005 | O verify consegue reusar `compute_signature` e a leitura do bloco de assinatura sem importar `adapters` a partir de `sparkforge/receipt/` | Se `_split_report`/`_signature_parts` so existirem em `_core.py`, o DESIGN decide entre mover para `findings/` ou chamar pelo adapter | [x] So existem em `_core.py`; o adapter le e passa (DESIGN Decision 1) |
| A-006 | O `case.yaml` tem um `case_id` legivel por `store.load_case` | A parte `case` sairia so com hash | [x] `case/store.py:71` |
| A-007 | O golden de paridade MCP aceita tool nova como adicao sem regenerar o golden inteiro | Se nao aceitar, o DESIGN decide regenerar sob o SDK 2.x | [x] `NOVAS_DEPOIS_DO_GOLDEN` em `tests/test_fixtures_golden_mcp_parity.py:73` |
| A-008 | O span do proprio emit so e gravado no `traces.db` depois que o handler devolve | Se fosse gravado antes, `build` precisaria filtrar pelo `span_id` corrente | [x] Mais do que isso: `record()` roda depois do handler e so no buffer; o disco so no `atexit`. O emit le por `shared_ledger().spans_of` e o verify ancora por `span_id` (DESIGN Decision 2) |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Sete lugares nomeados, spans sem `case_id` medido, limite do `report sign` explicito |
| Users | 3 | Tres papeis, cada um ligado a uma saida (verify, emit, executor) |
| Goals | 3 | 18 metas MoSCoW, cada uma ligada a SC ou AT |
| Success | 3 | Contagens exatas (6 partes, 60 facts, 2 tools, 7 registros, 16 ATs) |
| Scope | 2 | Escopo e fora de escopo explicitos; A-005 a A-008 ficam para o DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-005 a A-008 sao de implementacao e se decidem no DESIGN.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | define-agent | Versao inicial, a partir de `BRAINSTORM_EXECUTION_RECEIPT.md`; A-004 corrige "traces.db podavel por desenho" do brainstorm |
| 1.1 | 2026-09-12 | design-agent | A-005 a A-008 fechadas; G14 com o caminho real do ADR (`.sparkforge/blackboard/adr/`) |

---

## Next Step

**Next:** `/build .claude/sdd/features/DESIGN_EXECUTION_RECEIPT.md`
