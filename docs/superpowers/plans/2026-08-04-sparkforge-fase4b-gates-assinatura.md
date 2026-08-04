# SparkForge Fase 4b — gates fail-closed e assinatura: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o case deixa de avançar de fase com gate não satisfeito quando o operador pede rigor, e o relatório passa a carregar prova de que corresponde à evidência e ao catálogo que o produziram.

**Architecture:** o gate vive em `store.set_phase`, único ponto de passagem entre fases. O produtor de cada gate é declarado no `routing.yaml` — sem produtor declarado, o gate segue advisory mesmo sob rigor. A assinatura é hash de correspondência, sem chave e sem segredo.

**Tech Stack:** Python stdlib (`hashlib`), YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-04-sparkforge-fase4b-gates-assinatura-design.md`](../specs/2026-08-04-sparkforge-fase4b-gates-assinatura-design.md) — §6 tem os dez critérios, §8 os dois desvios medidos antes de começar.

---

## Fatos do ambiente verificados antes de escrever este plano

```
store.py:23  PHASES  intake inventory facts diagnosis hypothesis experiment validation report
store.py:34  GATES   baseline_captured dominant_bottleneck_identified
                     functional_validation_defined flows_mapped        <- QUATRO
store.py:71  new_case  "gates": dict.fromkeys(GATES, False)
store.py:121 set_phase  valida contra PHASES, faz deepcopy, seta e devolve
store.py:129 set_gate   valida contra GATES

routing.yaml  blocked_by so em ROUTE-012 [baseline_captured]
                        e ROUTE-015 [functional_validation_defined]
resume.py:213 imprime "bloqueado por (advisory)"
cli.py:386-387 --gate / --gate-value       _core.py:1641 store.set_gate
_core.py:1626  case_update(repo, phase, gate, gate_value, skill, now, outcome)
templates/performance-report.md  54 linhas, secoes numeradas, sem bloco de assinatura
```

**A consequência que decide a Task 1:** as fases do case são as **oito** acima —
`remediation` **não existe**, e o exemplo do D-4 do spec usa esse nome. Onde o
gate morde é na entrada de `experiment` e de `validation`, e a Task 1 mede qual,
em vez de herdar o nome errado.

> **Medido na Task 1, e diferente do que esta linha supunha:** `experiment` não
> serve para `baseline_captured` — `bench.run_delta` exige o lado `--after`, que
> só existe depois de `experiment`, então o gate seria insatisfazível no momento
> em que morde. E há um terceiro ponto que esta linha não previa: `hypothesis`,
> para `flows_mapped`. Ver a tabela do Step 3 da Task 1.

**A consequência que decide a Task 2:** `case update --gate X --gate-value true`
já permite virar qualquer gate. Sob rigor ele é **ignorado** (desvio D-4b-2 do
spec) — senão virar a flag seria override sem motivo e sem registro.

---

## Task 1: classificar os quatro gates, e medir onde cada um morde

Antes de qualquer código. O critério da §1 do spec — *gate só pode ser
fail-closed se tiver produtor declarado* — precisa ser aplicado aos **quatro**
nomes, e o spec só classificou dois.

**Files:** nenhum ainda. Esta task produz **medição e decisão**, escritas no plano.

- [x] **Step 1: Para cada gate, responda com evidência**

Vocabulário medido: **102 kinds** em 17 extratores de `sparkforge/facts/`
(`EMITTED_KINDS` de cada módulo, lido por import, não por grep). A pergunta
feita a cada gate foi *qual desses 102 kinds, se presente, prova o gate* — e
duas vezes a resposta honesta foi **nenhum**.

| Gate | Kind que o prova | Evidência de que prova (ou de que não prova) |
|---|---|---|
| `baseline_captured` | `bench.run_delta` | `benchmark.py:80`. Medido: `build_benchmark([], [])` devolve **só** `bench.unresolved` — o kind exige medida presente **dos dois lados**, então ele não pode ser fabricado por um lado vazio. É o único kind do vocabulário que afirma comparação entre execuções |
| `dominant_bottleneck_identified` | **nenhum** | Nenhum dos 102 kinds afirma dominância. Dominância é ordenação entre candidatos, e todo extrator emite medida de **um** sujeito por vez, por construção (`engine._condition_candidates` lê um fact por vez). O que se aproxima é um **Finding** — e Finding não é Fact: ele é o julgamento do catálogo, mora em `findings_index`, não em `facts_index`, e `set_phase` recebe kinds de fact. Além disso `findings_index.count > 0` diria "há achados", nunca "este domina" |
| `functional_validation_defined` | **nenhum** | Ver o quase-produtor rejeitado abaixo. O gate é sobre a validação **da mudança** (contagem, schema, chaves, agregados comparados antes/depois), e o artefato disso — o resultado de consultas que alguém roda — não existe no motor. É a Fase 4c, como a §2 do spec registrou |
| `flows_mapped` | `callgraph.reachable_spark_work` | `call_graph.py:45`. O kind é emitido **por entrypoint**, com `attrs.entrypoint`, `attrs.work_kind`, `attrs.via` e `min_depth` (`call_graph.py:356-390`) — que é literalmente "o DAG de cada fluxo, separado", a coisa que a ROUTE-003 exige antes de diagnosticar |

**Comandos, conferidos em `sparkforge --help` e nos subcomandos, não de memória:**

| Gate | Comando que produz o kind |
|---|---|
| `baseline_captured` | `sparkforge benchmark --before <facts_antes.json> --after <facts_depois.json> --out .sparkforge/facts_bench.json` (flags `--before/--after/--out` verificadas em `benchmark --help`) |
| `flows_mapped` | `sparkforge analyze call-graph --facts .sparkforge/facts.json --out .sparkforge/facts_callgraph.json` (flag `--facts` verificada em `analyze call-graph --help`; a entrada é o `--out` de `analyze pyspark`) |

**Dois kinds foram medidos e REJEITADOS como produtor.** Registrados porque cada
um passaria numa leitura rápida, e o gate que eles satisfariam seria um gate que
mente:

- **`callgraph.summary` para `flows_mapped`.** Medido:
  `build_call_graph([], path_hint="x.py")` devolve `['callgraph.summary']` — o
  kind é emitido **incondicionalmente** (`call_graph.py:430`), inclusive sobre
  entrada vazia. Um gate satisfeito por ele destravaria rodando `analyze
  call-graph` num arquivo de facts vazio. `callgraph.reachable_spark_work` não
  tem essa saída: ele só existe se algum entrypoint alcança trabalho Spark.
- **`dq.check` para `functional_validation_defined`.** É o quase-produtor, e a
  §1 do spec teria dito "nenhum" sem tê-lo olhado. Ele prova que **o job**
  valida o dado dele em execução (PyDeequ, Great Expectations, check artesanal),
  ancorado numa linha do `.py` (`data_quality.py:875`). Isso é verdade **antes e
  depois** da mudança, e continua verdade se a otimização quebrou a semântica —
  ele não compara nada entre duas execuções. Aceitá-lo trocaria a pergunta do
  gate por uma pergunta vizinha e mais fácil, que é a forma de falha que este
  projeto existe para não cometer. Fica advisory.

- [x] **Step 2: Meça em que transição o gate morde**

```
PHASES  intake inventory facts diagnosis hypothesis experiment validation report
```

`remediation` não existe, confirmado. Três regras saíram da medição, e **nenhuma
das três é ordem alfabética nem posição na tupla**:

**R1 — o gate não pode morder numa fase onde a rota que o destrava ainda opera.**
`routing.yaml` declara `phase_in` em toda rota, e isso é evidência da intenção
original. ROUTE-012 (`blocked_by: [baseline_captured]`) opera em
`[diagnosis, hypothesis]`; ROUTE-003 (`gates.flows_mapped, equals: false`) opera
em `[inventory, diagnosis]`. Se o gate bloqueasse a entrada de uma fase onde a
própria rota que manda destravá-lo ainda casa, a rota viraria letra morta — a
mesma classe de defeito que o comentário da AGENT-008 (`routing.yaml:247-256`)
diz, com todas as letras, que este catálogo não aceita. Logo o gate morde na
entrada da fase **seguinte à última do `phase_in` da sua rota**.

**R2 — a fase guardada precisa ser uma fase em que o fact produtor já pode
existir.** Aqui a medição corrige a linha 34 deste plano, que supunha
`experiment` como candidata para `baseline_captured`. `bench.run_delta` exige
`--before` **e** `--after`, e o `--after` só existe depois de rodar o job
mudado — ou seja, depois de `experiment`. Um gate satisfeito por
`bench.run_delta` guardando a entrada de `experiment` seria **insatisfazível no
momento em que morde**: o impasse da §5.5 da Fase 0 reencenado, só que com
produtor. Por R2 ele desce para `validation`.

**R3 — `guards_phases` é lista, porque `set_phase` não impõe ordem.**
`store.py:121-128` valida apenas pertinência a `PHASES`; nada impede
`experiment → report`. Um gate declarado numa fase só seria contornado pulando
para a seguinte. A lista é o sufixo de `PHASES` a partir da primeira fase
guardada, escrita por extenso no dado — não derivada em Python.

Aplicando as três, pela pergunta que cada fase responde:

| Gate | Primeira fase guardada | Por quê |
|---|---|---|
| `baseline_captured` | `validation` | R1 dá `experiment`; R2 empurra para `validation`. E a justificativa pela pergunta bate: `validation` responde *"a mudança entregou o que prometeu e preservou a semântica?"* — entrar nela sem delta computado é validar um ganho que ninguém mediu. R3 estende para `[validation, report]`, que é exatamente o `phase_in` da ROUTE-015: as duas fases do fechamento já são tratadas como par no catálogo |
| `flows_mapped` | `hypothesis` | R1 dá `hypothesis` (ROUTE-003 ainda opera em `diagnosis`). A pergunta de `hypothesis` é *"o que eu proponho mudar, e o que prevejo?"* — com fluxo full e incremental não separados, a hipótese não tem sujeito: ela fala de "o job" quando existem dois caminhos com DAGs diferentes, e vira intestável. R3 estende para `[hypothesis, experiment, validation, report]` |

Resposta ao "se depender do gate": **depende**, e por isso o mapeamento é
**dado**, em `routing.yaml`, ao lado do produtor — nunca `if` em Python.

- [x] **Step 3: Escreva a decisão no plano**

### O contrato das Tasks 2 e 3

| Gate | Fact produtor | Comando que destrava | Fases que guarda | Regime |
|---|---|---|---|---|
| `baseline_captured` | `bench.run_delta` | `sparkforge benchmark --before <facts_antes.json> --after <facts_depois.json> --out .sparkforge/facts_bench.json` | `validation`, `report` | **fail-closed** |
| `flows_mapped` | `callgraph.reachable_spark_work` | `sparkforge analyze call-graph --facts .sparkforge/facts.json --out .sparkforge/facts_callgraph.json` | `hypothesis`, `experiment`, `validation`, `report` | **fail-closed** |
| `dominant_bottleneck_identified` | — | — | nenhuma | **advisory**: dominância é ordenação entre candidatos, e nenhum dos 102 kinds a afirma; o que se aproxima é Finding, que não é Fact |
| `functional_validation_defined` | — | — | nenhuma | **advisory**: sem produtor até a Fase 4c. `dq.check` foi medido e rejeitado — prova validação **no job**, não validação **da mudança** |

Bloco a escrever no `routing.yaml` (Task 2, Step 1). Os quatro aparecem: gate
ausente do bloco é ambíguo entre "esqueceram" e "advisory de propósito".

```yaml
gates:
  baseline_captured:
    satisfied_by: bench.run_delta
    produced_by: "sparkforge benchmark --before <facts_antes.json> --after <facts_depois.json> --out .sparkforge/facts_bench.json"
    guards_phases: [validation, report]
  flows_mapped:
    satisfied_by: callgraph.reachable_spark_work
    produced_by: "sparkforge analyze call-graph --facts .sparkforge/facts.json --out .sparkforge/facts_callgraph.json"
    guards_phases: [hypothesis, experiment, validation, report]
  dominant_bottleneck_identified:
    # SEM satisfied_by: dominancia e ordenacao entre candidatos, e nenhum dos
    # 102 kinds do vocabulario a afirma. O que se aproxima e um Finding, que
    # nao e Fact -- mora em findings_index e nao chega a `set_phase`.
    advisory_reason: "nenhum fact prova dominancia; o julgamento e do catalogo, nao da evidencia"
  functional_validation_defined:
    # SEM satisfied_by: nenhum extrator emite fact que prove isto ate a Fase 4c.
    # Endurece-lo agora e o impasse que a secao 5.5 da Fase 0 recusou.
    # `dq.check` foi medido e REJEITADO: prova validacao dentro do job, que e
    # verdade antes e depois da mudanca e nao compara duas execucoes.
    advisory_reason: "sem produtor ate a Fase 4c"
```

**Três armadilhas para a Task 2, que saíram desta medição:**

1. `PHASE_GUARDADA` = `"validation"` e `PHASE_DO_GATE_SEM_PRODUTOR` = `"report"`
   **não servem como estão**: `report` também é guardada por `baseline_captured`.
   O teste `test_gate_sem_produtor_declarado_nunca_bloqueia` precisa passar
   `fact_kinds={"bench.run_delta"}` — senão ele passa pelo motivo errado, que é
   `baseline_captured` bloqueando, e provaria o oposto do que afirma. Para
   `flows_mapped`, a fase limpa é `"hypothesis"`: nenhum outro gate a guarda.
2. A checagem é por **presença de kind**, não por conteúdo de fact: `set_phase`
   recebe `fact_kinds`, um conjunto de strings. Isso prova que a análise rodou,
   nunca que ela cobriu todo `scope.entrypoints` nem que o benchmark é do job
   certo. Limitação aceita e registrada: a alternativa exigiria passar facts a
   `set_phase`, o que puxaria o índice inteiro para dentro do store. É a mesma
   fronteira que `bench.run_delta` já tem.
3. Corpus sem trabalho Spark alcançável não produz `callgraph.reachable_spark_work`
   — a saída é o override com motivo do D-4, e é para isso que ele existe.

- [x] **Step 4: Commit**

---

## Task 2: o gate em `set_phase`

**Files:**
- Modify: `sparkforge/case/store.py`, `rules/catalog/routing.yaml`, `tests/test_case_store.py`

- [x] **Step 1: O produtor no `routing.yaml`**

Bloco novo, no topo, ao lado das rotas — a decisão vira dado, como o roteamento de coordenador virou na Fase 4:

```yaml
gates:
  baseline_captured:
    satisfied_by: bench.run_delta
    produced_by: "sparkforge benchmark --before <facts_antes> --after <facts_depois> --out .sparkforge/facts_bench.json"
    guards_phase: <o que a Task 1 mediu>
  functional_validation_defined:
    # SEM satisfied_by: nenhum extrator emite fact que prove isto ate a Fase 4c.
    # Endurece-lo agora e o impasse que a secao 5.5 da Fase 0 recusou.
    advisory_reason: "sem produtor ate a Fase 4c"
```

Os quatro gates aparecem, inclusive os que ficam advisory — gate ausente do bloco é ambíguo entre "esqueceram" e "é advisory de propósito".

> **Escrito: o bloco real é o do Step 3 da Task 1**, não este esboço — `guards_phases`
> é **lista** (R3), e os **quatro** gates estão lá. `guards_phase` no singular acima
> é anterior à medição.

- [x] **Step 2: O teste que falha**

```python
def test_gate_com_produtor_bloqueia_a_transicao_sob_rigor():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    with pytest.raises(store.CaseError) as exc:
        store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())
    assert "baseline_captured" in str(exc.value)
    assert "sparkforge benchmark" in str(exc.value)


def test_sem_rigor_a_transicao_passa_como_hoje():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    assert store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())["phase"] == PHASE_GUARDADA


def test_o_fact_produtor_satisfaz_o_gate():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    novo = store.set_phase(case, PHASE_GUARDADA, fact_kinds={"bench.run_delta"})
    assert novo["phase"] == PHASE_GUARDADA


def test_gate_sem_produtor_declarado_nunca_bloqueia():
    """O criterio da secao 1 do spec, travado: functional_validation_defined nao
    tem `satisfied_by`, entao nem sob rigor ele impede a transicao."""
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    novo = store.set_phase(case, PHASE_DO_GATE_SEM_PRODUTOR, fact_kinds=set())
    assert novo["phase"] == PHASE_DO_GATE_SEM_PRODUTOR


def test_o_booleano_manual_nao_destrava_sob_rigor():
    """Desvio D-4b-2: `case update --gate X --gate-value true` seria override sem
    motivo e sem registro."""
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    case = store.set_gate(case, "baseline_captured", True)
    with pytest.raises(store.CaseError):
        store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())
```

Substitua `PHASE_GUARDADA` e `PHASE_DO_GATE_SEM_PRODUTOR` pelo que a Task 1 mediu.

- [x] **Step 3: Rode e veja falhar**

Run: `python -m pytest tests/test_case_store.py -k gate -v`
Expected: FAIL — `set_phase() got an unexpected keyword argument 'fact_kinds'`

- [x] **Step 4: Implemente**

`set_phase(case, phase, fact_kinds=None)`. Parâmetro **opcional**: `set_phase` é chamado de dentro do `_core` e de testes, e a assinatura antiga precisa continuar valendo — sem `fact_kinds`, o comportamento é o de hoje.

A checagem só acontece quando `case.get("strict_gates")` é verdadeiro **e** o gate tem `satisfied_by` no `routing.yaml`. A mensagem nomeia a fase pedida, o gate, o fact que faltou e o comando de `produced_by` — o D-5 do spec, e o teste assere **conteúdo**, porque a Fase 4a mediu que mensagem inacionável passa no CI.

- [x] **Step 5: Rode e commite**

---

## Task 3: rigor na abertura, e override com motivo

**Files:**
- Modify: `sparkforge/case/store.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `sparkforge/case/resume.py`, `tests/`

- [x] **Step 1: `strict_gates` no case**

`new_case` ganha o parâmetro, default `False`, e a chave entra no dicionário. Case gravado por versão anterior não tem a chave — `case.get("strict_gates")` responde `None`, que é falsy, e o comportamento antigo se preserva sem migração. **Confira se `SCHEMA_VERSION` precisa subir**: se houver teste que valide o conjunto exato de chaves do case, ele decide, e a resposta vai no relatório.

> **Medido: `SCHEMA_VERSION` fica em 1.** Nenhum teste valida o conjunto **exato**
> de chaves do case — `test_has_required_top_level_keys` afirma `key in case`,
> que é subconjunto, e `load_case` só compara `schema_version`. Não há fixture
> de `case.yaml` gravado em disco em `fixtures/`, `evals/` nem `examples/`. As
> duas chaves novas (`strict_gates`, `gate_overrides`) são aditivas e a ausência
> delas significa exatamente o comportamento antigo, então subir a versão só
> recusaria case em andamento sem ganhar nada.

- [x] **Step 2: `case open --strict-gates`**

CLI, `_core.case_open` e a tool MCP, na mesma passada — deixar o MCP para trás recria a assimetria que a Fase 5b corrigiu na flag `--emr`.

> **As três listas manuais de `test_adapters_tools.py` não mudam nesta task**, e
> isso foi medido, não suposto: elas enumeram *tools* (`set(TOOLS)`, os
> `openWorldHint`, os não-`readOnly`), e a Task 3 acrescenta **parâmetro** a tool
> existente, nunca tool nova. Quem paga a conta delas é a Task 5. No lugar
> entrou `TestOsControlesDeGateChegamAosTresAdaptadores`
> (`tests/test_capability_parity.py`), que casa flag da CLI, propriedade do
> `inputSchema` e parâmetro de `_core` para os quatro controles novos — a
> simetria vira teste mecânico em vez de disciplina.

- [x] **Step 3: O override, e o teste primeiro**

```python
def test_override_sem_motivo_e_recusado():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    with pytest.raises(store.CaseError) as exc:
        store.override_gate(case, "baseline_captured", reason="")
    assert "motivo" in str(exc.value).lower()


def test_override_com_motivo_fica_gravado_e_destrava():
    case = store.new_case("c1", "2026-08-04T00:00:00Z", {}, repo=".")
    case["strict_gates"] = True
    case = store.override_gate(case, "baseline_captured", reason="job descontinuado")
    registro = case["gate_overrides"][0]
    assert registro["gate"] == "baseline_captured"
    assert registro["reason"] == "job descontinuado"
    assert store.set_phase(case, PHASE_GUARDADA, fact_kinds=set())["phase"] == PHASE_GUARDADA
```

`gate_overrides` é lista, não dicionário: dois overrides do mesmo gate em momentos diferentes são dois fatos, e sobrescrever apagaria o primeiro motivo.

> **Desvio D-4b-6 — o esboço acima passaria pelo motivo errado, de novo.** É o
> D-4b-3 reencenado: `validation` é guardada pelos **dois** gates com produtor,
> então overridar só `baseline_captured` e chamar `set_phase(..., fact_kinds=set())`
> continua bloqueando, por `flows_mapped`. O teste escrito cobre um gate com
> override e o outro com evidência (`fact_kinds={KIND_FLOWS}`), e mais um teste
> novo — `test_override_de_um_gate_nao_destrava_o_outro` — trava que o override é
> por gate, e não um interruptor geral.

- [x] **Step 4: `case update --override-gate --reason`**

Nos três adaptadores. `--override-gate` sem `--reason` sai com `exit_code=2` e mensagem que diz o que falta.

> **Desvio D-4b-5 — sem `--facts` em `case update`, rigor não teria chave.** O
> plano descreveu o que **tranca** e o que **passa por cima**, e não descreveu
> por onde entra a evidência que **destrava**. Medido: `set_phase` recebe
> `fact_kinds`, e `_core.case_update` chamava `store.set_phase(case, phase)` sem
> nada. A outra fonte imaginável, `case["facts_index"]["by_kind"]`, é **sempre
> vazia**: `store.set_index` não tem chamador fora do próprio store — nenhum
> verbo da CLI ou tool MCP a preenche. Ou seja, `--strict-gates` entregaria um
> modo em que **nenhuma** transição guardada passa por evidência, e a única saída
> seria o override — que viraria burocracia obrigatória em vez de escapatória, e
> esvaziaria o `--reason` do D-4 exatamente como o `--gate-value true` esvaziaria.
> Entrou `--facts` (repetível) em `case update`, `facts_path` na tool, e
> `_fact_kinds_for_gates` no `_core`, na mesma forma que `judge --facts` e
> `case open --facts` já têm.
>
> **Desvio D-4b-7 — `--reason` sem `--override-gate` é recusado.** O plano não
> disse o que fazer, e o default silencioso seria ignorar o motivo. Ignorar em
> silêncio é a família de defeito desta fase inteira: o operador acha que
> registrou e não registrou. Sai `exit_code=2` nomeando o comando completo.

- [x] **Step 5: `resume` mostra o override**

`resume.py:213` hoje imprime `bloqueado por (advisory)`. Quando o case tem `strict_gates`, a palavra `advisory` está **errada** — e quando há override, a retomada precisa mostrar gate, motivo e quando. Quem retoma numa outra máquina tem que saber que alguém passou por cima, sem abrir o YAML.

> **Desvio D-4b-8 — trocar `advisory` por `estrito` seria trocar uma palavra
> falsa por outra.** Medido: `blocked_by` sai de `router.next_step`, que calcula
> `[g for g in blocked_by if not gates.get(g)]` — o **booleano** do case. Sob
> rigor esse booleano não bloqueia (o fact pode estar presente e a transição
> passar) nem destrava (D-4b-2). Chamar a lista de "estrito" afirmaria que ela
> decide, e ela não decide. O rótulo escrito diz o que é verdade: *"strict_gates
> ligado: quem decide a transição é a presença do fact produtor, não este
> booleano"*. Sem rigor, `advisory` continua correto e continua lá.
>
> **`HANDOFF_SECTIONS` foi de 10 para 11**: a seção `Overrides de gate` entra
> depois de `Gates`, e a seção `Gates` ganha uma linha de rigor quando o case é
> estrito. O teste que contava dez agora conta onze — número medido, não copiado.

- [x] **Step 6: Rode a suíte inteira e commite**

Nenhum case existente pode quebrar: é o critério 5 do spec.

Medido: **3369 passed / 5 skipped** (era 3329/5), `ruff check .` limpo,
`len(TOOLS) == 34` (inalterado — a Task 3 não cria tool).

---

## Task 4: a assinatura de correspondência

**Files:**
- Create: `sparkforge/findings/signature.py`, `tests/test_findings_signature.py`
- ~~Modify: `sparkforge/adapters/{_core,cli,tools}.py`, `templates/performance-report.md`~~
  — é a Task 5. A Task 4 é só o módulo de cálculo, e nada fora dele foi tocado.

- [x] **Step 1: O teste que falha**

```python
from sparkforge.findings.signature import compute_signature, normalize_body


def test_reformatar_o_corpo_nao_muda_a_assinatura():
    a = compute_signature(body="## Titulo\n\ntexto\n", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    b = compute_signature(body="## Titulo\n\n\ntexto  \n\n", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    assert a == b


def test_editar_o_conteudo_muda_a_assinatura():
    a = compute_signature(body="ganho de 40%", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    b = compute_signature(body="ganho de 60%", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    assert a != b


def test_a_ordem_da_evidencia_nao_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=["f_aaa111", "f_bbb222"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=["f_bbb222", "f_aaa111"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    assert a == b


def test_trocar_a_evidencia_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=["f_aaa111"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=["f_ccc333"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    assert a != b


def test_catalogo_diferente_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=[], rule_ids=[], catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=[], rule_ids=[], catalog_version=2, schema_version=1)
    assert a != b
```

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_findings_signature.py -v`
Expected: FAIL — `ModuleNotFoundError`

Medido: `ImportError: cannot import name 'signature' from 'sparkforge.findings'`,
1 error na coleta (com o módulo removido da árvore, para provar o estado vermelho).

- [x] **Step 3: Implemente**

```python
"""Assinatura de CORRESPONDENCIA de um relatorio.

Prova que o texto foi derivado daquela evidencia com aquele catalogo. NAO prova
autoria: nao ha chave, nao ha segredo, e qualquer um com os mesmos facts produz
a mesma assinatura. O bloco escrito no relatorio diz isso, porque bloco que
sugere autoridade mente por omissao.

O corpo entra no hash de proposito (D-7 do spec): sem ele alguem reescreve o
texto inteiro mantendo a assinatura valida, e ela garantiria menos do que o
leitor supoe.
"""
from __future__ import annotations

import hashlib
import json
import re

SIGNATURE_VERSION = 1

_WS = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n{3,}")


def normalize_body(body: str) -> str:
    """Absorve reformatacao, e SO ela.

    Espaco horizontal repetido, espaco no fim da linha, CRLF, e mais de uma
    linha em branco seguida. Nao absorve pontuacao, ordem, numero nem palavra --
    o que ela absorve esta escrito aqui e tem teste dos dois lados.
    """
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(_WS.sub(" ", line).rstrip() for line in text.split("\n"))
    return _BLANKS.sub("\n\n", text).strip()


def compute_signature(
    body: str,
    fact_ids: list[str],
    rule_ids: list[str],
    catalog_version: int,
    schema_version: int,
) -> str:
    payload = {
        "signature_version": SIGNATURE_VERSION,
        "body": normalize_body(body),
        "fact_ids": sorted(set(fact_ids)),
        "rule_ids": sorted(set(rule_ids)),
        "catalog_version": catalog_version,
        "schema_version": schema_version,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sig_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

`SIGNATURE_VERSION` entra no hash: mudar a normalização no futuro sem mudar a versão faria assinaturas antigas parecerem inválidas sem que nada tivesse sido adulterado.

> **Desvio D-4b-9 — o esboço inventava uma segunda serialização canônica.** Medido:
> `sparkforge/findings/models.py:21` já tem `_canonical` (`sort_keys=True`,
> `separators=(",", ":")`, `ensure_ascii=True`), e ela é a base do `Fact.id`. O
> esboço chamava `json.dumps(..., ensure_ascii=False)` — uma segunda definição de
> "canônico", com política de escape diferente, no mesmo pacote. Duas formas de
> canonizar são duas oportunidades de divergir, e o dia em que divergirem a
> assinatura de um relatório com acento muda sem que nada tenha sido adulterado.
> `signature.py` importa `_canonical` de `models` e comenta o porquê do import
> privado. O local do módulo (`sparkforge/findings/`) foi confirmado, não copiado:
> `findings/` já é onde mora o gate de saída (`validate.py`) e o vocabulário que a
> assinatura cobre (`fact_id`, `rule_id`, `catalog_version`, `schema_version`);
> não existe pacote `report/` no repositório, e `templates/performance-report.md`
> é dado, não código.
>
> **Desvio D-4b-10 — 16 hex era escolha, e a medição diz 64.** O repositório já
> separa os dois usos de digest: `Fact.id` trunca sha1 em 6 hex e a própria
> docstring registra que "resistência a colisão é irrelevante para esse fim"
> (content-addressing), enquanto `CollectEntry.sha256` guarda os 64 hex porque é
> **integridade** (`^[0-9a-f]{64}$`, `collect/base.py:69`). Assinatura existe para
> resistir a uma edição deliberada: é integridade, e fica do lado dos 64 hex.
> Truncar em 16 (64 bits) reintroduziria em silêncio o "força criptográfica é
> moot" no único valor desta fase em que ela é exatamente o que importa, e não
> compra nada — o bloco tem uma linha e quem compara é o `verify`. O prefixo
> `sig_` fica (é a convenção `f_` do repositório, e torna a assinatura
> grepável e auto-descritiva); é decisão registrada, não medição. **A Task 5 deve
> escrever no bloco `sig_` + 64 hex**, não os 16 do exemplo daquela task. O módulo
> exporta `SIGNATURE_RE` para que a Task 5 não invente uma segunda verdade de forma.
>
> **Desvio D-4b-11 — a normalização do esboço absorvia indentação, e indentação
> não é reformatação.** `_WS.sub(" ", line)` colapsa *todo* espaço horizontal
> repetido, inclusive o recuo do início da linha. Em Markdown, quatro espaços de
> recuo são bloco de código e um espaço é prosa, e o recuo também decide o nível
> de um item de lista: com o esboço, trocar `    df.collect()` por
> ` df.collect()` mudaria o que o leitor lê e a assinatura continuaria válida —
> exatamente a "adulteração que passa" que o D-7 do spec manda evitar. A
> normalização entregue preserva o recuo e colapsa só o espaço repetido **depois**
> do primeiro caractere não-branco. Os cinco itens absorvidos estão listados na
> docstring e cada um tem teste dos dois lados; `test_indentacao_invalida` e
> `test_indentacao_de_item_de_lista_invalida` travam o lado que o esboço deixaria
> passar.

- [x] **Step 4: Rode e commite**

Medido: **25 passed** em `tests/test_findings_signature.py` (os 5 literais do plano
mais 20 de cobertura dos dois lados), suíte **3394 passed / 5 skipped**
(era 3369/5), `ruff check .` limpo.

---

## Task 5: `report sign` e `report verify`

**Files:**
- Modify: `sparkforge/adapters/{_core,cli,tools}.py`, `templates/performance-report.md`, `parity.yaml`, `manifest.json`, `tests/`
- Create: `tests/test_adapters_report_signature.py`

- [x] **Step 1: O bloco no relatório**

No fim, delimitado, e **fora** do que a própria assinatura cobre — ele não pode entrar no hash que ele mesmo carrega. O corpo assinado é tudo que vem antes do delimitador.

```markdown
<!-- sparkforge:signature -->
- assinatura: sig_a1b2c3d4e5f60718
- evidência: 12 facts, 4 regras
- catálogo: catalog_version 1, schema_version 1
- verifique com: `sparkforge report verify --report <este arquivo> --facts <facts.json>`

Esta assinatura prova **correspondência**, não autoria: que este texto foi
derivado desta evidência com este catálogo. Ela não diz quem o emitiu, e qualquer
pessoa com os mesmos facts produz a mesma assinatura.
<!-- /sparkforge:signature -->
```

> **O bloco escrito difere deste esboço em quatro pontos, todos medidos.** A
> assinatura é `sig_` + **64 hex** (D-4b-10, e o módulo exporta `SIGNATURE_RE`
> para que a forma não tenha segunda verdade); `--facts` virou `--findings`
> (D-4b-12); as linhas de metadado usam **chave ASCII** (`catalog_version:`,
> `schema_version:`, em vez de `catálogo:`) porque são as linhas que o `verify`
> parseia e acento em regex de parsing é superfície de divergência de console; e
> o bloco declara os **`fact_ids` e `rule_ids`** (D-4b-14), sem os quais o Step 2
> não consegue isolar as três partes.

- [x] **Step 2: `report verify` diz o que divergiu**

Não "inválido". Recompute as três partes separadamente e diga qual não bate:
evidência, catálogo ou corpo. É o critério 8 do spec, e o teste cobre os três
casos, mais o de bloco ausente e o de bloco malformado.

> **Desvio D-4b-14 — "recompute as três partes separadamente" não fecha sozinho.**
> Medido ao escrever: as três partes de **agora** saem do arquivo de findings e
> do corpo atual, mas a assinatura gravada é um hash único das três partes
> **de então** — não há como recomputá-las em separado a partir dela. Com só o
> hash, evidência trocada e corpo editado produzem a mesma resposta ("não bate"),
> que é exatamente o que o critério 8 recusa. A isolação vem de o bloco declarar
> o que foi assinado: `evidence` compara os ids declarados com os do arquivo de
> findings; `catalog` idem para as duas versões; `body` recomputa
> `compute_signature` do corpo atual segurando evidência e catálogo nos valores
> **declarados** — se fecha, o corpo está intacto ainda que os findings de hoje
> sejam outros. O bloco mora fora do hash e portanto é editável: por isso o
> veredito `valid` nunca sai dele, sai das três checagens juntas, e a atribuição
> de `body` diz as duas leituras possíveis ("o corpo foi editado, ou o próprio
> bloco foi") em vez de escolher uma que ela não pode provar.
>
> **Desvio D-4b-15 — texto DEPOIS do bloco é recusado, não ignorado.** O plano
> definiu o corpo como "tudo que vem antes do delimitador" e não disse o que
> fazer com o que vem depois do fechamento. Ignorar deixaria a porta que a
> assinatura existe para fechar: um parágrafo apendado ao fim do arquivo que
> nenhuma assinatura cobre e que o leitor lê como parte do relatório verificado.
> `sign` recusa com `exit_code=2`; `verify` devolve `malformed_block`.

- [x] **Step 3: Os dois verbos nos três adaptadores**

`report sign --report <md> --facts <json>` e `report verify --report <md> --facts <json>`, na CLI, no `_core` e como tool MCP. Mais `parity.yaml` e `manifest.json`, e as **três** listas manuais de `tests/test_adapters_tools.py` que a Fase 5c mediu.

> **Desvio D-4b-12 — a flag é `--findings`, e não `--facts`.** Medido antes de
> escolher: o arquivo de **facts** carrega `id`, `kind`, `subject`, `measures` e
> `provenance` — e **nenhum** `rule_id`, `catalog_version` ou `schema_version`.
> Os quatro campos não-corpo da assinatura estão todos no arquivo de
> **findings**: `evidence` é a lista de `fact_id` citados
> (`models.Finding.evidence`), `rule_id` é a regra que disparou, e as duas
> versões viajam em cada achado (`Finding.to_dict`, alimentadas por
> `loader.py:212` a partir do cabeçalho do arquivo de catálogo — a resposta à
> pergunta "está em cada regra ou no cabeçalho" é: no cabeçalho, propagada para
> cada regra e daí para cada achado). Com `--facts` o verbo precisaria de **dois**
> arquivos para responder três dos quatro campos; com `--findings` responde os
> quatro com um só, e nenhum terceiro formato é inventado.
>
> **Desvio D-4b-13 — as listas manuais são QUATRO, não três.** As três previstas
> mudaram (`set(TOOLS)`, o branch de `_real_output_for`, `FAILABLE`), e a quarta
> apareceu porque `sign` **escreve**: `test_only_case_writers_are_not_read_only`
> afirmava `writers == {case_open, case_update}`. Um `sign` que só devolvesse o
> bloco para alguém colar seria a versão decorativa da capacidade — e a colagem
> manual é exatamente onde o corpo assinado deixaria de ser o corpo escrito.
> `sparkforge_report_sign` é `_WRITE_IDEMPOTENT` (assinar duas vezes devolve o
> arquivo byte-idêntico, travado por teste); `report_verify` fica `_READ_ONLY`.
>
> **Desvio D-4b-16 — dois inputs impossíveis de assinar honestamente, recusados.**
> Nenhum dos dois estava no plano, e o default silencioso de cada um seria uma
> assinatura que afirma mais do que sabe. (a) `findings` **vazio**: a assinatura
> cobriria só o corpo, e o leitor a leria como prova de que o texto vem dos
> facts — recusa mandando rodar `judge`. (b) `catalog_version` (ou
> `schema_version`) **divergente entre achados**: `compute_signature` recebe um
> inteiro, e escolher um dos valores faria a assinatura afirmar um catálogo que
> não foi o único usado. Recusa nomeando os valores.
>
> **Desvio D-4b-17 — a fronteira "docs é a Task 6" não cobre `agents/`.**
> `tests/test_agent_coverage.py::test_no_tool_is_orphan` reprova tool que nenhum
> coordenador alcança, e as duas tools novas caíram nele na mesma passada
> (`2 de 36`). Não é documentação adiável: é o invariante que existe para impedir
> capacidade inerte, e adiá-lo deixaria a suíte vermelha entre os dois commits.
> Entrou o passo 3 de `agents/executors/sf-synthesizer.md` — o executor que
> **escreve** o relatório —, espelhado por `scripts/sync_skills.py` para
> `.claude/`, `.agents/` e `.github/`. `AGENT_PROTOCOL.md`, `STATUS.md`,
> `README.md` e `AGENTS.md` continuam na Task 6.

- [x] **Step 4: Rode e commite**

Medido: **43 passed** em `tests/test_adapters_report_signature.py`, suíte
**3443 passed / 5 skipped** (era 3394/5), `ruff check .` limpo,
`len(TOOLS) == 36` (era 34: `report_sign` e `report_verify`).

Os 49 testes a mais decompõem-se assim, e o número não é o do arquivo novo: 43
de `test_adapters_report_signature.py`, mais 4 de `FAILABLE` (duas tools novas ×
dois testes parametrizados) e 2 de `TestRealOutputValidatesAgainstItsOwnSchema`
(parametrizado por `sorted(TOOLS)`). As três listas manuais rendem teste sozinhas
— é para isso que elas existem.

---

## Task 6: fechamento

**Files:**
- Modify: `docs/superpowers/STATUS.md`, `README.md`, `AGENTS.md`, `AGENT_PROTOCOL.md`

- [ ] **Step 1: Meça**

```bash
python -m pytest -q 2>&1 | tail -2
python -c "from sparkforge.adapters.tools import TOOLS; print('tools', len(TOOLS))"
ruff check .
```

- [ ] **Step 2: `AGENT_PROTOCOL.md`**

A regra que fala de gates precisa dizer que sob `--strict-gates` o booleano manual não destrava, e que override exige motivo. É o documento que o executor lê antes de agir — a Fase 4a mediu que a quebra de contrato do `benchmark_ref` não tinha chegado nele.

- [ ] **Step 3: `STATUS.md`, `README.md`, `AGENTS.md`**

Números medidos. Seção "Fase 4b" no formato das anteriores: o defeito de partida (a razão da Fase 0 deixando de valer para gate com produtor), o que entrou, e o que **não** entrou — a validação funcional, que é a 4c. Na §16, marcar dois dos três itens de rigor como fechados.

- [ ] **Step 4: Suíte verde, ruff limpo, commit**
