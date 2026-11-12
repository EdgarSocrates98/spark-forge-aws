---
name: sdd-plan
description: "Use quando o design.md da feature está ready e falta quebrar a construção em tarefas pequenas, com teste e código, que outra sessão execute sem contexto — \\\"escreve o plano\\\", \\\"quebra em tarefas\\\", \\\"fase plan\\\"."
metadata:
  sparkforge_aws_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - references/task-graph.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../docs/sdd/README.md
  - ../../docs/sdd/CONTRATO.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge-aws sdd check
  - sparkforge-aws code search
  - sparkforge-aws sdd stamp
---

# SDD Plan

Fase 3a do SDD próprio. Escreve o plano para quem vai executá-lo **sem contexto
nenhum** do repositório: um subagente novo, outra sessão, outra pessoa. Tudo o
que ele precisa está na tarefa — arquivos exatos, teste, comando, código. O
`sparkforge-aws sdd check` confere que toda tarefa nomeia seu teste e que todo
critério do define tem tarefa.

## Antes de começar

1. `sparkforge-aws sdd check --repo . --feature <F>` com o design em `ready`.
2. Leia o manifesto e as decisões do design: o plano não inventa arquivo que o
   design não listou. Se precisar de um, volte ao design (e à cascata).
3. Copie `docs/sdd/templates/plan.md` para `docs/sdd/<FEATURE>/plan.md`, com
   `status: draft` e `upstream.path` no design da feature.

## A tarefa

No frontmatter, cada tarefa tem `id` `T<n>`, `files`, `covers` (os `AC` do
define) e `test` com `path` e `name`. Tarefa sem `test` sai `task_without_test`
(no perfil operator, `proof` também serve; veja abaixo). `name` é o node id do
pytest sem o arquivo: `test_x`, ou `TestClasse::test_x` para método de classe.
O sufixo `[...]` do parametrize é descartado antes da conferência; escreva o
nome da função.

No corpo, cada tarefa é uma seção `## T<n> — título` com passos de poucos
minutos cada:

1. **Escrever o teste que falha** — o código do teste inteiro, num bloco.
2. **Rodar e ver falhar** — o comando exato e a falha esperada
   (`AssertionError` sobre o campo X; `ModuleNotFoundError` só quando o módulo
   ausente é a unidade sob teste).
3. **Código mínimo** — o código inteiro, num bloco, com o caminho do arquivo.
4. **Rodar e ver passar** — o mesmo comando.
5. **Gates vizinhos** — os comandos da seção de `docs/gates-por-mudanca.md` que a
   tarefa toca.
6. **Commit** — um por tarefa, com a mensagem.

Tarefa sem teste próprio (regenerar referência, atualizar lock de superfície)
nomeia como `test` o gate que falha antes da regeneração, por exemplo
`tests/test_reference_docs.py::test_referencia_em_dia`. É esse vermelho que o
build vai registrar.

Ordem de dependência: a tarefa que cria uma coisa também move os registros
manuais dela. Deixar os registros para uma tarefa final é o jeito mais comum de
um vermelho atravessar vários commits.

## Sem placeholder

Nada disto entra no plano:

- "TBD", "TODO", "implementar depois", "preencher".
- "Tratar os erros", "validar a entrada", "cobrir os casos de borda" sem o código.
- "Escrever os testes" sem o teste.
- "Igual a T2" — repita o código; quem executa pode ler as tarefas fora de ordem.
- Função, tipo ou flag que nenhuma tarefa define e o repositório não tem.
- Comando que ninguém rodou: confirme com `sparkforge-aws <verbo> --help` ou
  `sparkforge-aws code search`.

## O grafo de tarefas

O plano também é um grafo. Além de `id`, `files`, `covers` e `test`/`proof`,
cada tarefa registra **na seção `## T<n>` do corpo** — campo novo no
frontmatter sai `schema_invalid` hoje; o schema formaliza depois (contrato
em `references/task-graph.md`):

- **`depends_on`** — as tarefas que precisam terminar antes. A ordem do
  plano já expressa o essencial; `depends_on` registra o que ela não diz
  (T5 depende de T2 mesmo vindo depois de T4).
- **`parallel_safe`** — `true` só com `write_scope` disjunto, teste que não
  compartilha estado e nenhuma dependência entre as tarefas.
- **`risk`** — `low|medium|high`. Caminho crítico, formato persistido ou
  contrato público é `high`, e `high` não vai para modelo barato.
- **`write_scope`** — os caminhos que a tarefa pode escrever; fora dele,
  para. O `files` do schema continua sendo a lista que o gate vê; o escopo
  é o limite que o executor respeita.
- **`blocking`** — `true` quando outra tarefa ou gate depende dela: entra
  cedo, não no fim.
- **`decisions_needed`** — perguntas que voltam ao define/design; plano não
  absorve decisão, ele a lista.
- **dependências externas** — permissão AWS, quota, serviço de terceiro:
  nomeadas, com o `unlock` que as resolve.
- **checkpoint** — o commit da tarefa é o ponto de retomada; tarefa
  reexecutada lê o estado (o teste, o diff) antes de escrever, não de novo.
- **esforço/custo** — só com evidência (medida, execução anterior
  comparável); estimativa de corredor não entra.

Paralelismo seguro é exigência, não conveniência: `parallel_safe` das duas
tarefas, `write_scope` disjunto, nenhuma dependência entre elas, nenhum
registro manual compartilhado. Na dúvida, serial — dois writers na mesma
árvore é defeito do build, não do plano.

Priorização: `blocking` primeiro, depois `risk` alto, depois o caminho
crítico. Tarefa de registro manual viaja com a tarefa que a cria — já diz a
regra da dependência.

## Ergonomia do código na tarefa

"Código inteiro" é meio, não fim — o fim é o subagente executar **sem
contexto** e sem inventar. Cada bloco declara o papel (tabela completa em
`references/task-graph.md`):

| papel | quando | o que mantém verificável |
|---|---|---|
| contrato | o código **é** o contrato (schema, envelope, assinatura pública) | literal e completo, sempre |
| interface | a fronteira entre módulos | assinatura exata; corpo só quando muda |
| pseudocódigo | a lógica é algorítmica e o teste a prende | o teste executável continua completo |
| exemplo | ilustra uso | marcado `exemplo`, nunca conta como spec |
| instrução | mecânica sem ambiguidade | arquivo + símbolo + gate vizinho que o prova |
| teste executável | sempre | completo, com o node id |

Toda flexibilização preserva verificabilidade: instrução vale porque o
arquivo, o símbolo e o teste a prendem; "verifique o óbvio" e "ajuste o que
precisar" são placeholder com outro nome e não entram. Repetição cara entre
tarefas (o mesmo boilerplate colado quatro vezes) vira referência por id de
símbolo, nunca "igual a T2".

## Cobertura

Todo `AC` do define aparece no `covers` de alguma tarefa. O que faltar sai
`acceptance_uncovered`.

## Autorrevisão

Antes de pedir revisão ao operador, releia o plano contra o define e o design:

1. **Cobertura** — cada critério e cada item do manifesto têm tarefa?
2. **Placeholder** — alguma frase da lista acima escapou, ou um bloco de
   código perdeu o papel declarado (contrato, interface, instrução...)?
3. **Consistência de nomes** — a função chamada em T4 é a que T2 definiu?
4. **Comandos reais** — todo `sparkforge-aws <verbo>` citado aceita os argumentos
   escritos?
5. **O grafo fecha** — `depends_on` aponta para tarefas que existem e vêm
   antes; nenhuma tarefa `parallel_safe` divide `write_scope` ou teste com
   outra; `decisions_needed` não tem resposta embutida (decisão respondida
   no plano é decisão roubada do operador)?
6. **Escopo** — `files` dentro do `write_scope` declarado e nenhum caminho
   fora do manifesto do design?

Corrija no lugar. Isso é checagem sua, não nota.

## O laço

O de `docs/sdd/README.md#o-laço-de-cada-fase`, com a autorrevisão antes do
stamp: `sparkforge-aws sdd stamp --repo . docs/sdd/<F>/plan.md` e
`sparkforge-aws sdd check --repo . --feature <F>`. Aqui `test_not_written` para
cada tarefa é esperado (o teste nasce no build); recusa não é. Próximo passo:
`sdd-build`.

## Perfil operator

- As tarefas seguem `docs/sdd/README.md#caminho-da-mudança-do-operador`;
  nenhuma tarefa edita a árvore do operador direto. O plano mora em
  `.sparkforge_aws/sdd/<F>/plan.md`:
  `sparkforge-aws sdd stamp --repo . --root .sparkforge_aws/sdd .sparkforge_aws/sdd/<F>/plan.md`.
- Toda tarefa prova alguma coisa. Com pytest sobre as funções puras do job, é
  `test`. Sem ele, a tarefa declara `proof` no lugar:

  | `proof.kind` | `proof.ref` | o que o check faz |
  |---|---|---|
  | `funcval` | o arquivo de `funcval compare --out` | o mesmo do define: `funcval_not_run`, `funcval_not_comparison`, `funcval_blind_spot` |
  | `fact` | `<facts.json>#kind:<kind>` (ou `#<id>`) | `fact_not_collected` até a coleta |
  | `finding` | `<change_id>#<rule_id>`, ou `#<rule_id>` para o `change_id` do build | lacuna `finding_not_observed` até o sandbox mostrar a regra em `resolved` e fora de `new`; com o build pronto, recusa `moved_not_observed` |

  Prefira `#<rule_id>`: o id do sandbox é hash e não existe na hora do plano.
  No perfil dev, `proof` é `schema_invalid` e `test` segue obrigatório.

## Quando NÃO usar

- Design em `draft`, ou manifesto sem os registros que a mudança move: volte a
  `sdd-design`.
- Para executar as tarefas: `sdd-build`.
- Para mudança de uma linha já coberta por teste existente: um plano de uma
  tarefa basta, mas ele existe.

## Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| conferir o design | `sparkforge-aws sdd check --repo . --feature <F>` | `sparkforge_aws_sdd_check` |
| confirmar um nome | `sparkforge-aws code search <nome>` | `sparkforge_aws_code_search` |
| carimbar | `sparkforge-aws sdd stamp --repo . docs/sdd/<F>/plan.md` | `sparkforge_aws_sdd_stamp` |
| cascata | `sparkforge-aws sdd status --repo .` | `sparkforge_aws_sdd_status` |

Recusas desta fase: `phase_out_of_order`, `task_without_test`,
`acceptance_uncovered`, `upstream_stale`, `moved_not_observed` (operator).
Template: `docs/sdd/templates/plan.md`.

## Red flags

- Tarefa com "e depois ajustar o que precisar".
- Bloco de código com `...` no lugar do corpo, ou sem o papel declarado.
- Teste descrito em prosa em vez de escrito.
- Tarefa de uma hora que devia ser três.
- Registros manuais empurrados para a última tarefa.
- Plano carimbado com o design em `upstream_stale`.
- `parallel_safe` declarado onde duas tarefas escrevem o mesmo arquivo ou
  dividem o mesmo teste.
- `depends_on` inventado no frontmatter (o schema ainda não o aceita) ou
  apontando para tarefa que vem depois.
- Esforço ou custo estimado sem medida nem execução anterior comparável.
- Decisão respondida dentro do plano em vez de listada em
  `decisions_needed` e levada ao operador.
- Dependência externa (permissão, quota, serviço) absorvida sem `unlock`.
- Instrução sem arquivo, símbolo e gate — "instrução" que é placeholder.


## Contrato de qualidade SparkForge (v1)

Esta skill trata **plano executável com testes e cobertura SDD**. Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.
- **Verbos primários:** `sparkforge-aws sdd check`, `sparkforge-aws code search`, `sparkforge-aws sdd stamp`. Use-os na ordem indicada pela skill e conserve saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.
- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.
- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.
- **Referências e eval:** `../_shared/references/evidence-first.md`, `../_shared/references/evaluation-contract.md`, `../_shared/references/operational-safety.md`, `../../docs/sdd/README.md`, `../../docs/sdd/CONTRATO.md`; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.
