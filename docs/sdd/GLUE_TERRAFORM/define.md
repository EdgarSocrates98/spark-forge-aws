---
sdd: 1
feature: GLUE_TERRAFORM
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/GLUE_TERRAFORM/explore.md
  sha256: "68d07e569155cc36228ffa3925b2ea5777046dde43ab4038d68ac086e555cf92"
hypothesis:
  claim: "As duas funcoes hoje duplicadas entre stepfunctions.py e airflow_dag.py -- o indice de nome literal de job Glue vindo de tf.attribute, e a leitura de max_retries com as tres origens -- podem morar num modulo auxiliar unico sem que NENHUM fact mude de conteudo e sem que a contagem de extratores se mova, porque o que distingue extrator de auxiliar em todas as varreduras do repositorio e ter EMITTED_KINDS."
  prediction: "Depois da mudanca: as duas funcoes existem uma vez so, em sparkforge/facts/glue_terraform.py, e nenhum dos dois extratores guarda copia local; o modulo NAO tem EMITTED_KINDS e NAO entra nas duas listas manuais de teste nem na medida de snippet; a contagem publicada de extratores de facts continua a mesma; e a suite inteira de goldens passa SEM regeneracao. Se algum golden mudar, se a contagem de extratores se mover, ou se alguma copia local sobreviver, a afirmacao esta errada."
  experiment: "Rodar os goldens de stepfunctions, airflow e fusao, depois python -m pytest tests/test_fixtures_golden*.py -q sem regenerar, e python scripts/check_status_numbers.py --strict."
acceptance:
  - id: AC1
    statement: "sparkforge/facts/glue_terraform.py existe com as duas funcoes publicas, e nem stepfunctions.py nem airflow_dag.py guardam copia local delas: os dois importam do modulo novo."
    verified_by: {kind: test, ref: "tests/test_glue_terraform.py::test_a_definicao_e_unica_e_os_dois_extratores_importam"}
  - id: AC2
    statement: "As duas funcoes continuam respondendo o mesmo: o indice devolve nome literal de job -> [(arquivo, endereco, id)] so para tf.attribute name literal no bloco root de aws_glue_job, e max_retries devolve literal/absent/not_literal pelas mesmas regras, inclusive o not_literal conservador quando ha tf.unresolved de max_retries no MESMO arquivo."
    verified_by: {kind: test, ref: "tests/test_glue_terraform.py::test_as_tres_origens_de_max_retries_e_o_indice_por_nome"}
  - id: AC3
    statement: "O modulo auxiliar NAO e contado como extrator: ele nao tem EMITTED_KINDS, nao entra em tests/test_rules_catalog_reachability.py::EXTRACTORS nem em tests/test_fixtures_kind_coverage.py::EXTRACTORS, e nao entra na medida de snippet. As tres varreduras do repositorio o ignoram pelo mesmo criterio."
    verified_by: {kind: test, ref: "tests/test_glue_terraform.py::test_o_modulo_auxiliar_nao_conta_como_extrator"}
  - id: AC4
    statement: "As duas derivacoes que consomem as funcoes -- build_sfn_glue_link e build_af_glue_link -- continuam produzindo os mesmos facts: os goldens dos dois dominios passam sem regeneracao."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_airflow.py::test_golden"}
  - id: AC5
    statement: "Os registros que um arquivo .py novo em sparkforge/ move estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Definicoes de _glue_jobs_por_nome e _max_retries no repositorio, antes e depois"
    source: "grep em sparkforge/facts/"
  - id: SC2
    metric: "Goldens que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
  - id: SC3
    metric: "Extratores de facts publicados, antes e depois"
    source: "python scripts/check_status_numbers.py --strict"
out_of_scope:
  - "Mudar o comportamento de qualquer uma das duas funcoes: esta feature e movimento, nao correcao."
  - "Consolidar outras duplicacoes entre os extratores de orquestracao: so estas duas foram medidas como gemeas identicas."
  - "Dar EMITTED_KINDS ao modulo novo ou transforma-lo em extrator: ele LE facts, nao artefato."
  - "Tocar terraform.py, que e quem PRODUZ o tf.attribute que estas funcoes leem."
unknowns: []
change_kinds: [extractor, status_numbers, claims]
---

# GLUE_TERRAFORM — requisitos

## Problema

`_glue_jobs_por_nome` e `_max_retries` existem duas vezes, em `stepfunctions.py` e em
`airflow_dag.py`, com **corpos idênticos** e docstrings diferentes. A duplicação foi
deliberada no #91 e está escrita no código: *"um leitor de DAG nao deveria importar um
leitor de ASL para saber ler Terraform. O lugar certo da funcao e um modulo proprio (...)
e ele nao esta no manifesto deste desenho."*

Três revisões finais seguidas conferiram à mão que as cópias não divergiram. **Conferência
manual repetida é o sintoma, não a solução.**

## A armadilha que o AC3 existe para travar

O `CLAUDE.md` tem uma regra permanente: *"Extrator novo entra nas duas listas manuais de
teste e na medida de snippet."* Ela está certa — e **não se aplica aqui**, porque o módulo
novo não é extrator.

As três varreduras discriminam pelo mesmo critério, e as duas listas manuais fazem
`frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))`: acrescentar a elas um módulo
sem `EMITTED_KINDS` quebra com `AttributeError`. O comentário de
`tests/test_harness_untrusted.py` já diz a regra por escrito: *"`EMITTED_KINDS` e o que
distingue extrator de modulo auxiliar"*, e a docstring de
`scripts/check_status_numbers.py::_extratores` nomeia o precedente — `runtime_matrix` e
`pricing` moram em `facts/` e não são extratores.

AC3 trava isso num teste, para que a próxima pessoa que seguir o hábito encontre um
vermelho com explicação em vez de um `AttributeError` sem contexto.

## O critério que uma refatoração precisa ter

Refatoração sem mudança de comportamento **não tem vermelho natural**: todo teste já
passa. Por isso o aceite principal não é "os testes passam", é **nenhum golden muda**,
medido sobre a suíte inteira sem regeneração (AC4 e SC2). AC1 e AC2 são o vermelho que o
build consegue produzir — o módulo não existe ainda, e o teste que o importa falha na
coleta.

## Critérios

- AC1 e AC2 são o movimento e o comportamento preservado.
- AC3 é a armadilha acima.
- AC4 é a prova de que nada mudou onde importa.
- AC5 são os registros.
