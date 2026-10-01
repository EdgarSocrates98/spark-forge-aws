---
sdd: 1
feature: CRITERIO_DE_DOMINIO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/CRITERIO_DE_DOMINIO/plan.md
  sha256: "4f417f3377f6047b00b10c82fe04de8dd912e8537afb45f8d667d5d71dffd6e8"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_criterio_de_dominio.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_criterio_de_dominio.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_criterio_de_dominio.py -k \"escrito or vivo\" -q", exit: 1}
    green: {command: "python -m pytest tests/test_criterio_de_dominio.py -k \"escrito or vivo\" -q", exit: 0}
claims:
  - text: "O catalogo commitado nao tem regra executable: false."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_catalogo_nao_tem_area_de_coordenacao"
  - text: "Toda area do catalogo tem regra executavel sem blocked_on."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_toda_area_tem_regra_que_julga"
  - text: "Todo coordenador de agents/ declara area que julga e nenhuma area inexistente."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_declara_area_que_julga"
  - text: "Todo coordenador tem rota que dispara por finding, fact ou entrypoint real, e nao so por sentinela __agentic_*__."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"
  - text: "Os sete sf-* e as cinco skills sairam, e as tres sparkforge_sdd_* sao citadas por spark-performance-architect."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_o_que_so_o_nome_alcancava_saiu"
  - text: "O criterio esta em docs/gates-por-mudanca.md, citando o teste, e CLAUDE.md e AGENTS.md apontam para ele."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_criterio_escrito_e_apontado"
  - text: "Nenhum documento vivo cita agente ou skill que saiu nesta feature."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_documento_vivo_nao_cita_o_que_saiu"
  - text: "Nenhuma tool ficou orfa."
    evidence_ref: "tests/test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan"
  - text: "Na arvore de 91643841 (antes do SF_STUBS), o teste novo falha nos sete testes, e os tres niveis nomeiam areas agentic-sf (SF-AGENTS, SF-AIRFLOW...) e agentes sf-* (sf-agent-builder, sf-orchestrator...)."
    evidence_ref: "git worktree em 91643841 com tests/test_criterio_de_dominio.py de 3aeb9c58: 7 failed (2026-09-19)"
  - text: "Todos os goldens de fixture passam sem regeneracao: 3217 passed, 4 skipped, arvore limpa."
    evidence_ref: "python -m pytest tests/test_fixtures_golden*.py -q (2026-09-19, em 3aeb9c58)"
change_id: null
---

# CRITERIO_DE_DOMINIO — relatório do build

## Commits

| tarefa | commit | o quê |
|---|---|---|
| emenda do D1 | `43de7901` | condição `case` com entrypoint real conta como artefato |
| T1 | `59003a7f` | o gate, e saem 7 agentes, 5 skills e 7 rotas |
| T2 | `5952e025` | o critério escrito, ponteiros, documentos vivos e números |
| ajuste | `62de42f9` | `aws-database` e `aws-observability` param de citar skill removida |

Os hashes são os de depois do rebase sobre a `main` com o #88 (`febcdecb`).

## Desvios do plano

- **D1 emendado antes da T1.** A primeira versão não contava nenhuma condição `case`,
  era mais estrita que o AC4, e reprovava `glue-incremental-performance-architect`, cuja
  rota AGENT-006 casa o entrypoint `incremental` do código do job. O erro veio do
  explore, que contou essa rota como real por um critério ("não contém `__agentic_`")
  diferente do que o design escreveu. Agora conta como artefato a rota com `findings_area`
  ou `fact`, ou a rota com condição `case` cujo valor não é sentinela `__nome__`.
- **T1:**
  - `scripts/regen_fixtures.py` não cobre `knowledge_drift`. O golden
    `filtro_por_url` foi regenerado por `SPARKFORGE_REGEN_DRIFT=1` no próprio teste.
    Saíram quatro caminhos `agents/<removido>.md`, e `totals.agents` foi de 8 para 4,
    a contagem desses mesmos caminhos.
  - `refresh_knowledge.py --offline --update` não atualiza
    `knowledge/offline-manifest.json`. O sha256 foi recalculado com
    `sparkforge.tools.offline._content_sha256`.
  - `tests/test_platform_compilers.py` procurava `sf-orchestrator` no registro real e
    passou a procurar `sf-runtime-specialist`.
  - Três links para páginas de referência removidas saíram já na T1, porque o
    `test_reference_docs` cairia até a T2.
  - Alegações:
    - VNX-500, 502 e 504 passaram a `historical`.
    - VNX-053: 56 para 51.
    - VNX-640: 752 para 753.
    - VNX-430: 39 para 37 KB.
- **T2:**
  - A linha do `AGENTS.md` cita o título em português da seção, porque o teste exige a
    palavra "artefato".
  - Ela entrou em `## Operating contract`: o arquivo não tem seção de verificação.
  - `docs/guia/07-conhecimento-e-catalogo.md` também acompanhou os números.
- **Ajuste depois da T2:** `skills/aws-database` e `skills/aws-observability` citavam
  `design-neptune-graph` e `analyze-analytics`. Isso foi achado por `git grep` depois
  da T2, e as duas entraram em `VIVOS`.

## Revisão

A revisão por tarefa em dois estágios não rodou. O controlador conferiu cada relato, os
gates que o plano nomeia e um `git grep` final pelos nomes removidos. Fora dos
documentos históricos, esse `git grep` só achou dado sintético em três testes
(`test_harness_authorization`, `test_canonical_registry`, `test_agentic_*`) e linhas
datadas do STATUS.

## Medidas

| | antes (`99ae3eaf`) | depois |
|---|---|---|
| coordenadores em `agents/` | 19 | 12 |
| skills | 56 | 51 |
| rotas em `routing.yaml` | 47 | 40 |
| bytes de skills (surface lock) | 522 870 | 516 561 |
| testes do critério que falham em `91643841` | — | 7 de 7 |
