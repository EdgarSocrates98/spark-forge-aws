# Economia de Tokens e Qualidade

## Objetivo

O custo deve cair principalmente pela redução de contexto redundante, chamadas repetidas e trabalho sem ganho de informação. Nunca remova evidência, verificação ou critérios de aceitação apenas para reduzir a contagem.

## Pipeline econômico

1. Faça cache por fingerprint de entrada, versão de ferramenta e configuração.
2. Rode filtros determinísticos, parsing e regras antes do LLM.
3. Elimine duplicatas e selecione registros por relevância, risco e dependência.
4. Envie um snapshot curto com IDs de evidência e diferenças desde a última rodada.
5. Escalone esforço apenas quando houver ambiguidade, contradição, risco alto ou falha de gate.
6. Comprima o histórico após preservar decisões, fatos, lacunas e referências.

## O que sempre preservar

Objetivo, escopo, restrições, decisões, fatos críticos, referências, incertezas, falhas, critérios de sucesso e rollback. O agent pode receber ponteiros em vez de conteúdo duplicado, desde que a ferramenta consiga resolver os ponteiros.

## Anti-padrões

Não retransmita o transcript completo a cada chamada. Não faça fan-out indiscriminado. Não peça ao LLM para calcular o que uma regra determinística resolve. Não use resumo sem contagem e IDs. Não aumente o orçamento automaticamente em um loop estagnado.

## Métricas de controle

Registre `tokens_input`, `tokens_output`, `tokens_total`, `cache_hits`, `records_deduplicated`, `evidence_coverage`, `accepted_findings` e `verification_failures`. A métrica de sucesso é qualidade por token, acompanhada da taxa de conclusões verificadas.
