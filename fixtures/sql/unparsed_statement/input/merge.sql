-- MERGE nao e SELECT: o extrator so reconhece a forma SELECT ... FROM.
-- Adivinhar tabela e predicado daqui produziria fact errado sobre uma query
-- que o parser nao entendeu.
MERGE INTO glue_catalog.curated.pedidos AS destino
USING atualizacoes AS origem
ON destino.pedido_id = origem.pedido_id
WHEN MATCHED THEN UPDATE SET destino.status = origem.status
WHEN NOT MATCHED THEN INSERT *
