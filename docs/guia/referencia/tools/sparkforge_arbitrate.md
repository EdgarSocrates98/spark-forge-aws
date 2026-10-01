<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_arbitrate`

**Efeito:** Grava em disco local e muda o estado a cada chamada (repetir não é igual a chamar uma vez).

## O que faz

Executor agentico DETERMINISTICO. Roda DEPOIS de `sparkforge_judge`, sobre findings ja julgados, e nao reavalia regra nenhuma: o que ele decide e o que o julgamento deixou em aberto -- conflito entre dois achados que movem a MESMA propriedade em direcoes opostas, lastro suficiente para uma afirmacao virar recomendacao, qual medida falta para fechar a lacuna, e em que ordem as acoes podem ser aplicadas. Grava `Claim`, `Evidence`, `Contradiction`, `Objection`, `Unknown`, `Experiment` e `Decision` no blackboard do case (`<repo>/.sparkforge/blackboard/`), mais um ADR por decisao significativa. Recebe `findings` inline ou `findings_path`, e `facts` inline ou `facts_path` -- que aceita uma LISTA de caminhos, e a lista e o ponto: o executor precisa da UNIAO dos facts do case, o MESMO conjunto que `judge` recebeu. Alimenta-lo com um subconjunto fabrica claim desancorada que a execucao real nao produz, e o gate de lastro a reprova por ausencia de medida. Fact sem `id` tem o id computado pelo conteudo. O QUE ELA NAO FAZ, e isto e contrato e nao ressalva: (1) nao estima ganho -- afirmar quanto se economiza exige o custo do run que NAO aconteceu, e ele nao existe; (2) nao publica score de arbitragem como confianca medida -- os pesos de `assess_claim` (evidencia 40%, autoridade 30%, especificidade 20%, aplicabilidade 10%) sao CONVENCAO e nenhum experimento os calibrou; eles ordenam claims dentro de uma arbitragem e o valor absoluto nao sai na resposta, so o desfecho; (3) nao executa debate -- quando a arbitragem nao fecha, sai um PLANO em `debate_plans`, com `executed: false` e `unresolved.reason: debate.unresolved`. Quem debateria e um `AgentRuntime` concreto, do host: `sparkforge/` nao chama provider nenhum. Cada plano traz `debate_gate` (Debate ROI Gate): `experimentar_antes` quando ha lacuna mensuravel citando o par, `debater` com severidade na politica, acao irreversivel ou arbitragem sem lastro, `nao_debater` quando tudo e conhecido e nada disso casa, e `unresolved` nomeando o sinal que falta; `expected_information_gain` sai recusado, sem fonte. Autonomia L0: escreve decisao e NUNCA aplica mudanca. O ADR e proposta com `rollback` obrigatorio, nao registro de coisa feita -- `applied_changes` sai sempre `false`. `persisted: false` nao e falha da chamada: a resposta e montada antes da gravacao e o que falhou sai nomeado em `persistence.errors`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do case. O blackboard e os ADRs ficam em `<repo>/.sparkforge/blackboard/` -- ADR de case viaja com o case, nunca em `docs/`. |
| `athena` | string | não |  |
| `databricks` | string | não | Versao do Databricks Runtime ('15.4' ou '15.4.x-scala2.12'). DECLARACAO, nao observacao: perde para o event log, e discordar vira divergencia reportada em `runtime.divergences`. |
| `emr` | string | não | Release do EMR on EC2, nas duas grafias ('emr-7.5.0' ou '7.5.0'). DECLARACAO, nao observacao: perde para o event log e para um dump de describe-cluster, e discordar de um deles vira divergencia reportada em `runtime.divergences`, nunca valor substituido em silencio. |
| `facts` | array de object | não |  |
| `facts_path` | string ou array de string | não | Um caminho, ou varios: os facts sao unidos e deduplicados por id antes de arbitrar. A UNIAO e obrigatoria -- ver a descricao. |
| `findings` | array de object | não |  |
| `findings_path` | string | não | Arquivo gerado por `sparkforge judge --out`. Aceita a lista nua e o objeto com a chave `findings` (ou `items`). |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `photon` | string: `on`, `off` | não | Photon ligado ou desligado no Databricks. Com 'on', regra de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (plan.photon) faz o mesmo sem declaracao e vence 'off', que vira divergencia 'photon:'. Sem databricks, vira divergencia 'photon:'. |
| `python` | string | não |  |
| `spark` | string | não |  |

## Na CLI

[`sparkforge arbitrate`](../cli/arbitrate.md)

## Capacidade

arbitrate already-judged findings and decide what the judgement left open

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `false` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
