---
sdd: 1
feature: FORGE_LAB_PRODUCT
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_PRODUCT/define.md
  sha256: "acf2bbebe59812db106f11646d248d37b2f83888fac10434dd2c5e8d1d481da0"
files:
  - {path: sparkforge_aws/lab/contract.py, action: create, reason: "Registry, fidelidade, profiles, modes, scenario DSL e validação canônica."}
  - {path: sparkforge_aws/lab/scenario.py, action: create, reason: "Compilador de cenário para actions reutilizáveis."}
  - {path: sparkforge_aws/lab/generators.py, action: create, reason: "Dataset generator determinístico com seed, skew, late events e duplicidade."}
  - {path: sparkforge_aws/lab/workload.py, action: create, reason: "Workload generator separado do dataset."}
  - {path: sparkforge_aws/lab/faults.py, action: create, reason: "Fault plan para Toxiproxy, processo, compute, application e data."}
  - {path: sparkforge_aws/lab/runtime.py, action: create, reason: "Planos comuns de Compose/Testcontainers e guardas de execução."}
  - {path: sparkforge_aws/lab/doctor.py, action: create, reason: "Diagnóstico local de Docker, recursos, arquitetura, portas e imagens sem iniciar serviços."}
  - {path: sparkforge_aws/lab/evidence.py, action: create, reason: "Run directory, artifact capture, receipt, oracle, compare e promoção."}
  - {path: sparkforge_aws/lab/compatibility.py, action: create, reason: "Matriz multi-engine, equivalência e perfis Polaris sem alegar resultado não medido."}
  - {path: sparkforge_aws/lab/aws.py, action: create, reason: "Contrato L3, TTL, budget, tags, prefixo e recusa default de mutações AWS."}
  - {path: sparkforge_aws/lab/cli.py, action: create, reason: "Handlers CLI-first para o ciclo operacional do Lab."}
  - {path: sparkforge_aws/lab/__init__.py, action: modify, reason: "Exportar API de produto Lab."}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "Registrar comando top-level lab sem ampliar MCP por padrão."}
  - {path: labs/forge-lab/lab.yaml, action: modify, reason: "Manifesto com registry, tiers, profiles, Golden 20 e contrato de evidência."}
  - {path: labs/forge-lab/compose.yaml, action: modify, reason: "Profiles compartilhados, nomes de projeto e imagens externalizadas/pinadas."}
  - {path: lab/versions.yaml, action: create, reason: "Fonte única de versões, images, digests e compatibilidade."}
  - {path: lab/scenarios/, action: create, reason: "Golden 20 declarativo, oracle e experiment plan por cenário."}
  - {path: lab/compose/, action: create, reason: "Fragments documentais para stacks e observability."}
  - {path: lab/generators/, action: create, reason: "Schemas canônicos e geradores reproduzíveis."}
  - {path: lab/probes/, action: create, reason: "Contrato machine-readable de probes, não screenshots."}
  - {path: lab/contracts/, action: create, reason: "Schemas de scenario, receipt, run e oracle."}
  - {path: tests/test_forge_lab_product.py, action: create, reason: "Cobertura de contrato, DSL, plans, evidence e guardas; executada ao final."}
  - {path: docs/knowledge/forge-lab-product.md, action: create, reason: "Documentação operacional completa e limites de fidelidade."}
decisions:
  - id: D1
    choice: "Um registry e um scenario DSL são a fonte para Compose, Testcontainers, CI e receipts."
    rejected: ["versões duplicadas por Dockerfile/CI/docs", "scripts shell independentes"]
    rollback: "git revert dos commits de registry/DSL; manifest anterior continua analisável."
  - id: D2
    choice: "CLI-first, offline plan por default, mutação somente com --execute --confirm."
    rejected: ["MCP por action", "subir Docker automaticamente durante analyze"]
    rollback: "remover registro top-level lab e manter analyze forge-lab read-only."
  - id: D3
    choice: "Expected oracle é declarativo e independente do output do Forge."
    rejected: ["gerar expected a partir do actual", "assertar números voláteis"]
    rollback: "desabilitar promoção de fixture até oracle externo ser revisado."
  - id: D4
    choice: "L3 AWS exige opt-in explícito, budget, TTL, região, prefixo e tags; default é recusa."
    rejected: ["reutilizar conta por conveniência", "janitor destrutivo sem filtro"]
    rollback: "manter apenas contrato AWS e nenhum cliente AWS no núcleo offline."
covers:
  - {part: "foundation and runtime", acceptance: [AC1, AC3, AC5]}
  - {part: "scenario, generators and faults", acceptance: [AC2, AC3]}
  - {part: "evidence, oracle and compatibility", acceptance: [AC4]}
  - {part: "CLI and documentation", acceptance: [AC5]}
---

# FORGE_LAB_PRODUCT — desenho

O runtime compila um manifesto em ações, e não em shell arbitrário. Backends
Compose e Testcontainers recebem o mesmo `ActionPlan`. Capture só aceita paths
dentro do run; receipts possuem fingerprint do conteúdo; oracle não usa analyzer
para criar expectativas. A integração com `analyze`/`judge` é por artifacts
exportados e nunca por importação de um provider.
