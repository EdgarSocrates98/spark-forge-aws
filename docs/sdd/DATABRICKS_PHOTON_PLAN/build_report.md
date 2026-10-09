---
sdd: 1
feature: DATABRICKS_PHOTON_PLAN
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/DATABRICKS_PHOTON_PLAN/plan.md
  sha256: "ae03fe9050f0c4d1df8ea34eed6406707a3a96c035221b2ef85fb46386d405f3"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_plano_photon_gera_fact_de_photon -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_plano_photon_gera_fact_de_photon -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_fact_de_photon_recusa_regra_de_plano_sem_declaracao -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_fact_de_photon_recusa_regra_de_plano_sem_declaracao -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_photon_off_contra_plano_photon_diverge -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_photon_off_contra_plano_photon_diverge -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_capability_parity.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_capability_parity.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_arrow_eval_python_nao_afirma_pandas -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_arrow_eval_python_nao_afirma_pandas -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_knowledge_registra_o_extrator_sob_photon -q", exit: 1}
    green: {command: "python -m pytest tests/test_databricks_photon_plan.py::test_knowledge_registra_o_extrator_sob_photon -q", exit: 0}
claims:
  - text: "Um plano com operadores de prefixo Photon gera um fact plan.photon com a contagem de nos Photon, o total de nos, os nomes distintos ordenados e a primeira linha da secao == Photon Explanation ==."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_plano_photon_gera_fact_de_photon"
  - text: "A contagem vale tambem num plano so-arvore, sem os blocos de detalhe numerados, com cada no contado uma vez."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_plano_photon_so_arvore_conta_cada_no_uma_vez"
  - text: "Com plan.photon entre os facts, regra que exige kind de plano sai em skipped com databricks.photon.unresolved sem --photon e sem --databricks; sem o fact, a mesma regra dispara."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_fact_de_photon_recusa_regra_de_plano_sem_declaracao"
  - text: "Sob Photon, a regra de UDF (plan.python_udf) e a de AQE (plan.aqe) continuam julgadas."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_udf_sob_photon_continua_julgada"
  - text: "Plano sem operador Photon nao gera plan.photon, e o veredito (rule_id, severidade, subject) de todas as fixtures de plano ja existentes ficou identico ao golden."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_plano_sem_photon_nao_muda_veredito"
  - text: "--photon off diante de plano Photon, sob databricks, vira divergencia photon: e o estado fica on com fonte plan."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_photon_off_contra_plano_photon_diverge"
  - text: "Sob databricks, SF-ENV-006 nao dispara quando o plano ja mostra Photon, e continua disparando sem plano."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_plano_photon_cala_sf_env_006"
  - text: "Os ramos da observacao em _photon estao travados: plano sem databricks nao entra no contexto nem diverge; declaracao concordante nao diverge; declaracao sem databricks continua divergindo; databricks pelo event log mais plano da on com fonte plan."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_databricks_do_event_log_com_plano_photon_sem_flag"
  - text: "ArrowEvalPython sai com udf_type arrow, e SF-PLAN-002 continua disparando sem afirmar pandas_udf."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_arrow_eval_python_nao_afirma_pandas"
  - text: "O ramo pandas de SF-PLAN-002 continua coberto: um no MapInPandas dispara exatamente um SF-PLAN-002."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_sf_plan_002_ainda_casa_udf_pandas"
  - text: "A secao 4 de knowledge/databricks/runtime-matrix.md registra plan.photon, a recusa databricks.photon.unresolved e o udf_type arrow."
    evidence_ref: "tests/test_databricks_photon_plan.py::test_knowledge_registra_o_extrator_sob_photon"
  - text: "O eixo photon de RuntimeContext tem produtor (plan.photon em _runtime_reading) e saiu de AXES_DECLARED_ONLY; o teste de paridade deriva a chave crua de _photon."
    evidence_ref: "tests/test_capability_parity.py"
change_id: null
---

# DATABRICKS_PHOTON_PLAN — relatório do build

A tarefa TX (desvio aprovado) aparece no frontmatter como `T6`, porque o
schema só aceita ids `T<n>`. Build no perfil `dev`, na branch
`sdd/databricks-photon-plan`, a partir do plan
`81915b7e`. Um subagente implementador novo por tarefa (opus em T1 a T3 e TX;
sonnet em T4, T5 e nos consertos mecânicos), e para cada tarefa uma revisão de
spec e depois uma de qualidade, feitas por um subagente novo. A máquina tem
pouca memória: rodaram só testes nomeados, um comando por vez, e nenhum lote da
suíte.

## Commits

| commit | o que é |
|---|---|
| `685f56e0` | T1: `plan.photon` no extrator, fixtures `photon_join` e `photon_udf` |
| `160c890f` | conserto da revisão de T1: contagem no plano só-árvore |
| `8979fd73` | T2: recusa pelo fact no engine, `plan.aqe` isento |
| `c8c62e9b` | T3: o plano é observação e vence a declaração |
| `5e997c75` | conserto da revisão de T3: testes dos ramos de `_photon` |
| `929be198` | TX: textos públicos e trava de paridade |
| `14083311` | conserto da revisão de TX |
| `abf2e448` | T4: `ArrowEvalPython` com `udf_type: arrow`, SF-PLAN-002 pandas ou arrow |
| `3036ff29` | conserto da revisão de T4: cobertura do ramo pandas de SF-PLAN-002 |
| `6bcf4593` | T5: knowledge §4, mais §3 U2 e `plan-reading.md` |
| `788d1cb3` | conserto da revisão de T5 |
| `45022495` | conserto da revisão final: números do STATUS/README, textos, provas de AC4 e AC8 |

## Red e green por tarefa (relatados pelos implementadores)

- **T1.** A trava do AC3 (`test_plano_sem_photon_nao_muda_veredito`) passou
  antes do código, como o plano previa. O vermelho foi `assert 0 == 1`, sem
  nenhum `plan.photon`. Gates vizinhos: 889 passed.
- **T2.** O vermelho foi `AssertionError: 'SF-PLAN-003' not in
  {'SF-PLAN-003', 'SF-PLAN-004'}`. `test_udf_sob_photon_continua_julgada`
  passou antes do código, como o plano previa, e depois do código passou a
  travar a isenção de `plan.aqe`. Gates: 126 passed.
- **T3.** O vermelho foi `assert 'off' == 'on'`. `test_plano_photon_cala_sf_env_006`
  também falhou antes do código (`'SF-ENV-006' not in {'SF-ENV-006'}`). Gates:
  145, 199 e 13 passed.
- **TX.** O vermelho foi a trava de paridade depois que `photon` saiu de
  `AXES_DECLARED_ONLY` e antes de o teste aprender a derivação: exit 1, "eixo
  de RuntimeContext sem produtor em _runtime_reading: ['photon']". Depois,
  44 passed. As outras partes são texto e não têm vermelho próprio; o gate
  delas foram os goldens, os locks e a referência gerada.
- **T4.** O vermelho foi `assert ['pandas'] == ['arrow']`. Bloco de regra:
  891 + 253 + 698 passed.
- **T5.** O vermelho foi `assert 'plan.photon' in secao`. Offline, surface e
  drift ficaram verdes (4, 6 e 733 passed).
- **Consertos de revisão.** Travam comportamento que já existia, então o
  vermelho de cada um foi uma mutação temporária, desfeita em seguida:
  - `160c890f`: `_PHOTON_PREFIX` trocado por `"PhotonX"`, `assert 0 == 1`.
  - `5e997c75`: a observação ignorada em `_photon`, 4 failed.
  - `3036ff29`: o ramo pandas apagado do `any` de SF-PLAN-002, `assert 0 == 1`.

  - `45022495`: `_photon_recusa` forçado a `False` e a frase "Lacuna do
    SparkForge" reposta na §4 derrubaram 3 testes, entre eles os de AC4 e AC8.

  `14083311` e `788d1cb3` são só texto, sem vermelho.

## Goldens que mudaram

- Novos: `fixtures/plan/photon_join` (SF-PLAN-004) e `fixtures/plan/photon_udf`
  (SF-PLAN-002).
- `fixtures/plan/python_udf_in_plan` e `photon_udf` (T4): mudaram só o
  `udf_type` do nó `ArrowEvalPython` e o texto de SF-PLAN-002. rule_id,
  severidade e subject ficaram iguais.
- `fixtures/runtime/databricks_divergent_spark`,
  `databricks_event_log_runtime` e `databricks_flag_runtime` (TX): mudou só o
  texto de SF-ENV-006 (`explanation` e `proposed_change[1]`).
- Nenhuma fixture de plano sem Photon mudou de veredito (SC1 = 0).

## Desvios do plano

- **TX, tarefa nova.** A revisão de T2 achou que os textos públicos ficaram
  falsos. Eles diziam que Photon é só declaração e que só `plan.python_udf`
  escapa da recusa. Nenhuma tarefa os cobria, e a TX foi aprovada pelo
  coordenador. Pontos corrigidos:
  - `_PHOTON_FLAG_HELP`;
  - `_PHOTON_INPUT`;
  - a descrição de `photon` na saída do runtime;
  - a descrição do motivo de pulo em `_JUDGE_SKIPPED_ITEM`, sem mexer nos
    valores do enum;
  - o comentário de `RuntimeContext.photon`;
  - SF-ENV-006 (`explanation` e `proposed_change[1]`), sem mudar `when`,
    severidade, `runtime_scope` nem `action`;
  - os comentários do engine;
  - o `README.md`, corrigido no conserto `14083311`.

  A TX também tirou `photon` de `AXES_DECLARED_ONLY`, que ficou vazio. O teste
  passou a derivar a chave crua de `runtime_detect._photon`. Registros que ela
  moveu:
  - 17 páginas de referência gerada;
  - `docs/surface.lock.json`: +1620 bytes, e mais +1116 no conserto;
  - no `tests/test_fixtures_golden_mcp_parity.py`, só o texto do motivo que já
    estava declarado.
- **T3, passo 4.** `test_declared_only_axes_are_real_axes_without_producer`
  não falhou, porque não conseguia reprovar `photon`: a derivação do teste só
  lia `_PLATFORM_KEYS` e `_DIRECT_KEYS`. O ajuste que o plano condicionava a
  essa falha foi para a TX, que ensinou o teste a derivar a chave.
- **T3, `_photon_declarado` removida.** Tinha um chamador só, e o caso dela
  entrou em `_photon(sources, databricks)`, que passou a devolver valor,
  fonte e divergência numa única leitura. O plano pedia isso, "sem duplicar a
  leitura das fontes".
- **T4, literal fora da lista.**
  `tests/test_fixtures_golden_plan.py::TestAdversarial::test_python_udf_nodes_keep_their_flavor`
  fixava `{"ArrowEvalPython": "pandas"}` e passou a `"arrow"`. É consequência
  direta de D4, com o mesmo veredito.
- **T5, escopo acrescentado.** Dois textos de knowledge ficaram falsos depois
  de T3 e T4, e nenhuma tarefa os cobria:
  - `knowledge/databricks/runtime-matrix.md` §3 U2 ("Photon é declarado, não
    detectado");
  - `knowledge/spark/plan-reading.md` ("`ArrowEvalPython` é `pandas_udf`").

  No conserto `788d1cb3` entrou também `knowledge/INDEX.md`. Os três estão no
  `offline-manifest` e no `surface.lock`, com o knowledge em +941 e +1362 bytes.
- **Gate de lastro, remediado por id.** A contagem de linhas dos documentos
  auditados ficou preservada em todos os casos:
  - T1: VNX-640.
  - T3: VNX-653, 658, 666, 674, 741 e 322.
  - `5e997c75`: VNX-674.
  - TX: VNX-663, 666, 741, 674, 431, 324 e 327.
  - `14083311`: VNX-663, 666, 741, 674 e 431.

  T2, T4, T5 e os consertos `3036ff29`, `788d1cb3` e `45022495` saíram com 0
  divergências.
- **Atribuição.** Os commits `160c890f` e `14083311` saíram com
  `Co-Authored-By: Claude Sonnet 5` em vez da linha pedida. Os subagentes
  seguiram o aviso de atribuição da própria sessão. Não houve amend, por regra.
- **Arquivos vazios espúrios na raiz** (`Spark`, `por`, `dict[str`), criados
  por comandos de shell intermediários: apagados antes de cada commit. O
  `tuple[dict[str` na raiz é rastreado desde `749d44b9` (PR #67), é anterior a
  esta feature e ficou intocado.

## Limitações conhecidas

Registradas pelas revisões e aceitas neste build. Corrigi-las mudaria
comportamento além do design, ou fica para depois.

- A linha `== Photon Explanation ==` conta em
  `plan.analyzed.measures.skipped_logical_lines` (1 em cada fixture Photon).
  Num plano só-árvore com essa seção, ela ainda troca `plan.analyzed.attrs.mode`
  para `extended`. Nenhuma regra lê essas medidas hoje.
- O subject de `plan.photon` depende do modo do explain: no formatado é o
  bloco (1), a folha; no só-árvore é a raiz.
- A fonte `plan` não entra em `RuntimeContext.detected_from`. A procedência
  fica em `databricks.photon.attrs.source` e no texto da divergência.
- Um plano com a seção de explicação e nenhum nó Photon não emite
  `plan.photon`, e a frase se perde (ligado ao U2).
- A recusa pelo fact vale por case. Um plano Photon em qualquer ponto da união
  recusa também regras de outro plano ou de `spark.sql.*`. Hoje nenhuma regra
  exige `spark.sql.*`, e o comentário do engine o diz.
- `AXES_DECLARED_ONLY` está vazio. O teste que o percorre fica sem casos, mas
  o mecanismo continua mordendo se alguém reinserir um eixo com produtor.
- SF-ENV-006: `risks` e `proposed_change[0]` estão incompletos, não falsos. A
  coleta do plano virou uma alternativa à declaração.
- Pendências de texto para o ship ou uma frente própria:
  - A skill `analyze-spark-plan` e os espelhos rotulam `ArrowEvalPython` como
    "(UDF vetorizada)" e não listam `plan.photon`. Editá-los passa pela
    sincronização de espelhos, que apaga `.claude/agents/README.md`.
  - `docs/superpowers/STATUS.md` guarda o texto antigo de SF-ENV-006.
  - `.venv/Lib/site-packages` tem uma cópia velha do catálogo.
- O teste de AC3 (`test_plano_sem_photon_nao_muda_veredito`) compara o
  veredito atual com o golden versionado, que a própria feature poderia
  regenerar. O "antes igual ao depois" da D5 foi conferido pelo diff dos
  goldens (em `fixtures/plan` só `python_udf_in_plan` mudou, e só no texto e no
  `udf_type`) e pelo literal de veredito em `TestAdversarial`
  (`{"SF-PLAN-001": "P1", "SF-PLAN-002": "P3"}`). Uma regeneração futura que
  mude um veredito passaria nesse teste.
- `docs/gates-por-mudanca.md` não cita `check_status_numbers.py` nas seções de
  extrator e de corpus de fixture, e por isso a contagem de kinds e fixtures só
  foi pega pela revisão final. Fica como sugestão para o ship.
- U1 e U2 do define continuam abertos. A forma observada vem de um ambiente
  só: Free Edition, serverless, Spark 4.2.0, 2026-09-18. O texto de suporte
  parcial da explicação não foi visto.

## Revisão

- **Por tarefa.** A spec deu conforme em T1, T2, T3, TX e T4. Em T5 não deu:
  três frases do knowledge não diziam o que o código faz (lacunas "corrigidas"
  em excesso, "desde esta feature", caso sem databricks). O conserto foi o
  `788d1cb3`. Achados importantes e o que foi feito com cada um:
  - T1: contagem só-árvore sem teste → `160c890f`.
  - T2: textos públicos falsos → TX.
  - T3: ramos de `_photon` sem teste → `5e997c75`.
  - TX: descrição de `runtime.photon` sem o caso sem databricks, e o README →
    `14083311`.
  - T4: ramo pandas de SF-PLAN-002 sem cobertura → `3036ff29`.
  - T5: `knowledge/INDEX.md` → `788d1cb3`.

  Os menores ficaram na seção de limitações ou foram consertados junto.
- **Final.** Um revisor novo leu o diff `81915b7e..788d1cb3` contra o define e
  o design. Não achou nada crítico.
  - Importante: `scripts/check_status_numbers.py --strict`, que o CI roda, tinha
    4 divergências. Eram a contagem de fact kinds (227 → 228) e de fixtures
    golden (514 → 516) em `docs/superpowers/STATUS.md` e em duas linhas do
    `README.md`.
  - Menores:
    - o teste de AC4 não chamava `judge`;
    - o de AC8 não conferia que a lacuna saiu;
    - a U2 do knowledge atribuía o fact também à seção de explicação;
    - o README omitia a condição de databricks no "estado fica `on`";
    - o `proves` de `photon_udf` dizia "UDF vetorizada";
    - o teste de AC3 não segura o "antes" (acima, em limitações).

  Todos, menos o do AC3, foram consertados em `45022495`. Um revisor novo
  reconferiu esse commit e deu conforme: `check_status_numbers --strict` com
  0 divergências e 14 testes passando.
- **Por AC**, segundo a revisão final:
  - AC1, AC2, AC5, AC6 e AC7: entregues e provados.
  - AC4 e AC8: entregues e provados depois de `45022495`.
  - AC3: entregue, com a prova do "antes" pelo diff dos goldens.

## Verificação antes de fechar

Rodado de novo pelo controlador, depois do último commit, um comando por vez:

- `python -m pytest tests/test_databricks_photon_plan.py -q`: 14 passed. São
  os `verified_by` de AC1 a AC8.
- `python -m pytest tests/test_capability_parity.py tests/test_fixtures_golden_plan.py -q`:
  112 passed.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.

A suíte inteira não rodou: a máquina tem pouca memória, e o operador vetou os
lotes neste build.
