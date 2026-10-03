---
sdd: 1
feature: FORGE_LAB_DIGITAL_TWIN
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_DIGITAL_TWIN/define.md
  sha256: "64d91ea569a716657c45cfa28e09c10816bdf16bc2130a1de29315d9268a925e"
files:
  - {path: sparkforge/lab/__init__.py, action: create, reason: "API do contrato offline do Forge Lab."}
  - {path: sparkforge/lab/spec.py, action: create, reason: "Loader, validação e descrição determinística da topologia."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Núcleo compartilhado do analisador Forge Lab."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Verbo analyze forge-lab."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Tool MCP read-only com contrato estruturado."}
  - {path: parity.yaml, action: modify, reason: "Registro de paridade do analisador Forge Lab."}
  - {path: labs/forge-lab/lab.yaml, action: create, reason: "Topologia e cenários versionados."}
  - {path: labs/forge-lab/compose.yaml, action: create, reason: "Blueprint de serviços por profile, com imagens configuráveis."}
  - {path: labs/forge-lab/README.md, action: create, reason: "Procedimento de uso, limites e segurança."}
  - {path: tests/test_forge_lab.py, action: create, reason: "Casos de topologia e não execução."}
  - {path: docs/knowledge/forge-lab-digital-twin.md, action: create, reason: "Conhecimento operacional do laboratório."}
decisions:
  - id: D1
    choice: "Compose declarativo com imagens parametrizadas por ambiente e profiles por subsistema."
    rejected: ["instalar dependências no host", "hardcode de tags externas não verificado nesta fase"]
    rollback: "git revert do commit do blueprint; remover a pasta labs/forge-lab."
  - id: D2
    choice: "Failure injection como catálogo de ações e evidências esperadas, não como mutação automática."
    rejected: ["CLI matar containers", "alterar dados de teste sem confirmação"]
    rollback: "git revert do commit do analisador; nenhum estado externo foi alterado."
covers:
  - {part: "lab spec", acceptance: [AC1]}
  - {part: "offline analysis", acceptance: [AC2]}
---

# FORGE_LAB_DIGITAL_TWIN — desenho

```text
lab.yaml + compose.yaml
          |
          v
load/validate/describe (offline)
          |
          +--> topology order + unresolved
          +--> scenario catalog + expected evidence
          +--> CLI / MCP read-only
```

Compose não é executado pelo analisador. Cada cenário explicita alvo, ação,
risco e observações esperadas para posterior execução humana ou por harness
separado.
