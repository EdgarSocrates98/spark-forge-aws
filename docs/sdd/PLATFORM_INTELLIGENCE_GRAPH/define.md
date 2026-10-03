---
sdd: 1
feature: PLATFORM_INTELLIGENCE_GRAPH
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_GRAPH/explore.md
  sha256: "cbc86d352370f86a7f464e60b7967e61e5636be959f441ab31f5a2abe1198f96"
hypothesis:
  claim: "Um contrato determinístico de grafo de plataforma, composto sobre as primitivas federadas atuais, dá ao Spark Forge uma base única para lineage e análise de impacto."
  prediction: "Dado um manifesto com entidades e arestas explícitas, a análise retorna nós, arestas, proveniência, pontos cegos e blast radius transitivo de forma estável; se faltar endpoint ou evidência, o vínculo é unresolved em vez de ser inferido."
  experiment: "Carregar manifesto JSON/YAML sintético por CLI e MCP, executar impacto downstream/upstream/both com limite de profundidade e comparar saída canônica e fingerprint."
acceptance:
  - id: AC1
    statement: "O analisador carrega contrato de plataforma, valida entidades e arestas, preserva proveniência e retorna fingerprint determinístico."
    verified_by: {kind: test, ref: "tests/test_platform_graph.py::test_platform_graph_loads_and_fingerprints_deterministically"}
  - id: AC2
    statement: "O impacto percorre somente arestas explícitas, retorna caminhos diretos e transitivos e registra endpoint ausente ou atributo desconhecido como unresolved."
    verified_by: {kind: test, ref: "tests/test_platform_graph.py::test_platform_graph_impact_preserves_paths_and_unresolved"}
  - id: AC3
    statement: "A CLI e a ferramenta MCP usam o mesmo núcleo e expõem o contrato estruturado de grafo e impacto."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli analyze platform-graph --path fixtures/platform/graph.yaml --changed-node postgres.orders --direction downstream"}
success:
  - id: SC1
    metric: "Fingerprint e ordenação idênticos para o mesmo manifesto carregado em JSON e YAML equivalente"
    source: "saída de analyze platform-graph e teste determinístico do analisador"
  - id: SC2
    metric: "Todos os endpoints ausentes e atributos não observáveis aparecem em unresolved"
    source: "campo unresolved da saída de analyze platform-graph"
out_of_scope:
  - "Conectores que consultam AWS, Kafka, Flink, dbt, Airflow ou catálogos ao vivo."
  - "Inferência de lineage por nome, heurística de SQL ou descoberta implícita de owner/SLO."
  - "Benchmark de precisão/recall ou alegação de ganho de performance nesta fase."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Regenerar o surface lock e a referência MCP depois de registrar a nova operação."
case_id: null
change_kinds: [extractor, tool_or_verb]
---

# PLATFORM_INTELLIGENCE_GRAPH — requisitos

## Problema

Os grafos atuais compõem repositórios e artefatos, mas não oferecem um contrato
único para a topologia de uma plataforma de dados nem uma resposta auditável de
blast radius por mudança de dataset, contrato ou esquema.

## Critérios

O grafo deve aceitar entidades de plataforma (`dataset`, `job`, `run`, `consumer`,
`producer`, `contract`, `owner`, `slo`, `dependency`, `schema`, `dashboard`,
`metric`, `model`, `service`, `topic`, `stream`, `catalog`), relações declaradas,
evidências, proveniência, freshness e unresolved. Nenhuma aresta é criada por
similaridade de rótulo.

## Segurança operacional

O analisador é offline/read-only. Artefatos de produção e dados sensíveis não
entram no repositório; o fixture é sintético. O limite de nós, arestas, caminhos e
profundidade é obrigatório para impedir expansão não controlada.
