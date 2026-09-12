# DESIGN: Simulate (what-if estrutural)

> Technical design for SIMULATE

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMULATE |
| **Date** | 2026-09-12 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_SIMULATE.md](./DEFINE_SIMULATE.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 CLI  sparkforge simulate           MCP  sparkforge_simulate (READ_ONLY)
            └──────────────┬──────────────┘
                           v
 adapters/_core.py  simulate_change(facts_path[], sets[], runtime flags)
   - _merge_facts_files(facts)            -> uniao original
   - simulate.parse_sets(sets)            -> [(camada, chave, valor)] ou exit 2
   - simulate.apply_sets(uniao, sets)     -> uniao alterada + changes, ou exit 2
   - para CADA lado: simulate.strip_derived -> fuse() -> build_runtime_context -> judge
   - simulate.diff(antes, depois, stable_keys) -> disappeared/appeared/skipped_delta
                           │
                           v
 sparkforge/simulate/ (puro; nao roda judge nem le arquivo)
   layers.py  CAMADAS: tf, code, effective, emr -> kinds
   patch.py   parse_sets, apply_sets (attrs.value; measures.value numerico)
   diff.py    strip_derived, diff por (rule_id, chave estavel), skipped_delta

 facts/fusion.py  fuse(): ... build_lakeformation(facts) ... extract_timeout_diagnosis(facts, "")   <- passo 0
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `facts/fusion.py` | Passo 0: `fuse()` chama `extract_timeout_diagnosis` depois do `build_lakeformation`, com a mesma checagem de namespace | — |
| `sparkforge/simulate/layers.py` | Mapa camada -> kinds | stdlib |
| `sparkforge/simulate/patch.py` | Parse do `--set` e alteracao dos facts | stdlib |
| `sparkforge/simulate/diff.py` | Remocao dos derivados, comparacao, `skipped_delta` | `proof.keys.stable_key` |
| `adapters/_core.py` `simulate_change` | Pipeline dos dois lados | `fuse`, `judge`, `build_runtime_context` |
| `adapters/cli.py`, `adapters/tools.py` | Verbo `simulate`, tool `sparkforge_simulate` READ_ONLY | argparse |
| `agents/spark-performance-architect.md` (+ espelhos) | Dono: o coordenador que ja declara `tune` | — |

---

## Key Decisions

### Decision 1: o passo 0 liga o timeout dentro do `fuse()`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** `extract_timeout_diagnosis(facts, path)` nao tem chamador de producao; `fuse()` ja encadeia `build_lakeformation` (`fusion.py:519`) com checagem de namespace. Medido: 0 de 7 goldens de `fixtures/fusion/` tem fact de event log.

**Choice:** depois do `build_lakeformation`, `fuse()` roda `extract_timeout_diagnosis(facts, "")`, confere que os kinds saem de `timeout_diagnosis.EMITTED_KINDS` e junta pelo id. `path` vazio: ele so alimenta a proveniencia do fact de relacao, e um caminho inventado mentiria.

**Rationale:** o mesmo lugar, o mesmo molde do derivado que ja tem porta.

**Alternatives Rejected:**
1. Timeout no `judge_findings`: o `judge` nao deriva nada hoje, e passar a derivar mudaria todo verbo que julga.

**Consequences:**
- `sparkforge fuse` passa a produzir `spark.timeout.*`; `SF-TIMEOUT-001/002` alcancaveis por `fuse` -> `judge`.
- O golden `test_fixtures_golden_timeout.py` segue com o helper proprio; um teste novo prende que `fuse()` produz o mesmo que o helper.

---

### Decision 2: o `--set` altera todo fact da camada com a chave

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** medido no prototipo: em `infra_code/fgac_abaixo_do_minimo_de_workers`, `--set tf:number_of_workers=1` alterou os 2 jobs e fez `SF-LF-006` aparecer no segundo.

**Choice:** todo fact de um kind da camada cujo `attrs.key` bate e alterado. `attrs.value` recebe o texto; se o fact tinha `measures.value`, ele recebe `int` (sem ponto) ou `float`. Valor nao numerico para medida numerica -> `valor_nao_numerico_para_medida`; nenhum fact na camada -> `chave_ausente_na_camada`; qualquer recusa -> exit 2. `changes` diz quantos facts cada `--set` alterou e os valores antigos distintos.

**Rationale:** e a leitura mais simples e ja da o caso "regra aparece"; selecionar um recurso e escopo proprio.

**Alternatives Rejected:**
1. Seletor de subject (`--set tf:aws_glue_job.x#number_of_workers=1`): fora do escopo (YAGNI).

**Consequences:**
- Alterar `measures` muda o `Fact.id`; a comparacao e pela chave estavel (Decision 3).

---

### Decision 3: os dois lados pelo mesmo pipeline, comparados pela chave estavel

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** medido no prototipo: o mesmo valor (simetria) deu diff vazio; os derivados foram rederivados (`--set tf:--enable-lakeformation-fine-grained-access=false` fez `SF-LF-001` sumir).

**Choice:** para cada lado, `strip_derived` tira os kinds de `fusion.EMITTED_KINDS`, `lakeformation.EMITTED_KINDS` e `timeout_diagnosis.EMITTED_KINDS`; `fuse()` rederiva (Decision 1); `build_runtime_context` detecta o runtime a partir dos facts do lado, com as flags explicitas valendo para os dois; `judge(..., return_skipped=True)`. `diff` compara `(rule_id, stable_key(subject))`; `skipped_delta` lista a regra que muda entre avaliada e pulada (ou de razao de pulo).

**Rationale:** a diferenca so pode vir do `--set`.

**Consequences:**
- `--set tf:glue_version=3.0` muda o runtime detectado (medido: 5.0 -> 3.0) e a saida o mostra; com `--glue` explicito, a flag vence nos dois lados e o runtime nao muda -- a saida diz isso.

---

### Decision 4: superficie e dono

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Choice:** CLI `sparkforge simulate --facts U [--facts ...] --set camada:chave=valor [--set ...]` com as flags de runtime; tool `sparkforge_simulate` `_READ_ONLY` com `facts_path` e `sets` (catalogo 91 -> 92; tools com caminho 85 -> 86; READ_ONLY 59 -> 60). Dono: `spark-performance-architect`, o coordenador que declara `tune`. `refused` fixo: `performance_prediction`, `dependency_incompatibility` (-> `migration_assess`), `execution_graph`.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/facts/fusion.py` + teste de `fuse` com timeout | Modify/Create | Passo 0 | (general) | None |
| 2 | `sparkforge/simulate/{__init__,layers,patch,diff}.py` | Create | Modulo puro | @agentspec:python:python-developer | None |
| 3 | `tests/test_simulate_patch.py`, `tests/test_simulate_diff.py` | Create | Unidade | @agentspec:test:test-generator | 2 |
| 4 | `sparkforge/adapters/_core.py` | Modify | `simulate_change` | (general) | 1, 2 |
| 5 | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py` | Modify | Verbo e tool | (general) | 4 |
| 6 | `fixtures/simulate/` + `tests/test_fixtures_golden_simulate.py` | Create | Os seis cenarios do prototipo e as recusas, com `FIXTURES = ROOT / "fixtures" / "simulate"` | @agentspec:test:test-generator | 4, 5 |
| 7 | Registros (`test_adapters_tools`, `test_harness_authorization`, `test_fixtures_golden_mcp_parity`, `parity.yaml`, `manifest.json`, `spark-performance-architect.md` + `sync_skills`) | Modify | Tool nova | (general) | 5 |
| 8 | `docs/simulate.md`, `docs/superpowers/STATUS.md`, surface lock, claims | Create/Modify | Guia; timeout com porta; gates | (general) | all |
| 9 | `.claude/sdd/reports/BUILD_REPORT_SIMULATE.md` | Create | Relatorio | (general) | all |

**Total Files:** 9 entradas.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 2 | Funcoes puras |
| @agentspec:test:test-generator | 3, 6 | Unidade e golden |
| (general) | 1, 4, 5, 7–9 | Registros e adapters deste repositorio |

**Agent Discovery:** build direto, como nas frentes anteriores.

---

## Code Patterns

### Pattern 1: alteracao de um fact

```python
def patch_fact(fact: Fact, value: str) -> Fact:
    measures = dict(fact.measures)
    if "value" in measures:
        measures["value"] = float(value) if "." in value else int(value)
    return Fact(kind=fact.kind, subject=fact.subject, measures=measures,
                attrs={**fact.attrs, "value": value}, provenance=fact.provenance)
```

### Pattern 2: um lado do pipeline (adapter)

```python
def _um_lado(facts, rules, versoes):
    crus = strip_derived(facts)
    derivados = fuse(crus)
    runtime = build_runtime_context(**{**versoes, "facts": derivados}).to_dict()
    achados, pulados = run_judge(derivados, rules, runtime, return_skipped=True)
    return [a.to_dict() for a in achados], list(pulados), runtime
```

---

## Data Flow

```text
1. uniao --(apply_sets)--> uniao alterada + changes      (recusa -> exit 2)
2. cada lado: strip_derived -> fuse -> runtime -> judge
3. diff(antes, depois) por (rule_id, chave estavel) + skipped_delta
4. {changes, disappeared, appeared, persisted_count, skipped_delta, runtime, refused}
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| `facts.fusion.fuse` | Chamada interna (dois lados) | N/A |
| `rules.engine.judge` | Chamada interna (dois lados) | N/A |
| `proof.keys.stable_key` | Comparacao | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | parse, alteracao (texto e medida), recusas | `tests/test_simulate_patch.py` | pytest | AT-007..009 |
| Unit | strip, diff, skipped_delta, chave estavel | `tests/test_simulate_diff.py` | pytest | SC3 |
| Passo 0 | `fuse()` produz `spark.timeout.*` igual ao helper do golden de timeout; goldens de fusion intactos | teste novo + `test_fixtures_golden_fusion` | pytest | SC0 |
| Golden | Seis cenarios do prototipo pela CLI | `tests/test_fixtures_golden_simulate.py` | pytest | AT-001..006 |
| Contract | Tool com amostra real; formas de erro | `tests/test_adapters_tools.py` | pytest | SC4 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `--set` sem prefixo ou camada desconhecida | Exit 2 com as camadas validas | No |
| Chave ausente na camada | Exit 2 `chave_ausente_na_camada` | No |
| Valor nao numerico para medida | Exit 2 `valor_nao_numerico_para_medida` | No |
| Nenhum `--set` | Exit 2 (simular sem mudanca nao e simular) | No |

---

## Security Considerations

- Leitura so; nenhuma escrita; `facts_path` confinado pela cadeia de autorizacao.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Metrics | `persisted_count` e contagens por lado |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Item 1 | `fuse` produz timeout; goldens de fusion intactos |
| B2 | Itens 2, 3 | Unidade verde |
| B3 | Itens 4, 5 | Tool com amostra real |
| B4 | Item 6 | Golden verde (seis cenarios medidos no prototipo) |
| B5 | Itens 7, 8; gates; suite por lotes | Tudo verde |
| B6 | Commit, push, PR; item 9 | CI verde |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | design-agent | Versao inicial. A-006 (dono `spark-performance-architect`) e A-007 (cenarios medidos por prototipo) fechadas |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_SIMULATE.md`
