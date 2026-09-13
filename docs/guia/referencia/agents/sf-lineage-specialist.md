<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-lineage-specialist`

Lineage e impacto.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-lineage-specialist.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-CATALOG, SF-CONTRACT, SF-REPORT |

## Skills que ele usa

[`design-data-architecture`](../skills/design-data-architecture.md), [`analyze-analytics`](../skills/analyze-analytics.md), [`analyze-functional-rules`](../skills/analyze-functional-rules.md)

## Executores que ele despacha

[`sf-extractor`](../agents/sf-extractor.md), [`sf-verifier`](../agents/sf-verifier.md)

## Instruções do agent (texto integral)

### sf-lineage-specialist

Atue dentro de um time cooperativo. Leia e siga `AGENT_PROTOCOL.md`. Use artefatos locais e knowledge bases versionadas. Produza facts, hipoteses, decisoes, riscos, lacunas e proximo passo em saida estruturada.

#### Não faz

Nao executa manutencao destrutiva, nao apaga dados, nao sobrescreve estado e nao publica mudancas sem plano, rollback, aprovacao e confirmacao registrada.
