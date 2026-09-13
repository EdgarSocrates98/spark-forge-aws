<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `token-efficient-agent`

Use quando o objetivo exigir economia de tokens sem reduzir evidencia, precisao, cobertura ou verificacao.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/token-efficient-agent/SKILL.md` |

## Procedimento (texto integral)

## Agent Eficiente em Tokens

Reduza contexto redundante, chamadas repetidas e trabalho sem ganho de informacao, preservando evidencias, revisao e criterios de aceitacao.

### Politica

Use cache, filtros deterministas, deduplicacao, selecao por relevancia, snapshot verificavel e escalonamento de esforco.
### Quando NÃO usar

Nao use esta skill quando uma ferramenta deterministica simples resolver a tarefa sem cooperacao adicional.

### Referência rápida

Entrada: objetivo, escopo, evidencias e restricoes. Saida: handoff estruturado, referencias e proximo passo.

### Red flags

Contexto inteiro retransmitido, fan-out sem ganho, ausencia de evidencias, retry de contrato invalido ou mutacao sem aprovacao.

### Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
