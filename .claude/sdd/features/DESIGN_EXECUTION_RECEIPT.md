# DESIGN: Execution Receipt

> Technical design for EXECUTION_RECEIPT

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXECUTION_RECEIPT |
| **Date** | 2026-09-12 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_EXECUTION_RECEIPT.md](./DEFINE_EXECUTION_RECEIPT.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
 CLI  sparkforge receipt emit|verify           MCP  sparkforge_receipt_emit (LOCAL_MUTATION)
            │                                        sparkforge_receipt_verify (READ_ONLY)
            └──────────────┬─────────────────────────────┘
                           v
 adapters/_core.py  receipt_emit / receipt_verify / receipt_write      (camada de adapter)
   - confina todo caminho declarado a --repo (is_relative_to)
   - findings  -> _signature_parts(findings_path)         (ja existe, report sign)
   - report    -> _split_report + _BLOCK_SIGNATURE        (ja existe, report sign)
   - spans     -> shared_ledger().spans_of(run_id)        (buffer + traces.db)
   - host      -> extract_host_transcript_path(path)      (ja existe, telemetry export)
                           │  entradas ja lidas + caminhos relativos + now
                           v
 sparkforge/receipt/  (modulo novo, nao importa adapters nem provider)
   _hash.py    text_sha256(path)  CRLF->LF ; receipt_digest(doc) via findings.models._canonical
   build.py    build(...) -> dict      partes: case, evidence, judgment, decision, proof,
                                               tools, host, actions, unresolved, refused
   verify.py   verify(doc, ...) -> dict   ordem fixa: version, integrity, case, evidence,
                                          judgment, decision, proof, tools, host
                           │
                           v
 <repo>/.sparkforge/receipts/<receipt_id>.json   (temp + replace; commitavel; sem conteudo)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/receipt/__init__.py` | Reexporta `build`, `verify`, `RECEIPT_VERSION`, `RECEIPT_PREFIX` | stdlib |
| `sparkforge/receipt/_hash.py` | `text_sha256(path)` (bytes com `\r\n` trocado por `\n`), `digest_of(obj)` (sha256 do JSON canonico), `receipt_id_of(doc)` | `hashlib`; `findings.models._canonical` |
| `sparkforge/receipt/build.py` | Monta as partes a partir de caminhos relativos ja confinados, dos findings ja lidos, dos spans e dos facts `host.*` ja extraidos | stdlib |
| `sparkforge/receipt/verify.py` | Recalcula cada parte, devolve `{valid, status, diverged, checks, not_rechecked, not_evaluable}` | stdlib |
| `adapters/_core.py` | `receipt_emit`, `receipt_verify`, `receipt_write`: confinamento, leitura de findings/report/spans/host pelas funcoes que ja existem, escrita em temp + `replace` | — |
| `adapters/cli.py` | Grupo `receipt` com `emit` e `verify` | argparse |
| `adapters/tools.py` | `sparkforge_receipt_emit` (`_WRITE_IDEMPOTENT`) e `sparkforge_receipt_verify` (`_READ_ONLY`), schemas e handlers | — |
| `agents/executors/sf-synthesizer.md` (+ espelhos) | Passo novo depois de `telemetry_export` | — |
| `fixtures/receipt/` | Case sintetico completo e o golden | — |

---

## Key Decisions

### Decision 1: o modulo nao le findings, report nem spans; o adapter le e passa

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** DEFINE A-005. `_signature_parts`, `_split_report` e os regex do bloco de assinatura moram so em `adapters/_core.py:4246-4436`. O `shared_ledger()` mora em `observability/`, e o leitor do transcript em `facts/host_transcript.py`.

**Choice:** `sparkforge/receipt/` recebe dados ja lidos: `findings_parts` (o retorno de `_signature_parts`), `report_signature` (o `sig_...` do bloco, ou `None`), `spans` (lista de dicts) e `host_facts` (os facts `host.*`). O modulo so abre arquivo para hashear, por caminho relativo que o adapter ja confinou.

**Rationale:** mantem o modulo testavel com entrada sintetica (spans com `span_id` fixo dao golden estavel) e reusa as funcoes que ja carregam as mensagens de erro do `report sign`, sem mover codigo testado.

**Alternatives Rejected:**
1. Mover `_split_report`/`_signature_parts` para `findings/`: mexe no `report sign`, que esta fora do escopo, por ganho nenhum aqui.
2. O modulo importar `adapters._core`: inverte a camada; `agents/autonomy.py` so faz isso com import local e com justificativa escrita.

**Consequences:**
- O adapter fica com as leituras, e a validacao de findings (vazio, `catalog_version` divergente) sai com a mesma mensagem e o mesmo exit 2 do `report sign`.
- O modulo nao sabe de onde o span veio: quem garante que e o run certo e o adapter.

---

### Decision 2: spans vem do `shared_ledger()`, e o recibo guarda o `span_id`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** DEFINE A-008, medido em `observability/context_ledger.py`:
- `call_tool` chama `record()` **depois** que o handler devolve (`payload_bytes(resultado)`), e `record()` so anexa a um buffer em memoria.
- O disco so recebe no `flush()`, e o unico gatilho automatico e o `atexit`.
- `shared_ledger().spans_of(run_id)` junta buffer e disco.

Tres consequencias:
1. Numa sessao MCP, os spans do run ainda estao no buffer. Ler o `traces.db` direto daria lista vazia.
2. O span do proprio emit nao existe quando o handler roda. Ele fica fora naturalmente, sem filtro.
3. Depois do `atexit`, o run ganha os spans posteriores ao emit: o proprio emit, verifies, `next_step`. "Todos os spans do run" no verify seria outro conjunto.

**Choice:**
- O emit le por `shared_ledger().spans_of(run_id)`.
- Cada span entra com `span_id`, `name`, `status`, `outcome`, `payload_bytes`, `detail_level`, `start_time`, `end_time`, ordenados por (`start_time`, `span_id`). `spans_sha256` e o digest dessa lista. Os nomes sao os das colunas de `spans` (o DEFINE G5 dizia `start`/`end`).
- `tools.excluded` declara o span do emit, com a razao `gravado_depois_do_handler`.
- O verify seleciona do run **so os `span_id` do recibo**:
  - todos presentes: recalcula e compara;
  - nenhum presente: `not_rechecked`, com `run_ausente` ou `traces_db_ausente`;
  - parte presente: `diverged`, com os `span_id` que faltam.
- Os spans posteriores ao emit sao contados em `checks.tools.spans_after_emit` e nao entram na comparacao.

**Rationale:** e a unica leitura que ve o proprio processo MCP e o disco. Ancorar no `span_id` torna o verify estavel antes e depois do `atexit`.

**Alternatives Rejected:**
1. Ler `traces.db` com `SQLiteTraceStore` direto: vazio na sessao MCP ate o processo morrer.
2. Forcar `flush()` no emit: grava `status="running"` no meio da sessao e muda o `traces.db` como efeito colateral de uma tool que so deveria gravar o recibo.
3. Comparar "todos os spans do run": qualquer chamada depois do emit faria o recibo divergir.

**Consequences:**
- O `span_id` e aleatorio (`uuid4`), entao o golden usa spans sinteticos passados direto ao `build`.
- Na tool, sem `run_id`, o default e `shared_ledger().run_id`, o run do proprio processo. Isso e medido, nao deduzido.
- Na CLI, o processo novo nao tem span de tool. Sem `--run-id`, `tools` sai `unresolved` (`run_id_nao_declarado`).

---

### Decision 3: hash de texto com CRLF normalizado, e `receipt_id` sobre o JSON canonico

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:**
- Todo artefato que o recibo amarra e texto: JSON, YAML, JSONL, Markdown e o transcript JSONL.
- O checkout do git no Windows pode trocar os finais de linha.
- Ja existem seis helpers de JSON canonico no pacote.

**Choice:**
- `text_sha256(path) = sha256(path.read_bytes().replace(b"\r\n", b"\n"))`.
- `receipt_id = "rcpt_" + sha256(_canonical(doc_sem_receipt_id))`, usando `findings.models._canonical`: `sort_keys`, `separators=(",", ":")` e `ensure_ascii=True`.
- O arquivo e gravado com `json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`.
- A integridade recalcula sobre o JSON **parseado**, entao reformatar o arquivo nao quebra o recibo, e mudar qualquer valor quebra.
- `receipt_version: 1` entra no hash, e com ela a regra de normalizacao.

**Rationale:** um so digest para qualquer texto, verificavel nas duas plataformas (SC7), sem criar um setimo helper.

**Alternatives Rejected:**
1. Bytes crus: o recibo emitido no Windows diverge no CI Linux.
2. Normalizar tambem espacos no fim da linha, como faz o `report sign`: la o corpo e prosa editada a mao; aqui sao artefatos gerados, e trocar um espaco e mudanca real.

**Consequences:**
- Um arquivo binario amarrado por engano teria `\r\n` reescrito no hash. Nenhuma parte aceita binario, e o `.db` nunca e hasheado como arquivo.

---

### Decision 4: todo caminho confinado ao `--repo`, exceto o transcript do host

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:**
- O verify resolve caminhos relativos ao repo.
- `_caminhos_declarados` (`agents/autonomy.py:248`) confina parametros com nome de caminho, lista inclusive.
- O transcript real do host mora em `~/.claude/projects/...`, fora do repo, e o `telemetry export` ja o aceita assim.

**Choice:**
- `facts_path` (string ou lista), `findings_path` e `report_path` precisam resolver dentro de `--repo`. Senao, exit 2 na CLI e erro na tool, e nada e gravado (AT-015). No recibo o caminho sai relativo e em POSIX.
- `host_transcript` mantem o mesmo nome e a mesma regra do `telemetry_export`. So o `transcript_sha256` entra no recibo, e o caminho absoluto nunca entra, porque tem o nome do usuario da maquina.
- No verify, `host` e reconferido so se `--host-transcript` for passado de novo. Sem ele, sai `not_rechecked` (`transcript_fora_do_repo`).

**Rationale:** o verify precisa alcancar tudo pelo repo, e um caminho absoluto de home no recibo vazaria identidade num arquivo commitavel.

**Alternatives Rejected:**
1. Exigir o transcript dentro do repo: o fluxo real nunca teria `host`.
2. Gravar o caminho absoluto: vaza o usuario da maquina.

**Consequences:**
- Um recibo verificado em outra maquina sai com dois `not_rechecked` tipicos, `tools` e `host`, e `valid: true` se o resto confere.

---

### Decision 5: blackboard, ADR e debate por nome conhecido, sem varrer diretorio

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:**
- `test_facts_scan` varre `sparkforge/` por AST e recusa `Path.glob`/`rglob`.
- O ADR mora em `.sparkforge/blackboard/adr/ADR-<decision_id>.md` (`agentic/executor/run.py:136` e `:982`), e nao em `.sparkforge/adr/` como o DEFINE 1.0 dizia.
- O blackboard tem nomes fixos em `agentic/blackboard.py:49-58`.

**Choice:**
- `decision.blackboard`: para cada nome do mapa de `blackboard.py` que existe, caminho, sha256 e numero de linhas.
- `decision_ids`: os ids de `decisions.jsonl`.
- `adrs`: `blackboard/adr/ADR-<id>.md` para cada decisao. Com o arquivo ausente, o item sai `missing` ja no emit.
- `rollback_present` sai do registro da decisao, sem parsear o Markdown.
- `debates`: pela funcao de listagem que `debate_run.py` ja expoe sobre `.sparkforge/debate/`. Por debate, id e sha256 do arquivo de estado.
- Sem blackboard e sem debate: `unresolved` com `sem_arbitragem`.

**Rationale:** enumeracao por dado que ja existe e deterministica, e o teste de varredura continua verde.

**Alternatives Rejected:**
1. `glob("*.jsonl")`: derruba `test_facts_scan` e pegaria arquivo estranho ao blackboard.

**Consequences:**
- Um arquivo novo no blackboard so entra no recibo quando entrar no mapa de `blackboard.py`, o que e o certo.

---

### Decision 6: `proof` e `host` so apontam

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** regras 13, 23 e 30.

**Choice:**
- `proof.tests` recebe os fact_ids de kind `funcval.*` da uniao, e `proof.before_after` os de benchmark. O prefixo exato do kind de benchmark e conferido no B1 contra o extrator.
- `host` usa os mesmos facts `host.*` que o `otlp._host` le, com a mesma regra de `unresolved`: `transcript_ausente`, `provider_nao_declarado` e `modelos_multiplos`.
- Nenhum valor medido entra.

**Rationale:** o recibo diz onde esta a prova e quem o host disse que era; julgar e com `funcval compare`, `benchmark` e o operador.

**Alternatives Rejected:**
1. Copiar o veredito do `funcval` para o recibo: vira julgamento dentro de um documento de proveniencia.

**Consequences:**
- A varredura V2 (SC5) prova que nenhum valor de `measures` escapou.

---

### Decision 7: superficie e registros

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** regra 26 e o conjunto medido de sete registros que caem com tool nova. DEFINE A-007: o teste de paridade MCP ja tem `NOVAS_DEPOIS_DO_GOLDEN`.

**Choice:**
- `sparkforge_receipt_emit`: `annotations: _WRITE_IDEMPOTENT`, que da `LOCAL_MUTATION` por `tool_class`. A mesma entrada com o mesmo `now` grava o mesmo arquivo.
  - `required`: `repo`, `facts_path`, `findings_path`, `now`.
  - Opcionais: `report_path`, `run_id`, `host_transcript`, `provider`.
- `sparkforge_receipt_verify`: `_READ_ONLY`. `required`: `repo` e `receipt_path`; opcional: `host_transcript`.
- As duas declaram caminho: `SEM_CAMINHO` nao muda, e a contagem de tools com caminho sobe 2.
- `NOVAS_DEPOIS_DO_GOLDEN` recebe as duas, com motivo datado.
- `parity.yaml` ganha a capacidade "prove what an execution used and decided".
- O `sf-synthesizer` e o dono das duas.

**Rationale:** mesmo desenho de `report_sign`/`report_verify`, e a paridade ja tem o mecanismo para tool nova.

**Alternatives Rejected:**
1. Regenerar o golden de paridade: perderia a prova sob o 1.29.

**Consequences:**
- Registros que caem: `test_adapters_tools` (lista e construtor de amostra real), `test_harness_authorization` (contagem), `parity.yaml`, `sf-synthesizer.md` e espelhos, `manifest.json`, `docs/surface.lock.json` e `docs/claims.lock.json` com os docs auditados.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/receipt/__init__.py`, `_hash.py` | Create | API publica, `text_sha256`, `digest_of`, `receipt_id_of` | @agentspec:python:python-developer | None |
| 2 | `sparkforge/receipt/build.py` | Create | Montagem das partes (Decisions 2, 3, 5, 6) | @agentspec:python:python-developer | 1 |
| 3 | `sparkforge/receipt/verify.py` | Create | Diagnostico por parte, `not_rechecked`, `not_evaluable` | @agentspec:python:python-developer | 1, 2 |
| 4 | `tests/test_receipt_build.py`, `tests/test_receipt_verify.py` | Create | Unidade com entrada sintetica: determinismo, CRLF, V2, adulteracao por parte, spans por `span_id` | @agentspec:test:test-generator | 2, 3 |
| 5 | `sparkforge/adapters/_core.py` | Modify | `receipt_emit`, `receipt_verify`, `receipt_write`, confinamento | (general) | 2, 3 |
| 6 | `sparkforge/adapters/cli.py` | Modify | Grupo `receipt` (`emit`, `verify`), exit 0/1/2 | (general) | 5 |
| 7 | `sparkforge/adapters/tools.py` | Modify | Duas tools, schemas, handlers, registro no mapa | (general) | 5 |
| 8 | `fixtures/receipt/` (`input/` com `.sparkforge/case.yaml`, `blackboard/*.jsonl`, `blackboard/adr/ADR-*.md`, facts e findings da uniao, report assinado; `expected/receipt.json`) + `tests/test_fixtures_golden_receipt.py` | Create | Golden byte a byte (SC1) e os ATs de ponta a ponta pela CLI | @agentspec:test:test-generator | 5, 6 |
| 9 | `tests/test_adapters_tools.py`, `tests/test_harness_authorization.py`, `tests/test_fixtures_golden_mcp_parity.py` | Modify | Lista, amostra real, contagem, `NOVAS_DEPOIS_DO_GOLDEN` | (general) | 7 |
| 10 | `parity.yaml`, `manifest.json`, `agents/executors/sf-synthesizer.md` + espelhos (`scripts/sync_skills.py`) | Modify | Capacidade, chave `tools`, passo novo | (general) | 7 |
| 11 | `docs/execution-receipt.md`, `docs/superpowers/STATUS.md` | Create/Modify | Schema, o que prova e recusa, `cosign attest-blob` fora do pacote (G18) | (general) | all |
| 12 | `docs/surface.lock.json`, `docs/claims.lock.json` + docs auditados | Modify (pelo gate) | Regra 26; claims por lista de ids | (general) | all |
| 13 | `.claude/sdd/reports/BUILD_REPORT_EXECUTION_RECEIPT.md` | Create | Relatorio | (general) | all |

**Total Files:** 13 entradas.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 1, 2, 3 | Funcoes puras com dataclass-free dicts e stdlib |
| @agentspec:test:test-generator | 4, 8 | Golden, adulteracao por parte, pares |
| (general) | 5–7, 9–13 | Adapters e registros manuais deste repositorio, que dependem das armadilhas medidas |

**Agent Discovery:**
- Scanned: agentes do plugin agentspec e os da sessao.
- Matched by: tipo de arquivo e palavra-chave.
- Como nos PRs #50 a #53, o build pode ser direto: cada passo depende de medida do anterior.

---

## Code Patterns

### Pattern 1: hash e id

```python
import hashlib
from pathlib import Path
from typing import Any

from sparkforge.findings.models import _canonical

RECEIPT_VERSION = 1
RECEIPT_PREFIX = "rcpt_"


def text_sha256(path: Path) -> str:
    """sha256 do texto com CRLF normalizado (Decision 3)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def digest_of(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("ascii")).hexdigest()


def receipt_id_of(doc: dict[str, Any]) -> str:
    sem_id = {chave: valor for chave, valor in doc.items() if chave != "receipt_id"}
    return RECEIPT_PREFIX + digest_of(sem_id)
```

### Pattern 2: um item de artefato, com `missing` nomeado

```python
def artefato(raiz: Path, relativo: str) -> dict[str, Any]:
    alvo = raiz / relativo
    if not alvo.is_file():
        return {"path": relativo, "state": "missing"}
    return {"path": relativo, "sha256": text_sha256(alvo)}
```

### Pattern 3: spans por `span_id` no verify (Decision 2)

```python
_COLUNAS = ("span_id", "name", "status", "outcome", "payload_bytes", "detail_level",
            "start_time", "end_time")


def projetar_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    linhas = [{c: s.get(c) for c in _COLUNAS} for s in spans]
    return sorted(linhas, key=lambda s: (s["start_time"] or 0, s["span_id"]))


def conferir_tools(declarado: dict[str, Any], do_run: list[dict[str, Any]]) -> dict[str, Any]:
    ids = {s["span_id"] for s in declarado["spans"]}
    presentes = [s for s in do_run if s.get("span_id") in ids]
    depois = len(do_run) - len(presentes)
    if not presentes:
        return {"state": "not_rechecked", "reason": "run_ausente", "spans_after_emit": depois}
    faltam = sorted(ids - {s["span_id"] for s in presentes})
    if faltam:
        return {"state": "diverged", "missing_span_ids": faltam, "spans_after_emit": depois}
    igual = digest_of(projetar_spans(presentes)) == declarado["spans_sha256"]
    return {"state": "match" if igual else "diverged", "spans_after_emit": depois}
```

### Pattern 4: entrada da tool (forma de `report_sign`)

```python
"sparkforge_receipt_emit": {
    "description": "...correspondencia entre este recibo e estes artefatos -- nunca autoria...",
    "inputSchema": {
        "type": "object",
        "required": ["repo", "facts_path", "findings_path", "now"],
        "properties": {
            "repo": {"type": "string"},
            "facts_path": {"type": ["string", "array"], "items": {"type": "string"}},
            "findings_path": {"type": "string"},
            "report_path": {"type": "string"},
            "run_id": {"type": "string"},
            "host_transcript": {"type": "string"},
            "provider": {"type": "string"},
            "now": {"type": "string", "description": "ISO 8601; entra no hash"},
        },
    },
    "outputSchema": _may_fail(_RECEIPT_EMIT_SCHEMA, "O recibo gravado, ou erro de entrada."),
    "annotations": _WRITE_IDEMPOTENT,
},
```

---

## Data Flow

```text
1. emit: adapter confina facts/findings/report ao repo; le _signature_parts(findings),
   a signature do bloco do report, spans_of(run_id) e os facts host.*
   │
   ▼
2. build: hasheia case.yaml, cada facts, findings, report, blackboard, ADRs, debates;
   projeta spans; aponta proof; monta host/actions/unresolved/refused; calcula receipt_id
   │
   ▼
3. receipt_write: .sparkforge/receipts/<receipt_id>.json (temp + replace, confinado)
   │
   ▼
4. verify (outro dia, outra maquina): le o recibo; version -> integrity -> cada parte
   contra o disco; spans por span_id; host so com --host-transcript
   │
   ▼
5. {valid, status, diverged, checks, not_rechecked, not_evaluable}; exit 0 / 1 / 2
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| `report sign` (`_signature_parts`, `_split_report`) | Chamada interna no adapter | N/A |
| `observability.context_ledger.shared_ledger` | Leitura de spans (buffer + `traces.db`) | N/A |
| `facts.host_transcript.extract_host_transcript_path` | Leitura do transcript declarado | N/A |
| `agentic.blackboard` / `executor.run` / `executor.debate_run` | Nomes de arquivo e listagem de debates | N/A |
| `cosign attest-blob` (fora do pacote) | Documentado em `docs/execution-receipt.md` | Do operador |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | `text_sha256` com LF e CRLF; `receipt_id` estavel; mudar um valor muda o id; reformatar o arquivo nao muda | `tests/test_receipt_build.py` | pytest | SC7, AT-002, AT-013 |
| Unit | Partes com entrada sintetica; `unresolved` sem host, sem run e sem arbitragem; `refused` sempre com as duas; varredura V2 | `tests/test_receipt_build.py` | pytest | SC5, SC6, AT-010, AT-011 |
| Unit | Adulteracao de cada uma das 6 partes com artefato (so aquela em `diverged`); `missing`; `integrity`; `not_evaluable`; spans: todos, nenhum, parte, e mais spans depois do emit | `tests/test_receipt_verify.py` | pytest | SC2, SC3, SC4, AT-004 a AT-009, AT-012, AT-014 |
| Golden | Case de `fixtures/receipt/` pela CLI com `--now` fixo, sem `--run-id`; golden com spans sinteticos pelo modulo | `tests/test_fixtures_golden_receipt.py` | pytest | SC1, AT-001, AT-003 |
| Contract | As duas tools com amostra real validam contra o schema; caminho fora do repo recusado; span do emit fora | `tests/test_adapters_tools.py` + teste novo de handler | pytest | SC8, SC9, AT-015 |
| CLI | JSON invalido da exit 2; invalido da exit 1 | `tests/test_fixtures_golden_receipt.py` | pytest | AT-016 |
| Parity | Duas tools em `NOVAS_DEPOIS_DO_GOLDEN`; chamadas gravadas intactas | `tests/test_fixtures_golden_mcp_parity.py` | pytest | SC10 |
| Cross-OS | Golden gerado no Windows verificado no CI Linux (matriz 3.10/3.11 do CI) | CI | GitHub Actions | SC7 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Caminho declarado fora de `--repo` | Exit 2 / erro da tool; nada gravado | No |
| Findings vazio ou `catalog_version` divergente | A mesma `AdapterError` do `report sign`, exit 2 | No |
| Report com bloco malformado | Exit 2 com o problema de `_split_report` | No |
| `traces.db` indisponivel ou run sem span no emit | `tools` em `unresolved` (`traces_db_indisponivel`, `run_sem_spans`); o emit segue (regra 27) | No |
| Transcript ilegivel | `host` em `unresolved` (`transcript_ilegivel`); o emit segue | No |
| Recibo ilegivel, JSON invalido ou sem `receipt_version` | Exit 2 com a dica `sparkforge receipt verify --receipt ... --repo .` | No |
| `receipt_version` maior que o da build | Partes de normalizacao `not_evaluable`, `status: version_mismatch` | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--now` / `now` | ISO 8601 | obrigatorio | Entra no hash (G11) |
| `--run-id` / `run_id` | string | CLI: nenhum; tool: `shared_ledger().run_id` | Run cujos spans entram |
| `--host-transcript` / `host_transcript` | caminho | nenhum | Transcript do host; so o sha256 entra |
| `--provider` / `provider` | string | nenhum | Declarado, nunca deduzido |
| `RECEIPT_VERSION` | int (codigo) | 1 | Entra no hash; muda com a regra de normalizacao |

---

## Security Considerations

- Nenhum conteudo de caso no recibo (V2): caminho relativo, hash, id, contagem, versao e colunas escolhidas do span; nunca `metadata_json` nem `measures`.
- Nenhum caminho absoluto no recibo; o transcript entra so por sha256 (Decision 4).
- Todo caminho de entrada confinado ao repo, e a escrita so em `.sparkforge/receipts/`, com o destino conferido antes de gravar.
- O recibo nao prova autoria e diz isso em `proves` e em `refused`. Quem precisa de autoria assina o arquivo fora do pacote.
- Nenhuma rede e nenhum provider.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | N/A |
| Metrics | O verify devolve `spans_after_emit` e as contagens por estado |
| Tracing | O span do `receipt_emit` e gravado pelo `call_tool` como qualquer outro, e aparece nos recibos seguintes |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Itens 1–4; confirmar o prefixo do kind de benchmark e os campos de modelo e agente dos facts `host.*` | Unidade verde; `test_facts_scan` e `test_codeintel_staleness` verdes com o modulo novo (depois de `git add`) |
| B2 | Itens 5–7 | Handlers com amostra real validam; AT-015 e AT-016 verdes |
| B3 | Item 8 | Golden verde; verify limpo com exit 0 |
| B4 | Itens 9–10; `scripts/sync_skills.py` | `test_adapters_tools`, `test_harness_authorization`, `test_capability_parity`, `test_agent_coverage`, `test_docs_coverage`, paridade MCP verdes |
| B5 | Itens 11–12; `check_surface_lock --update` com o crescimento declarado; `check_vnext_claims` remediado pela lista de ids; `check_status_numbers --strict`; `check_evals`; `ruff`; suite por lotes | Tudo verde |
| B6 | Commit, push, PR; item 13 | CI verde nas duas plataformas |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | design-agent | Versao inicial. A-005 a A-008 decididas; ADR em `.sparkforge/blackboard/adr/` (corrige o DEFINE 1.0); spans ancorados por `span_id` e lidos do `shared_ledger` (Decision 2) |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_EXECUTION_RECEIPT.md`
