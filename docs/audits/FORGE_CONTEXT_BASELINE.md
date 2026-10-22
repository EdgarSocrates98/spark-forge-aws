# FORGE_CONTEXT_BASELINE — spark-forge-aws

Auditoria do Ciclo 1 (lf-0034 / `prompt_evo_install2.0.md` §3). Documento de
evidência: cada afirmação cita o comando executado ou o arquivo:linha inspecionado.
Nada aqui foi preenchido por suposição.

- Repo: `/home/edgar/Documentos/projetos/forjas/spark-forge-aws`
- SHA: `2230a5d2b42eb94f65fe00110630a7541f72ec03` (`git rev-parse HEAD`, branch `main`, worktree limpo)
- Versão declarada: `0.5.6` (`pyproject.toml:7`, `sparkforge_aws/__init__.py:3`)
- Python requerido: `>=3.10` (`pyproject.toml:12`)
- Data da auditoria: 2026-10-22
- Referência madura comparada: `data-sentinel-forge@92f245f` (installkit com
  `install manifest`, `install env`, `install mcp-verify`, `MANIFEST.sha256` de
  assets, 5 hosts incl. `cursor`, wizard interativo via typer)

---

## 1. Inspeção de arquitetura (§3.1)

### 1.1 Módulos

`sparkforge_aws/` tem ~65 subpacotes (`ls sparkforge_aws/`): `adapters`,
`agentic`, `agents`, `analytics`, `architecture`, `capacity`, `case`, `catalog`,
`change`, `cli`, `cloud`, `codeintel`, `collect`, `context`, `controlm`,
`databases`, `decision`, `delegation`, `diagnosis`, `distribution`, `dq_ai`,
`dqdl`, `economy`, `errors`, `evals`, `facts`, `findings`, `finops`, `iceberg`,
`install`, `integrate`, `journal`, `knowledge_engine`, `lab`, `lakeformation`,
`migration`, `observability`, `orchestration`, `packs`, `platform`, `policy`,
`protocols`, `providers`, `receipt`, `registry`, `reliability`, `reporting`,
`rules`, `scan`, `sdd`, `simulate`, `spark`, `storage`, `streaming`,
`terraform`, `tools`, `tuning`, `ui`, `workflows`, `workload`, `workspace`.

Arquivos vendored (canônico em outro repo — **não editar aqui**):

| Arquivo | Canônico declarado | Evidência |
|---|---|---|
| `sparkforge_aws/_installkit.py` | `the-forge/scripts/installkit/forge_installkit.py` | docstring linha 3-6; `_INSTALLKIT_VERSION = "1.0.0"`, `_SOURCE_SHA256 = "bc189dd2ae0028ce"` (linhas 35-38); sha256 `37250539…` idêntico ao de `sparkforge_azure/_installkit.py` e `data_sentinel/_installkit.py` |
| `sparkforge_aws/_graphview.py`, `_graphstudio.py` | `the-forge/src/theforge` | `pyproject.toml` per-file-ignores linhas 223-224 |
| `sparkforge_aws/ui/**` | `the-forge/src/theforge/ui` | `pyproject.toml:226` |
| `sparkforge_aws/_forge_portal.py`, `_portal_telemetry.py` | `forge-portal/portal_core` | `pyproject.toml:236-238` |
| `vendor/` | terceiros pinados | `vendor/MANIFEST.sha256` existe e pin por hash (único MANIFEST.sha256 do repo — ver §5 GAP-P1-4) |
| `scripts/forge_bootstrap.py`, `scripts/forge_installkit.py` | `the-forge` | sha256 `c9d1d583…` idêntico entre AWS e Azure |

### 1.2 CLI

- Entry points (`pyproject.toml:114-119`): `sparkforge-aws` →
  `sparkforge_aws.adapters.cli:main`; `sparkforge-aws-tools` →
  `sparkforge_aws.tools.cli:main`. Confirmados no wheel em
  `dist-info/entry_points.txt` (ver §4).
- `adapters/cli.py` registra ~68 verbos de topo (`--help` executado):
  `lab, analyze, architecture, migrate, glue, iceberg, release, controlm,
  benchmark, workload, capacity, finops, dq-ai, tune, economy, decision,
  delegate, context, distribution, workspace, agentops, agents, blackboard,
  decisions, budget, autonomy, funcval, sdd, fuse, judge, arbitrate, case,
  next-step, resume, handoff, journal, playbook, runtime, code, graph, pack,
  knowledge, debate, root-cause, lakeformation, rules, validate, report,
  telemetry, receipt, proof, simulate, gain, scan, doctor, integrate, detach,
  ai, install, status, repair, update, uninstall, mcp, portal, policy, change,
  collect`.
- Ciclo de vida do install (`sparkforge_aws/install/cli.py`): verbos de topo
  `install`, `status`, `repair`, `update`, `uninstall` + subverbos
  `install doctor`, `mcp verify`, `mcp serve`. O `doctor` de topo é uma
  superfície separada (saúde do engine/case), distinta de `install doctor`.
- **Ausente**: `install manifest` e `install env` — os dois verbos que o
  data-sentinel-forge expõe (`src/data_sentinel/cli/install.py:252,228`).
  `forge.json`/`forge.agentic.json` não são emitidos por nenhum verbo da CLI.

### 1.3 Installkit e instalação portátil

- `sparkforge_aws/install/lifecycle.py` implementa
  `install/status/doctor/repair/uninstall/update` sobre `_installkit` +
  `integrate/writer.py` (mesma máquina de posse: ledger sha256 em
  `.sparkforge_aws/integrations.json`).
- `sparkforge_aws/install/hosts.py`: 4 hosts (`claude`, `devin`, `codex`,
  `copilot`) com diretórios de projeto `.claude/agents|skills`,
  `.devin/agents|skills` + `.agents/agents|skills` (SHARED_AGENT_HOSTS),
  `.codex/agents` (TOML) + `.agents/skills`, `.github/agents|skills`.
- `sparkforge_aws/integrate/`: caminho `user` — `hosts.py` (tabela declarativa
  com fontes URL por host), `sources.py` (content_root: repo →
  `integrate/bundle/`), `writer.py` (plan/apply/remove com ledger),
  `render.py` (render por plataforma), `claude.py` (marketplace plugin em
  `~/.sparkforge_aws/claude/plugins/sparkforge-aws`), `open_host.py`,
  `conflict.py`.
- Bootstrap de conta: `install.sh`/`install.ps1`/`install.windows.sh` +
  `scripts/forge_bootstrap.py` — cria venv em `~/.forge/installs/<forge>/.venv`,
  shim em `~/.local/bin`, manifesto `forge/InstallationManifest/v1` em
  `~/.forge/installations/spark-forge-aws.json` (observado em disco nesta
  máquina: 7 forges registradas).

### 1.4 Integração com hosts

- Projeto (scope=project/workspace): skills+agents renderizados por plataforma
  para os diretórios acima; `.mcp.json` único com merge de
  `mcpServers.sparkforge-aws` (command = `sys.executable` absoluto +
  `-m sparkforge_aws.adapters.mcp --transport stdio`); bloco gerenciado
  `<!-- sparkforge-aws:managed -->` em `AGENTS.md` (e `CLAUDE.md` se existir).
- `.devin/config.json` do repo declara `read_config_from` e `permissions`
  (allow/ask); `.mcp.json` do repo usa forma plugin (`${CLAUDE_PLUGIN_ROOT}`).
- Config de usuário (scope=user): `~/.config/devin/`, `~/.codex/`, `~/.copilot/`,
  `~/.agents/skills` compartilhado, marketplace Claude em `~/.sparkforge_aws/`.

### 1.5 MCP adapters

- `adapters/mcp.py`: servidor full — 148 tools (`AGENTS.md` linha 144/175
  declara "148 tools, 52 com `detail_level`", recount datado 2026-10-16);
  `--transport stdio|http`, `--mode full|compact`.
- `adapters/mcp_compact.py`: superfície compacta (7 operações, opt-in).
- `mcp verify` = handshake JSON-RPC real (`initialize` +
  `notifications/initialized` + `tools/list` + `tools/call` de
  `sparkforge_aws_runtime_detect`) — evidência em §4.5.
- Extra `mcp` opcional (`pyproject.toml:87-93`): `mcp>=2,<3`, starlette,
  uvicorn, pisos idna/python-dotenv por CVE. Sem o extra o servidor recusa com
  mensagem nomeada (evidência §4.5).

### 1.6 Empacotamento

- `pyproject.toml`: hatchling, `reproducible = true` explícito (linhas 121-145
  documentam os 4 eixos e o que a flag não cobre).
- Wheel `packages = ["sparkforge_aws"]` + `force-include` (linhas 155-171):
  `rules/catalog` → `sparkforge_aws/rules/catalog`, `knowledge` →
  `sparkforge_aws/knowledge`, `skills` → `integrate/bundle/skills`, `agents` →
  `integrate/bundle/agents`, `portal/assets` → `portal_assets`,
  `evals/agentic` → `evals_data/agentic`.
- sdist `include` (linhas 184-196): lista curta; efeito colateral medido em §4.2.

### 1.7 Schemas, manifests, assets

- `contracts/lakehouse-catalog-v1.schema.json`, `platform-graph-v1.schema.json`
  (só no repo — não entram no wheel nem no sdist).
- `sparkforge_aws/findings/schemas/` (4 arquivos) — entra no wheel via pacote.
- `forge.json` (raiz): forge_id/package/distribution/cli/python/
  mcp_server_name/mcp_command/extras/lab — **sem `version` e sem
  `install_command`** (sentinel tem ambos).
- `forge.agentic.json` (raiz): `forge/SpecialistAgenticManifest/v1`,
  **version `"0.5.0"` defasada** vs pacote 0.5.6 — workflows analyze-pyspark /
  doctor / playbook, host_adapters [claude, devin, codex, copilot].
- `manifest.json` (raiz): manifesto plugin-style — `name`, `version` 0.5.6,
  `skills` (61), `tools` (148), `platforms` (4), `knowledge_base`, `mcp`,
  `schemas`, `entry_prompt: PROMPT_INICIAL_MESTRE.md`,
  `plugin: .claude-plugin/plugin.json`, `parity: parity.yaml`. Gerador não
  identificado; `tests/test_docs_coverage.py` o valida.
- `.claude-plugin/plugin.json`: plugin manifest (version 0.5.6).
- Assets: `skills/` 62 dirs (61 skills + `_shared/`), `agents/` 14 coordenadores
  + `executors/` 5, `knowledge/` 114 arquivos, `rules/catalog/` 49 yamls,
  `evals/` (agentic, holdout, mcp-conformance, platform_intelligence, skills,
  token_efficient — 82 arquivos), `templates/` 7, `commands/` 4 (`sf-*`),
  `checklists/` 2, `config/` 7 yamls, `portal/assets/` 46, `fixtures/` (corpus
  golden), `lab/`, `labs/`.

### 1.8 Canônico vs gerado

| Recurso | Canônico | Gerado | Gerador oficial |
|---|---|---|---|
| Skills | `skills/` | `.claude/skills`, `.agents/skills`, `.github/skills` (install) | `scripts/sync_skills.py` (`--check` no CI) |
| Agents | `agents/` + `agents/executors/` | `.claude/agents`, `.agents/agents`, `.github/agents` (sufixo `.agent.md`) | `scripts/sync_skills.py` |
| Rules p/ hosts | — | `.agents/rules/` (4 arquivos com cabeçalho "GENERATED FROM CANONICAL SOURCE") | gerador não identificado (cabeçalho declara geração; fonte = regras de `AGENTS.md`/CLAUDE.md?) |
| Catálogo de regras | `rules/catalog/*.yaml` | — | — |
| Knowledge | `knowledge/` | — | `scripts/refresh_knowledge.py` (refresh) |
| `manifest.json` | ? (ver GAP-P2) | — | não identificado |
| `docs/agentic-catalog.md` etc. | — | gerados | `scripts/gen_*.py` |
| Locks | — | `locks/py*.txt` | `scripts/gen_lock.py` |

Regra de ouro confirmada: `scripts/sync_skills.py` renderiza por plataforma
(não copia byte a byte — Devin perde `tools:`, ganha `subagent:`/`agent:`); o
gate `--check` roda no CI.

### 1.9 Docs de instalação, testes, CI/CD, PyPI

- `docs/installation/`: 12 arquivos (quickstart, portable, account, global,
  uninstall, update-and-repair, troubleshooting, por-host claude/devin/codex).
- Testes de portabilidade: `tests/test_install.py`,
  `tests/test_integrate.py`, `tests/test_installed_provenance.py`,
  `tests/test_verify_wheel.py`, `tests/test_artifact_contents.py`,
  `tests/test_package_importable.py`, `tests/test_portable_distribution.py`
  (~500 `test_*.py` no total).
- `scripts/verify_wheel.py`: gate que constrói sdist+wheel, instala em venv
  limpo, roda goldens sob `SPARKFORGE_AWS_VERIFY_INSTALLED=1`, compara dois
  builds por sha256, e tem `--outdir` (o byte publicado = o byte testado).
- CI: `.github/workflows/ci.yml` (matriz py3.10–3.14, install congelado por
  `locks/py*.txt` com `--require-hashes`, ruff, mirror sync, suite);
  `publish-pypi.yml` (version gate + build + manifesto sha256 + OIDC trusted
  publishing + verificação pós-publish em venv limpo); `refresh-knowledge.yml`;
  `release.yml`.
- PyPI: `sparkforge-aws` publicado — `pip index versions` → `0.5.6` é a
  latest (0.5.0–0.5.6 no índice).

---

## 2. Matriz de recursos (§3.2)

Preenchida só com evidência executada. Legenda: ✅ = evidência direta;
⚠️ = parcial/condição; ❌ = evidência de ausência/falha; `n/a` = não se aplica.

| Recurso | Existe na fonte | Está no wheel | Instalado no alvo | Descoberto pelo host | Utilizável | Verificado |
|---|---|---|---|---|---|---|
| Skills | ✅ 62 dirs (`ls -d skills/*/` → 62; 61 `SKILL.md` + `_shared/`) | ✅ 61 `SKILL.md` em `integrate/bundle/skills/` (`unzip -l`) | ✅ copiadas por host — 62 dirs em `.claude/skills` + `.agents` + `.devin` + `.github` (install log: 1498 arquivos) | ✅ layout nativo por host (`.claude/skills`, `.agents/skills`, `.devin/skills`, `.github/skills`) | ⚠️ `references/`/`scripts/`/`evals/` copiados e resolvem; **mas refs `../../knowledge/*` quebradas** (ver GAP-P0-2) | ⚠️ suites de eval existem (`python -m sparkforge_aws.evals list` → 4 suites) mas nenhum teste prova host carregando a skill |
| Agents | ✅ 14 + 5 executors (`agents/*.md`, `agents/executors/*.md`) | ✅ `integrate/bundle/agents/` (15 paths com executors/) | ✅ `.claude/agents` (+`executors/`), `.agents/agents`, `.devin/agents`, `.github/agents`, `.codex/agents` TOML (executors fora: sem `description`) | ⚠️ `.agents/agents` nativo p/ Devin; `.codex` TOML; `.github` `.agent.md` — depende do host ler | ⚠️ referenciam `AGENT_PROTOCOL.md` ausente (GAP-P0-1) | ⚠️ nenhuma prova de spawn/host |
| MCP | ✅ `adapters/mcp.py` + `mcp_compact.py` | ✅ módulo no pacote | ✅ `.mcp.json` escrito com `command: <python do venv> -m sparkforge_aws.adapters.mcp --transport stdio` | ✅ `.mcp.json` de projeto lido por claude/devin; codex: NOT_APPLICABLE (nota emitida no receipt); copilot: mesmo arquivo | ⚠️ exige extra `[mcp]` — sem ele, recusa nomeada "SDK do MCP nao instalado" (evidência §4.5) | ✅ `mcp verify` = handshake real; doctor reporta UNVERIFIED/FAIL honesto |
| Knowledge | ✅ 114 arquivos (`find knowledge -type f`) | ✅ `sparkforge_aws/knowledge/` (114 entradas no wheel) | ❌ não copiado ao alvo (REFERENCIAR: resolve em site-packages via `knowledge path` → `/tmp/audit_aws/venv/.../sparkforge_aws/knowledge`) | ❌ host não recebe índice/manifesto; skills citam caminhos relativos quebrados | ⚠️ `knowledge path`, `knowledge list`, `rules lookup` funcionam do wheel | ⚠️ acessível via CLI/MCP; não via filesystem do alvo |
| Rules | ✅ `rules/catalog/` 49 yamls + `routing.yaml` | ✅ `sparkforge_aws/rules/catalog/` (50 entradas) | ❌ não copiado ao alvo | ❌ idem knowledge | ✅ `rules lookup --id SF-ENV-001` retorna regra do wheel | ⚠️ via CLI/MCP apenas |
| Evals | ✅ `evals/` 82 arquivos | ⚠️ só `evals/agentic` → `evals_data/agentic` (51); holdout/mcp-conformance/etc. ficam fora do wheel (vazam só no sdist — ver §4.2) | ❌ não instalado | ❌ | ⚠️ `python -m sparkforge_aws.evals list` → 4 suites packaged | ⚠️ suites existem; nenhum eval prova instalação/host |
| Protocols | ✅ `AGENT_PROTOCOL.md` (raiz, 13 962 B) | ❌ fora do wheel e do sdist | ❌ **não instalado** | ❌ | ❌ **quebrado**: 65 arquivos instalados citam `AGENT_PROTOCOL.md` (`grep -rln` em skills+agents do alvo) | ❌ |
| Verificadores | ✅ `scripts/check_*.py`, `verify_wheel.py`, gates CI | ❌ `scripts/` fora do wheel | ❌ | ❌ | ⚠️ parte embutida na CLI (`sdd check`, `validate`, `doctor`) | ⚠️ os de repo não viajam com o pacote |
| Políticas | ✅ `.sparkforge_aws/policy.yaml` (state), `.claude/settings.json` hooks, `policy/` módulo | ⚠️ `sparkforge_aws/policy/` no pacote | ❌ hooks/permissions do repo não vão ao alvo (só marker + .mcp.json + mirrors) | ❌ | ⚠️ `sparkforge-aws policy` existe na CLI | ⚠️ |

Coluna "Descoberto pelo host": hoje nada declara ao host *como* consultar
knowledge/rules/evals — o bloco gerenciado em `AGENTS.md` diz apenas "MCP +
mirrors + ciclo de vida" (`install/lifecycle.py:107-115`). `AGENT_PROTOCOL.md`
(que contém as regras de uso) não viaja.

---

## 3. Análise do instalador (§3.3)

Código: `sparkforge_aws/install/lifecycle.py`, `install/hosts.py`,
`integrate/{hosts,sources,writer,render,claude}.py`, `_installkit.py`.

### Resolução do alvo

`kit.resolve_scope(spec, scope, cwd, root)` (`_installkit.py`):
- `project` → `--root` explícito, senão raiz VCS (`_find_vcs_root`), senão
  `_find_state_root`, senão `FORGE-INSTALL-NOT-A-REPO`.
- `workspace` → `_find_workspace_root` (sobe procurando workspace manifest),
  senão fallback VCS/cwd.
- `user` → `Path.home()` (delega ao `integrate`). `FORGE_HOME_OVERRIDE`
  honrado em `_home()` — testes isolam HOME por ele.

### Scopes (evidência §4.4)

| Escopo | Comando executado | Resultado observado |
|---|---|---|
| project | `install --scope project --root /tmp/audit_aws/proj --yes` | `completed`, 1498 managed_files, `.mcp.json`, `AGENTS.md` marker, `.sparkforge_aws/{integrations.json,receipts/}` |
| workspace | `install --scope workspace --root /tmp/audit_aws/ws --host claude --yes` | `completed`, 371 arquivos + `.sparkforge_aws/workspace-install.json` (`forge/WorkspaceInstall/v1`) |
| user | `install --scope user --host devin --yes --dry-run` (HOME fake) | plano `integrate`: `~/.config/devin/agents/*`, `~/.agents/skills/*`, `~/.config/devin/mcp_config.json` |

### Assets: copiados vs referenciados vs ignorados

- **Copiados** (por host, renderizados): toda a árvore de `skills/` (SKILL.md +
  `references/` + `scripts/` + `evals/`) e `agents/*.md` + `agents/executors/`.
  Renderização por plataforma (`writer.plan_files` → `render.render_*`):
  codex → `.toml`, github → `.agent.md`, devin → `.md` c/ campos `subagent:`.
- **Mesclados**: `.mcp.json` (chave `mcpServers.sparkforge-aws`, outras chaves
  preservadas — `apply_json_config`); `AGENTS.md`/`CLAUDE.md` (bloco
  `<!-- sparkforge-aws:managed -->`, `kit.apply_marker_block`).
- **Referenciados** (ficam no pacote): `knowledge/`, `rules/catalog/`,
  `evals_data/agentic/` — acessados por `knowledge path`, `rules lookup`,
  `python -m sparkforge_aws.evals`.
- **Ignorados** (não vão ao alvo): `AGENT_PROTOCOL.md`,
  `PROMPT_INICIAL_MESTRE.md`, `templates/`, `commands/` (`sf-*`),
  `checklists/`, `config/`, `.agents/rules/`, `contracts/`, `manifest.json`,
  `forge.json`, `forge.agentic.json`, `parity.yaml`.

### Merge e ownership

- Ledger `.sparkforge_aws/integrations.json`: por arquivo
  `{sha256, owners: [hosts], preexistente?}`; configs em `hosts[*].config`
  com `entry_sha256`. Conflito → recusas nomeadas `arquivo_do_usuario` /
  `editado_pelo_usuario` — arquivo alheio nunca é sobrescrito
  (`writer.apply_files`, linhas 535-559).
- Registro global: `~/.forge/installations/spark-forge-aws.json`
  (`forge/InstallationManifest/v1`) via `kit.register_installation`.

### Uninstall / repair / update (evidência §4.4)

- `uninstall --purge`: remove só o que o ledger declara nosso (owner único +
  sha íntegro + não `preexistente`), tira entrada `mcpServers`, remove blocos
  de marker, poda diretórios vazios. Observado: `completed`, 1499 removidos,
  diretório do alvo vazio.
- `repair`: re-renderiza arquivos gerenciados sumidos/modificados e restaura
  entrada MCP do `entry` gravado; arquivo do usuário divergente → `skipped`,
  nunca regravado. Observado: `.claude/skills/analyze-spark-plan/SKILL.md`
  apagado → `repair` → `completed`, `repaired: [o arquivo]`.
- `update`: lê `~/.forge/installations/spark-forge-aws.json`, recusa
  `--to latest`, planeja `<venv>/bin/pip install --upgrade <checkout>`
  (observado em `--dry-run`).

### Host selection e perfis

- `--host {all,claude,devin,codex,copilot}`; código aceita `none` e csv
  (`_hosts_for`, `lifecycle.py:90-104`) mas **argparse rejeita ambos**
  (GAP-P2-1). `codex` não recebe executors (TOML exige `description`).
- `--profile {minimal,recommended,full}`: `_profile_kinds` → minimal=sem
  skills/agents; **recommended e full são idênticos** (ambos `(True,True)`).
- `--gateway-profile {economy,balanced,deep}`: seleciona `--mode compact` no
  comando MCP (`integrate/hosts.py:mcp_command`).
- `--components` csv (`skills,agents,mcp,tui,graph-studio`) →
  `kit.component_options`; observado `--components skills` →
  `asset_kinds: [config, marker, state, skill]`.
- Wizard TUI: `sparkforge-aws install` sem args em TTY →
  `ui/wizard.run_wizard` (install/cli.py:33-43).

---

## 4. Diagnóstico PyPI (§3.4)

### 4.1 Build local

```
cd spark-forge-aws && .venv/bin/python -m build --outdir /tmp/audit_aws/dist .
→ hatchling==1.32.4 (isolated), Successfully built
  sparkforge_aws-0.5.6.tar.gz + sparkforge_aws-0.5.6-py3-none-any.whl
```

### 4.2 Conteúdo real

**Wheel** (`unzip -l`, 1113 arquivos, 12 291 243 B):
`integrate/bundle` 371 · `rules/catalog` 50 · `knowledge/` 114 ·
`portal_assets` 46 · `evals_data` 51 · `_installkit.py`, `_graphview.py`,
`_graphstudio.py`, `_forge_portal.py`, `ui/kit`, `findings/schemas/` 4,
`codeintel/domain_terms.yaml` — todos presentes.

**Ausentes do wheel**: `forge.json`, `forge.agentic.json`, `manifest.json`,
`AGENTS.md`, `CLAUDE.md`, `AGENT_PROTOCOL.md`, `.mcp.json`, `templates/`,
`commands/`, `checklists/`, `config/`, `parity.yaml`, `tests/`, `install.*`,
`scripts/` (0 ocorrências cada no `unzip -l`).

**Sdist** (`tar -tf`, 2060 arquivos — `python -m build` constrói o wheel a
partir dele): a lista `include` usa padrões sem barra (`skills`, `agents`,
`evals/agentic`, `portal`) que casam em **qualquer profundidade** — entram
`.claude/{agents,skills}`, `.agents/{agents,skills}`, `.codex/agents`,
`.github/agents`, `.devin`, `.caveman`, `docs/`, `scripts/` (200), `vendor/`,
`lab/`, `labs/`, `payloads/`, `fixtures/` (2), `evals/{holdout,skills,README.md}`.
E **não entram** `forge.json`, `forge.agentic.json`, `manifest.json`,
`AGENTS.md`, `CLAUDE.md`, `AGENT_PROTOCOL.md`, `.mcp.json`, `templates/`,
`commands/`, `checklists/`, `config/`, `parity.yaml`, `tests/` (verificados por
`grep` na listagem — 0 ocorrências). Efeito: sdist de 4.7 MB com conteúdo
gerado duplicado e sem os manifests/agent-docs do topo (GAP-P1-2, P2-2).

### 4.3 Venv limpo + install fora do checkout

```
python3 -m venv /tmp/audit_aws/venv
venv/bin/pip install /tmp/audit_aws/dist/sparkforge_aws-0.5.6-py3-none-any.whl
cd /tmp/audit_aws/proj            # fora do checkout; pacote só em site-packages
venv/bin/sparkforge-aws --version → sparkforge-aws 0.5.6
venv/bin/sparkforge-aws install --scope project --root . --yes
  → status "completed", checks files=PASS "1498 written, 0 removed",
    refusals=PASS, nota codex NOT_APPLICABLE, verification PASS
```

`content_root()` resolveu `integrate/bundle/` dentro do wheel (repo-root não
existe em site-packages — `sources.py:31-42`).

### 4.4 Descoberta e ciclo de vida (tudo do venv, fora do checkout)

| Verificação | Resultado |
|---|---|
| `status --root proj` | `healthy`, 1499 ledger entries, drift 1500 ok / 0 modified / 0 missing |
| `install doctor` | `healthy`; `mcp-handshake UNVERIFIED` (extra ausente — honesto) |
| `mcp verify` | `FAIL` com recusa nomeada: "SDK do MCP nao instalado. Rode `pip install 'sparkforge-aws[mcp]'`" |
| `rules lookup --id SF-ENV-001` | retorna a regra (total_count 1) |
| `knowledge path` | `root: /tmp/audit_aws/venv/.../sparkforge_aws/knowledge`, 114 arquivos listados |
| `playbook spark-performance-architect` | decomposição completa (rule_areas, skills, executors) |
| `delegate discover` | `PeerDiscoveryReport/v1` — data-sentinel-forge NOT_INSTALLED, 8 declared_capabilities |
| `python -m sparkforge_aws.evals list` | 4 suites: debate, fase0, recovery, sdd |
| `repair` (após `rm` de um SKILL.md) | `completed`, repaired=[arquivo] |
| `uninstall --purge` | `completed`, 1499 removidos, alvo vazio |
| `update --dry-run` | lê `~/.forge/installations/…json`, planeja `pip install --upgrade <checkout>` |
| `install --components skills --dry-run` | `planned`, asset_kinds `[config, marker, state, skill]` |

### 4.5 MCP com e sem extra

Sem `[mcp]`: `mcp verify` FAIL honesto (acima). A entrada `.mcp.json` escrita
usa o `sys.executable` do venv (`/tmp/audit_aws/venv/bin/python3`) — caminho
absoluto e correto; mas o servidor só sobe com o extra instalado.

### 4.6 Comparação com PyPI publicado

```
pip download sparkforge-aws==0.5.6 --no-deps
sha256 wheel local   = 0128a4e2d93ae87757ff7c01234895691c82ce3ae8fa1caa25e1e5c3f5cdb0e8
sha256 wheel PyPI    = 0128a4e2d93ae87757ff7c01234895691c82ce3ae8fa1caa25e1e5c3f5cdb0e8  ← idêntico
sha256 sdist local   = 2446c610980d7eb6b4779c902678a4da9095bcc9832e003637375ae82367ddca
sha256 sdist PyPI    = 2446c610980d7eb6b4779c902678a4da9095bcc9832e003637375ae82367ddca  ← idêntico
```

Build reproduzível bit a bit entre a máquina local e a do publisher — o wheel
local **é** o artefato publicado; as conclusões desta auditoria valem para o
PyPI sem ressalva.

---

## 5. Gaps P0 / P1 / P2

### P0 — bloqueia o objetivo do install 2.0

**GAP-P0-1 — `AGENT_PROTOCOL.md` não viaja: referência morta em 65 arquivos
instalados.**
Causa-raiz: o instalador só copia `skills/` + `agents/` + `.mcp.json` +
markers; o protocolo operacional (regras duras do case — `next_step`,
`rules_lookup`, `validate_output`, executor-tracking, `unresolved`) existe só
na raiz do repo e fora do wheel/sdist. `grep -rln AGENT_PROTOCOL` no alvo
instalado → 65 SKILL.md/agents citam um arquivo que não existe ali (item 7 do
§1 do prompt, literalmente).
Risco: host instalado segue skills que mandam ler um documento inalcançável —
as regras de evidência e de ciclo de vida ficam fora do contexto.
Decisão proposta: materializar protocolo mínimo no alvo (COPIAR versão
compacta em `.sparkforge_aws/` ou embutir bloco gerenciado) + referenciá-la do
manifesto de capacidades; ou publicar `AGENT_PROTOCOL.md` dentro do pacote e
resolver via CLI (`sparkforge-aws protocol show`).
Migração: definir `forge/AgentProtocol/v1` (resumo executável vs documento
longo); manter `AGENT_PROTOCOL.md` canônico no repo como fonte do resumo.

**GAP-P0-2 — `../../knowledge/*` quebrados: 130 referências em 51 SKILL.md.**
Causa-raiz: SKILL.md usa caminhos relativos ao checkout
(`../../knowledge/spark/plan-reading.md`); `knowledge/` não é copiada ao alvo
(fica no pacote, acessível por `knowledge path`/MCP `knowledge_path`).
`grep -rhn "../../knowledge/"` nos mirrors instalados → 130; `ls knowledge` no
alvo → inexistente. É o item 9 do §1 do prompt.
Risco: host tenta abrir caminho inexistente → conhecimento não recuperado;
instrução certa existe (AGENT_PROTOCOL regra 4 manda usar `knowledge_path`),
mas não viaja (GAP-P0-1).
Decisão proposta: reescrever refs no render da skill (`render.render_skill_file`
já transforma por plataforma — trocar `../../knowledge/x` por instrução de
verb `knowledge path --file x` / MCP `knowledge_path`), e/ou materializar
índice `knowledge/` enxuto (INDEX.md + offline-manifest) no alvo.
Migração: alterar render + regen de mirrors + gate `sync_skills --check`;
cobrir com teste de instalação que resolve toda ref dos mirrors.

### P1 — brecha significativa vs contrato install 2.0

**GAP-P1-1 — sem `install manifest`/`install env`.**
O data-sentinel expõe `install manifest` (emite forge.json, `--agentic` emite
`forge/SpecialistAgenticManifest/v1`) e `install env` (runtime, hosts
detectados, registry). AWS não tem equivalente — `install` só tem `doctor`
como subverbo; `forge.json`/`forge.agentic.json` nem são emitidos nem
empacotados. Consequência: instalado via PyPI, nenhum verbo publica o
manifesto de capacidades — descoberta por forge-cli/the-forge depende do repo.
Decisão: adicionar `install manifest [--agentic]` emitindo os dois docs
(fonte: `forge.json` da raiz como canônico, version lida do pacote).

**GAP-P1-2 — `forge.json`/`forge.agentic.json`/`manifest.json` fora de wheel
e sdist + versões defasadas.**
`forge.agentic.json` diz `"version": "0.5.0"` (pacote 0.5.6); `forge.json` não
tem `version` nem `install_command` (o sentinel tem ambos). Nenhum dos três
entra nos artefatos. Decisão: shippar `forge*.json` no pacote
(`sparkforge_aws/` ou `_data/`), gerar `version` dinamicamente, alinhar schema
com o do sentinel (`install_command`).

**GAP-P1-3 — manifesto de capabilities para hosts não existe.**
O bloco gerenciado em `AGENTS.md` diz "MCP + mirrors + ciclo de vida" mas não
aponta para: catálogo de regras, knowledge, protocolos, evals, verificadores,
políticas, rotas (`routing.yaml`), economia. É exatamente a lista de recursos
"não descobertos" do §1. Decisão: emitir `forge/ForgeContext/v1` (ou usar o
manifesto do Cycle 2) declarando onde cada classe de recurso resolve
(copiado vs referenciado vs verb).

**GAP-P1-4 — sem `MANIFEST.sha256` de assets instaláveis.**
`vendor/MANIFEST.sha256` existe (código vendored), mas o conjunto
skills/agents/markers que o install escreve não tem manifesto de integridade
empacotado — o ledger `.sparkforge_aws/integrations.json` nasce no install e
prova drift pós-escrita, não integridade do payload do wheel. Sentinel tem
`installation/assets/MANIFEST.sha256`. Decisão: gerar manifesto sha256 do
bundle no build e verificá-lo no `install doctor`.

**GAP-P1-5 — cópia indiscriminada: ~1 498 arquivos por install de projeto.**
Cada projeto recebe a árvore inteira de 61 skills × até 4 hosts (evidência:
receipt "1498 written"). §2.3 do prompt pede COPIAR só o selecionado pelo
perfil + entradas de descoberta; `--profile` hoje só liga/desliga classes
(minimal vs recommended≡full). Risco: custo de disco/diff e revisão por
projeto. Decisão: perfil seleciona conjunto de skills (manifesto declara o
subconjunto); skills ficam referenciáveis via `pack`/bundle on-demand.

### P2 — melhorias e inconsistências

- **GAP-P2-1**: `--host none` e csv (`claude,devin`) aceitos pelo código
  (`_hosts_for`) mas rejeitados pelo argparse — incluir `none` nas choices ou
  remover o código morto.
- **GAP-P2-2**: sdist carrega mirrors gerados (`.claude`, `.agents`, `.codex`,
  `.devin`, `.github`) + `docs/`, `scripts/`, `vendor/`, `lab*/`, `payloads/`
  por casamento de padrão em profundidade — 4.7 MB com conteúdo duplicado;
  `evals/{holdout,skills}` também vazam. Apertar `include` para caminhos com
  barra (`skills/`, `agents/`).
- **GAP-P2-3**: `recommended` ≡ `full` em `_profile_kinds` — sem distinção.
- **GAP-P2-4**: bloco marker não aponta `sparkforge-aws status|doctor|repair`
  nem os verbs de consulta (knowledge/rules/protocol).
- **GAP-P2-5**: `update` confia no manifesto `~/.forge` — nesta máquina o
  registro diz `version 0.5.6` mas o venv instalado reporta `0.5.0`
  (drift sem gate de verificação de versão).
- **GAP-P2-6**: `manifest.json` da raiz não tem gerador identificado e não
  viaja nos artefatos; `parity.yaml` e `config/` idem (fora do sdist).
- **GAP-P2-7**: `.mcp.json` do repo usa `python` + `${CLAUDE_PLUGIN_ROOT}`
  (forma plugin) enquanto o install escreve `sys.executable` absoluto — duas
  formas convivem; documentar qual vale em qual contexto.
- **GAP-P2-8**: codex MCP em escopo de projeto é NOT_APPLICABLE documentado
  (receipt informa), mas não há caminho alternativo oferecido além de
  `--scope user`.

---

## 6. Riscos, compatibilidades, decisões, plano de migração

### Compatibilidades confirmadas

- Wheel e sdist locais **bit-idênticos** ao PyPI 0.5.6 — sem deriva publicada.
- `install`/`status`/`repair`/`uninstall`/`update` funcionam do wheel puro,
  fora do checkout, com ledger sha256 e recusas nomeadas.
- `rules lookup`, `knowledge path`, `playbook`, `evals list`,
  `delegate discover` resolvem dentro do pacote (REFERENCIAR ok).
- Installkit é **byte-idêntico** entre AWS, Azure e data-sentinel
  (`sha256 37250539…`) — contrato `forge/*` compartilhado já existe.
- Recusa honesta sem extra `mcp`; codex documenta limitação de MCP em projeto.

### Riscos

- Skills instaladas citam documentos inalcançáveis (P0-1/P0-2) → degradação
  silenciosa de qualidade de resposta do host.
- Sdist inclui espelhos gerados → versões duplicadas podem divergir da fonte
  dentro do próprio artefato.
- Cópia de ~1 500 arquivos por projeto → custo de revisão e de `.gitignore`
  do usuário.
- Sem `install manifest`, o registry compartilhado depende do repo —
  quebra a independência PyPI-first do §8 do prompt.

### Decisões propostas (resumo)

1. Publicar `AGENT_PROTOCOL.md` (ou resumo executável `forge/AgentProtocol/v1`)
   no pacote e materializá-lo/referenciá-lo no install.
2. Renderizar refs `../../knowledge/*` para o verb `knowledge path` no espelho
   instalado; incluir `knowledge/INDEX.md` mínimo quando perfil o pedir.
3. Adicionar `install manifest [--agentic]` e `install env` alinhados ao
   sentinel; shippar `forge*.json` no pacote com `version` dinâmica.
4. Emitir manifesto de capabilities descobrível (Cycle 2) + `MANIFEST.sha256`
   de assets; verificar no `doctor`.
5. Perfis com subconjunto real de skills; `--host none`/csv na CLI.
6. Apertar `sdist.include` para barras (`skills/`, `agents/`), e decidir se
   `tests/`+manifestos de topo devem entrar no sdist.

### Plano de migração sugerido

- **Passo 0** (este ciclo): baselines (este doc + irmãos) — sem código.
- **Passo 1**: P0-1/P0-2 — protocolo + refs de knowledge (mudança em render +
  install; gate `sync_skills --check` + teste de resolução de refs no alvo).
- **Passo 2**: P1-1/P1-2 — `install manifest`/`env` + ship dos manifests com
  version dinâmica (alinhamento com o contrato do sentinel e `forge/` schemas).
- **Passo 3**: P1-3/P1-4 — manifesto de capabilities + `MANIFEST.sha256` +
  `doctor` que verifica integridade do bundle.
- **Passo 4**: P1-5 + P2 — perfis seletivos, CLI de hosts, sdist enxuto.
- Cada passo com gate: `pytest tests/test_install*.py`,
  `test_artifact_contents.py`, `verify_wheel.py`, e um novo teste e2e que
  instala do wheel e resolve refs (sem `pip install -e .` como prova).

---

## 7. Apêndice — comandos executados (seleção)

```bash
git rev-parse HEAD                       # 2230a5d…
.venv/bin/python -m build --outdir /tmp/audit_aws/dist .
unzip -l /tmp/audit_aws/dist/sparkforge_aws-0.5.6-py3-none-any.whl
tar -tf  /tmp/audit_aws/dist/sparkforge_aws-0.5.6.tar.gz
python3 -m venv /tmp/audit_aws/venv
/tmp/audit_aws/venv/bin/pip install /tmp/audit_aws/dist/*.whl
cd /tmp/audit_aws/proj && sparkforge-aws install --scope project --root . --yes
sparkforge-aws status|install doctor|mcp verify|repair|uninstall --purge
sparkforge-aws rules lookup --id SF-ENV-001
sparkforge-aws knowledge path
sparkforge-aws playbook spark-performance-architect --repo .
sparkforge-aws delegate discover
python -m sparkforge_aws.evals list
pip download sparkforge-aws==0.5.6 --no-deps [-d pypi_dl]   # sha256 idêntico
pip index versions sparkforge-aws                          # latest 0.5.6
sha256sum sparkforge_aws/_installkit.py                    # 37250539… (= Azure = sentinel)
```
