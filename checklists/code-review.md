# Checklist de revisão PySpark

## Leitura

- [ ] Projection pruning explícito.
- [ ] Predicate pushdown possível.
- [ ] Filtros aplicados cedo.
- [ ] Schema controlado.
- [ ] Evita listar/ler objetos desnecessários.
- [ ] Partition pruning confirmado no plano.

## Transformações

- [ ] Funções nativas em vez de Python UDF.
- [ ] Sem actions para logging.
- [ ] Sem loops que montam planos gigantes.
- [ ] Cardinalidade de `explode`, joins e unions estimada.
- [ ] Agregação parcial/pré-agregação considerada.

## Joins

- [ ] Colunas reduzidas antes do join.
- [ ] Estatísticas/tamanho dos lados conhecidos.
- [ ] Estratégia física confirmada.
- [ ] Skew analisado.
- [ ] Chaves nulas e hot keys tratadas semanticamente.
- [ ] Broadcast cabe com margem na memória.

## Partições e shuffle

- [ ] Partições baseadas em volume e paralelismo.
- [ ] Sem `coalesce(1)`.
- [ ] Sem repartition redundante.
- [ ] AQE considerado.
- [ ] Tasks não são excessivamente pequenas/grandes.

## Persistência

- [ ] Dataset é reutilizado.
- [ ] StorageLevel adequado.
- [ ] Benefício maior que custo.
- [ ] `unpersist()` presente.

## Escrita

- [ ] Quantidade de arquivos estimada.
- [ ] Particionamento atende padrões de consulta.
- [ ] Não cria diretórios/chaves de alta cardinalidade.
- [ ] Estratégia Iceberg condiz com append/merge/delete.
- [ ] Manutenção é planejada, não improvisada.

## Correção

- [ ] Contagem.
- [ ] Schema.
- [ ] Chaves e duplicidades.
- [ ] Agregados de controle.
- [ ] Regras de negócio.
- [ ] Snapshot/partições corretos.
