---
sdd: 1
feature: TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Uma avaliacao ampla que mede qualidade por eixo ao lado de payload bytes e usage do transcript, somada a um coletor de grafo AWS por recursos declarados, fecha os tres gaps sem transformar estimativa em medida ou ausencia em evidencia."
  prediction: "A suite ampliada produz uma matriz por caso e perfil com status, evidence recall, false-positive rate, unresolved, execution plan e payload_bytes; transcripts validos resolvem provider tokens; custo so resolve com cost_basis; o grafo live produz nos e arestas de Glue, Lake Formation e S3 e registra lacunas nomeadas para acesso negado, truncamento e cross-account sem role explicito."
  experiment: "Rodar a suite deterministica ampliada e seu comparador, pontuar transcripts fixture com tokens, calcular custo com uma tabela de precos declarada, e executar o coletor live contra clientes AWS stubados usando um manifesto com recursos locais e cross-account."
acceptance:
  - id: AC1
    statement: "A suite token-efficient contem pelo menos doze casos de qualidade com eixos declarados e ids unicos, cobrindo resposta, evidencia, findings, unresolved e plano."
    verified_by: {kind: test, ref: "tests/test_token_efficient_benchmark.py::test_suite_ampla_tem_eixos_e_casos_unicos"}
  - id: AC2
    statement: "O runner grava uma matriz caso x perfil com payload_bytes separado de provider_tokens e com as metricas de qualidade sem nota composta."
    verified_by: {kind: test, ref: "tests/test_token_efficient_benchmark.py::test_matriz_preserva_eixos_e_bytes_separados"}
  - id: AC3
    statement: "A comparacao entre duas matrizes recusa suites diferentes e publica deltas por eixo e por perfil sem somar bytes a tokens."
    verified_by: {kind: test, ref: "tests/test_token_efficient_benchmark.py::test_compare_matriz_por_eixo_sem_score_composto"}
  - id: AC4
    statement: "O relatorio de provider usage resolve input, output e cache tokens somente de transcript valido e calcula custo somente quando a tabela de precos traz cost_basis explicito."
    verified_by: {kind: test, ref: "tests/test_provider_economy.py::test_provider_cost_requires_cost_basis_and_keeps_token_units"}
  - id: AC5
    statement: "O manifesto de workspace aceita recursos cloud declarados com Glue, Lake Formation, S3, catalog_id, account_id e role_arn opcionais, sem descobrir recursos fora da declaracao."
    verified_by: {kind: test, ref: "tests/test_workspace_semantic_graph.py::test_manifest_carrega_recursos_cloud_declarados"}
  - id: AC6
    statement: "O coletor de grafo live cria nos e arestas de conta, Glue, Lake Formation e S3 usando somente recursos declarados e preserva status, origem e timestamps no artefato."
    verified_by: {kind: test, ref: "tests/test_collect_live_graph.py::test_collect_live_graph_compose_glue_lakeformation_s3"}
  - id: AC7
    statement: "O coletor exige role_arn explicito quando a conta alvo diverge da identidade AWS observada e registra cross_account_role_required em vez de tentar assumir acesso implicitamente."
    verified_by: {kind: test, ref: "tests/test_collect_live_graph.py::test_cross_account_requires_explicit_role"}
  - id: AC8
    statement: "AccessDenied, credencial ausente, lista truncada e dados ausentes saem como unresolved nomeado e nunca como no ou aresta positiva."
    verified_by: {kind: test, ref: "tests/test_collect_live_graph.py::test_live_graph_preserves_unresolved_states"}
  - id: AC9
    statement: "A CLI expõe comandos reproduziveis para rodar a matriz de benchmark, calcular custo observado com pricing declarado e coletar o grafo live."
    verified_by: {kind: test, ref: "tests/test_adapters_cli.py::test_cli_exposes_observed_economy_and_live_graph_commands"}
success:
  - id: SC1
    metric: "Quantidade de casos e eixos presentes na matriz token-efficient, por perfil"
    source: "python scripts/run_token_efficient_bench.py --out <arquivo> e tests/test_token_efficient_benchmark.py"
  - id: SC2
    metric: "Provider tokens resolvidos, payload_bytes e cost_usd com cost_basis nomeado"
    source: "transcript fixture, pricing JSON declarado e tests/test_provider_economy.py"
  - id: SC3
    metric: "Nos, arestas e unresolved do grafo cloud declarado"
    source: "artefato JSON de collect workspace-graph e tests/test_collect_live_graph.py"
out_of_scope:
  - "Estimativa de token por bytes, tiktoken, ou qualquer token fabricado quando o transcript nao traz usage."
  - "Preco embutido no codigo, inferencia de preco por provider/modelo, ou custo em dolar sem cost_basis e tabela declarada."
  - "Descoberta automatica de todos os recursos AWS, mutacao de Glue, Lake Formation, S3 ou IAM, e coleta sem manifesto allowlist."
  - "Consulta live no CI; testes usam clientes stubados e fixtures, enquanto a chamada real depende de credenciais, regiao e permissoes do operador."
  - "Score unico que combine qualidade, bytes e tokens; os eixos permanecem separados."
unknowns:
  - id: U1
    blocks: [SC2]
    unlock: "O operador fornece pricing JSON versionado com currency, cost_basis e preco por unidade de input, output, cache_read e cache_creation tokens."
  - id: U2
    blocks: [SC3]
    unlock: "O operador executa collect workspace-graph com credenciais AWS e um workspace manifest contendo recursos, regioes, catalogos e roles explicitamente declarados."
change_kinds: [tool_or_verb, extractor, fixture_corpus, claims]
---

# TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH — requisitos

## Problema

O vNext mede bytes e preserva tokens quando o host fornece transcript, mas a
suite ainda e pequena, nao calcula custo observado com uma base de preco
declarada e o grafo semantico ainda nao atravessa recursos AWS live.

## Critérios

Os nove acceptance criteria acima fecham os tres gaps em unidades separadas:
qualidade x payload, usage x pricing e grafo cloud x evidência de acesso.

## Restrições

- O nucleo continua offline e provider-independent.
- Coleta AWS e read-only, allowlist por manifesto, com conta/regiao/role
  explicitos quando aplicavel.
- Ausencia de evidence continua sendo `unresolved`, nunca um no vazio ou um
  edge positivo.
- Mudanca nao afirma economia percentual sem comparar runs ou pricing declarado.

## Hipóteses rastreáveis

| ID | Hipótese | Impacto se errada | Validação |
|---|---|---|---|
| R1 | Transcripts suportados carregam usage suficiente para separar input/output/cache. | Matriz fica parcialmente unresolved. | Fixtures do host transcript e parser existente. |
| R2 | Pricing externo pode ser fornecido em formato estável e versionado. | Custo permanece unresolved sem bloquear tokens. | Schema/teste do pricing. |
| R3 | Recursos cloud declarados têm identidade suficiente para Glue, Lake Formation e S3. | O grafo publica lacunas por recurso, sem descobrir nomes. | Manifesto e clientes AWS stubados. |

## Próximo passo

`sdd-design` deve decidir o schema de pricing, o schema de `cloud_resources`,
o artefato live e os pontos de integração CLI sem adicionar superfície MCP por
inferência.
