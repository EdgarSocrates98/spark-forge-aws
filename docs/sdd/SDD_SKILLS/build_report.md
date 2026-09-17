---
sdd: 1
feature: SDD_SKILLS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_SKILLS/plan.md
  sha256: "40d8507980aca91bfd0860fa7db97b214f73929163bc0d2ed24c9dc9d6881a2f"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_templates_formam_feature_valida -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_seis_skills_existem -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_arvore_versionada.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_comandos_citados_existem tests/test_sdd_skills.py::test_o_detector_recusa_verbo_inventado -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd_skills.py::test_credito_das_bases -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_skills.py tests/test_vendor_caveman.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_reference_docs.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_reference_docs.py -q", exit: 0}
claims:
  - text: "Os seis templates copiados para uma feature EXEMPLO e carimbados em ordem passam no sdd check sem recusa e sem lacuna."
    evidence_ref: "tests/test_sdd_skills.py::test_templates_formam_feature_valida"
  - text: "As seis skills sdd-* existem com name, as tres secoes obrigatorias e a citacao de sparkforge sdd check."
    evidence_ref: "tests/test_sdd_skills.py::test_seis_skills_existem"
  - text: "Todo verbo sparkforge citado entre crases nas seis skills e aceito pelo parser da CLI, e o detector recusa verbo inventado."
    evidence_ref: "tests/test_sdd_skills.py::test_comandos_citados_existem"
  - text: "vendor/CREDITS.md credita superpowers e AgentSpec (MIT) e nomeia as seis skills."
    evidence_ref: "tests/test_sdd_skills.py::test_credito_das_bases"
  - text: "Os espelhos .claude/skills e .agents/skills das seis skills conferem com a renderizacao."
    evidence_ref: "python scripts/sync_skills.py --check"
  - text: "As seis skills sao nao despachaveis e registradas na tabela de despacho (U1 resolvido: render_skill recusa skill sem decisao)."
    evidence_ref: "scripts/sync_skills.py"
  - text: "A superficie de skills cresceu 39828 bytes (488597 para 528425), de 60 para 66 documentos."
    evidence_ref: "docs/surface.lock.json"
  - text: "O gate de lastro fecha com zero divergencia depois de remediar VNX-053 e VNX-640."
    evidence_ref: "docs/claims.lock.json"
---

# SDD_SKILLS — relatório do build

Cinco tarefas, um commit cada: `0398cf7e` (T1), `af4c63dd` (T2), `4baa4a4b`
(T3), `51e46237` (T4), `01efeafd` (T5). Todo vermelho acima foi visto na hora,
com o exit que o comando devolveu.

## U1

`scripts/sync_skills.py::render_skill` levanta `ValueError` para skill sem
decisão de despacho: a entrada na tabela é obrigatória. As seis entraram em
`NON_DISPATCHABLE_SKILLS` com a razão ao lado (D1 do design).

## Desvios do plano

1. **T1, teste mais forte.** Além de `refused == []`, o teste exige
   `unresolved == []`, `ok` verdadeiro e `features == ["EXEMPLO"]`; um segundo
   teste (`test_templates_nao_viram_feature_no_repositorio`) prova que
   `docs/sdd/templates/` fica fora da descoberta no repositório real.
2. **T1, templates conferidos contra o núcleo real.** Como o template de
   explore existe, o template de define declara `upstream` para ele (define sem
   explore recusaria o bloco). O `verified_by` e o `test` apontam
   `tests/test_exemplo.py::test_exemplo`, que o teste cria no repositório
   temporário: com o build `ready`, teste ausente seria `verified_by_dangling`.
   O define do template usa `change_kinds: [agent_or_skill]` e o ship lista
   `sync_skills` e `agents_parity`, em vez de `change_kinds: []`, para ensinar
   a derivação. O corpo do plano de exemplo traz um teste e uma implementação
   reais (`exemplo/resumo.py`) em vez de `pass`.
3. **Arquivos fora do manifesto do design.** A entrega tocou registros que o
   design não listou: `manifest.json` (lista de skills,
   `tests/test_docs_coverage.py`), `tests/test_sync_render.py` (conjunto de
   não-despacháveis sem coordenador), `docs/superpowers/STATUS.md` (linha de
   Skills, `check_status_numbers.py`), `docs/claims.lock.json`,
   `docs/vnext/CURRENT-STATE.md` e `docs/harness/CODEINTEL-GAP.md` (VNX-053 e
   VNX-640), `docs/guia/05-agents-e-skills.md` (linha da tabela de pedidos) e
   `docs/guia/referencia/` (listado no plano, não no design). A skill
   `sdd-design` passou a mandar pôr esses registros no manifesto desde o início.
4. **T3, vermelho pelo auxiliar ausente.** As skills já citavam só verbos
   reais; o vermelho observado foi `NameError` dos auxiliares
   `_verbos_citados`/`_aceito_pelo_parser`, escritos depois do teste. Nenhum
   texto de skill precisou de correção. Entrou um teste de guarda
   (`test_o_detector_recusa_verbo_inventado`) que prova que o detector recusa
   `sdd verify`, para o teste principal não passar por vacuidade.
5. **T4, teste mais forte.** Além dos quatro trechos do plano, o teste exige o
   nome de cada uma das seis skills em `vendor/CREDITS.md`.
6. **T5, vermelho de outro teste.** O plano nomeia
   `tests/test_skill_content.py::test_copias_conferem_com_a_renderizacao`, mas
   esse teste ficou verde já no T2, quando os espelhos foram gerados. O vermelho
   registrado para T5 é `tests/test_reference_docs.py` antes de
   `python scripts/gen_reference_docs.py`; `python scripts/check_surface_lock.py`
   sem `--update` também saiu com exit 1 (três divergências de skills) antes da
   atualização.

## Revisão

Sem subagente nesta execução: o build rodou numa sessão só, tarefa por tarefa,
com os gates vizinhos de cada uma (`docs/gates-por-mudanca.md`, seções
"Alterar agent, skill ou seus espelhos" e "Acrescentar ou alterar tool, verbo
de CLI, agent ou skill: a referência gerada"). A revisão em dois estágios que a
skill `sdd-build` descreve fica para as features seguintes.

## Gates rodados no fechamento

- `python scripts/sync_skills.py --check` — OK.
- `python -m pytest tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_arvore_versionada.py tests/test_bootstrap_budget.py tests/test_sdd.py tests/test_vendor_caveman.py tests/test_suite_batches.py -q` — 1179 passaram.
- `python scripts/gen_reference_docs.py` — 268 páginas, 8 regravadas.
- `python scripts/check_surface_lock.py --update` — skills 60 → 66 documentos, 488597 → 528425 bytes.
- `python scripts/check_vnext_claims.py` — 0 divergências depois de VNX-053 e VNX-640.
- `python scripts/check_status_numbers.py --strict` — 0 divergências.
