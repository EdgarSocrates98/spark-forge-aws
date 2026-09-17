<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `sdd-build`

Use quando o plan.md da feature está ready e é hora de construir — "executa o plano", "implementa a feature", "fase build" — no SparkForge (perfil dev) ou num job do operador (perfil operator, sempre por change sandbox).

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/sdd-build/SKILL.md` |

## Procedimento (texto integral)

## SDD Build

Fase 3b do SDD próprio. Executa o plano tarefa por tarefa, com TDD, e deixa um
relatório que o gate confere: toda tarefa feita declara o comando que falhou
antes do código, toda afirmação aponta evidência, e no perfil operator a mudança
passou por um sandbox.

### A lei

```
NENHUM CÓDIGO DE PRODUÇÃO SEM UM TESTE QUE FALHOU ANTES
```

Código escrito antes do teste é apagado, e a tarefa recomeça pelo teste. Não
vale guardar "como referência" nem "adaptar enquanto escreve o teste".

**Ver falhar** é: rodar o comando, ler a mensagem, e a falha ser pelo motivo
certo — o comportamento ausente, não um erro de digitação no próprio teste. Se o
teste passou de primeira, ele não testa nada novo: pare e revise a tarefa.
Erro de import ou de coleta (`ModuleNotFoundError`, `NameError`) só conta como
vermelho quando o que falta é **a unidade sob teste**; faltando outra coisa (um
auxiliar, um fixture, um typo), o teste está quebrado, não vermelho.

### Antes de começar

1. `sparkforge sdd check --repo . --feature <F>` com o plan em `ready`.
2. Branch de trabalho, nunca a principal.
3. Leia o plano **com olho crítico**, uma vez, e extraia cada tarefa com o texto
   inteiro. Tarefa ambígua, comando que não existe, arquivo fora do manifesto
   ou ordem que não fecha: levante a dúvida ao operador e **pare** — adivinhar
   para seguir é como o plano errado vira código.
4. Copie `docs/sdd/templates/build_report.md` para
   `docs/sdd/<FEATURE>/build_report.md`, com `status: draft`, `upstream.path` no
   plan, e `tasks: []` para ir preenchendo.
5. Abra `docs/gates-por-mudanca.md` nas seções dos `change_kinds` do define: são
   os gates vizinhos de cada tarefa.

### Por tarefa

1. **Vermelho.** Escreva o teste da tarefa. Rode o comando do plano. Veja a
   falha certa. Anote `red: {command, exit}` com o exit **que apareceu**.
2. **Verde.** Escreva o mínimo que faz o teste passar. Rode o mesmo comando.
   Anote `green: {command, exit: 0}`.
3. **Refatore** mantendo verde.
4. **Gates vizinhos.** Rode os comandos da seção da mudança. Vermelho vizinho
   é desta tarefa, não da próxima.
5. **Commit**, um por tarefa. Arquivo novo entra no índice antes dos testes que
   conferem a árvore versionada.
6. **Revisão em dois estágios** (abaixo).
7. Tarefa no relatório com `status: done`.
   **O controlador escreve `red` e `green`** no `build_report.md`, a partir do
   comando e do exit que o subagente relatou ter visto; o subagente não edita
   o relatório. Relato sem exit volta ao subagente.

### Um subagente por tarefa

- **Novo a cada tarefa**, sem herdar o histórico da sessão. Você monta o
  contexto dele; ele não lê o plano sozinho.
- **Cole o texto da tarefa** inteiro no pedido, mais: onde ela se encaixa, as
  decisões do design que a afetam, as regras do repositório que a mordem
  (edição por ferramenta de edição, fim de linha LF, registros manuais).
- **Modelo pelo tamanho:** tarefa mecânica de um ou dois arquivos vai para um
  modelo mais barato; integração e julgamento, para o mais capaz.
- **Nunca dois subagentes escrevendo na mesma árvore ao mesmo tempo.**
- O subagente devolve um de quatro estados:

| estado | o que fazer |
|---|---|
| `DONE` | revisão de spec |
| `DONE_WITH_CONCERNS` | leia as dúvidas; se forem de correção ou escopo, resolva antes da revisão |
| `NEEDS_CONTEXT` | dê o que faltou e despache de novo |
| `BLOCKED` | mais contexto, modelo mais capaz, tarefa menor — ou o plano está errado, e isso sobe ao operador |

Esqueleto do pedido ao implementador:

```
Você implementa a tarefa T<n> da feature <F>.

## Tarefa
<texto inteiro da tarefa, colado>

## Contexto
<onde ela se encaixa; decisões do design; regras do repositório>

## Antes de começar
Pergunte agora o que estiver ambíguo.

## Trabalho
1. Teste primeiro; rode e veja falhar; guarde comando e exit.
2. Código mínimo; rode e veja passar; guarde comando e exit.
3. Gates vizinhos: <comandos>.
4. Commit.
5. Autorrevisão: fez tudo? fez só isso? o teste testa comportamento?

## Relato
Estado (DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED), arquivos,
red {command, exit}, green {command, exit}, dúvidas.
```

### Revisão em dois estágios

1. **Spec.** Um subagente novo recebe o texto da tarefa e o relato do
   implementador, e **não confia no relato**: lê o código. Procura o que falta,
   o que sobra (o que ninguém pediu) e o que foi entendido errado. Devolve
   "conforme" ou a lista com `arquivo:linha`.
2. **Qualidade**, só depois da spec conforme. Outro subagente novo lê o diff
   entre o commit anterior e o atual: uma responsabilidade por arquivo, teste
   que exercita comportamento (não o mock), arquivo que cresceu demais, padrão do
   repositório seguido. Devolve achados classificados em crítico, importante e
   menor.

Achado corrigido volta ao **mesmo** estágio. Revisor lista achados; não dá nota.

### Revisão final

Depois da última tarefa e **antes do ship**, um revisor novo lê o diff inteiro
da feature (do commit do plano até o último) contra o define e o design:
critério sem entrega, tarefas que se contradizem, código duplicado entre
tarefas, registro manual esquecido. Achado crítico ou importante volta ao
build; o resultado entra no corpo do relatório.

### O relatório (`build_report.md`)

- **`tasks`**: `id`, `status` (`done`, `skipped`, `blocked`), `red` e `green`.
  Tarefa `done` sem `red`, ou com `red.exit` igual a zero, sai
  `red_not_declared`.
- **Tarefa sem vermelho próprio** (regenerar referência, lock de superfície):
  o `red` é o gate que falhou **antes** da regeneração, se você o viu falhar.
  Se não viu, `status: skipped` e uma nota no corpo. Exit inventado é o defeito
  mais grave deste relatório.
- **`claims`**: `text` e `evidence_ref` — o node id do teste, o arquivo, o fact.
  Sem evidência, `claim_without_evidence`.
- **Corpo**: desvios do plano com o motivo, decisões tomadas sozinho com a
  alternativa que ficou de fora, e os achados das revisões.
- Com o relatório em `ready` ou `done`, todo teste citado no define e no plan
  **precisa existir**: o que faltar sai `verified_by_dangling`.

Feche pelo laço de `docs/sdd/README.md#o-laço-de-cada-fase`:
`sparkforge sdd stamp --repo . docs/sdd/<F>/build_report.md` e
`sparkforge sdd check --repo . --feature <F>`. Zero recusa e zero lacuna →
`status: done`.

### Conhecimento durante o build

Antes de mexer num símbolo, `sparkforge code symbol <node_id>` diz quem o chama.
O resto: `docs/sdd/README.md#conhecimento-citado-nunca-memória`.

### Perfil operator

A sessão **nunca** escreve na árvore do operador. Spec e evidências moram em
`.sparkforge/sdd/<F>/` (a cópia do sandbox poda `.sparkforge`). Siga
`docs/sdd/README.md#caminho-da-mudança-do-operador`; os três passos que mais
erram:

- `sparkforge change sandbox --repo . --diff d.patch`: o `id` vai para
  `change_id`. Id fora de `.sparkforge/sandbox/` e de `.sparkforge/proposal/`
  sai `change_missing`. Achado novo P0 ou P1: pare e volte ao design.
- `funcval compare ... --out <ref do AC>` e `benchmark ... --out bench.json`:
  sem o `--out`, a evidência não existe para o gate.
- `change propose --sandbox <id> --repo . --funcval <cmp.json> --benchmark bench.json`:
  sem as duas flags, o pacote diz PENDENTE.

Registro por tarefa:

- Tarefa com `test`: `red` é o teste rodado antes do sandbox; `green`, o mesmo
  teste depois do compare.
- Tarefa com `proof`, sem pytest: `moved: {change_id: <id>, resolved: [<rule_id>...]}`
  no lugar de `red` e `green`, com o **mesmo** `change_id` do relatório
  (outro sai `moved_change_mismatch`). O gate lê
  `.sparkforge/sandbox/<id>/report.json` (ou
  `.sparkforge/proposal/<id>/evidence/sandbox_report.json`) e exige cada
  regra em `resolved` e fora de `new`; senão, `moved_not_observed`. No dev,
  `moved` é `schema_invalid`.

Feche com `sparkforge sdd check --repo . --root .sparkforge/sdd --feature <F>`.
O `case_id` é o de `sparkforge case open` (`.sparkforge/case.yaml`).

### Verificação antes de fechar

Rode de novo, agora, os comandos que provam o que o relatório afirma. "Deve
passar" e "passou antes da última edição" não são evidência. Todo
`verified_by` de `kind: command` do define roda aqui e precisa sair com
exit 0. A suíte inteira roda em lotes, um por vez
(`tests/test_suite_batches.py`, constante `LOTES`).

### Quando NÃO usar

- Plan em `draft`, ou tarefa sem teste: volte a `sdd-plan`.
- Para decidir arquitetura no meio do build: pare, volte a `sdd-design`, e deixe
  a cascata marcar o que ficou velho.
- Para aplicar mudança direto no job do operador ou em produção.
- Para fechar a feature e rodar os registros: `sdd-ship`.

### Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| conferir o plan | `sparkforge sdd check --repo . --feature <F>` | `sparkforge_sdd_check` |
| quem chama | `sparkforge code symbol <node_id>` | `sparkforge_code_symbol` |
| carimbar o relatório | `sparkforge sdd stamp --repo . docs/sdd/<F>/build_report.md` | `sparkforge_sdd_stamp` |
| diff (operator) | `sparkforge change plan --facts <f> --set k=v --out d.patch` | `sparkforge_change_plan` |
| sandbox (operator) | `sparkforge change sandbox --repo . --diff d.patch` | `sparkforge_change_sandbox` |
| semântica (operator) | `sparkforge funcval compare --plan <p> --before <a> --after <b> --out <ref do AC>` | `sparkforge_funcval_compare` |
| desempenho (operator) | `sparkforge benchmark --before <a> --after <b> --out bench.json` | `sparkforge_benchmark` |
| pacote do PR (operator) | `sparkforge change propose --sandbox <id> --repo . --funcval <cmp.json> --benchmark bench.json` | `sparkforge_change_propose` |

Recusas desta fase: `red_not_declared`, `claim_without_evidence`,
`change_missing`, `moved_not_observed`, `moved_change_mismatch`,
`verified_by_dangling`, `upstream_stale`. Contrato completo:
`docs/sdd/CONTRATO.md`. Template: `docs/sdd/templates/build_report.md`.

### Red flags

- Código antes do teste, "só desta vez".
- `red.exit` escrito sem ter rodado o comando, ou copiado do `green`.
- Teste que passou de primeira e ficou assim.
- Subagente que recebeu "leia o plano" em vez do texto da tarefa.
- Revisão de qualidade antes da de spec, ou revisor que dá nota.
- Dois subagentes editando a mesma árvore.
- "Deve passar" no lugar da saída do comando.
- Arquivo do operador editado fora do sandbox.
- Claim sem `evidence_ref`, ou ganho de desempenho afirmado sem medida.
