<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `verify-agent-evidence`

Use quando for necessaria a capacidade de verificar evidencias, fontes, escopo e lacunas.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/verify-agent-evidence/SKILL.md` |

## Procedimento (texto integral)

## Verify Agent Evidence

Valide findings contra fatos locais e referencias.

### Protocolo
Use fatos locais, evidence_refs, confidence e unresolved. Entregue uma decisao estruturada ao coordenador. não executa manutencao destrutiva. Se houver mutacao, sobe a decisao ao coordenador e exige confirmacao explicita.

### Quando NÃO usar
Nao use quando uma ferramenta deterministica simples resolver o caso.

### Referência rápida
Entrada: pacote minimo. Saida: facts, riscos, lacunas e next_step. Parada: uma rodada.

### Red flags
Sem fonte, contexto inteiro retransmitido, afirmacao sem evidence_ref ou mutacao sem aprovacao.
