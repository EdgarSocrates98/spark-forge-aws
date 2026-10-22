# FORGE_CONTEXT_FINAL_HOMOLOGATION — spark-forge-aws

Relatório final do programa Install 2.0 (spec-fonte
`prompt_evo_install2.0.md` §12.6), cobrindo os ciclos 2–7 executados sobre a
baseline `docs/audits/FORGE_CONTEXT_BASELINE.md` (ciclo 1, lf-0034).
Documento de evidência: cada afirmação cita commit/PR, arquivo:linha ou
comando executado. O que não foi executado está marcado **NÃO EXECUTADO**
(§16 — nenhum teste não executado é reportado como sucesso).

- **Repo:** `/home/edgar/Documentos/projetos/forjas/spark-forge-aws`
- **SHA antes:** `2230a5d2b42eb94f65fe00110630a7541f72ec03` (tag `v0.5.6`,
  2026-10-21 — mesma HEAD auditada no baseline)
- **SHA depois:** `5aab9cf3552d3f41a57913f47d89662cfaff961c` (HEAD de `main`)
- **Versão:** `sparkforge-aws` 0.5.6 → **0.6.0** (`pyproject.toml` bumpado em
  worktree, **pendente de publicação** — §10)
- **Python:** `>=3.10`
- **Data:** 2026-10-22

---

## 1. SHAs antes/depois

| | SHA | Descrição |
|---|---|---|
| Tag base / baseline | `2230a5d2b42eb94f65fe00110630a7541f72ec03` | `release: 0.5.6 — governed peer delegation + delegate-specialists skill` |
| HEAD final | `5aab9cf3552d3f41a57913f47d89662cfaff961c` | `fix(install): installkit 1.0.1 — stale-lock created_at + backport bootstrap fixes (userinfo regex, argv trim, smoke vazio) (#197)` |

Range medido: `git log v0.5.6..HEAD` → **20 commits**, `git diff --stat` →
**49 arquivos, +7.720/−315 linhas**.

## 2. PRs

Todos os PRs mergeados em `EdgarSocrates98/spark-forge-aws`, verdes no CI
no momento do merge.

| PR | Merge / squash | Conteúdo |
|---|---|---|
| #185 | `3eefc03` (merge), `86786ea` | docs(audit): FORGE_CONTEXT_BASELINE (lf-0034) |
| #186 | `d655720` (merge), `9e8efa9` | feat(context): `forge/context/v1` — vendored registry + install wiring (ciclo 2) |
| #187 | `b3b695a` (merge), `c3edf5c` | feat(context): consumer-docs layer — blocos `forge:*` + AGENT_PROTOCOL.md consolidado (ciclo 3, lf-0036) |
| #188 | `7355771` (merge), `f80f215` | test(gate): isenta `_forgecontext` + install wiring do raw-glob scan |
| #189 | `1e0fc1d` (merge), `c9571c3` `d8cc6aa` `14ce44d` | feat(install): wheel distribution parity — `forge*.json` empacotados (lf-0039 §8); discovery lf-0037 (ops §6.2 + knowledge/rules/context-pack + dead-ref remediation); fix §8.2 leitor `_PKG_DIR` |
| #190 | `68ee9af` (squash) | fix(lint): PLW1510/RUF100/ISC004/F401 no wheel test + drop `manifest_json` dead code |
| #191 | `c57425f` (squash) | feat(evals): ciclo 5 — evals taxonomy + §7.2 ops + §7.3 sealing (lf-0038) |
| #192 | `5b2b7cd` (squash) | fix(installkit): `_forgecontext` v1.2.1 — `timezone.utc` p/ Python 3.10 |
| #193 | `f960898` (squash) | fix(evals): runtime→avaliacao via importlib (harness boundary) |
| #194 | `edfefa0` (squash) | fix(lint): ordem isort no bloco importlib (`_core.capabilities`) |
| #196 | `a56d0eb` (squash) | fix(ci): contract convergence — skills, MCP parity, portal, claims |
| #195 | `23cdf52` (squash) | feat(install): transactional context registry — vendored `_forgecontext` v1.3.0 (lf-0040, ciclo 7) |
| #197 | `5aab9cf` (squash) | fix(install): installkit 1.0.1 — stale-lock `created_at` + backports do bootstrap |

## 3. Commits

20 commits no range (`git log v0.5.6..HEAD --format='%h %s'`, ordem cronológica):

```text
86786ea docs(audit): FORGE_CONTEXT_BASELINE — Install 2.0 cycle 1 (lf-0034)
3eefc03 Merge pull request #185 (audit/install-context)
9e8efa9 feat(context): forge/context/v1 — vendored registry + install wiring (ciclo 2)
d655720 Merge pull request #186 (cycle/install-context)
c3edf5c feat(context): consumer-docs layer — blocos forge:* + AGENT_PROTOCOL.md consolidado (lf-0036)
b3b695a Merge pull request #187 (cycle/install-context-docs)
f80f215 test(gate): exempt _forgecontext + install wiring from raw-glob scan
7355771 Merge pull request #188 (fix/glob-gate-exemptions)
c9571c3 feat(install): wheel distribution parity — forge manifests packaged (lf-0039 §8)
d8cc6aa discovery: lf-0037 install-time knowledge/rules/context-pack retrieval + dead-ref remediation
14ce44d fix(install): manifest reader resolve _PKG_DIR packaged manifests sob wheel (lf-0039 §8.2)
1e0fc1d Merge pull request #189 (cycle/install-context)
68ee9af fix(lint): PLW1510/RUF100/ISC004/F401 no wheel test + drop manifest_json dead code (#190)
c57425f feat(evals): install-2.0 ciclo 5 — evals taxonomy + §7.2 ops + §7.3 sealing (lf-0038) (#191)
5b2b7cd fix(installkit): _forgecontext v1.2.1 — timezone.utc p/ Python 3.10 (#192)
f960898 fix(evals): runtime->avaliacao via importlib (harness boundary) (#193)
edfefa0 fix(lint): ordem isort no bloco importlib (_core.capabilities) (#194)
a56d0eb fix(ci): contract convergence — skills, MCP parity, portal, claims (#196)
23cdf52 feat(install): transactional context registry — vendored _forgecontext v1.3.0 (lf-0040) (#195)
5aab9cf fix(install): installkit 1.0.1 — stale-lock created_at + backport bootstrap fixes (userinfo regex, argv trim, smoke vazio) (#197)
```

## 4. Arquivos modificados

`git diff --name-only v0.5.6..HEAD` → 49 arquivos. Agrupados:

| Grupo | Arquivos |
|---|---|
| Vendored | `sparkforge_aws/_forgecontext.py` (novo, v1.3.1, `_SOURCE_SHA256 = "e72e93eab21ade74"`), `sparkforge_aws/_installkit.py` (v1.0.1, `4c446922f5e77a0c`), `scripts/forge_installkit.py`, `scripts/forge_bootstrap.py` (v1.1.1) |
| Wiring de produção | `sparkforge_aws/install/lifecycle.py` (`install_transaction`/`uninstall_transaction` em `:1274`/`:1307`, `_context_manifest`, `_PKG_DIR` reader), `sparkforge_aws/install/hosts.py`, `sparkforge_aws/discovery_ops.py` (novo — fonte única do mapa §6.2), `sparkforge_aws/adapters/{cli,_core,mcp,tools}.py` (verbos `capabilities`, `context pack`, `knowledge search --domain`, `rules lookup --query`, `evals`), `sparkforge_aws/integrate/{__init__,render,writer}.py` (rewrite de refs + pointer stubs), `sparkforge_aws/evals/{surface,taxonomy}.py`, `sparkforge_aws/portal_adapter.py` |
| Empacotamento | `pyproject.toml` (force-include `forge.json`/`forge.agentic.json` → `sparkforge_aws/forge/`) |
| Docs | `docs/audits/FORGE_CONTEXT_BASELINE.md`, `docs/install/DISTRIBUTION_PARITY.md`, `docs/evals-taxonomy.md`, `docs/guia/referencia/cli/{capabilities,context,evals,knowledge,rules,README}.md`, `docs/guia/referencia/tools/*`, `docs/claims.lock.json`, `docs/surface.lock.json`, `docs/harness/*`, `docs/vnext/adrs/ADR-010-*` |
| Testes | `tests/test_install.py` (53 testes), `tests/test_wheel_isolation.py`, `tests/test_evals_surface.py` (21), `tests/test_discovery_ops.py` (28), `tests/test_integrate.py`, `tests/test_sync_render.py`, `tests/test_facts_scan.py`, `tests/test_installed_provenance.py`, `tests/test_capability_parity.py`, `tests/test_{adapters_detail_level,adapters_freshness,codeintel_security,fixtures_golden_mcp_parity,skill_content}.py` |

## 5. Gaps corrigidos

Mapeamento gap do baseline (§5) → correção entregue:

| Gap baseline | Status | Evidência |
|---|---|---|
| **GAP-P0-1** — `AGENT_PROTOCOL.md` não viaja (referência morta em 65 arquivos instalados) | **CORRIGIDO** | consumer-docs do `_forgecontext.py` grava `AGENT_PROTOCOL.md` consolidado na raiz do alvo (`install/lifecycle.py:109` `_CONSUMER_DOCS`); commit `c3edf5c` |
| **GAP-P0-2** — `../../knowledge/*` quebrados (130 refs em 51 SKILL.md) | **CORRIGIDO** | `integrate/render.py:666+` rewrite depth-aware + `integrate/writer.py` pointer stubs (`knowledge path --file` com proveniência sha256); commit `d8cc6aa` |
| **GAP-P1-2** — `forge.json`/`forge.agentic.json`/`manifest.json` fora de wheel e sdist | **CORRIGIDO** | `pyproject.toml:181-182` force-include → `sparkforge_aws/forge/`; leitor `_PKG_DIR`-aware (`lifecycle.py:1038-1045`); commits `c9571c3`, `14ce44d` |
| **GAP-P1-3** — manifesto de capabilities para hosts inexistente | **CORRIGIDO** | `forge/context/v1` (`.forge/context/capabilities/sparkforge-aws.json`) + registry + `ROUTING.md`; verbo `capabilities`; commits `9e8efa9`, `d8cc6aa` |
| **GAP-P1-1** — sem `install manifest`/`install env` | **PARCIAL** | o manifesto de capacidades agora é emitido pelo install (`forge/context/v1`) e consultável via `capabilities` — os subverbos literais `install manifest`/`install env` continuam inexistentes em `install/cli.py` |
| **GAP-P1-4** — sem `MANIFEST.sha256` de assets instaláveis | **PARCIAL** | o contrato `forge/context/v1` agora suporta `integrity.files` sha256 (schema validado em `_forgecontext.py:863-877`) e o ledger sha256 por arquivo segue cobrindo drift pós-escrita; um `MANIFEST.sha256` dedicado do bundle canônico não foi emitido |
| — install/transação multi-forge (ciclo 7) | **CORRIGIDO** | `install_transaction`/`uninstall_transaction` wired (`lifecycle.py:1274`,`:1307`); `_forgecontext` v1.3.1; commit `23cdf52` |
| — evals sem classificação §7 | **CORRIGIDO** | `evals/taxonomy.py` + `evals/surface.py` + `evals list|describe|run|result` + `eval_suites[].kind` no manifesto; commits `c57425f`, `f960898` |
| — `_forgecontext` incompatível com py3.10 (`timezone.utc`) | **CORRIGIDO** | v1.2.1; commit `5b2b7cd` |
| — installkit 1.0.0 → staleness cego com PID indecidível; bootstrap com regex de userinfo vazando, argv não-trimmado, smoke vazio=PASS | **CORRIGIDO** | `_installkit.py` v1.0.1 + `forge_bootstrap.py` v1.1.1 byte-idênticos ao canônico; commit `5aab9cf` |

## 6. Gaps restantes

- **E2E real de hosts (§10.2) — NÃO EXECUTADO** (ciclo 8 pendente; ver §9).
- **Economia/observabilidade (ciclo 9, §11) — pendente.**
- **Publicação PyPI — pendente** (§10).
- **GAP-P1-1** (subverbos literais) e **GAP-P1-4** (`MANIFEST.sha256`
  dedicado) — parciais, ver §5.
- **GAP-P1-5 — cópia indiscriminada (~1.498 arquivos por install)** segue
  aberta: `_profile_kinds` (`lifecycle.py:61-67`) continua ligando classes
  inteiras (skills?/agents?), sem subconjunto de skills por perfil.
- **GAP-P2-1/P2-2/P2-3** — `--host none`/csv, sdist com mirrors gerados,
  `recommended`≡`full` — não tocados no range.
- **GAP-P2-4** — bloco marker agora é o bloco `forge:<id>` gerenciado com
  descoberta real (ciclo 3), mas o apontamento específico de
  `status|doctor|repair` no marker segue ausente — os verbos estão no
  AGENT_PROTOCOL consolidado e no manifesto.
- **GAP-P2-5/P2-6/P2-7/P2-8** — drift do registry de conta, `manifest.json`
  sem gerador, `.mcp.json` plugin-form vs absoluto, codex MCP em projeto —
  não tocados.
- **`DISTRIBUTION_PARITY.md`** descreve a lacuna do leitor pré-§8.2 como
  "tracked" — o §8.2 (`14ce44d`) corrigiu; o doc registra o histórico.

## 7. Testes executados

| Suíte | Arquivo | Contagem | Resultado |
|---|---|---|---|
| install lifecycle + context | `tests/test_install.py` | 53 | verde |
| wheel isolation (lf-0039) | `tests/test_wheel_isolation.py` | 1 (e2e) | verde |
| evals §7 surface | `tests/test_evals_surface.py` | 21 | verde |
| discovery ops §6.2 | `tests/test_discovery_ops.py` | 28 | verde |
| integrate/render sync | `tests/test_integrate.py` + `test_sync_render.py` | — | verde |
| verify wheel / packaging | `tests/test_verify_wheel.py` | 46 | verde |
| demais gates do repo | `test_facts_scan.py`, `test_installed_provenance.py`, `test_capability_parity.py`, gates de skill/adapters | — | verde |

Cross-forge (rodado em the-forge, cobrindo esta wheel):
**120/120** permutações de ordem de instalação (`test_multi_forge_e2e.py`,
marker `slow`) e `vendor.py --check` **CLEAN**.

## 8. Resultados

- `sparkforge_aws/_forgecontext.py` **byte-idêntico** ao canônico e às 4
  outras forjas (sha256 `390f5e0e61ab80dc…`, `_SOURCE_SHA256 =
  "e72e93eab21ade74"`, v1.3.1).
- Install escreve `.forge/context/{registry.json, capabilities/
  sparkforge-aws.json, ROUTING.md}` + consumer-docs (`forge:sparkforge-aws`
  blocks + `AGENT_PROTOCOL.md` consolidado) sob um único lock
  transacional; uninstall remove só o próprio.
- `discovery_ops.py` é fonte única do mapa §6.2 → verbos reais
  (`capabilities`, `knowledge search --domain`, `rules lookup --query`,
  `context pack`, `doctor`); `eval_commands()` cobre §7.2.
- `domains` publicados: `pyspark, aws-glue, amazon-emr, amazon-athena,
  apache-iceberg, spark-streaming, terraform, data-quality`
  (`lifecycle.py:1003-1012`); `DOMAIN_PREFIXES` traduz para prefixos
  nativos de regra/knowledge.
- Evals classificados nas 4 categorias §7.1 com suítes seladas §7.3 —
  `docs/evals-taxonomy.md` + `evals describe`.
- `forge.json`/`forge.agentic.json` empacotados em `sparkforge_aws/forge/`
  — manifesto lê do pacote sob wheel (§8.2).

## 9. Evidências Devin/Claude/Codex

**NÃO EXECUTADO.** A prova E2E real por host (§10.2 — Devin CLI com job
PySpark/Glue, Claude, Codex, Copilot) pertence ao ciclo 8, pendente. Os
artefatos instalados foram verificados por testes de integração e
isolation de wheel — não por telemetria de host.

## 10. Matriz PyPI

| Componente | Estado |
|---|---|
| Wheel local (HEAD) | construída e testada em venv limpa fora do checkout (`tests/test_wheel_isolation.py`); usada na matriz 5! do the-forge |
| `forge.json`/`forge.agentic.json` no wheel | presentes em `sparkforge_aws/forge/` (force-include `pyproject.toml:181-182`) |
| Manifestos/skills/agents/knowledge/rules/evals_data | empacotados (ver `docs/install/DISTRIBUTION_PARITY.md`) |
| Publicação no índice | **PENDENTE DE PUBLICAÇÃO** — worktree marca `0.6.0`; PyPI ainda serve `0.5.6` |
| PyPI 0.5.6 publicado | bit-idêntico ao wheel 0.5.6 local (baseline §6) |

## 11. Compatibilidade

- Contratos `forge/*` v1 estáveis; `forge/context/v1` +
  `forge/context-registry/v1` adicionados sem tocar
  `forge/InstallationManifest/v1` (registry de conta, do bootstrap).
- Engine vendored roda em py3.10 (`_forgecontext` v1.2.1, #192) — o piso
  desta forja.
- Rollback: uninstall transacional só remove o próprio manifesto/entry/
  blocks; as outras forjas preservadas (prova na matriz 5!).

## 12. Segurança

Herdada do motor vendored + wiring local:

- `_txn_restore` com validação de path (`..`, absoluto, `\`, drive;
  blob `^\d{1,8}$`) — `_forgecontext.py:2495-2531`.
- KeyboardInterrupt/SystemExit propagam bare após rollback (`:2670+`).
- `forge_bootstrap.py` 1.1.1: `_URL_USERINFO_RE` `[^/\s]+@` (userinfo com
  `@` interno não vaza), argv trim, smoke vazio≠PASS.
- installkit 1.0.1: stale-lock `created_at` fallback para PID indecidível.
- Gate de raw-glob isenta explicitamente o vendored + wiring
  (`f80f215`); boundaries de harness respeitadas (`f960898`, `edfefa0`).
- Ownership `FORGE-CONTEXT-OWNERSHIP`; markers ambíguos recusam
  `FORGE-CONTEXT-CONFLICT`; conteúdo de usuário byte-preservado.

## 13. Performance

- Reinstall inalterado = zero writes (registry determinístico — prova na
  matriz 5!, `test_multi_forge_e2e.py:412+`).
- `discovery_ops` é tabela em memória (fonte única, sem re-leitura).
- Sem claims quantitativos — ciclo 9 (§11) não executado.

## 14. Recomendações

1. Ciclo 8 (§10.2) — prova real Devin/Claude/Codex sobre um job Glue com
   esta wheel instalada; sem ela o aceite §16 sobre hosts fica aberto.
2. Publicar `0.6.0` (§12.5) ou marcar release bloqueada — nunca simular.
3. Decidir GAP-P1-1 (`install manifest`/`env` literais vs o fluxo
   `capabilities` + `forge/context/v1` — documentar o caminho oficial).
4. Perfis com subconjunto real de skills (GAP-P1-5) — hoje ~1.500 arquivos
   por install de projeto.
5. `MANIFEST.sha256` do bundle canônico + verificação no `doctor`
   (GAP-P1-4 completo).
6. Resíduos: `--host none`/csv (P2-1), sdist enxuto (P2-2),
   `recommended`≠`full` (P2-3), registry de conta com refresh (P2-5),
   gerador de `manifest.json` (P2-6), unificar forma `.mcp.json` (P2-7),
   caminho codex-MCP (P2-8).

## 15. Status por Forge

| Forge | `forge/context/v1` | `_forgecontext` | `_installkit` | `forge_bootstrap` | Status |
|---|---|---|---|---|---|
| the-forge | registry + docs + txn | v1.3.1 | v1.0.1 | v1.1.1 | **merged, pendente de release** (0.6.0) |
| **spark-forge-aws** | registry + docs + txn | v1.3.1 | v1.0.1 | v1.1.1 | **merged, pendente de release** (0.6.0) |
| spark-forge-azure | registry + docs + txn | v1.3.1 | v1.0.1 | v1.1.1 | **merged, pendente de release** (0.2.0) |
| api-forge | registry + docs + txn | v1.3.1 | v1.0.1 | v1.1.1 | **merged, pendente de release** (0.2.0) |
| platform-forge | registry + docs + txn | v1.3.1 | v1.0.1 | v1.1.1 | **merged, pendente de release** (0.2.0) |
| forge-doctor-api | — | ausente | v1.0.1 | v1.1.1 | **installkit only (boundary)** |
| forge-doctor-data | — | ausente | v1.0.1 | v1.1.1 | **installkit only (boundary)**; certifi PYSEC-2026-4320 |
| data-sentinel-forge | — | ausente | v1.0.0 | ausente | **deferred by owner** |

---

## Apêndice — comandos executados para este relatório

```text
git log v0.5.6..HEAD --format='%h %H %s'     → 20 commits
git diff --stat v0.5.6..HEAD                 → 49 files, +7720/−315
sha256sum sparkforge_aws/_forgecontext.py    → 390f5e0e61ab80dc…
sha256sum sparkforge_aws/_installkit.py      → 1484135ae71c396e…
sha256sum scripts/forge_bootstrap.py         → 978862ebedb9ecfb…
grep _FORGECONTEXT_VERSION sparkforge_aws/_forgecontext.py → "1.3.1"
grep -c 'def test_' tests/test_{install,wheel_isolation,
  evals_surface,discovery_ops,verify_wheel}.py → 53/1/21/28/46
```

## Pós-release — evidência de publicação (2026-10-23 UTC)

| Item | Estado | Evidência |
|---|---|---|
| Tag | CRIADA | `v0.6.0` no merge commit da release PR |
| GitHub Release | CRIADO | `gh release view v0.6.0` |
| PyPI | PUBLICADO | `pypi.org/pypi/sparkforge-aws/json` → `0.6.0` |
| Wheel smoke (venv limpo) | PASS | `pip install sparkforge-aws==0.6.0` + `sparkforge-aws --version` → `0.6.0` |

Notas: installkit canônico 1.0.2 (`_SOURCE_SHA256 a15ca78bb34a0109`), bootstrap 1.1.1 — propagados aos 7 carriers; `vendor.py --check` CLEAN ×7. `data-sentinel-forge`: **deferido pelo dono** (outro CLI evoluindo).
