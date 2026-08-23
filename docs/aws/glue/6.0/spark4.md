# A fronteira do Spark 4

O Glue 6.0 é o empacotamento em que o Apache Spark 4 chega ao Glue. As duas coisas não são a
mesma, e a distinção decide onde cada regra é guardada.

Conhecimento completo, com as tabelas de nome antigo/novo, API removida/substituta e piso de
dependência, em
[`../../../../knowledge/spark/spark4-migration.md`](../../../../knowledge/spark/spark4-migration.md).
As versões exatas de Spark por runtime estão na matriz — ver [`runtime.md`](runtime.md).
Nenhuma delas é repetida aqui.

## Por que a área é `SF-SPARK4` e é guardada por Spark

`rules/catalog/spark4.yaml` declara a área **`SF-SPARK4`**, e cada regra dela usa
`runtime_scope` com chave `spark`, não `glue`.

Quem mudou o produto foi o Apache. As afirmações da área valem igual num cluster EMR com a
mesma versão de Spark, e guardá-las por versão de Glue amarraria a afirmação a um
empacotamento que não a produziu. `tests/test_rule_scope_by_nature.py` cobra essa escolha em
vez de deixá-la a critério de quem escreve a próxima regra.

A regra do ANSI mode é a exceção declarada: ela vive em `SF-MIG-003`, na área de migração de
Glue e guardada por versão de **Glue**, porque o que ela responde é "a partir de qual runtime
de Glue este `cast` sem guarda passa a estourar" — e essa fronteira é do empacotamento, não
do Apache. As duas leituras coexistem: o Apache ligou o ANSI numa versão de Spark; o usuário
de Glue cruza essa fronteira numa versão de Glue.

## O que é detectável estaticamente

Estas são as afirmações que um extrator de facts sustenta hoje, com o kind que as observa:

| Regra | O que o fact observa | Kind |
|---|---|---|
| `SF-SPARK4-001` | configuração do Spark que mudou de nome na versão 4, ainda escrita com o nome antigo | `mig.renamed_conf` |
| `SF-SPARK4-002` | API de pandas-on-Spark removida na versão 4 ainda chamada no código | `mig.removed_api` |
| `SF-SPARK4-003` | PyArrow pinado abaixo do piso declarado | `mig.python_dep` |
| `SF-SPARK4-004` | JAR cujo nome codifica Scala anterior ao 2.13 | `mig.jar_binary` |

Duas observações que mudam como o resultado deve ser lido:

**`SF-SPARK4-001` descreve silêncio, não erro.** A chave antiga não causa falha; ela
simplesmente não é lida. Quem lê o job vê uma configuração que parece ativa e não está. É a
mesma classe de defeito que `SF-MIG-002` descreve para a configuração de EMRFS.

**`SF-SPARK4-004` é a única P0 da área**, e é a única que descreve **falha certa**. A
fronteira entre Scala 2.12 e 2.13 é binária: não é API depreciada que roda com aviso, é
bytecode que não carrega. O limite do fact está declarado: ele observa todo `.jar` da árvore,
inclusive um que seja recurso de teste fora do classpath do job, e um JAR cujo nome **não**
codifica a versão de Scala não recebe o campo e não é acusado — ele pode ser Java puro, que
não tem versão de Scala nenhuma para estar errada.

Não existe tool MCP dedicada a varredura de Spark 4. `sparkforge_analyze_pyspark` seguido de
`sparkforge_judge` entrega o mesmo resultado sem superfície nova — ver
[`known-unknowns.md`](known-unknowns.md).

## O que só aparece em execução

A seção 5 de
[`../../../../knowledge/spark/spark4-migration.md`](../../../../knowledge/spark/spark4-migration.md)
lista as mudanças de comportamento **sem sinal no código**. Elas não estão lá por preguiça:
não há nada no job para um extrator observar. Um `SELECT` que produz um resultado diferente
não escreve no arquivo que produzirá um resultado diferente.

São, pelo nome do que muda e sem repetir os valores da fonte:

- política de parsing de tempo e precedência de CTE mudam de default;
- codec padrão do ORC muda;
- o teto de bytes de partição única deixa de ser efetivamente ilimitado;
- cast de timestamp com overflow fora do ANSI muda o que devolve;
- Storage-Partitioned Join passa a ligado por padrão.

**Consequência para quem migra:** estas não geram finding, e a ausência de finding sobre elas
não é ausência de risco. Elas são entrada para o **plano de regressão**, não para o relatório
de análise estática. O [`decision-guide.md`](decision-guide.md) as trata como checagem
manual, que é o que elas são.

Da mesma natureza, um degrau acima: a falha de um JAR de Scala 2.12 aparece em **runtime**,
não na submissão — a submissão não carrega classe nenhuma do JAR. Na prática ela chega na
primeira vez que aquele caminho de código executa, e passa em qualquer smoke test que não
exercite exatamente aquela chamada.

## Quando não há conserto local

Quando o JAR vem de terceiro e não existe build para 2.13, não há recompilação possível sem o
fonte. A migração está **bloqueada**, não atrasada, e confirmar isso com o mantenedor é
pré-requisito do plano — não tarefa dentro dele.
