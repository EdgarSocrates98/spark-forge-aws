# DESIGN: Portas de CLI faltando

> Technical design for implementing CLI Ports: `analyze workload`, utilização no `fuse` e `collect parquet-footer`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CLI_PORTS |
| **Date** | 2026-09-14 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_CLI_PORTS.md](./DEFINE_CLI_PORTS.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 workload.yaml ──> analyze workload (CLI + tool READ_ONLY) ──> workload.declared ─┐
      │                                                                          │
      └─ na raiz: scan/plan.py Entrada(workload, workload.yaml, origem=nome)      ├─> capacity / finops / workload
                                                                                  │
 analyze cloudwatch ──> glue.metric ─┐                                           │
 analyze event-log  ──> spark.stage.task_duration ─┤                             │
                                     v                                           │
                    fusion.fuse(): se ha glue.metric ──> extract_utilization     │
                                     │                  (glue.utilization.summary|unresolved)
                                     v
                                  judge ──> SF-WASTE-001 / SF-WASTE-002

 collect parquet-footer (CLI + tool open-world) ──> collect/parquet_footer.collect_parquet_footer
      └─> .sparkforge/artifacts/<footer>.json + manifesto (kind parquet_footer, sha256)
            └─> scan: KIND_PARA_ANALYZE["parquet_footer"] ──> analyze parquet-footer
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/facts/utilization.py` | Ganha `SOURCE_KINDS = frozenset({"glue.metric"})`, a guarda que o `fuse` consulta | constante |
| `sparkforge/facts/fusion.py` | Deriva a utilização depois do timeout, com a asserção de namespace | molde do bloco de timeout |
| `sparkforge/adapters/_core.py` | `analyze_workload` (+ `_extract_workload_facts`), `collect_parquet_footer`, e `"workload"` em `_scan_extrair` | molde de `analyze_consumers` e `collect_athena_workgroup` |
| `sparkforge/scan/plan.py` | `workload.yaml` da raiz vira `Entrada("workload", "workload.yaml", "nome")` | uma checagem de arquivo |
| `sparkforge/adapters/cli.py` | `analyze workload` e `collect parquet-footer` | argparse |
| `sparkforge/adapters/tools.py` | `sparkforge_analyze_workload` (`_READ_ONLY`) e `sparkforge_collect_parquet_footer` (`_WRITE_LOCAL_OPEN_WORLD`) | schemas existentes (`_ANALYZE_FACTS_SCHEMA`, `_COLLECT_ARTIFACT_SCHEMA`) |

---

## Key Decisions

### Decision 1: A utilização deriva no `fuse`, guardada pela presença de `glue.metric`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** Os golden de `fixtures/waste` derivam o resumo dentro do teste. Medido no design, `extract_utilization(run_fuse(input))` bate com `expected/facts.json` nos 5 casos, então a derivação sobre o pool fundido é a mesma. Fora de `fixtures/waste`, nenhum golden tem `glue.metric`.

**Choice:** Depois do bloco de timeout: `if any(f.kind in UTILIZATION_SOURCE_KINDS for f in facts)`, chama `extract_utilization(facts, "")`, confere os kinds contra `utilization.EMITTED_KINDS` e acrescenta ao `combined`. A derivação recebe o `facts` de entrada, como o timeout recebe, e não o pool já derivado.

**Rationale:** Sem a guarda, todo pool sem CloudWatch que tivesse qualquer fact ganharia um `glue.utilization.unresolved`, e isso mudaria todo golden de fusion e do `scan`. Com ela, quem não tem a métrica não vê diferença (SC3).

**Alternatives Rejected:**
1. Derivar sempre: rejeitado pela razão acima.
2. Verbo próprio `analyze utilization`: rejeitado no brainstorm, porque repete o defeito do timeout sem porta.

**Consequences:**
- O `fixtures/waste/sem_cloudwatch` (pool sem `glue.metric`) não ganha a sentinela pelo `fuse`. O golden de waste continua derivando pelo extrator direto, sem mudança.
- `fuse` + `judge` passam a produzir SF-WASTE-001/002.

### Decision 2: `analyze workload` no molde de `analyze consumers`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Choice:**
- `_extract_workload_facts(path)`: caminho inexistente vira `AdapterError` exit 2 com o comando que resolve, como no `consumers`. O extrator trata o arquivo ausente como sentinela, mas aqui o operador apontou para ele: apontar para o nada é erro de entrada.
- Arquivo existente chama `extract_workload_path(p, repo_root=p.parent)`, que reproduz o `anchor` do golden (A-004 medido).
- Sai por `_facts_page(facts, "workload.unresolved", ...)`.
- A CLI tem `--path`, `--out`, `--kind`, `--limit`, `--cursor` e `--detail-level`. A tool recebe `path`.

### Decision 3: O `scan` lê `workload.yaml` só da raiz

**Choice:** Em `plan()`, depois do manifesto, se `(raiz / "workload.yaml").is_file()`, acrescenta `Entrada("workload", "workload.yaml", "nome")`. `_scan_extrair` ganha `"workload": analyze_workload`. Subpasta não é lida (YAGNI).

### Decision 4: `collect parquet-footer` no molde dos coletores

**Choice:**

```python
def collect_parquet_footer(repo: str, *, prefix: str, now: str, max_files: int = 50) -> dict[str, Any]:
    rel_path = collect_parquet.parquet_footer_path(prefix)
    try:
        entry = collect_parquet.collect_parquet_footer(prefix, Path(repo), now=now, max_files=max_files)
    except ValueError as exc:
        raise AdapterError(f"{exc}\n  Rode: sparkforge collect parquet-footer --repo ... --prefix ... --max-files <1..teto>", exit_code=2) from exc
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)
```

- O padrão de `max_files` vem de `_MAX_FILES_PADRAO` do coletor, e não de um número copiado para cá.
- A tool tem `repo`, `prefix`, `now` e `max_files`, com `_WRITE_LOCAL_OPEN_WORLD` e `_COLLECT_ARTIFACT_SCHEMA`.
- A classe `CLOUD_MUTATION` entra em `permissions.ask` pela policy do §16, e por isso `policy sync-settings` regrava o `.claude/settings.json`.
- O pyarrow ausente sobe como `CollectorUnavailable`, e `_collect_error` deve citar o `pip install`. Se não citar, a mensagem é ajustada ali (AT-009).

### Decision 5: Casos novos em domínios que já existem

**Choice:** `fixtures/scan/workload_na_raiz/` (repositório com `workload.yaml` e um `job.py`) prova o AT-010 no golden do `scan`. SF-WASTE pelo `fuse` é provado por teste novo sobre os `fixtures/waste` existentes, e o coletor por teste com Parquet gerado em `tmp_path`. Nenhum domínio novo entra.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/facts/utilization.py` | Modify | `SOURCE_KINDS` | @python-developer | None |
| 2 | `sparkforge/facts/fusion.py` | Modify | Derivação guardada | @python-developer | 1 |
| 3 | `sparkforge/adapters/_core.py` | Modify | `analyze_workload`, `collect_parquet_footer`, `_scan_extrair` | @python-developer | None |
| 4 | `sparkforge/scan/plan.py` | Modify | `workload.yaml` da raiz | @python-developer | 3 |
| 5 | `sparkforge/adapters/cli.py` | Modify | Dois comandos | @python-developer | 3 |
| 6 | `sparkforge/adapters/tools.py` | Modify | Duas tools | @python-developer | 3 |
| 7 | `fixtures/scan/workload_na_raiz/` | Create | Golden do `scan` | @test-generator | 4 |
| 8 | `tests/test_cli_ports.py` | Create | AT-001 a AT-011 | @test-generator | 1-6 |
| 9 | Registros de tool nova (lista, amostra real, FAILABLE, writers, harness 94, paridade MCP, `parity.yaml`, `manifest.json`, agentes + `sync_skills`), `.claude/settings.json` (`policy sync-settings`), surface, claims, referência | Modify | Tool nova | (general) | 6 |
| 10 | `docs/guia/usos/{custo-e-capacidade,iceberg-e-parquet,scan-e-doctor}.md`, STATUS, contagens, memória de lacunas | Modify | Docs | (general) | 5, 6 |

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1-6 | Portas finas sobre código existente |
| @test-generator | 7, 8 | Golden e unidade |
| (general) | 9, 10 | Registros e docs do repositório |

---

## Code Patterns

### Pattern 1: Derivação guardada no `fuse`

```python
    if any(f.kind in UTILIZATION_SOURCE_KINDS for f in facts):
        derivados_util = extract_utilization(facts, "")
        desconhecidos_util = {f.kind for f in derivados_util} - UTILIZATION_EMITTED_KINDS
        if desconhecidos_util:
            raise AssertionError(
                f"kind fora do namespace de utilization: {sorted(desconhecidos_util)}"
            )
        for fact in derivados_util:
            combined[fact.id] = fact
```

### Pattern 2: Entrada por nome no plano do `scan`

```python
WORKLOAD_NA_RAIZ = "workload.yaml"

    if (raiz / WORKLOAD_NA_RAIZ).is_file():
        entradas.append(Entrada("workload", WORKLOAD_NA_RAIZ, "nome"))
```

---

## Data Flow

```text
operador: analyze cloudwatch --out cw.json ; analyze event-log --out el.json ; analyze workload --path workload.yaml --out wl.json
       -> fuse --facts cw.json --facts el.json -> (glue.utilization.summary) -> judge -> SF-WASTE-00x
       -> capacity/finops --facts wl.json ... -> SLA declarado na resposta
scan:  manifesto (parquet_footer) + extensão + workload.yaml na raiz -> analyzes -> fuse (com utilização) -> judge
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| S3 (só com `--prefix s3://`) | pyarrow lê o footer | cadeia padrão do pyarrow; nenhum cliente boto3 novo |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit/golden | `analyze workload` contra `fixtures/workload`; YAML ausente e malformado | `tests/test_cli_ports.py` | pytest | AT-001 a AT-003 |
| Golden pelo `fuse` | `run_fuse` + `judge` sobre `fixtures/waste`, sem chamar o extrator no teste | `tests/test_cli_ports.py` | pytest | AT-004 a AT-006, SC2 |
| Não regressão | goldens de fusion e do `scan` intactos | suítes existentes | pytest | SC3 |
| Coletor | Parquet local via pyarrow em `tmp_path`; manifesto; `collect verify`; `scan --dry-run`; pyarrow ausente por monkeypatch | `tests/test_cli_ports.py` | pytest | AT-007 a AT-009 |
| Scan | `fixtures/scan/workload_na_raiz` e subpasta | golden do `scan` + unidade | pytest | AT-010 |
| Registros | 102 tools, 94 com caminho | suítes existentes | pytest | AT-011, SC7 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `workload.yaml` inexistente no `analyze` | `AdapterError` exit 2, com o comando | No |
| YAML inválido | `workload.unresolved` (`read_error`), pelo extrator | No |
| `max_files` fora da faixa | `AdapterError` exit 2 | No |
| pyarrow ausente, S3 negado | `_collect_error`, ou `status` no artefato (o coletor já classifica) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--max-files` | int | `_MAX_FILES_PADRAO` do coletor | Amostra declarada (os N primeiros pelo nome) |

---

## Security Considerations

- O coletor lê só o footer, e nenhuma linha de dado.
- `prefix` S3 usa a credencial da cadeia padrão. A tool é open-world e entra em `ask` pela policy.
- `analyze workload` lê o arquivo que o operador apontou, sem varredura.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum novo |
| Metrics | Nenhuma nova |
| Tracing | As duas tools passam por `call_tool` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | design-agent | Versão inicial. A-001 e A-004 medidos (5/5 e 2/2 iguais ao golden) |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_CLI_PORTS.md`
