---
sdd: 1
feature: SFN_TENTATIVA
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SFN_TENTATIVA/define.md
  sha256: "5a7576a7df05bdbb179527daf1b907eb8fa2bcbfdfdd99b580a99be94bdcbfa1"
files:
  - {path: tests/test_sfn_history.py, action: modify, reason: "os quatro testes de AC1 a AC4, escritos antes do codigo"}
  - {path: sparkforge/facts/sfn_history.py, action: modify, reason: "os tres tipos entram em _TIPOS_CONHECIDOS; ExecutionRedriven ganha razao propria; a numeracao passa pelo teste de ancestralidade entre entradas de mesmo nome; build_sfn_retry_observado recusa o artefato com redrive"}
  - {path: rules/catalog/sfn-history.yaml, action: modify, reason: "o bloco de abertura da area e a explanation da SF-SFNX-001 passam a dizer que a contagem nao atravessa um redrive, e por que"}
  - {path: fixtures/sfn_history/execucao_com_redrive/meta.yaml, action: create, reason: "a fixture de AC1 e AC2: historico com ExecutionRedriven mais o ASL pareado, SF-SFNX-001 calada"}
  - {path: fixtures/sfn_history/parallel_estado_homonimo/meta.yaml, action: create, reason: "a fixture de AC3: dois ramos de um Parallel com um estado de mesmo nome, nenhum sfn.attempt daquele nome"}
  - {path: fixtures/sfn_history/retry_em_ramo_unico/meta.yaml, action: create, reason: "a fixture NEGATIVA de AC4: reentrada sequencial do mesmo estado continua numerada 1..n, e e ela que mata a troca do teste de ancestralidade por um teste so de contagem"}
  - {path: tests/test_fixtures_golden_sfn_history.py, action: modify, reason: "as tres fixtures entram em REQUIRED_FIXTURES, a lista escrita a mao que impede o corpus de encolher calado"}
  - {path: knowledge/stepfunctions/execution-history.md, action: modify, reason: "AC6: as lacunas 8 e 9 sao reescritas para o que o extrator passou a recusar, e a 9 registra o que ainda faltaria para MEDIR o redrive"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "o sha256 do documento editado, regravado por sparkforge.tools.offline._content_sha256"}
  - {path: docs/surface.lock.json, action: modify, reason: "editar um .md de knowledge/ move knowledge.total_bytes e knowledge.by_name_sha256: measure_surface mede o conteudo byte a byte. Sem isto, test_surface_lock::TestOLockBateComAMedida::test_the_knowledge_matches fica vermelho"}
  - {path: fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json, action: modify, reason: "a consequencia medida do D5: a explanation da regra viaja dentro do Finding, e a SF-SFNX-001 aparece em UM so golden do repositorio. Regenerado no mesmo commit da mudanca de prosa"}
  - {path: docs/guia/usos/step-functions.md, action: modify, reason: "as duas razoes novas de sfn.unresolved entram na pagina: recusa que o operador ve e a pagina nao nomeia e lacuna de documentacao"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "AC7: a contagem de fixtures golden, que as tres fixtures movem"}
  - {path: docs/claims.lock.json, action: modify, reason: "as alegacoes de bytes do corpus *.py que a edicao de sfn_history.py move, remediadas por id"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "os numeros auditados que as mesmas alegacoes publicam"}
  - {path: docs/vnext/adrs/ADR-010-code-intelligence-indice-local.md, action: modify, reason: "a mesma alegacao de bytes do corpus *.py que docs/claims.lock.json remedia publica um numero aqui; o gate de lastro a listou por id e a remediacao tocou este arquivo. Achado F5 da revisao final"}
  - {path: fixtures/sfn_history/map_inline_iteracoes/meta.yaml, action: create, reason: "a fixture do F2: duas iteracoes de um Map INLINE caem na mesma recusa de nome que os ramos de um Parallel, e os dois sfn.job_run sobrevivem a ela sem #<n> e sem attempt_index. O define so falava de Parallel, e nao havia fixture de Map nenhuma no corpus"}
  - {path: fixtures/sfn_history/parallel_estado_homonimo/expected/facts.json, action: modify, reason: "o F2 aplicado a fixture que ja exercitava o caminho da recusa: os dois sfn.job_run dos ramos passam a sair, e job_run_count vai de 1 para 3. Regenerado pelo nome"}
  - {path: fixtures/sfn_history/historico_truncado/expected/facts.json, action: modify, reason: "o F4, divida anterior a esta feature: read_events sai de attrs para measures e os dois facts que colidiam no id f_bae972 passam a sobreviver ao fuse. Regenerado pelo nome"}
decisions:
  - id: D1
    choice: "O caso homonimo e detectado por ANCESTRALIDADE entre as entradas de mesmo nome, nao pela presenca de um Parallel no arquivo. Para um nome de estado, o extrator junta os `TaskStateEntered` distintos aos quais os `TaskScheduled` daquele nome se encadeiam; se DOIS deles forem mutuamente nao-ancestrais -- nenhum alcanca o outro subindo `previousEventId` --, o nome nao identifica um estado naquele historico: nenhum `sfn.attempt` dele e emitido e sai `sfn.unresolved` nomeado."
    rejected:
      - "Chavear `ordem_por_estado` pelo id do `TaskStateEntered` (abordagem B do explore): resolveria tambem a reentrada por Choice, mas se o Retry reentrar no estado todo retry vira indice 1 e a SF-SFNX-001 perde a medida que ela existe para fazer. E a lacuna U1, e ela nao esta fechada."
      - "Disparar a recusa quando o arquivo contem qualquer evento de Parallel ou Map: mais simples, e recusa DEMAIS -- um estado de nome unico retentado dentro de um Parallel perderia a numeracao sem motivo."
      - "Numerar assim mesmo e marcar o fact como suspeito: manteria o attempt_index errado ancorando a SF-SFNX-002 e a SF-SFNX-003, que e o defeito que a feature existe para tirar."
    rollback: "git revert do commit da deteccao; a numeracao volta a ser por nome e o corpus volta pelo golden regenerado."
  - id: D2
    choice: "A ancestralidade e indiferente a lacuna U1 POR CONSTRUCAO: reentrada sequencial (retry ou Choice) deixa a entrada anterior na cadeia da seguinte, entao as duas sao ancestrais uma da outra e continuam numeradas; ramos concorrentes de um Parallel nunca se alcancam. O criterio nao pergunta se o Retry reentra no estado, que e justamente o que ninguem mediu."
    rejected: ["Fechar a U1 antes de agir, lendo a pagina de tratamento de erro com esse foco: seria uma leitura util, mas a feature nao precisa dela, e o define ja registra a lacuna com o que a destrava."]
    rollback: "o mesmo revert de D1."
  - id: D3
    choice: "O redrive age em DOIS lugares, com nomes diferentes: o extrator emite `sfn.unresolved` com razao `execution_redriven` por evento `ExecutionRedriven` (com o `event_id` em `measures`, como as demais recusas desde 20b3bce2), e `build_sfn_retry_observado` passa a ler as recusas do pool, e para cada artefato que tenha uma delas emite `sfn.unresolved: redrive_in_execution` NO LUGAR do `sfn.retry_observado`. As tentativas continuam sendo extraidas e publicadas; o que se recusa e a COMPARACAO com o teto declarado."
    rejected:
      - "Nao emitir `sfn.attempt` nenhum no historico com redrive: apagaria medida que o arquivo sustenta. O que o redrive quebra e a comparabilidade com o ASL, nao a leitura das tentativas."
      - "Contar o redrive e comparar mesmo assim, com um aviso: exigiria saber quantas tentativas cairam antes e quantas depois, e a forma do evento nao foi lida (U3)."
    rollback: "git revert do commit do redrive; `ExecutionRedriven` volta a `event_type_unknown` e a derivacao volta a comparar."
  - id: D4
    choice: "`EvaluationFailed` e `MapRunRedriven` entram em `_TIPOS_CONHECIDOS` sem consequencia nenhuma, como os demais `MapRun*` ja estao: tipo conhecido que nao produz fact. Com isso `_TIPOS_CONHECIDOS` passa a ser IGUAL aos 62 `Valid Values` publicados, e o comentario acima dela deixa de descrever um subconjunto."
    rejected: ["Deixar os dois de fora e tratar so o redrive: manteria a lista publicada e a do codigo divergentes por dois nomes, que e o defeito que a lacuna 9 aponta."]
    rollback: "git revert do commit; os dois voltam a sair em event_type_unknown."
  - id: D5
    choice: "A prosa da area SF-SFNX e da SF-SFNX-001 passa a dizer que a contagem nao atravessa um redrive, e por que. Regra que afirma o que o extrator recusa foi achado IMPORTANTE em duas das tres features anteriores (#91 e #92), e a correcao entra no mesmo commit da mudanca de comportamento."
    rejected: ["Deixar a prosa para um commit de documentacao depois: e exatamente o que produziu os dois achados anteriores."]
    rollback: "git revert do commit da regra; o texto volta, e o golden dos findings e regenerado pelo caminho do proprio teste."
  - id: D6
    choice: "A recusa cala a NUMERACAO, nao o valor: no caminho de `state_name_in_concurrent_branches` o `sfn.job_run` continua saindo, com `subject.symbol` igual ao nome do estado SEM o `#<n>` e sem `attempt_index` nas `measures`. O `JobRunId` e um VALOR que o arquivo publica literalmente, nao uma ordem, e e a unica ponte para o `finops`. Decidido pelo operador em 2026-09-20, depois que a revisao final mediu o alcance real: iteracoes de um `Map` INLINE divergem no `MapStateStarted` comum exatamente como ramos de um `Parallel`, entao todo estado dentro de um `Map` cai na recusa -- 400 iteracoes produziam 400 tentativas e passaram a produzir zero, com os `JobRunId` indo junto."
    rejected:
      - "Declarar a perda e seguir: menor diff, e cortaria a ponte para o `finops` em todo job com `Map` ou `Parallel`, por um defeito que e so de ORDEM."
      - "Restringir a recusa ao `Parallel`, exigindo que o ancestral comum seja um `ParallelStateStarted`: `Map` inline voltaria a ser numerado com o mesmo indice errado que a feature existe para tirar."
      - "Emitir so o `sfn.job_run` legivel e calar o ilegivel: afirmacao parcial, que a regra 20 proibe. As duas recusas de leitura do `output` saem no mesmo caminho."
    rollback: "git revert do commit do F2; o `sfn.job_run` volta a ser calado junto com a tentativa, e as fixtures `map_inline_iteracoes` e `parallel_estado_homonimo` voltam pelo golden regenerado."
covers:
  - {part: "tipos conhecidos e a razao do redrive", acceptance: [AC1]}
  - {part: "recusa do confronto na derivacao", acceptance: [AC2]}
  - {part: "ancestralidade entre entradas de mesmo nome", acceptance: [AC3, AC4]}
  - {part: "corpus de fixture e golden", acceptance: [AC5]}
  - {part: "conhecimento e guia", acceptance: [AC6]}
  - {part: "registros", acceptance: [AC7]}
---

# SFN_TENTATIVA — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| tipos conhecidos e a razão do redrive | `sparkforge/facts/sfn_history.py`, `tests/test_sfn_history.py` | AC1 |
| recusa do confronto na derivação | `sparkforge/facts/sfn_history.py`, `tests/test_sfn_history.py` | AC2 |
| ancestralidade entre entradas de mesmo nome | `sparkforge/facts/sfn_history.py`, `tests/test_sfn_history.py` | AC3, AC4 |
| corpus de fixture e golden | `fixtures/sfn_history/*` (3 novas), `fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json`, `tests/test_fixtures_golden_sfn_history.py`, `rules/catalog/sfn-history.yaml` | AC5 |
| conhecimento e guia | `knowledge/stepfunctions/execution-history.md`, `knowledge/offline-manifest.json`, `docs/surface.lock.json`, `docs/guia/usos/step-functions.md` | AC6 |
| registros | `docs/superpowers/STATUS.md`, `docs/claims.lock.json`, `docs/harness/CODEINTEL-GAP.md` | AC7 |

## O critério que decide, em uma frase

**Reentrada sequencial deixa rastro na cadeia; ramos concorrentes não.** Quando um estado
é reentrado por retry ou por `Choice`, a entrada anterior está na cadeia de
`previousEventId` da seguinte — uma alcança a outra. Quando dois ramos de um `Parallel`
têm um estado de mesmo nome, nenhuma das duas entradas alcança a outra: elas divergem no
`ParallelStateStarted` comum.

É por isso que o D2 existe como decisão separada: esse critério **não pergunta** se o
`Retry` reentra no estado, que é exatamente a lacuna U1. Qualquer que seja a resposta, a
reentrada é sequencial e continua numerada.

## O que cada fixture nova prova

- `execucao_com_redrive` — AC1 e AC2. O histórico traz `ExecutionRedriven`, e o ASL
  pareado traz o `MaxAttempts`. A SF-SFNX-001 fica **calada**: sem a recusa, ela dispararia
  sobre uma contagem que soma as tentativas de antes e as de depois do redrive.
- `parallel_estado_homonimo` — AC3. Dois ramos, um estado `Carga` em cada. Nenhum
  `sfn.attempt` de `Carga`, e os estados de nome único do mesmo histórico continuam
  virando tentativa.
- `retry_em_ramo_unico` — AC4, e é a **negativa** do D1. O mesmo estado agendado três
  vezes em sequência, com índices 1, 2 e 3. É ela que mata a troca do teste de
  ancestralidade por um teste só de contagem de entradas: com "mais de uma entrada ⇒
  recusa", esta fixture ficaria vermelha.

## Dois registros que o desenho não tinha visto

O plano achou dois arquivos obrigatórios fora deste manifesto, e eles entraram aqui em
vez de virarem desvio do build:

- **`docs/surface.lock.json`.** Editar um `.md` de `knowledge/` move `knowledge.total_bytes`
  e `knowledge.by_name_sha256`, porque `measure_surface` mede o conteúdo byte a byte. Sem
  ele, `tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches`
  fica vermelho.
- **`fixtures/sfn_history/retry_acima_do_declarado/expected/findings.json`.** A consequência
  medida do D5: a `explanation` da regra viaja **dentro** de cada `Finding`, e a
  SF-SFNX-001 aparece em **um só** golden do repositório. Ele é regenerado no mesmo commit
  da mudança de prosa.

## Conhecimento consultado

`knowledge/stepfunctions/execution-history.md` §5, lacunas 8 e 9, lidas por
`sparkforge knowledge path` em 2026-09-20 — são elas que dão os 62 `Valid Values`, os três
tipos que faltam, a semântica do redrive e a premissa não publicada do `previousEventId`
por ramo. As páginas que as sustentam estão na seção `## Fontes` do mesmo documento, com
a data de leitura.

Nenhuma afirmação nova sobre a API entra nesta feature: ela age sobre o que aquele
documento já mediu e já recusou.
