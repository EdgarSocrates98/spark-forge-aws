---
sdd: 1
feature: SFN_TENTATIVA
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SFN_TENTATIVA/build_report.md
  sha256: "fc7dbeeb5444279b60713cfe38f0022461bd2c335f48fc84b5cf4a2823b05294"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, runtime_scope_gates, fixture_corpus_gates, offline_manifest, sources_lock, surface_lock, generated_reference, sync_skills, agents_parity, router_gates, status_numbers_gate, claims_gate]
deviations:
  - "A revisao final do diff inteiro achou um critico, tres importantes e dois menores, corrigidos em sete commits. O critico: _ancestrais descartava a razao de parada da travessia, entao cadeia quebrada e ciclo saiam com o nome de ramos concorrentes E levavam junto todas as tentativas do estado, num arquivo sem Parallel nenhum."
  - "O alcance real era maior do que o design declarava: iteracoes de um Map INLINE caem na mesma recusa que ramos de um Parallel, e o define so falava de Parallel. O operador decidiu em 2026-09-20 preservar o sfn.job_run na recusa, e isso virou o D6 do design, escrito DEPOIS da revisao."
  - "Uma fixture a mais que o design previa: map_inline_iteracoes, que a revisao mostrou faltar. Sao quatro no corpus novo, nao tres."
  - "Quatro linhas acrescentadas ao manifesto do design depois do build: o ADR-010 (achado F5), a fixture do Map, e os dois goldens regenerados. A cascata foi recarimbada."
  - "O AC4 nao teve vermelho proprio: test_ramo_unico_com_retry_mantem_os_indices e guarda de regressao, e o plano previu que ficaria verde no vermelho da T2. A revisao mostrou o limite dela: a fixture tem cadeia perfeita, e a regressao do critico passou por baixo."
  - "O plano errou a previsao do gate de lastro nas quatro tarefas: previu oito alegacoes de bytes e caiu uma noutro documento (T1), duas (T2), nenhuma (T3), nenhuma (T4). Todas remediadas pela lista de ids da saida."
  - "Dois campos context do docs/claims.lock.json estavam defasados desde remediacoes anteriores, um deles por 86 mil bytes. O gate NAO confere esse campo. Realinhados."
  - "docs/sdd/SFN_TENTATIVA/plan.md tem cinco trechos de prosa hoje desatualizados, que ainda dizem que o sfn.job_run e calado junto com a tentativa. Plano e registro historico e nao foi reescrito; o D6 do design e que vale."
  - "A revisao em dois estagios por tarefa nao rodou; a revisao final do diff inteiro rodou."
---

# SFN_TENTATIVA — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de quatro jeitos, e nenhum aconteceu na árvore
final:

- **Um histórico com `ExecutionRedriven` sai com recusa própria e não produz
  `sfn.retry_observado`**, e a SF-SFNX-001 fica sem âncora naquele arquivo.
- **Um `Parallel` cujos dois ramos têm um estado de mesmo nome não produz `sfn.attempt`
  daquele nome**, e sai recusado.
- **Um histórico de ramo único com o mesmo estado agendado três vezes continua produzindo
  três tentativas, com índices 1, 2 e 3.**
- **Nenhum golden de achado existente mudou.** `pytest tests/test_fixtures_golden*.py` dá
  3299 passed, 4 skipped, sem regeneração.

**O que quase invalidou a terceira parte, e por que ela ainda vale.** No fim do build, a
detecção descartava a razão de parada da travessia, então um histórico de **ramo único**
com a cadeia interrompida perdia todas as suas tentativas e ganhava uma recusa afirmando
ramos concorrentes. A fixture do AC4 tem cadeia perfeita e não pegou. A revisão final
pegou, a correção passou a exigir que os dois passeios do par cheguem à raiz limpos, e o
caso que faltava virou teste. **A previsão está confirmada sobre a árvore que entrega.**

## O que a feature entrega

Duas afirmações que o extrator fazia sem base viraram recusa com nome:

- **O redrive.** `ExecutionRedriven` entrou na lista de tipos conhecidos com razão própria,
  e `build_sfn_retry_observado` recusa a **comparação** com o teto declarado no ASL para o
  artefato que tenha redrive. As tentativas continuam medidas: o que o redrive quebra é a
  comparabilidade, não a leitura. `EvaluationFailed` e `MapRunRedriven` entraram calados, e
  com isso a lista do código passou a ser **igual** aos 62 `Valid Values` publicados.
- **O nome do estado que não identifica uma tentativa.** Quando dois `TaskStateEntered` de
  mesmo nome são mutuamente não-ancestrais — ramos de um `Parallel`, iterações de um `Map`
  inline —, o extrator para de numerar e recusa. Quando a cadeia entre eles está
  interrompida ou é cíclica, a recusa é **outra**, com a parada nomeada: as duas causas não
  compartilham nome.

**O que a recusa não cala:** o `sfn.job_run`. O `JobRunId` é um valor que o arquivo publica
literalmente, não uma ordem, e é a única ponte para o `finops` (D6).

## Medidas

| | antes (`4862921a`) | depois |
|---|---|---|
| tipos conhecidos | 59 de 62 publicados | 62 de 62 |
| razões de `sfn.unresolved` | 20 | 23 |
| fixtures golden | 551 em 59 domínios | 555 em 59 |
| `knowledge.total_bytes` | 532 870 | 536 670 |
| goldens passando | 3291 | 3299 |

Nenhuma regra, área, tool, extrator ou rota foi acrescentada: a feature muda o que um
extrator existente afirma, não o que o catálogo cobre.

## Gates rodados

| gate | resultado |
|---|---|
| extrator, golden da feature, fusão, gêmea, domínio, SDD (7 arquivos) | 320 passed |
| regra, catálogo, eixo, governança, escopo por natureza (10 arquivos) | 1490 passed |
| cobertura de kind, snippet, bundle, superfície, referência, números, agente (10 arquivos) | 489 passed |
| `python scripts/sync_skills.py --check` | exit 0 |
| `python scripts/verify_offline_bundle.py` (AC6) | `"ok": true` |
| `python scripts/check_surface_lock.py` | 0 divergências |
| `python scripts/check_status_numbers.py --strict` (AC7) | 0 divergências |
| `python scripts/check_vnext_claims.py` | 0 divergências |
| `python -m ruff check sparkforge scripts tests` | limpo |
| `python -m pytest tests/test_fixtures_golden*.py -q` | 3299 passed, 4 skipped |
| `sparkforge sdd check --repo . --feature SFN_TENTATIVA` | `ok: true`, 0 recusas, 0 lacunas |

Os dois `verified_by` de `kind: command` do define:

| critério | comando | exit |
|---|---|---|
| AC6 | `python scripts/verify_offline_bundle.py` | 0 |
| AC7 | `python scripts/check_status_numbers.py --strict` | 0 |

## Pendências

- **U1 continua aberta**, e por desenho a feature não precisou dela: se o `Retry` reentra
  no estado não está em nenhuma das páginas lidas, e o critério de ancestralidade não
  pergunta. Ela volta a importar se alguém quiser numerar por entrada.
- **U2 continua aberta.** A premissa do `previousEventId` por ramo não está publicada, e
  agora o extrator **age** sobre ela. Se ela estiver errada, o efeito é recusa a mais,
  nunca afirmação a menos — e o corpus sintético exercita o mecanismo, não a premissa.
- **U3 continua aberta.** Medir o redrive em vez de recusá-lo exige a forma do evento, que
  não foi lida.
- **Map distribuído (`mapRunArn`)** continua fora, como na SFN_HISTORY.
- **A reentrada por `Choice`** continua contada como tentativa, e está no `out_of_scope`.
- **Nenhum histórico real foi observado.** As quatro fixtures novas são sintéticas.

## Lições

- **A revisão final achou o crítico num caso construído, não num teste vermelho** — pela
  terceira feature seguida. Ela mediu em memória, importando só `sparkforge.facts.*`, e
  montou o que o corpus não tem: `Map` de 400 iterações, ciclo na cadeia, redrive junto com
  `Parallel` homônimo. É essa a técnica que pega o defeito, e vale repeti-la por padrão.
- **Guarda de regressão cobre o caso que ela constrói, e nada além.** O AC4 existia para
  impedir que "recusar mais" virasse "recusar tudo", e não impediu — porque a fixture dele
  tem cadeia perfeita e o defeito estava na cadeia quebrada.
- **Recusa com o nome errado é pior que recusa sem nome.** O crítico não apagava só dado:
  ele afirmava "ramos concorrentes" num arquivo sem `Parallel` nenhum. Quando uma função
  nova consome outra que distingue causas de propósito, descartar essa distinção é o
  defeito.
- **Campo que nenhum gate confere apodrece calado.** Dois `context` do `claims.lock.json`
  estavam defasados desde remediações anteriores, um deles por 86 mil bytes.
