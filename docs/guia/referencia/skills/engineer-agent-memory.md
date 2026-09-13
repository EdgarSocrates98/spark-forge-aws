<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `engineer-agent-memory`

Use quando for necessaria a capacidade de projetar memoria auditavel por sessao, caso e dominio.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/engineer-agent-memory/SKILL.md` |

## Procedimento (texto integral)

## Engineer Agent Memory

Recupere decisoes e casos semelhantes com origem e checksum.

### Protocolo
Use fatos locais, evidence_refs, confidence e unresolved. Entregue uma decisao estruturada ao coordenador. não executa manutencao destrutiva. Se houver mutacao, sobe a decisao ao coordenador e exige confirmacao explicita.

### Quando NÃO usar
Nao use quando uma ferramenta deterministica simples resolver o caso.

### Referência rápida
Entrada: pacote minimo. Saida: facts, riscos, lacunas e next_step. Parada: uma rodada.

### Red flags
Sem fonte, contexto inteiro retransmitido, afirmacao sem evidence_ref ou mutacao sem aprovacao.
