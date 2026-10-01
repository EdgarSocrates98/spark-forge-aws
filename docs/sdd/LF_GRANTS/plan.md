---
sdd: 1
feature: LF_GRANTS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LF_GRANTS/design.md
  sha256: "54317f304c56fc972062e52c83ca5882446c35817593df467eaff771a01e7ca7"
tasks:
  - id: T1
    files: [knowledge/glue/lakeformation-permissions.yaml, sparkforge/facts/lakeformation_missing_grant.py, tests/test_lakeformation_missing_grant.py]
    covers: [AC10]
    test: {path: tests/test_lakeformation_missing_grant.py, name: test_tabela_de_operacao_cita_fonte_e_cobre_o_extrator}
  - id: T2
    files: [sparkforge/facts/lakeformation_missing_grant.py, tests/test_lakeformation_missing_grant.py, tests/test_harness_untrusted.py, docs/superpowers/STATUS.md, docs/claims.lock.json]
    covers: [AC1, AC2, AC3, AC8, AC9, AC17]
    test: {path: tests/test_lakeformation_missing_grant.py, name: test_fta_append_sem_all_acusa_all}
  - id: T3
    files: [sparkforge/facts/lakeformation_missing_grant.py, tests/test_lakeformation_missing_grant.py]
    covers: [AC4, AC5, AC6, AC7]
    test: {path: tests/test_lakeformation_missing_grant.py, name: test_fgac_escrita_cobra_iam_com_denied_by}
  - id: T4
    files: [sparkforge/facts/fusion.py, sparkforge/simulate/diff.py, tests/test_rules_catalog_reachability.py, tests/test_lakeformation_missing_grant.py]
    covers: [AC11]
    test: {path: tests/test_lakeformation_missing_grant.py, name: test_fuse_deriva_missing_grant}
  - id: T5
    files: [rules/catalog/lakeformation.yaml, rules/catalog/errors.yaml, knowledge/errors/lakeformation/access_denied_cross_account.json, knowledge/sources.lock.json, manifest.json, tests/test_lakeformation_rules.py, tests/test_lakeformation_missing_grant.py, docs/superpowers/STATUS.md, docs/claims.lock.json]
    covers: [AC10, AC12, AC13, AC16]
    test: {path: tests/test_lakeformation_rules.py, name: test_sf_lf_011_dispara_so_com_permissao_nomeada}
  - id: T6
    files: [fixtures/cloudwatch_logs, tests/test_fixtures_golden_cloudwatch_logs.py, scripts/regen_fixtures.py, tests/test_fixtures_kind_coverage.py]
    covers: [AC12, AC16]
    test: {path: tests/test_fixtures_golden_cloudwatch_logs.py, name: test_all_required_fixtures_exist}
  - id: T7
    files: [sparkforge/lakeformation/graph.py, tests/test_lakeformation_access_graph.py]
    covers: [AC14, AC15]
    test: {path: tests/test_lakeformation_access_graph.py, name: test_grafo_usa_missing_grant_quando_existe}
---

# LF_GRANTS — plano

Sete tarefas, na ordem de dependência. Cada tarefa que cria alguma coisa também atualiza
os registros manuais que essa coisa exige. Premissas do design:

- **D1:** extrator derivado próprio, chamado por `fuse()`.
- **D2:** tabela operação→permissão em YAML, lida via `knowledge_ref`.
- **D3:** operação sai de `pyspark.read`, `pyspark.write` e `sql.write_statement`.
- **D4:** recurso sai do trecho `permission(s) on <recurso>` da mensagem.
- **D5:** versão sai de `env.runtime_signal` (`component=glue`), com `tf.attribute
  glue_version` como reserva.
- **D6:** sob FGAC, escrita cobra `s3:PutObject`, e overwrite também `s3:DeleteObject`.
- **D7:** `SF-LF-011` com `runtime_scope: {}`.
- **D8:** o grafo consome o fact quando ele existe.
- **D9:** o modelo de acesso sai de `access_model`, `filesystem` e `iceberg_catalog`.
- **D10:** o gatilho é só `ERR-LF-001`.
- **D11:** o golden fica no corpus `cloudwatch_logs`.
- **D12:** o kind novo entra em `DERIVED_KINDS` do simulate.

Comando de teste, sempre um arquivo por vez (a suíte inteira não roda num processo só):
`python -m pytest <arquivo> -q`.

**Registros de números.** Toda tarefa que muda a contagem de extratores, kinds ou regras
roda os dois gates abaixo e corrige o que eles apontarem:

- `python scripts/check_status_numbers.py --strict`: o gate imprime a dimensão divergente
  com o valor medido; troque o número em negrito da linha correspondente na tabela
  *Números correntes* de `docs/superpowers/STATUS.md` pelo valor que o gate mediu.
- `python scripts/check_vnext_claims.py`: para cada id que o gate listar, rode
  `python scripts/check_vnext_claims.py --seed` e reclassifique a entrada em
  `docs/claims.lock.json` com o número novo. Remedie pela lista de ids, nunca por varredura.

## T1 — a tabela operação→permissão, como dado citado

### 1. Escrever o teste que falha

`tests/test_lakeformation_missing_grant.py`, primeira versão:

```python
"""`lakeformation.missing_grant` -- a permissao que a operacao exigia e o grant
medido nao tinha, cruzada com a falha observada (`ERR-LF-001`).

Os cenarios sao Fact em memoria, sinteticos. O golden em
`fixtures/cloudwatch_logs/` prende o caminho inteiro (log, Terraform, codigo e
artefato de `collect lakeformation`); aqui cada ramo do extrator e medido sozinho.
"""
from __future__ import annotations

from sparkforge.facts.lakeformation_missing_grant import (
    OPERACOES_MAPEADAS,
    load_table,
    requirement,
)


def test_tabela_de_operacao_cita_fonte_e_cobre_o_extrator():
    tabela = load_table()
    fontes = tabela["fontes"]
    assert fontes, "a tabela precisa declarar fontes"
    for url in fontes.values():
        assert url.startswith("https://docs.aws.amazon.com/"), url
    for linha in tabela["operacoes"]:
        assert linha["source"] in fontes, linha
        assert linha["quote"].strip(), linha
        assert linha["requires"], linha
        assert linha["side"] in {"lf", "iam"}, linha
    for operacao in OPERACOES_MAPEADAS:
        assert any(l["operation"] == operacao for l in tabela["operacoes"]), operacao
    # As duas linhas que o explore tinha errado, fixadas contra a fonte.
    assert requirement("write", "fta")["requires"] == ["ALL"]
    assert requirement("read", "fta")["requires"] == ["SELECT"]
    assert "DATA_LOCATION_ACCESS" not in requirement("write", "fta")["requires"]
    assert requirement("write", "fgac")["side"] == "iam"
```

### 2. Rodar e ver falhar

`python -m pytest tests/test_lakeformation_missing_grant.py -q`. Falha esperada: erro de
coleta (exit 2) com `ModuleNotFoundError: No module named
'sparkforge.facts.lakeformation_missing_grant'`. O módulo ausente é a unidade sob teste.

### 3. Código mínimo

`knowledge/glue/lakeformation-permissions.yaml`:

```yaml
# Operacao do job Glue Spark -> permissao que ela exige, por modelo de acesso.
#
# Lido por `sparkforge/facts/lakeformation_missing_grant.py::load_table`. Cada linha
# cita a fonte pela chave de `fontes` e traz a frase literal em `quote`. Linha sem
# fonte ou sem frase reprova a carga: a tabela nao e escrita de memoria.
#
# Duas correcoes medidas contra a fonte em 2026-09-21 (docs/sdd/LF_GRANTS/define.md):
# escrita sob FTA exige ALL, e nao INSERT, porque a pagina de FTA do Glue e mais
# especifica que a referencia generica; e DATA_LOCATION_ACCESS nao autoriza escrita
# de dado -- "is not needed to query or update underlying data".
fontes:
  lf_reference: "https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html"
  fta: "https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html"
  fgac_considerations: "https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html"
operacoes:
  - operation: read
    model: fta
    side: lf
    resource_level: table
    requires: [SELECT]
    source: lf_reference
    quote: "A principal with this permission can view a table in the Data Catalog, and can query the underlying data in Amazon S3 at the location specified by the table."
  - operation: read
    model: fgac
    side: lf
    resource_level: table
    requires: [SELECT]
    source: lf_reference
    quote: "A principal with this permission can view a table in the Data Catalog, and can query the underlying data in Amazon S3 at the location specified by the table."
  - operation: write
    model: fta
    side: lf
    resource_level: table
    requires: [ALL]
    source: fta
    quote: "AWS Glue Spark jobs that write/delete data in Amazon S3 require AWS Lake Formation ALL permission."
  - operation: overwrite
    model: fta
    side: lf
    resource_level: table
    requires: [ALL]
    source: fta
    quote: "AWS Glue Spark jobs that write/delete data in Amazon S3 require AWS Lake Formation ALL permission."
  - operation: write
    model: fgac
    side: iam
    resource_level: table
    requires: ["s3:PutObject"]
    source: fgac_considerations
    quote: "If your job runtime role has the necessary S3 permissions, you can use it to run write operations"
  - operation: overwrite
    model: fgac
    side: iam
    resource_level: table
    requires: ["s3:PutObject", "s3:DeleteObject"]
    source: fgac_considerations
    quote: "If your job runtime role has the necessary S3 permissions, you can use it to run write operations"
  - operation: create
    model: fta
    side: lf
    resource_level: database
    requires: [CREATE_TABLE]
    source: lf_reference
    quote: "A principal with this permission can create a metadata table or resource link in the Data Catalog within the specified database."
```

`sparkforge/facts/lakeformation_missing_grant.py`, primeira versão (só a tabela):

```python
"""`lakeformation.missing_grant` -- a permissao que a operacao exigia e o grant
medido nao tinha, cruzada com a falha observada.

Derivacao pura sobre a UNIAO dos facts, no molde de `lakeformation.py` e
`timeout_diagnosis.py`: nao le artefato, e e chamada por `fuse()`.

## Por que ele existe

`ERR-LF-001` (`Insufficient Lake Formation permission(s) on`) declara
`lakeformation.missing_grant` em `evidence_required` desde antes de o motor ler
Lake Formation. A mensagem nomeia o RECURSO e nao a permissao; a permissao sai da
OPERACAO que o codigo faz, lida da tabela citada em
`knowledge/glue/lakeformation-permissions.yaml`. "Permissao exigida fora do
conjunto concedido" nao cabe nos seis comparadores de `rules/expr.py`, e por isso
e fact (regra 33 do CLAUDE.md).

## O modelo decide o lado (regras 31 e 32)

Sob FTA, a credencial do Lake Formation le e escreve: cobra-se o grant. Sob FGAC,
a leitura cobra o grant e a escrita cobra o IAM do runtime role. Escrita em alvo
REGISTRADO sob FGAC e o conflito declarado da secao 6 de
`knowledge/glue/lakeformation-fgac.md`, e sai recusa nomeada, sem lado escolhido.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

EXTRACTOR_ID = "lakeformation_missing_grant@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "lakeformation.missing_grant",
        "lakeformation.missing_grant.unresolved",
    }
)

# As operacoes que `_operacoes` produz. A tabela precisa ter ao menos uma linha
# para cada uma; `test_tabela_de_operacao_cita_fonte_e_cobre_o_extrator` cobra.
OPERACOES_MAPEADAS = ("read", "write", "overwrite", "create")

_RELATIVE = "glue/lakeformation-permissions.yaml"
_CAMPOS = ("operation", "model", "side", "resource_level", "requires", "source", "quote")


def _path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _RELATIVE)


@lru_cache(maxsize=1)
def load_table() -> dict[str, Any]:
    """A tabela inteira, validada. Linha sem campo, ou com fonte fora de `fontes`,
    levanta `ValueError` -- a mesma guarda de `lakeformation_matrix.load`."""
    with _path().open("r", encoding="utf-8") as arquivo:
        documento = yaml.safe_load(arquivo) or {}
    fontes = documento.get("fontes") or {}
    problemas: list[str] = []
    for linha in documento.get("operacoes") or []:
        rotulo = f"{linha.get('operation')}/{linha.get('model')}"
        for campo in _CAMPOS:
            if not linha.get(campo):
                problemas.append(f"{rotulo}: sem `{campo}`")
        if linha.get("source") and linha["source"] not in fontes:
            problemas.append(f"{rotulo}: `source` {linha['source']!r} fora de `fontes`")
    if problemas:
        raise ValueError(
            "knowledge/glue/lakeformation-permissions.yaml invalido:\n  "
            + "\n  ".join(problemas)
        )
    return documento


def requirement(operation: str, model: str) -> dict[str, Any] | None:
    """A linha da tabela para (operacao, modelo), ou `None` quando a fonte nao a declara."""
    for linha in load_table().get("operacoes") or []:
        if linha["operation"] == operation and linha["model"] == model:
            return dict(linha)
    return None


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "OPERACOES_MAPEADAS",
    "load_table",
    "requirement",
]
```

### 4. Rodar e ver passar

`python -m pytest tests/test_lakeformation_missing_grant.py -q` → 1 passed.

### 5. Gates vizinhos

`python scripts/verify_wheel.py` (é leitura de disco em código de `sparkforge/`: o YAML
precisa estar no wheel. `knowledge/` já entra por `force-include`).

### 6. Commit

`feat(lakeformation): cite the operation-to-permission table as data`

## T2 — o extrator, lado Lake Formation

### 1. Escrever o teste que falha

Acrescentar a `tests/test_lakeformation_missing_grant.py`. Os helpers e os `cenario_*`
ficam no nível do módulo porque T5 os importa.

```python
from sparkforge.facts.lakeformation_missing_grant import (
    EMITTED_KINDS,
    build_missing_grant,
)
from sparkforge.findings.models import Fact

PROV = {"extractor": "teste@0.0.0", "artifact": "memoria"}
ROLE = "arn:aws:iam::111111111111:role/glue-curated"
TABELA = "default.dim_cliente"
LINHA = (
    "2026-09-09 10:08:04,910 ERROR [main] lakeformation.Client: "
    f"AccessDeniedException: Insufficient Lake Formation permission(s) on {TABELA}"
)


def _gatilho(sig: str = "ERR-LF-001", linha: str = LINHA) -> Fact:
    return Fact(
        kind="error.signature_match",
        subject={"type": "job_run", "symbol": "etl-dim", "signature_id": sig},
        attrs={"signature_id": sig, "matched_on": "log_line", "matched_line": linha},
        provenance={"extractor": "matcher@0.1.0", "artifact": "logs/erro.json"},
    )


def _grant(perms: list[str], principal: str = ROLE, tabela: str = TABELA) -> Fact:
    return Fact(
        kind="lakeformation.grant",
        subject={"type": "table", "file": "lf.json", "symbol": f"{tabela}#{principal}", "catalog_id": ""},
        measures={"permission_count": len(perms)},
        attrs={
            "principal": principal,
            "is_iam_allowed_principals": principal == "IAM_ALLOWED_PRINCIPALS",
            "permissions": sorted(perms),
            "permissions_with_grant_option": [],
            "has_select": "SELECT" in perms,
            "has_all": "ALL" in perms,
            "has_describe": "DESCRIBE" in perms,
        },
        provenance=PROV,
    )


def _escrita(mode: str = "append", target: str | None = TABELA) -> Fact:
    attrs: dict = {"api": "v1", "mode": mode}
    if target is not None:
        attrs["target"] = target
    return Fact(
        kind="pyspark.write",
        subject={"type": "source_location", "file": "job.py", "line": 20},
        attrs=attrs,
        provenance=PROV,
    )


def _leitura(target: str = TABELA) -> Fact:
    return Fact(
        kind="pyspark.read",
        subject={"type": "source_location", "file": "job.py", "line": 10},
        attrs={"format": "table", "target": target},
        provenance=PROV,
    )


def _fta() -> Fact:
    return Fact(
        kind="lakeformation.filesystem",
        subject={"type": "tf_resource", "file": "main.tf", "symbol": "aws_glue_job.etl"},
        attrs={
            "lf_credentials_resolver_declared": True,
            "emrfs_restored": True,
            "fs_s3_impl": "com.amazon.ws.emr.hadoop.fs.EmrFileSystem",
            "source": "terraform",
        },
        provenance=PROV,
    )


def _modelo(model: str) -> Fact:
    return Fact(
        kind="lakeformation.access_model",
        subject={"type": "tf_resource", "file": "main.tf", "symbol": "aws_glue_job.etl"},
        attrs={
            "model": model,
            "fgac_enabled": model in {"fgac", "both"},
            "declared_value": "true",
            "fta_markers": [],
            "source": "terraform",
        },
        provenance=PROV,
    )


def _glue(versao: str) -> Fact:
    return Fact(
        kind="env.runtime_signal",
        subject={"type": "job_run", "symbol": "glue"},
        measures={"distinct_versions": 1, "source_count": 1},
        attrs={"component": "glue", "resolved": versao, "observed": [versao], "source": "resolved"},
        provenance={"extractor": "runtime_detect@0.1.0"},
    )


def _registrada(sim: bool = True) -> Fact:
    return Fact(
        kind="lakeformation.registered_location",
        subject={"type": "table", "file": "lf.json", "symbol": TABELA, "catalog_id": ""},
        attrs={
            "registered": sim,
            "resource_arn": "arn:aws:s3:::sparkforge-demo/default/dim_cliente",
            "role_arn": "",
            "hybrid_access_enabled": None,
            "with_federation": None,
        },
        provenance=PROV,
    )


def _decisao(acao: str, decisao: str, denied_by: str = "implicit_deny") -> Fact:
    return Fact(
        kind="iam.access_decision",
        subject={"type": "job_run", "file": "iam.json", "symbol": f"{ROLE}#{acao}@*"},
        measures={"matched_statements": 0},
        attrs={
            "role_arn": ROLE,
            "action": acao,
            "resource": "*",
            "decision": decisao,
            "allowed": decisao == "allowed",
            "denied_by": "" if decisao == "allowed" else denied_by,
        },
        provenance=PROV,
    )


def cenario_fta_append_sem_all() -> list[Fact]:
    return [_gatilho(), _fta(), _escrita(), _grant(["DESCRIBE", "SELECT"])]


def cenario_fta_leitura_sem_select() -> list[Fact]:
    return [_gatilho(), _fta(), _leitura(), _grant(["DESCRIBE"])]


def cenario_grant_que_cobre() -> list[Fact]:
    return [_gatilho(), _fta(), _escrita(), _grant(["ALL"])]


def cenario_sem_operacao() -> list[Fact]:
    return [_gatilho(), _fta(), _grant(["SELECT"])]


def cenario_fgac_escrita_negada() -> list[Fact]:
    return [_gatilho(), _modelo("fgac"), _glue("5.1"), _escrita(), _decisao("s3:PutObject", "implicitDeny")]


def cenario_fgac_escrita_registrada() -> list[Fact]:
    return [
        _gatilho(),
        _modelo("fgac"),
        _glue("5.1"),
        _escrita(),
        _registrada(True),
        _decisao("s3:PutObject", "implicitDeny"),
    ]


def _de(facts: list[Fact], kind: str) -> list[Fact]:
    return [f for f in facts if f.kind == kind]


def test_sem_falha_observada_nao_emite():
    sem_gatilho = [_fta(), _escrita(), _grant(["SELECT"])]
    assert build_missing_grant(sem_gatilho) == []
    # ERR-LF-003 e falta de IAM de credential vending, nao de grant (D10).
    outra_assinatura = [_gatilho(sig="ERR-LF-003", linha="lakeformation:GetDataAccess"), *sem_gatilho]
    assert build_missing_grant(outra_assinatura) == []


def test_sem_operacao_recusa_por_nome():
    saida = build_missing_grant(cenario_sem_operacao())
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "operacao_nao_medida"
    assert "sparkforge analyze pyspark" in recusa.attrs["unblocked_by"]


def test_fta_append_sem_all_acusa_all():
    pool = cenario_fta_append_sem_all()
    saida = build_missing_grant(pool)
    (falta,) = _de(saida, "lakeformation.missing_grant")
    assert falta.attrs["side"] == "lf"
    assert falta.attrs["operation"] == "write"
    assert falta.attrs["resource"] == TABELA
    assert falta.attrs["principal"] == ROLE
    assert falta.attrs["model"] == "fta"
    assert falta.attrs["requires"] == ["ALL"]
    assert falta.attrs["missing"] == ["ALL"]
    assert falta.attrs["granted"] == ["DESCRIBE", "SELECT"]
    grant = _de(pool, "lakeformation.grant")[0]
    assert grant.id in falta.attrs["evidence"]
    assert pool[0].id in falta.attrs["evidence"]
    assert falta.kind in EMITTED_KINDS


def test_fta_leitura_sem_select_acusa_select():
    (falta,) = _de(build_missing_grant(cenario_fta_leitura_sem_select()), "lakeformation.missing_grant")
    assert falta.attrs["side"] == "lf"
    assert falta.attrs["operation"] == "read"
    assert falta.attrs["missing"] == ["SELECT"]


def test_grant_que_cobre_nao_acusa():
    assert build_missing_grant(cenario_grant_que_cobre()) == []


def test_fta_escrita_em_alvo_nao_registrado_recusa():
    # Secao 5: sob FTA, tabela NAO registrada e escrita pela credencial do runtime
    # role, e cobrar ALL do grant do LF seria acusar a perna errada.
    pool = [*cenario_fta_append_sem_all(), _registrada(False)]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "fta_escrita_em_alvo_nao_registrado"
    # Leitura no mesmo alvo continua cobrando SELECT: a recusa e so da escrita.
    leitura = [*cenario_fta_leitura_sem_select(), _registrada(False)]
    assert _de(build_missing_grant(leitura), "lakeformation.missing_grant")
```

### 2. Rodar e ver falhar

`python -m pytest tests/test_lakeformation_missing_grant.py -q`. Falha esperada: erro de
coleta (exit 2) com `ImportError: cannot import name 'build_missing_grant'`.

### 3. Código mínimo

Acrescentar a `sparkforge/facts/lakeformation_missing_grant.py`, depois de `requirement`.
Os imports de topo passam a ser:

```python
from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.findings.models import Fact, sort_facts
from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file
```

Constantes, logo abaixo de `OPERACOES_MAPEADAS`:

```python
# So a mensagem de grant ausente dispara (D10). ERR-LF-002 a 005 nomeiam acao IAM ou
# validacao de seguranca e tem SF-ERR-014 a 017.
GATILHO = "ERR-LF-001"
SOURCE_KINDS = frozenset({"error.signature_match"})

IAM_ALLOWED_PRINCIPALS = "IAM_ALLOWED_PRINCIPALS"

_RECURSO_RE = re.compile(r"permission\(s\)\s+on\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE)

_SQL = {
    "insert_into": "write",
    "merge_into": "write",
    "update": "write",
    "insert_overwrite": "overwrite",
    "delete_from": "overwrite",
    "create_table": "create",
    "create_table_as": "create",
}

_DESTRAVA = {
    "recurso_ambiguo": (
        "a mensagem nao nomeia o recurso e o case tem mais de uma tabela com grant ou "
        "registro coletado; colete so a tabela da falha com `sparkforge collect lakeformation`"
    ),
    "operacao_nao_medida": (
        "nenhum fact de operacao sobre o recurso; rode `sparkforge analyze pyspark` sobre o "
        "codigo do job e junte a saida ao case"
    ),
    "operacao_nao_ligada_ao_recurso": (
        "o codigo le ou escreve outros alvos literais e nenhum e o recurso da mensagem; "
        "confira se o alvo vem de variavel, que o extrator de codigo nao resolve"
    ),
    "modelo_both": (
        "o job declara FGAC e marcador de FTA juntos, e a AWS nao permite os dois no mesmo "
        "job; decida o modelo antes (secao 5 de knowledge/glue/lakeformation-fgac.md)"
    ),
    "modelo_ausente": (
        "nenhum modelo de acesso declarado; rode `sparkforge analyze terraform` sobre o job "
        "(argumento de FGAC ou confs de FTA)"
    ),
    "grant_nao_coletado": (
        "nenhum `lakeformation.grant` para o recurso; rode `sparkforge collect lakeformation` "
        "sobre ele"
    ),
    "principal_ambiguo": (
        "mais de um principal com grant na tabela e nenhuma decisao de IAM que diga qual e o "
        "role do job; rode `sparkforge collect iam-access` para o runtime role"
    ),
    "permissao_de_database_nao_coletada": (
        "create exige permissao no DATABASE, e `collect lakeformation` coleta grant de tabela"
    ),
    "fta_escrita_em_alvo_nao_registrado": (
        "sob FTA, tabela nao registrada no Lake Formation e escrita pela credencial do "
        "runtime role, e nao pelo grant (secao 5 de knowledge/glue/lakeformation-fgac.md); "
        "rode `sparkforge collect iam-access` com s3:PutObject sobre o alvo"
    ),
    "operacao_sem_requisito_declarado": (
        "a tabela citada nao declara requisito para esta operacao neste modelo; nada e "
        "afirmado sem fonte"
    ),
}
```

Funções, antes do `__all__`:

```python
def _prov(gatilho: Fact) -> dict[str, Any]:
    artefato = str((gatilho.provenance or {}).get("artifact") or "")
    return {"extractor": EXTRACTOR_ID, "artifact": artefato}


def _unresolved(
    reason: str, recurso: str, gatilho: Fact, **extra: Any
) -> Fact:
    rotulo = "#".join(p for p in (recurso, reason, str(extra.get("operation") or "")) if p)
    return Fact(
        kind="lakeformation.missing_grant.unresolved",
        subject={"type": "table", "symbol": rotulo},
        measures={},
        attrs={
            "reason": reason,
            "resource": recurso,
            "signature_id": GATILHO,
            "unblocked_by": str(extra.pop("unblocked_by", "") or _DESTRAVA.get(reason, "")),
            "extractor": EXTRACTOR_ID,
            **extra,
        },
        provenance=_prov(gatilho),
    )


def _tabela_de(fact: Fact) -> str:
    return str((fact.subject or {}).get("symbol", "")).split("#", 1)[0]


def _recurso_da_mensagem(gatilho: Fact) -> str | None:
    attrs = gatilho.attrs or {}
    texto = str(attrs.get("matched_line") or attrs.get("matched_class") or "")
    casou = _RECURSO_RE.search(texto)
    return casou.group(1).rstrip(".") if casou else None


def _candidato_unico(facts: Sequence[Fact]) -> str | None:
    tabelas = {
        _tabela_de(f)
        for f in facts
        if f.kind in {"lakeformation.grant", "lakeformation.registered_location"}
    }
    tabelas.discard("")
    return tabelas.pop() if len(tabelas) == 1 else None


def _casa(alvo: str, recurso: str) -> bool:
    return alvo == recurso or alvo.split(".")[-1] == recurso.split(".")[-1]


def _operacoes(recurso: str, facts: Sequence[Fact]) -> list[tuple[str, Fact]] | str:
    todas: list[tuple[str, str, Fact]] = []
    for f in facts:
        attrs = f.attrs or {}
        if f.kind == "pyspark.read":
            todas.append(("read", str(attrs.get("target") or ""), f))
        elif f.kind == "pyspark.write":
            op = "overwrite" if attrs.get("mode") == "overwrite" else "write"
            todas.append((op, str(attrs.get("target") or ""), f))
        elif f.kind == "sql.write_statement" and attrs.get("operation") in _SQL:
            todas.append((_SQL[attrs["operation"]], str(attrs.get("table") or ""), f))
    if not todas:
        return "operacao_nao_medida"
    com_alvo = [t for t in todas if t[1]]
    escolhidas = [t for t in com_alvo if _casa(t[1], recurso)] if com_alvo else todas
    if not escolhidas:
        return "operacao_nao_ligada_ao_recurso"
    por_operacao: dict[str, Fact] = {}
    for op, _alvo, f in escolhidas:
        por_operacao.setdefault(op, f)
    return sorted(por_operacao.items())


def _modelo(facts: Sequence[Fact]) -> str:
    """D9: `access_model` so existe quando o argumento de FGAC e declarado; job so de
    FTA aparece como `filesystem` com o resolver do LF ou catalogo com LF ligado."""
    modelos = {
        str((f.attrs or {}).get("model"))
        for f in facts
        if f.kind == "lakeformation.access_model"
    }
    if "both" in modelos:
        return "modelo_both"
    if "fgac" in modelos:
        return "fgac"
    fta = any(
        (f.kind == "lakeformation.filesystem" and (f.attrs or {}).get("lf_credentials_resolver_declared"))
        or (f.kind == "lakeformation.iceberg_catalog" and (f.attrs or {}).get("lakeformation_enabled"))
        for f in facts
    )
    return "fta" if fta else "modelo_ausente"


def _principal(facts: Sequence[Fact], grants: Sequence[Fact]) -> str | None:
    roles = {
        str((f.attrs or {}).get("role_arn") or "")
        for f in facts
        if f.kind == "iam.access_decision"
    }
    roles.discard("")
    if len(roles) == 1:
        return roles.pop()
    principais = {str((g.attrs or {}).get("principal") or "") for g in grants}
    principais -= {"", IAM_ALLOWED_PRINCIPALS}
    return principais.pop() if len(principais) == 1 else None


def _cobre(concedidas: Sequence[str], permissao: str) -> bool:
    return "ALL" in concedidas or permissao in concedidas


def _lado_lf(
    recurso: str, operacao: str, origem: Fact, linha: dict[str, Any], modelo: str,
    gatilho: Fact, facts: Sequence[Fact],
) -> list[Fact]:
    if linha["resource_level"] == "database":
        return [_unresolved("permissao_de_database_nao_coletada", recurso, gatilho, operation=operacao)]
    nao_registrada = any(
        f.kind == "lakeformation.registered_location"
        and _tabela_de(f) == recurso
        and (f.attrs or {}).get("registered") is False
        for f in facts
    )
    if modelo == "fta" and operacao in {"write", "overwrite"} and nao_registrada:
        return [_unresolved("fta_escrita_em_alvo_nao_registrado", recurso, gatilho, operation=operacao)]
    grants = [f for f in facts if f.kind == "lakeformation.grant" and _tabela_de(f) == recurso]
    if not grants:
        return [_unresolved("grant_nao_coletado", recurso, gatilho, operation=operacao)]
    # Tabela aberta a `IAM_ALLOWED_PRINCIPALS` com ALL e governada pelo IAM: falta de
    # grant do LF nao e a causa, e SF-LF-008 ja fala dela.
    if any((g.attrs or {}).get("is_iam_allowed_principals") and (g.attrs or {}).get("has_all") for g in grants):
        return []
    principal = _principal(facts, grants)
    if principal is None:
        return [_unresolved("principal_ambiguo", recurso, gatilho, operation=operacao)]
    do_principal = [g for g in grants if (g.attrs or {}).get("principal") == principal]
    concedidas = sorted({str(p) for g in do_principal for p in (g.attrs or {}).get("permissions") or []})
    faltam = [p for p in linha["requires"] if not _cobre(concedidas, p)]
    if not faltam:
        return []
    return [
        Fact(
            kind="lakeformation.missing_grant",
            subject={"type": "table", "symbol": f"{recurso}#{operacao}#lf"},
            measures={},
            attrs={
                "resource": recurso,
                "operation": operacao,
                "model": modelo,
                "side": "lf",
                "principal": principal,
                "requires": list(linha["requires"]),
                "missing": faltam,
                "granted": concedidas,
                "source": load_table()["fontes"][linha["source"]],
                "quote": linha["quote"],
                "signature_id": GATILHO,
                "evidence": sorted({gatilho.id, origem.id, *(g.id for g in do_principal)}),
                "extractor": EXTRACTOR_ID,
            },
            provenance=_prov(gatilho),
        )
    ]


def _lado_iam(
    recurso: str, operacao: str, origem: Fact, linha: dict[str, Any], modelo: str,
    gatilho: Fact, facts: Sequence[Fact],
) -> list[Fact]:
    return []


def _derivar(recurso: str, gatilho: Fact, facts: Sequence[Fact]) -> list[Fact]:
    operacoes = _operacoes(recurso, facts)
    if isinstance(operacoes, str):
        return [_unresolved(operacoes, recurso, gatilho)]
    modelo = _modelo(facts)
    if modelo not in {"fta", "fgac"}:
        return [_unresolved(modelo, recurso, gatilho)]
    saida: list[Fact] = []
    for operacao, origem in operacoes:
        linha = requirement(operacao, modelo)
        if linha is None:
            saida.append(_unresolved("operacao_sem_requisito_declarado", recurso, gatilho, operation=operacao, model=modelo))
            continue
        lado = _lado_lf if linha["side"] == "lf" else _lado_iam
        saida.extend(lado(recurso, operacao, origem, linha, modelo, gatilho, facts))
    return saida


def build_missing_grant(facts: Sequence[Fact]) -> list[Fact]:
    """Deriva `lakeformation.missing_grant` da uniao dos facts. Sem `ERR-LF-001` no
    pool, devolve lista vazia: sem falha observada nao ha permissao ausente a afirmar."""
    lista = list(facts)
    gatilhos = [
        f
        for f in lista
        if f.kind == "error.signature_match" and (f.attrs or {}).get("signature_id") == GATILHO
    ]
    if not gatilhos:
        return []
    saida: dict[str, Fact] = {}
    recursos: dict[str, Fact] = {}
    for gatilho in gatilhos:
        recurso = _recurso_da_mensagem(gatilho) or _candidato_unico(lista)
        if recurso is None:
            recusa = _unresolved("recurso_ambiguo", "", gatilho)
            saida[recusa.id] = recusa
            continue
        recursos.setdefault(recurso, gatilho)
    for recurso, gatilho in recursos.items():
        for fact in _derivar(recurso, gatilho, lista):
            saida[fact.id] = fact
    return sort_facts(list(saida.values()))
```

E o `__all__` passa a ser:

```python
__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "GATILHO",
    "OPERACOES_MAPEADAS",
    "SOURCE_KINDS",
    "build_missing_grant",
    "load_table",
    "requirement",
]
```

`tests/test_harness_untrusted.py`: no import de `_derivados_de_facts`, acrescentar
`lakeformation_missing_grant` à tupla de `from sparkforge.facts import (...)`, e depois da
linha `yield "lakeformation", lakeformation.build_lakeformation(pool)`:

```python
    # `lakeformation_missing_grant` deriva de `error.signature_match` mais grant,
    # decisao de IAM e operacao, e nao de caminho. Sem esta chamada a guarda
    # fail-closed para com o nome do modulo.
    yield "lakeformation_missing_grant", lakeformation_missing_grant.build_missing_grant(pool)
```

### 4. Rodar e ver passar

`python -m pytest tests/test_lakeformation_missing_grant.py -q` → 7 passed.
`python -m pytest tests/test_harness_untrusted.py -q` → verde.

### 5. Gates vizinhos

`python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q`.
Neste commit o módulo ainda não entra nas duas listas `EXTRACTORS`. Isso é deliberado: ele
entra em T4, junto com a chamada em `fuse()`. Com a regra ainda inexistente, os dois kinds
não têm consumidor, e esses dois testes só contam kinds de extrator listado.
Depois, os dois gates de números, como descrito no topo.

### 6. Commit

`feat(lakeformation): derive the missing grant from the observed ERR-LF-001 failure`

## T3 — o lado IAM sob FGAC, a versão e o conflito declarado

### 1. Escrever o teste que falha

Acrescentar a `tests/test_lakeformation_missing_grant.py`:

```python
def test_fgac_escrita_cobra_iam_com_denied_by():
    (falta,) = _de(build_missing_grant(cenario_fgac_escrita_negada()), "lakeformation.missing_grant")
    assert falta.attrs["side"] == "iam"
    assert falta.attrs["model"] == "fgac"
    assert falta.attrs["action"] == "s3:PutObject"
    assert falta.attrs["decision"] == "implicitDeny"
    assert falta.attrs["denied_by"] == "implicit_deny"
    assert falta.attrs["runtime"] == "5.1"
    assert falta.attrs["missing"] == ["s3:PutObject"]


def test_fgac_escrita_registrada_e_conflito_declarado():
    saida = build_missing_grant(cenario_fgac_escrita_registrada())
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "conflito_declarado_fgac_escrita_registrada"
    assert "knowledge/glue/lakeformation-fgac.md" in recusa.attrs["unblocked_by"]
    assert "missing" not in recusa.attrs


def test_modelo_ou_runtime_desconhecido_recusa_por_nome():
    both = [_gatilho(), _modelo("both"), _escrita(), _grant(["SELECT"])]
    ausente = [_gatilho(), _escrita(), _grant(["SELECT"])]
    sem_runtime = [_gatilho(), _modelo("fgac"), _escrita(), _decisao("s3:PutObject", "implicitDeny")]
    razoes = []
    for pool in (both, ausente, sem_runtime):
        (recusa,) = _de(build_missing_grant(pool), "lakeformation.missing_grant.unresolved")
        assert recusa.attrs["unblocked_by"], recusa.attrs
        razoes.append(recusa.attrs["reason"])
    assert razoes == ["modelo_both", "modelo_ausente", "runtime_ausente"]


def test_fgac_escrita_em_runtime_sem_suporte_nao_e_permissao():
    pool = [_gatilho(), _modelo("fgac"), _glue("5.0"), _escrita(), _decisao("s3:PutObject", "implicitDeny")]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "escrita_fgac_nao_suportada_no_runtime"
    assert recusa.attrs["runtime"] == "5.0"
```

### 2. Rodar e ver falhar

`python -m pytest tests/test_lakeformation_missing_grant.py -q`. Falhas esperadas nos quatro
testes novos, porque `_lado_iam` devolve `[]`:
- `test_fgac_escrita_cobra_iam_com_denied_by`, `test_fgac_escrita_registrada_e_conflito_declarado`
  e `test_fgac_escrita_em_runtime_sem_suporte_nao_e_permissao`: `ValueError: not enough
  values to unpack (expected 1, got 0)`.
- `test_modelo_ou_runtime_desconhecido_recusa_por_nome`: o mesmo `ValueError` no terceiro
  pool.

### 3. Código mínimo

Em `sparkforge/facts/lakeformation_missing_grant.py`, acrescentar o import
`from sparkforge.facts import lakeformation_matrix` e a constante
`EIXO_ESCRITA_FGAC = "fgac_spark_native_write"` junto das outras. Acrescentar a `_DESTRAVA`:

```python
    "runtime_ausente": (
        "a escrita sob FGAC depende da versao do Glue; rode `sparkforge runtime detect` ou "
        "`sparkforge analyze terraform` sobre o job (glue_version)"
    ),
    "runtime_divergente": (
        "o case observa mais de uma versao de Glue; resolva a divergencia antes"
    ),
    "runtime_sem_celula_na_matriz": (
        "knowledge/glue/lakeformation-matrix.yaml nao declara escrita sob FGAC para esta "
        "versao; nada e afirmado sem a pagina de migracao lida"
    ),
    "escrita_fgac_nao_suportada_no_runtime": (
        "a matriz de versao declara que esta versao nao escreve sob FGAC Spark-native "
        "(eixo fgac_spark_native_write); a causa e versao, nao permissao"
    ),
    "conflito_declarado_fgac_escrita_registrada": (
        "escrita em localizacao registrada sob FGAC e o conflito declarado da secao 6 de "
        "knowledge/glue/lakeformation-fgac.md; as tres saidas que a documentacao sustenta "
        "estao la, e nenhuma e escolhida aqui (regra 32)"
    ),
    "acao_iam_nao_simulada": (
        "a acao exigida nao foi simulada; rode `sparkforge collect iam-access` incluindo-a"
    ),
```

Substituir o corpo de `_lado_iam` e acrescentar `_runtime` antes dele:

```python
def _runtime(facts: Sequence[Fact]) -> tuple[str | None, str | None]:
    """D5: `(versao, None)` ou `(None, razao)`."""
    sinais = [
        f
        for f in facts
        if f.kind == "env.runtime_signal" and (f.attrs or {}).get("component") == "glue"
    ]
    if sinais:
        valores = {str((f.attrs or {}).get("resolved") or "") for f in sinais} - {""}
        divergente = any(int((f.measures or {}).get("distinct_versions") or 0) > 1 for f in sinais)
        if divergente or len(valores) > 1:
            return None, "runtime_divergente"
        if len(valores) == 1:
            return valores.pop(), None
    declarados = {
        str((f.attrs or {}).get("value") or "")
        for f in facts
        if f.kind == "tf.attribute" and (f.attrs or {}).get("key") == "glue_version"
    } - {""}
    if len(declarados) > 1:
        return None, "runtime_divergente"
    if len(declarados) == 1:
        return declarados.pop(), None
    return None, "runtime_ausente"


def _lado_iam(
    recurso: str, operacao: str, origem: Fact, linha: dict[str, Any], modelo: str,
    gatilho: Fact, facts: Sequence[Fact],
) -> list[Fact]:
    versao, razao = _runtime(facts)
    if razao is not None:
        return [_unresolved(razao, recurso, gatilho, operation=operacao)]
    celula = lakeformation_matrix.capability(str(versao), EIXO_ESCRITA_FGAC) or {}
    status = celula.get("status")
    if status in {"not_supported", "not_applicable"}:
        return [_unresolved("escrita_fgac_nao_suportada_no_runtime", recurso, gatilho, operation=operacao, runtime=versao)]
    if status != "supported":
        return [_unresolved("runtime_sem_celula_na_matriz", recurso, gatilho, operation=operacao, runtime=versao)]
    registrada = any(
        f.kind == "lakeformation.registered_location"
        and _tabela_de(f) == recurso
        and (f.attrs or {}).get("registered") is True
        for f in facts
    )
    if registrada:
        return [_unresolved("conflito_declarado_fgac_escrita_registrada", recurso, gatilho, operation=operacao, runtime=versao)]
    decisoes = [f for f in facts if f.kind == "iam.access_decision"]
    saida: list[Fact] = []
    for acao in linha["requires"]:
        da_acao = [d for d in decisoes if (d.attrs or {}).get("action") == acao]
        if not da_acao:
            saida.append(_unresolved("acao_iam_nao_simulada", recurso, gatilho, operation=operacao, action=acao))
            continue
        for negada in (d for d in da_acao if not (d.attrs or {}).get("allowed")):
            attrs = negada.attrs or {}
            saida.append(
                Fact(
                    kind="lakeformation.missing_grant",
                    subject={"type": "table", "symbol": f"{recurso}#{operacao}#iam#{acao}"},
                    measures={},
                    attrs={
                        "resource": recurso,
                        "operation": operacao,
                        "model": modelo,
                        "side": "iam",
                        "principal": str(attrs.get("role_arn") or ""),
                        "action": acao,
                        "decision": str(attrs.get("decision") or ""),
                        "denied_by": str(attrs.get("denied_by") or ""),
                        "runtime": versao,
                        "requires": list(linha["requires"]),
                        "missing": [acao],
                        "source": load_table()["fontes"][linha["source"]],
                        "quote": linha["quote"],
                        "signature_id": GATILHO,
                        "evidence": sorted({gatilho.id, origem.id, negada.id}),
                        "extractor": EXTRACTOR_ID,
                    },
                    provenance=_prov(gatilho),
                )
            )
    return saida
```

### 4. Rodar e ver passar

`python -m pytest tests/test_lakeformation_missing_grant.py -q` → 11 passed.

### 5. Gates vizinhos

`python -m pytest tests/test_lakeformation_matrix.py tests/test_harness_untrusted.py -q`.

### 6. Commit

`feat(lakeformation): charge the IAM side under FGAC, and refuse by name on version and the declared conflict`

## T4 — `fuse()` chama o extrator, e o simulate o conhece

### 1. Escrever o teste que falha

Acrescentar a `tests/test_lakeformation_missing_grant.py`:

```python
from sparkforge.facts.fusion import fuse
from sparkforge.simulate.diff import DERIVED_KINDS


def _tf_conf_resolver() -> Fact:
    chave = "spark.hadoop.fs.s3.credentialsResolverClass"
    return Fact(
        kind="tf.spark_conf",
        subject={"type": "tf_resource", "file": "main.tf", "line": 9, "symbol": f"aws_glue_job.etl#{chave}"},
        attrs={
            "key": chave,
            "value": "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
            "source_argument": "--conf",
            "block": "default_arguments",
        },
        provenance=PROV,
    )


def test_fuse_deriva_missing_grant():
    # Sem `lakeformation.filesystem` no pool: `fuse` precisa deriva-lo primeiro
    # (build_lakeformation) e so depois cruzar, senao o modelo sai ausente.
    pool = [_gatilho(), _tf_conf_resolver(), _escrita(), _grant(["SELECT"])]
    kinds = {f.kind for f in fuse(pool)}
    assert "lakeformation.missing_grant" in kinds
    assert EMITTED_KINDS <= DERIVED_KINDS
    sem_falha = [_tf_conf_resolver(), _escrita(), _grant(["SELECT"])]
    assert not {f.kind for f in fuse(sem_falha)} & EMITTED_KINDS
```

### 2. Rodar e ver falhar

`python -m pytest tests/test_lakeformation_missing_grant.py::test_fuse_deriva_missing_grant -q`.
Falha esperada: `AssertionError` em `assert "lakeformation.missing_grant" in kinds`.

### 3. Código mínimo

`sparkforge/facts/fusion.py`, junto dos imports de `timeout_diagnosis`:

```python
from sparkforge.facts.lakeformation_missing_grant import (
    EMITTED_KINDS as MISSING_GRANT_EMITTED_KINDS,
)
from sparkforge.facts.lakeformation_missing_grant import (
    SOURCE_KINDS as MISSING_GRANT_SOURCE_KINDS,
)
from sparkforge.facts.lakeformation_missing_grant import build_missing_grant
```

Logo depois do laço `for fact in derivados_lf: combined[fact.id] = fact`:

```python
    # `lakeformation.missing_grant` deriva AQUI, DEPOIS de `lakeformation.*`: o
    # modelo de acesso que ele le (`access_model`, `filesystem`, `iceberg_catalog`)
    # so existe depois da derivacao acima, e por isso ele recebe `combined` e nao
    # `facts`. A guarda por `SOURCE_KINDS` mantem o `fuse` igual para quem nao tem
    # falha de Lake Formation no pool, o mesmo molde do timeout abaixo.
    if any(f.kind in MISSING_GRANT_SOURCE_KINDS for f in facts):
        derivados_mg = build_missing_grant(list(combined.values()))
        desconhecidos_mg = {f.kind for f in derivados_mg} - MISSING_GRANT_EMITTED_KINDS
        if desconhecidos_mg:
            raise AssertionError(
                f"kind fora do namespace de lakeformation_missing_grant: {sorted(desconhecidos_mg)}"
            )
        for fact in derivados_mg:
            combined[fact.id] = fact
```

`sparkforge/simulate/diff.py`:

```python
from sparkforge.facts import fusion, lakeformation, lakeformation_missing_grant, timeout_diagnosis
from sparkforge.findings.models import Fact
from sparkforge.proof.keys import stable_key

DERIVED_KINDS = frozenset(
    fusion.EMITTED_KINDS
    | lakeformation.EMITTED_KINDS
    | lakeformation_missing_grant.EMITTED_KINDS
    | timeout_diagnosis.EMITTED_KINDS
)
```

Também atualize o docstring do módulo: onde está escrito "`fusion`, `lakeformation` e
`timeout_diagnosis`", passe a ler "`fusion`, `lakeformation`, `lakeformation_missing_grant`
e `timeout_diagnosis`".

`tests/test_rules_catalog_reachability.py`: acrescentar `lakeformation_missing_grant` às duas
listas. Na tupla de import de `sparkforge.facts`, logo depois de `lakeformation_grants,`.
Em `EXTRACTORS`, logo depois de `lakeformation_grants,` com o comentário:

```python
    # `lakeformation_missing_grant` deriva o kind que `ERR-LF-001` declarava em
    # `evidence_required` desde antes de o motor ler Lake Formation. Entra nas DUAS
    # listas no commit que o liga ao `fuse()`, antes da regra que o consome.
    lakeformation_missing_grant,
```

### 4. Rodar e ver passar

`python -m pytest tests/test_lakeformation_missing_grant.py -q` → 12 passed.

### 5. Gates vizinhos

`python -m pytest tests/test_rules_catalog_reachability.py tests/test_facts_fusion.py tests/test_simulate.py -q`.
Se algum desses arquivos não existir com esse nome, localize com
`sparkforge code search fuse` e `sparkforge code search strip_derived` e rode os testes que
chamam essas funções. `test_rules_catalog_reachability` pode acusar os dois kinds como
órfãos, porque nenhuma regra os consome até T5. Se acusar, o vermelho fica registrado no
build_report e T5 o fecha.

### 6. Commit

`feat(fusion): derive lakeformation.missing_grant after the access model`

## T5 — a regra `SF-LF-011`, a assinatura e os registros

### 1. Escrever o teste que falha

`tests/test_lakeformation_rules.py`, no fim:

```python
from sparkforge.facts.lakeformation_missing_grant import build_missing_grant
from tests.test_lakeformation_missing_grant import (
    cenario_fgac_escrita_negada,
    cenario_fgac_escrita_registrada,
    cenario_fta_append_sem_all,
    cenario_fta_leitura_sem_select,
    cenario_grant_que_cobre,
    cenario_sem_operacao,
)


def _sf_lf_011_dispara(pool) -> bool:
    facts = list(pool) + build_missing_grant(pool)
    return "SF-LF-011" in {f.rule_id for f in judge(facts, load_catalog(), RUNTIME_GLUE_50)}


def test_sf_lf_011_dispara_so_com_permissao_nomeada():
    for cenario in (cenario_fta_append_sem_all, cenario_fta_leitura_sem_select, cenario_fgac_escrita_negada):
        assert _sf_lf_011_dispara(cenario()), cenario.__name__
    for cenario in (cenario_grant_que_cobre, cenario_fgac_escrita_registrada, cenario_sem_operacao):
        assert not _sf_lf_011_dispara(cenario()), cenario.__name__
```

`tests/test_lakeformation_missing_grant.py`, no fim:

```python
import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def test_evidence_de_err_lf_001_e_emitida():
    assinatura = json.loads(
        (RAIZ / "knowledge/errors/lakeformation/access_denied_cross_account.json").read_text(encoding="utf-8")
    )
    assert assinatura["id"] == "ERR-LF-001"
    assert assinatura["evidence_required"] == ["lakeformation.missing_grant"]
    assert "ram.unaccepted_share" in assinatura["evidence_out_of_reach"]
    assert "lakeformation.missing_grant" in EMITTED_KINDS


def test_fontes_da_tabela_estao_no_lock():
    lock = json.loads((RAIZ / "knowledge/sources.lock.json").read_text(encoding="utf-8"))["sources"]
    for url in load_table()["fontes"].values():
        assert url in lock, url
```

### 2. Rodar e ver falhar

- `python -m pytest tests/test_lakeformation_rules.py::test_sf_lf_011_dispara_so_com_permissao_nomeada -q`:
  `AssertionError: cenario_fta_append_sem_all`, porque a regra não existe.
- `python -m pytest tests/test_lakeformation_missing_grant.py -q`:
  `test_evidence_de_err_lf_001_e_emitida` com `KeyError: 'evidence_out_of_reach'`, e
  `test_fontes_da_tabela_estao_no_lock` com `AssertionError` na URL
  `lf-permissions-reference.html`.

### 3. Código mínimo

`rules/catalog/lakeformation.yaml`, no fim da lista de regras:

```yaml
  # ---------------------------------------------------------------------------
  # SF-LF-011 -- a primeira que cruza a FALHA observada com a permissao medida.
  #
  # `ERR-LF-001` declarava `lakeformation.missing_grant` em `evidence_required`, e
  # nenhum extrator o emitia: `SF-ERR-006` so podia mandar investigar a cadeia.
  # O fact agora sai de `sparkforge/facts/lakeformation_missing_grant.py`, que ja
  # resolveu modelo, versao e operacao -- por isso `runtime_scope: {}` e o gate
  # real e `requires_facts` (docs/gates-por-mudanca.md, secao runtime_scope).
  - id: SF-LF-011
    category: lakeformation-governance
    governance_decision_required: true
    security_impact: widens_scope
    security_impact_reason: >-
      Conceder a permissão que falta amplia o que o runtime role pode fazer sobre a tabela, e o raio é o de todo job que usa o mesmo role.
    title: >-
      O job falhou por permissão do Lake Formation, e a permissão que a operação
      exige não está no grant medido (ou na decisão de IAM, sob FGAC)
    requires_facts: [lakeformation.missing_grant]
    when:
      all:
        - fact: lakeformation.missing_grant
    status: confirmed
    severity_default: P1
    runtime_scope: {}
    explanation: >
      O log do run tem `Insufficient Lake Formation permission(s) on <recurso>`
      (`ERR-LF-001`), e o fact `lakeformation.missing_grant` cruzou três medidas
      com essa falha: a operação que o código faz sobre o recurso, o grant
      coletado por `collect lakeformation` e, sob FGAC, a decisão de
      `iam:SimulatePrincipalPolicy` coletada por `collect iam-access`.


      **O lado muda o conserto.** Com `side: lf` (Full Table Access, ou leitura
      sob FGAC), falta permissão no grant do Lake Formation. Para job Spark do
      Glue que escreve sob FTA, a permissão é `ALL`, e não `INSERT`: *"AWS Glue
      Spark jobs that write/delete data in Amazon S3 require AWS Lake Formation
      ALL permission."* Com `side: iam` (escrita sob FGAC), quem autoriza a
      escrita é o IAM do runtime role, e `denied_by` diz qual camada negou.
      Nesse caso, acrescentar uma statement só resolve quando `denied_by` é
      `implicit_deny`.


      **O que a regra NÃO afirma:** que o job passa depois do grant. Outras
      partes do caminho (RAM share, key policy do KMS, bucket policy) não têm
      coletor, e a simulação de IAM não avalia policy de recurso. Escrita em
      localização registrada sob FGAC não chega aqui: é o conflito declarado da
      §6 de `knowledge/glue/lakeformation-fgac.md` e sai como recusa nomeada.
    proposed_change:
      - >-
        Com `side: lf`: conceder ao principal do fact, sobre o recurso do fact,
        as permissões de `attrs.missing`. Confira antes se a tabela deve ser
        governada pelo Lake Formation (`SF-LF-008`), porque grant numa tabela
        aberta a `IAM_ALLOWED_PRINCIPALS` não muda nada.
      - >-
        Com `side: iam`: ler `attrs.denied_by` antes de editar a policy. Se for
        `implicit_deny`, falta uma statement com `attrs.action`. Se for
        `explicit_deny`, `permissions_boundary` ou `service_control_policy`,
        acrescentar não resolve: é preciso achar a negação e decidir se ela sai.
    action:
      kind: security.verify_access_chain
      target: lakeformation.grant
      direction: investigate
      requires_absent: []
      moves: []
      depends_on: []
    risks:
      - >-
        `ALL` concede também `DROP` e `ALTER` sobre a tabela. Sob FTA, a fonte
        exige `ALL` para escrever, e o custo dessa exigência é um raio maior que o
        da operação.
      - >-
        A operação vem do código analisado. Alvo em variável não é resolvido pelo
        extrator de código, e nesse caso o fact sai recusado
        (`operacao_nao_ligada_ao_recurso`), não acusado.
    tradeoffs:
      - >-
        Conceder só o que falta mantém o menor privilégio. Trocar o modelo de
        acesso (FGAC ou FTA) muda quem vende a credencial, e é decisão de
        plataforma, não de job.
    validation:
      - >-
        Recoletar com `sparkforge collect lakeformation` (ou `collect iam-access`,
        sob FGAC) e rodar `sparkforge fuse` de novo. O `lakeformation.missing_grant`
        do recurso precisa sumir.
      - >-
        Reexecutar o job e confirmar que `ERR-LF-001` sai do log do run. Nenhum
        eixo de dado é exigido: a mudança é de permissão, não de conteúdo.
    rollback:
      - >-
        Revogar a permissão concedida (`aws lakeformation revoke-permissions`) ou
        remover a statement acrescentada ao role. O job volta a falhar como antes.
    sources:
      - {url: "https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html", retrieved: 2026-09-21}
      - {url: "https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html", retrieved: 2026-09-21}
      - {url: "https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html", retrieved: 2026-09-21}
```

`knowledge/errors/lakeformation/access_denied_cross_account.json`: trocar a linha
`"evidence_required": [...]` por:

```json
  "evidence_required": ["lakeformation.missing_grant"],
  "evidence_out_of_reach": ["ram.unaccepted_share"],
```

`rules/catalog/errors.yaml`: nos dois blocos de comentário que afirmam que
`lakeformation.missing_grant` não é emitido (o cabeçalho que lista `ERR-LF-001` em torno
da linha 69, e o comentário antes de `SF-ERR-014`, em torno da linha 1774), acrescentar
logo depois da afirmação:

```yaml
#   ATUALIZADO em 2026-09-21 (docs/sdd/LF_GRANTS/): `lakeformation.missing_grant`
#   passou a ser emitido por `sparkforge/facts/lakeformation_missing_grant.py`, e
#   `SF-LF-011` o consome. `ram.unaccepted_share` continua sem coletor e foi movido
#   para `evidence_out_of_reach` da assinatura. `SF-ERR-006` fica como esta: ela
#   dispara sem grant coletado, que e o caso que o fact novo recusa por nome.
```

O `explanation` de `SF-ERR-006` diz "MEDIDO em 2026-09-09 nenhum dos dois é kind que este
motor emite". Acrescente ao fim desse parágrafo: "Desde 2026-09-21,
`lakeformation.missing_grant` é emitido quando o grant e a operação foram coletados, e
`SF-LF-011` nomeia a permissão."

Registros:
- `python scripts/refresh_knowledge.py --update --offline` acrescenta as URLs de
  `SF-LF-011` a `knowledge/sources.lock.json`.
- `manifest.json`: `"rule_count"` sobe de `168` para `169`. Confira antes o valor com
  `python -m pytest tests/test_docs_coverage.py -q`, que mostra o número medido.
- Rode os dois gates de números descritos no topo.

### 4. Rodar e ver passar

`python -m pytest tests/test_lakeformation_rules.py -q` → verde.
`python -m pytest tests/test_lakeformation_missing_grant.py -q` → 14 passed.

### 5. Gates vizinhos

```
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py \
  tests/test_rules_result_axis.py tests/test_rules_engine.py \
  tests/test_agent_coverage.py tests/test_router_agents.py \
  tests/test_docs_coverage.py tests/test_refresh_knowledge.py \
  tests/test_rules_threshold_mutation.py tests/test_rules_errors.py -q
python -m pytest tests/test_rule_scope_by_nature.py \
  tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q
python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py --strict
```

`tests/test_fixtures_kind_coverage.py` fica vermelho até T6, porque `SF-LF-011` ainda não
tem golden. O vermelho é registrado no build_report, e T6 o fecha.

### 6. Commit

`feat(rules): SF-LF-011 names the missing Lake Formation or IAM permission behind ERR-LF-001`

## T6 — o golden: uma positiva, uma negativa, e três goldens regenerados

### 1. Escrever o teste que falha

`tests/test_fixtures_golden_cloudwatch_logs.py`: acrescentar a `REQUIRED_FIXTURES`:

```python
    # LF_GRANTS (2026-09-21): o par que prende SF-LF-011 pelo caminho inteiro --
    # log com ERR-LF-001, Terraform com FTA, codigo com a escrita e o artefato de
    # `collect lakeformation` em `input/lf/`. A negativa tem o MESMO log e grant ALL.
    "lf_negado_fta_append_sem_all",
    "lf_negado_fta_grant_all",
```

### 2. Rodar e ver falhar

`python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py::test_all_required_fixtures_exist -q`.
Falha esperada: `AssertionError` no conjunto, porque os dois diretórios não existem.

### 3. Código mínimo

**Runner e regen, idênticos.** Em `tests/test_fixtures_golden_cloudwatch_logs.py::_extract`,
acrescentar o import `from sparkforge.facts.lakeformation_grants import
extract_lakeformation_tree` e `from sparkforge.facts.lakeformation_missing_grant import
build_missing_grant`. Logo antes de `facts.extend(build_lakeformation(facts))`:

```python
    # O artefato de `collect lakeformation` entra sob guarda de DIRETORIO, pela mesma
    # razao de `catalog/` e `s3/`: `*.json` na raiz ja e o log.
    permissoes = entrada / "lf"
    if permissoes.is_dir():
        facts.extend(extract_lakeformation_tree(permissoes, repo_root=entrada))
```

E depois de `facts.extend(build_signature_matches(facts))`:

```python
    # `build_missing_grant` vem por ULTIMO: ele le o match de ERR-LF-001, que so
    # existe depois do matcher, e o modelo de acesso, que so existe depois de
    # `build_lakeformation`.
    facts.extend(build_missing_grant(facts))
```

Em `scripts/regen_fixtures.py::regen_cloudwatch_logs`, na mesma posição relativa, o mesmo
bloco de `input_dir / "lf"` (com `input_dir` no lugar de `entrada`) e a mesma linha
`facts.extend(build_missing_grant(facts))` depois de `build_signature_matches`. Acrescente
o import `from sparkforge.facts.lakeformation_missing_grant import build_missing_grant  # noqa: E402`.
`extract_lakeformation_tree` já é importado ali.

**Fixture positiva** `fixtures/cloudwatch_logs/lf_negado_fta_append_sem_all/`:

`input/logs/curated-fta_jr_lf9_aws-glue_jobs_error.json`:

```json
{
  "end": "2026-09-21T11:00:00Z",
  "events": [
    {
      "eventId": "e0",
      "ingestionTime": 1790000000500,
      "logStreamName": "jr_lf9",
      "message": "2026-09-21 10:08:04,910 ERROR [main] lakeformation.Client: AccessDeniedException: Insufficient Lake Formation permission(s) on analytics.dim_cliente",
      "timestamp": 1790000000000
    }
  ],
  "events_collected": 1,
  "filter_pattern": "?ERROR ?Exception",
  "job_name": "curated-fta",
  "job_run_id": "jr_lf9",
  "log_group": "/aws-glue/jobs/error",
  "log_stream_prefix": "jr_lf9",
  "max_events": 500,
  "start": "2026-09-21T10:00:00Z",
  "status": "ok",
  "truncated": false
}
```

`input/main.tf`:

```hcl
# Job sintetico sob Full Table Access: o `--conf` pede a credencial do Lake
# Formation e restaura EMRFS, e nao ha argumento de FGAC.

resource "aws_glue_job" "curated_fta" {
  name              = "curated-fta"
  role_arn          = "arn:aws:iam::111111111111:role/glue-fta"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/fta.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--conf"                  = "spark.hadoop.fs.s3.credentialsResolverClass=com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver --conf spark.hadoop.fs.s3.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem"
  }
}
```

`input/job.py`:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

novos = spark.read.parquet("s3://sparkforge-demo/landing/clientes/")
novos.write.mode("append").saveAsTable("analytics.dim_cliente")
```

`input/lf/local_analytics_dim_cliente.json`:

```json
{
  "catalog_id": "",
  "data_lake_settings": {
    "allow_external_data_filtering": true,
    "allow_full_table_external_data_access": true,
    "external_data_filtering_allow_list": [],
    "status": "ok"
  },
  "database": "analytics",
  "permissions": {
    "grants_collected": 1,
    "principals": [
      {
        "Permissions": ["DESCRIBE", "SELECT"],
        "PermissionsWithGrantOption": [],
        "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/glue-fta"},
        "Resource": {"Table": {"DatabaseName": "analytics", "Name": "dim_cliente"}}
      }
    ],
    "status": "ok",
    "truncated": false
  },
  "registered_location": {
    "hybrid_access_enabled": null,
    "registered": true,
    "resource_arn": "arn:aws:s3:::sparkforge-demo/analytics/dim_cliente",
    "role_arn": "arn:aws:iam::111111111111:role/lf-registration",
    "status": "ok",
    "with_federation": false
  },
  "status": "ok",
  "table": "dim_cliente"
}
```

`meta.yaml`:

```yaml
name: lf_negado_fta_append_sem_all
proves: >
  O POSITIVO de `SF-LF-011` pelo caminho inteiro. O log do run tem `ERR-LF-001`
  sobre `analytics.dim_cliente`, o Terraform declara Full Table Access (resolver
  do Lake Formation e EMRFS restaurado), o codigo faz append nessa tabela, e o
  grant coletado do role do job e so `DESCRIBE` + `SELECT`. Sob FTA, escrita de
  job Spark do Glue exige `ALL`: o fact sai com `missing: [ALL]`, `side: lf`.
  A negativa e `lf_negado_fta_grant_all`: mesmo log, mesmo job, grant `ALL`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: []
expects_rules: []
```

**Fixture negativa** `fixtures/cloudwatch_logs/lf_negado_fta_grant_all/`: os mesmos quatro
arquivos de input, com três diferenças:
- no log, `logStreamName`, `job_run_id` e `log_stream_prefix` passam a `jr_lf10`, e o
  arquivo passa a se chamar `curated-fta_jr_lf10_aws-glue_jobs_error.json`;
- no artefato em `input/lf/`, `"Permissions": ["ALL"]` e
  `"PermissionsWithGrantOption": ["ALL"]`;
- o `meta.yaml` tem `name: lf_negado_fta_grant_all` e um `proves:` que diz: "O NEGATIVO de
  `SF-LF-011`: o grant cobre a escrita (`ALL`), e a falha de `ERR-LF-001` está em outra
  parte do caminho. Nenhum `lakeformation.missing_grant` é emitido, e o extrator não
  inventa uma perna."

**Regenerar e preencher os `meta.yaml`:**

```
python scripts/regen_fixtures.py lf_negado_fta_append_sem_all lf_negado_fta_grant_all lf_negado_com_catalogo_de_outra_conta lf_negado_sem_catalogo_declarado quatro_assinaturas_de_log
python -c "import json,sys; [print(d, sorted({f['kind'] for f in json.load(open(f'fixtures/cloudwatch_logs/{d}/expected/facts.json'))}), sorted({f['rule_id'] for f in json.load(open(f'fixtures/cloudwatch_logs/{d}/expected/findings.json'))})) for d in sys.argv[1:]]" lf_negado_fta_append_sem_all lf_negado_fta_grant_all lf_negado_com_catalogo_de_outra_conta lf_negado_sem_catalogo_declarado quatro_assinaturas_de_log
```

Copie a lista de kinds e a de regras que o segundo comando imprime para `expects_kinds` e
`expects_rules` de cada `meta.yaml`. Aceite só se a saída bater com estas condições:
- `lf_negado_fta_append_sem_all`: `expects_kinds` contém `lakeformation.missing_grant`, e
  `expects_rules` contém `SF-LF-011`;
- `lf_negado_fta_grant_all`: não aparece `lakeformation.missing_grant` nem `SF-LF-011`;
- `lf_negado_com_catalogo_de_outra_conta`, `lf_negado_sem_catalogo_declarado` e
  `quatro_assinaturas_de_log` ganham exatamente `lakeformation.missing_grant.unresolved`
  (sem `.py` no input: `operacao_nao_medida`), e as regras deles não mudam.

Se qualquer condição falhar, pare: o extrator ou a fixture está errado, e o `meta.yaml` não
se ajusta à saída. Qualquer outra regra que dispare na positiva (por exemplo sobre o grant ou
o Terraform) entra em `expects_rules` com uma linha no `proves:` explicando por quê.

`tests/test_fixtures_kind_coverage.py`: acrescentar o import de `lakeformation_missing_grant`
logo depois de `lakeformation_grants,` na tupla de `sparkforge.facts`, e ao dicionário, logo
depois de `"lakeformation_grants": lakeformation_grants,`:

```python
    # `lakeformation_missing_grant` entra no commit das fixtures que trazem os dois
    # kinds para um golden: `missing_grant` na positiva do corpus cloudwatch_logs, e
    # `.unresolved` nas tres fixtures antigas com ERR-LF-001 e sem codigo.
    "lakeformation_missing_grant": lakeformation_missing_grant,
```

### 4. Rodar e ver passar

`python -m pytest tests/test_fixtures_golden_cloudwatch_logs.py -q` → verde.
`python -m pytest tests/test_fixtures_kind_coverage.py -q` → verde.

### 5. Gates vizinhos

`python -m pytest tests/test_rules_catalog_reachability.py tests/test_rules_errors.py tests/test_rules_threshold_mutation.py -q`
e `python scripts/check_vnext_claims.py` (o corpus de fixtures mudou).

### 6. Commit

`test(fixtures): pin SF-LF-011 end to end with a positive and a negative in the CloudWatch corpus`

## T7 — o grafo lê o fact

### 1. Escrever o teste que falha

`tests/test_lakeformation_access_graph.py`, no fim:

```python
from sparkforge.findings.models import Fact

_ROLE = "arn:aws:iam::111111111111:role/glue-curated"
_PROV = {"extractor": "teste@0.0.0", "artifact": "memoria"}


def _grant_select() -> Fact:
    return Fact(
        kind="lakeformation.grant",
        subject={"type": "table", "file": "lf.json", "symbol": f"db.t#{_ROLE}", "catalog_id": ""},
        measures={"permission_count": 1},
        attrs={
            "principal": _ROLE,
            "is_iam_allowed_principals": False,
            "permissions": ["SELECT"],
            "permissions_with_grant_option": [],
            "has_select": True,
            "has_all": False,
            "has_describe": False,
        },
        provenance=_PROV,
    )


def _falta_all() -> Fact:
    return Fact(
        kind="lakeformation.missing_grant",
        subject={"type": "table", "symbol": "db.t#write#lf"},
        attrs={
            "resource": "db.t",
            "operation": "write",
            "model": "fta",
            "side": "lf",
            "principal": _ROLE,
            "requires": ["ALL"],
            "missing": ["ALL"],
            "granted": ["SELECT"],
        },
        provenance={"extractor": "lakeformation_missing_grant@0.1.0"},
    )


def test_grafo_usa_missing_grant_quando_existe():
    grafo = build_access_graph([_grant_select(), _falta_all()], principal_arn=_ROLE, target_table="db.t")
    aresta = _por_tipo(grafo, "lf_grant")
    assert aresta["status"] == "missing"
    assert "ALL" in aresta["evidence"] and "write" in aresta["evidence"]


def test_grafo_sem_missing_grant_inalterado():
    grafo = build_access_graph([_grant_select()], principal_arn=_ROLE, target_table="db.t")
    aresta = _por_tipo(grafo, "lf_grant")
    assert aresta["status"] == STATUS_GRANTED
    assert aresta["evidence"] == "grant medido com SELECT ou ALL"
```

### 2. Rodar e ver falhar

`python -m pytest tests/test_lakeformation_access_graph.py -q`. Falha esperada em
`test_grafo_usa_missing_grant_quando_existe`: `AssertionError`, com `'granted' == 'missing'`.
`test_grafo_sem_missing_grant_inalterado` passa antes e depois: é a guarda AC15, declarada com
`guard` no define.

### 3. Código mínimo

`sparkforge/lakeformation/graph.py::build_access_graph`, junto das outras listas no início:

```python
    faltas = [f for f in lista if getattr(f, "kind", "") == "lakeformation.missing_grant"]
```

E trocar o `elif any(_attrs(f).get("has_select") or _attrs(f).get("has_all") for f in do_par):`
da perna 1 por dois ramos. O primeiro é novo; o segundo é o `elif` atual, intocado:

```python
    elif faltas_do_par := [
        f
        for f in faltas
        if _attrs(f).get("side") == "lf"
        and _attrs(f).get("resource") == target_table
        and _attrs(f).get("principal") == principal_arn
    ]:
        # D8: com o fact de LF_GRANTS no case, o que a perna exige vem da OPERACAO
        # medida, e nao do SELECT fixo abaixo -- que acusaria leitura num job que
        # falhou escrevendo.
        exigidas = sorted(
            {
                f"{_attrs(f).get('operation')}: {', '.join(_attrs(f).get('missing') or [])}"
                for f in faltas_do_par
            }
        )
        arestas.append(
            _aresta(
                principal_arn,
                alvo_lf,
                "lf_grant",
                STATUS_MISSING,
                "grant medido nao cobre a operacao -- falta " + "; ".join(exigidas),
            )
        )
    elif any(_attrs(f).get("has_select") or _attrs(f).get("has_all") for f in do_par):
```

### 4. Rodar e ver passar

`python -m pytest tests/test_lakeformation_access_graph.py tests/test_lakeformation_engine.py -q` → verde.

### 5. Gates vizinhos

`python -m pytest tests/test_adapters_tools.py -q -k lakeformation` (o grafo é servido pela tool
`sparkforge_lakeformation_access_graph`).

### 6. Commit

`feat(lakeformation): the access graph charges what the operation needs when the fact exists`

## Verificação final (antes do build_report)

Rode `tests/test_suite_batches.py` para listar os lotes. Rode os lotes, **um por vez**, e
os gates do AC16:

```
python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py --strict
```

Qualquer registro descoberto só nesta fase vai para a seção de desvios do build_report.
