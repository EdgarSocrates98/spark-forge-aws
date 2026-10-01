# BRAINSTORM: SARIF + GitHub Check

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SARIF_GITHUB_CHECK |
| **Date** | 2026-09-11 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Frente §22 de `prompt_new_evo.md`, "UX: existe um produto escondido dentro da CLI". A proposta: `sparkforge scan . --format sarif` para aparecer no GitHub Code Scanning, e um GitHub Check no PR ("41 checks passed / 3 findings / 1 P0"). Deterministico e sem provider. Branch `feat/sarif-github-check`, a partir da `main` (que ja tem o #49).

**Context Gathered:**
- Nenhum arquivo em `sparkforge/` cita SARIF. Tambem nao existe verbo `scan`. Existe `report sign`/`report verify`, uma familia `report` onde o verbo novo cabe.
- `Finding` (`sparkforge/findings/models.py`) nao tem campo de localizacao: onde o problema esta vive em `subject`, e cada `evidence` e um `fact_id`, cujo fact tem o proprio `subject`.
- **Medido nos goldens (`fixtures/**/expected/findings.json`, 222 findings):**

  | `subject.type` | Findings | Com `file` | Com `line` |
  |---|---|---|---|
  | `source_location` | 73 | 73 | 53 |
  | `job_run` | 60 | 3 | 0 |
  | `stage` | 28 | 0 | 0 |
  | `table` | 28 | 18 | 0 |
  | `tf_resource` | 25 | 24 | 24 |
  | `plan_node` | 8 | 8 | 8 |

  Cerca de 77 findings tem linha em arquivo de codigo do repositorio. Os de `plan_node` apontam para `plan.txt`, que e artefato de execucao. Os 116 de runtime (`job_run`, `stage`, `table`) nao tem linha nenhuma.
- **Conferido na fonte T1** (`docs.github.com/.../sarif-support-for-code-scanning`):
  - resultado sem `locations` e descartado;
  - `uri` relativo e interpretado a partir da raiz do repositorio;
  - `region.startLine` identifica a linha;
  - o `upload-sarif` calcula `partialFingerprints` a partir do fonte quando ele falta, e o GitHub so usa o `primaryLocationLineHash`;
  - `level` aceita `note`, `warning` ou `error`;
  - `security-severity` (0,1 a 10) e so para regras marcadas `security`;
  - limites: 20 runs por arquivo, 5 000 resultados exibidos por run e 10 MB compactado;
  - `runAutomationDetails.id` separa uploads por categoria.
- CI: `.github/workflows/ci.yml`, `release.yml` e `refresh-knowledge.yml`. Nenhum sobe SARIF hoje.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/report/` (ou `sparkforge/github/`) para a projecao; `adapters/_core.py`, `adapters/cli.py` e `adapters/tools.py` para o verbo e a tool; `fixtures/sarif/`; `docs/` e `examples/github/` | O verbo compoe sobre findings e facts, no molde dos verbos de topo |
| Relevant KB Domains | CI/CD (GitHub Actions), testing (golden, validacao por JSON Schema), static analysis reporting (SARIF 2.1.0) | Padrao de golden por fixture e de schema versionado |
| IaC Patterns | GitHub Actions (`ci.yml`) | Um job novo, so por `workflow_dispatch` |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual superficie do GitHub e o objetivo? | Os dois: Code Scanning (SARIF) e check de PR | Duas saidas da mesma projecao |
| 2 | Onde roda, e quem liga? | Verbo da CLI + workflow de exemplo documentado | Nada publicado no Marketplace; o time copia o workflow |
| 3 | O que o verbo consome? | Findings + facts ja julgados | Nao le artefato; compoe como os verbos de topo |
| 4 | Criterio de sucesso? | Schema + golden + upload real | SARIF valida contra o schema OASIS, golden por fixture, e o GitHub aceita um upload real |
| 5 | Amostras? | So fixtures + fontes T1 | Nada de repositorio real em arquivo |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/**/expected/findings.json` + `facts.json` | 222 findings, 6 tipos de `subject` | Entrada do invariante "nenhum finding some" |
| Output examples | `fixtures/sarif/*/expected/{sparkforge.sarif,summary.md,annotations.txt}` (a criar) | 4 casos | Golden |
| Ground truth | Schema `sarif-schema-2.1.0.json` (OASIS), versionado com a URL e o sha256 | 1 | Validacao de forma |
| Related code | `sparkforge/findings/models.py`, `rules/catalog/*.yaml`, `adapters/_core.py` (`report sign`/`verify`) | — | `tool.driver.rules` vem do catalogo |

**How samples will be used:**

- Os 4 casos de `fixtures/sarif/` fixam a saida byte a byte.
- Os 222 findings dos goldens existentes provam que nenhum finding some: cada um vai para o SARIF ou para a recusa nomeada.
- O schema OASIS valida todo SARIF que os testes geram.

---

## Approaches Explored

### Approach A: um verbo, duas saidas da mesma projecao, e recusa nomeada para o que nao tem linha ⭐ Recommended

**Description:** `sparkforge report github` compoe sobre findings + facts e produz tres coisas.
- **SARIF 2.1.0** so com os findings que tem localizacao no repositorio. A localizacao vem do `subject` ou, se ele nao tiver, de um fact de `evidence` com arquivo e linha, e so conta se o arquivo existir sob `--repo`.
- **Resumo em Markdown** para o check do PR, com todos os findings. Os sem localizacao ficam numa secao propria, com o motivo.
- **Anotacoes** `::error|warning|notice file=,line=::` no stdout, que aparecem no diff do PR.

O pacote nao faz chamada de rede.

**Pros:**
- Deterministico e offline.
- Nenhum finding some, e nenhum ganha uma linha que nao tem.
- Aceito pelo GitHub por construcao.

**Cons:**
- Cerca de metade dos findings aparece so no resumo do PR, e nao na aba Security.

**Why Recommended:** e o unico caminho em que a localizacao e medida, e nao inventada. A regra 20 ja da o formato da recusa, e os verbos de topo dao o formato de compor sem ler artefato. Confianca 0,85: ha padrao no codigo, mas nenhum precedente de SARIF.

---

### Approach B: SARIF com tudo, ancorando runtime num arquivo

**Description:** os findings de runtime ficam presos a um arquivo ancora, como `.sparkforge/case.yaml` na linha 1, ou o proprio artefato.

**Pros:**
- Tudo na aba Security.

**Cons:**
- Precisao falsa: o alerta aponta uma linha que nao causou nada.
- O event log nao esta no repositorio, e o GitHub descarta o que nao localiza.

---

### Approach C: Checks API chamada pelo proprio pacote

**Description:** o verbo publica o check, com anotacoes e resumo, pela API do GitHub com um token.

**Pros:**
- Check com nome proprio e anotacoes ricas.

**Cons:**
- Rede e token dentro do pacote, o que fere o perfil `offline-strict`.
- Maior superficie de seguranca, sem ganho de fidelidade sobre o step summary e as anotacoes do workflow.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-11 |
| **Reasoning** | Localizacao medida, nenhum finding perdido, sem rede no pacote |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Verbo `sparkforge report github`, na familia `report` | Compoe sobre findings e facts, sem ler artefato | `scan .`, que descobre, extrai e julga tudo de uma vez |
| 2 | Localizacao: `subject` com arquivo e linha; senao, fact de `evidence` com arquivo e linha; e o arquivo precisa existir sob `--repo` | So entra no SARIF o que o GitHub consegue mostrar numa linha real | Ancorar em arquivo sintetico |
| 3 | Sem localizacao: secao do resumo com motivo (`runtime`, `arquivo fora do repo`, `sem linha`) | Regra 20: recusa tem nome | Descartar calado |
| 4 | Saidas com nome fixo (`.sparkforge/report/sparkforge.sarif` e `summary.md`) dentro de `--repo` | Nada do argv vira caminho de escrita (licao do Snyk no eval harness) | `--out <caminho>` |
| 5 | Severidade: P0/P1 viram `error`, P2 vira `warning`, P3/P4 viram `note`; sem `security-severity` | As regras sao de performance e custo; marca-las como `security` as poria na contagem de vulnerabilidades | Mapear para `security-severity` |
| 6 | `partialFingerprints` omitido | O `upload-sarif` o calcula a partir do fonte, e o GitHub so usa o `primaryLocationLineHash` | Calcular o hash no pacote |
| 7 | `--fail-on P0\|P1`: exit 1 quando ha finding daquela severidade ou pior; erro de uso continua 2 | O check do PR fica vermelho sem API | Sempre 0 |
| 8 | Tool MCP `sparkforge_report_github`, `READ_ONLY`, que devolve o SARIF, o resumo, as contagens e a recusa, sem gravar | Gravar e da CLI; a tool so le | Tool `LOCAL_MUTATION` |
| 9 | Upload real so por `workflow_dispatch`, com `category: sparkforge-fixtures` | Os alertas das fixtures, codigo ruim de proposito, nao enchem a aba Security a cada push | Upload a cada push na `main` |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `sparkforge scan .` (descobrir artefatos, escolher extratores e julgar) | Muito maior; o workflow de exemplo encadeia analyze → judge → report | Yes |
| So findings novos do PR (diff contra a base) | O proprio Code Scanning compara com a analise da base e marca o que o PR introduziu | Yes |
| Checks API / check com nome proprio | Exige rede e token no pacote (abordagem C) | Yes |
| PR Review Bot (comentarios) | Mesma razao, e as anotacoes no diff ja cobrem o que tem linha | Yes |
| `sparkforge doctor` | Fora do nucleo desta frente | Yes |
| TUI | Fora do nucleo desta frente | Yes |
| GitHub Action publicada no Marketplace | O workflow de exemplo resolve; publicar exige versionamento e manutencao proprios | Yes |
| `security-severity` / tag `security` | Regras de performance e custo nao sao vulnerabilidades | No, salvo se entrar regra de seguranca de verdade |
| Localizar findings de `stage` pela ponte codigo–execucao (`spark.stage.callsite`) | E derivacao nova, e pede fixture propria | Yes: e o proximo passo natural para tirar findings de runtime da recusa |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Forma do verbo e da projecao (saidas, localizacao, severidade, tool MCP) | ✅ | "Sim, segue" | No |
| Prova (fixtures/sarif, schema OASIS, invariante dos 222, gate e anotacoes, upload real so por `workflow_dispatch`) | ✅ | "Sim, escreve o BRAINSTORM" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Os findings do SparkForge so existem como JSON e texto de CLI. O time que revisa um PR de job PySpark ou de Terraform nao os ve onde revisa: nem na linha do diff, nem na aba Security, nem no status do PR.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Engenheiro de dados que abre PR | So descobre o P0 se alguem rodar a CLI e ler o JSON |
| Revisor do PR | Nao ve o finding na linha que esta revisando |
| Dono da plataforma | Nao tem um gate que bloqueie o merge por severidade sem integrar a API do GitHub |

### Success Criteria (Draft)
- [ ] Todo SARIF gerado nos testes valida contra o `sarif-schema-2.1.0.json` da OASIS, versionado com o sha256 de origem.
- [ ] 4 casos em `fixtures/sarif/` batem byte a byte com os goldens (SARIF, resumo e anotacoes).
- [ ] Nos 222 findings dos goldens de `fixtures/`, a soma SARIF + recusa e 222; nenhum resultado do SARIF tem arquivo inexistente ou linha ausente.
- [ ] `--fail-on P0` sai 1 com um P0 e 0 so com P1; `--fail-on P1` sai 1 com um P1.
- [ ] Um upload real por `workflow_dispatch` e aceito pelo GitHub, conferido em `gh api repos/{repo}/code-scanning/analyses` com a contagem de resultados.
- [ ] `check_surface_lock.py --update` com o crescimento declarado, e os gates de lastro, status e evals verdes.

### Constraints Identified
- Regra 20: todo finding sem localizacao sai como recusa nomeada.
- Regra 23 e perfil `offline-strict`: nenhuma chamada de rede no pacote.
- Regra 26: a tool nova move o `surface.lock` e os 7 registros manuais.
- A saida escreve so sob `--repo`, com nomes fixos.
- Limites do GitHub: 5 000 resultados exibidos por run e 10 MB compactado; acima disso a recusa tem de ser nomeada, nunca truncamento calado.
- Um dominio novo em `fixtures/` exige modulo golden (`test_fixtures_kind_coverage.py`).

### Out of Scope (Confirmed)
- Tudo o que esta na tabela YAGNI acima.
- Mudar `Finding`, os schemas das tools existentes ou o catalogo.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 9 (5 de discovery, 1 de abordagem, 1 de YAGNI, 2 de validacao) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 9 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_SARIF_GITHUB_CHECK.md`
