---
sdd: 1
feature: SFN_TENTATIVA
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/SFN_TENTATIVA/explore.md
  sha256: "b36aefb8596c1309f297938c24722934bd1f18057309f64ff4fe6b7ffbfdbb78"
hypothesis:
  claim: "Os dois casos em que o extrator de historico hoje AFIRMA um numero que o arquivo nao sustenta -- a contagem que atravessa um redrive e o attempt_index de estados homonimos em ramos diferentes de um Parallel -- podem virar recusa nomeada sem tocar o caso que a SF-SFNX-001 existe para medir, que e o retry de um estado num fluxo de ramo unico."
  prediction: "Sobre fixtures sinteticas construidas a partir da forma de evento publicada: um historico com ExecutionRedriven sai com recusa propria e NAO produz sfn.retry_observado, e a SF-SFNX-001 fica calada nele; um historico com Parallel cujos dois ramos tem um estado de mesmo nome nao produz sfn.attempt daquele nome, sai recusado, e SF-SFNX-002 e SF-SFNX-003 ficam caladas ali; e um historico de ramo unico com o mesmo estado agendado varias vezes continua produzindo um sfn.attempt por agendamento, com indices 1..n, e a SF-SFNX-001 continua disparando e continua calada na fronteira. Se a recusa do redrive nao aparecer, se algum sfn.attempt for emitido no caso homonimo, se os indices do caso de ramo unico mudarem, ou se algum golden de achado existente mudar, a afirmacao esta errada."
  experiment: "Rodar sparkforge analyze sfn-history e judge sobre as fixtures novas, fuse sobre a fixture pareada ASL + historico com redrive, e python -m pytest tests/test_fixtures_golden*.py -q sem regenerar."
acceptance:
  - id: AC1
    statement: "ExecutionRedriven deixa de sair como event_type_unknown e passa a sair em sfn.unresolved com razao propria, nomeando o evento; EvaluationFailed e MapRunRedriven entram na lista de tipos conhecidos e nao produzem fact nem recusa, como os demais MapRun*."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_redrive_sai_com_razao_propria_e_os_outros_dois_tipos_entram_calados"}
  - id: AC2
    statement: "Com ExecutionRedriven no historico, build_sfn_retry_observado NAO emite sfn.retry_observado para aquele artefato: sai sfn.unresolved com razao propria, porque um teto declarado no ASL nao se compara com uma contagem que atravessa um redrive."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_redrive_recusa_o_confronto_em_vez_de_comparar"}
  - id: AC3
    statement: "Num historico com Parallel em que dois ramos tem um estado de mesmo nome, nenhum sfn.attempt daquele nome e emitido e sai sfn.unresolved nomeado; os estados de nome unico do mesmo historico continuam virando tentativa normalmente."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_estado_homonimo_em_ramos_diferentes_sai_recusado_sem_indice"}
  - id: AC4
    statement: "Historico de ramo unico com o mesmo estado agendado varias vezes continua produzindo um sfn.attempt por agendamento, com attempt_index 1..n na ordem do arquivo: a mudanca nao toca o caso que a SF-SFNX-001 mede."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_ramo_unico_com_retry_mantem_os_indices"}
  - id: AC5
    statement: "As tres regras da area SF-SFNX se comportam como o corpus declara: SF-SFNX-001 calada na fixture de redrive e nas fixtures que ja existiam onde estava calada, e SF-SFNX-002 e SF-SFNX-003 caladas na fixture de Parallel homonimo."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"}
  - id: AC6
    statement: "As lacunas 8 e 9 de knowledge/stepfunctions/execution-history.md sao reescritas para o comportamento novo, dizendo o que o extrator passou a recusar e o que continua aberto; o bundle offline continua integro."
    verified_by: {kind: command, ref: "python scripts/verify_offline_bundle.py"}
  - id: AC7
    statement: "Os registros que extrator, corpus de fixture, regra e documento de knowledge movem estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "sfn.attempt e sfn.unresolved emitidos por fixture, antes e depois"
    source: "goldens de fixtures/sfn_history"
  - id: SC2
    metric: "Goldens de achado existentes que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
  - id: SC3
    metric: "Fixtures do corpus sfn_history e razoes de sfn.unresolved distintas, antes e depois"
    source: "fixtures/sfn_history/ e sparkforge/facts/sfn_history.py"
out_of_scope:
  - "Numerar as tentativas por ENTRADA de estado (abordagem B do explore): pende da lacuna U1 e seria trocar um indice errado por outro."
  - "A reentrada de estado por Choice, que continua contada como tentativa."
  - "Seguir as execucoes filhas de um Distributed Map (mapRunArn): continua fora, como na SFN_HISTORY."
  - "Ler o redriveCount ou qualquer medida do redrive: a feature RECUSA o confronto, nao o mede."
  - "EXPRESS: a API nao suporta o historico dele."
unknowns:
  - id: U1
    blocks: [AC4]
    unlock: "Se o Retry do Step Functions reentra no estado -- ou seja, se ele emite um NOVO TaskStateEntered por tentativa -- nao esta em nenhuma das quatro paginas ja citadas em knowledge/stepfunctions/execution-history.md. E ela que decide se a numeracao por entrada (abordagem B) e possivel. Destrava: a pagina de tratamento de erro lida com esse foco, ou um historico real com retry."
  - id: U2
    blocks: [AC3]
    unlock: "A lacuna 8 do documento de conhecimento: nenhuma frase publicada diz que, dentro de um Parallel, o previousEventId aponta para o anterior do MESMO ramo. A deteccao do caso homonimo usa essa premissa, e se ela estiver errada o efeito e recusar demais, nunca afirmar de menos. Destrava: um historico real com Parallel."
  - id: U3
    blocks: [AC1]
    unlock: "A forma do evento ExecutionRedriven nao foi lida: se ele traz detalhes proprios (um redriveCount, por exemplo) nao esta nas paginas citadas. A feature so precisa do TIPO, e por isso a lacuna nao a bloqueia -- mas ela nomeia o que faltaria para medir o redrive em vez de recusa-lo. Destrava: a pagina do HistoryEvent lida com esse foco, ou um historico real com redrive."
change_kinds: [extractor, rule, fixture_corpus, knowledge_doc, status_numbers, claims]
---

# SFN_TENTATIVA — requisitos

## Problema

O extrator de histórico afirma, hoje, dois números que o arquivo não sustenta.

O primeiro é a contagem que **atravessa um redrive**. Um redrive reagenda o Task dentro
da mesma execução, e nada no extrator separa as tentativas de antes das de depois — o
`ExecutionRedriven` sai como tipo desconhecido, o que diz "não conheço esta palavra"
quando a frase certa é "conheço, e ela diz que minha contagem não é comparável com o teto
declarado no ASL".

O segundo é o `attempt_index` de **estados homônimos em ramos diferentes de um
`Parallel`**. O contador `ordem_por_estado` é chaveado só pelo nome do estado, então a
primeira tentativa do segundo ramo sai com índice 2. Esse índice é o `subject.symbol` do
`sfn.attempt`, e é por ele que a SF-SFNX-002 e a SF-SFNX-003 apontam o achado.

Os dois são o mesmo defeito: **afirmação onde cabia recusa**, contra a regra 20 do
`CLAUDE.md`.

## Fontes citadas

`knowledge/stepfunctions/execution-history.md` §5, lacunas 8 e 9, relidas em 2026-09-20,
e as duas páginas da API que elas citam. O `explore.md` desta feature transcreve as
frases que decidem.

## Critérios

- AC1 e AC2 são o redrive: o tipo passa a ser conhecido, e a consequência dele é recusar
  o confronto.
- AC3 e AC4 são o par que define o escopo da mudança: o caso homônimo passa a recusar, e
  o caso de ramo único — o que a SF-SFNX-001 existe para medir — fica **intacto**. O AC4
  é o critério que impede a correção de virar regressão.
- AC5 é o corpus.
- AC6 e AC7 são os registros.
