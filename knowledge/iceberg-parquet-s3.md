# Iceberg, Parquet e S3

Iceberg adiciona snapshots, manifestos, evolucao de schema e commits atomicos sobre S3. Glue Catalog, locking, S3FileIO, multipart upload e retries devem ser validados. Parquet deve usar tipos corretos, compressao, row groups, estatisticas e arquivos de tamanho adequado.

Separe zonas e ownership no S3, use KMS, Block Public Access, lifecycle, versioning, inventario e logs. Meça bytes lidos, pruning, small files, compaction, expiracao e rollback.

Fonte: https://iceberg.apache.org/docs/latest/aws/
