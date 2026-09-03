-- Tabela Iceberg de TESTE, para validar o coletor contra artefato real.
--
-- POR QUE ESTE ARQUIVO EXISTE
--
-- As nove fixtures de `fixtures/iceberg/` sao SINTETICAS: o shape do dump que
-- `sparkforge/facts/iceberg_metadata.py` espera foi escrito a mao, e ninguem
-- nunca rodou `collect_iceberg_metadata` contra uma tabela de verdade para
-- conferir. Se o `SELECT *` do Athena devolver uma coluna a mais, uma a menos,
-- ou um tipo diferente, nada acusaria.
--
-- Esta tabela existe para produzir esse dump real UMA vez, e a comparacao com o
-- shape assumido e o que se ganha.
--
-- CUSTO, DECLARADO ANTES DE RODAR
--
-- Athena cobra por BYTES ESCANEADOS (US$ 5 por TB na us-east-1). Esta tabela
-- tem ~30 linhas: cada consulta escaneia kilobytes, e o custo total do roteiro
-- fica em fracao de centavo. O S3 cobra armazenamento (~US$ 0,023/GB/mes) e
-- requisicoes -- a tabela inteira nao chega a 1 MB.
--
-- O que NAO e de graca e esquecer a tabela ligada. A secao de LIMPEZA no fim
-- e parte do roteiro, nao um extra.
--
-- ORDEM DE EXECUCAO
--
-- Os passos 3 a 6 PRECISAM rodar em sequencia e separados: cada INSERT/DELETE
-- e um commit, e um commit e um snapshot. Rodar tudo de uma vez produziria uma
-- tabela com um snapshot so, que e exatamente o que este corpus NAO quer
-- exercitar.
--
-- Substitua <BUCKET> pelo bucket criado no passo 1.

-- ---------------------------------------------------------------------------
-- PASSO 1 (fora daqui): criar o bucket e o database
-- ---------------------------------------------------------------------------
-- aws s3 mb s3://<BUCKET> --region us-east-1 --profile sparkforge
-- aws athena start-query-execution \
--   --query-string "CREATE DATABASE IF NOT EXISTS sparkforge_teste" \
--   --result-configuration OutputLocation=s3://<BUCKET>/athena-results/ \
--   --region us-east-1 --profile sparkforge

-- ---------------------------------------------------------------------------
-- PASSO 2: a tabela. `format-version` = 2 de proposito.
-- ---------------------------------------------------------------------------
-- v2 e o caso que o corpus ja cobre em 9 fixtures, e o objetivo aqui e
-- comparar o SHAPE do dump, nao exercitar v3. Uma segunda tabela em v3 e
-- trabalho a parte, e so vale depois que o shape de v2 estiver conferido.
CREATE TABLE sparkforge_teste.pedidos (
  id            bigint,
  cliente       string,
  valor         double,
  dia           date
)
PARTITIONED BY (dia)
LOCATION 's3://<BUCKET>/pedidos/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format-version' = '2',
  -- MERGE-ON-READ nas tres operacoes: e o que faz o DELETE do passo 5 gerar
  -- position delete FILES em vez de reescrever os data files. Com o default
  -- (copy-on-write) nao haveria `.delete_files` nenhum, e a metade do corpus
  -- que este roteiro existe para validar ficaria vazia.
  'write_target_data_file_size_bytes' = '536870912',
  'format' = 'parquet'
);

-- ---------------------------------------------------------------------------
-- PASSO 3, 4 e 5: TRES commits separados -> tres snapshots
-- ---------------------------------------------------------------------------
-- Rode um de cada vez. Cada um gera snapshot, manifest e data files proprios.

-- 3:
INSERT INTO sparkforge_teste.pedidos VALUES
  (1, 'ana',   100.0, DATE '2026-01-01'),
  (2, 'bruno', 250.5, DATE '2026-01-01'),
  (3, 'carla',  75.2, DATE '2026-01-02');

-- 4:
INSERT INTO sparkforge_teste.pedidos VALUES
  (4, 'diego', 310.0, DATE '2026-01-02'),
  (5, 'elena',  42.9, DATE '2026-01-03');

-- 5:
INSERT INTO sparkforge_teste.pedidos VALUES
  (6, 'fabio', 999.9, DATE '2026-01-03');

-- ---------------------------------------------------------------------------
-- PASSO 6: o DELETE que gera delete files
-- ---------------------------------------------------------------------------
-- E o passo que produz a secao `.delete_files` do dump -- sem ele,
-- `iceberg.delete_files_summary` sai com contagem zero e o censo por `content`
-- (position vs equality) nao tem o que separar.
DELETE FROM sparkforge_teste.pedidos WHERE id = 2;

-- ---------------------------------------------------------------------------
-- PASSO 7: conferir o que as metadata tables devolvem
-- ---------------------------------------------------------------------------
-- Estas sao as CINCO que `collect/aws.py::ICEBERG_METADATA_SECTIONS` consulta.
-- Rode cada uma e compare as COLUNAS com o que `fixtures/iceberg/*/input/
-- dump.json` assume. A divergencia de shape e o achado que este roteiro busca.

SELECT * FROM "sparkforge_teste"."pedidos$files"        LIMIT 20;
SELECT * FROM "sparkforge_teste"."pedidos$delete_files" LIMIT 20;
SELECT * FROM "sparkforge_teste"."pedidos$snapshots"    LIMIT 20;
SELECT * FROM "sparkforge_teste"."pedidos$manifests"    LIMIT 20;
SELECT * FROM "sparkforge_teste"."pedidos$partitions"   LIMIT 20;

-- A coluna `content` de `$delete_files` e o que o censo de 2026-09-02 le:
-- 1 = position, 2 = equality. Este roteiro produz POSITION (o DELETE acima),
-- e nao equality -- equality delete vem de MERGE/upsert, nao de DELETE
-- simples. Se `content` nao aparecer aqui, o censo nunca teria dado outra
-- coisa alem de `content_unresolved` em producao.
SELECT content, count(*) AS n
FROM "sparkforge_teste"."pedidos$delete_files"
GROUP BY content;

-- ---------------------------------------------------------------------------
-- LIMPEZA -- parte do roteiro, nao extra
-- ---------------------------------------------------------------------------
-- DROP TABLE sparkforge_teste.pedidos;
-- DROP DATABASE sparkforge_teste;
-- aws s3 rb s3://<BUCKET> --force --region us-east-1 --profile sparkforge
--
-- O `DROP TABLE` de tabela Iceberg no Athena remove os dados do S3. O
-- `s3 rb --force` fecha o que sobrar (resultados de query do Athena).
