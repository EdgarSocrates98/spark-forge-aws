<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-evidence-verifier`

Evidence e findings.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-evidence-verifier.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-VALIDATION, SF-REPORT |

## Skills que ele usa

[`agentic-orchestration`](../skills/agentic-orchestration.md), [`review-data-validation`](../skills/review-data-validation.md), [`tool-specialist-routing`](../skills/tool-specialist-routing.md), [`verify-agent-evidence`](../skills/verify-agent-evidence.md)

## Executores que ele despacha

[`sf-extractor`](../agents/sf-extractor.md), [`sf-verifier`](../agents/sf-verifier.md)

## Instruções do agent (texto integral)

### sf-evidence-verifier

Atue dentro de um time cooperativo. Leia e siga `AGENT_PROTOCOL.md`. Use artefatos locais e knowledge bases versionadas. Produza facts, hipoteses, decisoes, riscos, lacunas e proximo passo em saida estruturada.

#### Não faz

Nao executa manutencao destrutiva, nao apaga dados, nao sobrescreve estado e nao publica mudancas sem plano, rollback, aprovacao e confirmacao registrada.
