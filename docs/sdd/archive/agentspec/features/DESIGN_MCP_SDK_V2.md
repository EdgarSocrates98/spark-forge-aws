# DESIGN: MCP SDK v2

> Technical design for implementing MCP SDK v2

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MCP_SDK_V2 |
| **Date** | 2026-09-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_MCP_SDK_V2.md](./DEFINE_MCP_SDK_V2.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                         SERVIDOR MCP (SDK 2.x)                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  cliente (stdio | POST /mcp)                                              │
│        │                                                                  │
│        ▼                                                                  │
│  mcp.server.lowlevel.Server("sparkforge", version, description,           │
│        │                     instructions, cache_hints,                   │
│        │                     on_list_tools, on_call_tool)                 │
│        │                                                                  │
│        ├── tools/list ──► _list(ctx, params)                              │
│        │                    └─ tools_do_transporte(transport)  [SPEC 71]  │
│        │                    └─ Tool(input_schema=..., output_schema=...)  │
│        │                                                                  │
│        └── tools/call ──► _call(ctx, params)                              │
│                             │                                             │
│                             ▼                                             │
│               sparkforge/adapters/mcp_envelope.py  (SEM import de mcp)    │
│               ┌──────────────────────────────────────────────────┐        │
│               │ 1. fora do catálogo do transporte → erro         │        │
│               │ 2. validar_entrada(args, inputSchema)            │        │
│               │ 3. tools.call_tool(name, args)  (exceção → str)  │        │
│               │ 4. {"error","exit_code"} → erro compacto          │        │
│               │ 5. validar_saida(result, outputSchema)           │        │
│               │ 6. sucesso: structured + json.dumps(indent=2)    │        │
│               └──────────────────┬───────────────────────────────┘        │
│                                  ▼                                        │
│                     Envelope (dataclass pura: text, structured, is_error) │
│                                  │                                        │
│                                  ▼                                        │
│                     CallToolResult(content=[TextContent], ...)            │
│                                                                           │
│  HTTP: build_http_app → StreamableHTTPSessionManager(stateless=True)      │
└──────────────────────────────────────────────────────────────────────────┘

PROVA DE PARIDADE (fora do caminho de produção)

  [SDK 1.29, uma vez]  scripts/mcp_parity.py snapshot ──► fixtures/mcp_parity/*.json
                                                              │  (congelado)
  [SDK 2.x, CI]        tests/test_mcp_parity.py ──────────────┘  diff == allowlist
  [host, uma vez]      scripts/run_agentic_eval.py + compare (N=3, Haiku)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/adapters/mcp_envelope.py` | As três garantias que o 1.x fazia implicitamente, mais a conversão de exceção, como funções puras sobre dicts; devolve `Envelope` | Python + `jsonschema` (dependência do núcleo); nenhum import de `mcp` |
| `sparkforge/adapters/mcp.py` | Casca: `Server` 2.x com `on_list_tools`/`on_call_tool`, SPEC 71, `build_http_app`, `main` | `mcp>=2,<3`, starlette, uvicorn |
| `scripts/mcp_parity.py` | Gera o golden sob o 1.x (`snapshot`) e compara sob qualquer versão (`diff`), por cliente em processo | SDK instalado no momento da execução |
| `fixtures/mcp_parity/` | Golden congelado: `tools_list_{stdio,http}.json`, `calls.json`, `meta.json` (versão do SDK e do `jsonschema` que gerou) | JSON canônico, `sort_keys` |
| `tests/test_adapters_mcp_envelope.py` | Os quatro caminhos do envelope, sem o SDK | pytest |
| `tests/test_adapters_mcp.py` | Construção do servidor e do app HTTP, SPEC 71, reescrito para a API do 2.x | pytest + `mcp.Client(server)` |
| `tests/test_mcp_parity.py` | Golden contra o servidor vivo, com allowlist | pytest + `mcp.Client(server)` |

---

## Key Decisions

### Decision 1: `Server` de baixo nível + envelope puro fora do SDK

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o `call_tool` do SDK 1.29 (lido de `mcp/server/lowlevel/server.py`) faz quatro coisas que o adapter nunca escreveu:
1. `jsonschema.validate(arguments, tool.inputSchema)`, e em caso de falha `"Input validation error: {e.message}"`;
2. para o dict devolvido, `structuredContent = dict` e `content = [TextContent(json.dumps(dict, indent=2))]`;
3. com `outputSchema`: sem conteúdo estruturado, `"Output validation error: outputSchema defined but no structured output returned"`; com conteúdo inválido, `"Output validation error: {e.message}"`;
4. qualquer exceção do handler vira `isError` com `str(e)`.

O servidor 2.2.0 não importa `jsonschema`, e o `on_call_tool` devolve um `CallToolResult` pronto.

**Choice:** as quatro regras viram funções puras em `mcp_envelope.py`, que devolvem uma dataclass `Envelope(text, structured, is_error)`. O `_call` do adapter só converte o `Envelope` em `CallToolResult`. As mensagens são copiadas literalmente do 1.29.

**Rationale:** todo byte que chega ao cliente passa a sair de código nosso, então a paridade é conferível. E a validação passa a ter teste que roda sem o extra `mcp`: hoje ela só existe quando o SDK existe.

**Alternatives Rejected:**
1. `mcpserver` (FastMCP): o schema seria gerado da assinatura, os 86 schemas escritos à mão mudariam de bytes, e o golden ficaria impossível por construção.
2. Confiar no host para validar: seria perder a validação em silêncio, que é exatamente o defeito que esta entrega existe para evitar.

**Consequences:**
- Cerca de 80 linhas passam a ser nossas, e a formatação de `e.message` depende da versão do `jsonschema`. O `meta.json` do golden registra a versão; se ela mudar e a mensagem mudar, o teste acusa.
- O envelope é reutilizável por outro transporte sem SDK.

---

### Decision 2: golden no nível do fio, gerado uma vez sob o 1.29 e congelado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o CI terá só o 2.x depois do corte, então comparar 1.x × 2.x ao vivo exigiria dois ambientes para sempre.

**Choice:** `scripts/mcp_parity.py snapshot` roda com o 1.29 instalado, conecta um cliente **em processo** ao `build_server(transport)`:
- no 1.x, `mcp.shared.memory.create_connected_server_and_client_session`;
- no 2.x, `mcp.Client(server)`.

Grava cada resultado como `model_dump(mode="json", by_alias=True, exclude_none=True)` serializado com `sort_keys=True, ensure_ascii=False, indent=2`. Chaves com alias garantem que o golden fala o **fio** (`inputSchema`, `isError`, `structuredContent`), e não os nomes Python, que no 2.x viraram snake_case.

O `snapshot` roda a amostra **duas vezes** e recusa gravar se as duas divergirem: saída não determinística (horário, caminho absoluto) não entra no golden. O script se recusa a rodar `snapshot` sob `mcp>=2`, e só regenera com `--force-regenerate-under-2x --reason "<texto>"`, que grava o motivo no `meta.json`.

**Rationale:** "idêntico ao 1.x" só significa algo se a referência foi produzida pelo 1.x.

**Alternatives Rejected:**
1. Snapshot de `tools.call_tool` cru: não pega o envelope, que é justamente o que muda.
2. Stdio real com subprocesso: mais fiel ao transporte, mas o fio do stdio é o mesmo JSON-RPC, e o subprocesso fica fora do pacote de qualquer forma. Fica como COULD, se a A-004 falhar.

**Consequences:**
- O golden é congelado, e uma mudança legítima futura de tool exige regenerar com motivo escrito.
- O gerador precisa rodar **antes** de trocar o SDK instalado. Isso é a ordem B1 do build.

---

### Decision 3: amostra de `tools/call` escolhida por determinismo, não por cobertura

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o SC2 pede pelo menos 8 chamadas, uma por família mais os quatro caminhos de erro. Muitas tools devolvem caminho absoluto do repositório ou horário.

**Choice:** a amostra é uma lista literal em `scripts/mcp_parity.py` (`AMOSTRA`), cada item com `name`, `arguments` com caminhos relativos a `fixtures/`, `transport` e um `motivo`. Critérios:

| Caminho | Critério de escolha |
|---------|---------------------|
| 1 sucesso `analyze_*` | extrator puro sobre fixture versionada |
| 1 sucesso de verbo de topo | `rules_lookup` ou equivalente sem I/O de AWS |
| 1 sucesso `debate` | `debate_referee` sobre um caso de `fixtures/debate/` (só leitura) |
| 1 `collect_*` | só se houver caminho offline determinístico; senão, registrar no `meta.json` que não há, sem inventar |
| erro de fronteira | argumento que produz `AdapterError` (arquivo inexistente relativo) |
| input inválido | campo obrigatório ausente |
| nome fora do catálogo HTTP | `sparkforge_code_read` sob `transport="http"` |
| nome desconhecido | `sparkforge_nao_existe` (`KeyError` → `str(e)`) |
| output fora do schema | **não** entra no golden, porque nenhuma tool real viola o próprio schema; fica coberto em `test_adapters_mcp_envelope.py` com schema sintético |

As chamadas rodam com `cwd` num diretório temporário com cópia das fixtures, para que o `shared_ledger()` e o `.sparkforge/` não escrevam na árvore.

**Rationale:** um golden instável é pior do que nenhum, porque ensina a ignorar o diff.

**Alternatives Rejected:**
1. As 86 tools: descartado no YAGNI do BRAINSTORM; o envelope é o mesmo para todas.
2. Normalizar caminho e horário no comparador: um normalizador esconde diff real.

**Consequences:**
- Algumas famílias entram no golden só pela listagem, não pela chamada.

---

### Decision 4: allowlist de metadados, fechada e com motivo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** G7 e G8 acrescentam `instructions`, `version`, `description` e `cache_hints`. O 2.x também pode acrescentar campos default a `Tool` e `ListToolsResult`.

**Choice:** `tests/test_mcp_parity.py` tem `ALLOWLIST: dict[str, str]` (caminho JSON → motivo). Com `cache_hints = {"tools/list": CacheHint(ttl_ms=3_600_000, scope="public")}`, o resultado de `tools/list` ganha `ttlMs`/`cacheScope`, que ficam na allowlist. Campo novo que o 2.x acrescentar e que não estiver na allowlist derruba o teste: o build decide se o suprime (`exclude_none`, valor explícito) ou se o declara com motivo.

O `ttl_ms` de 1 hora é **convenção**, não medida: o catálogo só muda com upgrade do pacote. `scope="public"` porque a lista não depende de quem pergunta.

**Rationale:** diff novo só com declaração, que é o espírito da regra 26.

**Alternatives Rejected:**
1. Comparar só `content`/`structuredContent`/`isError`: esconderia o crescimento do handshake.

**Consequences:**
- A allowlist é a documentação executável do que mudou no fio.

---

### Decision 5: corte único, com locks regenerados na mesma entrega

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o CI instala de `locks/py3.10.txt` e `locks/py3.11.txt` com `--require-hashes`, e ambos fixam `mcp==1.30.0`. O 2.2.0 traz `httpx2`, `mcp-types`, `opentelemetry-api`, `pyjwt[crypto]` e `pywin32` (só em win32).

**Choice:**
- `mcp>=2,<3` nos extras `mcp` e `dev` e em `requirements.txt`;
- `python scripts/gen_lock.py` (exige rede e `uv`) e depois `--check`;
- os pisos `idna`/`python-dotenv` permanecem; removê-los fica fora de escopo.

**Rationale:** um lock desalinhado do `pyproject` faz o CI instalar um SDK que o código não usa.

**Alternatives Rejected:**
1. Deixar os locks para depois: o CI ficaria no 1.30 e testaria o código errado.

**Consequences:**
- O SCA passa a ver transitivas novas. Achado alto ou crítico bloqueia a entrega (A-006).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `scripts/mcp_parity.py` | Create | `snapshot` (recusa sob 2.x), `diff`, dupla execução, `AMOSTRA` literal, cliente em processo nas duas versões | @agentspec:python:python-developer | None |
| 2 | `fixtures/mcp_parity/{tools_list_stdio,tools_list_http,calls,meta}.json` | Create | Golden gerado pelo item 1 **sob o 1.29** | (general) | 1 |
| 3 | `sparkforge/adapters/mcp_envelope.py` | Create | `Envelope`, `envelope_da_chamada`, `validar_entrada`, `validar_saida`, mensagens do 1.29 | @agentspec:python:python-developer | None |
| 4 | `tests/test_adapters_mcp_envelope.py` | Create | 4 caminhos + exceção + nome fora do catálogo, sem SDK (AT-004, 005, 006, 009) | @agentspec:test:test-generator | 3 |
| 5 | `pyproject.toml` | Modify | `mcp>=2,<3` em `mcp` e `dev`; comentário do pin reescrito | (general) | 2 |
| 6 | `requirements.txt` | Modify | Espelho do piso | (general) | 5 |
| 7 | `sparkforge/adapters/mcp.py` | Modify | `Server` 2.x, `_list`/`_call` sobre o envelope, metadados, `cache_hints`, docstring do topo | @voltagent-dev-exp:mcp-developer | 3, 5 |
| 8 | `tests/test_adapters_mcp.py` | Modify | `_call` via `mcp.Client(server)`; handlers registrados conferidos pela API 2.x; SPEC 71; HTTP (AT-001, 002, 007, 008, 011) | @agentspec:test:test-generator | 7 |
| 9 | `tests/test_mcp_parity.py` | Create | Golden × servidor vivo, `ALLOWLIST` com motivo (AT-001..003, SC3) | @agentspec:test:test-generator | 2, 7 |
| 10 | `tests/test_mcp_modern_era.py` | Create | Cliente 2.x no protocolo `2026-07-28`: `server/discover` + `tools/list` (AT-010, COULD) | @voltagent-dev-exp:mcp-developer | 7 |
| 11 | `locks/py3.10.txt`, `locks/py3.11.txt` | Modify | Gerados por `gen_lock.py` | (general) | 5 |
| 12 | `tests/test_suite_batches.py` | Modify (se preciso) | Os três arquivos de teste novos caem em exatamente um lote | (general) | 4, 9, 10 |
| 13 | `README.md` | Modify | Linhas 140 e 207: pin e motivo | (general) | 7 |
| 14 | `docs/superpowers/STATUS.md` | Modify | Entrega registrada com números medidos | (general) | 9 |
| 15 | `docs/surface.lock.json` | Modify (se o gate acusar) | `check_surface_lock.py --update`, crescimento declarado | (general) | 7 |
| 16 | `docs/claims.lock.json` + doc auditado | Modify (se o gate acusar) | Remediar por lista de ids | (general) | 1, 3, 4, 9, 10 |
| 17 | `.claude/sdd/reports/BUILD_REPORT_MCP_SDK_V2.md` | Create | Relatório | (general) | all |

**Total Files:** 17 entradas (cerca de 21 arquivos físicos).

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 1, 3 | Funções puras, dataclass e type hints; script de CLI em `scripts/` |
| @voltagent-dev-exp:mcp-developer | 7, 10 | API de servidor MCP, transportes, era moderna do protocolo |
| @agentspec:test:test-generator | 4, 8, 9 | Suítes pytest, fixtures e golden |
| (general) | 2, 5, 6, 11–17 | Execução mecânica, gates e documentação; o build faz direto |

**Agent Discovery:**
- Scanned: `agents/**/*.md` do plugin e os agentes disponíveis na sessão.
- Matched by: tipo de arquivo, palavra-chave (MCP, test, python), caminho.
- Nota de execução: como no build do debate, quando delegar, **um escritor por vez** na árvore, e o briefing de cada agente leva as armadilhas do repositório (lotes por arquivo, `git add` de `.py` novo, sem `.glob` em `sparkforge/`, sem `def` duplicado no mesmo escopo, arquivos vazios na raiz).

---

## Code Patterns

### Pattern 1: envelope puro (`sparkforge/adapters/mcp_envelope.py`)

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import jsonschema

ERRO_SEM_ESTRUTURA = (
    "Output validation error: outputSchema defined but no structured output returned"
)


@dataclass(frozen=True)
class Envelope:
    text: str
    structured: dict[str, Any] | None
    is_error: bool


def _erro(texto: str) -> Envelope:
    return Envelope(text=texto, structured=None, is_error=True)


def _erro_compacto(payload: Mapping[str, Any]) -> Envelope:
    return _erro(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def validar_entrada(arguments: Mapping[str, Any], schema: Mapping[str, Any]) -> str | None:
    try:
        jsonschema.validate(instance=dict(arguments), schema=dict(schema))
    except jsonschema.ValidationError as exc:
        return f"Input validation error: {exc.message}"
    return None


def validar_saida(resultado: Any, schema: Mapping[str, Any] | None) -> str | None:
    if schema is None:
        return None
    if not isinstance(resultado, dict):
        return ERRO_SEM_ESTRUTURA
    try:
        jsonschema.validate(instance=resultado, schema=dict(schema))
    except jsonschema.ValidationError as exc:
        return f"Output validation error: {exc.message}"
    return None


def envelope_da_chamada(
    name: str,
    arguments: Mapping[str, Any] | None,
    catalogo: Mapping[str, Mapping[str, Any]],
    transport: str,
    executar: Callable[[str, dict[str, Any]], Any],
) -> Envelope:
    if name not in catalogo:
        return _erro_compacto(
            {
                "error": (
                    f"ferramenta indisponivel no transporte {transport!r}: {name}. "
                    "Use --transport stdio."
                ),
                "exit_code": 2,
            }
        )
    spec = catalogo[name]
    argumentos = dict(arguments or {})
    falha = validar_entrada(argumentos, spec["inputSchema"])
    if falha is not None:
        return _erro(falha)
    try:
        resultado = executar(name, argumentos)
    except Exception as exc:
        return _erro(str(exc))
    if isinstance(resultado, dict) and "error" in resultado and "exit_code" in resultado:
        return _erro_compacto(resultado)
    falha = validar_saida(resultado, spec.get("outputSchema"))
    if falha is not None:
        return _erro(falha)
    return Envelope(text=json.dumps(resultado, indent=2), structured=resultado, is_error=False)
```

Observações que o build confere contra o golden, sem assumir:
- a mensagem do nome fora do catálogo é a atual de `mcp.py` (linhas 142–145), não a do SDK;
- `json.dumps(resultado, indent=2)` **sem** `ensure_ascii=False`, porque é o que o 1.29 fazia. Se o golden mostrar outra coisa, o golden vence;
- `executar` recebe `tools.call_tool`. O `KeyError` de nome desconhecido não acontece para nome do catálogo, mas o `except Exception` reproduz o `str(e)` do 1.x para qualquer outra falha.

### Pattern 2: casca do servidor 2.x (`sparkforge/adapters/mcp.py`)

```python
def build_server(transport: str = "stdio") -> Any:
    try:
        from mcp.server import Server
        from mcp.server.caching import CacheHint
        from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool
    except ImportError as exc:
        raise SystemExit(_INSTALL_HINT) from exc

    from sparkforge.adapters.mcp_envelope import envelope_da_chamada

    catalogo = tools_do_transporte(transport)

    async def _list(ctx: Any, params: Any) -> Any:
        return ListToolsResult(
            tools=[
                Tool(
                    name=name,
                    description=spec["description"],
                    input_schema=spec["inputSchema"],
                    output_schema=spec["outputSchema"],
                )
                for name, spec in catalogo.items()
            ]
        )

    async def _call(ctx: Any, params: Any) -> Any:
        env = envelope_da_chamada(params.name, params.arguments, catalogo, transport, call_tool)
        return CallToolResult(
            content=[TextContent(type="text", text=env.text)],
            structured_content=env.structured,
            is_error=env.is_error,
        )

    return Server(
        "sparkforge",
        version=_versao_do_pacote(),
        description=_DESCRICAO,
        instructions=_INSTRUCOES,
        cache_hints={"tools/list": CacheHint(ttl_ms=3_600_000, scope="public")},
        on_list_tools=_list,
        on_call_tool=_call,
    )
```

Nomes Python do 2.x (`input_schema`, `structured_content`, `is_error`, `CacheHint`) foram lidos no wheel 2.2.0. O build confere contra o `mcp.types` instalado antes de escrever: se o construtor aceitar alias camelCase, snake_case continua sendo o escolhido, para ficar num nome só. `_call` é síncrono por dentro, como hoje: `call_tool` não é async.

### Pattern 3: cliente em processo nas duas versões (`scripts/mcp_parity.py`)

```python
def _abrir_cliente(server: Any):
    import mcp

    if mcp_major() >= 2:
        from mcp import Client

        return Client(server)
    from mcp.shared.memory import create_connected_server_and_client_session

    return create_connected_server_and_client_session(server)


def _canonico(modelo: Any) -> str:
    dado = modelo.model_dump(mode="json", by_alias=True, exclude_none=True)
    return json.dumps(dado, sort_keys=True, ensure_ascii=False, indent=2)
```

---

## Data Flow

```text
1. Cliente envia tools/call {name, arguments}
   │
   ▼
2. Server 2.x despacha para _call(ctx, params)
   │
   ▼
3. envelope_da_chamada: catálogo do transporte → validar_entrada → call_tool
   │                    → erro de fronteira? → validar_saida
   ▼
4. Envelope(text, structured, is_error)
   │
   ▼
5. CallToolResult → serializado pelo SDK com alias camelCase → cliente

Prova:
A. [1.29] mcp_parity.py snapshot ×2 → iguais? → fixtures/mcp_parity/ (commit)
B. [2.x]  test_mcp_parity.py: servidor vivo → _canonico → diff contra golden ⊆ ALLOWLIST
C. [host] run_agentic_eval.py (N=3) → python -m sparkforge.evals compare
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| SDK `mcp` 2.x (PyPI) | Dependência opcional (extra `mcp`) | N/A |
| Claude Code / Devin CLI | MCP stdio | N/A |
| Devin Desktop | MCP streamable HTTP em `/mcp`, stateless | Nenhuma (SPEC 71: tools de fonte desligadas) |
| `claude -p` (eval, só `scripts/`) | Subprocesso fora do pacote | Credencial do host |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Envelope sem SDK: sucesso, input inválido, output inválido (schema sintético), resultado não dict, erro de fronteira, exceção, fora do catálogo | `tests/test_adapters_mcp_envelope.py` | pytest | 100% dos ramos de `mcp_envelope.py` |
| Integration | Construção, SPEC 71, HTTP `/mcp` e `/mcp/`, lifespan, SDK ausente | `tests/test_adapters_mcp.py` | pytest + `mcp.Client` | Todos os AT do adapter |
| Parity | Golden 1.29 × servidor 2.x | `tests/test_mcp_parity.py` | pytest | `tools/list` × 2 + a amostra inteira |
| Protocol | Era moderna `2026-07-28` | `tests/test_mcp_modern_era.py` | pytest + `mcp.Client` | `server/discover`, `tools/list` |
| Agent eval | Baseline Haiku × candidato 2.x, N = 3 | `scripts/run_agentic_eval.py`, `python -m sparkforge.evals compare` | host `claude -p` | 0 transições pass→fail/mixed |
| Regression | Suíte completa, um processo por arquivo | `tests/test_suite_batches.py::LOTES` | pytest | 0 falhas |
| Gates | lastro, status, surface, evals, lock, ruff, Snyk Code, SCA | `scripts/check_*.py`, `gen_lock.py --check` | — | Todos verdes |

**Cobertura dos AT:**

| AT | Onde |
|----|------|
| AT-001, AT-002 | `test_mcp_parity.py` + `test_adapters_mcp.py` |
| AT-003 | `test_mcp_parity.py` |
| AT-004, AT-005, AT-006 | `test_adapters_mcp_envelope.py`; AT-004 e AT-006 também no golden |
| AT-007 | golden + `test_adapters_mcp.py` |
| AT-008 | `test_adapters_mcp.py` |
| AT-009 | `test_adapters_mcp_envelope.py` (sem `importorskip`) + um teste AST de que o módulo não importa `mcp` |
| AT-010 | `test_mcp_modern_era.py` |
| AT-011 | `test_adapters_mcp.py` (monkeypatch do import) |
| AT-012 | eval (B7) |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Nome fora do catálogo do transporte | `isError`, JSON compacto com a mensagem atual | No |
| `arguments` inválido | `isError`, `"Input validation error: …"`; `call_tool` não roda | No |
| `call_tool` levanta exceção | `isError`, `str(exc)`, como no 1.x | No |
| `{"error","exit_code"}` do adapter | `isError`, JSON compacto, mensagem acionável preservada | No |
| Resultado viola o `outputSchema` | `isError`, `"Output validation error: …"` | No |
| SDK ausente | `SystemExit(_INSTALL_HINT)` | No |
| `snapshot` sob `mcp>=2` | O script sai com código 2 e explica | No |
| Duas execuções do `snapshot` divergem | O script recusa gravar e lista a chamada instável | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `cache_hints["tools/list"].ttl_ms` | int | `3_600_000` | Convenção (o catálogo só muda com upgrade), não medida |
| `cache_hints["tools/list"].scope` | str | `"public"` | A lista não depende de quem pergunta |
| `version` | str | `importlib.metadata.version("sparkforge-aws")`, com fallback `"0+unknown"` | Metadado do servidor |
| `instructions` | str | Até cerca de 400 bytes: aponta a tabela de verbos e o `detail_level` | Contexto carregado pelo cliente; bytes declarados no commit |
| `mcp` (extra) | pin | `>=2,<3` | Corte único |

---

## Security Considerations

- A SPEC 71 fica intacta: `sparkforge_code_read` fora de `tools/list` em HTTP, e `tools/call` recusa pelo nome antes de validar ou executar.
- A validação de entrada volta a ser **obrigatória e nossa**. Antes ela dependia de um detalhe do SDK que mudou sem aviso.
- `transport_security` (DNS rebinding) continua desligado por decisão registrada (fora de escopo). `build_http_app` usa o manager direto, como hoje, e não `streamable_http_app`, que ligaria a proteção só para localhost e mudaria o comportamento do Devin Desktop.
- Transitivas novas (`pyjwt[crypto]`, `httpx2`, `opentelemetry-api`, `pywin32`) passam pelo SCA. Achado alto ou crítico bloqueia.
- O código novo passa pelo Snyk Code: nada vindo de argv chega a caminho ou subprocesso em `scripts/mcp_parity.py`, que só aceita os subcomandos `snapshot`/`diff` e grava sob a base fixa `fixtures/mcp_parity/`.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Sem mudança; o SDK 2.x loga pelo `logging` padrão |
| Metrics | Os spans de `shared_ledger()` continuam gravados por `call_tool` (regra 27), inalterados |
| Tracing | OTel do SDK (`_otel.py`) **não** é ligado (frente separada) |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Itens 1–2 **com o 1.29 instalado**: gerador, dupla execução, golden commitado | Golden estável; A-004 e A-005 respondidas |
| B2 | Itens 3–4 | Testes do envelope verdes sem SDK |
| B3 | Item 5; instalar `mcp>=2,<3`; item 7 | `build_server` constrói nos dois transportes |
| B4 | Itens 8–9 | Diff do golden ⊆ allowlist (A-001, A-002, A-003) |
| B5 | Item 10 | Era moderna verde (COULD: se o cliente 2.x não expuser o protocolo, registrar no relatório e seguir) |
| B6 | Itens 6, 11–16; ruff, suíte por lotes, gates, Snyk, SCA | Tudo verde |
| B7 | Eval Haiku N = 3 (~US$ 7) contra `2026-09-11-haiku-4-5`, no workspace de prova | 0 transições pass→fail/mixed (SHOULD) |
| B8 | Item 17; statuses do DEFINE e do DESIGN | — |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | design-agent | Versão inicial |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_MCP_SDK_V2.md`
