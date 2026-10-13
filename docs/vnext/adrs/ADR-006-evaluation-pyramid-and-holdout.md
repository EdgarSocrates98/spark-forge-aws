# ADR-006: Multi-Tier Evaluation Pyramid and Holdout Datasets

## Status
Accepted

## Context
Avaliar agentes e ferramentas apenas por inspeção visual ("parece funcionar") resulta em regressões silenciosas, falhas de roteamento e desperdício de tokens.

## Decision
Construir uma pirâmide abrangente de avaliação executável:
1. **Unit Tests**: Testes rápidos de lógica de extração e regras determinísticas.
2. **Contract Tests**: Validação de schemas Pydantic e JSON Schema dos manifests.
3. **Golden Cases**: Casos com entradas e saídas esperadas bem conhecidas.
4. **BDD Scenarios**: Cenários de usuário no formato `Given/When/Then`.
5. **Holdout Evaluations**: Conjuntos de dados mantidos estritamente isolados do contexto e prompts dos agentes para medir capacidade real de generalização.
6. **Security Evals**: Testes de injeção de prompt, redação de credenciais e integridade de gates de mutação.
7. **Economy Evals**: Medição formal de consumo mediano de tokens, taxa de escalonamento e custo por tarefa resolvida.

## Consequences
- **Positivas**: Confiança matemática na evolução da plataforma e mensuração objetiva de melhorias de economia.
- **Trade-offs**: Maior tempo de execução de suites completas de avaliação.
