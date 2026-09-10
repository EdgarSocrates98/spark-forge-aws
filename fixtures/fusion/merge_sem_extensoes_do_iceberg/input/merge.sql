-- MERGE INTO e uma das TRES operacoes que a tabela de suporte do Apache Iceberg
-- marca com "Requires Iceberg Spark extensions". As outras duas sao UPDATE e
-- DELETE FROM row-level; INSERT INTO e INSERT OVERWRITE nao estao na lista.
MERGE INTO curated.fato_venda AS destino
USING (SELECT id, valor, dt FROM stage.venda_novos WHERE dt = '2026-09-09') AS origem
ON destino.id = origem.id
WHEN MATCHED THEN UPDATE SET destino.valor = origem.valor
WHEN NOT MATCHED THEN INSERT (id, valor, dt) VALUES (origem.id, origem.valor, origem.dt)
