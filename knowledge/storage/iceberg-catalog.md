# Catálogo Iceberg no Spark — as duas implementações, e o que cada uma faz

Este documento existe porque **duas classes diferentes atendem à mesma chave de
configuração**, e a diferença entre elas não é de performance nem de versão: é de
**quais tabelas passam a resolver**. Um job que lê Parquet e Iceberg na mesma
sessão é o caso em que a escolha errada é silenciosa até a primeira leitura da
tabela que não é Iceberg.

Versões embarcadas por runtime em [`../glue/runtime-matrix.md`](../glue/runtime-matrix.md).
O recorte de Lake Formation está em
[`../glue/lakeformation-fgac.md`](../glue/lakeformation-fgac.md) — em especial a §4,
que trata do `spark_catalog` sob controle de acesso fino.

---

## 1. As duas classes, lidas da fonte

A página de configuração do Spark do Apache Iceberg (Iceberg 1.11.0, coletada em
2026-09-09) declara as duas implementações lado a lado:

> A catalog is created and named by adding a property `spark.sql.catalog.(catalog-name)`
> with an implementation class for its value. Iceberg supplies two implementations:
>
> - `org.apache.iceberg.spark.SparkCatalog` supports a Hive Metastore or a Hadoop
>   warehouse as a catalog
> - `org.apache.iceberg.spark.SparkSessionCatalog` **adds support for Iceberg tables
>   to Spark's built-in catalog, and delegates to the built-in catalog for
>   non-Iceberg tables**

E, sobre `SparkCatalog` com backend Hive:

> The Hive-based catalog **only loads Iceberg tables**. To load non-Iceberg tables in
> the same Hive metastore, use a session catalog.

Sobre substituir o catálogo de sessão:

> To add Iceberg table support to Spark's built-in catalog, configure `spark_catalog`
> to use Iceberg's `SparkSessionCatalog`.
>
> ```
> spark.sql.catalog.spark_catalog = org.apache.iceberg.spark.SparkSessionCatalog
> spark.sql.catalog.spark_catalog.type = hive
> ```
>
> [...] **When a table is not an Iceberg table, the built-in catalog will be used to
> load it instead.** This configuration can use same Hive Metastore for both Iceberg
> and non-Iceberg tables. `SparkSessionCatalog` is useful when you want `spark_catalog`
> to work with both Iceberg and non-Iceberg tables in the same metastore.

---

## 2. A combinação que a fonte recorta, e o que ela implica

As três frases acima não dizem, numa frase só, "`SparkCatalog` em `spark_catalog`
quebra tabela não-Iceberg". Elas dizem duas coisas que **se somam**:

1. `SparkCatalog` com backend Hive **só carrega tabela Iceberg**;
2. para carregar tabela não-Iceberg no mesmo metastore, **use um session catalog** —
   e o session catalog do Spark é `spark_catalog`.

Portanto: um job que declara

```
spark.sql.catalog.spark_catalog = org.apache.iceberg.spark.SparkCatalog
```

substitui o catálogo de sessão por uma implementação que, pela própria fonte, não
carrega tabela não-Iceberg — e é o catálogo de sessão que resolve todo nome de
tabela **não qualificado**. Um `SELECT * FROM curated.fato_venda` sobre tabela
Parquet passa a não resolver.

**Esta é uma inferência de duas frases da mesma página, não uma frase única.** É por
isso que a regra que a julga (`SF-ICE-006`) sai como `structural`: ela afirma que a
configuração está fora do recorte que a documentação sustenta, nunca que uma falha
observada veio dela.

`SparkSessionCatalog` é a única das duas que a fonte descreve como delegando ao
catálogo embutido. `SparkCatalog` continua **correto** — e é a escolha certa — em
qualquer catálogo de nome próprio (`spark.sql.catalog.meu_catalogo`), que é o padrão
que a própria página exemplifica três vezes.

---

## 3. O cruzamento com Lake Formation

O recorte de FGAC empilha uma segunda restrição sobre a mesma chave. A AWS declara,
entre as limitações de Iceberg sob controle de acesso fino:

> You can only use Apache Iceberg with session catalog and not arbitrarily named
> catalogs.

Os dois recortes **não são o mesmo**, e a diferença importa:

| | O que restringe | Quem declara |
|---|---|---|
| `SF-ICE-006` | a **classe** em `spark_catalog` — `SparkCatalog` não delega | Apache Iceberg |
| `SF-LF-003` | o **nome** do catálogo sob FGAC — só `spark_catalog` | AWS |

Um job pode violar um sem violar o outro. `spark.sql.catalog.glue_catalog =
SparkCatalog` é **correto** para o Iceberg e **fora do recorte** sob FGAC.
`spark.sql.catalog.spark_catalog = SparkCatalog` é o inverso: dentro do recorte de
nome da AWS, e fora do que o Iceberg sustenta para tabela não-Iceberg.

A configuração que satisfaz os dois é uma só:

```
spark.sql.catalog.spark_catalog = org.apache.iceberg.spark.SparkSessionCatalog
```

---

## 4. `.glue.lakeformation-enabled` — onde a chave aparece, e onde não

A chave `spark.sql.catalog.<nome>.glue.lakeformation-enabled` aparece na página de
**Full Table Access** do Glue. Ela **não aparece** na página de FGAC.

O que isso significa quando o job liga FGAC e a chave está `true` **não está
documentado em lugar nenhum que este repositório vigie**. Ver a §7 de
[`../glue/lakeformation-fgac.md`](../glue/lakeformation-fgac.md), que registra a
lacuna.

**Nenhuma regra desta área julga a combinação, e a razão foi medida.** Uma regra
para ela foi escrita, ganhou fixture, e saiu: a chave é um dos dois marcadores de
Full Table Access que `sparkforge/facts/lakeformation.py` procura, então com FGAC
ligado o `access_model` sai sempre como `model: "both"` e `SF-LF-005` acusa a mesma
entrada — a regra específica nunca disparava sozinha, e a localização que ela
acrescentava já está no achado da outra. O registro está em `V-ICE-3`, no cabeçalho
de `rules/catalog/iceberg.yaml`.

FGAC e Full Table Access são mutuamente exclusivos por job (§5 do mesmo documento).
Uma chave de um modelo presente num job que declara o outro é, no mínimo,
configuração que ninguém releu.

---

## 5. Limite declarado — versão de formato contra biblioteca embarcada

`iceberg.format_version` é extraído do `metadata.json` e diz de que versão de spec a
tabela **é**. A pergunta que fecharia a família ICE-VERSION do prompt de origem —
"esta tabela pede uma versão de formato que o Iceberg embarcado neste runtime não
suporta?" — **não tem produtor neste repositório**, e por duas razões independentes:

1. **`RuntimeContext.iceberg` não é observado por extrator nenhum.**
   `sparkforge/facts/runtime_detect.py` só o preenche derivando de `GLUE_MATRIX`
   quando alguma fonte trouxe `glue_version`, ou lendo a flag `--iceberg` da CLI.
   Fora do Glue, e sem alguém digitar a versão à mão, o campo é `""` — e é
   exatamente por isso que as cinco primeiras regras de `SF-ICE` abandonaram
   `runtime_scope: {iceberg: ...}` na Fase 5a (ver o cabeçalho de
   `rules/catalog/iceberg.yaml`).
2. **Nenhum fact carrega a versão da biblioteca Iceberg em uso.** O dump de
   metadata table não a traz, e o event log não a publica como propriedade.

Escrever a regra assim mesmo produziria um dos dois defeitos que este repositório
recusa: um guarda derivado de Glue apagando a área inteira num runtime EMR, ou um
limiar de versão comparado contra `""`. O veto está declarado em
`rules/catalog/iceberg.yaml` como `V-ICE-2`.

**Destravaria:** um fact que publique a versão da biblioteca Iceberg do runtime —
lido de `spark.conf_effective` se alguma propriedade a expuser, ou de um dump de
classpath do job.

---

## Fontes

| Fonte | URL | Coletada |
|---|---|---|
| Apache Iceberg — Spark Configuration | `https://iceberg.apache.org/docs/latest/spark-configuration/` | 2026-09-09 |
| AWS Glue — considerações de FGAC | `https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html` | 2026-09-09 |
| AWS Glue — Full Table Access | `https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html` | 2026-09-09 |
