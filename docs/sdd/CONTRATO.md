# Contrato do SDD

O contrato **vivo** dos artefatos de `docs/sdd/` e dos três verbos
`sparkforge sdd check|status|stamp`: os campos de cada fase e todo código que o
gate emite, com quando dispara e em que fase. Ele descreve o código de hoje —
`sparkforge/sdd/checks.py`, `sparkforge/sdd/stamp.py`, `sparkforge/sdd/schema/*.json`
e `sparkforge/sdd/change_kinds.yaml`.

`tests/test_sdd.py::test_contrato_lista_todo_codigo` lê por `ast` todo código
literal passado a `recusa`, `lacuna` e `StampError` (e todo `"code"` literal
de dicionário) nos dois módulos, e exige que o conjunto seja **igual** ao da
primeira coluna das tabelas `| código |` deste documento. Código novo sem
linha aqui, ou linha aqui sem código, reprova o teste.

O spec `docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md` (§5, §5.0,
§13) é o registro histórico de como o contrato nasceu; a pasta está congelada
e não acompanha o código.

## A saída

```json
{"ok": false, "root": "docs/sdd", "features": ["F1"],
 "refused":    [{"code": "...", "feature": "...", "path": "...", "field": "...", "unlock": "..."}],
 "unresolved": [{"code": "...", "feature": "...", "path": "...", "unlock": "..."}]}
```

- `ok` só com zero recusa **e** zero lacuna.
- `refused` é o que está errado no artefato; `field` é o caminho do campo
  (`tasks/0/moved/change_id`) ou `null`. `unresolved` é o que o gate ainda não
  consegue decidir. Todo item traz `unlock`: o que fazer.
- `sparkforge sdd check` sai com **1** quando há recusa e **0** caso contrário
  (só lacuna sai 0 com `ok: false`). `--feature` que a varredura não achou sai
  com **2** e aponta `sdd status`, salvo quando uma lacuna já explica a
  ausência (`root_missing`, ou `path_skipped` com o nome da feature).
- `sparkforge sdd status` lê a mesma passada do `check` (`evaluate`): por
  feature, `phase`, `status`, `profile`, `next_phase`, e os códigos de
  `refused` e `unresolved`; lacuna sem feature descoberta sobe para o topo.
- `sparkforge sdd stamp` é a única escrita: grava `upstream.sha256` e devolve
  `{path, upstream, sha256, previous, changed}`. Recusa sai com **2** e o
  código no começo da mensagem.
- Repositório (`--repo`) inexistente é erro de uso, com **2**, nos três.

## Onde moram os artefatos

`<root>/<FEATURE>/<fase>.md`, com `<root>` = `docs/sdd` (padrão) ou
`.sparkforge/sdd` no operador. `FEATURE` casa `^[A-Z0-9_]+$`; outra pasta
(`templates/`, `archive/`) não é feature. Fases, em ordem: `explore`
(opcional), `define`, `design`, `plan`, `build_report`, `ship`. Nada mais fundo
que `<FEATURE>/<fase>.md` é lido. O frontmatter é YAML entre duas cercas
`---`; um BOM de UTF-8 antes da primeira é tolerado. O corpo nunca é julgado.

## Campos comuns

| campo | forma | regra |
|---|---|---|
| `sdd` | `1` | constante |
| `feature` | `^[A-Z0-9_]+$` | igual ao nome da pasta |
| `phase` | uma das seis fases | igual ao nome do arquivo |
| `profile` | `dev` \| `operator` | |
| `status` | `draft` \| `ready` \| `done` \| `superseded` | a fase seguinte exige a anterior em `ready` ou `done` |
| `upstream` | `{path, sha256}` | `sha256` vazio ou 64 hex; obrigatório em todas menos `explore`, e no `define` só quando `explore.md` existe |

Campo fora do schema da fase é `schema_invalid`.

## Campos por fase

**`explore`** — `approaches` (≥ 1: `id`, `summary`, `tradeoffs?`), `chosen`.

**`define`**

| campo | forma |
|---|---|
| `hypothesis` | `{claim, prediction, experiment}`, os três não vazios |
| `acceptance` | ≥ 1: `{id: AC<n>, statement, verified_by: {kind, ref}, guard?}`; `guard` é o motivo, texto com ao menos uma letra ou dígito, de uma guarda de regressão (passa antes e depois por desenho) e isenta o item de `acceptance_never_red` |
| `success` | `{id: SC<n>, metric, source?}` |
| `out_of_scope` | lista de texto |
| `unknowns` | opcional: `{id: U<n>, blocks?, unlock}` |
| `change_kinds` | chaves de `sparkforge/sdd/change_kinds.yaml` |
| `case_id` | texto ou `null`; exigido no operator |

`verified_by.kind`:

| `kind` | `ref` | o que o gate faz |
|---|---|---|
| `test` | node id do pytest (`tests/a.py::test_x`, `::TestA::test_x`; `[...]` descartado) | confere por `ast`, sem importar, só o que o pytest coleta por padrão |
| `command` | o comando | registra; quem roda é o ship |
| `funcval` | arquivo de `sparkforge funcval compare --out` | confere a forma, nunca o veredito |
| `fact` | `arquivo.json#<id>` ou `arquivo.json#kind:<kind>` | lista crua ou `{"items": [...]}`; item sem `id` não casa; `kind:` vazio não casa |

**`design`** — `files` (`{path, action: create|modify|delete, reason}`),
`decisions` (`{id: D<n>, choice, rejected?, rollback?}`), `covers`
(`{part, acceptance: [AC...]}`).

**`plan`** — `tasks` (≥ 1): `{id: T<n>, files, covers, test?: {path, name}, proof?: {kind: funcval|fact|finding, ref}}`.

**`build_report`** — `tasks` (`{id, status: done|skipped|blocked, red?, green?, moved?}`,
com `red`/`green` = `{command, exit}` e `moved` = `{change_id, resolved: [rule_id, ...]}`),
`claims` (`{text, evidence_ref?}`), `change_id` (texto ou `null`; exigido no operator).

**`ship`** — `registries`, `deviations`, `hypothesis_outcome?`
(`confirmed|refuted|abandoned`), `evidence?`
(`[{change_id, report_sha256: 64 hex}]`; exigido no operator).

## Recusas do `check`

| código | quando | fase |
|---|---|---|
| `schema_invalid` | frontmatter ausente, não UTF-8, YAML quebrado (com a linha), fora do schema, `phase`/`feature` diferentes do arquivo/pasta; `upstream` em `explore`, ou no `define` sem `explore.md`; `change_kinds` fora do mapa; `verified_by.kind: test` sem `::nome`; `proof` ou `moved` no dev; `evidence` no ship dev; `proof` `finding` sem `#<rule_id>`; `guard` vazio, sem letra nem dígito (só espaço, inclusive Unicode como U+200B, ou só pontuação) ou fora de texto | todas |
| `phase_out_of_order` | a fase anterior não existe ou não está em `ready`/`done` (anterior recusada por schema não repete a causa) | design, plan, build_report, ship |
| `upstream_missing` | sem bloco `upstream`, `upstream.path` inexistente ou que não é o upstream esperado da fase | todas menos explore |
| `upstream_stale` | `upstream.sha256` diferente do `text_sha256` do upstream (CRLF normalizado para LF) | todas menos explore |
| `success_without_source` | `success[]` sem `source` | define |
| `verified_by_dangling` | teste citado (`verified_by` do define ou `test` do plan) não existe com o `build_report` em `ready`/`done` | define, plan |
| `funcval_not_comparison` | o arquivo `funcval` existe e não tem nenhum `funcval.check_delta` (inclui JSON quebrado) | define, plan |
| `case_missing` | operator sem `case_id`, vazio, ou diferente do `case_id` de `.sparkforge/case.yaml` (comparados como texto); não confere com o ship em `done` | define |
| `manifest_path_unknown` | `modify` em caminho inexistente; `delete` em caminho inexistente antes do build pronto | design |
| `rollback_missing` | decisão sem `rollback` | design |
| `acceptance_uncovered` | `AC` do define fora de todo `covers` da fase conferida | design, plan |
| `task_without_test` | tarefa sem `test` (no operator, sem `test` nem `proof`) | plan |
| `moved_not_observed` | regra de `moved.resolved`, ou de `proof` `finding` com o build pronto, que o relatório da mudança não mostra em `resolved`, ou mostra também em `new`, ou relatório ausente/ilegível; não confere quando o ship está em `done` **e** nenhum relatório existe | plan, build_report |
| `moved_change_mismatch` | `moved.change_id` diferente do `change_id` do build_report, em qualquer status | build_report |
| `red_not_declared` | tarefa `done` sem `red`, ou com `red.exit` 0 (no operator, `moved` dispensa `red`) | build_report |
| `acceptance_never_red` | só no perfil `dev`, com o build_report em `ready`/`done` e o ship ausente ou fora de `done`: `acceptance` de `kind: test` sem `guard` que nenhuma tarefa `done` do plan com o AC em `covers` viu vermelho — o `red` dela precisa de `exit` diferente de zero e de 5 (nenhum teste coletado) **e** citar o node id do `verified_by` no comando, ou só o arquivo com `exit` 2 (erro de coleta), com `\` e `./` inicial normalizados dos dois lados; o gate confere a **citação** do node id no comando declarado, não a execução — um `red` com `--deselect` do node, ou com o node num comentário, passaria; tarefa já recusada por `red_not_declared` não repete a causa, nem ship recusado por schema | build_report |
| `claim_without_evidence` | claim sem `evidence_ref` | build_report |
| `change_missing` | operator com `change_id` vazio, com separador, `.`/`..`, ou sem `.sparkforge/sandbox/<id>/` nem `.sparkforge/proposal/<id>/` como pasta; não confere com o ship em `done` | build_report |
| `hypothesis_open_at_ship` | ship sem `hypothesis_outcome` | ship |
| `registry_unchecked` | registro exigido pelos `change_kinds` do define ausente de `registries` (um por registro) | ship |
| `ship_evidence_missing` | ship operator com o build_report sem `change_id`; sem `evidence`; ou sem entrada para um `change_id` citado (o do build, o de cada `moved`, o prefixo de cada `proof` `finding`); o `unlock` traz o `text_sha256` de cada relatório presente | ship |
| `ship_evidence_mismatch` | relatório presente da mudança com `text_sha256` diferente do `report_sha256` gravado; **todo** relatório presente precisa casar | ship |

## Lacunas do `check`

| código | quando | fase |
|---|---|---|
| `root_missing` | `<root>` não existe ou não é pasta | — |
| `path_skipped` | a varredura podou algo que a descoberta leria: pasta de feature, pasta dentro de uma, ou `<fase>.md` dentro de uma | — |
| `test_not_written` | teste citado ainda não existe, antes do build pronto; o build o escreve antes do código | define, plan |
| `fact_not_collected` | arquivo de facts ausente, ou sem o `#<id>`/`#kind:<kind>` citado | define, plan |
| `funcval_not_run` | arquivo `funcval` citado ainda não existe | define, plan |
| `funcval_blind_spot` | um por `funcval.unresolved` do arquivo, com `subject.symbol` e `attrs.reason` | define, plan |
| `finding_not_observed` | `proof` `finding` cuja regra o relatório não mostra saindo, antes do build pronto | plan |

`test_not_written`, `fact_not_collected`, `funcval_not_run` e
`finding_not_observed` são as lacunas esperadas até o build; `build_report` e
`ship` só vão a `done` com zero recusa e zero lacuna.

## Perfil operator

- **Raiz.** A spec mora em `.sparkforge/sdd/` (`--root`): a cópia do sandbox
  poda `.sparkforge`. A raiz passada à descoberta nunca é podada.
- **`change_id`** é um segmento só e vale enquanto existir
  `.sparkforge/sandbox/<id>/` ou `.sparkforge/proposal/<id>/`. O relatório da
  mudança é `report.json` na primeira ou `evidence/sandbox_report.json` na
  segunda, lido só se resolver dentro da pasta (symlink para fora é ignorado);
  vale o primeiro que for JSON de objeto.
- **`proof`** substitui `test` na tarefa do plan: `funcval` e `fact` usam as
  conferências do define; `finding` é `<change_id>#<rule_id>`, ou
  `#<rule_id>` para o `change_id` do build.
- **`moved`** substitui `red`/`green` na tarefa do build: `change_id` igual ao
  do build e cada regra em `resolved` e fora de `new` no relatório.
- **Seletor por kind.** `verified_by.kind: fact` (e `proof` `fact`) aceita
  `#kind:<kind>`: passa com ao menos um fact daquele kind.
- **Evidência do ship.** O ship grava
  `evidence: [{change_id, report_sha256}]`, com o `text_sha256` do relatório
  que leu, para cada `change_id` citado.
- **História.** Com o ship em `done`: `case_missing` e `change_missing` não
  conferem (o case pode ser outro, a pasta pode ter sido limpa). `moved` e
  `finding` só deixam de conferir quando **nenhum** relatório da mudança
  existe; aí o que sustenta a mudança é o `report_sha256` gravado. Relatório
  presente continua conferido, e contra o hash gravado. `fact` e `funcval`
  conferem sempre.

## Recusas do `stamp`

| código | quando |
|---|---|
| `artifact_missing` | o caminho não existe sob `--repo` |
| `not_an_artifact` | o alvo não resolve para `<root>/<FEATURE>/<fase>.md` |
| `schema_invalid` | frontmatter ausente, não UTF-8, ou YAML quebrado |
| `upstream_missing` | sem `upstream.path`, upstream inexistente, ou bloco sem a linha `sha256:` |
| `upstream_flow_style` | `upstream: {…}`; o `stamp` só reescreve bloco |
| `sha_line_unsupported` | a linha `sha256:` não é um escalar simples inteiro na própria linha (valor abaixo, bloco `\|`/`>`, multilinha, tag, âncora, `sha256:x`) |

O `stamp` reescreve só a linha do hash, como `sha256: "<hex>"`, preservando
quebra de linha, BOM, comentário no fim da linha e comentário de coluna zero
dentro do bloco.

## `change_kinds.yaml`

Cada chave dá o título literal da seção de `docs/gates-por-mudanca.md` e os
`registries` que o ship lista. Um teste trava os dois sentidos entre as seções
do documento e o mapa.
