---
name: glue-incremental-performance-architect
description: Use quando investigar de ponta a ponta uma biblioteca PySpark no AWS Glue com fluxos full e incremental, latest-per-key em tabelas Iceberg bilionárias, batching, OOM após horas e cargas muito variáveis, e precisa orquestrar as skills especializadas em vez de fazer tuning localizado.
---

# Glue Incremental Performance Architect

## Sequência obrigatória

1. Ler `PROMPT_INICIAL_MESTRE.md`.
2. Executar `analyze-library-call-graph`.
3. Desenhar fluxos full e incremental.
4. Executar `design-incremental-processing`.
5. Executar `optimize-latest-per-key` para cada tabela incremental relevante.
6. Executar `analyze-batch-loop`.
7. Executar `diagnose-oom`.
8. Analisar joins, planos, UI e skew.
9. Analisar Parquet/Iceberg.
10. Executar `review-glue-terraform`.
11. Executar `optimize-variable-volume-job`.
12. Formular arquitetura-alvo.
13. Criar experimentos.
14. Executar `benchmark-pyspark-job`.
15. Validar resultados e gerar rollback.

## Bloqueios de qualidade

Não encerrar com:
- apenas aumento de workers;
- apenas mudança de shuffle partitions;
- apenas broadcast hints;
- apenas compactação;
- apenas cache.

É obrigatório explicar a relação entre full, incremental, estado atual, scans globais, batching e commits Iceberg.

## Quando NÃO usar

- O job tem um único fluxo simples e um sintoma isolado: use `sparkforge-diagnose` ou a skill específica.
- Você só quer revisar código/PR/Terraform: use a skill focada correspondente.
- Já mapeou tudo e falta apenas medir: vá para `benchmark-pyspark-job`.

## Referência rápida

| Etapa da investigação | Skill de apoio | Pergunta central |
|---|---|---|
| mapear trabalho oculto | `analyze-library-call-graph` | onde estão actions, reads, writes e UDFs? |
| provar incremental real | `design-incremental-processing` | entrada pequena reduz bytes/arquivos lidos? |
| custo do latest-per-key | `optimize-latest-per-key` | recomputa todo o histórico a cada ciclo? |
| batching prejudicial | `analyze-batch-loop` | reduz trabalho na origem ou recompõe o DAG? |
| classificar a falha | `diagnose-oom` | driver, executor, broadcast, metadata ou lineage? |
| dimensionar por carga | `optimize-variable-volume-job` | um perfil serve para micro e full? |

## Red flags

- Fazer tuning localizado antes de mapear biblioteca, actions, batching, latest-per-key e OOM.
- Encerrar só com "mais workers", shuffle partitions, broadcast, compactação ou cache.
- Não separar e explicar os DAGs de full e incremental.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
