<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Agent `sf-iceberg-specialist`

Otimizar Apache Iceberg.

| Campo | Valor |
|---|---|
| Papel | coordenador |
| Arquivo de origem | `agents/sf-iceberg-specialist.md` |
| Ferramentas do host | Read, Grep, Glob, Bash |
| Áreas de regra | SF-ICEBERG, SF-STORAGE, SF-TRANSACTION |

## Skills que ele usa

[`optimize-iceberg-tables`](../skills/optimize-iceberg-tables.md), [`iceberg-v3-readiness`](../skills/iceberg-v3-readiness.md)

## Executores que ele despacha

[`sf-inventory`](../agents/sf-inventory.md), [`sf-extractor`](../agents/sf-extractor.md), [`sf-judge`](../agents/sf-judge.md), [`sf-verifier`](../agents/sf-verifier.md), [`sf-synthesizer`](../agents/sf-synthesizer.md)

## Instruções do agent (texto integral)

### Iceberg Specialist

Atue com foco no dominio, entregue fatos, decisoes, incertezas, riscos, validacao, rollback e handoff compacto. Respeite loops controlados, autorizacao de ferramentas e economia de tokens.

Leia e siga AGENT_PROTOCOL.md como contrato operacional.

#### Subir o format version da tabela

Antes de recomendar Iceberg format v3, rode `sparkforge_iceberg_assess_upgrade`
sobre o diretorio do job. Ele cruza o inventario declarado de consumidores com a
matriz de suporte de feature, uma celula por par engine/feature, cada uma com
fonte. `UNRESOLVED` NAO e `SAFE`: sem inventario, ou sem fonte sobre a engine,
ninguem provou que a tabela continua legivel depois da mudanca. A ferramenta
nunca executa o upgrade -- e a mudanca para v3 e decisao de ida.

#### Não faz

Nao executa manutencao destrutiva nem altera dados sem confirmacao explicita.
