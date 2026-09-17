---
sdd: 1
feature: SDD_SKILLS
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Seis skills sdd-* canonicas, espelhadas por sync_skills, dao a quem clona o repo o ciclo spec, plan, build com TDD e ship ancorado no sdd check, sem plugin de usuario."
  prediction: "As features SDD_OPERATOR, SDD_MIGRATION e SDD_EVAL, escritas com essas skills, fecham com sparkforge sdd check sem recusa, e os gates de skill passam com as seis."
  experiment: "Escrever as skills e os templates, usar as skills para escrever as tres features seguintes, e rodar sparkforge sdd check --repo . mais os testes de skill."
acceptance:
  - id: AC1
    statement: "As seis skills sdd-explore, sdd-define, sdd-design, sdd-plan, sdd-build e sdd-ship existem em skills/ com frontmatter valido e as secoes obrigatorias."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_seis_skills_existem"}
  - id: AC2
    statement: "Os seis templates de docs/sdd/templates/ formam uma feature que passa no sdd check quando copiados para uma pasta de feature e carimbados em ordem."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_templates_formam_feature_valida"}
  - id: AC3
    statement: "Toda linha de comando sparkforge citada nas skills sdd-* e aceita pelo parser da CLI."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_comandos_citados_existem"}
  - id: AC4
    statement: "vendor/CREDITS.md credita AgentSpec e superpowers, com licenca e o que foi usado como base."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_credito_das_bases"}
  - id: AC5
    statement: "Os espelhos .claude/skills e .agents/skills das seis skills conferem com a renderizacao."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check"}
success:
  - id: SC1
    metric: "Recusas do sdd check sobre docs/sdd depois de B, C, D e E"
    source: "sparkforge sdd check --repo . (refused)"
out_of_scope:
  - "Detalhe do perfil operator alem de apontar para change sandbox e case (subprojeto C)."
  - "Desativar plugins e mover historico (subprojeto D)."
  - "Afirmar que o SDD proprio e melhor que superpowers ou AgentSpec (subprojeto E, regra 30)."
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "Ler scripts/sync_skills.py para saber se toda skill nova precisa de entrada na tabela de despacho."
change_kinds: [agent_or_skill, tool_or_verb]
---

# SDD_SKILLS — o ciclo como skills do repositorio

## Problema

O nucleo (`sparkforge sdd check|status|stamp`) confere artefatos, mas nada no
repositorio ensina um agente a escreve-los. Hoje quem ensina sao dois plugins de
nivel usuario (superpowers e AgentSpec), que nao vem com o clone e nao chegam ao
Devin nem ao Copilot.

## O que muda

Seis skills canonicas em `skills/`, uma por fase, e um template por fase em
`docs/sdd/templates/`. As skills dizem **como pensar** cada fase; o `sdd check`
diz se o resultado **fecha**. Nenhuma skill atribui nota a si mesma.

## Base e credito

A ordem das fases e a ideia de manifesto de arquivos vem do AgentSpec 3.5.0
(MIT). O dialogo uma pergunta por vez, as tarefas pequenas com codigo completo, o
TDD vermelho-verde e a revisao em dois estagios vem do superpowers (MIT). O que
e nosso: o gate deterministico, a cascata por hash, o teste real por criterio, o
perfil operator e o ship derivado de `docs/gates-por-mudanca.md`.
