# SDD próprio — núcleo determinístico (subprojeto A)

> **Contrato vivo em `docs/sdd/CONTRATO.md`.** Este spec é registro histórico,
> numa pasta congelada: os códigos e campos do §5, §5.0 e §13 não acompanham o
> código. Para o que o gate faz hoje, leia o contrato vivo.

**Data:** 2026-09-16
**Estado:** implementado (subprojeto A), branch `sdd/nucleo-spec`; desvios no §13
**Frente:** A de 5 (A núcleo · B skills dev · C perfil operador · D migração · E medida)

> Este é o **último** spec gravado em `docs/superpowers/specs/`. O formato que ele
> desenha substitui o ciclo do superpowers e o SDD do AgentSpec; quando o
> subprojeto B existir, specs novos passam a morar em `docs/sdd/`.

---

## 1. Por que existe

Hoje o repositório tem **dois** processos de spec ativos ao mesmo tempo, os dois
vindos de plugins de nível usuário, nenhum distribuído com o repo:

| processo | onde grava | medido em 2026-09-16 |
|---|---|---|
| superpowers (brainstorming → writing-plans → executing-plans) | `docs/superpowers/specs/`, `docs/superpowers/plans/` | 41 specs, 36 plans; 21 commits desde 2026-09-10 |
| AgentSpec 3.5.0 (brainstorm → define → design → build → ship) | `.claude/sdd/` | 104 arquivos `.md`, 15 BUILD_REPORT arquivados; 23 commits desde 2026-09-10 |

Problemas medidos:

- **Nenhum dos dois vem com o clone.** Quem clona o SparkForge não tem nenhum dos
  dois, e Devin/Copilot não têm nenhum dos dois.
- **Julgamento de LLM vestido de número.** O gate do AgentSpec é um *clarity
  score* 12/15 que o próprio modelo atribui (`skills/sdd-define/SKILL.md` do
  plugin, linha 155). Na escala de autoridade do projeto isso é T5.
- **Cascata depende de memória.** `/iterate` do AgentSpec depende do agente
  lembrar de atualizar o que está abaixo.
- **Conhecimento paralelo desatualizado.** `kb/aws/quick-reference.md:74` e
  `kb/aws/lambda/quick-reference.md:83` do plugin 3.5.0 apontam Glue 5.0 como
  alvo de ETL.
- **Estado específico de plataforma.** `.claude/sdd/` é diretório do Claude; o
  hook `SessionStart` do plugin reescreve `.claude/sdd/.detected-stack.md` a
  cada sessão (árvore suja todo dia) e detectou apenas "Pydantic", que nem é
  dependência direta.

Decisões do operador (2026-09-16):

1. o SDD próprio **substitui** o ciclo spec → plan → execução do superpowers,
   a disciplina de TDD dele, e o SDD do AgentSpec;
2. serve **dois perfis**: `dev` (evoluir o SparkForge) e `operator` (quem usa
   os agents do SparkForge para mudar os próprios jobs);
3. o gate mora **no pacote**, como verbo próprio com tool MCP;
4. no perfil `operator`, BUILD passa **sempre** por `change sandbox/propose`;
   nunca escreve na árvore do operador;
5. o plugin AgentSpec é desativado no projeto (subprojeto D);
6. skills com prefixo `sdd-`.

## 2. Decomposição

| # | subprojeto | depende de |
|---|---|---|
| **A** | núcleo: contrato dos artefatos + `sparkforge sdd check\|status\|stamp` | — |
| B | skills `sdd-explore`, `sdd-define`, `sdd-design`, `sdd-plan`, `sdd-build` (TDD), `sdd-ship`, canônicas em `skills/`, espelhadas por `scripts/sync_skills.py`; templates em `docs/sdd/templates/` | A |
| C | perfil operador: ligação com `case`, `change plan/sandbox/propose`, `funcval` | A, B |
| D | migração: desativar AgentSpec e o ciclo do superpowers, apontar `CLAUDE.md`/`AGENTS.md`, arquivar `.claude/sdd/` e `docs/superpowers/` como histórico (sem reescrever) | B |
| E | medida de "melhor" (regra 30) no `evals/agentic` | B, D |

**Este spec cobre só A.**

## 3. Estrutura

```
sparkforge/sdd/
  __init__.py
  schema/            # um JSON Schema por fase
    common.json
    explore.json  define.json  design.json
    plan.json     build_report.json  ship.json
  change_kinds.yaml  # tipo de mudança -> seção de docs/gates-por-mudanca.md -> registros exigidos
  load.py            # lê .md, separa frontmatter YAML e corpo
  checks.py          # os gates; cada falha é recusa com nome
  status.py          # deriva fase/estado de cada feature
  stamp.py           # grava upstream.sha256
```

- Lógica pura. Nenhum import de provider (regra 23). Dependências: `PyYAML` e
  `jsonschema`, que já são do núcleo.
- Artefatos em `docs/sdd/<FEATURE>/<PHASE>.md`; raiz configurável por `--root`.
- **Separação de estado.** O artefato `operator` referencia o case por
  `case_id`; não copia nada dele. `.sparkforge/` continua sendo do case, e o SDD
  nunca escreve lá (o `stamp` escreve só no próprio `.md` e no journal).

## 4. Contrato dos artefatos

Markdown com frontmatter YAML. **O frontmatter é conferível; o corpo é livre**
e o pacote não o valida.

### 4.1 Campos comuns

```yaml
sdd: 1                       # versão do método
feature: NUCLEO_SDD
phase: define                # explore|define|design|plan|build_report|ship
profile: dev                 # dev|operator
status: draft                # draft|ready|done|superseded
upstream:                    # ausente só em explore
  path: docs/sdd/NUCLEO_SDD/explore.md
  sha256: "…"
```

### 4.2 Campos por fase

**explore** — `approaches[] {id, summary, tradeoffs}`, `chosen` (id).

**define**

```yaml
hypothesis:
  claim: "…"
  prediction: "…"
  experiment: "…"
acceptance:
  - id: AC1
    statement: "…"
    verified_by: {kind: test, ref: "tests/test_sdd_checks.py::test_upstream_stale"}
    # kind: test | command | funcval | fact
success:
  - id: SC1
    metric: "…"
    source: "…"              # de onde vem o número (regra 24)
out_of_scope: ["…"]
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "…"              # a medida que destrava (regra 20)
case_id: null                # obrigatório em profile: operator
change_kinds: [tool_or_verb] # chaves de change_kinds.yaml
```

**design**

```yaml
files:
  - {path: sparkforge/sdd/checks.py, action: create, reason: "…"}   # create|modify|delete
decisions:
  - {id: D1, choice: "…", rejected: ["…"], rollback: "…"}
covers:
  - {part: "gates", acceptance: [AC1, AC2]}
```

**plan**

```yaml
tasks:
  - id: T1
    files: [sparkforge/sdd/checks.py]
    covers: [AC1]
    test: {path: tests/test_sdd_checks.py, name: test_upstream_stale}
```

**build_report**

```yaml
tasks:
  - id: T1
    status: done             # done|skipped|blocked
    red:   {command: "pytest tests/test_sdd_checks.py -k upstream_stale", exit: 1}
    green: {command: "pytest tests/test_sdd_checks.py -k upstream_stale", exit: 0}
claims:
  - {text: "…", evidence_ref: "…"}
change_id: null              # obrigatório em profile: operator
```

**ship**

```yaml
hypothesis_outcome: confirmed    # confirmed|refuted|abandoned
registries: [surface_lock, generated_reference]
deviations: ["…"]
```

### 4.3 Limite declarado

`red` é **declarado**, não reverificado: depois do fato ninguém prova que o
teste falhou antes. O gate confere que foi registrado e que `exit != 0`.
Reexecutar `green` fica fora de A (executar código é outra classe de efeito); o
`sdd-build` (B) roda e registra.

## 5. Gates

`checks.py` devolve:

```json
{"ok": false,
 "refused":    [{"code": "...", "feature": "...", "path": "...", "field": "...", "unlock": "..."}],
 "unresolved": [{"code": "...", "feature": "...", "path": "...", "unlock": "..."}]}
```

| código | quando | fase |
|---|---|---|
| `schema_invalid` | frontmatter ausente, YAML quebrado (com linha) ou fora do schema | todas |
| `phase_out_of_order` | fase existe sem a anterior em `status: ready` ou `done` | todas |
| `upstream_missing` | `upstream.path` não existe | todas menos explore |
| `upstream_stale` | `upstream.sha256` ≠ sha256 **de texto** do upstream (`\r\n` normalizado para `\n`, o `text_sha256` de `sparkforge/receipt/_hash.py`) | todas menos explore |
| `acceptance_uncovered` | acceptance id do define ausente de todos os `covers` **da fase conferida** (conferido separadamente no design e no plan) | design, plan |
| `task_without_test` | task do plan sem `test` | plan |
| `verified_by_dangling` | `kind: test` aponta arquivo inexistente ou função ausente (conferido por `ast`, sem importar) **depois do build** — antes disso é `unresolved: test_not_written` | define, plan (quando existe `build_report.md` válido com `status: ready` ou `done`) |
| `success_without_source` | métrica sem `source` | define |
| `manifest_path_unknown` | `action: modify` em caminho inexistente, sempre; `action: delete` em caminho inexistente só **antes do build** — depois dele o arquivo sumido é o design cumprido | design (o `delete` só enquanto não existe `build_report.md` válido com `status: ready` ou `done`) |
| `rollback_missing` | decisão sem `rollback` | design |
| `red_not_declared` | task `done` sem `red`, ou `red.exit == 0` | build_report |
| `claim_without_evidence` | claim sem `evidence_ref` | build_report |
| `hypothesis_open_at_ship` | ship sem `hypothesis_outcome` | ship |
| `registry_unchecked` | ship não lista registro que `change_kinds.yaml` exige para os `change_kinds` do define | ship |
| `case_missing` | `profile: operator` sem `case_id`, ou case inexistente | define |
| `change_missing` | `profile: operator` sem `change_id`, ou id ausente de `.sparkforge/sandbox/` | build_report |

**`explore` é opcional.** Ordem exigida: define → design → plan → build_report →
ship. O define só declara `upstream` quando `explore.md` existe. `feature`
pedida que não existe é erro de uso do verbo, não código desta tabela.

`unresolved` quando o gate **não consegue decidir**:

| código | quando |
|---|---|
| `root_missing` | `--root` não existe |
| `test_not_written` | `verified_by.kind: test` ou `plan.tasks[].test` ainda sem arquivo/função, com a feature antes de `build_report` — TDD escreve o teste no build, então ausência aqui é esperada; `unlock` nomeia a task |
| `fact_not_collected` | `verified_by.kind: fact` com fact que ainda não existe; `unlock` nomeia a coleta |
| `funcval_not_run` | `verified_by.kind: funcval` sem resultado de `funcval compare` |

#### 5.0 Códigos acrescentados na revisão

- **Feature é só pasta no padrão do schema** (`^[A-Z0-9_]+$`). `templates/`,
  `archive/` e afins sob a raiz não viram feature, mesmo com `define.md` dentro.
- **`unresolved: path_skipped`.** A descoberta usa `varrer_source_files`
  (`sparkforge/facts/scan.py`), que poda nomes da lista de pulos (`build`,
  `dist`, `vendor`, `secrets`, `credentials`… comparados em minúsculas). Vira
  lacuna com nome só o pulo que esconde algo que a descoberta leria: pasta de
  primeiro nível com nome de feature (`BUILD/`), pasta de segundo nível dentro
  de uma (`F1/build/`) e `<fase>.md` dentro de uma. Arquivo direto na raiz,
  `templates/vendor/` ou pasta mais funda a descoberta ignoraria de qualquer
  jeito, e contá-los deixaria `ok` falso para sempre. `feature` é a pasta de
  primeiro nível, `path` é `<root>/<relativo>`, e o `unlock` manda renomear.
  Sem isso, uma feature `BUILD` sumia e o `check` saía `ok`. O `status` sobe
  para o topo as lacunas cuja feature não foi descoberta.
- **`upstream` onde não cabe é `schema_invalid`**, campo `upstream`: em
  `explore` (primeira fase, sem upstream) e em `define` quando a feature não
  tem `explore.md`. Antes o bloco era ignorado calado.
- **Recusas do `stamp`** (`StampError.code`), além de `artifact_missing`,
  `schema_invalid` e `upstream_missing`:
  - `not_an_artifact` — o alvo não resolve para `<repo>/<root>/<FEATURE>/<fase>.md`
    (FEATURE no padrão, fase em `PHASES`); `stamp` ganha `root` (default
    `docs/sdd`), que CLI e MCP repassam;
  - `sha_line_unsupported` — a linha `sha256:` não é um escalar simples
    (plano, aspas simples ou duplas) inteiro na própria linha: valor na linha
    de baixo, bloco `|`/`>`, escalar multilinha, tag ou âncora;
  - `upstream_flow_style` — `upstream: {…}`; o `stamp` só reescreve bloco.
- **Referência de teste é node id do pytest.** O sufixo `[...]` do
  parametrize é descartado antes de conferir; classe aninhada vira
  `TestA::TestB::test_c`; só conta o que o pytest coleta por padrão — função
  `test*`, classe `Test*` e seus métodos `test*` (`::_helper` não conta).
  `kind: test` sem `::nome` é `schema_invalid` no campo
  `acceptance/<i>/verified_by/ref`, em qualquer fase. `verified_by_dangling`
  só dispara com o `build_report` em `ready`/`done`; em `draft` segue
  `test_not_written`.
- **`fact`:** item sem `id` verdadeiro é ignorado (`#None` não casa).
- **`change_id`** é um segmento só, sem separador, e precisa ser subpasta
  direta de `.sparkforge/sandbox/`; `..`, `.` e `../../docs` saem
  `change_missing`. **`case_id`** é comparado como texto nos dois lados, e
  vazio conta como ausente.
- O `stamp` preserva comentário de coluna zero dentro do bloco `upstream:`,
  comentário no fim da linha do hash e o BOM de UTF-8; `load_artifact` tolera
  o BOM antes da cerca.
- **`funcval` confere a forma, nunca o veredito** (feature `SDD_OPERATOR`).
  Achado o arquivo, o gate o lê como lista de facts (lista crua ou
  `{"items": [...]}`):
  - `refused: funcval_not_comparison` — nenhum `funcval.check_delta` (inclui
    JSON quebrado ou que não é lista de facts); `unlock` manda rodar
    `sparkforge funcval compare --out <ref>`;
  - `unresolved: funcval_blind_spot` — um por `funcval.unresolved`, com o
    `subject.symbol` (ou o subject cru) e o `attrs.reason` no `unlock`.
  Se a divergência passa do limiar continua com as `SF-FVAL-*` no `judge`
  (regra 11).
- **Perfil operator durável** (feature `SDD_OPERATOR_DURAVEL`). A spec do
  operador mora em `.sparkforge/sdd` (`--root`), porque a cópia do sandbox poda
  `.sparkforge`; a raiz passada à descoberta nunca é podada.
  - **`change_id`** vale quando `.sparkforge/sandbox/<id>/` **ou**
    `.sparkforge/proposal/<id>/` existe como diretório, as duas com o mesmo
    confinamento de um segmento.
  - **Referência histórica.** Com o `ship.md` carregado em `status: done`,
    `case_missing`, `change_missing` e as conferências de `moved` e de
    `proof` `finding` não rodam: o case atual pode ser outro e o sandbox pode
    ter sido limpo. `fact` e `funcval` seguem conferidos.
  - **Seletor por kind.** `verified_by.kind: fact` aceita
    `path#kind:<kind>`, que passa com ao menos um fact daquele kind;
    `kind:` vazio não casa. `path#<id>` segue igual.
  - **`plan.tasks[].proof`** `{kind: funcval|fact|finding, ref}` substitui
    `test` só no operator; no dev é `schema_invalid` e `test` segue exigido
    (`task_without_test`). `funcval` e `fact` usam as conferências do define.
    `finding` é `<change_id>#<rule_id>` (ref sem `#<rule_id>` é
    `schema_invalid` em `tasks/<i>/proof/ref`); `change_id` vazio usa o do
    `build_report`.
  - **`build_report.tasks[].moved`** `{change_id, resolved: [rule_id, ...]}`
    substitui `red`/`green` só no operator; no dev é `schema_invalid` e
    `red_not_declared` continua. O gate lê `report.json` do sandbox ou
    `evidence/sandbox_report.json` da proposal.
  - `refused: moved_not_observed` — regra de `moved.resolved` (ou de um
    `proof` `finding` com o build `ready`/`done`) que o relatório não mostra em
    `resolved`, ou mostra também em `new`, ou relatório ausente.
  - `unresolved: finding_not_observed` — o mesmo para `proof` `finding` antes
    do build pronto.

Fora de A, de propósito: julgar se a prosa é boa ou o design é sensato. Isso é
do agente e de review; o gate não finge avaliar qualidade.

### 5.1 `change_kinds.yaml`

`docs/gates-por-mudanca.md` é prosa. Para `registry_unchecked` ser
determinístico, `change_kinds.yaml` mapeia cada chave para o título da seção e
para os registros exigidos:

```yaml
tool_or_verb:
  section: "Acrescentar ou alterar tool, verbo de CLI, agent ou skill: a referência gerada"
  registries: [surface_lock, generated_reference]
```

Um teste trava a deriva: todo título `## ` de `docs/gates-por-mudanca.md`
(exceto "Quando nada acima serve") aparece em alguma `section`, e toda
`section` existe no documento.

## 6. Superfície

| verbo | tool MCP | classe |
|---|---|---|
| `sparkforge sdd check [--feature X] [--root docs/sdd]` | `sparkforge_sdd_check` | `READ_ONLY` |
| `sparkforge sdd status [--root docs/sdd]` | `sparkforge_sdd_status` | `READ_ONLY` |
| `sparkforge sdd stamp <arquivo>` | `sparkforge_sdd_stamp` | `LOCAL_MUTATION` |

- `stamp` existe porque sha256 calculado à mão por agente erra, e cada erro vira
  `upstream_stale` falso. Grava `started`/`finished` no journal.
- **Sem `detail_level`.** No código, a flag só existe em verbo que devolve
  facts (`_add_detail_level` em `sparkforge/adapters/cli.py`), e a projeção
  `summary` trabalha sobre `provenance`, que recusa de SDD não tem. Mesmo
  tratamento de `judge`, `rules lookup` e `debate referee`.
- `status` diz, por feature, a fase atual, o `status` e as recusas que impedem
  avançar.

## 7. Erros

- YAML quebrado → `schema_invalid` com linha; nunca exceção.
- Raiz inexistente → `unresolved: root_missing`.
- Falha no journal não derruba `stamp` (regra 27).
- Saída: `0` ok, `1` com recusa; erro de uso segue a convenção dos verbos
  existentes em `sparkforge/cli/forge.py`.

## 8. O que a entrega move

- `docs/surface.lock.json` via `python scripts/check_surface_lock.py --update`,
  com o crescimento declarado no commit (regra 26);
- os registros manuais de tool nova (lista em `docs/gates-por-mudanca.md`,
  seção de tool/verbo, e a referência gerada);
- uma linha na tabela de verbos do `CLAUDE.md` (teto em
  `tests/test_bootstrap_budget.py`);
- nenhuma mudança em `LOTES`: `tests/test_sdd_*.py` já cai no lote `g-z`
  (`tests/test_suite_batches.py`);
- `python scripts/check_vnext_claims.py` antes do commit (arquivo `.py` novo
  move alegações).

## 9. Testes

- **Uma feature sintética por recusa**, montada em `tmp_path` por um construtor
  de teste, que dispara exatamente aquela recusa, e uma feature limpa que passa
  sem nada. Não há fixture estática: o hash de upstream em arquivo versionado é
  o caso que o checkout do Windows com `core.autocrlf=true` já quebrou uma vez
  (PR #63).
- **Cascata:** editar `define.md` torna `design.md` `upstream_stale`; `stamp`
  resolve.
- **`verified_by`:** conferido por `ast` contra arquivo de teste sintético,
  incluindo função ausente; antes do build sai `test_not_written`, no ship sai
  `verified_by_dangling`.
- **Perfil operador:** case e sandbox falsos em `tmp_path`.
- **Paridade:** CLI e MCP devolvem o mesmo payload.
- **Autonomia:** `stamp` recusado em nível sem `LOCAL_MUTATION`.
- **Deriva:** `change_kinds.yaml` × títulos de `docs/gates-por-mudanca.md`.
- **Regra 23:** `sparkforge/sdd/` não importa provider.

Todas as fixtures são sintéticas (repo público).

## 10. Critérios de aceite de A

1. Cada código das tabelas do §5 tem feature sintética que o produz e só ele.
2. A feature limpa sai `ok: true`, sem `refused` nem `unresolved`.
3. `stamp` seguido de `check` elimina `upstream_stale`.
4. `check`, `status` e `stamp` existem na CLI e no MCP com o mesmo payload.
5. `surface.lock`, referência gerada e `CLAUDE.md` atualizados, e os
   gates de `docs/gates-por-mudanca.md` aplicáveis passam.

## 11. Fora de escopo

- skills, templates e comandos `sdd-*` (B);
- ligação real com `change sandbox/propose` além de conferir que o `change_id`
  existe (C);
- desativar plugins, mover histórico, reescrever `CLAUDE.md` além da linha do
  verbo (D);
- qualquer afirmação de que o SDD próprio é melhor que os dois (E, regra 30);
- reexecutar testes, julgar qualidade de prosa.

## 12. Crédito

Estrutura de fases, templates e a ideia de manifesto de arquivos vêm do
AgentSpec (MIT, `luanmorenommaciel/agentspec`, 3.5.0) e do ciclo do superpowers.
A atribuição entra em `vendor/CREDITS.md` no subprojeto B, quando o primeiro
texto derivado entrar no repo.

## 13. Desvios na implementação

O que a entrega fez diferente do texto acima, ou decidiu onde ele calava. Os
itens da revisão já estão descritos no §5.0; aqui fica só o registro.

- **`explore` é opcional.** A ordem exigida começa no define, e o define só
  declara `upstream` quando `explore.md` existe (§5).
- **Feature inexistente é erro de uso do verbo**, não código do §5: `--feature`
  que a varredura não achou sai com exit 2 e aponta `sdd status`. As exceções
  são as ausências que uma lacuna já explica: `root_missing`, ou um
  `path_skipped` com o nome da feature.
- **Sem `detail_level`** nas três tools (§6).
- **Hash de texto.** `upstream.sha256` é o `text_sha256` (quebra de linha
  normalizada), não o hash dos bytes.
- **Features sintéticas em `tmp_path`**, sem fixture versionada (§9).
- **`stamp` recebe `root`** e recusa o que não é artefato (`not_an_artifact`),
  além de `sha_line_unsupported` e `upstream_flow_style`.
- **`path_skipped`** nasceu na revisão, e só para pulo que a descoberta leria
  (§5.0).
- **`delete` no manifesto** deixa de ser `manifest_path_unknown` depois que o
  build fica `ready` ou `done` (§5).
- **Endurecimento da revisão:** BOM de UTF-8 tolerado, comentário no fim da
  linha do hash preservado com o espaço antes do `#`, `change_id` confinado à
  pasta do sandbox, `case_id` comparado como texto, referência de teste lida
  como node id do pytest, `evaluate` público para o `status` usar a mesma
  passada do `check`, e `root_path: null` no MCP tratado como a raiz padrão.
