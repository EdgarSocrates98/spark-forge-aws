# DESIGN: Checkpoint/resume/event journal (§31 P0 item 7)

> Technical design for implementing Checkpoint/resume/event journal (§31 P0 item 7)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHECKPOINT_RESUME_JOURNAL |
| **Date** | 2026-09-15 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_CHECKPOINT_RESUME_JOURNAL.md](./DEFINE_CHECKPOINT_RESUME_JOURNAL.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
porta MCP                                   porta CLI
tools.call_tool(name, args)                 cli._dispatch(args)
  ├─ policy recusa -> retorna (sem evento)    ├─ tool = "sparkforge_" + comando + "_" + sub
  └─ journal.recording(...)                   └─ journal.recording(...)   (so se tool em JOURNALED)
          │                                           │
          └──────────────┬────────────────────────────┘
                         ▼
        sparkforge/journal/record.py :: recording(tool, port, args, now)
          ├─ raiz = raiz_do_journal(tool, args)      (repo | ancestral com case.yaml | None)
          ├─ started  -> durable.append_line(journal.jsonl)   (sob trava, seq/prev lidos na trava)
          ├─ handler(args)                            (o verbo, intocado)
          └─ finished -> started_seq, outcome, outputs | outputs_unresolved
             falha do journal -> resultado["journal"] = "unrecorded" + motivo (regra 27)

sparkforge/durable.py
  write_atomic(path, text)   tmp no mesmo dir -> fsync -> os.replace (retry em PermissionError no Windows)
  append_line(path, line)    trava do proprio arquivo; cauda sem "\n" -> <arquivo>.torn; append
  read_jsonl(path)           (registros, torn_tail); linha ruim no meio -> DurableError(linha)
        ▲ usado por
  case/store.save_case | blackboard _append_jsonl/_read_jsonl | debate_run _escreve_json/_anexa_jsonl/_le_jsonl
  debate_evidence append_evidence_facts | journal

leitura
  journal/read.py :: estado(raiz) -> {last_seq, open_calls, chain, torn_tail}
  _core.resume_case -> case/resume.resume(..., journal=estado) -> in_flight / in_flight_source
  _core.journal_verify -> CLI `sparkforge journal verify --repo` (exit 1 em broken)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/durable.py` | Escrita atômica, append sob trava com quarentena da cauda, leitura JSONL que tolera só a cauda | stdlib (`os`, `tempfile`, `msvcrt`/`fcntl`, `json`) |
| `sparkforge/journal/__init__.py` | Constantes: `JOURNAL_FILE`, `LITERAL_KEYS`, `JOURNALED` (derivado de `TOOLS` sob demanda) | stdlib |
| `sparkforge/journal/record.py` | `recording()`, forma canônica dos eventos, raiz, `outputs` por verbo | stdlib + `durable` |
| `sparkforge/journal/read.py` | `estado(raiz)` e `verify(raiz)`: cadeia, `open_calls`, cauda | stdlib + `durable` |
| `adapters/tools.py::call_tool` | Gancho MCP depois da policy, em volta do handler | chamada a `recording` |
| `adapters/cli.py::_dispatch` | Gancho CLI em volta do handler; verbo `journal verify` | chamada a `recording` |
| `adapters/_core.py` | `resume_case` lê `estado`; `journal_verify` | chamadas puras |
| `case/resume.py` | Bloco `journal`, `in_flight_source`, linhas do `handoff.md` | função pura (recebe o estado pronto) |

---

## Key Decisions

### Decision 1: Primitivas duráveis num módulo só, usadas pelos donos do estado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-15 |

**Context:** Hoje há cinco appenders (`blackboard.py:81`, `debate_run.py:1159`, `debate_evidence.py:182`, `agentic/memory.py:66`, `agents/room.py:62`) e três escritas de estado com `write_text` direto (`save_case`, `debate_run._escreve_json` para `plan.json` e `decision.json`). Uma linha cortada faz `_read_jsonl`/`_le_jsonl` levantar `json.loads` e trava o blackboard e o debate.

**Choice:**
- `write_atomic(path, text)`: `tempfile.NamedTemporaryFile(dir=path.parent, delete=False)`, grava, `flush`, `os.fsync`, `os.replace(tmp, path)`. Qualquer exceção remove o temporário e relança; o original fica intacto. No Windows, `PermissionError` no `os.replace` (destino aberto por outro processo sem `FILE_SHARE_DELETE`) tenta de novo até 5 vezes com 20 ms; depois relança.
- `append_line(path, line)`: abre em `"a+b"`, trava o próprio arquivo (`fcntl.flock(LOCK_EX)`; no Windows `msvcrt.locking(LK_LOCK, 1)` no byte 0), confere o último byte; se não é `\n`, copia os bytes depois do último `\n` para `<arquivo>.torn` (acrescentando), trunca até o último `\n`, e só então anexa `line + "\n"`, `flush`, `fsync`, destrava. Devolve o texto das linhas anteriores quando o chamador precisa (journal) para calcular `seq`/`prev` DENTRO da trava.
- `read_jsonl(path) -> (list[dict], str | None)`: linha final sem `\n` e sem JSON válido vira `torn_tail`; qualquer outra linha inválida levanta `DurableError` com o número da linha.
- Entram: `save_case`, `_escreve_json`, `_append_jsonl`/`_read_jsonl`, `_anexa_jsonl`/`_le_jsonl`, `append_evidence_facts` e o leitor de `facts.jsonl` do debate. Ficam fora `agentic/memory.py` e `agents/room.py` (não são estado do case que `resume`/debate leiam).
- `.gitignore` ganha `.sparkforge/**/*.torn`: a quarentena é evidência local de queda, não estado.

**Rationale:** Uma implementação só da mesma garantia; a trava no próprio arquivo dispensa arquivo de lock ao lado (que seria mais um arquivo em pasta commitável).

**Alternatives Rejected:**
1. Arquivo `.lock` ao lado — mais um arquivo para ignorar e para sobrar depois de queda.
2. Apagar a cauda cortada — some a única evidência do que a queda interrompeu.
3. Tolerar toda linha inválida — linha ruim no meio é outro defeito e passaria calada.

**Consequences:**
- `_read_jsonl` e `_le_jsonl` passam a devolver também `torn_tail`; os chamadores atuais só usam os registros (a assinatura pública de `read_claims` etc. não muda).
- O conteúdo gravado é o mesmo byte a byte: goldens de debate não se regravam.

---

### Decision 2: Forma canônica do evento e da cadeia

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-15 |

**Context:** Ordem sem relógio (timestamp nunca é gerado no pacote), pares não ambíguos com chamadas concorrentes, e remoção ou edição detectável.

**Choice:**
- Linha = `json.dumps(evento, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`.
- `seq` começa em 1 e cresce de 1 em 1; `prev` = sha256 hex dos bytes UTF-8 da linha anterior (sem o `\n`); na primeira linha, `prev: null`.
- `started`: `{"event": "started", "seq", "prev", "call", "tool", "port", "args", "at", "schema_version": 1}`; `call` = sha256 de `tool + "\n" + json canônico de args` (já normalizados, ver Decision 4).
- `finished`: `{"event": "finished", "seq", "prev", "started_seq", "tool", "outcome", "outputs" | "outputs_unresolved", "schema_version": 1}`; `outcome` ∈ `ok`, `error`.
- `seq` e `prev` são lidos da última linha válida DENTRO da trava de `append_line`.

**Rationale:** `started_seq` pareia sem ambiguidade (duas chamadas iguais e concorrentes têm o mesmo `call`); `prev` sobre os bytes da linha, e não sobre o objeto, faz qualquer edição de linha quebrar a cadeia.

**Alternatives Rejected:**
1. Parear por `call` — ambíguo com chamada repetida.
2. Hash sobre o objeto re-serializado — reformatar a linha não seria detectado.

**Consequences:**
- `verify` recalcula a cadeia inteira em uma passada.

---

### Decision 3: Gancho nas duas portas, conjunto derivado das anotações

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-15 |

**Context:** A CLI não passa por `call_tool` (0 ocorrência em `cli.py`); `call_tool` (`tools.py:10252`) é o despacho único do MCP e recusa pela policy antes do handler.

**Choice:**
- `JOURNALED = {nome for nome, spec in TOOLS.items() if not spec["annotations"]["readOnlyHint"] and not nome.startswith("sparkforge_code_")}` (27), calculado em `journal/__init__.py` por função com cache, importando `TOOLS` tarde (o módulo `journal` não pode arrastar `adapters.tools` para o hook de policy).
- MCP: em `call_tool`, depois do bloco da policy, `with recording(name, "mcp", argumentos, now=argumentos.get("now")) as rec:` em volta do `handler(argumentos)`; `rec.finish(resultado, desfecho)` antes do `record` do ledger.
- CLI: em `_dispatch`, `tool = "sparkforge_" + "_".join(p.replace("-", "_") for p in (args.command, sub_action) if p)`; se `tool in JOURNALED`, envolve `handler(args)` com `port="cli"`, `args = vars(args)` menos `command`, `*_action`, `subcommand` e `func`. Medido: a convenção dá o nome certo para 27 de 27.
- Desfecho CLI: exit 0 → `ok`; exit ≠ 0 ou `AdapterError` → `error`.

**Rationale:** Dois pontos de gancho em vez de 27; a anotação já é a fonte da classe de autorização (§16), e tool nova que grava entra no journal sem ninguém lembrar.

**Alternatives Rejected:**
1. Chamada em cada verbo de `_core` — 27 pontos, esquecimento silencioso.
2. Mapa verbo → tool pelo `parity.yaml` — ele agrupa por capacidade, não um a um.

**Consequences:**
- **Revisão do critério de sucesso 2 do DEFINE:** medido que os nomes de argumento divergem entre as portas em 27 de 27 (`facts` × `facts_path`, `raiz` × `repo`, `debate` × `debate_id`). O mesmo verbo pelas duas portas grava `tool`, `outcome` e `outputs` iguais; `args` (e portanto `call`) segue o nome de cada porta. Normalizar os nomes exigiria 27 mapas de alias, frágeis.

---

### Decision 4: Raiz, argumentos, `at` e `outputs`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-15 |

**Context:** 24 dos 27 recebem `repo` (na CLI do `scan`, o destino é `raiz`); `report_sign`, `funcval_plan` e `funcval_compare` não. Medido: `test_adapters_report_signature.py:430` roda `report sign` com o cwd na raiz do projeto — com `raiz_do_projeto()` o journal sujaria o repositório (A-004 caiu para esses 3). 18 dos 27 recebem `now`. `outputSchema` declara caminho em 20 dos 27.

**Choice:**
- Raiz: `args["repo"]` (MCP) ou `args.repo`/`args.raiz` (CLI). Para os 3 sem `repo`: o primeiro ancestral do arquivo de saída (`report`/`report_path`; `out`/`out_path`) que contém `.sparkforge/case.yaml`. Sem ancestral: não grava, e o resultado ganha `journal: "unrecorded"`, `journal_reason: "sem_raiz_de_case"`.
- Argumentos: cada valor vira `sha256:` + sha256 do JSON canônico; literal só para `LITERAL_KEYS = {"rules", "debate_id", "debate", "sandbox", "sandbox_id", "fail_on", "format", "output_format", "phase", "gate"}` e só se o valor não for caminho absoluto nem conter separador de drive.
- `at`: `args["now"]` quando é texto não vazio, senão `null`.
- `outputs` por tabela `OUTPUTS` em `record.py` (caminho relativo à raiz → sha256 do arquivo depois do verbo):

| Tool | Fonte dos caminhos |
|------|--------------------|
| `case_open`, `case_update` | fixo `.sparkforge/case.yaml` |
| `collect_*` (13 com `path`) | `resultado["path"]` e `.sparkforge/artifacts/manifest.json` |
| `collect_glue_job_runs` | `.sparkforge/artifacts/manifest.json` |
| `scan` | `resultado["outputs"]` |
| `receipt_emit` | `resultado["receipt_path"]` |
| `debate_start` | `resultado["state_dir"]` + `plan.json` |
| `change_propose` | `resultado["files"]` |
| os demais | `outputs_unresolved: "verbo_sem_declaracao_de_saida"` |

Caminho fora da raiz ou arquivo ausente entra como `null` com o caminho, não como erro.

**Rationale:** Repositório público e "caso real nunca entra em arquivo"; `redact` é heurístico. A raiz pelo case evita journal em diretório que não é case.

**Alternatives Rejected:**
1. `raiz_do_projeto()` para os 3 — suja a raiz do repositório na suíte (medido).
2. Varrer `.sparkforge/` por mtime para achar saídas — inventa lista.

**Consequences:**
- `outputs` é parcial por desenho; o número de verbos com `outputs` resolvido sai medido no BUILD_REPORT.

---

### Decision 5: `resume` e `verify`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-15 |

**Context:** `case/resume.py` é puro e determinístico (docstring); `sparkforge_resume` está no golden MCP 1.29; nenhum `outputSchema` dos verbos de escrita fecha `additionalProperties`, e o `calls.json` do golden não tem chamada de verbo de escrita (medidos).

**Choice:**
- `journal/read.py::estado(raiz) -> {"last_seq", "open_calls": [{"seq", "tool", "port", "at"}], "chain": "intact"|"broken"|"absent", "broken_at": int|None, "torn_tail": bool}`.
- `_core.resume_case` chama `estado(repo)` e passa `journal=` para `resume()`; `resume()` continua puro. `in_flight` = texto do chamador se não vazio (`in_flight_source: caller`); senão, se há `open_calls`, `"<tool> (<port>, seq <n>) sem finished"` para cada um (`journal`); senão `none`.
- `_RESUME_SCHEMA` ganha `journal` e `in_flight_source` em `properties`, fora de `required` (diferença só aditiva); `sparkforge_resume` entra em `ALTERADAS_DEPOIS_DO_GOLDEN`.
- `handoff.md`: a seção "Em voo na interrupcao" lista cada `open_call` com "sem finished (caiu ou ainda roda)".
- `verify(raiz)` recalcula `seq` e `prev` linha a linha: salto de `seq` ou `prev` que não confere → `broken` com `broken_at`; só cauda cortada → `torn_tail`; arquivo ausente → `absent`. CLI `sparkforge journal verify --repo <raiz>`, exit 1 em `broken`, exit 0 nos outros. Entra em `ALLOWED_CLI_ONLY` de `tests/test_capability_parity.py` com a razão (auditoria; o `resume` já leva o estado pela tool existente).

**Rationale:** Dado no lugar do texto livre, sem quebrar quem já passa texto; paridade MCP só aditiva.

**Alternatives Rejected:**
1. Ler o journal dentro de `case/resume.py` — a função deixaria de ser pura.
2. Pôr os campos em `required` — seria reescrita, não diferença aditiva.

**Consequences:**
- `open_calls` diz "sem finished", nunca "caiu".

---

### Decision 6: Isolamento na suíte

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-15 |

**Context:** `tests/conftest.py` já tem a fixture de sessão que isola o ledger e afirma, no fim, que `.sparkforge/traces.db` da raiz não foi criado. 24 arquivos rastreados moram em `fixtures/**/.sparkforge/`.

**Choice:** A mesma fixture de sessão fotografa, no início, o sha256 (ou a ausência) de `_ROOT/.sparkforge/journal.jsonl` e de todo `fixtures/**/.sparkforge/journal.jsonl`, e afirma no fim que nada mudou. Um teste de unidade roda `report sign` com o cwd na raiz do projeto e confere `journal: "unrecorded"` com `sem_raiz_de_case`.

**Rationale:** Verifica o EFEITO, como o backstop do `traces.db`: pega qualquer teste presente ou futuro.

**Alternatives Rejected:**
1. Variável de ambiente que desliga o journal na suíte — a suíte deixaria de exercitar o gancho.

**Consequences:**
- Teste que rode verbo de escrita sobre pasta de fixture sem copiar derruba a suíte no teardown, com o caminho.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/durable.py` | Create | `write_atomic`, `append_line`, `read_jsonl`, `DurableError` | @python-developer | None |
| 2 | `sparkforge/journal/__init__.py`, `record.py`, `read.py` | Create | Evento, raiz, `outputs`, `recording`, `estado`, `verify` | @python-developer | 1 |
| 3 | `sparkforge/case/store.py` | Modify | `save_case` por `write_atomic` | @python-developer | 1 |
| 4 | `sparkforge/agentic/blackboard.py`, `agentic/executor/debate_run.py`, `agentic/executor/debate_evidence.py` | Modify | Appenders e leitores pelo `durable` | @python-developer | 1 |
| 5 | `sparkforge/adapters/tools.py` | Modify | Gancho em `call_tool`; `_RESUME_SCHEMA` com `journal`/`in_flight_source` | @python-developer | 2 |
| 6 | `sparkforge/adapters/cli.py` | Modify | Gancho em `_dispatch`; subcomando `journal verify` | @python-developer | 2 |
| 7 | `sparkforge/adapters/_core.py`, `sparkforge/case/resume.py` | Modify | `resume_case` com `estado`; `journal_verify`; bloco no payload e no `handoff.md` | @python-developer | 2 |
| 8 | `.gitignore` | Modify | `.sparkforge/**/*.torn` | (general) | None |
| 9 | `tests/test_durable.py`, `tests/test_journal.py` | Create | Unidade: atomicidade com `os.replace` sabotado, cauda, linha ruim no meio, trava, conjunto = anotações, duas portas, sem literal, regra 27, recusa da policy, `sem_raiz_de_case` | @test-generator | 1-7 |
| 10 | `fixtures/journal/<6 casos>/` + `tests/test_fixtures_golden_journal.py` | Create | Goldens de queda com `FIXTURES = ROOT / "fixtures" / "journal"` literal; `.gitattributes` `fixtures/journal/** -text` | @test-generator | 2, 7 |
| 11 | `tests/conftest.py`, `tests/test_case_resume.py`, `tests/test_fixtures_golden_mcp_parity.py`, `tests/test_capability_parity.py` | Modify | Backstop do journal, payload novo, `ALTERADAS_DEPOIS_DO_GOLDEN["sparkforge_resume"]`, `ALLOWED_CLI_ONLY["journal verify"]` | (general) | 5-7 |
| 12 | `CLAUDE.md`, `docs/superpowers/STATUS.md`, `docs/guia/usos/` (página do case), referência gerada, `docs/claims.lock.json`, `docs/surface.lock.json` | Modify | Manual e números | (general) | 1-11 |

**Total Files:** 12 grupos

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1-7 | Python puro, stdlib, no molde dos módulos de estado do repositório |
| @test-generator | 9, 10 | Unidade e goldens sintéticos |
| (general) | 8, 11, 12 | Registros literais e números do repositório |

**Agent Discovery:**
- Scanned: `agents/**/*.md` do agentspec
- Matched by: tipo de arquivo; o build constrói direto, como nas frentes anteriores

---

## Code Patterns

### Pattern 1: Escrita atômica

```python
def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _replace(tmp: str, path: Path) -> None:
    for tentativa in range(_TENTATIVAS_REPLACE):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if os.name != "nt" or tentativa == _TENTATIVAS_REPLACE - 1:
                raise
            time.sleep(_ESPERA_REPLACE_S)
```

### Pattern 2: Append sob trava, com quarentena da cauda

```python
def append_line(path: Path, montar: Callable[[str | None], str]) -> str:
    """`montar` recebe a ultima linha valida (ou None) e devolve a linha nova;
    roda DENTRO da trava, para `seq`/`prev` nunca serem disputados."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as fh:
        _travar(fh)
        try:
            fh.seek(0)
            conteudo = fh.read()
            corte = conteudo.rfind(b"\n") + 1
            if corte < len(conteudo):
                with path.with_name(path.name + ".torn").open("ab") as quarentena:
                    quarentena.write(conteudo[corte:] + b"\n")
                fh.truncate(corte)
            ultima = conteudo[:corte].rstrip(b"\n").rsplit(b"\n", 1)[-1] or None
            linha = montar(ultima.decode("utf-8") if ultima else None)
            fh.seek(0, os.SEEK_END)
            fh.write(linha.encode("utf-8") + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
            return linha
        finally:
            _destravar(fh)
```

### Pattern 3: Gancho sem derrubar a chamada (regra 27)

```python
@contextlib.contextmanager
def recording(tool: str, port: str, args: Mapping[str, Any], now: Any = None):
    rec = _Registro(tool, port)
    if tool in journaled():
        try:
            rec.start(args, now)
        except Exception as exc:  # noqa: BLE001 -- journal nunca derruba o verbo
            rec.falhou(f"{type(exc).__name__}: {exc}")
    yield rec
```

---

## Data Flow

```text
1. host chama verbo de escrita (CLI ou MCP)
   │
   ▼
2. recording: raiz -> started (seq n, prev, args hasheados, at) sob trava
   │
   ▼
3. handler do verbo roda como hoje (escritas de estado pelo durable)
   │
   ▼
4. finished (started_seq n, outcome, outputs) sob trava
   │   (queda entre 2 e 4 deixa started sem finished)
   ▼
5. outra sessao: resume -> estado(raiz) -> open_calls -> in_flight_source: journal
   │
   ▼
6. revisor: sparkforge journal verify -> intact | broken(seq) | torn_tail | absent
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Host (Devin, Claude Code, `scripts/run_debate.py`) | Lê `resume`/`handoff.md`; roda `journal verify` | N/A |
| Paridade MCP (golden 1.29) | `sparkforge_resume` em `ALTERADAS_DEPOIS_DO_GOLDEN` | N/A |
| git | `journal.jsonl` commitável; `*.torn` ignorado | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | `write_atomic` com `os.replace` sabotado; `append_line` com cauda; `read_jsonl` com linha ruim no meio | `tests/test_durable.py` | pytest, monkeypatch | AT-010, AT-011, AT-012 |
| Unit | Conjunto = anotações; par pela CLI e pelo MCP; leitura não grava; policy recusa sem evento; `sem_raiz_de_case`; journal indisponível; varredura sem literal | `tests/test_journal.py` | pytest | AT-001 a AT-004, AT-013 a AT-015 |
| Golden | 6 cenários de queda, `resume` e `verify` | `fixtures/journal/`, `tests/test_fixtures_golden_journal.py` | pytest | AT-005 a AT-010 |
| Golden existente | 13 de debate, `retomada`, `receipt/uniao_debate` sem regravação | suíte | pytest | AT-016 |
| Paridade | `sparkforge_resume` aditivo; `journal verify` só CLI | `test_fixtures_golden_mcp_parity.py`, `test_capability_parity.py` | pytest | Constraints |
| Backstop | Journal da raiz e das fixtures igual antes e depois | `tests/conftest.py` | pytest | SC de árvore limpa |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Journal não grava (diretório no lugar do arquivo, disco, trava) | Verbo roda; resultado ganha `journal: "unrecorded"` e `journal_reason` | No |
| `os.replace` com `PermissionError` no Windows | Até 5 tentativas com 20 ms; depois relança (estado do produto, não medição) | Yes |
| Falha entre temporário e rename | Temporário removido, original intacto, exceção relançada | No |
| Cauda cortada | Leitura tolera (`torn_tail`); append move a cauda para `.torn` | No |
| Linha inválida no meio | `DurableError` com o número da linha; `resume` devolve `chain: "broken"` | No |
| Verbo sem raiz de case (3 sem `repo`) | `journal: "unrecorded"`, `journal_reason: "sem_raiz_de_case"` | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `LITERAL_KEYS` | frozenset (código) | 10 chaves | Argumentos que entram literais no journal |
| `_TENTATIVAS_REPLACE` | int (código) | `5` | Tentativas do `os.replace` no Windows |
| `_ESPERA_REPLACE_S` | float (código) | `0.02` | Espera entre tentativas |

---

## Security Considerations

- Argumento só como sha256, salvo lista fechada de chaves com valor não absoluto (repo público).
- Caminhos de `outputs` sempre relativos à raiz; fora dela, `null` com o caminho relativo recusado.
- Raiz vinda de argumento passa por `sparkforge.paths.resolve_within` antes de abrir arquivo (lição do Snyk em §16).
- Nada chama provider nem rede (regra 23).

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | CLI: aviso em stderr quando `journal: "unrecorded"` |
| Metrics | Span do ledger continua por chamada MCP; o journal não duplica span |
| Tracing | O próprio journal: um par por verbo de escrita |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-15 | design-agent | Initial version |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_CHECKPOINT_RESUME_JOURNAL.md`
