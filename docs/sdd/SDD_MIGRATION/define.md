---
sdd: 1
feature: SDD_MIGRATION
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Com o AgentSpec desativado no projeto, o historico dos dois processos arquivado sem reescrita e os documentos de entrada apontando para as skills sdd-*, um agente que abre o repositorio usa o SDD proprio e nao os plugins."
  prediction: "Nenhum arquivo rastreado sob .claude/sdd/, settings do projeto com agentspec desligado, e CLAUDE.md, AGENTS.md e CONTRIBUTING.md citando sdd-define e sparkforge sdd check."
  experiment: "Teste que le settings, arvore versionada e os tres documentos, mais o sdd check sobre docs/sdd depois da migracao."
acceptance:
  - id: AC1
    statement: ".claude/settings.json desliga agentspec@agentspec."
    verified_by: {kind: test, ref: "tests/test_sdd_migration.py::test_agentspec_desligado_no_projeto"}
  - id: AC2
    statement: "Nenhum arquivo rastreado mora sob .claude/sdd/, o historico do AgentSpec esta em docs/sdd/archive/agentspec/ com o mesmo conteudo, e .claude/sdd/ esta no .gitignore."
    verified_by: {kind: test, ref: "tests/test_sdd_migration.py::test_historico_agentspec_arquivado"}
  - id: AC3
    statement: "docs/superpowers/README.md declara specs/ e plans/ congelados, e STATUS.md continua ali como fonte da verdade das fases."
    verified_by: {kind: test, ref: "tests/test_sdd_migration.py::test_superpowers_congelado"}
  - id: AC4
    statement: "CLAUDE.md, AGENTS.md e CONTRIBUTING.md mandam usar as skills sdd-* e sparkforge sdd check, e nenhum deles manda gravar spec em .claude/sdd/ ou docs/superpowers/specs/."
    verified_by: {kind: test, ref: "tests/test_sdd_migration.py::test_documentos_de_entrada_apontam_o_sdd"}
  - id: AC5
    statement: "README.md apresenta o SDD proprio (as seis skills e os tres verbos) e .sparkforge/journal.jsonl deste repositorio fica fora do git."
    verified_by: {kind: test, ref: "tests/test_sdd_migration.py::test_readme_e_journal"}
success:
  - id: SC1
    metric: "Arquivos rastreados sob .claude/sdd/ depois da migracao"
    source: "git ls-files .claude/sdd"
out_of_scope:
  - "Desinstalar plugins no nivel do usuario: e configuracao do operador, fora do repositorio."
  - "Desligar o superpowers inteiro: debugging, verificacao e revisao dele continuam em uso; so o ciclo de spec e o TDD sao trocados, por instrucao."
  - "Reescrever specs e planos antigos."
unknowns: []
change_kinds: [agent_or_skill]
---

# SDD_MIGRATION — trocar o processo sem apagar a historia

## O que sai

- O AgentSpec, no projeto (`enabledPlugins`), e com ele o hook que reescreve
  `.claude/sdd/.detected-stack.md` a cada sessao.
- `.claude/sdd/` da arvore versionada: vira `docs/sdd/archive/agentspec/` por
  `git mv`, sem editar conteudo.

## O que fica

- `docs/superpowers/STATUS.md`, que continua a fonte da verdade das fases.
- `docs/superpowers/specs/` e `plans/`, congelados como registro; spec novo
  nasce em `docs/sdd/<FEATURE>/`.
- O superpowers instalado, porque debugging, verificacao e revisao continuam
  uteis; a troca do ciclo de spec e do TDD e por instrucao nos documentos de
  entrada.
