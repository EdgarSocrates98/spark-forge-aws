# DEFINE: Doctor e Scan

> `sparkforge doctor` diz se o ambiente esta pronto; `sparkforge scan` roda sozinho os analyzes que cabem num repositorio, julga e resume, sem rede.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DOCTOR_SCAN |
| **Date** | 2026-09-13 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Para usar o SparkForge num repositorio, o operador precisa saber qual `analyze` roda em cada arquivo, encadear `judge` e `report github` a mao, e so descobre extra ausente, pack recusado ou manifesto adulterado quando a chamada falha. Nao ha verbo que diga "o ambiente esta pronto" nem um que "rode o que cabe aqui".

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Engenheiro de dados novo no projeto | Usa a CLI num repositorio de jobs Glue | Nao sabe qual `analyze` usar em cada arquivo; a doc medida em 2026-09-13 precisou de 15 manuais para ensinar isso |
| Mantenedor de CI | Configura o pipeline de PR | Precisa de tres passos (`analyze`, `judge`, `report github`) para ter SARIF e falhar em P0 |
| Operador com instalacao quebrada | Roda a CLI ou o servidor MCP | Descobre extra ausente, pack recusado ou indice velho so no erro; medido: o pacote instalado na maquina do operador responde 0.4.0 no pip e 0.5.0 na CLI |
| Agente host via MCP | Chama tools | Nao tem tool para "rode tudo que cabe neste repositorio" nem para checar o ambiente |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `sparkforge scan [raiz]` monta um plano puro: artefato coletado pelo `kind` do `.sparkforge/artifacts/manifest.json` (sha256 conferido), codigo por extensao (`.py`, `.sql`, `.tf`, `.jsonl`) pela varredura que ja existe |
| **MUST** | Recusas nomeadas no plano: `sem_manifesto` (JSON solto fora do manifesto), `sha256_divergente`, `kind_sem_analyze`, e `analyze_falhou` na execucao, sem derrubar os outros analyzes |
| **MUST** | `scan` grava em `.sparkforge/scan/`: facts por analyze, a uniao, os findings do `judge` e um `summary.json`; imprime o resumo |
| **MUST** | `scan --dry-run` imprime o plano e nao grava nada |
| **MUST** | `sparkforge doctor` com nove checagens nomeadas (`pacote`, `extras`, `mcp`, `catalogo`, `packs`, `knowledge`, `indice_de_codigo`, `artefatos`, `credencial_aws`), cada uma com `status` (`ok`, `warn`, `fail`, `skip`), `detail` e `unlock`; exit 1 com algum `fail` |
| **MUST** | Sem rede no `scan` e no `doctor` por padrao; `doctor --online` (so CLI) chama STS |
| **MUST** | Tools `sparkforge_scan` (`LOCAL_MUTATION`, declara `repo`) e `sparkforge_doctor` (`READ_ONLY`, declara `repo`, nunca vai a rede), com os registros de tool nova |
| **SHOULD** | `scan --format sarif` e `--fail-on P0\|P1` pelo mesmo caminho do `report github` |
| **SHOULD** | `scan` aceita `--glue/--spark/--python/--iceberg/--athena/--emr` e repassa ao `judge` |
| **SHOULD** | `glue_job_run` do manifesto roda `analyze glue-job-runs` com o `--job-name` tirado do `source` (`glue:get_job_runs:{job_name}/{run_id}`); `source` fora dessa forma sai `exige_job_name` |
| **COULD** | `summary.json` lista os `pulos` da varredura (credencial, diretorio ignorado) com a razao |

---

## Success Criteria

- [x] SC1: num repositorio sintetico misto (codigo + artefatos coletados com manifesto), `scan` produz facts e findings iguais, fact a fact e finding a finding, aos dos `analyze` e do `judge` rodados a mao sobre os mesmos arquivos.
- [x] SC2: cada uma das 5 recusas (`sem_manifesto`, `sha256_divergente`, `kind_sem_analyze`, `analyze_falhou`, `exige_job_name`) tem caso em `fixtures/scan/`, e com 1 analyze falhando os outros N-1 ainda gravam facts.
- [x] SC3: `scan --dry-run` sai 0 e deixa `.sparkforge/scan/` sem nenhum arquivo novo.
- [x] SC4: `scan --format sarif` gera SARIF byte a byte igual ao de `report github` sobre os mesmos findings e facts.
- [x] SC5: `doctor` sai 1 com uma checagem `fail` e 0 sem nenhuma; as 9 checagens tem teste para cada status que podem assumir.
- [x] SC6: 2 tools novas (97 no total), registros, surface lock e claims em dia; suite nos 9 lotes com 0 falhas; referencia de `docs/guia/referencia/` regerada.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Repositorio misto | `job.py`, `main.tf`, `query.sql` e dois artefatos coletados com manifesto | `sparkforge scan <raiz>` | plano com 5 entradas; `facts.json` = uniao dos analyzes; `findings.json` = `judge` da uniao; exit 0 |
| AT-002 | Plano sem execucao | o mesmo repositorio | `scan --dry-run` | JSON do plano; nada gravado |
| AT-003 | JSON solto | `dump.json` fora de `.sparkforge/` e fora do manifesto | `scan` | `refused` com `sem_manifesto` e o caminho; nada farejado |
| AT-004 | Artefato adulterado | entrada do manifesto com sha256 que nao bate | `scan` | `sha256_divergente`; o artefato nao e analisado |
| AT-005 | Kind sem analyze | manifesto com `kind` que nenhum analyze le | `scan` | `kind_sem_analyze` |
| AT-006 | Analyze que falha | `.sql` ou event log malformado ao lado de arquivos bons | `scan` | `analyze_falhou` com o erro; os outros analyzes gravam facts |
| AT-007 | Runs do Glue | entrada `glue_job_run` com `source` `glue:get_job_runs:job_x/jr_1` | `scan` | `analyze glue-job-runs --job-name job_x` no plano |
| AT-008 | SARIF | repositorio com findings | `scan --format sarif --fail-on P0` | SARIF igual ao do `report github`; exit 1 se houver P0 |
| AT-009 | Doctor saudavel | instalacao com catalogo valido | `sparkforge doctor` | nove checagens; nenhuma `fail`; exit 0 |
| AT-010 | Doctor com falha | catalogo invalido (diretorio apontado por variavel) | `doctor` | `catalogo` = `fail` com `unlock`; exit 1 |
| AT-011 | Extra ausente | `mcp` ou `boto3` nao importavel | `doctor` | `extras` = `warn`; `mcp`/`credencial_aws` = `skip` com a razao |
| AT-012 | Credencial offline | `boto3` presente, sem credencial resolvivel | `doctor` | `credencial_aws` = `warn`; nenhuma chamada de rede |
| AT-013 | Tool do doctor | chamada MCP `sparkforge_doctor` | `call_tool` | mesma lista de checagens; `--online` inexistente na tool |

---

## Out of Scope

- TUI, bot de review de PR e GitHub Check com totais (custo e regressao exigem `gain` e `funcval`).
- Coleta dentro do `scan` (rede e credencial; seria `CLOUD_MUTATION`).
- Classificar JSON solto pelo conteudo.
- Aposentar ou mudar `forge doctor` (`sparkforge/cli/forge.py`).
- Portas de CLI que faltam para `workload.yaml` e utilizacao (lacunas medidas em 2026-09-13, frente propria).
- Abrir ou atualizar case a partir do `scan`.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 23: nada de rede no pacote alem dos `collect_*`; `doctor --online` e so CLI | Tool do doctor `READ_ONLY` com `openWorldHint: false` |
| Technical | Regra 20: toda recusa com nome | Cinco recusas no plano e na execucao |
| Technical | Varredura so por `varrer_source_files` (gate de glob cru em `sparkforge/`) | `.sparkforge`, `.venv`, `vendor` e credenciais ja sao pulados com razao |
| Technical | Tool nova move registros manuais (memoria `tool-nova-move-registros-manuais`, itens 1-14) | Duas tools: lista, amostra, FAILABLE, `SEM_CAMINHO`/contagem, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity, agente dono, surface, claims, referencia |
| Resource | Fixtures sinteticos (repositorio publico) | `fixtures/scan/` montado de arquivos que ja existem |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/scan/` (novo), `sparkforge/doctor.py` (novo), `sparkforge/adapters/{_core,cli,tools}.py`, `fixtures/scan/`, `tests/` | Ao lado das portas que o scan e o doctor compoem |
| **KB Domains** | Nenhum dominio do KB do agentspec cobre isto; padroes do repositorio: `collect/base.py` (manifesto), `facts/scan.py` (varredura), `_core.report_github` (SARIF), `packs/manifest.py::installed_version`, `rules/loader.py::load_catalog` | Consultar esses modulos no design |
| **IaC Impact** | None | Nada de infraestrutura |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Um fixture pode commitar `.sparkforge/artifacts/` (o `.gitignore` so ignora esse caminho na raiz) | Golden teria de montar o manifesto em `tmp_path` | [x] padrao ancorado, medido 2026-09-13; confirmar com `git check-ignore` no build |
| A-002 | `varrer_source_files` ja pula `.sparkforge`, entao codigo e artefato nunca se contam em dobro | Scan analisaria o event log coletado duas vezes | [x] `DIRETORIOS_IGNORADOS` inclui `.sparkforge` |
| A-003 | Todo `kind` do manifesto casa com um analyze existente (14 kinds dos `collect_*`) | Mapa incompleto; `kind_sem_analyze` mais frequente que o esperado | [ ] conferir no design, um a um |
| A-004 | Os extratores do `_core` aceitam um arquivo so, alem de diretorio | Scan teria de agrupar por diretorio | [ ] conferir por analyze no design |
| A-005 | `report_github` pode ser chamado com arquivos gravados pelo scan sem mudar sua saida | SC4 exige refatorar o caminho do SARIF | [ ] |
| A-006 | O `judge` da uniao produz os mesmos findings que o fluxo manual, sem `fuse` | Scan precisaria rodar `fuse`; medido na doc: regras de Lake Formation e `SF-TIMEOUT-001` so aparecem apos `fuse` | [ ] decidir no design se o scan roda `fuse` |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Dor concreta, medida pela doc de 2026-09-13 e pela versao divergente do pacote |
| Users | 3 | Quatro personas com dor nomeada |
| Goals | 3 | MoSCoW, cada goal verificavel |
| Success | 3 | Seis criterios com numero ou igualdade conferivel |
| Scope | 2 | Fora de escopo explicito; A-006 (rodar `fuse` ou nao) muda o que o scan acha |
| **Total** | **14/15** | |

---

## Open Questions

- A-006: o scan roda `fuse` antes do `judge`? O manual de Lake Formation mostra `SF-LF-005` P0 so depois do `fuse`. Decidir no design, com a igualdade do SC1 contra o fluxo que o manual ensina.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | define-agent | Versao inicial a partir de BRAINSTORM_DOCTOR_SCAN.md |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_DOCTOR_SCAN.md`
