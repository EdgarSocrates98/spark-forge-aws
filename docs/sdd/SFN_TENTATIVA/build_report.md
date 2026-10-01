---
sdd: 1
feature: SFN_TENTATIVA
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SFN_TENTATIVA/plan.md
  sha256: "0ccd19b92056fc72044bd46c42150845f2daafb3d2499d65062f027380046209"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_sfn_history.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_sfn_history.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_sfn_history.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest \"tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches\" -q", exit: 1}
    green: {command: "python -m pytest \"tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches\" -q", exit: 0}
claims:
  - text: "A lista de tipos conhecidos passou a ser IGUAL aos 62 Valid Values publicados; EvaluationFailed e MapRunRedriven entram calados, e ExecutionRedriven sai em sfn.unresolved com razao propria."
    evidence_ref: "tests/test_sfn_history.py::test_redrive_sai_com_razao_propria_e_os_outros_dois_tipos_entram_calados"
  - text: "Com redrive no historico, build_sfn_retry_observado emite redrive_in_execution no lugar do sfn.retry_observado, e as tentativas continuam medidas e publicadas: o que se recusa e a COMPARACAO com o teto declarado."
    evidence_ref: "tests/test_sfn_history.py::test_redrive_recusa_o_confronto_em_vez_de_comparar"
  - text: "A recusa do redrive e por ARTEFATO: uma execucao com redrive nao cala a execucao vizinha do mesmo case, que continua tendo confronto."
    evidence_ref: "tests/test_sfn_history.py::test_redrive_recusa_o_confronto_em_vez_de_comparar"
  - text: "Estados de mesmo nome em ramos mutuamente nao-ancestrais deixam de ser numerados e saem em state_name_in_concurrent_branches; os estados de nome unico do mesmo historico continuam virando tentativa."
    evidence_ref: "tests/test_sfn_history.py::test_estado_homonimo_em_ramos_diferentes_sai_recusado_sem_indice"
  - text: "Reentrada SEQUENCIAL do mesmo estado -- retry ou Choice -- continua numerada 1..n, porque a entrada anterior fica na cadeia da seguinte: o criterio nao pergunta se o Retry reentra no estado, que e a lacuna U1."
    evidence_ref: "tests/test_sfn_history.py::test_ramo_unico_com_retry_mantem_os_indices"
  - text: "Cadeia interrompida ou ciclica entre duas entradas de mesmo nome sai em state_entries_chain_unwalkable, com a parada em attrs.detail, e NAO no nome que afirma ramos concorrentes."
    evidence_ref: "tests/test_sfn_history.py::test_cadeia_impassavel_nao_vira_ramos_concorrentes"
  - text: "As duas recusas de identidade de nome tem o mesmo subject e ids diferentes, porque o discriminador mora em measures: as duas sobrevivem ao fuse."
    evidence_ref: "tests/test_sfn_history.py::test_cadeia_impassavel_nao_vira_ramos_concorrentes"
  - text: "Iteracoes de um Map INLINE caem na mesma recusa de nome que os ramos de um Parallel, e os sfn.job_run sobrevivem a ela sem #<n> e sem attempt_index, com ids distintos."
    evidence_ref: "tests/test_sfn_history.py::test_map_inline_recusa_o_indice_e_preserva_o_job_run"
  - text: "As duas recusas de historico_truncado deixaram de colidir de id e sobrevivem ao fuse, porque read_events saiu de attrs para measures."
    evidence_ref: "tests/test_sfn_history.py::test_truncado_e_terminal_ausente_sobrevivem_ao_fuse"
  - text: "As tres regras da area SF-SFNX se comportam como o corpus declara, e a SF-SFNX-001 fica calada nas quatro fixtures novas."
    evidence_ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"
  - text: "Nenhum golden de achado existente mudou de comportamento: a suite inteira de goldens passa sem regeneracao."
    evidence_ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"
---

# SFN_TENTATIVA — relatório do build

## As quatro tarefas do plano

| tarefa | commit | o que entregou |
|---|---|---|
| T1 | `987af534` | o redrive: os três tipos, `execution_redriven`, `redrive_in_execution` |
| T2 | `b1d4a9bc` | a ancestralidade entre entradas de mesmo nome |
| T3 | `b3fd0aec` | as três fixtures, o `REQUIRED_FIXTURES` e a contagem do `STATUS.md` |
| T4 | `088e7d4b` | as lacunas 8 e 9 do documento de conhecimento |

**O AC4 não teve vermelho próprio, e isso é declaração, não descuido.**
`test_ramo_unico_com_retry_mantem_os_indices` ficou verde já no vermelho da T2, e o plano
previu que ficaria: ele é **guarda de regressão**, não prova de comportamento novo.
"Recusar mais" seria trivialmente satisfeito recusando tudo, e é ele que impede isso. O
`red` registrado para a T2 é o da falha que apareceu de fato — uma só, a do caso homônimo.

E a revisão final mostrou o limite exato dessa guarda: a fixture do AC4 tem cadeia
perfeita, então a regressão do achado crítico passou por baixo dela. **Guarda de regressão
cobre o caso que ela constrói, e nada além.**

## A revisão final, e o que ela mudou

Um revisor novo leu o diff inteiro contra o define e o design, medindo em memória com
`sparkforge.facts.*`. Achou **um crítico, três importantes e dois menores**, corrigidos em
sete commits (`088e7d4b..b65714c7`).

### O crítico

`_ancestrais` **descartava a razão de parada** da travessia. `_ancestral` tem três de
propósito — `chain_root`, `chain_broken`, `chain_cycle` — e a docstring dela diz por quê:
confundi-las esconderia truncamento atrás de "não achei". Sem a razão, "B não alcança A e A
não alcança B" virava **concorrência**, quando a causa podia ser cadeia interrompida.

Medido num histórico de **um ramo só, sem `Parallel` nenhum**, com um evento intermediário
fora da travessia: as duas tentativas e os dois `JobRunId` que o arquivo sustenta
**desapareciam**, e no lugar saía uma recusa afirmando ramos concorrentes. Três defeitos
num: dado medido some, a recusa tem o nome **errado** (regra 20 — recusa com nome errado é
pior que recusa sem nome), e contradiz a docstring do próprio módulo.

A correção fez `_ancestrais` devolver `(vistos, parada)`, e a conclusão de concorrência
passou a exigir que **os dois** passeios do par tenham terminado em `chain_root` limpo. O
resto sai em `state_entries_chain_unwalkable`, com a parada em `attrs.detail`.

### Os três importantes

- **O alcance real era muito maior do que a feature declarava.** Iterações de um `Map`
  **inline** divergem no `MapStateStarted` comum exatamente como ramos de `Parallel`, então
  todo estado dentro de um `Map` caía na recusa — 400 iterações produziam zero tentativas —
  e o `sfn.job_run` ia junto. O define só falava de `Parallel`, e o `out_of_scope` só
  excluía o Map **distribuído**. Não havia fixture de `Map` nenhuma.
- **Uma frase falsa viajando dentro do achado.** A regra e o documento diziam que a
  SF-SFNX-001 "fica em `skipped`" com redrive. Ela fica em `skipped` quando o **kind
  inteiro** falta do pool; com dois históricos no case, um limpo, o kind está lá e a regra
  avalia. O próprio teste da feature prova esse cenário.
- **Colisão de id em `historico_truncado`**, dívida anterior a esta feature: `read_events`
  ia para `attrs`, que não entra no hash do fact, e o `fuse` descartava uma das duas
  recusas.

### A decisão do operador

O `Map` inline levantou uma pergunta de escopo que não era minha: a recusa deve calar
também o `sfn.job_run`? O operador decidiu em 2026-09-20 que **não** — o `JobRunId` é um
**valor** que o arquivo publica literalmente, não uma ordem, e é a única ponte para o
`finops`. A recusa cala a numeração; o id sobrevive, com `subject.symbol` sem `#<n>` e sem
`attempt_index`. É o D6 do design, acrescentado depois da revisão.

## Desvios do plano

1. **O plano errou a previsão do gate de lastro nas quatro tarefas.** Na T1 previu oito
   alegações de bytes e caiu **uma**, noutro documento; na T2 caíram **duas**; na T3
   **nenhuma**; na T4 **nenhuma**. Todas remediadas pela lista de ids da saída, com o valor
   vindo de rodar a própria prova.
2. **Dois campos `context` do `docs/claims.lock.json` estavam defasados desde remediações
   anteriores** — um dizia `156534` onde o documento já dizia `242888`. O gate **não
   confere esse campo**, e é por isso que ele apodrece calado. Realinhados.
3. **`docs/vnext/adrs/ADR-010-code-intelligence-indice-local.md` entrou fora do
   manifesto**, e a linha dele foi acrescentada ao design (achado F5). Mais três linhas:
   a fixture do `Map` e os dois goldens regenerados.
4. **O `--update` do `check_surface_lock.py` não imprime o crescimento**, ao contrário do
   que o plano previa. Medido pelo diff do lock e pelo assert do teste vermelho.
5. **Uma fixture a mais que o design previa**: `map_inline_iteracoes`, que a revisão
   mostrou faltar. São quatro no corpus novo, não três.
6. **`docs/sdd/SFN_TENTATIVA/plan.md` tem prosa hoje desatualizada** (cinco trechos que
   ainda dizem que o `sfn.job_run` é calado junto com a tentativa). Plano é registro
   histórico e não foi reescrito; o D6 do design é que vale.
7. **A revisão em dois estágios por tarefa não rodou**; a revisão final do diff inteiro
   rodou, e é dela que vieram os seis achados.

## Medidas

| | antes (`4862921a`) | depois |
|---|---|---|
| tipos conhecidos | 59 de 62 publicados | 62 de 62 |
| razões de `sfn.unresolved` | 20 | 23 |
| fixtures golden | 551 em 59 domínios | 555 em 59 |
| `knowledge.total_bytes` | 532 870 | 536 670 |
| goldens passando | 3291 | 3299 |
