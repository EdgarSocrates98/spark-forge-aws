# Golden path: diagnóstico Spark

Este é o caminho mínimo para investigar um job PySpark sem transformar uma
simulação em evidência de execução.

1. Prepare o caso com uma entrada versionada e um objetivo explícito.
2. Faça o replay determinístico sobre uma fixture local:

   ```powershell
   sparkforge-aws analyze pyspark --path fixtures/pyspark/collect_unbounded/input
   ```

3. Compare `facts` e `findings` com o oracle de
   `fixtures/pyspark/collect_unbounded/expected/`.
4. Só depois de uma decisão humana, faça a execução ao vivo no ambiente
   autorizado e anexe uma receipt independente.

O contrato executável está em
`docs/golden-paths/spark-diagnostic.json`. Ele usa `collect_unbounded` como
caso positivo (a regra `SF-PY-002`) e `clean_job` como negativo. Os hashes
impedem que uma fixture seja trocada silenciosamente.

## Estados de evidência

- `PREPARED`: entrada, objetivo e contexto foram definidos.
- `REPLAY_VERIFIED`: o analisador local reproduziu o oracle versionado.
- `LIVE_EXECUTED`: reservado para uma execução real autorizada; fica
  `NOT_RUN` neste contrato.
- `INDEPENDENTLY_VERIFIED`: reservado para uma receipt independente; não é
  satisfeito pelo próprio replay.

Se a entrada não existir, o caso fica `UNRESOLVED`. Hash divergente, oracle
divergente ou finding no caso negativo bloqueiam a promoção do diagnóstico.
Nenhum estado deste golden path afirma acesso à AWS, execução de Glue ou
telemetria de um cluster.
