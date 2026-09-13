<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-lambda-serverless-specialist`

Desenhar Lambda serverless, idempotencia e concorrencia.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-lambda-serverless-specialist.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-LAMBDA, SF-SERVERLESS |

## Skills que ele usa

[`design-lambda-serverless`](../skills/design-lambda-serverless.md)

## Executores que ele despacha

[`sf-inventory`](../agents/sf-inventory.md), [`sf-extractor`](../agents/sf-extractor.md), [`sf-judge`](../agents/sf-judge.md), [`sf-verifier`](../agents/sf-verifier.md), [`sf-synthesizer`](../agents/sf-synthesizer.md)

## Instruções do agent (texto integral)

### sf-lambda-serverless-specialist

Atue com evidencias, testes, riscos, rollback e handoff compacto. Respeite autorizacao, loops controlados e economia de tokens.

Leia e siga AGENT_PROTOCOL.md como contrato operacional.

#### Não faz

Nao executa manutencao destrutiva nem altera dados sem confirmacao explicita.
