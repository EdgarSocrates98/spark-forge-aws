# ADR-003: Token Economy Engine and Capability-Based Model Routing

## Status
Accepted

## Context
O uso indiscriminado de LLMs caros ou múltiplos agentes para tarefas simples ou determinísticas gera desperdício financeiro e latência sem ganho de qualidade. O princípio fundamental do projeto é "Resultado Correto por Token Consumido".

## Decision
Adotamos uma cascata de execução rigorosa em 7 Tiers:
- **Tier 0**: Determinístico (0 chamadas LLM)
- **Tier 1**: Cache de resultados verificados por hash
- **Tier 2**: Retrieval de contexto mínimo
- **Tier 3**: Inferência econômica / modelo local
- **Tier 4**: Modelo especialista com injeção de skill
- **Tier 5**: Raciocínio premium sob alta complexidade/risco
- **Tier 6**: Decomposição multi-agente apenas sob ganho comprovado

Adicionalmente, implementamos um `ModelRouter` desacoplado que seleciona a rota com base em capacidade (`complexidade × risco × capacidade × budget × privacidade`), perfis de execução (`ECO` como padrão, `BALANCED`, `QUALITY`, `OFFLINE`, `STRICT`) e detecção automática de desperdício (`sparkforge optimize`).

## Consequences
- **Positivas**: Redução drástica de custos em tarefas determinísticas e simples; previsibilidade orçamentária; controle fino de execução.
- **Trade-offs**: Exige orquestração cuidadosa de orçamentos e fallback gracioso.
