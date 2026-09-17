# SDD próprio do SparkForge

Spec-driven development com gate determinístico. O agente escreve os artefatos;
o pacote confere o que dá para conferir e recusa o resto por nome. Nenhuma fase
atribui nota a si mesma.

## Onde moram as coisas

```
docs/sdd/
  README.md            este arquivo
  templates/           um artefato válido por fase (feature EXEMPLO)
  <FEATURE>/           uma pasta por feature, nome em MAIÚSCULAS_COM_SUBLINHADO
    explore.md         opcional
    define.md
    design.md
    plan.md
    build_report.md
    ship.md
```

`templates/` não é feature: só pasta no padrão `^[A-Z0-9_]+$` entra na
descoberta. O contrato de cada fase está em `sparkforge/sdd/schema/`, e o mapa de
tipo de mudança para registros do ship em `sparkforge/sdd/change_kinds.yaml`.

## Os três verbos

| verbo | tool MCP | o que faz |
|---|---|---|
| `sparkforge sdd check --repo . [--feature F]` | `sparkforge_sdd_check` | confere schema, ordem, cascata por hash, testes, manifesto, cobertura, hipótese e registros; `ok` só com zero recusa e zero lacuna |
| `sparkforge sdd status --repo .` | `sparkforge_sdd_status` | a fase de cada feature e quem ficou `upstream_stale` |
| `sparkforge sdd stamp --repo . <artefato>` | `sparkforge_sdd_stamp` | grava o `sha256` do upstream; só a linha do hash muda |

Toda fase termina igual: `sparkforge sdd stamp` na fase escrita (quando ela tem
upstream) e `sparkforge sdd check --repo . --feature <F>`. `status: ready` só com
o check limpo.

## As skills

Uma por fase, canônicas em `skills/` e espelhadas por `scripts/sync_skills.py`:

| fase | skill | o que ela exige |
|---|---|---|
| explore | `sdd-explore` | perfil primeiro, uma pergunta por vez, duas ou três abordagens |
| define | `sdd-define` | hipótese em três partes, critério com `verified_by`, métrica com `source` |
| design | `sdd-design` | manifesto conferido no código, decisão com `rejected` e `rollback` |
| plan | `sdd-plan` | tarefa pequena com teste nomeado e código completo |
| build | `sdd-build` | vermelho antes do verde, um subagente por tarefa, revisão em dois estágios |
| ship | `sdd-ship` | registros de `docs/gates-por-mudanca.md`, hipótese fechada, desvios |

## Dois perfis

- `dev`: evoluir o próprio SparkForge.
- `operator`: quem usa os agents para mudar o próprio job Glue/PySpark. O define
  carrega o `case_id` de `sparkforge case open`; o build passa por
  `sparkforge change sandbox` e o PR pela skill `propose-change-pr`. A árvore do
  operador nunca é escrita pela sessão.

## Perfil operator: onde mora a spec

No repositório do operador, os artefatos e as evidências ficam em
`.sparkforge/sdd/<FEATURE>/`, e todo verbo do SDD leva a raiz:

```
sparkforge sdd check --repo . --root .sparkforge/sdd --feature <F>
sparkforge sdd stamp --repo . --root .sparkforge/sdd .sparkforge/sdd/<F>/<fase>.md
```

Por quê: a cópia que `sparkforge change sandbox` valida poda `.sparkforge`.
Uma spec em `docs/sdd/` muda a árvore copiada, e `sparkforge change propose`
recusa o pacote com `sandbox_desatualizado`. A árvore do job continua mudando
só pelo diff de `sparkforge change sandbox` e pelo pacote de
`sparkforge change propose`. Não ponha `.sparkforge/sdd/` no `.gitignore`: é a
spec do operador. `.sparkforge/sandbox/` e `.sparkforge/proposal/` são
recriados a cada execução.

O que o gate aceita só no operator:

| onde | campo | prova |
|---|---|---|
| define | `verified_by: {kind: fact, ref: <facts.json>#kind:<kind>}` | ao menos um fact daquele kind; prefira ao `#<id>`, que é hash desconhecido antes da coleta |
| plan | `proof: {kind: funcval\|fact\|finding, ref}` no lugar de `test` | `finding` é `<change_id>#<rule_id>` ou `#<rule_id>` (o `change_id` do build); lacuna `finding_not_observed` até o sandbox |
| build_report | `moved: {change_id, resolved: [<rule_id>...]}` no lugar de `red`/`green` | cada regra em `resolved` e fora de `new` no `report.json` do sandbox ou no `evidence/sandbox_report.json` da proposal; senão `moved_not_observed` |

`change_id` vale enquanto existir `.sparkforge/sandbox/<id>/` ou
`.sparkforge/proposal/<id>/`. Com o ship em `status: done`, `case_missing`,
`change_missing` e a conferência de `moved`/`finding` param: o case e a
mudança citados viraram histórico.

## Cascata

Mudou uma fase? `sparkforge sdd status` mostra quem ficou `upstream_stale`. A
fase de baixo é **revisada antes** de ser carimbada de novo: carimbar sem revisar
é o erro que a cascata existe para pegar.

## Base e crédito

A ordem das fases e o manifesto de arquivos vêm do AgentSpec (MIT); o diálogo
uma pergunta por vez, o plano sem placeholder, o TDD e a revisão em dois
estágios vêm do superpowers (MIT). Detalhe em `vendor/CREDITS.md`.
