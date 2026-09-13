<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `design-neptune-graph`

Use quando for necessario projetar Amazon Neptune, Gremlin, openCypher, RDF, indices, carga e alta disponibilidade.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/design-neptune-graph/SKILL.md` |

## Procedimento (texto integral)

## Amazon Neptune

Use a especialidade para coletar evidencias, comparar alternativas, validar custo, risco, testes e rollback.

### Quando NAO usar

Nao use quando o problema estiver fora do dominio declarado.

### Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e proxima acao.

### Red flags

Modelo sem access patterns, carga sem checkpoint, backup nao testado e IAM amplo.

### Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
### Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

### Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.
