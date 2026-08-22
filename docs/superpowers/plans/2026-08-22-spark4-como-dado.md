# Spark 4 como dado (fase G1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar as mudanças de Spark 3.5→4.0→4.1 confirmadas em fonte oficial no primeiro conjunto de regras `SF-SPARK4`, alimentadas pelo extrator de migração que já existe.

**Architecture:** O conhecimento entra como documento em `knowledge/spark/`, com fonte e `retrieved`, vigiado pelo lock. Três kinds novos entram em `sparkforge/facts/migration.py` (observação pura, nenhum julgamento). Uma área nova `SF-SPARK4` em `rules/catalog/spark4.yaml` julga esses kinds com `runtime_scope` guardado por versão de **Spark**, não de Glue — a fronteira é do Apache, não da AWS, e vale igual em EMR. Nenhuma bifurcação do motor: `judge` e `assess` já fazem o resto.

**Tech Stack:** Python 3.10/3.11 (stdlib + PyYAML), pytest, o catálogo de regras e o modelo `Fact`/`Finding` existentes.

**Mapa de origem:** [`../../harness/GLUE6-GAP.md`](../../harness/GLUE6-GAP.md), seções 3 e 4.

---

## Ordem das fases — o mapa inteiro, e por que esta vem primeiro

`docs/harness/GLUE6-GAP.md` deixou 31 linhas em `NÃO EXISTE` ou `EXISTE PARCIAL`. Elas
não são independentes: metade não tem consumidor enquanto a outra metade não existir como
**dado**. A ordem abaixo é por dependência medida, não por ordem do prompt.

| fase | escopo | depende de | por que aqui |
|---|---|---|---|
| **G1** | Spark 4 como dado: knowledge, kinds novos, área `SF-SPARK4` | — | Glue 6.0 **é** Spark 4.1. Hoje o repositório tem uma única mudança de Spark 4 codificada (ANSI, em `SF-MIG-003`). Toda outra frente que fala de Glue 6 depende disto para ter o que dizer |
| **G2** | Compatibilidade binária: sufixo Scala, coordenadas Maven, ABI de wheel Python | G1 (para o `runtime_scope` por Spark) | `mig.jar_binary` e `mig.python_dep` já observam; falta o julgamento. É a quebra que a própria AWS chama de breaking change em `migrating-version-60.html` |
| **G3** | Iceberg 1.11 e spec v3 como dado: Variant, deletion vectors, row lineage, nanossegundo | — | Independente de G1/G2. É o segundo bloco de conhecimento que falta como dado |
| **G4** | `IcebergFeatureCompatibilityMatrix` + bloqueio por consumidor incompatível | **G3** | A matriz sem o conhecimento de G3 teria célula que o repositório não consegue provar — o que a §20 do prompt proíbe. `env.consumer` já existe e é a outra metade |
| **G5** | Lake Formation por operação × versão × FTA/FGAC × conta | G3 (Iceberg v3 muda o que a LF cobre) | Exige pesquisa própria e extensa; o grafo de permissão já existe como base |
| **G6** | Suítes de cenário por par de versões, holdout, evals | G1–G4 | Cenário de migração só é golden honesto quando as regras que ele deve disparar existem |
| **G7** | Docs dedicadas, guia de decisão, ADR | G1–G6 | Documentar antes de existir é o que a auditoria de lastro removeu de `docs/vnext/` |
| **avulsos** | TTL por domínio (§44), `RuntimeChangeGraph` (§41), `CapabilityRegistry` por capacidade (§74), preço com data e região (§51), benchmark por runtime (§52) | — | Cada um é pequeno e sem dependência. Encaixam em qualquer fase; nenhum bloqueia outro |

**O que continua fora, e por quê.** As skills das §9 e §12 (mais de quarenta arquivos) não
entram em fase nenhuma até G1 e G3 fecharem: skill é camada de apresentação sobre
conhecimento, e escrever quarenta arquivos que apontam para conhecimento inexistente é a
duplicação que o §73 do prompt manda evitar e a arquitetura prematura que o §87 proíbe.

---

## Escopo desta fase

Três kinds novos, três regras, um documento de conhecimento. Nada mais.

**Fora do escopo, deliberadamente:** APIs de pandas-on-Spark removidas fora da lista da
Task 3 (a cauda é longa e o valor cai rápido); mudanças de JDBC por dialeto (fase própria,
se algum dia houver evidência de uso); `spark.sql.ansi.enabled`, que `SF-MIG-003` já cobre
e cobrir de novo criaria dois achados para o mesmo problema.

## Convenções deste repositório que valem para todas as tasks

- Comentários e docstrings em português, explicando *por quê*, nunca *o quê*.
- `python -m ruff check sparkforge scripts tests` não pode acusar nada novo nos arquivos
  tocados. Limite de linha 100.
- Nenhum teste afirma contagem copiada (`len(rules) == 3`). Conte derivando, ou asserte
  estrutura.
- `Fact` é observação ancorada e **nunca** contém juízo nem limiar
  (`sparkforge/findings/models.py`). Limiar mora na regra.
- Todo extrator declara `EMITTED_KINDS` fechado. `migration` **já está** registrado em
  `tests/test_rules_catalog_reachability.py` e `tests/test_fixtures_kind_coverage.py`, então
  **kind novo sem golden derruba a suíte no mesmo commit**. Kind, regra e fixture entram
  juntos.
- `runtime_scope` guarda **versão de runtime**. O que gateia por natureza do artefato é
  `requires_facts`.
- Antes de commitar, rodar os gates de `docs/gates-por-mudanca.md` para "acrescentar ou
  alterar uma REGRA no catálogo", "dar `runtime_scope` a uma regra" e "acrescentar ou
  alterar um EXTRATOR de facts". Eles cobram listas escritas à mão que nada mais cobra.

## File Structure

| arquivo | responsabilidade |
|---|---|
| `knowledge/spark/spark4-migration.md` | criar — as mudanças 3.5→4.0→4.1 confirmadas, com fonte e `retrieved`. Prosa para humano e para o terceiro degrau de portabilidade |
| `knowledge/sources.lock.json` | modificar — as duas URLs de migração do Spark 4.1 passam a ser vigiadas |
| `knowledge/offline-manifest.json` | modificar — `sha256` do documento novo |
| `sparkforge/facts/migration.py` | modificar — três kinds novos em `EMITTED_KINDS` e os detectores deles |
| `rules/catalog/spark4.yaml` | criar — área `SF-SPARK4`, três regras |
| `rules/catalog/routing.yaml` | modificar — rota para a área nova |
| `agents/sf-runtime-specialist.md` | modificar — `SF-SPARK4` em `rule_areas` |
| `manifest.json` | modificar — `rule_count` |
| `fixtures/migration/spark4_removed_api/` | criar — golden do kind `mig.removed_api` |
| `fixtures/migration/spark4_renamed_conf/` | criar — golden do kind `mig.renamed_conf` |
| `fixtures/migration/spark4_dep_floor/` | criar — golden do kind `mig.python_dep` disparando SF-SPARK4-003 |
| `tests/test_facts_migration.py` | modificar — um teste por kind novo |
| `tests/test_spark4_rules.py` | criar — as três regras dentro e fora do `runtime_scope` |
| `tests/test_rule_scope_by_nature.py` | modificar — `SPARK_VERSIONED` ganha as três regras |
| `docs/harness/GLUE6-GAP.md` | modificar — as linhas das seções 3 e 4 mudam de classificação |
| `docs/superpowers/STATUS.md` | modificar — seção da fase |

---

### Task 1: Conhecimento de Spark 4 como documento vigiado

**Files:**
- Create: `knowledge/spark/spark4-migration.md`
- Modify: `knowledge/sources.lock.json` (gerado por script, não à mão)
- Modify: `knowledge/offline-manifest.json` (gerado por script, não à mão)

- [ ] **Step 1: Escrever o documento**

Criar `knowledge/spark/spark4-migration.md` com este conteúdo. Todo item veio das duas
fontes oficiais citadas na seção `## Fontes`, lidas em 2026-08-22 — nenhum foi inferido.

```markdown
# Migração Apache Spark 3.5 → 4.0 → 4.1

Glue 6.0 roda Spark 4.1.1; Glue 5.1 roda 3.5.6; Glue 4.0 roda 3.3.0. Um salto de Glue 4.0
para 6.0 atravessa as duas fronteiras de uma vez. Ver
[`../glue/runtime-matrix.md`](../glue/runtime-matrix.md).

## 1. ANSI mode

Ligado por padrão a partir de 4.0 (`spark.sql.ansi.enabled`). No SparkForge isso é
`SF-MIG-003`, guardado por Glue 6.0 — não é repetido aqui como regra.

## 2. Configurações que mudaram de nome em 4.0

As configs de rebase de data/hora perderam o prefixo `legacy`. O nome antigo **não** é lido:

| nome em 3.5 | nome em 4.0+ |
|---|---|
| `spark.sql.legacy.parquet.int96RebaseModeInWrite` | `spark.sql.parquet.int96RebaseModeInWrite` |
| `spark.sql.legacy.parquet.datetimeRebaseModeInWrite` | `spark.sql.parquet.datetimeRebaseModeInWrite` |
| `spark.sql.legacy.parquet.int96RebaseModeInRead` | `spark.sql.parquet.int96RebaseModeInRead` |
| `spark.sql.legacy.avro.datetimeRebaseModeInWrite` | `spark.sql.avro.datetimeRebaseModeInWrite` |
| `spark.sql.legacy.avro.datetimeRebaseModeInRead` | `spark.sql.avro.datetimeRebaseModeInRead` |

O codec Parquet `lz4raw` deixou de ser aceito; o nome passou a ser `lz4_raw`.

O risco é o mesmo de `fs.s3.consistent` no Glue 5 (ver `SF-MIG-002`): **silêncio**. A chave
antiga não causa erro, e quem lê o job vê uma configuração que parece ativa e não está.

## 3. APIs de pandas-on-Spark removidas em 4.0

Removidas sem substituto compatível por assinatura:

| removida | substituta |
|---|---|
| `DataFrame.append`, `Series.append` | `ps.concat` |
| `DataFrame.iteritems`, `Series.iteritems` | `.items` |
| `DataFrame.to_koalas` | `DataFrame.pandas_api` |
| `DataFrame.koalas` | `DataFrame.pandas_on_spark` |
| `DataFrame.get_dtype_counts` | `DataFrame.dtypes.value_counts()` |
| `Series.is_monotonic`, `Index.is_monotonic` | `.is_monotonic_increasing` |
| `DataFrameGroupBy.backfill` | `DataFrameGroupBy.bfill` |
| `DataFrameGroupBy.pad` | `DataFrameGroupBy.ffill` |
| `DataFrame.mad`, `Series.mad` | sem substituto |
| `Int64Index`, `Float64Index` | `Index` |

`from pyspark.sql.functions import *` deixou de exportar `DataFrame`, `Column` e
`StructType`; eles vêm de `pyspark.sql` e `pyspark.sql.types`.

## 4. Piso de dependência Python em 4.0 e 4.1

| pacote | piso em 4.0 | piso em 4.1 |
|---|---|---|
| PyArrow | 11.0.0 | 15.0.0 |
| pandas | 2.0.0 | 2.2.0 |
| NumPy | 1.21 | 1.21 |

Python 3.8 deixou de ser suportado em 4.0, e 3.9 em 4.1. Glue 6.0 roda Python 3.13, então a
fronteira do interpretador não morde ali — o que morde é o **pin** de um pacote no
`requirements.txt` do job, que continua valendo o que estava escrito.

## 5. Mudanças de comportamento sem sinal no código

Estas não são detectáveis por análise estática do job; entram aqui como conhecimento para
quem desenha o plano de regressão:

- `spark.sql.legacy.timeParserPolicy` e `spark.sql.legacy.ctePrecedencePolicy` passam de
  `EXCEPTION` para `CORRECTED` por padrão.
- Codec padrão do ORC passa de `snappy` para `zstd` (`spark.sql.orc.compression.codec`).
- `spark.sql.maxSinglePartitionBytes` passa de `Long.MaxValue` para `128m`.
- Cast de timestamp com overflow fora do ANSI passa a devolver `null` em vez do valor
  circular.
- Storage-Partitioned Join passa a ligado por padrão.

## Fontes

- Migration Guide: SQL, Datasets and DataFrame — Apache Spark 4.1.1. https://spark.apache.org/docs/4.1.1/sql-migration-guide.html (retrieved 2026-08-22)
- Upgrading PySpark — Apache Spark 4.1.1. https://spark.apache.org/docs/4.1.1/api/python/migration_guide/pyspark_upgrade.html (retrieved 2026-08-22)
```

- [ ] **Step 2: Registrar as fontes no lock**

Run:
```bash
python scripts/refresh_knowledge.py --update --offline
```
Expected: as duas URLs aparecem na saída, ligadas a `knowledge/spark/spark4-migration.md`.

- [ ] **Step 3: Gravar o checksum no manifesto offline**

Run:
```bash
python - <<'PY'
import json, pathlib
from sparkforge.tools.offline import _content_sha256
p = pathlib.Path("knowledge/offline-manifest.json")
d = json.loads(p.read_text(encoding="utf-8"))
alvo = "knowledge/spark/spark4-migration.md"
d["documents"].append(
    {"path": alvo, "title": "spark4-migration", "sha256": _content_sha256(pathlib.Path(alvo))}
)
d["documents"].sort(key=lambda x: x["path"])
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
python scripts/verify_offline_bundle.py
```
Expected: `"failed": []`, `"ok": true`, e `"checked"` uma unidade maior que antes.

- [ ] **Step 4: Rodar os gates de knowledge**

Run: `python -m pytest tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add knowledge/spark/spark4-migration.md knowledge/sources.lock.json knowledge/offline-manifest.json
git commit -m "docs(knowledge): mudancas de Spark 3.5 a 4.1 confirmadas em fonte oficial"
```

---

### Task 2: Kind `mig.renamed_conf` — config que perdeu o prefixo `legacy`

**Files:**
- Modify: `sparkforge/facts/migration.py`
- Test: `tests/test_facts_migration.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_facts_migration.py`:

```python
class TestConfigRenomeadaNoSpark4:
    def test_reconhece_a_chave_de_rebase_com_prefixo_legacy(self, tmp_path):
        (tmp_path / "job.py").write_text(
            'spark.conf.set("spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")\n',
            encoding="utf-8",
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        renomeadas = [f for f in facts if f.kind == "mig.renamed_conf"]
        assert len(renomeadas) == 1
        assert renomeadas[0].attrs["key"] == "spark.sql.legacy.parquet.int96RebaseModeInWrite"
        assert renomeadas[0].attrs["renamed_to"] == "spark.sql.parquet.int96RebaseModeInWrite"

    def test_codec_lz4raw_e_observado_pelo_mesmo_kind(self, tmp_path):
        (tmp_path / "job.py").write_text(
            'df.write.option("compression", "lz4raw").parquet(destino)\n', encoding="utf-8"
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        renomeadas = [f for f in facts if f.kind == "mig.renamed_conf"]
        assert [f.attrs["renamed_to"] for f in renomeadas] == ["lz4_raw"]

    def test_chave_legacy_que_nao_foi_renomeada_nao_vira_este_kind(self, tmp_path):
        """`spark.sql.legacy.timeParserPolicy` continua existindo com esse nome
        em Spark 4. Tratar toda chave `legacy.` como renomeada acusaria config
        correta -- e `mig.legacy_conf` ja observa a familia inteira."""
        (tmp_path / "job.py").write_text(
            'spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")\n', encoding="utf-8"
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        assert [f for f in facts if f.kind == "mig.renamed_conf"] == []
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_facts_migration.py::TestConfigRenomeadaNoSpark4 -v`
Expected: FAIL — nenhum fact com kind `mig.renamed_conf` é emitido.

- [ ] **Step 3: Implementar**

Em `sparkforge/facts/migration.py`, acrescentar `"mig.renamed_conf"` a `EMITTED_KINDS` e,
junto das outras constantes de regex:

```python
# Configs que MUDARAM DE NOME no Spark 4.0 -- o nome antigo nao e lido e nao
# reclama, entao o job segue rodando com a configuracao que quem le acha que
# esta ativa. Mesmo modo de falha de `fs.s3.consistent` no Glue 5 (SF-MIG-002):
# silencio, nao erro. Mapa fechado de propósito: `spark.sql.legacy.` continua
# sendo um prefixo VALIDO em Spark 4 (`timeParserPolicy`, `ctePrecedencePolicy`),
# e tratar a familia inteira como renomeada acusaria config correta.
_RENAMED_CONF: dict[str, str] = {
    "spark.sql.legacy.parquet.int96RebaseModeInWrite": (
        "spark.sql.parquet.int96RebaseModeInWrite"
    ),
    "spark.sql.legacy.parquet.datetimeRebaseModeInWrite": (
        "spark.sql.parquet.datetimeRebaseModeInWrite"
    ),
    "spark.sql.legacy.parquet.int96RebaseModeInRead": (
        "spark.sql.parquet.int96RebaseModeInRead"
    ),
    "spark.sql.legacy.avro.datetimeRebaseModeInWrite": (
        "spark.sql.avro.datetimeRebaseModeInWrite"
    ),
    "spark.sql.legacy.avro.datetimeRebaseModeInRead": (
        "spark.sql.avro.datetimeRebaseModeInRead"
    ),
    # Nao e config: e valor de `compression`. Entra no mesmo kind porque o
    # fato observado e o mesmo -- um nome que o runtime alvo nao aceita mais.
    "lz4raw": "lz4_raw",
}
```

e um detector, chamado de `_config_facts` no mesmo laço que já varre as linhas:

```python
def _renamed_conf_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Observa nome antigo de config renomeada no Spark 4.0.

    Le o mesmo token entre aspas que `_config_facts` ja le -- nao reparseia a
    linha de outro jeito, para que as duas leituras nunca discordem sobre o que
    esta escrito ali.
    """
    facts: list[Fact] = []
    for numero, linha in enumerate(text.splitlines(), start=1):
        for token in _CONF_KEY_RE.findall(linha):
            novo = _RENAMED_CONF.get(token)
            if novo is None:
                continue
            facts.append(
                Fact(
                    kind="mig.renamed_conf",
                    subject=_source_subject(anchor, numero),
                    attrs={"key": token, "renamed_to": novo},
                    provenance=provenance,
                )
            )
    return facts
```

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_facts_migration.py::TestConfigRenomeadaNoSpark4 -v`
Expected: PASS.

- [ ] **Step 5: Criar o golden do kind**

Criar `fixtures/migration/spark4_renamed_conf/` com `meta.yaml`, `input/job.py` e
`expected/`, no formato dos vizinhos. Gerar os arquivos de `expected/` com o mesmo
caminho de código do runner:

```bash
mkdir -p fixtures/migration/spark4_renamed_conf/input fixtures/migration/spark4_renamed_conf/expected
cat > fixtures/migration/spark4_renamed_conf/input/job.py <<'EOF'
spark.conf.set("spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")
df.write.option("compression", "lz4raw").parquet(destino)
EOF
```

`meta.yaml`:

```yaml
name: spark4_renamed_conf
proves: >
  Duas linhas que rodam sem erro em Spark 3.5 e passam a ser inertes em 4.0 -- a
  config de rebase perdeu o prefixo `legacy` e o codec `lz4raw` virou `lz4_raw`.
  Nenhuma das duas falha na submissao do job: o Spark ignora a chave que nao
  conhece, e quem le o codigo ve uma configuracao que parece ativa. SF-SPARK4-001
  dispara.
runtime:
  glue: "6.0"
  spark: "4.1.1"
  python: "3.13"
  iceberg: "1.11.0"
expects_kinds:
  - mig.renamed_conf
  - migration.module_analyzed
expects_rules:
  - SF-SPARK4-001
```

> Confirme o nome exato do kind sentinela lendo `EMITTED_KINDS` em
> `sparkforge/facts/migration.py` antes de escrever `expects_kinds`; a lista precisa
> bater com o que o extrator emite para aquele arquivo, e `test_declared_kinds_all_present`
> compara conjunto com conjunto.

Gerar `expected/facts.json` e `expected/findings.json` rodando o mesmo par
extrator + `judge` que `tests/test_fixtures_golden_migration.py` usa.

- [ ] **Step 6: Rodar os gates do extrator**

Run:
```bash
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py \
  tests/test_fixtures_golden_migration.py -q
```
Expected: PASS. Se `test_fixtures_kind_coverage` reclamar de kind sem golden, o golden da
Step 5 não está sendo encontrado — confira o nome do diretório.

- [ ] **Step 7: Commit**

```bash
git add sparkforge/facts/migration.py tests/test_facts_migration.py fixtures/migration/spark4_renamed_conf
git commit -m "feat(facts): observa config de Spark que mudou de nome na versao 4.0"
```

---

### Task 3: Kind `mig.removed_api` — API de pandas-on-Spark removida em 4.0

**Files:**
- Modify: `sparkforge/facts/migration.py`
- Test: `tests/test_facts_migration.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
class TestApiRemovidaNoSpark4:
    def test_reconhece_metodo_removido(self, tmp_path):
        (tmp_path / "job.py").write_text("novo = base.append(extra)\n", encoding="utf-8")
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        removidas = [f for f in facts if f.kind == "mig.removed_api"]
        assert [f.attrs["symbol"] for f in removidas] == ["append"]
        assert removidas[0].attrs["replacement"] == "ps.concat"

    def test_reconhece_propriedade_removida_sem_parenteses(self, tmp_path):
        (tmp_path / "job.py").write_text("if serie.is_monotonic:\n    pass\n", encoding="utf-8")
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        removidas = [f for f in facts if f.kind == "mig.removed_api"]
        assert [f.attrs["symbol"] for f in removidas] == ["is_monotonic"]

    def test_o_nome_substituto_nao_e_confundido_com_o_removido(self, tmp_path):
        """`is_monotonic_increasing` CONTEM `is_monotonic`. Casar por substring
        acusaria justamente o codigo ja corrigido -- o falso positivo mais caro
        possivel, porque ensina a ignorar a regra."""
        (tmp_path / "job.py").write_text(
            "if serie.is_monotonic_increasing:\n    pass\n", encoding="utf-8"
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        assert [f for f in facts if f.kind == "mig.removed_api"] == []

    def test_metodo_de_outro_objeto_com_o_mesmo_nome_tambem_e_observado(self, tmp_path):
        """`.append(` num `list` Python nao e a API removida. O extrator OBSERVA
        assim mesmo -- ele nao tem tipo para distinguir, e inventar um seria
        juizo dentro do extrator. Quem separa e a regra, que exige o job usar
        pandas-on-Spark (`requires_facts` do lado dela)."""
        (tmp_path / "job.py").write_text("acc = []\nacc.append(1)\n", encoding="utf-8")
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        assert len([f for f in facts if f.kind == "mig.removed_api"]) == 1
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_facts_migration.py::TestApiRemovidaNoSpark4 -v`
Expected: FAIL — kind `mig.removed_api` não existe.

- [ ] **Step 3: Implementar**

Acrescentar `"mig.removed_api"` a `EMITTED_KINDS` e:

```python
# APIs de pandas-on-Spark removidas no Spark 4.0. Mapa fechado: so entra aqui
# o que a fonte oficial lista como REMOVIDO, nunca o que ela chama de
# deprecado -- deprecado ainda roda, e acusar os dois junto apagaria a
# diferenca entre "quebra" e "vai quebrar".
_REMOVED_API: dict[str, str] = {
    "append": "ps.concat",
    "iteritems": ".items",
    "to_koalas": "DataFrame.pandas_api",
    "koalas": "DataFrame.pandas_on_spark",
    "get_dtype_counts": "DataFrame.dtypes.value_counts()",
    "is_monotonic": ".is_monotonic_increasing",
    "backfill": ".bfill",
    "pad": ".ffill",
    "mad": "",
    "Int64Index": "Index",
    "Float64Index": "Index",
}

# `\b` no fim e o que separa `is_monotonic` de `is_monotonic_increasing`: sem
# ele o casamento por substring acusaria o codigo JA CORRIGIDO, que e o falso
# positivo que faz um operador aprender a ignorar a regra inteira.
_REMOVED_API_RES: tuple[tuple[re.Pattern[str], str, str], ...] = tuple(
    (re.compile(r"\." + re.escape(nome) + r"\b"), nome, substituto)
    if nome[0].islower()
    else (re.compile(r"\b" + re.escape(nome) + r"\b"), nome, substituto)
    for nome, substituto in _REMOVED_API.items()
)


def _removed_api_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Observa uso de API removida no Spark 4.0.

    Le a linha crua, nao a AST: `pyspark_ast.py` ja existe e resolve chamada com
    precisao, mas exige que o arquivo seja Python VALIDO para a versao que roda
    este processo -- e uma parte do corpus que este extrator varre e justamente
    codigo escrito para um interpretador mais antigo. Leitura por linha degrada
    para "observei um nome"; leitura por AST degradaria para "nao observei
    nada", que e falso negativo silencioso.
    """
    facts: list[Fact] = []
    for numero, linha in enumerate(text.splitlines(), start=1):
        for padrao, nome, substituto in _REMOVED_API_RES:
            if padrao.search(linha):
                facts.append(
                    Fact(
                        kind="mig.removed_api",
                        subject=_source_subject(anchor, numero),
                        attrs={"symbol": nome, "replacement": substituto},
                        provenance=provenance,
                    )
                )
    return facts
```

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_facts_migration.py::TestApiRemovidaNoSpark4 -v`
Expected: PASS.

- [ ] **Step 5: Criar o golden**

Criar `fixtures/migration/spark4_removed_api/` no mesmo formato da Task 2, com
`input/job.py`:

```python
import pyspark.pandas as ps

base = ps.read_parquet(origem)
novo = base.append(extra)
```

`meta.yaml` com `expects_rules: [SF-SPARK4-002]` e o mesmo bloco `runtime` da Task 2.

- [ ] **Step 6: Rodar os gates do extrator**

Run:
```bash
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py \
  tests/test_fixtures_golden_migration.py -q
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add sparkforge/facts/migration.py tests/test_facts_migration.py fixtures/migration/spark4_removed_api
git commit -m "feat(facts): observa API de pandas-on-Spark removida no Spark 4.0"
```

---

### Task 4: Área `SF-SPARK4` com as três regras

**Files:**
- Create: `rules/catalog/spark4.yaml`
- Test: `tests/test_spark4_rules.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_spark4_rules.py`:

```python
from sparkforge.facts import migration
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

SPARK_4 = {"glue": "6.0", "spark": "4.1.1", "python": "3.13"}
SPARK_35 = {"glue": "5.1", "spark": "3.5.6", "python": "3.11"}


def _facts(tmp_path, corpo: str):
    (tmp_path / "job.py").write_text(corpo, encoding="utf-8")
    return migration.extract_migration_tree(tmp_path, repo_root=tmp_path)


class TestConfigRenomeada:
    CORPO = 'spark.conf.set("spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")\n'

    def test_dispara_em_spark_4(self, tmp_path):
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_4)
        assert "SF-SPARK4-001" in {f.rule_id for f in findings}

    def test_nao_dispara_em_spark_35(self, tmp_path):
        """A chave antiga e a CERTA em 3.5. Acusa-la ali seria mandar consertar
        o que nao esta quebrado."""
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_35)
        assert "SF-SPARK4-001" not in {f.rule_id for f in findings}


class TestApiRemovida:
    CORPO = "import pyspark.pandas as ps\nnovo = base.append(extra)\n"

    def test_dispara_em_spark_4(self, tmp_path):
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_4)
        assert "SF-SPARK4-002" in {f.rule_id for f in findings}

    def test_nao_dispara_em_spark_35(self, tmp_path):
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_35)
        assert "SF-SPARK4-002" not in {f.rule_id for f in findings}


class TestPisoDeDependencia:
    def test_pyarrow_abaixo_do_piso_dispara(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pyarrow==11.0.0\n", encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        findings = judge(facts, load_catalog(), SPARK_4)
        assert "SF-SPARK4-003" in {f.rule_id for f in findings}

    def test_pyarrow_no_piso_nao_dispara(self, tmp_path):
        """O piso do Spark 4.1 e 15.0.0. Acusar exatamente 15.0.0 tornaria a
        regra ruido em todo job que ja migrou."""
        (tmp_path / "requirements.txt").write_text("pyarrow==15.0.0\n", encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        findings = judge(facts, load_catalog(), SPARK_4)
        assert "SF-SPARK4-003" not in {f.rule_id for f in findings}
```

- [ ] **Step 2: Rodar para ver falhar**

Run: `python -m pytest tests/test_spark4_rules.py -v`
Expected: FAIL — nenhuma regra `SF-SPARK4-*` existe no catálogo.

- [ ] **Step 3: Escrever o catálogo**

Criar `rules/catalog/spark4.yaml` com cabeçalho `area: SF-SPARK4` e as três regras. Cada
uma declara `runtime_scope: {spark: ">=4.0.0"}` — a fronteira é do Apache, não da AWS, e
vale igual num EMR com Spark 4. Cada regra precisa dos campos obrigatórios listados em
`rules/catalog/README.md`: `id`, `category`, `title`, `requires_facts`, `when`, `status`,
`severity_default`, `runtime_scope`, `explanation`, `proposed_change`, `risks`,
`tradeoffs`, `validation`, `rollback`, `sources`.

Condições:

```yaml
  - id: SF-SPARK4-001
    requires_facts: [mig.renamed_conf]
    when:
      all:
        - fact: mig.renamed_conf
    severity_default: P2
    runtime_scope: {spark: ">=4.0.0"}

  - id: SF-SPARK4-002
    requires_facts: [mig.removed_api]
    when:
      all:
        - fact: mig.removed_api
    severity_default: P1
    runtime_scope: {spark: ">=4.0.0"}

  - id: SF-SPARK4-003
    requires_facts: [mig.python_dep]
    when:
      all:
        - fact: mig.python_dep
          where: {attrs.package: "pyarrow"}
          expr: "attrs.major < 15"
    severity_default: P1
    runtime_scope: {spark: ">=4.1.0"}
```

> `attrs.major` **não existe hoje** em `mig.python_dep` — o kind guarda `version` como
> string. O avaliador de expressões compara números, não versões. Antes de escrever
> `SF-SPARK4-003`, acrescente `major` (inteiro) aos `attrs` do kind em
> `sparkforge/facts/migration.py`, com teste próprio em `tests/test_facts_migration.py`:
> `pyarrow==11.0.0` produz `attrs["major"] == 11`. Extrair o major é observação, não
> juízo — o limiar `15` continua na regra, que é onde ele pertence.
> Versão que não começa por dígito (`pyarrow==@git+...`) **não** recebe `major`, e a
> condição não casa: fail-closed, sem adivinhar.

As `sources` das três são as duas URLs da Task 1, com `retrieved: 2026-08-22`.

- [ ] **Step 4: Rodar para ver passar**

Run: `python -m pytest tests/test_spark4_rules.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rules/catalog/spark4.yaml tests/test_spark4_rules.py sparkforge/facts/migration.py tests/test_facts_migration.py
git commit -m "feat(rules): area SF-SPARK4 com as tres primeiras regras"
```

---

### Task 5: Ligar a área nova nas listas escritas à mão

Sem esta task a suíte fica vermelha em pelo menos quatro arquivos, e cada um deles existe
porque uma área já nasceu órfã antes. Ver `docs/gates-por-mudanca.md`.

**Files:**
- Modify: `rules/catalog/routing.yaml`
- Modify: `agents/sf-runtime-specialist.md`
- Modify: `manifest.json`
- Modify: `tests/test_rule_scope_by_nature.py`

- [ ] **Step 1: Rodar os gates para ver o que falha**

Run:
```bash
python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py \
  tests/test_docs_coverage.py tests/test_rule_scope_by_nature.py \
  tests/test_runtime_glue_versions.py -q
```
Expected: FAIL. Anote cada mensagem — elas nomeiam exatamente a lista que falta.

- [ ] **Step 2: Declarar a área no agente**

Em `agents/sf-runtime-specialist.md`, acrescentar `SF-SPARK4` ao campo `rule_areas` do
frontmatter. É o agente certo porque a área julga compatibilidade entre versões de runtime,
que é o que o perfil dele já declara.

Cuidado com o YAML do frontmatter: `: ` dentro de valor escalar sem aspas quebra o parse e
derruba dezenas de testes de uma vez.

- [ ] **Step 3: Rotear a área**

Em `rules/catalog/routing.yaml`, acrescentar uma entrada para `SF-SPARK4` no mesmo formato
da entrada de `SF-MIG`, apontando para `sf-runtime-specialist`. Declarar a área no agente
**não** roteia; a entrada própria é obrigatória.

- [ ] **Step 4: Atualizar a contagem do manifesto**

Run:
```bash
python - <<'PY'
import json, pathlib
from sparkforge.rules.loader import load_catalog
p = pathlib.Path("manifest.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["knowledge_base"]["rule_count"] = len(load_catalog())
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(d["knowledge_base"]["rule_count"])
PY
```
Expected: imprime a contagem nova.

- [ ] **Step 5: Classificar as regras nas listas de escopo**

Em `tests/test_rule_scope_by_nature.py`, acrescentar `SF-SPARK4-001`, `SF-SPARK4-002` e
`SF-SPARK4-003` ao conjunto `SPARK_VERSIONED`, com um comentário dizendo por que elas são
guardadas por versão de **Spark** e não de Glue: a fronteira é do Apache, e as três valem
igual num EMR com Spark 4.

Se `TestNoCatalogAreaVanishesEntirely` reprovar dizendo que `SF-SPARK4` some inteira em
algum runtime, a resposta **não** é acrescentar exceção em `AREA_MAY_VANISH_WHEN`: leia o
critério escrito acima daquele mapa. Área que some por falta de versão **detectada** pede
`runtime_scope: {}` mais `requires_facts`; exceção ali é só para infraestrutura que o
runtime comprovadamente não tem.

- [ ] **Step 6: Rodar os gates de novo**

Run:
```bash
python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py \
  tests/test_docs_coverage.py tests/test_rule_scope_by_nature.py \
  tests/test_runtime_glue_versions.py tests/test_rules_loader.py \
  tests/test_rules_result_axis.py tests/test_rules_engine.py -q
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rules/catalog/routing.yaml agents/sf-runtime-specialist.md manifest.json tests/test_rule_scope_by_nature.py
git commit -m "fix(rules): declara SF-SPARK4 nas listas hand-written e roteia a area"
```

---

### Task 6: Golden do piso de dependência e sincronização dos espelhos

**Files:**
- Create: `fixtures/migration/spark4_dep_floor/`
- Modify: `.claude/`, `.agents/`, `.github/` (gerados por script, nunca à mão)

- [ ] **Step 1: Criar o golden**

`fixtures/migration/spark4_dep_floor/input/requirements.txt`:

```
pyarrow==11.0.0
```

`meta.yaml` com `expects_kinds: [mig.python_dep]`, `expects_rules: [SF-SPARK4-003]` e o
bloco `runtime` com `spark: "4.1.1"`.

- [ ] **Step 2: Rodar o gate de cobertura de ramo de severidade**

Run: `python -m pytest tests/test_fixtures_kind_coverage.py -q`
Expected: PASS. Este gate exige golden para **todo ramo de severidade**, não só por regra.

- [ ] **Step 3: Sincronizar os espelhos do agente**

Run:
```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --check
```
Expected: `OK: .claude, .agents e .github em dia com skills/ e agents/`.

- [ ] **Step 4: Rodar os gates de paridade**

Run: `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_capability_parity.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fixtures/migration/spark4_dep_floor .claude .agents .github
git commit -m "test(spark4): golden do piso de PyArrow e espelhos sincronizados"
```

---

### Task 7: Fechar o mapa e o STATUS

**Files:**
- Modify: `docs/harness/GLUE6-GAP.md`
- Modify: `docs/claims.lock.json` (via `--seed`, nunca à mão)
- Modify: `docs/superpowers/STATUS.md`

- [ ] **Step 1: Atualizar as linhas do mapa**

Em `docs/harness/GLUE6-GAP.md`, seção 4, trocar a classificação de duas linhas:

- *Conhecimento de breaking changes de Spark `3.3` a `4.1`* passa a **EXISTE, com teste**,
  citando `knowledge/spark/spark4-migration.md` e `tests/test_spark4_rules.py`.
- *Áreas `SF-SPARK4` e `SF-ICE-V3` (§43)* passa a **EXISTE PARCIAL** — `SF-SPARK4` existe,
  `SF-ICE-V3` continua não existindo e depende da fase G3.

Não mexer na linha das skills `spark-4-*`: elas continuam sem existir, e agora com o
conhecimento por trás pronto para quando alguém as escrever.

- [ ] **Step 2: Reclassificar as alegações**

Run:
```bash
python scripts/check_vnext_claims.py --seed
```

Depois, para cada entrada nova, escrever `state: PROVADA` com `proof`. Alegação de
capacidade usa `kind: artifact` com `path` e `test`; número usa `kind: command` com um
comando reexecutável. **Nunca** `--seed --force`, que descarta toda a classificação.

- [ ] **Step 3: Rodar o gate de lastro**

Run: `python scripts/check_vnext_claims.py`
Expected: `0 divergencia(s).`

- [ ] **Step 4: Escrever a seção do STATUS**

Acrescentar a `docs/superpowers/STATUS.md` uma seção da fase, e **remedir** os números que
ela muda em vez de copiá-los: contagem de regras, de fixtures, de fontes vigiadas e de
kinds distintos. Comando por número, ao lado dele.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `python -m pytest -q -p no:randomly`
Expected: PASS, sem regressão. Entre 13 e 35 minutos.

- [ ] **Step 6: Commit**

```bash
git add docs/harness/GLUE6-GAP.md docs/claims.lock.json docs/superpowers/STATUS.md
git commit -m "docs: Spark 4 sai de lacuna no mapa, com o lastro reclassificado"
```

---

## Auto-revisão deste plano

**Cobertura contra o mapa.** Esta fase fecha duas linhas da seção 4 do `GLUE6-GAP.md`
(conhecimento de Spark 4; área `SF-SPARK4`, parcialmente) e uma da seção 3. Não toca as
outras 28 — cada uma tem fase declarada na tabela de ordem, e as skills `spark-4-*` ficam
explicitamente de fora, com razão escrita.

**Dependência descoberta ao escrever, e resolvida dentro do plano.** `SF-SPARK4-003`
precisa de `attrs.major` em `mig.python_dep`, que hoje não existe: o kind guarda a versão
como string e o avaliador de expressões compara número. A Task 4, Step 3 traz o
acréscimo e o teste, em vez de deixar a regra referenciar um campo inexistente.

**Nomes conferidos entre tasks.** `mig.renamed_conf`, `mig.removed_api` e `mig.python_dep`
aparecem com a mesma grafia na Task 2, 3, 4 e 6. `SF-SPARK4-001/002/003` idem, incluindo
os `expects_rules` dos três goldens.

**O que este plano deliberadamente não faz:** não cria skill, não cria tool MCP nova, não
mexe na CLI. Nenhuma das três tem consumidor nesta fase, e as três apareceriam como
superfície nova que os gates de paridade cobram para sempre.
