# Grafo de tarefas e ergonomia do plano

Referência da skill `sdd-plan`. O schema do `plan.md` cobre `id`, `files`,
`covers`, `test`/`proof`; os campos do grafo moram **na seção `## T<n>` do
corpo** — campo novo no frontmatter sai `schema_invalid` hoje, e migra para
o schema quando o engine formalizá-lo.

## Os campos do grafo

| campo | forma | regra |
|---|---|---|
| `depends_on` | `[T<n>, ...]` | só tarefas que vêm antes no plano; ciclo e autorreferência não valem |
| `parallel_safe` | `true` | só com `write_scope` disjunto, teste sem estado compartilhado, nenhuma dependência mútua |
| `risk` | `low` \| `medium` \| `high` | `high` = caminho crítico, formato persistido ou contrato público; `high` não vai para modelo barato |
| `write_scope` | lista de caminhos | contém `files`; o executor para ao sair dele |
| `blocking` | `true` | outra tarefa ou gate depende dela — entra cedo |
| `proof` | `{kind, ref}` | o campo do schema (operator); o grafo só repete a regra |
| `decisions_needed` | lista de perguntas | pergunta que volta ao define/design; nunca respondida no plano |
| dependências externas | texto | permissão, quota, serviço de terceiro — com `unlock` |
| checkpoint | o commit da tarefa | retomada lê o estado antes de escrever |
| esforço/custo | texto com fonte | só com evidência; estimativa não entra |

## Paralelismo seguro — os quatro testes

Duas tarefas só rodam juntas quando **as quatro** condições valem:

1. `parallel_safe: true` nas duas;
2. `write_scope` disjunto — nenhum caminho em comum, nem diretório;
3. nenhuma dependência entre elas (`depends_on` dos dois lados);
4. nenhum registro manual compartilhado (a mesma tabela de despacho, o
   mesmo lock).

Na dúvida, serial. Dois writers na mesma árvore ao mesmo tempo é defeito
que o plano prevê e o build executa — não acidente de execução.

## Checkpoints e retomada idempotente

- O commit de cada tarefa é o checkpoint: interrupção retoma dele, nunca
  do meio.
- Tarefa reexecutada lê o estado **antes** de escrever: o teste existe? o
  diff está aplicado? Idempotente é a tarefa que detecta o que já fez em
  vez de fazer de novo.
- Tarefa que não consegue ser idempotente (migração destrutiva, registro
  de uma vez) declara o porquê e o ponto de no-return.

## Ergonomia — os seis papéis do conteúdo

"Código inteiro" era a regra de ouro quando toda tarefa era código novo.
Com registros, regenerações e mecânica repetitiva no cardápio, a regra
virou: **o papel declara a forma, a verificabilidade não se negocia**.

| papel | forma | verificável por |
|---|---|---|
| código de contrato | literal, completo | o teste + o gate do schema |
| interface | assinatura exata, corpo só quando muda | quem a implementa não inventa a fronteira |
| pseudocódigo | algoritmo em prosa estruturada | o teste executável continua completo |
| exemplo | marcado `exemplo` | nunca conta como spec; não gera `red` |
| instrução | verbo + arquivo + símbolo + gate vizinho | o gate que falha antes e passa depois |
| teste executável | completo, com node id | é o `red` da tarefa |

Regras duras da flexibilização:

1. O que é contrato continua literal — schema, envelope, assinatura
   pública, formato de saída. Omissão em contrato é defeito, não
   ergonomia.
2. Instrução só vale com trilha: arquivo, símbolo, e o gate vizinho que
   falha antes e passa depois. "Adicione o campo `mode` ao dict de
   saída em `x.py::to_report`" é instrução; "ajuste a saída" é
   placeholder.
3. Subagente executa sem contexto: cada forma diz o suficiente para
   produzir o resto sem inventar. Se a forma exige que ele adivinhe, a
   forma está errada — não ele.
4. Boilerplate repetido entre tarefas vira referência por símbolo ("o
   mesmo wrapper de `x.py::run`"), nunca "igual a T2" nem cópia nova
   divergente.
5. Esforço e custo só com evidência: medida, execução anterior
   comparável, ou declaração explícita de que não há base — que é
   informação, não número.
