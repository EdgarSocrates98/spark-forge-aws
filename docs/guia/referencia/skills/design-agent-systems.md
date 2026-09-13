<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `design-agent-systems`

Use quando for necessario criar agents, skills, loops, handoffs e avaliacao.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/design-agent-systems/SKILL.md` |

## Procedimento (texto integral)

## Agent Systems

Declare contrato, especialidade, ferramentas, memoria minima, loop controlado, orcamento, parada, autorizacao e avaliacao.

### Quando NAO usar

Nao use quando o problema estiver fora do escopo.

### Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e rollback.

### Red flags

Loop sem parada, evidencia ausente, risco nao autorizado, custo nao medido e rollback inexistente.

### Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
### Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

### Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.
