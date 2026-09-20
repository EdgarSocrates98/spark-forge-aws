---
sdd: 1
feature: SFN_HISTORY
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SFN_HISTORY/build_report.md
  sha256: "3a6178c344abf457f7a4db72bbb10e70aa14b94a93c8eb53f330ee155e5044e6"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, runtime_scope_gates, routing_yaml, coordinator_rule_areas, fixture_corpus_gates, offline_manifest, sources_lock, surface_lock, generated_reference, sync_skills, agents_parity, router_gates, status_numbers_gate, claims_gate]
deviations:
  - "T4 ficou skipped: o subagente dela nunca entregou relato, e eu nao vi o vermelho. O trabalho esta commitado em 08e6a1bc e os comandos de kind: command do define rodaram com exit 0, mas exit que ninguem viu nao se escreve."
  - "A revisao final do diff inteiro achou um critico, sete importantes e onze menores, corrigidos em 25 commits sobre 08e6a1bc, em duas rodadas (codigo e prosa). O critico somava tentativas de execucoes diferentes e fazia a SF-SFNX-001 disparar um achado falso; o corpus nao pegava, porque nenhuma fixture tinha dois historicos."
  - "Duas medidas foram renomeadas na correcao: event_count virou read_event_count (contava so os eventos validados) e job_name/pattern do sfn.retry_observado viraram declared_*, porque vem do ASL e o historico tem os seus."
  - "Dois bugs no TEXTO do plano, achados no build: um helper de teste produzia 03:00:91, que nao e ISO 8601, e outro chamava fuse([a, b]) quando fuse recebe uma Sequence plana. Os dois corrigidos pela forma do precedente, sem tocar asserção."
  - "As contagens do plano estavam defasadas (ele foi escrito antes de o #91 entrar na pilha). Os deltas bateram; publiquei o medido, nao o previsto."
  - "Uma fixture a mais que o plano previa: task_timed_out_sem_submissao, a negativa que a correcao da SF-SFNX-002 exigiu. Sao 11 no corpus, nao 10."
  - "Tres arquivos fora do manifesto, todos pela renomeacao de read_event_count: docs/guia/usos/step-functions.md, sparkforge/adapters/tools.py e a pagina gerada da tool."
  - "O define.md nao foi editado, e o AC1 dele ainda diz contagem de eventos. Editar o frontmatter agora cascatearia o sha256 de upstream para todas as fases abaixo; fica como desvio, que e o que o SDD manda fazer com spec que envelhece."
  - "A revisao em dois estagios por tarefa nao rodou; a revisao final do diff inteiro rodou, e e dela que vieram os 19 achados."
  - "O .claude/agents/README.md, untracked, sumiu durante as tarefas. Devolve-lo quebra dois gates (sync_skills --check o acusa ORFAO e test_agents_parity o apaga de novo). A copia esta no scratchpad da sessao, e a decisao e do operador."
---

# SFN_HISTORY — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de quatro jeitos, e nenhum aconteceu na árvore
final:

- **O extrator conta as tentativas por estado e lê o `JobRunId` de cada
  `TaskSubmitted`.** O estado vem da cadeia de `previousEventId`, nunca da ordem dos
  eventos.
- **A regra de divergência dispara quando as tentativas não cabem no retry declarado, e
  fica calada quando cabem.** A fronteira tem fixture própria: `retry_dentro_do_declarado`
  tem 2 tentativas contra teto 2, e a SF-SFNX-001 não dispara.
- **Histórico sem `includeExecutionData` sai `sfn.unresolved` nomeado, nunca com `JobRun`
  inventado.**
- **Nenhum golden de achado existente mudou.** Os cinco de assessment se moveram só na
  contagem do catálogo, e o `brief.json` do debate numa linha que não é achado.

**O que quase invalidou a segunda parte, e por que ela ainda vale.** No fim do build, a
regra de divergência **disparava falso** quando dois históricos entravam no mesmo pool: o
agrupamento era só pelo nome do estado, e duas execuções que cabiam no retry declarado
somavam suas tentativas e estouravam o teto. O corpus inteiro não pegava, porque nenhuma
fixture tinha dois históricos. A revisão final pegou, a correção chaveou o lado medido
por `(artefato, nome do estado)`, e a fixture que faltava virou teste. **A previsão está
confirmada sobre a árvore que entrega, não sobre a que o build fechou.**

## O que o domínio entrega

- **Extrator.** `sparkforge analyze sfn-history --path` e a tool
  `sparkforge_analyze_sfn_history` leem o JSON salvo de
  `aws stepfunctions get-execution-history`. Saem `sfn.execution`, `sfn.attempt`,
  `sfn.job_run`, `sfn.unresolved` com razão própria e `sfn.analyzed`.
- **Derivação em `fuse`.** `build_sfn_retry_observado` confronta o retry **declarado** no
  ASL com o **observado** no histórico, pareando pelo nome do estado, que é o único
  identificador que o histórico publica.
- **Regras.** Três na área SF-SFNX, coordenada pelo `glue-infra-reviewer` pela rota
  AGENT-088:
  - **001, P2:** as tentativas observadas de um estado excedem o que o retry declarado
    permite.
  - **002, P1:** uma tentativa de Task `.sync` terminou em `TaskTimedOut` **depois de
    submetida**: o Task expirou e o histórico não registra o fim do JobRun que ele
    acompanhava.
  - **003, P1:** a execução terminou abortada ou expirada com um Task `.sync` em voo.
- **Conhecimento.** `knowledge/stepfunctions/execution-history.md`, com as frases citadas
  das duas páginas da API e as lacunas nomeadas.

**O que o catálogo recusa, por escrito:** quantas vezes o job Glue rodou por tentativa. O
histórico dá um **piso** de JobRuns, e o `MaxRetries` do próprio job é outra camada. É a
lacuna U1, e foi exatamente a frase que a revisão achou contradita na `description` do
coordenador.

## Medidas

| | antes (`f155fddf`) | depois |
|---|---|---|
| regras | 165 | 168 |
| áreas | 30 | 31 |
| tools | 108 | 109 |
| extratores | 40 | 41 |
| kinds | 242 | 243 |
| rotas | 42 | 43 |
| fixtures | 540 em 58 domínios | 551 em 59 |
| fontes vigiadas | 265 | 267 |

## Gates rodados

| gate | resultado |
|---|---|
| regra, catálogo, eixo, governança, escopo (9 arquivos) | 935 passed |
| SDD, extrator, golden da feature, critério de domínio (4 arquivos) | 208 passed |
| fusão, gêmea, cobertura de kind, referência, superfície, números (10 arquivos) | 427 passed |
| agente, rota, tool, parity (7 arquivos) | 679 passed |
| escopo por natureza, runtime, bundle offline, watchlist (5 arquivos) | 686 passed |
| `tests/test_harness_untrusted.py` (medida de snippet) | 4 passed |
| `tests/test_agents_parity.py` | 67 passed |
| `python scripts/sync_skills.py --check` | exit 0 |
| `python scripts/verify_offline_bundle.py` (AC9) | `"ok": true`, 56 conferidos |
| `python scripts/check_status_numbers.py --strict` (AC10) | 0 divergências |
| `python scripts/check_surface_lock.py` | 0 divergências |
| `python scripts/check_vnext_claims.py` | 0 divergências |
| `python -m ruff check sparkforge scripts tests` | limpo |
| `sparkforge sdd check --repo . --feature SFN_HISTORY` | `"ok": true`, 0 recusas, 0 lacunas |

Os dois `verified_by` de `kind: command` do define:

| critério | comando | exit |
|---|---|---|
| AC9 | `python scripts/verify_offline_bundle.py` | 0 |
| AC10 | `python scripts/check_status_numbers.py --strict` | 0 |

## Pendências

- **U1 continua aberta.** O mecanismo está pronto — é ele que a feature entrega —, mas a
  resposta de como o retry do orquestrador se compõe com o `MaxRetries` do Glue exige um
  histórico **real** de execução com falha. Fixture sintética prova o extrator, não a
  composição.
- **U2:** nenhum histórico real foi observado. As fixtures saem da forma de evento
  publicada.
- **Duas execuções no mesmo arquivo continuam somando**, e está escrito no docstring da
  derivação: não há campo no histórico que as separe. O `executionArn` só existe se quem
  salvou o acrescentou, e não viaja por evento. Limite declarado, não resolvido.
- **`_TIPOS_CONHECIDOS` é subconjunto próprio do publicado**: 59 de 62. Faltam
  `EvaluationFailed`, `ExecutionRedriven` e `MapRunRedriven`, e o terceiro importa — a
  execução **retomada** muda o que "quantas vezes o Task foi agendado" significa. Nada se
  perde hoje: cada um sai em `event_type_unknown` e continua na travessia da cadeia.
- **A premissa do ramo é nossa, não citada.** As duas páginas da API dão uma única
  descrição de `previousEventId`: "The id of the previous event." Ela não diz que o
  anterior é o do mesmo ramo, e é disso que todo o pareamento depende. Lacuna 9 do
  documento de conhecimento, com o que a destrava.
- **Estados homônimos em `Parallel`** fundem tentativas no extrator; a derivação recusa
  com `state_name_ambiguous`, mas o `attempt_index` já saiu errado antes disso.
- **Módulo compartilhado:** `_glue_jobs_por_nome` e `_max_retries` seguem duplicados entre
  `stepfunctions.py` e `airflow_dag.py`, de propósito. `sparkforge/facts/glue_terraform.py`
  é incremento separado.
- **`.claude/agents/README.md`** está ausente e não pode voltar como está. Decisão do
  operador.

## Lições

- **A revisão final pegou o que o corpus inteiro não pegava.** O defeito crítico exigia
  duas execuções no mesmo pool, e nenhuma fixture tinha duas. Corpus verde não é prova de
  ausência de defeito — é prova de que o defeito não está no que o corpus cobre.
- **Citação de linha de código envelhece dentro da própria rodada.** Duas frases foram
  ancoradas em `sfn_history.py:535` e `:570`; os commits seguintes empurraram as cinco
  citações, e a pior passou a apontar para outro `if`. Nenhum gate confere citação de
  linha. Cite símbolo.
- **Subagente que não relata deixa um buraco que não se preenche depois.** O vermelho da
  T4 não existe mais em lugar nenhum, e a tarefa fica `skipped` para sempre. Vale encerrar
  o subagente pendurado cedo e redespachar, em vez de conferir os gates por fora e herdar
  o buraco.
