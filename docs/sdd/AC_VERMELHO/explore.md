---
sdd: 1
feature: AC_VERMELHO
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Derivar a ligacao do que ja existe: todo acceptance de kind test precisa de uma tarefa do plan que o cubra (covers) com red.exit diferente de zero rodando o node id dele no build_report. Guarda de regressao se DECLARA no define (campo novo no acceptance, com motivo) e fica isenta. Recusa nova acceptance_never_red."
    tradeoffs:
      - "sem campo novo no build_report: a ligacao AC -> tarefa -> red ja existe via covers"
      - "pega a classe do CONFIG_OCA:AC4, um dos dois criticos da feature anterior"
      - "NAO pega a classe do CONFIG_OCA:AC2: aquele teste ficou vermelho de verdade e cobria pouco. Visto vermelho nao e o mesmo que cobre o criterio"
      - "exige mudar o schema do define, que hoje tem additionalProperties false no acceptance"
  - id: B
    summary: "Campo novo no build_report, acceptance_red, com comando e exit por criterio."
    tradeoffs:
      - "explicito de ler"
      - "mais escrituracao por feature, e mais um lugar para exit inventado, que e o defeito mais grave do build_report"
  - id: C
    summary: "Mutacao declarada por criterio, que o ship executa e que precisa deixar o teste vermelho."
    tradeoffs:
      - "prova a propriedade real -- o teste falharia se o criterio fosse violado -- e pegaria os dois criticos"
      - "faz o sdd check, que hoje so le frontmatter, passar a executar codigo; muda a natureza do gate"
chosen: A
---

# AC_VERMELHO — exploração

## Origem

Cinco features seguidas tiveram critério verificado por teste que não cobria o que o
critério afirmava, e o `sparkforge sdd check` passou em todas: ele confere que o
`verified_by` existe e tem forma, não que o teste mede o critério. Na CONFIG_OCA (#95)
isso produziu os dois críticos. Pedido do operador em 2026-09-21.

## Perfil

`dev`.

## Medido nesta árvore (2026-09-21, `main` em `ed90f77f`)

Sobre as 12 features com `define`, `plan` e `build_report`, ligando cada critério
`kind: test` ao `red` das tarefas do plano que o cobrem (`covers`), por **arquivo** do
teste:

- **112** critérios `kind: test`; **14** sem vermelho ligado:
  `AIRFLOW_DAG` AC3, AC4, AC5, AC8; `CONFIG_OCA` AC4; `CRITERIO_DE_DOMINIO` AC7;
  `GLUE_TERRAFORM` AC4; `SDD_ENDURECIMENTO` AC8; `SF_STUBS` AC5; `SFN_HISTORY` AC8;
  `STEP_FUNCTIONS` AC3, AC4, AC5, AC8.
- O **`CONFIG_OCA:AC4`** está entre eles — é um dos dois críticos. A abordagem A o pegaria.
- O **`CONFIG_OCA:AC2`** não está: o teste dele foi vermelho de verdade. A abordagem A não
  o pegaria, e isso fica declarado.
- **Ligação por arquivo é frouxa.** O `SFN_TENTATIVA:AC4`, guarda de regressão que passa
  antes e depois por desenho, **escapou** da lista porque o `red` da T2 rodou o arquivo
  inteiro. Ligação por **node id** o pegaria — e é exatamente o caso que precisa de guarda
  declarada.

Onde o código mora: `sparkforge/sdd/checks.py::_gate_red` (hoje só exige `red.exit != 0`
por tarefa) e `sparkforge/sdd/schema/define.json` (o item de `acceptance` tem
`additionalProperties: false`).

## Perguntas feitas

1. Qual abordagem? Resposta (2026-09-21): A.

## Abordagens

A é a recomendada porque usa a ligação que já existe e pega a classe de defeito medida.
C é a que prova a propriedade certa, e fica registrada como o próximo passo se A se mostrar
insuficiente: ela exige que o SDD execute código, e isso é decisão maior que esta feature.

## O que o define precisa decidir

- **As 12 features entregues.** Aplicado a elas, o gate quebra o `sdd check` do repositório
  inteiro. O precedente da casa é o do perfil operator: com o `ship` em `done`, o que ele cita
  vira histórico. Aplicar só a feature cujo `ship` não está `done` mantém a regra 21 — fechar
  é acréscimo, não reescrita.
- **Arquivo ou node id.** O `red` de uma tarefa costuma rodar o arquivo inteiro. `exit 2` do
  pytest é erro de coleta, que deixa o arquivo todo vermelho; `exit 1` é teste falhando, e aí
  não se sabe qual. A regra precisa dizer o que conta.
