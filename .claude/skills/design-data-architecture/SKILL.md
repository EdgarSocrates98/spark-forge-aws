---
name: design-data-architecture
description: "Use quando for necessario desenhar arquiteturas de dados completas."
metadata:
  sparkforge_aws_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/data-platform-architecture.md
  - ../../knowledge/cross-service-constraints.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge-aws next-step
---
# Arquitetura de Dados

Defina dominios, ownership, contratos, zonas, SLAs, qualidade, seguranca, observabilidade, custo e ADRs.

## Quando NAO usar

Nao use quando o problema estiver fora do escopo.

## Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e rollback.

## Red flags

Loop sem parada, evidencia ausente, risco nao autorizado, custo nao medido e rollback inexistente.

## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
## Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

## Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.


## Contrato de qualidade SparkForge (v1)

Esta skill trata **arquitetura de dados, contratos, ownership e operação**. Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.
- **Verbos primários:** `sparkforge-aws next-step`. Use-os na ordem indicada pela skill e conserve saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.
- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.
- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.
- **Referências e eval:** `../_shared/references/evidence-first.md`, `../_shared/references/evaluation-contract.md`, `../_shared/references/operational-safety.md`, `../../knowledge/data-platform-architecture.md`, `../../knowledge/cross-service-constraints.md`; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.
