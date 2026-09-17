# DEFINE: MCP SDK v2

> Migrar o servidor MCP do SparkForge do SDK `mcp` 1.x para o 2.x, com as validações que o 1.x fazia implicitamente reescritas no adapter e a paridade provada byte a byte contra um golden congelado sob o 1.x.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MCP_SDK_V2 |
| **Date** | 2026-09-11 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O servidor MCP (`sparkforge/adapters/mcp.py`, 86 tools, stdio e streamable HTTP) está preso ao `mcp>=1.0,<2`. O 2.x removeu os decoradores `@server.list_tools()`/`@server.call_tool()`, e — o que o pin não registra — também deixou de fazer três coisas que o adapter recebia do 1.x sem declarar: validar `arguments` contra o `inputSchema`, validar o resultado contra o `outputSchema`, e transformar o dict devolvido em `structuredContent` com o texto `json.dumps(indent=2)`. Uma troca só de API manteria as tools respondendo e perderia as duas validações em silêncio. Por isso a migração precisa reescrever essas garantias e provar que nenhum byte servido mudou.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador em Claude Code / Devin CLI | Consome as 86 tools via stdio | Fica preso a um SDK que não fala o protocolo `2026-07-28` nem `server/discover`; qualquer cliente que exija a era moderna fica fora |
| Operador em Devin Desktop | Consome via `http://<host>:<port>/mcp` | Mesmo bloqueio no transporte HTTP, onde o cliente é o que mais tende a subir de versão |
| Mantenedor do SparkForge | Evolui tools e adapter | A validação de entrada e saída depende de um comportamento implícito do SDK que nenhum teste do repositório cobra sem o SDK instalado; o pin `<2` é dívida registrada em duas docstrings |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: o servidor roda sob `mcp>=2,<3` (extras `mcp` e `dev`), com `Server` de baixo nível do 2.x registrado por `on_list_tools`/`on_call_tool`, nos dois transportes |
| **MUST** | G2: as três garantias do 1.x (validação de entrada, validação de saída, envelope `structuredContent` + `json.dumps(indent=2)`) viram funções puras em `sparkforge/adapters/mcp_envelope.py`, testáveis sem o SDK instalado, com as mensagens de erro copiadas do texto do 1.x |
| **MUST** | G3: golden de paridade gerado **uma vez** sob o 1.x e congelado em `fixtures/mcp_parity/`; sob o 2.x, diff vazio exceto campos em allowlist com motivo escrito |
| **MUST** | G4: SPEC 71 intacta — `sparkforge_code_read` fora de `tools/list` em HTTP, e `tools/call` recusando nome fora do catálogo do transporte |
| **MUST** | G5: locks reproduzíveis (`locks/py3.10.txt`, `locks/py3.11.txt`) regenerados por `scripts/gen_lock.py` com o 2.x e as transitivas novas, e o scan de SCA verde |
| **SHOULD** | G6: eval agêntico do candidato 2.x contra o baseline `2026-09-11-haiku-4-5`, N = 3, sem transição pass→fail ou pass→mixed |
| **SHOULD** | G7: metadados do servidor no construtor — `version` (do pacote), `description`, `instructions` curto apontando a tabela de verbos — com o crescimento declarado no `surface.lock` (regra 26) |
| **SHOULD** | G8: `cache_hints` para `tools/list`, já que o catálogo é estático por transporte |
| **COULD** | G9: teste explícito da era moderna — cliente 2.x no protocolo `2026-07-28` recebe `server/discover` e `tools/list` |

---

## Success Criteria

- [ ] SC1: `pip install '.[mcp]'` numa venv limpa resolve `mcp` 2.x (≥ 2.0, < 3.0), e `build_server("stdio")`/`build_server("http")` constroem sem exceção.
- [ ] SC2: `fixtures/mcp_parity/` contém o golden de `tools/list` (stdio: 86 tools; HTTP: 85) e de pelo menos **8** chamadas de `tools/call`: 1 sucesso por família (analyze, collect com fixture offline, verbo de topo, debate), 1 erro de fronteira (`exit_code`), 1 input inválido, 1 output fora do schema forçado, 1 nome fora do catálogo HTTP.
- [ ] SC3: sob o 2.x, a comparação do golden dá **0** diferenças em `content[].text`, `structuredContent` e `isError`, e as diferenças em metadados de servidor ficam restritas à allowlist (≤ 3 campos: `instructions`, `version`, `cache_hints`), cada um com motivo.
- [ ] SC4: `tests/test_adapters_mcp_envelope.py` (nome a fixar no DESIGN) roda **sem** o SDK e cobre os 4 caminhos: sucesso, input inválido, output fora do schema, erro de fronteira.
- [ ] SC5: `compare` do baseline contra o candidato, N = 3: **0** transições pass→fail/mixed (G6).
- [ ] SC6: `check_surface_lock.py`, `check_vnext_claims.py`, `check_status_numbers.py --strict`, `check_evals.py` e `ruff` verdes; suíte completa por lotes com **0** falhas.
- [ ] SC7: `gen_lock.py --check` (ou equivalente do script) verde para as duas versões de Python do lock.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Listagem stdio | Servidor 2.x, transporte stdio | `tools/list` | 86 tools, bytes de `name`/`description`/`inputSchema`/`outputSchema` iguais ao golden 1.x |
| AT-002 | Listagem HTTP | Servidor 2.x, transporte http | `tools/list` | 85 tools; `sparkforge_code_read` ausente; resto igual ao golden |
| AT-003 | Chamada com sucesso | Tool com fixture offline e `outputSchema` | `tools/call` válido | `structuredContent` = dict do `call_tool`; `content[0].text` = `json.dumps(result, indent=2)`; `isError` falso; bytes = golden |
| AT-004 | Input inválido | Argumentos que ferem o `inputSchema` (campo obrigatório ausente) | `tools/call` | `isError` verdadeiro, texto igual ao do 1.x no golden; `call_tool` **não** é chamado |
| AT-005 | Output fora do schema | Tool cujo retorno viola o `outputSchema` (forçado em teste) | `tools/call` | `isError` verdadeiro com a mensagem do 1.x; o dict inválido não sai em `structuredContent` |
| AT-006 | Erro de fronteira | `call_tool` devolve `{"error", "exit_code"}` | `tools/call` | `isError` verdadeiro, texto com `separators=(",", ":")`, igual ao golden |
| AT-007 | Tool escondida no HTTP | Transporte http | `tools/call sparkforge_code_read` | `isError` verdadeiro, mensagem "ferramenta indisponivel no transporte 'http'", sem executar |
| AT-008 | App HTTP | `build_http_app(build_server("http"))` | Lifespan aberto, POST `/mcp` e `/mcp/` | Ambos atendem sem redirect; outra rota dá 404 com o texto atual |
| AT-009 | Envelope sem SDK | Ambiente sem `mcp` instalado | Testes de `mcp_envelope.py` | Passam; nenhum import de `mcp` no módulo |
| AT-010 | Era moderna | Cliente 2.x no protocolo `2026-07-28` | `server/discover` e depois `tools/list` | Resposta válida, com o mesmo catálogo de AT-001 |
| AT-011 | SDK ausente | Sem o extra `mcp` | `build_server()` | `SystemExit` com `_INSTALL_HINT`, como hoje |
| AT-012 | Eval agêntico | Baseline `2026-09-11-haiku-4-5` + candidato 2.x, N = 3 | `python -m sparkforge.evals compare` | 0 transições pass→fail/mixed |

---

## Out of Scope

- `InputRequiredResult`/MRTR, extensions, resources e prompts MCP, subscriptions e apps.
- Sampling e elicitation: pediriam ao host que gerasse texto, o que fere o espírito da regra 23.
- OTel do SDK (é outra frente) e OAuth/auth do SDK.
- `transport_security`/proteção contra DNS rebinding no HTTP: é endurecimento que a SPEC 71 trata junto de token e rate limit.
- Mudar schemas, nomes, `detail_level` ou a classe de qualquer tool.
- Suportar 1.x e 2.x ao mesmo tempo.
- Trocar o texto do sucesso para `separators=(",", ":")`: seria mudança de byte sem medida, e é outra frente.
- Remover os pisos `idna`/`python-dotenv` do extra `mcp` — só se o SCA disser que a transitiva sumiu, e então como decisão registrada, não de passagem.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 23: nada de provider nem subprocess em `sparkforge/` | O eval roda fora do pacote (`scripts/run_agentic_eval.py`); o adapter segue sem chamar modelo |
| Technical | Import do SDK sempre tardio; o pacote funciona sem o extra `mcp` | `mcp_envelope.py` não importa `mcp`; `build_server` mantém o `try/except ImportError` |
| Technical | Regra 26: `instructions`, `description` e `cache_hints` movem a superfície | `check_surface_lock.py --update` com o crescimento declarado no commit |
| Technical | Regra 30: o eval só afirma "não regrediu" | Nenhum número de ganho publicado |
| Technical | O golden é gerado com o SDK 1.x e **nunca** regenerado sob o 2.x sem justificativa escrita | O script do golden fica em `scripts/` e registra a versão do SDK que o gerou |
| Technical | O CI instala por `--require-hashes` a partir de `locks/` | Subir o `mcp` exige regenerar os dois locks; o 2.2.0 traz `httpx2`, `mcp-types`, `opentelemetry-api`, `pyjwt[crypto]` e `pywin32` (win32) como transitivas novas |
| Technical | Os testes atuais usam `server.request_handlers[types.CallToolRequest]`, API do 1.x | `tests/test_adapters_mcp.py` é reescrito para a forma do 2.x |
| Technical | Suíte um processo por arquivo; `.py` novo precisa de `git add` antes dos lotes | Plano de verificação do BUILD |
| Resource | Eval N = 3 custa ~US$ 7 de host | Roda uma vez, no fim, com o snapshot já verde |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/adapters/mcp.py`, novo `sparkforge/adapters/mcp_envelope.py`, `scripts/` (gerador e comparador do golden), `fixtures/mcp_parity/`, `tests/`, `pyproject.toml`, `requirements.txt`, `locks/` | O adapter continua como casca fina sobre `tools.py` |
| **KB Domains** | MCP (servidor lowlevel, transportes stdio/streamable HTTP), testing (golden/snapshot, testes sem dependência opcional), Python packaging (extras, lock com hash) | Padrão de golden já usado em `fixtures/*/expected/` |
| **IaC Impact** | None | Sem infraestrutura; o CI muda só pelos locks |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Com `on_call_tool` devolvendo `CallToolResult` montado por nós, o 2.x não reescreve `content`/`structuredContent` no fio | A paridade byte a byte cai; teria de comparar depois da desserialização | [ ] |
| A-002 | O `serve_dual_era_loop` atende clientes do protocolo `2025-06-18` sem mudar o `tools/list` | Clientes antigos quebram; seria preciso negociar versão | [ ] |
| A-003 | `StreamableHTTPSessionManager(app, json_response, stateless)`, `.run()` e `.handle_request()` do 2.x se comportam como no 1.x para `stateless=True` | `build_http_app` precisa de reescrita, não só de manutenção | [ ] (assinaturas conferidas no wheel; comportamento não) |
| A-004 | `mcp.shared.memory.create_client_server_memory_streams` basta para dirigir o servidor em processo no gerador do golden e nos testes | O golden precisaria de subprocesso com stdio real — o que fica em `scripts/`, nunca em `sparkforge/` | [ ] |
| A-005 | O texto de erro de validação do 1.x é reproduzível só a partir da mensagem do `jsonschema.ValidationError` | Paridade de erro exige copiar a formatação exata do 1.x; se depender de versão do `jsonschema`, o golden fixa a versão | [ ] |
| A-006 | As transitivas novas do 2.2.0 resolvem nas duas versões de Python do lock e passam no SCA | Travaria no G5; alternativa seria fixar um 2.x anterior | [ ] |
| A-007 | Nenhum cliente em uso (Claude Code, Devin CLI/Desktop) depende de comportamento que só o 1.x tinha | O eval (G6) e o teste manual de conexão acusariam | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Causa medida no wheel (três garantias implícitas), com o efeito nomeado (validação perdida em silêncio) |
| Users | 2 | Três personas; a necessidade real da era moderna pelos clientes em uso é inferida, não medida (A-007) |
| Goals | 3 | MoSCoW com 9 metas, cada uma ligada a um SC ou AT |
| Success | 3 | Contagens exatas (86/85 tools, ≥ 8 chamadas, 0 diffs, ≤ 3 campos, 0 transições) |
| Scope | 3 | Tabela YAGNI do BRAINSTORM transformada em lista explícita, mais os limites de byte e de pin |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. As hipóteses A-001 a A-006 são validadas no início do BUILD (a primeira tarefa é o gerador do golden sob o 1.x, que exercita A-004 e A-005). A A-007 é validada pelo eval.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | define-agent | Versão inicial, a partir de `BRAINSTORM_MCP_SDK_V2.md` |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_MCP_SDK_V2.md`
