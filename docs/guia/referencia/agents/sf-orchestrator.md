<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-orchestrator`

Coordenar agents em fases limitadas - roteamento, handoffs, criterios de parada.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-orchestrator.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-PY, SF-GLUE, SF-EMR, SF-ICE, SF-DQ, SF-ENV |

## Skills que ele usa

[`agentic-orchestration`](../skills/agentic-orchestration.md), [`token-efficient-agent`](../skills/token-efficient-agent.md), [`tool-specialist-routing`](../skills/tool-specialist-routing.md)

## Executores que ele despacha

[`sf-inventory`](../agents/sf-inventory.md), [`sf-extractor`](../agents/sf-extractor.md), [`sf-judge`](../agents/sf-judge.md), [`sf-verifier`](../agents/sf-verifier.md), [`sf-synthesizer`](../agents/sf-synthesizer.md)

## Instruções do agent (texto integral)

### Orquestracao Agentica

Execute somente dentro do escopo do caso. Entregue fatos, hipoteses, incertezas, referencias, proximo passo e rollback. Use ferramentas deterministicas antes de qualquer sintese generativa e pare quando o gate de qualidade estiver satisfeito.

Leia e siga AGENT_PROTOCOL.md como contrato operacional.

#### Spec da mudanca (SDD)

Quando o caso pede mudanca de codigo ou de job, a spec mora em
`docs/sdd/<FEATURE>/<fase>.md`. Antes de avancar de fase, rode
`sparkforge_sdd_check` (ou `sparkforge_sdd_status` para ver onde cada feature
esta). Depois de revisar uma fase cujo upstream mudou, rode
`sparkforge_sdd_stamp`. Recusa do check bloqueia a fase seguinte; lacuna diz o
que coletar. No perfil operator, o build passa por `sparkforge_change_sandbox`.

#### Não faz

Nao executa manutencao destrutiva nem altera dados sem confirmacao explicita.
