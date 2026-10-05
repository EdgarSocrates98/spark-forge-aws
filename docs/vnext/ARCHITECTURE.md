# SparkForge AWS — Canonical Architecture vNext (target + current implementation)

## 1. Visão Geral da Arquitetura

O **SparkForge AWS vNext** é projetado como uma **Data & AWS Agent Factory industrial**, estruturada em camadas independentes e de acoplamento fraco, orientada ao princípio:

> **RESULTADO CORRETO POR TOKEN CONSUMIDO.**
> `DETERMINISTIC FIRST → RETRIEVAL → SMALL/CHEAP MODEL → SPECIALIST → POWERFUL MODEL → MULTI-AGENT`

Este documento combina arquitetura-alvo com estado implementado. "Implementado"
significa contrato local, determinístico e testável; não significa chamada de provider,
promoção automática de modelo ou execução AWS. "Target" identifica integração futura,
exporter sob demanda ou capacidade dependente de evidência externa.

## Estado corrente da arquitetura

| Área | Estado | Fonte de verdade |
|---|---|---|
| Core de facts/rules/findings/case | Implementado e offline | `sparkforge/facts`, `sparkforge/rules`, `sparkforge/findings`, `sparkforge/case` |
| Registry e exporters | Implementado; artefatos de plataforma são gerados sob demanda | `sparkforge/registry`, `sparkforge/adapters/platforms` |
| Gateway/contexto e economia | Implementado com métricas separadas e router `shadow` | `sparkforge/context`, `sparkforge/economy` |
| Agentic OS v2 | Implementado local-first | `sparkforge/agentic`, `sparkforge/protocols/forge.py` |
| AgentOps | Implementado para traces locais | `sparkforge/observability/agentops.py` |
| Providers, active routing e AWS mutation | Fora desta onda | ADR-012, `AGENTS.md`, `CLAUDE.md` |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Layer 6: Local-First AgentOps & Observability            │
│       Traces (run_id / span_id), Token/Cost Tracking, SQLite Local Storage  │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 5: Workflow Engine & Execution DAG                 │
│       Task Spec, Execution DAG, Parallel/Sequential Waves, Validation Gates │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 4: Context Funnel & Scoped Memory                  │
│   Context Funnel (Candidate -> Chunks -> Dedup -> Context), Progressive A/B/C│
│   Memory: Working (Ephem), Episodic (Runs), Semantic (Facts), Procedural    │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 3: Token Economy Engine & Model Router             │
│   Cascade 7 Tiers (0: Deterministic ... 6: Multi-Agent), Profiles (ECO, ...)│
│   Capability-Based Model Router, Token Waste Detector, Budget Guardrails    │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 2: Multi-Platform Compilers & Protocols            │
│   MCP Protocol, A2A/ACP Interfaces, Platform Exporters:                     │
│   - Antigravity (.agents/agents, .agents/skills, .agents/rules)             │
│   - Cursor (.cursor/rules/*.mdc, MCP config)                                │
│   - Claude Code (CLAUDE.md bootstrap, .claude/agents, .claude/skills)       │
│   - Devin / Windsurf (Platform adapters, instructions, memory)              │
│   - Generic Open Standard (AGENTS.md, Agent Skills, JSON Schema)            │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 1: Canonical Factory Registry (SSOT)               │
│   Pydantic & JSON Schemas: AgentManifest, SkillManifest, ToolManifest,      │
│   TeamManifest, WorkflowManifest, PolicyManifest, KnowledgeManifest, Eval   │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 0: Deterministic Core (0 Tokens LLM)                │
│   sparkforge.facts (extractors, fact kinds), sparkforge.rules (AST Engine)  │
│   sparkforge.findings (Immutable Evidence Schema), sparkforge.case (Gates)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Descrição Detalhada das Camadas

### Layer 0: Deterministic Core (Fundação Inviolável)
- **Zero LLM Calls**: Toda análise de código (PySpark AST), planos físicos (`EXPLAIN FORMATTED`), logs de eventos Spark (`.jsonl`), metadados Iceberg, schemas Glue e configurações Terraform é processada localmente sem modelo de linguagem.
- **Rastreabilidade e Integridade**: Findings estruturados que exigem lista não-vazia de `fact_id`s ancorados e assinatura digital imutável SHA-256.
- **Gates Invioláveis**: Bloqueio de fases do caso sem evidência correspondente, auditado por overrides rastreáveis.

#### Lane de arquitetura Lake Formation

O núcleo determinístico mantém uma lane específica para arquitetura version-aware
de Lake Formation. `sparkforge/lakeformation/capabilities.py` lê
`knowledge/lakeformation/capability-matrix.yaml`; `catalog_routing.py` mantém
ownership de job, conta local, catálogo de origem e catálogo de destino sem
colar `glue.id` a `glue.account-id`; `architecture.py` compõe capability,
operação, credential vending e cross-account em `consistent`, `unresolved` ou
`blocked`. A superfície é `sparkforge lakeformation architect` e
`sparkforge_lakeformation_architect`, ambos offline e sem mutação AWS.

A mesma lane expõe `review`: operational review que compõe facts de PySpark/Terraform, detecta
configuração tardia, explica caminhos metadata/data, classifica credential
vending/RAM/S3/KMS, gera preflight/root-cause/migration e seleciona referências
por progressive disclosure. Números de performance/FinOps só entram com
benchmark ou DPUSeconds observado.

O migration report mantém campos legados e também expõe
`review.migration.sections`: runtime, Spark, Python, Iceberg, Lake Formation,
DynamicFrame, FGAC/FTA, cross-account, CatalogId/RAM/IDs, código, Terraform,
IAM/LF, testes e rollback. Para EMR, o disclosure carrega a matriz EMR sem
carregar a referência específica de Glue; combinações não declaradas continuam
`unknown`/`unresolved`.

### Layer 1: Canonical Factory Registry (Single Source of Truth)
- Substitui a dispersão de definições manuais por um registro canônico tipado via Pydantic e validado contra JSON Schema.
- Entidades canônicas:
  - `AgentManifest`: id, nome, versão, propósito, domínios, habilidades requeridas/opcionais, ferramentas permitidas/negadas, nível de risco, política de modelo, budget padrão, memória e targets suportados.
  - `SkillManifest`: id, nome, descrição concisa para roteamento (Level A), instruções de procedimento (Level B), referências e patterns (Level C), triggers e anti-triggers.
  - `ToolManifest`: id, nome, namespace, esquema de entrada/saída, descrição compacta, classe de mutação (`read-only`, `reversible`, `sensitive`, `destructive`).
  - `TeamManifest`: id, coordenador, membros especialistas, handoffs estruturados e políticas de escalonamento.
  - `WorkflowManifest`: id, DAG de tarefas, waves, pré-requisitos, gates e critérios de sucesso.
  - `PolicyManifest`: regras operacionais estritas (redação de segredos, boundaries de sandbox, restrições de rede).

### Layer 2: Platform Compiler & Adapter Layer
- Arquitetura de compilação: `Canonical Registry` → `Platform Compiler` → `Target Artifacts`.
- Suporte nativo aos ecossistemas:
  1. **Antigravity**: `.agents/agents/`, `.agents/skills/`, `.agents/rules/` com progressive disclosure.
  2. **Cursor**: `.cursor/rules/*.mdc` com escopo por arquivo/linguagem/tarefa e MCP config.
  3. **Claude Code**: `CLAUDE.md` conciso como bootstrap, espelhos `.claude/agents/` e `.claude/skills/`.
  4. **Devin & Windsurf**: Mapeamento limpo e isolado sem vazar detalhes no core.
  5. **Generic / Open Standard**: `AGENTS.md`, especificação padrão de Agent Skills e schemas JSON abertos.
- Comandos CLI: `sparkforge export --target <target>` e `sparkforge sync`.

### Layer 3: Token Economy Engine & Model Router
- **Cascata de 7 Tiers**:
  - `Tier 0` (Determinístico): Extração de fatos e regras (Custo 0).
  - `Tier 1` (Cache): Reutilização de artefato validado por hash de conteúdo e dependências.
  - `Tier 2` (Retrieval): Recuperação estritamente direcionada de chunks de código e conhecimento.
  - `Tier 3` (Cheap / Local Model): Modelos rápidos e econômicos para classificação e tarefas triviais.
  - `Tier 4` (Specialist Model): Modelos de código intermediários com injeção da Skill específica.
  - `Tier 5` (Premium Reasoning): Modelos topo de linha acionados apenas sob alto risco ou complexidade extrema.
  - `Tier 6` (Multi-Agent): Decomposição paralela apenas quando o benefício superar mensuravelmente o custo.
- **Perfis de Execução**:
  - `ECO` (Default): Single-agent, cheap models, turns curtos, cache agressivo.
  - `BALANCED`: Equilíbrio entre custo e verificação adicional.
  - `QUALITY`: Modelos fortes com critic/refiner e validações ampliadas.
  - `OFFLINE`: Zero chamadas externas, inferência local ou determinística.
  - `STRICT`: Revisões rigorosas de segurança, gates explícitos e evidência máxima.
- **Model Router Baseado em Capacidade**: Seleção por `(complexidade × risco × capacidade_necessária × budget × privacidade)`.
- **Token Waste Detector**: Análise automática de loops redundantes, retries idênticos e context over-provisioning via `sparkforge optimize`.

### Layer 4: Context Funnel & Scoped Memory
- **Context Funnel**: `Repositório Completo` → `Arquivos Candidatos` → `Chunks Relevantes` → `Evidências Desduplicadas` → `Contexto Mínimo da Tarefa`.
- **Progressive Disclosure**:
  - `Nível A (Metadados)`: Identificação e triggers (~20-50 tokens).
  - `Nível B (Instruções)`: Procedimento da skill carregado sob demanda.
  - `Nível C (Referências)`: Documentação técnica extensa lida seletivamente.
- **Engine de Memória**:
  - `Working Memory`: Estado efêmero da tarefa em andamento.
  - `Episodic Memory`: Histórico de runs anteriores com métricas e desfechos.
  - `Semantic Memory`: Fatos e regras consolidados com TTL e invalidação automática em caso de mutação.
  - `Procedural Memory`: Blueprints e receitas de solução de problemas.

### Layer 5: Workflow Engine & Waves
- Representação de pipelines complexos como DAGs de nós (`Task`, `Agent`, `Tool`, `Gate`, `Artifact`).
- Execução em Waves:
  - `Wave 0`: Discovery e extração determinística.
  - `Wave 1`: Pesquisa e hipóteses independentes.
  - `Wave 2`: Implementação e transformações.
  - `Wave 3`: Validação funcional e benchmarks.
  - `Wave 4`: Segurança, regressão e assinatura.
  - `Wave 5`: Publicação e handoff.

### Layer 6: Local-First Observability & AgentOps
- Rastreamento unificado com `run_id` e `span_id` para cada etapa.
- Métricas calculadas:
  - Custo por tarefa bem-sucedida (`Cost / Success`)
  - Tokens por tarefa resolvida (`Tokens / Success`)
  - Taxa de escalonamento (`Escalation Rate`)
  - Desperdício em retries (`Retry Waste`)
  - Taxa de acerto de cache (`Cache Hit Rate`)
- Armazenamento em SQLite local ou JSONL estruturado (zero dependência de SaaS ou cloud).

---

## 3. Estrutura Modular de Pacotes vNext

```
sparkforge/
├── core/               # Tipos base, contratos e exceções fundamentais
├── registry/           # Manifests Pydantic, Schemas JSON e Registry Canônico
├── facts/              # Extratores determinísticos offline (Layer 0)
├── rules/              # Motor de regras AST e Catálogos (Layer 0)
├── findings/           # Modelos de Finding, Validação e Assinatura (Layer 0)
├── case/               # Gerenciador de ciclo de vida e Gates (Layer 0)
├── economy/            # Cascata de 7 Tiers, Budgets, Cache e Waste Detector (Layer 3)
├── routing/            # Capability Model Router e Seleção de Perfis (Layer 3)
├── context/            # Context Funnel, Progressive Disclosure e Knowledge Packs (Layer 4)
├── agentic/            # Trust, memória, checkpoints, debate e execução auditável
├── workflows/          # DAG de Execução, Waves e Task Spec Engine (Layer 5)
├── observability/      # AgentOps Local, Tracing (run_id/span_id) e SQLite Storage (Layer 6)
├── security/           # Políticas de Autorização, Sandboxing e Redação de Segredos
├── evals/              # Framework de Avaliação: Golden, BDD, Holdout, Economia
├── providers/          # Contratos/adapters; core não chama provider automaticamente
├── adapters/           # Compiladores de Plataformas (Antigravity, Cursor, Claude, Devin, etc.)
└── tools/              # Ferramentas determinísticas de utilidade e CLI
```

---

## 4. Estratégia de Migração e Compatibilidade Inegociável

1. **Retrocompatibilidade de CLI**: O comando `sparkforge` continuará aceitando todos os subcomandos existentes (`analyze`, `judge`, `case`, `report`, `benchmark`, `funcval`, `runtime`, `fuse`). Novos comandos (`export`, `doctor`, `inspect`, `optimize`, `workflow`, `eval`) serão introduzidos de forma aditiva.
2. **Retrocompatibilidade de MCP**: As ferramentas MCP expostas continuam com as mesmas assinaturas e retornos JSON estruturados.
3. **Preservação de Catálogos de Regras**: Os catálogos de regras YAML existentes em `rules/catalog/` continuam sendo a fonte canônica para julgamentos.
4. **Autoridade separada de evidência**: trust, taint, `instruction_authority`,
   `cost_basis`, `unresolved` e promoção são campos distintos; nenhum scorecard pode
   autorizar uma rota `active` sozinho.

## 5. Decision Control Plane — completion build (2026-09-28)

O plano de decisão bounded agora converge em uma única `AuthorityPolicy`, carregada de
`config/decisions/agentic_control_plane.yaml`. `shadow` observa, `assisted` exige autoridade
explícita para propor e `active` exige autoridade explícita, evidência de promoção, rollback e
`active.enabled`; o default permanece fail-closed. Serviço, controller, bridge e kernel usam a
mesma decisão estruturada, sem promoção automática por benchmark.

`DecisionCache` lê somente registros do owner/freshness do escopo e aplica `cache_max_entries`
por escopo, sem reduzir a capacidade de outro consumidor. A chave inclui contrato, estado,
policy, calibration, profile e risco. `RecoveryGovernor` consome retry e replan em categorias
independentes e recusa fingerprint de ciclo repetida antes de consumir budget; receipts registram
autoridade, cache, budget e recovery.

Hosts Claude/Codex/Devin continuam adapters de recordings, sem SDK ou rede no core. O hash do
transcript é calculado sobre conteúdo canônico sem o hash declarado, e provider tokens só entram
quando usage e transcript coincidem; caso contrário, ficam `tokens_unresolved`. O replay benchmark
mantém qualidade, rota, bytes, tokens e custo como eixos independentes. Custo requer `cost_basis`;
bytes nunca são convertidos em tokens.
## 6. Lake Formation FGAC/FTA — decision graph por perna

O motor `sparkforge/lakeformation/architecture.py` agora compõe decisões
independentes para source e target, preservando formato e operação de cada lado.
`not_supported` bloqueia; escrita em `read_only` bloqueia; `limited` e
`version_dependent` exigem evidência específica; `unknown` permanece
`unresolved`. A decisão composta não transforma uma leitura Parquet em suporte
implícito para um `MERGE` Iceberg.

`table_access_model` (FGAC/FTA) é separado de `access_governance_mode`
(Lake Formation/IAM/Hybrid). Cross-account declara uma rota: Glue ETL pode usar
CatalogId explícito sem resource link quando a evidência liga o id ao catálogo
produtor. `IAMAllowedPrincipals` não é bloqueio universal em Hybrid Access;
registro, opt-in e versão cross-account continuam verificações independentes.
`glue.id` é comparado a ownership e `glue.account-id` ao contexto esperado,
sem alias entre propriedades.

## 7. Agentic OS v2 — implementação local-first

O desenho acima agora tem uma camada de contratos implementada sem provider SDK:

| Área | Contrato/código | Limite operacional |
|---|---|---|
| Memória institucional | `sparkforge.agentic.memory` | decisão sem evidência entra em quarantine; retrieval não confia nela por padrão |
| Trust e handoff | `sparkforge.agentic.trust`, `sparkforge.protocols.forge` | confiança não concede autoridade de instrução; handoff é `DATA_ONLY` |
| Contexto | `sparkforge.context.quality` | bytes, tokens observados e custo ficam em eixos separados |
| Economia | `sparkforge.economy.ledger`, `model_router` | `cost_basis` obrigatório; router shadow por default |
| Checkpoint | `sparkforge.agentic.checkpoint` | estado resumível é content-addressed e serializável |
| AgentOps | `sparkforge.observability.agentops` | SQLite local; transcript, preço e qualidade ausentes saem `unresolved` |

As operações públicas são aditivas: `context inspect`, `agentops
inspect|compare|baseline` e `doctor agentic`. CLI e MCP chamam o mesmo `_core`; salvar
baseline é a única mutação nova e fica limitada a arquivo local. A ativação de modelos
ou execução AWS permanece fora dessa onda.
