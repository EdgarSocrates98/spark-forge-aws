# BRAINSTORM: Execution Receipt

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXECUTION_RECEIPT |
| **Date** | 2026-09-12 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Frente §14 de `prompt_new_evo.md`, "Execution Receipt". A ideia e que toda execucao produza uma "nota fiscal" assinada ou content-addressed, com `execution_id`, `case_id`, agente, modelo, tools, evidencia, claims, decisao, acoes, testes, metricas antes e depois, rollback e `artifacts_sha256`. Ela responderia "quem decidiu, baseado em que, usando qual modelo, que ferramenta chamou, que alteracao fez e como provou o resultado". Branch `feat/execution-receipt`, a partir da `main` (ja com #48 a #53).

**Context Gathered:**
- **O que ja existe:**
  - `report sign`/`report verify` (`adapters/_core.py:4748` e `:4838`, `findings/signature.py`). A assinatura e o sha256 do corpo normalizado mais `fact_ids`, `rule_ids`, `catalog_version` e `schema_version`, sem chave. O proprio verbo declara que prova "correspondencia entre este corpo, esta evidencia e este catalogo -- nunca autoria". O verify diz qual parte divergiu (`version`, `evidence`, `catalog`, `body`), em ordem fixa, e sai com codigo 1.
  - Spans de tool em `.sparkforge/traces.db` (`observability/store.py:61-96`), com chave `run_id`. Colunas: `name`, `status`, `outcome`, `payload_bytes`, `payload_basis`, `detail_level`, `item_count`, horarios, `metadata_json`. O `telemetry export` (#52) ja le essa tabela.
  - O `telemetry export` le o transcript do host (`observability/otlp.py::_host`) e declara provider sem deduzir. Sem provider sai `gen_ai.provider.name` com `provider_nao_declarado`, e sem modelo sai `modelo_ausente` ou `modelos_multiplos`.
  - Artefatos agenticos do case: blackboard em `.sparkforge/blackboard/*.jsonl` (`claims`, `evidence`, `contradictions`, `decisions`, `unknowns`...), ADR em `.sparkforge/adr/ADR-<id>.md` com `rollback` obrigatorio, e debate em `.sparkforge/debate/<debate_id>/`.
  - `funcval compare` e `benchmark` ja emitem facts (`funcval.*` e os de benchmark). "Tests" e "before/after" do §14 existem como fact quando fazem parte da uniao.
  - `sf-synthesizer.md` ja fecha a sessao com `report_sign` (passo 4) e `telemetry_export`. A capacidade vizinha em `parity.yaml:679` e "prove a report corresponds to its evidence and catalog".
- **O que nao existe:**
  - Nenhum artefato amarra, num so lugar, o case, a uniao de facts, os findings, o report, as decisoes agenticas, as tools chamadas e o host.
  - Os spans **nao carregam `case_id`** (zero ocorrencias em `sparkforge/observability/`). So o `run_id` liga uma sessao de tools a um case.
  - O span **nao guarda hash** de entrada nem de saida da tool (zero `sha256`/`hashlib` em `context_ledger.py`).
- **Medido em 2026-09-12:**
  - Seis helpers de JSON canonico e digest ja duplicados: `_canonical` em `findings/models.py:21` e `agentic/models.py:77`, `_canonico` em `adapters/_core.py:235` e `agentic/executor/debate_run.py:1073`, `_digest` em `agentic/models.py:82` e `adapters/_core.py:7036`.
  - `.gitignore:31-45`: a politica default de `.sparkforge/` e "derivado pequeno pode ser commitado". Ficam fora so `artifacts/*`, `traces.db`, `cache/` e `local/`. Um recibo em `.sparkforge/receipts/` e commitavel, e por isso nao pode carregar conteudo de caso.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/receipt/` (modulo puro: `build`, `verify`); `adapters/_core.py`, `adapters/cli.py`, `adapters/tools.py`; `agents/executors/sf-synthesizer.md`; `parity.yaml`; `fixtures/receipt/` | Compoe sobre artefatos que outros verbos ja gravaram; nao le artefato de job |
| Relevant KB Domains | Proveniencia e integridade (content addressing), testing (golden byte a byte, adulteracao por parte), observabilidade (spans do `traces.db`) | Mesmo contrato do `report sign`/`verify` |
| IaC Patterns | Nenhum recurso novo | So codigo e registros manuais |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Que garantia o recibo da? | Content-addressed, sem chave | `receipt_id` = sha256 do JSON canonico; autoria sai como recusa nomeada; cosign/`attest-blob` pode assinar o arquivo fora do pacote sem codigo novo |
| 2 | O que e "uma execucao"? | O case, com `--run-id` declarado | Verbo explicito `receipt emit`; sem run-id, os spans saem `unresolved`; nunca deduzir o run a partir do case |
| 3 | Quais blocos do §14 entram alem do nucleo? | Os quatro: host, decisao, prova, actions L0 | Todo bloco sem fonte sai `unresolved` nomeado, nunca vazio calado |
| 4 | O bloco `tools` amarra o que? | O span como esta | Sem mudar a instrumentacao; `tool_io` sai como recusa nomeada |
| 5 | CLI ou MCP? | CLI e duas tools MCP | `receipt_emit` (LOCAL_MUTATION) e `receipt_verify` (READ_ONLY); o span do proprio emit fica fora, com nome |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/graph/import_sem_jar_no_iac` + `fixtures/infra_code/fgac_com_jar_extra` (uniao) | 60 facts, 3 findings | Ja medida em 2026-09-08: o `arbitrate` produz 3 claims, 11 evidencias e 1 contradicao, o que da bloco de decisao nao vazio |
| Input files | `traces.db` sintetico, gerado no teste | 1 run | Cobre `match`, run podado e banco ausente |
| Input files | Transcript de host sintetico | 1 | Cobre `host.model` presente; a ausencia cobre `unresolved` |
| Output examples | `fixtures/receipt/expected/receipt.json` | 1 golden | Byte a byte com `--now` fixo |
| Ground truth | `report sign`/`verify` e `telemetry export` | — | Contratos que o recibo reutiliza em vez de reimplementar |

**How samples will be used:**

- O golden fixa o formato e o determinismo: a mesma entrada com o mesmo `--now` da o mesmo `receipt_id`.
- Os testes de adulteracao editam, apagam ou podam uma parte por vez, e o verify precisa nomear exatamente aquela parte.
- Nenhum caso real entra em arquivo; tudo e sintetico.

---

## Approaches Explored

### Approach A: manifesto por referencia, com hash por parte ⭐ Recommended

**Description:** o recibo guarda caminho, sha256, ids e contagens de cada artefato do case (case, arquivos de facts, findings, report, blackboard, ADR, debate) e as colunas escolhidas dos spans do run-id. Cada parte tem digest proprio. O `receipt_id` e `rcpt_` + sha256 do JSON canonico sem o proprio id. O `receipt verify` recalcula tudo a partir do disco e diz qual parte divergiu.

**Pros:**
- E o contrato que `report sign`/`verify` ja provaram: diagnostico por parte, ordem fixa e codigo 1.
- Nao carrega conteudo, entao pode ser commitado.
- Reutiliza `compute_signature` e o `report_verify`: a signature do report entra como parte.

**Cons:**
- Verificar exige o repositorio com os artefatos; sem eles, a parte sai `missing`.
- Os spans sao snapshot e o `traces.db` e podavel, entao a parte `tools` pode sair `not_rechecked`.

**Why Recommended:** e o menor passo que responde ao §14 sem ferir "caso real nunca entra em arquivo", e reaproveita dois contratos ja testados. Confianca 0,85.

---

### Approach B: bundle autocontido

**Description:** o recibo carrega copias de facts, findings e spans, e verifica sem o repositorio.

**Pros:**
- Verificacao portatil.

**Cons:**
- Arquivo grande.
- Poe conteudo de caso num arquivo commitavel.

**Why not:** fere "caso real nunca entra em arquivo".

---

### Approach C: arvore de Merkle

**Description:** cada fact, finding e span e uma folha, e a raiz e o `receipt_id`. Permite provar uma parte sem revelar as outras.

**Pros:**
- Prova seletiva.

**Cons:**
- Complexidade sem consumidor hoje.

**Why not:** YAGNI. A abordagem A ja da diagnostico por parte com uma arvore de um nivel, e `receipt_version` dentro do hash deixa evoluir para C sem ambiguidade.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-12 |
| **Reasoning** | Contrato ja provado pelo `report verify`, diagnostico por parte, sem conteudo de caso no arquivo |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Content-addressed sem chave; `proves` diz "correspondencia entre este recibo e estes artefatos -- nunca autoria"; `refused: authorship` com `content_addressed_sem_chave` | Mesmo contrato do `report sign`; zero dependencia nova; assinatura de autoria e gestao de chave, que mora no host ou no CI | Chave ed25519 local, Sigstore keyless no pacote, slot `attestations[]` |
| 2 | Unidade = o case, com `--run-id` declarado pelo operador | Os spans nao carregam `case_id`; deduzir a ligacao seria inventar | Recibo so da sessao de tools; recibo automatico por verbo |
| 3 | `--facts` repetivel e obrigatoriamente a uniao | O mesmo contrato do `arbitrate`: subconjunto fabrica recibo que a execucao real nao produziu | Um arquivo so |
| 4 | Bloco `host` com `--host-transcript` e `--provider` declarados, reusando o leitor do `telemetry export`; sem eles, `unresolved` (`host.model: transcript_ausente`, `host.provider: provider_nao_declarado`) | Regra 23: o pacote nao chama provider, e o modelo so aparece por declaracao do host | Deduzir o provider pelo nome do modelo |
| 5 | Bloco `decision` com ids e hashes do blackboard, dos ADRs (com `rollback_present`) e dos debates, so quando existirem | Responde "quem decidiu, baseado em que" sem copiar o texto das decisoes | Copiar claims e decisoes para dentro do recibo |
| 6 | Bloco `proof` so com fact_ids `funcval.*` e de benchmark presentes na uniao; nenhuma comparacao nem ganho | Regras 13 e 30; o recibo aponta onde esta a prova ou diz que ela nao existe | Calcular delta antes/depois |
| 7 | Bloco `actions` fixo: `autonomy: L0`, `applied_changes: false`, `items: []` | Diz no proprio recibo que nada foi aplicado | Omitir o campo |
| 8 | Bloco `tools` com `name`, `status`, `outcome`, `payload_bytes`, `detail_level`, `start`, `end` e `spans_sha256`; `metadata_json` fica fora; `refused: tool_io` com `span_sem_hash_de_io` | O conteudo que importa ja esta amarrado pelos arquivos de facts e findings; mexer na instrumentacao arrasta `telemetry export` e a paridade MCP | Gravar `args_sha256`/`result_sha256` no span |
| 9 | O span do proprio `receipt_emit` fica fora, listado em `tools.excluded` | O recibo nao pode conter a chamada que o produz | Incluir e fechar o hash depois |
| 10 | `emitted_at` vem de `--now` e entra no hash | Mesmo `--now` com os mesmos artefatos da o mesmo id | Relogio implicito |
| 11 | O JSON canonico reutiliza um helper existente (`findings/models._canonical`) | Ja existem seis helpers duplicados; um setimo aumenta a divida | Helper novo |
| 12 | sha256 de artefato de texto normaliza CRLF para LF antes de hashear, sob `receipt_version` | Sem isso, um recibo emitido no Windows diverge no CI Linux pelo checkout do git | Bytes crus |
| 13 | `receipt verify` na ordem fixa `version, integrity, case, evidence, judgment, decision, proof, tools, host`; item `match`, `diverged` ou `missing`; `valid` = integrity ok e nenhuma parte `diverged` ou `missing`; codigo 1 quando invalido e 2 em erro de uso | Mesmo contrato do `report verify`; arquivo apagado e `missing`, nunca `diverged` | Veredito unico sem diagnostico |
| 14 | Spans com run podado ou `traces.db` ausente saem `not_rechecked` com a razao, listados, sem derrubar `valid` | O `traces.db` fica fora do git e nao existe em outra maquina nem no CI (nenhum codigo o poda: corrigido no DEFINE, A-004); o modo estrito quebraria a verificacao nesses lugares | `not_rechecked` derruba `valid` |
| 15 | `receipt_version` diferente da build: partes que dependem de normalizacao saem `not_evaluable`, fora de `diverged` | Licao do `report verify`: a versao no hash garante que as assinaturas diferem, e a versao declarada permite dizer por que | Tratar como corpo adulterado |
| 16 | CLI `receipt emit`/`receipt verify` e tools `sparkforge_receipt_emit` (LOCAL_MUTATION, grava so em `.sparkforge/receipts/`, caminhos confinados ao repo) e `sparkforge_receipt_verify` (READ_ONLY) | Quem executa e o agente, e ele fecha a sessao emitindo o recibo | So CLI; so verify no MCP |
| 17 | `sf-synthesizer` ganha um passo depois do sign e do telemetry; `parity.yaml` ganha a capacidade "prove what an execution used and decided" | O executor que ja fecha a sessao | Coordenador novo |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Assinatura com chave ou identidade (autoria) | Gestao de chave mora no host ou no CI; `cosign attest-blob` assina o arquivo sem codigo no pacote | Yes |
| Hash de entrada e saida por chamada de tool | Mexe na instrumentacao, no `telemetry export` e na paridade MCP; o conteudo relevante ja esta amarrado | Yes |
| Recibo automatico por verbo, encadeado | Muda o output de verbos existentes e os goldens | Yes |
| Cadeia de recibos (hash do anterior) | Sem consumidor | Yes |
| Arvore de Merkle / prova seletiva | Sem consumidor (abordagem C) | Yes, sob novo `receipt_version` |
| Bundle autocontido | Poe conteudo de caso em arquivo commitavel (abordagem B) | No |
| Comparacao antes/depois ou ganho estimado | Regras 13 e 30; mora em `benchmark` e na futura frente §21 | No, dentro do recibo |
| `model`, `agent_version` deduzidos | Regra 23; so por declaracao do host | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| 1: forma do recibo, local e invariantes V1 a V5 | ✅ | "Sim, segue" | No |
| 2: verify por parte, `not_rechecked` sem derrubar `valid` | ✅ | "Sim, segue" | No |
| 3: superficie, V6 de CRLF, fixture, testes e fora do escopo | ✅ | "Sim, escreve o documento" | No |

**Invariantes aprovados:**
- V1: toda parte sem fonte vai para `unresolved` ou `refused`, nunca `{}` calado.
- V2: o recibo nao carrega conteudo, so caminho, hash, id, contagem e as colunas escolhidas do span.
- V3: `--facts` e a uniao.
- V4: o JSON canonico reutiliza um helper existente.
- V5: `emitted_at` vem de `--now` e entra no hash.
- V6: artefato de texto e hasheado com CRLF normalizado para LF.

**Forma aprovada (esboco, o Define fixa o schema):**

```json
{
  "receipt_version": 1,
  "receipt_id": "rcpt_<sha256 do JSON canonico sem este campo>",
  "emitted_at": "<--now>",
  "case":      {"path": ".sparkforge/case.yaml", "sha256": "...", "case_id": "..."},
  "evidence":  {"facts_files": [{"path": "...", "sha256": "...", "fact_count": 0}], "fact_ids_sha256": "..."},
  "judgment":  {"findings_path": "...", "sha256": "...", "rule_ids": [], "fact_ids": [],
                "catalog_version": 0, "schema_version": 0, "report": {"path": "...", "signature": "sig_..."}},
  "decision":  {"blackboard": [{"path": "...", "sha256": "...", "count": 0}], "decision_ids": [],
                "adrs": [{"path": "...", "sha256": "...", "rollback_present": true}], "debates": []},
  "proof":     {"tests": [], "before_after": []},
  "tools":     {"run_id": "...", "spans": [], "spans_sha256": "...", "excluded": ["receipt_emit"]},
  "host":      {"provider": "...", "model": "...", "agent": "...", "transcript_sha256": "..."},
  "actions":   {"autonomy": "L0", "applied_changes": false, "items": []},
  "unresolved": [],
  "refused":   [{"field": "authorship", "reason": "content_addressed_sem_chave"},
                {"field": "tool_io", "reason": "span_sem_hash_de_io"}],
  "proves": "correspondencia entre este recibo e estes artefatos -- nunca autoria"
}
```

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Depois de uma sessao, o SparkForge deixa artefatos espalhados: o case, os arquivos de facts, os findings, o report assinado, o blackboard, os ADRs, os debates e os spans num `traces.db` que nao vai para o git. Nenhum artefato diz, num lugar so e de forma conferivel, quais desses pertencem a mesma execucao, com qual catalogo ela julgou, que tools chamou, que modelo o host declarou e que nada foi aplicado. O `report sign` prova a correspondencia do relatorio, mas nao a da execucao.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Revisor corporativo ou auditor | Precisa saber em que evidencia, com qual catalogo e com qual modelo declarado uma recomendacao nasceu, e se algum artefato mudou depois |
| Operador que recebe o case de outra pessoa | Nao tem como conferir que os arquivos que recebeu sao os da execucao original |
| Agente que fecha a sessao (`sf-synthesizer`) | Nao tem onde registrar o fechamento alem do report assinado |

### Success Criteria (Draft)
- [ ] Golden byte a byte em `fixtures/receipt/` com `--now` fixo; duas emissoes identicas dao o mesmo `receipt_id`.
- [ ] Adulteracao por parte: editar cada artefato faz o verify nomear exatamente aquela parte; apagar da `missing`; podar o run da `not_rechecked` com `valid: true`; editar o recibo da `integrity`; `receipt_version` diferente da `not_evaluable`.
- [ ] Sem transcript e sem provider: `host.model` e `host.provider` saem em `unresolved` com a razao.
- [ ] Varredura V2: o recibo nao contem nenhum valor de `measures` nem `metadata_json`.
- [ ] O recibo emitido no Windows verifica no CI Linux (V6).
- [ ] O span do proprio emit fica fora e aparece em `tools.excluded`.
- [ ] As duas tools validam contra o proprio schema com amostra real.
- [ ] Os sete registros de tool nova atualizados, `check_surface_lock --update` com o crescimento declarado no commit, e as claims de `len(TOOLS)` remediadas pela lista de ids da saida do gate.
- [ ] Gates (`check_vnext_claims`, `check_status_numbers --strict`, `check_surface_lock`, `check_evals`, `ruff`) e suite por lotes verdes.

### Constraints Identified
- Regra 20: toda lacuna com nome (`unresolved`/`refused`/`not_rechecked`).
- Regra 23: o pacote nao chama provider; host e modelo so por declaracao.
- Regras 13 e 30: nenhum ganho, nenhuma comparacao dentro do recibo.
- Regra 26: duas tools novas movem a superficie, e o crescimento sai declarado.
- Regra 27: se o `traces.db` estiver indisponivel, o emit nao falha; a parte `tools` sai `unresolved`.
- Caso real nunca entra em arquivo: fixture sintetica, e recibo sem conteudo.
- Modulo novo: `iter_source_files` em vez de `Path.glob` (`test_facts_scan`), e `git add` antes dos lotes.

### Out of Scope (Confirmed)
- Tudo o que esta na tabela YAGNI acima.
- Mudar a instrumentacao de spans, o `Finding`, o catalogo ou o `report sign`.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 9 (5 de discovery, 1 de abordagem, 3 de validacao) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Validations Completed | 3 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_EXECUTION_RECEIPT.md`
