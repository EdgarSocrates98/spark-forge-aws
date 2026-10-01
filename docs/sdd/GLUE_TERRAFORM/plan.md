---
sdd: 1
feature: GLUE_TERRAFORM
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/GLUE_TERRAFORM/design.md
  sha256: "31f4c2b96eecce27a6b489fe259ea171ba41916b69eec11b4e0aa4d0f855a837"
tasks:
  - id: T1
    files: [tests/test_glue_terraform.py, sparkforge/facts/glue_terraform.py, sparkforge/facts/stepfunctions.py, sparkforge/facts/airflow_dag.py, docs/claims.lock.json, docs/harness/CODEINTEL-GAP.md]
    covers: [AC1, AC2, AC3, AC4, AC5]
    test: {path: tests/test_glue_terraform.py, name: test_a_definicao_e_unica_e_os_dois_extratores_importam}
---

# GLUE_TERRAFORM — plano

**Uma tarefa só, e de propósito.** Isto é um movimento de código: criar o módulo sem
trocar os chamadores, ou trocar os chamadores sem criar o módulo, deixa a árvore vermelha
entre dois commits. Os registros que a mudança move entram no mesmo commit, pela regra da
casa.

## T1 — as duas funções passam a ter uma definição só

> Fecha **AC1**, **AC2**, **AC3**, **AC4** e **AC5**.

### 1. Escrever o teste que falha

Crie `tests/test_glue_terraform.py` com exatamente este conteúdo:

```python
"""Guarda do modulo auxiliar que le o Terraform de job Glue.

Os tres testes cobrem coisas diferentes: que a definicao e UNICA (AC1), que ela
responde o mesmo de antes (AC2), e que o modulo NAO e tratado como extrator (AC3).

O terceiro existe por causa de uma regra permanente do `CLAUDE.md` -- "Extrator novo
entra nas duas listas manuais de teste e na medida de snippet" -- que esta certa e NAO
se aplica aqui. Quem seguir o habito e acrescentar `glue_terraform` aquelas listas leva
um `AttributeError` dentro de um `frozenset().union(...)`, sem contexto nenhum. Este
teste transforma isso num vermelho que explica.
"""
from __future__ import annotations

from pathlib import Path

from sparkforge.facts import airflow_dag, glue_terraform, stepfunctions
from sparkforge.facts.glue_terraform import glue_jobs_por_nome, glue_max_retries
from sparkforge.findings.models import Fact

RAIZ = Path(__file__).resolve().parents[1]


def _tf_name(arquivo: str, simbolo: str, valor: str) -> Fact:
    return Fact(
        kind="tf.attribute",
        subject={"file": arquivo, "symbol": simbolo, "line": 1},
        attrs={"key": "name", "block": "root", "literal": True, "value": valor},
    )


def _tf_retries(arquivo: str, simbolo: str, valor, literal: bool = True) -> Fact:
    return Fact(
        kind="tf.attribute",
        subject={"file": arquivo, "symbol": simbolo, "line": 2},
        measures={"value": valor},
        attrs={"key": "max_retries", "block": "root", "literal": literal, "value": valor},
    )


def test_a_definicao_e_unica_e_os_dois_extratores_importam():
    """AC1: uma definicao, e os dois extratores usam ELA.

    A conferencia e por IDENTIDADE (`is`), nao por nome: um `from ... import` que
    trouxesse uma copia igual passaria num teste de nome e falha aqui.
    """
    assert stepfunctions.glue_jobs_por_nome is glue_terraform.glue_jobs_por_nome
    assert stepfunctions.glue_max_retries is glue_terraform.glue_max_retries
    assert airflow_dag.glue_jobs_por_nome is glue_terraform.glue_jobs_por_nome
    assert airflow_dag.glue_max_retries is glue_terraform.glue_max_retries

    # E nenhuma copia local sobreviveu.
    for nome in ("stepfunctions", "airflow_dag"):
        fonte = (RAIZ / "sparkforge" / "facts" / f"{nome}.py").read_text(encoding="utf-8")
        assert "def _glue_jobs_por_nome" not in fonte, nome
        assert "def _max_retries" not in fonte, nome


def test_as_tres_origens_de_max_retries_e_o_indice_por_nome():
    """AC2: o comportamento e o de antes, origem por origem."""
    facts = [
        _tf_name("a.tf", "aws_glue_job.carga", "carga-diaria"),
        _tf_retries("a.tf", "aws_glue_job.carga", 3),
        _tf_name("b.tf", "aws_glue_job.outro", "carga-diaria"),
        _tf_name("c.tf", "aws_glue_job.semretry", "sem-retry"),
        # Ruido que o indice tem de ignorar: outro recurso, outro bloco, nao literal.
        Fact(
            kind="tf.attribute",
            subject={"file": "d.tf", "symbol": "aws_s3_bucket.x", "line": 1},
            attrs={"key": "name", "block": "root", "literal": True, "value": "balde"},
        ),
        Fact(
            kind="tf.attribute",
            subject={"file": "d.tf", "symbol": "aws_glue_job.dinamico", "line": 1},
            attrs={"key": "name", "block": "root", "literal": False, "value": "${var.n}"},
        ),
    ]

    nomes = glue_jobs_por_nome(facts)
    assert set(nomes) == {"carga-diaria", "sem-retry"}
    assert [(a, s) for a, s, _ in nomes["carga-diaria"]] == [
        ("a.tf", "aws_glue_job.carga"),
        ("b.tf", "aws_glue_job.outro"),
    ]
    # O terceiro elemento e o id do fact lido, que entra em `derived_from`.
    assert nomes["sem-retry"][0][2] == facts[3].id

    # literal
    assert glue_max_retries(facts, "a.tf", "aws_glue_job.carga") == ("literal", 3, facts[1].id)
    # absent vale 0: atributo nao declarado nao pede retry
    assert glue_max_retries(facts, "c.tf", "aws_glue_job.semretry") == ("absent", 0, None)

    # not_literal pelo proprio atributo
    interpolado = [*facts, _tf_retries("e.tf", "aws_glue_job.interp", "${var.r}", literal=False)]
    origem, n, fid = glue_max_retries(interpolado, "e.tf", "aws_glue_job.interp")
    assert (origem, n) == ("not_literal", None)
    assert fid == interpolado[-1].id

    # not_literal CONSERVADOR: o tf.unresolved nao carrega o endereco do recurso, entao
    # qualquer um de `max_retries` no MESMO arquivo contamina o arquivo inteiro. Nunca
    # um zero que ninguem leu.
    contaminado = [
        _tf_name("f.tf", "aws_glue_job.sem", "sem-atributo"),
        Fact(
            kind="tf.unresolved",
            subject={"file": "f.tf", "symbol": "", "line": 9},
            attrs={"key": "max_retries", "reason": "interpolation"},
        ),
    ]
    assert glue_max_retries(contaminado, "f.tf", "aws_glue_job.sem") == ("not_literal", None, None)


def test_o_modulo_auxiliar_nao_conta_como_extrator():
    """AC3: `EMITTED_KINDS` e o que distingue extrator de auxiliar, nas TRES varreduras.

    A regra do `CLAUDE.md` que manda por extrator novo nas duas listas manuais NAO vale
    aqui, e este teste e o lugar onde isso esta escrito de forma executavel.
    """
    assert not hasattr(glue_terraform, "EMITTED_KINDS")
    assert not hasattr(glue_terraform, "EXTRACTOR_ID")
    assert not [n for n in dir(glue_terraform) if n.startswith("extract_")]

    # As duas listas manuais fazem `frozenset().union(*(m.EMITTED_KINDS for m in
    # EXTRACTORS))`: o modulo la dentro levantaria AttributeError na COLETA, e a
    # mensagem nao diria por que. A conferencia e por texto para nao importar os
    # modulos de teste um do outro.
    for arquivo in (
        "tests/test_rules_catalog_reachability.py",
        "tests/test_fixtures_kind_coverage.py",
        "tests/test_harness_untrusted.py",
    ):
        fonte = (RAIZ / arquivo).read_text(encoding="utf-8")
        assert "glue_terraform" not in fonte, (
            f"{arquivo} cita glue_terraform. Ele NAO e extrator: nao emite kind, nao le "
            "artefato, e as listas manuais fazem union de EMITTED_KINDS. Ver AC3 de "
            "docs/sdd/GLUE_TERRAFORM/define.md."
        )
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_glue_terraform.py -q
```

Falha esperada: **exit 2**, erro na **coleta**, com a linha decisiva
`ModuleNotFoundError: No module named 'sparkforge.facts.glue_terraform'`. O módulo
ausente é a unidade sob teste, então isso conta como vermelho pela regra da casa.

Confirme também o estado de partida, para o relato:

```bash
python -c "import pathlib; print(sum(pathlib.Path('sparkforge/facts/'+n+'.py').read_text(encoding='utf-8').count('def _glue_jobs_por_nome') for n in ('stepfunctions','airflow_dag')))"
```

Deve imprimir `2`.

### 3. Código mínimo

#### 3.1 Criar `sparkforge/facts/glue_terraform.py`

```python
"""Leitura do Terraform de job Glue, compartilhada pelos extratores de orquestracao.

ESTE MODULO NAO E EXTRATOR. Ele nao le artefato, nao tem `EXTRACTOR_ID`, nao tem
`EMITTED_KINDS` e nao emite `Fact` nenhum: ele LE facts que `terraform.py` ja extraiu
(`tf.attribute`, `tf.unresolved`) e devolve estrutura Python que as derivacoes
`build_sfn_glue_link` (`stepfunctions.py`) e `build_af_glue_link` (`airflow_dag.py`)
usam para montar os facts delas.

A ausencia de `EMITTED_KINDS` e o que o mantem fora das TRES varreduras do repositorio:
a de `scripts/check_status_numbers.py::_extratores`, a de `pkgutil` em
`tests/test_harness_untrusted.py`, e as duas listas manuais
(`tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`),
cujo `EMITTABLE` faz `frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))` e
levantaria `AttributeError` se alguem o acrescentasse la. O precedente do lugar sao
`runtime_matrix` e `pricing`, que moram em `facts/` pelo mesmo motivo.

As duas funcoes moraram duplicadas em `stepfunctions.py` e `airflow_dag.py` do
incremento do Step Functions ate este: a copia foi deliberada, esta registrada em
`docs/sdd/AIRFLOW_DAG/ship.md`, e tres revisoes finais seguidas conferiram a mao que
elas nao tinham divergido.
"""
from __future__ import annotations

from collections.abc import Sequence

from sparkforge.findings.models import Fact

__all__ = ["glue_jobs_por_nome", "glue_max_retries"]


def glue_jobs_por_nome(facts: Sequence[Fact]) -> dict[str, list[tuple[str, str, str]]]:
    """Nome literal do job -> [(arquivo, endereco, id do fact)], de `tf.attribute` `name`.

    Um mesmo nome pode vir de mais de um recurso, e por isso o valor e LISTA: quem
    chama decide o que fazer com a ambiguidade, e as duas derivacoes a nomeiam em
    `job_definition_ambiguous` em vez de escolher uma.
    """
    nomes: dict[str, list[tuple[str, str, str]]] = {}
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        subject = fact.subject or {}
        attrs = fact.attrs or {}
        simbolo = str(subject.get("symbol") or "")
        if not simbolo.startswith("aws_glue_job."):
            continue
        if attrs.get("key") != "name" or attrs.get("block") != "root" or not attrs.get("literal"):
            continue
        arquivo = str(subject.get("file") or "")
        nomes.setdefault(str(attrs.get("value")), []).append((arquivo, simbolo, fact.id))
    return nomes


def glue_max_retries(
    facts: Sequence[Fact], arquivo: str, simbolo: str
) -> tuple[str, int | None, str | None]:
    """(`literal`, n, id), (`absent`, 0, None) ou (`not_literal`, None, id|None).

    O terceiro elemento e o id do `tf.attribute` lido, que entra em `derived_from`.

    `absent` vale 0 porque o atributo nao declarado nao pede retry. Valor interpolado
    vira `tf.unresolved` sem o endereco do recurso (`terraform.py`); por isso qualquer
    `tf.unresolved` de `max_retries` no MESMO arquivo torna a resposta `not_literal` --
    conservador de proposito: nunca um zero que ninguem leu.
    """
    for fact in facts:
        subject = fact.subject or {}
        if fact.kind != "tf.attribute" or subject.get("symbol") != simbolo:
            continue
        if subject.get("file") != arquivo:
            continue
        attrs = fact.attrs or {}
        if attrs.get("key") != "max_retries" or attrs.get("block") != "root":
            continue
        valor = (fact.measures or {}).get("value")
        if attrs.get("literal") and isinstance(valor, int | float) and not isinstance(valor, bool):
            return "literal", int(valor), fact.id
        return "not_literal", None, fact.id
    interpolado = any(
        f.kind == "tf.unresolved"
        and (f.attrs or {}).get("key") == "max_retries"
        and (f.subject or {}).get("file") == arquivo
        for f in facts
    )
    return ("not_literal", None, None) if interpolado else ("absent", 0, None)
```

#### 3.2 `sparkforge/facts/stepfunctions.py`

1. No bloco de imports, **depois** de `from sparkforge.facts.scan import iter_source_files`,
   acrescente:

   ```python
   from sparkforge.facts.glue_terraform import glue_jobs_por_nome, glue_max_retries
   ```

2. **Apague** as duas funções `_glue_jobs_por_nome` e `_max_retries` inteiras, com os
   docstrings delas.

3. Em `build_sfn_glue_link`, troque as duas chamadas:
   - `nomes = _glue_jobs_por_nome(facts)` → `nomes = glue_jobs_por_nome(facts)`
   - `origem, retries, retries_id = _max_retries(facts, arquivo, simbolo)` →
     `origem, retries, retries_id = glue_max_retries(facts, arquivo, simbolo)`

#### 3.3 `sparkforge/facts/airflow_dag.py`

O mesmo, nos quatro pontos equivalentes: o import depois de
`from sparkforge.facts.scan import iter_source_files`, as duas funções apagadas — **com
os docstrings que declaravam a duplicação de propósito, que deixam de ser verdade** — e
as duas chamadas em `build_af_glue_link`.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_glue_terraform.py -q
```

Exit 0, 3 passed.

### 5. Gates vizinhos, um comando por vez

```bash
python -m pytest tests/test_stepfunctions.py tests/test_airflow_dag.py -q
python -m pytest tests/test_fixtures_golden_stepfunctions.py tests/test_fixtures_golden_airflow.py -q
python -m pytest tests/test_facts_fusion.py tests/test_fixtures_golden_fusion.py -q
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_harness_untrusted.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py -q
python -m ruff check sparkforge scripts tests
python scripts/check_status_numbers.py --strict
```

**Nenhum golden pode mudar.** Se algum mudar, **pare e relate** — é a hipótese falhando,
não algo a regenerar.

`check_status_numbers.py --strict` tem de continuar em `0 divergencia(s)` **sem** você
editar o `STATUS.md`: a contagem de extratores não se move, porque o módulo novo não tem
`EMITTED_KINDS`. Se ela se mover, o módulo ficou com `EMITTED_KINDS` por engano.

Faça `git add` do arquivo novo **antes** de `tests/test_arvore_versionada.py`.

### 6. Gate de lastro

```bash
python scripts/check_vnext_claims.py
```

Passa dos 2 minutos: rode em segundo plano. Remedie **pela lista de ids que a saída
listar**, um por vez, nunca `--seed` e nunca por varredura. **O plano não prevê quais
ids caem** — nas quatro tarefas da feature anterior ele errou as quatro vezes. Cada
entrada tem `text`, `context` **e** `proof.expect.value`, e o valor vem de rodar a
própria `proof.cmd` por `shlex.split`, nunca `shell=True`. Regrave
`docs/claims.lock.json` com `json.dumps(..., ensure_ascii=False, indent=2) + "\n"` e
**sem** `sort_keys`. Se a saída vier vazia, não toque no lock nem no `CODEINTEL-GAP.md`.

### 7. Commit

```bash
git add sparkforge/facts/glue_terraform.py tests/test_glue_terraform.py \
  sparkforge/facts/stepfunctions.py sparkforge/facts/airflow_dag.py
git commit -F <arquivo com a mensagem>
```

Mensagem:

```
refactor(facts): give the Glue Terraform readers a single definition

`_glue_jobs_por_nome` and `_max_retries` existed twice, in `stepfunctions.py`
and `airflow_dag.py`, with identical bodies. The duplication was deliberate when
the Airflow domain landed, and the docstring said where it belonged: "o lugar
certo da funcao e um modulo proprio". Three final reviews in a row checked by
hand that the copies had not drifted. Repeated manual checking is the symptom.

`sparkforge/facts/glue_terraform.py` is not an extractor: it reads facts, not
artifacts, and has no `EMITTED_KINDS`. That absence is what keeps it out of all
three sweeps the repository runs, and `tests/test_glue_terraform.py` now says so
executably — the manual lists union `EMITTED_KINDS`, so adding it there would
raise `AttributeError` with no explanation.

No golden changed and the published extractor count did not move.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

Se o gate de lastro tiver listado ids, acrescente `docs/claims.lock.json` e o documento
auditado ao `git add`, e um parágrafo à mensagem dizendo quais ids e com que valor
medido.
