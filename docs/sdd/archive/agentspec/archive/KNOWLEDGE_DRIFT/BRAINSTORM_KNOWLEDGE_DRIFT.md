# BRAINSTORM: Knowledge Drift Radar

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_DRIFT |
| **Date** | 2026-09-13 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** §17 de `prompt_new_evo.md`: transformar conhecimento em cadeia de fornecimento (fonte oficial -> snapshot -> claim -> verificacao -> no de conhecimento -> grafo de dependencia de regras -> testes -> pack publicado) e, quando uma documentacao externa mudar, responder "que claims mudaram? que regras dependem delas? que evals precisam rodar de novo?" -- o **Knowledge Drift Radar**. O §18 (freshness computavel) ja foi entregue em 2026-09-11 (PR #53).

**Context Gathered:**
- `knowledge/sources.lock.json` tem **247** fontes; cada entrada ja carrega `rules` (ids que a citam) e `docs` (paginas de `knowledge/`). **21** foram conferidas por hash (`sha256`, `checked_at`); **0** tem `changed_at`; **15** sao fixas por versao. O primeiro salto do grafo (fonte -> regras e docs) ja existe no lock.
- `scripts/refresh_knowledge.py::render_report` ja lista, por URL que mudou, as regras e as paginas que a citam e o `retrieved` declarado.
- **O refresh semanal falha desde 2026-08-10, cinco execucoes seguidas.** A conferencia roda e o commit do lock e feito; o passo do PR quebra com `pull request create failed: GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)` -- configuracao do repositorio (Settings -> Actions -> General). As paginas da BMC devolvem 403 e o script as marca ilegiveis, sem tratar como "nao mudou".
- `sparkforge/knowledge_freshness.py` ja calcula o estado de uma citacao (`estado`, `mapa`, `carregar_lock` com `SPARKFORGE_SOURCES_LOCK`, `fontes_de_knowledge`) e o script do refresh importa dele.
- Ligacoes que existem em arquivo: evals citam `rule_id` 57 vezes em 12 arquivos; agentes, 50 vezes em 13 arquivos, e declaram `rule_areas` (lido por `sparkforge/case/playbook.py`); skills nao citam `rule_id`. Regra -> golden e o `expected/findings.json` de cada fixture (`tests/test_fixtures_kind_coverage.py::_rules_fired_in_goldens`, so em teste).
- O wheel leva `sparkforge`, `rules/catalog` e `knowledge` (`pyproject.toml`). `fixtures/`, `evals/` e `agents/` NAO vao no pip install.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/knowledge_drift.py` (novo), `scripts/refresh_knowledge.py`, `adapters/{_core,cli,tools}.py`, `docs/knowledge-freshness.md` | Modulo puro ao lado de `knowledge_freshness.py`; duas portas |
| Relevant KB Domains | Nenhum dominio do KB do agentspec cobre proveniencia de conhecimento; a fonte e o proprio repositorio | Padroes: `knowledge_freshness`, `_rules_fired_in_goldens`, `playbook` |
| IaC Patterns | GitHub Actions (`refresh-knowledge.yml`) | O workflow nao muda; a permissao de abrir PR e configuracao do operador |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual o objetivo desta frente? (drift radar / claims com citacao / so destravar o refresh) | **Drift Radar**: quando uma fonte muda de hash, dizer o que ela arrasta | Granularidade de pagina, nao de afirmacao; nada de reescrever as 267 citacoes |
| 2 | Onde o radar entrega? (verbo + refresh / so refresh / so verbo) | **Verbo + relatorio do refresh**, uma funcao, duas portas | Tool READ_ONLY nova; o PR semanal ganha a secao de impacto |
| 3 | Ate onde o radar segue? (tudo medido / regras e goldens / ate agentes) | **Tudo que e medido**: regras, docs, goldens, evals e agentes, so por ligacao que existe em arquivo | Nenhuma ligacao inferida; o que o wheel nao leva sai `unresolved` |
| 4 | Que amostra ancora os testes? (lock sintetico / refresh com rede / os dois) | **Lock sintetico** apontado por `SPARKFORGE_SOURCES_LOCK` | Golden deterministico sobre o catalogo, goldens, evals e agentes reais |
| 5 | Qual abordagem? (A calculado na leitura / B indice versionado) | **A** | Nenhum arquivo derivado novo para envelhecer |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `knowledge/sources.lock.json` + um lock sintetico com `changed_at` | 247 fontes reais | O sintetico marca mudanca depois do `retrieved` de algumas regras reais |
| Output examples | `scripts/refresh_knowledge.py::render_report` | 1 | Forma atual do relatorio; o radar acrescenta a secao de impacto |
| Ground truth | `fixtures/*/*/expected/findings.json`, `evals/**`, `agents/*.md` | 432 fixtures, 12 arquivos de eval, 13 agentes com `rule_id` | O impacto esperado e conferivel por grep |
| Related code | `sparkforge/knowledge_freshness.py`, `tests/test_fixtures_kind_coverage.py`, `sparkforge/case/playbook.py`, `fixtures/sarif/freshness` | 4 | Estado por citacao, regra -> golden, `rule_areas`, lock sintetico em golden |

**How samples will be used:**

- Golden do verbo sobre o lock sintetico e o repositorio real.
- Um caso sem repositorio (raiz ausente) para provar o `unresolved` nomeado.
- O relatorio do refresh gerado offline com o mesmo lock, conferido contra o verbo.

---

## Approaches Explored

### Approach A: Calculado na leitura ⭐ Recommended

**Description:** `sparkforge/knowledge_drift.py` recebe lock, catalogo, secoes `Fontes` e a raiz do repositorio (opcional). Para cada URL com `changed_at`, pega as citacoes (regras e docs), da a cada uma o estado de `knowledge_freshness.estado`, e para cada regra `stale` segue os saltos por arquivo: goldens, evals, agentes. Sem raiz de repositorio, os tres saltos saem `unresolved` (`sem_repositorio`). Verbo `sparkforge knowledge drift`, tool `sparkforge_knowledge_drift`, e a secao "Impacto" do PR do refresh, todos pela mesma funcao.

**Pros:**
- Reusa o calculo de estado que ja existe e que o script ja importa.
- Nenhum arquivo derivado: o impacto e sempre o do repositorio de agora.

**Cons:**
- Instalado por pip, so o primeiro salto (regras e docs) responde.
- Varre `fixtures/` e `evals/` a cada chamada.

**Why Recommended:** e o molde de `knowledge_freshness` (calculado na leitura, nunca gravado), e a memoria do projeto registra o defeito de numero publicado que ninguem recalcula.

---

### Approach B: Indice versionado

**Description:** Script gera `knowledge/drift_index.json` (regra -> goldens, evals, agentes), gate trava, vai no wheel.

**Pros:**
- Responde instalado.

**Cons:**
- Mais um arquivo derivado a manter em dia, com gate proprio.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-13, nesta sessao |
| **Reasoning** | Mesmo molde de `knowledge_freshness`; nada gravado que envelheca |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Gatilho e `changed_at` no lock; citacao e `stale` quando `retrieved` < `changed_at` | E o estado que `knowledge_freshness` ja calcula | Recalcular hash no radar |
| 2 | Citacao ja relida (`retrieved` >= `changed_at`) conta no total, fora do impacto | Mostra que alguem releu sem pedir releitura de novo | Omiti-la |
| 3 | Saltos so por ligacao em arquivo: `expected/findings.json`, `rule_id` citado em `evals/`, `rule_areas` e citacao em `agents/` | Nada inferido | Similaridade de texto |
| 4 | Sem raiz de repositorio, goldens/evals/agentes saem `unresolved` com `sem_repositorio` | Lista vazia pareceria "nada afetado" (regra 20) | Omitir os saltos |
| 5 | `refused` fixo: o radar nao diz se a mudanca tocou o trecho citado | Exige leitura humana, ou claim com citacao, que ficou fora | Heuristica de diff |
| 6 | O workflow do refresh nao muda; a permissao de abrir PR e documentada como pre-requisito do operador | O defeito e configuracao, nao codigo | Mudar o workflow |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Claim com `quote_hash`, `valid_from`/`valid_until`, `supersedes`/`conflicts_with` | Granularidade de afirmacao, descartada na pergunta 1 | Yes |
| Snapshot da fonte guardado | O lock guarda hash, nao conteudo | Yes |
| Rodar os evals afetados | O radar lista; rodar e do host (regra 23) | Yes |
| PR automatico | Ja existe; barrado pela configuracao do repositorio | N/A |
| Estados `deprecated`/`superseded` | Nenhuma fonte os declara hoje | Yes |
| Indice versionado | Abordagem B | Yes |
| Mudar o workflow para detectar o "not permitted" | O conserto e a configuracao; documentar basta | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura: modulo puro, gatilho `changed_at`, cinco saltos, `unresolved` fora do repo, recusa, tres portas | ✅ | "Sim, segue" | No |
| Corte: YAGNI, workflow sem mudanca, citacao ja relida fora do impacto | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Quando uma fonte oficial muda, o SparkForge sabe quais regras e documentos a citam, mas nao diz que goldens provam essas regras, que evals as exercitam nem que agentes as usam -- e o refresh que detectaria a mudanca nao abre PR desde 2026-08-10.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Mantenedor do catalogo | Uma fonte muda e ele descobre a mao o que precisa reler e rodar de novo |
| Revisor do PR semanal do refresh | O PR lista URLs; nao diz o tamanho do impacto |
| Agente host via MCP | Nao consegue perguntar "o que esta fonte arrasta" |

### Success Criteria (Draft)
- [ ] Com o lock sintetico, o verbo lista, por URL mudada, as citacoes com estado e o impacto em regras, docs, goldens, evals e agentes, conferivel por grep.
- [ ] Sem raiz de repositorio, goldens/evals/agentes saem `unresolved` com `sem_repositorio`.
- [ ] O relatorio do refresh e o verbo, sobre o mesmo lock, dao o mesmo impacto.
- [ ] Sem `changed_at` no lock (o estado real de hoje), o verbo responde vazio com a contagem de fontes conferidas e nao conferidas.

### Constraints Identified
- Nenhuma rede no verbo; o refresh continua sendo o unico ponto com rede.
- O wheel nao leva `fixtures/`, `evals/`, `agents/`.
- Regra 23: nada chama provider.
- Tool nova move os registros manuais.

### Out of Scope (Confirmed)
- Claims com citacao, snapshot, estados novos, rodar evals, indice versionado.
- Mudar o workflow do refresh ou a configuracao do repositorio.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 7 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_KNOWLEDGE_DRIFT.md`
