# Final Hardening — Baseline

Registro do ponto de partida da onda de fechamento descrita em
`prompt_evo_final_hardening.md` (arquivo ignorado por `.gitignore:81`, lido no
worktree). Onda de CLOSURE, nao de expansao: fechar as costuras declaradas,
classificar o que fica, e declarar o projeto em Architecture Freeze /
Evaluation Phase.

## Baseline

| campo | valor |
|---|---|
| BASE_SHA | `a1bf2ada47e182f52b1253910b92e45ef3508ecc` (`origin/main`, PR #125 — runtime convergence wave) |
| BRANCH | `devin/final-hardening-freeze` |
| DIRTY_STATE na criacao | `locks/py3.10.txt`, `locks/py3.11.txt`, `locks/py3.12.txt` — refresh de dependencias herdado do worktree (boto3/botocore 1.43.105→108, cryptography, etc.), commitado em separado |
| PYTHON_VERSION | 3.14.6 |
| PACKAGE_VERSION | 0.5.0 |
| DATA | 2026-10-06 |
| CI_REMOTE | NOT_OBSERVED (cota de Actions esgotada — limitacao de ambiente, nao de codigo) |

## Documentos lidos e validados

- `docs/audit/RUNTIME-CONVERGENCE-BASELINE.md`
- `docs/audit/RUNTIME-CONVERGENCE-FINAL-REPORT.md`
- `docs/audit/RUNTIME-CONVERGENCE-OUTCOME-BRIEF.md`
- `docs/gates-por-mudanca.md`

Os tres relatorios descrevem a onda anterior (`devin/runtime-convergence-wave`,
SHAs historicos `8f1581f`/`edf89ac`) — sao documentos de epoca e continuam
verdadeiros como historia; as referencias de SHA/branch nao se aplicam a esta
onda e a higiene de evidencia delas e tratada na propria wave.

## Lacuna declarada que esta onda fecha

`RoleContextPlan → AgentHandoff` (PARTIAL no relatorio final): o plano de role
governa selecao de contexto no `ContextGateway`, mas `AgentHandoff` era so um
contrato de dados — nenhum caminho o admitia contra o plano do receptor.
Fechamento nesta onda: admission gate deterministico em
`sparkforge_aws/agentic/handoff.py` com decisao ALLOW/DENY/REVIEW, preservacao
DATA_ONLY, teto de trust declarado, taint por varredura lexical, defesa de
confused deputy e filtragem por seccao — tudo com negacao nomeada, nunca
sumico.

## Fora de escopo desta onda (classificacao, nao construcao)

| item | classificacao | gatilho |
|---|---|---|
| Adaptive Model Router ativo | DEFERRED — permanece shadow | corpus rotulado + gates de qualidade/economia |
| `provider_availability` | UNRESOLVED — core e offline por desenho | medida de host real |
| Scorecard persistente | DEFERRED — sem consumidor | consumidor real declarado |
| Paginacao MCP | BACKLOG | resultado que exceda janela util do host |
| A2A | EXPERIMENTAL — adapter stdlib-puro, `a2a-ready` | revisao da spec vigente + driver real |
| OTLP collector live | DEFERRED_EXTERNAL | collector acessivel |
| Memory event sourcing | DEFERRED | consumidor de replay |
| Forge Kernel | NOT_NOW — sem extracao | evidencia de reuso fora do repo |
