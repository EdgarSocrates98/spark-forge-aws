# SparkForge AWS — Current State Assessment (Phase 0)

## 1. Arquitetura Atual

O SparkForge AWS é uma plataforma de engenharia de desempenho e qualidade para cargas de dados PySpark na AWS (Glue, EMR EC2, EMR Serverless, Athena, Iceberg, S3).
A arquitetura atual baseia-se em um pipeline puramente determinístico para extração e julgamento de regras, com uma camada de orquestração agêntica:

```
[ Artifacts no Disco / S3 / Dumps ]
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge.facts (Extratores)         │ ──> Fact Kinds Determinísticos
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge.rules (Motor AST Seguro)   │ <── rules/catalog/*.yaml (Catálogos)
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge.findings (Modelos/Sign)    │ ──> Findings com Evidência Ancorada
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge.case (Ciclo de Vida)       │ ──> Gates, Overrides, Playbook, Router
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge.adapters (CLI / MCP)       │ ──> Consoles, IDEs, Claude, Devin, MCP
└────────────────────────────────────────┘
```

### Componentes Principais

1. **`sparkforge.facts`**: extratores offline (AST de PySpark, physical plans formatados, JSONL Spark event logs, Iceberg metadata dumps, Glue Data Catalog, Terraform HCL, SQL literals, Athena workgroups, EMR clusters, EMR Serverless, Data Quality checks, Graph/GraphFrames, Call Graphs, S3 listings, Table consumers, Terraform diffs, Benchmarks, Functional validation, Runtime detection, Fusion).
2. **`sparkforge.rules`**: Motor de avaliação seguro em Python AST sem `eval()`, com suporte a operadores tipados e escopos de versão (Glue e EMR).
3. **`sparkforge.findings`**: Estrutura imutável e assinável de achados técnicos com rastreabilidade obrigatória de `fact_id` e `rule_id`.
4. **`sparkforge.case`**: Gerenciador durável de casos de investigação com 4 gates (`baseline_captured`, `flows_mapped`, `functional_validation_defined`, `dominant_bottleneck_identified`) com bloqueio fail-closed e trilha de override auditada.
5. **`sparkforge.agents`**: Supervisores, políticas de modelo, observabilidade básica e controle de autonomia.
6. **`sparkforge.adapters`**: Interface CLI (`sparkforge`, `sparkforge-tools`) e servidor MCP (`sparkforge/adapters/mcp.py`).

---

## 2. Inventário de Recursos

| Categoria | Quantidade | Localização | Descrição |
|---|---|---|---|
| **Agents** | 5 executores de ciclo (+ demais especialistas) | `agents/*.md`, `agents/executors/*.md` | Agentes especialistas e executores determinísticos de fase (Phase Loop) |
| **Skills** | 44 | `skills/*/SKILL.md` | Habilidades especializadas com procedimentos e regras |
| **Subagents** | 16 | `config/subagents.yaml`, `subagents/*.md` | Contratos efêmeros com limite de tokens (1.800 tokens) |
| **Teams** | 5 | `config/teams-expansion.yaml` | Composições de times (evidence-quality, governance, etc.) |
| **Extratores de Fatos** | — | `sparkforge/facts/*.py` | Fatos determinísticos extraídos localmente |
| **Catálogos de Regras** | — | `rules/catalog/*.yaml` | Regras estruturadas com condições, severidade e ações |
| **Knowledge Base** | — | `knowledge/**/*.md`, `knowledge/**/*.json` | Guias de arquitetura, runtimes, anti-patterns, lockfiles |
| **Testes Automatizados** | — | `tests/test_*.py` | Cobertura unitária, contratos, golden cases e paridade |
| **Adapters / Mirrors** | 3 | `.agents/`, `.claude/`, `manifest.json` | Configurações para Antigravity, Claude Code e Devin |

As linhas acima que perderam a contagem ("—") tinham número desatualizado ou sem
artefato de medição — ver `docs/claims.lock.json` para o motivo de cada uma.

---

## 3. Strengths (Pontos Fortes)

1. **Zero LLM para Fatos e Regras**: Análise de código, plano de execução, metadados e logs 100% determinística, offline e sem custo de tokens.
2. **Evidência Rastreável por Construção**: É impossível gerar um `Finding` válido sem lista não-vazia de `fact_id` ancorados.
3. **Gates Fail-Closed com Assinatura Criptográfica**: Investigação rigorosa com integridade de relatório protegida por hash SHA-256 sobre fatos, regras e corpo.
4. **Respeito a Runtimes e Versões**: Matrizes formais de compatibilidade Glue/EMR impedem sugestões inválidas de APIs.
5. **Cobertura de Testes**: Suíte extensa de testes garantindo não-regressão, determinismo e reprodutibilidade.
6. **Build Reprodutível**: Configuração hatchling com normalização de permissões, timestamps e ordem de arquivos.

---

## 4. Weaknesses & Dívida Técnica (Fragilidades)

1. **Fragmentação de Registros**: Definições de agentes e skills espalhadas por múltiplos arquivos (`config/agents.yaml`, `config/subagents.yaml`, `config/agentic-expansion.yaml`, `config/teams-expansion.yaml`, `agents/*.md`, `skills/*`).
2. **Sincronização Manual de Plataformas**: A geração de espelhos para IDEs depende de scripts Python pontuais (`sync_skills.py`, `install_skills.py`) em vez de um compilador canônico com pipeline de exportação padronizado.
3. **Falta de Cascata Formal de Economia de Tokens**: Embora exista `knowledge/token-economy.md` e regras de budget, não há engine unificado que aplique a cascata de 7 tiers (Tier 0 Deterministic → Tier 1 Cache → Tier 2 Retrieval → Tier 3 Cheap → Tier 4 Specialist → Tier 5 Premium → Tier 6 Multi-Agent).
4. **Model Router Inicial**: Seleção de modelos baseada em regras simples em vez de avaliação multidimensional (complexidade × risco × capacidade × custo × privacidade).
5. **Ausência de Context Funnel Estruturado**: O empacotamento de contexto (`context_pack`) ainda é genérico e não implementa formalmente o funil de contexto e disclosure progressivo em níveis (A: Metadados, B: Instruções, C: Referências).
6. **Observabilidade Local Não-Centralizada**: Falta de storage padronizado para rastreamento completo de execuções (`run_id`, `span_id`, traces estruturados, SQLite/JSONL unificado).

---

## 5. Riscos

1. **Proliferação Desordenada de Agentes**: Manter agentes permanentes sem controle de ativação pode induzir custos desnecessários em plataformas que carregam perfis automaticamente.
2. **Quebra de Compatibilidade de Exportação**: Mudanças nas convenções do Cursor (`.mdc`), Claude Code (`.claude/`) ou Devin podem degradar a experiência se não houver golden tests dedicados para cada target.
3. **Overhead de Contexto**: Se descrições de ferramentas e skills ficarem muito extensas, consomem a janela de contexto antes mesmo da execução.

---

## 6. Baseline de Testes e Funcionalidades

- **Total de Testes**: contagem removida — o número publicado em `a5b9e96` está desatualizado (ver `docs/claims.lock.json`).
- **Tempo Médio de Execução da Suite Completa**: ~90-120 segundos
- **Compatibilidade Python**: piso mínimo e versões testadas declarados em `pyproject.toml` (`requires-python`).
- **Dependências de Produção Obrigatórias**: `PyYAML`, `jsonschema` (versões mínimas em `pyproject.toml`; zero dependência externa pesada).

---

## 7. Decisões Arquiteturais que Devem Ser Preservadas

- **D-1**: Manter camada determinística pura (Layer 0) com 0 chamadas de LLM para extração de fatos e avaliação de regras.
- **D-2**: Preservar schema canônico e imutável de `Finding` com lista obrigatória de `evidence` (`fact_id`).
- **D-3**: Preservar gates do caso (`sparkforge.case`) com trilha de override rastreável e assinatura de relatório.
- **D-4**: Preservar contratos de CLI existentes (`sparkforge analyze ...`, `sparkforge judge ...`, `sparkforge case ...`, `sparkforge report ...`) e MCP tools.
- **D-5**: Manter o princípio Local-First / Offline-First sem exigir infraestrutura cloud ou banco pago.
