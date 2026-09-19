---
sdd: 1
feature: SF_STUBS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SF_STUBS/plan.md
  sha256: "bbc4995c695e35461ffda6df814c898c539f5db6a0f6a30ecc7c1234f9288133"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sf_stubs.py::test_conteudo_real_muda_de_dono -q", exit: 1}
    green: {command: "python -m pytest tests/test_sf_stubs.py::test_conteudo_real_muda_de_dono -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sf_stubs.py -k \"catalogo or todo_sf or rota\" -q", exit: 1}
    green: {command: "python -m pytest tests/test_sf_stubs.py -k \"catalogo or todo_sf or rota\" -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu -q", exit: 1}
    green: {command: "python -m pytest tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu -q", exit: 0}
claims:
  - text: "O catalogo nao tem rules/catalog/agentic-sf-*.yaml nem regra com executable: false, e tem 157 regras, todas executaveis."
    evidence_ref: "tests/test_sf_stubs.py::test_catalogo_so_tem_regra_que_julga"
  - text: "Os 19 agentes ocos nao existem em agents/, e os 11 sf-* que ficam declaram so areas com regra executavel."
    evidence_ref: "tests/test_sf_stubs.py::test_todo_sf_declara_area_que_julga"
  - text: "Nenhuma rota de routing.yaml recomenda agente inexistente nem dispara por findings_area sem regra executavel."
    evidence_ref: "tests/test_sf_stubs.py::test_rota_aponta_para_agente_e_area_que_existem"
  - text: "As nove sparkforge_code_* sao citadas por pyspark-code-reviewer, sparkforge_iceberg_assess_upgrade e iceberg-v3-readiness por iceberg-performance-engineer, e analyze-functional-rules e declarada por data-quality-reviewer."
    evidence_ref: "tests/test_sf_stubs.py::test_conteudo_real_muda_de_dono"
  - text: "Nenhuma tool ficou orfa."
    evidence_ref: "tests/test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan"
  - text: "Os documentos vivos, os dois config/*-expansion.yaml, as cinco skills aws-* e validate.py nao citam agente nem skill que saiu."
    evidence_ref: "tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu"
  - text: "Nos cinco goldens de assessment regenerados so mudaram catalog_rules (192 para 157), unguarded_rules (166 para 131), reachable_rules (-35) e a frase statement que os repete; findings e recusas ficaram identicos."
    evidence_ref: "git diff a5a055f3..405881be -- fixtures/scenarios evals/holdout"
  - text: "Todos os goldens de fixture passam sem regeneracao depois da remocao: 3217 passed, 4 skipped, e a arvore ficou limpa."
    evidence_ref: "python -m pytest tests/test_fixtures_golden*.py -q (2026-09-19, em 0161da5b)"
change_id: null
---

# SF_STUBS — relatório do build

## Commits

| tarefa | commit | o quê |
|---|---|---|
| T1 | `9c433b98` | conteúdo real muda de dono |
| T2 | `405881be` | a camada oca sai: 35 áreas, 19 agentes, 54 rotas, 10 skills |
| T3 | `862917f6` | documentos vivos, config de times, skills `aws-*`, notas nos históricos |
| ajuste | `4c074445` | a linha `Teams:` do `AGENTS.md` |
| revisão | `0161da5b` | os achados da revisão final |

T1 foi feita antes do rebase sobre a `main` com o #87 (`cac7fc17` virou `9c433b98`); o
conflito foi só em `docs/claims.lock.json`, resolvido com a versão da `main` e a VNX-640
remedida de novo (751 para 752).

## Desvios do plano

- **T1:** `import re` e `load_catalog` entraram só nas tarefas que os usam, para o ruff
  não acusar F401. O `check_surface_lock --update` não mudou nada: agents não entram no
  lock.
- **T2:**
  - Os 19 `.codex/agents/*.toml` saíram por `git rm`: `scripts/sync_skills.py` não gera
    `.codex/agents/`, ao contrário do que o D1 do design afirmava.
  - 7 das 10 skills estavam em `NON_DISPATCHABLE_SKILLS`, não em `DISPATCHABLE_SKILLS`;
    saíram das duas tabelas.
  - `tests/test_sync_render.py::test_agent_so_aparece_onde_ha_um_coordenador_so`: além de
    tirar as três skills que saíram, ganhou `analyze-analytics`, `analyze-functional-rules`
    e `review-data-validation`, que passaram a ter coordenador único (consequência de D1 e D6).
  - `tests/test_rules_loader.py::test_every_committed_coordination_area_is_inert` perdeu só
    a pré-condição `assert areas`; o laço fica e guarda a próxima área de coordenação.
  - Links para páginas de referência removidas foram trocados já na T2 em quatro guias,
    porque `tests/test_reference_docs.py::test_links_relativos_dos_guias_resolvem` cairia
    até a T3.
  - Os goldens de assessment mudaram também em `reachable_rules` (−35), contagem derivada
    do catálogo, não achado.
  - Alegações remedidas: VNX-503, 508, 510 e 511 (`proof` passou a `historical`,
    ancorada em `9c433b98`), VNX-053 (skills 66 para 56), VNX-430 (`routing.yaml` 55 para
    39 KB).
- **T3:** `VIVOS` foi de 9 para 18 arquivos: `docs/guia/usos/custo-e-capacidade.md`,
  `config/teams-expansion.yaml` (lido por `sparkforge/registry/loader.py`; os quatro times
  cujo coordenador saiu foram removidos, fica `governance-security`),
  `config/agentic-expansion.yaml`, cinco skills `aws-*` que apontavam para skill removida,
  e `sparkforge/findings/validate.py`. O design não listava esses arquivos. Alegações:
  VNX-056 (times 5 para 1), VNX-793/794/795 novas (a nota de desvio em
  `MIGRATIONS-GLUE-GAP.md` cita 35, 19 e 10, com prova `historical` em `9c433b98`).
- **Revisão final:** `.devin/README.md`, a contagem de rotas no guia 05, o §15 do
  `operations-guide.md` e as seções realocadas nos `.codex/*.toml` foram corrigidos em
  `0161da5b`, junto de oito itens menores. `sparkforge/finops/report.py::_AREAS_DE_CODIGO`
  perdeu `SF-SQL`, área removida. VNX-796 nova.

## Revisão

Um revisor leu o diff inteiro (`a5a055f3..4c074445`) contra define e design. Crítico:
nenhum. Importante: quatro (números em `.devin/README.md` e no guia 05, §15 do guia
operacional contra os configs, `.codex` sem as seções realocadas). Menor: onze. Todos
corrigidos em `0161da5b`, menos o item 17, fora de escopo e registrado no ship: sete
`sf-*` que ficaram (`sf-analytics-specialist`, `sf-graph-specialist`,
`sf-neptune-specialist`, `sf-orchestrator`, `sf-pyspark-specialist`,
`sf-storage-specialist`, `sf-token-verifier`) só são alcançáveis por rotas
`__agentic_*__`, que nenhum código aciona.

A revisão por tarefa em dois estágios não rodou: T1 foi conferida pelo controlador no
diff do commit, T2 e T3 pelos gates nomeados no plano, e a revisão final cobriu o
conjunto.

## Medidas

| | antes (`91643841`) | depois |
|---|---|---|
| regras no catálogo | 192 | 157 |
| regras executáveis | 157 | 157 |
| áreas de coordenação | 35 | 0 |
| coordenadores em `agents/` | 38 | 19 |
| skills | 66 | 56 |
| rotas em `routing.yaml` | 101 | 47 |
| bytes de skills (surface lock) | 533 906 | 522 870 |
