---
sdd: 1
feature: UPSTREAM_FACTS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Argumento `upstream` em `analyze pyspark` (CLI `--upstream` e tool): o documento sparkforge/upstream-facts/v1 é validado por `sparkforge/adapters/upstream.py` e seus facts entram no fim de `items`."
    tradeoffs:
      - "mesmo contrato nas duas superfícies (CLI e MCP tool), sem verbo novo"
      - "espelha `apiforge/upstream-facts/v1`: um fluxo de handoff só no ecossistema"
      - "o merge mora em `_core.analyze_pyspark`, que já é a porta do CLI e da tool"
  - id: B
    summary: "Verbo novo `ingest upstream` que grava os facts num arquivo consumível por `judge --facts`."
    tradeoffs:
      - "dois passos para o orquestrador em vez de um"
      - "move a superfície (verbo + tool) sem ganho: `--facts` já existe, mas aceitar evidência estrangeira ali lavaria a origem — um arquivo `--facts` é suposto ser saída de extrator nativo"
  - id: C
    summary: "O orquestrador traduz e injeta os facts no workspace como `.json` solto."
    tradeoffs:
      - "zero código aqui, e zero marcação: facts estrangeiros ficariam indistinguíveis de observação local — o defeito que `AF-UPSTREAM-UNMARKED` do API Forge recusa"
chosen: A
---

# UPSTREAM_FACTS — exploração

## Perfil

dev — mudança no repositório do SparkForge, não num job do operador.

## Problema

O The Forge quer encadear `forge-doctor-data` (observa um pipeline de dados) →
Spark Forge (analisa o código PySpark). Hoje `analyze pyspark` só lê os `*.py`
do workspace: o diagnóstico do Doctor chegaria como texto solto ou nada — sem
intake declarado, sem marcação de origem, sem limite.

## Abordagens

A abordagem A é a que o ecossistema já mediu: o API Forge recebe
`--upstream` + `apiforge/upstream-facts/v1` (PR #34) com identidade estrangeira
obrigatória, denylist de chaves imperativas e bounds. O documento aqui usa o
shape nativo de Fact (sete campos), com `id`/`kind`/`provenance.extractor` nos
namespaces que impedem lavagem — o equivalente local das mesmas três
propriedades.

## Conhecimento consultado

- `src/apiforge/application/analyze.py::_check_upstream` (repo api-forge):
  contrato de provenance `attrs.upstream` + `_FORBIDDEN_KEYS` iterativo.
- `sparkforge/findings/models.py::Fact`: shape nativo e a deriva de `id`
  (`f_<sha1>`), que o intake NÃO pode reaplicar.
- `sparkforge/adapters/_core.py::analyze_pyspark`: ponto de merge único usado
  por CLI e tool.
