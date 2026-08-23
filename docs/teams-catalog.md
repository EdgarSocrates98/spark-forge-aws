# Catalogo de Times do SparkForge AWS

## Proposito

Os times sao uma metafora operacional para coordenar agents especializados. A sala de conversa representa um protocolo: mensagens estruturadas, contexto selecionado, handoffs verificaveis, revisao cruzada e criterio de parada. O supervisor nao retransmite todo o historico; ele compartilha apenas fatos, decisoes, lacunas e evidencias relevantes.

## Composicao comum

| Papel | Responsabilidade | Saida |
| --- | --- | --- |
| Coordenador | Define objetivo, orçamento, fases, roteamento e parada | Plano e decisao |
| Especialista | Resolve uma parte do problema com conhecimento profundo | Evidencia e recomendacao |
| Builder | Produz codigo, configuracao, schema ou desenho | Artefato revisavel |
| Revisor cruzado | Procura contradições, gaps, riscos e alternativas | Findings priorizados |
| Verificador | Executa testes, checks, benchmark e cobertura | Evidencia de validade |
| Documentador | Registra contratos, ADRs, runbooks e uso | Memoria duravel |
| Operador de ferramenta | Usa apenas ferramentas autorizadas e idempotentes | Resultado da operacao |

## Time de Arquitetura de Solucoes de Dados

Composicao: sf-data-architect como coordenador, sf-analytics-specialist, sf-functional-rules-specialist, sf-runtime-specialist, sf-storage-specialist, sf-terraform-specialist e sf-token-verifier. O time parte de requisitos e access patterns, define dominios, contratos, zonas, segurança, SLAs, ownership, custo e ADRs. O handoff para implementacao contém modelo, interfaces, riscos, testes, rollback e critérios de aceite.

## Time de Arquitetura de Pipelines Completos

Composicao: sf-airflow-specialist ou sf-step-functions-specialist como coordenador de fluxo, sf-pyspark-specialist, sf-runtime-specialist, sf-iceberg-specialist, sf-parquet-specialist, sf-s3-specialist, sf-athena-specialist e sf-token-verifier. O time desenha ingestao, transformacao, particao, armazenamento, orquestracao, retries, backfill, qualidade, observabilidade e custo. O gate exige idempotencia, reexecucao segura, teste de falha e medicao de bytes ou tempo.

## Time de Storage e Lakehouse

Composicao: sf-storage-specialist como coordenador, sf-iceberg-specialist, sf-parquet-specialist, sf-s3-specialist, sf-athena-specialist e sf-terraform-specialist. O foco é catalogo, locking, snapshots, layout, compaction, small files, lifecycle, criptografia, policies, pruning e custo. O time entrega tabela, schema, particoes, politica de manutencao, segurança e plano de rollback.

## Time de Orquestracao Serverless

Composicao: sf-step-functions-specialist como coordenador, sf-lambda-serverless-specialist, sf-airflow-specialist, sf-runtime-specialist, sf-terraform-specialist e sf-token-verifier. O foco é estados, eventos, retries, timeout, idempotencia, concorrencia, DLQ, observabilidade, IAM e custo. O gate exige cenarios de erro, replay, deduplicacao e limite de impacto.

## Time de Grafos e Serving Operacional

Composicao: sf-graph-specialist como coordenador, sf-neptune-specialist, sf-dynamodb-specialist, sf-athena-specialist, sf-s3-specialist e sf-terraform-specialist. O time compara traversal, access patterns, chaves, indices, consistencia, carga, spill, RCUs, bytes scanned e custo. O resultado inclui consultas representativas, limites de cardinalidade, testes de carga e comportamento de falha.

## Time de Criacao e Evolucao de Agents

Composicao: sf-agent-builder como coordenador, sf-orchestrator, sf-token-verifier, especialistas de dominio, revisor cruzado e documentador. O time define contrato, ferramentas, skills, memoria, loops, handoffs, autorização, seleção adaptativa de modelos, avaliação e observabilidade opcional. Nenhum loop é aceito sem orçamento, criterio de parada e teste de qualidade.

## Time de Revisao e Validacao

Composicao: sf-token-verifier como coordenador, revisor de regras, especialista tecnico relevante, sf-terraform-specialist quando houver infraestrutura e documentador. O time verifica cobertura, evidência, qualidade, custo, segurança, regressao, rollback e legibilidade. A revisão deve separar defeitos bloqueantes, riscos aceitos, perguntas abertas e melhorias futuras.

## Protocolo de handoff

Todo handoff segue o contrato: `goal`, `facts`, `decisions`, `uncertainties`, `artifacts`, `risks`, `validation`, `rollback` e `next_action`. O receptor confirma o que pode reutilizar e aponta somente lacunas. Não se deve copiar logs extensos, repetir contexto já conhecido ou substituir evidência por opinião.

## Fluxo de execução

1. Observe: inventário barato, escopo, fatos e lacunas.
2. Planeje: decomposição, orçamento, critérios de sucesso e agentes autorizados.
3. Despache: tarefas sem sobreposição inútil e com entregáveis explícitos.
4. Debata: compare alternativas e faça revisão cruzada apenas onde houver risco ou divergência.
5. Verifique: execute testes, benchmark, contraexemplos e checagens de segurança.
6. Sintetize: registre decisão, tradeoffs, evidências, custo, riscos e rollback.
7. Decida: pare quando o critério for atingido, quando não houver ganho marginal, quando o orçamento terminar ou quando exigir autorização humana.

## Economia e autonomia

A autonomia é alta em melhoria, construcao, documentacao e validacao, mas limitada por autorização de ferramentas e risco. Use coleta deterministica, fingerprints, deduplicacao, contexto por relevancia, resumos compactos, fan-out controlado e modelos adaptativos descobertos do inventario da conta. Observabilidade da conversa é opcional; quando houver uso de tokens, exiba aviso sem tornar trace obrigatório.
