# SparkForge Fase 5a — Correção de Escopo: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** fazer o escopo de regra dizer o que a regra significa, e fazer a ausência ser explicada em vez de silenciosa. Hoje `runtime_scope: {glue: "*"}` não filtra nada, 20 regras agnósticas estão marcadas como se fossem de Glue, e `SF-GLUE-002` some de findings **e** de skipped.

**Architecture:** três correções encadeadas, em ordem inegociável. Primeiro reetiquetar as 20 agnósticas — enquanto o curinga ainda é permissivo. Só então tornar o curinga sensível à presença da chave. Por último, reancorar `SF-GLUE-002` e fazer as skills passarem runtime. Invertido, as 20 regras somem do relatório no instante em que a semântica muda.

**Tech Stack:** YAML declarativo (`rules/catalog/`), Python stdlib, pytest.

**Spec:** [`../specs/2026-08-01-sparkforge-fase5-emr-design.md`](../specs/2026-08-01-sparkforge-fase5-emr-design.md) — §3.1, §3.2, §3.3 e os critérios 10, 11 e 13.

**Escopo:** esta é a **5a**. EMR propriamente — `emr` no `RuntimeContext`, `EMR_MATRIX`, extrator de cluster, área `SF-EMR`, coordenador — é a **5b**, com plano próprio, sobre a base que esta corrige.

---

## Fatos do ambiente verificados antes de escrever este plano

Medidos, não copiados:

```
regras          48   |  com runtime_scope {glue:"*"}: 25
agnosticas      20   SF-PY-001..012, SF-PQ-001/003/005, SF-PLAN-001/002,
                     SF-CG-001, SF-UI-005, SF-ENV-001
infra Glue       5   SF-GLUE-002..006
testes        1940   |  ruff limpo, espelhos conferindo
```

`sparkforge/rules/version_scope.py:41-42` — o ramo do curinga:

```python
if spec == "*":
    continue
```

Provado por execução:
```
in_scope({'glue': '*'}, {'spark': '3.5.6', 'emr': '7.5.0'})  -> True
in_scope({'glue': '*'}, {})                                  -> True
```

`requires_facts` de cada uma das 25, que é o que determina a natureza:

| Regra | requires_facts |
|---|---|
| SF-PY-001..012 | `pyspark.*` — AST puro |
| SF-CG-001 | `callgraph.cycle` — derivado de AST |
| SF-PLAN-001/002 | `plan.python_udf` |
| SF-PQ-001/003 | `s3.prefix_summary` |
| SF-PQ-005 | `s3.prefix_summary`, `catalog.table_partitions` |
| SF-UI-005 | `spark.executor.lost` |
| SF-ENV-001 | `env.runtime_signal` |
| SF-GLUE-002 | `tf.module_analyzed` ← **sentinela genérico, causa do silêncio** |
| SF-GLUE-003/006 | `tf.attribute` |
| SF-GLUE-004 | `tf.attribute`, `pyspark.write` |
| SF-GLUE-005 | `tf.attribute`, `spark.log_analyzed`, `spark.job.spill_summary`, `spark.executor.memory_usage` |

**`SF-ENV-001` é caso especial.** Ela é a regra que **detecta divergência de runtime**. Se passar a exigir `glue` presente, para de funcionar exatamente num job EMR — que é quando mais se precisa dela. Ver Task 2.

Outros fatos:
- `build_runtime_context` (`sparkforge/adapters/_core.py:104-121`) monta o contexto **só** de flags da CLI, nunca dos facts coletados.
- 10 skills chamam `judge`; nem todas passam `--glue` ou `--spark`.
- `judge --show-skipped` existe e funciona: `engine.judge(..., return_skipped=True)` devolve `skipped` com `reason` em `{runtime_scope, blocked_on, requires_facts}`.
- `tests/test_runtime_glue_versions.py` já testa escopo por runtime nas bordas — é o padrão a seguir.
- **Achado durante a execução:** `SF-ATH-001..005` usam `{athena: "*"}`, e `RuntimeContext.athena` tem default `""` que `to_dict()` sempre emite — a chave nunca é detectada, só preenchida pela flag `--athena`. Segunda família de curinga, mesmo defeito. Ver Task 3, Step 0.

---

## File Structure

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `rules/catalog/pyspark.yaml` | 12 regras reetiquetadas |
| `rules/catalog/parquet.yaml` | 3 reetiquetadas |
| `rules/catalog/spark-plan.yaml` | 2 reetiquetadas |
| `rules/catalog/callgraph.yaml` | 1 reetiquetada |
| `rules/catalog/spark-ui.yaml` | 1 reetiquetada |
| `rules/catalog/env.yaml` | SF-ENV-001 — decisão própria |
| `rules/catalog/glue-infra.yaml` | SF-GLUE-002 reancorada |
| `sparkforge/rules/version_scope.py` | curinga exige presença |
| `sparkforge/facts/terraform.py` | fact específico de `aws_glue_job` |
| `skills/*/SKILL.md` | passar runtime no `judge` |
| `tests/test_rules_version_scope.py` | curinga com chave ausente e presente |
| `tests/test_runtime_glue_versions.py` | matriz de escopo por runtime |

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `tests/test_rule_scope_by_nature.py` | Invariante: regra agnóstica não some por falta de `glue` |

---

## Task 1: O invariante do escopo, antes de mexer em regra

Primeiro, e vermelho. Ele descreve o estado desejado e é o que prova que a reetiquetagem das tasks seguintes não apagou regra nenhuma.

**Files:**
- Create: `tests/test_rule_scope_by_nature.py`

- [x] **Step 1: Escreva o teste**

```python
# tests/test_rule_scope_by_nature.py
"""Escopo de regra tem que dizer o que a regra significa.

`runtime_scope: {glue: "*"}` foi lido como "qualquer runtime" quando significa
"qualquer versao de Glue" -- e o ramo do curinga em `version_scope.py` nem
checa presenca da chave, entao ele nunca filtrou nada.

O resultado: 20 regras agnosticas marcadas como de Glue, e 5 regras de infra
Glue avaliando em silencio num runtime que nao e Glue. Silencio, para um agente
autonomo, le como "nada encontrado" -- e a versao de orientacao do defeito que
`pyspark.unresolved` existe para impedir no analisador.
"""
from pathlib import Path

import pytest

from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope

ROOT = Path(__file__).resolve().parents[1]

# Runtime EMR-like: Spark e Iceberg detectados, NENHUMA chave `glue`.
# E o cenario que a Fase 5 existe para servir.
EMR_LIKE = {"spark": "3.5.1", "python": "3.11", "iceberg": "1.7.1"}

# As que dependem de infraestrutura Glue. Lista explicita porque e curta,
# fechada, e a fronteira exata desta fase -- derivar do disco esconderia uma
# regra nova entrando no grupo errado sem ninguem decidir.
GLUE_INFRA = {"SF-GLUE-002", "SF-GLUE-003", "SF-GLUE-004", "SF-GLUE-005", "SF-GLUE-006"}


def _rules() -> list[dict]:
    return load_catalog()


class TestAgnosticRulesSurviveWithoutGlue:
    """Regra de codigo, plano, armazenamento ou execucao nao pode sumir so
    porque o runtime nao e Glue."""

    # `ids` como lista pre-computada, NUNCA `ids=lambda`. Com `parametrize` sobre
    # lista vazia -- o que acontece se `load_catalog()` falhar -- o pytest 8.x
    # chama o callable sobre um sentinela interno e estoura DENTRO do coletor,
    # abortando a suite inteira em vez de pular. Mordeu na Fase 4.
    _AGNOSTICAS = [r for r in _rules() if r["id"] not in GLUE_INFRA]

    @pytest.mark.parametrize(
        "rule", _AGNOSTICAS, ids=[r["id"] for r in _AGNOSTICAS]
    )
    def test_agnostic_rule_is_evaluated_on_a_non_glue_runtime(self, rule):
        assert in_scope(rule.get("runtime_scope") or {}, EMR_LIKE), (
            f"{rule['id']} some num runtime sem `glue`. Se ela depende mesmo de "
            f"infraestrutura Glue, acrescente-a a GLUE_INFRA e justifique; se nao, "
            f"o `runtime_scope` esta errado."
        )


class TestGlueInfraRulesAreSkippedWithoutGlue:
    """A outra ponta. Sem isto, elas avaliam e nunca disparam -- silencio."""

    @pytest.mark.parametrize("rule_id", sorted(GLUE_INFRA))
    def test_glue_infra_rule_is_out_of_scope_without_glue(self, rule_id):
        rule = next(r for r in _rules() if r["id"] == rule_id)
        assert not in_scope(rule.get("runtime_scope") or {}, EMR_LIKE), (
            f"{rule_id} e avaliada num runtime sem `glue`. Ela le `aws_glue_job` do "
            f"Terraform: vai avaliar e nunca disparar, e o operador nao fica sabendo "
            f"que esse eixo nao foi coberto."
        )


class TestNoRuleUsesTheAmbiguousWildcardAnymore:
    def test_glue_wildcard_is_gone_from_agnostic_rules(self):
        """`{glue: "*"}` so pode sobrar nas regras que sao mesmo de Glue."""
        offenders = sorted(
            r["id"]
            for r in _rules()
            if str(r.get("runtime_scope")) == "{'glue': '*'}" and r["id"] not in GLUE_INFRA
        )
        assert not offenders, (
            f"regras agnosticas ainda com `{{glue: '*'}}`: {offenders}. "
            f"O curinga diz 'qualquer versao de Glue', nao 'qualquer runtime'."
        )
```

- [x] **Step 2: Rode e leia a falha**

Run: `python -m pytest tests/test_rule_scope_by_nature.py -v`

Esperado hoje: `TestAgnosticRulesSurviveWithoutGlue` **passa** (o curinga permissivo faz tudo avaliar), `TestGlueInfraRulesAreSkippedWithoutGlue` **falha nas 5**, e `TestNoRuleUsesTheAmbiguousWildcardAnymore` **falha listando as 20**.

Cole a saída no relatório. A assimetria é o diagnóstico: o curinga faz o lado errado passar e o lado certo falhar.

- [x] **Step 3: Commit**

```bash
git add tests/test_rule_scope_by_nature.py
git commit -m "test: invariante de escopo por natureza da regra"
```

---

## Task 2: Reetiquetar as 20 — antes de tocar no curinga

**A ordem é inegociável.** Enquanto o curinga ainda é permissivo, reetiquetar é seguro: as regras que ganharem escopo novo passam a ser filtradas por ele, e as que ainda têm curinga seguem avaliando. Invertido, as 20 somem no instante em que a semântica muda.

**Files:**
- Modify: `rules/catalog/pyspark.yaml`, `parquet.yaml`, `spark-plan.yaml`, `callgraph.yaml`, `spark-ui.yaml`, `env.yaml`

- [x] **Step 1: Decida o escopo de cada grupo, lendo o que a regra exige**

Não é substituição em massa. O critério é o `requires_facts`:

| Grupo | Regras | `requires_facts` | Escopo proposto |
|---|---|---|---|
| Código | SF-PY-001..012, SF-CG-001 | `pyspark.*`, `callgraph.*` | `{spark: ">=3.0"}` |
| Plano | SF-PLAN-001/002 | `plan.python_udf` | `{spark: ">=3.0"}` |
| Execução | SF-UI-005 | `spark.executor.lost` | `{spark: ">=3.0"}` |
| Armazenamento | SF-PQ-001/003/005 | `s3.*`, `catalog.*` | ver Step 2 |
| Divergência | SF-ENV-001 | `env.runtime_signal` | ver Step 3 |

`{spark: ">=3.0"}` é o mesmo escopo que SF-PLAN, SF-UI e outras 9 regras já usam — não é invenção desta fase.

**Antes de aplicar, leia cada uma das 13 regras de código e plano** e confirme que nenhuma depende de comportamento posterior a Spark 3.0. Se alguma depender, dê a ela o escopo mais estreito e **diga qual e por quê** no relatório.

- [x] **Step 2: SF-PQ — decida e justifique**

As três leem `s3.prefix_summary` e `catalog.table_partitions`. Armazenamento não depende do motor de execução: um prefixo com small files é small files independentemente de quem escreveu.

Duas saídas, e você escolhe com justificativa:
- `{spark: ">=3.0"}`, alinhando com as demais — simples, mas amarra armazenamento a versão de motor sem razão
- escopo vazio `{}`, que `in_scope` trata como "sempre casa" — honesto para regra que não depende de runtime nenhum

**Confirme o comportamento de `{}` lendo `version_scope.py`** antes de decidir. Se `{}` for equivalente ao curinga de hoje, ele carrega o mesmo problema — e aí a primeira saída é a certa.

- [x] **Step 3: SF-ENV-001 — o caso que exige cuidado**

Ela **detecta divergência de runtime**. Se ganhar `{glue: ">=3.0"}` ou qualquer escopo que exija Glue, para de funcionar num job EMR — exatamente onde divergência entre fontes é mais provável, porque há duas plataformas em jogo.

Decida entre escopo vazio, `{spark: ">=3.0"}`, ou outro que você defenda. Escreva a justificativa **no comentário da regra**, não só no relatório: quem mexer nela depois precisa entender por que ela é diferente das outras.

- [x] **Step 4: Aplique e confirme que nada sumiu**

```bash
python -m pytest tests/test_rule_scope_by_nature.py -v
python -m pytest tests/test_runtime_glue_versions.py -v
python -m pytest -q
```

Esperado: `TestNoRuleUsesTheAmbiguousWildcardAnymore` passa. `TestAgnosticRulesSurviveWithoutGlue` **continua passando** — se alguma regra sumir aqui, o escopo que você deu é estreito demais.

`test_runtime_glue_versions.py` tem `test_every_area_of_the_catalog_survives_the_version_guard` para Glue 4.0, 5.0 e 5.1. Ele **não pode regredir**: as regras reetiquetadas precisam continuar valendo em Glue.

- [x] **Step 5: Prove nos dois runtimes**

```bash
python - <<'EOF'
import sys; sys.path.insert(0,'.')
from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope
for nome, rt in [("Glue 5.0", {"glue":"5.0","spark":"3.5.4","python":"3.11","iceberg":"1.7.1"}),
                 ("EMR-like", {"spark":"3.5.1","python":"3.11","iceberg":"1.7.1"})]:
    r = load_catalog()
    dentro = [x["id"] for x in r if in_scope(x.get("runtime_scope") or {}, rt)]
    fora   = [x["id"] for x in r if not in_scope(x.get("runtime_scope") or {}, rt)]
    print(f"{nome:10} avaliadas {len(dentro):>2} | puladas {len(fora):>2}: {', '.join(sorted(fora))}")
EOF
```

Esperado: em Glue, todas as 48 avaliadas (ou só as que já eram puladas antes). Em EMR-like, as 5 SF-GLUE puladas — **mas só depois da Task 3**; aqui elas ainda passam pelo curinga. Relate os dois números.

- [x] **Step 6: Commit**

```bash
git add rules/catalog
git commit -m "fix(rules): 20 regras agnosticas estavam marcadas como de Glue"
```

---

## Task 3: O curinga passa a exigir presença

Só agora. Com as 20 já reetiquetadas, mudar a semântica afeta apenas as regras que devem ser afetadas.

> **Corrigido durante a execução.** A Task 2 encontrou uma segunda família de curinga que este plano não previu: `SF-ATH-001..005` declaram `runtime_scope: {athena: "*"}`, e `athena` **nunca é detectado** — `RuntimeContext.athena` tem default `""`, `to_dict()` sempre emite a chave, e o valor só é preenchido pela flag `--athena` explícita. Depois da mudança de semântica, `runtime.get("athena")` devolve `""`, que é falso, e as 5 somem **em todo runtime**: Glue 4.0, 5.0, 5.1 e EMR-like. Isso quebraria `test_every_area_of_the_catalog_survives_the_version_guard` (área SF-ATH inteira desaparece) e `TestAgnosticRulesSurviveWithoutGlue` (as 5 não estão em `GLUE_DEPENDENT`). A mesma razão de ordem que motivou a Task 2 vale aqui: **reetiquetar antes de mudar a semântica.** Daí o Step 0 abaixo.

**Files:**
- Modify: `rules/catalog/athena.yaml`, `sparkforge/rules/version_scope.py`, `tests/test_rules_version_scope.py`, `tests/test_rule_scope_by_nature.py`

- [x] **Step 0: Reetiquetar as SF-ATH, antes de tudo**

O gate real dessas 5 é `requires_facts`, não versão:

| Regra | `requires_facts` |
|---|---|
| SF-ATH-001 | `sql.projection.enriched` |
| SF-ATH-002 | `sql.projection`, `catalog.table_schema` |
| SF-ATH-003 | `catalog.table_partitions` |
| SF-ATH-004 | `athena.workgroup` |
| SF-ATH-005 | `sql.predicate.enriched` |

Nenhuma dispara sem que alguém tenha analisado uma consulta, um schema de catálogo ou um workgroup. `{athena: "*"}` foi escrito querendo dizer "estas são regras de Athena" — uma etiqueta de serviço — mas o mecanismo que ele usa é guarda de versão. É exatamente o erro de camada que esta fase existe para desfazer: `runtime_scope` guarda versão; quem gateia por natureza do artefato é `requires_facts`.

Dê às 5 escopo vazio `{}`, com comentário YAML explicando que o gate é `requires_facts` e que a versão de engine do Athena não é detectada — só declarada por flag. Se você discordar e defender outro escopo, **diga qual e por quê** em vez de seguir.

Generalize também `TestNoRuleUsesTheAmbiguousWildcardAnymore` em `tests/test_rule_scope_by_nature.py`: hoje ele procura a string literal `{'glue': '*'}`. Ele tem que pegar **qualquer** `runtime_scope` de valor `"*"` cuja chave não esteja declarada como dependente daquele serviço — foi a literalidade dele que deixou `{athena: "*"}` passar.

- [x] **Step 1: Escreva os testes primeiro**

Acrescente a `tests/test_rules_version_scope.py`, na classe `TestInScope`:

```python
    def test_wildcard_requires_the_key_to_be_present(self):
        """`{glue: "*"}` significa "qualquer VERSAO de Glue", nao "qualquer
        runtime". Antes desta fase o ramo do curinga pulava a checagem de
        presenca e nunca filtrava nada -- foi essa ambiguidade que fez 20 regras
        agnosticas serem marcadas como de Glue."""
        assert in_scope({"glue": "*"}, {"glue": "5.0"}) is True
        assert in_scope({"glue": "*"}, {"spark": "3.5.1"}) is False
        assert in_scope({"glue": "*"}, {}) is False

    def test_wildcard_accepts_any_version_of_a_present_key(self):
        for versao in ("3.0", "4.0", "5.0", "5.1"):
            assert in_scope({"glue": "*"}, {"glue": versao}) is True

    def test_wildcard_still_composes_with_other_keys(self):
        scope = {"glue": "*", "iceberg": ">=1.7.0"}
        assert in_scope(scope, {"glue": "5.0", "iceberg": "1.7.1"}) is True
        assert in_scope(scope, {"glue": "5.0", "iceberg": "1.0.0"}) is False
        assert in_scope(scope, {"iceberg": "1.7.1"}) is False
```

- [x] **Step 2: Veja falhar**

Run: `python -m pytest tests/test_rules_version_scope.py -v`
Esperado: os casos de chave ausente falham — hoje devolvem `True`.

- [x] **Step 3: Mude o ramo do curinga**

Em `sparkforge/rules/version_scope.py`, substitua:

```python
        if spec == "*":
            continue
```

por:

```python
        if spec == "*":
            # `"*"` e "qualquer VERSAO deste componente", nao "qualquer runtime":
            # a chave precisa estar presente. Antes desta fase o ramo pulava a
            # checagem inteira e o curinga nunca filtrava nada -- foi essa
            # ambiguidade que fez 20 regras agnosticas serem etiquetadas como de
            # Glue, e as 5 de infra Glue avaliarem em silencio num job EMR.
            if not runtime.get(key):
                return False
            continue
```

- [x] **Step 4: Veja passar, e confirme que o resto não regrediu**

```bash
python -m pytest tests/test_rules_version_scope.py tests/test_rule_scope_by_nature.py -v
python -m pytest tests/test_runtime_glue_versions.py tests/test_rules_engine.py -v
python -m pytest -q
```

Esperado: `TestGlueInfraRulesAreSkippedWithoutGlue` **passa agora** — as 5 são puladas em EMR-like. E `test_runtime_glue_versions.py` continua verde: em Glue, a chave está presente e o curinga casa.

Se algum golden de fixture mudar, **leia o diff antes de regenerar**: significa que uma regra parou de disparar onde disparava, e você precisa entender qual e por quê.

- [x] **Step 5: Rode o Step 5 da Task 2 de novo**

O mesmo script dos dois runtimes. Agora as 5 SF-GLUE têm que aparecer como puladas em EMR-like. Cole a saída — é a prova do objetivo desta fase.

- [x] **Step 6: Commit**

```bash
git add sparkforge/rules/version_scope.py tests/test_rules_version_scope.py
git commit -m "fix(scope): curinga exige presenca da chave, como todo leitor assume"
```

---

## Task 3b: `SF-ICE` sumia inteira quando a versão não era detectada

> **Acrescentada durante a execução.** A Task 3 mediu, num runtime EMR realista em que só o event log observou Spark, que a área `SF-ICE` inteira desaparecia. `SF-GLUE` sumir ali é o objetivo da fase — não há infraestrutura Glue a revisar, e agora isso aparece como pulado com motivo. `SF-ICE` sumir é falso negativo: tabelas Iceberg existem em EMR, e a área apagava porque ninguém **detectou** a versão.

As 5 declaravam `{iceberg: ">=1.0.0"}`, e `iceberg` só é resolvido por flag explícita ou inferido de `GLUE_MATRIX` quando há Glue — ou seja, era um gate de Glue disfarçado sobre regras que nada têm de Glue. O gate real é `requires_facts` (`iceberg.files_summary`, `.delete_files_summary`, `.snapshots_summary`, `.table_property`), que só existe se alguém apontou o extrator para metadados Iceberg.

**Concluída** no commit `cb80f17`. As 5 ficaram com `{}`, e `tests/test_rule_scope_by_nature.py` ganhou `TestNoCatalogAreaVanishesEntirely`, que mede o **agregado** — foi o agregado que escapou, não a regra individual — com runtimes derivados de `GLUE_MATRIX` e exceção declarada só para `SF-GLUE`.

---

## Task 3c: esvaziar os guardas de versão falsos

> **Acrescentada durante a execução, e decidida pelo usuário.** A Task 3b mediu a consequência das Tasks 2 e 3 juntas: com `build_runtime_context()` sem flags — que é o padrão de `sparkforge judge` — **6 das 9 áreas do catálogo somem**. As 19 regras que a Task 2 moveu de `{glue: "*"}` para `{spark: ">=3.0"}` trocaram um rótulo permissivo e errado por um guarda estrito e errado. Medido:
>
> ```
> build_runtime_context() -> {'glue':'','spark':'','python':'','iceberg':'','athena':''}
> SF-CG 0/1  SF-GLUE 0/6  SF-PLAN 0/4  SF-PQ 0/5  SF-PY 0/12  SF-UI 0/6
> ```

**Files:**
- Modify: `rules/catalog/pyspark.yaml`, `parquet.yaml`, `spark-plan.yaml`, `spark-ui.yaml`, `callgraph.yaml`, `env.yaml`
- Modify: `tests/test_rule_scope_by_nature.py`

- [x] **Step 1: O critério, e ele é o da fase**

`runtime_scope` só pode ser não-vazio quando o **gatilho** da regra genuinamente varia com a versão **e** essa versão vem do runtime, não de um fact que a própria regra já lê.

Regra cujo gatilho é AST (`SF-PY`, `SF-CG`), plano físico (`SF-PLAN`), event log (`SF-UI`) ou layout de armazenamento (`SF-PQ`) não depende de versão detectada para valer: `coalesce(1)` é P0 em Spark 3.0 e em 3.5. O gate certo é `requires_facts`.

**Cuidado com o caso inverso**, e ele existe: regra cujo *gatilho* é agnóstico mas cuja *recomendação* cita algo versionado — a Task 2 registrou que `SF-PY-005`, `SF-PY-009`, `SF-PY-010` e `SF-PQ-001` mencionam AQE e o hint `REBALANCE` (Spark 3.2) no `proposed_change`. Esvaziar o guarda faz elas dispararem onde o conselho pode não se aplicar. **Isso é aceito**: o achado continua verdadeiro, e apagar um P0 real por causa de um bullet de remediação é o erro maior. Mas verifique cada uma e **diga no relatório quais têm essa propriedade**, para que a 5b decida se o `proposed_change` precisa de ramo por versão.

- [x] **Step 2: `SF-ENV-004` — o guarda está na camada errada**

Ela declara `{glue: "<4.0"}`, mas a condição do `when` é `attrs.spark_minor < 3.2` — puramente Spark. Num cluster EMR com Spark 3.1.1 ela é apagada exatamente quando é mais necessária.

Duas leituras, e você decide com justificativa: `{spark: "<3.2"}`, que ao menos é verdadeiro e casa com a condição; ou `{}`, porque o `when` já lê a versão do fact e o guarda é redundante — e `{spark: "<3.2"}` falharia fechado quando `spark` não é detectado, que é o defeito que esta task existe para fechar. Leia a regra inteira antes.

- [x] **Step 3: O teste que trava**

`TestNoCatalogAreaVanishesEntirely` já existe e deriva runtimes de `GLUE_MATRIX`. Acrescente o runtime **vazio** — `build_runtime_context()` sem argumento nenhum, o padrão real da CLI — ao conjunto exercitado. A exceção declarada para `SF-GLUE` continua valendo; nenhuma outra área pode sumir.

- [x] **Step 4: Verificação**

```bash
rtk proxy python -m pytest tests/test_rule_scope_by_nature.py -q
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
```

Golden vai mudar em massa — só o campo `runtime_scope` do payload pode divergir. **Leia o diff antes de regenerar.**

- [x] **Step 5: Commit**

```bash
git add rules/catalog tests fixtures
git commit -m "fix(rules): guarda de versao apagava analise estatica sem runtime detectado"
```

---

## Task 4: `SF-GLUE-002` some de findings e de skipped

Independente do curinga. Mesmo num runtime que **é** Glue, se o Terraform não tem `aws_glue_job`, ela desaparece dos dois lados.

**Files:**
- Modify: `rules/catalog/glue-infra.yaml`, possivelmente `sparkforge/facts/terraform.py`
- Test: `tests/test_rule_scope_by_nature.py` (acrescentar)

- [x] **Step 1: Reproduza o silêncio**

```bash
python - <<'EOF'
import sys, tempfile, json; sys.path.insert(0,'.')
from pathlib import Path
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

d = Path(tempfile.mkdtemp())
(d / "main.tf").write_text(
    'resource "aws_emr_cluster" "x" {\n  release_label = "emr-7.5.0"\n}\n', encoding="utf-8")
facts = extract_terraform_tree(d, repo_root=d)
rt = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}
findings, skipped = judge(facts, load_catalog(), rt, return_skipped=True)
print("kinds emitidos:", sorted({f.kind for f in facts}))
print("SF-GLUE em findings:", sorted({f.rule_id for f in findings if f.rule_id.startswith("SF-GLUE")}))
print("SF-GLUE em skipped:", sorted({s["rule_id"] for s in skipped if s["rule_id"].startswith("SF-GLUE")}))
EOF
```

Confirme a assinatura real de `judge(..., return_skipped=True)` lendo `sparkforge/rules/engine.py` — ajuste a chamada se divergir, e diga isso no relatório.

Esperado: `SF-GLUE-002` **não aparece em nenhum dos dois**. Cole a saída.

- [x] **Step 2: Escreva o teste que trava**

Acrescente a `tests/test_rule_scope_by_nature.py`:

```python
class TestNoRuleVanishesFromBothSides:
    """Regra que nao dispara TEM que aparecer em `skipped`, com motivo.

    `judge --show-skipped` e o mecanismo de ausencia explicada, e ele funciona --
    mas so ve regra que foi barrada por `runtime_scope`, `blocked_on` ou
    `requires_facts`. Uma regra cujo `requires_facts` e satisfeito por um
    sentinela generico passa pela barreira, avalia o `when`, da falso, e some dos
    dois lados. Para quem le o relatorio isso e indistinguivel de "esta tudo bem".
    """

    def test_a_glue_rule_without_glue_job_terraform_is_reported(self, tmp_path):
        from sparkforge.facts.terraform import extract_terraform_tree
        from sparkforge.rules.engine import judge

        (tmp_path / "main.tf").write_text(
            'resource "aws_emr_cluster" "x" {\n  release_label = "emr-7.5.0"\n}\n',
            encoding="utf-8",
        )
        facts = extract_terraform_tree(tmp_path, repo_root=tmp_path)
        runtime = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}
        findings, skipped = judge(facts, load_catalog(), runtime, return_skipped=True)

        visiveis = {f.rule_id for f in findings} | {s["rule_id"] for s in skipped}
        sumidas = sorted(GLUE_INFRA - visiveis)
        assert not sumidas, (
            f"{sumidas} nao aparecem nem em findings nem em skipped. O operador nao "
            f"fica sabendo que o eixo de infraestrutura Glue nao foi coberto."
        )
```

- [x] **Step 3: Veja falhar, e conserte**

Run: `python -m pytest tests/test_rule_scope_by_nature.py::TestNoRuleVanishesFromBothSides -v`
Esperado: falha listando `SF-GLUE-002`.

O conserto é trocar o `requires_facts` dela: `tf.module_analyzed` é sentinela de "algum `.tf` foi lido", não de "há job Glue aqui". Ela precisa exigir um fact que só exista quando há `aws_glue_job`.

**Leia `sparkforge/facts/terraform.py` e veja o que já existe.** Se `tf.resource` carregar o `resource_type` em `attrs`, pode bastar mudar o `requires_facts` e o `when` da regra. Se não houver fact adequado, o extrator precisa emitir um — e aí a mudança é maior, exige fixture nova, e você deve **relatar antes de fazer**.

Cuidado: mudar `requires_facts` de uma regra pode fazê-la parar de disparar onde disparava. `fixtures/terraform/` e `fixtures/infra_code/` têm goldens que a exercitam. Rode-os e **leia qualquer diff antes de regenerar**.

- [x] **Step 4: Verifique**

```bash
python -m pytest tests/test_rule_scope_by_nature.py tests/test_fixtures_golden_terraform.py tests/test_fixtures_golden_infra_code.py -v
python -m pytest -q
python -m ruff check sparkforge scripts tests
```

- [x] **Step 5: Commit**

```bash
git add rules/catalog/glue-infra.yaml sparkforge/facts tests/ fixtures/
git commit -m "fix(rules): SF-GLUE-002 sumia de findings e de skipped ao mesmo tempo"
```

---

## Task 5: As skills passam runtime

Depois da Task 3, `{spark: ">=3.0"}` é falso-fechado quando `spark` não é detectado. E `build_runtime_context` monta o contexto **só** de flags da CLI, nunca dos facts. Uma skill que chame `judge` sem runtime apaga as 20 regras reetiquetadas — com motivo, mas apaga.

**Files:**
- Modify: `skills/*/SKILL.md` (as que chamam `judge`)
- Test: `tests/test_skill_content.py`

- [x] **Step 1: Levante quais precisam**

```bash
grep -ln "judge" skills/*/SKILL.md
grep -c -- "--glue\|--spark\|--emr" skills/*/SKILL.md | grep ":0$"
```

A segunda lista é a que importa: skills que chamam `judge` e não passam runtime.

- [x] **Step 2: Escreva o teste**

Acrescente a `tests/test_skill_content.py`:

```python
class TestSkillsPassRuntimeToJudge:
    """`judge` sem runtime apaga as regras com guarda de versao.

    `build_runtime_context` monta o contexto so de flags da CLI, nunca dos facts
    coletados. Depois de as regras agnosticas ganharem `{spark: ">=3.0"}`, uma
    skill que chame `judge` sem `--spark` nem `--glue` recebe um relatorio com as
    20 apagadas -- com motivo em `--show-skipped`, mas apagadas.
    """

    def test_every_skill_that_judges_passes_runtime(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        faltando = []
        for skill in sorted(root.glob("skills/*/SKILL.md")):
            texto = skill.read_text(encoding="utf-8")
            if "judge" not in texto:
                continue
            if not any(flag in texto for flag in ("--glue", "--spark", "--emr")):
                faltando.append(skill.parent.name)
        assert not faltando, (
            f"skills que chamam `judge` sem passar runtime: {faltando}. "
            f"Sem runtime, toda regra com guarda de versao e pulada."
        )
```

- [x] **Step 3: Veja falhar, corrija as skills, veja passar**

Ao corrigir, **não cole a flag mecanicamente**: leia cada skill e escreva a chamada que faz sentido para o que ela investiga. Uma skill de código pode precisar só de `--spark`; uma de infra Glue precisa de `--glue`. Se alguma skill legitimamente não precisa de runtime, **diga qual e por quê** — e então o teste precisa de uma exceção declarada, não de afrouxamento.

- [x] **Step 4: Espelhos**

```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --check
```

- [x] **Step 5: Commit**

```bash
git add skills tests/test_skill_content.py .claude .agents .github
git commit -m "fix(skills): judge sem runtime apagava as regras com guarda de versao"
```

---

## Task 6: Documentação e varredura

**Files:**
- Modify: `rules/catalog/README.md`, `docs/superpowers/STATUS.md`, o spec da fase

- [x] **Step 1: Documente a semântica do curinga**

`rules/catalog/README.md` documenta o vocabulário de `runtime_scope`. Acrescente o que `"*"` significa **agora** — "qualquer versão deste componente, mas ele precisa estar presente" — e o que significava antes, para quem ler um Finding antigo entender.

- [x] **Step 2: `STATUS.md`**

Números medidos. Fase 5a concluída com faixa de commits. E registre o que sobra para a 5b: `emr` no `RuntimeContext`, `EMR_MATRIX`, extrator de cluster, área `SF-EMR`, coordenador, e a divergência de plataforma da §3.3 do spec.

- [x] **Step 3: Spec**

Trocar `**Status:** aprovado para planejamento` por implementado-parcial, deixando claro que a 5a fechou §3.1, §3.2 e os critérios 10, 11 e 13, e que EMR é a 5b.

- [x] **Step 4: Varredura**

Confira, com comando, cada critério que esta fase se propôs a fechar: **10** (`SF-GLUE-002` nunca em silêncio), **11** (curinga exige presença, sem regressão), **13** (skills passam runtime). Os demais são da 5b.

```bash
python -m pytest -q
python -m ruff check sparkforge scripts tests
python scripts/sync_skills.py --check
python scripts/gen_requirements.py --check
python scripts/check_evals.py
```

- [x] **Step 5: Commit**

```bash
git add rules/catalog/README.md docs/superpowers
git commit -m "docs: semantica do curinga, e fecha a Fase 5a"
```

---

## Resultado esperado

| | Antes | Depois |
|---|---|---|
| Regras com `{glue: "*"}` | 25 | 5 (só as de infra Glue) |
| Regras com `{athena: "*"}` | 5 | 0 — gate é `requires_facts` |
| Regras com `{iceberg: ">=1.0.0"}` | 5 | 0 — era gate de Glue disfarçado |
| Áreas que somem num runtime sem flags | 6 de 9 | 1 — só `SF-GLUE`, e é o correto |
| Curinga filtra | nada | exige presença da chave |
| Regras avaliadas num runtime EMR-like | 44, com 5 em silêncio | 43, com as 5 **em `skipped`, com motivo** |
| `SF-GLUE-002` sem `aws_glue_job` | some dos dois lados | aparece em `skipped` |
| Skills chamando `judge` sem runtime | várias | nenhuma |

A 5b nasce sobre escopo que diz a verdade.
