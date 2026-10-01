# ADR-005: Intentional and Scoped Agentic Memory

## Status
Accepted

## Context
Despejar históricos de conversa inteiros em novos prompts consome tokens excessivos e introduz ruído e informações desatualizadas.

## Decision
Adotamos um modelo de memória intencional categorizado em:
- **Working Memory**: Estado efêmero da tarefa em andamento.
- **Episodic Memory**: Registros de execuções anteriores, benchmarks e investigações passadas.
- **Semantic Memory**: Fatos, regras e entidades comprovadas, com TTL, nível de confiança e invalidação automática em caso de mutação nos artefatos.
- **Procedural Memory**: Blueprints e receitas de solução de problemas.

Toda memória persistida deve possuir metadados de procedência (`provenance`, `timestamp`, `hash`), evitando que saídas antigas de LLM sejam tratadas como fatos imutáveis.

## Consequences
- **Positivas**: Memória limpa, auditável e resistente a informações obsoletas.
- **Trade-offs**: Requer lógica de invalidação e controle de expiração (TTL).
