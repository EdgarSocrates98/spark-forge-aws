<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `sdd-define`

Use quando a abordagem já está escolhida, ou o pedido já é claro, e falta fixar o que significa pronto — "define os requisitos", "quais os critérios de aceite?", "fase define" — para uma mudança no SparkForge ou num job do operador.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/sdd-define/SKILL.md` |

## Procedimento (texto integral)

## SDD Define

Fase 1 do SDD próprio. Fixa **o que** a feature entrega e **como se prova** que
entregou, antes de qualquer arquivo ser desenhado. O `sparkforge sdd check`
confere que cada campo tem a forma certa e aponta para algo real; ele não julga
se o requisito é bom. Isso é do operador.

### Antes de começar

1. `sparkforge sdd status --repo .` e, se existir, `docs/sdd/<FEATURE>/explore.md`
   com `status: ready`. A abordagem escolhida lá é a premissa daqui.
2. Copie `docs/sdd/templates/define.md` para `docs/sdd/<FEATURE>/define.md` e
   ponha `status: draft`.
3. Sem `explore.md` na feature, apague o bloco `upstream` inteiro: define sem
   explore não declara upstream (o check recusa com `schema_invalid`).

### Campo por campo

**`hypothesis`** — `claim`, `prediction` e `experiment`, os três juntos. A
previsão é falsificável (diz o que se observa se a afirmação estiver errada),
**mensurável no ship** (cada parte tem medida que o ship consegue rodar; parte
que só se mede depois vira feature própria, não promessa) e o experimento diz o
que vai rodar. É esta hipótese que o ship fecha, sem reescrevê-la.

**`acceptance`** — um item por critério, `id` `AC<n>`, uma frase verificável e
um `verified_by`:

| `kind` | `ref` | o que o check faz |
|---|---|---|
| `test` | node id do pytest, `tests/arquivo.py::test_nome` | antes do build, teste ausente é lacuna `test_not_written`; com o build `ready` ou `done`, é recusa `verified_by_dangling` |
| `command` | o comando cujo exit 0 prova o critério | registra; quem roda é o ship |
| `funcval` | o arquivo de `sparkforge funcval compare --out` | lacuna `funcval_not_run` até existir; sem `funcval.check_delta`, recusa `funcval_not_comparison`; cada `funcval.unresolved`, lacuna `funcval_blind_spot` |
| `fact` | `arquivo.json#fact_id` ou `arquivo.json#kind:<kind>` | lacuna `fact_not_collected` até a coleta |

Prefira `test`. Critério que nada verifica é desejo, e não entra.

**`kind: test` precisa ser visto vermelho.** No perfil `dev`, com o build pronto e
o ship fora de `done`, o check exige uma tarefa do plan com o AC em `covers` cujo `red`, no
build_report, tenha exit diferente de zero e cite o node id do `verified_by` — ou só
o arquivo, com exit 2 (erro de coleta). Sem isso, `acceptance_never_red`. A exceção é
a **guarda de regressão**, o teste que passa antes e depois por desenho (o que impede
"recusar mais" de virar "recusar tudo"): declare `guard: "<o motivo>"` no item. O
motivo é o que a revisão lê; `guard` vazio é `schema_invalid`.

**`success`** — `metric` e `source`, sempre. O `source` diz de onde vem o número
(o comando, o arquivo, o fact). Sem ele, `success_without_source`. Token de
provider só com transcript do host; dólar só com `cost_basis` nomeado.

**`out_of_scope`** — o que fica fora, por escrito. É o que segura o design.

**`unknowns`** — `id` `U<n>`, os critérios que a lacuna `blocks`, e o `unlock`:
a leitura ou medida que a resolve. Lacuna com nome vale mais que suposição.

**`change_kinds`** — as chaves de `sparkforge/sdd/change_kinds.yaml` que a
mudança toca. É delas que o ship deriva os gates. Guia rápido:

| a mudança... | chave |
|---|---|
| acrescenta ou muda regra do catálogo | `rule` (e `rule_runtime_scope`, `rule_area` quando couber) |
| acrescenta ou muda extrator de facts | `extractor` |
| edita documento em `knowledge/` | `knowledge_doc` |
| mexe em agent, skill ou espelho | `agent_or_skill` |
| acrescenta tool, verbo de CLI, agent ou skill | `tool_or_verb` |
| muda dependência ou workflow | `dependency` |
| muda número publicado em `docs/vnext/` ou `docs/harness/` | `claims` |

Chave fora do arquivo sai `schema_invalid` com a lista das válidas. Na dúvida,
abra `docs/gates-por-mudanca.md` e procure a seção que descreve a mudança.

### Conhecimento

Critério sobre Glue, Spark ou Iceberg cita a fonte, com a versão:
`docs/sdd/README.md#conhecimento-citado-nunca-memória`.

### O laço

O de `docs/sdd/README.md#o-laço-de-cada-fase`. Aqui: com `explore.md`
presente, `sparkforge sdd stamp --repo . docs/sdd/<F>/define.md`; sempre
`sparkforge sdd check --repo . --feature <F>`. `status: ready` exige zero
recusa **e** a leitura do operador: mostre o define inteiro e espere o "pode
seguir". Zero recusa sozinho é forma, não sign-off. Próximo passo:
`sdd-design`.

### Perfil operator

- **A spec mora em `.sparkforge/sdd/<F>/`** no repositório do operador, nunca
  em `docs/sdd/`: a cópia do `change sandbox` poda `.sparkforge`, e escrever
  fora dele deixa o sandbox desatualizado para `change propose`. Todo verbo do
  SDD leva a raiz: `sparkforge sdd check --repo . --root .sparkforge/sdd --feature <F>`.
  Não ponha `.sparkforge/sdd/` no `.gitignore`.
- Abra o case antes: `sparkforge case open --repo . --case-id <id> --now <ISO 8601>`,
  e copie o `case_id` para o define (ele fica em `.sparkforge/case.yaml`). Sem
  ele, ou com outro, sai `case_missing` — até o ship ficar `done`; dali em
  diante o case citado é histórico.
- Preservar a semântica é critério, não detalhe: um `AC` com `kind: funcval`,
  planejado por `sparkforge funcval plan` com a chave de negócio **declarada**
  (o caminho inteiro: `docs/sdd/README.md#caminho-da-mudança-do-operador`).
- O aceite do operador raramente é pytest: `{kind: funcval, ref: <arquivo do
  compare --out>}` para o resultado e `{kind: fact, ref: <facts.json>#kind:<kind>}`
  para o sintoma medido. **Prefira o seletor `#kind:`** agora: o id de fact é
  hash de conteúdo e só existe depois da coleta; `#<fact_id>` continua valendo.
  Grave os dois arquivos dentro de `.sparkforge/sdd/<F>/`. O gate confere a
  forma; o veredito é do `judge`.
- Métrica de desempenho vem de `sparkforge benchmark` entre dois runs medidos;
  custo, de `dpu_seconds` medido. Economia estimada não é métrica.

### Quando NÃO usar

- A ideia ainda está aberta, com mais de uma abordagem viva: `sdd-explore`.
- Para decidir arquivos e arquitetura: `sdd-design`.
- Para escolher valor de configuração: `sparkforge tune`, com a medida.
- Para reescrever a hipótese depois do resultado: a hipótese se fecha no ship.

### Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| estado das features | `sparkforge sdd status --repo .` | `sparkforge_sdd_status` |
| carimbar o upstream | `sparkforge sdd stamp --repo . docs/sdd/<F>/define.md` | `sparkforge_sdd_stamp` |
| conferir | `sparkforge sdd check --repo . --feature <F>` | `sparkforge_sdd_check` |
| regra citada | `sparkforge rules lookup --id <SF-...>` | `sparkforge_rules_lookup` |
| documento citado | `sparkforge knowledge path --file <arquivo>` | `sparkforge_knowledge_path` |
| case (operator) | `sparkforge case open --repo . --case-id <id> --now <ISO>` | `sparkforge_case_open` |
| semântica (operator) | `sparkforge funcval plan --facts <f> --key <k> --out <p>` | `sparkforge_funcval_plan` |

Recusas desta fase: `schema_invalid`, `success_without_source`, `case_missing`,
`funcval_not_comparison`, `upstream_missing`, `upstream_stale`. Template: `docs/sdd/templates/define.md`.

### Red flags

- Critério sem `verified_by`, ou com "conferir manualmente".
- `guard` num critério que devia falhar antes do código, ou com motivo que não diz por que ele passa sempre.
- Nota de clareza, pontuação ou confiança escrita no artefato.
- Métrica sem `source`, ou token estimado por contagem de caracteres.
- `sha256` digitado à mão.
- `change_kinds` inventado, ou vazio numa mudança que mexe em skill ou tool.
- `case_id` copiado de outro case.
- Afirmação sobre Glue ou Spark sem versão e sem fonte citada.
