# SparkForge AWS — Current State Audit (baseline + v2 closure)

## 1. Visão Geral da Auditoria

Auditoria aprofundada de arquitetura, componentes e cobertura do repositório SparkForge AWS para evolução em **AWS Data Platform Engineering Agent Factory**.
As linhas históricas abaixo são baseline; o estado implementado e os limites atuais
estão explicitados na seção de fechamento Agentic OS v2.

---

## 2. Inventário de Componentes Auditados

| Camada | Itens Auditados | Estado Atual | Avaliação |
|---|---|---|---|
| **Deterministic Facts** | Módulos em `sparkforge/facts/` | Extratores determinísticos | **Excelente**: 100% determinístico, offline, sem LLM. |
| **Rules Engine** | Catálogos YAML em `rules/catalog/` | AST Python puro | **Excelente**: Sem `eval()`, tipado e com version scope. |
| **Findings** | Modelos imutáveis (`sparkforge/findings/`) | SHA-256 Signatures | **Excelente**: Requer lista não-vazia de `fact_id`. |
| **Case Lifecycle** | 4 Gates duráveis (`sparkforge/case/`) | Fail-closed | **Excelente**: Overrides auditados e assinados. |
| **Canonical Registry** | `sparkforge/registry/` | Pydantic / JSON Schema | **Sólido**: Unificado para agentes, skills, tools e teams. |
| **Token Economy** | `sparkforge/economy/` | Ledger + Router + Decision Plane | **Sólido com gates**: reconciliação explícita, `cost_basis` e router `shadow` por default. |
| **Context Funnel** | `sparkforge/context/` | Gateway + Quality + Disclosure A/B/C | **Sólido com limites**: itens, evidência, stale, cache e tokens observados separados. |
| **Platform Compilers** | `sparkforge/adapters/platforms/` | 7 Targets | **Sólido**: Antigravity, Cursor, Claude, Devin, etc. |
| **Workflows & DAG** | `sparkforge/workflows/` | TaskSpec + Waves DAG | **Sólido**: Handoffs estruturados e detecção de ciclos. |
| **Local Observability** | `sparkforge/observability/` | SQLite + AgentOps | **Sólido localmente**: traces, inspect, compare e baseline; eixos sem fonte permanecem `unresolved`. |
| **Agentic OS v2** | `sparkforge/agentic/`, `sparkforge/protocols/forge.py` | Contratos locais | **Implementado**: trust, memória, checkpoint, handoff `DATA_ONLY` e envelopes content-addressed. |

A linha "Test Baseline" (contagem de arquivos de teste, testes coletados e resultado
"passed/skipped/falhas") foi removida: os números publicados em `a5b9e96` estão
desatualizados, e `--collect-only` mede testes coletados, não testes passando — ver
`docs/claims.lock.json` para o motivo de cada número.

---

## 3. Lacunas de execução e evidência que permanecem

1. **Evals live de provider**: o core não chama modelos; qualidade, tokens de provider e custo exigem transcript/observação externa.
2. **Promoção automática para `active`**: scorecards informam decisão, mas não concedem autoridade; promoção continua explícita e gated.
3. **Memória semântica vetorial**: retrieval local lexical existe; vector database obrigatório não faz parte do contrato.
4. **Sincronização contínua de plataformas**: exporters geram artefatos sob demanda; hooks/watchers ficam fora desta entrega.
5. **Execução AWS**: coleta e mutação são fronteiras explícitas; o Agentic OS v2 permanece local-first e não executa AWS implicitamente.

As lacunas de domínio listadas na auditoria original foram fechadas por módulos
determinísticos em `sparkforge/migration`, `lakeformation`, `iceberg`, `spark`,
`terraform`, `databases`, `streaming` e `errors`; cada domínio continua condicionado
às suas facts, runtime matrix, regras e evidências específicas.

## 4. Fechamento Agentic OS v2

| Contrato | Fonte atual | Limite preservado |
|---|---|---|
| Memória/trust | `sparkforge.agentic.memory`, `sparkforge.agentic.trust` | quarantine, taint e `DATA_ONLY`; sem autoridade implícita |
| Contexto/economia | `sparkforge.context.quality`, `sparkforge.economy.ledger` | bytes, tokens observados e custo não são intercambiáveis |
| Continuidade | `sparkforge.agentic.checkpoint`, `sparkforge.protocols.forge` | envelopes serializáveis e content-addressed |
| AgentOps | `sparkforge.observability.agentops` | traces locais; ausências permanecem `unresolved` |
| Superfícies | `sparkforge.adapters._core`, CLI e MCP | mesma implementação; baseline save limitado a arquivo local |

Referências operacionais: `docs/vnext/ARCHITECTURE.md`,
`docs/vnext/CURRENT-STATE.md`, ADR-012 e
`docs/sdd/AGENTIC_ENGINEERING_OS_V2/ship.md`.
