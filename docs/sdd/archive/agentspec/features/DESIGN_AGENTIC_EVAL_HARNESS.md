# DESIGN: Agentic Eval Harness

> Technical design for implementing Agentic Eval Harness

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AGENTIC_EVAL_HARNESS |
| **Date** | 2026-09-10 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_AGENTIC_EVAL_HARNESS.md](./DEFINE_AGENTIC_EVAL_HARNESS.md) |
| **Status** | ✅ Complete (Built) |

> **Desvios do build (2026-09-11).** Este documento é registro histórico. O build divergiu dele em pontos que mudam o uso, e a lista completa com as razões está em `.claude/sdd/reports/BUILD_REPORT_AGENTIC_EVAL_HARNESS.md` ("Deviations from Design"). Os que mudam como se usa:
> - o verbo não é `sparkforge eval …`, e sim `python -m sparkforge.evals grade|compare` (`sparkforge/evals/cli.py`), porque `tests/test_harness_boundary.py` proíbe runtime importar avaliação. Por isso as linhas de `_core.py`/`cli.py` do diagrama e do manifesto não existem;
> - a CLI recebe nomes sob bases fixas, e não caminhos;
> - o runner roda numa cópia de prova sem gabarito;
> - `suite.py` lê `fase0.xml` sem parser XML;
> - a âncora `abst-03` é `plan.unresolved`.

**Design confidence: 0.80.** Nenhum domínio do KB do agentspec (`testing`, `python`, `pydantic`, `genai`) traz padrão de avaliação de agente sobre transcript. O que sustenta o desenho é o codebase:

- `sparkforge/collect/host_usage.py` — leitura do transcript com lacunas nomeadas;
- `sparkforge/facts/benchmark.py` — dois lados comparados, com recusa por nome;
- o par `_cmd_*` → `_core.*` → módulo puro de `sparkforge/adapters/`;
- os registros manuais de extrator conferidos nos testes.

Todo dado de formato citado abaixo foi medido, não suposto.

**Premissas do DEFINE resolvidas nesta fase:**

| ID | Resultado | Como |
|----|-----------|------|
| A-001 | Confirmada e ampliada | Transcript local desta sessão, nada commitado. 216 linhas `user`/`assistant`, todas com `version`, `sessionId`, `timestamp`, `uuid`. 131/131 mensagens de assistente com `message.model`. 37 blocos `tool_use` com chaves `caller,id,input,name,type`. `tool_result` em linhas `user` com `content` `str` (73) ou `list` (3), `is_error` opcional (8), e pareamento por `tool_use_id` |
| A-002 | Parcial: as flags existem, o arquivo ainda não foi visto | `claude --help`: `-p`, `--session-id <uuid>`, `--output-format stream-json`, `--no-session-persistence` (logo, `-p` persiste por padrão), `--mcp-config`, `--strict-mcp-config`, `--model`, `--max-budget-usd`. A Task B1 do build faz um smoke de uma pergunta antes do resto do runner |
| A-004 | Confirmada | 82 facts `*.unresolved` em `fixtures/**/expected/facts.json`. Âncoras escolhidas: `glue.run_cost.unresolved` (`finops/no_dpu_no_cost`), `bench.unresolved` (`bench/one_side_missing`) e `glue.utilization.unresolved` (`waste/sem_cloudwatch`) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  FORA DO PACOTE (gasta token, nunca no CI)                               │
│                                                                          │
│  scripts/run_agentic_eval.py                                             │
│    para cada pergunta de suite.yaml:                                     │
│      claude -p --session-id <uuid> --mcp-config <sparkforge> ... "<q>"   │
│      copia ~/.claude/projects/*/<uuid>.jsonl → <out>/<run_id>/<qid>.jsonl│
│    grava <out>/<run_id>/run.json (argv, claude --version, data)          │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  arquivos (fora do repo)
┌───────────────────────────────▼──────────────────────────────────────────┐
│  sparkforge/  (só lê arquivo; sem provider, sem subprocess)              │
│                                                                          │
│  facts/host_transcript.py ──► Fact: host.transcript  host.tool_call      │
│   (extrator, EMITTED_KINDS)        host.final_answer host.usage          │
│                                    host.transcript.unresolved            │
│            │                                                             │
│            ▼                                                             │
│  evals/suite.py ──► Suite (perguntas resolvidas + sha256)                │
│   lê evals/agentic/<s>/suite.yaml + fase0.xml#N                          │
│            │                                                             │
│            ▼                                                             │
│  evals/grade.py    facts × suite ──► scorecard.json (1 por run)          │
│            │                                                             │
│            ▼                                                             │
│  evals/compare.py  N scorecards A × N scorecards B ──► compare.json      │
│                                                                          │
│  adapters/_core.py  eval_grade() / eval_compare()                        │
│  adapters/cli.py    `sparkforge eval grade` / `sparkforge eval compare`  │
└──────────────────────────────────────────────────────────────────────────┘
        ▲                                   ▲
        │ golden (CI)                       │ ground truth (versionado)
  fixtures/host_transcript/<caso>/    evals/fase0.xml (intocado)
                                      evals/agentic/fase0/suite.yaml
```

Dependências sempre descem, sem ciclo: `cli` → `_core` → `evals.*` → `facts.host_transcript` → `findings.models`. `facts/host_transcript.py` não importa nada de `evals/`, e `evals/` não importa nada de `adapters/`.

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/facts/host_transcript.py` | Extrator. Lê um JSONL do Claude Code e emite facts `host.*` com lacunas nomeadas. Reusa a validação de usage de `host_usage` | Python 3 stdlib (`json`), `Fact` de `sparkforge/findings/models.py` |
| `sparkforge/evals/suite.py` | Carrega `suite.yaml`, resolve `source: fase0.xml#N` para pergunta e resposta, valida o schema e calcula o `sha256` da suíte resolvida | PyYAML (já dependência do catálogo), `xml.etree` |
| `sparkforge/evals/grade.py` | Função pura: facts de N transcripts + `Suite` → scorecard (veredito por pergunta e agregados) | stdlib (`statistics.median_low`) |
| `sparkforge/evals/compare.py` | Função pura: dois conjuntos de scorecards → classes `pass`/`fail`/`mixed`, transições e recusas | stdlib |
| `sparkforge/adapters/_core.py` | `eval_grade(suite_dir, transcripts_dir)` e `eval_compare(baseline_dir, candidate_dir)`: I/O de arquivo e montagem do payload | já existente |
| `sparkforge/adapters/cli.py` | Verbo aninhado `eval` com `grade` e `compare`, no molde de `release describe/diff` | argparse, já existente |
| `evals/agentic/fase0/suite.yaml` | Ground truth agêntico: 10 referências a `fase0.xml` e 3 perguntas de abstention | YAML |
| `scripts/run_agentic_eval.py` | Runner fora do pacote: uma sessão `claude -p` por pergunta, cópia do transcript persistido e `run.json` | Python 3 stdlib (`subprocess`, `uuid`) |
| `fixtures/host_transcript/` | Corpus sintético: transcripts por desfecho, suíte mínima, scorecards e compare esperados | JSONL/YAML/JSON |

---

## Key Decisions

### Decision 1: O extrator emite `Fact` e mora em `sparkforge/facts/`, não em `collect/`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** `host_usage.py` mora em `collect/` e devolve um dict, porque só alimenta o `economy report`. O harness precisa de sequência de tools, resposta e usage por arquivo, com procedência, e o brainstorm escolheu "compor sobre facts, como `benchmark`". Em `sparkforge/`, extrator é o módulo que declara `EMITTED_KINDS` (critério de `test_harness_untrusted.py` e de `docs/harness/BASELINE.md`), e os extratores que leem arquivo local ficam em `facts/` (`event_log.py`, `parquet_footer.py`).

**Choice:** `sparkforge/facts/host_transcript.py` com `EXTRACTOR_ID = "host_transcript@0.1.0"`, `EMITTED_KINDS` fechado e `extract_host_transcript_path(path) -> list[Fact]`. A validação numérica de usage vem de `sparkforge.collect.host_usage._somar_usage`, importada e não copiada. `host_usage.py` fica intocado e segue servindo o `economy report`.

**Rationale:** `Fact` traz `provenance.extractor`, `schema_version` e `sort_facts`, e entra no mesmo corpus golden de todo extrator. Os testes de cobertura de kind passam a verificar os kinds `host.*`, em vez de eles existirem sem ninguém conferir.

**Alternatives Rejected:**
1. Estender `host_usage.py` para devolver também as tools — rejeitada: mistura o contrato do `economy report` (soma) com o do eval (sequência), e um dict sem procedência escapa das duas listas de cobertura de kind.
2. Extrator em `collect/` emitindo `Fact` — rejeitada: `collect/` é a porta de quem busca artefato remoto (AWS). Ler arquivo local é o papel de `facts/`.

**Consequences:**
- Aceitamos mexer em quatro registros manuais: as duas tuplas `EXTRACTORS` (`tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`), um módulo golden para o domínio novo de fixture e a medida de snippet (Decision 7).
- Ganhamos golden nas duas direções e a garantia de que todo `host.transcript.unresolved` é exercitado (`test_every_unresolved_kind_is_exercised`).

---

### Decision 2: `grade` e `compare` ficam fora do motor de regras

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** A regra 11 diz "custo é fact, limiar é regra". O `benchmark` emite facts `bench.*` que o catálogo julga por limiar (`SF-BENCH-002`). O eval poderia seguir o mesmo caminho: facts `eval.*` e regras `SF-EVAL-*`.

**Choice:** `evals/grade.py` e `evals/compare.py` são funções puras que devolvem scorecard e compare como dict JSON. Não emitem `Fact`, não declaram `EMITTED_KINDS` e não criam regra.

**Rationale:** Não há limiar no eval. O veredito é igualdade contra ground truth (`correct`/`wrong`) ou pertinência (`missing`), e as classes do compare são definições fechadas (`k == N`, `k == 0`), não números escolhidos. Uma regra `SF-EVAL-*` precisaria de um limiar ("regressão se cair X%"), que é justamente o veredito agregado que o DEFINE recusou. Ficar fora do catálogo também evita derrubar o conjunto de registros de regra (rota, coordenador, `test_rule_scope_by_nature`, fixture que dispara etc.).

**Alternatives Rejected:**
1. Facts `eval.*` + regras `SF-EVAL-*` com limiar de regressão — rejeitada: inventa limiar, e com ele o gate que o YAGNI cortou.
2. `grade` emitindo `Fact` sem regra — rejeitada: um kind sem consumidor no catálogo não ganha nada, e ainda entra nas listas de cobertura.

**Consequences:**
- O scorecard não passa por `judge` nem vira finding, e isso é deliberado.
- Se um dia houver gate de PR, ele nasce como regra sobre um fact de compare. A decisão está registrada aqui para não ser tomada por acidente.

---

### Decision 3: O hash da suíte cobre a suíte RESOLVIDA, não o arquivo YAML

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** `suite.yaml` referencia `fase0.xml#N`. Se a resposta de `fase0.xml` mudar (o que o README registra ter acontecido três vezes com Q6/Q10), o YAML continua byte a byte igual, e dois scorecards de ground truth diferente pareceriam comparáveis.

**Choice:** `sha256` sobre a serialização canônica (`json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`) da lista de perguntas depois de resolvida: id, pergunta, resposta esperada, `required_tools`, `order` e `expects_abstention`.

**Rationale:** O que o `compare` precisa saber é se os dois lados foram pontuados contra o mesmo gabarito, não se o arquivo é o mesmo.

**Alternatives Rejected:**
1. Hash dos bytes de `suite.yaml` — rejeitada: não enxerga a mudança em `fase0.xml`.
2. Hash de `suite.yaml` + `fase0.xml` inteiros — rejeitada: uma mudança numa pergunta que a suíte nem referencia recusaria a comparação sem motivo.

**Consequences:**
- Reformatar o YAML (comentário, ordem de chave) não muda o hash.
- Mudar a pergunta ou a resposta muda, e o `compare` recusa com `suite_mismatch`.

---

### Decision 4: Normalização de nome de tool por regra fechada, sem consultar o parser da CLI

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** O mesmo verbo chega por dois canais: `mcp__<servidor>__sparkforge_judge` (o servidor pode vir prefixado por plugin) e Bash `sparkforge judge --facts x`. Descobrir o conjunto de verbos por `build_parser()` ou `TOOLS` faria `evals/` depender de `adapters/`, e inverteria a camada.

**Choice:** Três regras, em ordem:
1. `name` casa `^mcp__.+__sparkforge_(?P<v>[a-z0-9_]+)$`. Verbo = `v`, canal `mcp`.
2. `name == "Bash"`. O `input.command` é quebrado em `&&`, `||`, `;` e `|`. Em cada segmento, depois de tirar prefixos opcionais (`rtk`, `uv run`, `python -m`), o primeiro token precisa ser `sparkforge`. Verbo = token seguinte, mais `_` e o token depois dele quando esse casar `^[a-z][a-z-]*$`. `-` vira `_`. Canal `bash`. Vale só a primeira ocorrência por segmento.
3. Qualquer outro caso: canal `other`, verbo `null`. Entra em `other_calls` e em `tool_calls`, nunca em `required_tools`.

**Rationale:** É determinístico e testável isoladamente, e não adivinha. `sparkforge judge facts.json` dá `judge`, porque `facts.json` não casa o padrão. `sparkforge analyze pyspark lib/` dá `analyze_pyspark`.

**Alternatives Rejected:**
1. Conjunto de verbos lido de `build_parser()` — rejeitada: dependência para cima.
2. `tool_aliases` declarados em `suite.yaml` — rejeitada: joga para cada suíte um trabalho que a regra fechada resolve.

**Consequences:**
- Um verbo de três palavras vira os dois primeiros tokens (`code search`, por exemplo, sai `code_search`, que é também o nome da tool).
- Invocação por caminho absoluto do executável (`/usr/bin/sparkforge`) não casa. Cai em `other` e fica contada. A lacuna está registrada, não é silenciosa.
- Verbo de uma palavra seguido de argumento posicional só com letras minúsculas (`sparkforge judge cases`) vira `judge_cases`. O efeito é um falso `missing:[judge]`, visível no scorecard, nunca um acerto fabricado. O snippet foi rodado contra 9 casos em 2026-09-10 (MCP simples, MCP com prefixo de plugin, Bash com flag, cadeia `&&` com `rtk`, `python -m`, argumento com `.`, `ls`, tool não-Bash e comando vazio), e todos saíram como esta decisão descreve. O teste 15 fixa esta borda como caso conhecido.

---

### Decision 5: Listagem de transcripts por `os.scandir` plano

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** `tests/test_facts_scan.py::test_nenhum_modulo_varre_com_glob_cru` reprova por AST qualquer `.glob`, `.rglob` ou `.iglob` sob `sparkforge/`. `iter_source_files` tem teto de tamanho, e um arquivo pulado por tamanho viraria pergunta sem transcript sem ninguém ver.

**Choice:** `_core.eval_grade` lista o diretório com `os.scandir`, sem recursão, filtra `name.endswith(".jsonl")` e ordena por nome. O stem do arquivo é o `qid`. Pergunta da suíte sem arquivo sai `ungraded` com `transcript_not_found`. Arquivo sem pergunta correspondente vai para `unmatched_transcripts` no scorecard.

**Rationale:** Um diretório de run tem 13 arquivos conhecidos. Varredura com denylist não protege nada aqui, e o teto de tamanho perderia dado em silêncio.

**Alternatives Rejected:**
1. `Path.glob("*.jsonl")` — rejeitada: reprovada pelo gate de AST.
2. `iter_source_files(dir, "*.jsonl")` — rejeitada pelo teto de tamanho.

**Consequences:** Nenhuma pergunta some. Tudo é contado como `graded`, `ungraded` ou `unmatched`.

---

### Decision 6: O runner lê o transcript persistido pela sessão, não o `stream-json`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (sujeito ao smoke da Task B1) |
| **Date** | 2026-09-10 |

**Context:** A-002. O `stream-json` tem envelope próprio (`system`, `result`) que o extrator não conhece. O arquivo de sessão é o formato que A-001 conferiu.

**Choice:** O runner gera um `uuid4`, chama `claude -p --session-id <uuid> --output-format json ...` e, depois do exit, localiza `~/.claude/projects/*/<uuid>.jsonl` e o copia para `<out>/<run_id>/<qid>.jsonl`. O glob está em `scripts/`, fora do alcance do gate de AST, que só varre `sparkforge/`. O JSON final de stdout vai para `<qid>.result.json` e não é pontuado.

**Rationale:** Um formato só, o que já foi medido. O `result.json` fica guardado para o operador conferir e não entra no grader.

**Alternatives Rejected:**
1. `--output-format stream-json` como transcript — rejeitada: seria um segundo formato no extrator.
2. `--no-session-persistence` — rejeitada: apaga justamente o arquivo que o extrator lê.

**Consequences:**
- Se o smoke da Task B1 mostrar que `-p` não grava o arquivo, ou grava com outro envelope, esta decisão é reaberta antes das Tasks B2 a B4. O grader não muda, porque ele só lê arquivo.
- O runner imprime o caminho de cada transcript e nunca o grava no repo.

---

### Decision 7: O extrator não produz `subject.snippet`; a resposta vai para `attrs.answer`, truncada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** Transcript é conteúdo não confiável: `tool_use.input` e `tool_result.content` carregam texto arbitrário. `tests/test_harness_untrusted.py::extratores_com_snippet` roda todo `extract*_path` sobre o corpus e exige que `docs/harness/UNTRUSTED-CONTENT.md` nomeie quem produz snippet.

**Choice:**
- Nenhum fact `host.*` carrega texto de `input` ou de `tool_result`. `host.tool_call` guarda verbo canônico, canal, `is_error` e `result_bytes`.
- `host.final_answer` guarda em `attrs.answer` só o valor depois de `ANSWER:` na última linha que o contém, sem espaços nas pontas e truncado em 200 caracteres (`attrs.truncated: true` quando cortado).
- `subject` = `{"type": "transcript", "symbol": <stem>, "path": <caminho>}`, e o scorecard nunca copia `path`.
- `extract_host_transcript_path` rejeita barato quando o arquivo não é seu: sufixo diferente de `.jsonl`, ou primeira linha JSON sem `type`. Nesse caso devolve um único `host.transcript.unresolved` com `host_format_unknown`, sem ler o resto.

**Rationale:** O extrator não produz snippet, então `UNTRUSTED-CONTENT.md` não muda e a medida continua batendo. A rejeição barata mantém a medida perto dos ~4s sobre os `eventlog.jsonl` do corpus, que não têm `type` no envelope.

**Alternatives Rejected:**
1. Guardar o comando Bash inteiro para depuração — rejeitada: texto de terceiro dentro do fact, e o path pode conter diretório do usuário.
2. Resposta sem teto — rejeitada: um agente que despeja o transcript na linha `ANSWER:` levaria esse texto até o scorecard commitado.

**Consequences:**
- Depurar um veredito exige abrir o transcript fora do repo, e isso é intencional.
- O scorecard commitado carrega só ids, vereditos, contagens e respostas curtas.

---

### Decision 8: Agregados sem interpolação e sem nota composta

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** O DEFINE proíbe nota ponderada, e a regra 12 proíbe interpolar. A mediana de uma contagem par interpola (a média dos dois do meio).

**Choice:** Os agregados de custo usam `statistics.median_low` e `max`. As contagens de veredito são inteiros por coluna. Não existe campo `score`.

**Rationale:** Todo número publicado é um valor observado em algum run.

**Alternatives Rejected:** `statistics.median` — rejeitada: pode publicar um valor que nenhum run teve.

**Consequences:** Em N par, a mediana reportada é o menor dos dois do meio, e o nome do campo diz isso (`median_low`).

---

### Decision 9: Verbo só de CLI, declarado em `ALLOWED_CLI_ONLY`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-10 |

**Context:** `tests/test_capability_parity.py::test_every_cli_verb_has_an_mcp_tool_or_a_declared_reason` reprova verbo de CLI sem tool MCP e sem razão declarada. O YAGNI cortou a tool.

**Choice:** `"eval grade"` e `"eval compare"` entram em `ALLOWED_CLI_ONLY` com a razão: "pontua arquivo de transcript do disco de quem roda o agente; agente pontuando a si mesmo via MCP não é caso de uso (BRAINSTORM_AGENTIC_EVAL_HARNESS, YAGNI)". Nada entra em `parity.yaml`, `TOOLS` ou `surface.lock`.

**Rationale:** Precedente direto: `handoff`, `validate` e os verbos `agents`/`blackboard` estão na mesma lista com razão escrita.

**Alternatives Rejected:** Criar a tool só para passar no teste — rejeitada: move os sete registros sem caso de uso.

**Consequences:** A superfície MCP não cresce, e `check_surface_lock.py` não é tocado.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/facts/host_transcript.py` | Create | Extrator `host.*` (Decisions 1, 4, 7) | @python-developer | None |
| 2 | `sparkforge/evals/__init__.py` | Create | Pacote, docstring com o contrato (sem provider, sem subprocess) | @python-developer | None |
| 3 | `sparkforge/evals/suite.py` | Create | Carga, resolução e hash da suíte (Decision 3) | @python-developer | 2 |
| 4 | `sparkforge/evals/grade.py` | Create | Scorecard (Decisions 2, 8) | @python-developer | 1, 3 |
| 5 | `sparkforge/evals/compare.py` | Create | Classes, transições e recusas | @python-developer | 4 |
| 6 | `sparkforge/adapters/_core.py` | Modify | `eval_grade`, `eval_compare` (Decision 5) | @python-developer | 4, 5 |
| 7 | `sparkforge/adapters/cli.py` | Modify | Parser `eval {grade,compare}` e despacho `("eval","grade")`, `("eval","compare")` | @python-developer | 6 |
| 8 | `evals/agentic/fase0/suite.yaml` | Create | Ground truth agêntico: 10 refs e 3 perguntas de abstention | @sf-agent-evaluation-specialist | 3 |
| 9 | `fixtures/host_transcript/<caso>/input/transcript.jsonl` (≥ 10 casos) | Create | Corpus sintético, um por desfecho, incluindo `not_a_transcript` (primeira linha sem `type`) | @sf-agent-evaluation-specialist | 1 |
| 10 | `fixtures/host_transcript/<caso>/expected/facts.json` | Create | Golden do extrator | @test-generator | 1, 9 |
| 11 | `fixtures/host_transcript/_suite/suite.yaml` + `fixtures/host_transcript/<caso>/expected/scorecard.json` | Create | Suíte mínima das fixtures e golden do grade | @test-generator | 4, 9 |
| 12 | `fixtures/host_transcript/compare_<caso>/input/{baseline,candidate}/*.json` + `expected/compare.json` | Create | Golden do compare (estável, virada, suite_mismatch, single_sample, modelo diferente) | @test-generator | 5 |
| 13 | `tests/test_fixtures_golden_host_transcript.py` | Create | `FIXTURES = ROOT / "fixtures" / "host_transcript"`; golden de facts, scorecard e compare; determinismo (lote `goldens-2`) | @test-generator | 10, 11, 12 |
| 14 | `tests/test_evals_suite.py` | Create | Schema, resolução `fase0.xml#N`, hash estável a reformatação e sensível à resposta; âncoras de abstention existem no corpus (lote `d-e`) | @test-generator | 3, 8 |
| 15 | `tests/test_evals_normalize.py` | Create | Tabela de casos da Decision 4 (lote `d-e`) | @test-generator | 1 |
| 16 | `tests/test_evals_invariants.py` | Create | AST sob `sparkforge/`: 0 import de `anthropic`, `openai`, `bedrock`, `litellm`; 0 import de `subprocess` em `sparkforge/evals/` e `facts/host_transcript.py`; scorecard sem campo que some byte com token (lote `d-e`) | @test-generator | 1–5 |
| 17 | `tests/test_cli_eval.py` | Create | Os dois verbos de ponta a ponta sobre as fixtures (lote `a-c`) | @test-generator | 7 |
| 18 | `tests/test_rules_catalog_reachability.py` | Modify | `host_transcript` na tupla `EXTRACTORS`, com comentário do porquê | @test-generator | 1 |
| 19 | `tests/test_fixtures_kind_coverage.py` | Modify | `"host_transcript": host_transcript` em `EXTRACTORS` | @test-generator | 1 |
| 20 | `tests/test_capability_parity.py` | Modify | `ALLOWED_CLI_ONLY` + `"eval grade"`, `"eval compare"` (Decision 9) | @test-generator | 7 |
| 21 | `scripts/verify_wheel.py` | Modify | `GOLDEN_MODULES` + `test_fixtures_golden_host_transcript` (`tests/test_verify_wheel.py::test_discovers_every_golden_module_on_disk` cobra) | (general) | 13 |
| 22 | `tests/test_evals_holdout.py` | Modify (COULD, G9) | A varredura de superfície de agente também recusa citação de `evals/agentic` | @test-generator | 8 |
| 23 | `scripts/run_agentic_eval.py` | Create | Runner (Decision 6); `--suite`, `--out`, `--repeat N`, `--model`, `--mcp-config`, `--max-budget-usd`, `--dry-run` | @python-developer | 3 |
| 24 | `evals/README.md` | Modify | Seção "Nível de agente automatizado": como rodar, o que o scorecard mede e não mede; substitui a frase de `:59` com data | @code-documenter | 7, 23 |
| 25 | `README.md` | Modify | Verbo `eval` na lista da CLI | @code-documenter | 7 |
| 26 | `CLAUDE.md` | Modify | Linha na tabela "Os verbos que compõem": `eval` — "O agente acertou, com as tools certas, e recusou onde devia?" | @code-documenter | 7 |
| 27 | `docs/superpowers/STATUS.md` | Modify | Entrega registrada (fonte da verdade das fases) | @code-documenter | 24 |
| 28 | `docs/claims.lock.json` + `docs/harness/*.md` / `docs/vnext/*.md` | Modify (se o gate acusar) | Alegações movidas pelos `.py` novos, remediadas pela lista de ids da saída de `scripts/check_vnext_claims.py`, nunca por varredura | (general) | 1–7, 23 |
| 29 | `evals/agentic/fase0/baselines/<data>/*.json` | Create (SHOULD, G8) | Primeiro baseline: scorecards (ids e números), sem transcript | (general) | 23 |

**Total Files:** 29 entradas (itens 9–12 são diretórios de caso).

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer (`agentspec:python:python-developer`) | 1–7, 23 | Módulos Python puros com dataclass e type hints, e parser de formato |
| @test-generator (`agentspec:test:test-generator`) | 10–22 | Golden tests pytest, fixtures, registros manuais de teste |
| @sf-agent-evaluation-specialist (agente do projeto: "Golden cases e qualidade de agents") | 8, 9 | Escolha das perguntas de abstention e dos desfechos sintéticos: é qualidade de ground truth, não código |
| @code-documenter (`agentspec:python:code-documenter`) | 24–27 | README, `evals/README.md`, `CLAUDE.md`, STATUS |
| (general) | 21, 28, 29 | Edições de registro e execução de gate; nenhuma especialização agrega |

**Agent Discovery:**
- Scanned: `agentspec/3.5.0/agents/**/*.md` e os agentes `sf-*` do projeto (lista da sessão)
- Matched by: tipo de arquivo (`.py` → python-developer; `tests/` → test-generator), propósito (ground truth de agente → sf-agent-evaluation-specialist), documentação → code-documenter

---

## Code Patterns

### Pattern 1: Esqueleto do extrator (convenção de `facts/benchmark.py` + recusa de `host_usage.py`)

```python
"""Transcript do HOST como fact: que tools o agente chamou, o que respondeu.

Le o formato que `host_usage` ja confirmou (JSONL do Claude Code) e recusa por
NOME o que nao conhece. Nenhum fact carrega texto de `tool_use.input` nem de
`tool_result.content`: transcript e conteudo nao confiavel, e o que o grader
precisa e verbo, ordem e tamanho.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sparkforge.collect.host_usage import _somar_usage
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "host_transcript@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "host.transcript",
        "host.tool_call",
        "host.final_answer",
        "host.usage",
        "host.transcript.unresolved",
    }
)

ANSWER_MAX_CHARS = 200
_ANSWER = re.compile(r"^\s*ANSWER:\s*(?P<v>.*?)\s*$")


def extract_host_transcript_path(path: Path | str) -> list[Fact]:
    caminho = Path(path)
    prov = {"extractor": EXTRACTOR_ID}
    subject = {"type": "transcript", "symbol": caminho.stem, "path": str(caminho)}
    if caminho.suffix != ".jsonl" or not caminho.is_file():
        return [_unresolved(subject, prov, "host_format_unknown", 1)]
    # ... primeira linha sem "type" -> mesmo retorno, sem ler o resto (Decision 7)
    # ... laco linha a linha: tool_use (assistant) pareado por tool_use_id com
    #     tool_result (user); ultima linha ANSWER: do ultimo texto de assistente;
    #     usage somado via _somar_usage; lacunas num Counter
    facts: list[Fact] = []
    return sort_facts(facts)


def _unresolved(subject: dict[str, Any], prov: dict[str, Any], reason: str, count: int) -> Fact:
    return Fact(
        kind="host.transcript.unresolved",
        subject=subject,
        measures={"count": count},
        attrs={"reason": reason},
        provenance=prov,
    )
```

Razões de lacuna, vocabulário fechado: `host_format_unknown`, `malformed_line`, `message_field_not_object`, `usage_field_absent`, `usage_value_malformed`, `usage_value_fractional`, `usage_value_negative` (os sete de `host_usage`), mais `tool_result_orphan` (resultado sem `tool_use` correspondente) e `tool_use_without_result`. Cada uma precisa de fixture que a exercite (`test_every_unresolved_kind_is_exercised` cobra o kind; `tests/test_fixtures_golden_host_transcript.py` cobra cada reason).

### Pattern 2: Normalização de canal (Decision 4)

```python
_MCP = re.compile(r"^mcp__.+__sparkforge_(?P<v>[a-z0-9_]+)$")
_SEP = re.compile(r"&&|\|\||;|\|")
_PREFIXOS = (("rtk",), ("uv", "run"), ("python", "-m"))
_PALAVRA = re.compile(r"^[a-z][a-z-]*$")


def canonical_verb(name: str, tool_input: dict[str, Any]) -> tuple[str, str | None]:
    """(canal, verbo). Canal em {"mcp", "bash", "other"}; verbo None em "other"."""
    casou = _MCP.match(name)
    if casou:
        return "mcp", casou.group("v")
    if name == "Bash":
        comando = tool_input.get("command")
        if isinstance(comando, str):
            for segmento in _SEP.split(comando):
                tokens = segmento.split()
                for prefixo in _PREFIXOS:
                    if tuple(tokens[: len(prefixo)]) == prefixo:
                        tokens = tokens[len(prefixo):]
                        break
                if tokens[:1] == ["sparkforge"] and len(tokens) > 1 and _PALAVRA.match(tokens[1]):
                    partes = [tokens[1]]
                    if len(tokens) > 2 and _PALAVRA.match(tokens[2]):
                        partes.append(tokens[2])
                    return "bash", "_".join(partes).replace("-", "_")
    return "other", None
```

### Pattern 3: Configuração — `suite.yaml`

```yaml
# evals/agentic/fase0/suite.yaml
schema_version: 1
id: fase0
answer_protocol: >-
  Termine a resposta com uma unica linha `ANSWER: <valor>`, no formato pedido
  pela pergunta, ou `ANSWER: unresolved` se os artefatos nao sustentam um valor.
questions:
  - id: fase0-01
    source: ../../fase0.xml#1          # indice 1-based de <qa_pair>
    required_tools: [analyze_pyspark, judge]
    order: [[analyze_pyspark, judge]]  # pares (antes, depois), ordem parcial
  - id: abst-01
    question: >-
      Na fixture finops/no_dpu_no_cost, quanto custou o run em DPU-segundos?
    expects_abstention: true
    anchor: {fixture: finops/no_dpu_no_cost, kind: glue.run_cost.unresolved}
    required_tools: [finops]
```

Regras de schema, validadas por `suite.py` com erro nomeado e nunca por default silencioso:
- `source` e `question` são mutuamente exclusivos.
- `expects_abstention: true` exige `anchor`, e o teste 14 roda o extrator da fixture e confere que o `kind` aparece.
- `order` só pode citar tools que estão em `required_tools`.
- `id` é único e é o stem do transcript.

### Pattern 4: Formas de saída

```json
{
  "schema_version": 1,
  "suite": {"id": "fase0", "sha256": "…"},
  "run": {"id": "2026-09-10T20-00-00Z-01", "models": ["…"], "host_versions": ["…"]},
  "questions": [
    {
      "id": "fase0-01",
      "status": "graded",
      "answer": "correct",
      "abstention": null,
      "tools": {"verdict": "ok", "missing": [], "order_violated": []},
      "cost": {
        "tool_calls": 2, "other_calls": 0, "tool_errors": 0,
        "tool_result_bytes": 1834,
        "tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0},
        "tokens_unresolved": false
      },
      "unresolved": []
    }
  ],
  "unmatched_transcripts": [],
  "totals": {
    "questions": 13, "graded": 13, "ungraded": 0,
    "correct": 0, "wrong": 0, "answer_absent": 0, "over_abstention": 0,
    "abstention_total": 3, "abstained": 0, "false_certainty": 0,
    "tools_ok": 0,
    "cost": {"tool_calls": {"median_low": 0, "max": 0}, "tool_result_bytes": {"median_low": 0, "max": 0}}
  }
}
```

- `answer` vale `correct` | `wrong` | `answer_absent` | `over_abstention` | `null` (pergunta de abstention usa `abstention`).
- `abstention` vale `abstained` | `false_certainty` | `null`.
- Pergunta `ungraded` tem `answer`, `abstention` e `tools` nulos e `unresolved` preenchido.
- Tokens nunca aparecem somados a bytes, e nenhum campo agrega os quatro tipos de token (decisão herdada de `host_usage`).

```json
{
  "schema_version": 1,
  "refused": null,
  "single_sample": false,
  "suite": {"id": "fase0", "sha256": "…"},
  "baseline": {"n": 3, "models": ["…"], "host_versions": ["…"]},
  "candidate": {"n": 3, "models": ["…"], "host_versions": ["…"]},
  "differs": {"models": false, "host_versions": true},
  "questions": [
    {"id": "fase0-01",
     "answer": {"baseline": "3/3", "candidate": "1/3", "transition": "pass->mixed"},
     "tools_ok": {"baseline": "3/3", "candidate": "3/3", "transition": "pass->pass"},
     "ungraded": {"baseline": 0, "candidate": 0}}
  ],
  "cost": {"baseline": {"tool_calls": {"median_low": 0, "max": 0}}, "candidate": {"tool_calls": {"median_low": 0, "max": 0}}}
}
```

- Classes: `pass` quando k == N graded, `fail` quando k == 0, `mixed` no resto, `ungraded` quando N graded == 0. Transição = `"<A>-><B>"`.
- Em pergunta de abstention, a coluna é `abstained`.
- Recusa: `refused: {"reason": "suite_mismatch", "baseline_sha256": …, "candidate_sha256": …}`, com `questions: []`. Scorecards de hash diferente dentro do mesmo lado dão `suite_mismatch_within_side`, e diretório sem scorecard dá `empty_side`.

---

## Data Flow

```text
1. Operador: python scripts/run_agentic_eval.py --suite evals/agentic/fase0 --out ~/sf-evals --repeat 3
   │   (fora do CI; cada pergunta é uma sessão `claude -p` nova)
   ▼
2. ~/sf-evals/<run_id>/{<qid>.jsonl, <qid>.result.json, run.json}   × 3 runs
   │
   ▼
3. sparkforge eval grade --suite evals/agentic/fase0 --transcripts ~/sf-evals/<run_id> --out <run_id>.scorecard.json
   │   _core: os.scandir → extract_host_transcript_path por arquivo → Suite → grade
   ▼
4. Operador copia os scorecards (só ids e números) para evals/agentic/fase0/baselines/<data>/
   │
   ▼
5. Após uma mudança agêntica: repete 1–3 e roda
   sparkforge eval compare --baseline evals/agentic/fase0/baselines/<data> --candidate <dir>
   │
   ▼
6. compare.json: transições por pergunta; o operador decide (regra 30: o harness não conclui)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Claude Code CLI (`claude -p`) | Subprocess, **só em `scripts/run_agentic_eval.py`** | A sessão já logada do operador; o runner não lê nem grava credencial |
| `~/.claude/projects/*/<uuid>.jsonl` | Leitura de arquivo pelo runner | Nenhuma |
| Servidor MCP do SparkForge | `--mcp-config` apontando para o `sparkforge mcp` local; `--strict-mcp-config` opcional para isolar | Nenhuma |

Nenhuma integração nova dentro de `sparkforge/`.

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Golden (unit, duas direções) | Extrator, grade, compare sobre fixtures | `tests/test_fixtures_golden_host_transcript.py` | pytest | 100% dos casos de `fixtures/host_transcript/` |
| Unit | Normalização, suíte, hash, invariantes | `tests/test_evals_normalize.py`, `tests/test_evals_suite.py`, `tests/test_evals_invariants.py` | pytest | Toda regra das Decisions 3, 4, 7 e 8 |
| Integração | CLI de ponta a ponta | `tests/test_cli_eval.py` | pytest + `cli.main([...])` | Os dois verbos, sucesso e recusa |
| Registros | Cobertura de kind, paridade, wheel, snippet, facts_scan | testes existentes modificados | pytest | Verdes antes dos lotes longos |
| E2E manual | Runner real | `scripts/run_agentic_eval.py` | `claude -p` | Smoke de 1 pergunta (B1) e baseline N ≥ 3 (SC8) |

**Mapeamento dos testes de aceitação:**

| AT | Onde | Fixture / caso |
|----|------|----------------|
| AT-001 | golden | `fixtures/host_transcript/correct_mcp/` |
| AT-002 | golden | `wrong_answer/` |
| AT-003 | golden | `answer_absent/` |
| AT-004 | golden | `false_certainty/` |
| AT-005 | golden | `abstained/` |
| AT-006 | golden | `over_abstention/` |
| AT-007 | golden | `tool_missing/` |
| AT-008 | golden | `order_violated/` |
| AT-009 | golden | `extra_tool/` |
| AT-010 | normalize + golden | `mixed_channels/` (MCP + Bash para o mesmo verbo) |
| AT-011 | normalize | caso `ls fixtures/` → `other` |
| AT-012 | golden | `broken_envelope/` (linha não-JSON + `message` em lista) e `not_a_transcript/` |
| AT-013 | golden | `no_usage/` |
| AT-014 | invariants | varredura das chaves do scorecard |
| AT-015 | golden compare | `compare_stable/` |
| AT-016 | golden compare | `compare_flip/` |
| AT-017 | golden compare | `compare_suite_mismatch/` |
| AT-018 | golden compare | `compare_single_sample/` |
| AT-019 | golden compare | `compare_model_differs/` |
| AT-020 | golden | toda fixture pontuada duas vezes, com saída byte-idêntica |

**Ordem de verificação** (memória do projeto: registros primeiro, lotes depois, um de cada vez):
1. Os testes rápidos de registro: `test_rules_catalog_reachability`, `test_fixtures_kind_coverage`, `test_capability_parity`, `test_verify_wheel`, `test_harness_untrusted`, `test_facts_scan`, `test_docs_coverage`.
2. Os testes novos.
3. `python scripts/check_evals.py`.
4. `python scripts/check_vnext_claims.py`.
5. Os lotes de `tests/test_suite_batches.py::LOTES`.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Linha não-JSON, envelope sem `type`, `message` que não é objeto | Lacuna nomeada em `host.transcript.unresolved`; a leitura segue (regra 27) | No |
| Arquivo que não é transcript (sufixo, primeira linha) | Um único `host_format_unknown`, sem ler o resto | No |
| Pergunta sem transcript | `ungraded` + `transcript_not_found` | No |
| Transcript sem pergunta | `unmatched_transcripts`, contado | No |
| Transcript com lacuna que impede o veredito (0 mensagens de assistente reconhecidas) | `ungraded`; nunca `wrong` | No |
| `suite.yaml` inválido (fonte e pergunta juntas, `anchor` ausente, `order` fora de `required_tools`, id duplicado, `fase0.xml#N` fora do intervalo) | `SuiteError` nomeado; a CLI sai com código ≠ 0 e mensagem que cita o campo | No |
| Compare com hash diferente, lado vazio | `refused` nomeado, exit 0 (é resposta, não falha) | No |
| Runner: `claude` ausente, sessão sem arquivo persistido, timeout | O runner registra em `run.json` por pergunta (`status: host_failed`, motivo) e segue para a próxima; o grade dá `transcript_not_found` | Não automático; o operador reroda |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `suite.yaml: answer_protocol` | string | obrigatório | Instrução de formato que o runner acrescenta a toda pergunta |
| `suite.yaml: questions[].required_tools` | list[str] | obrigatório, não vazio | Verbos canônicos exigidos |
| `suite.yaml: questions[].order` | list[[str, str]] | `[]` | Pares de ordem parcial |
| `suite.yaml: questions[].expects_abstention` | bool | `false` | A resposta certa é `unresolved` |
| `host_transcript.ANSWER_MAX_CHARS` | int | `200` | Teto de `attrs.answer` (Decision 7) |
| runner `--repeat` | int | `1` | Runs por pergunta; N=1 leva a `single_sample` no compare |
| runner `--max-budget-usd` | float | ausente | Repassado ao `claude -p`; o runner não calcula dólar (regra 25) |
| runner `--mcp-config` | path | obrigatório | Isola o ambiente MCP do agente e fica registrado em `run.json` |

---

## Security Considerations

- **Transcript é conteúdo não confiável.** Nenhum fact carrega `tool_use.input` nem `tool_result.content`, a resposta é truncada em 200 caracteres e o scorecard nunca copia `path` (Decision 7).
- **Caso real nunca entra no repo.** O runner grava fora do repo por padrão e recusa `--out` dentro da árvore do git (checagem com `git rev-parse --show-toplevel`). O que se commita são as fixtures sintéticas e os scorecards.
- **Regra 23.** `tests/test_evals_invariants.py` prova por AST: 0 import de provider em `sparkforge/` e 0 `subprocess` em `sparkforge/evals/` e em `facts/host_transcript.py`. O `subprocess` do runner mora só em `scripts/`.
- **Credenciais.** O runner herda a sessão do operador e não lê nem grava token. `run.json` grava argv, e argv não contém segredo, porque o runner não aceita chave por flag.
- **Holdout (COULD).** A varredura de superfície de agente passa a recusar citação de `evals/agentic`, porque resposta resolvida nas instruções é resposta disponível.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum log novo; o payload JSON da CLI é a saída. O runner imprime uma linha por pergunta (qid, status, caminho do transcript) |
| Metrics | O scorecard é a métrica. `run.json` registra `claude --version`, argv e data de cada run |
| Tracing | N/A. O `economy report` segue medindo o custo do SparkForge por span; o eval mede o custo do host por transcript, e os dois ficam separados (regra 22) |

---

## Pipeline Architecture (if applicable)

N/A. Não há pipeline de dado.

---

## Build Order

| Task | Entrega | Gate |
|------|---------|------|
| B1 | Smoke de A-002: uma pergunta com `claude -p --session-id`; confere que `~/.claude/projects/*/<uuid>.jsonl` existe e que o extrator (mesmo em esboço) lê `tool_use` e `ANSWER:` | Se falhar, reabrir a Decision 6 antes de B2 |
| B2 | Itens 1, 9, 10, 15, 18, 19, 13 (parte de facts) | Registros rápidos verdes |
| B3 | Itens 2–5, 11, 12, 14, 16 | Golden de scorecard e compare verdes |
| B4 | Itens 6, 7, 17, 20, 21 | `test_capability_parity`, `test_verify_wheel` verdes |
| B5 | Itens 8, 22 | `check_evals.py` verde, `fase0.xml` com 0 linhas alteradas |
| B6 | Item 23 | `--dry-run` sem gastar token |
| B7 | Itens 24–28 | `check_vnext_claims.py` verde; lotes |
| B8 (SHOULD) | Item 29: baseline N ≥ 3 | SC8 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-10 | design-agent | Versão inicial. A-001 ampliada e A-004 confirmadas por medida; A-002 parcial (flags confirmadas, arquivo pendente do smoke B1) |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_AGENTIC_EVAL_HARNESS.md`
