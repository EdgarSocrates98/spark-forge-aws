# Auditoria dos 26 critérios de aceite do prompt

| # | Critério | Prova executável | Limite honesto |
|---:|---|---|---|
| 1 | FGAC vs FTA | `test_prompt_scenario_matrix_has_positive_and_negative_cases` | `unknown` sem modelo declarado |
| 2 | quando usar cada modelo | `test_performance_finops_preserves_measurement_boundaries` | impacto é condicional |
| 3 | Glue 4/5.0/5.1 | `test_migration_report_covers_declared_transition_families` | fontes version-aware |
| 4 | releases EMR | `test_prompt_scenario_matrix_has_positive_and_negative_cases` | célula não publicada fica `unknown` |
| 5 | Parquet cross-account | matriz de cenários + `test_access_graph_and_cross_account_observability_are_explicit` | catálogo governado não vira S3 direto |
| 6 | Iceberg cross-account | caminho Iceberg no access graph | GlueCatalog/S3FileIO separados |
| 7 | metadata vs data | `authorization` e `access_explain` | não provar acesso só por metadata |
| 8 | credential vending | preflight/taxonomia | GetDataAccess deve ser medido |
| 9 | RAM | preflight RAM share/association | ausência é `unresolved` |
| 10 | cross-account version | preflight version | versão não é inferida da conta |
| 11 | IAMAllowed/hybrid | testes de governance anteriores | opt-in/registration continuam necessários |
| 12 | `glue.id` | routing semantic comparisons | ownership precisa ser declarado |
| 13 | `glue.account-id` | routing semantic comparisons | contexto esperado precisa ser declarado |
| 14 | IDs distintos | `test_source_and_target...` e routing | nenhum alias automático |
| 15 | Terraform | `review.code_and_iac` | facts já extraídos; sem reextração |
| 16 | Spark config | `review.code_and_iac` | ordem desconhecida é lacuna |
| 17 | PySpark | DynamicFrame/direct-S3 checks | não substitui execução |
| 18 | configuração tardia | `LATE-LF-CONFIG` | linha ausente não prova ordem |
| 19 | resource links | rota condicionada | Glue ETL pode usar CatalogId explícito |
| 20 | diagnóstico por evidência | root cause/taxonomia | hipóteses não são fatos |
| 21 | least privilege | checks e fix sem wildcard | não concede permissões |
| 22 | performance/custo | dimensões FinOps | sem número sem benchmark |
| 23 | cenários positivos | matriz declarativa | não substitui run real |
| 24 | cenários negativos | matriz declarativa | fail-closed |
| 25 | conhecimento version-aware | capability matrix/source locks | divergência fica `version_dependent` |
| 26 | economia de tokens | decision graph/progressive disclosure | bytes não viram tokens |

O documento é auditado por `tests/test_lakeformation_prompt_acceptance.py` e não
substitui os facts coletados do caso operacional.
