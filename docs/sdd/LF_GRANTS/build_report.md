---
sdd: 1
feature: LF_GRANTS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/LF_GRANTS/plan.md
  sha256: "587313d9f9aadc966bb1f9a8247289a42330ccd7566c460e279e502e8d0c81fd"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_lakeformation_missing_grant.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_lakeformation_missing_grant.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_lakeformation_missing_grant.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_lakeformation_missing_grant.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_lakeformation_missing_grant.py::test_fgac_escrita_cobra_iam_com_denied_by tests/test_lakeformation_missing_grant.py::test_fgac_escrita_registrada_e_conflito_declarado tests/test_lakeformation_missing_grant.py::test_modelo_ou_runtime_desconhecido_recusa_por_nome tests/test_lakeformation_missing_grant.py::test_fgac_escrita_em_runtime_sem_suporte_nao_e_permissao -q", exit: 1}
    green: {command: "python -m pytest tests/test_lakeformation_missing_grant.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_lakeformation_missing_grant.py::test_fuse_deriva_missing_grant -q", exit: 1}
    green: {command: "python -m pytest tests/test_lakeformation_missing_grant.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_lakeformation_rules.py::test_sf_lf_011_dispara_so_com_permissao_nomeada tests/test_lakeformation_missing_grant.py::test_evidence_de_err_lf_001_e_emitida tests/test_lakeformation_missing_grant.py::test_fontes_da_tabela_estao_no_lock -q", exit: 1}
    green: {command: "python -m pytest tests/test_lakeformation_rules.py tests/test_lakeformation_missing_grant.py tests/test_docs_coverage.py -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py::test_all_required_fixtures_exist -q", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py -q", exit: 0}
  - id: T7
    status: done
    red: {command: "python -m pytest tests/test_lakeformation_access_graph.py::test_grafo_usa_missing_grant_quando_existe -q", exit: 1}
    green: {command: "python -m pytest tests/test_lakeformation_access_graph.py tests/test_lakeformation_engine.py -q", exit: 0}
claims: []
change_id: null
---

# LF_GRANTS — relatório do build

## Desvios do plano

- **Os subagentes leram o texto da tarefa num arquivo, em vez de recebê-lo colado no
  pedido.** Cada tarefa foi copiada literalmente do plano para `scratchpad/T<n>.md`, e o
  subagente leu só esse arquivo, sem o resto do plano. O conteúdo é o mesmo que seria
  colado; o que mudou foi apenas o meio.
- **T1, achado menor da revisão de qualidade, corrigido em `0bcc7d18`.** A citação de
  escrita sob FGAC estava cortada no meio da frase. Ela passou a trazer a frase inteira, e a
  primeira oração ("uses IAM permission rather than Lake Formation granted permissions") é
  justamente a que sustenta `side: iam`.
- **T2, registros fora do manifesto.** Os mesmos números aparecem em outros arquivos além
  dos que o design listava, e os dois gates de números cobraram os dois lados:
  - extratores (41→42) e kinds (243→245) em `README.md` e em
    `docs/guia/06-extrair-julgar-compor.md`;
  - o corpus `.py` (778→780 arquivos, 243041→245145 bytes) em
    `docs/harness/CODEINTEL-GAP.md`, que corresponde a `VNX-640` e `VNX-674` em
    `docs/claims.lock.json`.

  O controlador autorizou a edição só desses números. O manifesto do design não previa
  nenhum dos três arquivos.
- **T2, `claims.lock.json` editado à mão, não com a saída do `--seed`.** O `--seed` criou
  dois ids `SEM_LASTRO` novos em vez de atualizar `VNX-640` e `VNX-674`, e reescreveu cerca
  de 250 entradas sem relação com a tarefa. O arquivo foi restaurado do HEAD, e só as duas
  entradas foram editadas. O gate saiu com exit 0.
- **T2, formatação exigida pelo `ruff` do CI.** Linhas com mais de 100 caracteres foram
  quebradas, e a variável `l` virou `linha` no teste da T1. O comportamento não mudou.
- **Os nomes dos atributos do fact não são os do define.** O AC1 fala em `required=ALL`, e
  o design (D7 e D8) fala em `permission`. O fact emite duas listas, `requires` e `missing`,
  porque uma operação pode exigir mais de uma permissão ou ação (overwrite sob FGAC exige
  `s3:PutObject` e `s3:DeleteObject`). A T5 (texto da regra) e a T7 (grafo) já leem
  `missing`.
- **T2, revisão de qualidade: seis achados importantes, que vieram do próprio plano.** Foram
  corrigidos em `26fe30b4`, com teste vermelho antes do conserto (10 falharam, depois 23
  passaram). O primeiro subagente de correção morreu no limite semanal sem tocar a árvore, e
  uma versão anterior deste relatório dava a correção como feita antes de ela existir. O
  pedido foi recuperado do transcript e despachado de novo:
  1. nome curto do recurso na mensagem;
  2. tabelas homônimas em databases diferentes;
  3. operação sem alvo que sumia em silêncio;
  4. `principal` escolhido errado quando há mais de um role;
  5. regex que capturava `s3` ou `arn` como nome de tabela;
  6. modo de escrita sem distinção de maiúscula e minúscula, e `writeTo` sem terminal
     medido.

  Os menores entraram junto: ordenação dos gatilhos, `catalog_id` ambíguo, testes das
  recusas que não tinham teste, e estilo.
- **T2, segunda revisão de qualidade (sobre `26fe30b4`): um crítico, quatro importantes.**
  Corrigidos em `cc276a9c`, com teste vermelho antes (11 falharam, depois 34 passaram):
  1. crítico: cláusula `on <recurso>` que o regex não lia (vírgula, aspas,
     `Required Select on`) caía no candidato único e acusava a tabela errada; agora lê essas
     formas, recusa o resto como `recurso_nao_lido`, e `s3a://`/`s3n://` saem
     `recurso_nao_e_tabela`;
  2. `principal_ambiguo` e `recurso_ambiguo` tinham texto falso em parte dos cenários; zero
     candidatos virou `principal_nao_coletado` e `recurso_nao_nomeado`;
  3. escrita com `api == "ambigua"` sem modo virava `write`; agora
     `terminal_de_escrita_nao_medido`, com `operation: write` e `writer_api`;
  4. operação sem alvo sozinha era presumida sobre o recurso; agora nunca é presumida
     (nenhum AC nem golden dependia do presumido).

  Os menores: texto de `operacao_com_alvo_nao_resolvido`, `catalog_id` vazio ao lado de um
  preenchido, comparação sem caixa. O coletor sempre qualifica o symbol
  (`sparkforge/facts/lakeformation_grants.py:78`), então tabela sem ponto no pool não
  precisou de tratamento.
- **T2, regex quadrática (`b00c0c8d`).** A busca da cláusula `on` introduzida em
  `cc276a9c` (`permission\(s\).*?\bon\b`) recomeçava em cada "permission(s)" do texto do
  artefato: 20 mil repetições levavam cerca de 60 s. Virou busca em dois passos lineares,
  com `test_linha_hostil_com_prefixo_repetido_nao_trava` visto vermelho (59 s) antes.
  Achado na revisão manual de segurança, porque o scan do Snyk não rodou (MCP sem
  autenticação).
- **T2, terceira revisão de qualidade (sobre `cc276a9c`): um crítico, dois importantes.**
  Corrigidos em `23edef40`, com teste vermelho antes (8 falharam, depois 43 passaram):
  1. crítico: o matcher guarda só 200 caracteres da mensagem
     (`sparkforge/errors/matcher.py:307`, `sparkforge/facts/exception.py:124`); quando o
     corte comia a cláusula ou o nome, o candidato único acusava a tabela errada. Agora sai
     `trecho_truncado`, com o teto medido por porta e um teste de guarda pelo caminho real;
  2. recusa de modelo calada pela de alvo sem resolução: agora as duas saem;
  3. duas partes da correção anterior sem teste que as matasse: mutação à mão confirmou
     que os testes novos falham com elas.

  Os menores: a forma `": Required X on"` saiu (o matcher nunca a gera, e ela lia database
  como tabela); cauda `)}'"` no nome; texto de `recurso_ambiguo`; recusas `recurso_nao_lido`
  distintas por trecho; `_recurso(gatilho, lista)` extraída. Dois testes criados em
  `cc276a9c` mudaram de caso por isso: " on staging.outra)" passou a ser lido, e
  ": Required Select on" saiu do teste de leitura.
- **T2, quarta revisão de qualidade (sobre `23edef40`): nenhum crítico, dois
  importantes.** Corrigidos pelo controlador em `0f9a3237`, com teste vermelho antes (3
  falharam, depois 48 passaram):
  1. corte logo depois de `on` pela cabeça da exceção: o `strip` do matcher tira o espaço
     e o trecho fica com 199 caracteres, abaixo do teto, e saía `recurso_nao_lido` com
     texto falso. `on` sem nome no fim do texto é corte em qualquer tamanho, porque a
     assinatura só casa com `permission(s) on` na mensagem inteira;
  2. a metade "e só então" da regra de corte e o teto medido por porta não tinham teste
     que os travasse. Dois testes novos, e cada um cai sob o mutante que remove o que ele
     guarda (conferido à mão, e os mutantes revertidos).

  Os menores: com dois "permission(s)" no texto, a cláusula que `_RECURSO_RE` lê decide se
  o nome encosta no corte; `trecho_truncado` leva a cláusula, e não o texto inteiro, e as
  duas portas do mesmo corte dão uma recusa só. Fica aceito: nome inteiro que termina
  exatamente no caractere 200 sai `trecho_truncado`, porque é indistinguível de um corte
  sem o tamanho original, que o matcher não grava; a recusa diz isso.
- **T2 fechada depois de quatro passes de qualidade.** O plano previa o extrator em um
  commit; saíram seis (`6b5687f9`, `26fe30b4`, `cc276a9c`, `b00c0c8d`, `23edef40`,
  `0f9a3237`). Os achados vieram quase todos da mesma fonte: o texto do gatilho é um
  trecho de 200 caracteres de uma mensagem que o extrator não controla, e o design (D5)
  tratou a leitura do recurso como um regex só.
- **T3, decisões do operador (2026-09-25), fora do plano.** Duas lacunas que a T3
  expôs foram levadas ao operador:
  1. *Overwrite presumido como write:* o operador escolheu ampliar
     `sparkforge/facts/pyspark_ast.py` (fora do manifesto do design) para gravar modo não
     literal como desconhecido e `insertInto(overwrite=True)` como overwrite. Entra como
     tarefa extra depois da correção da T3;
  2. *Registro não coletado sob FGAC:* sem `lakeformation.registered_location`, o fact
     recusa `registro_nao_coletado` em vez de presumir "não registrada". Os cenários de AC4
     ganham `_registrada(False)` explícito.
- **T3, revisão de spec: não conforme.** Colisão de id entre decisões negadas da mesma
  ação em recursos diferentes (dependia da ordem do pool); decisão de IAM de outro bucket
  acusava a tabela; ramos de runtime sem teste; texto de `not_applicable`; um teste com
  nome que prometia outra coisa; `_lado_lf` casando registro por igualdade exata.
  Corrigidos em `c1a04672` junto com `registro_nao_coletado`, com teste vermelho antes (8
  falharam, depois 66 passaram; os três testes dos ramos de runtime passaram de primeira,
  porque são guarda de ramo que já funcionava). Decisões do implementador:
  - a localização da tabela é o `resource_arn` do `lakeformation.registered_location`; a
    decisão de IAM pertence à tabela quando o recurso é `*`, um prefixo que contém a
    localização, ou um objeto dentro dela. Sem localização e com mais de um recurso
    simulado, sai `recurso_iam_nao_ligado_a_tabela`;
  - Glue 4.0 (`not_applicable`) ganhou razão própria,
    `fgac_spark_native_inexistente_no_runtime`, fiel à célula da matriz; o 5.0 continua
    `escrita_fgac_nao_suportada_no_runtime`.
- **T3, revisão de qualidade (sobre `c1a04672`): dois críticos, três importantes.** A
  simulação do IAM (`SimulatePrincipalPolicy`) avalia cada par ação e recurso ao pé da
  letra, e a primeira versão lia `implicitDeny` em `*`, no bucket ou num prefixo mais largo
  como evidência sobre a tabela. Uma policy escopada à tabela também nega nesses recursos,
  então o fact acusava em falso; os testes usavam `*` e esconderam isso. Corrigidos em
  `e67ecb54` (14 falharam, depois 82 passaram):
  - `implicitDeny` acusa só em `<localização>/*`; `explicitDeny` acusa em qualquer recurso
    que contém a tabela e vence `allowed`; `allowed` cobre só em `<localização>/*`;
  - o texto de destrava manda simular `--resource-arn <localização>/*`;
  - decisão malformada e decisão de nome desconhecido ganharam recusa própria;
  - `_lado_iam` virou `_gate_escrita_fgac`, `_decisoes_da_tabela` e `_falta_iam`;
  - a acusação do lado IAM carrega `registration_scope: exact_arn` e uma ressalva: o
    registro é conferido no ARN exato, e um registro no prefixo pai não foi olhado.

  Três testes que usavam decisão em `*` passaram a usar `<localização>/*`, sem mudar o
  que afirmam. Um teste inverteu a afirmação por decisão da regra nova:
  `implicitDeny` num objeto dentro da localização não fala pela tabela. Pelo controlador,
  em `d30cbcd1`: `implicitDeny` e `allowed` no mesmo `<localização>/*`, vindos de dois
  artefatos, recusam `decisoes_iam_contraditorias`; e a ressalva diz também que a
  localização é o `--resource-arn` passado ao collect, e que, se ela for mais larga que a
  tabela, uma policy escopada à tabela nega em `<localização>/*` do mesmo jeito. Esse
  último caso é limite aceito: sem a localização da própria tabela
  (`StorageDescriptor.Location`), o fact não distingue.
- **Tarefa extra (decisão do operador): o modo de escrita no `pyspark_ast`, `21966c09`.**
  `sparkforge/facts/pyspark_ast.py` passou a gravar `mode` a partir de `mode=` no terminal
  (e da posição dele) e de `insertInto(t, overwrite=<literal>)`, e marca
  `mode_unresolved: true` quando o modo não é literal. `lakeformation_missing_grant` recusa
  essa escrita como `modo_de_escrita_nao_lido`, em vez de presumir `write` e calar o
  `s3:DeleteObject` do overwrite sob FGAC. Teste vermelho antes (11 falharam no extrator e
  2 no consumo). Os 57 goldens passaram sem regenerar. A única regra que lê `mode`,
  `SF-GLUE-004`, passa a disparar também em `insertInto(overwrite=False)` e em
  `mode="append"`, o que é correção. O gate de lastro moveu quatro alegações de tamanho do
  corpus (`VNX-643`, `VNX-666`, `VNX-674`, `VNX-741`), atualizadas à mão com nota.
- **Tarefa extra, revisão: nenhum crítico, dois importantes.** As posições de `mode` batem
  com o `DataFrameWriter` do PySpark 3.x. Importantes: a recusa `modo_de_escrita_nao_lido`
  calava um grant que falta em qualquer modo (a exigência de write está contida na de
  overwrite), e `.mode(saveMode=...)` passava calado. Corrigidos em `2c05ac47`, com teste
  vermelho antes (7 falharam, depois 135 passaram, goldens intactos): a escrita de modo
  não lido é avaliada como write e acusa o que falta nela; a recusa só sai quando o
  overwrite pede mais que o write, pela diferença dos `requires` da tabela
  (`overwrite_only`); `saveMode=` é lido; e vale o último `.mode()` da cadeia, como no
  Spark. Declarado e fora do escopo desta feature:
  - `df.write.mode("append").save(p, **opts)` passou a sair `mode_unresolved`, porque
    `**opts` pode trazer o modo, e `SF-GLUE-004` deixa de disparar nesse padrão;
  - `SF-GLUE-004` casa `append` só em minúscula, e o Spark aceita o modo sem distinguir
    caixa (anterior a esta feature);
  - `format` posicional ainda vaza para `target` em `save(caminho, "parquet", ...)`
    (anterior a esta feature);
  - no Spark 2.x (Glue 2.0), `insertInto` sempre fazia append, e o fact segue o 3.x.
- **T4, `8b9e6bdc`.** `fuse()` chama `build_missing_grant` depois de
  `build_lakeformation`, guardado por `SOURCE_KINDS` (`error.signature_match`), e o
  simulate tira o kind novo. Revisão do controlador sobre o diff: conforme. O caminho de
  produção é `analyze error-signatures --out`, que grava o gatilho, seguido de `fuse --facts`
  com os dois arquivos; o gatilho entra na união e a guarda deixa passar. Nenhum golden
  mudou. `test_rules_catalog_reachability` não acusou o kind novo como órfão, então não
  houve o vermelho que o plano previa. Para a T6: o `_derive` do golden de CloudWatch e o
  `regen_cloudwatch_logs` chamam `build_lakeformation` e `build_signature_matches` direto,
  sem `fuse`, e precisam chamar `build_missing_grant` depois do matcher.
- **T5, `e8a54809`.** `SF-LF-011` entrou, `ERR-LF-001` passou a exigir só
  `lakeformation.missing_grant` e declara `ram.unaccepted_share` em
  `evidence_out_of_reach`. Contagens medidas: 169 regras, 11 SF-LF, 268 fontes. Desvios: o
  texto da regra foi ajustado ao que o fact faz depois das revisões (razões de recusa
  verdadeiras, a regra de decisão do lado IAM, `caveat` e `mode_unresolved`), e sete
  goldens foram regenerados por contagem de cobertura e texto de `SF-ERR-006`, sem finding
  novo ou sumido. `test_fixtures_kind_coverage` ficou vermelho em dois testes até a T6:
  `SF-LF-011` sem fixture que a faça disparar, e o ramo P1 sem golden. A varredura dos
  goldens morreu por memória na segunda metade; o controlador a refez um arquivo por vez,
  e os 31 restantes passaram.
- **T5, revisão: conforme no texto da regra, um importante.** O agente
  `sf-lake-formation-specialist` e a skill `diagnose-lakeformation-access` não listavam
  `SF-LF-011`, e nenhuma tarefa do plano previa isso. Menores: o explanation de
  `SF-ERR-006` (frase ditada pelo plano) ficou falso sobre `evidence_required` e sobre o
  lado IAM; o primeiro parágrafo de `SF-LF-011` dizia que o lado IAM lê o grant; a
  validação não pedia `--action`; comentários velhos em `tests/test_rules_errors.py`.
  Aberto para o ship: o `verified_by` de AC10 não mede "com fonte T1 no lock"; quem mede é
  `test_fontes_da_tabela_estao_no_lock`, que o define não cita.
- **T5, correção da revisão, `d2645cdb`.** Agente e skill listam `SF-LF-011`, espelhos
  sincronizados e referência regenerada; texto de `SF-ERR-006` e o primeiro parágrafo de
  `SF-LF-011` fiéis aos dois lados; validação com `--action`. A partir daqui, por pedido do
  operador, cada tarefa roda só o próprio teste e `ruff`; goldens e gates de número rodam
  uma vez depois da T7.
- **T6, `5b03fe76`.** Positiva `lf_negado_fta_append_sem_all` (`missing: [ALL]`,
  `side: lf`, `SF-LF-011`) e negativa `lf_negado_fta_grant_all` (sem `missing_grant` e sem
  recusa). As três fixtures antigas com `ERR-LF-001` ganharam só
  `lakeformation.missing_grant.unresolved` com `operacao_nao_medida`, texto verdadeiro para
  log sem código; os findings delas não mudaram. `test_fixtures_kind_coverage` fechou.
  **Achado fora do escopo:** `SF-LF-010` dispara nas duas fixtures novas dizendo que o job
  "não declara nem FGAC nem Full Table Access", e o job declara FTA. A regra pede
  `absent: lakeformation.access_model`, e um job só de FTA não produz esse kind (a
  superfície dele é `lakeformation.filesystem`). É anterior a esta feature; ficou fixado
  no golden com uma linha no `proves:` que nomeia a lacuna. Corrigir exige um predicado
  derivado (o `absent` do motor só confere kind, regra 33), e fica como frente própria.
- **T7, `277e58f4`, pelo controlador.** A perna `lf_grant` do grafo lê
  `lakeformation.missing_grant` (`side: lf`, mesmo recurso e principal) e nomeia a operação
  e a permissão que faltou, no lugar do SELECT fixo. Sem o fact, a perna não muda (AC15,
  guarda). Desvio: a comparação do recurso ignora caixa, e um teste a mais prova que falta
  do lado IAM ou de outro principal não muda a perna.
- **Verificação final (2026-09-25).** A suíte rodou em lotes, um subprocesso por lote e um
  por arquivo de golden. Das 64 unidades, 55 passaram de primeira. Vermelhos:
  - **causados pela feature**, fechados em `7594ace0`: a auditoria de termos AWS acusou
    `SF-LF-011`, e o extrator entrou na lista `SO_AWS` do teste (o fact só nasce de
    artefatos de AWS, como `utilization` e `sfn_history`), sem mexer na regra; a contagem
    de governança foi de 10 para 11 SF-LF; `SF-GLUE-004` saiu da dívida de mutação, porque
    as fixtures novas (`max_retries = 0`, `append`) percebem a fronteira; `STATUS.md`
    (achados sem pergunta de ouro 31 para 34, goldens 555 para 557); lock de superfície
    (skills +1608 bytes, knowledge +85); `VNX-640`, `VNX-674` e `VNX-726` relidas à mão;
  - **do ambiente, não da feature**: o SDK `mcp` instalado é 1.30, sem `mcp.Client` nem
    `mcp.server.caching`, e isso derruba `test_adapters_mcp.py` (coleta),
    `test_doctor.py` (4) e `test_run_debate.py` (2). Nenhum arquivo por trás deles mudou
    na branch;
  - **do script de lotes do controlador**: `test_fixtures_golden_change.py` (4) e
    `test_fixtures_golden_receipt.py` (7) falharam com `FileNotFound` porque o
    `--basetemp` tinha `/` no nome; rodados sozinhos, 33 passaram e 4 foram pulados.
- **Limitação que passa para a T3.** Resolvida pela tarefa extra acima: `sparkforge/facts/pyspark_ast.py` não grava `mode`
  em `.mode(variavel)` nem em `insertInto(t, overwrite=True)`, e o fact presume `write`.
  Sob FTA não muda nada (write e overwrite exigem ALL); sob FGAC, overwrite exige
  `s3:DeleteObject` a mais. Mexer no extrator de AST está fora do manifesto desta feature.

## Revisão

Cada tarefa passou por revisão de spec e de qualidade, com as rodadas registradas acima
por tarefa. A revisão final leu o diff inteiro (`da3171bb..7594ace0`) contra o define e
o design: nenhum crítico, três importantes.

1. **Este relatório estava incompleto** (T7 e a tarefa extra fora do frontmatter, desvios
   da verificação final ausentes): corrigido nesta versão. A tarefa extra do
   `pyspark_ast` não está em `tasks:` porque não é tarefa do plano; ela mora no corpo, em
   "Tarefa extra".
2. **O guia de usuário de Lake Formation** (`docs/guia/usos/lake-formation-e-acesso.md`)
   não conhece o fact, a regra nem a aresta nova do grafo: fica para a etapa de docs em
   pt-br e en-us que o operador pediu para depois da T7, antes do ship.
3. **A tabela de permissões** tinha linhas FGAC cujo `quote` não nomeava a ação exigida,
   e a divisão write/overwrite (DeleteObject só no overwrite, sem KMS) não tinha fonte.
   Corrigido em `bad38e3d`: a fonte passou a ser
   `glue/latest/dg/getting-started-min-privs-job.html` ("Data targets require
   s3:ListBucket, s3:PutObject, and s3:DeleteObject permissions."), que não separa append
   de overwrite, e por isso as duas escritas sob FGAC exigem PutObject e DeleteObject.
   ListBucket (ação de bucket, que a simulação em `<localização>/*` não responde) e KMS
   saem em `unchecked`, declarados na acusação, sem ação inventada. A frase das
   considerações de FGAC ficou como `side_quote`, a razão de o lado ser IAM. O ramo
   `modo_de_escrita_nao_lido` ficou inalcançável com a tabela atual e continua coberto
   por teste com a tabela trocada.

Menores, corrigidos no mesmo commit: casamento de nome de tabela duplicado entre o grafo e o
extrator; `docs/simulate.md` sem o módulo novo; texto da skill que dizia "ou" onde o
fact exige "e", e o exemplo sem o comando que grava `facts_code.json`; `Fact` mutado
depois de construído; `principal_nao_coletado` no lado IAM sem decisão; índice de
conhecimento e `parity.yaml` sem a tabela nova. Registrados e aceitos, sem mudança:

- o D2 do design prometia `alter` e `DATA_LOCATION_ACCESS` condicional no create; a
  tabela não tem as duas linhas. É inerte hoje: o extrator de SQL não produz `alter`, e o
  create sai recusado (`permissao_de_database_nao_coletada`);
- leitura sob FTA em alvo não registrado continua acusando `SELECT`, e só a escrita
  recusa (AC17); nenhum texto explica a assimetria;
- sob FGAC, o fact liga uma mensagem de permissão do Lake Formation a um deny de IAM no
  S3, e um deny de S3 costuma aparecer como AccessDenied do S3. Está dentro do AC4
  aprovado, e o título de `SF-LF-011` não afirma que a negação produziu a mensagem.

Depois da revisão final: as docs pt-br que a feature toca foram atualizadas em
`f9cef23c` (guia `usos/lake-formation-e-acesso.md` com o caminho de ponta a ponta até
`SF-LF-011`, capítulos 06 e 07, entrada no `STATUS.md`); o espelho en-us fica para a
feature `DOCS_EN`, por decisão do operador. A atualização das docs achou um último texto
falso, corrigido em `121ef24a`: `runtime_ausente` mandava rodar `sparkforge runtime
detect`, que nunca emite `env.runtime_signal` para Glue; o texto agora aponta o
`glue_version` literal do Terraform.

Fora do escopo, registrados: `SF-LF-010` dispara em job que declara FTA (lacuna anterior
à feature); o SDK `mcp` 1.30 do ambiente derruba três arquivos de teste.
