---
sdd: 1
feature: AGENTIC_ECONOMY_COMPLETION
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Unir fragments estáticos e live por bridges declaradas, cachear descriptors por assinatura de filesystem e separar execução MCP por intenção reduz reprocessamento e ambiguidade de autorização sem inferir relações ou misturar superfícies."
  prediction: "A composição preserva nós, arestas, provenance e unresolved dos dois lados; chamadas repetidas de descriptors não leem corpos inalterados; execute_read aceita somente capabilities read-only e execute_mutation aceita somente capabilities mutáveis; a suíte monolítica termina com exit 0."
  experiment: "Rodar os testes de contrato novos, os gates de surface/benchmark e python -m pytest -q em um TEMP externo ao repositório."
acceptance:
  - id: AC1
    statement: "O workspace compõe SemanticGraph e artefato live Glue/Lake Formation/S3 em um FederatedGraph usando apenas bridges explícitas, preservando cross-account, provenance e unresolved."
    verified_by: {kind: test, ref: "tests/test_workspace_federation.py::test_static_and_live_graph_compose_with_explicit_bridge"}
  - id: AC2
    statement: "PackRegistry reutiliza descriptors quando a assinatura de arquivos não mudou e invalida o cache quando um arquivo muda, sem alterar source_hash."
    verified_by: {kind: test, ref: "tests/test_knowledge_compiler.py::test_descriptors_reuse_unchanged_manifest_without_reading_pack_bodies"}
  - id: AC3
    statement: "A superfície compacta publica execute_read e execute_mutation com políticas distintas, rejeitando capability incompatível antes do dispatcher."
    verified_by: {kind: test, ref: "tests/test_adapters_mcp_compact.py::test_compact_catalog_splits_read_and_mutation_execution"}
  - id: AC4
    statement: "A suíte monolítica completa termina com exit 0 e preserva os gates de superfície e benchmark."
    verified_by: {kind: command, ref: "python -m pytest -q"}
success:
  - id: SC1
    metric: "Nós, arestas, provenance e unresolved do FederatedGraph composto"
    source: "tests/test_workspace_federation.py::test_static_and_live_graph_compose_with_explicit_bridge"
  - id: SC2
    metric: "Leituras de corpos de pack no segundo descriptors() sem mudança de assinatura"
    source: "tests/test_knowledge_compiler.py::test_descriptors_reuse_unchanged_manifest_without_reading_pack_bodies"
  - id: SC3
    metric: "Contagem, nomes e annotations da superfície compacta"
    source: "python scripts/check_surface_lock.py e tests/test_adapters_mcp_compact.py"
  - id: SC4
    metric: "Exit code da suíte monolítica"
    source: "python -m pytest -q"
out_of_scope:
  - "Inferência de bridges por nome, label ou prefixo entre graph sources."
  - "Descoberta AWS fora de cloud_resources declarados ou mutação AWS."
  - "Score composto de qualidade, bytes, tokens ou custo."
  - "Execução live no CI; o CI usa clientes stubados para o grafo e executa a suíte offline."
unknowns: []
change_kinds: [tool_or_verb, claims]
---

# AGENTIC_ECONOMY_COMPLETION — requisitos

## Problema

O grafo estático e o artefato live já existem em fronteiras separadas, mas não
há um compositor público que receba ambos e uma lista de bridges verificáveis.
`PackRegistry.descriptors()` relê todos os corpos em cada chamada. A superfície
compacta ainda expõe um executor único, embora a autorização precise distinguir
leitura de mutação. A suíte completa ainda não tem um resultado final registrado.

## Restrições

- Nenhuma relação cross-source é inferida; toda bridge vem da declaração do chamador.
- O cache de descriptors só é válido enquanto a assinatura de caminhos/tamanho/mtime permanecer igual.
- `execute_read` e `execute_mutation` validam a annotation da capability antes do dispatcher existente.
- O teste monolítico roda com TEMP/cache fora do workspace quando o host negar o TEMP padrão.
