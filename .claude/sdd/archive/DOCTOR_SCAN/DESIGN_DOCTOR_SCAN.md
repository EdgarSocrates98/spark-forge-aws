# DESIGN: Doctor e Scan

> Technical design for implementing Doctor e Scan (§22)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DOCTOR_SCAN |
| **Date** | 2026-09-13 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_DOCTOR_SCAN.md](./DEFINE_DOCTOR_SCAN.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
                         sparkforge scan [raiz] [--dry-run] [--format json|sarif] [--fail-on P0|P1] [--glue ...]
                                              |
                                              v
+------------------------- sparkforge/scan/plan.py (PURO) -------------------------+
|  manifest.json --(kind, sha256 via collect.base.verify_artifact)--> Entrada        |
|  varrer_source_files(raiz) --(.py .sql .tf .jsonl)--> Entrada                      |
|  .json solto -> Recusa(sem_manifesto) ; sha divergente -> Recusa(sha256_divergente)|
|  kind sem extrator -> Recusa(kind_sem_analyze) ; source sem job -> exige_job_name  |
+----------------------------------------------+-------------------------------------+
                                               | Plano(entradas, recusas, pulos)
                   --dry-run: imprime e para <-+
                                               v
+------------------------------ _core.scan (orquestra) ------------------------------+
|  para cada Entrada: _core.analyze_<x>(path, limit=None)  -- erro -> analyze_falhou  |
|  uniao -> fuse_facts -> judge_findings(runtime das flags)                           |
|  grava .sparkforge/scan/{facts_<analyze>.json, facts.json, findings.json,           |
|                          summary.json}                                               |
|  --format sarif -> report_github(findings, facts, repo) + report_github_write        |
+----------------------------------------------+-------------------------------------+
                                               v
                          summary (stdout / tool)  ; exit 1 se --fail-on disparar

                         sparkforge doctor [--repo .] [--online]
                                              |
+----------------------- _core.doctor (sonda as portas) -----------------------+
| installed_version, find_spec, build_server, load_catalog, pack_list,          |
| knowledge_path(freshness), code_status, collect_verify, boto3 (STS so online) |
+----------------------------------+-------------------------------------------+
                                   v  saidas cruas das portas
+-------------------- sparkforge/doctor.py (PURO) --------------------+
| avaliar_<id>(saida) -> Checagem{id,status,detail,unlock} ; resumo() |
+---------------------------------------------------------------------+
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/scan/plan.py` | Plano puro: manifesto + varredura -> entradas e recusas nomeadas | Python, `collect.base`, `facts.scan.varrer_source_files` |
| `sparkforge/scan/summary.py` | Resumo puro do que rodou: contagem por analyze, findings por severidade, recusas, pulos | Python |
| `sparkforge/doctor.py` | Avaliacao pura de cada checagem a partir da saida da porta; resumo e exit | Python |
| `_core.scan`, `_core.doctor` | Orquestram as portas que ja existem; unica camada que importa `_core` | `sparkforge/adapters/_core.py` |
| CLI `scan`, `doctor` | Verbos de topo | `argparse` em `adapters/cli.py` |
| Tools `sparkforge_scan`, `sparkforge_doctor` | Mesma funcao pelo MCP | `adapters/tools.py` |
| `fixtures/scan/` | Repositorios sinteticos com `.sparkforge/artifacts/` commitado | JSON, `.py`, `.tf`, `.sql`, `.jsonl` copiados de fixtures existentes |

---

## Key Decisions

### Decision 1: O scan roda `fuse` antes do `judge`, sempre

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** A-006 do DEFINE. A doc de 2026-09-13 mediu regras de Lake Formation e `SF-TIMEOUT-001` que so aparecem depois do `fuse`.

**Choice:** `facts.json` do scan e a saida do `fuse_facts` sobre a uniao; o `judge` roda sobre ele.

**Rationale:** Medido em 2026-09-13 em 6 casos (arquivo PySpark, event log, Terraform de FGAC, SQL + catalogo, facts de timeout, diretorio Terraform): o `fuse` so ACRESCENTA facts (3->4, 28->30, 17->21, 4->6, 5->9) e nenhum finding se perdeu; ganhou `SF-LF-005`, `SF-ATH-001` e `SF-TIMEOUT-001`. Um scan sem `fuse` calaria P0 de Lake Formation que o manual ensina a achar.

**Alternatives Rejected:**
1. `judge` sobre a uniao crua - rejeitado: perde as tres regras medidas.
2. Flag `--fuse` opcional - rejeitado: o default errado e o que o leigo usa, e nenhum caso medido perde finding com `fuse`.

**Consequences:**
- SC1 compara contra `analyze` -> `fuse` -> `judge`, o fluxo que os manuais ensinam.
- `facts.json` contem os derivados do `fuse`; `facts_<analyze>.json` guardam o que cada extrator emitiu.

---

### Decision 2: Plano puro por manifesto + extensao, e as recusas moram no plano

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** JSON de dump tem a mesma extensao para 10 extratores diferentes.

**Choice:** `plan(raiz)` le `.sparkforge/artifacts/manifest.json` (entrada = `kind` + `path`, sha256 conferido por `verify_artifact`) e varre o codigo por `varrer_source_files` (que ja pula `.sparkforge`, `.venv`, `vendor` e credenciais, com razao). Mapa fechado `KIND_PARA_ANALYZE`:

| `kind` do manifesto | analyze |
|---|---|
| `event_log` | `event-log` |
| `glue_job_run` | `glue-job-runs` (`--job-name` do `source` `glue:get_job_runs:{job}/{run}`) |
| `cloudwatch` | `cloudwatch` |
| `cloudwatch_logs` | `cloudwatch-logs` |
| `iceberg_metadata` | `iceberg` |
| `athena_workgroup` | `athena-workgroup` |
| `emr_cluster` / `emr_serverless` / `emr_eks` | `emr-cluster` / `emr-serverless` / `emr-eks` |
| `parquet_footer` | `parquet-footer` |
| `iam_access` | `iam-access` |
| `lakeformation` | `lakeformation-grants` |
| `glue_resource_link` | `glue-resource-link` |
| `terraform` (JSON de `collect glue-job`) | recusa `kind_sem_analyze`: o `analyze terraform` le HCL, e a definicao implantada nao tem extrator (medido pela doc de 2026-09-13) |

Extensao, fora de `.sparkforge/`: `.py` -> `pyspark` e `sql` (literal `spark.sql`, via `from_pyspark`); `.sql` -> `sql`; `.tf` -> `terraform`; `.jsonl` -> `event-log`; `.json` -> recusa `sem_manifesto`.

**Rationale:** O coletor ja declarou o tipo; farejar conteudo mandaria dump ambiguo ao extrator errado (decisao do brainstorm). Plano puro e testavel sem executar e e o que `--dry-run` imprime.

**Alternatives Rejected:**
1. Farejar chaves do JSON - rejeitado no brainstorm.
2. Um analyze por diretorio - rejeitado: um arquivo malformado derrubaria o diretorio inteiro; por arquivo, `analyze_falhou` isola (A-004 medido: os extratores aceitam arquivo unico).

**Consequences:**
- Um repositorio com muitos `.json` de configuracao (ex.: `package.json`) gera muitas recusas `sem_manifesto`; o resumo as agrupa por razao com contagem e a lista completa fica no `summary.json`.
- Mapa novo a manter junto dos `collect_*`: um teste cobra que todo `kind=` emitido em `sparkforge/collect/` esteja no mapa (analyze ou recusa declarada).

---

### Decision 3: Doctor com avaliacao pura separada da sondagem

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** Testar `warn`/`fail`/`skip` de nove checagens exigiria montar ambientes quebrados.

**Choice:** `_core.doctor` chama as portas e entrega a saida crua; `sparkforge/doctor.py` tem `avaliar_<id>(saida) -> Checagem` puro, testavel com dicionarios. A tool nunca recebe `online`.

**Rationale:** Cada status vira teste de unidade de uma linha; so a sondagem toca o ambiente. Medido: `pack_list` devolve `active/refused/env`, `knowledge_path(source_freshness=True)` traz `freshness_policy.counts`, `code_status` sem indice devolve `initialized`/`fresh`, `collect_verify` devolve `total/ok/missing/mismatched`.

**Alternatives Rejected:**
1. Reusar `forge doctor` - rejeitado: fora de escopo (DEFINE), e ele nao cobre MCP, packs, credencial.
2. Checagens com monkeypatch de ambiente em todo teste - rejeitado: frageis e lentos.

**Consequences:**
- `detail` e `unlock` sao texto do projeto (comando que resolve), nunca saida de rede.

---

### Decision 4: Ferramentas, anotacoes e donos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** `sparkforge_scan` `_WRITE_IDEMPOTENT` (grava em `.sparkforge/scan/`, repetir sobrescreve igual), declara `repo`; `sparkforge_doctor` `_READ_ONLY`, declara `repo`. Tools 95 -> 97; com caminho 87 -> 89; `READ_ONLY` 63 -> 64. Dono: executor `sf-inventory` (inventario do repositorio e do ambiente), checagem nova no corpo dele.

**Rationale:** A anotacao reflete o efeito; ambas confinam leitura a `repo`.

**Consequences:** entram em `test_only_case_and_report_writers_are_not_read_only` (scan) com razao escrita, e nos demais registros da memoria `tool-nova-move-registros-manuais` (itens 1-14).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/scan/__init__.py` | Create | Exporta `plan`, `Plano`, `Entrada`, `Recusa`, `resumo` | (general) | None |
| 2 | `sparkforge/scan/plan.py` | Create | Plano puro, `KIND_PARA_ANALYZE`, recusas | @python-developer | None |
| 3 | `sparkforge/scan/summary.py` | Create | Resumo puro | @python-developer | 2 |
| 4 | `sparkforge/doctor.py` | Create | `Checagem`, `avaliar_*`, `resumo` | @python-developer | None |
| 5 | `sparkforge/adapters/_core.py` | Modify | `scan()`, `doctor()`, escrita em `.sparkforge/scan/` | @python-developer | 2, 3, 4 |
| 6 | `sparkforge/adapters/cli.py` | Modify | Verbos `scan` e `doctor`, dispatch | @python-developer | 5 |
| 7 | `sparkforge/adapters/tools.py` | Modify | Schemas, entradas, handlers, mapa | @python-developer | 5 |
| 8 | `tests/test_scan_plan.py` | Create | Unidade do plano e do mapa contra os `kind=` dos coletores | @test-generator | 2 |
| 9 | `tests/test_doctor.py` | Create | Cada status de cada checagem; exit; tool sem `online` | @test-generator | 4, 5 |
| 10 | `fixtures/scan/<caso>/` | Create | `misto`, `json_solto`, `sha256_divergente`, `kind_sem_analyze`, `analyze_falhou`, `glue_job_run`, `sarif` | (general) | None |
| 11 | `tests/test_fixtures_golden_scan.py` | Create | Golden pela CLI em copia `tmp_path`; SC1 contra analyze->fuse->judge; SC4 contra `report github` | @test-generator | 6, 10 |
| 12 | `agents/executors/sf-inventory.md` | Modify | Checagem: doctor antes, scan para inventariar | (general) | 7 |
| 13 | Registros (`tests/test_adapters_tools.py`, `tests/test_harness_authorization.py`, `tests/test_fixtures_golden_mcp_parity.py`, `manifest.json`, `parity.yaml`) | Modify | Tool nova move registro manual | (general) | 7 |
| 14 | `docs/guia/usos/scan-e-doctor.md` (se o PR #62 estiver na main) + referencia regerada | Create | Manual simples; `python scripts/gen_reference_docs.py` | (general) | 6, 7 |
| 15 | `docs/superpowers/STATUS.md`, `CLAUDE.md`, `AGENTS.md`, `GUIA_DE_USO.md`, `.devin/README.md`, `docs/surface.lock.json`, `docs/claims.lock.json` + `docs/harness/*` | Modify | Contagens 95 -> 97, fixtures, surface, claims por id | (general) | 7, 10 |

**Total Files:** 15 entradas (7 casos de fixture)

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 2, 3, 4, 5, 6, 7 | Codigo Python puro com dataclasses e tipos, no molde dos modulos do projeto |
| @test-generator | 8, 9, 11 | Testes pytest de unidade e golden |
| (general) | 1, 10, 12, 13, 14, 15 | Registros manuais, fixtures e docs do proprio repositorio; build direto |

**Agent Discovery:**
- Scanned: `agents/**/*.md` do agentspec e do projeto
- Matched by: tipo de arquivo e proposito; build feito direto, como nas frentes anteriores

---

## Code Patterns

### Pattern 1: Plano puro

```python
from dataclasses import dataclass, field
from pathlib import Path

from sparkforge.collect.base import load_manifest, verify_artifact
from sparkforge.facts.scan import varrer_source_files

KIND_PARA_ANALYZE: dict[str, str | None] = {
    "event_log": "event-log",
    "glue_job_run": "glue-job-runs",
    "cloudwatch": "cloudwatch",
    "cloudwatch_logs": "cloudwatch-logs",
    "iceberg_metadata": "iceberg",
    "athena_workgroup": "athena-workgroup",
    "emr_cluster": "emr-cluster",
    "emr_serverless": "emr-serverless",
    "emr_eks": "emr-eks",
    "parquet_footer": "parquet-footer",
    "iam_access": "iam-access",
    "lakeformation": "lakeformation-grants",
    "glue_resource_link": "glue-resource-link",
    "terraform": None,  # JSON de `collect glue-job`: sem extrator
}
EXTENSAO_PARA_ANALYZE = {".py": ("pyspark", "sql"), ".sql": ("sql",), ".tf": ("terraform",),
                         ".jsonl": ("event-log",)}


@dataclass(frozen=True)
class Entrada:
    analyze: str
    path: str  # relativo a raiz, com barra
    origem: str  # "manifesto" | "extensao"
    job_name: str | None = None


@dataclass(frozen=True)
class Recusa:
    path: str
    reason: str  # sem_manifesto | sha256_divergente | kind_sem_analyze | exige_job_name
    detail: str = ""


@dataclass(frozen=True)
class Plano:
    entradas: tuple[Entrada, ...]
    recusas: tuple[Recusa, ...]
    pulos: tuple[dict, ...] = field(default=())
```

### Pattern 2: Checagem pura do doctor

```python
from dataclasses import dataclass

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"


@dataclass(frozen=True)
class Checagem:
    id: str
    status: str
    detail: str
    unlock: str | None = None


def avaliar_artefatos(verify: dict) -> Checagem:
    if verify["total_count"] == 0:
        return Checagem("artefatos", SKIP, "sem manifesto de artefatos coletados")
    ruins = verify["missing_count"] + verify["mismatched_count"]
    if ruins:
        return Checagem("artefatos", WARN, f"{ruins} artefato(s) ausente(s) ou divergente(s)",
                        "sparkforge collect verify --repo .")
    return Checagem("artefatos", OK, f"{verify['ok_count']} artefato(s) integro(s)")
```

### Pattern 3: Saida gravada (nomes fixos, nada do argv vira caminho)

```text
<repo>/.sparkforge/scan/facts_<analyze>.json   o que cada extrator emitiu (lista de facts)
<repo>/.sparkforge/scan/facts.json             uniao apos fuse (o que o judge viu)
<repo>/.sparkforge/scan/findings.json          itens do judge
<repo>/.sparkforge/scan/summary.json           plano, contagens, recusas, pulos, runtime
```

---

## Data Flow

```text
1. plan(raiz): manifesto (sha256) + varredura -> Plano(entradas, recusas, pulos)
   |
   v  (--dry-run: imprime o plano e sai 0)
2. para cada Entrada: _core.analyze_<x>(path, limit=None)["items"]; excecao -> Recusa(analyze_falhou)
   |
   v
3. uniao -> fuse_facts -> judge_findings(runtime das flags, limit=None)
   |
   v
4. grava .sparkforge/scan/*; --format sarif: report_github + report_github_write
   |
   v
5. summary no stdout/tool; exit 1 se --fail-on encontrar a severidade (P1 inclui P0)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| AWS STS (so `doctor --online`, so CLI) | boto3 `get_caller_identity` | Cadeia padrao do boto3 |
| Nenhum outro | - | - |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Plano, mapa contra os `kind=` de `sparkforge/collect/`, recusas | `tests/test_scan_plan.py` | pytest | AT-003, AT-004, AT-005, AT-007 |
| Unit | Cada status das 9 checagens; exit; tool sem `online` | `tests/test_doctor.py` | pytest | AT-009 a AT-013 |
| Golden (CLI) | Repositorios de `fixtures/scan/` copiados para `tmp_path` | `tests/test_fixtures_golden_scan.py` | pytest | AT-001, AT-002, AT-006, AT-008 |
| Igualdade | scan == analyze -> fuse -> judge a mao; SARIF == `report github` | idem | pytest | SC1, SC4 |
| Registros | Tools novas nos registros manuais | suites existentes | pytest | SC6 |

`fixtures/scan/*/repo/.sparkforge/artifacts/manifest.json` com sha256 real; A-001 conferido por `git check-ignore` no build. O golden roda sobre copia em `tmp_path` para o scan nunca gravar dentro de `fixtures/`, e fixa a raiz do repositorio (gate de wheel, memoria item 13).

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Raiz inexistente | `AdapterError` exit 2 | No |
| Manifesto ilegivel (JSON invalido) | `AdapterError` exit 2 nomeando o arquivo | No |
| Extrator levanta | `Recusa(analyze_falhou, detail=<tipo: mensagem curta>)`; os outros seguem | No |
| Nenhuma entrada no plano | Resumo com zero analyzes e exit 0; `judge` nao roda | No |
| `--fail-on` invalido | `AdapterError` exit 2 | No |
| Porta do doctor levanta | A checagem vira `fail` com a mensagem; as outras seguem | No |
| STS falha (`--online`) | `credencial_aws` = `warn` com o erro | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--dry-run` | bool | `false` | So o plano |
| `--format` | `json`\|`sarif` | `json` | SARIF pelo caminho do `report github` |
| `--fail-on` | `P0`\|`P1` | nenhum | Exit 1 se houver finding na severidade |
| `--glue/--spark/--python/--iceberg/--athena/--emr` | string | nenhum | Repassados ao `judge` |
| `doctor --online` | bool | `false` | So CLI; chama STS |

---

## Security Considerations

- Sem rede no scan e na tool do doctor; STS so por `--online` na CLI.
- Varredura herda a poda de credenciais (`DIRETORIOS_SENSIVEIS`, `.pem`, `.env`, `.tfstate`), relatada como pulo.
- Caminhos de escrita fixos em `<repo>/.sparkforge/scan/`. Entrada do manifesto com caminho absoluto ou que resolve fora da raiz sai com a recusa `fora_da_raiz` (sexta recusa, acrescentada no design ao conjunto do DEFINE) e nunca e lida.
- Artefato so e analisado com sha256 conferido.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum; o `summary.json` e o registro |
| Metrics | Contagens no resumo (analyzes, facts, findings por severidade, recusas por razao) |
| Tracing | Spans de tool pelo `call_tool`, como toda tool |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | design-agent | Versao inicial; A-004 e A-006 medidos |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_DOCTOR_SCAN.md`
