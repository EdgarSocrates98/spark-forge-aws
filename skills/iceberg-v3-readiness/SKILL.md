---
name: iceberg-v3-readiness
description: Use quando alguém pergunta "posso subir essa tabela para Iceberg format v3?", "o Athena lê v3?", "vale a pena o VARIANT / os deletion vectors / o row lineage?" ou quando uma query em Athena passou a falhar com `Cannot read unsupported version 3` depois de uma migração de runtime. Use antes de qualquer recomendação de mudar `format-version`. Se você está prestes a responder de memória o que cada engine suporta, rode `sparkforge iceberg assess-upgrade <dir> --from 2 --to 3` — a matriz de suporte tem uma célula por par engine/feature, cada uma com fonte, e a maioria é `UNKNOWN`, que é o resultado honesto e não uma lacuna a preencher por inferência.
---

# Iceberg v3 Readiness

Subir o format version é **decisão de ida**. O modo de falha é perverso: o job de escrita passa, e o consumidor quebra dias depois, com a causa a semanas de distância no log de mudanças. Por isso a pergunta certa não é "o Iceberg suporta?" — é "quem lê esta tabela suporta?".

## Duas metades que não se deduzem uma da outra

**Feature da spec** é o que o formato v3 define: VARIANT com shredding, timestamp de nanossegundo, tipos geoespaciais, deletion vectors, row lineage, default values.

**Suporte da engine** é o que cada motor executa. Nunca se infere "o Iceberg suporta, logo o Athena suporta" — nem na direção negativa. A fonte que diz que o Athena não lê uma tabela v3 fala do **formato da tabela**, não de cada feature; estender a frase preencheria células a partir de uma fonte que não fala delas.

`sparkforge/storage/feature_support.py` grava essa regra em código: célula afirmativa sem `source`, `source_type` e `retrieved` faz o carregador estourar na carga.

## Procedimento

1. Declare quem consome, em `.sparkforge/consumers.yaml`:

   ```yaml
   consumers:
     - table: glue_catalog.curated.pedidos
       service: athena
     - table: glue_catalog.curated.pedidos
       service: emr_eks          # NUNCA `emr` — ver abaixo
       release: emr-7.7.0        # opcional, e é o que faz a resposta ser específica
   ```

   Sem inventário não há quem consultar. O extrator lê um arquivo que **uma pessoa escreveu**, de propósito: quem consome uma tabela não está no código do job, nem no plano físico, nem no metadata Iceberg — é conhecimento da organização. Derivar do histórico de queries do Athena veria só o Athena.

## `emr` não é uma engine

As três plataformas publicam Iceberg **diferente** — divergência em **6 de 26** releases comparáveis entre EC2 e EKS. Em `emr-7.7.0` o EC2 traz `1.7.1-amzn-0` e o EKS traz `1.6.1-amzn-2`; em `emr-6.5.0` o EC2 traz `0.12.0` e o EKS **não traz Iceberg nenhum**. Uma resposta dada para "EMR" está errada para pelo menos uma das três, e quem pergunta não tem como saber qual.

Declare `emr_ec2`, `emr_serverless` ou `emr_eks`. `emr` continua sendo reconhecido pelo extrator — tirá-lo transformaria ambiguidade em alarme de grafia — mas ele **não tem linha na matriz**, e por isso sai como `UNKNOWN` **nomeado**, com a frase dizendo qual das três declarar.

Com `release:` declarada, a resposta cruza a versão de Iceberg **daquela release, daquela plataforma** com o `min_library_version` da feature. `min_library_version` é **limite inferior**: biblioteca anterior ao mínimo é `UNSUPPORTED` (não pode ter o que ainda não existia); biblioteca que atende o mínimo **não** vira `SUPPORTED` — a resposta continua sendo a da célula da engine, que quase sempre é `UNKNOWN`. Atender é condição necessária, nunca suficiente.

A resposta é **por família de release**. A fonte declara que `emr-7.7.0-java8-latest` não tem Iceberg enquanto `emr-7.7.0` tem, então um label com variante de imagem recebe `UNKNOWN` com a razão `variante_de_imagem_fora_da_matriz` — nunca a resposta da família.

## IAM não é prova de acesso ao dado

Lake Formation, S3, KMS e Glue Catalog são camadas **separadas**. Duas combinações estão confirmadas por fonte: FGAC não é suportado com coluna `VARIANT`, e Lake Formation **não gerencia permissão** para `VACUUM`, `MERGE`, `UPDATE` ou `OPTIMIZE` em tabela Iceberg. Duas ficam `UNKNOWN` e continuam `UNKNOWN`: `v3 × FGAC` e `REST Catalog × Lake Formation`. Permissão IAM concedida não é prova de que o dado chega.

2. `sparkforge iceberg assess-upgrade <dir> --from 2 --to 3`

3. Leia o veredito **e as células**. O veredito sem elas seria uma palavra que ninguém consegue conferir.

## Os quatro vereditos, e a precedência entre eles

| Veredito | O que significa |
|---|---|
| `BLOCKED` | Há fonte dizendo que uma engine declarada não executa. Vence tudo: não há o que resolver |
| `UNRESOLVED` | Falta fonte sobre alguma engine — **inclusive quando não há inventário nenhum**. Vence `CONDITIONAL` e `SAFE` |
| `CONDITIONAL` | Suporte parcial, somente-leitura, preview ou fontes conflitantes. Exige ler a nota da célula |
| `SAFE` | Toda célula consultada é afirmativa |

`UNRESOLVED` **não** é `SAFE`. Ausência de declaração não é declaração de ausência, e responder "seguro" a um inventário vazio seria a resposta errada com cara de resposta certa.

O comando **nunca executa o upgrade**. A garantia é estrutural: o módulo não importa cliente de AWS nem Spark.

## O caso documentado

Glue 5.1 e 6.0 escrevem Iceberg format v3. Athena SQL não lê: `Cannot read unsupported version 3` (`ERR-ATH-001`). A regra `SF-ENV-002` acusa isso em P0 quando o inventário declara Athena e a tabela está em v3 — e o eixo `consumidor` do assessment de migração fecha junto, sem acusar duas vezes.

Deletion vectors e row lineage **já vinham** no Glue 5.1: migrar para 6.0 por causa deles é pagar por algo que já se tem.

## Referência rápida

Aprofundamento sob demanda: [`knowledge/storage/iceberg-v3.md`](../../knowledge/storage/iceberg-v3.md) separa as duas metades em prosa; [`knowledge/storage/iceberg-feature-support.yaml`](../../knowledge/storage/iceberg-feature-support.yaml) é a matriz consultável, com as notas por engine explicando por que cada `UNKNOWN` continua `UNKNOWN`; [`docs/aws/glue/6.0/iceberg.md`](../../docs/aws/glue/6.0/iceberg.md) traz as limitações declaradas pela AWS para o Glue 6.0.

## Quando NÃO usar

- A tabela está lenta, com small files, delete files ou snapshots demais: isso é manutenção, não formato — use `optimize-iceberg-table`.
- A pergunta é sobre a **migração do runtime** e não sobre o formato da tabela: use `migrate-glue-6`.
- A pergunta é sobre **FGAC com coluna VARIANT**: a restrição existe e está em `lakeformation-fgac-guard`.

## Red flags

- **"Ninguém mais usa essa tabela."** Sem inventário, isso é memória, não evidência. O veredito correspondente é `UNRESOLVED`.
- **"O Iceberg 1.11 suporta, então está liberado."** Suporte da biblioteca não é suporte da engine que lê. São as duas metades.
- **"Se der problema a gente volta para v2."** Reverter format version depois de escritas em v3 não é trivial. Trate como decisão de ida e confirme na documentação da versão de Iceberg em uso antes de assumir reversibilidade.
- **"A matriz está cheia de `UNKNOWN`, então ela não serve."** `UNKNOWN` é o resultado: significa que ninguém publicou fonte sobre aquela engine. Preencher por raciocínio é fabricar célula. Hoje são **174 `UNKNOWN` em 191 células**, e as 17 restantes carregam URL e data.
- **"O consumidor é EMR."** Qual? As três publicam Iceberg diferente. Enquanto a declaração for `emr`, a resposta é uma lacuna nomeada, não um veredito.
- **"A biblioteca daquela release é 1.10, então a feature está lá."** Não. Versão de biblioteca que atende o mínimo é condição necessária; a AWS repackaga (`-amzn-N`) e pode desabilitar o que a upstream entrega.
