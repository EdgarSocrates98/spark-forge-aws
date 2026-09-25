---
sdd: 1
feature: LF_FTA_DECLARADO
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Um kind derivado lakeformation.fta_declared, emitido por build_lakeformation onde o resolver de credencial do Lake Formation foi declarado, basta para SF-LF-010 deixar de acusar job que declara Full Table Access, sem calar a regra no job que so troca o filesystem S3."
  prediction: "Nas fixtures lf_negado_fta_append_sem_all e lf_negado_fta_grant_all o golden passa a ter lakeformation.fta_declared e perde SF-LF-010, e nenhum outro finding muda. Com localizacao registrada e so spark.hadoop.fs.s3.impl declarado (sem resolver), SF-LF-010 continua disparando. Se alguma das duas fixtures mantiver SF-LF-010, ou o caso so com fs.s3.impl calar a regra, ou algum golden sem resolver declarado perder SF-LF-010, a afirmacao esta errada."
  experiment: "Rodar tests/test_facts_lakeformation.py e tests/test_lakeformation_rules.py, regenerar os goldens afetados com scripts/regen_fixtures.py e ler o diff de findings de cada um."
acceptance:
  - id: AC1
    statement: "Com spark.hadoop.fs.s3.credentialsResolverClass contendo AWSLakeFormationCredentialResolver numa superficie de conf, build_lakeformation emite um lakeformation.fta_declared por superficie, com o subject e a proveniencia do lakeformation.filesystem da mesma superficie, e attrs marker, emrfs_restored e source."
    verified_by: {kind: test, ref: "tests/test_facts_lakeformation.py::TestFtaDeclarado::test_resolver_do_lake_formation_declara_fta"}
  - id: AC2
    statement: "Superficie que so declara spark.hadoop.fs.s3.impl, ou declara resolver de outro fornecedor, produz lakeformation.filesystem e nenhum lakeformation.fta_declared; num case com duas superficies, so a que pede o resolver do Lake Formation declara FTA."
    verified_by: {kind: test, ref: "tests/test_facts_lakeformation.py::TestFtaDeclarado::test_so_a_superficie_com_resolver_declara_fta"}
  - id: AC3
    statement: "lakeformation.access_model nao muda: job so de FTA continua sem access_model, e FGAC com resolver continua both."
    verified_by: {kind: test, ref: "tests/test_facts_lakeformation.py::TestOEstadoBOTH::test_job_SO_de_fta_nao_produz_access_model"}
    guard: "Guarda de regressao do comportamento de access_model: passa antes e depois por desenho, e impede que o kind novo vire um model fta calado."
  - id: AC4
    statement: "SF-LF-010 nao dispara com lakeformation.registered_location registered=true e o resolver do Lake Formation declarado (FTA), e a regra declara absent de lakeformation.fta_declared ao lado de absent de lakeformation.access_model."
    verified_by: {kind: test, ref: "tests/test_lakeformation_rules.py::TestSfLf010::test_registrado_com_fta_declarado_nao_dispara"}
  - id: AC5
    statement: "Negativo: com localizacao registrada e so spark.hadoop.fs.s3.impl declarado (sem resolver do Lake Formation), SF-LF-010 continua disparando; e sem configuracao nenhuma tambem."
    verified_by: {kind: test, ref: "tests/test_lakeformation_rules.py::TestSfLf010::test_registrado_so_com_fs_s3_impl_continua_disparando"}
    guard: "Guarda de regressao: passa antes e depois por desenho, e impede que calar a regra no FTA vire calar a regra em todo job que mexe no filesystem."
  - id: AC6
    statement: "Os goldens commitados de lf_negado_fta_append_sem_all e lf_negado_fta_grant_all trazem lakeformation.fta_declared nos facts e nao trazem SF-LF-010 nos findings nem em expects_rules; o proves deixa de nomear a lacuna."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_cloudwatch_logs.py::test_fta_declarado_cala_sf_lf_010_nos_goldens"}
  - id: AC7
    statement: "lakeformation.fta_declared aparece em algum golden (cobertura de kind por extrator)."
    verified_by: {kind: test, ref: "tests/test_fixtures_kind_coverage.py::test_every_kind_of_every_extractor_appears_in_some_golden"}
  - id: AC8
    statement: "Os gates de registro manual passam: surface lock, lastro e numeros do STATUS."
    verified_by: {kind: command, ref: "python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Goldens em que SF-LF-010 sai, contra goldens com resolver do Lake Formation declarado e localizacao registrada (esperado: 2 de 2); goldens sem resolver em que SF-LF-010 sai (esperado: 0)."
    source: "git diff dos expected/findings.json depois de scripts/regen_fixtures.py, e grep SF-LF-010 em fixtures/"
  - id: SC2
    metric: "Contagem de fact kinds distintos emitidos (esperado: 245 para 246) e numeros derivados de golden que moverem."
    source: "saida de python scripts/check_status_numbers.py --strict no ship"
out_of_scope:
  - "Tratar spark.sql.catalog.<nome>.glue.lakeformation-enabled sozinho como declaracao de FTA: o significado da chave sob FGAC esta como a verificar na secao 7 de knowledge/glue/lakeformation-fgac.md."
  - "Julgar se o FTA declarado e efetivo (resolver sob S3A no Glue 5.1 e ignorado): e pergunta da regra de EMRFS, nao desta."
  - "Mudar o comportamento de lakeformation.access_model, do FGAC ou de SF-LF-011."
  - "Resolver a semantica de conjunto do absent (um job com FTA cala a regra para outro job do mesmo case): limite ja escrito nos risks da regra."
unknowns: []
case_id: null
change_kinds: [extractor, rule, status_numbers, claims]
---

# LF_FTA_DECLARADO — requisitos

## Problema

`SF-LF-010` dispara com `lakeformation.registered_location` (`registered: true`) e
`absent: lakeformation.access_model`, e diz que o job "não declara nem FGAC nem Full Table
Access". Um job só de FTA não produz `access_model` por desenho (docstring de
`_access_models` em `sparkforge/facts/lakeformation.py`): FTA não tem argumento que o
ligue, e a superfície dele é `lakeformation.filesystem`. A regra acusa falsamente o job
que declara FTA. Medido nas fixtures `fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all`
e `lf_negado_fta_grant_all`, cujo `proves:` nomeia a lacuna e cujo `expects_rules` prende
`SF-LF-010`.

`absent: lakeformation.filesystem` não serve: esse fact sai também quando só
`spark.hadoop.fs.s3.impl` é declarado, sem o resolver. `absent:` só confere KIND, sem
`where` (regra 33 do `CLAUDE.md`): o predicado vira fact derivado.

## O que a feature entrega

1. Kind derivado `lakeformation.fta_declared`, emitido por `build_lakeformation`, um por
   superfície de conf onde o resolver do Lake Formation foi pedido.
2. `SF-LF-010` ganha `absent: lakeformation.fta_declared`, e o texto passa a dizer isso.
3. Os dois goldens de FTA regenerados, com o diff explicado.
