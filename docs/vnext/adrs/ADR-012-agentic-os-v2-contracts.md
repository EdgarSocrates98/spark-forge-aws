# ADR-012 — Agentic OS v2: contratos locais, trust e economia observável

Status: accepted

Date: 2026-10-04

## Contexto

SparkForge já possui facts, rules, findings, case, blackboard, Decision Plane,
Context Gateway e traces SQLite. A evolução do prompt exige memória institucional,
trust entre fontes e agentes, métricas de contexto, economia reconciliada, routing
gated, checkpoints, interoperabilidade Forge/A2A e AgentOps. Essas áreas precisam
preservar o núcleo offline e não podem transformar ausência de transcript em token ou
ausência de benchmark em ganho.

## Decisão

Adicionar contratos Python puros e superfícies finas:

- `sparkforge_aws.agentic.memory` persiste records estruturados; evidência inválida vai
  para quarantine e retrieval padrão aceita apenas records aceitos/verificados.
- `sparkforge_aws.agentic.trust` separa trust, taint e `instruction_authority`; dados
  externos e handoffs entre agentes são `DATA_ONLY`.
- `sparkforge_aws.context.quality` calcula qualidade sobre itens declarados; bytes,
  tokens observados e custo são medidas independentes.
- `sparkforge_aws.economy.ledger` exige `cost_basis`; `model_router` começa em shadow e
  não chama provider.
- `SemanticCheckpoint` e `sparkforge_aws.protocols.forge` expõem envelopes serializáveis,
  content-addressed e sem blackboard interno.
- `sparkforge_aws.observability.agentops` lê traces locais e retorna `unresolved` para
  qualquer eixo sem evidência.
- CLI e MCP chamam as mesmas funções de `sparkforge_aws.adapters._core`; baseline save é
  mutação local idempotente e declarada no catálogo.

## Alternativas rejeitadas

- Reescrever kernel, Context Gateway ou Decision Plane: aumenta blast radius e impede
  atribuir causa a uma onda.
- Converter bytes em tokens por divisor: viola contrato de economia e fabrica precisão.
- Vector database obrigatório: quebra local-first e adiciona custo operacional.
- Active routing por scorecard: scorecard é evidência para avaliação, não autorização.
- Sanitizar removendo texto externo: destrói evidência; o envelope preserva conteúdo e
  marca taint/autoridade.

## Consequências

Positivas: contratos pequenos podem ser usados por CLI, MCP, testes e hosts sem SDK;
quarantine e unresolved tornam limites visíveis; commits por área permitem rollback;
retrieval, contexto e AgentOps passam a carregar evidência estruturada.

Negativas: persistência JSONL tem retrieval lexical local, sem semântica vetorial;
qualidade exige contrato de tarefa para recall; custo e tokens permanecem incompletos sem
transcript/preço; baseline save adiciona uma mutação local que precisa de anotação MCP.

## Validação e rollback

Validação: `tests/test_agentic_os_v2.py`, paridade declarada em `parity.yaml`,
`sparkforge-aws sdd check`, gates de referências/superfície/claims e suíte final.

Rollback: reverter commits das ondas agentic/economy/observability/adapters. Facts,
rules, findings, case, Decision Plane e traces legados permanecem no commit anterior.
