---
sdd: 1
feature: AC_VERMELHO
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/AC_VERMELHO/explore.md
  sha256: "914e775fd02e9ec98922cec387978db4c7d2a1e8883676560650896ba09049d5"
hypothesis:
  claim: "Um criterio de kind test cujo teste nunca foi visto vermelho pode ser recusado pelo sdd check sem campo novo no build_report, derivando a ligacao do covers do plano e do red de cada tarefa; e a guarda de regressao legitima, que passa antes e depois por desenho, fica separada de 'ninguem testou' por uma declaracao explicita no define."
  prediction: "Sobre uma feature ainda nao entregue: um criterio de kind test sem tarefa que o cubra com red.exit diferente de zero rodando o node id dele -- ou o arquivo dele com exit 2 -- sai recusado com nome proprio, nomeando o criterio e o teste; o mesmo criterio declarado como guarda, com motivo, passa; guarda sem motivo e recusada; red com o arquivo e exit 1 nao conta; e as 12 features ja entregues continuam passando no sdd check do repositorio inteiro. Se um criterio sem vermelho passar, se a guarda declarada for recusada, se exit 1 no arquivo contar, ou se alguma feature entregue quebrar, a afirmacao esta errada."
  experiment: "Rodar sparkforge sdd check sobre features sinteticas montadas em tmp_path, e sparkforge sdd check --repo . sobre a arvore inteira antes e depois."
acceptance:
  - id: AC1
    statement: "Com o build_report em ready ou done e o ship ausente ou fora de done, todo acceptance de kind test precisa de ao menos uma tarefa do plan que o cubra (covers) e cujo red, no build_report, tenha exit diferente de zero e cite o node id do verified_by no comando. Sem isso sai a recusa acceptance_never_red, nomeando o criterio e o teste."
    verified_by: {kind: test, ref: "tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado"}
  - id: AC2
    statement: "Um red que cita so o ARQUIVO do teste conta quando saiu com exit 2, que no pytest e erro de coleta e deixa o arquivo inteiro vermelho; com exit 1 nao conta, porque nao se sabe qual teste falhou."
    verified_by: {kind: test, ref: "tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1"}
  - id: AC3
    statement: "Um acceptance pode declarar guard com um motivo nao vazio: e guarda de regressao, que passa antes e depois por desenho, e fica isenta de acceptance_never_red. guard vazio sai schema_invalid."
    verified_by: {kind: test, ref: "tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada"}
  - id: AC4
    statement: "Feature com o ship em done nao e conferida por esta regra: o que ela registrou vira historico, como no perfil operator. As 12 features ja entregues continuam passando."
    verified_by: {kind: test, ref: "tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida"}
  - id: AC5
    statement: "O contrato do SDD, o template do define e as skills sdd-define e sdd-build dizem a regra, a recusa nova e como declarar guarda."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check"}
  - id: AC6
    statement: "Os registros que o arquivo .py novo e a edicao das skills movem estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_vnext_claims.py"}
success:
  - id: SC1
    metric: "Criterios de kind test sem vermelho ligado, por feature entregue, com a regra aplicada retroativamente so para medir"
    source: "script de medida do explore, rodado de novo no ship"
  - id: SC2
    metric: "Features entregues que passam no sdd check do repositorio, antes e depois"
    source: "python -m sparkforge.adapters.cli sdd check --repo ."
out_of_scope:
  - "Mutacao por criterio (abordagem C do explore): provaria que o teste falharia se o criterio fosse violado, mas faz o sdd check executar codigo."
  - "Pegar teste que foi vermelho de verdade e cobre pouco (a classe do CONFIG_OCA:AC2): visto vermelho nao e cobre o criterio, e so a abordagem C chega la."
  - "Reescrever o build_report das 12 features entregues."
  - "Criterios de kind command, funcval e fact: o red de tarefa e de pytest."
unknowns: []
change_kinds: [agent_or_skill, claims]
---

# AC_VERMELHO — requisitos

## Problema

O `sparkforge sdd check` confere que o `verified_by` de cada critério existe e tem forma.
Ele não confere que o teste citado **alguma vez falhou** — e teste que nunca falhou não foi
visto verificando nada. Na CONFIG_OCA isso deixou passar um crítico: o `AC4` apontava para
um teste que não olhava o arquivo que o critério descrevia, e passou verde de ponta a ponta.

## O que a regra faz, e o que ela não faz

Ela **pega** o critério que nenhuma tarefa viu vermelho. Medido no explore: 14 de 112
critérios `kind: test` das features entregues, incluindo o `CONFIG_OCA:AC4`.

Ela **não pega** o teste que foi vermelho e cobre pouco — o `CONFIG_OCA:AC2` falhou de
verdade antes do código, e o defeito dele era de alcance. Isso está no `out_of_scope`, com
o nome da abordagem que chegaria lá.

## A guarda de regressão

Um teste que passa antes e depois **pode** ser legítimo: o `SFN_TENTATIVA:AC4` existe para
impedir que "recusar mais" vire "recusar tudo", e nunca fica vermelho por desenho. Proibir
isso seria errado; deixar passar calado é o defeito. A saída é **declarar** — `guard` com
um motivo — e a declaração fica no define, onde a revisão a lê.

## Critérios

- AC1 e AC2 são a regra e o que conta como vermelho.
- AC3 é a guarda.
- AC4 é o que mantém o repositório passando: entregue é histórico.
- AC5 e AC6 são a documentação e os registros.
