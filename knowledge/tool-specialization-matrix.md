# Matriz de Especialização de Ferramentas

| Domínio | Agent primário | Ferramentas | Evidência produzida | Escalonamento |
|---|---|---|---|---|
| Inventário | sf-inventory | listagem, detecção de runtime, leitura de configuração | escopo, versões, caminhos | sf-extractor |
| Coleta | sf-extractor | fatos AWS, logs, metadados e snapshots | fatos normalizados com origem | sf-judge |
| PySpark | sf-pyspark-specialist | AST, plano físico, benchmark e análise de skew | achados de código e performance | sf-verifier |
| Glue e EMR | sf-runtime-specialist | matriz de runtime, configuração e infraestrutura | compatibilidade e riscos | sf-verifier |
| Iceberg e Parquet | sf-storage-specialist | metadados, layout e diagnóstico de tabela | layout, manutenção e impacto | sf-verifier |
| Qualidade | sf-data-quality | validações, contratos e consistência | falhas reproduzíveis | sf-judge |
| Julgamento | sf-judge | regras catalogadas e fusão de fatos | gargalo dominante e confiança | sf-verifier |
| Verificação | sf-verifier | reexecução, assinatura e validação | confirmação, refutação ou bloqueio | sf-synthesizer |
| Síntese | sf-synthesizer | relatório, plano, rollback e assinatura | recomendação final rastreável | humano quando necessário |

Cada agent recebe apenas as ferramentas da sua linha e os conhecimentos referenciados. O supervisor pode aumentar a colaboração quando a evidência divergir, mas não deve fan-out por padrão.
