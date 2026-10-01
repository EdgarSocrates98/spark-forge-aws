-- Substitua catalog.database.table pelo identificador real.

-- Arquivos de dados
SELECT
  count(*) AS data_file_count,
  sum(file_size_in_bytes) AS total_bytes,
  avg(file_size_in_bytes) AS avg_file_bytes,
  min(file_size_in_bytes) AS min_file_bytes,
  max(file_size_in_bytes) AS max_file_bytes
FROM catalog.database.table.files
WHERE content = 0;

-- Arquivos de delete
SELECT
  content,
  count(*) AS file_count,
  sum(file_size_in_bytes) AS total_bytes
FROM catalog.database.table.files
WHERE content IN (1, 2)
GROUP BY content;

-- Snapshots
SELECT *
FROM catalog.database.table.snapshots
ORDER BY committed_at DESC;

-- Histórico
SELECT *
FROM catalog.database.table.history
ORDER BY made_current_at DESC;

-- Manifests
SELECT *
FROM catalog.database.table.manifests;

-- Partições
SELECT *
FROM catalog.database.table.partitions;
