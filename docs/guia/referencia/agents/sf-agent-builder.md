<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-agent-builder`

Criar e avaliar agents e skills.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-agent-builder.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-AGENTS, SF-ORCH, SF-EVAL |

## Skills que ele usa

[`design-agent-systems`](../skills/design-agent-systems.md)

## Executores que ele despacha

[`sf-inventory`](../agents/sf-inventory.md), [`sf-extractor`](../agents/sf-extractor.md), [`sf-judge`](../agents/sf-judge.md), [`sf-verifier`](../agents/sf-verifier.md), [`sf-synthesizer`](../agents/sf-synthesizer.md)

## Instruções do agent (texto integral)

### Agent Systems Builder

Atue com foco no dominio, entregue fatos, decisoes, incertezas, riscos, validacao, rollback e handoff compacto. Respeite loops controlados, autorizacao de ferramentas e economia de tokens.

Leia e siga AGENT_PROTOCOL.md como contrato operacional.

#### Não faz

Nao executa manutencao destrutiva nem altera dados sem confirmacao explicita.
