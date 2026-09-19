---
sdd: 1
feature: SF_STUBS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/SF_STUBS/explore.md
  sha256: "dd916b11b6f54f04213e3d72fb5970e60a02e0b06eaae309d22453c624eb4f64"
hypothesis:
  claim: "A camada agentic-sf e os 19 agentes sf-* que so a declaram nao julgam nada: apaga-los, realocando as tools e a skill com conteudo que so eles alcancam, nao tira nenhuma capacidade que julga."
  prediction: "Depois da remocao, o catalogo tem as mesmas 157 regras executaveis de antes e nenhuma nao executavel; os goldens de findings das fixtures e dos cenarios passam sem regeneracao; nenhuma tool fica orfa. Se algum golden de findings mudar, se a contagem de executaveis sair de 157, ou se alguma tool ficar sem coordenador, a afirmacao esta errada."
  experiment: "Contar regras executaveis antes (main em 91643841) e depois; rodar os testes de golden de findings e tests/test_agent_coverage.py sem regenerar nada."
acceptance:
  - id: AC1
    statement: "O catalogo nao tem nenhuma regra com executable: false nem nenhum rules/catalog/agentic-sf-*.yaml, e continua com 157 regras executaveis."
    verified_by: {kind: test, ref: "tests/test_sf_stubs.py::test_catalogo_so_tem_regra_que_julga"}
  - id: AC2
    statement: "Os 19 agentes sf-* que so declaravam area de coordenacao nao existem mais em agents/, e todo sf-* que fica declara ao menos uma area com regra executavel e nenhuma area inexistente."
    verified_by: {kind: test, ref: "tests/test_sf_stubs.py::test_todo_sf_declara_area_que_julga"}
  - id: AC3
    statement: "Nenhuma rota de rules/catalog/routing.yaml recomenda agente inexistente nem dispara por findings_area que nao existe no catalogo."
    verified_by: {kind: test, ref: "tests/test_sf_stubs.py::test_rota_aponta_para_agente_e_area_que_existem"}
  - id: AC4
    statement: "As tools sparkforge_code_* e sparkforge_iceberg_assess_upgrade, e a skill iceberg-v3-readiness, continuam alcancaveis por um coordenador que fica."
    verified_by: {kind: test, ref: "tests/test_sf_stubs.py::test_conteudo_real_muda_de_dono"}
  - id: AC5
    statement: "Nenhuma tool fica orfa."
    verified_by: {kind: test, ref: "tests/test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan"}
  - id: AC6
    statement: "Os espelhos de agents e skills (.claude, .agents, .codex, .github) refletem a remocao."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check"}
  - id: AC7
    statement: "Os numeros publicados que contavam as 35 areas (contagem do catalogo, de agents e de skills) batem com a medida nova."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
  - id: AC8
    statement: "Nenhum documento vivo cita agente ou skill que saiu; os documentos historicos ficam como estavam, com uma nota de desvio no topo."
    verified_by: {kind: test, ref: "tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu"}
success:
  - id: SC1
    metric: "Regras executaveis antes e depois (157 e 157), e nao executaveis (35 e 0)"
    source: "sparkforge.rules.loader.load_catalog() contado por executable, em 91643841 e no fim do build"
  - id: SC2
    metric: "Goldens de findings que mudaram, e, nos goldens de assessment, os campos que mudaram"
    source: "testes de golden de fixtures e cenarios rodados sem regenerar; nos assessment.json de fixtures/scenarios e evals/holdout, que carregam a contagem do catalogo, o diff depois da regeneracao"
  - id: SC3
    metric: "Coordenadores, skills e rotas antes e depois"
    source: "agents/*.md, skills/*/SKILL.md e as rotas de rules/catalog/routing.yaml contados antes e depois"
out_of_scope:
  - "Remover o campo executable do loader: a validacao nas duas direcoes continua, e o criterio de dominio pode precisar dela."
  - "Criterio escrito e gate de dominio novo por artefato: feature CRITERIO_DE_DOMINIO."
  - "Reescrever os 11 sf-* que ficam: so perdem as areas ocas e ganham o conteudo realocado."
  - "Coletor novo para Airflow, DynamoDB, Kinesis, Lambda ou Step Functions."
  - "Reescrever documento historico (relatorio de entrega, spec congelado): ganha nota de desvio, nao reescrita."
unknowns:
  - id: U1
    blocks: [AC6, AC7]
    unlock: "Documentos que citam os agentes e skills que saem: docs/agentic-expansion.md, docs/delivery-report.md, docs/teams-catalog.md, docs/operations-guide.md, docs/guia/05-agents-e-skills.md, knowledge/domain-tool-matrix.md, docs/harness/MIGRATIONS-GLUE-GAP.md, AGENTS.md. O design decide, arquivo por arquivo, se e documento vivo (atualiza) ou historico (nota de desvio)."
  - id: U2
    blocks: [AC4]
    unlock: "Quem recebe a secao Indice de codigo de sf-context-engineer (as nove tools sparkforge_code_*): o design escolhe o coordenador lendo quem ja responde pergunta de codigo."
change_kinds: [rule, rule_area, agent_or_skill, tool_or_verb, routing, status_numbers, knowledge_doc, claims]
---

# SF_STUBS — requisitos

## Problema

A expansão agêntica v2 (commit `308fa4dd`) criou 35 áreas de regra que não julgam
nada e 30 coordenadores `sf-*`, dos quais 19 só declaram essas áreas. O catálogo
publica 192 regras, e 35 delas nunca podem disparar. 45 rotas levam a esses 19
agentes, e nenhuma casa com um finding real. É nome de domínio sem artefato.

## Fontes citadas

- `docs/sdd/SF_STUBS/explore.md`, seção Medidas (2026-09-19, `main` em `91643841`).
- `sparkforge/rules/loader.py`, a validação de `executable` nas duas direções.
- `tests/test_agent_coverage.py`: área sem coordenador e tool órfã.

## Critérios

- AC1 a AC4 travam o resultado num teste novo, `tests/test_sf_stubs.py`.
- AC5 é o teste que já existe e que a remoção quebraria sem a realocação.
- AC6 e AC7 são os gates de espelho e de número publicado.
- AC8 trava a limpeza dos documentos vivos no mesmo teste novo.
