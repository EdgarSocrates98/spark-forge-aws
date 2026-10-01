# ADR-002: Multi-Platform Adapter and Compiler Architecture

## Status
Accepted

## Context
Diferentes ferramentas de desenvolvimento (Antigravity, Cursor, Claude Code, Devin, Windsurf, Copilot) utilizam convenções distintas para agentes, regras e skills (ex: `.cursor/rules/*.mdc`, `.claude/agents/*.md`, `.agents/skills/*`). Criar e manter essas configurações manualmente em paralelo é insustentável e sujeito a erros.

## Decision
Implementar um compilador de plataforma modular (`sparkforge/adapters/platforms/` e comando `sparkforge export --target <target>`) que lê o registro canônico e gera os artefatos específicos de cada target com cabeçalhos claros indicando origem gerada (`GENERATED FROM CANONICAL SOURCE`). Cada target possuirá suíte de testes de fixture/golden para evitar quebras silenciosas em atualizações.

## Consequences
- **Positivas**: Portabilidade total sem duplicação de esforço; novos targets de IDE podem ser adicionados implementando uma classe abstrata `BasePlatformExporter`.
- **Trade-offs**: Arquivos gerados precisam de verificação de não-derivação no CI (`sparkforge export --verify`).
