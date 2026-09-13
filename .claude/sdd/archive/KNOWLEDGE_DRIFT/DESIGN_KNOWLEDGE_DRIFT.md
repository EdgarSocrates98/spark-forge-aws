# DESIGN: Knowledge Drift Radar

> Technical design for implementing the Knowledge Drift Radar (§17 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_DRIFT |
| **Date** | 2026-09-13 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_KNOWLEDGE_DRIFT.md](./DEFINE_KNOWLEDGE_DRIFT.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ lock (carregar_lock: knowledge_dir() | SPARKFORGE_SOURCES_LOCK)       │
│ catalogo (load_catalog)   secoes Fontes (fontes_de_knowledge)          │
│ raiz do repo? ── build_index(root) ─► RepoIndex(goldens, evals,        │
│                   (iter_source_files)            agentes, areas)       │
│        │                                   │                           │
│        └────────────► drift(...) ◄─────────┘   (funcao pura)          │
│                          │                                             │
│   por URL com changed_at (nao pinned):                                 │
│     citacoes (regra|doc) + estado de knowledge_freshness.estado        │
│     stale -> impacto: regras, docs, goldens, evals, agentes            │
│     revalidada -> total, fora do impacto                               │
│                          │                                             │
│      ┌───────────────────┼──────────────────────┐                      │
│      ▼                   ▼                      ▼                      │
│ CLI knowledge drift   tool sparkforge_       refresh_knowledge.py      │
│ [--url] [--as-of]     knowledge_drift        render_report(+Impacto)   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/knowledge_drift.py::build_index` | Le goldens, evals e agentes da raiz do repositorio pela porta da casa | `iter_source_files`, PyYAML |
| `sparkforge/knowledge_drift.py::drift` | Funcao pura: citacoes com estado e impacto por URL mudada | `knowledge_freshness.estado` |
| `sparkforge/knowledge_drift.py::render_markdown` | A secao "Impacto" do relatorio do refresh | texto |
| `_core.knowledge_drift` + CLI + tool | Carrega lock, catalogo, fontes e raiz; chama `drift` | adapters existentes |
| `scripts/refresh_knowledge.py` | Acrescenta a secao ao relatorio do PR | a mesma funcao |

---

## Key Decisions

### Decision 1: Uma funcao pura, e o indice do repositorio montado a parte

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** O mesmo calculo serve o verbo, a tool e o relatorio do refresh (G7). O script roda com o lock NOVO em memoria, antes de grava-lo; o verbo, com o lock em disco.

**Choice:** `drift(lock, motivo_lock, rules, doc_citations, index, as_of, url=None) -> dict` nao le disco. Quem chama monta: `lock` (mapa ou `None` com o motivo), `rules` (o catalogo), `doc_citations` (o `por_doc` de `fontes_de_knowledge`) e `index` (`RepoIndex` de `build_index(root)`, ou `None` fora do repositorio).

**Rationale:** o script passa o lock que acabou de conferir; o teste passa lock sintetico sem variavel de ambiente; o `sem_repositorio` e so `index=None`.

**Alternatives Rejected:**
1. Funcao que le o lock sozinha -- rejeitado: o refresh teria de gravar o lock antes de relatar.
2. Uma funcao so com leitura de repositorio embutida -- rejeitado: o caso `sem_repositorio` so seria testavel apagando diretorio.

**Consequences:** o adapter e o script repetem a montagem (quatro linhas cada).

---

### Decision 2: Estado por citacao pelo `estado` que ja existe; o gatilho e `changed_at`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** fonte mudada = entrada do lock com `changed_at` e `pinned` falso. Para cada citacao (regra: `sources[].url` do catalogo; documento: `por_doc[doc][url]`), o estado vem de `knowledge_freshness.estado(url, retrieved, lock, as_of)`. `stale` entra no impacto; qualquer outro estado numa fonte com `changed_at` e `revalidated` (o `retrieved` alcancou a mudanca), no total e fora do impacto. Documento com varias datas para a mesma URL usa a mais antiga, como `mapa` ja faz.

**Rationale:** um calculo de estado so no pacote; a regra de precedencia da freshness vale igual aqui.

**Alternatives Rejected:** comparar datas no radar -- rejeitado: segunda implementacao da mesma regra, que diverge em silencio.

---

### Decision 3: Saltos so por arquivo, e a raiz do repositorio pela mesma precedencia de `catalog_dir()`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** `build_index(root)` le, por `iter_source_files` (glob cru e proibido em `sparkforge/`):
- goldens: `fixtures/**/findings.json` cujo pai e `expected`; o golden e `dominio/caso`;
- evals: todo arquivo de texto em `evals/` que cita um `rule_id` (regex `\b[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}\b`, o mesmo formato do schema);
- agentes: `agents/**/*.md`, com `rule_areas` do frontmatter e os `rule_id` citados no corpo.

A area de uma regra e o prefixo ate o ultimo hifen (A-001, o mesmo de `root_cause`). A raiz e `Path(__file__).parents[1]` quando ali existem `fixtures/`, `evals/` e `agents/`; senao `None` e os tres saltos saem `unresolved` com `sem_repositorio` (o wheel so leva `sparkforge`, `rules/catalog` e `knowledge`).

**Rationale:** medido: a varredura dos tres diretorios custa 287 ms, perto dos ~810 ms do `load_catalog`; sem cache.

**Alternatives Rejected:** variavel de ambiente para a raiz -- rejeitado: nenhum consumidor pediu, e o repositorio e a unica raiz com esses diretorios.

---

### Decision 4: Uma tool READ_ONLY sem caminho, subcomando do `knowledge` na CLI

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** CLI `sparkforge knowledge drift [--url U] [--as-of AAAA-MM-DD]` (grupo `knowledge` existente, despacho `("knowledge", "drift")`). Tool `sparkforge_knowledge_drift`, `_READ_ONLY`, entradas `url` e `as_of`, nenhuma de caminho: entra em `SEM_CAMINHO`. Tools 93 -> 94; READ_ONLY 61 -> 62; as que declaram caminho continuam 86. Dono: `agents/executors/sf-verifier.md` (a checagem 6 ja pede o estado das fontes). `--url` que o lock nao vigia: erro com codigo 2.

**Rationale:** o lock e conhecimento versionado que viaja no pacote, como a matriz de Lake Formation; nao ha caminho que o chamador escolha.

---

### Decision 5: A secao "Impacto" do refresh e renderizada pela mesma saida

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** medido: `refresh_knowledge.py --offline` sai cedo e nao gera relatorio; so o caminho com rede chama `render_report`.

**Choice:** `render_report(events, entries, today, impacto=None)` acrescenta `knowledge_drift.render_markdown(impacto)` quando dado. No `main` com rede, `impacto = drift(...)` sobre o lock NOVO devolvido por `compare`, limitado as URLs dos eventos `changed`. O AT-009 do DEFINE passa a testar `render_report` com o impacto do lock sintetico (o caminho offline nao gera relatorio).

**Consequences:** o PR semanal lista impacto so quando o workflow voltar a abrir PR (pre-requisito do operador).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/knowledge_drift.py` | Create | `RepoIndex`, `build_index`, `drift`, `render_markdown` | (general) | None |
| 2 | `tests/test_knowledge_drift.py` | Create | Estados, saltos, `sem_repositorio`, pinned, documento, recusa | (general) | 1 |
| 3 | `sparkforge/adapters/_core.py` | Modify | `knowledge_drift(url, as_of)` | (general) | 1 |
| 4 | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py` | Modify | `knowledge drift`; tool com schema proprio | (general) | 3 |
| 5 | `scripts/refresh_knowledge.py` | Modify | `render_report(..., impacto)` e o calculo no `main` | (general) | 1 |
| 6 | `fixtures/knowledge_drift/` + `tests/test_fixtures_golden_knowledge_drift.py` | Create | Locks sinteticos e golden pela CLI | (general) | 4 |
| 7 | Registros (lista, amostra, `SEM_CAMINHO`, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity, `sf-verifier` + sync) | Modify | Tool nova | (general) | 4 |
| 8 | `docs/knowledge-freshness.md`, STATUS, contagens, surface, claims | Modify | Radar e pre-requisito do operador | (general) | 7 |
| 9 | `.claude/sdd/reports/BUILD_REPORT_KNOWLEDGE_DRIFT.md` | Create | Relatorio | (general) | 8 |

**Total Files:** ~18 (contando os casos de fixture)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| (general) | 1-9 | Nenhum agente do plugin cobre proveniencia de conhecimento nem a superficie MCP deste repositorio; build direto, como nas frentes anteriores |

**Agent Discovery:** scanned `${CLAUDE_PLUGIN_ROOT}/agents/**/*.md`; o dono de produto e `sf-verifier`, que nao e agente de build.

---

## Code Patterns

### Pattern 1: Citacoes de uma fonte mudada

```python
from sparkforge.knowledge_freshness import estado


def citacoes(url, rules, doc_citations, lock, as_of):
    saida = []
    for regra in rules:
        datas = [s.get("retrieved") for s in regra.get("sources") or [] if s.get("url") == url]
        if datas:
            e = estado(url, min(str(d) for d in datas), lock, as_of)
            saida.append({"kind": "rule", "id": regra["id"], "retrieved": min(map(str, datas)),
                          "state": e.state, "reason": e.reason})
    for doc, por_url in doc_citations.items():
        if url in por_url:
            validado = min(por_url[url])
            e = estado(url, validado, lock, as_of)
            saida.append({"kind": "doc", "id": doc, "retrieved": validado,
                          "state": e.state, "reason": e.reason})
    return saida
```

### Pattern 2: Saida

```json
{
  "as_of": "2026-09-13",
  "lock": {"sources": 247, "checked": 21, "pinned": 15, "changed": 1},
  "changed_sources": [
    {
      "url": "https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html",
      "changed_at": "2026-09-09",
      "citations": [{"kind": "rule", "id": "SF-LF-001", "retrieved": "2026-08-22", "state": "stale"}],
      "revalidated": ["SF-ERR-017"],
      "impact": {"rules": [], "docs": [], "goldens": [], "evals": [], "agents": []}
    }
  ],
  "totals": {"rules": 0, "docs": 0, "goldens": 0, "evals": 0, "agents": 0},
  "unresolved": [],
  "refused": [{"field": "conteudo_da_mudanca", "reason": "exige_leitura_humana_da_fonte"}]
}
```

### Pattern 3: Lock sintetico de fixture

```json
{"schema_version": 1, "sources": {
  "https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html": {
    "changed_at": "2026-09-09", "checked_at": "2026-09-09", "sha256": "sintetico",
    "pinned": false, "rules": [], "docs": []}}}
```

---

## Data Flow

```text
1. Adapter: carregar_lock(knowledge_dir()) -> (lock, motivo); load_catalog(); fontes_de_knowledge(); build_index(raiz) ou None
2. drift(): fontes com changed_at e nao pinned (filtradas por --url)
3. Por fonte: citacoes com estado; stale -> impacto (regras, docs; goldens/evals/agentes pelo indice)
4. Totais distintos, unresolved (lock_ausente | sem_repositorio), refused fixo
5. CLI imprime; tool devolve; refresh anexa render_markdown ao relatorio
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Sistema de arquivos do repositorio | Leitura por `iter_source_files` | N/A |
| GitHub Actions (`refresh-knowledge.yml`) | Sem mudanca; o relatorio ganha a secao | Permissao de criar PR e do operador |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | `drift` com lock e indice sinteticos: stale, revalidada, pinned, documento, recusa, `sem_repositorio`, lock ausente | `tests/test_knowledge_drift.py` | pytest | AT-002, AT-003, AT-005..AT-008, AT-010 |
| Integration | `build_index` sobre o repositorio real conferido contra grep | `tests/test_knowledge_drift.py` | pytest | SC3 |
| E2E | CLI com `SPARKFORGE_SOURCES_LOCK` sintetico; `--url`; lock real | `tests/test_fixtures_golden_knowledge_drift.py` | pytest | AT-001, AT-002, AT-004 |
| Refresh | `render_report` com impacto | `tests/test_refresh_knowledge.py` (existente) | pytest | AT-009 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Lock ausente ou ilegivel | `unresolved` com o motivo de `carregar_lock`; sem erro | No |
| `--url` fora do lock | `AdapterError` codigo 2 | No |
| Fora do repositorio | `unresolved` `sem_repositorio` nos tres saltos | No |
| Frontmatter de agente ilegivel | O agente entra so pelas citacoes do corpo | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `SPARKFORGE_SOURCES_LOCK` | caminho (existente) | ausente | Lock avulso, ja respeitado por `carregar_lock` |

---

## Security Considerations

- Nenhuma rede no verbo; so leitura de arquivo do repositorio, pela porta com denylist.
- Tool sem parametro de caminho.
- Conteudo de eval e agente e lido so para casar `rule_id`; nada e executado.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum; a resposta traz `unresolved` e `refused` |
| Metrics | O span de `call_tool` da tool nova |
| Tracing | N/A |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | design-agent | Versao inicial. A-002 confirmada (`por_doc`, 28 documentos); A-003 confirmada (287 ms); A-005 revista: o refresh offline nao gera relatorio, e o AT-009 passa a testar `render_report` direto |
| 1.1 | 2026-09-13 | ship-agent | Shipped and archived (PR #60). Desvios do build: filtro `source` em vez de `url` (INV-009); o golden fixa a raiz do repositorio (gate de wheel) |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_KNOWLEDGE_DRIFT.md`
