# ADR-004: Context Funnel and Progressive Knowledge Disclosure

## Status
Accepted

## Context
Enviar documentação técnica extensa ou árvores completas de arquivos em prompts sobrecarrega a janela de contexto, aumenta custos e induz alucinações.

## Decision
Adotamos o **Context Funnel** e o modelo de **Progressive Disclosure** em 3 níveis:
- **Funil de Contexto**: `Repositório` → `Arquivos Candidatos` → `Trechos Relevantes (Chunks)` → `Evidências Desduplicadas` → `Contexto Mínimo`.
- **Níveis de Conhecimento**:
  - **Level A (Metadados)**: Nome, tags, triggers e anti-triggers (~20-50 tokens) para seleção rápida.
  - **Level B (Instruções da Skill)**: Procedimentos práticos carregados apenas quando a skill é ativada.
  - **Level C (Referências)**: Documentação técnica extensa, matrizes e patterns recuperados sob demanda.

Bancos vetoriais pesados não são obrigatórios; índices locais, FTS e busca estruturada por grafos são prioritários.

## Consequences
- **Positivas**: Prompts leves, bootstrap rápido e consumo mínimo de tokens.
- **Trade-offs**: Exige indexação local precisa e manutenção de metadados concisos.
