---

name: analyze-functional-rules

description: "Use quando for necessario estudar regras funcionais, contratos, estados, excecoes e criterios de aceite."

metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/dq/validation-frameworks.md
  - ../../knowledge/data-contracts-schema-evolution.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze data-quality
subagent: true
agent: data-quality-reviewer
---

# Regras Funcionais e Contratos



Converta texto de negocio em regras atomicas, precondicoes, poscondicoes, entradas, saidas, estados, excecoes, severidade, owner e criterios de aceite. Diferencie regra declarada, comportamento observado e decisao ainda sem dono.



Gere uma matriz regra-fonte-teste-evidencia. Liste conflitos entre documentos e pergunte apenas quando a ambiguidade mudar a implementacao. Valide contra dados, codigo, logs e testes sem substituir o owner humano.



## Quando NÃO usar



Nao use quando o pedido for somente uma transformacao tecnica sem regra funcional ou decisao de negocio.



## Referência rápida



Entrada: requisitos, glossario, exemplos, codigo e logs. Saida: regras atomicas, estados, casos de fronteira, matriz de rastreabilidade e lacunas.



## Red flags



Regra sem fonte, owner ou teste, conflito oculto, exemplo tratado como norma, semantica inventada, estado impossivel e criterio de aceite subjetivo.


## Protocolo

não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.

A decisao sobe ao pai coordenador antes de qualquer escrita.

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.

## Nao faz

Voce não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.

## Manutencao destrutiva

A skill não executa a operacao; a decisao sobe ao pai coordenador antes de qualquer escrita.

não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.
Manutencao destrutiva: não executa; a decisao sobe ao pai antes de qualquer escrita.

## Contrato de qualidade SparkForge (v1)

Esta skill trata **regras funcionais, contratos, estados e critérios de aceite**. Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.
- **Verbos primários:** `sparkforge analyze data-quality`. Use-os na ordem indicada pela skill e conserve saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.
- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.
- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.
- **Referências e eval:** `../_shared/references/evidence-first.md`, `../_shared/references/evaluation-contract.md`, `../_shared/references/operational-safety.md`, `../../knowledge/dq/validation-frameworks.md`, `../../knowledge/data-contracts-schema-evolution.md`; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.
