# ADR-001: Canonical Factory Registry as Single Source of Truth

## Status
Accepted

## Context
Atualmente, definições de agentes, skills, subagentes e times estão fragmentadas em múltiplos formatos e locais (`config/agents.yaml`, `config/subagents.yaml`, `config/agentic-expansion.yaml`, `config/teams-expansion.yaml`, `agents/*.md`, `skills/*`). Isso gera risco de divergência entre plataformas (Antigravity, Cursor, Claude Code, Devin) e dificulta a validação programática e a evolução de schemas.

## Decision
Adotamos um **Registro Canônico Único** (`sparkforge/registry/`) baseado em modelos Pydantic e esquemas JSON estritos para todas as entidades da factory:
- `AgentManifest`
- `SkillManifest`
- `ToolManifest`
- `TeamManifest`
- `WorkflowManifest`
- `PolicyManifest`
- `KnowledgeManifest`
- `EvalManifest`

Nenhum artefato específico de IDE ou plataforma deve ser editado manualmente; todos os artefatos de exportação serão gerados deterministicamente a partir do registro canônico.

## Consequences
- **Positivas**: Fonte única de verdade, validação estrita em tempo de compilação/teste, eliminação de duplicações, facilidade de auditoria.
- **Trade-offs**: Requer etapa de sincronização/exportação antes da distribuição para novas plataformas.
