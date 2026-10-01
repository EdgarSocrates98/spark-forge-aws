# Parquet footer — o motor sabe o que ele decide, e não o lê

**Data:** 2026-09-09
**Estado:** desenho aprovado, implementação não iniciada
**Frente:** 1 de 3 da triagem dos dois prompts da raiz (`prompt_evo_20.md` §8 e
`prompt_especialization_spark_forge.md` §23-25)

---

## 1. O que está errado hoje

`knowledge/storage/parquet-layout.md` **já explica** o que o footer decide:

> Pruning acontece em nível de row group, usando as estatísticas do footer.
> [...] Estatística min/max só é útil se os valores estiverem **agrupados**.
> Dado ordenado aleatoriamente faz cada row group ter min/max cobrindo quase
> todo o domínio → nenhum row group pode ser descartado → pruning inútil apesar
> de existir estatística.

E o §6 do mesmo documento manda, no passo 7 do diagnóstico: *"Verificar sort
order vs. colunas de filtro de alta cardinalidade."*

**Nada no motor lê o footer.** Medido em 2026-09-09:

- **zero** kind `parquet.*` entre os 195 que os extratores declaram;
- as cinco regras da área `SF-PQ` julgam por outra coisa:

| regra | `requires_facts` | o que ela vê |
|---|---|---|
| `SF-PQ-001` | `s3.prefix_summary` | tamanho de arquivo, da **listagem S3** |
| `SF-PQ-002` | `plan.file_scan` | `PartitionFilters` **declarados no plano** |
| `SF-PQ-003` | `s3.prefix_summary` | compressão pelo **nome do arquivo** |
| `SF-PQ-004` | `plan.file_scan` | `ReadSchema` **do plano** |
| `SF-PQ-005` | `s3.prefix_summary` + `catalog.table_partitions` | contagem por partição |

Nenhuma abre um arquivo. **Row group, estatística, dicionário, page index,
bloom filter e codec por coluna são invisíveis para o motor inteiro** — e são
exatamente o que o próprio `knowledge/` declara como a alavanca.

O modo de falha que isso produz é específico e caro: uma tabela com arquivos de
512 MB passa por `SF-PQ-001` (tamanho ótimo), tem `PartitionFilters` no plano e
passa por `SF-PQ-002`, e **lê a tabela inteira** — porque os row groups não
podem ser descartados. O motor diz que está tudo bem, e a leitura custa 40×.

---

## 2. As duas camadas

### 2.1 Coletor — `sparkforge/collect/parquet_footer.py`

Lê **só o footer**, nunca o dado. Um artefato JSON por prefixo coletado, no
molde de `collect/cloudwatch_logs.py`.

`pyarrow` entra como dependência **opcional**, pelo mesmo caminho que `boto3`:
`require_pyarrow()` no molde de `require_boto3()`, importado sob demanda e nunca
no topo. O núcleo determinístico continua com `PyYAML` + `jsonschema` e mais
nada — quem roda `judge` sobre um artefato já coletado não precisa de pyarrow.

**Amostragem é declarada, nunca inventada.** Ler o footer custa um round-trip
por arquivo, e uma tabela com 100 000 arquivos não é lida inteira. O operador
declara `--max-files`, e o artefato registra `files_seen`, `files_read` e
`sampling` — um censo parcial que se anuncia como parcial. Escolher a amostra em
silêncio seria escolher o diagnóstico.

### 2.2 Extrator — `sparkforge/facts/parquet_footer.py`

```
parquet.file             num_rows, num_row_groups, total_byte_size, created_by, format_version
parquet.row_group        num_rows, total_byte_size, por (arquivo, índice)
parquet.column_profile   POR COLUNA, agregado sobre os row groups
parquet.footer_analyzed  o censo: arquivos lidos, row groups, colunas
parquet.unresolved       recusa nomeada
```

**`parquet.column_chunk` NÃO existe, e a ausência é decisão.** Um arquivo com
100 row groups e 50 colunas produziria 5 000 facts que não decidem nada
sozinhos, e `facts.json` é barramento de handoff committado. O que decide é o
**perfil agregado por coluna**, no molde de `iceberg.files_summary` e
`spark.job.spill_summary`.

`parquet.column_profile` carrega, por coluna:

| medida | o que é |
|---|---|
| `stats_coverage` | fração dos row groups com estatística gravada |
| `min_max_coverage` | fração com `min`/`max` de fato presentes |
| `dictionary_coverage` | fração com dictionary page |
| `page_index_coverage` | fração com column index **e** offset index |
| `bloom_coverage` | fração com bloom filter |
| `compression_ratio` | descomprimido / comprimido |
| `null_fraction` | nulos sobre valores |

E `attrs` com `codecs` (a lista dos observados — mais de um no mesmo arquivo é
sinal próprio) e `physical_type`.

### 2.3 A medida que ninguém tem: sobreposição de min/max

É o §2 do `knowledge/storage/parquet-layout.md` virando número.

Para cada coluna de tipo **numérico ou temporal**, com min/max presentes em
todos os row groups:

```
largura_do_dominio = max(todos os max) - min(todos os min)
cobertura_do_rg    = (max_rg - min_rg) / largura_do_dominio
avg_range_coverage = média das coberturas
```

Leitura:

- `avg_range_coverage ≈ 1/N` → dado agrupado; cada row group cobre a sua fatia,
  e o pruning funciona;
- `avg_range_coverage ≈ 1.0` → dado espalhado; **cada row group cobre quase todo
  o domínio, e nenhum pode ser descartado** — pruning inútil apesar de a
  estatística existir.

A medida companheira, e é ela que o operador lê:
`expected_row_groups_scanned = avg_range_coverage × num_row_groups` — quantos
row groups um predicado de igualdade não consegue descartar.

**O que essa medida NÃO é, declarado junto com ela:** ela assume o predicado
**uniformemente distribuído sobre o domínio observado**. É uma propriedade do
LAYOUT, não uma previsão do job — um filtro que sempre pede o último dia de uma
tabela ordenada por data lê pouco mesmo com cobertura alta. Ela nomeia layout
que **não pode** podar, nunca job que vai ler muito.

**Recusa nomeada onde a medida não se sustenta:**

| situação | `parquet.unresolved` com `reason` |
|---|---|
| tipo não ordenável numericamente (string, binário) | `tipo_sem_dominio_numerico` |
| estatística ausente em algum row group | `estatistica_incompleta` |
| um único row group no arquivo | `row_group_unico` |
| domínio de largura zero (coluna constante) | `dominio_degenerado` |

Comparar min/max lexicográfico de string produziria um número com cara de
medida e sem significado de distância — e é por isso que a recusa existe em vez
do palpite.

---

## 3. As regras

Área **`SF-PQ`**, continuando de `SF-PQ-005`. Cada uma exige `requires_facts` do
que realmente lê.

| id | afirma | companheiro |
|---|---|---|
| `SF-PQ-006` | row group fora da faixa que o `knowledge/` declara | `parquet.row_group` |
| `SF-PQ-007` | estatística ausente ou parcial — pruning por row group **impossível** | `parquet.column_profile` |
| `SF-PQ-008` | estatística presente e **inútil**: cobertura alta, dado espalhado | `parquet.column_profile` + `sql.predicate` ou `plan.file_scan` |
| `SF-PQ-009` | codec divergente entre arquivos do mesmo prefixo | `parquet.column_profile` |

`SF-PQ-008` é a regra que justifica a frente, e ela **exige a coluna de filtro
ao lado**: cobertura alta numa coluna que ninguém filtra não é defeito. Sem
`sql.predicate` ou `plan.file_scan` no case, a regra é pulada com o que falta
nomeado — a mesma disciplina de `SF-ERR-003`.

**Fica de fora:** page index e bloom filter **não viram regra** nesta frente.
Eles são medidos e publicados em `parquet.column_profile`, e param aí: o custo
de gravá-los e o ganho de tê-los dependem do predicado real do consumidor, e
nenhuma fonte deste repositório declara o limiar. Publicar a medida sem a regra
é a diferença entre relatar e acusar.

---

## 4. O que fica de fora

- **Nenhuma leitura de dado.** Só o footer. Um extrator que lê linha estaria
  lendo dado de produção para diagnosticar layout.
- **Nenhuma estimativa de custo ou de ganho.** `expected_row_groups_scanned` é
  propriedade do layout; "você economizaria X reordenando" exige o run que não
  aconteceu (regra 13).
- **Nenhuma recomendação de sort key.** A regra aponta a coluna filtrada com
  cobertura alta; **qual** ordenação escolher depende dos outros consumidores, e
  é decisão do operador.
- **Nenhum score de saúde.** O prompt pede `PARQUET HEALTH` com um número
  agregado; o repo publica as medidas separadas, porque um score dilui a
  diferença entre "sem estatística" e "estatística inútil", que pedem consertos
  opostos.

---

## 5. Gates que a entrega move

- extrator novo nas **duas listas manuais** de teste e na medida de snippet;
- kinds novos em `EMITTED_KINDS`; o total sobe de 195;
- coletor + verbo `analyze` movem `docs/surface.lock.json` — crescimento
  declarado no commit (regra 26);
- área `SF-PQ` **já tem rota**; as regras novas não pedem rota nova, mas
  `tests/test_rule_scope_by_nature.py` e `test_fixtures_kind_coverage.py`
  cobram fixture que dispare cada uma;
- `pyproject.toml` ganha o extra `parquet` — e é a **primeira** dependência
  opcional deste repositório fora de `aws` e `mcp`.

---

## 6. Testes

- footer com 3 row groups ordenados → `avg_range_coverage ≈ 1/3`;
- **o mesmo dado embaralhado** → cobertura ≈ 1, e é o par que prova que a medida
  mede ordenação e não tamanho;
- coluna string → `parquet.unresolved: tipo_sem_dominio_numerico`, e **não** um
  número lexicográfico;
- arquivo com um row group só → `row_group_unico`, e a regra cala;
- estatística desligada na escrita → `stats_coverage: 0`, `SF-PQ-007` dispara e
  `SF-PQ-008` **não** — a segunda precisa da estatística que a primeira diz
  faltar;
- `SF-PQ-008` sem `sql.predicate` no case → pulada, com o que falta nomeado;
- amostragem declarada: `files_read < files_seen` chega em
  `parquet.footer_analyzed`, e nenhum fact afirma sobre o que não foi lido.
