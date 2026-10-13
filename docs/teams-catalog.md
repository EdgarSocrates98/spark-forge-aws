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

## Time de Storage e Lakehouse

Composicao: iceberg-performance-engineer como coordenador, athena-query-optimizer e sf-terraform-specialist. O foco é catalogo, locking, snapshots, layout, compaction, small files, lifecycle, criptografia, policies, pruning e custo. O time entrega tabela, schema, particoes, politica de manutencao, segurança e plano de rollback.

## Time de Grafos e Serving Operacional

Composicao: pyspark-code-reviewer como coordenador, athena-query-optimizer, iceberg-performance-engineer e sf-terraform-specialist. O time compara traversal, access patterns, chaves, indices, consistencia, carga, spill, RCUs, bytes scanned e custo. O resultado inclui consultas representativas, limites de cardinalidade, testes de carga e comportamento de falha.

## Time de Revisao e Validacao

Composicao: spark-performance-architect como coordenador, revisor de regras, especialista tecnico relevante, sf-terraform-specialist quando houver infraestrutura e documentador. O time verifica cobertura, evidência, qualidade, custo, segurança, regressao, rollback e legibilidade. A revisão deve separar defeitos bloqueantes, riscos aceitos, perguntas abertas e melhorias futuras.

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
