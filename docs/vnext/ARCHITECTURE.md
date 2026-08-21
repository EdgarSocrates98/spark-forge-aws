# SparkForge AWS — Target Canonical Architecture vNext (Phase 1)

## 1. Visão Geral da Arquitetura

O **SparkForge AWS vNext** é projetado como uma **Data & AWS Agent Factory industrial**, estruturada em camadas independentes e de acoplamento fraco, orientada ao princípio:

> **RESULTADO CORRETO POR TOKEN CONSUMIDO.**
> `DETERMINISTIC FIRST → RETRIEVAL → SMALL/CHEAP MODEL → SPECIALIST → POWERFUL MODEL → MULTI-AGENT`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Layer 6: Local-First AgentOps & Observability            │
│       Traces (run_id / span_id), Token/Cost Tracking, SQLite Local Storage  │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 5: Workflow Engine & Execution DAG                 │
│       Task Spec, Execution DAG, Parallel/Sequential Waves, Validation Gates │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 4: Context Funnel & Intentional Memory             │
│   Context Funnel (Candidate -> Chunks -> Dedup -> Context), Progressive A/B/C│
│   Memory: Working (Ephem), Episodic (Runs), Semantic (Facts), Procedural    │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 3: Token Economy Engine & Model Router             │
│   Cascade 7 Tiers (0: Deterministic ... 6: Multi-Agent), Profiles (ECO, ...)│
│   Capability-Based Model Router, Token Waste Detector, Budget Guardrails    │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Layer 2: Multi-Platform Compilers & Protocols            │
│   MCP Protocol, A2A/ACP Interfaces, Platform Exporters:                     │
│   - Antigravity 2.0 (.agents/agents, .agents/skills, .agents/rules)         │
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
│   sparkforge.facts (21 extractors, 118 kinds), sparkforge.rules (AST Engine)│
│   sparkforge.findings (Immutable Evidence Schema), sparkforge.case (Gates)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Descrição Detalhada das Camadas

### Layer 0: Deterministic Core (Fundação Inviolável)
- **Zero LLM Calls**: Toda análise de código (PySpark AST), planos físicos (`EXPLAIN FORMATTED`), logs de eventos Spark (`.jsonl`), metadados Iceberg, schemas Glue e configurações Terraform é processada localmente sem modelo de linguagem.
- **Rastreabilidade e Integridade**: Findings estruturados que exigem lista não-vazia de `fact_id`s ancorados e assinatura digital imutável SHA-256.
- **Gates Invioláveis**: Bloqueio de fases do caso sem evidência correspondente, auditado por overrides rastreáveis.

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
  1. **Antigravity 2.0**: `.agents/agents/`, `.agents/skills/`, `.agents/rules/` com progressive disclosure.
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
  - `ECO` (Default): Single-agent, cheap models, turns curtos, cache agressivo, 0 reflection desnecessária.
  - `BALANCED`: Equilíbrio entre custo e verificação adicional.
  - `QUALITY`: Modelos fortes com critic/refiner e validações ampliadas.
  - `OFFLINE`: Zero chamadas externas, inferência local ou determinística.
  - `STRICT`: Revisões rigorosas de segurança, gates explícitos e evidência máxima.
- **Model Router Baseado em Capacidade**: Seleção por `(complexidade × risco × capacidade_necessária × budget × privacidade)`.
- **Token Waste Detector**: Análise automática de loops redundantes, retries idênticos e context over-provisioning via `sparkforge optimize`.

### Layer 4: Context Funnel & Intentional Memory
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
├── memory/             # Working, Episodic, Semantic e Procedural Memory (Layer 4)
├── workflows/          # DAG de Execução, Waves e Task Spec Engine (Layer 5)
├── observability/      # AgentOps Local, Tracing (run_id/span_id) e SQLite Storage (Layer 6)
├── security/           # Políticas de Autorização, Sandboxing e Redação de Segredos
├── evals/              # Framework de Avaliação: Golden, BDD, Holdout, Economia
├── providers/          # Abstração de Provedores de Modelo (Mock, Local, OpenAI-compat, AWS)
├── adapters/           # Compiladores de Plataformas (Antigravity, Cursor, Claude, Devin, etc.)
└── tools/              # Ferramentas determinísticas de utilidade e CLI
```

---

## 4. Estratégia de Migração e Compatibilidade Inegociável

1. **Retrocompatibilidade de CLI**: O comando `sparkforge` continuará aceitando todos os subcomandos existentes (`analyze`, `judge`, `case`, `report`, `benchmark`, `funcval`, `runtime`, `fuse`). Novos comandos (`export`, `doctor`, `inspect`, `optimize`, `workflow`, `eval`) serão introduzidos de forma aditiva.
2. **Retrocompatibilidade de MCP**: As ferramentas MCP expostas continuam com as mesmas assinaturas e retornos JSON estruturados.
3. **Preservação de Catálogos de Regras**: As 52 regras YAML existentes continuam sendo a fonte canônica para julgamentos.
