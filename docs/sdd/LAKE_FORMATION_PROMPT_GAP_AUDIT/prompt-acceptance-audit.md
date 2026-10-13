# Auditoria final dos gaps do prompt FGAC/FTA

Esta auditoria complementa `LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION`.
Ela não repete a suíte ampla já validada; prova lacunas de cobertura da matriz
final e regressões dos cinco pontos destacados na revisão.

| Gap/combinação | Prova | Resultado esperado |
|---|---|---|
| Glue 5.1 FTA Parquet | `test_prompt_final_knowledge_matrix_is_executable` | `unresolved` sem filesystem/prova suficiente |
| Glue 4 DynamicFrame corrente | mesma matriz + `test_prompt_critical_gap_regressions` | não vira migration sem target |
| EMR Serverless cross-account/resource link | matriz final | `consistent` com rota/evidência fechadas |
| EMR FTA cross-account | matriz final | separa producer/consumer e RAM |
| Hybrid cross-account | matriz final e regressão crítica | `IAMAllowedPrincipals` contextual |
| LF-TBAC + RAM | matriz final | não inventa grant nem bloqueio genérico |
| Cross-account v5 | matriz final | versão 5 aceita pelo contrato `>=4` |
| EMR 7.12 FGAC DML | matriz final | `unknown`/`unresolved` sem célula exata |
| capability `not_supported` | `test_prompt_critical_gap_regressions` | decision engine `blocked` |
| source/target independentes | mesma regressão | operações e capabilities separadas |
| Glue ETL `explicit_catalog_id` | mesma regressão | resource link não é requisito universal |
| migration report | `test_migration_report_has_prompt_sections` | seções estruturadas do §77 |
| disclosure por engine | `test_decision_graph_is_bounded_and_version_aware` | EMR não carrega Glue-only ref |

Limites permanecem explícitos: os casos são offline e não provam execução AWS,
IAM, RAM, CloudTrail, KMS, grants ou correção semântica de dados no ambiente
real. `consistent` significa somente que nenhuma lacuna foi encontrada nos
facts declarados.
