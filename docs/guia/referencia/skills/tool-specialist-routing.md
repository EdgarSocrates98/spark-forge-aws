<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `tool-specialist-routing`

Use quando for necessario escolher, validar ou autorizar ferramentas por especializacao, risco e contrato.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/tool-specialist-routing/SKILL.md` |
| `metadata` | {'sparkforge_contract': 'v1', 'evals': 'evals/evals.json', 'references': ['references/README.md', '../_shared/references/evidence-first.md', '../_shared/references/evaluation-contract.md', '../_shared/references/operational-safety.md'], 'scripts': ['scripts/validate_evidence.py'], 'primary_verbs': ['sparkforge next-step']} |

## Procedimento (texto integral)

## Especializacao e Roteamento de Ferramentas

Escolha poucas ferramentas por agent, valide argumentos, registre fingerprints e autorize mutacoes somente com aprovacao e rollback.

### Contrato

Toda ferramenta devolve status, facts, warnings, evidence_refs, next_step e rollback.
### Quando NÃO usar

Nao use esta skill quando uma ferramenta deterministica simples resolver a tarefa sem cooperacao adicional.

### Referência rápida

Entrada: objetivo, escopo, evidencias e restricoes. Saida: handoff estruturado, referencias e proximo passo.

### Red flags

Contexto inteiro retransmitido, fan-out sem ganho, ausencia de evidencias, retry de contrato invalido ou mutacao sem aprovacao.

### Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.


### Contrato de qualidade SparkForge (v1)

Esta skill trata **roteamento por evidência para especialista e verbo**. Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.
- **Verbos primários:** `sparkforge next-step`. Use-os na ordem indicada pela skill e conserve saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.
- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.
- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.
- **Referências e eval:** `../_shared/references/evidence-first.md`, `../_shared/references/evaluation-contract.md`, `../_shared/references/operational-safety.md`; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.
