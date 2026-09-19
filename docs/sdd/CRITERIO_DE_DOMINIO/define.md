---
sdd: 1
feature: CRITERIO_DE_DOMINIO
phase: define
profile: dev
status: draft
upstream:
  path: docs/sdd/CRITERIO_DE_DOMINIO/explore.md
  sha256: "87de88ba724c0e08dad2b2aada81c807953193c306f4316bcc5635daabe296d1"
hypothesis:
  claim: "Tres gates (area sem regra que julga, coordenador sem area que julga, coordenador so alcancavel por rota __agentic_*__) teriam barrado a camada agentic-sf quando ela entrou, e passam no repositorio de hoje depois de sair o que so a rota __agentic_*__ alcanca, sem mudar nenhum achado."
  prediction: "Rodado sobre a arvore de 91643841 (antes do SF_STUBS), o teste novo falha nos tres niveis, nomeando areas agentic-sf e agentes sf-*; rodado no fim do build, passa; e os goldens de fixture passam sem regeneracao. Se algum dos tres gates passar em 91643841, ou se algum golden de achado mudar, a afirmacao esta errada."
  experiment: "git worktree em 91643841, copiar tests/test_criterio_de_dominio.py para la e rodar; rodar o mesmo teste e python -m pytest tests/test_fixtures_golden*.py -q no fim do build."
acceptance:
  - id: AC1
    statement: "O catalogo commitado nao tem regra com executable: false."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_catalogo_nao_tem_area_de_coordenacao"}
  - id: AC2
    statement: "Toda area do catalogo tem ao menos uma regra executavel sem blocked_on, ou seja, que julga fact que algum extrator ja emite."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_toda_area_tem_regra_que_julga"}
  - id: AC3
    statement: "Todo coordenador de agents/ declara ao menos uma area com regra executavel, e nenhuma area que nao exista."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_declara_area_que_julga"}
  - id: AC4
    statement: "Todo coordenador de agents/ tem ao menos uma rota em routing.yaml que dispara por finding ou fact, e nao so por scope.entrypoints __agentic_*__."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"}
  - id: AC5
    statement: "Os sete sf-* so alcancaveis por __agentic_*__ (sf-analytics-specialist, sf-graph-specialist, sf-neptune-specialist, sf-orchestrator, sf-pyspark-specialist, sf-storage-specialist, sf-token-verifier) e as cinco skills que so eles declaram (analyze-analytics, analyze-graph-data, design-neptune-graph, agentic-orchestration, token-efficient-agent) saem; as tools sparkforge_sdd_check, sparkforge_sdd_stamp e sparkforge_sdd_status, que so sf-orchestrator alcancava, passam a spark-performance-architect."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_o_que_so_o_nome_alcancava_saiu"}
  - id: AC6
    statement: "O criterio esta escrito numa secao de docs/gates-por-mudanca.md que cita o teste que o trava, e o CLAUDE.md e o AGENTS.md apontam para ela numa linha."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_criterio_escrito_e_apontado"}
  - id: AC7
    statement: "Nenhuma tool fica orfa."
    verified_by: {kind: test, ref: "tests/test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan"}
  - id: AC8
    statement: "Nenhum documento vivo cita agente ou skill que saiu nesta feature."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_documento_vivo_nao_cita_o_que_saiu"}
  - id: AC9
    statement: "Espelhos e numeros publicados batem com a medida nova."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Falhas do teste novo na arvore de 91643841, por nivel"
    source: "saida do pytest no worktree de 91643841"
  - id: SC2
    metric: "Coordenadores, skills e rotas antes e depois"
    source: "agents/*.md, skills/*/SKILL.md e routing.yaml contados em 99ae3eaf e no fim do build"
  - id: SC3
    metric: "Goldens de achado que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
out_of_scope:
  - "Criterio para skill sem coordenador (as skills AWS nao despachaveis continuam validas sem agent)."
  - "Tirar o campo executable do loader: o gate proibe no catalogo commitado; o loader continua validando as duas direcoes."
  - "Remover o modo __agentic_*__ das rotas de coordenadores que tambem tem rota por artefato (sf-runtime-specialist, sf-lake-formation-specialist, sf-security-reviewer, sf-terraform-specialist): o gate so exige que exista a rota por artefato."
  - "Subagents de config/subagents.yaml e tools inexistentes de config/agentic-expansion.yaml (pendencias do SF_STUBS)."
unknowns:
  - id: U1
    blocks: [AC5, AC8]
    unlock: "22 arquivos fora de agents/ e skills/ citam os sete ou as cinco skills, entre eles config/agents.yaml (lido por sparkforge/registry/loader.py), fixtures/knowledge_drift/filtro_por_url/expected/result.json e knowledge/tool-specialization-matrix.md (lido por sparkforge/knowledge_drift.py). O design decide, arquivo por arquivo, consumidor real, documento vivo ou historico."
change_kinds: [agent_or_skill, tool_or_verb, routing, status_numbers, knowledge_doc, claims]
---

# CRITERIO_DE_DOMINIO — requisitos

## Problema

O SF_STUBS removeu a camada que entrou sem artefato: 35 áreas que nunca julgam e 19
coordenadores que só as declaravam. Nada impede que ela volte: o loader aceita área só
com regra `executable: false`, nenhum teste exige que coordenador tenha área que julga,
e rota `__agentic_*__` faz um coordenador existir sem que nenhum finding o chame. Hoje
sete `sf-*` estão nessa última situação.

## O critério, em uma frase

Domínio entra por artefato coletável: uma área só existe com regra que julga fact
emitido por extrator, e um coordenador só existe com área que julga e rota que um
finding ou fact dispara.

## Fontes citadas

- `docs/sdd/CRITERIO_DE_DOMINIO/explore.md`, seção Medidas.
- `docs/sdd/SF_STUBS/ship.md`, Pendências.
- `tests/test_rules_catalog_reachability.py`, `tests/test_agent_coverage.py`,
  `tests/test_router_agents.py`: o que já tem gate.
