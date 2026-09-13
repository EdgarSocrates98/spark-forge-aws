<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_iceberg_assess_upgrade`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Avalia subir o format version de uma tabela Iceberg CONTRA quem a consome. Cruza o inventario declarado (`env.consumer`, na convencao `.sparkforge/consumers.yaml`) com a matriz de suporte de feature (`knowledge/storage/iceberg-feature-support.yaml`), uma celula por par engine/feature, cada uma com fonte. NUNCA executa o upgrade: o modulo por tras nao importa cliente de AWS nem Spark. Veredito em vocabulario fechado -- BLOCKED quando ha fonte dizendo que uma engine nao le; UNRESOLVED quando falta fonte, INCLUSIVE quando nao ha inventario nenhum, porque ausencia de declaracao nao e declaracao de ausencia; CONDITIONAL quando o suporte e parcial; SAFE so quando toda celula consultada e afirmativa.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Diretorio do job, com o inventario em `.sparkforge/consumers.yaml`. Cada consumidor aceita um `release:` OPCIONAL (`emr-7.7.0`): com ele, a resposta cruza a versao de Iceberg daquela release com o minimo de biblioteca da feature, e por isso `emr_ec2` e `emr_eks` respondem DIFERENTE na mesma release, como as fontes dizem que respondem. Sem ele, a resposta e a da engine sem recorte de versao -- mais fraca, e nao errada. |
| `source` | integer | sim | Format version de origem. |
| `target` | integer | sim | Format version alvo. |

## Na CLI

[`sparkforge iceberg assess-upgrade`](../cli/iceberg.md)

## Capacidade

assess an Iceberg format version upgrade against declared consumers

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
