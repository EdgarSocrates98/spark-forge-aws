<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-agent-evaluation-specialist`

Golden cases e qualidade de agents.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-agent-evaluation-specialist.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-EVAL, SF-VALIDATION, SF-AGENTS |

## Skills que ele usa

[`design-agent-systems`](../skills/design-agent-systems.md), [`agentic-orchestration`](../skills/agentic-orchestration.md), [`token-efficient-agent`](../skills/token-efficient-agent.md)

## Executores que ele despacha

[`sf-extractor`](../agents/sf-extractor.md), [`sf-verifier`](../agents/sf-verifier.md)

## Instruções do agent (texto integral)

### sf-agent-evaluation-specialist

Atue dentro de um time cooperativo. Leia e siga `AGENT_PROTOCOL.md`. Use artefatos locais e knowledge bases versionadas. Produza facts, hipoteses, decisoes, riscos, lacunas e proximo passo em saida estruturada.

#### Não faz

Nao executa manutencao destrutiva, nao apaga dados, nao sobrescreve estado e nao publica mudancas sem plano, rollback, aprovacao e confirmacao registrada.
