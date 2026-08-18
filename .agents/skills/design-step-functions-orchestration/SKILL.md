---

name: design-step-functions-orchestration

description: Use quando for necessario desenhar, revisar ou validar AWS Step Functions, EventBridge, retries e workflows serverless.

---

# Orquestracao com Step Functions



Escolha Standard ou Express por duracao, taxa de eventos, interacao humana, semantica de entrega, idempotencia e custo. Modele estados, transicoes, Choice, Map, Parallel, timeout do workflow, TimeoutSeconds, HeartbeatSeconds e TaskToken.



Classifique erros em transitorios, permanentes, timeout, permissao e limite. Use Retry especifico com IntervalSeconds, MaxAttempts, BackoffRate, MaxDelaySeconds e jitter quando necessario. Use Catch com contexto preservado e caminho de compensacao.



Evite payloads grandes entre estados: passe referencias S3 quando o dado puder crescer. Considere limite de historico, workflows aninhados, redrive, IAM minimo, logs estruturados e custo por transicao. Eventos S3 podem iniciar execucoes via EventBridge.



## Quando NÃO usar



Nao use quando um fluxo sincrono simples e deterministico puder ser resolvido por uma unica funcao sem estado duravel.



## Referência rápida



Entrada: eventos, estados, dependencias, SLAs, falhas e custos. Saida: grafo ASL, politica de erro, timeouts, IAM, observabilidade, testes e rollback.



## Red flags



Retry em erro permanente, ausencia de timeout, payload crescente, Lambda sem idempotencia, Catch que perde contexto, IAM amplo e workflow sem caminho de compensacao.


## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
