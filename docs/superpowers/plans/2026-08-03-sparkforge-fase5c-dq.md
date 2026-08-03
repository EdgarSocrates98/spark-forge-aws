# SparkForge Fase 5c — SF-DQ: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** uma área `SF-DQ` que afirma onde a validação de dados está, se ela tem consequência e quanto ela custa — sobre o mesmo `.py` que o motor já lê.

**Architecture:** extrator próprio (`sparkforge/facts/data_quality.py`) caminha a AST e **decide as correlações**, porque o motor de regras avalia um fact por vez; o catálogo lê atributo de um fact só. Quatro kinds, quatro regras, coordenador próprio, oito fixtures com golden bidirecional.

**Tech Stack:** Python stdlib (`ast`), YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-03-sparkforge-fase5c-dq-design.md`](../specs/2026-08-03-sparkforge-fase5c-dq-design.md) — §4.4 é a tradução de gatilho em condição, e §7 são os nove critérios que esta fase fecha.

**Base:** [Fase 5b](2026-08-01-sparkforge-fase5b-emr.md) fixou os dois padrões que esta fase reusa inteiros: *se a resposta depende de mais de uma propriedade, o extrator decide e emite* (`SF-EMR-008`), e *exclusão contada, nunca silenciosa* (`opaque_caller_function_count`).

---

## Fatos do ambiente verificados antes de escrever este plano

```
engine.py:48   _condition_candidates  avalia UM fact por vez (where/expr sobre um fact)
engine.py:68   _absent_satisfied      compara so `kind`
engine.py:73   _subject_group_key     symbol se houver, senao "file:line"
               -> correlacao entre facts NAO e expressavel no YAML

pyspark_ast.py 40KB, 20 kinds, ja emite pyspark.write / .cache / .action / .read
grep -ril "deequ|great.expectations|dbt"  ->  so STATUS.md   (folha em branco)

EXTRACTORS e declarado DUAS vezes, manualmente:
    tests/test_rules_catalog_reachability.py:44   (tupla)
    tests/test_fixtures_kind_coverage.py:44       (dict)

scripts/sync_skills.py   espelha agents/ e skills/ para .claude/, .agents/, .github/agents/
catalogo   58 regras, 10 areas | testes 2852 passando, 5 skipped
```

---

## File Structure

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/data_quality.py` | reconhece validação na AST e decide as correlações |
| `rules/catalog/data-quality.yaml` | área `SF-DQ` |
| `knowledge/dq/validation-frameworks.md` | o que a pesquisa da Task 0 apurou, com data |
| `agents/data-quality-reviewer.md` | coordenador da área |
| `skills/review-data-validation/SKILL.md` | fluxo focado |
| `tests/test_facts_data_quality.py` | extrator |
| `tests/test_fixtures_golden_dq.py` | golden do domínio |
| `tests/test_dq_investigation_end_to_end.py` | prova do objetivo |
| `fixtures/dq/*` | oito casos |

**Modificados:** `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`, `sparkforge/adapters/{cli,_core,tools}.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`, `docs/superpowers/STATUS.md`.

---

## Task 0: Pesquisa de fontes

Primeiro, e antes de qualquer código. Na Fase 5b três dos quatro candidatos de regra morreram nesta etapa; aqui há três premissas explicitamente marcadas como não verificadas na §4.3 do spec.

**Files:**
- Create: `knowledge/dq/validation-frameworks.md`

- [x] **Step 1: Great Expectations — qual é a superfície pública hoje**

Busque a documentação oficial vigente (`docs.greatexpectations.io`) e responda, com URL e data:
1. A 1.x ainda expõe `SparkDFDataset` e métodos `expect_*` chamáveis direto sobre um DataFrame?
2. Qual é a forma canônica de validar um DataFrame Spark na versão corrente?
3. O nome do pacote importado mudou (`great_expectations` continua)?

- [x] **Step 2: PyDeequ — alcance e superfície**

Mesma disciplina, sobre `github.com/awslabs/python-deequ` e a doc da AWS:
1. `VerificationSuite(spark).onData(df).addCheck(...).run()` continua a entrada?
2. Quais versões de Spark a release corrente acompanha? Compare com `GLUE_MATRIX` e `EMR_MATRIX` — se PyDeequ não alcançar as versões que o repo cobre, `proposed_change` não pode recomendá-lo.
3. Uma `VerificationSuite` com N checks é uma passada só sobre o dado? Esta resposta é o fundamento de `attrs.single_pass`, e sem ela `SF-DQ-004` não pode existir.

- [x] **Step 3: `assert` sob `python -O`**

Fonte: a referência da linguagem Python (`docs.python.org`, seção `assert`). Confirme que `assert` é removido quando `__debug__` é falso, e verifique se Glue e EMR rodam o driver com `-O` por padrão. Se rodarem, `assert` **não** é consequência; se não rodarem, é consequência com ressalva escrita dentro do achado.

- [x] **Step 4: Escreva `knowledge/dq/validation-frameworks.md`**

Uma seção por pergunta, cada afirmação com URL e `retrieved:`. Onde a fonte contrariar o spec, escreva o veto — ele vai para o cabeçalho de `rules/catalog/data-quality.yaml` na Task 7, e é o que impede alguém de reinventar a premissa morta.

- [x] **Step 5: Commit**

```bash
git add knowledge/dq/validation-frameworks.md
git commit -m "docs: pesquisa de fontes das tres premissas nao verificadas da 5c"
```

---

## Task 1: Extrator — esqueleto, sentinela e o check artesanal

**Files:**
- Create: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [x] **Step 1: Escreva o teste que falha**

```python
# tests/test_facts_data_quality.py
import ast

from sparkforge.facts.data_quality import EMITTED_KINDS, extract_data_quality


def _facts(source: str):
    return extract_data_quality(ast.parse(source), "job.py")


def test_o_modulo_varrido_deixa_sentinela():
    facts = _facts("x = 1\n")
    kinds = [f.kind for f in facts]
    assert kinds == ["dq.module_analyzed"]
    assert facts[0].measures["check_count"] == 0


def test_filter_count_comparado_e_um_check_artesanal():
    facts = _facts(
        "ruins = clientes.filter(clientes.cpf.isNull()).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('cpf nulo')\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 1
    assert checks[0].attrs["framework"] == "handmade"
    assert checks[0].attrs["target"] == "clientes"
    assert checks[0].subject["line"] == 1


def test_kind_fora_do_namespace_declarado_e_erro():
    assert "dq.check" in EMITTED_KINDS
    assert "dq.module_analyzed" in EMITTED_KINDS
```

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_facts_data_quality.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sparkforge.facts.data_quality'`

- [x] **Step 3: Implemente o mínimo**

```python
# sparkforge/facts/data_quality.py
"""Extrator de Facts sobre VALIDACAO DE DADOS num modulo PySpark.

Modulo separado de `pyspark_ast.py` -- que ja tem 40 KB e 20 kinds -- porque
reconhecer validacao e responsabilidade propria, com frameworks proprios. O
custo aceito e caminhar a mesma AST duas vezes.

Este extrator DECIDE as correlacoes (posicao relativa ao write, persistencia do
alvo, numero de checks sobre o mesmo alvo) porque o motor de regras avalia um
fact por vez: `engine._condition_candidates` le o contexto de um unico fact e
`engine._absent_satisfied` compara so `kind`. E o mesmo padrao que `SF-EMR-008`
fixou na Fase 5b -- se a resposta depende de mais de uma propriedade, o extrator
decide e emite.

Nunca aplica limiar, nunca atribui severidade, nunca adivinha alvo: alvo nao
resolvido vira `dq.unresolved`, contado e nao presumido.
"""
from __future__ import annotations

import ast
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "data_quality@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "dq.check",
        "dq.enforcement",
        "dq.unresolved",
        "dq.module_analyzed",
    }
)

# `count` sobre uma cadeia que passou por um destes e a forma artesanal: filtra
# o que viola a regra e conta o que sobrou.
_HANDMADE_GATES = frozenset({"filter", "where"})


def _subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _chain_root(node: ast.AST) -> tuple[str | None, list[str]]:
    """(nome da variavel raiz, metodos chamados na cadeia, da raiz para fora)."""
    methods: list[str] = []
    current = node
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        methods.append(current.func.attr)
        current = current.func.value
    while isinstance(current, ast.Attribute):
        current = current.value
    methods.reverse()
    if isinstance(current, ast.Name):
        return current.id, methods
    return None, methods


def _handmade_check(node: ast.Call, path: str, provenance: dict[str, Any]) -> Fact | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "count":
        return None
    target, methods = _chain_root(node)
    if not any(m in _HANDMADE_GATES for m in methods):
        return None
    if target is None:
        return None
    return Fact(
        kind="dq.check",
        subject=_subject(path, node.lineno),
        measures={"line": node.lineno},
        attrs={"framework": "handmade", "check_type": "count_of_violations", "target": target},
        provenance=provenance,
    )


def extract_data_quality(tree: ast.AST, path: str, artifact_sha256: str = "") -> list[Fact]:
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fact = _handmade_check(node, path, provenance)
            if fact is not None:
                facts.append(fact)

    check_count = sum(1 for f in facts if f.kind == "dq.check")
    unresolved_count = sum(1 for f in facts if f.kind == "dq.unresolved")
    facts.append(
        Fact(
            kind="dq.module_analyzed",
            subject=_subject(path),
            measures={"check_count": check_count, "unresolved_count": unresolved_count},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)
```

- [x] **Step 4: Rode e veja passar**

Run: `python -m pytest tests/test_facts_data_quality.py -v`
Expected: PASS, 3 testes

- [x] **Step 5: Alvo não resolvível vira `dq.unresolved`, nunca um alvo adivinhado**

Teste primeiro:

```python
def test_alvo_que_nao_e_variavel_vira_unresolved():
    facts = _facts("ruins = spark.table('t').filter('x is null').count()\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.unresolved"]
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert unresolved.attrs["reason"] == "unresolved_target"
```

Rode. **O `FAIL` medido não é o previsto** (desvio D-5c-6): o check não some — ele sai
com `attrs.target == "spark"`. `_chain_root` desce a cadeia inteira e a raiz de
`spark.table("t")` é o `ast.Name` da *sessão*, não do dado. Nomear a sessão como alvo é
exatamente o alvo adivinhado que esta fase recusa: `SF-DQ-001` passaria a comparar a linha
deste check com o `write` de qualquer outro DataFrame que também saia de `spark`. Além do
helper, portanto, a cadeia que passa por um método que **constrói** o DataFrame a partir da
raiz (`_SOURCE_TERMINALS`: os oito de `_READ_TERMINALS` em `pyspark_ast.py:55` —
`table`, `sql`, `parquet`, `csv`, `json`, `orc`, `load`, `format` — mais `range`,
`createDataFrame`, `text` e `jdbc`) também vira `dq.unresolved`.

A presença é testada em **qualquer posição da cadeia**, e a primeira versão desta correção
errou aqui (achado da revisão da Task 1): testar só o primeiro elo deixava passar
`spark.read.format("delta").load(p).filter(...).count()` e
`spark.read.option("mergeSchema", "true").parquet(p).filter(...).count()` — `option`,
`schema` e `format` configuram o reader antes do terminal e empurram o terminal para fora
da posição 0. As duas formas voltavam a nomear a sessão como alvo, e são a leitura
canônica de Delta/Iceberg/JDBC em job Glue real, não caso de canto. Acrescente o helper,
que as Tasks 3 e 4 também usam:

```python
def _unresolved(path: str, line: int, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="dq.unresolved",
        subject=_subject(path, line),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )
```

E troque o `return None` do alvo ausente em `_handmade_check` por:

```python
    if target is None or any(m in _SOURCE_TERMINALS for m in methods):
        return _unresolved(
            path, node.lineno, "unresolved_target", provenance, check_type="count_of_violations"
        )
```

Rode de novo: PASS.

- [x] **Step 6: `extract_data_quality_path` e `_tree`**

Mesma convenção de `athena_workgroup.py`: falha de leitura vira `dq.unresolved` com `reason: "read_error"`, `SyntaxError` vira `reason: "syntax_error"`, nunca exceção que derruba quem chamou.

```python
def extract_data_quality_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [
            Fact(
                kind="dq.unresolved",
                subject=_subject(anchor),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance=empty,
            )
        ]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance_sha = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            Fact(
                kind="dq.unresolved",
                subject=_subject(anchor, exc.lineno or 0),
                attrs={"reason": "syntax_error", "detail": str(exc.msg)},
                provenance=provenance_sha,
            )
        ]
    return extract_data_quality(tree, anchor, artifact_sha256=sha)


def extract_data_quality_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    facts: list[Fact] = []
    for py_file in sorted(root.rglob("*.py")):
        facts.extend(extract_data_quality_path(py_file, repo_root))
    return sort_facts(facts)
```

Acrescente `import hashlib` e `from pathlib import Path` no topo. Teste com `tmp_path`: um `.py` válido, um com sintaxe quebrada, e confirme que o segundo devolve um único `dq.unresolved` com `reason: "syntax_error"`.

Uma correção medida sobre o `_tree` acima (desvio D-5c-7): a guarda de
`extract_data_quality_path` é estreita demais para o que a travessia encontra. Um `.py` que
não decodifica levanta `UnicodeDecodeError` — um `ValueError`, **não** um `OSError` — e
escaparia, derrubando a árvore inteira por causa de um arquivo. `extract_data_quality_tree`
envolve cada arquivo num `except Exception` que vira `dq.unresolved` com
`reason: "read_error"`, exatamente como `athena_workgroup.extract_athena_workgroup_tree` já
fazia, e o teste com bytes inválidos é o que prova.

- [x] **Step 7: Commit**

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py
git commit -m "feat(facts): extrator de validacao de dados, com o check artesanal"
```

---

## Task 2: As correlações que o motor não faz

O núcleo da fase. Cada atributo aqui existe porque a §4.4 do spec mediu que o YAML não consegue expressá-lo.

**Files:**
- Modify: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [x] **Step 1: `attrs.position_vs_write` — três valores, nunca booleano**

Teste primeiro:

```python
def test_check_depois_do_write_marca_a_posicao():
    facts = _facts(
        "vendas.write.mode('overwrite').parquet('s3://b/p')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "after_write"


def test_check_antes_do_write_marca_a_posicao():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.mode('overwrite').parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "before_write"


def test_modulo_que_valida_e_nao_escreve_nao_e_before_write():
    facts = _facts("ruins = vendas.filter(vendas.valor < 0).count()\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "no_write_in_module"
```

Run: `python -m pytest tests/test_facts_data_quality.py -k position -v` → FAIL (`KeyError: 'position_vs_write'`)

Implemente uma varredura prévia que colhe, por variável, a linha do primeiro `write`:

```python
_WRITE_ATTRS = frozenset({"write", "writeTo", "writeStream"})


def _write_lines_by_target(tree: ast.AST) -> dict[str, int]:
    """Primeira linha de write por variavel. `df.write...` aparece como
    Attribute encadeado, entao a raiz da cadeia e o alvo."""
    lines: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or node.attr not in _WRITE_ATTRS:
            continue
        current: ast.AST = node.value
        while isinstance(current, ast.Attribute | ast.Call):
            current = current.func.value if isinstance(current, ast.Call) else current.value
        if isinstance(current, ast.Name):
            lines.setdefault(current.id, node.lineno)
    return lines


def _position_vs_write(target: str, line: int, writes: dict[str, int]) -> str:
    write_line = writes.get(target)
    if write_line is None:
        return "no_write_in_module"
    return "after_write" if line > write_line else "before_write"
```

Chame `_write_lines_by_target(tree)` uma vez no topo de `extract_data_quality` e passe o dict a `_handmade_check`, que acrescenta `"position_vs_write": _position_vs_write(target, node.lineno, writes)` aos `attrs`.

Run: PASS.

**O esqueleto acima não sobreviveu à medição** (desvio D-5c-8). Rodado sobre três formas
que o repositório contém, ele produz:

| Fonte | `_write_lines_by_target` do plano |
|---|---|
| `carrega('vendas').write.parquet(p)` | `AttributeError: 'Name' object has no attribute 'value'` |
| `spark.read.parquet(a).write.parquet(b)` | `{'spark': 1}` |
| write em laço (linha 2) e write raso (linha 4) | `{'vendas': 4}` |

São três defeitos, e cada um tem teste:

1. **A descida da cadeia quebra.** `current.func.value if isinstance(current, ast.Call)` assume
   que `func` é sempre um `ast.Attribute`; quando é um `ast.Name` — `f(x).write...` — não há
   `.value`, e a extração inteira morre por causa de uma linha. O caminhamento correto já
   existia: `_chain_root` trata as duas formas e devolve `None` para a raiz que não é nome.
2. **A raiz da cadeia de leitura não é o alvo.** A mesma armadilha da Task 1 (D-5c-6), agora do
   lado do write: `spark.read.parquet(a).write...` registraria a *sessão* como alvo escrito, e
   um check enraizado em `spark` seria datado contra a publicação de um dado que nunca o tocou.
   `_chain_target` reusa `_SOURCE_TERMINALS` e devolve `None` — a cadeia de leitura não entra
   no registro.
3. **`setdefault` não guarda a primeira linha do arquivo.** `ast.walk` percorre por nível, não
   por linha: um write dentro de um laço é visitado *depois* de um write no corpo do módulo, e
   "a primeira que eu vi" fica sendo a linha 4 quando a primeira do arquivo é a 2 — o check da
   linha 3 sairia `before_write` tendo validado depois de publicar. O índice guarda o
   **conjunto** de linhas por alvo e quem consome escolhe o extremo: `min` para o write.

O helper único `_lines_by_target(tree, attrs, methods)` responde às três perguntas dos Steps 1
e 2 (write, persist, action), e `_ModuleIndex` as carrega juntas — `_write_lines_by_target`
como função separada não sobreviveu.

- [x] **Step 2: `attrs.target_persisted` e `attrs.action_after_check`**

Teste primeiro:

```python
def test_check_sobre_df_nao_persistido_com_action_depois():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is False
    assert check.attrs["action_after_check"] is True


def test_df_persistido_antes_do_check():
    facts = _facts(
        "vendas.cache()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True
```

Implemente com a mesma forma do Step 1: uma varredura que colhe `cache`/`persist` por variável (só conta se a linha for **anterior** à do check) e outra que colhe as actions por variável (`write`, `count`, `collect`, `show`, `foreach`, `save`, `saveAsTable`), marcando `action_after_check` quando existir action sobre o mesmo alvo em linha posterior à do check e que não seja o próprio check.

Run: PASS.

- [x] **Step 3: `measures.checks_on_target` e `attrs.shares_scan`**

> **Corrigido pela Task 0** (desvio D-5c-1 do spec). O atributo chamava-se
> `single_pass` e afirmava "N checks, uma passada" — falso: Deequ faz *scan
> sharing por agrupamento*, e `isUnique` paga passada própria. `shares_scan`
> afirma só o que a fonte autoriza. `measures.declared_checks` **não entra**
> (D-5c-2): contar `addCheck` não conta restrições.

Teste primeiro:

```python
def test_dois_checks_no_mesmo_alvo_contam_um_ao_outro():
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count()\n"
        "b = vendas.filter(vendas.cliente.isNull()).count()\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 2
    assert {c.measures["checks_on_target"] for c in checks} == {2}
    assert {c.attrs["shares_scan"] for c in checks} == {False}


def test_check_unico_nao_compartilha_varredura():
    facts = _facts("a = vendas.filter(vendas.valor < 0).count()\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.measures["checks_on_target"] == 1
    assert check.attrs["shares_scan"] is False
```

`shares_scan` é `False` para todo check artesanal: cada `count()` é uma varredura própria, sem compartilhamento nenhum. Ele vira `True` só na Task 3, para a `VerificationSuite`, e a §2.3 de `knowledge/dq/validation-frameworks.md` é a fonte que autoriza — e que delimita: scan sharing por agrupamento, não passada única.

Implemente contando os checks por alvo **depois** de construí-los, num segundo passe sobre a lista de facts (o valor não é conhecível durante a primeira travessia).

Run: PASS.

**Dois falsos positivos medidos na revisão** (desvio D-5c-9). Os quatro atributos correlacionam
por **nome nu**, e nome nu não identifica objeto. A revisão da Task 2 reproduziu duas fontes em
que o extrator acusava código correto:

```python
def a(vendas):                       # colisão entre escopos
    vendas.write.parquet(1)
def b(vendas):
    return vendas.filter(1).count()  # saía after_write, datado contra o write de `a`

vendas.write.parquet(p)              # rebind entre o write e o check
vendas = carrega('outra')
ruins = vendas.filter(...).count()   # saía after_write, sobre um DF nunca escrito
```

As correções, ambas no padrão que a fase já usa:

1. **Índice por escopo.** Corpo do módulo e cada `FunctionDef`/`AsyncFunctionDef` viram escopos
   separados (`_scopes`), e write, persist, action e `checks_on_target` só correlacionam dentro
   do próprio escopo. `_ModuleIndex` virou `_ScopeIndex`. `checks_on_target` também passou a ser
   por escopo: dois checks homônimos em duas funções não são dois checks sobre o mesmo alvo, e
   contá-los juntos afirmaria varredura repetida sobre um dado que não é o mesmo.
2. **Religação do nome.** Dentro de um escopo, `vendas = carrega('outra')` troca o objeto sem
   trocar o nome, então evidência de um lado da religação não vale do outro. Todo `ast.Name` em
   contexto `Store` conta, o que cobre `Assign`, `AnnAssign`, `AugAssign`, alvo de `for` e
   `with ... as` de uma vez. **Os quatro atributos tratam religação** — a diferença entre eles é
   a *direção do erro*, não estilo:
   - `position_vs_write` **omite a chave** (não inventa um quarto valor). `engine._where_matches`
     reprova caminho ausente, então `SF-DQ-001` não avalia o check — é o mecanismo de D-5c-3.
   - `target_persisted` e `action_after_check` emitem **`false`**. `SF-DQ-003` dispara sobre esses
     dois valores, então tanto o valor errado quanto a ausência calariam a regra, e omitir faria
     da religação um jeito de sumir com ela.
   - Na `action_after_check` a religação invalida **a action que vem depois dela, não o intervalo
     inteiro**: com check em 2, action em 3, religação em 5 e action em 7, a de 3 continua valendo
     e o atributo é `true`. São N candidatas, e cada uma responde por si.
3. **`target_persisted` afirma estado, não ocorrência.** `cache()` / `unpersist()` / check saía
   `True`. O último evento antes do check decide, e a posição é `(linha, coluna)` para que dois
   eventos na mesma linha ainda se ordenem.

**A propriedade que fecha o D-5c-9** — e que está escrita no cabeçalho do módulo, não como quatro
notas soltas: *nome nu não identifica objeto*. Entre escopos, o índice é por escopo; dentro de um
escopo, a religação invalida a evidência do outro lado. Um atributo que erra para menos cala a
regra e custa subnotificação; um que erra para mais faz o motor **acusar código correto**.
`action_after_check` é o único dos quatro do lado da acusação — `SF-DQ-003` dispara sobre
`action_after_check: true` — e por isso é o que mais precisa da guarda.

`checks_on_target` também passou a ser por escopo, e a decisão está registrada como **D-5c-10** na
§10 do spec: dois homônimos em duas funções não são dois checks sobre o mesmo alvo, e contá-los
juntos faria `SF-DQ-004` afirmar varredura repetida sobre dado que não é o mesmo. Vence a letra da
§4.4, que dizia "no módulo".

Cinco limites ficam **documentados no ponto do código e não corrigidos**, e todos erram para
menos: alias não é seguido (`df2 = vendas`); check irmão conta como `action_after_check` — é
verdade, mas quem ler "o dado é reusado" se engana, porque o reuso é recomputo; write e check na
mesma linha via `;` caem em `before_write`; `lambda`/corpo de `class` não são escopos separados; e
a separação por escopo introduz o quinto — função que lê um DataFrame global perde a correlação
com o write do módulo e sai `no_write_in_module`.

- [x] **Step 4: Commit**

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py
git commit -m "feat(facts): as correlacoes que o motor nao expressa viram atributo"
```

---

## Task 3: PyDeequ e Great Expectations

**Files:**
- Modify: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [x] **Step 1: Confira a Task 0 antes de escrever**

Releia `knowledge/dq/validation-frameworks.md`. Se a pesquisa mostrou que a superfície do GE 1.x é outra, **o teste abaixo muda para a forma apurada**, e o veto à forma antiga vai para o cabeçalho do catálogo na Task 7. Não escreva detecção para uma API que a fonte diz não existir mais.

- [x] **Step 2: Teste do PyDeequ**

```python
def test_verification_suite_compartilha_varredura():
    facts = _facts(
        "from pydeequ.verification import VerificationSuite\n"
        "r = VerificationSuite(spark).onData(vendas).addCheck(c1).addCheck(c2).run()\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 1
    assert checks[0].attrs["framework"] == "pydeequ"
    assert checks[0].attrs["target"] == "vendas"
    assert checks[0].attrs["shares_scan"] is True
    assert "declared_checks" not in checks[0].measures
```

Run: FAIL (nenhum `dq.check`).

- [x] **Step 3: Reconheça pela forma, não por lista de nomes**

```python
def _pydeequ_check(
    node: ast.Call, path: str, writes: dict[str, int], provenance: dict[str, Any]
) -> Fact | None:
    """`VerificationSuite(spark).onData(df).addCheck(...).run()`. A cadeia e
    reconhecida por CONTER `onData` e terminar em `run`, nao por casar a
    sequencia exata -- a ordem dos `addCheck` varia e a API aceita encadeamento
    livre."""
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "run":
        return None
    _, methods = _chain_root(node)
    if "onData" not in methods:
        return None
    target = _on_data_argument(node)          # Name passado a onData(...)
    if target is None:
        return _unresolved(
            path, node.lineno, "unresolved_target", provenance, check_type="verification_suite"
        )
    return Fact(
        kind="dq.check",
        subject=_subject(path, node.lineno),
        measures={"line": node.lineno},
        attrs={
            "framework": "pydeequ",
            "check_type": "verification_suite",
            "target": target,
            # `shares_scan`, nao `single_pass`: o runner do Deequ agrupa as
            # agregacoes que compartilham o mesmo agrupamento e as roda numa
            # passada; `isUnique`/entropia exigem re-particionamento e pagam
            # passada propria (Schelter et al., PVLDB 2018, §4.1 e §5.1 --
            # knowledge/dq/validation-frameworks.md §2.3). Uma suite com N
            # checks custa uma passada POR AGRUPAMENTO, nunca uma.
            "shares_scan": True,
            "position_vs_write": _position_vs_write(target, node.lineno, writes),
        },
        provenance=provenance,
    )
```

`_on_data_argument` percorre a cadeia procurando a chamada cujo `func.attr == "onData"` e devolve o `id` do primeiro argumento quando ele é um `ast.Name`; `None` caso contrário. Registre `_pydeequ_check` junto de `_handmade_check` na travessia de `extract_data_quality`, e garanta que um mesmo `ast.Call` produz **um** fact só.

Run: PASS.

**A assinatura acima não sobreviveu à Task 2** (desvio D-5c-11). O esqueleto recebe
`writes: dict[str, int]` e escreve `"position_vs_write": _position_vs_write(...)` **dentro do
literal de `attrs`**, incondicionalmente — que é a forma anterior à correção do D-5c-9. Copiada
como está, ela reintroduz no PyDeequ os dois falsos positivos que a Task 2 mediu: o write de um
homônimo em outro escopo dataria a suíte, e a religação do nome entre o write e a suíte produziria
`after_write` sobre um DataFrame que nunca foi escrito. Além disso a suíte não recebia
`target_persisted` nem `action_after_check`, e `SF-DQ-003` avaliaria só o check artesanal.

A correção é um construtor **único** para os três frameworks — `_check(path, line, index,
provenance, *, framework, check_type, target, **extra)` —, que aplica os quatro atributos de
correlação por escopo, omite `position_vs_write` sob religação e recebe por `extra` só o que cada
framework permite afirmar (`shares_scan` nos dois primeiros, chave nenhuma no GE). É o mesmo
argumento que reuniu `_rebound_between` num predicado só: um segundo caminho por framework
divergiria, e divergência aqui é falso positivo ou falso negativo.

Duas medições confirmadas antes de escrever, ambas contra o que o esqueleto sugere:

| Forma | Medido |
|---|---|
| `_chain_root` sobre `VerificationSuite(spark).onData(vendas)...run()` | `(None, ['onData', 'addCheck', 'addCheck', 'run'])` — a raiz é um `ast.Call`, e **não** um `ast.Name` |
| `lineno` da chamada externa numa cadeia quebrada em quatro linhas | `1` — a linha do início da expressão, e não a do `.run()` |

Ou seja: a detecção usa só `methods` de `_chain_root`, e o alvo sai exclusivamente do argumento de
`onData`. Se a raiz nomeasse alguém, seria `VerificationSuite` ou `spark` — o alvo adivinhado que
`_SOURCE_TERMINALS` recusa do outro lado.

- [x] **Step 4: Great Expectations, na forma que a Task 0 apurou (desvio D-5c-3)**

A pesquisa fechou este step. `SparkDFDataset` não existe desde a 1.0.0, e a detecção por prefixo `expect_*` está **vetada**: o prefixo sobrevive em `Validator.__getattr__`, e o AST não sabe se a variável é um `Validator` — casar por prefixo produz falso positivo sobre qualquer objeto.

O que resta é estreito e verdadeiro: o DataFrame aparece sob **chave literal** no dict de `batch_parameters`.

```python
def test_great_expectations_pela_chave_literal_do_batch_parameters():
    facts = _facts(
        "import great_expectations as gx\n"
        "res = validation_definition.run(batch_parameters={'dataframe': vendas})\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["framework"] == "great_expectations"
    assert check.attrs["target"] == "vendas"
    # Quantas expectativas rodam vive no store do contexto, FORA do .py.
    # Chave ausente e a forma de dizer "nao sei" sem virar `false`.
    assert "shares_scan" not in check.attrs
```

Reconheça o `ast.Call` que tem `keyword` chamado `batch_parameters` cujo valor é um `ast.Dict` com a chave constante `"dataframe"`; o alvo é o `ast.Name` daquele valor, e um valor que não seja `Name` vira `dq.unresolved` com `reason: "unresolved_target"`.

A chave `shares_scan` fica **fora** dos `attrs` deste framework, de propósito: `engine._where_matches` reprova caminho ausente, então `SF-DQ-004` não avalia check de GE — que é o correto, porque o extrator não sabe quantas expectativas a suíte tem.

**Duas decisões que o step não fixava** (desvio D-5c-12), ambas medidas contra a §1.2 da pesquisa:

1. **`check_type` nomeia a evidência, não o objeto.** O receptor de `batch_parameters` varia — a
   documentação corrente mostra `validation_definition.run(...)`, e `Checkpoint.run(...)` aceita o
   mesmo argumento —, então `check_type: "validation_definition"` afirmaria um objeto que o AST não
   enxerga. O valor é `batch_parameters_dataframe`: exatamente o que foi lido.
2. **Sem a chave literal não há `dq.unresolved`.** `batch_parameters=params` (não é dict literal) e
   `batch_parameters={'ano': 2026}` (sem a chave) produzem fact **nenhum**. Sem `"dataframe"` nada
   prova que a chamada é do Great Expectations, e contar como ponto cego qualquer função com um
   argumento homônimo inflaria `unresolved_count` com ruído. `dq.unresolved` fica para o caso em que
   a validação **está** reconhecida e o alvo é que não se lê — `{'dataframe': spark.table('t')}`.
   Erra para menos, que é a direção aceita nesta área.

**Dois buracos medidos na revisão da Task 3, e os dois fechados.**

**D-5c-13 — só o dict inline era detectado, e a documentação não usa dict inline.** A forma da §1.2
de `knowledge/dq/validation-frameworks.md` monta o dict numa linha e o passa por nome na seguinte:

```python
batch_parameters = {"dataframe": dataframe}
validation_definition.run(batch_parameters=batch_parameters)
```

Com só o dict inline reconhecido, isso produzia **fact nenhum** — o suporte a GE reconhecia a forma
que a fonte oficial não usa, e o recall em código real ficava perto de zero. A correção segue o
nome **um passo**, dentro do escopo: `_dict_bindings` indexa os dicts literais ligados a cada nome,
e `_dict_bound_to` devolve o último ligado antes da linha do uso. Duas guardas, ambas reusando o
que já existia em vez de reescrever:

- **Religação invalida**, pelo mesmo `_rebound_between` dos quatro atributos: em `params = {...}` /
  `params = f()` / `run(batch_parameters=params)`, o dict lido não é o que chega à chamada. Isso
  também é o que faz um nome ligado a chamada de função (`params = monta()`) não produzir alvo.
- **Mesmo escopo**, pelo mesmo motivo que o índice inteiro é por escopo.

Sem ligação legível não há `dq.unresolved`: o argumento do D-5c-12 continua valendo, porque sem a
chave literal nada prova que a chamada é do Great Expectations.

**D-5c-14 — suíte com `onData` e sem `run` era ponto cego não contado.**
`VerificationSuite(spark).onData(vendas).addCheck(c).useRepository(rep)` produzia nada e não entrava
em `unresolved_count`, o que contraria a disciplina que a 5b fixou com
`opaque_caller_function_count`: exclusão contada, nunca silenciosa. Passa a sair `dq.unresolved` com
`reason: "suite_run_not_visible"`.

É ponto cego e **não** achado, e a razão está escrita no código porque quem vier depois vai querer
transformá-la em regra: a cadeia pode ser guardada numa variável e executada em outro lugar
(`s = VerificationSuite(...).onData(df)` / `s.run()`), e o extrator não segue o objeto. A afirmação
honesta é "há uma suíte aqui cuja execução eu não enxergo", nunca "esta suíte não roda".

A implementação obrigou uma mudança de forma no `_pydeequ_check`: a detecção deixou de exigir que o
terminal seja `run` e passa a exigir que `run` **esteja na cadeia** — senão `.run().printResults()`
seria lido como suíte não executada —, e só o nó **mais externo** da cadeia responde por ela
(`_ScopeIndex.chained`, o `id()` de todo nó que é receptor de outra chamada). Sem esse recorte, uma
cadeia de quatro elos emitiria um fact por elo, já que `onData` está nos `methods` de todos.

- [x] **Step 5: Rode a suíte inteira do extrator**

Run: `python -m pytest tests/test_facts_data_quality.py -v`
Expected: PASS

Medido: **86 passed** no arquivo (50 antes desta task; 72 antes de D-5c-13 e D-5c-14), e **2938
passed / 5 skipped** na suíte inteira. `ruff check .` limpo, e
`git diff --stat main -- fixtures/pyspark/` vazio.

- [x] **Step 6: Commit**

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py knowledge/dq/validation-frameworks.md
git commit -m "feat(facts): pydeequ e great expectations, reconhecidos pela forma"
```

---

## Task 4: `dq.enforcement` — a consequência que o extrator prova

**Files:**
- Modify: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [x] **Step 1: Teste primeiro — e note o subject**

```python
def test_check_com_raise_produz_enforcement_no_mesmo_subject():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('valor negativo')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.subject == check.subject
    assert enforcement.attrs["form"] == "raise"


def test_resultado_lido_sem_aborto_nao_e_enforcement():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "print(ruins)\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_resultado_nunca_lido_nao_e_enforcement():
    facts = _facts("vendas.filter(vendas.valor < 0).count()\n")
    assert not [f for f in facts if f.kind == "dq.enforcement"]
```

O subject idêntico é o que faz `same_subject` de `SF-DQ-002` funcionar (spec §4.4). Proteção pela metade — resultado lido, sem aborto — **não emite**.

Run: FAIL.

Medido: **18 failed / 95 passed** no arquivo. Os três testes acima viraram vinte e um, e os negativos (`resultado_lido_sem_aborto`, `resultado_nunca_lido`) já passavam antes da implementação — como tinham de passar, porque asseguram ausência.

- [x] **Step 2: Implemente**

Percurso: (1) achar o `ast.Assign` cujo valor é o `Call` do check e guardar o nome da variável; (2) procurar `ast.If` cujo `test` referencia esse nome e cujo `body` contém `ast.Raise`, `sys.exit` ou `os._exit`; (3) procurar `ast.Assert` cujo `test` referencia o nome. Cada acerto emite um `dq.enforcement` com o **subject do check** e `attrs.form` em `{"raise", "exit", "assert"}`, mais `measures.line` da própria consequência.

```python
def _enforcement(check_subject, form: str, line: int, provenance) -> Fact:
    return Fact(
        kind="dq.enforcement",
        subject=dict(check_subject),
        measures={"line": line},
        attrs={"form": form},
        provenance=provenance,
    )
```

Run: PASS. **113 passed** no arquivo (86 antes desta task).

O `Fact` acima sobreviveu intacto — é o único trecho de código do step que sobreviveu. **O percurso de três passos não sobreviveu à medição**, e os quatro desvios abaixo dizem onde.

**D-5c-15 — a consequência pode não passar por variável nenhuma.** `if vendas.filter(vendas.valor < 0).count() > 0: raise ValueError(...)` tem o check dentro do próprio `test` do `if`, e `assert vendas.filter(...).count() == 0` idem: não existe `ast.Assign` a achar, e o percurso do plano produzia fact nenhum sobre a forma mais compacta de validar com consequência. Um extrator que só enxerga a forma com variável acusaria de `SF-DQ-002` justamente o código mais direto.

A leitura passou a ser reconhecida de **dois jeitos dentro do mesmo percurso**, e não por dois percursos: `_read_of` caminha o `test` uma vez e devolve `(inline, names)` — `inline` é o nó do check encontrado por **identidade** dentro do teste, `names` são os nomes que carregam o resultado. Inline dispensa toda guarda de nome, porque não há nome a religar.

**D-5c-16 — a ligação é por continência, não por igualdade, e `ast.Assign` não é a única.** `ha_ruins = vendas.filter(...).count() > 0` liga o nome a um `ast.Compare`, não ao `ast.Call`; `ast.AnnAssign` e `ast.NamedExpr` (o walrus, que é como o `if` inline liga quando o valor é reusado) ligam do mesmo jeito. `_bound_names` procura o nó do check **dentro** do valor (`any(child is check for child in ast.walk(value))`).

É essa continência que faz os **três frameworks caírem no mesmo caminho**, como a Task 3 fez com `_check`: `ruins = ....count()`, `r = VerificationSuite(...).run()` e `res = validation_definition.run(...)` diferem na forma da cadeia, e o que se procura não é a cadeia — é o nó do check. Nenhum ramo por framework foi escrito.

**D-5c-17 — religação, escopo e ordem valem aqui, e o step não os mencionava.** Os três são a mesma propriedade do módulo (*nome nu não identifica objeto*), aplicada ao par check/consequência:

- **Escopo**: a busca por consequência acontece dentro da lista de nós do escopo do check. Check em `def valida(...)` e `if ruins > 0: raise` no corpo do módulo são dois `ruins` diferentes, e emitir ali calaria `SF-DQ-002` sobre uma função que valida e não protege.
- **Religação**: `ruins = ....count()` / `ruins = 0` / `if ruins > 0: raise` testa o zero, não o check. `_rebound_between` — o mesmo predicado dos quatro atributos, sem cópia — derruba a evidência.
- **Ordem**: a leitura tem de vir **depois** da linha do check. `if ruins > 0: raise` antes da atribuição lê outra coisa.

Cada nome responde por si, e não o conjunto: `a = b = check` com `a` religado ainda vale se o teste lê `b`. É a mesma decisão de `_action_after_check`, onde N candidatas respondem uma a uma.

**D-5c-18 — `body` não é o único ramo, e a linha é identidade do fact.** Duas correções no reconhecimento do aborto e uma no fact:

1. **`orelse` conta.** `if ruins == 0: log(...) else: raise ...` é consequência, e o `if` que o plano descreve olharia só o `body`.
2. **`assert` dentro do ramo conta**, e `exit` nu também (`from sys import exit`). Reconhecer o nome nu arrisca casar uma função homônima do usuário; não reconhecer arrisca acusar quem abortou de verdade — e neste kind a acusação falsa é o pior lado, então o nome nu entra.
3. **`measures.line` é a única coisa que distingue dois enforcements do mesmo check.** `Fact.id` é sha de `kind + subject + measures`, e o subject é o do check por construção: dois consumidores do mesmo resultado (`if ruins > 0: raise` mais `assert ruins == 0`) colidiriam em um fact só se a linha não entrasse. O par `(forma, linha)` é deduplicado e ordenado antes de emitir, porque a ordem de travessia de `_scopes` não é ordem de fonte.

**A assimetria deste kind, escrita no cabeçalho do módulo.** `SF-DQ-002` dispara sobre a **ausência** de `dq.enforcement`, então a direção do erro se inverte em relação aos quatro atributos da Task 2: emitir um enforcement que não existe **cala** a regra (subnotificação), e deixar de emitir um que existe faz a regra **acusar** código correto. As bordas acima estão decididas com essa assimetria na mão — na dúvida entre reconhecer e não reconhecer uma forma de consequência, este kind reconhece. O que ele não faz é inventar consequência onde não há: proteção pela metade (`if ruins > 0: logger.warning(...)`) não emite, e `raise` que não lê o resultado do check também não.

**Limite conhecido, registrado e não corrigido:** consequência atrás de helper (`aborta_se(ruins)`) não é vista, e `SF-DQ-002` acusa um código que protege. Provar isso exige seguir o valor para dentro da função, o que esta fase não faz. O recorte vai declarado no achado — "sem consequência **neste corpus**" —, como a §8 do spec já previa e a 5b passou a fazer em `unreferenced_function_count`.

**Quatro achados da revisão da Task 4, todos fechados.**

**D-5c-19 — `col` fixo em zero colidia `Fact.id`, e o defeito é do repositório e não deste kind.** `Fact.id` é `sha1(canonical({kind, subject, measures}))[:6]` com `attrs` **fora** (`findings/models.py:41-54`), e `_subject` fixava `col: 0`. Medido:

```python
a = vendas.filter(vendas.valor < 0).count(); b = clientes.filter(clientes.cpf.isNull()).count()
```

Os dois `dq.check` saíam com o mesmo `id`, e os dois enforcements também — o `fact_id` que um `Finding` cita deixava de identificar evidência. Herdado da Task 1, barato agora porque `fixtures/dq/` só nasce na Task 6.

**O que os outros extratores fazem com `col`, medido antes de decidir:** `pyspark_ast.py:138` usa `getattr(node, "col_offset", 0)` — coluna de verdade — e `:436` usa `exc.offset or 0` no `SyntaxError`. Os outros onze (`terraform`, `event_log`, `sql_literal`, `s3_listing`, `catalog_schema`, `athena_workgroup`, `emr_cluster`, `call_graph`, `iceberg_metadata`, `consumers`, `spark_plan`, `fusion`) fixam zero. **Não é decisão de arquitetura**: eles ancoram em artefatos sem coluna útil — JSON de event log, HCL, resposta de API, plano físico —, enquanto `pyspark_ast` ancora no mesmo `.py` que este módulo e é o único com `ast.AST` na mão. `data_quality` segue a forma do irmão, que é o precedente correto.

`_check` passou a receber o **nó** em vez de `line`: linha e coluna saem do mesmo lugar, e nenhum chamador consegue passar uma sem a outra. `_unresolved` ganhou `col` pelo mesmo motivo — dois alvos não resolvidos na mesma linha também colidiam.

**Efeito colateral verificado, não presumido:** `engine._subject_group_key` monta a chave com `file:line` quando não há `symbol`, e **ignora `col`**. O agrupamento de `same_subject` sobrevive, e há teste que chama `_subject_group_key` direto para provar que enforcement e check continuam no mesmo grupo.

**D-5c-20 — `_rebound_between` muda de lado conforme o kind, e isso não estava escrito.** O único ponto onde a política do cabeçalho é contrariada de propósito:

```python
try:
    ruins = vendas.filter(vendas.valor < 0).count()
except Exception:
    ruins = 0
if ruins > 0:
    raise ValueError('x')
```

→ **zero enforcement** (medido), e `SF-DQ-002` acusa código que protege. Nos quatro atributos da Task 2 o mesmo predicado erra para o **silêncio** — omite chave ou emite `false`, e a regra deixa de opinar. Aqui ele erra para a **acusação**, porque descartar a leitura descarta o fact inteiro e a ausência do fact *é* o gatilho.

A decisão é mantida — sem seguir fluxo, o valor testado pode mesmo não ser o do check —, mas passou a estar escrita nos dois lugares: no cabeçalho do módulo, com o caso medido, e em `_reads_this_check`. Quem mexer no predicado precisa saber que ele paga em moedas opostas nos dois lados.

**D-5c-21 — quatro formas de leitura faltavam, e todas eram subreconhecimento.** Subreconhecer é o lado da acusação falsa neste kind. As **quatro** foram implementadas, e nenhuma pediu estrutura nova — as cinco formas passam por **uma porta só**, `_reader`, que devolve `(o que lê, onde o aborto pode estar)`:

| Forma | Como entrou |
|---|---|
| alvo de tupla (`ruins, total = ...count(), 10`) | `_bound_names` caminha o alvo atrás de `Name` em `Store` em vez de filtrar `isinstance(t, ast.Name)` |
| `while` | forma idêntica ao `if` — uma cláusula do `_reader` |
| `match` | lê pelo `subject` **e por cada `guard`**; aborta em qualquer `case`. `requires-python = ">=3.10"` confirmado no `pyproject.toml`, então `ast.Match` sempre existe |
| curto-circuito e `IfExp` (`ruins > 0 and sys.exit(1)`) | `ast.Expr`, onde leitura e aborto vivem na **mesma** expressão: o statement é ao mesmo tempo o que lê e o ramo |

O `ast.Expr` não afrouxa a exigência de aborto — `print(ruins)` também é `ast.Expr`, e `_abort_in` não acha nada nele. Há teste que fixa isso (`ruins > 0 and logger.warning(1)` → nenhum enforcement).

**A que virou limite escrito:** a mesma expressão em posição de **valor** (`x = sys.exit(1) if ruins > 0 else 0`) não é lida. Cobri-la exigiria tratar todo statement como leitor em potencial, e abortar dentro do valor de uma atribuição não é forma que se escreva. Erra para o silêncio.

**D-5c-22 — quatro limites de `_abort_in`, medidos um a um e escritos no ponto.** Todos do mesmo lado — o fact afirma consequência onde ela pode não acontecer, e o erro cai no silêncio de `SF-DQ-002`:

1. `try: raise ... except: pass` em volta do aborto **ainda conta** (medido: enforcement na linha 4). Provar que a exceção escapa exige seguir handlers, e um `except` que engole o aborto da própria validação não se escreve por engano.
2. `sys.exit(0)` **conta** como aborto. O fact afirma que o resultado leva a saída do processo, não que a saída sinaliza falha; distinguir pelo argumento seria julgar o valor, e julgar não é trabalho de extrator.
3. `raise`/`assert` **não relacionado** dentro do ramo conta (`if ruins > 0: assert conf is not None` seguido de `logger.warning(...)` → enforcement `assert`). Amarrar um ao outro exigiria análise de dependência dentro do ramo.
4. `raise` dentro de `def` aninhado no ramo conta, e não deveria — ele não roda ali. Raro o bastante para não pagar travessia com escopo próprio.

Os quatro foram **rodados**, não presumidos, e o comportamento medido é o que o docstring afirma.

- [x] **Step 3: `assert` conta como enforcement, com ressalva (desvio D-5c-4)**

A Task 0 fechou o ramo: a referência da linguagem confirma que `-O` apaga o `assert`, mas **nenhuma** fonte da AWS mostra Glue ou EMR rodando o driver assim, e no Glue o caminho documentado (`--customer-driver-env-vars`) rejeita chaves sem o prefixo `CUSTOMER_`. Então `form: "assert"` **é** enforcement — não emita `dq.unresolved` por causa disso.

A ressalva vai escrita na `explanation` de `SF-DQ-002`, na Task 7, com a URL da referência da linguagem. Deixe um comentário no código apontando para `knowledge/dq/validation-frameworks.md` §3.4, para ninguém "corrigir" isso depois sem ler a fonte.

Feito: o comentário mora em `_EXIT_CALLS`, com o argumento inteiro (por que `-O` não vale como padrão, por que `--customer-driver-env-vars` fecha a porta, e o que aconteceria com `SF-DQ-002` se `assert` não contasse), mais os vetos V-AS-1 e V-AS-2 nomeados. O teste `test_assert_sobre_o_resultado_conta_como_enforcement` prova as duas metades: o enforcement sai, e `dq.unresolved` **não** sai.

- [x] **Step 4: Commit**

Medido antes do commit: **113 passed** em `tests/test_facts_data_quality.py`, **2965 passed / 5 skipped** na suíte inteira (2938 antes desta task), `ruff check .` limpo e `git diff --stat main -- fixtures/pyspark/` vazio.

Depois da revisão (D-5c-19 a D-5c-22): **124 passed** no arquivo e **2976 passed / 5 skipped** na suíte, com `ruff check .` limpo e `fixtures/pyspark/` intocado.

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py
git commit -m "feat(facts): dq.enforcement so quando a consequencia esta provada"
```

---

## Task 5: Registro de superfície

Oito pontos. Esquecer um é o modo de falha desta fase, e dois deles são listas manuais duplicadas.

**Files:**
- Modify: `tests/test_rules_catalog_reachability.py:26-63`, `tests/test_fixtures_kind_coverage.py:24-59`, `sparkforge/adapters/_core.py`, `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`

- [x] **Step 1: As duas listas `EXTRACTORS`**

Acrescente `data_quality` ao import e à coleção nos **dois** arquivos — tupla em `test_rules_catalog_reachability.py`, dict (`"data_quality": data_quality`) em `test_fixtures_kind_coverage.py`.

Run: `python -m pytest tests/test_fixtures_kind_coverage.py -v`
Expected: FAIL em `test_every_kind_of_every_extractor_appears_in_some_golden[data_quality]` — os quatro kinds ainda não têm golden. **É o resultado correto nesta etapa**; a Task 6 o fecha.

- [x] **Step 2: `_core.analyze_data_quality`**

Copie a forma de `analyze_emr_cluster` (`sparkforge/adapters/_core.py:829`):

```python
def _extract_data_quality_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio do codigo PySpark ou para um arquivo .py:\n"
            f"    sparkforge analyze data-quality --path src/ --out .sparkforge/facts_dq.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_data_quality_tree(target, repo_root=target)
    return extract_data_quality_path(target, repo_root=target.parent)


def analyze_data_quality(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_data_quality_facts(path)
    return _facts_page(facts, "dq.unresolved", kind, limit, cursor)
```

- [x] **Step 3: CLI**

Subparser `data-quality` sob `analyze`, com `--path` (required), `--out`, `--kind` (append), `--limit`, `--cursor`; handler `_cmd_analyze_data_quality` na forma de `_cmd_analyze_emr_cluster` (`cli.py:740`); entrada `("analyze", "data-quality"): _cmd_analyze_data_quality` no dict de dispatch (`cli.py:1021`).

- [x] **Step 4: MCP**

`sparkforge_analyze_data_quality` em `TOOLS`, com `inputSchema` de `path`/`kind`/`limit`/`cursor` e `outputSchema` `_may_fail(_ANALYZE_FACTS_SCHEMA, ...)`; handler `_h_analyze_data_quality`; entrada no dict de handlers. A `description` precisa dizer o que o fact carrega **e o que ele recusa afirmar** — que não julga o dado, só onde a validação está.

- [x] **Step 5: `parity.yaml` e `manifest.json`**

```yaml
  - name: extract facts about data validation in PySpark code
    tools: [sparkforge_analyze_data_quality]
    cli: [analyze data-quality]
    knowledge: [knowledge/dq/validation-frameworks.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]
```

E `"sparkforge_analyze_data_quality"` na lista de tools do `manifest.json`.

- [x] **Step 6: `regen_dq` em `scripts/regen_fixtures.py`**

```python
def regen_dq(directory: Path) -> None:
    """Como `regen_pyspark`, mas so os facts `dq.*`: `*.py` sob input/,
    extraidos com `extract_data_quality_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = extract_data_quality_tree(input_dir, repo_root=input_dir)
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)
```

Mais o import, a constante `FIXTURES_DQ = ROOT / "fixtures" / "dq"` e o par `(FIXTURES_DQ, regen_dq)` na lista de matches.

- [x] **Step 7: Rode o que já pode passar**

Run: `python -m pytest tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_capability_parity.py -q`
Expected: PASS

Medido: **207 passed** com `tests/test_docs_coverage.py` junto (é ele que compara `manifest.json` com `TOOLS`). Suíte inteira: **2981 passed / 3 failed / 5 skipped** — os três vermelhos estão em D-5c-23 e D-5c-24, e nenhum deles é desta task para fechar.

**Quatro desvios medidos nesta task.**

**D-5c-23 — o registro deixa DOIS vermelhos, e o plano previu um.** "A Task 6 fecha o vermelho que ela deixa" (§Ordem e dependências) conta só o de fixture. Medido, são dois vermelhos de fixture e um de orientação:

| Teste | Causa | Quem fecha |
|---|---|---|
| `test_fixtures_kind_coverage.py::test_every_kind_of_every_extractor_appears_in_some_golden[data_quality]` | os quatro `dq.*` sem golden | Task 6 |
| `test_fixtures_kind_coverage.py::test_every_unresolved_kind_is_exercised` | `dq.unresolved` sem golden — mesma causa, recorte explícito sobre a máquina de ponto cego | Task 6 |
| `test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan` | `sparkforge_analyze_data_quality` não é citada em coordenador nenhum | **Task 9** |

O terceiro não é da mesma família dos outros dois: ele é o invariante de que capacidade sem orientação não é capacidade — exatamente a medição de abertura da Fase 4. Registrar a tool ANTES de existir quem a despache é o que o acende, e a única forma de não o acender seria não registrar a tool. Fica vermelho da Task 5 até a Task 9, e a Task 9 não pode ser adiada para depois da 10 por causa dele.

**D-5c-24 — os pontos de registro são onze, não oito.** Os oito do plano estão corretos e nenhum sobrava; o que falta na conta são três listas manuais em `tests/test_adapters_tools.py`, todas com a mesma natureza das duas `EXTRACTORS` — adição manual que nenhum invariante deriva:

1. `TestToolSurface::test_the_full_tool_surface_is_declared` (o `set(TOOLS) == {...}` literal);
2. `_real_output_for` — sem o branch, `AssertionError: sem construtor de argumentos reais`, e a tool nova não teria a saída real validada contra o próprio schema;
3. `TestErrorShapesValidateToo.FAILABLE` — este é o único opcional (nenhum teste exige que toda tool `analyze` esteja lá), e entrou porque o EMR está.

Somando, o registro de uma superfície nova custa **onze** edições manuais, das quais cinco são listas literais que ninguém deriva.

**D-5c-25 — o laço de corpus completo de `regen_fixtures.py` NÃO entrou, e é dívida assumida da Task 6.** O `main()` sem argumento itera `FIXTURES_X.iterdir()` para cada corpus; `fixtures/dq/` só nasce na Task 6, e o laço adicionado hoje quebraria `python scripts/regen_fixtures.py` com `FileNotFoundError`. As alternativas — guarda `is_dir()` só nesse laço, ou criar o diretório vazio — custam mais do que resolvem: a guarda vira mentira assim que o corpus existir, e o diretório vazio acenderia `test_every_fixture_domain_has_a_golden_module`. O esquecimento é autodetectável: sem o laço, a Task 6 Step 3 (`python scripts/regen_fixtures.py`) não gera `fixtures/dq/*/expected/`, e o golden novo falha na hora. **Task 6: acrescente `for directory in sorted(p for p in FIXTURES_DQ.iterdir() if p.is_dir()): regen_dq(directory)` junto com as fixtures.**

**D-5c-26 — nenhum teste de paridade exige simetria `analyze`/`collect`, verificado antes de assumir.** `TestNoCliVerbIsAnUndeclaredMcpGap` cobra o caminho verbo → tool MCP, e `test_every_phase_zero_tool_appears_in_some_capability` cobra tool → capacidade. Nenhum dos dois olha para `collect`. O artefato de `SF-DQ` é o `.py` do repositório, não uma resposta de API, então não há coletor a construir e a área fica sem verbo `collect` sem acender nada — ao contrário de `SF-EMR`, onde o par existe porque o dump vem da AWS.

- [x] **Step 8: Commit**

```bash
git add tests/ sparkforge/adapters/ parity.yaml manifest.json scripts/regen_fixtures.py
git commit -m "feat(adapters): analyze data-quality na CLI, no MCP e nos manifestos"
```

---

## Task 6: Fixtures e o golden do domínio

**Files:**
- Create: `fixtures/dq/*` (oito), `tests/test_fixtures_golden_dq.py`

- [x] **Step 1: Os oito diretórios**

Cada um com `input/*.py`, `meta.yaml` e `expected/` gerado. Os `meta.yaml` seguem a forma de `fixtures/pyspark/*/meta.yaml`:

```yaml
name: validation_after_write
proves: >
  A validacao roda depois do write: quando ela acusa, o dado ruim ja esta
  publicado. SF-DQ-001 dispara sobre dq.check com attrs.position_vs_write ==
  after_write.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [dq.check, dq.enforcement, dq.module_analyzed]
expects_rules: [SF-DQ-001]
```

Os oito, e o que cada um prova:

| Fixture | Prova |
|---|---|
| `validation_after_write` | positivo de `SF-DQ-001` |
| `suite_without_enforcement` | positivo de `SF-DQ-002` |
| `check_recomputes_lineage` | positivo de `SF-DQ-003` |
| `repeated_checks_same_target` | positivo de `SF-DQ-004` |
| `validated_correctly` | negativo das quatro: valida antes do write, com `raise`, sobre DF com `cache()`, e um único check |
| `pydeequ_suite` | `shares_scan: true` — **não** `single_pass`, e **sem** `declared_checks`, os dois nomes vetados pelos desvios D-5c-1 e D-5c-2 |
| `great_expectations_suite` | o mesmo kind saindo do outro framework, pela chave literal de `batch_parameters`, e **sem** a chave `shares_scan` (D-5c-3) |
| `unresolved_helper` | validação atrás de helper — `dq.unresolved`, sem alvo adivinhado |

`expects_kinds` de `validated_correctly` e de `unresolved_helper` juntos precisam cobrir os quatro kinds de `EMITTED_KINDS`, senão a Task 5 Step 1 continua vermelha.

- [x] **Step 2: `tests/test_fixtures_golden_dq.py`**

Copie a estrutura de `tests/test_fixtures_golden_callgraph.py`: `REQUIRED_FIXTURES` com os oito nomes, `run_fixture` chamando `extract_data_quality_tree` + `judge`, e a classe `TestGolden` com os quatro testes (`facts_match_golden`, `findings_match_golden`, `declared_kinds_all_present`, `declared_rules_all_fire`).

- [x] **Step 3: Gere os goldens e LEIA o diff**

Run: `python scripts/regen_fixtures.py`
Depois: `git diff --stat fixtures/dq/`

Nesta etapa `findings.json` sai vazio em todas — o catálogo `SF-DQ` só nasce na Task 7. **Isso é esperado**, e os goldens de findings são regenerados de novo lá.

- [x] **Step 4: Rode**

Run: `python -m pytest tests/test_fixtures_golden_dq.py tests/test_fixtures_kind_coverage.py -v`
Expected: PASS, incluindo `test_every_kind_of_every_extractor_appears_in_some_golden[data_quality]`, que a Task 5 deixou vermelho

**Medido nesta task.** Os oito corpora produzem **24 facts**: 8 `dq.check`, 7 `dq.enforcement`, 1 `dq.unresolved` e 8 `dq.module_analyzed` — os quatro kinds de `EMITTED_KINDS`, e os dois vermelhos de fixture da Task 5 fecharam. Suíte inteira: **3050 passed / 1 failed / 5 skipped**, e o único vermelho é `test_no_tool_is_orphan`, que é da Task 9 (D-5c-23). Nenhum golden de outro corpus mudou (`git status` depois de `regen_fixtures.py` sem argumento: só `fixtures/dq/` novo), e `git diff --stat main -- fixtures/pyspark/` continua vazio.

**Base para o gate da Task 8:** a taxa de alvo não resolvido deste corpus é **1 em 9** (`unresolved_count / (check_count + unresolved_count)`), ≈ 11%. O único não resolvido é o `spark.table(tabela)` de `unresolved_helper`, e ele é intencional.

**Quatro desvios medidos nesta task.**

**D-5c-27 — `unresolved_helper` prova alvo ilegível, e não "validação atrás de helper".** O plano (Step 1, tabela) escreveu "validação atrás de helper — `dq.unresolved`". Medido, a forma que o plano descreve não produz `dq.unresolved` nenhum: um check dentro de uma função auxiliar é um `dq.check` normal, com o escopo daquela função; o que a ausência do helper apaga é o `dq.enforcement`, e apagar um fact não emite outro. Quem produz `dq.unresolved` é o **alvo que não se lê** — `spark.table(tabela).filter(...).count()`, cuja raiz de cadeia é a sessão. A fixture ficou com a forma que de fato exercita o kind, e o helper continua no arquivo porque é o que torna o alvo ilegível (o nome da tabela chega por parâmetro).

**D-5c-28 — a âncora de uma cadeia multilinha é a PRIMEIRA linha da expressão, não a do terminal.** `_check` usa `node.lineno`, e para `(VerificationSuite(spark)
.onData(df)
...
.run())` o `lineno` do `ast.Call` mais externo é a linha do `VerificationSuite`, e não a do `.run()`. Em `pydeequ_suite` a suite ocupa as linhas 33–41 e o `dq.check` sai ancorado em `L33:8`. Consequência real, e não cosmética: um `write` colocado **entre** o início da cadeia e o `run()` seria lido como posterior ao check, e `position_vs_write` sairia `before_write` sobre um código que valida depois de publicar. Nenhuma fixture depende disso hoje (as duas suites escrevem depois da cadeia inteira); quem escrever o corpus de `SF-DQ-001` com suite multilinha precisa saber.

**D-5c-29 — o `meta.yaml` de exemplo do plano não é aplicável nesta task.** Ele traz `expects_rules: [SF-DQ-001]`, e o catálogo `SF-DQ` só nasce na Task 7: `test_declared_rules_all_fire` reprovaria os oito. Todos os oito nasceram com `expects_rules: []`, e sete deles serão preenchidos nas Tasks 7 e 8 — `validated_correctly` fica vazio para sempre, e é essa permanência que faz dele a metade negativa das quatro regras.

**D-5c-30 — todo o corpus valida DENTRO de `main()`, e isso é exigência do extrator, não estilo.** `_ScopeIndex` é por escopo: leitura, transformação, check e write precisam do mesmo escopo para que `position_vs_write`, `target_persisted` e `action_after_check` tenham o que comparar. Escrever a validação numa função e o write no corpo do módulo faria `position_vs_write` sair `no_write_in_module` — subnotificação silenciosa, e a fixture deixaria de provar o que o nome dela diz sem que nenhum teste reclamasse. Registrado porque o corpus é o material da Task 8: um job que valide num escopo e escreva noutro é forma REAL, e o dia em que ela entrar aqui vai parecer um bug do extrator sem esta nota. `TestAdversarial` em `tests/test_fixtures_golden_dq.py` trava o atributo decisivo de cada fixture justamente para que essa regressão apareça como falha, e não como golden verde.

- [x] **Step 5: Commit**

```bash
git add fixtures/dq tests/test_fixtures_golden_dq.py
git commit -m "test(dq): oito fixtures, e os quatro kinds provados por golden"
```

---

## Task 7: `SF-DQ-001` e `SF-DQ-002`

**Files:**
- Create: `rules/catalog/data-quality.yaml`
- Modify: `fixtures/dq/*/expected/findings.json` (regenerados), `fixtures/dq/*/meta.yaml`

- [x] **Step 1: Cabeçalho do catálogo, com os vetos da Task 0**

O cabeçalho registra três coisas, na forma que `rules/catalog/emr-infra.yaml` e `callgraph.yaml` usam: por que `runtime_scope` é vazio nas quatro (gatilho é AST, critério da Fase 5a); por que a correlação vive no extrator (§4.4 do spec, `engine._condition_candidates`); e **os vetos que a Task 0 produziu**, um parágrafo por premissa morta, para ninguém reinventá-las.

- [x] **Step 2: `SF-DQ-001`**

```yaml
catalog_version: 1
schema_version: 1
area: SF-DQ
retrieved: 2026-08-03

rules:

  - id: SF-DQ-001
    category: data-quality
    title: Validação roda depois da escrita
    requires_facts: [dq.check]
    when:
      all:
        - fact: dq.check
          where: {attrs.position_vs_write: after_write}
    status: structural
    severity_default: P1
    # Escopo vazio: o gatilho e a POSICAO de uma chamada no AST. Nao varia com
    # versao de Glue, Spark, EMR ou Iceberg. Criterio da Fase 5a.
    runtime_scope: {}
    explanation: >
      A validação existe para impedir que dado ruim chegue ao consumidor, e aqui ela roda
      depois de o dado já ter sido escrito. Quando ela acusa, o estrago já é público: o
      consumidor a jusante pode ter lido, e reverter exige apagar ou reescrever partição.
      `attrs.position_vs_write` distingue três situações, e só uma delas é esta —
      `no_write_in_module` significa que o módulo valida e não escreve, que é legítimo e
      não dispara.
    proposed_change:
      - Mover a validação para antes do `write`, sobre o DataFrame já transformado.
      - Se a validação precisa do dado escrito (contagem no destino, por exemplo), escrever primeiro numa área de staging e só promover ao destino final depois de a validação passar.
    risks:
      - Validar antes do write adiciona uma action antes da escrita; sobre DataFrame não persistido isso recomputa o lineage. Ver SF-DQ-003.
    tradeoffs:
      - Staging mais promoção dobra a escrita e o custo de S3, e é o preço de não publicar dado inválido.
    validation:
      - Rodar com um lote que viole a regra e confirmar que nada é escrito no destino final.
      - Contagem no destino antes e depois da mudança, para provar que a semântica do write não mudou.
    rollback: [Reverter o commit.]
    sources:
      - {origin: field-heuristic, note: "A severidade P1 é decisão de campo: o custo depende de haver consumidor a jusante, e nenhum fact disponível mede isso."}
```

- [x] **Step 3: `SF-DQ-002`, com `same_subject`**

```yaml
  - id: SF-DQ-002
    category: data-quality
    title: Validação sem consequência
    requires_facts: [dq.check]
    when:
      same_subject: true
      all:
        - fact: dq.check
        - absent: dq.enforcement
    status: structural
    severity_default: P1
    runtime_scope: {}
    explanation: >
      O check roda, gasta uma passada sobre o dado, e o resultado não leva a lugar nenhum:
      não há `raise`, não há saída com código de erro. O job termina verde com dado
      inválido, que é pior do que não validar — a suíte cria a crença de que há uma
      garantia. `dq.enforcement` só é emitido quando a consequência está presente e é
      coerente; proteção pela metade não emite, e o que não pôde ser lido virou
      `dq.unresolved`, que não conta como ausência de proteção.
      O recorte é o corpus analisado: se a consequência está noutro módulo fora do
      recorte, o achado é um convite a verificar, não uma sentença.
      Ressalva sobre `assert` (desvio D-5c-4): `assert` conta como consequência aqui,
      porque nenhuma fonte da AWS mostra Glue ou EMR rodando o driver com `-O`, e no Glue
      o caminho documentado para variáveis de ambiente do driver rejeita `PYTHONOPTIMIZE`.
      Mas a linguagem é explícita — sob `-O` o interpretador não gera código nenhum para
      `assert` — então validação cuja única consequência é um `assert` fica a uma variável
      de ambiente de virar validação sem consequência nenhuma.
    proposed_change:
      - Ler o resultado do check e abortar o job quando ele reprovar.
      - Se o job deve seguir com dado parcial de propósito, registrar a decisão em métrica ou log estruturado e declarar o contrato — validação que só observa precisa dizer que só observa.
    risks:
      - Passar a abortar o job muda o comportamento de produção: pipeline que hoje termina verde passará a falhar quando o dado violar a regra. É o efeito pretendido, e precisa ser combinado com quem opera.
    tradeoffs:
      - Abortar cedo protege o consumidor e interrompe a carga; seguir e sinalizar preserva a carga e transfere o risco a jusante.
    validation:
      - Rodar com um lote que viole a regra e confirmar que o job falha com código de saída diferente de zero.
      - Rodar com um lote válido e confirmar que nada mudou.
    rollback: [Reverter o commit.]
    sources:
      - {origin: field-heuristic, note: "P1 e não P0: o defeito é a garantia inexistente, não um dado comprovadamente inválido — o motor não sabe se o check reprovaria."}
```

- [x] **Step 4: Regenere e leia o diff**

Run: `python scripts/regen_fixtures.py && git diff fixtures/dq/*/expected/findings.json`

Confirme, lendo: `validation_after_write` ganhou `SF-DQ-001`; `suite_without_enforcement` ganhou `SF-DQ-002`; **`validated_correctly` continua com `findings.json` vazio**. Acrescente os `expects_rules` correspondentes nos `meta.yaml`.

- [x] **Step 5: Rode**

Run: `python -m pytest tests/test_fixtures_golden_dq.py tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q`
Expected: PASS

**Medido nesta task.** `regen_fixtures.py` sobre o corpus inteiro mudou **dois** arquivos, e só eles: `fixtures/dq/validation_after_write/expected/findings.json` (0 -> 1 achado, `SF-DQ-001`, ancorado em `job.py:38:16`) e `fixtures/dq/suite_without_enforcement/expected/findings.json` (0 -> 1 achado, `SF-DQ-002`, ancorado em `job.py:32:8`). As outras seis fixtures de `dq` continuam com `findings.json` vazio, `validated_correctly` inclusive — a metade negativa das quatro regras segue negativa. `git diff --stat main -- fixtures/pyspark/` vazio. Suíte inteira: **3063 passed / 2 failed / 5 skipped**; `ruff check .` limpo. Os dois vermelhos são de coordenador e fecham na Task 9: `test_no_tool_is_orphan` (herdado da Task 5) e `test_no_area_is_orphan`, que é exatamente o vermelho que o Step 1 da Task 9 manda provocar e colar como justificativa — a área `SF-DQ` existe no catálogo e ainda não tem coordenador que a declare em `rule_areas`.

**Três desvios medidos nesta task.**

**D-5c-31 — `SF-DQ-001` ganhou `same_subject: true`, que o plano não previa.** O YAML do plano trazia só `all: [{fact: dq.check, where: ...}]`. Medido em `engine._evaluate_when`: regra **sem** `same_subject` produz no máximo UM grupo de evidência, logo um Finding, com `evidence` juntando todos os checks que casaram e `subject` do primeiro. Num recorte com três validações tardias isso vira um achado ancorado numa delas — o operador corrige aquela, roda de novo e descobre a próxima, sem nunca saber quantas faltam. O `README.md` deste diretório trata subcontagem como enganosa do mesmo jeito que um falso negativo ("Um Finding por subject"), e as regras escritas depois dessa decisão (`SF-CG-001`, `SF-PLAN-001/002/004`) usam `same_subject` com uma condição só, exatamente por isso. Aqui a entidade é o check, e a chave de grupo é `<arquivo>:<linha>` (`_subject_group_key` ignora `col`). Sem efeito no golden — `validation_after_write` tem um check só —, e é justamente por isso que a decisão precisa estar escrita: nenhuma fixture a defenderia se ela fosse revertida.

**D-5c-32 — dois campos do YAML do plano não sobreviviam ao carregador, e o golden mostrou.** `rollback: [Reverter o commit. Quando houve staging, apagar o prefixo...]` em fluxo inline: a vírgula da frase é separador de item em YAML, e o `rollback` chegou ao `Finding` picado em dois passos, o segundo começando em minúscula. E, em `risks` de `SF-DQ-002`, `- Passar a abortar o job muda o comportamento de produção: pipeline que hoje...` virou **mapa** — `texto: texto` num item de lista é um par chave-valor —, e o `Finding` saiu com um dicionário dentro de `risks`, que nenhum schema reprova (`validate_finding` aceita a lista). Os dois passaram por `load_catalog(validate_exprs=True)` e pelos 607 testes das suítes de catálogo: quem pegou foi **ler o diff do golden**, que é a etapa que o Step 4 existe para forçar. Corrigidos com aspas e lista em bloco, com o motivo escrito ao lado de cada um. Vale para toda regra futura: prosa com `: ` ou com vírgula em item de lista precisa de aspas.

**D-5c-33 — `manifest.json` e `README.md` carregam a contagem de regras, e ela é testada.** `tests/test_docs_coverage.py::test_rule_count_equals_the_real_catalog` compara `manifest.json.knowledge_base.rule_count` com `len(load_catalog())`: duas regras novas quebram o teste até o manifesto acompanhar. 58 -> 60 no manifesto e nas duas menções do `README.md` (o próprio teste registra que esse número já apodreceu três vezes). Junto, `rules/catalog/README.md` ganhou as quatro áreas que faltavam na tabela "Arquivos" (`spark-plan`, `callgraph`, `emr-infra` e a nova `data-quality`) e as quatro siglas que faltavam na linha do campo `id` — a tabela tinha parado na Fase 1. `knowledge/sources.lock.json` NÃO muda: as duas regras citam `origin: field-heuristic` com `note` apontando para `knowledge/dq/validation-frameworks.md`, e o lock só vigia `sources` com `url`.

- [x] **Step 6: Commit**

```bash
git add rules/catalog/data-quality.yaml fixtures/dq
git commit -m "feat(rules): SF-DQ-001 e SF-DQ-002, posicao e consequencia"
```

Commitado em `6f370eb`, com quatro arquivos a mais do que o plano listava: `rules/catalog/README.md`, `manifest.json`, `README.md` e este plano (D-5c-33).

---

## Task 8: `SF-DQ-003` e `SF-DQ-004`, com o gate medido

**Files:**
- Modify: `rules/catalog/data-quality.yaml`, `fixtures/dq/*`

- [x] **Step 1: `SF-DQ-003`**

```yaml
  - id: SF-DQ-003
    category: data-quality
    title: Validação recomputa o lineage
    requires_facts: [dq.check]
    when:
      all:
        - fact: dq.check
          where: {attrs.target_persisted: false, attrs.action_after_check: true}
    status: structural
    severity_default: P2
    runtime_scope: {}
    explanation: >
      Spark é lazy: a action do check materializa o DataFrame, e a próxima action sobre o
      mesmo DataFrame recomeça do último ponto materializado. Sem `cache`/`persist`, o
      lineage inteiro — leitura, joins, transformações — roda duas vezes, uma para validar
      e outra para escrever. O custo é proporcional ao lineage, não ao tamanho do check.
    proposed_change:
      - Persistir o DataFrame antes do check, com o nível de storage adequado ao tamanho, e liberar com `unpersist` depois da última action.
      - Alternativa sem cache: calcular a métrica de validação junto do resultado, numa única agregação, em vez de numa passada separada.
    risks:
      - Cache de DataFrame grande pressiona memória de executor e pode causar spill ou OOM — o remédio de um gargalo vira outro.
    tradeoffs:
      - Persistir troca CPU e I/O de recomputo por memória; qual é melhor depende de qual recurso está saturado.
    validation:
      - Número de jobs Spark submetidos antes e depois, na Spark UI.
      - Tempo de execução com o volume de produção.
      - Contagem e schema do resultado, inalterados.
    rollback: [Remover o `cache`/`persist` e reverter o commit.]
    sources:
      - {url: "https://docs.aws.amazon.com/prescriptive-guidance/latest/tuning-aws-glue-for-apache-spark/optimize-shuffles.html", retrieved: 2026-08-03, note: "Secao 'Remove unneeded Spark actions': cada RDD transformado pode ser recomputado a cada action."}
```

- [x] **Step 2: Meça o gate de `SF-DQ-004` antes de escrevê-la**

A §4.2 do spec condiciona esta regra a um número. Rode:

```bash
python -c "
from pathlib import Path
from sparkforge.facts.data_quality import extract_data_quality_tree
facts = extract_data_quality_tree(Path('fixtures'), repo_root=Path('fixtures'))
checks = [f for f in facts if f.kind == 'dq.check']
unresolved = [f for f in facts if f.kind == 'dq.unresolved' and f.attrs.get('reason') == 'unresolved_target']
print('checks', len(checks), 'alvo nao resolvido', len(unresolved))
"
```

Cole a saída no commit. **Se `unresolved` for maior que `checks`**, `SF-DQ-004` não entra: escreva no cabeçalho do catálogo o veto com o número medido, no lugar da regra, e pule para o Step 4. Regra cujo gatilho depende de um alvo que o AST erra mais da metade das vezes dispara por acidente.

- [x] **Step 3: `SF-DQ-004`, se o gate passou**

```yaml
  - id: SF-DQ-004
    category: data-quality
    title: Vários checks, várias passadas sobre o mesmo dado
    requires_facts: [dq.check]
    when:
      all:
        - fact: dq.check
          where: {attrs.shares_scan: false}
          expr: "measures.checks_on_target >= 2"
    status: structural
    severity_default: P2
    runtime_scope: {}
    explanation: >
      Cada check artesanal é uma action, e cada action é uma varredura do dado. Dois ou
      mais checks independentes sobre o mesmo DataFrame varrem o mesmo dado duas ou mais
      vezes para responder perguntas que uma única agregação responderia junto.
      `attrs.shares_scan` separa quem já compartilha varredura: o runner do Deequ agrupa as
      agregações que exigem o mesmo agrupamento e as roda numa passada só — o que **não**
      quer dizer uma passada para a suíte inteira, porque `isUnique`, `hasUniqueness` e
      entropia exigem re-particionamento e pagam passada própria. O contraste que esta
      regra afirma é N contra ≤ N, nunca N contra um.
      Check de Great Expectations não traz a chave `shares_scan` e portanto não é avaliado
      aqui: quantas expectativas a suíte tem vive no store do contexto, fora do arquivo.
    proposed_change:
      - Reunir os checks numa única agregação, com uma expressão por regra (`sum(when(cond, 1).otherwise(0))` por violação), e ler todas as contagens de uma linha só. Esta é a mudança que não depende de biblioteca nenhuma.
      - Alternativa, com guarda de versão obrigatória - uma suíte que compartilha varredura. PyDeequ não instala em Glue 3.0 nem em nenhuma release EMR 6.x, e o Spark 3.4 está fora do mapa de `pydeequ/configs.py`; Great Expectations 1.x exige Python 3.10 ou maior. Conferir o alcance medido em `knowledge/dq/validation-frameworks.md` §2.2 e §1.4 antes de recomendar a alguém.
    risks:
      - Agregação única muda a mensagem de erro: em vez de falhar no primeiro check, o job passa a reportar todas as violações juntas. É melhor para diagnóstico e diferente do que a equipe está acostumada a ler.
    tradeoffs:
      - Uma agregação com muitas expressões é mais difícil de ler que N checks separados.
    validation:
      - Número de jobs Spark submetidos antes e depois, na Spark UI.
      - Cada contagem de violação, idêntica à da versão anterior, sobre o mesmo lote.
    rollback: [Reverter o commit.]
    sources:
      - {url: "https://www.vldb.org/pvldb/vol11/p1781-schelter.pdf", retrieved: 2026-08-03, note: "Schelter et al., PVLDB 2018, §4.1 e §5.1: scan sharing por agrupamento, e metricas que exigem re-particionamento pagam passada propria."}
      - {origin: field-heuristic, note: "P2: o custo é real e proporcional ao número de checks, mas nenhum dado disponível mede o tamanho do lineage varrido."}
```

- [x] **Step 4: Regenere, leia o diff, rode**

Run: `python scripts/regen_fixtures.py && python -m pytest tests/test_fixtures_golden_dq.py -q`
Expected: PASS, com `check_recomputes_lineage` e `repeated_checks_same_target` disparando as regras novas e `validated_correctly` ainda vazio

- [x] **Step 5: Commit**

```bash
git add rules/catalog/data-quality.yaml fixtures/dq
git commit -m "feat(rules): SF-DQ-003 e SF-DQ-004, o custo da validacao"
```

**Feito em `c153b9e`.** Os cinco steps fechados, com quatro desvios do plano:

1. **`same_subject: true` nas duas regras**, que o YAML deste plano não tinha.
   D-5c-31 já fixou o motivo na Task 7: sem ele o motor produz UM grupo de
   evidência e N ocorrências viram um achado ancorado na primeira.
   `repeated_checks_same_target` prova o efeito — os dois `count()` saem como
   DOIS achados de `SF-DQ-004`, e não um.
2. **`SF-DQ-003` dispara em quatro fixtures, e não em uma.**
   `great_expectations_suite` e `suite_without_enforcement` também validam um
   DataFrame não persistido e o reusam no write depois; o recomputo de lineage
   não depende de framework. Os dois `meta.yaml` ganharam a prosa que explica
   por quê, e `pydeequ_suite` continua calada por ter o alvo em `cache()` — o
   contraste que prova que o gatilho não é "é uma suíte".
3. **`knowledge/sources.lock.json`**, que este plano não previa: as duas URLs
   novas de `SF-DQ-004` quebraram
   `test_refresh_knowledge.py::test_the_committed_lock_matches_the_catalog`.
   Entraram só as duas, com hash medido; `refresh_knowledge.py --update`
   recarimbaria as 35 existentes e enterraria a mudança real.
4. **`README.md` junto do `manifest.json`** no 60 → 62: o número aparece duas
   vezes no README e nenhum teste olha para lá.

Gate do Step 2, medido: `checks 8 alvo nao resolvido 1` — 1 em 9 (~11%), o
mesmo da Task 6. O número ficou como comentário acima de `SF-DQ-004` no
catálogo, e não só na mensagem de commit.

---

## Task 9: Coordenador, skill e espelhos

**Files:**
- Create: `agents/data-quality-reviewer.md`, `skills/review-data-validation/SKILL.md`

- [x] **Step 1: Rode o teste que prova a órfã**

Run: `python -m pytest tests/test_agent_coverage.py -v`
Expected: FAIL em `test_no_area_is_orphan` — `SF-DQ` não tem coordenador. Cole a saída: é a justificativa da task.

**Medido.** Foram **dois** vermelhos, e não um — o plano previu só o de área. `19 passed, 2 failed`:

```
E   AssertionError: 1 de 33 tools nao sao alcancaveis a partir de nenhum coordenador:
E   ['sparkforge_analyze_data_quality']. Cite a tool no coordenador, numa skill que ele
E   declare, ou num executor que ele despache.
tests\test_agent_coverage.py:67: AssertionError

E   AssertionError: areas de regra sem coordenador: ['SF-DQ']. Toda area precisa de
E   alguem que saiba quando investiga-la.
tests\test_agent_coverage.py:81: AssertionError
```

O primeiro é o D-5c-23, aceso desde a Task 5; o segundo, desde a Task 7. Os dois fecham com
o mesmo arquivo, e por motivos diferentes: `test_no_area_is_orphan` lê `rule_areas` do
frontmatter, e `test_no_tool_is_orphan` lê o **corpus alcançável** — o texto do coordenador
mais o das skills e executores que ele declara.

- [x] **Step 2: `agents/data-quality-reviewer.md`**

Frontmatter na forma de `agents/emr-infra-reviewer.md`:

```yaml
---
name: data-quality-reviewer
description: Use quando o job PySpark valida dado — PyDeequ, Great Expectations ou validação artesanal — e a pergunta é se a validação está no lugar certo, se ela tem consequência, e quanto ela custa em passadas sobre o dado.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - review-data-validation
  - analyze-library-call-graph
  - review-pyspark-pr
rule_areas: [SF-DQ]
executors: [sf-inventory, sf-extractor, sf-judge, sf-verifier, sf-synthesizer]
---
```

O corpo precisa de uma seção **"Quando você entra, e quando o irmão entra"**, como o `emr-infra-reviewer` tem: `pyspark-code-reviewer` revisa o código; você revisa a validação dentro dele. O que decide é a pergunta, não o artefato — os dois leem o mesmo `.py`. E uma fronteira negativa (`## Não faz`): **você não julga o dado**. Se o check reprova, quem responde é a ferramenta de DQ, não este motor.

**Entrou como o plano pediu, com a distinção escrita em forma aplicável** — um teste de decisão ("apague mentalmente as linhas de validação; a pergunta continua de pé?"), uma tabela de seis perguntas, e a âncora verificável: os dois lados saem de extratores diferentes sobre a mesma AST, com namespaces de fact disjuntos (`pyspark.*` contra `dq.*`) e áreas disjuntas. A seção também declara que um achado `SF-PY` e um `SF-DQ` sobre a mesma linha **não** são duplicação — é a mesma afirmação que a Task 10 Step 1 vai provar por teste.

- [x] **Step 3: `skills/review-data-validation/SKILL.md`**

Fluxo focado, na forma de `skills/review-emr-cluster/SKILL.md`. Toda invocação de `sparkforge judge` dentro da skill **passa runtime** — invariante de `tests/test_skill_content.py` desde a Fase 5a.

- [x] **Step 4: Espelhe**

Run: `python scripts/sync_skills.py`
Depois: `git status --short` — devem aparecer as cópias em `.claude/`, `.agents/` e `.github/agents/`.

**Cinco cópias, todas geradas pelo script**: `.claude/skills/`, `.agents/skills/`, `.claude/agents/`, `.agents/agents/` e `.github/agents/data-quality-reviewer.agent.md` (sufixo de plataforma). Nenhum destino ficou de fora, e nada foi copiado à mão.

- [x] **Step 5: Rode**

Run: `python -m pytest tests/test_agent_coverage.py tests/test_skill_content.py -q`
Expected: PASS

**Medido nesta task.** `tests/test_agent_coverage.py` e `tests/test_skill_content.py` passaram (308 testes com `test_agents_parity.py` junto), e os **dois** vermelhos do Step 1 fecharam. Mas a suíte inteira acendeu **outros dois**, que o plano não previu e que nenhum dos arquivos da Task 9 fecha sozinho — ver D-5c-31 e D-5c-32. Depois deles, suíte inteira: **3095 passed / 0 failed / 5 skipped**, e `ruff check .` limpo. Era a primeira vez desde a Task 5 que a suíte fechou sem vermelho.

**Dois desvios medidos nesta task.**

**D-5c-31 — registrar um coordenador custa QUATRO pontos, não dois.** O plano listou `agents/` e `skills/` (com os espelhos derivados do script). A suíte inteira cobra mais dois, e nenhum deles é derivado:

1. `tests/test_router_agents.py::TestAgentRoutes::test_there_is_at_least_one_route_per_coordinator` — `coordenadores sem rota: ['data-quality-reviewer']`. Toda entrada de `agents/*.md` precisa de uma rota `AGENT-*` em `rules/catalog/routing.yaml` com `recommended_agent`, `id` prefixado e `reason`. É o invariante que impede o coordenador de existir e nunca ser recomendado por `next_step` — a mesma família do órfão de tool, do outro lado do roteamento.
2. `tests/test_docs_coverage.py::TestAgentsMd::test_agents_md_lists_every_coordinator` — o `stem` de cada arquivo de `agents/` tem que aparecer em `AGENTS.md`.

Os dois foram atendidos: `AGENT-008` em `routing.yaml` e uma linha nova na tabela de coordenadores de `AGENTS.md` (com a faixa `AGENT-001`…`AGENT-007` corrigida para `AGENT-008` no parágrafo seguinte). `routing.yaml` fica em `rules/catalog/`, mas **não é catálogo de regra**: `load_catalog()` o exclui por construção (`tests/test_rules_loader.py::test_routing_is_excluded`), então nenhuma contagem de regra e nenhum golden de finding se move por causa dele.

**D-5c-32 — a posição da rota nova é precedência, e o lugar óbvio a deixaria morta.** `router._matching_rules` devolve na ordem do YAML e `next_step` projeta `agent_matches[0]`. Acrescentar `AGENT-008` no fim da lista — o gesto natural — a colocaria **depois** da `AGENT-004` (SF-PY, SF-PLAN, SF-CG), e SF-PY dispara em quase todo job PySpark: a rota nunca casaria na prática. É o mesmo defeito que os invariantes de cobertura desta fase existem para pegar, só que dentro do roteamento. A rota foi inserida **antes** da `AGENT-004`, com o motivo escrito no próprio YAML: é o único par da tabela que lê o MESMO artefato, e SF-DQ é estritamente mais estreita. Nenhuma decisão anterior muda — facts `dq.*` não existiam antes desta fase, então nenhum case já resolvido tinha como casar aqui. Medido depois da mudança:

```
['SF-DQ-001']              -> data-quality-reviewer  (AGENT-008)
['SF-DQ-001', 'SF-PY-004'] -> data-quality-reviewer  (AGENT-008)
['SF-PY-004']              -> pyspark-code-reviewer  (AGENT-004)
['SF-GLUE-002','SF-DQ-002']-> glue-infra-reviewer    (AGENT-002)
```

**Dívida deixada aberta, e nomeada:** `pyspark-code-reviewer` não tem a seção recíproca dizendo quando entregar a investigação ao `data-quality-reviewer`. A distinção está escrita só de um lado. Editar o outro coordenador está fora da Task 9, e a assimetria não acende teste nenhum — é justamente por isso que fica registrada aqui.

- [x] **Step 6: Commit**

```bash
git add agents skills .claude .agents .github rules/catalog/routing.yaml AGENTS.md
git commit -m "feat(agents): data-quality-reviewer, coordenador da area SF-DQ"
```

---

## Task 10: A prova do objetivo, e o fechamento

**Files:**
- Create: `tests/test_dq_investigation_end_to_end.py`
- Modify: `docs/superpowers/STATUS.md`

- [ ] **Step 1: A prova de D-3 — sem duplicação semântica**

O critério 7 do spec. No molde de `tests/test_emr_investigation_end_to_end.py`: um job real, **sem flag de runtime nenhuma**, com uma validação artesanal depois do write sobre DataFrame não persistido.

```python
def test_dq_e_py_falam_da_mesma_linha_sem_se_repetirem():
    facts = extract_data_quality_tree(JOB, repo_root=JOB) + extract_tree(JOB, repo_root=JOB)
    findings, skipped = judge(facts, load_catalog(), {}, return_skipped=True)
    areas = {f.rule_id.rsplit("-", 1)[0] for f in findings}
    assert "SF-DQ" in areas
    # Nenhuma regra SF-PY foi alterada por esta fase, e nenhuma foi suprimida:
    # as duas areas podem falar da mesma linha, dizendo coisas diferentes.
    dq_titles = {f.rule_id for f in findings if f.rule_id.startswith("SF-DQ")}
    py_titles = {f.rule_id for f in findings if f.rule_id.startswith("SF-PY")}
    assert dq_titles and not (dq_titles & py_titles)
```

- [ ] **Step 2: O critério 9 — nenhum golden de `pyspark/` mudou**

Run: `git diff --stat main -- fixtures/pyspark/`
Expected: saída vazia. Se qualquer `fixtures/pyspark/*/expected/facts.json` aparecer, algo desta fase tocou `pyspark_ast`, e o D-2 foi violado — pare e investigue antes de seguir.

- [ ] **Step 3: Rode a suíte inteira**

Run: `python -m pytest -q`
Expected: 0 failed. Anote o total: ele vai para o STATUS no Step 5.

- [ ] **Step 4: Meça os números correntes**

```bash
python -c "
from sparkforge.rules.loader import load_catalog
import collections
rules = load_catalog()
print('regras', len(rules))
print(dict(collections.Counter(r['id'].rsplit('-',1)[0] for r in rules)))
"
python -c "
import importlib, pkgutil
import sparkforge.facts as F
kinds=set(); n=0
for m in pkgutil.iter_modules(F.__path__):
    mod = importlib.import_module('sparkforge.facts.'+m.name)
    if hasattr(mod,'EMITTED_KINDS'):
        n+=1; kinds |= set(mod.EMITTED_KINDS)
print('extratores', n, 'kinds', len(kinds))
from sparkforge.adapters.tools import TOOLS
print('tools', len(TOOLS))
"
ls -d fixtures/*/*/ | wc -l
```

- [ ] **Step 5: STATUS**

Atualize a tabela **Números correntes** com os valores medidos no Step 4 e no Step 3 — nunca copiados deste plano. Acrescente a seção "Fase 5c — SF-DQ" no formato das anteriores: o defeito de partida (o ponto cego medido, `grep` devolvendo um arquivo só), o que entrou, **o que a Task 0 vetou e por quê**, e a faixa de commits. Se `SF-DQ-004` não entrou, o número medido no gate vai escrito ali.

Nas **Dívidas abertas**, acrescente as duas que esta fase cria por decisão registrada: GE declarativo (`great_expectations.yml` e suites JSON) e dbt continuam sem cobertura, com a razão da §2 do spec.

- [ ] **Step 6: Commit**

```bash
git add tests/test_dq_investigation_end_to_end.py docs/superpowers/STATUS.md
git commit -m "docs: fecha a Fase 5c"
```

---

## Ordem e dependências

Task 0 antes de tudo — ela pode reescrever as Tasks 3 e 4. Tasks 1 → 2 → 3 → 4 são sequenciais no mesmo arquivo. Task 5 depende só da Task 1 (o módulo existir), e a Task 6 fecha o vermelho que ela deixa. Tasks 7 e 8 dependem da 6 (fixtures) e a 8 tem gate medido. Task 9 é independente das regras — depende só da área existir no catálogo. Task 10 fecha.
