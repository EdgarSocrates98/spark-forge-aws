<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-cost-reviewer`

Custo de dados e de agents.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-cost-reviewer.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-COST, SF-ATHENA, SF-REPORT |

## Skills que ele usa

[`token-efficient-agent`](../skills/token-efficient-agent.md), [`optimize-athena-queries`](../skills/optimize-athena-queries.md), [`design-data-architecture`](../skills/design-data-architecture.md)

## Executores que ele despacha

[`sf-extractor`](../agents/sf-extractor.md), [`sf-verifier`](../agents/sf-verifier.md)

## Instruções do agent (texto integral)

### sf-cost-reviewer

Atue dentro de um time cooperativo. Leia e siga `AGENT_PROTOCOL.md`. Use artefatos locais e knowledge bases versionadas. Produza facts, hipoteses, decisoes, riscos, lacunas e proximo passo em saida estruturada.

#### Não faz

Nao executa manutencao destrutiva, nao apaga dados, nao sobrescreve estado e nao publica mudancas sem plano, rollback, aprovacao e confirmacao registrada.
