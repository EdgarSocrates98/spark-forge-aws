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

- [x] **Step 4: Commit**

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py
git commit -m "feat(facts): as correlacoes que o motor nao expressa viram atributo"
```

---

## Task 3: PyDeequ e Great Expectations

**Files:**
- Modify: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [ ] **Step 1: Confira a Task 0 antes de escrever**

Releia `knowledge/dq/validation-frameworks.md`. Se a pesquisa mostrou que a superfície do GE 1.x é outra, **o teste abaixo muda para a forma apurada**, e o veto à forma antiga vai para o cabeçalho do catálogo na Task 7. Não escreva detecção para uma API que a fonte diz não existir mais.

- [ ] **Step 2: Teste do PyDeequ**

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

- [ ] **Step 3: Reconheça pela forma, não por lista de nomes**

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

- [ ] **Step 4: Great Expectations, na forma que a Task 0 apurou (desvio D-5c-3)**

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

- [ ] **Step 5: Rode a suíte inteira do extrator**

Run: `python -m pytest tests/test_facts_data_quality.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py knowledge/dq/validation-frameworks.md
git commit -m "feat(facts): pydeequ e great expectations, reconhecidos pela forma"
```

---

## Task 4: `dq.enforcement` — a consequência que o extrator prova

**Files:**
- Modify: `sparkforge/facts/data_quality.py`, `tests/test_facts_data_quality.py`

- [ ] **Step 1: Teste primeiro — e note o subject**

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

- [ ] **Step 2: Implemente**

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

Run: PASS.

- [ ] **Step 3: `assert` conta como enforcement, com ressalva (desvio D-5c-4)**

A Task 0 fechou o ramo: a referência da linguagem confirma que `-O` apaga o `assert`, mas **nenhuma** fonte da AWS mostra Glue ou EMR rodando o driver assim, e no Glue o caminho documentado (`--customer-driver-env-vars`) rejeita chaves sem o prefixo `CUSTOMER_`. Então `form: "assert"` **é** enforcement — não emita `dq.unresolved` por causa disso.

A ressalva vai escrita na `explanation` de `SF-DQ-002`, na Task 7, com a URL da referência da linguagem. Deixe um comentário no código apontando para `knowledge/dq/validation-frameworks.md` §3.4, para ninguém "corrigir" isso depois sem ler a fonte.

- [ ] **Step 4: Commit**

```bash
git add sparkforge/facts/data_quality.py tests/test_facts_data_quality.py
git commit -m "feat(facts): dq.enforcement so quando a consequencia esta provada"
```

---

## Task 5: Registro de superfície

Oito pontos. Esquecer um é o modo de falha desta fase, e dois deles são listas manuais duplicadas.

**Files:**
- Modify: `tests/test_rules_catalog_reachability.py:26-63`, `tests/test_fixtures_kind_coverage.py:24-59`, `sparkforge/adapters/_core.py`, `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py`, `parity.yaml`, `manifest.json`, `scripts/regen_fixtures.py`

- [ ] **Step 1: As duas listas `EXTRACTORS`**

Acrescente `data_quality` ao import e à coleção nos **dois** arquivos — tupla em `test_rules_catalog_reachability.py`, dict (`"data_quality": data_quality`) em `test_fixtures_kind_coverage.py`.

Run: `python -m pytest tests/test_fixtures_kind_coverage.py -v`
Expected: FAIL em `test_every_kind_of_every_extractor_appears_in_some_golden[data_quality]` — os quatro kinds ainda não têm golden. **É o resultado correto nesta etapa**; a Task 6 o fecha.

- [ ] **Step 2: `_core.analyze_data_quality`**

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

- [ ] **Step 3: CLI**

Subparser `data-quality` sob `analyze`, com `--path` (required), `--out`, `--kind` (append), `--limit`, `--cursor`; handler `_cmd_analyze_data_quality` na forma de `_cmd_analyze_emr_cluster` (`cli.py:740`); entrada `("analyze", "data-quality"): _cmd_analyze_data_quality` no dict de dispatch (`cli.py:1021`).

- [ ] **Step 4: MCP**

`sparkforge_analyze_data_quality` em `TOOLS`, com `inputSchema` de `path`/`kind`/`limit`/`cursor` e `outputSchema` `_may_fail(_ANALYZE_FACTS_SCHEMA, ...)`; handler `_h_analyze_data_quality`; entrada no dict de handlers. A `description` precisa dizer o que o fact carrega **e o que ele recusa afirmar** — que não julga o dado, só onde a validação está.

- [ ] **Step 5: `parity.yaml` e `manifest.json`**

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

- [ ] **Step 6: `regen_dq` em `scripts/regen_fixtures.py`**

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

- [ ] **Step 7: Rode o que já pode passar**

Run: `python -m pytest tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_capability_parity.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add tests/ sparkforge/adapters/ parity.yaml manifest.json scripts/regen_fixtures.py
git commit -m "feat(adapters): analyze data-quality na CLI, no MCP e nos manifestos"
```

---

## Task 6: Fixtures e o golden do domínio

**Files:**
- Create: `fixtures/dq/*` (oito), `tests/test_fixtures_golden_dq.py`

- [ ] **Step 1: Os oito diretórios**

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

- [ ] **Step 2: `tests/test_fixtures_golden_dq.py`**

Copie a estrutura de `tests/test_fixtures_golden_callgraph.py`: `REQUIRED_FIXTURES` com os oito nomes, `run_fixture` chamando `extract_data_quality_tree` + `judge`, e a classe `TestGolden` com os quatro testes (`facts_match_golden`, `findings_match_golden`, `declared_kinds_all_present`, `declared_rules_all_fire`).

- [ ] **Step 3: Gere os goldens e LEIA o diff**

Run: `python scripts/regen_fixtures.py`
Depois: `git diff --stat fixtures/dq/`

Nesta etapa `findings.json` sai vazio em todas — o catálogo `SF-DQ` só nasce na Task 7. **Isso é esperado**, e os goldens de findings são regenerados de novo lá.

- [ ] **Step 4: Rode**

Run: `python -m pytest tests/test_fixtures_golden_dq.py tests/test_fixtures_kind_coverage.py -v`
Expected: PASS, incluindo `test_every_kind_of_every_extractor_appears_in_some_golden[data_quality]`, que a Task 5 deixou vermelho

- [ ] **Step 5: Commit**

```bash
git add fixtures/dq tests/test_fixtures_golden_dq.py
git commit -m "test(dq): oito fixtures, e os quatro kinds provados por golden"
```

---

## Task 7: `SF-DQ-001` e `SF-DQ-002`

**Files:**
- Create: `rules/catalog/data-quality.yaml`
- Modify: `fixtures/dq/*/expected/findings.json` (regenerados), `fixtures/dq/*/meta.yaml`

- [ ] **Step 1: Cabeçalho do catálogo, com os vetos da Task 0**

O cabeçalho registra três coisas, na forma que `rules/catalog/emr-infra.yaml` e `callgraph.yaml` usam: por que `runtime_scope` é vazio nas quatro (gatilho é AST, critério da Fase 5a); por que a correlação vive no extrator (§4.4 do spec, `engine._condition_candidates`); e **os vetos que a Task 0 produziu**, um parágrafo por premissa morta, para ninguém reinventá-las.

- [ ] **Step 2: `SF-DQ-001`**

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

- [ ] **Step 3: `SF-DQ-002`, com `same_subject`**

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

- [ ] **Step 4: Regenere e leia o diff**

Run: `python scripts/regen_fixtures.py && git diff fixtures/dq/*/expected/findings.json`

Confirme, lendo: `validation_after_write` ganhou `SF-DQ-001`; `suite_without_enforcement` ganhou `SF-DQ-002`; **`validated_correctly` continua com `findings.json` vazio**. Acrescente os `expects_rules` correspondentes nos `meta.yaml`.

- [ ] **Step 5: Rode**

Run: `python -m pytest tests/test_fixtures_golden_dq.py tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add rules/catalog/data-quality.yaml fixtures/dq
git commit -m "feat(rules): SF-DQ-001 e SF-DQ-002, posicao e consequencia"
```

---

## Task 8: `SF-DQ-003` e `SF-DQ-004`, com o gate medido

**Files:**
- Modify: `rules/catalog/data-quality.yaml`, `fixtures/dq/*`

- [ ] **Step 1: `SF-DQ-003`**

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

- [ ] **Step 2: Meça o gate de `SF-DQ-004` antes de escrevê-la**

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

- [ ] **Step 3: `SF-DQ-004`, se o gate passou**

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

- [ ] **Step 4: Regenere, leia o diff, rode**

Run: `python scripts/regen_fixtures.py && python -m pytest tests/test_fixtures_golden_dq.py -q`
Expected: PASS, com `check_recomputes_lineage` e `repeated_checks_same_target` disparando as regras novas e `validated_correctly` ainda vazio

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/data-quality.yaml fixtures/dq
git commit -m "feat(rules): SF-DQ-003 e SF-DQ-004, o custo da validacao"
```

---

## Task 9: Coordenador, skill e espelhos

**Files:**
- Create: `agents/data-quality-reviewer.md`, `skills/review-data-validation/SKILL.md`

- [ ] **Step 1: Rode o teste que prova a órfã**

Run: `python -m pytest tests/test_agent_coverage.py -v`
Expected: FAIL em `test_no_area_is_orphan` — `SF-DQ` não tem coordenador. Cole a saída: é a justificativa da task.

- [ ] **Step 2: `agents/data-quality-reviewer.md`**

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

- [ ] **Step 3: `skills/review-data-validation/SKILL.md`**

Fluxo focado, na forma de `skills/review-emr-cluster/SKILL.md`. Toda invocação de `sparkforge judge` dentro da skill **passa runtime** — invariante de `tests/test_skill_content.py` desde a Fase 5a.

- [ ] **Step 4: Espelhe**

Run: `python scripts/sync_skills.py`
Depois: `git status --short` — devem aparecer as cópias em `.claude/`, `.agents/` e `.github/agents/`.

- [ ] **Step 5: Rode**

Run: `python -m pytest tests/test_agent_coverage.py tests/test_skill_content.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents skills .claude .agents .github
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
