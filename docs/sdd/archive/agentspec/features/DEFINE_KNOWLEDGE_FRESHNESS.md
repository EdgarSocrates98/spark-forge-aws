# DEFINE: Freshness computavel das fontes

> O estado de cada fonte citada (fixed, unverified, stale, aging, fresh, com `conflicted` ao lado), calculado na leitura a partir de `knowledge/sources.lock.json`, da data em que a regra ou o documento validou a fonte e de um `as_of` injetavel. Ele aparece junto do achado no `judge` e no `rules_lookup`, por documento no `knowledge_path`, opcionalmente no resumo do `report github`, e na checagem do `sf-verifier`, sem mudar o `Finding` e sem rede.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_FRESHNESS |
| **Date** | 2026-09-11 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O SparkForge cita 218 fontes de regra e 132 fontes de conhecimento e nao sabe dizer quais envelheceram: 157 fontes de regra nunca foram conferidas por hash, a ultima conferencia geral tem 42 dias, e quando uma pagina muda o lock esquece a data da mudanca. Por isso um achado sai com a mesma seguranca tenha a fonte sido relida ontem ou alterada depois de quem escreveu a regra.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Engenheiro que le um achado | Consome a saida do `judge` ou o resumo do PR | Nao sabe se a regra ainda se apoia no que a documentacao diz hoje |
| Mantenedor do catalogo | Revisa o PR semanal do `refresh-knowledge` e mantem `rules/catalog/` | Nao tem a lista de regras cuja fonte mudou depois da validacao, nem de quais nunca foram conferidas |
| Revisor de PR | Le o resumo do `report github` | Recebe o achado sem aviso de que a fonte pede releitura |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: modulo puro `sparkforge/knowledge_freshness.py` que, dados URL, data de validacao (o `retrieved` da regra ou do documento), o lock, `as_of` e o limiar, devolve `state` (`fixed`, `unverified`, `stale`, `aging`, `fresh`), `reason`, as datas usadas e o atributo `conflicted`. Precedencia: `fixed` > `stale` > `unverified` > `aging` > `fresh` |
| **MUST** | G2: `stale` quando `changed_at` do lock e posterior a data de validacao; `aging` quando a fonte foi conferida e o `checked_at` e mais velho que o limiar em relacao a `as_of`; `fresh` quando foi conferida dentro do limiar; `unverified` quando e movel e nao tem `sha256`; `fixed` quando e `pinned` |
| **MUST** | G3: limiar de `aging` = **14 dias**, declarado como convencao, versionado no codigo com a razao escrita (duas rodadas perdidas do refresh semanal), e devolvido em `freshness_policy` junto com `as_of` |
| **MUST** | G4: `scripts/refresh_knowledge.py --update` grava `changed_at` = hoje quando o hash muda, preserva o `changed_at` anterior quando o hash nao muda, nao grava `changed_at` em fonte nova, e mantem os campos numa conferencia inalcancavel. `sync_metadata` (offline) preserva `changed_at` e nunca o cria |
| **MUST** | G5: com `source_freshness: true` (tool) ou `--source-freshness` (CLI), e `as_of` opcional (`AAAA-MM-DD`, default hoje em UTC), `judge` e `rules_lookup` devolvem, no topo, `source_freshness` (URL para estado, so das fontes citadas na pagina devolvida) e `freshness_policy` (limiar, razao, `as_of` e contagem por estado). O `Finding` e o `findings.json` nao mudam, e sem a flag a resposta e byte a byte a de hoje (DESIGN Decision 1) |
| **MUST** | G6: fonte sem URL (`note`/`origin`) nao recebe estado e aparece na contagem como `sem_url`; lock ausente no pacote instalado faz o estado sair `unresolved` com o motivo, sem derrubar o verbo |
| **SHOULD** | G7: `conflicted` como atributo, ao lado do estado principal, quando o lock registra para a mesma URL um `retrieved` diferente do que a regra ou o documento declaram, com as datas envolvidas |
| **SHOULD** | G8: `knowledge_path`, com a mesma flag: com `file`, o estado de cada URL da secao `Fontes` daquele documento, usando o `retrieved` que o documento declara; sem `file`, a contagem por estado de cada documento |
| **SHOULD** | G9: `report github --source-freshness` (opt-in): secao "Fontes que pedem releitura" no resumo, com os findings que citam fonte `stale` ou `aging`, e uma linha com quantos findings citam fonte `unverified` |
| **SHOULD** | G10: `sf-verifier` ganha a checagem 6: achado com fonte `stale` fica `open`, com o statement "fonte mudou em X, depois da validacao de Y", e nunca sai confirmado sem releitura; a checagem nao o refuta |
| **SHOULD** | G11: `docs/knowledge-freshness.md` com os estados, a precedencia, o limiar e a razao dele, o que o `changed_at` significa, e a distribuicao real datada |
| **COULD** | G12: a distribuicao real no STATUS: por fonte de regra, 21 `fixed`, 157 `unverified` e 40 conferidas; 20 das 21 URLs conferidas em `aging` com `as_of` 2026-09-11; 0 `stale`, porque o `changed_at` nasce nesta frente |

---

## Success Criteria

- [ ] SC1: pares positivo/negativo para os 5 estados e para cada par da precedencia, com lock e regras sinteticos e `as_of` fixo; o mesmo par, com `as_of` 1 dia antes e 1 dia depois do limiar, alterna entre `fresh` e `aging`.
- [ ] SC2: `refresh_knowledge --update`, com `fetch` falso, grava `changed_at` so no caso "mudou" dos quatro (mudou, nao mudou, nova, inalcancavel); `sync_metadata` preserva o `changed_at` existente.
- [ ] SC3: os **166** `findings.json` de `fixtures/**/expected/` ficam byte a byte.
- [ ] SC4: `judge`, `rules_lookup` e `knowledge_path` com a flag validam contra o proprio `outputSchema`, e `source_freshness` so contem URLs citadas na pagina devolvida; sem a flag, a resposta e igual a de antes, e o golden de paridade MCP so aceita diferenca aditiva nos schemas dessas tools.
- [ ] SC5: um caso novo em `fixtures/sarif/` com `--source-freshness` e lock sintetico bate com o golden; os 7 casos atuais, sem a flag, ficam byte a byte.
- [ ] SC6: nenhuma fonte sem URL recebe estado, e a contagem `sem_url` e igual ao numero de fontes de regra sem `url` nas regras da pagina.
- [ ] SC7: com o lock removido do caminho de knowledge, os tres verbos devolvem o resultado com o estado `unresolved` e o motivo, e exit 0.
- [ ] SC8: gates (`check_vnext_claims`, `check_status_numbers --strict`, `check_surface_lock` com o crescimento declarado, `check_evals`, `ruff`) e suite por lotes com **0** falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Fonte imutavel | URL `pinned` no lock | estado | `fixed`, sem olhar datas |
| AT-002 | Nunca conferida | URL movel sem `sha256` | estado | `unverified`, com o motivo |
| AT-003 | Mudou depois da validacao | `changed_at` 2026-09-01, regra validou em 2026-08-01 | estado | `stale`, com as duas datas |
| AT-004 | Mudou antes da validacao | `changed_at` 2026-08-01, regra revalidou em 2026-09-01 | estado | Nao `stale`; `fresh` ou `aging` pelo `checked_at` |
| AT-005 | Conferida e recente | `checked_at` 5 dias antes de `as_of`, sem mudanca | estado | `fresh` |
| AT-006 | Conferida e velha | `checked_at` 20 dias antes de `as_of`, sem mudanca | estado | `aging`, com a idade e o limiar |
| AT-007 | Datas divergentes | Lock com `retrieved` [07-31, 08-03], regra declara 07-31 | estado | Estado principal e mais `conflicted` com as duas datas |
| AT-008 | Refresh detecta mudanca | Hash anterior diferente do novo | `--update` com `fetch` falso | `changed_at` = hoje, `checked_at` = hoje |
| AT-009 | Refresh sem mudanca | Mesmo hash, `changed_at` anterior | `--update` | `changed_at` preservado, `checked_at` = hoje |
| AT-010 | Judge | Findings de uma fixture existente | `judge --source-freshness` | `source_freshness` com as URLs citadas; `findings` identicos aos de antes |
| AT-011 | Documento de knowledge | `knowledge_path --file glue/workers-and-capacity.md --source-freshness` | tool | Estado de cada URL da secao `Fontes` |
| AT-012 | Resumo do PR | Caso novo de `fixtures/sarif/` com fonte `stale` no lock sintetico | `report github --source-freshness` | Secao "Fontes que pedem releitura" com o finding e as datas |
| AT-013 | Sem lock | Pacote sem `sources.lock.json` | `judge --source-freshness` | Resultado normal, `source_freshness` com `unresolved` e o motivo |

---

## Out of Scope

- Estados `deprecated` e `superseded`: nenhum dado os sustenta hoje.
- Gate de CI por fonte `stale`.
- Verbo proprio de freshness e tool nova.
- Estado dentro do `Finding` ou pre-calculado no catalogo.
- Historico de hashes no lock.
- Rebaixar score numerico de confianca no `sf-verifier`.
- Rodar o refresh com rede nesta frente: o lock real continua com os dados de hoje, e o `changed_at` passa a ser gravado a partir do proximo refresh.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 11 | O limiar de `aging` sai declarado, com a razao, e nao como fato |
| Technical | Regra 20 | `unverified`, `sem_url` e `unresolved` saem nomeados; nada vira `fresh` por omissao |
| Technical | Regra 26 | Os schemas de tres tools crescem; `check_surface_lock --update` com o crescimento declarado |
| Technical | Contrato do `refresh_knowledge` | Nenhum modo sem rede carimba hash, `checked_at` ou `changed_at` |
| Technical | `sparkforge/knowledge` e o destino do force-include do `knowledge/` no wheel | O modulo novo nao pode ser pacote com esse nome |
| Technical | O finding e deterministico | Nada que dependa do lock ou do dia entra no `Finding` nem nos goldens atuais |
| Technical | `scripts/` nao e pacote | Codigo compartilhado entre o script e o verbo mora em `sparkforge/`, e o script importa dele |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/knowledge_freshness.py`; `adapters/_core.py` e `adapters/tools.py` (`judge`, `rules_lookup`, `knowledge_path`, `report github`); `adapters/cli.py` (flag `--source-freshness`); `sparkforge/reporting/github.py`; `scripts/refresh_knowledge.py`; `agents/executors/sf-verifier.md` e espelhos; `fixtures/sarif/`; `docs/knowledge-freshness.md` | Nenhum recurso de nuvem |
| **KB Domains** | Knowledge management (proveniencia de fonte), testing (pares com relogio injetado), CI/CD (workflow `refresh-knowledge`) | — |
| **IaC Impact** | None | O workflow `refresh-knowledge.yml` nao muda; so o script |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O lock viaja no wheel junto com `knowledge/` (force-include para `sparkforge/knowledge`) | O estado sairia `unresolved` em todo pacote instalado | [x] `pyproject.toml` |
| A-002 | O lock junta as datas `retrieved` das duas origens numa lista sem dizer de qual origem cada uma veio (`scripts/refresh_knowledge.py::watchlist`) | — | [x] lido no script |
| A-003 | A data de validacao de uma fonte de regra vem do catalogo (`sources[].retrieved`), que o pacote ja carrega | — | [x] 218 de 218 fontes com URL tem `retrieved` |
| A-004 | Para o estado por documento, o pacote precisa ler a secao `Fontes` de `knowledge/**.md`; o leitor hoje mora so em `scripts/refresh_knowledge.py` | O DESIGN move o leitor para `sparkforge/` e o script passa a importa-lo, para nao haver duas copias | [x] DESIGN Decision 4 |
| A-005 | O `retrieved` do catalogo e carregado como `datetime.date` pelo YAML | A comparacao de datas precisaria normalizar texto | [x] visto na leitura do catalogo |
| A-006 | Nenhum golden atual compara a saida inteira do `judge` ou do `rules_lookup` alem dos findings e regras | Se algum comparar, o campo novo quebra o golden e o DESIGN decide entre regenerar e fixar `as_of` | [x] Errada: `fixtures/mcp_parity` compara uma chamada real de `rules_lookup` e os schemas das tres tools; DESIGN Decisions 1 e 6 (opt-in, diff so aditivo) |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Numeros medidos: 157 nunca conferidas, 42 dias, data da mudanca perdida |
| Users | 3 | Tres papeis, cada um ligado a uma saida |
| Goals | 3 | MoSCoW com 12 metas, cada uma ligada a SC ou AT |
| Success | 3 | Contagens exatas (166 goldens, 7 casos de SARIF, 5 estados, 4 casos do refresh) |
| Scope | 2 | Escopo claro; a mudanca do leitor de `Fontes` (A-004) e o impacto nos goldens de verbos (A-006) ficam para o DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Build. A-004 e A-006 decididas no DESIGN.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | define-agent | Versao inicial, a partir de `BRAINSTORM_KNOWLEDGE_FRESHNESS.md` |
| 1.1 | 2026-09-11 | design-agent | Opt-in por `source_freshness`/`as_of` (G5, G8, SC4, AT-010/011/013); A-004 e A-006 fechadas |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_KNOWLEDGE_FRESHNESS.md`
