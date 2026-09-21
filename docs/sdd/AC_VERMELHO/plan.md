---
sdd: 1
feature: AC_VERMELHO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/AC_VERMELHO/design.md
  sha256: "b1c78ad94b04dad58fbcea2f1781af552d759fc77a753d806b1b685e82402ec0"
tasks:
  - id: T1
    files: [tests/test_sdd_ac_vermelho.py, sparkforge/sdd/checks.py, sparkforge/sdd/schema/define.json, docs/sdd/CONTRATO.md, tests/test_sdd.py, docs/claims.lock.json]
    covers: [AC1, AC2, AC3, AC4]
    test: {path: tests/test_sdd_ac_vermelho.py, name: test_criterio_sem_vermelho_ligado_e_recusado}
  - id: T2
    files: [docs/sdd/templates/define.md, skills/sdd-define/SKILL.md, skills/sdd-build/SKILL.md, .claude/skills/sdd-define/SKILL.md, .claude/skills/sdd-build/SKILL.md, .agents/skills/sdd-define/SKILL.md, .agents/skills/sdd-build/SKILL.md, docs/guia/referencia/skills/sdd-define.md, docs/guia/referencia/skills/sdd-build.md, docs/surface.lock.json, docs/claims.lock.json]
    covers: [AC5, AC6]
    test: {path: tests/test_surface_lock.py, name: TestOLockBateComAMedida::test_the_skills_match}
---

# AC_VERMELHO — plano

Duas tarefas. **T1** é a regra: o schema ganha `guard`, o `sdd check` ganha o gate
`_gate_acceptance_red`, e os quatro testes de AC1 a AC4 nascem em
`tests/test_sdd_ac_vermelho.py`. **T2** é o que a regra obriga a dizer: contrato já vai
na T1 (o `test_contrato_lista_todo_codigo` exige o código novo no mesmo commit do gate);
na T2 vão o template do define, as duas skills, os espelhos, a referência gerada e o lock
de superfície.

## O manifesto e o D5

O `files:` do design foi emendado nesta fase com o que a medida exigiu: `tests/test_sdd.py`,
os quatro espelhos das skills e as duas páginas da referência gerada. E o design ganhou o
**D5: o gate só age no perfil `dev`**. Medido com o gate dev-only injetado por plugin de
pytest sobre a árvore de hoje, sem editar teste nenhum: **6 testes caem**, todos em
`tests/test_sdd.py` (`test_phase_out_of_order_por_status`,
`test_dangling_so_com_build_report_pronto[ready-esperado1]`,
`test_delete_some_depois_do_build_pronto`,
`test_modify_sumido_e_recusado_mesmo_com_build_pronto`, `test_task_pulada_nao_exige_red`,
`test_claim_without_evidence`). Cinco são o `feature_limpa` registrando o `red` com o
arquivo e exit 1; o sexto é a tarefa pulada, que deixa o AC1 sem vermelho — ali a recusa
é a certa. Com o D5, o caso `operador` do corpus dourado, os três testes operator de
`moved` e o `tests/test_sdd_eval_suite.py` **não mudam** (medido: os cinco casos dourados
dão exatamente a recusa de antes, sem editar fixture).

Possível arquivo a mais, só se o gate de lastro listar: o documento auditado cujo texto
carrega o número que moveu (na GLUE_TERRAFORM foi `docs/harness/CODEINTEL-GAP.md`). O
plano não prevê quais ids caem; se cair, ele entra no commit e no *Desvios* do build.

## Antes de começar

1. Branch `sdd/ac-vermelho`. `git status --short` limpo, fora `docs/sdd/AC_VERMELHO/`.
2. `ls .sparkforge/traces.db` — o operador o apagou em 2026-09-21. Se reaparecer, algo
   construiu `ContextLedger()` fora do lugar e o `tests/conftest.py:85` acusa; pare e
   relate, não apague.
3. `ls .claude/agents/README.md` — hoje **ausente**. Se aparecer, copie-o para o
   scratchpad antes de qualquer `sync_skills.py` sem `--check` e restaure depois.
4. Toda edição por Edit/Write, nunca `sed -i`. Fim de linha LF. `line-length = 100`.
5. Mensagem de commit: escreva com Write num arquivo do **scratchpad da sua sessão** e
   rode `git commit -F` com o caminho real dele. Exemplo real, desta sessão:
   `C:/Users/edgar/AppData/Local/Temp/claude/E--projetos-spark-forge-aws/aecdc55f-7550-4610-801b-0b1e6d24fd0a/scratchpad/commit-t1.txt`.
   Nunca um marcador entre sinais de menor e maior: numa feature anterior ele foi
   executado literalmente e deixou lixo na raiz.

## O vermelho desta feature confere ela mesma

Esta feature muda o `sdd check` que confere `docs/sdd/AC_VERMELHO/`. Quando o
`build_report.md` dela ficar `ready`, o gate novo roda sobre ela: AC1 a AC4 são
`kind: test` e só a T1 os cobre, e a feature é `profile: dev`. Por isso o `red` da T1 no
build_report **cita os node ids** no comando — os quatro dos critérios e o do D5 —,
exatamente assim:

```yaml
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1 tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida tests/test_sdd_ac_vermelho.py::test_feature_operator_nao_e_conferida -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1 tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida tests/test_sdd_ac_vermelho.py::test_feature_operator_nao_e_conferida -q", exit: 0}
```

Rodar só `tests/test_sdd_ac_vermelho.py` não serve: os cinco falham por asserção, o exit
é 1, e arquivo com exit 1 não conta (AC2). O exit que vai para o relatório é o que
**apareceu**; se não for 1, pare e relate. AC5 e AC6 são `kind: command` e ficam fora
da regra (D4).

## T1 — a regra, o campo `guard` e os quatro testes

> Fecha **AC1**, **AC2**, **AC3** e **AC4**.

### 1. Escrever o teste que falha

Crie `tests/test_sdd_ac_vermelho.py` com exatamente este conteúdo. Ele reusa os helpers
de `tests/test_sdd.py` (precedente: `tests/test_sf_stubs.py` importa de
`tests.test_config_declarado_existe`).

```python
"""AC_VERMELHO: criterio de `kind: test` precisa ter sido visto vermelho por uma tarefa.

Cada teste cobre um criterio de `docs/sdd/AC_VERMELHO/define.md`, sobre a feature
sintetica de `tests/test_sdd.py::feature_limpa` -- a mesma que o resto do SDD usa. Ela
nasce com o ship em `done`, e feature entregue e historico: o gate so age com o ship
ausente ou fora de `done`. Por isso quase todo teste tira o ship antes de estragar UMA
coisa.

A ligacao entre criterio e vermelho e derivada, nunca registrada (D1 do design): o
`covers` do plan diz que tarefas cobrem o criterio, e o `red` de cada uma, no
build_report, diz o que ela viu falhar.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge.sdd.checks import check
from tests.test_sdd import _codigos, _define_meta, _meta, _reescreve, _restampa, feature_limpa

ROOT = Path(__file__).resolve().parents[1]
NODE = "tests/test_alvo.py::test_alvo"


def _sem_ship(repo: Path) -> dict[str, Path]:
    """A feature construida e ainda nao entregue: `feature_limpa` sem o ship."""
    caminhos = feature_limpa(repo)
    caminhos.pop("ship").unlink()
    return caminhos


def _red(caminhos: dict[str, Path], comando: str, saida: int) -> None:
    """Troca o `red` da T1 no build_report (o ultimo artefato: ninguem abaixo fica stale)."""
    meta = _meta(caminhos["build_report"])
    meta["tasks"][0]["red"] = {"command": comando, "exit": saida}
    _reescreve(caminhos["build_report"], tasks=meta["tasks"])


def test_criterio_sem_vermelho_ligado_e_recusado(tmp_path):
    """AC1: o red de uma tarefa que cobre o criterio cita o node id, ou sai a recusa."""
    caminhos = _sem_ship(tmp_path)
    _red(caminhos, f"python -m pytest {NODE} -q", 1)
    assert _codigos(check(tmp_path)) == ([], [])

    # o red viu OUTRO teste falhar
    _red(caminhos, "python -m pytest tests/test_alvo.py::test_outro -q", 1)
    recusas = check(tmp_path)["refused"]
    assert [(r["code"], r["path"], r["field"]) for r in recusas] == [
        ("acceptance_never_red", "docs/sdd/F1/build_report.md", "tasks"),
    ]
    assert "AC1" in recusas[0]["unlock"] and NODE in recusas[0]["unlock"]

    # prefixo do node id nao e o node id
    _red(caminhos, f"python -m pytest {NODE}_outro -q", 1)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])

    # o node id aparece, mas o exit e zero: red_not_declared ja nomeia a causa
    _red(caminhos, f"python -m pytest {NODE} -q", 0)
    assert _codigos(check(tmp_path)) == (["red_not_declared"], [])

    # o node id aparece no red de uma tarefa que NAO cobre o criterio
    plano = _meta(caminhos["plan"])
    plano["tasks"].append({
        "id": "T2", "files": [], "covers": [],
        "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
    })
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    build = _meta(caminhos["build_report"])
    build["tasks"] = [
        {"id": "T1", "status": "done",
         "red": {"command": "python -m pytest tests/test_alvo.py::test_outro -q", "exit": 1},
         "green": {"command": f"python -m pytest {NODE} -q", "exit": 0}},
        {"id": "T2", "status": "done",
         "red": {"command": f"python -m pytest {NODE} -q", "exit": 1},
         "green": {"command": f"python -m pytest {NODE} -q", "exit": 0}},
    ]
    _reescreve(caminhos["build_report"], tasks=build["tasks"])
    _restampa(tmp_path)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])


def test_arquivo_conta_com_exit_2_e_nao_com_exit_1(tmp_path):
    """AC2: so o arquivo conta com exit 2 (erro de coleta), nunca com exit 1."""
    caminhos = _sem_ship(tmp_path)
    for comando in ("python -m pytest tests/test_alvo.py -q",
                    "python -m pytest tests\\test_alvo.py -q",
                    "python -m pytest ./tests/test_alvo.py -q"):
        _red(caminhos, comando, 2)
        assert _codigos(check(tmp_path)) == ([], []), comando

    _red(caminhos, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])

    # exit 2 em OUTRO arquivo nao e o arquivo do criterio
    _red(caminhos, "python -m pytest tests/test_outro.py -q", 2)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])


def test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada(tmp_path):
    """AC3: `guard` com motivo isenta o criterio; `guard` vazio e schema_invalid."""
    caminhos = _sem_ship(tmp_path)
    _red(caminhos, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])

    meta = _define_meta(caminhos)
    meta["acceptance"][0]["guard"] = "guarda de regressao: passa antes e depois por desenho"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    _restampa(tmp_path)
    assert _codigos(check(tmp_path)) == ([], [])

    for vazio in ("", "   ", True):
        meta["acceptance"][0]["guard"] = vazio
        _reescreve(caminhos["define"], acceptance=meta["acceptance"])
        _restampa(tmp_path)
        recusas = check(tmp_path)["refused"]
        assert {(r["code"], r["path"], r["field"]) for r in recusas} == {
            ("schema_invalid", "docs/sdd/F1/define.md", "acceptance/0/guard"),
        }, vazio


def test_feature_entregue_e_historico_e_nao_e_conferida(tmp_path):
    """AC4: com o ship em done a regra nao confere; fora de done, confere."""
    caminhos = feature_limpa(tmp_path)
    _red(caminhos, "python -m pytest tests/test_alvo.py -q", 1)
    _restampa(tmp_path)  # o build_report mudou; o ship volta a casar com ele
    assert _codigos(check(tmp_path)) == ([], [])

    for status in ("ready", "draft"):
        _reescreve(caminhos["ship"], status=status)
        assert _codigos(check(tmp_path)) == (["acceptance_never_red"], []), status

    # build_report em draft: o build nao aconteceu, e a regra nao confere
    _reescreve(caminhos["build_report"], status="draft")
    refused, _ = _codigos(check(tmp_path))
    assert "acceptance_never_red" not in refused

    # as features do repositorio -- as entregues, e esta mesma -- passam na regra
    relatorio = check(ROOT)
    assert [r for r in relatorio["refused"] if r["code"] == "acceptance_never_red"] == []


def test_feature_operator_nao_e_conferida(tmp_path):
    """D5: so o perfil dev e conferido; no operator o contrato de `moved` fica como era."""
    operador = feature_limpa(tmp_path / "operador", "operator")
    operador.pop("ship").unlink()
    _red(operador, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path / "operador")) == ([], [])

    # o mesmo red no dev e recusado: o que isenta o operator e o perfil, nao o red
    dev = _sem_ship(tmp_path / "dev")
    _red(dev, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path / "dev")) == (["acceptance_never_red"], [])
```

`git add tests/test_sdd_ac_vermelho.py` logo depois de criar.

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1 tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida tests/test_sdd_ac_vermelho.py::test_feature_operator_nao_e_conferida -q
```

Esperado: **exit 1, 5 failed**, todos por `AssertionError` — o gate não existe, e o check
devolve `([], [])` onde o teste pede `acceptance_never_red` (no AC1, a lista de recusas
vem vazia; no AC3, a primeira asserção; no AC4, `AssertionError: ready`; no do D5, a
metade dev). Medido nesta fase contra a árvore de hoje. `ImportError` ou `NameError` aqui é teste quebrado, não
vermelho. Guarde o comando e o exit para o `red` da T1 (seção *O vermelho desta feature*).

### 3. Código mínimo

#### 3.1 `sparkforge/sdd/schema/define.json`

Troque a linha

```json
          "statement": {"type": "string", "minLength": 1},
```

por

```json
          "statement": {"type": "string", "minLength": 1},
          "guard": {"type": "string", "minLength": 1, "pattern": "\\S"},
```

`pattern: "\\S"` é o que faz `"   "` sair `schema_invalid` (D3: o motivo é texto que a
revisão lê).

#### 3.2 `sparkforge/sdd/checks.py`

Logo **depois** da função `_gate_red` (termina em `"(exit diferente de zero)")`), antes de
`def _gate_claims`, acrescente:

```python
def _vermelho_cita(referencia: str, vermelho: dict[str, Any] | None) -> bool:
    """O `red` viu `referencia` falhar: o node id no comando, ou so o arquivo com exit 2.

    Exit 2 no pytest e erro de coleta e deixa o arquivo inteiro vermelho; exit 1 com so
    o arquivo nao diz qual teste falhou. A comparacao e por token do comando, para que
    `::test_x` nao case `::test_x_outro`.
    """
    if not vermelho or vermelho["exit"] == 0:
        return False
    arquivo, _ = _separa_ref(referencia)
    for bruto in str(vermelho["command"]).split():
        token = bruto.strip("'\"").replace("\\", "/").removeprefix("./")
        if token == referencia or token.startswith(f"{referencia}["):
            return True
        if vermelho["exit"] == 2 and token == arquivo:
            return True
    return False


def _red_recusado(tarefa: dict[str, Any]) -> bool:
    """A tarefa que `_gate_red` ja recusou com `red_not_declared`: a causa nao se repete."""
    vermelho = tarefa.get("red")
    return tarefa["status"] == "done" and (not vermelho or vermelho["exit"] == 0)


def _gate_acceptance_red(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    """Todo `kind: test` sem `guard` foi visto vermelho por uma tarefa que o cobre.

    A ligacao e derivada, nunca registrada (D1 do design AC_VERMELHO): o `covers` do plan
    diz quem cobre o criterio, e o `red` do build_report diz o que falhou. Feature com o
    ship em `done` e historia e nao e conferida (D2). So o perfil dev: no operator o
    criterio e quase sempre funcval ou fact, e a tarefa prova por `moved` (D5).
    """
    if artefato.meta["profile"] != "dev":
        return
    define = ctx.artefatos.get("define")
    plano = ctx.artefatos.get("plan")
    if define is None or plano is None or not _build_pronto(ctx) or _ship_feito(ctx):
        return
    if "ship" in ctx.caminhos and "ship" not in ctx.artefatos:
        return  # o ship existe e foi recusado por schema: nao se sabe se e historia
    do_build = {tarefa["id"]: tarefa for tarefa in artefato.meta["tasks"]}
    for item in define.meta["acceptance"]:
        prova = item["verified_by"]
        if prova["kind"] != "test" or item.get("guard"):
            continue
        donas = [do_build[t["id"]] for t in plano.meta["tasks"]
                 if item["id"] in t["covers"] and t["id"] in do_build]
        if any(_vermelho_cita(prova["ref"], tarefa.get("red")) for tarefa in donas):
            continue
        if any(_red_recusado(tarefa) for tarefa in donas):
            continue
        ctx.recusa("acceptance_never_red", artefato.path, "tasks",
                   f"{item['id']}: nenhuma tarefa que o cobre viu {prova['ref']} vermelho; "
                   "o red de uma delas cita esse node id (ou so o arquivo, com exit 2), "
                   "ou o define declara guard com o motivo")
```

`_ship_feito` é definida mais abaixo no módulo; a chamada resolve em tempo de execução,
como já faz `_gate_case`. Nenhum import novo: `Any`, `_separa_ref` e `_build_pronto` já
existem no arquivo.

Na tabela `_GATES`, troque

```python
    "build_report": (_gate_order, _gate_upstream, _gate_red, _gate_claims, _gate_change),
```

por

```python
    "build_report": (
        _gate_order, _gate_upstream, _gate_red, _gate_acceptance_red, _gate_claims, _gate_change,
    ),
```

#### 3.3 `docs/sdd/CONTRATO.md` (no mesmo commit: `test_contrato_lista_todo_codigo` exige)

1. Troque a linha

   ```
   | `acceptance` | ≥ 1: `{id: AC<n>, statement, verified_by: {kind, ref}}` |
   ```

   por

   ```
   | `acceptance` | ≥ 1: `{id: AC<n>, statement, verified_by: {kind, ref}, guard?}`; `guard` é o motivo, texto não vazio, de uma guarda de regressão (passa antes e depois por desenho) e isenta o item de `acceptance_never_red` |
   ```

2. Na linha de `schema_invalid` da tabela de recusas, troque o trecho final
   ``; `proof` `finding` sem `#<rule_id>` | todas |`` por
   ``; `proof` `finding` sem `#<rule_id>`; `guard` vazio, só com espaço ou fora de texto | todas |``.

3. Logo **depois** da linha que começa com ``| `red_not_declared` |``, acrescente:

   ```
   | `acceptance_never_red` | só no perfil `dev`, com o build_report em `ready`/`done` e o ship ausente ou fora de `done`: `acceptance` de `kind: test` sem `guard` que nenhuma tarefa do plan com o AC em `covers` viu vermelho — o `red` dela precisa de `exit` diferente de zero **e** citar o node id do `verified_by` no comando, ou só o arquivo com `exit` 2 (erro de coleta); tarefa já recusada por `red_not_declared` não repete a causa, nem ship recusado por schema | build_report |
   ```

#### 3.4 `tests/test_sdd.py` — os registros que o gate move

1. Em `feature_limpa`, troque

   ```python
               "red": {"command": "pytest tests/test_alvo.py", "exit": 1},
   ```

   por

   ```python
               "red": {"command": "pytest tests/test_alvo.py::test_alvo", "exit": 1},
   ```

2. Em `test_task_pulada_nao_exige_red`, troque

   ```python
       _reescreve(caminhos["build_report"], tasks=[{"id": "T1", "status": "skipped"}])
       assert _codigos(check(tmp_path)) == ([], [])
   ```

   por

   ```python
       _reescreve(caminhos["build_report"], tasks=[{"id": "T1", "status": "skipped"}])
       # a tarefa pulada nao deve red; o criterio que so ela cobria fica sem vermelho
       assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])
   ```

Nada mais muda em `tests/test_sdd.py`: com o D5, os testes operator de `moved` não são
conferidos pela regra. Pelo mesmo motivo, o caso `operador` de `fixtures/sdd/` não muda, e
o caso `tdd` também não (lá a tarefa não tem `red`, `red_not_declared` já nomeia a causa,
e o gate não a repete).

### 4. Rodar e ver passar

O mesmo comando do passo 2. Esperado: **exit 0, 5 passed**.

### 5. Gates vizinhos, um comando por vez

```bash
python -m pytest tests/test_sdd.py -q
python -m pytest tests/test_sdd_operator.py tests/test_sdd_skills.py tests/test_sdd_migration.py -q
python -m pytest tests/test_fixtures_golden_sdd.py tests/test_sdd_eval_suite.py -q
python -m pytest tests/test_arvore_versionada.py tests/test_suite_batches.py -q
python -m ruff check sparkforge scripts tests
python -m sparkforge.adapters.cli sdd check --repo .
```

Medido nesta fase com o gate dev-only injetado e as duas edições de 3.4 aplicadas numa
cópia: `tests/test_sdd.py` 165 passed e os cinco novos passed; sobre a árvore de hoje,
`test_sdd_operator.py`, `test_sdd_skills.py`, `test_sdd_migration.py`,
`test_fixtures_golden_sdd.py` e `test_sdd_eval_suite.py` passam sem edição, com os cinco
casos dourados dando exatamente a recusa de antes; e `sdd check --repo .` sem
`acceptance_never_red` em feature nenhuma. Se o
`sdd check` do repositório mostrar `acceptance_never_red` em qualquer feature entregue,
**pare e relate**: é a hipótese falhando, não algo a ajustar no define dela.

### 6. Gate de lastro

Com a árvore da T1 no estado final e o arquivo novo já no índice:

```bash
python scripts/check_vnext_claims.py
```

Em **primeiro plano**, com timeout de 300000 ms. Remedie **pela lista de ids que a saída
listar**, um por vez; nunca `--seed`, nunca por varredura. Cada entrada tem `text`,
`context` e `proof.expect.value`, e o valor vem de rodar a própria `proof.cmd` por
`shlex.split` (nunca `shell=True`). Regrave `docs/claims.lock.json` com
`json.dumps(dado, ensure_ascii=False, indent=2) + "\n"`, **sem** `sort_keys`. Se o número
também estiver escrito no documento auditado, esse documento entra no commit (e nos
*Desvios* do build_report, porque não está no manifesto). Saída vazia: não toque no lock. Rode de novo até exit 0.

### 7. Commit

```bash
git add tests/test_sdd_ac_vermelho.py sparkforge/sdd/checks.py sparkforge/sdd/schema/define.json docs/sdd/CONTRATO.md tests/test_sdd.py
git commit -F C:/Users/edgar/AppData/Local/Temp/claude/E--projetos-spark-forge-aws/aecdc55f-7550-4610-801b-0b1e6d24fd0a/scratchpad/commit-t1.txt
```

(Troque o caminho pelo do scratchpad da sua sessão, com o arquivo já escrito por Write.)
Mensagem:

```
feat(sdd): refuse a test criterion that no task ever saw red

`sdd check` confirmed that each `verified_by` test exists and has a node id.
It never confirmed that the test had failed before the code, and a test never
seen failing was never seen verifying anything: CONFIG_OCA:AC4 passed green
end to end while pointing at a test that did not read the file it described.

`_gate_acceptance_red` derives the link instead of recording it: the plan's
`covers` says which tasks cover a criterion, the build report's `red` says
what failed. A task counts when `red.exit != 0` and the command carries the
criterion's node id, or only its file with exit 2 (a collection error, which
leaves the whole file red). File with exit 1 does not count.

A regression guard that passes before and after by design is declared with
`guard: "<reason>"` in the define; an empty guard is `schema_invalid`. A
feature whose ship is `done` is history and is not checked, so the delivered
features keep passing. Only the dev profile is checked: operator criteria are
mostly funcval or fact, and the `moved` contract stays as it was.

The synthetic `feature_limpa` recorded the file with exit 1; it now carries
the node id, and a skipped task that alone covered a criterion now leaves it
refused.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

Se o gate de lastro listou ids, acrescente `docs/claims.lock.json` (e o documento
auditado) ao `git add`, e um parágrafo à mensagem com os ids e o valor medido.

## T2 — contrato escrito onde a próxima feature lê

> Fecha **AC5** e **AC6**.

Tarefa sem vermelho próprio: o `test` dela é o gate que falha depois de editar as skills
e antes de regenerar o lock, `tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_skills_match`.

### 1. O "teste" que falha: editar as skills

Edite **só as fontes** em `skills/`; os espelhos saem do `sync_skills.py`.

**`skills/sdd-define/SKILL.md`**

1. Troque a linha

   ```
   Prefira `test`. Critério que nada verifica é desejo, e não entra.
   ```

   por

   ```
   Prefira `test`. Critério que nada verifica é desejo, e não entra.

   **`kind: test` precisa ser visto vermelho.** No perfil `dev`, com o build pronto e
   o ship fora de `done`, o check exige uma tarefa do plan com o AC em `covers` cujo `red`, no
   build_report, tenha exit diferente de zero e cite o node id do `verified_by` — ou só
   o arquivo, com exit 2 (erro de coleta). Sem isso, `acceptance_never_red`. A exceção é
   a **guarda de regressão**, o teste que passa antes e depois por desenho (o que impede
   "recusar mais" de virar "recusar tudo"): declare `guard: "<o motivo>"` no item. O
   motivo é o que a revisão lê; `guard` vazio é `schema_invalid`.
   ```

2. Em *Red flags*, depois da linha `- Critério sem `verified_by`, ou com "conferir manualmente".`,
   acrescente a linha:

   ```
   - `guard` num critério que devia falhar antes do código, ou com motivo que não diz por que ele passa sempre.
   ```

**`skills/sdd-build/SKILL.md`**

1. Em *Por tarefa*, troque

   ```
   1. **Vermelho.** Escreva o teste da tarefa. Rode o comando do plano. Veja a
      falha certa. Anote `red: {command, exit}` com o exit **que apareceu**.
   ```

   por

   ```
   1. **Vermelho.** Escreva o teste da tarefa. Rode o comando do plano. Veja a
      falha certa. Anote `red: {command, exit}` com o exit **que apareceu**. O
      comando cita o **node id** de cada critério `kind: test` que a tarefa cobre
      (`python -m pytest tests/a.py::test_x tests/a.py::test_y -q`); só o arquivo
      conta apenas com exit 2, erro de coleta.
   ```

2. Em *O relatório*, depois do bullet que termina em `` `red_not_declared`. ``,
   acrescente o bullet:

   ```
   - **Cada critério `kind: test` visto vermelho.** No perfil `dev`, com o relatório
     em `ready` ou `done` e o ship fora de `done`, todo `acceptance` de `kind: test` sem `guard`
     precisa de uma tarefa que o cubra (`covers` do plan) cujo `red` tenha exit
     diferente de zero e cite o node id do `verified_by` — ou o arquivo, com exit 2.
     Sem isso, `acceptance_never_red`. Arquivo com exit 1 não conta: não diz qual
     teste falhou.
   ```

3. Em *Referência rápida*, troque

   ```
   Recusas desta fase: `red_not_declared`, `claim_without_evidence`,
   ```

   por

   ```
   Recusas desta fase: `red_not_declared`, `acceptance_never_red`, `claim_without_evidence`,
   ```

**`docs/sdd/templates/define.md`** — em `## Critérios`, depois do bullet que termina em
``build escrevê-lo.``, acrescente:

```
- `guard: "<motivo>"` num item de `acceptance` declara guarda de regressão: um
  teste que passa antes e depois por desenho. Ele fica isento de
  `acceptance_never_red` (regra do perfil `dev`); sem `guard`, todo `kind: test` precisa de uma tarefa
  cujo `red` cite o node id dele (ou o arquivo, com exit 2). `guard` vazio é
  `schema_invalid`.
```

(O frontmatter do template não muda: `test_templates_formam_feature_valida` carimba e
confere os seis templates, e o `red` do template de build_report já cita o node id.)

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_skills_match -q
```

Esperado: **exit 1**, `AssertionError` em `total_bytes` das skills. Se sair 0, a medida
não lê o que foi editado: pare e relate. Este comando e o exit vão para o `red` da T2.

### 3. Regenerar o que as skills movem

1. `git status --short .claude .agents .github` — anote. `ls .claude/agents/README.md`
   (ausente em 2026-09-21; se existir, copie ao scratchpad antes do passo 2).
2. `python scripts/sync_skills.py` e depois `python scripts/sync_skills.py --check` (exit 0).
3. `git status --short .claude .agents .github` — têm de aparecer **exatamente** quatro
   `M`: `.claude/skills/sdd-define/SKILL.md`, `.claude/skills/sdd-build/SKILL.md`,
   `.agents/skills/sdd-define/SKILL.md`, `.agents/skills/sdd-build/SKILL.md`. Qualquer
   `D` é o sync apagando o que não rastreia: `git checkout -- <o caminho>` e relate.
4. `python scripts/gen_reference_docs.py` e depois `python scripts/gen_reference_docs.py --check`.
   Esperado: mudam `docs/guia/referencia/skills/sdd-define.md` e `sdd-build.md`, e só.
5. `python scripts/check_surface_lock.py --update`. Anote o crescimento com
   `git diff docs/surface.lock.json` (o `total_bytes` das skills antes e depois): ele vai
   para a mensagem do commit (regra 26).

### 4. Rodar e ver passar

O mesmo comando do passo 2. Esperado: **exit 0**.

### 5. Gates vizinhos, um comando por vez

```bash
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q
python -m pytest tests/test_reference_docs.py tests/test_surface_lock.py -q
python -m pytest tests/test_sdd_skills.py tests/test_sdd.py tests/test_sdd_ac_vermelho.py -q
python -m pytest tests/test_arvore_versionada.py -q
python -m sparkforge.adapters.cli sdd check --repo .
```

`tests/test_agents_parity.py::TestMirrors::test_sync_check_passes_after_sync` roda o
`sync_skills.py` em modo escrita: confira `.claude/agents/README.md` de novo depois dele.

### 6. Gate de lastro

Com a árvore no estado final da feature:

```bash
python scripts/check_vnext_claims.py
```

Primeiro plano, timeout 300000 ms, e a mesma disciplina da T1 passo 6: remediar só pelos
ids da saída, `proof.cmd` por `shlex.split`, `json.dumps(dado, ensure_ascii=False,
indent=2) + "\n"` sem `sort_keys`, repetir até exit 0. Este é o `verified_by` do AC6, e
o `sync_skills.py --check` do passo 5 é o do AC5: os dois precisam sair exit 0 aqui.

### 7. Commit

```bash
git add skills/sdd-define/SKILL.md skills/sdd-build/SKILL.md docs/sdd/templates/define.md .claude/skills/sdd-define/SKILL.md .claude/skills/sdd-build/SKILL.md .agents/skills/sdd-define/SKILL.md .agents/skills/sdd-build/SKILL.md docs/guia/referencia/skills/sdd-define.md docs/guia/referencia/skills/sdd-build.md docs/surface.lock.json
git commit -F C:/Users/edgar/AppData/Local/Temp/claude/E--projetos-spark-forge-aws/aecdc55f-7550-4610-801b-0b1e6d24fd0a/scratchpad/commit-t2.txt
```

(Caminho do scratchpad da sua sessão, arquivo escrito por Write.) Mensagem, com os dois
números de bytes lidos no passo 3.5 no lugar das palavras ANTES e DEPOIS:

```
docs(sdd): teach the define and build skills that a test criterion must be seen red

`sdd-define` says when to declare `guard` and why its reason is the part the
review reads; `sdd-build` says the red command carries the node id of every
test criterion the task covers, and lists `acceptance_never_red` among the
phase's refusals. The define template shows the field.

Surface grows by declaration (rule 26): skills total_bytes ANTES -> DEPOIS.
Mirrors and the generated skill reference regenerated from the sources.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

Se o gate de lastro listou ids, acrescente `docs/claims.lock.json` (e o documento
auditado) ao `git add`, e um parágrafo com os ids e o valor medido.

## Ao fechar o build

O `build_report.md` desta feature registra a T1 com os quatro node ids no `red` (seção
*O vermelho desta feature*) e a T2 com o comando do passo 2 dela. Depois do stamp,
`python -m sparkforge.adapters.cli sdd check --repo . --feature AC_VERMELHO` tem de sair
sem recusa: é o gate novo conferindo a feature que o criou.
