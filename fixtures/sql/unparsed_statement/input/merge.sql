-- A OPERACAO e a TABELA ALVO daqui SAO extraidas (`sql.write_statement`), por
-- parse ancorado no inicio do texto. O que NAO se extrai e o predicado: o filtro
-- deste MERGE mora no `ON`, e adivinhar dali produziria `sql.predicate` errado
-- sobre uma clausula que o extrator nao entende.
MERGE INTO glue_catalog.curated.pedidos AS destino
USING atualizacoes AS origem
ON destino.pedido_id = origem.pedido_id
WHEN MATCHED THEN UPDATE SET destino.status = origem.status
WHEN NOT MATCHED THEN INSERT *
