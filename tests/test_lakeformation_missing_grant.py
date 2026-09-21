"""`lakeformation.missing_grant` -- a permissao que a operacao exigia e o grant
medido nao tinha, cruzada com a falha observada (`ERR-LF-001`).

Os cenarios sao Fact em memoria, sinteticos. O golden em
`fixtures/cloudwatch_logs/` prende o caminho inteiro (log, Terraform, codigo e
artefato de `collect lakeformation`); aqui cada ramo do extrator e medido sozinho.
"""
from __future__ import annotations

from sparkforge.facts.lakeformation_missing_grant import (
    EMITTED_KINDS,
    OPERACOES_MAPEADAS,
    build_missing_grant,
    load_table,
    requirement,
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
        subject={
            "type": "table",
            "file": "lf.json",
            "symbol": f"{tabela}#{principal}",
            "catalog_id": "",
        },
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
    return [
        _gatilho(),
        _modelo("fgac"),
        _glue("5.1"),
        _escrita(),
        _decisao("s3:PutObject", "implicitDeny"),
    ]


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
    outra_assinatura = [
        _gatilho(sig="ERR-LF-003", linha="lakeformation:GetDataAccess"),
        *sem_gatilho,
    ]
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
    (falta,) = _de(
        build_missing_grant(cenario_fta_leitura_sem_select()), "lakeformation.missing_grant"
    )
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
        assert any(linha["operation"] == operacao for linha in tabela["operacoes"]), operacao
    # As duas linhas que o explore tinha errado, fixadas contra a fonte.
    assert requirement("write", "fta")["requires"] == ["ALL"]
    assert requirement("read", "fta")["requires"] == ["SELECT"]
    assert "DATA_LOCATION_ACCESS" not in requirement("write", "fta")["requires"]
    assert requirement("write", "fgac")["side"] == "iam"
