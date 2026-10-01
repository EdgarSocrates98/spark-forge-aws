# Timeout Intelligence — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separar os quatro mecanismos que o operador chama de "timeout" — relógio do Glue, broadcast, rede e heartbeat — e registrar em regra que aumentar o número não é o conserto quando há sintoma ao lado.

**Architecture:** Uma fonte nova no event log (`spark.stage.failure`, a razão da stage que falhou), um módulo que deriva a categoria a partir de facts (no precedente de `run_cost.py`, que deriva de fact e não de caminho), e duas regras no catálogo. Nenhum verbo novo.

**Tech Stack:** Python 3, `pytest`. Spec: [`../specs/2026-08-29-timeout-intelligence-design.md`](../specs/2026-08-29-timeout-intelligence-design.md).

**Convenções do repositório que valem em toda tarefa:**

- Lint ruff `E,F,I,UP,B,S`, linha máxima 100 (config do `pyproject.toml`).
- Todo comando com prefixo `rtk`. Commit em português, Conventional Commits, via `rtk git commit -F <arquivo>`. **Mensagem via heredoc para um arquivo**, nunca `printf` de string longa.
- Não rode a suíte inteira sem alvo (17 minutos), exceto onde a tarefa pedir.
- Não faça `git add` dos untracked pré-existentes na raiz.
- Módulo golden novo **tem** que chamar `validate_fact`.
- Regra nova **tem** que ser alcançada por golden que dispara: é o gate de `tests/test_fixtures_kind_coverage.py`.

**APIs reais que este plano consome** (medidas em 2026-08-28):

```
spark.executor.lost      attrs {reason, heap_oom_in_log}
                         subject {type: job_run, symbol: <executor id>}
spark.conf_effective     attrs {key, value, app_id, source_event}  -- UM FACT POR CHAVE
glue.job_run             measures {execution_time_s, number_of_workers, timeout_min, dpu_seconds}
                         attrs {state, worker_type, glue_version, autoscaling, dpu_source}
spark.stage.spill        measures {memory_spill_bytes, disk_spill_bytes, input_bytes}
spark.stage.task_duration measures {p50_ms, p95_ms, task_count}
spark.stage.gc           measures {gc_time_ms, task_time_ms}

sparkforge.facts.secrets.redact(key, value) -> (value, redacted: bool)
sparkforge.findings.models.Fact, sort_facts
sparkforge.rules.loader.load_catalog()  -- 130 regras hoje, nenhuma com "timeout"
```

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/timeout_diagnosis.py` | `spark.timeout.diagnosis` e `spark.timeout.unresolved` |
| `tests/test_facts_timeout_diagnosis.py` | Testes do módulo |
| `tests/test_fixtures_golden_timeout.py` | Módulo golden do domínio novo |
| `fixtures/timeout/` | Oito cenários |
| `rules/catalog/timeout.yaml` | `SF-TIMEOUT-001` e `SF-TIMEOUT-002` |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/facts/event_log.py` | `spark.stage.failure` a partir de `Stage Info["Failure Reason"]` |
| `tests/test_facts_event_log.py` | O fact novo |
| `tests/test_harness_untrusted.py` | `timeout_diagnosis` em `_derivados_de_facts` |
| `tests/test_fixtures_kind_coverage.py`, `tests/test_rules_catalog_reachability.py` | Registrar o extrator nas DUAS listas |
| `rules/catalog/routing.yaml` | A área nova, se o roteamento a exigir |
| `README.md`, `docs/superpowers/STATUS.md` | Os números medidos e a fase |

---

## Task 1: A razão da stage que falhou

**Files:**
- Modify: `sparkforge/facts/event_log.py`
- Test: `tests/test_facts_event_log.py`

- [ ] **Step 1: Escrever o teste que falha**

Um event log sintético com `SparkListenerStageCompleted` cujo `Stage Info` traz
`"Failure Reason": "Could not execute broadcast in 300 secs..."`, e três
asserções: o fact `spark.stage.failure` existe, `attrs.reason` traz a frase
literal, e o `subject` é o stage. Mais um teste negativo: stage sem
`Failure Reason` **não** produz o fact — ausência de falha não é falha vazia.

Um terceiro teste prova a redação: `Failure Reason` contendo
`jdbc:postgresql://user:senha@host` sai redigida, pelo mesmo `redact` que
`spark.conf_effective` usa. Razão de falha carrega credencial com a mesma
facilidade que configuração carrega, e `facts.json` é commitado.

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_event_log.py -k failure -v
```

- [ ] **Step 3: Implementar**

No handler de `SparkListenerStageCompleted`, que hoje lê `Stage ID`,
`Stage Name` e `Number of Tasks`. Acrescente `EMITTED_KINDS` com o kind novo.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_event_log.py -q
```

- [ ] **Step 5: Commit**

Mensagem: `feat(facts): a razao da stage que falhou entra no barramento`

---

## Task 2: As quatro categorias, e a precedência declarada

**Files:**
- Create: `sparkforge/facts/timeout_diagnosis.py`
- Test: `tests/test_facts_timeout_diagnosis.py`

- [ ] **Step 1: Escrever o teste que falha**

Uma classe por categoria, cada uma com a evidência mínima que a decide:

| Teste | Entrada | Espera |
|---|---|---|
| `test_glue_timeout_state_alone_is_wall_clock` | `glue.job_run` com `state: TIMEOUT` | `category == "wall_clock"`, `basis == "glue_job_run_state"` |
| `test_executor_heartbeat_phrase_decides_heartbeat` | `spark.executor.lost` com "Executor heartbeat timed out after 130000 ms" | `category == "heartbeat"` |
| `test_broadcast_phrase_decides_broadcast` | `spark.stage.failure` com "Could not execute broadcast in 300 secs" | `category == "broadcast"` |
| `test_rpc_phrase_decides_network` | `spark.stage.failure` com "Futures timed out after [120 seconds]" | `category == "network"` |
| `test_evidence_text_is_the_literal_phrase` | qualquer uma acima | `attrs.evidence_text` contém a frase, não uma paráfrase |

E o teste que prova a precedência:

```python
def test_precedence_keeps_what_it_did_not_choose(self):
    """Heartbeat vence wall-clock, e o preterido continua legivel.

    Escolher em silencio seria escolher pelo operador: o run estourou o
    relogio do Glue PORQUE o executor morreu, e quem le precisa dos dois.
    """
    facts = [_run_em_timeout(), _executor_perdido_por_heartbeat()]
    diag = _diagnosticos(extract_timeout_diagnosis(facts, "facts.json"))[0]

    assert diag.attrs["category"] == "heartbeat"
    assert diag.attrs["also_seen"] == ["wall_clock"]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_timeout_diagnosis.py -v
```

Esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Implementar**

`sparkforge/facts/timeout_diagnosis.py`, no molde de `run_cost.py`: recebe um
pool de facts e um `path`, devolve `sort_facts(...)`. `EXTRACTOR_ID`,
`EMITTED_KINDS`, e a precedência como constante nomeada:

```python
# Do mais especifico para o mais generico. O generico e CONSEQUENCIA do
# especifico sempre que os dois aparecem: o run estourou o relogio do Glue
# porque o executor morreu, e nao ao contrario.
_PRECEDENCIA = ("heartbeat", "network", "broadcast", "wall_clock")
```

Os padrões de frase ficam numa tabela `{categoria: (regex, basis)}`, com a
frase de referência em comentário ao lado de cada um — quem for mexer precisa
ver o texto que o Spark escreve, não só o regex.

- [ ] **Step 4: Rodar e ver passar**

- [ ] **Step 5: Commit**

Mensagem: `feat(facts): as quatro categorias de timeout, e a precedencia entre elas`

---

## Task 3: As três recusas, cada uma com o seu nome

**Files:**
- Modify: `sparkforge/facts/timeout_diagnosis.py`
- Test: `tests/test_facts_timeout_diagnosis.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
class TestRecusas:
    def test_no_signal_produces_no_diagnosis_and_a_named_gap(self):
        facts = [_run_bem_sucedido()]
        saida = extract_timeout_diagnosis(facts, "facts.json")

        assert not [f for f in saida if f.kind == "spark.timeout.diagnosis"]
        assert [f.attrs["reason"] for f in saida] == ["no_timeout_evidence"]

    def test_timeout_state_without_log_says_so(self):
        """`wall_clock` e a resposta honesta, e a lacuna diz o que falta."""
        saida = extract_timeout_diagnosis([_run_em_timeout()], "facts.json")

        assert [f for f in saida if f.kind == "spark.timeout.diagnosis"]
        lacunas = [f for f in saida if f.kind == "spark.timeout.unresolved"]
        assert lacunas[0].attrs["reason"] == "state_without_log"
        assert "collect event-log" in lacunas[0].attrs["detail"]

    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact
        ...
```

- [ ] **Step 2–4: falhar, implementar, passar**

- [ ] **Step 5: Commit**

Mensagem: `feat(facts): as tres recusas do diagnostico de timeout`

---

## Task 4: As duas regras

**Files:**
- Create: `rules/catalog/timeout.yaml`
- Test: `tests/test_rules_*` conforme o gate exigir

- [ ] **Step 1: Escrever o teste que falha**

`SF-TIMEOUT-001` — dispara com diagnóstico **e** sintoma; **não** dispara com
diagnóstico sozinho. Os dois casos são teste, e o negativo é o que importa: o
§31 do documento de origem diz por escrito que aumentar timeout pode ser a
decisão certa quando o job está saudável.

`SF-TIMEOUT-002` — dispara com `heartbeatInterval >= network.timeout`; **não**
dispara quando só uma das duas chaves foi observada.

- [ ] **Step 2: Rodar e ver falhar**

- [ ] **Step 3: Implementar**

Siga a forma de uma regra existente que lê `spark.conf_effective` (há
precedente em `spark-ui.yaml`). Campos obrigatórios: `evidence`, `validation`,
`rollback`, `sources`. `runtime_scope` fica `{}` — a relação entre as duas
propriedades não depende de versão de Glue.

Atenção às unidades: `heartbeatInterval` e `network.timeout` aceitam sufixo
(`10s`, `120s`, `1min`). Comparar string seria comparar texto. A normalização
para segundos entra com teste próprio, incluindo o valor sem sufixo, que o
Spark lê como segundos nessas duas chaves.

- [ ] **Step 4: Rodar e ver passar**

- [ ] **Step 5: Commit**

Mensagem: `feat(rules): aumentar timeout nao e conserto, e a relacao heartbeat-network`

---

## Task 5: Fixtures e as garantias do corpus

**Files:**
- Create: `fixtures/timeout/` (oito cenários), `tests/test_fixtures_golden_timeout.py`
- Modify: `tests/test_fixtures_kind_coverage.py`, `tests/test_rules_catalog_reachability.py`, `tests/test_harness_untrusted.py`

- [ ] **Step 1: Registrar o extrator nas DUAS listas, e em `_derivados_de_facts`**

As duas primeiras são manuais e duplicadas — o próprio arquivo avisa que
esquecer uma não quebra nada, e é por isso que ela é esquecida. A terceira é a
medida de snippet, que é fail-closed: módulo com `EMITTED_KINDS` que a medida
não sabe invocar não pode entrar na conta como "sem snippet" por omissão.
`timeout_diagnosis` deriva de fact, e portanto vai junto de `run_cost`.

- [ ] **Step 2: Os oito cenários**

| Cenário | Prova |
|---|---|
| `wall_clock_sem_event_log` | estado `TIMEOUT` sozinho, e a lacuna nomeada |
| `heartbeat_perdido` | a frase do executor removido decide |
| `broadcast_estourado` | `broadcastTimeout` excedido |
| `network_futures_timeout` | timeout de RPC |
| `heartbeat_vence_wall_clock` | precedência escolhe, `also_seen` preserva |
| `timeout_com_spill_e_skew` | `SF-TIMEOUT-001` dispara |
| `heartbeat_maior_que_network` | `SF-TIMEOUT-002` dispara |
| `timeout_sem_evidencia` | `no_timeout_evidence`, e nenhuma regra dispara |

- [ ] **Step 3: O módulo golden e as quatro garantias**

```python
class TestOQueOCorpusInteiroGarante:
    def test_every_diagnosis_carries_basis_and_the_literal_phrase(self):
        """Categoria sem a frase que a produziu e opiniao."""

    def test_no_diagnosis_without_a_timeout_signal(self):
        """Diagnostico sobre run saudavel seria categoria inventada."""

    def test_nothing_recommends_a_new_timeout_value(self):
        """O criterio 17 e outro subprojeto, e ele entra com a procedencia
        por propriedade que o 36 pede -- ou nao entra."""

    def test_every_emitted_fact_validates(self):
        ...
```

- [ ] **Step 4: Rodar**

```bash
rtk pytest tests/test_fixtures_golden_timeout.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py tests/test_harness_untrusted.py -q
```

Grave os goldens com a saída real e **leia** cada um antes de commitar.

- [ ] **Step 5: Commit**

Mensagem: `test(fixtures): oito cenarios do diagnostico de timeout`

---

## Task 6: Documentação e os gates

- [ ] **Step 1: Suíte inteira**

```bash
rtk pytest -q
```

- [ ] **Step 2: README** — os números de extratores e kinds **medidos**, nos **dois** lugares que os citam. Contagem esperada, a conferir medindo: 26 extratores, 155 kinds.

- [ ] **Step 3: STATUS** — a fase, e a **linha da auditoria** do critério 11 e do item P0 passando de ABERTO para ENTREGUE. Registre as decisões (a categoria é fact no precedente de `heap_oom_in_log`; a precedência é declarada e o preterido fica legível; a relação entre as duas propriedades é conferível e o valor isolado não é) e o que ficou de fora (recomendar valor novo de timeout).

- [ ] **Step 4: Gate de números**

```bash
rtk python scripts/check_vnext_claims.py
rtk pytest tests/test_docs_coverage.py -q
```

Itere até `0 divergencia(s).`

- [ ] **Step 5: Commit e prova final**

Mensagem: `docs: o diagnostico de timeout, e o criterio 11 fechado`

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §1.1 os quatro mecanismos | 2 |
| §3.1 a categoria é fact | 2 |
| §3.2 precedência declarada | 2 |
| §3.3 as três recusas | 3 |
| §3.4 a relação conferível | 4 |
| §3.5 o §31 como regra | 4 |
| §4.0 `spark.stage.failure` | 1 |
| §4.1 `spark.timeout.diagnosis` | 2 |
| §4.2 `spark.timeout.unresolved` | 3 |
| §4.3 as duas regras | 4 |
| §7.1 domínio de fixture | 5 |
| §7.2 as garantias do corpus | 5 |
| §8 documentação | 6 |
| §9 critérios de aceite 1–7 | 2, 3, 4, 5 |
