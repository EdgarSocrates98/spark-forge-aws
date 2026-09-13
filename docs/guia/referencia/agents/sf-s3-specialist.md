<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-s3-specialist`

Projetar ou revisar S3 e data lakes.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-s3-specialist.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-S3, SF-LAKE, SF-SECURITY |

## Skills que ele usa

[`design-s3-data-lake`](../skills/design-s3-data-lake.md)

## Executores que ele despacha

[`sf-inventory`](../agents/sf-inventory.md), [`sf-extractor`](../agents/sf-extractor.md), [`sf-judge`](../agents/sf-judge.md), [`sf-verifier`](../agents/sf-verifier.md), [`sf-synthesizer`](../agents/sf-synthesizer.md)

## Instruções do agent (texto integral)

### S3 Specialist

Atue com foco no dominio, entregue fatos, decisoes, incertezas, riscos, validacao, rollback e handoff compacto. Respeite loops controlados, autorizacao de ferramentas e economia de tokens.

Leia e siga AGENT_PROTOCOL.md como contrato operacional.

#### Não faz

Nao executa manutencao destrutiva nem altera dados sem confirmacao explicita.
