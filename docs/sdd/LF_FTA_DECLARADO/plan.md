---
sdd: 1
feature: LF_FTA_DECLARADO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LF_FTA_DECLARADO/design.md
  sha256: "7601c3bb853b3009436f8308102b235418330392c133e39499ba73c9165d6684"
tasks:
  - id: T1
    files: [tests/test_facts_lakeformation.py, sparkforge/facts/lakeformation.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_facts_lakeformation.py, name: TestFtaDeclarado::test_resolver_do_lake_formation_declara_fta}
  - id: T2
    files: [tests/test_lakeformation_rules.py, rules/catalog/lakeformation.yaml, tests/test_rules_catalog_reachability.py]
    covers: [AC4, AC5]
    test: {path: tests/test_lakeformation_rules.py, name: TestSfLf010::test_registrado_com_fta_declarado_nao_dispara}
  - id: T3
    files: [tests/test_fixtures_golden_cloudwatch_logs.py, fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all/meta.yaml, fixtures/cloudwatch_logs/lf_negado_fta_grant_all/meta.yaml, docs/guia/usos/lake-formation-e-acesso.md, docs/superpowers/STATUS.md]
    covers: [AC6, AC7, AC8]
    test: {path: tests/test_fixtures_golden_cloudwatch_logs.py, name: test_fta_declarado_cala_sf_lf_010_nos_goldens}
---

# LF_FTA_DECLARADO — plano

pytest sempre com `-p no:cacheprovider --basetemp=E:/sfpt_fta`.

## T1 — o kind derivado

Teste primeiro, em `tests/test_facts_lakeformation.py`, depois de `TestFilesystem`:

```python
_RESOLVER_LF = "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver"
_EMRFS = "com.amazon.ws.emr.hadoop.fs.EmrFileSystem"


class TestFtaDeclarado:
    """FTA nao tem argumento de job: o pedido e o resolver de credencial."""

    def test_resolver_do_lake_formation_declara_fta(self):
        saida = build_lakeformation(
            [
                _tf_conf("spark.hadoop.fs.s3.credentialsResolverClass", _RESOLVER_LF),
                _tf_conf("spark.hadoop.fs.s3.impl", _EMRFS),
            ]
        )
        fs = _de(saida, "lakeformation.filesystem")
        fta = _de(saida, "lakeformation.fta_declared")
        assert len(fta) == 1
        assert fta[0].subject == fs[0].subject
        assert fta[0].provenance == fs[0].provenance
        assert fta[0].attrs["marker"] == "spark.hadoop.fs.s3.credentialsResolverClass"
        assert fta[0].attrs["emrfs_restored"] is True
        assert fta[0].attrs["source"] == "terraform"

    def test_so_a_superficie_com_resolver_declara_fta(self):
        """Trocar o filesystem nao pede credencial do Lake Formation."""
        saida = build_lakeformation(
            [
                _tf_conf("spark.hadoop.fs.s3.credentialsResolverClass", _RESOLVER_LF),
                _codigo("spark.hadoop.fs.s3.impl", _EMRFS),
                _efetiva(
                    "spark.hadoop.fs.s3.credentialsResolverClass", "com.exemplo.MeuResolver"
                ),
            ]
        )
        assert len(_de(saida, "lakeformation.filesystem")) == 3
        fta = _de(saida, "lakeformation.fta_declared")
        assert [f.attrs["source"] for f in fta] == ["terraform"]
        assert fta[0].attrs["emrfs_restored"] is False
```

`TestContratoDoModulo::test_todo_kind_emitido_esta_declarado` ganha o resolver na entrada,
para que o conjunto emitido continue igual a `EMITTED_KINDS`.

Rodar e ver falhar (`len(fta) == 1` com zero):

```bash
python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta "tests/test_facts_lakeformation.py::TestFtaDeclarado" -q
```

Código, em `sparkforge/facts/lakeformation.py`: `"lakeformation.fta_declared"` em
`EMITTED_KINDS`, e em `build_lakeformation`:

```python
    filesystems = _filesystems(facts)
    saida.extend(filesystems)
    saida.extend(_fta_declarados(filesystems))
```

```python
def _fta_declarados(filesystems: Sequence[Fact]) -> list[Fact]:
    """Um fact por superficie que pede o resolver de credencial do Lake Formation."""
    saida: list[Fact] = []
    for fs in filesystems:
        attrs = fs.attrs or {}
        if not attrs.get("lf_credentials_resolver_declared"):
            continue
        saida.append(
            Fact(
                kind="lakeformation.fta_declared",
                subject=dict(fs.subject or {}),
                measures={},
                attrs={
                    "marker": _RESOLVER_KEY,
                    "emrfs_restored": attrs["emrfs_restored"],
                    "source": attrs["source"],
                    "extractor": EXTRACTOR_ID,
                },
                provenance=fs.provenance,
            )
        )
    return saida
```

Verde: o mesmo comando e o arquivo inteiro. Commit.

## T2 — a regra

Teste primeiro, em `tests/test_lakeformation_rules.py`:

```python
_RESOLVER_KEY = "spark.hadoop.fs.s3.credentialsResolverClass"
_IMPL_KEY = "spark.hadoop.fs.s3.impl"
_RESOLVER_LF = "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver"
_EMRFS = "com.amazon.ws.emr.hadoop.fs.EmrFileSystem"


def _conf_tf(key: str, value: str) -> Fact:
    return Fact(
        kind="tf.spark_conf",
        subject={"type": "tf_resource", "file": "main.tf", "line": 9,
                 "symbol": f"aws_glue_job.etl#{key}"},
        measures={},
        attrs={"key": key, "value": value, "source_argument": "--conf",
               "block": "default_arguments"},
        provenance={"extractor": "teste@0.0.0", "artifact": "memoria"},
    )


def _sf_lf_010_dispara(pool) -> bool:
    facts = list(pool) + build_lakeformation(pool)
    return "SF-LF-010" in {f.rule_id for f in judge(facts, load_catalog(), RUNTIME_GLUE_50)}


class TestSfLf010:
    def test_registrado_com_fta_declarado_nao_dispara(self):
        pool = [_registrada(True), _conf_tf(_RESOLVER_KEY, _RESOLVER_LF),
                _conf_tf(_IMPL_KEY, _EMRFS)]
        assert not _sf_lf_010_dispara(pool)
        ausentes = sorted(
            c["absent"] for c in _rule("SF-LF-010")["when"]["all"] if "absent" in c
        )
        assert ausentes == ["lakeformation.access_model", "lakeformation.fta_declared"]

    def test_registrado_so_com_fs_s3_impl_continua_disparando(self):
        assert _sf_lf_010_dispara([_registrada(True), _conf_tf(_IMPL_KEY, _EMRFS)])
        assert _sf_lf_010_dispara([_registrada(True)])
        assert not _sf_lf_010_dispara([_registrada(False), _conf_tf(_IMPL_KEY, _EMRFS)])
```

`_registrada` vem de `tests/test_lakeformation_missing_grant.py`; `Fact` de
`sparkforge.findings.models`.

Vermelho: `test_registrado_com_fta_declarado_nao_dispara` falha porque a regra dispara.

```bash
python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta "tests/test_lakeformation_rules.py::TestSfLf010" -q
```

Código, em `rules/catalog/lakeformation.yaml`, `SF-LF-010`: `- absent:
lakeformation.fta_declared` depois de `- absent: lakeformation.access_model`; title,
explanation, `proposed_change`, risks e rollback como a decisão D3 do design. O comentário de
`SF-LF-010` em `ALLOWED_SET_LEVEL` (`tests/test_rules_catalog_reachability.py`) nomeia os dois
`absent`. Verde: o mesmo comando, o arquivo inteiro e `tests/test_rules_catalog_reachability.py`.
Commit.

## T3 — goldens e registros

Teste primeiro, em `tests/test_fixtures_golden_cloudwatch_logs.py`:

```python
FTA_DECLARADO = ("lf_negado_fta_append_sem_all", "lf_negado_fta_grant_all")


@pytest.mark.parametrize("nome", FTA_DECLARADO)
def test_fta_declarado_cala_sf_lf_010_nos_goldens(nome):
    """O job declara FTA pelo resolver; SF-LF-010 nao o acusa (LF_FTA_DECLARADO)."""
    directory = FIXTURES / nome
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    expected = directory / "expected"
    facts = json.loads((expected / "facts.json").read_text(encoding="utf-8"))
    achados = json.loads((expected / "findings.json").read_text(encoding="utf-8"))
    assert "lakeformation.fta_declared" in {f["kind"] for f in facts}
    assert "SF-LF-010" not in {a["rule_id"] for a in achados}
    assert "SF-LF-010" not in meta.get("expects_rules", [])
    assert "Lacuna da regra" not in meta["proves"]
```

Vermelho, junto com a cobertura de kind (AC7), antes do regen:

```bash
python -m pytest -p no:cacheprovider --basetemp=E:/sfpt_fta "tests/test_fixtures_golden_cloudwatch_logs.py::test_fta_declarado_cala_sf_lf_010_nos_goldens" "tests/test_fixtures_kind_coverage.py::test_every_kind_of_every_extractor_appears_in_some_golden" -q
```

Depois: `python scripts/regen_fixtures.py` com as fixtures que têm o resolver declarado; ler o
diff de `expected/findings.json` de cada uma; ajustar `expects_kinds`, `expects_rules` e o
`proves` das duas FTA e o `expects_kinds` das outras. Verde: o mesmo comando e os três módulos
de golden (`cloudwatch_logs`, `infra_code`, `lakeformation`). Guia e `STATUS.md` pelos gates de
número. Commit das fixtures; commit dos registros.
