<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `design-realtime-data-architecture`

Use quando houver requisitos de workload streaming e for necessário comparar candidatos por constraints, preservando assumptions, unresolved e ADR sem fabricar vencedor.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/design-realtime-data-architecture/SKILL.md` |
| `metadata` | {'sparkforge_contract': 'v1', 'evals': 'evals/evals.json', 'references': ['../_shared/references/evidence-first.md', '../_shared/references/evaluation-contract.md', '../_shared/references/operational-safety.md', '../../knowledge/streaming-realtime-candidate-matrix.md']} |
| `primary_verbs` | sparkforge architecture streaming |
| `subagent` | True |

## Procedimento (texto integral)

## Design Realtime Data Architecture

Use JSON offline para separar requisitos declarados de premissas e executar a
matriz de candidatos:

```bash
sparkforge architecture streaming \
  --path workload-requirements.json \
  --out streaming-architecture.json
```

### Procedimento

1. Exija `requirements` para constraints operacionais: source, sink, state,
   `foreachBatch`, output mode, API e managed-only.
2. Registre `assumptions` separadamente. Nunca use hipótese como prova.
3. Leia `candidate_matrix`, `constraint_elimination` e `unresolved` antes do
   ADR.
4. Aceite `selected` somente quando exatamente um candidato permanecer
   suportado por constraints factuais.
5. Se houver empate, latência/custo não medidos ou requisitos ausentes,
   mantenha ADR `unresolved` e liste o artefato ou experimento que destrava.

### Limites

- `supported` significa somente "não eliminado pelas constraints fornecidas";
- a matriz não mede benchmark, custo, throughput, SLO ou disponibilidade;
- nenhum serviço é alterado e nenhuma infraestrutura é provisionada;
- a decisão exige validação de runtime, contrato, replay, segurança e rollback.
