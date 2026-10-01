# BRAINSTORM: Freshness computavel das fontes

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_FRESHNESS |
| **Date** | 2026-09-11 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Frente §18 de `prompt_new_evo.md`, "Freshness precisa virar uma propriedade computavel". Cada conhecimento deveria ter um estado (fresh, aging, stale, conflicted, unverified, deprecated, superseded), e o agente deveria poder dizer "tenho uma regra para isso, mas a fonte foi alterada depois da ultima validacao", em vez de uma resposta que parece segura. Branch `feat/knowledge-freshness`, a partir da `main` (ja com #50, #51 e #52).

**Context Gathered:**
- **O que ja existe:**
  - `knowledge/sources.lock.json` guarda, por URL, `pinned` (versao no path, conteudo imutavel), `rules` e `docs` que dependem dela, a lista de `retrieved` e, quando a fonte foi conferida com rede, `sha256` e `checked_at`.
  - Esse lock e escrito por `scripts/refresh_knowledge.py` (workflow semanal que abre PR e nunca commita sozinho).
  - Cada fonte de regra no catalogo tem `url` e `retrieved` (a data em que o autor leu), e o motor copia `sources` da regra para o finding.
  - `sparkforge/agentic/evidence.py` separa autoridade (tier) de vigencia (versao alvo), mas nao olha data nem mudanca de fonte.
- **O que nao existe:**
  - Nenhum estado de freshness e calculado; nenhum verbo diz que uma fonte envelheceu ou mudou.
  - O lock nao guarda **quando** o hash mudou: o `--update` sobrescreve `sha256` e `checked_at`, e a mudanca se perde.
- **Medido em 2026-09-11, sobre o catalogo e o lock reais:**
  - 247 URLs vigiadas: 15 imutaveis e 232 moveis. So 21 das moveis tem hash conferido.
  - **218** fontes de regra com URL (115 URLs distintas, 127 regras), e mais **49** fontes so com `note`/`origin`, sem URL.
  - Por fonte de regra: **21** imutaveis, **157** moveis nunca conferidas por hash e **40** conferidas.
  - Idade do `checked_at` das 21 URLs conferidas: 20 com 39 a 42 dias e 1 com 16. A ultima conferencia geral foi em 2026-07-31, entao o refresh semanal nao entra na `main` ha cerca de 6 semanas.
  - **60** fontes de regra caem em URL cujo `retrieved` diverge entre regra e documento de knowledge (ex.: a regra leu em 07-31 e o documento em 08-03).
  - As 132 URLs so de knowledge: 124 nunca conferidas, 2 conferidas e 6 imutaveis.
  - **166** goldens de `fixtures/**/expected/findings.json` carregam **368** `sources`.
- O diretorio `knowledge/` inteiro vai para o wheel como `sparkforge/knowledge` (force-include no `pyproject.toml`): o lock viaja com o pacote, e um pacote Python com esse nome colidiria com ele.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/knowledge_freshness.py` (modulo puro); `adapters/_core.py` e `adapters/tools.py` (`judge`, `rules_lookup`, `knowledge_path`, `report github`); `sparkforge/reporting/github.py`; `scripts/refresh_knowledge.py`; `agents/executors/sf-verifier.md`; `docs/knowledge-freshness.md` | Compoe sobre o lock e o catalogo, sem rede |
| Relevant KB Domains | Knowledge management (proveniencia de fonte), testing (pares positivo/negativo, relogio injetado), CI/CD (workflow `refresh-knowledge`) | Estado calculado na leitura, nunca gravado no finding |
| IaC Patterns | Nenhum recurso novo; o workflow `refresh-knowledge.yml` ja existe | So o script muda |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual frente do `prompt_new_evo.md`? | Freshness computavel (§18) | Estado por fonte, com motivo |
| 2 | Onde o estado aparece primeiro? | No finding e no `rules_lookup` | Quem le o achado ve o estado na hora |
| 3 | Como detectar "mudou depois da validacao"? | `changed_at` no lock | O refresh grava a data em que o hash mudou; stale = `changed_at` posterior ao `retrieved` da regra |
| 4 | Criterio de sucesso? | Distribuicao medida + pares | Pares por estado nos testes, distribuicao real publicada, goldens de findings intactos |
| 5 | Amostras? | Lock e catalogo reais + sinteticos | A distribuicao sai dos reais; os pares usam lock e regras sinteticos com `as_of` fixo |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `knowledge/sources.lock.json` | 247 URLs | Base da distribuicao real |
| Input files | `rules/catalog/*.yaml` (`sources[]`) | 218 fontes com URL, 49 sem | Data de validacao por regra (`retrieved`) |
| Input files | `knowledge/**.md`, secao `Fontes` | 132 URLs so de knowledge | Estado por documento no `knowledge_path` |
| Output examples | Testes com lock sintetico, e um caso novo em `fixtures/sarif/` com `--source-freshness` | 1 caso de golden + pares de unidade | O `as_of` e o lock sinteticos fixam a saida |
| Ground truth | `scripts/refresh_knowledge.py` (o que ele grava e quando) | — | O `changed_at` nasce dele |
| Related code | `sparkforge/agentic/evidence.py`, `sparkforge/rules/engine.py`, `sparkforge/reporting/github.py` | — | Vigencia por versao, copia de `sources`, resumo do PR |

**How samples will be used:**

- Os pares sinteticos provam cada estado e a precedencia entre eles, com `as_of` fixo.
- A distribuicao real sai datada no STATUS e em `docs/knowledge-freshness.md`, e nao como teste: ela muda a cada refresh do lock.
- Os 166 `findings.json` continuam byte a byte; e a prova de que o estado nao entrou no finding.

---

## Approaches Explored

### Approach A: estado ao lado do finding, calculado na leitura ⭐ Recommended

**Description:** um modulo puro calcula o estado de cada fonte a partir do lock, da data de validacao da regra e de um `as_of` injetavel.
- O `judge` (CLI e tool) e o `rules_lookup` ganham, no topo da resposta, `source_freshness` (por URL citada na pagina devolvida) e `freshness_policy`.
- O `Finding` e o `findings.json` nao mudam.
- O `refresh_knowledge --update` passa a gravar `changed_at`.

**Pros:**
- Os 166 goldens de findings ficam intactos.
- O finding continua deterministico, e o estado sai sempre junto do achado.

**Cons:**
- Quem le so o `findings.json` gravado nao ve o estado; precisa da resposta do verbo ou do `rules_lookup`.

**Why Recommended:** o estado depende do lock e do dia, e o finding nao pode depender de nenhum dos dois. E o mesmo padrao do `report github` e do `telemetry export`: compor sobre o que ja foi medido. Confianca 0,85.

---

### Approach B: estado dentro de `Finding.sources[]`

**Description:** o motor copia a fonte da regra e acrescenta `freshness` em cada item.

**Pros:**
- O estado viaja no arquivo do achado.

**Cons:**
- Os 166 goldens mudam uma vez e voltam a mudar a cada refresh do lock.
- `aging` quebraria golden so pela passagem do tempo.

**Why not:** acopla o golden ao relogio e ao PR semanal do refresh.

---

### Approach C: estado pre-calculado no catalogo

**Description:** o `refresh_knowledge` escreve o estado em cada regra do YAML.

**Cons:**
- O estado envelhece entre um refresh e outro.
- O catalogo passa a guardar derivado.

**Why not:** e exatamente o estado que envelhece calado.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-11 |
| **Reasoning** | Finding deterministico, goldens intactos, estado calculado na leitura |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Estados `fixed`, `unverified`, `stale`, `aging` e `fresh`, com precedencia `fixed` > `stale` > `unverified` > `aging` > `fresh` | Cada um tem medida na fonte | `deprecated` e `superseded`, que nao tem dado nenhum hoje |
| 2 | `stale` = `changed_at` posterior ao `retrieved` que a regra (ou o documento) declara | Liga "mudou" a "depois de quem validou" | Comparar so datas de conferencia, que nao dizem se o conteudo mudou |
| 3 | `changed_at` gravado pelo `refresh_knowledge --update` quando o hash muda, preservado quando nao muda; fonte nova entra sem `changed_at`; `sync_metadata` (offline) preserva e nunca inventa | O unico lugar que sabe que o conteudo mudou | Historico de hashes no lock |
| 4 | Limiar de `aging`: **14 dias**, declarado como convencao, versionado e com a razao (duas rodadas perdidas do refresh semanal) | Nao ha fonte T1 para "quantos dias e velho"; o numero e escolha, e a regra 11 manda dizer isso | Numero sem razao escrita |
| 5 | `conflicted` e atributo ao lado do estado principal, com as duas datas | Com 60 de 218, trocar o estado inteiro esconderia `unverified`/`fixed` atras de uma divergencia de data que quase sempre e releitura posterior | `conflicted` como estado principal |
| 6 | Fonte sem URL (`note`/`origin`) nao recebe estado e entra na contagem como `sem_url` | Nao ha o que conferir | Tratar como `unverified` |
| 7 | `source_freshness` e `freshness_policy` no topo das respostas de `judge` e `rules_lookup`, so para as URLs da pagina devolvida | Aditivo; o finding nao muda | Campo dentro de cada finding (abordagem B) |
| 8 | `knowledge_path`: com `file`, estado de cada URL da secao `Fontes` do documento; sem `file`, contagem por estado por documento | As 132 URLs so de knowledge tambem envelhecem | So regras |
| 9 | `report github --source-freshness` (opt-in): secao "Fontes que pedem releitura" com os findings de fonte `stale` ou `aging`, e uma linha com a contagem de findings que citam fonte `unverified` | Com 157 de 218 `unverified`, listar um por um afogaria o resumo; opt-in para o golden de `fixtures/sarif` nao depender do lock e do dia | Ligado por padrao |
| 10 | `sf-verifier`, checagem 6: fonte `stale` deixa o achado `open`, com o statement "fonte mudou em X, depois da validacao de Y", e nunca confirmado sem releitura; nao refuta | A regra pode continuar certa; o que falta e reler | Refutar o achado |
| 11 | Modulo em `sparkforge/knowledge_freshness.py` | `sparkforge/knowledge` e o destino do force-include do `knowledge/` no wheel | Pacote `sparkforge/knowledge/` |
| 12 | Nenhuma tool nova; os schemas de `judge`, `rules_lookup` e `knowledge_path` crescem, e o crescimento e declarado (regra 26) | O estado mora onde a fonte ja aparece | Tool `knowledge_freshness` |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Estados `deprecated` e `superseded` | Nenhum dado no lock nem no catalogo diz que uma fonte foi substituida | Yes, quando o refresh detectar redirecionamento ou o catalogo declarar sucessora |
| Gate de CI que falha com fonte stale em regra P0/P1 | Escolhido "distribuicao medida + pares" em vez do gate | Yes |
| Verbo proprio `knowledge freshness` | O estado aparece onde a fonte ja aparece | Yes |
| Estado dentro do `Finding` | Acopla 166 goldens ao lock e ao relogio (abordagem B) | No, salvo com `as_of` fixo em todo lugar |
| Historico de hashes no lock | `changed_at` responde a pergunta; historico e peso sem consumidor | Yes |
| Rebaixar confianca numerica no `sf-verifier` | O score nao e confianca medida (CLAUDE.md, arbitragem); o que muda e o status `open` com a razao | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Estados, precedencia, limiar de 14 dias como convencao, `conflicted` como atributo, fonte sem URL | ✅ | "Sim, segue" | No |
| Superficies (`judge`, `rules_lookup`, `knowledge_path`, `report github` opt-in, `sf-verifier`), `changed_at` no refresh, prova | ✅ | "Sim, escreve o BRAINSTORM" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O SparkForge cita 218 fontes de regra e 132 fontes de conhecimento, e nao sabe dizer quais envelheceram: 157 fontes de regra nunca foram conferidas por hash, a ultima conferencia geral tem 42 dias, e quando uma pagina muda o lock esquece a data da mudanca. Um achado sai com a mesma seguranca tenha a fonte sido relida ontem ou alterada depois de quem escreveu a regra.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Engenheiro que le um achado | Nao sabe se a regra ainda se apoia no que a documentacao diz hoje |
| Mantenedor do catalogo | Nao tem a lista de regras cuja fonte mudou depois da validacao, nem de quais nunca foram conferidas |
| Revisor de PR (via `report github`) | Recebe o achado sem aviso de que a fonte pede releitura |

### Success Criteria (Draft)
- [ ] Pares positivo/negativo para cada estado e para a precedencia, com lock e regras sinteticos e `as_of` fixo.
- [ ] `refresh_knowledge --update` grava `changed_at` so quando o hash muda, com `fetch` falso cobrindo mudou, nao mudou, nova e inalcancavel; `sync_metadata` preserva.
- [ ] Os 166 `findings.json` dos goldens ficam byte a byte.
- [ ] `judge`, `rules_lookup` e `knowledge_path` validam contra o proprio schema com o campo novo.
- [ ] Caso novo em `fixtures/sarif/` com `--source-freshness` e lock sintetico; os casos atuais sem a flag ficam byte a byte.
- [ ] A distribuicao real sai datada no STATUS e em `docs/knowledge-freshness.md`: 21 `fixed`, 157 `unverified`, 40 conferidas, 20 das 21 URLs conferidas em `aging`, 0 `stale`.
- [ ] Gates (`check_vnext_claims`, `check_status_numbers --strict`, `check_surface_lock` com o crescimento declarado, `check_evals`, `ruff`) e suite por lotes verdes.

### Constraints Identified
- Regra 11: o limiar de `aging` e escolha, e sai declarado com a razao.
- Regra 20: fonte sem conferencia sai `unverified` e fonte sem URL sai `sem_url`, com nome, nunca como `fresh` por omissao.
- Regra 26: os schemas de tres tools crescem; `check_surface_lock --update` com o crescimento declarado.
- O refresh nunca carimba hash nem data sem rede (contrato do proprio `refresh_knowledge`).
- Pacote instalado sem lock: o estado sai `unresolved` com o motivo, e o verbo nao quebra.

### Out of Scope (Confirmed)
- Tudo o que esta na tabela YAGNI acima.
- Mudar `Finding`, o catalogo ou o motor de regras.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 9 (5 de discovery, 1 de abordagem, 1 de YAGNI, 2 de validacao) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_KNOWLEDGE_FRESHNESS.md`
