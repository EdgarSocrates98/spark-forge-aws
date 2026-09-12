# DESIGN: Freshness computavel das fontes

> Technical design for KNOWLEDGE_FRESHNESS

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_FRESHNESS |
| **Date** | 2026-09-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_KNOWLEDGE_FRESHNESS.md](./DEFINE_KNOWLEDGE_FRESHNESS.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
 scripts/refresh_knowledge.py --update ──(hash mudou)──> knowledge/sources.lock.json
        │  importa o leitor de `Fontes`                    {pinned, sha256, checked_at,
        v                                                   changed_at (novo), retrieved[]}
 sparkforge/knowledge_freshness.py (puro)                          │
   fontes_de_knowledge(root) -> URL -> {docs, retrieved}           │ carregar_lock(root)
   estado(url, validado_em, lock, as_of) -> Estado ◄───────────────┘
   mapa(fontes, lock, as_of) -> {source_freshness, freshness_policy}
        ▲                 ▲                   ▲                     ▲
        │ opt-in          │ opt-in            │ opt-in              │ opt-in
   judge_findings    rules_lookup      knowledge_path        report github
   (finding.sources) (rule.sources)   (Fontes do doc)   (--source-freshness: secao
                                                          "Fontes que pedem releitura")
        │
   sf-verifier (checagem 6): stale -> achado `open`, com a razao
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/knowledge_freshness.py` | `Estado`, `estado()`, `mapa()`, `carregar_lock()`, `fontes_de_knowledge()` (leitor de `Fontes` movido do script) e a politica (`AGING_DAYS = 14`, `AGING_BASIS`) | stdlib (`datetime`, `json`, `re`) |
| `scripts/refresh_knowledge.py` | `compare` grava `changed_at`; `knowledge_sources()` passa a delegar ao leitor do pacote | — |
| `_core.judge_findings`, `rules_lookup`, `knowledge_path` | Parametros `source_freshness: bool = False` e `as_of: str | None = None`; com a flag, os campos novos no topo | — |
| `_core.report_github` + `reporting/github.py::projetar` | `source_freshness` (mapa ja calculado) opcional; secao nova no resumo so quando presente | — |
| `adapters/cli.py` | `--source-freshness` e `--as-of AAAA-MM-DD` em `judge`, `rules lookup`, `knowledge path` e `report github` | argparse |
| `adapters/tools.py` | `source_freshness` e `as_of` no `inputSchema` das tres tools e na do `report_github`; `source_freshness`/`freshness_policy` opcionais no `outputSchema` | — |
| `agents/executors/sf-verifier.md` (+ espelhos) | Checagem 6 | — |
| `tests/test_fixtures_golden_mcp_parity.py` | `ALTERADAS_DEPOIS_DO_GOLDEN`: diff so aditivo (`antes == "<ausente>"`) nessas tools, com motivo | pytest |
| `docs/knowledge-freshness.md` | Estados, precedencia, limiar, `changed_at`, distribuicao datada | — |

---

## Key Decisions

### Decision 1: opt-in por parametro, e nao campo sempre presente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** A-006. Tres fatos medidos:
- `fixtures/mcp_parity/calls.json` grava uma chamada real de `sparkforge_rules_lookup` (`id: ["SF-TIMEOUT-002"]`), e `test_toda_chamada_bate_byte_a_byte` a compara byte a byte.
- A descricao da tool promete: "o LLM consulta o catalogo versionado e recebe sempre a mesma resposta".
- O estado depende do lock e do `as_of`, entao um campo sempre presente mudaria a resposta de um dia para o outro sem que o catalogo mudasse.

**Choice:** `source_freshness: true` (tool) ou `--source-freshness` (CLI) liga o calculo; `as_of` (`AAAA-MM-DD`) e opcional e fixa o dia; sem ele, e hoje em UTC. Sem a flag, a resposta e byte a byte a de hoje.
- O `sf-verifier` e o workflow de exemplo do `report github` ligam a flag.
- A descricao das tools diz que o estado depende do lock e do dia.

**Rationale:** mantem a promessa de determinismo do `rules_lookup` e do `judge`, e a paridade das chamadas gravadas, sem esconder o estado de quem pede.

**Alternatives Rejected:**
1. Sempre presente: quebra a promessa e o golden de chamadas, e a quebra repetiria a cada dia.
2. Sempre presente com a chave ignorada no teste de paridade: o teste deixaria de provar paridade justamente na resposta que mudou.

**Consequences:**
- Quem nao pede nao ve o estado. O `sf-verifier` pede sempre, e e ele que torna o estado parte do loop.
- Os schemas das tres tools crescem mesmo assim (parametro de entrada e campos opcionais de saida): o teste de paridade ganha `ALTERADAS_DEPOIS_DO_GOLDEN` (Decision 6).

---

### Decision 2: o estado, a precedencia e a politica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `estado(url, validado_em, lock, as_of)` decide nesta ordem:

| Ordem | Estado | Condicao | `reason` |
|---|---|---|---|
| 1 | `unresolved` | Lock ausente ou ilegivel | `lock_ausente` / `lock_ilegivel` |
| 2 | `unresolved` | URL fora do lock | `fora_do_lock` |
| 3 | `fixed` | `pinned` | `versao_no_caminho` |
| 4 | `stale` | `changed_at` existe, e `validado_em` ausente ou anterior a ele | `mudou_depois_da_validacao` |
| 5 | `unverified` | Sem `sha256` | `nunca_conferida` |
| 6 | `aging` | `as_of - checked_at > AGING_DAYS` | `conferida_ha_N_dias` |
| 7 | `fresh` | O resto | `conferida_ha_N_dias` |

- `validado_em` e o `retrieved` que a regra (ou o documento) declara, em `date`. O YAML ja o carrega como `datetime.date`, e texto ISO e aceito.
- `conflicted`: o lock registra para a URL um `retrieved` diferente de `validado_em`. Sai `{"validated": validado_em, "other_readings": [...]}` ao lado do estado; nao muda o estado.
- `AGING_DAYS = 14` e `AGING_BASIS = "convencao: duas rodadas perdidas do refresh semanal (refresh-knowledge.yml, cron segunda 06:00 UTC)"`. Os dois saem em `freshness_policy`, com `as_of` e a contagem por estado.
- Fonte sem `url` nao entra no mapa; a contagem `sem_url` sai em `freshness_policy.counts`.

**Rationale:** cada estado tem condicao medivel no lock. `stale` vem antes de `unverified` porque so existe `changed_at` onde houve hash, e antes de `aging` porque a mudanca e o sinal mais forte.

---

### Decision 3: `changed_at` no refresh

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** em `compare`, com `before != current`, a entrada ganha `changed_at = today`. Com `before == current`, o `changed_at` anterior e copiado. Fonte nova nao ganha `changed_at`, e a inalcancavel mantem a entrada anterior inteira. O `sync_metadata` ja preserva tudo o que nao reescreve e, para fonte `pinned`, remove `changed_at` junto com `sha256` e `checked_at`.

**Rationale:** e o unico ponto que sabe que o conteudo mudou.

---

### Decision 4: um leitor de `Fontes`, no pacote

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** A-004. O leitor mora em `scripts/refresh_knowledge.py::knowledge_sources()`, e o `knowledge_path` precisa dele no pacote instalado. O lock nao serve de substituto: ele junta as datas das duas origens numa lista so.

**Choice:** `fontes_de_knowledge(root: Path) -> dict[url, {docs, retrieved}]` em `knowledge_freshness.py`, com o mesmo corpo e as mesmas regras de leitura (heading exatamente `Fontes`, secao ate heading de nivel igual ou maior, URL em crase ignorada). O script chama `fontes_de_knowledge(ROOT / "knowledge")` e continua com o mesmo formato de saida. Para o estado por documento, o `knowledge_path` precisa do `retrieved` de cada documento, por isso a funcao devolve tambem `por_doc: {doc: {url: [datas]}}`.

**Rationale:** uma copia so, e o teste existente do refresh continua valendo sobre ela.

---

### Decision 5: `report github` recebe o mapa pronto

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `_core.report_github(..., source_freshness=False, as_of=None)` calcula o mapa sobre `finding.sources` (os findings ja trazem `url` e `retrieved` copiados da regra) e o passa a `projetar(..., freshness=mapa)`. O resumo ganha a secao `## Fontes que pedem releitura (N)` so quando o mapa existe:
- uma linha por finding com fonte `stale` ou `aging` (severidade, regra, URL, estado e datas);
- depois uma linha so: "M findings citam fonte nunca conferida por hash (`unverified`)".

O SARIF e as anotacoes nao mudam.

**Rationale:** o resumo e onde o revisor le. Listar os `unverified` um por um afogaria o resumo (157 de 218 fontes de regra).

**Consequences:**
- Um caso novo em `fixtures/sarif/` com `input/knowledge/sources.lock.json` sintetico e `meta.yaml` com `source_freshness: true` e `as_of`.
- O regen e o teste da CLI apontam `SPARKFORGE_KNOWLEDGE` para esse diretorio. Os 7 casos atuais nao passam a flag.

---

### Decision 6: paridade MCP aceita so diferenca aditiva nas tools alteradas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `ALTERADAS_DEPOIS_DO_GOLDEN = {tool: motivo}` para `sparkforge_judge`, `sparkforge_rules_lookup` e `sparkforge_knowledge_path`, e `_fora_da_allowlist` passa a aceitar diff dessas tools **so** quando `antes == "<ausente>"` (chave nova). As chamadas gravadas continuam byte a byte, porque nenhuma delas passa a flag. O teste de contagem de diffs passa a separar o diff aceito do `outputSchema.type` do diff aditivo, e cada um tem a sua contagem medida.

**Rationale:** prova que a mudanca so acrescenta; qualquer remocao ou alteracao de valor em schema existente continua derrubando o teste.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/knowledge_freshness.py` | Create | Estado, mapa, politica, lock e leitor de `Fontes` | @agentspec:python:python-developer | None |
| 2 | `scripts/refresh_knowledge.py` | Modify | `changed_at` no `compare`; o leitor delega ao pacote | @agentspec:python:python-developer | 1 |
| 3 | `tests/test_knowledge_freshness.py` | Create | Pares por estado, precedencia, borda do limiar, `conflicted`, `sem_url`, `unresolved`, leitor de `Fontes` | @agentspec:test:test-generator | 1 |
| 4 | `tests/test_refresh_knowledge.py` | Modify | Os quatro casos do `changed_at` com `fetch` falso; `sync_metadata` preserva | @agentspec:test:test-generator | 2 |
| 5 | `sparkforge/adapters/_core.py` | Modify | Flag e `as_of` em `judge_findings`, `rules_lookup`, `knowledge_path` e `report_github` | (general) | 1 |
| 6 | `sparkforge/reporting/github.py` | Modify | `projetar(..., freshness=None)` e a secao do resumo | @agentspec:python:python-developer | 1 |
| 7 | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py` | Modify | Flags da CLI; `inputSchema`/`outputSchema` e descricoes | (general) | 5 |
| 8 | `tests/test_fixtures_golden_mcp_parity.py` | Modify | `ALTERADAS_DEPOIS_DO_GOLDEN` e o diff aditivo | (general) | 7 |
| 9 | `tests/test_adapters_tools.py`, `tests/test_adapters_knowledge.py`, `tests/test_adapters_rules_knowledge.py`, `tests/test_reporting_github.py` | Modify | Saida real com a flag valida contra o schema; sem a flag, igual a hoje | @agentspec:test:test-generator | 5–7 |
| 10 | `fixtures/sarif/freshness/` + `scripts/regen_fixtures.py` + `tests/test_fixtures_golden_sarif.py` | Create/Modify | Caso novo com lock sintetico; `saidas_sarif` e o teste da CLI leem `source_freshness`/`as_of`/`knowledge` do `meta.yaml` | (general) | 6, 7 |
| 11 | `agents/executors/sf-verifier.md` + espelhos (`scripts/sync_skills.py`) | Modify | Checagem 6 | (general) | 5 |
| 12 | `docs/knowledge-freshness.md`, `docs/superpowers/STATUS.md`, `examples/github/sparkforge.yml` | Create/Modify | Guia, distribuicao datada, flag no workflow de exemplo | (general) | all |
| 13 | `docs/surface.lock.json`, `docs/claims.lock.json` + docs auditados | Modify (se o gate acusar) | Gates | (general) | all |
| 14 | `.claude/sdd/reports/BUILD_REPORT_KNOWLEDGE_FRESHNESS.md` | Create | Relatorio | (general) | all |

**Total Files:** 14 entradas.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 1, 2, 6 | Funcoes puras e o script |
| @agentspec:test:test-generator | 3, 4, 9 | Pares por estado e casos do refresh |
| (general) | 5, 7, 8, 10–14 | Registros, fixtures e documentos deste repositorio |

**Agent Discovery:**
- Scanned: agentes do plugin agentspec e os da sessao.
- Matched by: tipo de arquivo e palavra-chave.
- Como nos PRs #50 a #52, o build pode ficar direto: cada passo depende de medida do anterior.

---

## Code Patterns

### Pattern 1: estado (`knowledge_freshness.py`)

```python
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

AGING_DAYS = 14
AGING_BASIS = (
    "convencao: duas rodadas perdidas do refresh semanal "
    "(refresh-knowledge.yml, cron segunda 06:00 UTC)"
)


@dataclass(frozen=True)
class Estado:
    state: str
    reason: str
    validated: str | None = None
    checked_at: str | None = None
    changed_at: str | None = None
    age_days: int | None = None
    conflicted: dict[str, Any] | None = None


def _data(valor: Any) -> date | None:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def estado(
    url: str,
    validado_em: Any,
    lock: Mapping[str, Mapping[str, Any]] | None,
    as_of: date,
) -> Estado:
    if lock is None:
        return Estado("unresolved", "lock_ausente")
    entrada = lock.get(url)
    if entrada is None:
        return Estado("unresolved", "fora_do_lock")
    validado = _data(validado_em)
    ...
```

### Pattern 2: `changed_at` no `compare` (`refresh_knowledge.py`)

```python
novo = {
    "pinned": False,
    "sha256": current,
    "checked_at": today,
    "rules": meta["rules"],
    "docs": meta["docs"],
    "retrieved": meta["retrieved"],
}
if before is not None and before != current:
    novo["changed_at"] = today
elif before == current and "changed_at" in previous:
    novo["changed_at"] = previous["changed_at"]
stored[url] = novo
```

### Pattern 3: diff aditivo na paridade

```python
def _fora_da_allowlist(difs):
    return [
        (caminho, antes, agora)
        for caminho, antes, agora in difs
        if not (_OUTPUT_TYPE.match(caminho) and antes == "<ausente>" and agora == "object")
        and not (_da_tool_alterada(caminho) and antes == "<ausente>")
    ]
```

---

## Data Flow

```text
1. verbo recebe source_freshness=True e as_of? (default: hoje UTC)
2. lock = carregar_lock(knowledge_dir())           -> None se ausente/ilegivel
3. fontes = sources dos findings da pagina | das regras da pagina | Fontes do doc
4. mapa(fontes, lock, as_of) -> {source_freshness: {url: Estado}, freshness_policy}
5. resposta de hoje + os dois campos (so com a flag)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Workflow `refresh-knowledge.yml` | Roda o script, que passa a gravar `changed_at` | `GITHUB_TOKEN` do proprio workflow (sem mudanca) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | 5 estados, precedencia, borda de 14 dias, `conflicted`, `sem_url`, `unresolved`, `validado_em` texto e `date` | `tests/test_knowledge_freshness.py` | pytest | AT-001 a AT-007, SC1, SC6, SC7 |
| Unit | `changed_at` nos quatro casos; `sync_metadata`; leitor de `Fontes` delegado | `tests/test_refresh_knowledge.py` | pytest | AT-008, AT-009, SC2 |
| Contract | Tres tools com a flag validam contra o schema; sem a flag, resposta igual a de hoje | `tests/test_adapters_tools.py`, `tests/test_adapters_knowledge.py`, `tests/test_adapters_rules_knowledge.py` | pytest | AT-010, AT-011, SC4 |
| Golden | 166 `findings.json` intactos; caso `fixtures/sarif/freshness`; os 7 casos atuais intactos | goldens existentes + `tests/test_fixtures_golden_sarif.py` | pytest | SC3, SC5, AT-012 |
| Parity | Diff so aditivo nas tres tools; chamadas gravadas byte a byte | `tests/test_fixtures_golden_mcp_parity.py` | pytest | Decision 6 |
| Unit | Lock ausente com `SPARKFORGE_KNOWLEDGE` sem lock | `tests/test_knowledge_freshness.py` | pytest | AT-013 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Lock ausente ou JSON invalido | Estado `unresolved` (`lock_ausente`/`lock_ilegivel`); o verbo responde | No |
| `as_of` fora de `AAAA-MM-DD` | Exit 2 com o formato e o comando | No |
| `retrieved` ausente ou ilegivel na regra | Usa `None`: `stale` so se houver `changed_at`; o resto segue o lock | No |
| `checked_at` ilegivel no lock | Tratado como sem conferencia: `unverified` | No |
| Documento pedido no `knowledge_path` sem secao `Fontes` | `source_freshness` vazio, com `counts.total = 0` | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--source-freshness` / `source_freshness` | bool | `false` | Liga o calculo |
| `--as-of` / `as_of` | `AAAA-MM-DD` | hoje (UTC) | Dia de referencia |
| `AGING_DAYS` | int (codigo) | 14 | Convencao declarada, em `freshness_policy` |

---

## Security Considerations

- Nenhuma rede no pacote; o lock e so lido.
- `as_of` e validado como data antes de uso; nenhum caminho novo vem do argv.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | N/A |
| Metrics | Contagem por estado em `freshness_policy.counts` |
| Tracing | O span de tool existente registra os bytes a mais quando a flag e pedida |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Itens 1 e 3 | Unidade verde |
| B2 | Itens 2 e 4 | Testes do refresh verdes; a saida de `--offline --update` sobre o lock real nao muda nada |
| B3 | Itens 5–9 | Tools validam; paridade verde; respostas sem a flag iguais |
| B4 | Itens 10–11 | Golden novo verde, 7 casos intactos, 166 findings intactos |
| B5 | Itens 12–13; suite, gates, Snyk | Tudo verde |
| B6 | Commit, push, PR; item 14 | — |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | design-agent | Versao inicial; A-004 e A-006 decididas; opt-in por `source_freshness` (Decision 1) |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_KNOWLEDGE_FRESHNESS.md`
