# DESIGN: Realized Gain Ledger

> Technical design for implementing the Realized Gain Ledger (§21 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REALIZED_GAIN |
| **Date** | 2026-09-13 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_REALIZED_GAIN.md](./DEFINE_REALIZED_GAIN.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ --baseline a.json --baseline b.json      --candidate c.json ...       │
│        │ _load_facts_file (um conjunto por arquivo)                    │
│        ▼                                                               │
│ realized_gain(baseline: [[Fact]], candidate: [[Fact]])  (funcao pura) │
│   por arquivo: glue.job_run SUCCEEDED (outros -> discarded)            │
│                glue.run_cost pelo job_run_id                           │
│                volume = capacity._volume_de(arquivo) se 1 run          │
│   job_name unico nos dois lados, senao GainError (codigo 2)           │
│   por lado e metrica: N, mediana, min, max                            │
│   delta das medianas (valor e %) + marcas                             │
│   refused fixo                                                         │
│        │                                                               │
│   ┌────┴──────────────┐                                                │
│   ▼                   ▼                                                │
│ CLI sparkforge gain   tool sparkforge_gain (READ_ONLY, declara caminho)│
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/finops/realized.py` | `realized_gain`, `GainError`, estatistica por lado, marcas, recusas | Python puro, `statistics.median` |
| `sparkforge/capacity/plan.py::_volume_de` | Volume de um run (reusado, nao copiado) | existente |
| `_core.gain` | Carrega um conjunto de facts por arquivo e chama `realized_gain` | adapters existentes |
| CLI `gain` e tool `sparkforge_gain` | Superficie | adapters existentes |

---

## Key Decisions

### Decision 1: Um conjunto de facts por arquivo; run = `glue.job_run` `SUCCEEDED`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** Medido: o historico do capacity e um arquivo por run (com `spark.sql.scan`); o `analyze glue-job-runs` gera um arquivo com varios runs.

**Choice:** cada `--baseline`/`--candidate` e carregado como um conjunto. Todo `glue.job_run` do conjunto e um run candidato; os de `state` diferente de `SUCCEEDED` saem em `discarded.run_nao_sucedido`. O volume do run e `_volume_de(conjunto)` so quando o conjunto tem exatamente um `glue.job_run`; senao `None`. O custo e o `cost` do `glue.run_cost` com o mesmo `job_run_id` no conjunto.

**Rationale:** aceita os dois formatos que existem sem obrigar o operador a fatiar a saida do `analyze glue-job-runs`, e nunca liga scan a run por adivinhacao.

**Alternatives Rejected:** exigir um arquivo por run -- rejeitado: o formato do `analyze glue-job-runs` ficaria inutilizavel.

---

### Decision 2: Estatistica por lado e delta das medianas, com marcas por metrica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** para `execution_time_s`, `dpu_seconds` e `cost`, por lado: `n`, `median`, `min`, `max` sobre os runs que tem a medida. `delta = median_candidate - median_baseline`; `delta_pct = delta / median_baseline * 100` (arredondado a 1 casa; `null` com baseline 0). Marcas (`marks`) por metrica:
- `amostra_insuficiente`: `n < 3` em algum lado (vale para as tres metricas);
- `volume_diverge`: as medianas de volume dos lados diferem mais que `tolerancia * mediana_baseline` (vale para as tres);
- `volume_desconhecido`: algum lado sem nenhum run com volume (vale para as tres);
- `custo_indisponivel`: algum run sem `glue.run_cost`, ou mais de uma `currency` (so em `cost`).
A tolerancia e `volume_tolerance` do `workload.declared` do mesmo `job_name` em qualquer conjunto; senao 0,25 (a do capacity).

**Rationale:** mediana resiste a um run lento; a marca mostra o numero e diz por que ele nao e ganho (regra 20).

**Alternatives Rejected:** media -- um run de retry puxa o valor; esconder o delta marcado -- esconde o que foi medido.

---

### Decision 3: Recusas fixas e a capacidade como informacao

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** `refused` sempre com `economia_mensal` (`projecao_sobre_runs_que_nao_aconteceram`), `atribuicao_causal` (`sem_run_de_controle`) e `intervalo_de_confianca` (`amostra_pequena_use_mediana_e_faixa`). Cada lado traz `capacities`: as combinacoes (`glue_version`, `worker_type`, `number_of_workers`, `autoscaling`) com a contagem.

**Rationale:** regras 12 e 13; a mudanca de capacidade costuma ser a propria mudanca avaliada.

---

### Decision 4: Verbo de topo `gain`, tool READ_ONLY que declara caminho, dono `sf-verifier`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** CLI `sparkforge gain --baseline <facts> [...] --candidate <facts> [...]` (append, obrigatorios). Tool `sparkforge_gain`, `_READ_ONLY`, `baseline_paths` e `candidate_paths` (arrays de caminho): declara caminho, entao tools 94 -> 95, READ_ONLY 62 -> 63, as que declaram caminho 86 -> 87. `GainError` vira `AdapterError` codigo 2. Dono: `agents/executors/sf-verifier.md`, checagem 9 -- depois do Change Proof (checagem 7), o ganho observado.

**Alternatives Rejected:** `sf-extractor` (unico que cita `finops` hoje) -- rejeitado: ele extrai; comparar o antes e o depois de uma mudanca e verificacao.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/finops/realized.py` | Create | `realized_gain`, `GainError` | (general) | None |
| 2 | `tests/test_finops_realized.py` | Create | Estatistica, marcas, descarte, recusas, erros | (general) | 1 |
| 3 | `sparkforge/adapters/_core.py` | Modify | `gain(baseline_paths, candidate_paths)` | (general) | 1 |
| 4 | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py` | Modify | Verbo e tool | (general) | 3 |
| 5 | `fixtures/gain/` + `tests/test_fixtures_golden_gain.py` | Create | Casos pela CLI | (general) | 4 |
| 6 | Registros (lista, amostra, formas de erro, contagem de caminho 86 -> 87, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity, `sf-verifier` + sync) | Modify | Tool nova | (general) | 4 |
| 7 | `docs/realized-gain.md`, STATUS, contagens, surface, claims | Create/Modify | Doc e numeros | (general) | 6 |
| 8 | `.claude/sdd/reports/BUILD_REPORT_REALIZED_GAIN.md` | Create | Relatorio | (general) | 7 |

**Total Files:** ~20 (contando os casos de fixture)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| (general) | 1-8 | Nenhum agente do plugin cobre FinOps de Glue neste repositorio; build direto |

**Agent Discovery:** scanned `${CLAUDE_PLUGIN_ROOT}/agents/**/*.md`; o dono de produto e `sf-verifier`.

---

## Code Patterns

### Pattern 1: Estatistica de um lado

```python
from statistics import median


def _resumo(valores: list[float]) -> dict:
    if not valores:
        return {"n": 0, "median": None, "min": None, "max": None}
    return {"n": len(valores), "median": median(valores), "min": min(valores), "max": max(valores)}
```

### Pattern 2: Saida

```json
{
  "job_name": "etl_pedidos_diario",
  "baseline": {"runs": 10, "capacities": [{"worker_type": "G.1X", "number_of_workers": 10, "runs": 10}],
               "volume_median_bytes": 2000000000},
  "candidate": {"runs": 10, "capacities": [{"worker_type": "G.2X", "number_of_workers": 10, "runs": 10}],
                "volume_median_bytes": 2000000000},
  "metrics": {
    "execution_time_s": {"baseline": {"n": 10, "median": 900.0, "min": 0, "max": 0},
                         "candidate": {"n": 10, "median": 500.0, "min": 0, "max": 0},
                         "delta": -400.0, "delta_pct": -44.4, "marks": []}
  },
  "discarded": {"run_nao_sucedido": 0},
  "volume_tolerance": 0.25,
  "refused": [{"field": "economia_mensal", "reason": "projecao_sobre_runs_que_nao_aconteceram"}]
}
```

---

## Data Flow

```text
1. Adapter: um conjunto de facts por caminho de cada lado (`_load_facts_file`)
2. realized_gain: runs SUCCEEDED, custo por job_run_id, volume por conjunto de um run
3. job_name unico, lados nao vazios; senao GainError
4. Estatistica por lado e metrica; delta; marcas; capacidades; recusas
5. CLI imprime; tool devolve
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Nenhum | O verbo le facts ja extraidos | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | `realized_gain` com facts construidos: cada marca, descarte, erros, custo, tolerancia declarada | `tests/test_finops_realized.py` | pytest | AT-002..AT-011 |
| E2E | CLI sobre `fixtures/gain/` (recortes de `capacity/cheapest_that_fits`, `capacity/volume_filter_changes_the_answer`, `finops/cost_from_observed_dpu`) | `tests/test_fixtures_golden_gain.py` | pytest | AT-001, AT-005, AT-007 |
| Registros | Schema com amostra real e forma de erro | registros existentes | pytest | SC5 |

Medido para AT-001: em `capacity/cheapest_that_fits`, G.1X x10 (10 runs, mediana 900 s, 900 DPU-s) contra G.2X x10 (10 runs, 500 s, 1000 DPU-s), volume 2 GB nos dois: tempo -44,4%, DPU-s +11,1%. Para AT-005: `volume_filter_changes_the_answer`, G.2X x10 (100 MB) contra G.4X x10 (1 GB).

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `job_name` diferente entre os lados | `GainError` -> codigo 2, nomeando os jobs | No |
| Lado sem run `SUCCEEDED` | `GainError` -> codigo 2 | No |
| Arquivo ilegivel | O erro de `_load_facts_file`, codigo 2 | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `workload.declared.volume_tolerance` | float | 0,25 | Tolerancia de volume entre os lados (a mesma do capacity) |

---

## Security Considerations

- Leitura de facts pela porta que ja confina caminho dos outros verbos de topo; nada executado.
- Parametros de tool sem `url` no nome (INV-009).

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum; `discarded`, `marks` e `refused` na resposta |
| Metrics | O span de `call_tool` da tool nova |
| Tracing | N/A |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | design-agent | Versao inicial. A-002 confirmada (`cheapest_that_fits`: 3 capacidades x 10 runs, 2 GB); A-003: `_volume_de` so e usado pelo capacity, e e importado, nao copiado; dono `sf-verifier` |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_REALIZED_GAIN.md`
