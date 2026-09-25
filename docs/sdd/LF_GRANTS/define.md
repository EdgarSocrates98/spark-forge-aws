---
sdd: 1
feature: LF_GRANTS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/LF_GRANTS/explore.md
  sha256: "d0208d578db73592e38e90534a54ae16ceed3353b90b7429701b3f9c9f13a1dc"
hypothesis:
  claim: "Cruzar a falha observada (assinatura ERR-LF-*) com a operacao lida do codigo, os grants medidos, a decisao de IAM, o modelo de acesso e a versao do runtime basta para nomear a permissao ausente, ou recusar por nome quando nao basta, sem coletor novo."
  prediction: "Nas fixtures sinteticas de FTA com escrita, FTA com leitura e FGAC com escrita, judge emite SF-LF-011 nomeando a permissao ausente e o lado (lf ou iam). Na fixture negativa (grant cobre a operacao) SF-LF-011 nao dispara. Nas fixtures de conflito da secao 6, modelo both e operacao sem fact, sai lakeformation.missing_grant.unresolved com a razao nomeada. Se alguma fixture de acusacao sair unresolved, ou a negativa disparar, a afirmacao esta errada."
  experiment: "Rodar tests/test_lakeformation_missing_grant.py e tests/test_lakeformation_rules.py sobre as fixtures novas em fixtures/lakeformation/, e judge sobre a uniao dos facts de cada fixture."
acceptance:
  - id: AC1
    statement: "Sob FTA, com pyspark.write em modo append, grant medido so com SELECT e ERR-LF-001 casado no log, o extrator emite lakeformation.missing_grant com required=ALL, side=lf e o grant medido em evidence. Fonte: pagina de FTA do Glue, 'AWS Glue Spark jobs that write/delete data in Amazon S3 require AWS Lake Formation ALL permission.'"
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fta_append_sem_all_acusa_all"}
  - id: AC2
    statement: "Sob FTA, com pyspark.read e grant medido sem SELECT nem ALL, o extrator emite missing_grant com required=SELECT e side=lf."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fta_leitura_sem_select_acusa_select"}
  - id: AC3
    statement: "Fixture negativa: com o grant cobrindo a permissao que a operacao exige, nenhum lakeformation.missing_grant e emitido, mesmo com ERR-LF-001 casado. A falha esta em outra perna, e o extrator nao inventa uma."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_grant_que_cobre_nao_acusa"}
  - id: AC4
    statement: "Sob FGAC, com escrita, runtime cujo eixo fgac_spark_native_write e supported e iam.access_decision diferente de allowed para a acao exigida, o extrator emite missing_grant com side=iam e denied_by copiado da decisao."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fgac_escrita_cobra_iam_com_denied_by"}
  - id: AC5
    statement: "Sob FGAC, escrita cujo alvo tem lakeformation.registered_location com registered=true sai lakeformation.missing_grant.unresolved com reason=conflito_declarado_fgac_escrita_registrada, citando a secao 6 de knowledge/glue/lakeformation-fgac.md, e sem permissao nomeada."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fgac_escrita_registrada_e_conflito_declarado"}
  - id: AC6
    statement: "Modelo both, modelo ausente e runtime ausente saem cada um como unresolved, com uma razao distinta e com o unlock nomeado."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_modelo_ou_runtime_desconhecido_recusa_por_nome"}
  - id: AC7
    statement: "Sob FGAC, escrita num runtime cujo eixo fgac_spark_native_write e not_supported sai unresolved com reason=escrita_fgac_nao_suportada_no_runtime. A causa e versao, nao permissao."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fgac_escrita_em_runtime_sem_suporte_nao_e_permissao"}
  - id: AC8
    statement: "Com ERR-LF-001 casado e nenhum fact de operacao (pyspark.read, pyspark.write ou sql.write_statement), o extrator sai unresolved com reason=operacao_nao_medida e unlock nomeando o analyze de codigo."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_sem_operacao_recusa_por_nome"}
  - id: AC9
    statement: "Sem error.signature_match de assinatura ERR-LF-*, o extrator nao emite nada. Sem falha observada nao ha permissao ausente a afirmar."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_sem_falha_observada_nao_emite"}
  - id: AC10
    statement: "A tabela operacao->permissao e dado em knowledge/glue/, carregada por codigo, com fonte T1 em knowledge/sources.lock.json. Toda operacao que o extrator mapeia tem linha na tabela, e toda linha cita a fonte."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_tabela_de_operacao_cita_fonte_e_cobre_o_extrator"}
  - id: AC11
    statement: "fuse() chama o extrator: rodado sobre a uniao dos facts de uma fixture de acusacao, a saida contem lakeformation.missing_grant."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fuse_deriva_missing_grant"}
  - id: AC12
    statement: "A regra SF-LF-011 dispara em judge sobre as fixtures de AC1, AC2 e AC4, e nao dispara sobre as de AC3, AC5 e AC8."
    verified_by: {kind: test, ref: "tests/test_lakeformation_rules.py::test_sf_lf_011_dispara_so_com_permissao_nomeada"}
  - id: AC13
    statement: "lakeformation.missing_grant pertence a EMITTED_KINDS de algum extrator. ERR-LF-001 deixa de declarar em evidence_required um kind que ninguem emite, exceto ram.unaccepted_share, que continua fora de alcance e passa a ser declarado como tal."
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_evidence_de_err_lf_001_e_emitida"}
  - id: AC14
    statement: "build_access_graph, com missing_grant no case, marca a perna lf_grant como missing citando a permissao exigida pela operacao, e nao SELECT fixo."
    verified_by: {kind: test, ref: "tests/test_lakeformation_access_graph.py::test_grafo_usa_missing_grant_quando_existe"}
  - id: AC15
    statement: "Sem missing_grant no case, build_access_graph devolve exatamente o que devolvia antes."
    verified_by: {kind: test, ref: "tests/test_lakeformation_access_graph.py::test_grafo_sem_missing_grant_inalterado"}
    guard: "Guarda de regressao do comportamento atual do grafo: passa antes e depois por desenho, e impede que o consumo do fact novo mude as saidas e os goldens sem ele."
  - id: AC16
    statement: "Os gates de registro manual passam: surface lock, lastro e numeros do STATUS."
    verified_by: {kind: command, ref: "python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py"}
  - id: AC17
    statement: "Sob FTA, escrita (write ou overwrite) cujo alvo tem lakeformation.registered_location com registered=false medido sai lakeformation.missing_grant.unresolved com reason=fta_escrita_em_alvo_nao_registrado, e nenhum missing_grant. Fonte: secao 5 de knowledge/glue/lakeformation-fgac.md, 'the job's runtime role credentials will be used to read/write tables not registered with AWS Lake Formation.'"
    verified_by: {kind: test, ref: "tests/test_lakeformation_missing_grant.py::test_fta_escrita_em_alvo_nao_registrado_recusa"}
success:
  - id: SC1
    metric: "Fixtures sinteticas com ERR-LF-* em que o achado nomeia a permissao ausente, contra o total de fixtures de acusacao (esperado: 3 de 3). Fixtures de recusa com a razao certa (esperado: todas)."
    source: "saida de pytest tests/test_lakeformation_missing_grant.py tests/test_lakeformation_rules.py -v no ship"
  - id: SC2
    metric: "Crescimento declarado da superficie, em bytes, e a contagem nova de extratores, kinds e regras."
    source: "diff de docs/surface.lock.json e saida de python scripts/check_status_numbers.py no ship"
out_of_scope:
  - "Coletor novo, inclusive o de documento de policy IAM (get-account-authorization-details). Abordagem descartada no explore."
  - "Pernas sem coletor do caminho de acesso: RAM share (ram.unaccepted_share) e key policy do KMS."
  - "Gerar o comando grant-permissions ou o trecho de policy a aplicar. O fact nomeia o que falta, sem propor valor."
  - "Escolher lado no conflito declarado da secao 6 (regra 32)."
  - "Verbo novo de CLI ou tool MCP. O fact chega por fuse(), judge e o grafo que ja existem."
unknowns: []
case_id: null
change_kinds: [extractor, rule, rule_runtime_scope, knowledge_doc, disk_read, status_numbers, claims]
---

# LF_GRANTS — requisitos

## Problema

`ERR-LF-001` (`Insufficient Lake Formation permission(s) on`) declara
`lakeformation.missing_grant` como evidência, e nenhum extrator emite esse kind. Por isso
`SF-ERR-006` só consegue mandar `investigate`. Os grants (`collect lakeformation`) e a
decisão de IAM (`collect iam-access`) já são coletados, mas nenhum achado cruza os dois com
a falha observada. `build_access_graph` exige `SELECT` fixo e acusa a permissão errada
quando a operação que falhou é escrita.

## O que a feature entrega (abordagem A do explore)

1. **Extrator derivado** `lakeformation.missing_grant` e `.unresolved`, chamado em
   `fuse()`. Ele recebe a união dos facts: `error.signature_match` (ERR-LF-*),
   `pyspark.read`, `pyspark.write` e `sql.write_statement` para a operação,
   `lakeformation.grant`, `iam.access_decision`, `lakeformation.access_model`,
   `lakeformation.registered_location` e o runtime.
2. **Tabela operação→permissão** como dado em `knowledge/glue/`, com fonte T1.
3. **Regra `SF-LF-011`**, que consome o fact.
4. **`build_access_graph`** consome o fact quando ele existe.

## Decisão por modelo de acesso (regras 31 e 32)

| Modelo | Operação | Cobra | Saída quando falta |
|---|---|---|---|
| FTA | leitura | `SELECT` no grant do LF | `missing_grant`, `side=lf` |
| FTA | escrita ou delete de dado, alvo registrado ou não medido | `ALL` no grant do LF | `missing_grant`, `side=lf` |
| FTA | escrita, `registered: false` medido | — (escreve o runtime role) | `unresolved: fta_escrita_em_alvo_nao_registrado` (AC17) |
| FGAC | leitura | grant do LF | `missing_grant`, `side=lf` |
| FGAC | escrita, runtime `supported` | `iam.access_decision` | `missing_grant`, `side=iam`, `denied_by` |
| FGAC | escrita, runtime `not_supported` | — | `unresolved: escrita_fgac_nao_suportada_no_runtime` |
| FGAC | escrita em alvo registrado | — | `unresolved: conflito_declarado_fgac_escrita_registrada` |
| `both` ou ausente | qualquer | — | `unresolved`, razão própria |

O eixo de versão vem de `knowledge/glue/lakeformation-matrix.yaml` (`fgac_spark_native_write`),
lido por `sparkforge/facts/lakeformation_matrix.py`. A versão não é suposta.

## Fixtures

Todas sintéticas (memória *caso real nunca entra em arquivo*), em `fixtures/lakeformation/`,
uma por critério de AC1 a AC9. A negativa (AC3) e a de "outra perna" existem de propósito.
É o que a revisão final pega quando o corpus não cobre.

## Tabela operação→permissão (U1 resolvida em 2026-09-21, no design)

| Operação (Glue Spark) | Permissão do Lake Formation | Fonte |
|---|---|---|
| leitura | `SELECT` na tabela | FTA (§5 de `lakeformation-fgac.md`) e referência de permissões |
| escrita ou delete de dado, sob FTA | `ALL` na tabela | `security-access-control-fta.html` |
| create table | `CREATE_TABLE` no database, e `DATA_LOCATION_ACCESS` quando a localização é registrada e o database não é prefixo S3 dela | `lf-permissions-reference.html` |
| alter | `ALTER` na tabela | `lf-permissions-reference.html` |

**Correção do explore, aprovada pelo operador em 2026-09-21.** O explore dizia que append
pede `INSERT` e que alvo em localização registrada pede `DATA_LOCATION_ACCESS`. A fonte T1
desmente as duas coisas. Para job Spark do Glue sob FTA, escrita pede `ALL`. E a
referência diz: *"`DATA_LOCATION_ACCESS` is not needed to query or update underlying data.
This permission applies only to creating Data Catalog resources."* O `explore.md` fica como
registro histórico, e a correção vale a partir deste define.

## Lacunas resolvidas no design

- **U1:** tabela acima, cada linha citada.
- **U2:** pela §6 de `lakeformation-fgac.md`, opção 1, a escrita sob FGAC em alvo não
  registrado usa `s3:PutObject` e `s3:DeleteObject` do runtime role. Ação que o operador
  não simulou em `collect iam-access` sai `unresolved`, nomeando a ação a simular.
- **U3:** no caminho de log, `error.signature_match` carrega `attrs.matched_line`, com no
  máximo 200 caracteres (`sparkforge/errors/matcher.py`). O recurso sai do trecho
  `on <recurso>` quando cabe nesse limite. Quando não cabe, vem do case como candidato
  único, e com mais de um candidato sai `unresolved`.
