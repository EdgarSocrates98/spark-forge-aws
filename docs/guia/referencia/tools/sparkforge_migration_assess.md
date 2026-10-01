<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_migration_assess`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Julga a migracao de um job entre um par de versoes com o catalogo versionado (`SF-MIG`, `SF-SPARK4`, `SF-LF`), uma vez por DEGRAU do caminho -- 4.0 para 6.0 passa por 5.0 e 5.1, porque os breaking changes se acumulam e um salto esconde os do meio. Entrada: o diretorio do job (codigo, `requirements*.txt` e `.jar`) ou um arquivo `.py`; o diretorio e o caso que interessa, porque um pin de dependencia e um binario Scala nao tem linha de fonte Python e sobrevivem a troca de runtime. `source` e `target` nao tem default: um par embutido responderia sobre um alvo que ninguem declarou. `platform` aceita as QUATRO (`glue`, `emr_ec2`, `emr_serverless`, `emr_eks`) e tem default `glue`; a ordem das releases e o runtime de cada degrau vem da matriz DAQUELA plataforma, nunca de outra -- a de EC2 nao descreve EKS nem Serverless, e elas divergem em celulas reais. Devolve `findings` (cardinalidade por degrau), `report` (cada problema uma vez, com os degraus em que vale), `gates`, `missing_evidence`, `component_diff` (o que muda de componente por degrau, do `ReleaseDiff`) e `coverage`. LEIA `coverage.statement` ANTES de concluir qualquer coisa de um assessment sem achado: o catalogo tem ZERO regras guardadas por versao de EMR, entao um caminho de EMR avalia Spark e componente e NAO avalia breaking change de plataforma -- sem esse campo, 'nenhum achado' e indistinguivel de 'nada quebra'. Compoe o job inteiro: codigo, `.tf` quando existe (sem ele a area `SF-LF` fica sem produtor, porque a topologia de FGAC e declarada no Terraform) e o inventario de consumidores em `.sparkforge/consumers.yaml`. Todo eixo sem evidencia nasce BLOCKED com o motivo, nunca PASS.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Diretorio do job, ou um arquivo .py. |
| `source` | string | sim | Release de origem, na matriz da plataforma. Aceita as duas grafias que a fonte publica (`emr-7.5.0` e `7.5.0`) e emite uma. |
| `target` | string | sim | Release alvo, mesma convencao de `source`. |
| `platform` | string: `glue`, `emr_ec2`, `emr_serverless`, `emr_eks`, `controlm` | não | Qual matriz ordena o caminho. As QUATRO de Spark (`glue`, `emr_ec2`, `emr_serverless`, `emr_eks`) fornecem o runtime de cada degrau e julgam por `runtime_scope`. `controlm` e a QUINTA e responde por outro eixo: nao runtime, mas CAPACIDADE com fronteira declarada (`introduced_in`, `changed_in`, `deprecated_from`, `discontinued_in`), e por isso a saida dela traz `steps[].changes` e `breaking` em vez de `findings`. Ela tambem aceita migracao PARA TRAS, que as outras recusam -- descer de versao e onde `introduced_in` morde. Default `glue`, que era a unica resposta possivel antes desta extensao. |

## Na CLI

[`sparkforge migrate controlm`](../cli/migrate.md), [`sparkforge migrate emr`](../cli/migrate.md), [`sparkforge migrate glue`](../cli/migrate.md)

## Capacidade

assess a runtime version migration step by step, on any of the four platforms

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
