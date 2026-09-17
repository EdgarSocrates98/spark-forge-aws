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
Todo campo e todo código de recusa e de lacuna, com quando dispara e em que
fase, está em [`CONTRATO.md`](CONTRATO.md), travado por teste contra o código.

## Os três verbos

| verbo | tool MCP | o que faz |
|---|---|---|
| `sparkforge sdd check --repo . [--feature F]` | `sparkforge_sdd_check` | confere schema, ordem, cascata por hash, testes, manifesto, cobertura, hipótese e registros; `ok` só com zero recusa e zero lacuna |
| `sparkforge sdd status --repo .` | `sparkforge_sdd_status` | a fase de cada feature e quem ficou `upstream_stale` |
| `sparkforge sdd stamp --repo . <artefato>` | `sparkforge_sdd_stamp` | grava o `sha256` do upstream; só a linha do hash muda |

Toda fase termina igual (veja [O laço de cada fase](#o-laço-de-cada-fase)):
`status: ready` só com zero recusa, e as lacunas esperadas daquela fase são
permitidas; `ok` do `check` só com zero recusa e zero lacuna.

## O laço de cada fase

1. Copie `docs/sdd/templates/<fase>.md` para `<root>/<F>/<fase>.md`, troque
   `feature: EXEMPLO` pelo nome da feature e ponha `status: draft`.
2. Rascunhe. O que só o operador resolve vira **uma pergunta por vez**.
3. Fase com upstream (todas menos explore, e define sem explore):
   `sparkforge sdd stamp --repo . <root>/<F>/<fase>.md`. Nunca escreva o
   `sha256` à mão.
4. `sparkforge sdd check --repo . --feature <F>`. Cada recusa traz `field` e
   `unlock`: corrija aquele campo e rode de novo.
5. `status: ready` com **zero recusa** e **depois da leitura do operador** —
   zero recusa sozinho não é sign-off. As lacunas esperadas são permitidas no
   `ready` até o build, desde que cada uma vire tarefa:
   `test_not_written`, `fact_not_collected`, `funcval_not_run` e, no
   operator, `finding_not_observed`. `build_report` e `ship` só vão a `done`
   com zero recusa e zero lacuna.
6. **Cascata.** Mudou uma fase? `sparkforge sdd status --repo .` mostra quem
   ficou `upstream_stale`. A fase de baixo é **revisada antes** de ser
   carimbada de novo: carimbar sem revisar é o erro que a cascata existe para
   pegar.

No perfil operator, todo verbo do SDD leva `--root .sparkforge/sdd` (seção
abaixo).

## Caminho da mudança do operador

A sessão nunca escreve na árvore do operador. Spec e evidências ficam em
`.sparkforge/sdd/<F>/`; o job muda só por este caminho:

1. `sparkforge funcval plan --facts <f> --key <k> --out <p>`, com a chave de
   negócio **declarada**, antes da mudança.
2. `sparkforge change plan --facts <f> --set k=v --out d.patch` (ou
   `--from-tune`): valor de configuração sai de `sparkforge tune`, não do
   design.
3. `sparkforge change sandbox --repo . --diff d.patch`: o `id` vira
   `change_id`. Achado novo P0 ou P1 no sandbox: pare e volte ao design.
4. `sparkforge funcval compare --plan <p> --before <a> --after <b> --out <ref do AC>`:
   o `--out` é o `ref` do `verified_by` funcval, senão `funcval_not_run`
   nunca sai.
5. `sparkforge benchmark --before <a> --after <b> --out bench.json` sobre dois
   runs medidos.
6. `sparkforge change propose --sandbox <id> --repo . --funcval <cmp.json> --benchmark bench.json`:
   sem as duas flags, a medida fica PENDENTE no pacote. O PR vai pela skill
   `propose-change-pr`, que para antes de `git push` e de `gh pr create`.
7. O `rollback` de cada decisão é o `rollback.patch` do pacote, ou
   `git revert` depois do merge.

## Conhecimento citado, nunca memória

- Comportamento de Glue, Spark, Iceberg ou Lake Formation sai de
  `sparkforge rules lookup --id <SF-...>` ou
  `sparkforge knowledge path --file <documento>`, **com a versão alvo antes**:
  com AQE ou sem AQE, o mesmo número significa outra coisa.
- O que o código já faz sai de `sparkforge code search <nome>`,
  `sparkforge code symbol <node_id>` (quem chama, o que quebra) e
  `sparkforge code path <origem> <destino>`.
- Documentação oficial e changelog sustentam uma decisão; texto de modelo
  sozinho (T5) não. Nota de clareza ou confiança que o agente atribui a si
  mesmo não entra em artefato.

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
| build_report | `moved: {change_id, resolved: [<rule_id>...]}` no lugar de `red`/`green` | `change_id` igual ao do build (senão `moved_change_mismatch`) e cada regra em `resolved` e fora de `new` no `report.json` do sandbox ou no `evidence/sandbox_report.json` da proposal; senão `moved_not_observed` |
| ship | `evidence: [{change_id, report_sha256}]`, obrigatório | uma entrada por `change_id` citado, com o `text_sha256` do relatório lido (senão `ship_evidence_missing`); relatório presente com outro hash, `ship_evidence_mismatch` |

`change_id` vale enquanto existir `.sparkforge/sandbox/<id>/` ou
`.sparkforge/proposal/<id>/`. Com o ship em `status: done`, `case_missing` e
`change_missing` param: o case e a pasta citados viraram histórico. A
conferência de `moved`/`finding` só para quando **nenhum** relatório da
mudança existe — aí o que sustenta a mudança é o `report_sha256` gravado em
`evidence`. Relatório presente continua conferido, também contra esse hash.

## Base e crédito

A ordem das fases e o manifesto de arquivos vêm do AgentSpec (MIT); o diálogo
uma pergunta por vez, o plano sem placeholder, o TDD e a revisão em dois
estágios vêm do superpowers (MIT). Detalhe em `vendor/CREDITS.md`.
