# BRAINSTORM: MCP SDK v2

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MCP_SDK_V2 |
| **Date** | 2026-09-11 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Frente de `prompt_new_evo.md`: migrar o servidor MCP do SparkForge do SDK `mcp` 1.x (o `pyproject.toml` fixa `mcp>=1.0,<2`; `sparkforge/adapters/mcp.py` usa `@server.list_tools()`/`@server.call_tool()`) para o SDK v2 / spec 2026-07-28, se existirem em fonte T1. O harness de eval agêntico e o baseline Haiku estão disponíveis para medir regressão.

**Context Gathered:**
- **T1/T2 conferido.** O PyPI lista `mcp` 2.2.0 (a mais recente), 2.0.0–2.1.1 e 1.30.0; a versão instalada localmente é a 1.29.0. O wheel 2.2.0 baixado mostra:
  - `Server.__init__(name, *, version, title, description, instructions, website_url, icons, cache_hints, lifespan, on_list_tools=..., on_call_tool=..., ...)`, sem os decoradores `list_tools`/`call_tool`;
  - as strings de protocolo `"2026-07-28"` (em `server/mcpserver/resolve.py`), `"2025-11-25"` e `"2025-06-18"`;
  - `server/discover` no cliente;
  - `Server.run` delega a `serve_dual_era_loop`, que atende o handshake legado e a era moderna, com envelope por requisição.
- **Custo não óbvio medido no wheel.** O `call_tool` do 1.x fazia três coisas implícitas:
  1. `jsonschema.validate(arguments, inputSchema)`;
  2. validação do resultado contra o `outputSchema`;
  3. a conversão do dict devolvido em `structuredContent`, com o texto em `json.dumps(results, indent=2)`.

  O servidor 2.x não importa `jsonschema` em lugar nenhum (só `client/session.py` importa), e `on_call_tool` devolve um `CallToolResult | InputRequiredResult` pronto. Migrar só a API manteria as 86 tools funcionando e perderia as duas validações sem nenhum aviso.
- **O que não muda:** `StreamableHTTPSessionManager(app, json_response, stateless)`, `.run()` e `.handle_request()` existem no 2.x com as mesmas assinaturas. `build_http_app` conserva a forma.
- O adapter nunca validou nada por conta própria: `sparkforge/adapters/` não tem `jsonschema`. A dependência `jsonschema>=4.0` já está no núcleo do `pyproject.toml`.
- A docstring do topo de `sparkforge/adapters/mcp.py` já registra por que o pin `<2` existe: o 2.x quebraria o servidor no import.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/adapters/mcp.py` + novo `sparkforge/adapters/mcp_envelope.py`; `scripts/` para o snapshot; `fixtures/mcp_parity/` para o golden | O runtime continua sem importar o SDK no topo do módulo |
| Relevant KB Domains | MCP (servidor, transportes), testing (golden/snapshot), Python packaging (extras) | Padrões de golden já usados em `fixtures/` |
| IaC Patterns | N/A | Sem infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Objetivo da migração? | Paridade + recursos novos ("os dois primeiros") | O MVP exige paridade provada **e** um recorte de recursos do 2.x |
| 2 | Estratégia de versão? | Corte único no 2.x (`mcp>=2,<3`) | Sem shim nem dois caminhos; a abordagem C fica descartada |
| 3 | Critério de sucesso? | Snapshot + harness | Golden 1.x byte a byte, mais o eval Haiku N=3 sem pass→fail |
| 4 | Amostras disponíveis? | Só as do repositório | Fixtures existentes + baseline `evals/agentic/fase0/baselines/2026-09-11-haiku-4-5` |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/` (casos por extrator) | 1 por família de tool | Entradas offline para `tools/call` |
| Output examples | `fixtures/mcp_parity/` (a criar, sob o SDK 1.29) | `tools/list` × 2 transportes + amostra de `tools/call` | Golden congelado |
| Ground truth | `evals/agentic/fase0/baselines/2026-09-11-haiku-4-5/r{1,2,3}.json` | 3 execuções × 13 perguntas | Lado "antes" do `compare` |
| Related code | `sparkforge/adapters/mcp.py`, `sparkforge/adapters/tools.py`, `tests/test_adapters_mcp.py` | 3 | `TOOLS` e schemas escritos à mão continuam como fonte da verdade |

**How samples will be used:**

- O golden de `tools/list` e `tools/call` é gerado **uma vez** sob o 1.x e passa a ser a referência do teste sob o 2.x.
- O baseline Haiku é o lado de referência de `python -m sparkforge.evals compare`.

---

## Approaches Explored

### Approach A: `Server` de baixo nível do 2.x + garantias explícitas no adapter ⭐ Recommended

**Description:** `Server("sparkforge", version=..., description=..., instructions=..., cache_hints=..., on_list_tools=_list, on_call_tool=_call)`. O adapter passa a fazer ele mesmo, em funções puras de `mcp_envelope.py`:
- a validação de entrada;
- a validação de saída;
- o envelope `CallToolResult(structuredContent=result, content=[TextContent(json.dumps(result, indent=2))])`.

**Pros:**
- Os 86 schemas de `tools.py` ficam intocados: o `surface.lock` só se move pelos campos novos declarados.
- O comportamento que era implícito no SDK vira código nosso, testável **sem o SDK instalado**.
- Os recursos novos entram pelo construtor, sem refatoração.

**Cons:**
- Cerca de 60 linhas de validação passam a ser nossas.
- O texto de erro de validação muda de autor. A decisão foi reproduzir o texto do 1.x.

**Why Recommended:** é a única das três em que dá para conferir a paridade byte a byte, porque todo byte que chega ao cliente sai de código nosso.

---

### Approach B: `mcpserver` de alto nível (o antigo FastMCP)

**Description:** as tools viram funções Python, e o SDK gera o schema a partir da assinatura e do pydantic.

**Pros:**
- Menos código de protocolo no adapter.

**Cons:**
- Os 86 schemas escritos à mão seriam gerados de novo: todos mudam de bytes, e o `surface.lock` inteiro se move.
- O snapshot "idêntico ao 1.x" fica impossível por construção.

---

### Approach C: shim 1.x + 2.x

**Description:** detecta a versão instalada e mantém os dois caminhos.

**Pros:**
- Não força a atualização em quem já instalou.

**Cons:**
- Contradiz o corte único escolhido.
- Dobra a matriz de teste de um servidor que não guarda estado.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-11 |
| **Reasoning** | Paridade conferível byte a byte; os schemas de `tools.py` continuam como a única fonte da verdade |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Corte único: `mcp>=2,<3` nos extras `mcp` e `dev` | Um caminho só, com teste só | Shim com as duas versões |
| 2 | Validação de entrada e de saída reimplementada em `mcp_envelope.py`, em funções puras | O 2.x não valida; perder a validação calado é regressão | Confiar no host para validar |
| 3 | O texto do sucesso continua `json.dumps(result, indent=2)` | É o que o 1.x mandava; trocar agora mudaria byte sem medida | `separators=(",", ":")` também no sucesso |
| 4 | As mensagens de erro de validação reproduzem o texto do 1.x | Paridade, sem diff para explicar | Mensagem própria em PT |
| 5 | Golden gerado uma vez sob o 1.29 e congelado em `fixtures/mcp_parity/` | O CI depois só terá o 2.x; regenerar sob o 2.x apagaria a referência | Comparar ao vivo 1.x × 2.x no CI |
| 6 | Allowlist explícita para os campos novos (`instructions`, `cache_hints`, `version`), cada um com o motivo escrito | Diff novo só com declaração, como pede a regra 26 | Aceitar qualquer diff nos metadados |
| 7 | Eval Haiku N=3 (~US$ 7) contra o baseline de 2026-09-11 | Mede a regressão no nível do agente; a regra 30 impede afirmar ganho | Só o snapshot |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `InputRequiredResult` / MRTR (`input-required`) | Nenhuma tool pede entrada no meio da chamada; o case vive em `case.yaml` | Yes |
| Extensions do protocolo | Sem consumidor identificado | Yes |
| Resources e prompts MCP | O servidor expõe só tools; knowledge já sai por tool | Yes |
| Sampling / elicitation | Pediria ao host que gerasse texto: fere o espírito da regra 23 | No (sem decisão estrutural nova) |
| OTel do SDK (`_otel.py`) | A frente OTel GenAI é separada; os spans próprios já existem | Yes |
| OAuth / auth do SDK | O HTTP é local; a SPEC 71 já desliga as tools de fonte | Yes |
| `transport_security` (proteção contra DNS rebinding) | Endurecer o HTTP é trabalho próprio, junto de token e rate limit (SPEC 71) | Yes |
| Subscriptions / apps | Sem caso de uso | Yes |
| Amostra de `tools/call` com uma chamada por tool (86) | Uma por família cobre o envelope; o domínio já tem testes próprios | Yes |

**Mantidos no MVP:** `cache_hints` em `tools/list`, metadados do servidor (`version`, `description`, `instructions`) e teste explícito da era moderna (`server/discover` no protocolo `2026-07-28`).

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Forma do adapter (Server 2.x + `mcp_envelope.py`, ordem das garantias, `indent=2`, texto de erro do 1.x) | ✅ | "Sim, segue" | No |
| Medição em 3 degraus (golden 1.x congelado → diff vazio sob o 2.x com allowlist → eval Haiku N=3) | ✅ | "Sim, escreve o BRAINSTORM" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O servidor MCP está preso ao SDK 1.x (`mcp<2`) porque o 2.x removeu os decoradores e as validações implícitas das quais o adapter dependia sem declarar; migrar exige reescrever essas garantias e provar que nenhum byte servido às 86 tools mudou.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador em Claude Code / Devin CLI (stdio) | Instalação limpa futura resolve para o SDK 2.x só quando o pin cair; até lá fica fora dos clientes novos |
| Operador em Devin Desktop (HTTP) | O protocolo `2026-07-28` e o `server/discover` não são atendidos pelo 1.x |
| Mantenedor | O pin `<2` é dívida registrada na docstring, e a validação depende de um comportamento implícito do SDK |

### Success Criteria (Draft)
- [ ] Golden de `tools/list` (stdio e HTTP) e da amostra de `tools/call` gerado sob o 1.29 e commitado.
- [ ] Sob o `mcp>=2,<3`, diff vazio contra o golden em `content[].text`, `structuredContent` e `isError`, exceto os campos da allowlist, cada um com motivo.
- [ ] `mcp_envelope.py` testado sem o SDK instalado: input inválido, output fora do schema, erro de fronteira e sucesso.
- [ ] Um cliente 2.x no protocolo `2026-07-28` recebe `server/discover` e `tools/list`.
- [ ] `compare` do baseline `2026-09-11-haiku-4-5` contra o candidato 2.x, N=3: zero transição pass→fail/mixed.
- [ ] `check_surface_lock.py --update` com o crescimento declarado no commit; os gates de lastro, de status e de evals verdes.

### Constraints Identified
- Regra 23: nada de provider nem subprocess em `sparkforge/`; o eval roda fora do pacote.
- Regra 26: o `instructions` e os metadados movem a superfície e têm de declarar quanto.
- Regra 30: o eval só afirma "não regrediu"; nenhum ganho.
- SPEC 71: `sparkforge_code_read` continua fora do catálogo HTTP, e a porta de `tools/call` continua recusando nome fora do catálogo.
- O import do SDK continua tardio; o pacote funciona sem o extra `mcp`.
- A suíte roda um processo por arquivo (`tests/test_suite_batches.py::LOTES`).

### Out of Scope (Confirmed)
- Tudo na tabela YAGNI acima.
- Mudar schemas de tools, nomes de tools ou `detail_level`.
- Suporte simultâneo ao 1.x.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 7 (4 de discovery, 1 de abordagem, 1 de YAGNI, 2 de validação) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 9 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_MCP_SDK_V2.md`
