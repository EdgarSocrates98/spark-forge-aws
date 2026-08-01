# Matriz de runtime Amazon EMR on EC2

Confirme sempre contra o runtime **efetivo** do cluster. Esta tabela orienta; não substitui a aba *Environment* do Spark UI, o `describe-cluster` do cluster analisado, nem as release notes da release label.

O espelho executável desta página é `EMR_MATRIX`, em [`../../sparkforge/facts/runtime_detect.py`](../../sparkforge/facts/runtime_detect.py). Divergir entre os dois é bug de dado, e `tests/test_runtime_emr_matrix.py` falha quando acontece.

## 1. O que a coluna `-amzn-N` significa, e por que ela importa aqui

A AWS não embarca o artefato da Apache: embarca um fork com patches próprios, versionado como `{VersãoComunidade}-amzn-{VersãoEMR}`. `3.5.6-amzn-2` é o Spark 3.5.6 da Apache com o terceiro conjunto de patches da AWS aplicado.

Duas consequências, e a segunda já causou defeito neste repositório:

1. **O sufixo é informação real e não é descartado.** Um cluster rodando `3.3.2-amzn-0.1` não roda o mesmo binário que um `3.3.2` da Apache; esconder isso do relatório esconderia a única pista de um `NoSuchMethodError` que só existe no fork. O valor cru sobrevive em `RuntimeContext.spark` e em `attrs.observed` do fact `env.runtime_signal`.
2. **Toda comparação de `runtime_scope` é contra versão Apache.** `sparkforge/rules/version_scope.py` compara truncando no primeiro segmento com sufixo de vendor. Isso já funcionava para a forma de um nível (`3.5.6-amzn-2` → `3.5.6`), mas **falhava** para a forma de dois níveis que só existe em EMR 6.x: `3.3.2-amzn-0.1` era lido como `3.3.2.0.1`, maior que `3.3.2`, e `== 3.3.2` dava falso. Quatro releases usam essa forma — 6.8.1, 6.9.1, 6.10.1, 6.11.1 — e nelas toda regra com range exato era pulada em silêncio. Corrigido na mesma entrega desta matriz.

## 2. Matriz 7.x

| Release | Spark | Hadoop | Iceberg | Python instalado | Python do PySpark |
|---|---|---|---|---|---|
| emr-7.13.0 | 3.5.6-amzn-2 | 3.4.2-amzn-0 | 1.10.0-amzn-1 | 3.9, 3.11 | 3.11 |
| emr-7.12.0 | 3.5.6-amzn-1 | 3.4.1-amzn-4 | 1.10.0-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.11.0 | 3.5.6-amzn-0 | 3.4.1-amzn-3 | 1.9.1-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.10.0 | 3.5.5-amzn-1 | 3.4.1-amzn-2 | 1.8.1-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.9.0 | 3.5.5-amzn-0 | 3.4.1-amzn-1 | 1.7.1-amzn-2 | 3.9, 3.11 | 3.9 |
| emr-7.8.0 | 3.5.4-amzn-0 | 3.4.1-amzn-0 | 1.7.1-amzn-1 | 3.9, 3.11 | 3.9 |
| emr-7.7.0 | 3.5.3-amzn-1 | 3.4.0-amzn-3 | 1.7.1-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.6.0 | 3.5.3-amzn-0 | 3.4.0-amzn-2 | 1.6.1-amzn-2 | 3.9, 3.11 | 3.9 |
| emr-7.5.0 | 3.5.2-amzn-1 | 3.4.0-amzn-1 | 1.6.1-amzn-1 | 3.9, 3.11 | 3.9 |
| emr-7.4.0 | 3.5.2-amzn-0 | 3.4.0-amzn-0 | 1.6.1-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.3.0 | 3.5.1-amzn-1 | 3.3.6-amzn-5 | 1.5.2-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.2.0 | 3.5.1-amzn-0 | 3.3.6-amzn-4 | 1.5.0-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.1.0 | 3.5.0-amzn-1 | 3.3.6-amzn-3 | 1.4.3-amzn-0 | 3.9, 3.11 | 3.9 |
| emr-7.0.0 | 3.5.0-amzn-0 | 3.3.6-amzn-2 | 1.4.2-amzn-0 | 3.9 | 3.9 |

## 3. Matriz 6.x

| Release | Spark | Hadoop | Iceberg | Python instalado | Python do PySpark |
|---|---|---|---|---|---|
| emr-6.15.0 | 3.4.1-amzn-2 | 3.3.6-amzn-1 | 1.4.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.14.0 | 3.4.1-amzn-1 | 3.3.3-amzn-6 | 1.3.1-amzn-0 | 2.7, 3.7 | — |
| emr-6.13.0 | 3.4.1-amzn-0 | 3.3.3-amzn-5 | 1.3.0-amzn-1 | 2.7, 3.7 | — |
| emr-6.12.0 | 3.4.0-amzn-0 | 3.3.3-amzn-4 | 1.3.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.11.1 | 3.3.2-amzn-0.1 | 3.3.3-amzn-3.1 | 1.2.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.11.0 | 3.3.2-amzn-0 | 3.3.3-amzn-3 | 1.2.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.10.1 | 3.3.1-amzn-0.1 | 3.3.3-amzn-2.1 | 1.1.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.10.0 | 3.3.1-amzn-0 | 3.3.3-amzn-2 | 1.1.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.9.1 | 3.3.0-amzn-1.1 | 3.3.3-amzn-1.1 | 0.14.1-amzn-0 | 2.7, 3.7 | — |
| emr-6.9.0 | 3.3.0-amzn-1 | 3.3.3-amzn-1 | 0.14.1-amzn-0 | 2.7, 3.7 | — |
| emr-6.8.1 | 3.3.0-amzn-0.1 | 3.2.1-amzn-8.1 | 0.14.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.8.0 | 3.3.0-amzn-0 | 3.2.1-amzn-8 | 0.14.0-amzn-0 | 2.7, 3.7 | — |
| emr-6.7.0 | 3.2.1-amzn-0 | 3.2.1-amzn-7 | 0.13.1-amzn-0 | 2.7, 3.7 | — |
| emr-6.6.0 | 3.2.0-amzn-0 | 3.2.1-amzn-6 | 0.13.1 | 2.7, 3.7 | — |
| emr-6.5.0 | 3.1.2-amzn-1 | 3.2.1-amzn-5 | 0.12.0 | 2.7, 3.7 | — |
| emr-6.4.0 | 3.1.2-amzn-0 | 3.2.1-amzn-4 | — | 2.7, 3.7 | — |

**Limite inferior da matriz.** A página oficial de 6.x vai até `emr-6.0.0`. A matriz para em `emr-6.4.0` porque `emr-6.3.1` e anteriores não têm Iceberg **nem** Spark ≥ 3.2 — não há regra do catálogo cuja aplicabilidade mude entre elas. Acrescentar linhas abaixo de 6.4.0 é acrescentar dado sem consumidor.

## 4. As quatro coisas que esta matriz tem e a de Glue não

### 4.1 Python é conjunto, não valor

A coluna `Python` da página oficial lista os interpretadores **instalados**, não o que o PySpark executa. Em 7.x são dois (`3.9, 3.11`); em 6.x são dois (`2.7, 3.7`). A `GLUE_MATRIX` declara um Python por release porque no Glue só há um.

Qual deles o PySpark usa é decidido por `PYSPARK_PYTHON`, na classificação `spark-env`. A AWS documenta o default **por release** só onde ele mudou:

> **Python 3.11 default for PySpark and Spark workloads** — Python 3.11 is now the default Python version for PySpark and Spark workloads. Python 3.9 remains the default for all other applications. Both Python 3.9 and 3.11 are included in the release.
> — release notes de `emr-7.13.0`

Daí a coluna `Python do PySpark`: `3.11` em 7.13.0, `3.9` em 7.0.0–7.12.0 (Python 3.9 é o default de sistema desde 7.0.0, e a nota acima data a virada), e **vazio em toda a série 6.x**, onde a AWS não reafirma o default do PySpark release a release.

Consequência no motor: a matriz resolve `python` para 7.x e **não resolve para 6.x**. Num cluster 6.x sem `PYSPARK_PYTHON` observado, `RuntimeContext.python` fica vazio e toda regra com `python` em `runtime_scope` é pulada por ausência — falha fechada, que é a semântica do projeto para "não detectada". Escolher `3.7` porque é o maior da lista seria inventar; hoje nenhuma regra do catálogo tem `python` em `runtime_scope`, então a escolha não custa cobertura nenhuma.

**Armadilha operacional em 7.13.0**, e ela já apareceu em campo: o `pip3` do bootstrap continua apontando para o site-packages do 3.9 enquanto Spark e YARN rodam 3.11. Pacote instalado no bootstrap não é visto pelo executor, e o sintoma é `ModuleNotFoundError` de biblioteca que "foi instalada".

### 4.2 Iceberg não existe antes de 6.5.0

A célula de `emr-6.4.0` é vazia na página oficial, e a matriz **omite a chave** em vez de guardar `"0.0.0"` ou `""`. `in_scope` reprova chave ausente e reprova valor vazio da mesma forma, mas as duas grafias mentem: `"0.0.0"` afirma uma versão que não existe, e `""` afirma uma leitura que não aconteceu. Regra `SF-ICE-*` em 6.4.0 é pulada por **ausência de Iceberg**, não por range.

### 4.3 Observação direta vence a matriz

`Cluster.Applications[].Version` vem populado no dump de `describe-cluster`: ali a AWS **observou** o que instalou. A matriz é fallback (quando só o release label é conhecido) e guard de drift (quando os dois existem e discordam).

Por isso `describe_cluster` entra em `_PRECEDENCE` **abaixo de `event_log`** — só o event log observou o *run* sob análise — e **acima de `cli`/`terraform`/`requirements`, que são declaração sem artefato. A derivação por matriz continua marcada com o sufixo `:matrix` na origem, e perde para qualquer leitura direta.

### 4.4 Duas plataformas não produzem divergência de versão

Quando Glue e EMR são detectados juntos, as duas matrizes derivam valores para o mesmo componente e eles quase sempre discordam — não há release de EMR que case com Glue 4.0 em Spark **e** Iceberg ao mesmo tempo. Contar isso como divergência de versão reportaria a *consequência* de um defeito com o remédio errado ("alinhe o Terraform à versão efetiva"), quando o remédio é remover o artefato que não é deste job.

Por isso `distinct_versions` é contado **por plataforma**: as derivações de cada plataforma são comparadas contra as observações diretas e contra as derivações da mesma plataforma, nunca contra as da outra. Multiplicidade de plataforma tem regra própria — `SF-ENV-005`, também P0. Observação direta nunca é excluída dessa contagem: `attrs.observed` continua listando tudo que foi lido, cru.

## 5. Como manter esta matriz

A forma correta de **manter** não é reler o HTML:

```
aws emr describe-release-label --release-label emr-7.13.0
```

devolve a mesma informação com contrato de API em vez de tabela HTML. Isso não viola "entrada é artefato local": o extrator do SparkForge segue sem rede, e só a manutenção humana desta página usa a API. A URL citada em `sources` continua sendo a página da documentação, que é o que um auditor consegue abrir.

## 6. Perfis de drift opostos das duas páginas

As duas páginas oficiais são vigiadas por `knowledge/sources.lock.json` via `scripts/refresh_knowledge.py`, mas o que um alarme significa é diferente em cada uma:

| Página | Perfil | O que um alarme significa |
|---|---|---|
| 6.x | **Estável.** A série não recebe minors novos; o último é `emr-6.15.0`. | Mudança na página é o evento que a watchlist existe para pegar. Reler. |
| 7.x | **Churn estrutural garantido.** A AWS se compromete a lançar um minor a cada 90 dias no máximo, e cada minor **prepende uma coluna** à tabela. | O hash muda ~4×/ano sem que nada que a matriz conhece tenha mudado. Alarme esperado; conferir se alguma célula existente mudou antes de gastar leitura. |

Por isso o guard de drift do repositório **não** é o hash para 7.x. `tests/test_runtime_emr_matrix.py` compara célula a célula as releases que `EMR_MATRIX` já conhece:

- **6.x**: o conjunto de releases da tabela e o do `EMR_MATRIX` têm que ser **idênticos**. Linha nova ou removida é falha.
- **7.x**: toda release do `EMR_MATRIX` tem que casar célula a célula. Release presente na tabela e **ausente** do `EMR_MATRIX` não é falha — é `UserWarning` dizendo "matriz desatualizada, considere acrescentar". Célula existente alterada é drift, e falha.

## Fontes

- Application versions in Amazon EMR 7.x releases. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-release-app-versions-7.x.html (retrieved 2026-08-01)
- Application versions in Amazon EMR 6.x releases. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-release-app-versions-6.x.html (retrieved 2026-08-01)
- Amazon EMR release 7.13.0 — release notes (default do Python para PySpark). https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-7130-release.html (retrieved 2026-08-01)
- Todas as células das seções 2 e 3 foram conferidas contra as duas páginas de *Application versions* em 2026-08-01, uma a uma. Nenhuma divergiu.
- O default do PySpark para a série 6.x **não** foi encontrado declarado por release na documentação oficial. A coluna fica vazia de propósito; não inferir.
