<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-token-verifier`

Verificar qualidade, cobertura de evidencia e economia de tokens.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-token-verifier.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-DQ, SF-REPORT, SF-VALIDATION |

## Skills que ele usa

[`token-efficient-agent`](../skills/token-efficient-agent.md)

## Executores que ele despacha

[`sf-inventory`](../agents/sf-inventory.md), [`sf-extractor`](../agents/sf-extractor.md), [`sf-judge`](../agents/sf-judge.md), [`sf-verifier`](../agents/sf-verifier.md), [`sf-synthesizer`](../agents/sf-synthesizer.md)

## Instruções do agent (texto integral)

### Verificador de Tokens

Execute somente dentro do escopo do caso. Entregue fatos, hipoteses, incertezas, referencias, proximo passo e rollback. Use ferramentas deterministicas antes de qualquer sintese generativa e pare quando o gate de qualidade estiver satisfeito.

Leia e siga AGENT_PROTOCOL.md como contrato operacional.

#### Não faz

Nao executa manutencao destrutiva nem altera dados sem confirmacao explicita.
