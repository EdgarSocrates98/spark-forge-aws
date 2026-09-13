# BRAINSTORM: Doctor e Scan

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DOCTOR_SCAN |
| **Date** | 2026-09-13 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** §22 de `prompt_new_evo.md`, "UX: existe um produto escondido dentro da CLI". O que resta dele depois do `report github` (PR #50): `sparkforge doctor` ("valida instalacao, MCP, runtimes, packs, credenciais, ferramentas e capacidades"), `sparkforge scan .` ("o Forge decide automaticamente quais coletores executar"), `--format sarif`, GitHub Check com totais, bot de review de PR e TUI.

**Context Gathered:**
- `sparkforge/cli/forge.py` ja tem um `doctor`, mas sem console script (so `sparkforge` e `sparkforge-tools` no pyproject). Ele confere registry, agentes, skills e assinaturas de erro; nao confere MCP, runtimes, packs nem credenciais. `code doctor` existe na CLI principal, so para o indice de codigo.
- Nao existe `scan` nem classificador de artefato. Os analyzes aceitam arquivo ou diretorio.
- Todo `collect_*` grava em `.sparkforge/artifacts/<tipo>/` e registra em `.sparkforge/artifacts/manifest.json` uma entrada com `kind`, `path`, `sha256`, `source` e `collect_command`; `collect verify` confere. Os `kind` casam um a um com um analyze (`event_log`, `terraform`, `glue_job_run`, `cloudwatch`, `iceberg_metadata`, `athena_workgroup`, `emr_cluster`, `emr_serverless`, `emr_eks`, `cloudwatch_logs`, `parquet_footer`, `iam_access`, `lakeformation`, `glue_resource_link`).
- O `source` do `glue_job_run` e `glue:get_job_runs:{job_name}/{run_id}`: o `--job-name` sai do manifesto sem adivinhar.
- `facts/scan.py::varrer_source_files` varre e devolve os `pulos` com nome.
- `report github` ja grava SARIF e resumo de PR; a Checks API chamada pelo pacote foi recusada naquela frente (rede e token).
- `sparkforge/workflows/dag.py` so e usado pelo proprio teste.
- `tests/test_capability_parity.py` cobra tool MCP para todo verbo de CLI, ou razao em `ALLOWED_CLI_ONLY`.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/scan/` (novo), `sparkforge/doctor.py` (novo), `adapters/{_core,cli,tools}.py`, `fixtures/scan/` | Ao lado das portas que ja existem |
| Relevant KB Domains | Nenhum dominio do KB do agentspec cobre descoberta de artefato de Glue; a fonte e o repositorio | Padroes: `collect/base.py` (manifesto), `facts/scan.py` (varredura), `report_github` (SARIF) |
| IaC Patterns | `.tf` do repositorio vai para `analyze terraform` | Nada de infraestrutura nova |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual recorte do §22? (doctor + scan / so scan / so doctor / TUI ou bot) | **doctor + scan** | TUI, bot e Check com totais adiados |
| 2 | Como o scan decide o analyze de cada arquivo? (manifesto + extensao / farejar conteudo / arquivo declarado) | **Manifesto + extensao** | JSON solto sem manifesto sai `sem_manifesto`; nada e farejado |
| 3 | O que o scan executa e grava? (so disco em `.sparkforge/scan` / so stdout / tambem coleta) | **So disco, grava em `.sparkforge/scan`** | Sem rede, sem credencial, sem case |
| 4 | Como o doctor confere credencial AWS? (local com `--online` opcional / sempre STS / nao confere) | **Local, `--online` opcional** | A tool MCP nunca vai a rede |
| 5 | Que amostra aterra o golden? (repo sintetico de fixtures / este repositorio / so unidade) | **Repo sintetico de fixtures** | `fixtures/scan/<caso>/` montado de arquivos que ja existem |
| 6 | Qual abordagem? (A plan/run / B script / C DAG) | **A** | Pacote com `plan()` puro e `run()` |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/pyspark/`, `fixtures/terraform/`, `fixtures/fusion/`, `fixtures/eventlog/` | varios por dominio | `job.py`, `main.tf`, `.sql`, event log `.jsonl` |
| Artefatos coletados | `fixtures/iceberg/`, `fixtures/athena/`, `fixtures/glue_job_run/` | varios | Copiados para `.sparkforge/artifacts/<tipo>/` com manifesto e sha256 reais |
| Output examples | goldens de `analyze` e `judge` dos mesmos arquivos | varios | O scan tem que reproduzir os mesmos facts e findings |
| Ground truth | findings esperados dos fixtures de origem | varios | Conferencia: scan de um arquivo = analyze + judge do mesmo arquivo |

**How samples will be used:**

- Casos de `fixtures/scan/`: repositorio misto (codigo + artefatos coletados), JSON sem manifesto, sha256 divergente, `kind` sem analyze, analyze que falha sem derrubar os outros, SARIF.
- Doctor: casos por status (`ok`, `warn`, `fail`, `skip`) montados por ambiente de teste (extra ausente, pack recusado, manifesto divergente).

---

## Approaches Explored

### Approach A: Pacote plan/run ⭐ Recommended

**Description:** `sparkforge/scan/` com `plan(raiz)` puro (manifesto com sha256, varredura por `varrer_source_files`, recusas nomeadas) e `run(plano)` (extratores do `_core`, uniao, `judge`, `summary.json` em `.sparkforge/scan/`, SARIF pelo caminho do `report github`). `sparkforge/doctor.py` com checagens nomeadas `{id, status, detail, unlock}` e exit code.

**Pros:**
- `--dry-run` mostra o plano sem executar; o plano e testavel isolado.
- Dentro do pacote: tool MCP, wheel, paridade de superficies.

**Cons:**
- Mais um mapa `kind` -> analyze a manter junto dos `collect_*`.

**Why Recommended:** cada peca tem porta existente no codigo (manifesto, varredura, extratores, SARIF). Confianca 0,80 (padrao de codigo, sem KB).

---

### Approach B: Script por subprocess

**Description:** `scripts/scan.py` encadeando a CLI.

**Pros:**
- Nao mexe no pacote.

**Cons:**
- Sem tool MCP, fora do wheel; um processo por analyze.

---

### Approach C: Sobre `workflows/dag.py`

**Description:** Reusar o motor de DAG.

**Pros:**
- Ordem e dependencia explicitas.

**Cons:**
- O fluxo e linear (extrair, unir, julgar); o DAG so tem uso em teste.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-13, nesta sessao |
| **Reasoning** | Portas existentes para cada passo; plano testavel e visivel por `--dry-run` |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Artefato coletado pelo `kind` do manifesto, com sha256 conferido | O coletor ja declarou o tipo; sha256 divergente e artefato adulterado ou trocado | Farejar conteudo |
| 2 | Codigo por extensao: `.py` -> `pyspark` e `sql` (literal), `.sql` -> `sql`, `.tf` -> `terraform`, `.jsonl` fora de `.sparkforge/` -> `event-log` | Extensoes inequivocas | Classificar `.json` solto |
| 3 | Recusas nomeadas: `sem_manifesto`, `sha256_divergente`, `kind_sem_analyze`, `analyze_falhou` | Regra 20 | Pular em silencio |
| 4 | `--job-name` do `glue_job_run` sai do `source` do manifesto | Deterministico | Inferir do nome do arquivo |
| 5 | Grava em `.sparkforge/scan/` (facts por analyze, uniao, findings, summary); stdout traz o resumo | Os outros verbos reusam os facts | So stdout |
| 6 | `--format sarif` e `--fail-on` pelo caminho do `report github` | Um SARIF so no projeto | Serializador proprio |
| 7 | Tool `sparkforge_scan` `LOCAL_MUTATION` com `repo`; tool `sparkforge_doctor` `READ_ONLY` com `repo`, nunca `--online` | Anotacao reflete o efeito | Doctor com rede pela tool |
| 8 | Doctor com nove checagens por portas existentes (`pacote`, `extras`, `mcp`, `catalogo`, `packs`, `knowledge`, `indice_de_codigo`, `artefatos`, `credencial_aws`); exit 1 em `fail` | Serve de gate de CI | Doctor que sempre sai 0 |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| TUI | Exige dependencia nova (rich/textual) | Yes |
| Bot de review de PR | Comentar exige rede e token no pacote | Yes, no host |
| GitHub Check com totais ("Cost decreased 12.4%") | Custo e regressao exigem `gain` e `funcval`, que o scan nao roda; o SARIF ja cobre o Code Scanning | Yes |
| Scan que coleta | Muda o verbo para rede e credencial (`CLOUD_MUTATION`) | Yes |
| Aposentar `forge doctor` | Tem teste e doc; unificar fica para depois | Yes |
| Farejar conteudo de JSON | Heuristica; dump ambiguo iria para o extrator errado | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Scan: plano por manifesto e extensao, recusas, gravacao em `.sparkforge/scan`, SARIF, tool | ✅ | "Sim, segue" | No |
| Doctor: nove checagens, contrato de saida, exit code, tool sem rede | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Usar o SparkForge num repositorio exige saber qual dos 25 `analyze` roda em cada arquivo, encadear `judge` e `report github` a mao, e descobrir sozinho por que uma tool ou um extra nao funciona. Nao ha um verbo que diga "o ambiente esta pronto" nem um que "rode o que cabe aqui".

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Engenheiro de dados que chega ao projeto | Nao sabe qual analyze usar em cada arquivo |
| Mantenedor de CI | Quer um passo so que produza SARIF e falhe em P0 |
| Operador com instalacao quebrada | Descobre extra ausente ou pack recusado so quando a chamada falha |
| Agente host via MCP | Nao tem tool para "rode tudo que cabe neste repositorio" |

### Success Criteria (Draft)
- [ ] Num repositorio sintetico misto, `scan` produz os mesmos facts e findings que os `analyze` e o `judge` rodados a mao sobre os mesmos arquivos.
- [ ] Cada recusa (`sem_manifesto`, `sha256_divergente`, `kind_sem_analyze`, `analyze_falhou`) tem caso de fixture, e um analyze que falha nao derruba os outros.
- [ ] `--dry-run` imprime o plano e nao grava nada.
- [ ] `--format sarif` gera o mesmo SARIF que `report github` sobre os mesmos findings e facts.
- [ ] `doctor` sai 1 com uma checagem `fail` e 0 sem nenhuma; cada checagem tem caso de teste para cada status que pode ter.
- [ ] Duas tools novas com registros, surface lock e claims em dia; suite por lotes com 0 falhas.

### Constraints Identified
- Sem rede no scan e na tool do doctor (regra 23 e anotacao `openWorldHint`).
- Regra 20: toda recusa com nome.
- Varredura so por `varrer_source_files` (gate de glob cru).
- Fixtures sinteticos (repositorio publico).

### Out of Scope (Confirmed)
- TUI, bot de PR, GitHub Check com totais, coleta dentro do scan, aposentar `forge doctor`, farejar conteudo.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 6 (mais YAGNI) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_DOCTOR_SCAN.md`
