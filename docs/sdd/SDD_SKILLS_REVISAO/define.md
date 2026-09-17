---
sdd: 1
feature: SDD_SKILLS_REVISAO
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Corrigir os achados da revisao de SDD_SKILLS nas skills, nos templates e no README, e fazer o teste de comandos conferir as flags, fecha as lacunas que deixavam funcval_not_run, pacote PENDENTE e verified_by command sem execucao, sem que as skills crescam."
  prediction: "Os testes novos de tests/test_sdd_skills.py passam sobre o texto revisado e falham sobre o texto de 480181a6; o teste de comandos recusa uma flag inventada; e a soma dos bytes das skills lida do surface lock fica menor ou igual a 532261 (o valor depois de SDD_OPERATOR_DURAVEL). Se qualquer uma das tres falhar, a afirmacao esta errada."
  experiment: "Escrever os testes antes do texto, rodar tests/test_sdd_skills.py e python scripts/check_surface_lock.py --update, e ler o total de skills."
acceptance:
  - id: AC1
    statement: "O teste de comandos citados confere, alem de verbo e subverbo, cada flag de cada comando sparkforge entre crases das skills sdd-*, com valor ficticio no lugar de marcador <...>, e recusa flag inventada."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_o_detector_recusa_flag_inventada"}
  - id: AC2
    statement: "A description de cada skill sdd-* comeca com 'Use quando', traz so as condicoes de disparo e tem no maximo 320 caracteres."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_descricoes_so_com_gatilho"}
  - id: AC3
    statement: "docs/sdd/README.md guarda os blocos repetidos (laco stamp, check e ready; caminho de mudanca do operador; conhecimento citado) e cada skill sdd-* aponta para a secao, mantendo o comando de check no proprio texto; README diz que ready e zero recusa com lacunas esperadas permitidas."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_blocos_comuns_moram_no_readme"}
  - id: AC4
    statement: "sdd-build e sdd-ship citam funcval compare com --out, benchmark com --out e change propose com --funcval e --benchmark; mandam rodar cada verified_by command exigindo exit 0; sdd-build tem a revisao final da implementacao inteira, a leitura critica do plano antes de comecar e diz quem escreve red e green; o vermelho por erro de import so conta quando falta a unidade testada."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_revisao_de_build_e_ship"}
  - id: AC5
    statement: "sdd-ship so permite confirmed com a previsao inteira medida, cita a regra 21, lista as quatro opcoes de fechamento com os testes verificados antes e confirmacao digitada para descartar, e pede a secao Licoes; sdd-define exige a leitura do operador antes de ready e previsao mensuravel no ship; sdd-explore diz que chosen e um approaches[].id; sdd-plan fala de TestClasse::test_x e do sufixo de parametrize."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_revisao_de_define_explore_plan_ship"}
  - id: AC6
    statement: "Os templates usam portugues acentuado, dizem para trocar feature EXEMPLO e por status draft ao copiar, o template de plan diz quando erro de import conta como vermelho, e o de ship tem a secao Licoes; os seis continuam formando uma feature valida."
    verified_by: {kind: test, ref: "tests/test_sdd_skills.py::test_templates_revisados"}
  - id: AC7
    statement: "Os espelhos das skills conferem com a renderizacao."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check"}
  - id: AC8
    statement: "O ship.md de SDD_SKILLS nao e reescrito (regra 21): o desfecho prematuro fica registrado nos desvios desta feature."
    verified_by: {kind: command, ref: "git diff --exit-code 480181a6 -- docs/sdd/SDD_SKILLS/ship.md"}
success:
  - id: SC1
    metric: "Bytes das skills antes (532261) e depois"
    source: "python scripts/check_surface_lock.py --update (docs/surface.lock.json, skills.total_bytes)"
  - id: SC2
    metric: "Bytes de cada skills/sdd-*/SKILL.md antes e depois"
    source: "wc -c skills/sdd-*/SKILL.md"
out_of_scope:
  - "Mudar o nucleo sparkforge/sdd/: e texto, template e teste."
  - "Reescrever SDD_SKILLS/ship.md: o desfecho e fechado por acrescimo aqui e verificado por SDD_EVAL."
  - "O perfil operator, ja revisto em SDD_OPERATOR_DURAVEL."
unknowns: []
change_kinds: [agent_or_skill]
---

# SDD_SKILLS_REVISAO — os achados da revisão das skills

## Problema

A revisão de `SDD_SKILLS` achou onze pontos no texto das skills, dos
templates e do README, e um teste fraco:

1. `funcval compare` citado sem `--out`: `funcval_not_run` nunca sai.
2. `benchmark` e `change propose` sem as flags de evidência: o pacote do PR
   fica PENDENTE.
3. `verified_by.kind: command` é registrado e ninguém manda rodar.
4. `sdd-build` sem revisão final, sem leitura crítica do plano e ambíguo sobre
   quem escreve `red`/`green`.
5. `sdd-define` deixa `ready` com zero recusa, sem a leitura do operador, e
   não exige previsão mensurável.
6. `sdd-ship` aceita `confirmed` parcial, não cita a regra 21, não lista as
   opções de fechamento e não pede lições.
7. Erro de import conta como vermelho mesmo quando falta outra coisa.
8. Detalhes: README sobre lacunas no `ready`, `chosen`, nomes de teste em
   classe e parametrize, `feature: EXEMPLO`, acentos nos templates.
9. Descrições longas, com resumo do fluxo.
10. Blocos repetidos nas seis skills.
11. `test_comandos_citados_existem` não confere flag, então o AC3 de
    `SDD_SKILLS` não era garantido.

E `SDD_SKILLS/ship.md` marcou `confirmed` com metade da previsão pendente.

## O que muda

Texto, templates, README e um teste mais forte. O `ship.md` de `SDD_SKILLS`
fica como está (regra 21); esta feature registra nos desvios que o desfecho
anterior foi prematuro e que a parte pendente é verificada por `SDD_EVAL`.

O operador pediu estes onze itens por escrito, e isso vale como a leitura que
o `ready` exige.
