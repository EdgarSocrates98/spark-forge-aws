# FASE 1 — Spark Forge AWS como produto de referência Agent-First

Relatório de fechamento da FASE 1 do `prompt_evo_foco1.md`. Cada item cita
a evidência que o sustenta; nada aqui é promovido por conveniência.

## §1.1 — Install lifecycle

| Requisito | Estado | Evidência |
|---|---|---|
| Escopos/perfis/hosts/componentes | FEITO | `install --scope project|workspace|user --host {claude,devin,codex,copilot,all} --profile {minimal,recommended,full} --components skills,agents,mcp,tui,graph-studio` verificado em install real num scratch (1393 arquivos gerenciados, 0 recusas). |
| doctor/repair/update/uninstall | FEITO | `status`/`repair` passaram a cobrir configs gerenciados (`.mcp.json`): apagar o arquivo move o estado para `degraded` e `repair` o restaura (antes: `healthy` mudo — bug P1 corrigido com testes). `uninstall` removeu os 1393 preservando state. `install doctor` ganhou `--scope`/`--root` na CLI (o handler já os lia). |
| `.mcp.json` compartilhado | FEITO | Dedup por path: um só arquivo serve os quatro hosts de projeto com dono único no manifesto + fallback de lookup cross-host. Recibo `completed`, sem `FAIL` espúrio. |
| Recibo honesto | FEITO | Codex em escopo projeto declara `mcp-scope:codex` `NOT_APPLICABLE` (Codex 0.160.0 não lê `.mcp.json` de projeto — verificado nativamente), nunca sucesso falso. |

## §1.2 — AI Host Experience

| Requisito | Estado | Evidência |
|---|---|---|
| Fluxos Devin/Claude/Codex | FEITO | Devin verificado nativamente: `devin mcp list` lista `sparkforge-aws`, 96 skills do projeto viram `/claude:*`. Claude: `.mcp.json` lido com aprovação por sessão (mecanismo real, documentado). Codex: `codex mcp list` → `enabled` sob `CODEX_HOME` redirecionado em `--scope user`. |
| Abrir host quando suportado | FEITO | `sparkforge-aws ai` (novo, §3.7): detecta binário→versão→auth oficial→integração→lança com `--launch`+TTY; deslogado recusa com `login_hint`. devin observado `READY`. MCP `sparkforge_aws_ai` expõe só o painel (lançar é fronteira humana). |
| Instruções/contexto portáteis | FEITO | Receitas `usar-com-{devin,claude,codex}`, `verificar-mcp`, `instalar-e-comecar`; quickstart documenta `ai`. |

## §1.3 — Skills & Agents

- 14 coordenadores + 5 executores + 60 skills auditados; 113 testes de paridade
  mirror↔canônico verdes.
- `docs/agentic-catalog.md` gerado de `scripts/gen_agentic_catalog.py` com as
  fichas §11 completas + cookbook de invocação por host; frescor travado por
  `tests/test_agentic_catalog.py`.

## §1.4 — TUI

- 17 entradas de menu cobrindo os 11 dashboards exigidos (PySpark, Glue, EMR,
  Iceberg, Lake Formation, Performance, Streaming, Graphfy, Findings, Evidence,
  Agentic Tasks) — todas invocam argv real.
- Contrato fortalecido: `test_menu_argv_parse_on_real_cli` parseia cada argv no
  parser de verdade — pegou `install mcp-verify` (verbo inexistente, corrigido
  para `mcp verify`) e `judge` sem `--facts` (corrigido).

## §1.5 — Graph

- Graph Studio validado com índice real: 15 nós, ForgeGraphView/v1 emitido,
  `SF-GRAPH-NO-INDEX` + unlock fora do índice.

## §1.6 — Documentação PT-BR

- 16 receitas em `docs/learn/recipes/` cobrindo as 14 exigidas (instalar,
  Devin, Claude, Codex, PySpark, Glue 5.1, performance, Iceberg,
  Lake Formation/FGAC, streaming, agents, skills, MCP, Graphfy) — escritas com
  comandos executados de verdade antes de documentar.

## §1.7 — E2E

Cadeia real num repo scratch:

```text
install → .mcp.json + 1393 arquivos → analyze pyspark (17 facts, file:line:col
+ sha256) → judge (5 findings, rule_id + evidence) → case open/update indexa
facts_index (17/10 kinds) e findings_index (5 por severidade) → set_phase
diagnosis → next-step roteia AGENT-004 → pyspark-code-reviewer + playbook
```

O desvio D-4b-5 (`facts_index`/`findings_index` nunca populados) foi corrigido
em código, com testes — `next-step` agora distingue "sem inventário" de "facts
sem findings" de "investigação julgada".

## §12 — Revisão semântica

`docs/experience/semantic-review.md`: 17 documentos com estado promovido por
evidência; **7 contradições reais** corrigidas (verbo inexistente `mcp serve`
em 5 docs, chave `_forge_managed` fictícia, claim falso de Codex+MCP,
`doctor`→`status` para drift, `mcp-verify`→`mcp verify`). `check_docs` sobre
940 arquivos: 0 problemas.

## Gates de fábrica executados

| Gate | Resultado |
|---|---|
| Surface lock | atualizado e verde (+2 086 bytes declarados no commit) |
| Reference docs | 296 páginas, `test_reference_docs` 5/5 |
| Paridade CLI↔MCP | 81 verdes (`test_capability_parity` + `test_docs_coverage`) |
| Harness authorization | 214 verdes (146 tools, 136 com caminho declarado) |
| Status numbers | `--strict` 0 divergências |
| check_docs (links+verbos) | 940 arquivos, 0 problemas |
| Lotes CLI/MCP/case/UI | 718 + 12 + 7 + 30 + 26 + 44 verdes |
| Ruff | limpo nos arquivos tocados |

## Limitações declaradas (não escondidas)

- Copilot: sem CLI instalado — `ai` reporta `NOT_DETECTED`/`logged_in: null`;
  claims não promovidos.
- Claude: `.mcp.json` de projeto exige aprovação por sessão — comportamento
  real do host, documentado, não contornado.
- Codex: MCP só por `--scope user` (limitação do host 0.160.0, verificada).
- Revisão semântica de `docs/guia/**`, `docs/reference/**`, `docs/experience/**`
  restante: AUTOMATICALLY_CHECKED, sweep da FASE 8.

## Suíte integral (gate final)

- **Run 1** (código pré-fixes, 1h25m18s): 14 877 passaram, 17 skipped,
  **2 falhas** — ambas diagnosticadas e corrigidas:
  1. `test_no_tool_is_orphan`: `sparkforge_aws_ai` órfã → citada no passo 0
     do `sf-inventory` (commit `391d29ed`, mirrors re-renderizados).
  2. `test_arquivos_de_instrucao_cabem_no_teto`: CLAUDE.md/AGENTS.md em
     26 378/26 435 bytes no worktree vs 26 000/25 992 no blob — drift CRLF
     de worktree (o defeito que `.gitattributes eol=lf` já declarava);
     checkout normalizado, sem mudança de conteúdo.
- **Run 2** (1h24m38s): 14 876 passaram, 17 skipped, **3 falhas** —
  todas diagnosticadas:
  1. `test_catalogo_em_dia` + `test_referencia_em_dia`: os espelhos
     gerados (`docs/agentic-catalog.md`, `docs/guia/referencia/agents/
     sf-inventory.md`) ficaram velhos quando `391d29ed` citou
     `sparkforge_aws_ai` — regen commitado (`c14ef60c`).
  2. `test_stale_receipt_lock_is_recovered_only_when_pid_is_absent`:
     flake de lock/PID sob carga de suíte (mesmo padrão observado no
     spark-forge-azure); passa isolado e por módulo.
- **Run 3**: relançada detached no HEAD pós-regen
  (`sf-suite3.log`, PID 17416) — gate final; resultado ao fechar.
