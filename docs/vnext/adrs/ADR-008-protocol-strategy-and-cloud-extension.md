# ADR-008: Protocol Strategy and Optional Cloud Remote Worker

## Status
Accepted

## Context
O suporte a protocolos de agentes (MCP, A2A, ACP) e a execução de tarefas pesadas (benchmarks longos, evals exaustivas) precisam ser equilibrados sem inflar as dependências essenciais do pacote base.

## Decision
- **Protocolos**: O Model Context Protocol (MCP) permanece como protocolo prioritário para interação Agent ↔ Ferramenta/Contexto. Interfaces abstratas para Agent-to-Agent (A2A) e Agent-Client (ACP) serão desenhadas como pontos de extensão sem impor dependências pesadas de bibliotecas de terceiros no core.
- **Execução Cloud Opcional**: O core da factory opera localmente. Criamos uma camada de abstração de **Remote Worker** com arquitetura Serverless (AWS Lambda, ECS Fargate, AWS Batch com Spot) sob demanda e scale-to-zero para benchmarks pesados, ativada exclusivamente via configuração explícita do usuário.

## Consequences
- **Positivas**: Núcleo leve e independente de rede; capacidade de escala em nuvem sob demanda sem custos fixos contínuos.
- **Trade-offs**: Abstração de execução local vs remota deve manter paridade de comportamento e contratos de segurança.
