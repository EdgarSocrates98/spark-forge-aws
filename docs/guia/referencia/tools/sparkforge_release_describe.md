<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_release_describe`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

O que uma release E, segundo a fonte DAQUELA plataforma e so ela: cada componente com versao, as fontes e a data de leitura. Le as quatro matrizes de `knowledge/` -- nao le artefato do operador, nao chama AWS e NAO JULGA. A FRONTEIRA, e ela vem antes da capacidade: o descritor afirma o que aquela fonte PUBLICA, e as quatro publicam conjuntos DIFERENTES. Componente que a fonte nao publica sai em `unresolved` NOMEADO -- nunca string vazia, nunca chave ausente em silencio, que o leitor confundiria com 'nao tem'. `unresolved_detail` diz de qual das DUAS recusas se trata, porque elas destravam com medidas diferentes: `platform_source_does_not_publish` (a fonte nao publica aquele eixo em release NENHUMA -- `hadoop` no EMR on EKS, 0 de 34 paginas) destrava com uma FONTE nova; `release_cell_absent` (a fonte publica o eixo e a celula DAQUELA release nao esta la -- `iceberg` em `emr-6.4.0`, `java` em Glue 5.1) destrava com uma LEITURA daquela pagina. Nenhum valor e herdado de outra plataforma: o mesmo `emr-7.7.0` publica Iceberg `1.7.1-amzn-0` no EC2 e `1.6.1-amzn-2` no EKS. `release` sai como a matriz o indexa, uma grafia so.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `platform` | string: `glue`, `emr_ec2`, `emr_serverless`, `emr_eks` | sim | Uma das quatro plataformas que este motor conhece. |
| `release` | string | sim | O rotulo da release, com ou sem o prefixo `emr-` (`7.7.0`, `emr-7.7.0`, `5.1`). A saida emite UMA grafia. |

## Na CLI

[`sparkforge release describe`](../cli/release.md)

## Capacidade

describe what a runtime release publishes, and what it does not

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
