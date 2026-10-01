# DEFINE: Knowledge Drift Radar

> Quando uma fonte oficial vigiada muda de hash, dizer o que ela arrasta -- regras, docs de knowledge, goldens, evals e agentes -- so por ligacao que existe em arquivo, calculado na leitura.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_DRIFT |
| **Date** | 2026-09-13 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Quando uma pagina oficial que o SparkForge cita muda, o lock (`knowledge/sources.lock.json`) sabe quais regras e documentos a citam, mas ninguem responde a pergunta seguinte: que goldens provam essas regras, que evals as exercitam e que agentes as usam -- e portanto o que precisa ser relido e rodado de novo. Hoje o mantenedor faz essa conta a mao, e o revisor do PR semanal do refresh recebe uma lista de URLs sem o tamanho do impacto.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Mantenedor do catalogo | Relê fontes e atualiza `sources[].retrieved` das regras | Uma fonte muda e ele descobre a mao o que reler e o que rodar de novo |
| Revisor do PR semanal do refresh | Decide o que reler a partir do relatorio | O PR lista URLs; nao diz quantas regras, goldens, evals e agentes elas arrastam |
| Agente host via MCP | Explica achado e confianca ao operador | Nao consegue perguntar "o que esta fonte arrasta" fora do PR |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: modulo puro `sparkforge/knowledge_drift.py`: entrada = lock, catalogo, secoes `Fontes` de `knowledge/` e a raiz do repositorio (opcional); saida por URL com `changed_at` = as citacoes (regra ou documento) com o `retrieved` declarado e o estado de `knowledge_freshness.estado`, e o impacto |
| **MUST** | G2: citacao com `retrieved` anterior ao `changed_at` e `stale` e entra no impacto; citacao com `retrieved` igual ou posterior e `revalidada`, conta no total e fica FORA do impacto; URL fixa por versao (`pinned`) nunca entra |
| **MUST** | G3: impacto de cada regra `stale`, so por ligacao em arquivo: goldens (`fixtures/*/*/expected/findings.json` com o `rule_id`), evals (arquivo em `evals/` que cita o `rule_id`), agentes (`agents/**/*.md` que declara a area da regra em `rule_areas` OU cita o `rule_id`) |
| **MUST** | G4: sem raiz de repositorio (instalado por pip: o wheel so leva `sparkforge`, `rules/catalog` e `knowledge`), goldens, evals e agentes saem em `unresolved` com `sem_repositorio`; regras e docs continuam respondendo |
| **MUST** | G5: `refused` fixo com `conteudo_da_mudanca`: o radar nao diz se a mudanca tocou o trecho que a regra cita (exige leitura humana, ou claim com citacao, fora de escopo) |
| **MUST** | G6: CLI `sparkforge knowledge drift [--url U] [--as-of AAAA-MM-DD]` e tool `sparkforge_knowledge_drift` READ_ONLY, sem parametro de caminho (le o lock de `knowledge_dir()`/`SPARKFORGE_SOURCES_LOCK`) |
| **MUST** | G7: `scripts/refresh_knowledge.py` chama a MESMA funcao e acrescenta a secao "Impacto" ao relatorio do PR |
| **SHOULD** | G8: `docs/knowledge-freshness.md` ganha a secao do radar e registra o pre-requisito do operador: o refresh semanal falha desde 2026-08-10 porque o GitHub Actions nao pode criar PR no repositorio |
| **COULD** | G9: totais por URL e gerais (regras, docs, goldens, evals, agentes distintos) para o resumo do PR |

---

## Success Criteria

- [ ] SC1: sobre o lock real de hoje (247 fontes, 21 conferidas por hash, 0 com `changed_at`), o verbo devolve lista de fontes mudadas vazia, com as contagens de fontes, conferidas e fixas.
- [ ] SC2: com um lock sintetico que marca `changed_at: 2026-09-09` em `https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html` (citada por 12 regras, lida em 2026-08-22, 2026-09-09 e 2026-09-10), as citacoes lidas em 2026-08-22 saem `stale` e entram no impacto, e as de 2026-09-09 e 2026-09-10 saem revalidadas, fora dele.
- [ ] SC3: o impacto de SC2 e conferivel por grep: cada golden listado tem o `rule_id` no `expected/findings.json`, cada eval cita o `rule_id`, cada agente declara a area ou cita o id; e nenhum golden, eval ou agente com essa ligacao falta.
- [ ] SC4: sem raiz de repositorio, goldens, evals e agentes saem `unresolved` com `sem_repositorio`, e regras e docs sao os mesmos de SC2.
- [ ] SC5: o relatorio do refresh gerado offline com o lock sintetico traz a secao "Impacto" com os mesmos totais do verbo.
- [ ] SC6: tool nova validada por amostra real; registros de tool nova; surface lock com o crescimento declarado; claims por lista de ids; suite por lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Nada mudou | lock real (0 `changed_at`) | `sparkforge knowledge drift` | `changed_sources: []`, com as contagens do lock |
| AT-002 | Fonte mudou | lock sintetico de SC2 | `knowledge drift` | a URL com as citacoes e o impacto; `stale` so nas citacoes lidas antes de 2026-09-09 |
| AT-003 | Ja relida | a mesma URL, citacao lida em 2026-09-10 | `knowledge drift` | a citacao aparece como revalidada, e a regra dela nao entra no impacto |
| AT-004 | Filtro por URL | lock sintetico com duas URLs mudadas | `knowledge drift --url <uma>` | so a URL pedida; URL nao vigiada sai erro com codigo 2 |
| AT-005 | Fixa por versao | lock sintetico marca `changed_at` numa URL `pinned` | `knowledge drift` | a URL nao entra (estado `fixed`) |
| AT-006 | Documento | URL citada so por documento de `knowledge/` | `knowledge drift` | o documento sai como citacao, com o `retrieved` que ele declara |
| AT-007 | Sem repositorio | raiz de repositorio ausente | `knowledge drift` | goldens/evals/agentes em `unresolved` com `sem_repositorio` |
| AT-008 | Lock ausente | `SPARKFORGE_SOURCES_LOCK` para arquivo inexistente | `knowledge drift` | `unresolved` com `lock_ausente`/`lock_ilegivel`, sem erro |
| AT-009 | Relatorio do refresh | impacto calculado sobre o lock sintetico | `render_report(..., impacto)` | secao "Impacto" com os totais do verbo (o `--offline` nao gera relatorio; medido no design) |
| AT-010 | Recusa | qualquer lock | `knowledge drift` | `refused` com `conteudo_da_mudanca` |

---

## Out of Scope

- Claim com citacao (`claim_id`, `quote_hash`, `valid_from`/`valid_until`, `supersedes`/`conflicts_with`).
- Guardar snapshot da pagina da fonte.
- Rodar os evals ou goldens afetados (o radar lista; rodar e do host ou do CI).
- Estados `deprecated` e `superseded`.
- Indice versionado do grafo de impacto.
- Mudar o workflow `refresh-knowledge.yml` ou a configuracao do repositorio.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | O verbo nao acessa a rede; o refresh continua o unico ponto com rede | Tudo sai do lock e dos arquivos do repositorio |
| Technical | O wheel nao leva `fixtures/`, `evals/` nem `agents/` | Instalado, tres saltos saem `unresolved` |
| Technical | `glob` cru e proibido em `sparkforge/` (`tests/test_facts_scan.py`) | Varredura de `fixtures/`, `evals/` e `agents/` pela porta da casa (`iter_source_files`) |
| Technical | `.claude/` e diretorio de plataforma (`TestNoPlatformKnowledge`) | Documentos SDD sem as chaves de metadado de regra escritas com dois-pontos |
| Technical | Tool nova move os registros manuais | Tools 93 -> 94; READ_ONLY 61 -> 62; sem parametro de caminho (entra em `SEM_CAMINHO`) |
| Technical | Regra 23 | Nada chama provider |
| Resource | Pre-requisito do operador | Sem a permissao de o Actions criar PR, o radar funciona no verbo, mas o PR semanal nao sai |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/knowledge_drift.py` (novo), `scripts/refresh_knowledge.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `docs/knowledge-freshness.md`, `fixtures/knowledge_drift/` | Ao lado de `knowledge_freshness.py`, que ja faz o estado por citacao |
| **KB Domains** | Nenhum dominio do KB do agentspec cobre proveniencia de conhecimento | Padroes do repo: `knowledge_freshness`, `_rules_fired_in_goldens`, `playbook` (`rule_areas`), golden `fixtures/sarif/freshness` |
| **IaC Impact** | None | O workflow nao muda |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | A area de uma regra e o prefixo ate o ultimo hifen, e `rule_areas` dos agentes usa esse formato (medido: 38 de 43 agentes declaram `rule_areas`) | O salto regra -> agente por area erraria | [ ] |
| A-002 | O `retrieved` de uma citacao de documento sai de `fontes_de_knowledge` (data declarada por documento) | Documento sem data sairia sem estado | [ ] |
| A-003 | Varrer `fixtures/` (432 diretorios) e `evals/` a cada chamada custa pouco perto do `load_catalog` (~810 ms) | Precisaria de cache por processo | [ ] |
| A-004 | Medido: toda URL citada por regra (115) alcanca ao menos um golden; 16 alcancam eval | O caso sintetico escolhido teria impacto vazio | [x] |
| A-005 | `refresh_knowledge.py` roda do repositorio, com a raiz disponivel | O relatorio do PR sairia com `unresolved` | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Ligacao fonte -> regras medida no lock; o resto e conta a mao hoje |
| Users | 3 | Tres personas com dor concreta |
| Goals | 3 | MoSCoW, com estados e saltos definidos |
| Success | 3 | Caso sintetico nomeado com as datas reais; contagens do lock medidas |
| Scope | 2 | Fora de escopo explicito; o formato exato da secao do PR fica para o design |
| **Total** | **14/15** | |

---

## Open Questions

Nenhuma que bloqueie o design. Ficam para ele: o formato exato da saida (por URL e por regra), a forma da secao "Impacto" no PR, e como o verbo acha a raiz do repositorio (mesma precedencia de `catalog_dir()`).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | define-agent | Versao inicial, a partir de `BRAINSTORM_KNOWLEDGE_DRIFT.md`; medido: 115 URLs de regra, 155 regras com golden, 14 com eval, 38 de 43 agentes com `rule_areas`, e a URL de SC2 lida em tres datas |
| 1.1 | 2026-09-13 | design-agent | AT-009 testa `render_report` direto: o `--offline` sai antes do relatorio |
| 1.2 | 2026-09-13 | ship-agent | Shipped and archived (PR #60). O filtro virou `--source`/`source` no build (INV-009) |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_KNOWLEDGE_DRIFT.md`
