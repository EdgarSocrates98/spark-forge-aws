# SparkForge AWS — Configuração Spark derivada: o valor que a medida sustenta, e a procedência de cada propriedade

> Subprojeto G. Fecha o critério 17 do §41 do `prompt_tunning_foco_spark.md`
> (derivar Spark confs) e o item P1 "derived Spark configurations" mais o
> "parallelism calculator" da mesma onda. Origem: §10, §11, §33, §34 e §36.

## 1. Contexto: a última lacuna de capacidade do documento de origem

A auditoria em `docs/superpowers/STATUS.md` deixou duas linhas abertas depois do
subprojeto F. Esta é a maior das duas, e é a que o documento de origem coloca
em letras grandes:

> `spark.sql.shuffle.partitions` passa a ser **DERIVED**, e não **HARDCODED**.

Hoje o catálogo **julga** configuração que já existe — `SF-UI` lê
`spark.conf_effective`, `SF-PY` lê `pyspark.conf_set`, `SF-EMR` lê
`emr.configuration`. Nada no repositório **deriva** um valor a partir de uma
medida. Medido: a busca por `shuffle.partitions` em `sparkforge/` encontra um
único módulo, `facts/terraform.py`, e ele **lê** a propriedade de um `.tf` — não
propõe nenhum valor.

### 1.1 O que já está medido, e por isso pode sustentar derivação

| Fonte | O que ela dá |
|---|---|
| `spark.stage.shuffle` | `write_bytes` e `read_bytes` por stage, medidos do event log |
| `spark.conf_effective` | o valor que o motor **aplicou**, uma chave por fact |
| `pyspark.conf_set` | o que o **código** pediu |
| `tf.spark_conf` | o que o **Terraform** declarou |
| `spark.runtime_version` | a versão de Spark do run |
| `facts/runtime_matrix.py` | o mapa Glue → Spark, com evidência versionada |

As quatro primeiras respondem perguntas diferentes, e é essa diferença que o
§36 do documento pede: uma propriedade que vale 200 sem que código, Terraform
ou operador tenham pedido veio do default ou do cluster, e isso muda o que
fazer com ela.

## 2. Escopo

**Dentro:**

1. Derivar `spark.sql.shuffle.partitions` a partir do shuffle **medido**, com a
   fórmula e a base declaradas dentro da resposta.
2. Procedência por propriedade (§36): de onde veio o valor efetivo de cada
   propriedade que este relatório toca.
3. Consciência de versão (§33): propriedade que não existe na versão de Spark
   do runtime não é proposta.
4. Nível de segurança por proposta (§34): `SAFE`, `REVIEW` ou `EXPERIMENTAL`.

**Fora:**

1. **Aplicar qualquer coisa.** A fronteira do projeto inteiro.
2. **Derivar propriedade sem base medida.** Memória, timeouts, speculation e
   os limiares de broadcast entram na lista de recusas **nomeadas**, cada uma
   com a medida que a destravaria — não como omissão.
3. **Um valor mágico global.** É exatamente o que o §10 recusa, e derivar sem
   base seria trocar um número mágico por outro com aparência de cálculo.
4. **Ordenar propostas por ganho estimado.** Mesmo contrafactual que o
   subprojeto E recusa por escrito.

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 Derivar é recomendar, e recomendação tem mecanismo próprio

Custo (E) e categoria de timeout (F) são fact porque são aritmética sobre
medida, sem escolha. Um valor **proposto** de configuração é escolha: existe um
alvo de tamanho de partição, e alvo é decisão. Por isso G segue o precedente de
`capacity` (D) e `finops` (E) — módulo de composição com verbo próprio, e não
extrator.

A alternativa recusada era emitir `spark.conf.derived` como fact. O motor de
regras julgaria um número que o próprio projeto propôs, e a regra passaria a
concordar com a recomendação em vez de julgar a evidência.

### 3.2 Só deriva o que a medida sustenta, e o resto é recusa nomeada

O §11 lista cerca de trinta propriedades. Uma só tem base medida hoje:
`spark.sql.shuffle.partitions`, contra `spark.stage.shuffle.write_bytes`.

As outras entram em `refused`, cada uma com a medida que a destravaria — por
exemplo, `spark.sql.autoBroadcastJoinThreshold` exigiria o tamanho serializado
do lado pequeno do join, que nem `plan.join` nem `spark.sql.join_input` dão
hoje. Listar a recusa é a diferença entre "não sei" e "não perguntei".

### 3.3 O alvo de tamanho de partição vem da documentação, não do gosto

`spark.sql.adaptive.advisoryPartitionSizeInBytes` tem default documentado de
64 MiB, e é o tamanho que o próprio AQE persegue ao coalescer. A derivação usa
esse número **como alvo declarado**, e o carrega na resposta:

```
shuffle_partitions = ceil(shuffle_write_bytes / target_partition_bytes)
```

Quando o run declara o próprio `advisoryPartitionSizeInBytes` em
`spark.conf_effective`, é esse valor que vale — o alvo do operador ganha do
default. A resposta diz qual dos dois usou.

### 3.4 AQE muda o que o número significa, e a versão decide

`knowledge/glue/runtime-matrix.md` registra: AQE é default desde Spark 3.2,
portanto default em Glue 4.0 e 5.x, e **não** em Glue 3.0.

Com AQE coalescendo, `shuffle.partitions` é um piso de paralelismo inicial que
o motor reduz com estatística real. Sem AQE, é o número final de partições. A
mesma derivação, portanto, tem duas explicações, e a versão decide qual sai —
recomendar "confie no AQE" para Glue 3.0 é erro de versão, e o arquivo de
conhecimento já diz isso.

### 3.5 Procedência por propriedade (§36), com precedência declarada

Para cada propriedade tocada, a resposta classifica de onde o valor efetivo
veio:

| classe | quando |
|---|---|
| `code` | `pyspark.conf_set` tem a chave |
| `terraform` | `tf.spark_conf` tem a chave |
| `runtime_or_cluster` | está em `spark.conf_effective` e ninguém no repositório pediu |
| `spark_default_explicit` | pedida com exatamente o valor default documentado |
| `unset` | não aparece em fonte nenhuma |

`spark_default_explicit` existe porque é o sintoma do §36: configuração que
alguém escreveu, ninguém mais entende, e que não muda nada.

### 3.6 Nível de segurança (§34), pelas listas do próprio documento

`SAFE` para o que não muda semântica nem custo de forma perceptível;
`REVIEW` para troca de paralelismo, broadcast hint, cache e capacidade;
`EXPERIMENTAL` para salting e reescrita de layout. A proposta desta fase —
paralelismo de shuffle — é `REVIEW` pela lista do documento, e a resposta nunca
omite o nível.

## 4. Modelo

### 4.1 O relatório

```
{
  "runtime": {"glue_version": ..., "spark_version": ..., "aqe_default": bool},
  "properties": [
    {"key": "spark.sql.shuffle.partitions",
     "current": {"value": ..., "provenance": <classe>, "evidence": [...]},
     "derived": {"value": ..., "formula": ..., "basis": {...}},
     "safety": "REVIEW",
     "supported_in_runtime": true,
     "explanation": <depende de AQE>}
  ],
  "refused": [{"reason": ..., "property": ..., "detail": ...}]
}
```

### 4.2 As recusas, cada uma com o seu nome

`no_shuffle_measured`, `runtime_unknown`, `property_not_in_version`,
`no_conf_observed`, `no_measured_basis` (uma por propriedade do §11 que não tem
fonte).

## 5. Superfície

Verbo de topo `sparkforge tune` e tool `sparkforge_tune`, pela mesma razão de
`capacity` e `finops`: consome facts já extraídos e não lê artefato nenhum.

## 6. Testes

`fixtures/tuning/`, com sete cenários: shuffle medido com AQE, o mesmo sem AQE
(Glue 3.0), alvo declarado pelo operador ganhando do default, propriedade vinda
do código, propriedade vinda do Terraform, propriedade default escrita à mão, e
o caso sem shuffle nenhum (recusa nomeada).

Garantias sobre o corpus inteiro:

1. Toda proposta carrega `formula` **e** `basis` não vazios.
2. Nenhuma proposta existe sem shuffle medido na entrada.
3. Toda proposta carrega `safety`.
4. Nada na saída aplica, nem ordena por ganho estimado.

## 7. Critérios de aceite

1. O valor derivado bate com a fórmula, provado por fixture com a conta escrita.
2. O alvo declarado pelo operador ganha do default, com teste.
3. A explicação muda com AQE, e a versão decide — com o par Glue 5.0 / Glue 3.0.
4. As cinco classes de procedência têm fixture.
5. Propriedade fora da versão não é proposta.
6. Toda recusa tem nome, e nenhuma é silenciosa.
