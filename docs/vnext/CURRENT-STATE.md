# SparkForge AWS — Current State Assessment (baseline + current overlay)

## 1. Arquitetura Atual

O SparkForge AWS é uma plataforma de engenharia de desempenho e qualidade para cargas de dados PySpark na AWS (Glue, EMR EC2, EMR Serverless, Athena, Iceberg, S3).
Este documento preserva o snapshot inicial para contexto histórico e fecha-o com o
overlay corrente. O núcleo continua determinístico; Agentic OS v2 adiciona contratos
locais, inspeção econômica e observabilidade sem provider SDK ou mutação AWS implícita.

```
[ Artifacts no Disco / S3 / Dumps ]
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge_aws.facts (Extratores)         │ ──> Fact Kinds Determinísticos
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge_aws.rules (Motor AST Seguro)   │ <── rules/catalog/*.yaml (Catálogos)
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge_aws.findings (Modelos/Sign)    │ ──> Findings com Evidência Ancorada
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge_aws.case (Ciclo de Vida)       │ ──> Gates, Overrides, Playbook, Router
└────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  sparkforge_aws.adapters (CLI / MCP)       │ ──> Consoles, IDEs, Claude, Devin, MCP
└────────────────────────────────────────┘
```

### Componentes Principais

1. **`sparkforge_aws.facts`**: extratores offline (AST de PySpark, physical plans formatados, JSONL Spark event logs, Iceberg metadata dumps, Glue Data Catalog, Terraform HCL, SQL literals, Athena workgroups, EMR clusters, EMR Serverless, Data Quality checks, Graph/GraphFrames, Call Graphs, S3 listings, Table consumers, Terraform diffs, Benchmarks, Functional validation, Runtime detection, Fusion).
2. **`sparkforge_aws.rules`**: Motor de avaliação seguro em Python AST sem `eval()`, com suporte a operadores tipados e escopos de versão (Glue e EMR).
3. **`sparkforge_aws.findings`**: Estrutura imutável e assinável de achados técnicos com rastreabilidade obrigatória de `fact_id` e `rule_id`.
4. **`sparkforge_aws.case`**: Gerenciador durável de casos de investigação com 4 gates (`baseline_captured`, `flows_mapped`, `functional_validation_defined`, `dominant_bottleneck_identified`) com bloqueio fail-closed e trilha de override auditada.
5. **`sparkforge_aws.agents`**: Supervisores, políticas de modelo, observabilidade básica e controle de autonomia.
6. **`sparkforge_aws.adapters`**: Interface CLI (`sparkforge-aws`, `sparkforge-aws-tools`) e servidor MCP (`sparkforge_aws/adapters/mcp.py`).

---

## 2. Inventário de Recursos

| Categoria | Quantidade | Localização | Descrição |
|---|---|---|---|
| **Agents** | Perfis canônicos de coordenadores e executores | `agents/*.md`, `agents/executors/*.md` | Agentes especialistas e executores determinísticos de fase; lista viva em `agents/` |
| **Skills** | Diretório canônico | `skills/*/SKILL.md` | Habilidades especializadas; contagem viva verificada por `scripts/sync_skills.py` |
| **Subagents** | 0 | — (o registro e os contratos saíram em `docs/sdd/CONFIG_OCA/`) | Não há mais contrato efêmero: nenhum módulo de `sparkforge_aws/`, `scripts/` ou `tests/` os lia |
| **Teams** | 1 | `config/teams-expansion.yaml` | Composições de times (governance-security) |
| **Extratores de Fatos** | — | `sparkforge_aws/facts/*.py` | Fatos determinísticos extraídos localmente |
| **Catálogos de Regras** | — | `rules/catalog/*.yaml` | Regras estruturadas com condições, severidade e ações |
| **Knowledge Base** | — | `knowledge/**/*.md`, `knowledge/**/*.json` | Guias de arquitetura, runtimes, anti-patterns, lockfiles |
| **Testes Automatizados** | — | `tests/test_*.py` | Cobertura unitária, contratos, golden cases e paridade |
| **Adapters / Mirrors** | Mirrors declarados | `.agents/`, `.claude/`, `.github/`, `manifest.json` | Configurações canônicas e instruções geradas para plataformas suportadas |

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

1. **Fragmentação de Registros**: Definições de agentes e skills espalhadas por múltiplos arquivos (`config/agents.yaml`, `config/agentic-expansion.yaml`, `config/teams-expansion.yaml`, `agents/*.md`, `skills/*`).
2. **Sincronização Manual de Plataformas**: A geração de espelhos para IDEs depende de scripts Python pontuais (`sync_skills.py`, `install_skills.py`) em vez de um compilador canônico com pipeline de exportação padronizado.
3. **Economia de provider ainda incompleta**: `TokenLedger` reconcilia estimated/observed e `cost_basis` é obrigatório; não há conversão bytes→tokens, preço implícito ou medição live sem transcript/preço.
4. **Model Router deliberadamente gated**: `AdaptiveModelRouter` ranqueia candidatos declarados e começa em `shadow`; `active` exige autoridade e evidência de promoção, sem chamada de provider no core.
5. **Contexto com contrato, não promessa**: `ContextQualityReport`, Gateway e planner implementam qualidade, disclosure e minimum sufficient context; recall exige evidência declarada e tokens ausentes permanecem `tokens_unresolved`.
6. **Observabilidade local disponível, live ainda limitada**: AgentOps oferece `inspect`, `compare` e `baseline` sobre traces locais; transcript, preço e qualidade externa continuam `unresolved`.

---

## 5. Riscos

1. **Proliferação Desordenada de Agentes**: Manter agentes permanentes sem controle de ativação pode induzir custos desnecessários em plataformas que carregam perfis automaticamente.
2. **Quebra de Compatibilidade de Exportação**: Mudanças nas convenções do Cursor (`.mdc`), Claude Code (`.claude/`) ou Devin podem degradar a experiência se não houver golden tests dedicados para cada target.
3. **Overhead de Contexto**: Se descrições de ferramentas e skills ficarem muito extensas, consomem a janela de contexto antes mesmo da execução.

---

## 6. Baseline de Testes e Funcionalidades

- **Total de Testes**: contagem removida — o número publicado em `a5b9e96` está desatualizado (ver `docs/claims.lock.json`).
- **Tempo da Suite Completa**: não é SLA e não fica fixado neste documento; a validação
  reexecutável e seu resultado ficam registrados no SDD da entrega.
- **Compatibilidade Python**: piso mínimo e versões testadas declarados em `pyproject.toml` (`requires-python`).
- **Dependências de Produção Obrigatórias**: `PyYAML`, `jsonschema` (versões mínimas em `pyproject.toml`; zero dependência externa pesada).

---

## 7. Decisões Arquiteturais que Devem Ser Preservadas

- **D-1**: Manter camada determinística pura (Layer 0) com 0 chamadas de LLM para extração de fatos e avaliação de regras.
- **D-2**: Preservar schema canônico e imutável de `Finding` com lista obrigatória de `evidence` (`fact_id`).
- **D-3**: Preservar gates do caso (`sparkforge_aws.case`) com trilha de override rastreável e assinatura de relatório.
- **D-4**: Preservar contratos de CLI existentes (`sparkforge-aws analyze ...`, `sparkforge-aws judge ...`, `sparkforge-aws case ...`, `sparkforge-aws report ...`) e MCP tools.
- **D-5**: Manter o princípio Local-First / Offline-First sem exigir infraestrutura cloud ou banco pago.
- **D-6**: Manter trust, taint, autoridade de instrução, `unresolved`, `cost_basis` e
  evidência de promoção como contratos independentes; nenhum scorecard concede autoridade sozinho.

## 8. Overlay atual — Agentic OS v2

As seções anteriores preservam o snapshot da auditoria inicial. Para o estado do
repositório após `AGENTIC_ENGINEERING_OS_V2`, leia este overlay:

- Memória institucional agora tem `DecisionMemoryRecord`, quarantine, trust,
  outcome, freshness, invalidação e retrieval híbrido local. Records antigos continuam
  legíveis, mas não entram no retrieval confiável sem evidência.
- Trust/taint e autoridade de instrução são campos distintos. `TrustEnvelope`,
  `RoleContextPlan` e os handoffs Forge/A2A preservam origem, escopo e
  `DATA_ONLY` para dados externos e mensagens entre agentes.
- Contexto tem `ContextQualityReport` e benchmark de minimum sufficient context. O
  relatório separa bytes serializados de tokens observados e deixa métricas sem
  transcript como `tokens_unresolved`.
- Economia tem `TokenLedger`, reconciliação estimated/observed e `cost_basis` obrigatório.
  `AdaptiveModelRouter` é independente do roteamento de caso e permanece shadow por
  default; active exige autoridade e evidência de promoção.
- Checkpoints semânticos são content-addressed. `sparkforge_aws.protocols.forge` publica
  envelopes mínimos de task, capability, evidence, handoff, result e health.
- AgentOps lê o SQLite de traces e oferece inspect, compare e baseline local. Waste é
  classificado como observado ou hipótese; ausência de provider transcript, contrato de
  qualidade ou preço efetivo permanece unresolved.
- CLI e MCP compartilham `_core` para `context inspect`, `agentops
  inspect|compare|baseline` e `doctor agentic`. Baseline save grava somente arquivo
  local e é a única mutação desta superfície.

Pendências deliberadas: evals live de provider, preço atual sem fonte efetiva, promoção
active automática, vector database obrigatório e execução AWS. A suíte final e os gates
de superfície/claims são a validação de entrega; nenhum ganho financeiro é inferido por
bytes ou por scorecard.
