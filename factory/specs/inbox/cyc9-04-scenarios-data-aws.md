---
id: cyc9-04
title: scenarios-data-engineering-aws
status: inbox
created: 2026-10-15
owner: spark-forge-aws
scope: repo
cycle: 9
wave: 3
priority: p1
risk: medium
agent: codex
source: prompt_evo_cycles.md §9.3 Data Engineering AWS
verification:
  - python -m pytest
  - sparkforge-aws sdd check --repo . --feature <feature>
  # + gates por mudança em docs/gates-por-mudanca.md
---

# Cenários Forge Lab — Data Engineering AWS

## Outcome

Biblioteca versionada de cenários do domínio Spark/Glue AWS com fixtures locais e ground truth: diagnóstico de job Glue, plano físico Spark, revisão PySpark, evolução Iceberg, Lake Formation, qualidade de dados, performance de leitura/escrita.

## Grill gate

- Problema observado: capacidades do especialista não têm cenários mensuráveis para provar precisão/tempo/cobertura.
- Usuário afetado: Benchmark Engineer e usuário avaliando o especialista.
- Falha concreta: claims de qualidade sem dataset verificável.
- Decisão: cenários do §9.3 AWS como fixtures sintéticos + diagnósticos classificados, limitados às capacidades suportadas.
- Fora de escopo: acesso a AWS real como requisito; centralizar motor de benchmark no the-forge (o cenário roda no motor local).
- Critério de parada: ao menos um cenário por categoria suportada, executável localmente e integrável ao harness federado.

## Acceptance

- Cenários versionados por categoria: job Glue lento, plano físico, revisão PySpark, evolução Iceberg, Lake Formation, qualidade de dados, leitura/escrita.
- Cada cenário: fixture + entrada + resultado esperado + diagnóstico classificado (ground truth).
- Execução local sem credenciais; saída compatível com contrato de métricas (cyc9-02).
- Categorias não suportadas hoje são registradas como `not_available`, não simuladas.

## Constraints

- Independência: roda sem the-forge/CLI/Portal.
- Sem credenciais AWS em fixtures.

## Verificação

- Confirmar no dispatch: `python -m pytest` / gates do repo.

## Pending

- ⚠ Quais capacidades efetivamente implementadas (levantar na baseline cyc0-01).
