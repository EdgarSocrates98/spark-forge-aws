---
sdd: 1
feature: DATABRICKS_SPARK
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/DATABRICKS_SPARK/plan.md
  sha256: "a1ed5f837ada38ecf2ffebdf75bb3676d05a563e0d3ff0332f7c463b7b8afa56"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_databricks_runtime_matrix.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_runtime_matrix.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_flag_declara_plataforma_e_deriva_spark -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_flag_declara_plataforma_e_deriva_spark -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_event_log_declara_plataforma_databricks -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_event_log_declara_plataforma_databricks -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_photon_recusa_regra_de_plano -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_photon_recusa_regra_de_plano -q", exit: 0}
  - id: T9
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_flags_seguem_o_emr -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_flags_seguem_o_emr -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_divergencia_spark_registrada -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_divergencia_spark_registrada -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_shuffle_partitions_auto_recusado -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_shuffle_partitions_auto_recusado -q", exit: 0}
  - id: T7
    status: done
    red: {command: "python -m pytest tests/test_databricks_rule_audit.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_rule_audit.py -q", exit: 0}
  - id: T8
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_fixture_pareada_mesmos_findings_neutros -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_fixture_pareada_mesmos_findings_neutros -q", exit: 0}
  - id: T10
    status: done
    red: {command: "python -m pytest tests/test_databricks_platform.py::test_readme_declara_databricks -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_platform.py::test_readme_declara_databricks -q", exit: 0}
claims:
  - text: "A matriz Databricks Runtime -> Spark carrega do YAML com fonte e data, e componente fora de spark estoura pelo loader publico."
    evidence_ref: "tests/test_databricks_runtime_matrix.py::test_matriz_tem_fonte_data_e_vocabulario_fechado"
  - text: "O guard de drift compara a tabela do documento Databricks com o YAML, e uma celula alterada no YAML o faz falhar."
    evidence_ref: "tests/test_runtime_matrix_drift.py"
  - text: "A flag databricks declara a plataforma, normaliza o rotulo da API e deriva spark pela matriz, sem inventar versao fora dela."
    evidence_ref: "tests/test_databricks_platform.py::test_flag_declara_plataforma_e_deriva_spark"
  - text: "A versao do Databricks Runtime em spark.conf_effective do event log detecta a plataforma sem flag; conf pedida em codigo nao conta."
    evidence_ref: "tests/test_databricks_platform.py::test_event_log_declara_plataforma_databricks"
  - text: "Com Photon declarado on sob Databricks, regra que exige kind de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf; sem declaracao, SF-ENV-006 dispara; fora de Databricks nada muda."
    evidence_ref: "tests/test_databricks_platform.py::test_photon_recusa_regra_de_plano"
  - text: "Regra que so exige plan.python_udf continua julgada com Photon on, porque o no ArrowEvalPython segue no plano."
    evidence_ref: "tests/test_databricks_platform.py::test_photon_nao_cala_regra_de_udf_python"
  - text: "Photon declarado sem a plataforma databricks vira divergencia photon: e nao fica no contexto."
    evidence_ref: "tests/test_databricks_platform.py::test_photon_sem_databricks_vira_divergencia"
  - text: "O rotulo 18 e 18.0.x contam como a mesma identidade de Databricks Runtime."
    evidence_ref: "tests/test_databricks_platform.py::test_rotulo_18_0_e_a_mesma_identidade_de_18"
  - text: "Databricks e Glue declarados juntos, pelo caminho de producao, disparam SF-ENV-005 sem SF-ENV-001 falso."
    evidence_ref: "tests/test_databricks_platform.py::test_databricks_com_glue_em_producao_sao_duas_plataformas"
  - text: "Um event log real com a chave de versao, lido pelo extrator, detecta Databricks Runtime 15.4 e Spark 3.5.0."
    evidence_ref: "tests/test_databricks_platform.py::test_event_log_databricks_de_ponta_a_ponta"
  - text: "Photon e excecao nomeada de eixo sem produtor, travada contra virar letra morta."
    evidence_ref: "tests/test_capability_parity.py::TestNoRuntimeAxisIsAnUndeclaredProducerGap::test_declared_only_axes_are_real_axes_without_producer"
  - text: "Todo parser da CLI, schema MCP e funcao publica de _core que aceita emr aceita databricks e photon, repassa os dois ate o runtime, e recusa photon fora de on/off."
    evidence_ref: "tests/test_databricks_platform.py::test_flags_seguem_o_emr"
  - text: "Todo eixo de RuntimeContext e declaravel na CLI e no MCP e tem produtor, com photon como excecao nomeada."
    evidence_ref: "tests/test_capability_parity.py"
  - text: "Spark do event log diferente do derivado pela matriz Databricks vira divergencia registrada e SF-ENV-001, nunca resolucao silenciosa."
    evidence_ref: "tests/test_databricks_platform.py::test_divergencia_spark_registrada"
  - text: "Com spark.sql.shuffle.partitions = auto, o tune recusa com shuffle_partitions_auto e nao propoe numero; com valor numerico, deriva como antes."
    evidence_ref: "tests/test_databricks_platform.py::test_shuffle_partitions_auto_recusado"
  - text: "Regra sem runtime_scope alcancavel por job Databricks so cita termo de AWS se citar Databricks no mesmo texto; SF-PQ-002 e a unica excecao, travada contra virar letra morta."
    evidence_ref: "tests/test_databricks_rule_audit.py::test_regra_sem_escopo_nao_remedia_com_termo_aws"
  - text: "O mesmo event log sob runtime Glue e sob Databricks Runtime 15.4 dispara as mesmas seis regras spark-ui, com a mesma severidade e o mesmo sujeito."
    evidence_ref: "tests/test_databricks_platform.py::test_fixture_pareada_mesmos_findings_neutros"
  - text: "README e STATUS declaram Databricks, o que fica fora, e os numeros correntes medidos batem com o gate."
    evidence_ref: "tests/test_databricks_platform.py::test_readme_declara_databricks"
  - text: "O tune pelo MCP aceita a recusa shuffle_partitions_auto no envelope de saida validado."
    evidence_ref: "tests/test_databricks_platform.py::test_tune_pelo_mcp_aceita_a_recusa_auto"
  - text: "O judge em producao julga os facts de ambiente da deteccao de runtime: SF-ENV-006 dispara sem --photon e cala com --photon off."
    evidence_ref: "tests/test_databricks_platform.py::test_judge_em_producao_julga_facts_de_ambiente"
  - text: "O scan grava no facts.json os facts de ambiente que os achados citam, e rejulgar a saida do scan usa a deteccao nova, nao a gravada."
    evidence_ref: "tests/test_databricks_platform.py::test_scan_grava_os_facts_de_ambiente_que_os_achados_citam"
  - text: "Fact ausente com subject da deteccao de runtime so vira motivo runtime quando a regra do achado exige um kind da deteccao."
    evidence_ref: "tests/test_reporting_github.py::TestLocalizar::test_subject_de_outro_extrator_com_simbolo_de_runtime_continua_evidencia_ausente"
  - text: "Cada passo de proposed_change e validation que cita termo AWS tem equivalente citando Databricks no mesmo campo."
    evidence_ref: "tests/test_databricks_rule_audit.py::test_passo_com_termo_aws_tem_equivalente_neutro_no_mesmo_campo"
change_id: null
---

# DATABRICKS_SPARK — relatório do build

## Desvios do plano

- **T1, vermelho.** O plano previa `AttributeError` sobre `DATABRICKS_COMPONENTS`; o
  teste lê o YAML antes, e o vermelho real foi `FileNotFoundError` do YAML ausente.
  Mesma causa (a unidade sob teste não existia).
- **T1, gate de lastro.** O `.py` novo moveu cinco alegações (VNX-726, VNX-640,
  VNX-674, VNX-675, VNX-767). Remedidas por id em `docs/claims.lock.json` e no
  número em negrito dos documentos auditados (`docs/harness/CODEINTEL-GAP.md`,
  `docs/harness/ICEBERG-GAP.md`, ADR-010), com a contagem de linhas preservada. O
  conserto seguinte moveu VNX-674 de novo (228755 -> 228887).
- **T1, guard de drift fora do manifesto.** A revisão de qualidade achou que
  `tests/test_runtime_matrix_drift.py` não cobria a matriz nova, e nenhuma tarefa o
  registrava. Entrou a plataforma `databricks` em `PLATAFORMAS` (commit `0ba54257`).
  Para não mexer no mecanismo compartilhado de chave, a tabela do documento passou a
  ter coluna `LTS` própria, e a chave ficou igual à do YAML. Prova por mutação:
  célula do YAML alterada fez `tests/test_runtime_matrix_drift.py -k databricks` sair
  com exit 1.
- **T1, teste por loader público.** O plano pedia o caminho de erro por
  `_carrega_matriz_fechada`; trocado pelo `load_databricks()` público com monkeypatch,
  padrão de `tests/test_runtime_matrix.py`.
- **T2, contrato MCP congelado.** O plano punha `databricks` e `photon` em
  `required` do schema de saída do runtime. `fixtures/mcp_parity` é golden congelado
  e só aceita mudança aditiva; os dois campos ficaram só em `properties` (commit
  `893b4a82`), e `tests/test_fixtures_golden_mcp_parity.py` declarou as seis tools
  alteradas e o tamanho medido do diff aceito (23 -> 35 por transporte).
- **T2, goldens além de `fixtures/scan`.** `fixtures/simulate` (6) também serializa o
  contexto e foi regenerado pelo seu runner; `tests/test_runtime_inferred_from_facts.py`
  ganhou as duas chaves no literal que compara com `to_dict()`.
- **T2, vermelho que atravessa commits.** `tests/test_capability_parity.py` exige que
  todo eixo de `RuntimeContext` tenha flag na CLI, flag no MCP e produtor. Os três
  invariantes ficam vermelhos de T2 até T9. Para encurtar o trecho, a ordem de
  execução passou a ser T4, T5, T9, T3, T6, T7, T8 e T10.
- **T2, teste sem privado.** A asserção da origem `cli:matrix` passou a ler o texto
  público de divergência em vez de `_collect` (commit `e3a167b5`).
- **T4, quarto vermelho previsto.** Com produtor para `databricks` e ainda sem flag,
  `test_capability_parity::test_the_flag_surface_and_the_producer_surface_cover_the_same_axes`
  fica vermelho até T9, ao lado dos três de T2.
- **T5, exceção de eixo sem produtor.** `tests/test_capability_parity.py` não tinha
  mecanismo de exceção e o docstring dizia que exceção só nasce com caso real.
  Photon é esse caso: entrou `AXES_DECLARED_ONLY = {"photon": ...}`, um parágrafo ao
  lado do "SEM EXCECAO DECLARADA", e o teste
  `test_declared_only_axes_are_real_axes_without_producer`. O teste de superfície
  compara `produced | AXES_DECLARED_ONLY` com `declared`, e continua exigindo a flag
  `--photon` até T9.
- **T5, só dois casos de runtime.** T3 ainda não existia; o passo 7 atualizou
  `databricks_flag_runtime` e `databricks_event_log_runtime`, e T3 nasce com SF-ENV-006.
- **T5, `test_rules_engine` não alarmou.** O alarme vigia `blocked_on` do catálogo,
  e SF-ENV-006 não tem; não houve decisão a registrar.
- **T5, enum MCP de motivo de pulo.** `_JUDGE_SKIPPED_ITEM.reason` em
  `sparkforge/adapters/tools.py` não conhece `databricks.photon.unresolved`; entra em
  T9, junto da flag que o torna alcançável pelo MCP.
- **T5, citação do comentário do engine.** O plano citava `runtime-matrix.md` seção 3
  para o fallback por operação, e ela não o diz; o comentário passou a citar a
  página oficial do Photon (commit `42e38487`).
- **T9, enum de motivo de pulo no golden MCP.** O crescimento de
  `_JUDGE_SKIPPED_ITEM.reason` (com `databricks.photon.unresolved` no fim) e a
  descrição dele entraram em `REESCRITAS_DEPOIS_DO_GOLDEN`, o mecanismo do teste para
  enum que cresce com os valores antigos na frente (reescritas 8 -> 10); as tools
  novas, em `ALTERADAS_DEPOIS_DO_GOLDEN` (aditivas 35 -> 47).
- **T9, `--photon` com `choices` também nos laços genéricos.** O plano punha a flag
  nas tuplas de proof, simulate e scan sem `choices`, e um valor inválido virava "não
  declarado" em silêncio. Corrigido no commit `4264a95e`, com asserção no teste.
- **T9, `.claude/agents/README.md` apagado e restaurado.** `tests/test_agents_parity.py`
  regenera os espelhos e remove o arquivo não rastreado; restaurado do backup em
  `%TEMP%/claude_agents_README.bak.md`. O arquivo não entrou em commit.
- **T3, depois de T9.** O caso `databricks_divergent_spark` nasceu já com
  `databricks.photon` e `SF-ENV-006` no meta, porque T5 veio antes. O vermelho foi o
  golden ausente (`FileNotFoundError` sobre `expected/findings.json`), já que a
  divergência em si existe desde T2.
- **T7, goldens fora do `regen_fixtures.py`.** `fixtures/change` regenerou pelo
  próprio runner (`SPARKFORGE_REGEN_CHANGE=1`); `fixtures/timeout` não tem regen
  oficial e foi regenerado por script que repete o caminho de
  `tests/test_fixtures_golden_timeout.py::run_fixture`, conferido pelo próprio teste.
- **T7 achou lacuna da T5.** Os goldens de `fixtures/scenarios` (3) e `evals/holdout`
  (2) guardam a contagem do catálogo e não foram regenerados quando SF-ENV-006
  entrou. Fechado no commit `91fddf6`, só com `catalog_rules`, `unguarded_rules`,
  `reachable_rules` e o `statement` que os repete.
- **T8, versão do Spark coerente no par.** O plano mudava só o `Spark Version` do
  `SparkListenerLogStart`; `spark.version` nas `Spark Properties` ficava 3.5.4. Um log
  real de Databricks Runtime 15.4 traz 3.5.0 nos dois lugares; corrigido no commit
  `a3d99aa3`, sem mudar as regras disparadas.
- **T10, números correntes.** `python scripts/check_status_numbers.py --strict`
  reprovava seis dimensões; todas remedidas: regras 191 -> 192, executáveis
  156 -> 157, `SF-ENV` 5 -> 6, kinds de fact 226 -> 227, fixtures golden 510 -> 514,
  fontes vigiadas 249 -> 253 — e duas que já estavam velhas antes desta feature, rotas
  99 -> 101 e vocabulário de `action.kind` 68 -> 70. `STATUS.md` não tem tabela de
  frentes; a feature entrou como seção própria no formato das vizinhas.

- **Revisão final, rodada R1.** A revisão do diff inteiro trouxe 3 críticos, 4
  importantes e 12 menores; os consertos entraram em 10 commits (`faad16b8` a
  `12438712`):
  - C1: `shuffle_partitions_auto` no enum de saída do `sparkforge_tune`; o teste passa
    pelo envelope MCP, o único caminho que valida a saída.
  - C2 (decisão do operador: ligar a porta): `_runtime_e_facts` junta os facts de
    ambiente ao `fact_list` em todo verbo que julga. SF-ENV-001, 004, 005 e 006
    passam a valer em produção; único golden movido foi
    `fixtures/simulate/versao_muda_so_o_runtime`, que ganhou SF-ENV-004 (Glue 3.0 é
    Spark 3.1, sem AQE por default: achado verdadeiro). Nenhum golden ganhou P0.
  - C3 + I1 + I3: auditoria sem diferenciar caixa e sobre todo extrator com
    `EMITTED_KINDS`, menos exclusões nomeadas (extratores só-AWS, `utilization` e dois
    kinds de fusão que só nascem de fonte AWS). 15 regras reescritas.
  - I2: `--photon` sem plataforma databricks vira divergência `photon:`, não fica no
    contexto. M2: `plan.python_udf` fora da recusa de Photon, porque o nó
    `ArrowEvalPython` continua no plano (observado; a página oficial fala em fallback).
  - M3: identidade `18` contra `18.0.x` sem divergência falsa. M4, M5: testes de
    borda, com prova por mutação. M1, M6: refatoração e docstrings.
  - I4: `knowledge/INDEX.md`, lista Cobertura do README e `docs/gates-por-mudanca.md`.
  - M8, M9: forma do rótulo e `runtime_engine` citados pela página da Clusters API
    (`https://docs.databricks.com/api/workspace/clusters/create`); caveat da U1 no
    README; STATUS corrigido nas duas afirmações.
  - Fora desta rodada, como trabalho futuro: M7 (texto de agentes e skills citando
    Databricks), M10 (pista `-photon-` no rótulo, que a mesma página documenta), M11
    (`User` e `spark.master` da fixture).

- **Revisão final, rodada R2.** A segunda volta trouxe 3 importantes e menores de
  texto; consertos em `749f39e6`, `5c01236f` e `3ef09a07`:
  - I-a: o scan grava a união de facts que o `judge` julgou, e `_runtime_e_facts`
    descarta os kinds da detecção vindos na entrada (o id de `databricks.photon` não
    depende do estado, e a detecção velha vazaria ao rejulgar). A equivalência
    `test_scan_igual_ao_fluxo_a_mao` passou a comparar a união.
  - I-b: a auditoria pula só regra com eixo de plataforma AWS (`glue`, `emr`,
    `athena`); SF-SPARK4-001, 003 e 004 e SF-GRAPH-002 entraram e foram reescritas.
  - I-c: `iam_access` saiu das exclusões; SF-IAM-001 ficou neutra. `catalog_schema`
    ficou excluído com motivo: o metastore Glue sob Databricks fica fora desta feature.
  - Conferência por passo em `proposed_change` e `validation` pegou SF-UI-005.
  - Textos (engine, SF-ENV-006, help, `_PHOTON_INPUT`, README, STATUS, U1) passaram a
    descrever o comportamento final.
- **Revisão da R2.** Um importante: a defesa de `locate.py` reconhecia subject da
  detecção só pela forma, e outros extratores (Athena, EMR, benchmark) emitem a mesma
  forma com símbolo arbitrário. Agora também exige que a regra do achado dependa de um
  kind da detecção (`92d64260`).
- **Suíte.** Nove lotes depois de R1 verdes; depois de R2, oito lotes verdes antes de
  a execução ser parada por falta de memória na máquina, e o nono (`g-z`) rodado de
  novo depois do conserto de `locate.py`: 5439 passed. O único vermelho, nos lotes
  `a-c`, é `test_arvore_versionada::test_espelho_gerado_esta_em_dia_no_disco`, causado
  pelo `.claude/agents/README.md` não rastreado de propósito, fora desta feature.

## Revisão

Por tarefa: revisão de spec e depois de qualidade, cada uma por um subagente
novo. No fim, a revisão final do diff inteiro da feature.

- **T1.** Spec: conforme. Qualidade, primeira volta: dois importantes (guard de
  drift sem a matriz; teste por função privada) e um menor (fonte inline do
  `auto`); o achado de código sem consumidor foi aceito, porque T2 liga o loader.
  Segunda volta: nenhum achado.
- **T2.** Spec: conforme. Qualidade: um importante (teste chamava `_collect`),
  corrigido; um menor (`ROOT` sem uso) recusado, porque T3, T5, T8 e T10 o usam no
  mesmo arquivo. Conferidos na execução: rótulos da API com sufixo de ML, GPU e
  Photon dão o número certo; Glue e Databricks juntos disparam SF-ENV-005 sem
  SF-ENV-001 falso.
- **T4.** Spec e qualidade num subagente só, em sequência, por ser tarefa de um
  ramo: spec conforme; qualidade, um importante (ramo novo sem o porquê adjacente),
  corrigido no commit `d09b9ebe`.
- **T5.** Spec e qualidade em sequência: spec conforme; qualidade, um importante
  (citação errada no comentário do engine), corrigido. Conferidos: `_photon` com
  valores divergentes, fora do vocabulário ou vazios resolve para vazio; goldens de
  plano, SQL e do corpus principal sem mudança de veredito.
- **T9.** Spec e qualidade em sequência: spec conforme, cada função pública de
  `_core` seguida até o `build_runtime_context` sem nenhuma que aceite e descarte.
  Qualidade: dois menores. Corrigido o `--photon` inválido aceito em silêncio nos
  laços genéricos; aceito o `--photon` em verbos que não julgam, pela D6 (mesma lista
  do `--emr`).
- **T3.** Tarefa só de teste e fixture; revisão feita pelo controlador sobre o diff
  (`7cca69ac`): teste, meta e golden batem com o plano ajustado.
- **T6.** Tarefa de um ramo; revisão feita pelo controlador sobre o diff
  (`99ca17e5`): a recusa é o primeiro ramo da cadeia de shuffle, lê a procedência
  (código, Terraform ou efetivo) e cita a fonte. Os testes do tune e o golden de
  tuning passam (101).
- **T7.** Spec e qualidade em sequência: spec conforme (`parquet.yaml` e
  `glue-infra.yaml` intocados; goldens só com o texto trocado). Qualidade, dois
  menores aceitos sem conserto: a frase de SF-ENV-004 sobre Databricks não move a
  remediação, mas é verdadeira e diz ao usuário Databricks que a regra não dispara no
  runtime dele; falta `regen_timeout` em `scripts/regen_fixtures.py`, registrado como
  trabalho futuro.
- **T8.** Tarefa de fixture; revisão feita pelo controlador sobre o relato e o
  `diff` do event log (só as linhas 1 e 3 diferem do par Glue, e as seis SF-UI
  disparam iguais).
- **T10.** Tarefa de documentação; revisão feita pelo controlador sobre o relato e
  os gates (`check_status_numbers.py --strict` e `check_vnext_claims.py` sem
  divergência).
