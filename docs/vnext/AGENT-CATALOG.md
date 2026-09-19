# SparkForge AWS — Canonical Agent & Skill Catalog vNext (Phase 4)

## 1. Hierarquia Canônica de Agentes

Para evitar proliferação desordenada e desperdício de tokens, o SparkForge vNext adota uma estrutura em três níveis:

```
┌─────────────────────────────────────────────────────────────┐
│                 A. SPECIALIST ROLES / SUBAGENTS              │
│  Execução de Tarefas Específicas com Limites Estritos        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Carrega proceduralmente
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 B. COMPOSABLE SKILLS (40+)                  │
│  Instruções, Checklists e Procedimentos Lazy-Loaded (A/B)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Roteamento por Tiers

Este documento descrevia, em versões anteriores, uma camada de "Core
Coordinators" — sete agentes permanentes de supervisão e roteamento. Nenhum
dos sete existe em `agents/`, o diretório canônico (espelhado em
`.claude/agents/`, `.agents/agents/` e `.github/agents/` e verificado por
`tests/test_agents_parity.py::TestMirrors`). A auditoria registrada em
`docs/claims.lock.json` documenta, alegação por alegação, o motivo de
cada um.

O que existe de fato é o motor de economia de tokens em
`sparkforge/registry/models.py`, que define tiers de 0 a 6 (`ModelTier`)
usados para selecionar o perfil de execução de cada tarefa.

---

## 3. Matriz de Classificação e Refatoração de Agentes

| Agente Anterior | Classificação vNext | Destino / Justificativa | Alias de Compatibilidade |
|---|---|---|---|
| `spark-performance-architect` | **Core Coordinator** | Mantido como coordenador primário de performance PySpark. | `spark-performance-architect` |
| `glue-incremental-performance-architect` | **Core Coordinator** | Mantido para fluxos full + incremental complexos. | `glue-incremental-performance-architect` |
| `glue-infra-reviewer` | **Specialist Role** | Foco em infraestrutura Glue, worker types e auto scaling. | `glue-infra-reviewer` |
| `emr-infra-reviewer` | **Specialist Role** | Foco em clusters EMR EC2 e Serverless. | `emr-infra-reviewer` |
| `athena-query-optimizer` | **Specialist Role** | Otimização de consultas, pruning e workgroups Athena. | `athena-query-optimizer` |
| `pyspark-code-reviewer` | **Specialist Role** | Revisão de código PySpark e GraphFrames. | `pyspark-code-reviewer` |
| `iceberg-performance-engineer` | **Specialist Role** | Manutenção e performance de tabelas Iceberg. | `iceberg-performance-engineer` |
| `data-quality-reviewer` | **Specialist Role** | Auditoria do posicionamento e custo de regras de qualidade. | `data-quality-reviewer` |
| `sf-inventory` | **Executor** | Executor determinístico de inventário (Phase Loop). | `sf-inventory` |
| `sf-extractor` | **Executor** | Executor determinístico de evidências (Phase Loop). | `sf-extractor` |
| `sf-judge` | **Executor** | Executor de regras determinísticas (Phase Loop). | `sf-judge` |
| `sf-verifier` | **Executor** | Executor de validação de saídas (Phase Loop). | `sf-verifier` |
| `sf-synthesizer` | **Executor** | Executor de síntese de relatório assinado. | `sf-synthesizer` |

Seis agentes (`sf-pyspark-specialist`, `sf-storage-specialist`,
`sf-runtime-specialist`, `sf-token-verifier`,
`sf-security-reviewer` e um sexto, hoje removido) apareciam aqui como "Convertidos em Skill
Lazy-Loaded". Nenhum foi convertido: os cinco primeiros continuaram existindo como agentes
ativos em `agents/`, roteados de fato em `rules/catalog/routing.yaml` e
exercitados por `tests/test_router_agents.py` (ver `docs/claims.lock.json`, VNX-167 a
VNX-171 ou vizinhas, para o motivo de cada um). O sexto era um coordenador de FinOps,
de fato removido em 2026-09-19 na feature `docs/sdd/SF_STUBS/` (a lista completa dos 19
agentes `sf-*` ocos removidos está em `OCOS`, `tests/test_sf_stubs.py`) — não como skill,
apenas removido junto com a
camada `sf-*`/`agentic-sf-*` oca. A linha foi removida, não reescrita.

---

## 4. Catálogo de Skills Padronizadas (Lazy-Loaded)

Cada skill segue o padrão de Progressive Disclosure:

```
skills/<skill-name>/
├── SKILL.md          # Nível A (Metadados/Triggers) + Nível B (Procedimento)
├── references/       # Nível C (Documentação técnica aprofundada)
└── scripts/          # Ferramentas e automações executáveis
```

### Principais Skills de Engenharia de Dados & AWS:
1. `optimize-pyspark-code`: Eliminação de UDFs, tuning de joins, skew e persistência.
2. `diagnose-data-skew`: Diagnóstico de partições desbalanceadas e salting.
3. `optimize-iceberg-table`: Compaction, rewrite manifests, snapshot expiration, sort orders.
4. `tune-glue-job`: Ajuste de worker types (G.1X, G.2X, G.4X) e memória.
5. `review-emr-cluster`: Instâncias Spot, Task fleets e Managed Scaling.
6. `review-data-validation`: Posicionamento eficiente de checks PyDeequ / Great Expectations.
7. `token-efficient-agent`: Práticas de economia de contexto e saída concisa.
8. `tool-specialist-routing`: Seleção correta de ferramentas determinísticas por domínio.
9. `design-incremental-processing`: Padrões latest-per-key e watermarking.

`athena-query-optimizer` não é uma skill: é o **agent** listado na §3, e otimização de
consultas Athena passa pelo verbo `sparkforge analyze athena-workgroup`, não por uma skill
lazy-loaded.

---

## 5. Garantia de Retrocompatibilidade

Qualquer referência a nomes legados de agentes ou skills será resolvida automaticamente via **tabela de aliases** em `sparkforge.registry`, garantindo que scripts, integrações e comandos existentes continuem funcionando perfeitamente sem alterações.
