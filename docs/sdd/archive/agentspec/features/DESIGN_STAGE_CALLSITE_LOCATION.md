# DESIGN: Stage → linha de codigo

> Technical design for implementing Stage → linha de codigo

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STAGE_CALLSITE_LOCATION |
| **Date** | 2026-09-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_STAGE_CALLSITE_LOCATION.md](./DEFINE_STAGE_CALLSITE_LOCATION.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
localizar(finding, facts_por_id, raizes, existe, callsites=...)
  │
  ├─ 1. subject localizavel (source_location/tf_resource/plan_node)  ── ja existia
  ├─ 2. fact de evidencia de CODIGO                                   ── ja existia
  ├─ 3. NOVO: caminho de stage
  │      quem entra: subject.type == stage
  │                  OU fact de stage na evidencia (job_run/table)
  │      chave: (stage_id, artefato)  artefato = provenance.artifact do fact de stage
  │             sem fact de stage → so stage_id, e o callsite precisa ser unico
  │      callsite resolvido (Python) → sufixos de attrs.path contra as raizes
  │      callsite arquivo_nao_python → ^(\w+) at (.+):(\d+)$ no symbol
  │      → Localizado(uri, line, col=None, nota="linha da acao X que originou o stage N (nao e a causa)")
  │      → Recusa(callsite_ausente | callsite_sem_forma | callsite_nao_python |
  │               callsite_ambiguo | caminho_ambiguo | arquivo_fora_do_repo)
  └─ 4. recusas antigas (evidencia_ausente, runtime, sem_linha)

projetar → indice_de_callsites(facts_por_id) uma vez → passa a localizar
_mensagem(finding, local) → acrescenta local.nota
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/reporting/locate.py` | `indice_de_callsites`, `_caminho_de_stage`, `_por_sufixo`; `Localizado.nota`; motivos novos em `MOTIVOS` | Python puro |
| `sparkforge/reporting/github.py` | Constroi o indice uma vez; `_mensagem` acrescenta a nota ao resultado SARIF, a anotacao e a linha do resumo | Python puro |
| `sparkforge/adapters/tools.py` | Enum `reason` do `_REPORT_GITHUB_SCHEMA` com os motivos novos | — |
| `fixtures/sarif/{stage_python,stage_scala,stage_negativos}/` | Casos novos | JSON + event log + arvore |
| `tests/test_reporting_github.py` | Unidade dos caminhos de stage e invariante do corpus ("nenhum stage sai `runtime`") | pytest |
| `tests/test_fixtures_golden_sarif.py` | Lista de casos: 4 → 7; cobertura de motivos | pytest |
| `.github/workflows/ci.yml` | `stage_python` na matriz do `sarif-upload` | Actions |

---

## Key Decisions

### Decision 1: a chave e (stage_id, artefato), e o artefato vem do fact de stage da evidencia

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o `stage_id` recomeca em 0 em cada aplicacao Spark. Na uniao de dois event logs, o stage 0 de um nao e o do outro. Medido em 2026-09-11: 27 dos 28 findings de stage citam um fact de stage com `provenance.artifact`, e os 34 pares (fact de stage, callsite do mesmo `stage_id`) do corpus tem o mesmo artefato (A-002).

**Choice:**
- `indice_de_callsites` agrupa os `spark.stage.callsite` da uniao por `(stage_id, artifact)`.
- O finding usa o artefato do primeiro fact de stage da sua evidencia com o mesmo `stage_id` do subject; para `job_run`/`table`, o primeiro fact de stage da evidencia.
- Sem fact de stage na evidencia, busca so por `stage_id`: um artefato unico e usado; mais de um vira `callsite_ambiguo`; nenhum, `callsite_ausente`.

**Rationale:** usar so o `stage_id` poria o alerta na acao de outro job.

**Alternatives Rejected:**
1. So `stage_id`: colide entre event logs.
2. Recusar sempre sem artefato: jogaria fora o caso comum de um event log so.

**Consequences:**
- A regra do "unico" e testada com dois event logs (AT-003, AT-009).

---

### Decision 2: maior sufixo unico, parando no primeiro nivel que casa

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `attrs.path` (`/opt/spark/work/jobs/lib/job.py`) vira as partes `[opt, spark, work, jobs, lib, job.py]`. Para cada sufixo, do mais longo ao mais curto, testa `<raiz>/<sufixo>` em cada `--source-root`:
- o primeiro nivel com exatamente um arquivo vence;
- um nivel com dois ou mais e `caminho_ambiguo`, e para ali;
- nenhum nivel casa, e `arquivo_fora_do_repo`.

Para Scala so existe o nome base (`Etl.scala`), e o mesmo algoritmo roda com uma parte so.

**Rationale:** um sufixo mais longo e evidencia mais forte. Cair para o nome base depois de um empate trocaria ambiguidade por chute.

---

### Decision 3: Scala pelo `symbol`, com padrao estrito

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** para callsite nao-Python, o extrator grava `resolved: false`, `reason: arquivo_nao_python` e so `attrs.file`, sem linha. A linha esta no nome do stage (`save at Etl.scala:120`).

**Choice:** a regex `^(?P<metodo>\w+) at (?P<arquivo>[^:\s]+):(?P<linha>\d+)$` sobre `subject.symbol`. Casou e o arquivo existe: localiza. Casou e o arquivo nao existe: `callsite_nao_python`. Nao casou: `callsite_sem_forma`. Linha 0 nao casa (`\d+` com o valor >= 1 conferido depois).

**Rationale:** o golden do event log fica intacto (nenhum extrator muda). A derivacao fica na apresentacao, que e onde o repositorio a precisa.

**Alternatives Rejected:**
1. Mudar o extrator para gravar a linha do Scala: refaria goldens de event log e de ponte.

---

### Decision 4: a nota viaja no `Localizado`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `Localizado` ganha `nota: str | None = None`, preenchida so pelo caminho de stage: "linha da acao `<metodo>` que originou o stage `<id>` (nao e a causa)". O `_mensagem` passa a receber o `Localizado` e acrescenta ` -- <nota>` quando ela existe. Resultado SARIF, anotacao e linha do resumo usam a mesma mensagem.

**Rationale:** um texto so para as tres saidas. O default `None` mantem os 4 goldens anteriores byte a byte (A-004 conferida: nenhum deles tem stage na evidencia).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/reporting/locate.py` | Modify | Indice, caminho de stage, sufixo, Scala, motivos | @agentspec:python:python-developer | None |
| 2 | `sparkforge/reporting/github.py` | Modify | Indice uma vez; nota na mensagem | @agentspec:python:python-developer | 1 |
| 3 | `sparkforge/adapters/tools.py` | Modify | Enum de `reason` com os 4 motivos novos | (general) | 1 |
| 4 | `tests/test_reporting_github.py` | Modify | Unidade (AT-001 a AT-009) + invariante do corpus | @agentspec:test:test-generator | 1, 2 |
| 5 | `fixtures/sarif/{stage_python,stage_scala,stage_negativos}/` | Create | Casos novos, derivados de `fixtures/bridge/` | (general) | 2 |
| 6 | `tests/test_fixtures_golden_sarif.py` | Modify | 7 casos; cobertura de motivos | (general) | 5 |
| 7 | `.github/workflows/ci.yml` | Modify | `stage_python` na matriz | (general) | 5 |
| 8 | `docs/github-code-scanning.md`, `docs/superpowers/STATUS.md` | Modify | Motivos novos; denominador 0/28 | (general) | all |
| 9 | `docs/surface.lock.json`, `docs/claims.lock.json` + docs auditados | Modify (se o gate acusar) | Gates | (general) | all |
| 10 | `.claude/sdd/reports/BUILD_REPORT_STAGE_CALLSITE_LOCATION.md` | Create | Relatorio | (general) | all |

**Total Files:** 10 entradas.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 1, 2 | Funcoes puras |
| @agentspec:test:test-generator | 4 | Pares positivo/negativo |
| (general) | 3, 5–10 | Registros e fixtures deste repositorio |

**Agent Discovery:**
- Scanned: agentes do plugin e os da sessao.
- Matched by: tipo de arquivo e palavra-chave.
- O build pode ficar direto, como no PR #50: o escopo e um modulo.

---

## Code Patterns

### Pattern 1: indice e sufixo (`locate.py`)

```python
CALLSITE_KIND = "spark.stage.callsite"
_SIMBOLO_JVM = re.compile(r"^(?P<metodo>\w+) at (?P<arquivo>[^:\s]+):(?P<linha>\d+)$")


def indice_de_callsites(
    facts_por_id: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[Any, str], list[Mapping[str, Any]]]:
    indice: dict[tuple[Any, str], list[Mapping[str, Any]]] = {}
    for fact in facts_por_id.values():
        if fact.get("kind") != CALLSITE_KIND:
            continue
        chave = (
            (fact.get("subject") or {}).get("stage_id"),
            str((fact.get("provenance") or {}).get("artifact") or ""),
        )
        indice.setdefault(chave, []).append(fact)
    return indice


def _por_sufixo(
    partes: Sequence[str], raizes: Sequence[str], existe: Callable[[str], bool]
) -> str | Recusa:
    for inicio in range(len(partes)):
        sufixo = "/".join(partes[inicio:])
        achados = sorted(
            {
                (PurePosixPath(sufixo) if r in (".", "") else PurePosixPath(r) / sufixo).as_posix()
                for r in raizes
            }
            & {c for c in _candidatos(sufixo, raizes) if existe(c)}
        )
        if len(achados) == 1:
            return achados[0]
        if len(achados) > 1:
            return Recusa("caminho_ambiguo")
    return Recusa("arquivo_fora_do_repo")
```

(O build simplifica `_candidatos`, porque o conjunto dos candidatos e o proprio conjunto montado acima. O padrao mostra a ordem e a parada.)

### Pattern 2: mensagem com a nota (`github.py`)

```python
def _mensagem(finding: Mapping[str, Any], local: Localizado | None = None) -> str:
    base = ...  # titulo + (medido: ...), como hoje
    if local is not None and local.nota:
        return f"{base} -- {local.nota}"
    return base
```

---

## Data Flow

```text
1. projetar recebe findings, facts_por_id, raizes, existe
2. indice = indice_de_callsites(facts_por_id)            (uma vez)
3. para cada finding: localizar(..., callsites=indice)
     subject → evidencia de codigo → caminho de stage → recusas antigas
4. resultados, anotacoes e resumo com _mensagem(finding, local)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| GitHub Code Scanning | `sarif-upload` (matriz ganha `stage_python`) | `GITHUB_TOKEN` |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Chave com artefato, sem artefato unico/ambiguo, sufixo mais longo, empate sem fallback, Scala casa/nao casa/fora do repo, sem forma, ausente, nota na mensagem | `tests/test_reporting_github.py` | pytest | Todos os ramos novos |
| Invariant | Corpus: nenhum finding com stage sai `runtime`; SARIF + recusa = total | `tests/test_reporting_github.py` | pytest | 28 findings de stage |
| Golden | 7 casos (4 intactos + 3 novos) byte a byte, schema OASIS, CLI real | `tests/test_fixtures_golden_sarif.py` | pytest | AT-001 a AT-011 |
| E2E | `sarif-upload` com `stage_python` | `ci.yml` | GitHub | AT-012 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Callsite com `line` ausente, 0 ou nao inteiro | `callsite_sem_forma` | No |
| `attrs.path` vazio num callsite resolvido | Usa `attrs.file` como unico sufixo | No |
| Fact de stage da evidencia com `stage_id` diferente do subject | Ignorado; procura o proximo | No |

---

## Configuration

Nenhuma. Nao ha flag nova: as raizes continuam sendo as `--source-root`.

---

## Security Considerations

- Nenhum caminho novo sai do repositorio: o sufixo passa pelo mesmo `existe` confinado a `--repo`.
- O `symbol` do stage vem do event log (artefato externo). Ele so entra na mensagem pelo `metodo` casado por `\w+` e pelo `stage_id`, e o escape de anotacao continua aplicado.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | A linha de contagem do stderr, sem mudanca |
| Metrics | N/A |
| Tracing | N/A |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Itens 1–2 + unidade (item 4) | Unidade verde; os 4 goldens anteriores intactos |
| B2 | Item 3; invariante do corpus | Tool valida; nenhum stage `runtime` |
| B3 | Itens 5–6 | 7 goldens verdes |
| B4 | Itens 7–9; suite, gates, Snyk | Tudo verde |
| B5 | Commit, push, PR (base `feat/sarif-github-check`), `workflow_dispatch` | SC7 |
| B6 | Item 10 e statuses | — |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | design-agent | Versao inicial; A-002, A-003 e A-004 conferidas |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_STAGE_CALLSITE_LOCATION.md`
