---
name: review-streaming-operations
description: "Use quando houver um contrato declarativo de streaming e for necessário revisar SLO, FinOps, segurança, serving e lakehouse sem inventar medição, preço ou eficácia operacional."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/streaming-operations.md
  - ../../knowledge/streaming-format-serving-matrix.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze streaming-ops
  - sparkforge judge
subagent: true
agent: streaming-realtime-architect
---

# Review Streaming Operations

Use um contrato JSON salvo localmente. A análise mede declarações e preserva
lacunas; não consulta AWS e não calcula preço.

```bash
sparkforge analyze streaming-ops \
  --path streaming-operations.json \
  --out streaming-operations-facts.json
sparkforge judge --facts streaming-operations-facts.json
```

## Procedimento

1. Confirme que SLO tem métrica, unidade, janela, origem e `target` numérico.
2. Confirme que FinOps traz medida observada, unidade, período, região, tier e
   origem. Nunca transforme DPU-seconds, vCPU-hours ou bytes em preço sem uma
   base de custo declarada.
3. Revise controles de transporte, autenticação, TLS, KMS, VPC, Secrets
   Manager, cross-account e resource policy. Valores que parecem segredo são
   redigidos e viram `unresolved`.
4. Compare serving e formato lakehouse com a matriz de conhecimento; não
   derive compatibilidade, latência ou exactly-once por nome do produto.
5. Leia cada `streaming_ops.unresolved` antes de julgar. Proponha o artefato ou
   experimento que destrava cada lacuna.

## Limites

- declaração de controle não prova eficácia em runtime;
- o extrator não coleta IAM, KMS, VPC, CUR ou métricas de serviços;
- serving e formato são evidência de desenho, não benchmark;
- recomendações devem conter evidência, risco, trade-off, validação e rollback.

## Quando NÃO usar

Não use para calcular preço, coletar AWS ou declarar eficácia de controle sem
artefato de execução correspondente.

## Referência rápida

`fact_id` ancora a declaração; `*.unresolved` preserva ausência; `validation` e
`rollback` fecham a recomendação sem expor segredo.

## Red flags

SLO sem janela, FinOps sem unidade/período, segurança sem evidência de runtime e
serving sem benchmark são lacunas, não sucesso.

## Contrato de qualidade SparkForge (v1)

Separe medida declarada, finding e hipótese; não copie secrets e sempre nomeie
validation, risco e rollback.

## Protocolo

Siga `AGENT_PROTOCOL.md`, não executa manutenção destrutiva; sobe qualquer
mutação live ao operador.
