---
sdd: 1
feature: SFN_TENTATIVA
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SFN_TENTATIVA/design.md
  sha256: "2b1c5a1dac4929640b309954ebb6f9ed47d153c1ceddac8259b03569f5ed4d26"
tasks:
  - id: T1
    files: [tests/test_sfn_history.py, sparkforge/facts/sfn_history.py, rules/catalog/sfn-history.yaml, fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json, docs/guia/usos/step-functions.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC1, AC2]
    test: {path: tests/test_sfn_history.py, name: test_redrive_sai_com_razao_propria_e_os_outros_dois_tipos_entram_calados}
  - id: T2
    files: [tests/test_sfn_history.py, sparkforge/facts/sfn_history.py, docs/guia/usos/step-functions.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC3, AC4]
    test: {path: tests/test_sfn_history.py, name: test_estado_homonimo_em_ramos_diferentes_sai_recusado_sem_indice}
  - id: T3
    files: [fixtures/sfn_history/execucao_com_redrive/meta.yaml, fixtures/sfn_history/parallel_estado_homonimo/meta.yaml, fixtures/sfn_history/retry_em_ramo_unico/meta.yaml, tests/test_fixtures_golden_sfn_history.py, docs/superpowers/STATUS.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC5, AC7]
    test: {path: tests/test_fixtures_golden_sfn_history.py, name: test_golden}
  - id: T4
    files: [knowledge/stepfunctions/execution-history.md, knowledge/offline-manifest.json, docs/surface.lock.json]
    covers: [AC6]
    test: {path: tests/test_surface_lock.py, name: "TestOLockBateComAMedida::test_the_knowledge_matches"}
---

# SFN_TENTATIVA — plano

> Branch `sdd/sfn-history`, com a feature `SFN_HISTORY` já fechada nesta árvore
> (`a228ec4e`). Todos os números deste plano foram **medidos aqui**, com o comando ao
> lado. **Publique o que o gate medir na hora, não o número escrito aqui** — se alguma
> linha divergir ao executar, a medida do gate é que vale.
>
> O precedente inteiro — extrator, área, corpus, golden e os registros — está em
> `docs/sdd/SFN_HISTORY/plan.md`, na mesma árvore. Esta feature **não** acrescenta kind,
> regra, tool, verbo, agente, skill nem documento de `knowledge/`: ela muda o
> comportamento de um extrator que já existe, acrescenta três fixtures ao corpus que já
> existe, e reescreve duas lacunas de um documento que já existe.

## O que esta feature faz, em duas frases

O extrator de histórico afirma hoje dois números que o arquivo não sustenta, e os dois
viram **recusa nomeada** (regra 20 do `CLAUDE.md`): a contagem de tentativas que
atravessa um **redrive**, e o `attempt_index` de **estados homônimos em ramos
concorrentes de um `Parallel`**. Nos dois casos a leitura do arquivo continua valendo —
o que sai é a afirmação que ela não sustenta.

## Regras de execução

- **Um comando por vez.** A suíte inteira num processo só não sobrevive; os lotes de
  `tests/test_suite_batches.py::LOTES` ficam para o fim, e nunca com edição na árvore ao
  mesmo tempo.
- **Edição por ferramenta (Edit/Write), nunca `sed -i`.** Fim de linha **LF**.
  `line-length = 100` (ruff, `pyproject.toml`) — vale para `sparkforge/` e para `tests/`.
- **Arquivo novo entra no índice (`git add`) antes dos testes que conferem a árvore
  versionada.** Nesta feature nenhum `.py` nasce; nascem doze arquivos de fixture
  (`.json` e `.yaml`) em T3, e eles entram no `git add` antes de rodar
  `tests/test_arvore_versionada.py`.
- **Golden só por `python scripts/regen_fixtures.py <nome> [<nome>...]`** — por nome é
  instantâneo. O regen **sem argumento** leva mais de 10 minutos e
  `python -m pytest tests/test_fixtures_golden*.py -q` leva ~39: os dois estouram o
  timeout de 2 minutos da ferramenta e **precisam ir para segundo plano**. Onde este
  plano os usa, ele diz isso na hora.
- **Não rode `python scripts/sync_skills.py` sem `--check`, nem
  `tests/test_agents_parity.py`, sem antes proteger `.claude/agents/README.md`** — mas
  confira: hoje esse arquivo **não existe** na árvore, e os dois gates passam assim. Esta
  feature não mexe em agente nem em skill, e **nenhuma tarefa abaixo os chama**.
- **Commit por tarefa**, com `git commit -F <arquivo no scratchpad>`, mensagem
  conventional em inglês. **Nunca heredoc dentro de `$(...)`** — é o que dispara o prompt
  de permissão. A mensagem termina com:

  ```text
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
  ```

- **Gate de lastro (`python scripts/check_vnext_claims.py`) antes de todo commit que
  muda bytes de `.py`** — aqui, T1, T2 e T3. Remedie **pela lista de ids da saída**, um
  id por vez, **nunca `--seed`** e nunca por varredura. Cada entrada tem `text`,
  `context` **e** `proof.expect.value`: trocar só o texto não fecha o gate.
  `docs/claims.lock.json` se regrava com
  `json.dumps(..., ensure_ascii=False, indent=2) + "\n"` e **sem** `sort_keys`. A prova
  de cada alegação roda por `shlex.split`, nunca `subprocess` com `shell=True`.
  `expect.value` é `int` em `kind: number` e em `kind: pattern`, e string em
  `kind: contains`.

## Medidas desta árvore, tiradas antes de começar

| medida | antes | depois | como foi medida |
|---|---|---|---|
| `len(_TIPOS_CONHECIDOS)` | **59** | **62** | `python -c "from sparkforge.facts.sfn_history import _TIPOS_CONHECIDOS; print(len(_TIPOS_CONHECIDOS))"` |
| Razões distintas de `sfn.unresolved` no módulo | **20** (15 do extrator, 5 da derivação) | **23** | as duas listas da docstring de `sparkforge/facts/sfn_history.py` |
| Fixtures em `fixtures/sfn_history/` | **11** | **14** | `ls fixtures/sfn_history \| wc -l` |
| Fixtures golden (`STATUS.md`) | **551** em **59** domínios | **554** em **59** domínios | `python scripts/check_status_numbers.py --strict` (hoje: `0 divergencia(s)`) |
| Domínios de `fixtures/` com fixture | **58** (+ `mcp_parity`, que não tem fixture) | **58** | glob de `fixtures/*/*/` |
| `knowledge.total_bytes` em `docs/surface.lock.json` | **532870** | **meça** (`check_surface_lock.py --update` imprime) | `python scripts/check_surface_lock.py` (hoje: `0 divergencia(s)`) |
| Documentos de `knowledge/` no `surface.lock` | **56** | **56** (nenhum novo) | idem |
| Arquivos `.py` que `iter_source_files` entrega | **774** | **774** (nenhum `.py` novo) | `VNX-640` em `docs/claims.lock.json` |
| Alegações em `docs/claims.lock.json` | **768** | **768** (nenhuma nova; algumas **mudam de valor**) | `python -c "import json;print(len(json.load(open('docs/claims.lock.json',encoding='utf-8'))['claims']))"` |
| Fact kinds distintos emitidos | inalterado | inalterado | nenhum kind novo: as três recusas novas são `attrs.reason` de `sfn.unresolved`, que já existe |
| Regras do catálogo | inalterado | inalterado | nenhuma regra nova; a `SF-SFNX-001` muda só de **prosa** |

Quatro medidas que decidem o desenho deste plano, e que ficam registradas aqui:

1. **Nenhum golden existente muda de comportamento.** Medido nesta árvore: nenhuma
   fixture de `fixtures/sfn_history/` usa `EvaluationFailed`, `ExecutionRedriven` ou
   `MapRunRedriven` (`evento_desconhecido` usa `VariableSetEventDetailsEntered`), e
   **nenhuma** tem mais de um `TaskStateEntered` por nome de estado — o máximo é 1, em
   todas as onze. Logo nem a lista de tipos nem o teste de ancestralidade mexem em
   golden existente.
2. **Um golden existente muda de TEXTO, e é o da regra.** `explanation` viaja dentro de
   cada `Finding`, e `SF-SFNX-001` aparece em **um só** golden do repositório:
   `fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json` (medido com
   `grep -rl SF-SFNX-001 fixtures/`). O D5 manda a prosa da regra entrar no **mesmo
   commit** da mudança de comportamento, então o regen daquela fixture é de T1.
3. **`retry_em_ramo_unico` nasce SEM ASL, de propósito.** Com um ASL de
   `MaxAttempts: 2` ela teria `tentativas_observadas == teto_declarado`, ou seja, uma
   segunda fixture exatamente na fronteira da `expr` da `SF-SFNX-001` — território de
   `tests/test_rules_threshold_mutation.py::FRONTEIRA_SEM_GOLDEN`, que é comparada por
   **igualdade exata**. `retry_dentro_do_declarado` já é essa fronteira. Sem ASL, a
   fixture prova o que precisa provar (os índices 1, 2 e 3) e a `SF-SFNX-001` sai em
   `skipped` com a lacuna `asl_absent` nomeada — **nenhuma entrada nova, e nenhuma
   removida, em `FRONTEIRA_SEM_GOLDEN`**.
4. **Custo continua fora de tudo** (regras 13 e 25 do `CLAUDE.md`). Nenhuma recusa nova,
   nenhum texto novo de regra e nenhuma linha deste plano atribui custo a uma tentativa,
   estima economia ou fala em dólar.

## O que este plano decide sobre o desenho (e por quê)

Cinco pontos, todos repetidos na seção **Dúvidas** no fim.

1. **`docs/surface.lock.json` FALTA no manifesto do design.** Editar
   `knowledge/stepfunctions/execution-history.md` move `knowledge.total_bytes` e
   `knowledge.by_name_sha256` do lock — `measure_surface` mede
   `measure_directory(knowledge, "*.md")`, byte a byte do conteúdo (regra 26 do
   `CLAUDE.md`). Sem ele, `tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches`
   fica vermelho. T4 o inclui, **marcado como fora do manifesto**.
2. **`fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json` também
   falta.** É a consequência medida do D5 (ponto 2 acima). T1 o inclui, **marcado como
   fora do manifesto**.
3. **O manifesto nomeia cada fixture nova pelo `meta.yaml`; a fixture é o diretório.**
   Cada uma leva `meta.yaml`, `input/historico/execucao.json` (e, no redrive,
   `input/definicao/carga.asl.json`) e o `expected/` que o regen escreve. Este plano lê
   as três linhas do manifesto como "a fixture inteira", e não como "só o `meta.yaml`".
4. **`docs/guia/usos/step-functions.md` é editado em T1 e T2, não em T4.** O design o
   agrupa com "conhecimento e guia" (AC6), mas o AC6 fala só do documento de `knowledge/`
   e do bundle offline. A regra da casa — *a tarefa que cria uma coisa também move os
   registros manuais dela* — vale aqui: T1 acrescenta as duas razões do redrive à tabela
   do guia, T2 acrescenta a do homônimo. Deixar as três para o fim é o jeito mais comum
   de um registro atravessar dois commits desatualizado.
5. **O nome da recusa do caso homônimo é `state_name_in_concurrent_branches`.** O design
   diz "`sfn.unresolved` nomeado" e não fixa a palavra. `state_name_ambiguous` **já
   existe** na derivação, com outro significado (o ASL declara dois estados de mesmo
   nome), e reusá-la juntaria duas lacunas diferentes num nome só.

## Cobertura dos critérios, por id exato

Os nomes de teste são os que o `define` fixou; nenhum é inventado aqui.

| AC | tarefa | o que o fecha |
|---|---|---|
| AC1 | T1 | `tests/test_sfn_history.py::test_redrive_sai_com_razao_propria_e_os_outros_dois_tipos_entram_calados` |
| AC2 | T1 | `tests/test_sfn_history.py::test_redrive_recusa_o_confronto_em_vez_de_comparar` |
| AC3 | T2 | `tests/test_sfn_history.py::test_estado_homonimo_em_ramos_diferentes_sai_recusado_sem_indice` |
| AC4 | T2 | `tests/test_sfn_history.py::test_ramo_unico_com_retry_mantem_os_indices` |
| AC5 | T3 | `tests/test_fixtures_golden_sfn_history.py::test_golden` (as três fixtures novas, e as onze antigas inalteradas) |
| AC6 | T4 | `python scripts/verify_offline_bundle.py` |
| AC7 | T3 | `python scripts/check_status_numbers.py --strict` (a única dimensão medida que esta feature move é *Fixtures golden*, e ela se move em T3) |

## T1 — o redrive: tipo conhecido, recusa própria, e o confronto recusado

> Fecha **AC1** e **AC2**.

### 1. Testes que falham

Acrescente ao **fim** de `tests/test_sfn_history.py` (o arquivo termina hoje em
`test_fuse_confronta_o_retry_declarado_com_o_observado`; os helpers `_evento`,
`_agendado`, `_submetido`, `_de`, `_historico_de_duas_tentativas` e a constante
`ASL_COM_RETRY_DE_DUAS` já existem nele e são reusados):

```python
# O redrive REAGENDA o Task dentro da MESMA execucao: `ExecutionRedriven` (id 10)
# separa duas tentativas que falharam de uma terceira que passou. `_evento` formata o
# deslocamento como minuto e segundo, entao todo valor aqui fica abaixo de 3600.
HISTORICO_COM_REDRIVE = {
    "events": [
        _evento(1, 0, "ExecutionStarted", 0),
        _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
        _evento(3, 2, "TaskScheduled", 2, **_agendado()),
        _evento(4, 3, "TaskSubmitted", 3, **_submetido({"JobRunId": "jr_antes_1"})),
        _evento(
            5,
            4,
            "TaskFailed",
            30,
            taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "falhou"},
        ),
        _evento(6, 5, "TaskScheduled", 31, **_agendado()),
        _evento(7, 6, "TaskSubmitted", 32, **_submetido({"JobRunId": "jr_antes_2"})),
        _evento(
            8,
            7,
            "TaskFailed",
            60,
            taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "falhou"},
        ),
        _evento(
            9,
            8,
            "ExecutionFailed",
            61,
            executionFailedEventDetails={"error": "Glue.AWSGlueException"},
        ),
        _evento(10, 9, "ExecutionRedriven", 300),
        _evento(11, 10, "TaskStateEntered", 301, stateEnteredEventDetails={"name": "Carga"}),
        _evento(12, 11, "TaskScheduled", 302, **_agendado()),
        _evento(13, 12, "TaskSubmitted", 303, **_submetido({"JobRunId": "jr_depois_1"})),
        _evento(14, 13, "TaskSucceeded", 330),
        _evento(15, 14, "ExecutionSucceeded", 331),
    ]
}


def test_redrive_sai_com_razao_propria_e_os_outros_dois_tipos_entram_calados():
    """Os tres tipos que faltavam entram, e SO o redrive tem consequencia (AC1).

    A pagina `API_HistoryEvent` publica 62 `Valid Values` para o campo `type`, e
    `_TIPOS_CONHECIDOS` tinha 59. `EvaluationFailed` e `MapRunRedriven` entram
    CALADOS, como os demais `MapRun*`: tipo conhecido que nao produz fact nem recusa.
    `ExecutionRedriven` entra com razao propria, porque ele muda o que "quantas vezes
    o Task foi agendado" significa -- o redrive reagenda o Task dentro da MESMA
    execucao, e nada no arquivo separa as tentativas de antes das de depois.
    """
    from sparkforge.facts.sfn_history import _TIPOS_CONHECIDOS

    assert {"EvaluationFailed", "ExecutionRedriven", "MapRunRedriven"} <= _TIPOS_CONHECIDOS
    assert len(_TIPOS_CONHECIDOS) == 62

    facts = extract_sfn_history(HISTORICO_COM_REDRIVE, "redrive.json")
    [recusa] = _de(facts, "sfn.unresolved")
    assert recusa.attrs["reason"] == "execution_redriven"
    # O discriminador NUMERICO vai em `measures`, como as demais recusas: `Fact.id` e
    # sha1 de `kind + subject + measures`, e `attrs` nao entra no hash.
    assert recusa.measures == {"event_id": 10}

    # As tentativas continuam MEDIDAS: o que o redrive quebra e a comparacao com o
    # teto declarado, nao a leitura do arquivo.
    tentativas = sorted(_de(facts, "sfn.attempt"), key=lambda f: f.measures["attempt_index"])
    assert [t.measures["attempt_index"] for t in tentativas] == [1, 2, 3]
    corridas = sorted(_de(facts, "sfn.job_run"), key=lambda f: f.measures["attempt_index"])
    assert [c.attrs["job_run_id"] for c in corridas] == [
        "jr_antes_1",
        "jr_antes_2",
        "jr_depois_1",
    ]
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["status"] == "succeeded"

    # Os outros dois entram CALADOS: nenhum fact proprio, e nenhuma recusa.
    outros = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "EvaluationFailed", 1),
            _evento(3, 2, "MapRunRedriven", 2),
            _evento(4, 3, "ExecutionSucceeded", 3),
        ]
    }
    facts = extract_sfn_history(outros, "outros.json")
    assert _de(facts, "sfn.unresolved") == []
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.measures["read_event_count"] == 4


def test_redrive_recusa_o_confronto_em_vez_de_comparar():
    """Teto declarado no ASL nao se compara com contagem que atravessa um redrive (AC2).

    As tres tentativas continuam publicadas. O que sai e a COMPARACAO:
    `build_sfn_retry_observado` emite `sfn.unresolved: redrive_in_execution` no lugar
    do `sfn.retry_observado`, e a `SF-SFNX-001` fica sem ancora naquele artefato.
    """
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.stepfunctions import extract_stepfunctions

    historico = extract_sfn_history(HISTORICO_COM_REDRIVE, "redrive.json")
    definicao = extract_stepfunctions(ASL_COM_RETRY_DE_DUAS, "carga.asl.json")

    fundidos = fuse(definicao + historico)
    assert not [f for f in fundidos if f.kind == "sfn.retry_observado"]
    [recusa] = [
        f
        for f in fundidos
        if f.kind == "sfn.unresolved" and f.attrs["reason"] == "redrive_in_execution"
    ]
    assert recusa.subject["file"] == "redrive.json"
    assert recusa.subject["symbol"] == "Carga"
    assert recusa.attrs["state_name"] == "Carga"
    # A recusa CITA as tentativas que ela deixou de comparar: sem isso, o operador
    # veria um case sem confronto e sem por onde comecar.
    assert set(recusa.provenance["derived_from"]) == {
        f.id for f in historico if f.kind == "sfn.attempt"
    }

    # As tentativas continuam no pool -- o que saiu foi a comparacao, nao a medida.
    assert len([f for f in fundidos if f.kind == "sfn.attempt"]) == 3

    # A recusa e por ARTEFATO: a execucao SEM redrive, ao lado no mesmo case, continua
    # tendo confronto. Um redrive numa execucao nao cala a execucao vizinha.
    limpa = extract_sfn_history(_historico_de_duas_tentativas("jr_x", "jr_y"), "limpa.json")
    fundidos = fuse(definicao + historico + limpa)
    confrontos = [f for f in fundidos if f.kind == "sfn.retry_observado"]
    assert [f.subject["file"] for f in confrontos] == ["limpa.json"]
    recusas = [
        f
        for f in fundidos
        if f.kind == "sfn.unresolved" and f.attrs["reason"] == "redrive_in_execution"
    ]
    assert [f.subject["file"] for f in recusas] == ["redrive.json"]
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_sfn_history.py -q
```

Falha esperada, **duas**:

- `test_redrive_sai_com_razao_propria_e_os_outros_dois_tipos_entram_calados` —
  `AssertionError` na primeira asserção, porque os três nomes não estão em
  `_TIPOS_CONHECIDOS` (hoje `len` é 59).
- `test_redrive_recusa_o_confronto_em_vez_de_comparar` — `AssertionError` em
  `assert not [...]`: hoje o `fuse` **produz** um `sfn.retry_observado` para `Carga`,
  somando as três tentativas contra o teto declarado.

Não é `ModuleNotFoundError`: o módulo existe, e o que falta é comportamento.

### 3. Código mínimo

#### 3.1 `sparkforge/facts/sfn_history.py` — os três tipos e o comentário

Substitua o bloco de comentário que hoje precede `_TIPOS_CONHECIDOS` (as linhas que
começam em `# https://docs.aws.amazon.com/...API_HistoryEvent.html` e terminam em
`# muda o que "quantas vezes o Task foi agendado" significa.`) por:

```python
# https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html
# Os 62 `Valid Values` do campo `type`, conferidos na releitura de 2026-09-20. Tipo fora
# desta lista nao e erro do artefato -- e a API que cresceu --, e por isso sai em
# `sfn.unresolved` `event_type_unknown` com o nome, em vez de ser ignorado em silencio.
#
# ELA E A LISTA INTEIRA desde a feature `docs/sdd/SFN_TENTATIVA/`. Os tres que faltavam
# -- posteriores a leitura original -- entraram aqui, e nao entraram iguais:
# `EvaluationFailed` e `MapRunRedriven` sao tipo conhecido que nao produz fact nem
# recusa, como os demais `MapRun*`; `ExecutionRedriven` e a execucao RETOMADA, e ele muda
# o que "quantas vezes o Task foi agendado" significa -- o redrive reagenda o Task dentro
# da MESMA execucao, e nada aqui separa as tentativas de antes das de depois. Por isso
# ele sai em `sfn.unresolved` `execution_redriven`, e `build_sfn_retry_observado` recusa
# a COMPARACAO com o teto declarado no ASL. As tentativas continuam medidas.
```

E acrescente os três nomes ao `frozenset`, **em ordem alfabética** (é a ordem em que o
resto da lista está):

- `"EvaluationFailed",` entre `"ChoiceStateExited",` e `"ExecutionAborted",`;
- `"ExecutionRedriven",` entre `"ExecutionFailed",` e `"ExecutionStarted",`;
- `"MapRunRedriven",` entre `"MapRunFailed",` e `"MapRunStarted",`.

#### 3.2 `sparkforge/facts/sfn_history.py` — a recusa do extrator

Em `extract_sfn_history`, logo **depois** do bloco que emite `execution_terminal_absent`
e **antes** do comentário `# 1. Um agendamento -> uma tentativa.`, acrescente:

```python
    # `ExecutionRedriven` e a execucao RETOMADA: o Task e reagendado DENTRO da mesma
    # execucao, e nada no arquivo separa as tentativas de antes das de depois. A
    # leitura continua valendo -- o que deixa de valer e a comparacao com o teto
    # declarado no ASL, e quem a recusa e `build_sfn_retry_observado` (D3).
    for evento in ordenados:
        if str(evento.get("type")) != "ExecutionRedriven":
            continue
        leitura.facts.append(
            _unresolved(
                _file_subject(path),
                "execution_redriven",
                provenance,
                measures={"event_id": int(evento["id"])},
            )
        )
```

#### 3.3 `sparkforge/facts/sfn_history.py` — a recusa da derivação

Acrescente este helper **logo antes** de `def build_sfn_retry_observado(`:

```python
def _artefatos_com_redrive(facts: Sequence[Fact]) -> set[str]:
    """Os artefatos em que o extrator leu um `ExecutionRedriven`.

    A derivacao nao ve eventos -- ela ve facts --, e por isso le a recusa que o
    extrator ja emitiu (`sfn.unresolved: execution_redriven`, uma por evento) em vez de
    reabrir o arquivo. A granularidade e a MESMA do lado medido,
    `(artefato, nome do estado)`: um redrive numa execucao nao recusa o confronto da
    execucao ao lado, salva no mesmo case.
    """
    return {
        str((fact.provenance or {}).get("artifact") or "")
        for fact in facts
        if fact.kind == "sfn.unresolved"
        and (fact.attrs or {}).get("reason") == "execution_redriven"
    }
```

Dentro de `build_sfn_retry_observado`, acrescente a leitura ao lado das outras três:

```python
    tentativas = _glue_por_execucao(facts)
    declaradas = _glue_por_estado(facts, "sfn.task")
    ha_asl = any(f.kind == "sfn.task" for f in facts)
    com_redrive = _artefatos_com_redrive(facts)
```

E, dentro do laço `for artefato, nome in sorted(tentativas):`, **logo depois** do bloco
que monta `subject` e `proveniencia` e **antes** do `if not ha_asl:`, acrescente:

```python
        # O redrive vem ANTES do ASL de proposito: com `ExecutionRedriven` no arquivo,
        # nao ha confronto a fazer, e dizer `asl_absent` mandaria o operador buscar uma
        # definicao que nao destravaria nada. A comparacao e que foi recusada.
        if artefato in com_redrive:
            saida.append(
                _unresolved(
                    dict(subject), "redrive_in_execution", proveniencia, state_name=nome
                )
            )
            continue
```

#### 3.4 `sparkforge/facts/sfn_history.py` — a docstring do módulo

Na lista de razões de `sfn.unresolved` (a que hoje termina em
`` `execution_data_absent` e `job_run_id_unrecognized` ``), passe a listar
`` `execution_redriven` `` antes de `` `job_run_id_unrecognized` ``:

```text
- `sfn.unresolved` -- o que nao deu para ler. Razoes: `read_error`,
  `size_above_limit`, `invalid_json`, `json_too_deep`, `json_too_large`,
  `not_an_execution_history`, `truncated`, `event_not_an_object`,
  `event_type_unknown`, `event_id_duplicated`, `state_unresolved`, `attempt_unanchored`,
  `execution_terminal_absent`, `execution_data_absent`, `execution_redriven` e
  `job_run_id_unrecognized`.
```

E, na lista de razões que só a derivação emite, acrescente `` `redrive_in_execution` ``
com a frase que diz o que ela recusa. O trecho de hoje é

```text
  `asl_absent`, `state_name_absent_in_asl`, `state_name_ambiguous`,
  `declared_ceiling_unreadable` e `glue_attempt_absent` (um ARTEFATO tem tentativa
```

e passa a ser

```text
  `asl_absent`, `state_name_absent_in_asl`, `state_name_ambiguous`,
  `declared_ceiling_unreadable`, `redrive_in_execution` (o artefato tem
  `ExecutionRedriven`: o Task foi reagendado dentro da MESMA execucao, e a contagem
  deixa de ser comparavel com o teto declarado -- as tentativas continuam publicadas, e
  o que se recusa e a COMPARACAO) e `glue_attempt_absent` (um ARTEFATO tem tentativa
```

O resto do parágrafo de `glue_attempt_absent` — de `medida, e nenhuma delas e` até o fim
do parêntese — fica **exatamente como está**.

#### 3.5 `rules/catalog/sfn-history.yaml` — a prosa da área e da regra (D5)

No bloco de comentário de abertura, na lista **`O QUE A ÁREA NÃO JULGA, e por quê (D4)`**,
acrescente um item logo depois do item de custo:

```yaml
# - execução RETOMADA por redrive: `ExecutionRedriven` no histórico significa que o Task
#   foi reagendado dentro da MESMA execução, e nada no arquivo separa as tentativas de
#   antes das de depois. Ali o confronto com o teto declarado não acontece — sai
#   `sfn.unresolved: redrive_in_execution` no lugar do `sfn.retry_observado`, e a
#   `SF-SFNX-001` fica em `skipped` por falta de âncora. Medir o redrive em vez de
#   recusá-lo exigiria a forma do evento, que ninguém leu (lacuna 9 de
#   `knowledge/stepfunctions/execution-history.md`);
```

E, no `explanation:` da `SF-SFNX-001`, acrescente ao **fim** do bloco (depois da frase
que termina em `responde custo com \`dpu_seconds\` medido.`):

```yaml
      A contagem **não atravessa um redrive**. Com `ExecutionRedriven` no histórico, a
      execução foi RETOMADA e o Task é reagendado dentro da MESMA execução, sem que nada
      no arquivo separe as tentativas de antes das de depois: ali
      `build_sfn_retry_observado` emite `sfn.unresolved: redrive_in_execution` no lugar
      do fact que esta regra ancora, e ela sai em `skipped`. As tentativas continuam
      medidas e publicadas — o que se recusa é a COMPARAÇÃO com o teto declarado.
```

#### 3.6 `docs/guia/usos/step-functions.md` — as duas razões novas

Na linha da tabela do `sfn.unresolved` do histórico (a que começa em
`| \`sfn.unresolved\` | o que não deu para ler ou parear |`), troque o trecho

```text
`execution_data_absent`, `job_run_id_unrecognized`; e na derivação, `asl_absent`, `state_name_absent_in_asl`, `state_name_ambiguous`, `declared_ceiling_unreadable` e `glue_attempt_absent` |
```

por

```text
`execution_data_absent`, `execution_redriven`, `job_run_id_unrecognized`; e na derivação, `asl_absent`, `state_name_absent_in_asl`, `state_name_ambiguous`, `declared_ceiling_unreadable`, `redrive_in_execution` e `glue_attempt_absent` |
```

E acrescente, **logo depois** do parágrafo que começa em
`**Duas recusas que você pode ver e que não são erro seu.**`, este parágrafo novo:

```markdown
**Redrive: a contagem para de ser comparável, e a recusa diz isso.** Quando o histórico
traz `ExecutionRedriven`, a execução foi **retomada**: o Task é reagendado dentro da
MESMA execução, e nada no arquivo separa as tentativas de antes das de depois. As
tentativas continuam medidas e publicadas; o que sai é o **confronto** — por execução e
por estado sai `sfn.unresolved: redrive_in_execution` no lugar do `sfn.retry_observado`,
e a `SF-SFNX-001` fica sem âncora naquele arquivo. A recusa é por **arquivo**: uma
execução sem redrive, salva ao lado no mesmo case, continua tendo confronto. Medir o
redrive em vez de recusá-lo exigiria saber quantas tentativas caíram antes e quantas
depois, e a forma do evento não foi lida (lacuna 9 de
`knowledge/stepfunctions/execution-history.md`).
```

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_sfn_history.py -q
```

Todos verdes — AC1 e AC2.

Agora o golden que a prosa da regra move (ponto 2 das medidas). Instantâneo, por nome:

```bash
python scripts/regen_fixtures.py retry_acima_do_declarado
git diff --stat fixtures/sfn_history/retry_acima_do_declarado/
```

O diff tem de ser **só** `expected/findings.json`, e **só** no campo `explanation` do
finding de `SF-SFNX-001`. `expected/facts.json` não pode mudar: nenhuma daquelas
tentativas atravessa redrive. Se `facts.json` mudar, pare — alguma coisa em 3.2 ou 3.3
está mexendo em arquivo sem `ExecutionRedriven`.

```bash
python -m pytest tests/test_fixtures_golden_sfn_history.py -q
```

### 5. Gates vizinhos

Extrator e regra (seções *Acrescentar ou alterar um EXTRATOR de facts* e *Acrescentar ou
alterar uma REGRA no catálogo* de `docs/gates-por-mudanca.md`), **um comando por vez**:

```bash
python -m ruff check sparkforge/facts/sfn_history.py tests/test_sfn_history.py
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py -q
python -m pytest tests/test_rules_threshold_mutation.py tests/test_rules_action_field.py tests/test_rules_campos_de_lista.py -q
python -m pytest tests/test_fixtures_kind_coverage.py tests/test_docs_coverage.py tests/test_refresh_knowledge.py -q
python -m pytest tests/test_facts_fusion.py tests/test_fixtures_golden_fusion.py -q
python -m pytest tests/test_facts_scan.py tests/test_harness_untrusted.py tests/test_databricks_rule_audit.py -q
python -m pytest tests/test_reference_docs.py -q
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

- `test_rules_threshold_mutation.py` tem de passar **sem entrada nova e sem entrada
  removida** em `FRONTEIRA_SEM_GOLDEN`: a `expr` da `SF-SFNX-001` não mudou, só a prosa.
  Se ele pedir exceção, algo além da `explanation` foi editado na regra.
- `test_refresh_knowledge.py` está aqui porque o gate de regra o pede: **nenhuma URL
  nova** entra nesta tarefa (`sources:` da `SF-SFNX-001` fica como está), então ele passa
  sem `python scripts/refresh_knowledge.py --update --offline`.
- `test_reference_docs.py` confere os comandos e os links relativos de
  `docs/guia/usos/step-functions.md`.
- `check_status_numbers.py --strict` tem de continuar em `0 divergencia(s)`: nenhuma
  dimensão medida se move em T1.
- `check_vnext_claims.py` reprova pelas alegações de **bytes** do corpus `*.py` — o
  módulo e o arquivo de teste cresceram. A contagem de **arquivos** não muda (nenhum
  `.py` novo), então `VNX-640` deve continuar em 774. **Remedie pelos ids que a saída
  listar**, um por vez, corrigindo `text`, `context` e `proof.expect.value` de cada
  entrada em `docs/claims.lock.json` e o número correspondente em
  `docs/harness/CODEINTEL-GAP.md`, e rode o gate de novo até `0 divergencia(s)`. Os ids
  que costumam cair nesta família são `VNX-643`, `VNX-653`, `VNX-658`, `VNX-663`,
  `VNX-666`, `VNX-667`, `VNX-670` e `VNX-674` — **mas a lista da saída é que manda**.

### 6. Commit

```bash
git add tests/test_sfn_history.py sparkforge/facts/sfn_history.py rules/catalog/sfn-history.yaml fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json docs/guia/usos/step-functions.md docs/harness/CODEINTEL-GAP.md docs/claims.lock.json
git commit -F "$TEMP/sfn_tentativa_t1.txt"
```

Mensagem (escreva o arquivo com Write, no scratchpad — **nunca** heredoc dentro de
`$(...)`):

```text
fix(facts): refuse the retry comparison when the execution was redriven

`ExecutionRedriven`, `EvaluationFailed` and `MapRunRedriven` join
`_TIPOS_CONHECIDOS`, which now equals the 62 `Valid Values` the API publishes.
Two of them are silent; the redrive is not: it re-schedules the Task inside the
SAME execution, and nothing in the file separates the attempts before it from
the ones after. The extractor emits `sfn.unresolved: execution_redriven` per
event, and `build_sfn_retry_observado` emits `sfn.unresolved:
redrive_in_execution` in place of `sfn.retry_observado` for that artifact. The
attempts stay measured and published — what is refused is the COMPARISON with
the ceiling the ASL declares, and SF-SFNX-001 says so in its own prose.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

## T2 — estados homônimos em ramos concorrentes: numeração por ancestralidade

> Fecha **AC3** e **AC4**.

### 1. Testes que falham

Acrescente ao **fim** de `tests/test_sfn_history.py`:

```python
# Dois ramos de um `Parallel`, cada um com um estado chamado `Carga`. As duas entradas
# (ids 9 e 10) apontam para o MESMO `ParallelStateStarted` (id 8) e nenhuma esta na
# cadeia da outra: e ai que o nome deixa de identificar um estado.
HISTORICO_COM_PARALLEL_HOMONIMO = {
    "events": [
        _evento(1, 0, "ExecutionStarted", 0),
        _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Preparacao"}),
        _evento(3, 2, "TaskScheduled", 2, **_agendado()),
        _evento(4, 3, "TaskSubmitted", 3, **_submetido({"JobRunId": "jr_prep"})),
        _evento(5, 4, "TaskSucceeded", 20),
        _evento(6, 5, "TaskStateExited", 21, stateExitedEventDetails={"name": "Preparacao"}),
        _evento(7, 6, "ParallelStateEntered", 22, stateEnteredEventDetails={"name": "Cargas"}),
        _evento(8, 7, "ParallelStateStarted", 23),
        _evento(9, 8, "TaskStateEntered", 24, stateEnteredEventDetails={"name": "Carga"}),
        _evento(10, 8, "TaskStateEntered", 24, stateEnteredEventDetails={"name": "Carga"}),
        _evento(11, 9, "TaskScheduled", 25, **_agendado()),
        _evento(12, 10, "TaskScheduled", 25, **_agendado()),
        _evento(13, 11, "TaskSubmitted", 26, **_submetido({"JobRunId": "jr_ramo_a"})),
        _evento(14, 12, "TaskSubmitted", 26, **_submetido({"JobRunId": "jr_ramo_b"})),
        _evento(15, 13, "TaskSucceeded", 50),
        _evento(16, 14, "TaskSucceeded", 51),
        _evento(17, 16, "ParallelStateSucceeded", 52),
        _evento(18, 17, "ParallelStateExited", 53, stateExitedEventDetails={"name": "Cargas"}),
        _evento(19, 18, "ExecutionSucceeded", 54),
    ]
}


# O MESMO estado entra TRES vezes, uma depois da outra, por um `Choice` que volta. Cada
# entrada esta na cadeia da seguinte: as tres se alcancam, e o nome continua
# identificando um estado so.
HISTORICO_DE_RAMO_UNICO_COM_TRES_ENTRADAS = {
    "events": [
        _evento(1, 0, "ExecutionStarted", 0),
        _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
        _evento(3, 2, "TaskScheduled", 2, **_agendado()),
        _evento(4, 3, "TaskSubmitted", 3, **_submetido({"JobRunId": "jr_1"})),
        _evento(
            5,
            4,
            "TaskFailed",
            30,
            taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "falhou"},
        ),
        _evento(6, 5, "TaskStateExited", 31, stateExitedEventDetails={"name": "Carga"}),
        _evento(7, 6, "ChoiceStateEntered", 32, stateEnteredEventDetails={"name": "Repetir"}),
        _evento(8, 7, "ChoiceStateExited", 33, stateExitedEventDetails={"name": "Repetir"}),
        _evento(9, 8, "TaskStateEntered", 34, stateEnteredEventDetails={"name": "Carga"}),
        _evento(10, 9, "TaskScheduled", 35, **_agendado()),
        _evento(11, 10, "TaskSubmitted", 36, **_submetido({"JobRunId": "jr_2"})),
        _evento(
            12,
            11,
            "TaskFailed",
            60,
            taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "falhou"},
        ),
        _evento(13, 12, "TaskStateExited", 61, stateExitedEventDetails={"name": "Carga"}),
        _evento(14, 13, "ChoiceStateEntered", 62, stateEnteredEventDetails={"name": "Repetir"}),
        _evento(15, 14, "ChoiceStateExited", 63, stateExitedEventDetails={"name": "Repetir"}),
        _evento(16, 15, "TaskStateEntered", 64, stateEnteredEventDetails={"name": "Carga"}),
        _evento(17, 16, "TaskScheduled", 65, **_agendado()),
        _evento(18, 17, "TaskSubmitted", 66, **_submetido({"JobRunId": "jr_3"})),
        _evento(19, 18, "TaskSucceeded", 90),
        _evento(20, 19, "ExecutionSucceeded", 91),
    ]
}


def test_estado_homonimo_em_ramos_diferentes_sai_recusado_sem_indice():
    """Dois ramos de um `Parallel` com um estado de mesmo nome: o nome nao identifica (AC3).

    O contador `ordem_por_estado` era chaveado so pelo NOME, e a primeira tentativa do
    segundo ramo saia com `attempt_index: 2` -- um indice que o arquivo nao sustenta, e
    que e o `subject.symbol` por onde a `SF-SFNX-002` e a `SF-SFNX-003` apontam o
    achado. A deteccao e por ANCESTRALIDADE: as duas entradas de `Carga` divergem no
    `ParallelStateStarted` comum, e nenhuma alcanca a outra subindo `previousEventId`.
    """
    facts = extract_sfn_history(HISTORICO_COM_PARALLEL_HOMONIMO, "parallel.json")

    # Nenhuma tentativa de `Carga`, e nenhum `sfn.job_run` dela: o indice seria invencao.
    assert [t.attrs["state_name"] for t in _de(facts, "sfn.attempt")] == ["Preparacao"]
    assert [c.attrs["job_run_id"] for c in _de(facts, "sfn.job_run")] == ["jr_prep"]

    [recusa] = _de(facts, "sfn.unresolved")
    assert recusa.attrs["reason"] == "state_name_in_concurrent_branches"
    assert recusa.attrs["state_name"] == "Carga"
    assert recusa.subject["symbol"] == "Carga"
    assert recusa.measures == {"entry_count": 2, "attempt_count": 2}

    # O estado de nome UNICO do mesmo historico continua virando tentativa, com indice.
    [preparacao] = _de(facts, "sfn.attempt")
    assert preparacao.subject["symbol"] == "Preparacao#1"
    assert preparacao.measures["attempt_index"] == 1
    assert preparacao.attrs["result"] == "succeeded"

    # E as contagens da execucao contam o que SAIU, nao o que foi lido.
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.measures["attempt_count"] == 1
    assert execucao.measures["job_run_count"] == 1
    assert execucao.measures["read_event_count"] == 19


def test_ramo_unico_com_retry_mantem_os_indices():
    """Reentrada SEQUENCIAL continua numerada 1..n -- e e ela que impede a regressao (AC4).

    Este e o negativo de D1, e a razao de o criterio ser ancestralidade e nao contagem
    de entradas: com "mais de uma entrada => recusa", este historico perderia
    exatamente a numeracao que a `SF-SFNX-001` existe para medir.

    O criterio e indiferente a lacuna U1 POR CONSTRUCAO: se o `Retry` reentrar no
    estado, a reentrada e sequencial como esta aqui e as entradas se alcancam; se nao
    reentrar, ha uma entrada so. Nos dois casos a numeracao e a mesma, e por isso nao e
    preciso saber a resposta para agir.
    """
    facts = extract_sfn_history(HISTORICO_DE_RAMO_UNICO_COM_TRES_ENTRADAS, "ramo-unico.json")

    assert _de(facts, "sfn.unresolved") == []
    tentativas = sorted(_de(facts, "sfn.attempt"), key=lambda f: f.measures["attempt_index"])
    assert [t.measures["attempt_index"] for t in tentativas] == [1, 2, 3]
    assert [t.subject["symbol"] for t in tentativas] == ["Carga#1", "Carga#2", "Carga#3"]
    assert {t.attrs["state_name"] for t in tentativas} == {"Carga"}
    corridas = sorted(_de(facts, "sfn.job_run"), key=lambda f: f.measures["attempt_index"])
    assert [c.attrs["job_run_id"] for c in corridas] == ["jr_1", "jr_2", "jr_3"]

    # E o caso de UMA entrada com varios agendamentos -- o que as onze fixtures do
    # corpus ja tinham -- continua igual: nada aqui depende de quantas entradas ha.
    facts = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")
    tentativas = sorted(_de(facts, "sfn.attempt"), key=lambda f: f.measures["attempt_index"])
    assert [t.subject["symbol"] for t in tentativas] == [
        "CargaDiaria#1",
        "CargaDiaria#2",
        "CargaDiaria#3",
    ]
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_sfn_history.py -q
```

Falha esperada, **uma**:
`test_estado_homonimo_em_ramos_diferentes_sai_recusado_sem_indice` com `AssertionError`
em `assert [t.attrs["state_name"] for t in _de(facts, "sfn.attempt")] == ["Preparacao"]`
— hoje saem **três** tentativas (`Preparacao#1`, `Carga#1`, `Carga#2`), e é o
`Carga#2` do segundo ramo que é o índice inventado.

`test_ramo_unico_com_retry_mantem_os_indices` **passa desde já**, e é assim que tem de
ser: ele é o guarda contra a regressão que a correção poderia introduzir, não a
correção. Escreva-o agora mesmo assim — se ele ficar vermelho em algum momento depois
do passo 3, a correção comeu o caso que a `SF-SFNX-001` mede.

### 3. Código mínimo

#### 3.1 `sparkforge/facts/sfn_history.py` — os dois helpers

Acrescente, **logo depois** da função `_ancestral` (e antes de `_job_run`):

```python
def _ancestrais(evento: dict[str, Any], por_id: dict[int, dict[str, Any]]) -> set[int]:
    """Todo `id` que a cadeia de `previousEventId` alcanca subindo a partir de `evento`.

    O mesmo passeio de `_ancestral`, sem o filtro por tipo e sem razao de parada
    nomeada: aqui a pergunta nao e "qual ancestral" e sim "A alcanca B?". Raiz, cadeia
    quebrada e ciclo terminam o passeio devolvendo o que ja foi visto -- um conjunto
    menor nunca inventa alcance, e alcance a menos so faz RECUSAR mais, que e o lado
    seguro de errar.
    """
    vistos: set[int] = set()
    atual = evento
    while True:
        anterior = atual.get("previousEventId")
        if isinstance(anterior, bool) or not isinstance(anterior, int) or anterior <= 0:
            return vistos
        if anterior in vistos:
            return vistos
        vistos.add(anterior)
        pai = por_id.get(anterior)
        if pai is None:
            return vistos
        atual = pai


def _nomes_em_ramos_concorrentes(
    tentativas: dict[int, dict[str, Any]], por_id: dict[int, dict[str, Any]]
) -> dict[str, int]:
    """Nome do estado -> quantas entradas ele tem, quando DUAS delas nao se alcancam.

    Para um nome, juntam-se os `TaskStateEntered` distintos a que os `TaskScheduled`
    daquele nome se encadeiam. Reentrada SEQUENCIAL -- um retry, ou um `Choice` que
    volta ao mesmo estado -- deixa a entrada anterior na cadeia da seguinte: as duas se
    alcancam, e a numeracao 1..n continua valendo. Ramos concorrentes de um `Parallel`
    divergem no `ParallelStateStarted` comum e nunca se alcancam: ali o NOME nao
    identifica um estado, e o `attempt_index` seria invencao -- ele e o
    `subject.symbol` por onde `SF-SFNX-002` e `SF-SFNX-003` apontam o achado.

    O criterio NAO pergunta se o `Retry` reentra no estado, que e justamente a lacuna
    que ninguem mediu (U1 de `docs/sdd/SFN_TENTATIVA/define.md`): qualquer que seja a
    resposta, reentrada sequencial e ancestral e ramo concorrente nao e.

    O `previousEventId` ser o do MESMO RAMO continua sendo premissa nossa, nao
    publicada (lacuna 8 de `knowledge/stepfunctions/execution-history.md`). Se ela
    estiver errada, o efeito e recusar DEMAIS -- duas entradas sequenciais pareceriam
    nao-ancestrais --, nunca afirmar de menos.
    """
    entradas_por_nome: dict[str, list[int]] = {}
    for identificador in sorted(tentativas):
        estado = tentativas[identificador]
        lista = entradas_por_nome.setdefault(estado["state_name"], [])
        if estado["entry_id"] not in lista:
            lista.append(estado["entry_id"])
    concorrentes: dict[str, int] = {}
    for nome, entradas in entradas_por_nome.items():
        if len(entradas) < 2:
            continue
        alcance = {
            entrada: _ancestrais(por_id[entrada], por_id)
            for entrada in entradas
            if entrada in por_id
        }
        pares = [
            (a, b) for indice, a in enumerate(entradas) for b in entradas[indice + 1 :]
        ]
        if any(
            b not in alcance.get(a, set()) and a not in alcance.get(b, set())
            for a, b in pares
        ):
            concorrentes[nome] = len(entradas)
    return concorrentes
```

#### 3.2 `sparkforge/facts/sfn_history.py` — guardar a entrada na tentativa

No passo 1 de `extract_sfn_history`, acrescente `"entry_id"` ao dicionário da tentativa.
O bloco inteiro, depois da edição:

```python
        ordem_por_estado[nome] = ordem_por_estado.get(nome, 0) + 1
        tentativas[int(evento["id"])] = {
            "state_name": nome,
            # O `id` do `TaskStateEntered` de onde o nome veio. E ele que decide se o
            # nome identifica UM estado naquele historico (D1), e por isso ele fica
            # guardado em vez de descartado assim que o nome foi lido.
            "entry_id": int(entrada["id"]),
            "index": ordem_por_estado[nome],
            "scheduled": evento,
            "terminal": None,
            "submitted": None,
        }
```

(`entrada` nunca é `None` aqui: `nome` só deixa de ser `None` quando `entrada` existe e
tem `stateEnteredEventDetails.name`.)

#### 3.3 `sparkforge/facts/sfn_history.py` — a recusa, entre os passos 2 e 3

Acrescente, **depois** do laço do passo 2 (o que termina em
`elif alvo["terminal"] is None: alvo["terminal"] = evento`) e **antes** do comentário
`# 3. Os facts, em ordem de agendamento.`:

```python
    # 2.5 O NOME identifica UM estado? So quando as entradas dele se alcancam (D1).
    #
    # A recusa sai DEPOIS do passo 2 de proposito. Tirar as tentativas antes dele
    # faria cada terminal e cada `TaskSubmitted` daquele nome cair em
    # `attempt_unanchored` -- "nao achei o agendamento" --, que e outra coisa e
    # esconderia a lacuna de verdade atras de ruido por evento.
    concorrentes = _nomes_em_ramos_concorrentes(tentativas, por_id)
    for nome in sorted(concorrentes):
        quantas = sum(1 for e in tentativas.values() if e["state_name"] == nome)
        leitura.facts.append(
            _unresolved(
                _attempt_subject(path, nome),
                "state_name_in_concurrent_branches",
                provenance,
                measures={"entry_count": concorrentes[nome], "attempt_count": quantas},
                state_name=nome,
            )
        )
```

E, no passo 3, pule os nomes recusados:

```python
    # 3. Os facts, em ordem de agendamento.
    for identificador in sorted(tentativas):
        estado = tentativas[identificador]
        if estado["state_name"] in concorrentes:
            continue
        leitura.facts.extend(_fatos_da_tentativa(estado, status, classe, leitura))
```

#### 3.4 `sparkforge/facts/sfn_history.py` — a docstring do módulo

Acrescente `` `state_name_in_concurrent_branches` `` à lista de razões do extrator,
entre `` `state_unresolved` `` e `` `attempt_unanchored` ``.

E acrescente, **logo depois** da seção `## Como uma tentativa e PAREADA, e por que pela
cadeia`, esta seção nova:

```text
## O NOME identifica um estado? So quando as entradas dele se alcancam

O historico publica o NOME do estado (`stateEnteredEventDetails.name`), nunca o caminho
dele na definicao. Dentro de um `Parallel`, dois ramos podem ter um estado de mesmo
nome -- e ai o nome nao identifica nada. Ate 2026-09-20 o contador era chaveado so pelo
nome, e a primeira tentativa do segundo ramo saia com `attempt_index: 2`: um indice que
o arquivo nao sustenta, e que e o `subject.symbol` por onde `SF-SFNX-002` e
`SF-SFNX-003` apontam o achado.

O criterio e ANCESTRALIDADE, nao a presenca de um `Parallel` no arquivo. Para um nome,
juntam-se os `TaskStateEntered` distintos a que os `TaskScheduled` daquele nome se
encadeiam; se DOIS deles forem mutuamente nao-ancestrais -- nenhum alcanca o outro
subindo `previousEventId` --, nenhum `sfn.attempt` daquele nome e emitido, nenhum
`sfn.job_run` dele e ligado, e sai `sfn.unresolved: state_name_in_concurrent_branches`.

Reentrada SEQUENCIAL nao cai ali: um retry, ou um `Choice` que volta, deixa a entrada
anterior na cadeia da seguinte, e as duas se alcancam. E por isso que o criterio e
indiferente a lacuna U1 -- se o `Retry` reentra no estado nao esta publicado, e a
resposta nao muda a numeracao nos dois casos.
```

#### 3.5 `docs/guia/usos/step-functions.md` — a razão nova

Na mesma linha da tabela do `sfn.unresolved` do histórico, troque

```text
`state_unresolved`, `attempt_unanchored`,
```

por

```text
`state_unresolved`, `state_name_in_concurrent_branches`, `attempt_unanchored`,
```

E acrescente, logo depois do parágrafo `**Redrive: a contagem para de ser comparável...**`
que T1 escreveu:

```markdown
**Estado de mesmo nome em ramos concorrentes: sem índice, e sem tentativa.** Dentro de um
`Parallel`, dois ramos podem ter um estado com o mesmo nome — e o histórico publica
**nome**, não caminho. O extrator junta os `TaskStateEntered` distintos a que os
`TaskScheduled` daquele nome se encadeiam; se dois deles forem mutuamente
não-ancestrais — nenhum alcança o outro subindo `previousEventId` —, o nome não
identifica um estado naquele arquivo: nenhum `sfn.attempt` dele é emitido, nenhum
`sfn.job_run` dele é ligado, e sai `sfn.unresolved:
state_name_in_concurrent_branches` com o nome e com quantas entradas ele tinha.
Reentrada **sequencial** — um retry, ou um `Choice` que volta ao mesmo estado — não cai
aqui: a entrada anterior está na cadeia da seguinte, as duas se alcançam, e a numeração
1..n continua valendo.
```

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_sfn_history.py -q
python -m pytest tests/test_fixtures_golden_sfn_history.py -q
```

O segundo comando é o ponto 1 das medidas escrito como teste: **nenhuma** das onze
fixtures do corpus tem mais de um `TaskStateEntered` por nome, então nenhum golden pode
mudar aqui. Se algum mudar, **não regenere** — leia o diff primeiro, porque ele é uma
medida contra este plano.

### 5. Gates vizinhos

```bash
python -m ruff check sparkforge/facts/sfn_history.py tests/test_sfn_history.py
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_facts_fusion.py tests/test_fixtures_golden_fusion.py -q
python -m pytest tests/test_facts_scan.py tests/test_harness_untrusted.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py -q
python -m pytest tests/test_reference_docs.py -q
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

`test_harness_untrusted.py` roda `extract_sfn_history_tree` sobre todo domínio de
`fixtures/` (a medida de snippet): a recusa nova sai com `_attempt_subject`, cujo
`snippet` é vazio como o de todos os outros facts deste módulo.

O gate de lastro reprova de novo pelos bytes de `.py`. **Remedie pelos ids da saída**,
como em T1 — `text`, `context` **e** `proof.expect.value` de cada entrada.

### 6. Commit

```bash
git add tests/test_sfn_history.py sparkforge/facts/sfn_history.py docs/guia/usos/step-functions.md docs/harness/CODEINTEL-GAP.md docs/claims.lock.json
git commit -F "$TEMP/sfn_tentativa_t2.txt"
```

```text
fix(facts): stop numbering attempts of states that share a name across branches

The history publishes the state NAME, never its path in the definition. Two
branches of a `Parallel` could carry a state with the same name, and the counter
was keyed by name alone: the first attempt of the second branch came out with
`attempt_index: 2`, an index the file does not support and the very
`subject.symbol` SF-SFNX-002 and SF-SFNX-003 point at.

The test is ancestry, not the presence of a `Parallel`: for one name, join the
distinct `TaskStateEntered` its `TaskScheduled` events chain to, and if two of
them are mutually non-ancestral, emit no `sfn.attempt` of that name and refuse
by name instead. Sequential re-entry — a retry, or a `Choice` that loops back —
leaves the previous entry on the chain of the next one, so it stays numbered
1..n, which is exactly what SF-SFNX-001 exists to measure.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

## T3 — as três fixtures, o golden e a contagem do `STATUS.md`

> Fecha **AC5** e **AC7**.

### 1. O que falha antes

`tests/test_fixtures_golden_sfn_history.py::test_all_required_fixtures_exist`, assim que
os três diretórios existirem no disco e `REQUIRED_FIXTURES` ainda não os declarar; e
`::test_golden` enquanto o `expected/` de cada um não tiver sido gerado. O vermelho que
esta tarefa registra é o de `test_golden`.

### 2. Os arquivos de entrada

#### `fixtures/sfn_history/execucao_com_redrive/input/historico/execucao.json`

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T07:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T07:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaDiaria"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T07:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T07:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_cccccccc1\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T07:12:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_cccccccc1 FAILED"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T07:12:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T07:12:02.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_cccccccc2\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T07:24:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_cccccccc2 FAILED"}},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T07:24:01.000000+00:00", "type": "ExecutionFailed", "executionFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "JobRun jr_cccccccc2 FAILED"}},
    {"id": 10, "previousEventId": 9, "timestamp": "2026-09-18T09:00:00.000000+00:00", "type": "ExecutionRedriven"},
    {"id": 11, "previousEventId": 10, "timestamp": "2026-09-18T09:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaDiaria"}},
    {"id": 12, "previousEventId": 11, "timestamp": "2026-09-18T09:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 13, "previousEventId": 12, "timestamp": "2026-09-18T09:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_cccccccc3\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 14, "previousEventId": 13, "timestamp": "2026-09-18T09:11:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 15, "previousEventId": 14, "timestamp": "2026-09-18T09:11:01.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

#### `fixtures/sfn_history/execucao_com_redrive/input/definicao/carga.asl.json`

```json
{
  "Comment": "Carga diaria com UMA tentativa extra declarada: teto efetivo de duas.",
  "StartAt": "CargaDiaria",
  "States": {
    "CargaDiaria": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 1}],
      "End": true
    }
  }
}
```

#### `fixtures/sfn_history/execucao_com_redrive/meta.yaml`

```yaml
name: execucao_com_redrive
proves: >
  AC1 e AC2. O historico traz `ExecutionRedriven` (id 10): a execucao foi RETOMADA, e
  o Task foi agendado TRES vezes no total -- duas antes do redrive e uma depois --
  contra um teto declarado de DUAS (`MaxAttempts: 1`). Sem a recusa, a SF-SFNX-001
  dispararia sobre uma contagem que soma as tentativas de antes e as de depois, e o
  arquivo nao sustenta essa soma como uma coisa so. Com ela, sai
  `sfn.unresolved: execution_redriven` (pelo evento) e
  `sfn.unresolved: redrive_in_execution` (pela derivacao, no lugar do
  `sfn.retry_observado`), e a SF-SFNX-001 fica CALADA. As tres tentativas e os tres
  JobRuns continuam publicados: o que se recusa e a COMPARACAO. SF-SFN-002 dispara
  junto, pelo lado da DEFINICAO, e deve: o retrier reexecuta o job inteiro.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.state_machine
  - sfn.task
  - sfn.unresolved
expects_rules: [SF-SFN-002]
```

#### `fixtures/sfn_history/parallel_estado_homonimo/input/historico/execucao.json`

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T11:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T11:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "Preparacao"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T11:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T11:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_dddddddd0\", \"JobName\": \"preparacao\"}"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T11:04:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T11:04:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "Preparacao"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T11:04:02.000000+00:00", "type": "ParallelStateEntered", "stateEnteredEventDetails": {"name": "Cargas"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T11:04:03.000000+00:00", "type": "ParallelStateStarted"},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T11:04:04.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "Carga"}},
    {"id": 10, "previousEventId": 8, "timestamp": "2026-09-18T11:04:04.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "Carga"}},
    {"id": 11, "previousEventId": 9, "timestamp": "2026-09-18T11:04:05.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 12, "previousEventId": 10, "timestamp": "2026-09-18T11:04:05.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 13, "previousEventId": 11, "timestamp": "2026-09-18T11:04:06.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_dddddddd1\", \"JobName\": \"carga-ramo-a\"}"}},
    {"id": 14, "previousEventId": 12, "timestamp": "2026-09-18T11:04:06.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_dddddddd2\", \"JobName\": \"carga-ramo-b\"}"}},
    {"id": 15, "previousEventId": 13, "timestamp": "2026-09-18T11:20:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 16, "previousEventId": 14, "timestamp": "2026-09-18T11:21:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 17, "previousEventId": 16, "timestamp": "2026-09-18T11:21:01.000000+00:00", "type": "ParallelStateSucceeded"},
    {"id": 18, "previousEventId": 17, "timestamp": "2026-09-18T11:21:02.000000+00:00", "type": "ParallelStateExited", "stateExitedEventDetails": {"name": "Cargas"}},
    {"id": 19, "previousEventId": 18, "timestamp": "2026-09-18T11:21:03.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

#### `fixtures/sfn_history/parallel_estado_homonimo/meta.yaml`

```yaml
name: parallel_estado_homonimo
proves: >
  AC3. Dois ramos de um `Parallel` com um estado chamado `Carga` em cada: as entradas
  (ids 9 e 10) apontam para o MESMO `ParallelStateStarted` e nenhuma esta na cadeia da
  outra. Nenhum `sfn.attempt` de `Carga` e emitido, nenhum `sfn.job_run` dela e ligado,
  e sai `sfn.unresolved: state_name_in_concurrent_branches` com o nome. Antes, o
  segundo ramo saia com `attempt_index: 2` -- um indice que o arquivo nao sustenta, e
  que e o `subject.symbol` por onde SF-SFNX-002 e SF-SFNX-003 apontam o achado. O
  estado de nome UNICO do mesmo historico (`Preparacao`) continua virando tentativa com
  indice e JobRun: a recusa e por NOME, nao pelo arquivo. Sem ASL no case, entao a
  lacuna do confronto sai em `asl_absent` e a SF-SFNX-001 fica em `skipped`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: []
```

#### `fixtures/sfn_history/retry_em_ramo_unico/input/historico/execucao.json`

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T13:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T13:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaComLaco"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T13:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T13:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_eeeeeeee1\", \"JobName\": \"carga-com-laco\"}"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T13:10:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_eeeeeeee1 FAILED"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T13:10:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaComLaco"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T13:10:02.000000+00:00", "type": "ChoiceStateEntered", "stateEnteredEventDetails": {"name": "TentarDeNovo"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T13:10:03.000000+00:00", "type": "ChoiceStateExited", "stateExitedEventDetails": {"name": "TentarDeNovo"}},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T13:10:04.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaComLaco"}},
    {"id": 10, "previousEventId": 9, "timestamp": "2026-09-18T13:10:05.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 11, "previousEventId": 10, "timestamp": "2026-09-18T13:10:06.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_eeeeeeee2\", \"JobName\": \"carga-com-laco\"}"}},
    {"id": 12, "previousEventId": 11, "timestamp": "2026-09-18T13:20:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_eeeeeeee2 FAILED"}},
    {"id": 13, "previousEventId": 12, "timestamp": "2026-09-18T13:20:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaComLaco"}},
    {"id": 14, "previousEventId": 13, "timestamp": "2026-09-18T13:20:02.000000+00:00", "type": "ChoiceStateEntered", "stateEnteredEventDetails": {"name": "TentarDeNovo"}},
    {"id": 15, "previousEventId": 14, "timestamp": "2026-09-18T13:20:03.000000+00:00", "type": "ChoiceStateExited", "stateExitedEventDetails": {"name": "TentarDeNovo"}},
    {"id": 16, "previousEventId": 15, "timestamp": "2026-09-18T13:20:04.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaComLaco"}},
    {"id": 17, "previousEventId": 16, "timestamp": "2026-09-18T13:20:05.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 18, "previousEventId": 17, "timestamp": "2026-09-18T13:20:06.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_eeeeeeee3\", \"JobName\": \"carga-com-laco\"}"}},
    {"id": 19, "previousEventId": 18, "timestamp": "2026-09-18T13:32:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 20, "previousEventId": 19, "timestamp": "2026-09-18T13:32:01.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

#### `fixtures/sfn_history/retry_em_ramo_unico/meta.yaml`

```yaml
name: retry_em_ramo_unico
proves: >
  AC4, e e a NEGATIVA de D1. O MESMO estado entra TRES vezes, uma depois da outra, por
  um `Choice` que volta: as entradas (ids 2, 9 e 16) se alcancam pela cadeia de
  `previousEventId`, e por isso o nome continua identificando um estado so. Saem tres
  `sfn.attempt` com `attempt_index` 1, 2 e 3, e tres `sfn.job_run` ligados a eles. E ela
  que mata a troca do teste de ancestralidade por um teste so de CONTAGEM de entradas:
  com "mais de uma entrada => recusa", esta fixture ficaria vermelha, e a SF-SFNX-001
  perderia a medida que existe para fazer. SEM ASL de proposito -- com um teto
  declarado, ela seria uma segunda fixture exatamente na fronteira da `expr` da
  SF-SFNX-001, territorio de `tests/test_rules_threshold_mutation.py`, que ja tem
  `retry_dentro_do_declarado`. Aqui a lacuna do confronto sai em `asl_absent`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: []
```

### 3. `REQUIRED_FIXTURES`

`REQUIRED_FIXTURES` em `tests/test_fixtures_golden_sfn_history.py` é lista escrita à mão
de propósito — fixture removida em silêncio some do `parametrize` sem que nada reclame.
Cada entrada leva o comentário que diz **o que ela prova**, no estilo das que já estão
lá. Acrescente, ao fim do conjunto (depois de `"historico_sem_asl",`):

```python
    # Execucao RETOMADA: `ExecutionRedriven` no historico, e o ASL com `MaxAttempts` ao
    # lado. O confronto com o teto declarado e RECUSADO (`redrive_in_execution`), e a
    # SF-SFNX-001 fica calada sobre uma contagem que soma as tentativas de antes e as
    # de depois do redrive. As tentativas continuam publicadas.
    "execucao_com_redrive",
    # Dois ramos de um `Parallel` com um estado de mesmo nome: o nome nao identifica um
    # estado, nenhum `sfn.attempt` dele sai, e o de nome unico do mesmo historico
    # continua virando tentativa com indice.
    "parallel_estado_homonimo",
    # A NEGATIVA das duas acima, e a que impede a correcao de virar regressao: o mesmo
    # estado reentrado TRES vezes em sequencia continua numerado 1..3. E ela que mata a
    # troca do teste de ancestralidade por um teste so de contagem de entradas.
    "retry_em_ramo_unico",
```

### 4. Gerar o golden, e ler o diff

```bash
git add fixtures/sfn_history/execucao_com_redrive fixtures/sfn_history/parallel_estado_homonimo fixtures/sfn_history/retry_em_ramo_unico
python scripts/regen_fixtures.py execucao_com_redrive parallel_estado_homonimo retry_em_ramo_unico
```

Por **nome** é instantâneo. **Nunca** `python scripts/regen_fixtures.py` sem argumento
aqui: ele regenera o repositório inteiro, leva mais de 10 minutos e estoura o timeout de
2 minutos da ferramenta — se um dia for preciso, mande-o para segundo plano.

Leia os três `expected/facts.json` antes de seguir. O que tem de estar lá:

| fixture | `sfn.attempt` | `sfn.job_run` | razões de `sfn.unresolved` | `sfn.retry_observado` |
|---|---|---|---|---|
| `execucao_com_redrive` | 3, índices 1, 2 e 3 | 3 | `execution_redriven`, `redrive_in_execution` | **nenhum** |
| `parallel_estado_homonimo` | 1 (`Preparacao#1`) | 1 | `state_name_in_concurrent_branches`, `asl_absent` | nenhum |
| `retry_em_ramo_unico` | 3, índices 1, 2 e 3 | 3 | `asl_absent` | nenhum |

E então:

```bash
python -m pytest tests/test_fixtures_golden_sfn_history.py -q
```

Se `expects_rules` ou `expects_kinds` de algum `meta.yaml` divergir, **leia o
`expected/findings.json` gerado e corrija o `meta.yaml`** — a previsão deste plano é que
`execucao_com_redrive` produza `SF-SFN-002` (pelo lado da definição, como
`retry_acima_do_declarado`) e que as outras duas não produzam achado nenhum. A previsão
pode estar errada; o golden gerado é que é a medida.

### 5. O registro que esta tarefa move

`docs/superpowers/STATUS.md`, tabela *Números correntes*, linha **Fixtures golden** —
troca de prefixo, o resto da linha fica como está. Antes → depois:

```text
| Fixtures golden | **551** em 59 domínios — a **1** acrescida é
| Fixtures golden | **554** em 59 domínios — as **3** acrescidas são `fixtures/sfn_history/execucao_com_redrive`, `fixtures/sfn_history/parallel_estado_homonimo` e `fixtures/sfn_history/retry_em_ramo_unico` (2026-09-20, feature `docs/sdd/SFN_TENTATIVA/`): a execução retomada por redrive, em que o confronto com o teto declarado é recusado em vez de comparado; os dois ramos de um `Parallel` com um estado de mesmo nome, em que nenhum `sfn.attempt` daquele nome é emitido; e a NEGATIVA dos dois — o mesmo estado reentrado três vezes em sequência, que continua numerado 1, 2 e 3 e mata a troca do teste de ancestralidade por um teste só de contagem de entradas. O domínio continua sendo o mesmo, e nenhum golden existente mudou de comportamento. Leitura anterior de **551** em 59 domínios — a **1** acrescida é
```

**Se `551` não for o que `python scripts/check_status_numbers.py --strict` medir na
hora, publique o número do gate** e ajuste os dois (o novo e o "leitura anterior").

### 6. Rodar e ver passar, e os gates vizinhos

```bash
python scripts/check_status_numbers.py --strict
```

`0 divergencia(s)` — é o `verified_by` da **AC7**.

Corpus de fixture (`docs/gates-por-mudanca.md`, *Acrescentar um CORPUS de fixture novo*)
— o domínio `sfn_history` **já existe e já é reivindicado**, então nada muda em
`tests/test_fixtures_kind_coverage.py::_dominios_reivindicados` nem em
`scripts/verify_wheel.py`; o que estes comandos conferem é que as fixtures novas não
quebram a cobertura por kind nem a de wheel:

```bash
python -m ruff check tests/test_fixtures_golden_sfn_history.py
python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q
python -m pytest tests/test_rules_catalog_reachability.py tests/test_rules_threshold_mutation.py -q
python -m pytest tests/test_harness_untrusted.py tests/test_arvore_versionada.py -q
python -m pytest tests/test_status_numbers_gate.py tests/test_docs_coverage.py -q
python -m pytest tests/test_fixtures_golden_sfn_history.py tests/test_fixtures_golden_stepfunctions.py -q
python scripts/check_vnext_claims.py
```

`test_rules_threshold_mutation.py` tem de passar **sem mexer em
`FRONTEIRA_SEM_GOLDEN`** — é o ponto 3 das medidas, e é por isso que
`retry_em_ramo_unico` não tem ASL.

O gate de lastro reprova pelos bytes de `.py` (`tests/test_fixtures_golden_sfn_history.py`
cresceu; as doze fixtures são `.json` e `.yaml` e não contam). **Remedie pelos ids da
saída**, como em T1.

### 7. Commit

```bash
git add fixtures/sfn_history tests/test_fixtures_golden_sfn_history.py docs/superpowers/STATUS.md docs/harness/CODEINTEL-GAP.md docs/claims.lock.json
git commit -F "$TEMP/sfn_tentativa_t3.txt"
```

```text
test(fixtures): three Step Functions histories for the redrive and the homonym

`execucao_com_redrive` pairs a redriven history with the ASL that declares the
ceiling: without the refusal SF-SFNX-001 would fire on a count that spans the
redrive, and with it the rule stays silent. `parallel_estado_homonimo` has two
branches of a `Parallel` carrying a state with the same name, and no
`sfn.attempt` of that name comes out. `retry_em_ramo_unico` is the negative of
both: the same state re-entered three times in sequence stays numbered 1..3,
and it is what kills replacing the ancestry test with a plain count of entries.

No existing golden changed behaviour: none of the eleven fixtures already in the
corpus has more than one `TaskStateEntered` per state name, and none uses the
three event types that joined the known list.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

## T4 — as lacunas 8 e 9 do documento de conhecimento

> Fecha **AC6**.

### 1. O que falha antes

Esta tarefa não tem teste próprio: o vermelho é o do **lock de superfície**, que acusa o
documento de `knowledge/` editado enquanto `docs/surface.lock.json` ainda declara os
bytes antigos (regra 26 do `CLAUDE.md`) — é ele que o frontmatter nomeia como `test`. Ao
lado dele, `python scripts/verify_offline_bundle.py` reprova enquanto o `sha256` do
manifesto não for regravado.

O lock de **fontes** não fica vermelho aqui: **nenhuma URL nova** entra. O que as duas
lacunas passam a dizer sai da mesma página `API_HistoryEvent` que o documento já cita e
que já está em `knowledge/sources.lock.json`.

### 2. As edições em `knowledge/stepfunctions/execution-history.md`

#### 2.1 §4 — uma frase abaixo da tabela

Logo depois do parágrafo que começa em
`**Nenhuma das três atribui custo, e a recusa é de desenho.**`, acrescente:

```markdown
**A `SF-SFNX-001` não fala sobre execução retomada.** Com `ExecutionRedriven` no
histórico, `build_sfn_retry_observado` emite `sfn.unresolved: redrive_in_execution` no
lugar do fact que a regra ancora, e ela sai em `skipped` — "não perguntei", nunca "está
tudo bem". A razão está na lacuna 9.
```

#### 2.2 §5, lacuna 8 — reescrita inteira

Substitua o item **8** inteiro por:

```markdown
8. **O `previousEventId` por RAMO não está publicado, e é a premissa de todo o
   pareamento — inclusive da recusa nova.** Nas duas páginas da API relidas em
   2026-09-20, o campo tem uma descrição e só uma: "The id of the previous event." Nada
   ali diz que, dentro de um `Parallel` ou de um `Map`, o anterior é o do **mesmo ramo**.
   **O que mudou em 2026-09-20** (feature `docs/sdd/SFN_TENTATIVA/`): o extrator deixou
   de numerar estados de mesmo nome em ramos concorrentes. Para um nome, ele junta os
   `TaskStateEntered` distintos a que os `TaskScheduled` daquele nome se encadeiam; se
   dois deles forem mutuamente **não-ancestrais** — nenhum alcança o outro subindo
   `previousEventId` —, nenhum `sfn.attempt` daquele nome é emitido, nenhum `sfn.job_run`
   dele é ligado, e sai `sfn.unresolved: state_name_in_concurrent_branches`. Antes disso,
   o contador era chaveado só pelo nome, e a primeira tentativa do segundo ramo saía com
   `attempt_index: 2` — um índice que o arquivo não sustenta, e que é o `subject.symbol`
   por onde `SF-SFNX-002` e `SF-SFNX-003` apontam o achado. Reentrada **sequencial** —
   um retry, ou um `Choice` que volta — não cai ali: a entrada anterior está na cadeia da
   seguinte, as duas se alcançam, e a numeração 1..n continua valendo. **O critério
   depende da premissa, e errar nela continua sendo recusa a mais, nunca afirmação a
   menos**: se o encadeamento não fosse por ramo, duas entradas sequenciais poderiam
   parecer não-ancestrais, e o efeito seria recusar um estado que o arquivo sustenta. O
   que destrava: **um histórico real de execução com `Parallel` ou `Map`** — conferir se
   a cadeia de um ramo pula os `id` do outro é uma leitura de dois minutos —, ou uma
   frase oficial. O corpus sintético (`parallel_estado_homonimo` e `retry_em_ramo_unico`)
   exercita o **mecanismo**, não a premissa.
```

#### 2.3 §5, lacuna 9 — reescrita inteira

Substitua o item **9** inteiro por:

```markdown
9. **A lista de tipos conhecidos do extrator já é a publicada, e o redrive virou recusa
   em vez de medida.** Medido na releitura de 2026-09-20: os `Valid Values` do campo
   `type` do `HistoryEvent` trazem 62 tipos, e `_TIPOS_CONHECIDOS` tinha 59. **Em
   2026-09-20** (feature `docs/sdd/SFN_TENTATIVA/`) os três que faltavam entraram, e não
   entraram iguais: `EvaluationFailed` e `MapRunRedriven` são tipo conhecido que não
   produz fact nem recusa, como os demais `MapRun*`; `ExecutionRedriven` entra com razão
   própria. **`ExecutionRedriven` é a execução RETOMADA**, e ele muda o que "quantas
   vezes o Task foi agendado" significa: um redrive reagenda o Task dentro da MESMA
   execução, e nada no arquivo separa as tentativas de antes das de depois. O extrator
   emite `sfn.unresolved: execution_redriven` por evento, e `build_sfn_retry_observado`
   emite `sfn.unresolved: redrive_in_execution` **no lugar** do `sfn.retry_observado`
   para o artefato que tem uma delas — as tentativas continuam medidas e publicadas, e o
   que se recusa é a **comparação** com o teto declarado no ASL. **O que continua aberto
   é MEDIR o redrive em vez de recusá-lo.** A forma do evento `ExecutionRedriven` não foi
   lida: se ele traz um contador de redrive, ou o `id` do evento em que a retomada
   começou, não está em nenhuma das páginas citadas aqui (U3 de
   `docs/sdd/SFN_TENTATIVA/define.md`). Com esse campo, as tentativas de antes e as de
   depois se separariam e o confronto voltaria a existir, uma contagem por rodada. O que
   destrava: **a página do `HistoryEvent` lida com esse foco**, ou um histórico real com
   redrive.
```

### 3. Regravar os dois registros do documento

```bash
python -c "import json; from pathlib import Path; from sparkforge.tools.offline import _content_sha256; p = Path('knowledge/offline-manifest.json'); m = json.loads(p.read_text(encoding='utf-8')); doc = 'knowledge/stepfunctions/execution-history.md'; m['documents'] = [d for d in m['documents'] if d['path'] != doc] + [{'path': doc, 'title': 'execution-history', 'sha256': _content_sha256(Path(doc))}]; m['documents'].sort(key=lambda d: d['path']); p.write_bytes((json.dumps(m, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))"
python scripts/check_surface_lock.py --update
```

O hash tem de vir de `sparkforge.tools.offline._content_sha256` e de mais nada: a
docstring dela diz por quê — *"hash calculado de um jeito e conferido de outro e o
defeito que o gate existe para pegar"* —, e ela remove todo `CR` em vez de traduzir
`CRLF`, porque um manifesto gravado no Windows já reprovou os 43 documentos no Linux.

`check_surface_lock.py --update` imprime o crescimento em bytes. **Anote o número que
ele imprimir e declare-o no corpo do commit** (regra 26: acrescentar peso não é
proibido, é obrigado a dizer de quanto foi).

### 4. Rodar e ver passar

```bash
python -m pytest "tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches" -q
python scripts/verify_offline_bundle.py
```

O segundo é o `verified_by` da **AC6**: `"ok": true`.

### 5. Gates vizinhos

*Editar um documento em `knowledge/`* (`docs/gates-por-mudanca.md`), **um por vez**:

```bash
python -m pytest tests/test_offline_expansion.py -q
python -m pytest tests/test_surface_lock.py tests/test_refresh_knowledge.py -q
python -m pytest tests/test_knowledge_freshness.py tests/test_docs_coverage.py -q
python -m pytest tests/test_reference_docs.py tests/test_bootstrap_budget.py -q
python -m pytest tests/test_capability_parity.py -q
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

- `test_refresh_knowledge.py` passa **sem** `python scripts/refresh_knowledge.py --update
  --offline`, porque nenhuma URL entra ou sai da seção `## Fontes`. Se ele reclamar,
  alguma URL foi acrescentada sem querer — rode
  `python scripts/refresh_knowledge.py --update --offline` e inclua
  `knowledge/sources.lock.json` no commit.
- `check_vnext_claims.py` deve sair em `0 divergencia(s)` **sem remediação**: T4 não toca
  `.py` nenhum, e nenhuma alegação de `docs/vnext/` ou `docs/harness/` lê bytes de
  `knowledge/` (medido: `532870` não aparece em `docs/claims.lock.json`).

### 6. Commit

```bash
git add knowledge/stepfunctions/execution-history.md knowledge/offline-manifest.json docs/surface.lock.json
git commit -F "$TEMP/sfn_tentativa_t4.txt"
```

```text
docs(knowledge): rewrite gaps 8 and 9 for what the extractor now refuses

Gap 8 keeps naming the unpublished premise — `previousEventId` being the one of
the SAME branch — and now records what rests on it: attempts of a state name
that appears in mutually non-ancestral entries are refused, not numbered.
Getting the premise wrong still means refusing more, never asserting less.

Gap 9 stops describing a missing list. The three types joined
`_TIPOS_CONHECIDOS`, which now equals the 62 the API publishes, and the redrive
became a named refusal on both sides. What stays open is MEASURING the redrive
instead of refusing it, and the page that would unlock it is named.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S1PcV3ZaVfpAsJGbj2mgUK
```

## Antes de fechar a feature

```bash
python -m sparkforge.adapters.cli sdd stamp --repo . docs/sdd/SFN_TENTATIVA/plan.md
python -m sparkforge.adapters.cli sdd check --repo . --feature SFN_TENTATIVA
```

(A sintaxe do `stamp` é `sdd stamp --repo . <artefato>`; não existe `--feature`/`--phase`
nesse verbo.)

Com os quatro commits de pé, a suíte **em lotes, um por vez**, pela receita de
`tests/test_suite_batches.py::LOTES` — nunca a suíte inteira num processo só, e nunca com
edição na árvore ao mesmo tempo. **Nenhum arquivo de teste nasce nesta feature**, então
`LOTES` não muda: `test_sfn_history.py` continua no lote que já o leva, e
`test_fixtures_golden_sfn_history.py` também.

Por fim, o **SC2** do `define`:

```bash
python -m pytest tests/test_fixtures_golden*.py -q
```

**Sem regenerar**, e **em segundo plano**: ele leva ~39 minutos e estoura o timeout de 2
minutos da ferramenta. O único golden de achado que esta feature toca é
`fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json`, regenerado em T1
na mesma tarefa que mudou a prosa da regra. Qualquer outro golden que apareça vermelho é
notícia, não ruído — leia o diff antes de tocar em nada.

E o **SC3**: as razões distintas de `sfn.unresolved` do módulo, **20 → 23**
(`execution_redriven` e `state_name_in_concurrent_branches` no extrator,
`redrive_in_execution` na derivação), conferidas contra as duas listas da docstring de
`sparkforge/facts/sfn_history.py`.

## Dúvidas

O manifesto do design foi seguido; estes são os pontos em que ele ficou curto, ou em que
o plano precisou decidir. Todos estão repetidos no corpo, onde importam.

1. **`docs/surface.lock.json` falta no manifesto, e é obrigatório.** Editar
   `knowledge/stepfunctions/execution-history.md` move `knowledge.total_bytes` e
   `knowledge.by_name_sha256`, porque `measure_surface` mede
   `measure_directory(knowledge, "*.md")` byte a byte do conteúdo. Sem o lock atualizado,
   `tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches` fica
   vermelho. T4 o inclui. **Medido nesta árvore: `knowledge.total_bytes` = 532870, e
   `python scripts/check_surface_lock.py` em `0 divergencia(s)` antes de começar.**
2. **`fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json` falta no
   manifesto, e também é obrigatório.** O `explanation` da regra viaja dentro de cada
   `Finding`, e o D5 manda a prosa da `SF-SFNX-001` entrar no mesmo commit da mudança de
   comportamento. Medido: `SF-SFNX-001` aparece em **um só** golden do repositório, e é
   esse. T1 o inclui.
3. **O manifesto nomeia cada fixture nova pelo `meta.yaml`.** O plano lê isso como "a
   fixture inteira" — `meta.yaml`, `input/` e o `expected/` que o regen escreve. Se a
   intenção era outra, é aqui que se corrige.
4. **`docs/guia/usos/step-functions.md` foi movido do agrupamento AC6 para T1 e T2.** O
   AC6 fala do documento de `knowledge/` e do bundle offline; o guia é o registro manual
   do extrator, e a regra da casa manda a tarefa que cria a recusa mover o registro dela.
5. **O nome da recusa do caso homônimo é decisão deste plano:**
   `state_name_in_concurrent_branches`. `state_name_ambiguous` já existe na derivação com
   outro significado (o ASL declara dois estados de mesmo nome), e reusá-la juntaria duas
   lacunas diferentes num nome só.
6. **`retry_em_ramo_unico` nasce sem ASL.** Com um, ela seria uma segunda fixture na
   fronteira exata da `expr` da `SF-SFNX-001`, território de `FRONTEIRA_SEM_GOLDEN`, que
   `tests/test_rules_threshold_mutation.py` compara por igualdade exata. Sem ASL ela prova
   os índices 1, 2 e 3, que é o que o AC4 pede, e a lacuna do confronto sai em
   `asl_absent`.
7. **`expects_rules` de `execucao_com_redrive` é uma previsão.** O plano prevê
   `[SF-SFN-002]` — o mesmo que `retry_acima_do_declarado` produz pelo lado da definição,
   menos a `SF-SFNX-001`, que é exatamente o que esta feature cala. O `findings.json`
   gerado pelo regen é que é a medida; se divergir, o `meta.yaml` é que se corrige.
