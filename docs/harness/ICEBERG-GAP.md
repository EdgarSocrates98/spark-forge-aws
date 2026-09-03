# ICEBERG-GAP — as 27 camadas da §1, e o que sustenta cada uma

**Data:** 2026-09-02
**Origem:** auditoria da Fase A de `prompt_evo_iceberg.md`, que a §1 do prompt exige e a
Fase A manda fazer antes de qualquer código.
**Estado corrente:** [`../superpowers/STATUS.md`](../superpowers/STATUS.md)

---

## Por que este mapa existe

A §1 do prompt de origem exige raciocinar sobre **27 camadas** de Iceberg em separado, e
lista as 27. A pergunta que decide o trabalho não é *"o repositório fala dessas camadas?"*
— é **o que sustenta cada uma**: conhecimento, fato, regra, ou nada.

Sem este mapa, cada incremento recomeça a mesma pergunta, e a resposta muda conforme quem
procura.

## O erro de método que este mapa corrige

A primeira varredura procurou **o nome da camada** no repositório e concluiu que 15 das 27
não tinham mecanismo. Estava errada, e o erro é instrutivo: `deletion vectors`, `Puffin` e
`query planning` **estavam lá**, sob outros nomes —
`knowledge/storage/iceberg-feature-support.yaml` tem **878 linhas** com **14 engines × 13
features**, e `sparkforge/storage/` tem `feature_support.py`, `readiness.py` e
`upgrade.py`.

**Procure pelo que a camada FAZ, não pelo nome dela.** A segunda varredura usou padrões de
capacidade (`plan_files|scan_planning`, `commit\.retry|CommitFailed`, `io-impl|S3FileIO`) e
deu outro resultado.

## As 27, por estado

### Têm fato e regra (5)

| Camada | Fato | Regra |
|---|---|---|
| data files | `iceberg.files_summary` | `SF-ICE-001` |
| delete files | `iceberg.delete_files_summary` | `SF-ICE-002` |
| snapshots | `iceberg.snapshots_summary` | `SF-ICE-003` |
| sort orders | `iceberg.table_property` | `SF-ICE-004` |
| write planning | `iceberg.table_property` | `SF-ICE-005` |

### Têm fato, sem regra (3)

| Camada | Fato | Por quê |
|---|---|---|
| table specification | `iceberg.format_version` | consumida por `SF-ENV-002`, que julga o cruzamento com o consumidor — não a versão isolada |
| partition specs | `iceberg.partitions_summary` | nenhuma fonte publica limiar de cardinalidade de partição |
| manifests | `iceberg.manifests_summary` | **veto `V-ICE-1`** — a fonte diz que manifests causam planejamento lento e **não publica número** |

### Já existem sob outro nome (2)

| Camada | Onde |
|---|---|
| metadata tables | **é o próprio dump** — o artefato que `iceberg_metadata.py` lê É o resultado de consultar `.files`, `.snapshots`, `.manifests`, `.partitions` |
| compatibility | `feature_support.py` + `readiness.py` + `upgrade.py`, sobre uma matriz de 878 linhas |

### Pertencem a outro artefato, e já têm dono (4)

| Camada | Dono |
|---|---|
| optimistic concurrency | log de erro — `knowledge/errors/.../commit_conflict.json` |
| engine integrations | `spark.conf_effective` (`SparkCatalog`, `catalog-impl`) |
| governance | Lake Formation e IAM — `SF-LF-001` |
| catalogs | `env.consumer` e a conf de Spark |

Julgá-las a partir do metadata de Iceberg seria pedir ao artefato errado.

### O artefato não carrega o dado (6)

**Esta é a categoria que decide o próximo passo, e ela é do COLETOR, não das regras.**

O dump que `iceberg_metadata.py` lê tem dez seções: `table`, `format_version`,
`properties`, `files`, `delete_files`, `snapshots`, `manifests`, `partitions`,
`sort_order`, `partition_spec`. O que falta a cada camada:

| Camada | O que o coletor teria de trazer |
|---|---|
| schemas | não há seção `schemas`; exigiria `.refs`, `.metadata_log_entries` ou o `metadata.json` inteiro |
| manifest lists | `.manifests` lista **manifests**, não manifest lists; o `manifest_list` fica no snapshot do `metadata.json` |
| metadata files | `metadata-log` não está em metadata table nenhuma |
| Puffin | estatísticas vivem em `.statistics` / `.all_statistics` |
| transactions | transação não é estado observável num dump de metadata |
| query planning | tempo de planejamento é do **event log**, não do metadata |

O extrator declara, na própria docstring, que *"a coleta é responsabilidade de uma camada
anterior, fora deste pacote"*. Estender o coletor é fase própria — e sem artefato real
para validar, as fixtures seriam sintéticas.

### Parcialmente ao alcance (1)

**deletion vectors.** `.delete_files` tem a coluna `content` (`0` data, `1` position, `2`
equality), e em v3 os DV aparecem ali. O coletor não traz o campo. Destravaria com uma
coluna a mais no `SELECT`.

### Sem fonte que nomeie defeito (6)

| Camada | Medido |
|---|---|
| **storage** | `object-storage` tem **zero ocorrências** em todo `knowledge/` e `rules/`. `write.object-storage.enabled` é table property e o extrator já a emitiria — mas nenhuma fonte diz quando ligá-la é defeito |
| FileIO | `io-impl` é propriedade de **catálogo**, não de tabela |
| schemas (evolução) | a knowledge descreve evolução de schema; não publica quando ela é defeito |
| Puffin (uso) | idem |
| metadata files (acúmulo) | idem |
| manifest lists | idem |

**Achar pouco é resultado válido.** Escrever regra para qualquer uma destas seria inventar
limiar — o defeito que `V-ICE-1` recusou para manifests, e que
`IcebergMaintenancePlanner` cometia com `> 20`, `> 5` e `> 50` até ser reescrito.

## A auditoria das fontes que a §2 exige (Fase B)

A §2 do prompt manda auditar as fontes oficiais **antes de implementar qualquer coisa**, e
lista dezesseis páginas da documentação do Iceberg. Medido em 2026-09-02 contra
`knowledge/sources.lock.json`, que vigia **225** fontes no total:

**Três** páginas específicas de Iceberg estão vigiadas: a Table Specification,
`spark-procedures` e `spark-queries#inspecting-tables`.

**Treze não estão**: `spark-writes`, `spark-ddl`, `spark-configuration`, `maintenance`,
`partitioning`, `evolution`, `docs/latest/aws`, `configuration`, `branching`, `puffin`,
`metrics`, `rest-catalog` e o histórico de releases.

**A varredura por substring dá três falsos positivos, e vale registrá-los** porque quem
repetir a medição vai encontrá-los: `configuration` casa com
`spark.apache.org/docs/latest/configuration.html` — que é do **Spark**, não do Iceberg;
`metrics` casa com um blog da AWS; `releases` casa com a API de releases do **GraphFrames**.
A conta honesta é três, não sete.

### O critério para vigiar uma fonte, e por que ele não é "está na lista"

Vigiar custa: a fonte entra no `sources.lock.json` com hash de conteúdo, e cada mudança
dela vira alarme de drift. A matriz de runtime do EMR já dispara ~4×/ano e a página
mensal do Control-M ~12×/ano — alarmes que quase sempre fecham sem ação.

**Uma fonte só se paga quando sustenta um defeito.** As seis camadas da seção *"sem fonte
que nomeie defeito"* acima estão paradas exatamente por isso, e nenhuma das treze páginas
não vigiadas foi lida ainda para saber se destrava alguma.

O trabalho que decide, e que **não** foi feito: ler cada uma das treze varrendo por padrão
de defeito — `must`, `cannot`, `is not supported`, `up to \d+` —, como a entrega de
dependência e janela do Control-M fez sobre `API_CodeRef_JobProperties`. Lá a varredura
mediu **3 defeitos de janela, 2 de dependência e zero de SLA**, e o zero virou veto em vez
de cinco regras inventadas.

Até que essa leitura aconteça, acrescentar as treze ao `sources.lock.json` compraria treze
alarmes anuais sem nenhuma regra em troca.

## O que este mapa sustenta como próximo passo

Em ordem de valor por custo:

1. **Uma coluna no coletor** destrava `deletion vectors` — a mais barata das seis
   bloqueadas pelo artefato.
2. **§2–7, a auditoria das fontes** (Fase B do prompt). Seis camadas estão paradas por
   falta de fonte, não de mecanismo. Medir o que cada fonte oficial publica como **defeito**
   é o que decide se alguma delas destrava. No Control-M essa auditoria mediu que SLA tinha
   **zero** fonte, e evitou cinco regras inventadas.
3. **Estender o coletor** para `.statistics`, `.metadata_log_entries` e `.refs` — trabalho
   maior, e sem artefato real as fixtures seriam sintéticas.

**O que não fazer:** escrever regra para camada sem fonte. Seis das 27 estão exatamente
nessa condição, e cada uma delas produziria um número com cara de medida.
