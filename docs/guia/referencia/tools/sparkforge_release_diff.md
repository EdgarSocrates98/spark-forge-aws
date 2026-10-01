<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_release_diff`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

O que muda de COMPONENTE entre duas releases, cada lado dado por um par (plataforma, release). Le matriz de versao; NAO avalia compatibilidade e NAO diz se algo quebra -- essa pergunta e do `sparkforge_migration_assess`. O EIXO SAI DECLARADO em `axis`, e ele e resultado e nao entrada: `release` quando so a release varia, `platform` quando o mesmo rotulo e comparado entre duas plataformas (`emr-7.7.0` no EC2 contra o EKS publica Iceberg minor DIFERENTE), os dois quando os dois variam, e vazio quando nada varia. COM OS DOIS EIXOS VARIANDO ELE RECUSA A ATRIBUICAO por nome (`unresolved.attribution`): nenhuma linha de `changed` pode ser creditada a release ou a plataforma isoladamente, e o que destrava sao dois diffs de um eixo cada. CINCO DAS SETE DIMENSOES SAEM EM `unresolved` COM A RAZAO -- `deprecated`, `default_changes`, `compatibility_changes`, `security_changes` e `performance_changes` --, porque as matrizes sustentam versao de componente e nada mais; lista vazia seria lida como 'nao mudou nada'. So `added` e `removed` tem lastro, e eles medem a PRESENCA DA CELULA, nao 'a plataforma passou a embarcar'. Componente que UMA DAS DUAS plataformas nao publica como eixo nunca vira `added` nem `removed`: sai em `unresolved` com a chave `component.<nome>`, para a saida nao afirmar que 'o EKS removeu o Hadoop' quando a fonte do EKS nunca o publicou.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `left_platform` | string: `glue`, `emr_ec2`, `emr_serverless`, `emr_eks` | sim | Plataforma do lado de ONDE o operador sai. |
| `left_release` | string | sim | Release do lado de ONDE o operador sai. |
| `right_platform` | string: `glue`, `emr_ec2`, `emr_serverless`, `emr_eks` | sim | Plataforma do lado PARA ONDE o operador vai. |
| `right_release` | string | sim | Release do lado PARA ONDE o operador vai. |

## Na CLI

[`sparkforge release diff`](../cli/release.md)

## Capacidade

diff component versions between two runtime releases

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
