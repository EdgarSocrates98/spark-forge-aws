# Stacktrace intelligence — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fazer o erro entrar no motor: estruturar a exceção que já está coletada, transformar o matcher de juiz paralelo em extrator, e mover o julgamento para o catálogo.

**Architecture:** Três camadas. `facts/exception.py` deriva `spark.exception` de `spark.stage.failure` (molde de `bridge.py`, derivação pura sobre facts). O matcher passa a consumir esse fact e emitir `error.signature_match` — só o fato de ter casado. Regras `SF-ERR-*` consomem os dois e julgam.

**Tech Stack:** Python 3.11+, dataclasses frozen, YAML (catálogo), JSON (assinaturas), pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-stacktrace-intelligence-design.md`

---

## Estrutura de arquivos

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/exception.py` | deriva `spark.exception` e `spark.exception.frame` |
| `sparkforge/collect/cloudwatch_logs.py` | coletor de log group |
| `rules/catalog/errors.yaml` | regras `SF-ERR-*` |
| `tests/test_facts_exception.py` | testes do extrator |
| `tests/test_errors_signature_fact.py` | testes do matcher-como-extrator |
| `fixtures/exception/*` | corpus, par positivo/negativo |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/errors/matcher.py` | consome fact, emite fact, perde `confidence`/`fixes` |
| `sparkforge/adapters/tools.py` | tool do coletor (69 → 70) |
| `sparkforge/adapters/_core.py` | verbo de coleta |
| `rules/catalog/routing.yaml` | rota da área `SF-ERR` |
| `agents/*.md` | coordenador que declara a área |

---

## Task 1: `spark.exception` — estruturar o texto que já existe — ENTREGUE (2026-09-08, `deb08f2`)

**Files:**
- Create: `sparkforge/facts/exception.py`
- Test: `tests/test_facts_exception.py`

- [x] **Step 1: Medir o artefato real antes de escrever**

```bash
python -c "
import json,pathlib
for p in pathlib.Path('fixtures').rglob('expected/facts.json'):
    d=json.loads(p.read_text(encoding='utf-8'))
    d=d if isinstance(d,list) else d.get('facts',[])
    for f in d:
        if f.get('kind')=='spark.stage.failure':
            print(p.parent.parent.name, '|', (f.get('attrs') or {}).get('reason','')[:160])
"
```

Se o corpus não tiver `spark.stage.failure`, **diga no relatório** — a fixture
da Tarefa 4 terá de criá-lo, e o extrator nasce sem corpus real para exercitar.

- [x] **Step 2: Escrever o teste que falha**

```python
"""`spark.exception` estrutura o texto que `spark.stage.failure` ja carrega.

O artefato nao falta: `attrs.reason` E a excecao com a pilha, ja redigida por
`secrets.redact`. O que faltava era estrutura.
"""

from __future__ import annotations

from sparkforge.facts.exception import build_exceptions
from sparkforge.findings.models import Fact

_PILHA = (
    "org.apache.spark.SparkException: Job aborted due to stage failure\n"
    "\tat org.apache.spark.scheduler.DAGScheduler.failJobAndIndependentStages(DAGScheduler.scala:2668)\n"
    "\tat org.apache.spark.scheduler.DAGScheduler.abortStage(DAGScheduler.scala:2604)\n"
    "Caused by: java.lang.NoSuchMethodError: scala.collection.immutable.List.map\n"
    "\tat com.exemplo.Job.run(Job.scala:42)\n"
)


def _falha(reason: str) -> Fact:
    return Fact(
        kind="spark.stage.failure",
        subject={"stage_id": 3, "stage_name": "map at Job.scala:42"},
        measures={},
        attrs={"reason": reason},
    )


class TestExcecaoEstruturada:
    def test_classe_e_cabeca_da_mensagem(self):
        facts = build_exceptions([_falha(_PILHA)])
        exc = [f for f in facts if f.kind == "spark.exception"]
        assert len(exc) == 1
        assert exc[0].attrs["exception_class"] == "org.apache.spark.SparkException"
        assert "Job aborted" in exc[0].attrs["message_head"]

    def test_encadeamento_na_ordem(self):
        facts = build_exceptions([_falha(_PILHA)])
        exc = [f for f in facts if f.kind == "spark.exception"][0]
        assert exc.attrs["is_chained"] is True
        assert exc.attrs["caused_by"] == ["java.lang.NoSuchMethodError"]

    def test_frames_do_topo(self):
        facts = build_exceptions([_falha(_PILHA)])
        frames = [f for f in facts if f.kind == "spark.exception.frame"]
        assert frames, "a pilha tem frames"
        topo = frames[0]
        assert topo.attrs["class"].startswith("org.apache.spark.scheduler.DAGScheduler")
        assert topo.attrs["file"] == "DAGScheduler.scala"
        assert topo.attrs["line"] == 2668


class TestRecusaNomeada:
    def test_texto_sem_forma_de_stacktrace(self):
        facts = build_exceptions([_falha("Container killed by YARN")])
        un = [f for f in facts if f.kind == "spark.exception.unresolved"]
        assert len(un) == 1
        assert un[0].attrs["reason"] == "sem_forma_de_stacktrace"
        assert not [f for f in facts if f.kind == "spark.exception"]

    def test_texto_redigido_nao_vira_excecao(self):
        f = _falha("jdbc:postgresql://host/db?password=[REDACTED]")
        f = Fact(kind=f.kind, subject=f.subject, measures=f.measures,
                 attrs={**f.attrs, "redacted": True})
        facts = build_exceptions([f])
        un = [x for x in facts if x.kind == "spark.exception.unresolved"]
        assert un and un[0].attrs["reason"] == "reason_redigida"

    def test_sem_falha_no_case_nao_emite_nada(self):
        assert build_exceptions([]) == []
```

- [x] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_facts_exception.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [x] **Step 4: Escrever o extrator**

`sparkforge/facts/exception.py`, no molde de `bridge.py` — **derivação pura
sobre facts, sem ler artefato**:

```python
"""`spark.exception` -- a excecao que `spark.stage.failure` ja carrega.

Derivacao pura sobre a uniao dos facts, no molde de `bridge.py`. Nao le
artefato: `attrs.reason` do `spark.stage.failure` E o campo `Failure Reason` do
event log, que num job Spark e a excecao com a pilha, ja redigida por
`secrets.redact` em `event_log.py`.

A redacao vem ANTES do parse, e o parse nao a desfaz. Texto redigido vira
recusa nomeada, nunca excecao inventada.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EMITTED_KINDS = frozenset(
    {"spark.exception", "spark.exception.frame", "spark.exception.unresolved"}
)

# `com.pacote.Classe: mensagem` no inicio de linha. O `:` e obrigatorio -- sem
# ele o texto e mensagem livre, nao excecao, e forcar o parse produziria uma
# classe que ninguem lancou.
_CABECA = re.compile(r"^([\w$]+(?:\.[\w$]+)+)\s*:\s*(.*)$", re.MULTILINE)
_CAUSED = re.compile(r"^Caused by:\s*([\w$]+(?:\.[\w$]+)+)", re.MULTILINE)
_FRAME = re.compile(r"^\s+at\s+([\w$.]+)\.([\w$<>]+)\(([^:)]+):(\d+)\)", re.MULTILINE)

_TOPO = 5


def build_exceptions(facts: Sequence[Fact], top_n: int = _TOPO) -> list[Fact]:
    saida: list[Fact] = []
    for fact in facts:
        if fact.kind != "spark.stage.failure":
            continue
        subject = dict(fact.subject)
        reason = str((fact.attrs or {}).get("reason") or "")

        if (fact.attrs or {}).get("redacted"):
            saida.append(_unresolved(subject, "reason_redigida"))
            continue

        cabeca = _CABECA.search(reason)
        if not cabeca:
            saida.append(_unresolved(subject, "sem_forma_de_stacktrace"))
            continue

        causas = _CAUSED.findall(reason)
        saida.append(
            Fact(
                kind="spark.exception",
                subject=subject,
                measures={},
                attrs={
                    "exception_class": cabeca.group(1),
                    "message_head": cabeca.group(2).strip()[:200],
                    "is_chained": bool(causas),
                    "caused_by": causas,
                },
            )
        )
        for ordem, (cls, metodo, arquivo, linha) in enumerate(
            _FRAME.findall(reason)[:top_n]
        ):
            saida.append(
                Fact(
                    kind="spark.exception.frame",
                    subject={**subject, "frame": ordem},
                    measures={},
                    attrs={
                        "class": cls,
                        "method": metodo,
                        "file": arquivo,
                        "line": int(linha),
                    },
                )
            )
    return sort_facts(saida)


def _unresolved(subject: dict[str, Any], reason: str) -> Fact:
    return Fact(
        kind="spark.exception.unresolved",
        subject=subject,
        measures={},
        attrs={"reason": reason},
    )
```

**Confirme a assinatura de `sort_facts` e de `Fact`** antes de rodar — as reais
mandam.

- [x] **Step 5: Rodar**

Run: `python -m pytest tests/test_facts_exception.py -v`
Expected: PASS nos seis.

- [x] **Step 6: Registrar nas listas manuais**

Extrator novo entra em **duas listas manuais de teste** e na medida de snippet.
Encontre-as:

```bash
TOKENSAVE_DISABLE_GREP_HOOK=1 grep -rln "bridge" tests/test_facts_*.py tests/test_harness_*.py | head
```

- [x] **Step 7: Commit**

```bash
git add sparkforge/facts/exception.py tests/test_facts_exception.py
git commit -F <arquivo>
```

---

## Task 2: o matcher vira extrator — ENTREGUE (2026-09-08, `d07a161`)

**Files:**
- Modify: `sparkforge/errors/matcher.py`
- Test: `tests/test_errors_signature_fact.py`

- [x] **Step 1: Escrever o teste que falha**

```python
"""O matcher emite FATO, nao juizo.

Ele constata que a excecao casa com uma assinatura. O que fazer a respeito e
regra do catalogo, nao dele -- e por isso `confidence`, `fixes` e
`likely_causes` somem daqui.
"""

from __future__ import annotations

from sparkforge.errors.matcher import build_signature_matches
from sparkforge.findings.models import Fact


def _exc(classe: str) -> Fact:
    return Fact(
        kind="spark.exception",
        subject={"stage_id": 1},
        measures={},
        attrs={"exception_class": classe, "message_head": "x",
               "is_chained": False, "caused_by": []},
    )


class TestMatcherEmiteFato:
    def test_casa_por_classe_de_excecao(self):
        facts = build_signature_matches([_exc("java.lang.NoSuchMethodError")])
        m = [f for f in facts if f.kind == "error.signature_match"]
        assert m, "NoSuchMethodError tem assinatura no catalogo"
        assert m[0].attrs["signature_id"].startswith("ERR-")
        assert m[0].attrs["matched_on"] == "exception_class"

    def test_nao_carrega_juizo_nem_confidence(self):
        facts = build_signature_matches([_exc("java.lang.NoSuchMethodError")])
        for f in facts:
            assert "confidence" not in f.attrs
            assert "fixes" not in f.attrs
            assert "likely_causes" not in f.attrs
            assert "diagnostic_steps" not in f.attrs

    def test_sem_assinatura_sai_unresolved(self):
        facts = build_signature_matches([_exc("com.exemplo.ErroInedito")])
        un = [f for f in facts if f.kind == "error.signature.unresolved"]
        assert un and un[0].attrs["reason"] == "nenhuma_assinatura_casou"

    def test_sem_excecao_no_case_nao_emite_nada(self):
        assert build_signature_matches([]) == []
```

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_errors_signature_fact.py -v`
Expected: FAIL com `ImportError: cannot import name 'build_signature_matches'`

- [x] **Step 3: Reescrever o matcher**

Acrescentar `EMITTED_KINDS = frozenset({"error.signature_match", "error.signature.unresolved"})`
e `build_signature_matches(facts) -> list[Fact]`, que:

- consome `spark.exception` (não texto cru);
- casa `attrs.exception_class` e `attrs.caused_by` contra `signature` das
  assinaturas de `knowledge/errors/`;
- emite `error.signature_match` com `signature_id` e `matched_on`;
- **não** carrega `likely_causes`, `fixes`, `diagnostic_steps` nem `confidence`.

**`match_log` e `ErrorMatchResult` continuam existindo** — a CLI
`sparkforge forge errors match` os usa e não é escopo desta tarefa. Mas
acrescente comentário sobre `confidence=0.98` dizendo que ele é constante
literal, que a regra 28 o fecha, e que o caminho de fact não o carrega.

- [x] **Step 4: Rodar**

Run: `python -m pytest tests/test_errors_signature_fact.py tests/test_error_matcher.py -v`
Expected: PASS, sem regressão no teste antigo.

- [x] **Step 5: Commit**

---

## Task 3: regras `SF-ERR-*` — ENTREGUE (2026-09-08)

**Files:**
- Create: `rules/catalog/errors.yaml`
- Modify: `rules/catalog/routing.yaml`, `agents/sf-runtime-specialist.md`
- Test: `tests/test_rules_errors.py`

- [x] **Step 1: Ler as seis assinaturas**

```bash
for f in knowledge/errors/*/*.json; do echo "== $f"; python -c "
import json,sys; d=json.load(open('$f',encoding='utf-8'))
print(' id',d['id'],'| sig',d['signature'],'| evidence',d.get('evidence_required'))
"; done
```

- [x] **Step 2: Escrever UMA regra primeiro, e o teste dela**

`SF-ERR-001`, de `ERR-GLUE-002` (Scala 2.12 sob Glue 6.0), que é a que tem
`evidence_required` mais rico (`mig.jar_binary`, `tf.attribute`).

O teste que prova a integração está em
`tests/test_rules_errors.py::TestRegraExigeAEvidenciaDaAssinatura`. Duas
diferenças em relação ao esboço deste plano, e as duas são deliberadas:

- o `error.signature_match` **não é escrito à mão** — ele sai de
  `build_signature_matches` sobre um `spark.exception` construído no teste,
  lendo o catálogo real de `knowledge/errors/`. Um fact fabricado provaria que
  o YAML da regra casa com o YAML do teste; passar pelo matcher prova que a
  regra casa com o que o extrator REALMENTE emite;
- o esboço afirmava sobre `SF-ERR-002` no par de `ERR-GLUE-002`. O id certo é
  `SF-ERR-001` — `SF-ERR-002` é a regra de `ERR-GLUE-003`.

O teste declara `runtime={"glue": "6.0"}` de propósito: sem runtime as duas
regras são puladas por `runtime_scope`, e toda asserção de fronteira passaria
por SKIP — verde sem nunca ter olhado para a regra.

- [x] **Step 3: ~~Migrar as outras cinco~~ — DESVIO, e o motivo é medido**

**Duas regras, não seis.** O campo `signature` das seis foi lido, e ele não é
da mesma natureza:

| id | `signature` | natureza |
|---|---|---|
| **ERR-GLUE-002** | `NoSuchMethodError` | **classe de exceção** |
| **ERR-GLUE-003** | `NoSuchFieldError` | **classe de exceção** |
| ERR-ATH-001 | `Cannot read unsupported version 3` | trecho de mensagem |
| ERR-GLUE-001 | `Container killed by YARN for exceeding memory limits` | trecho de mensagem |
| ERR-ICE-001 | `CommitFailedException: Commit failed: ...` | trecho de mensagem |
| ERR-LF-001 | `Insufficient Lake Formation permission(s) on` | trecho de mensagem |

`build_signature_matches` (Task 2) casa a assinatura contra
`attrs.exception_class` e `attrs.caused_by` — CLASSE, nunca texto corrido de
log. As quatro de mensagem **nunca produzem `error.signature_match` por este
caminho**, e regra escrita sobre elas hoje seria regra que não dispara nunca:
`requires_facts` satisfeito, `when` mudo, relatório limpo. O caminho delas é o
coletor de CloudWatch Logs da Task 5.

O motivo está escrito no cabeçalho de `rules/catalog/errors.yaml` e é
**medido por teste**, não afirmado de memória:
`tests/test_rules_errors.py::test_a_assinatura_sem_regra_e_trecho_de_mensagem_e_nao_casa_por_classe`
alimenta cada uma das quatro como cabeça de mensagem e confirma que ela cai em
`error.signature.unresolved`.

- [x] **Step 4: Rota e coordenador**

`AGENT-084` em `routing.yaml` (`findings_area: SF-ERR`) e `SF-ERR` em
`rule_areas` de `agents/sf-runtime-specialist.md`, que já declara `SF-SPARK4`
e `SF-MIG` e traz as skills `migrate-glue-6` e `spark4-compatibility` — as duas
regras novas são a metade `confirmed` do que `SF-SPARK4-004` já afirma de forma
estrutural.

- [x] **Step 5: Rodar os gates de catálogo**

```bash
python -m pytest tests/test_rules_loader.py tests/test_rules_action_field.py   tests/test_agent_coverage.py tests/test_rules_catalog_reachability.py -q
```

684 passando. `tests/test_fixtures_kind_coverage.py` fica **vermelho de
propósito** em dois testes — `test_every_rule_has_a_fixture_that_fires_it` e
`test_every_severity_branch_has_a_golden_that_produces_it` — porque as duas
regras novas ainda não têm golden. A fixture é a Task 4, e forçar o gate agora
trocaria uma lacuna nomeada por um verde que não mede nada.

- [x] **Step 6: Commit**

Catálogo: **149** regras, **114** executáveis. `STATUS.md` remedido em quatro
linhas (regras de diagnóstico, `runtime_scope` não-vazio, eixo de resultado no
`validation`, rotas determinísticas), e o gate de lastro em três ids
(`VNX-640`, `VNX-674`, `VNX-430`), relidos pela própria prova.

---

## Task 4: fixtures — ENTREGUE (2026-09-08, `33b7393`; testes reparados em `2e0f1eb`)

**Files:**
- Create: `fixtures/exception/*/`

- [x] **Step 1: Criar o corpus**

Um par por caminho: exceção simples, exceção encadeada, texto sem forma,
texto redigido, assinatura que casa, assinatura que não casa.

Siga a forma dominante: `input/`, `expected/facts.json`,
`expected/findings.json`, `meta.yaml` com `name`, `runtime` e `proves`.

- [x] **Step 2: Rodar o gate de fixture**

```bash
python -m pytest tests/test_fixtures_kind_coverage.py tests/test_fixtures_golden.py -q
```

- [x] **Step 3: Commit**

---

## Task 5: coletor de CloudWatch Logs — ENTREGUE (2026-09-09, `d35d5d4` e `2407005`)

**Files:**
- Create: `sparkforge/collect/cloudwatch_logs.py`
- Modify: `sparkforge/adapters/_core.py`, `sparkforge/adapters/tools.py`

- [x] **Step 1: Ler o coletor de métricas como molde**

`sparkforge/facts/cloudwatch.py` e `_core.collect_cloudwatch` (linha ~4370).
**Medido: ele lê só métricas (`CLOUDWATCH_METRICS`), nunca log group.**

- [x] **Step 2: Escrever o coletor**

Traz o que o event log não carrega: falha de driver antes do primeiro stage,
`Py4JJavaError` de código Python, OOM de container.

**Toda linha passa por `secrets.redact` antes de virar fact.** Log de driver
carrega credencial com a mesma facilidade que configuração.

Recusa nomeada: log group inexistente, sem permissão ou vazio →
`cloudwatch.logs.unresolved` com a razão. **Nunca lista vazia silenciosa.**

- [x] **Step 3: Tool e surface lock**

```bash
python scripts/check_surface_lock.py          # antes, anote os bytes
python scripts/check_surface_lock.py --update # depois
python -c "from sparkforge.adapters.tools import TOOLS; print(len(TOOLS))"  # 70
```

- [x] **Step 4: Commit** declarando o crescimento em bytes.

---

## Task 6: fechamento — ENTREGUE (2026-09-09)

- [x] **Step 1: Gates**

```bash
python scripts/check_vnext_claims.py
python scripts/check_status_numbers.py --strict
python scripts/check_surface_lock.py
python -m ruff check sparkforge scripts tests
python -m pytest tests/test_suite_batches.py -q
```

- [x] **Step 2: Lotes afetados**, um por vez.

- [x] **Step 3: Docs** — STATUS com os números medidos (fact kinds, tools 70,
      regras, fixtures), e o que a frente **não** entregou: seguem **6**
      assinaturas, não 24.

- [x] **Step 4: Commit**

---

## Auto-revisão contra o spec

| Seção do spec | Tarefa |
|---|---|
| §2.1 extrator de exceção | 1 |
| §2.2 matcher vira extrator, perde `confidence` | 2 |
| §2.3 julgamento no catálogo, `evidence_required` verificado | 3 |
| §2.4 coletor de CloudWatch Logs | 5 |
| §3 redação e as três recusas | 1 (duas), 5 (a terceira) |
| §4 o que fica de fora | nenhuma tarefa infere causa sem assinatura, cria score, ou amplia para 24 |
| §5 gates | 1 (listas manuais), 3 (rota, coordenador), 5 (surface lock), 6 |
| §6 testes | 1, 2, 3, 4 |

---

## Desvios medidos, registrados no fechamento (2026-09-09)

O plano foi executado inteiro, e em quatro pontos o escopo mudou **por medição**.
Nenhum deles foi reescrito acima para casar com o resultado: o degrau fica como
foi planejado, e o desvio é acréscimo.

### D-1 — a T3 entregou DUAS regras, não seis

Planejado: uma regra `SF-ERR-*` por assinatura, seis no total. Entregue:
**`SF-ERR-001` e `SF-ERR-002`**.

A medição está no Step 3 da própria Task 3 e é cobrada por teste. Das seis
assinaturas de `knowledge/errors/`, só **duas** — `NoSuchMethodError`
(`ERR-GLUE-002`) e `NoSuchFieldError` (`ERR-GLUE-003`) — são **classe de
exceção**; as outras quatro são trecho de mensagem de log.
`build_signature_matches` casava, na T2, contra `attrs.exception_class` e
`attrs.caused_by` — CLASSE, nunca texto corrido. Regra escrita sobre as quatro
naquele momento seria regra que nunca dispara: `requires_facts` satisfeito,
`when` mudo, relatório limpo.

### D-2 — o caminho das quatro abriu na T5, e ele NÃO virou regra

A T5 acrescentou `cloudwatch.log_event`, e `build_signature_matches` passou a
casar a mesma assinatura contra o TEXTO DA LINHA, com `matched_on: "log_line"`.
As quatro de mensagem produzem `error.signature_match` hoje
(`fixtures/cloudwatch_logs/quatro_assinaturas_de_log/`).

**Regra `SF-ERR` sobre elas continua não existindo, e é entrega própria.** Ter o
fact não é ter a regra: cada uma exige `evidence_required` próprio, `sources`,
`validation` e `rollback`, mais o par positivo/negativo de fixture — o mesmo
trabalho que `SF-ERR-001` e `SF-ERR-002` custaram.

#### D-2 FECHADA em 2026-09-09 — `SF-ERR-003` a `SF-ERR-006`

A entrega própria que este desvio nomeava aconteceu, e o degrau acima fica como
foi escrito: as quatro regras existem, e as SEIS assinaturas de
`knowledge/errors/` têm regra.

O que a entrega descobriu, e que este desvio não previa: **três das quatro
assinaturas declaram `evidence_required` cujos nomes não são kind deste motor**
— `pyspark.skew_join`, `eventlog.executor_oom`, `spark.plan.cartesian_product`,
`iceberg.commit_conflict`, `iceberg.concurrent_writer`,
`lakeformation.missing_grant` e `ram.unaccepted_share`, medidos contra os 195
kinds emitidos. Copiá-los para `requires_facts` produziria a mesma regra muda
que a D-1 recusou escrever. Cada regra declara o companheiro que EXISTE e diz no
`explanation` o que ele não prova, e um teste novo
(`test_o_companheiro_de_cada_regra_e_kind_que_o_motor_EMITE`) impede a próxima
de cair nisso.

Consequência de escopo, também medida: as quatro declaram `runtime_scope: {}` —
nenhuma tem fronteira de versão —, e por isso **a área `SF-ERR` deixou de sumir**
num runtime sem Glue. Duas declarações de sumiço caíram vermelhas e foram
corrigidas: `AREA_MAY_VANISH_WHEN` em `tests/test_rule_scope_by_nature.py` e
`AREA_FULLY_OUT_OF_SCOPE` em `tests/test_runtime_glue_versions.py`.

Detalhes e números em `STATUS.md`, seção *As seis assinaturas viram seis regras*.

### D-3 — as recusas do log são QUATRO, não três

O plano (Step 2 da Task 5) e a §3 do spec listavam três: log group inexistente,
sem permissão, vazio. A entrega separou **`sem_credencial`**, porque ali **a
requisição nunca saiu** — gravar `vazio` seria afirmar que o log estava vazio sem
nunca o ter consultado.

Desvio de forma junto: os quatro **não levantam exceção**. Viram `status` no
artefato, e o extrator os traduz em `cloudwatch.logs.unresolved`.
`CollectionFailed` ficou reservado ao que impede até a recusa de ser gravada
(paginação que não termina). O spec já carrega esta seção de desvio.

### D-4 — a Task 6 fechou com duas lacunas nomeadas em vez de fechadas

- **Não há verbo `analyze cloudwatch-logs`.** `extract_cloudwatch_logs_tree` é
  referenciado por `scripts/regen_fixtures.py` e mais nada: o extrator é
  alcançado pelo golden, não por tool. Entrega própria.
- **O parser não alcança `classe_no_meio_da_linha`** — a forma que o
  `DAGScheduler` escreve em toda falha de task repetida. Ela sai como
  `spark.exception.unresolved`, e `fixtures/exception/classe_no_meio_da_linha/`
  prende o comportamento ATUAL para que alargar o parser vire diff de golden. O
  caminho proposto é um SEGUNDO padrão, sem tocar a âncora `^` do primeiro.

  **FECHADA em 2026-09-09, e exatamente por esse caminho.**
  `_CABECA_APOS_EXECUTOR` lê a classe depois de `executor <algo>): `, prefixo
  literal do escalonador; `_CABECA` continua ancorada em `^` e tem precedência,
  e `attrs.parsed_by` diz por qual dos dois a exceção entrou. O golden da
  fixture é o diff que a mudança produziu — `unresolved` virou
  `spark.exception` com dois frames —, e um teste novo mede a outra metade:
  estruturar a exceção **não inventa assinatura**, e
  `error.signature.unresolved` continua saindo porque
  `java.lang.OutOfMemoryError` não casa nenhuma das seis.

### O que a Task 6 remediou fora do escopo original

Duas linhas de *Números correntes* do `STATUS.md` que a própria frente deixou
defasadas, ambas em `SEM_MEDIDA` e portanto invisíveis para
`check_status_numbers.py`:

| Linha | Publicava | É |
|---|---|---|
| Tools alcançáveis a partir de algum coordenador | 69 de 69 | **70 de 70**, zero órfã |
| Testes | 10168 coletados | **10462** coletados |

O número de **passantes** por lote **não** foi remedido: rodar os nove lotes um a
um não estava no escopo desta tarefa, e publicá-lo sem tê-los rodado seria número
sem produtor.
