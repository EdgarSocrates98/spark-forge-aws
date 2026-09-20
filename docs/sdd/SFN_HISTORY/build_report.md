---
sdd: 1
feature: SFN_HISTORY
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SFN_HISTORY/plan.md
  sha256: "ea9b5d1e3cb2ce9948933cb6feba94a0f29eb511e2312ef213ac2560e4133c25"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sfn_history.py::test_cli_e_tool_devolvem_os_mesmos_facts -q", exit: 1}
    green: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sfn_history.py::test_fuse_confronta_o_retry_declarado_com_o_observado tests/test_fixtures_golden_sfn_history.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_sfn_history.py tests/test_fixtures_golden_sfn_history.py -q", exit: 0}
  - id: T4
    status: skipped
claims:
  - text: "Um JSON de get-execution-history vira sfn.execution com status pelo evento terminal, duracao e a contagem dos eventos LIDOS, e um sfn.attempt por tentativa de Task, com o estado resolvido pela cadeia de previousEventId e nunca pela ordem."
    evidence_ref: "tests/test_sfn_history.py::test_historico_vira_execucao_e_tentativas"
  - text: "O JobRunId do Glue e lido do output do TaskSubmitted e vira sfn.job_run; historico gravado sem includeExecutionData sai sfn.unresolved com razao propria e nenhum sfn.job_run e afirmado."
    evidence_ref: "tests/test_sfn_history.py::test_job_run_vem_do_output_e_a_ausencia_sai_nomeada"
  - text: "Historico truncado, evento de tipo desconhecido, evento que nao e objeto e JSON invalido saem sfn.unresolved nomeado, e o que foi lido continua valendo."
    evidence_ref: "tests/test_sfn_history.py::test_historico_incompleto_sai_nomeado_sem_perder_o_que_leu"
  - text: "O verbo analyze sfn-history e a tool MCP sparkforge_analyze_sfn_history devolvem os mesmos facts."
    evidence_ref: "tests/test_sfn_history.py::test_cli_e_tool_devolvem_os_mesmos_facts"
  - text: "A derivacao em fuse confronta o retry declarado no ASL com o observado no historico, e o que nao pareia sai recusado com nome: asl_absent, state_name_absent_in_asl, state_name_ambiguous, declared_ceiling_unreadable e glue_attempt_absent."
    evidence_ref: "tests/test_sfn_history.py::test_fuse_confronta_o_retry_declarado_com_o_observado"
  - text: "As tentativas de execucoes diferentes nao se somam: o lado medido e chaveado pelo par artefato e nome do estado, e duas execucoes que cabem no retry declarado nao produzem achado."
    evidence_ref: "tests/test_sfn_history.py::test_duas_execucoes_nao_somam_tentativas_uma_da_outra"
  - text: "Um evento de tipo desconhecido no MEIO da cadeia nao apaga as tentativas do ramo: ele fica na travessia e fora de todo fact, e a recusa continua saindo."
    evidence_ref: "tests/test_sfn_history.py::test_tipo_desconhecido_no_meio_da_cadeia_nao_apaga_a_tentativa"
  - text: "Recusas diferentes do mesmo arquivo tem ids diferentes e sobrevivem ao fuse, porque o discriminador numerico mora em measures, que entra no hash do fact."
    evidence_ref: "tests/test_sfn_history.py::test_recusas_do_mesmo_arquivo_nao_colidem_de_id"
  - text: "A recusa glue_attempt_absent e por artefato: um artefato sem nenhuma tentativa glue:startJobRun sai nomeado mesmo quando outro artefato do pool tem."
    evidence_ref: "tests/test_sfn_history.py::test_recusa_de_glue_ausente_e_por_artefato_e_nao_pelo_pool"
  - text: "Id de evento repetido sai recusado com event_id_duplicated, a primeira ocorrencia vence e a contagem de eventos lidos nao conta o que foi descartado."
    evidence_ref: "tests/test_sfn_history.py::test_id_de_evento_repetido_sai_nomeado"
  - text: "SF-SFNX-001 dispara quando as tentativas observadas excedem o teto declarado, e fica calada na fronteira; SF-SFNX-002 exige a submissao que ela manda o operador ler; SF-SFNX-003 dispara com a execucao parada e o Task .sync em voo."
    evidence_ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"
  - text: "A area SF-SFNX passa pelo criterio de dominio: regra executavel, coordenador que a declara e rota por findings_area."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_declara_area_que_julga"
  - text: "Nenhum golden de achado existente mudou: a suite inteira de goldens passa sem regeneracao, e os cinco de assessment se moveram so na contagem do catalogo."
    evidence_ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"
---

# SFN_HISTORY — relatório do build

## As quatro tarefas do plano

Cada uma com o vermelho que o subagente **viu**, e o verde depois. Os hashes abaixo são
os de hoje: a pilha foi rebaseada sobre o `main` depois do #91, e os hashes que os
subagentes relataram (`090139d3`, `94f361e7`, `e9d317c4`) não existem mais.

| tarefa | commit | o que entregou |
|---|---|---|
| T1 | `199aeed5` | o extrator `sparkforge/facts/sfn_history.py` e os facts `sfn.*` |
| T2 | `0f375285` | o verbo `analyze sfn-history`, a tool MCP e os registros de superfície |
| T3 | `4669c422` | a área SF-SFNX, a derivação em `fuse`, a rota AGENT-088 e 10 fixtures |
| T4 | `08e6a1bc` | o documento de conhecimento, o guia de uso e os números |

**A T4 está `skipped`, e é uma declaração, não um detalhe.** O trabalho dela está no
commit `08e6a1bc` e os comandos que o define pede como `kind: command` foram rodados por
mim e saíram com exit 0 — mas o subagente da T4 **nunca entregou relato**: ficou preso
esperando trabalho próprio em segundo plano até eu encerrá-lo. Eu não vi o vermelho
dela, e escrever um exit que ninguém viu é o defeito mais grave que este relatório pode
ter. Por isso a tarefa não é `done`.

## O que as duas rodadas de revisão mudaram

A revisão final do diff inteiro, feita depois das quatro tarefas, achou **um crítico,
sete importantes e onze menores**. Vieram em duas rodadas, 25 commits sobre `08e6a1bc`,
cada achado com vermelho próprio antes do verde.

### O crítico

`build_sfn_retry_observado` agrupava as tentativas **só pelo nome do estado**, sobre a
união dos facts. Dois históricos com duas tentativas cada do estado `Carga`, mais um ASL
com `MaxAttempts: 2`, produziam `{'tentativas_observadas': 4, 'teto_declarado': 3}` — e a
SF-SFNX-001 disparava um achado falso sobre dois runs que **cabem** no retry declarado.

O lado medido passou a ser chaveado por `(artefato, nome do estado)`; o lado declarado
segue pelo nome, porque o ASL é outro artefato e é esse o pareamento que o histórico
permite. **O corpus não pegava o defeito**: nenhuma fixture tem dois históricos.

### Os sete importantes

- Evento de tipo desconhecido no **meio** da cadeia quebrava a travessia e zerava as
  tentativas do ramo. O AC3 só estava demonstrado com o desconhecido em folha.
- Os `sfn.unresolved` do mesmo arquivo colidiam de id — o discriminador vivia em `attrs`,
  que não entra no hash — e o `fuse` deixava **um**. "Recusa tem nome" virava "uma recusa
  tem nome".
- SF-SFNX-002 disparava sem `TaskSubmitted` e mandava o operador ler um `JobRunId` que
  nesse caso não existe.
- O documento de conhecimento e o guia diziam que histórico truncado sai com `status:
  unresolved`. São duas perguntas independentes: com `reverseOrder`, sai `truncated: true`
  **e** `succeeded`.
- A `description` do coordenador dizia que o histórico conta "quantas vezes o job rodou de
  verdade" — exatamente a lacuna U1, que o catálogo recusa por escrito.
- Uma integração `aws-sdk` sumia calada no confronto, sem recusa nenhuma.
- `stepfunctions._loads` não tratava `MemoryError`, enquanto a gêmea tratava.

### Os menores que viraram commit

`event_count` virou `read_event_count` (contava só os validados); `job_name` e `pattern`
do confronto viraram `declared_*`, porque vêm do ASL e o histórico tem os seus; o grupo
passou a ser ordenado pelo índice da tentativa e não pelo hash; id de evento repetido
passou a sair recusado; `reverseOrder` foi declarado onde não estava; e as frases que
citavam linha de código passaram a citar símbolo — porque as linhas envelheceram **dentro
da própria rodada**.

## Duas decisões tomadas no caminho

**Id de evento repetido é descartado, e a primeira ocorrência vence.** A alternativa era
só emitir a recusa e deixar o índice inflado de pé — o que mantinha o extrator afirmando
uma ordem de tentativas que o arquivo não sustenta.

**A premissa do ramo virou lacuna, não citação.** "`previousEventId` aponta para o evento
anterior *daquele ramo*" sustenta todo o pareamento, e as duas páginas da API dão uma
única descrição do campo: "The id of the previous event." Ela diz que existe um anterior;
não diz que é o do mesmo ramo. Virou a lacuna 9 do documento de conhecimento, com o que a
destrava.

## Desvios do plano

1. **Bug no texto do plano, na T1.** O helper `_evento` formatava
   `f"...T03:00:{segundo:02d}..."` com deslocamentos de 60 a 91 segundos, produzindo
   `03:00:91`, que não é ISO 8601. Corrigido para carregar nos minutos; nenhuma asserção
   tocada.
2. **Bug no texto do plano, na T3.** O teste chamava `fuse([definicao, historico])`, mas
   `fuse` recebe uma `Sequence[Fact]` plana. Aplicada a forma do precedente,
   `fuse(definicao + historico)`.
3. **Contagens do plano defasadas.** Ele foi escrito antes de o #91 entrar na pilha; as
   bases subiram e os **deltas** bateram. Publiquei o medido, não o previsto.
4. **Âncoras de inserção deslocadas** em `cli.py`, `parity.yaml`,
   `test_adapters_tools.py`, `agents/glue-infra-reviewer.md` e `fusion.py`, todas pelo
   AIRFLOW_DAG já mergeado. Aplicadas na posição equivalente.
5. **Uma fixture a mais que o plano previa**: `task_timed_out_sem_submissao`, a negativa
   que a correção da SF-SFNX-002 exigiu. São 11 no corpus, não 10.
6. **Três arquivos fora do manifesto**, todos pela renomeação de `read_event_count`:
   `docs/guia/usos/step-functions.md`, `sparkforge/adapters/tools.py` (a description da
   tool) e a página gerada dela.
7. **O `define.md` não foi editado**, e o AC1 dele ainda diz "contagem de eventos". Editar
   o frontmatter agora cascatearia o `sha256` de `upstream` para todas as fases abaixo.
   Fica registrado como desvio, que é o que o SDD manda fazer com spec que envelhece.
8. **A revisão em dois estágios por tarefa não rodou**; a revisão final do diff inteiro
   rodou, e é dela que vieram os 19 achados.

## O que o `.claude/agents/README.md` mostrou

O arquivo é untracked e **sumiu durante as tarefas**. A cópia está no scratchpad da
sessão, e devolvê-la **quebra dois gates**: `sync_skills.py --check` a acusa `ORFAO` e
`tests/test_agents_parity.py` a apaga de novo. Ou seja: o arquivo não pode voltar como
está. Isso é decisão do operador, não minha, e está na seção de pendências do ship.
