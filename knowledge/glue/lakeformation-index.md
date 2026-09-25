# Lake Formation — onde cada resposta mora, e as transições de versão

O §29 do prompt de origem pede uma árvore de **16 documentos** em
`docs/aws/lakeformation/`. Ela não foi criada, e a razão é o §32 do mesmo prompt:
*"não duplicar funcionalidades existentes; antes de criar qualquer novo módulo,
localizar o que já existe e estender quando possível."*

Medido em 2026-09-10 sobre 186 documentos de `knowledge/` e `docs/`: **dez dos
dezesseis tópicos já têm dono**, e a cobertura está dispersa por organização
diferente — por artefato analisado, não por serviço AWS.

O que faltava não era conteúdo. Era **navegação**: "onde está a resposta sobre
X?". Este arquivo é isso, mais as três transições de versão que a matriz sustenta
e que ninguém havia escrito.

---

## Os dezesseis, e onde cada um mora

| Pedido | Onde a resposta está |
|---|---|
| `overview` | §1–§3 de [`lakeformation-fgac.md`](lakeformation-fgac.md) — o que FGAC exige, proíbe e custa |
| `fgac` | idem, mais as 11 regras `SF-LF` em `rules/catalog/lakeformation.yaml` (a `SF-LF-011`, de 2026-09-25, nomeia a permissão que falta atrás de `ERR-LF-001`, pela tabela operação → permissão de [`lakeformation-permissions.yaml`](lakeformation-permissions.yaml) — **legível por máquina**, com `source` e `quote` por linha) |
| `fta` | §5 de [`lakeformation-fgac.md`](lakeformation-fgac.md), e os eixos `fta_*` de [`lakeformation-matrix.yaml`](lakeformation-matrix.yaml) |
| `cross-account` | `rules/catalog/glue-cross-account.yaml` (`SF-XACC`), `SF-LF-007`, e `ERR-LF-002` |
| `resource-links` | §1 de [`lakeformation-fgac.md`](lakeformation-fgac.md) — *"cross-account só por resource link, com nome idêntico"*, e desde 2026-09-10 com **fact medido**: `sparkforge collect glue-resource-link` produz `glue.resource_link` e `glue.resource_link.target`, `SF-XACC-002` e `SF-XACC-003` julgam sobre eles, e a perna do grafo de acesso deixou de sair `unresolved` |
| `credential-vending` | `ERR-LF-002..005`, e o eixo `fta_*` da matriz |
| `iam` | `rules/catalog/iam.yaml` (`SF-IAM-001..003`) — e a decisão é **simulada**, nunca parse de policy |
| `s3` | `SF-LF-004` (o conector default), `lakeformation.registered_location`, e `SF-PQ` para layout |
| `kms` | `rules/catalog/glue-kms.yaml` (`SF-KMS-001/002`). **A key policy não tem coletor** — o grafo de acesso a devolve `unresolved` |
| `iceberg` | [`../storage/iceberg-catalog.md`](../storage/iceberg-catalog.md), mais `SF-ICE-006/008/009` e `SF-LF-003` |
| `parquet` | `SF-PQ` (9 regras) e [`../storage/parquet-layout.md`](../storage/parquet-layout.md) |
| `glue-4-to-5` | **a seção abaixo**, derivada da matriz |
| `glue-5-to-5.1` | **a seção abaixo**, derivada da matriz |
| `glue-5.1-to-6` | **a seção abaixo** — e ela é um limite declarado |
| `troubleshooting` | as 23 assinaturas de `knowledge/errors/`, mais a skill `diagnose-lakeformation-access` |
| `compatibility-matrix` | [`lakeformation-matrix.yaml`](lakeformation-matrix.yaml) — **legível por máquina**, com `source` e `quote` por célula |

**Seis dos dezesseis não são documento, são dado ou código**, e é por isso que a
árvore de arquivos não os representaria: a matriz de compatibilidade é YAML
validado na carga, as regras são catálogo executável, e as assinaturas são JSON
com fonte e data.

---

## As três transições, derivadas da matriz

As tabelas abaixo saem de `lakeformation-matrix.yaml` — só as células que
**mudam** entre as duas versões. `tests/test_lakeformation_matrix.py` trava a
consistência: se a matriz mudar e esta seção não, o gate reprova.

### Glue 4.0 → 5.0 — o modelo inteiro troca

| Eixo | 4.0 | 5.0 |
|---|---|---|
| FGAC via `GlueContext`/DynamicFrame | suportado | **não suportado** |
| FGAC Spark-native (leitura) | não existia | suportado |
| FGAC Spark-native (escrita) | não existia | **não suportado** |
| FGAC DDL/DML | não existia | não declarado |
| FTA Spark-native | não existia | suportado (Hive e Iceberg) |
| FTA via `GlueContext`/DynamicFrame | suportado | suportado, **só tabela não-OTF** |
| FTA DDL/DML | não existia | suportado |
| FTA com biblioteca custom, UDF e RDD | não existia | suportado |

**É a transição que mais quebra job, e a razão é a primeira linha.** Um job de
4.0 que lia tabela protegida por `create_dynamic_frame.from_catalog` **não tem
tradução direta** — o caminho é migrar para DataFrame do Spark. E no 5.0 a
escrita sob FGAC ainda não existia: quem migrou lendo por FGAC teve de escrever
por IAM.

### Glue 5.0 → 5.1 — quatro células, e uma quebra calada

| Eixo | 5.0 | 5.1 |
|---|---|---|
| **Filesystem S3 default** | **EMRFS** | **S3A** |
| FGAC Spark-native (escrita) | não suportado | **suportado** |
| FGAC DDL/DML | não declarado | suportado |
| FTA Spark-native | Hive e Iceberg | + Hudi e Delta |

**A primeira linha é a que quebra sem erro.**
`spark.hadoop.fs.s3.credentialsResolverClass` é chave de **EMRFS**; sob S3A ela é
ignorada em silêncio, a credencial do Lake Formation nunca é pedida, e o
`AccessDenied` que sai disso parece problema de governança. É `SF-LF-004`, e o
`runtime_scope` dela é `{glue: ">=5.1"}` — a fronteira mais estreita do catálogo.

**A segunda linha está em conflito declarado.** A página de migração afirma
suporte a escrita Spark-native; a de considerações lista escrita com permissão de
Lake Formation como não suportada, e diz que o caminho de acesso passa pelas
credenciais armazenadas **independentemente** do IAM do runtime role. Ver a §6 de
[`lakeformation-fgac.md`](lakeformation-fgac.md), que apresenta as quatro frases
e **não escolhe lado**, e `SF-LF-009`.

### Glue 5.1 → 6.0 — limite declarado

**Esta transição não existe na matriz**, e não por esquecimento. A página de
migração para o 6.0 existe e é vigiada por
[`runtime-matrix.yaml`](runtime-matrix.yaml) — é de lá que saem Spark 4.1.1 e
Iceberg 1.11.0 —, mas **ela não foi lida para o eixo de Lake Formation**.

`sparkforge lakeformation matrix --runtime 6.0` devolve
`reason: runtime_fora_da_matriz` com o que destravaria. Preencher uma coluna
"6.0" por analogia com o 5.1 seria inventar capacidade — e é exatamente o erro
que a §0 de [`lakeformation-fgac.md`](lakeformation-fgac.md) diz que mais engana
nesta área.

O que **é** sabido sobre o 6.0 e vale citar: três regras o guardam
(`SF-MIG-003`, `SF-ERR-001`, `SF-ERR-002`, todas `{glue: ">=6.0"}`), e
`knowledge/storage/iceberg-v3.md` cobre o formato v3 que ele suporta.

---

## O que este índice não resolve

**Duas pernas do caminho de acesso não têm coletor**, e o índice não as esconde:
RAM share e key policy do KMS. O grafo de acesso
(`sparkforge lakeformation access-graph`) as devolve `unresolved` com o que
destravaria cada uma — `ram:GetResourceShares` e `kms:GetKeyPolicy`.

**Eram três até 2026-09-10.** A terceira era resource link, e o que a destravava
estava escrito na própria recusa: *"`glue:GetTable` sobre o link, comparando o
nome com o do recurso de origem"*. `sparkforge/collect/glue_resource_link.py` é
exatamente essa chamada, e com ela a perna passou a ter quatro saídas medidas —
`granted` (nome idêntico e origem respondendo), `blocking` (nome divergente),
`not_applicable` (o objeto não é link) e `unresolved` (a origem respondeu
`EntityNotFoundException`, que sob Lake Formation **não** distingue recurso
inexistente de recurso não autorizado).

Enquanto as duas restantes não existirem, `is_accessible` nunca sai `true` num
case real: ele sai `null`, que significa *"o que eu consegui olhar não impede"*.
