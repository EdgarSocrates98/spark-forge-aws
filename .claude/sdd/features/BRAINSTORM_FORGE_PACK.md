# BRAINSTORM: Forge Pack

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FORGE_PACK |
| **Date** | 2026-09-12 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** §5 de `prompt_new_evo.md`: "Criaria imediatamente o conceito de **Forge Pack**". Um pack declara `facts`, `collectors`, `rules`, `knowledge`, `agents`, `skills`, `evals`, `capabilities`, `dependencies`, `compatibility`, `security` e `sources`, e se instala por `forge pack install spark-aws`. "O sistema central continua pequeno e confiavel." O §31 poe "Formalizacao do Forge Pack specification" no P0 (item 8) e o "Forge Pack SDK / registry" no P3; o §33 poe "Forge Pack architecture / SDK" como item 1 do TOP 10.

**Context Gathered:**
- Nao existe pack hoje. `rules/catalog/` e `knowledge/` moram na raiz e entram no wheel por `force-include` (`pyproject.toml`, decisao D-A da Fase 0). A leitura e de UMA raiz: `catalog_dir()` e `knowledge_dir()` resolvem variavel de ambiente -> raiz do repo -> pacote (`sparkforge/rules/loader.py:41`, `sparkforge/knowledge_ref.py:25`).
- Medido: **42** chamadas a `catalog_dir()`/`knowledge_dir()` em **17** arquivos, e **54** a `load_catalog(` em **12** (30 em `scripts/regen_fixtures.py`, 6 em `scripts/check_evals.py`, 9 em `adapters/_core.py`).
- O loader ja recusa `id` duplicado entre arquivos (`loader.py:329`) e tem `_REQUIRED`; `action` recusa chave desconhecida.
- Extratores sao descobertos por varredura de `EMITTED_KINDS` em `sparkforge.facts` (`diagnosis/root_cause.py::_modulo_por_kind`).
- `sparkforge/registry/` (ADR-001) existe, mas e outra coisa: manifestos de agente/skill/tool/time lidos de `config/*.yaml` para os compiladores de plataforma. Nao carrega regra nem knowledge.
- `sparkforge/cli/forge.py` ja declara `prog="forge"` (doctor, inspect), mas nenhum script `forge` esta em `[project.scripts]`.
- Area sem rota nao quebra: `case/router.py::next_step` cai no `fallback` do `routing.yaml`. A exigencia de rota e coordenador (`tests/test_agent_coverage.py`) cobre as areas do core.
- Freshness le um lock so: `knowledge_dir()/sources.lock.json` (`knowledge_freshness.py:53`, `carregar_lock`).
- `Finding` nao tem campo de origem; tem `catalog_version`. Nao ha `__version__` em `sparkforge/`: a versao mora no `pyproject.toml` (0.5.0) e em `manifest.json`.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/packs/` (modulo puro), `rules/loader.py`, `knowledge_ref.py`, `knowledge_freshness.py`, `adapters/{_core,cli,tools}.py`, `fixtures/packs/` | Carga em varias raizes nos loaders que ja existem; verbo novo de topo |
| Relevant KB Domains | Nenhum dominio do KB do agentspec cobre empacotamento ou registro (o indice tem dbt, spark, airflow...). Fonte e o proprio repositorio | Define se apoia no codigo medido acima |
| IaC Patterns | N/A | Nada de infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual e o objetivo principal do Forge Pack nesta frente? (estender / formalizar / distribuir) | **Estender**: um segundo pack carregado junto do core, sem fork, com a spec do manifesto dentro | A spec sozinha nao basta; o core precisa CARREGAR de mais de uma raiz |
| 2 | O que um pack de terceiro pode trazer? (so dado / dado e extrator / dado, extrator e tool) | **So dado**: regras YAML, knowledge e fixtures; as regras consomem kinds que o core ja emite | Nenhum codigo de terceiro e importado; a superficie de tools e a cadeia de autorizacao nao mudam por pack |
| 3 | Como o core encontra e ativa um pack? (variavel / case / flag) | **Variavel de ambiente** `SPARKFORGE_PACKS`, no molde de `SPARKFORGE_CATALOG` | Todo verbo ve o mesmo conjunto, inclusive os sem case; a MCP recebe pelo `.mcp.json` |
| 4 | Como as regras do pack convivem com as 190 do core? (prefixo proprio / area do core / sobrescrever) | **Prefixo proprio** declarado no pack; `SF-` reservado ao core; id repetido recusado | Colisao com o core e impossivel por construcao; o core continua previsivel |
| 5 | Que amostra ancora o primeiro pack? (sintetico / regras internas / extrair do core) | **Pack sintetico** em `fixtures/packs/` | Repo publico: nada de regra real de empresa |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | Facts de fixtures do core (`fixtures/terraform/*`, `fixtures/pyspark/*`) | a escolher no design | As regras do pack sintetico consomem `tf.attribute`, `pyspark.*` ja emitidos |
| Output examples | `fixtures/**/expected/findings.json` | 400+ | Forma do finding que a regra de pack tem que produzir |
| Ground truth | O pack sintetico com fixtures que disparam cada regra dele | a criar (2-3 regras) | O `pack check` prova o pack pelo mesmo contrato dos goldens |
| Related code | `rules/loader.py` (`catalog_dir`, `safe_catalog_file`, `load_catalog`), `knowledge_ref.py`, `paths.resolve_within`, `knowledge_freshness.py` | 4 | Contencao de caminho, id duplicado e resolucao por variavel ja existem |

**How samples will be used:**

- O pack sintetico `fixtures/packs/acme-platform/` e o golden de ponta a ponta: carregado pela variavel, julgado, listado e checado.
- Os facts de fixtures do core sao a entrada das regras do pack, sem fact novo.
- Packs quebrados de proposito (prefixo `SF`, id fora do prefixo, id duplicado, core incompativel) sao os casos de recusa.

---

## Approaches Explored

### Approach A: Varias raizes nos loaders ⭐ Recommended

**Description:** Modulo `sparkforge/packs/` le `SPARKFORGE_PACKS` e o `pack.yaml` de cada diretorio, valida e devolve os packs ativos e os recusados. `load_catalog()` passa a devolver core + regras dos packs ativos; `knowledge_path` lista `packs/<id>/<arquivo>`; a freshness da regra de pack le o lock do proprio pack. Verbo `sparkforge pack list|check` com tool READ_ONLY.

**Pros:**
- Segue o molde que ja existe (`SPARKFORGE_CATALOG`, `catalog_dir()`, contencao por `resolve_within`, recusa de id duplicado).
- Todo verbo e toda tool veem o pack sem parametro novo.
- A origem do finding sai do prefixo do `rule_id`, sem campo novo e sem mexer em golden.

**Cons:**
- 54 chamadas de `load_catalog` passam a depender do ambiente; gates e CI precisam rodar sem a variavel (o padrao).
- Freshness e knowledge ganham uma segunda fonte de verdade por pack.

**Why Recommended:** e a unica que cumpre "estender" com o core pequeno, e cada peca tem precedente medido no codigo (confianca 0,80: padrao do codebase, sem precedente de varias raizes).

---

### Approach B: Merge por comando

**Description:** `sparkforge pack merge` escreve um catalogo mesclado para onde `SPARKFORGE_CATALOG` aponta; o loader nao muda.

**Pros:**
- Nenhuma mudanca no carregamento.

**Cons:**
- A copia derivada envelhece e perde a origem de cada regra.
- Ativar vira dois passos, e knowledge e lock precisariam de merge proprio.

---

### Approach C: Pack julgado a parte

**Description:** `judge --pack <dir>` avalia so as regras do pack.

**Pros:**
- Risco zero no carregamento do core.

**Cons:**
- A MCP e os verbos de topo (`root_cause`, `proof`, `simulate`) nao veem o pack; nao estende nada.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-12, nesta sessao |
| **Reasoning** | Unica que estende sem fork e mantem o core previsivel; reusa contencao, resolucao por variavel e recusa de id que ja existem |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Pack e so dado (regras, knowledge, fixtures) | Importar Python de terceiro no processo da MCP e executar codigo nao revisado | Extrator e tool por pack |
| 2 | Ativacao por `SPARKFORGE_PACKS` (lista separada por `os.pathsep`) | Mesmo molde de `SPARKFORGE_CATALOG`; vale para verbos sem case | Declarado no case; flag por comando |
| 3 | Prefixo proprio; `SF` reservado; id duplicado recusado | Colisao com o core impossivel por construcao | Entrar em area do core; sobrescrever regra |
| 4 | Pack recusado sai inteiro, com motivo nomeado, visivel em `pack list` | Carga parcial daria resultado que ninguem consegue explicar (regra 20) | Carregar as regras validas e pular as outras |
| 5 | Sem a variavel, `load_catalog()` e byte a byte o de hoje | Gates, CI e goldens nao mudam | Pack embutido ativo por padrao |
| 6 | Finding sem campo novo: o prefixo do `rule_id` identifica o pack | Nenhum golden muda; `pack list` publica o mapa prefixo -> pack | `Finding.pack` |
| 7 | Pack nao declara rota; area de pack cai no `fallback` | Rota para coordenador exigiria validar agente, que saiu do escopo | `routes:` no pack |
| 8 | Lock de fontes opcional no pack; sem ele, fonte `unresolved` com `pack_sem_lock` | Freshness sem lock seria afirmar estado que ninguem vigia | Vigiar URL de pack no lock do core |
| 9 | Compatibilidade declarada em `core:` e conferida contra `importlib.metadata.version("sparkforge-aws")` | Nao ha `__version__` no pacote | Constante nova duplicando o `pyproject` |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Extractors e collectors de pack | Importar codigo de terceiro (pergunta 2) | Yes, com politica de confianca |
| MCP tools, agents, skills de pack | Mexem na superficie travada e no despacho; nenhum dado precisa deles | Yes |
| `forge pack install`, registry, packs assinados | Distribuicao; o objetivo e estender com pack ja no disco | Yes (P3 do §31) |
| Dependencia entre packs e resolvedor | Pack consome kinds do core, nao de outro pack | Yes |
| Sobrescrever regra do core | Resultado imprevisivel para quem nao sabe do pack (pergunta 4) | No |
| Rota de pack para coordenador | Exigiria validar agente (decisao 7) | Yes |
| A2A capabilities, migrations, source-watchers | Plataforma, fora do pacote | Yes |
| Script `forge` em `[project.scripts]` | O verbo mora na CLI `sparkforge` que ja existe; `forge.py` e outra superficie | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura: modulo `packs/`, carga pela variavel, finding sem campo novo, knowledge sob `packs/<id>/`, `pack list|check` | ✅ | "Sim, segue" | No |
| Corte: fora da frente, sem rota de pack, lock opcional com `pack_sem_lock` | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Uma equipe que quer regras e knowledge proprios sobre os mesmos artefatos precisa hoje de fork do SparkForge, porque o core le regras e knowledge de uma raiz so.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Equipe de plataforma de dados de uma empresa | Padroes internos (tags obrigatorias, convencao de worker, bibliotecas proibidas) viram fork ou revisao manual |
| Mantenedor do SparkForge | Todo pedido de regra especifica de empresa vira regra no core, e o core cresce |
| Agente host (Claude Code, Devin) via MCP | Precisa ver as regras do pack sem parametro novo em cada tool |

### Success Criteria (Draft)
- [ ] Sem `SPARKFORGE_PACKS`, `load_catalog()`, `knowledge_path` e todos os goldens ficam byte a byte.
- [ ] Com o pack sintetico ativo, `judge` sobre os facts de um fixture do core produz o finding `ACME-*` esperado, e `root_cause`/`simulate` o enxergam.
- [ ] Cada recusa (`prefixo_reservado`, `id_fora_do_prefixo`, `id_duplicado`, `core_incompativel`, `pack_duplicado`, manifesto invalido) tem pack de fixture e sai em `pack list` com o motivo; nenhuma regra do pack recusado entra.
- [ ] `pack check <dir>` roda os fixtures do pack pelo `judge` e falha quando uma regra do pack nao dispara no fixture dela.
- [ ] Knowledge do pack e servido confinado ao diretorio do pack; caminho com `..` recusado.
- [ ] Freshness de fonte de regra de pack le o lock do pack; sem lock, `unresolved` com `pack_sem_lock`.

### Constraints Identified
- Nenhum `import` de codigo de pack (so leitura de YAML/Markdown/JSON).
- Contencao de caminho por `sparkforge.paths.resolve_within`, como em `safe_catalog_file`.
- CI e gates rodam sem a variavel; `check_status_numbers` continua contando 190 regras.
- Tool nova move os registros manuais (lista literal, amostra, formas de erro, contagem de caminho, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity, coordenador, surface lock, claims, status).
- Regra 23: nada chama provider.

### Out of Scope (Confirmed)
- Extrator, collector, tool, agente e skill de pack.
- Instalar, publicar, assinar ou resolver dependencia de pack.
- Sobrescrever regra do core; rota de pack.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_FORGE_PACK.md`
