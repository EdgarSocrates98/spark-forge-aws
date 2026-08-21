# SparkForge AWS — Current State Audit (Phase 0)

## 1. Visão Geral da Auditoria

Auditoria aprofundada de arquitetura, componentes e cobertura do repositório SparkForge AWS para evolução em **AWS Data Platform Engineering Agent Factory**.

---

## 2. Inventário de Componentes Auditados

| Camada | Itens Auditados | Estado Atual | Avaliação |
|---|---|---|---|
| **Deterministic Facts** | 21 módulos (`sparkforge/facts/`) | 118 fact kinds | **Excelente**: 100% determinístico, offline, sem LLM. |
| **Rules Engine** | 52 catálogos YAML (`rules/catalog/`) | AST Python puro | **Excelente**: Sem `eval()`, tipado e com version scope. |
| **Findings** | Modelos imutáveis (`sparkforge/findings/`) | SHA-256 Signatures | **Excelente**: Requer lista não-vazia de `fact_id`. |
| **Case Lifecycle** | 4 Gates duráveis (`sparkforge/case/`) | Fail-closed | **Excelente**: Overrides auditados e assinados. |
| **Canonical Registry** | `sparkforge/registry/` | Pydantic / JSON Schema | **Sólido**: Unificado para agentes, skills, tools e teams. |
| **Token Economy** | `sparkforge/economy/` | 7 Tiers + Router | **Sólido**: Perfis `ECO`, `BALANCED`, `QUALITY`, `OFFLINE`. |
| **Context Funnel** | `sparkforge/context/` | Funnel + Disclosure A/B/C | **Sólido**: Chunks deduplicados e pacotes modulares. |
| **Platform Compilers** | `sparkforge/adapters/platforms/` | 7 Targets | **Sólido**: Antigravity, Cursor, Claude, Devin, etc. |
| **Workflows & DAG** | `sparkforge/workflows/` | TaskSpec + Waves DAG | **Sólido**: Handoffs estruturados e detecção de ciclos. |
| **Local Observability** | `sparkforge/observability/` | SQLite (`traces.db`) | **Sólido**: Traces unificados com `run_id`/`span_id`. |
| **Test Baseline** | 100 arquivos de teste | 5.463 testes | **100% Verde**: 5.458 passed, 5 skipped, 0 falhas. |

---

## 3. Lacunas Identificadas para Especialização em AWS Data Platform

1. **Glue 4.0 ➔ 5.1 Migration Lab**: Ausência de analisador específico de migração Spark 3.3 ➔ 3.5, Java 17, e auditoria de S3A vs EMRFS.
2. **Lake Formation Deep Engine**: Falta de grafo determinístico de permissões multi-conta (Principal ➔ IAM ➔ LF ➔ RAM ➔ Data Location ➔ S3 ➔ KMS) e motor de decisão FTA vs FGAC.
3. **Iceberg Platform Engine**: Necessidade de ferramenta `iceberg doctor` determinística e planejador de manutenção (compaction, orphan cleanup, snapshot expiration).
4. **Spark Performance Profilers**: Necessidade de analisadores dedicados para parsing de event logs (`.jsonl`) e árvores de `EXPLAIN FORMATTED`.
5. **Terraform Risk Scanner**: Falta de classificador de riscos em planos Terraform (`SAFE`, `REVIEW`, `HIGH RISK`, `BLOCK`) com detecção de destruição de dados e IAM widening.
6. **NoSQL & Graph Engines**: Especialização estruturada para DynamoDB (single-table, hot partitions) e Neptune (property graph, openCypher, Gremlin).
7. **Streaming Engines**: Especialização profunda para Amazon MSK / Kafka e Amazon Kinesis.
8. **Deterministic Error KB**: Base de conhecimento estruturada para mapeamento instantâneo de stacktraces conhecidos sem chamada LLM.
