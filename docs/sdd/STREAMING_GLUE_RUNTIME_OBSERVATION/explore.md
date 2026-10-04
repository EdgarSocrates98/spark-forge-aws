---
sdd: 1
feature: STREAMING_GLUE_RUNTIME_OBSERVATION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Correlacionar facts glue.streaming.job com glue.job_run no fuse existente e emitir runtime_link/unresolved."
    tradeoffs:
      - "Reutiliza collector, analyzer, CLI e MCP existentes; não aumenta surface."
      - "Só observa runs que o operador coletou e preserva unresolved quando a amostra não responde."
  - id: B
    summary: "Embebedar runs recentes dentro do artefato de definição Glue e estender o extrator de job."
    tradeoffs:
      - "Um artefato aparentemente simples para o operador."
      - "Acopla definição e histórico, duplica dados e dificulta cache/reextração incremental."
  - id: C
    summary: "Criar um novo verbo analyze glue-streaming-runtime e uma tool MCP correspondente."
    tradeoffs:
      - "Contrato explícito e descoberta direta."
      - "Move surface lock, referências e payload para uma operação que fuse já consegue compor."
chosen: A
---

# STREAMING_GLUE_RUNTIME_OBSERVATION — exploração

## Perfil e motivo

`dev`: mudança no SparkForge. A auditoria de `prompt_evo_streaming.md` deixou
Glue Streaming/RTM com contrato declarativo e cross-artifact Terraform, mas sem
ligação entre definição efetiva e execução observada. O repositório já possui
`collect glue-job-runs`, `analyze glue-job-runs` e facts `glue.job_run`; a lacuna
é a composição entre os dois domínios.

## Evidência consultada

- `sparkforge rules lookup --category glue_streaming`: cinco regras existentes,
  incluindo `SF-GLUESTREAM-001` a `SF-GLUESTREAM-005`.
- `sparkforge sdd status --repo .`: feature nova ainda inexistente; base em
  `6a93d30`.
- `sparkforge/facts/glue_streaming.py`: definição efetiva observa versão, modo,
  linguagem, fonte, capacidade e restrições.
- `sparkforge/facts/glue_job_run.py`: run terminal observa versão, worker type,
  workers, estado e duração.

## Perguntas e decisão operacional

1. Quem consome a correlação? O mesmo `fuse` e o `judge` que já consomem o
   link Terraform; nenhuma nova operação é necessária nesta wave.
2. O que é runtime observado? Somente campos presentes em `glue.job_run` e
   `glue.streaming.job`; ausência não vira igualdade.
3. Por que não criar um tool? A requisição de economia de tokens favorece
   composição sobre fatos já carregados, preservando uma única superfície.

## Escolha

Escolhida A. Ela fecha o maior ponto cego do Wave E usando artefatos que já têm
collector, analyzer, fixtures e contrato. B fica rejeitada por duplicação de
artefato; C fica rejeitada por crescimento de superfície sem novo consumidor.

## Limites

Esta wave não consulta AWS, não executa job, não prova saúde do stream, não
infere throughput/latência a partir de duração de run e não transforma uma
amostra curta em garantia de produção.
