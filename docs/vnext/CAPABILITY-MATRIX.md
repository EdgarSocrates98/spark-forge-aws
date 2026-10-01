# SparkForge AWS — AWS Data Platform Capability Matrix (Phase 0)

A matriz publicada em `a5b9e96` cruzava serviços AWS fundamentais de dados contra
dimensões de engenharia, marcando um único check por célula. A auditoria
registrada em `docs/claims.lock.json` não encontrou, para nenhum serviço
listado, artefato que provasse a cobertura simultânea de todas as dimensões
afirmadas — para vários serviços não existe nenhum código, coletor, agente ou
teste dedicado no repositório. A matriz afirmava uma cobertura que o repositório
não sustenta e foi removida pela auditoria; o motivo de cada linha está
registrado no manifesto de alegações.

## Lake Formation: matriz versionada com lastro

A lane de arquitetura Lake Formation não usa esta matriz ampla de serviços como
prova de suporte. Sua fonte operacional é
`knowledge/lakeformation/capability-matrix.yaml`, com células por engine
(`glue`, `emr_ec2`, `emr_serverless`), release, FGAC/FTA, formato e operação.
O consumidor determinístico é
`sparkforge/lakeformation/capabilities.py`; capability não declarada retorna
`unknown` e desbloqueio nomeado, nunca extrapolação.

Ownership de catálogo, RAM, resource link, `GetDataAccess`, filesystem e grants
continuam dimensões independentes no preflight. Use
`sparkforge lakeformation architect --input architecture.json` para obter a
decisão estruturada antes de qualquer coleta ou recomendação.

A matriz operacional inclui Hive/Parquet/Iceberg/Hudi/Delta e operações read,
com operational review e runbook para validar uso real antes de declarar suporte,
write, DDL/DML por release. Cada release tem células próprias; divergência entre
fontes oficiais permanece `version_dependent`/`unknown`, nunca suporte por
analogia.
