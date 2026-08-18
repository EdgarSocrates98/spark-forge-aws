---

name: design-lambda-serverless

description: Use quando for necessario projetar, analisar ou otimizar AWS Lambda, eventos, concorrencia e arquiteturas serverless.

---

# Lambda e Serverless



Analise ciclo de vida, reuso do ambiente, clientes SDK fora do handler, /tmp, conexoes, variaveis de ambiente, payload, dependencias, IAM, timeout, memoria, cold start e concorrencia.



Exija idempotencia para efeitos mutaveis e assuma entrega at-least-once em fontes de eventos. Revise reserved concurrency, limites downstream, retries com backoff e jitter, partial batch response, logs JSON, metricas, alarmes e EMF.



Meça memoria, duracao, erros, throttles, custo e throughput. Nao recomende escala sem testar dependencias downstream. Redija segredos e preserve apenas referencias seguras no contexto do agent.



## Quando NÃO usar



Nao use quando o problema for exclusivamente uma regra SQL, contrato funcional ou analise de tabela sem componente serverless.



## Referência rápida



Entrada: handler, eventos, limites, dependencias, IAM e metricas. Saida: desenho, riscos, parametros, testes, alarmes, idempotencia e rollback.



## Red flags



Invocacao recursiva, efeito mutavel sem chave de deduplicacao, timeout maior que visibilidade da fila, IAM amplo, conexao criada por evento, logs sem contexto e downstream sem limite.


## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
