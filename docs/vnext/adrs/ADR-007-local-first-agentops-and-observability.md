# ADR-007: Local-First Observability and AgentOps

## Status
Accepted

## Context
A maioria dos frameworks agênticos comerciais exige conexão com plataformas pagas de observabilidade na nuvem (SaaS), o que fere os princípios de privacidade de dados, portabilidade e capacidade offline do SparkForge.

## Decision
Adotamos uma infraestrutura de **Observabilidade Local-First**:
- Rastreamento unificado de execuções com identificadores `run_id` e `span_id`.
- Gravação de traces detalhados (task → routing → context → agent → model → tool → eval → result) em banco de dados SQLite local ou arquivos JSONL estruturados.
- Monitoramento de métricas essenciais: consumo de tokens de entrada/saída, custos estimados, tempos de resposta, tentativas (retries) e eficácia de cache.
- Integração opcional com OpenTelemetry / CloudWatch caso o usuário configure explicitamente, sem que isso seja dependência para o funcionamento local.

## Consequences
- **Positivas**: 100% privado, sem custos de infraestrutura adicionais e totalmente funcional offline.
- **Trade-offs**: Exige implementação própria de agregadores e consultas de métricas locais.
