---
name: sdd-plan
description: Use quando o design.md da feature está ready e é hora de quebrar a construção em tarefas executáveis — "escreve o plano", "quebra em tarefas", "fase plan". Grava docs/sdd/<FEATURE>/plan.md com tarefas pequenas, cada uma com o teste que falha antes, os arquivos, os critérios que cobre e o código completo no corpo, sem placeholder, e fecha com sparkforge sdd stamp e sparkforge sdd check.
---

# SDD Plan

Fase 3a do SDD próprio. Escreve o plano para quem vai executá-lo **sem contexto
nenhum** do repositório: um subagente novo, outra sessão, outra pessoa. Tudo o
que ele precisa está na tarefa — arquivos exatos, teste, comando, código. O
`sparkforge sdd check` confere que toda tarefa nomeia seu teste e que todo
critério do define tem tarefa.

## Antes de começar

1. `sparkforge sdd check --repo . --feature <F>` com o design em `ready`.
2. Leia o manifesto e as decisões do design: o plano não inventa arquivo que o
   design não listou. Se precisar de um, volte ao design (e à cascata).
3. Copie `docs/sdd/templates/plan.md` para `docs/sdd/<FEATURE>/plan.md`, com
   `status: draft` e `upstream.path` no design da feature.

## A tarefa

No frontmatter, cada tarefa tem `id` `T<n>`, `files`, `covers` (os `AC` do
define) e `test` com `path` e `name`. Tarefa sem `test` sai `task_without_test`.

No corpo, cada tarefa é uma seção `## T<n> — título` com passos de poucos
minutos cada:

1. **Escrever o teste que falha** — o código do teste inteiro, num bloco.
2. **Rodar e ver falhar** — o comando exato e a falha esperada
   (`ModuleNotFoundError`, `AssertionError` sobre o campo X).
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
- Comando que ninguém rodou: confirme com `sparkforge <verbo> --help` ou
  `sparkforge code search`.

## Cobertura

Todo `AC` do define aparece no `covers` de alguma tarefa. O que faltar sai
`acceptance_uncovered`.

## Autorrevisão

Antes de pedir revisão ao operador, releia o plano contra o define e o design:

1. **Cobertura** — cada critério e cada item do manifesto têm tarefa?
2. **Placeholder** — alguma frase da lista acima escapou?
3. **Consistência de nomes** — a função chamada em T4 é a que T2 definiu?
4. **Comandos reais** — todo `sparkforge <verbo>` citado aceita os argumentos
   escritos?

Corrija no lugar. Isso é checagem sua, não nota.

## O laço

1. Escreva tarefas e corpo com `status: draft`.
2. Autorrevisão.
3. `sparkforge sdd stamp --repo . docs/sdd/<F>/plan.md`.
4. `sparkforge sdd check --repo . --feature <F>`. Aqui `test_not_written` para
   cada tarefa é esperado: o teste nasce no build. Recusa não é.
5. `status: ready` com zero recusa, depois da leitura do operador.
6. Próximo passo: `sdd-build`.

## Perfil operator

- As tarefas seguem o caminho do change: `sparkforge funcval plan` antes da
  mudança, `sparkforge change plan` para gerar o diff, `sparkforge change sandbox`
  para aplicá-lo numa cópia, `sparkforge benchmark` e `sparkforge funcval compare`
  para medir, e a skill `propose-change-pr` para o PR.
- Nenhuma tarefa edita a árvore do operador direto.
- O gate ainda exige `test` em toda tarefa. No operador ele aponta a checagem
  que falha antes da mudança: pytest sobre as funções puras do job, se houver;
  senão, um teste que o build cria nos `tests/` do repositório do operador e que
  afirma o desfecho do `sparkforge funcval compare` ou dos achados `SF-FVAL`.

## Quando NÃO usar

- Design em `draft`, ou manifesto sem os registros que a mudança move: volte a
  `sdd-design`.
- Para executar as tarefas: `sdd-build`.
- Para mudança de uma linha já coberta por teste existente: um plano de uma
  tarefa basta, mas ele existe.

## Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| conferir o design | `sparkforge sdd check --repo . --feature <F>` | `sparkforge_sdd_check` |
| confirmar um nome | `sparkforge code search <nome>` | `sparkforge_code_search` |
| carimbar | `sparkforge sdd stamp --repo . docs/sdd/<F>/plan.md` | `sparkforge_sdd_stamp` |
| cascata | `sparkforge sdd status --repo .` | `sparkforge_sdd_status` |

Recusas desta fase: `phase_out_of_order`, `task_without_test`,
`acceptance_uncovered`, `upstream_stale`. Template: `docs/sdd/templates/plan.md`.

## Red flags

- Tarefa com "e depois ajustar o que precisar".
- Bloco de código com `...` no lugar do corpo.
- Teste descrito em prosa em vez de escrito.
- Tarefa de uma hora que devia ser três.
- Registros manuais empurrados para a última tarefa.
- Plano carimbado com o design em `upstream_stale`.
