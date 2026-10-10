# Revisão semântica da documentação pública — FASE 1

Ledger da auditoria semântica (§12 do programa). Estados:

```text
INVENTORIED              — existe no inventário, não lido semanticamente
AUTOMATICALLY_CHECKED    — passou em gates automáticos (links, índice, geração)
TECHNICALLY_VERIFIED     — comandos/claims conferidos contra a CLI real
SEMANTICALLY_REVIEWED    — lido por inteiro, comparado com o código,
                           contradições corrigidas, evidência registrada
USER_JOURNEY_VALIDATED   — exercitado como caminho real de usuário fim a fim
```

Estado **nunca** sobe só porque um script passou. Cada promoção abaixo cita
a evidência que a sustenta.

## Documentos revisados nesta fase

| Documento | Estado | Evidência |
|---|---|---|
| `README.md` | SEMANTICALLY_REVIEWED | Seção agent-first reescrita; corrigidos: claim `sparkforge-aws mcp serve` (verbo inexistente — real: `python -m sparkforge_aws.adapters.mcp --transport stdio`), perfil necessário para coordenadores (`--profile full`), escopo MCP do Codex, contagem de skills (60 canônicas; `_shared` não é skill). `check_status_numbers --strict` passa. |
| `docs/installation/mcp.md` | SEMANTICALLY_REVIEWED | Reescrito: citava verbo inexistente `mcp serve` e chave gerenciada fictícia `_forge_managed`; agora reflete a entrada real `mcpServers["sparkforge-aws"]` (verificada no `.mcp.json` de um install real), a tabela de consumo por host verificada nativamente (Devin lê; Claude pede aprovação; Codex não lê `.mcp.json` de projeto) e o par `status`/`install doctor` correto. |
| `docs/installation/codex-cli.md` | SEMANTICALLY_REVIEWED | Reescrito: afirmava que `.mcp.json` gerenciado registra o server para o Codex — Codex 0.160.0 verificado não lê `.mcp.json` nem `.codex/config.toml` de projeto; doc agora aponta `--scope user --host codex` (verificado com `codex mcp list` → `enabled` sob `CODEX_HOME` redirecionado) e declara o `mcp-scope:codex` `NOT_APPLICABLE` do recibo. |
| `docs/installation/claude-code.md` | SEMANTICALLY_REVIEWED | Entrada MCP corrigida para `mcpServers["sparkforge-aws"]` + fluxo real de aprovação na sessão (verificado: `claude mcp list` só mostra aprovados). |
| `docs/installation/devin-cli.md` | SEMANTICALLY_REVIEWED | Entrada MCP corrigida; `devin mcp list` verificado nativamente listando `sparkforge-aws` com o comando exato do `.mcp.json`; 96 skills do projeto expostas como `/claude:*`. |
| `docs/installation/troubleshooting.md` / `.en.md` | SEMANTICALLY_REVIEWED | `mcp-verify` → `mcp verify` (verbo real; `mcp` só tem a sub-ação `verify`). |
| `docs/installation/quickstart.md` | TECHNICALLY_VERIFIED | `status` e `doctor` existem e emitem saída estruturada (verificado por invocação real). |
| `docs/installation/update-and-repair.md` | SEMANTICALLY_REVIEWED | `doctor` → `status` como quem mostra o drift (o doctor agentic não computa drift de install). Cobertura de drift do `.mcp.json` adicionada ao `status`/`repair` nesta fase, com teste. |
| `docs/tutorials/first-run.md` | SEMANTICALLY_REVIEWED | Rótulos `mcp-verify` → `mcp verify` (2 tabelas). |
| `docs/learn/recipes/*.md` (16) | SEMANTICALLY_REVIEWED | 10 receitas novas escritas nesta fase com comandos executados de verdade antes de documentar (`usar-agents`, `usar-com-claude`, `usar-com-devin`, `usar-com-codex`, `usar-skills`, `verificar-mcp`, `graph-studio`, `streaming-eval`, `glue-51-investigation`, `doctor-extras`); 6 anteriores relidas e coerentes. |
| `docs/agentic-catalog.md` | AUTOMATICALLY_CHECKED | Gerado por `scripts/gen_agentic_catalog.py` dos canônicos; frescor travado por `tests/test_agentic_catalog.py` (14 coordenadores, 5 executores, 60 skills, campos §11). |
| `AGENTS.md` | SEMANTICALLY_REVIEWED | Tabela de coordenadores e contrato "playbook é o piso" conferidos contra `rules/catalog/routing.yaml` e `sparkforge_aws.integrate.render` (14 coordenadores, despacho verificado em Devin/Claude/Codex nesta fase). |
| `CLAUDE.md` | TECHNICALLY_VERIFIED | Regras 11–28 citadas e aplicadas nesta fase (drift, findings, índices); tabela de verbos conferida contra o parser real. |
| `GUIA_DE_USO.md` | TECHNICALLY_VERIFIED | Seções de invocação por host conferidas contra o comportamento observado (playbook para Codex, subagentes Devin/Claude). |
| `AGENT_PROTOCOL.md` | TECHNICALLY_VERIFIED | Regras de roteamento conferidas contra `routing.yaml` (ROUTES/AGENTS) e o `next-step` E2E. |

## Inventariados, revisão pendente

| Documento | Estado | Observação |
|---|---|---|
| `docs/installation/copilot-cli.md` | INVENTORIED | Sem CLI Copilot para verificação nativa — claim não promovido. |
| `docs/installation/global-installation.md`, `portable-installation.md`, `workspace-installation.md`, `uninstall.md`, `quickstart.en.md` | AUTOMATICALLY_CHECKED | Passam nos gates de docs; sem leitura semântica completa nesta fase. |
| `docs/experience/*.md` | AUTOMATICALLY_CHECKED | Gates passam; revisão semântica no sweep da FASE 8. |
| `docs/guia/**`, `docs/reference/**` | AUTOMATICALLY_CHECKED | Referência gerada travada por `test_reference_docs.py`; `commands.md` conferido pontualmente (`mcp verify`). |
| Histórico, SDD, ADRs, `docs/reports/**`, `docs/historico/**` | INVENTORIED | Preservados por política; fora do escopo de revisão pública. |

## Contradições reais encontradas e corrigidas nesta fase

1. **Verbo inexistente `sparkforge-aws mcp serve`** citado em `README.md`,
   `docs/installation/mcp.md`, `claude-code.md`, `devin-cli.md` e
   `codex-cli.md` — o `mcp` real só tem `verify`; o server sobe por
   `python -m sparkforge_aws.adapters.mcp --transport stdio`.
2. **Chave gerenciada fictícia `_forge_managed.spark-forge-aws`** em
   `mcp.md` — real: `mcpServers["sparkforge-aws"]`.
3. **Codex consome `.mcp.json` de projeto** — falso (verificado 0.160.0);
   corrigido para declarar a limitação e o caminho `--scope user`.
4. **`doctor` mostra drift** em `update-and-repair.md` — real: `status`.
5. **`mcp-verify` como verbo** em `troubleshooting.{md,en.md}` e
   `first-run.md` — real: `mcp verify`.
6. **`status`/`repair` cegos ao `.mcp.json`** — drift de config não era
   computado; corrigido em código (`lifecycle.py`) com testes, não só em doc.
7. **`facts_index`/`findings_index` nunca populados** — desvio D-4b-5
   corrigido em código; docs de referência regenerados.

## Limitação declarada

Revisão semântica completa de `docs/guia/**`, `docs/reference/**` e
`docs/experience/**` fica para o sweep final (FASE 8), quando a superfície
de todos os forges estiver congelada — revisar antes do freeze revalidaria
conteúdo que ainda pode mudar. O que era contradição contra comportamento
verificado nesta fase foi corrigido agora.
