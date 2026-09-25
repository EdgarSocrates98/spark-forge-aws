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


def _gatilho(
    sig: str = "ERR-LF-001", linha: str = LINHA, artefato: str = "logs/erro.json"
) -> Fact:
    return Fact(
        kind="error.signature_match",
        subject={"type": "job_run", "symbol": "etl-dim", "signature_id": sig},
        attrs={"signature_id": sig, "matched_on": "log_line", "matched_line": linha},
        provenance={"extractor": "matcher@0.1.0", "artifact": artefato},
    )


def _grant(
    perms: list[str], principal: str = ROLE, tabela: str = TABELA, catalog_id: str = ""
) -> Fact:
    return Fact(
        kind="lakeformation.grant",
        subject={
            "type": "table",
            "file": "lf.json",
            "symbol": f"{tabela}#{principal}",
            "catalog_id": catalog_id,
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


def _escrita(
    mode: str | None = "append", target: str | None = TABELA, api: str = "v1"
) -> Fact:
    attrs: dict = {"api": api}
    if mode is not None:
        attrs["mode"] = mode
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


LOCAL = "arn:aws:s3:::sparkforge-demo/default/dim_cliente"


def _registrada(sim: bool = True, arn: str = LOCAL, tabela: str = TABELA) -> Fact:
    return Fact(
        kind="lakeformation.registered_location",
        subject={"type": "table", "file": "lf.json", "symbol": tabela, "catalog_id": ""},
        attrs={
            "registered": sim,
            "resource_arn": arn,
            "role_arn": "",
            "hybrid_access_enabled": None,
            "with_federation": None,
        },
        provenance=PROV,
    )


def _decisao(
    acao: str,
    decisao: str,
    denied_by: str = "implicit_deny",
    role: str = ROLE,
    recurso: str = "*",
    arquivo: str = "iam.json",
    **attrs: object,
) -> Fact:
    return Fact(
        kind="iam.access_decision",
        subject={"type": "job_run", "file": arquivo, "symbol": f"{role}#{acao}@{recurso}"},
        measures={"matched_statements": 0},
        attrs={
            "role_arn": role,
            "action": acao,
            "resource": recurso,
            "decision": decisao,
            "allowed": decisao == "allowed",
            "denied_by": "" if decisao == "allowed" else denied_by,
            **attrs,
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
        _registrada(False),
        _decisao("s3:PutObject", "implicitDeny", recurso=LOCAL + "/*"),
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


OUTRO_ROLE = "arn:aws:iam::111111111111:role/glue-outro"
SEM_NOME = "AccessDeniedException: Insufficient Lake Formation permission(s)"


def _linha(recurso: str) -> str:
    return (
        "AccessDeniedException: Insufficient Lake Formation permission(s) on "
        f"{recurso} (Service: AWSGlue; Status Code: 400)"
    )


def _sql(operacao: str, tabela: str = TABELA) -> Fact:
    return Fact(
        kind="sql.write_statement",
        subject={"type": "source_location", "file": "job.py", "line": 30},
        attrs={"operation": operacao, "table": tabela},
        provenance=PROV,
    )


def _razoes(saida: list[Fact]) -> list[str]:
    return sorted(
        f.attrs["reason"] for f in _de(saida, "lakeformation.missing_grant.unresolved")
    )


def test_nome_curto_na_mensagem_canoniza_contra_o_grant():
    pool = [_gatilho(linha=_linha("dim_cliente")), *cenario_fta_append_sem_all()[1:]]
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["resource"] == TABELA
    assert falta.attrs["missing"] == ["ALL"]
    # Colado no parentese tambem e nome de tabela.
    colado = [_gatilho(linha=_linha("dim_cliente(x)")), *cenario_fta_append_sem_all()[1:]]
    assert _de(build_missing_grant(colado), "lakeformation.missing_grant")


def test_nome_curto_com_homonimas_recusa_recurso_ambiguo():
    pool = [
        _gatilho(linha=_linha("dim_cliente")),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"]),
        _grant(["DESCRIBE"], tabela="staging.dim_cliente"),
    ]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "recurso_ambiguo"
    assert recusa.attrs["candidates"] == ["default.dim_cliente", "staging.dim_cliente"]


def test_homonima_de_outro_database_nao_casa():
    # Le staging.dim_cliente e escreve default.dim_cliente: o SELECT de default nao
    # e cobrado pela leitura de staging.
    pool = [
        _gatilho(),
        _fta(),
        _leitura("staging.dim_cliente"),
        _escrita(),
        _grant(["DESCRIBE"]),
    ]
    faltas = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert [f.attrs["operation"] for f in faltas] == ["write"]
    # Catalogo na frente continua casando pelo sufixo.
    com_catalogo = [
        _gatilho(),
        _fta(),
        _leitura("glue_catalog.default.dim_cliente"),
        _grant(["DESCRIBE"]),
    ]
    (falta,) = _de(build_missing_grant(com_catalogo), "lakeformation.missing_grant")
    assert falta.attrs["operation"] == "read"


def test_operacao_sem_alvo_ao_lado_de_outra_recusa_por_nome():
    pool = [
        _gatilho(),
        _fta(),
        _leitura(),
        _escrita(target=None),
        _grant(["DESCRIBE", "SELECT"]),
    ]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "operacao_com_alvo_nao_resolvido"
    assert recusa.attrs["operation"] == "write"
    assert "variavel" in recusa.attrs["unblocked_by"]


def test_mais_de_um_role_na_decisao_de_iam_e_principal_ambiguo():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["ALL"], principal=OUTRO_ROLE),
        _decisao("s3:PutObject", "allowed"),
        _decisao("s3:PutObject", "allowed", role=OUTRO_ROLE + "-b"),
    ]
    assert _razoes(build_missing_grant(pool)) == ["principal_ambiguo"]


def test_mensagem_que_nomeia_s3_ou_arn_nao_e_tabela():
    for bruto in (
        "s3://sparkforge-demo/default/dim_cliente",
        "arn:aws:glue:us-east-1:111111111111:table/default/dim_cliente",
    ):
        pool = [_gatilho(linha=_linha(bruto)), *cenario_fta_append_sem_all()[1:]]
        saida = build_missing_grant(pool)
        assert _de(saida, "lakeformation.missing_grant") == [], bruto
        (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
        assert recusa.attrs["reason"] == "recurso_nao_e_tabela"
        assert recusa.attrs["resource"] == bruto


def test_modo_de_escrita_sem_caixa():
    for modo in ("Overwrite", "overwritePartitions"):
        pool = [_gatilho(), _fta(), _escrita(mode=modo), _grant(["DESCRIBE"])]
        (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
        assert falta.attrs["operation"] == "overwrite", modo


def test_write_to_sem_modo_recusa_terminal_nao_medido():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(mode=None, api="dataframe_writer_v2"),
        _grant(["DESCRIBE", "SELECT"]),
    ]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    assert _razoes(saida) == ["terminal_de_escrita_nao_medido"]


def test_gatilhos_repetidos_dao_a_mesma_saida_em_qualquer_ordem():
    a = _gatilho(artefato="logs/a.json")
    b = _gatilho(artefato="logs/b.json")
    resto = cenario_fta_append_sem_all()[1:]
    ida = build_missing_grant([a, b, *resto])
    volta = build_missing_grant([b, a, *resto])
    assert [f.to_dict() for f in ida] == [f.to_dict() for f in volta]
    # A mesma politica vale para a recusa de recurso ambiguo.
    a2 = _gatilho(linha=SEM_NOME, artefato="logs/a.json")
    b2 = _gatilho(linha=SEM_NOME, artefato="logs/b.json")
    dois = [_fta(), _escrita(), _grant(["ALL"]), _grant(["ALL"], tabela="x.outra")]
    ida = build_missing_grant([a2, b2, *dois])
    volta = build_missing_grant([b2, a2, *dois])
    assert [f.to_dict() for f in ida] == [f.to_dict() for f in volta]


def test_grants_da_mesma_tabela_em_dois_catalogos_recusa():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"], catalog_id="111111111111"),
        _grant(["ALL"], principal=OUTRO_ROLE, catalog_id="222222222222"),
        _decisao("s3:PutObject", "allowed"),
    ]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    assert _razoes(saida) == ["catalogo_ambiguo"]


def test_mensagem_sem_recurso_e_duas_tabelas_recusa_recurso_ambiguo():
    pool = [
        _gatilho(linha=SEM_NOME),
        _fta(),
        _escrita(),
        _grant(["ALL"]),
        _grant(["ALL"], tabela="staging.outra"),
    ]
    assert _razoes(build_missing_grant(pool)) == ["recurso_ambiguo"]


def test_operacao_em_outro_alvo_recusa_nao_ligada():
    pool = [_gatilho(), _fta(), _leitura("staging.fato_venda"), _grant(["DESCRIBE"])]
    assert _razoes(build_missing_grant(pool)) == ["operacao_nao_ligada_ao_recurso"]


def test_sem_grant_coletado_recusa():
    saida = build_missing_grant([_gatilho(), _fta(), _escrita()])
    assert _razoes(saida) == ["grant_nao_coletado"]
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert "collect lakeformation" in recusa.attrs["unblocked_by"]


def test_dois_principais_sem_decisao_de_iam_recusa():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"]),
        _grant(["DESCRIBE"], principal=OUTRO_ROLE),
    ]
    assert _razoes(build_missing_grant(pool)) == ["principal_ambiguo"]


def test_create_table_exige_permissao_de_database_nao_coletada():
    pool = [_gatilho(), _fta(), _sql("create_table"), _grant(["ALL"])]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "permissao_de_database_nao_coletada"
    assert recusa.attrs["operation"] == "create"


def test_iam_allowed_principals_com_all_nao_acusa():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"]),
        _grant(["ALL"], principal="IAM_ALLOWED_PRINCIPALS"),
    ]
    assert build_missing_grant(pool) == []


def _so_recusas(saida: list[Fact]) -> list[Fact]:
    assert _de(saida, "lakeformation.missing_grant") == []
    return _de(saida, "lakeformation.missing_grant.unresolved")


def test_nome_com_pontuacao_ou_aspas_e_lido_e_nao_troca_de_tabela():
    # O pool so tem grant de default.dim_cliente; a mensagem nomeia OUTRA tabela.
    # Ler mal o nome e cair no candidato unico acusaria a tabela errada.
    for resto in (
        " on staging.outra, retry later",
        " on staging.outra; (Service: AWSGlue)",
        " on staging.outra: denied",
        " on staging.outra.",
        " on 'staging.outra' (Service: AWSGlue)",
        ' on "staging.outra"',
        " on `staging.outra`,",
        " on staging.outra)",
    ):
        pool = [_gatilho(linha=SEM_NOME + resto), *cenario_fta_append_sem_all()[1:]]
        (recusa,) = _so_recusas(build_missing_grant(pool))
        assert recusa.attrs["reason"] == "operacao_nao_ligada_ao_recurso", resto
        assert recusa.attrs["resource"] == "staging.outra", resto


def test_clausula_on_ilegivel_recusa_recurso_nao_lido():
    # ": Required Select on" nunca vem do matcher (a assinatura exige
    # "permission(s) on"); ler o token depois dele trocaria database por tabela.
    for resto in (
        ' on "staging"."outra"',
        " on 'minha tabela'",
        ": Required Describe on default",
    ):
        pool = [_gatilho(linha=SEM_NOME + resto), *cenario_fta_append_sem_all()[1:]]
        (recusa,) = _so_recusas(build_missing_grant(pool))
        assert recusa.attrs["reason"] == "recurso_nao_lido", resto
        assert "nao presume" in recusa.attrs["unblocked_by"]
        assert "on" in recusa.attrs["matched"], resto


def test_s3a_e_s3n_nao_sao_tabela():
    for bruto in ("s3a://sparkforge-demo/default/dim_cliente", "s3n://b/k"):
        pool = [_gatilho(linha=_linha(bruto)), *cenario_fta_append_sem_all()[1:]]
        (recusa,) = _so_recusas(build_missing_grant(pool))
        assert recusa.attrs["reason"] == "recurso_nao_e_tabela", bruto
        assert recusa.attrs["resource"] == bruto


def test_mais_de_um_role_nomeia_as_candidatas():
    outro = OUTRO_ROLE + "-b"
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["ALL"], principal=OUTRO_ROLE),
        _decisao("s3:PutObject", "allowed"),
        _decisao("s3:PutObject", "allowed", role=outro),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "principal_ambiguo"
    assert recusa.attrs["candidates"] == sorted([ROLE, outro])
    assert "mais de um role na decisao de IAM" in recusa.attrs["unblocked_by"]


def test_sem_decisao_de_iam_e_sem_principal_nomeado_recusa_nao_coletado():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"], principal="IAM_ALLOWED_PRINCIPALS"),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "principal_nao_coletado"
    assert "collect iam-access" in recusa.attrs["unblocked_by"]


def test_mensagem_sem_recurso_e_pool_sem_tabela_recusa_nao_nomeado():
    pool = [_gatilho(linha=SEM_NOME), _fta(), _escrita()]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "recurso_nao_nomeado"
    assert "collect" in recusa.attrs["unblocked_by"]


def test_api_ambigua_sem_modo_recusa_terminal_nao_medido():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(mode=None, api="ambigua"),
        _grant(["DESCRIBE", "SELECT"]),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "terminal_de_escrita_nao_medido"
    assert recusa.attrs["operation"] in OPERACOES_MAPEADAS
    assert recusa.attrs["writer_api"] == "ambigua"
    assert "ambigua" in recusa.attrs["unblocked_by"]


def test_write_to_sem_modo_sai_com_operacao_mapeada():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(mode=None, api="dataframe_writer_v2"),
        _grant(["DESCRIBE", "SELECT"]),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["operation"] in OPERACOES_MAPEADAS
    assert recusa.attrs["writer_api"] == "writeTo"


def test_operacao_sem_alvo_sozinha_nao_e_presumida():
    pool = [_gatilho(), _fta(), _escrita(target=None), _grant(["DESCRIBE"])]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "operacao_com_alvo_nao_resolvido"
    assert recusa.attrs["operation"] == "write"
    assert "deste tipo" in recusa.attrs["unblocked_by"]


def test_catalogo_vazio_ao_lado_de_outro_e_ambiguo():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"]),
        _grant(["ALL"], principal=OUTRO_ROLE, catalog_id="222222222222"),
        _decisao("s3:PutObject", "allowed"),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "catalogo_ambiguo"
    assert recusa.attrs["catalog_ids"] == ["", "222222222222"]


def test_alvo_e_mensagem_sem_diferenca_de_caixa():
    # O Glue Data Catalog guarda nomes em minusculas.
    pool = [_gatilho(), _fta(), _escrita(target="Default.Dim_Cliente"), _grant(["DESCRIBE"])]
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["operation"] == "write"
    mensagem = [
        _gatilho(linha=_linha("Default.Dim_Cliente")),
        *cenario_fta_append_sem_all()[1:],
    ]
    (falta,) = _de(build_missing_grant(mensagem), "lakeformation.missing_grant")
    assert falta.attrs["resource"] == TABELA


def test_linha_hostil_com_prefixo_repetido_nao_trava():
    # O texto do gatilho vem do artefato; um regex que recomeca em cada "permission(s)"
    # fica quadratico, e 20 mil repeticoes levavam dezenas de segundos.
    import time

    pool = [_gatilho(linha="permission(s)" * 20000), *cenario_fta_append_sem_all()[1:]]
    inicio = time.perf_counter()
    build_missing_grant(pool)
    assert time.perf_counter() - inicio < 2.0


# O matcher guarda 200 caracteres da mensagem (matcher.py `_TRECHO`,
# exception.py `message_head[:200]`); a assinatura casou na mensagem inteira.
TETO = 200
FRASE = "AccessDeniedException: Insufficient Lake Formation permission(s) on "


def _encostado(frase: str, resto: str = "") -> str:
    """Uma mensagem cujo corte em `TETO` cai logo depois de `frase`."""
    return "y" * (TETO - len(frase) - 1) + " " + frase + resto


def test_trecho_cortado_recusa_truncado_e_nao_acusa_o_candidato_unico():
    cenarios = {
        # (a) o corte cai antes da clausula: o candidato unico seria outra tabela.
        "antes_da_clausula": ("y" * 190 + " " + FRASE + "staging.outra")[:TETO],
        # (b) o corte cai no meio de default.dim_cliente_hist.
        "no_meio_do_nome": _encostado(FRASE + "default.dim_cliente", "_hist (x)")[:TETO],
        # (c) o corte cai logo depois de "on ".
        "logo_depois_do_on": _encostado(FRASE, "staging.outra")[:TETO],
    }
    for nome, trecho in cenarios.items():
        assert len(trecho) == TETO, nome
        pool = [_gatilho(linha=trecho), *cenario_fta_append_sem_all()[1:]]
        (recusa,) = _so_recusas(build_missing_grant(pool))
        assert recusa.attrs["reason"] == "trecho_truncado", nome
        assert "mensagem inteira" in recusa.attrs["unblocked_by"], nome
        assert "nao presume" in recusa.attrs["unblocked_by"], nome
    # Abaixo do teto e sem clausula, o candidato unico continua valendo.
    curto = [_gatilho(linha=SEM_NOME), *cenario_fta_append_sem_all()[1:]]
    (falta,) = _de(build_missing_grant(curto), "lakeformation.missing_grant")
    assert falta.attrs["resource"] == TABELA


def test_gatilho_real_guarda_o_teto_e_recusa_truncado():
    # Monta o gatilho pelo caminho REAL do matcher e do extrator de excecao: se o
    # teto mudar la, este teste acusa.
    from sparkforge.errors.matcher import build_signature_matches
    from sparkforge.facts.exception import build_exceptions
    from sparkforge.facts.lakeformation_missing_grant import _TETO_DO_TRECHO

    mensagem = _encostado(FRASE + "default.dim_cliente", "_hist (Service: AWSGlue)")
    log = Fact(
        kind="cloudwatch.log_event",
        subject={"type": "job_run", "job_name": "etl-dim", "job_run_id": "jr_1"},
        attrs={"message": mensagem},
        provenance=PROV,
    )
    falha = Fact(
        kind="spark.stage.failure",
        subject={"type": "stage", "stage_id": 3},
        attrs={"reason": "com.amazonaws.lakeformation.AccessDeniedException: " + mensagem},
        provenance=PROV,
    )
    gatilhos = [
        f
        for f in build_signature_matches([log, *build_exceptions([falha])])
        if f.kind == "error.signature_match" and f.attrs["signature_id"] == "ERR-LF-001"
    ]
    por_porta = {f.attrs["matched_on"]: f for f in gatilhos}
    assert sorted(por_porta) == ["log_line", "message_head"]
    assert len(por_porta["log_line"].attrs["matched_line"]) == _TETO_DO_TRECHO
    cabeca = por_porta["message_head"].attrs["matched_class"].split(": ", 1)[1]
    assert len(cabeca) == _TETO_DO_TRECHO
    for porta, gatilho in por_porta.items():
        pool = [gatilho, *cenario_fta_append_sem_all()[1:]]
        assert _razoes(build_missing_grant(pool)) == ["trecho_truncado"], porta


def test_operacao_sem_alvo_nao_cala_a_recusa_de_modelo():
    for modelo, razao in (([], "modelo_ausente"), ([_modelo("both")], "modelo_both")):
        pool = [_gatilho(), *modelo, _escrita(target=None), _grant(["DESCRIBE"])]
        assert _razoes(build_missing_grant(pool)) == sorted(
            [razao, "operacao_com_alvo_nao_resolvido"]
        )


def test_nome_exato_sem_caixa_ganha_da_qualificada_que_casa_pelo_sufixo():
    pool = [
        _gatilho(linha=_linha("Default.Dim_Cliente")),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"]),
        _grant(["DESCRIBE"], tabela="glue_catalog.default.dim_cliente"),
    ]
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["resource"] == TABELA


def test_write_to_sem_alvo_sai_com_operacao_mapeada():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(mode=None, target=None, api="dataframe_writer_v2"),
        _grant(["DESCRIBE"]),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "operacao_com_alvo_nao_resolvido"
    assert recusa.attrs["operation"] == "write"


def test_nome_com_cauda_de_json_ou_parentese_e_lido():
    for resto in (" on dim_cliente;'", ' on default.dim_cliente"}', " on default.dim_cliente)"):
        pool = [_gatilho(linha=SEM_NOME + resto), *cenario_fta_append_sem_all()[1:]]
        (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
        assert falta.attrs["resource"] == TABELA, resto


def test_nome_qualificado_que_casa_duas_tabelas_de_catalogo_e_ambiguo():
    pool = [
        _gatilho(),
        _fta(),
        _escrita(),
        _grant(["DESCRIBE"], tabela="cat_a.default.dim_cliente"),
        _grant(["DESCRIBE"], tabela="cat_b.default.dim_cliente"),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "recurso_ambiguo"
    assert recusa.attrs["resource"] == TABELA
    assert "casa com mais de uma" in recusa.attrs["unblocked_by"]


def test_recusas_de_clausulas_diferentes_nao_colapsam():
    a = _gatilho(linha=SEM_NOME + ' on "staging"."outra"', artefato="logs/a.json")
    b = _gatilho(linha=SEM_NOME + " on 'minha tabela'", artefato="logs/b.json")
    recusas = _so_recusas(build_missing_grant([a, b, *cenario_fta_append_sem_all()[1:]]))
    assert sorted(r.attrs["matched"] for r in recusas) == [
        'permission(s) on "staging"."outra"',
        "permission(s) on 'minha",
    ]
    assert len({r.id for r in recusas}) == 2


def _gatilhos_reais(mensagem: str, classe: str = "AccessDeniedException") -> dict[str, Fact]:
    """Os gatilhos ERR-LF-001 que o matcher real grava, por porta."""
    from sparkforge.errors.matcher import build_signature_matches
    from sparkforge.facts.exception import build_exceptions

    log = Fact(
        kind="cloudwatch.log_event",
        subject={"type": "job_run", "job_name": "etl-dim", "job_run_id": "jr_1"},
        attrs={"message": mensagem},
        provenance=PROV,
    )
    falha = Fact(
        kind="spark.stage.failure",
        subject={"type": "stage", "stage_id": 3},
        attrs={"reason": f"com.amazonaws.lakeformation.{classe}: " + mensagem},
        provenance=PROV,
    )
    return {
        f.attrs["matched_on"]: f
        for f in build_signature_matches([log, *build_exceptions([falha])])
        if f.kind == "error.signature_match" and f.attrs["signature_id"] == "ERR-LF-001"
    }


def test_corte_logo_depois_do_on_e_truncado_nas_duas_portas():
    # Pela cabeca da excecao o `strip` tira o espaco depois de "on" e o trecho fica com
    # 199 caracteres: o nome sumiu no corte, e isso nao e forma que o extrator nao le.
    mensagem = "y" * (TETO - len(FRASE)) + FRASE + "staging.outra"
    por_porta = _gatilhos_reais(mensagem)
    assert sorted(por_porta) == ["log_line", "message_head"]
    for porta, gatilho in por_porta.items():
        pool = [gatilho, *cenario_fta_append_sem_all()[1:]]
        assert _razoes(build_missing_grant(pool)) == ["trecho_truncado"], porta


def test_nome_inteiro_antes_do_teto_e_lido_nas_duas_portas():
    # 200 caracteres ou mais, e o nome termina antes do corte: nada foi cortado nele.
    mensagem = _encostado(FRASE + TABELA + " (Service: AWSGlue; Status Code: 400)")
    for porta, gatilho in _gatilhos_reais(mensagem).items():
        pool = [gatilho, *cenario_fta_append_sem_all()[1:]]
        (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
        assert falta.attrs["resource"] == TABELA, porta


def test_classe_longa_nao_conta_no_teto_da_cabeca():
    # A cabeca fica abaixo do teto e so `classe: cabeca` passa dele: o nome no fim e
    # inteiro, e nao ha corte a presumir.
    mensagem = "y" * 20 + " " + FRASE + TABELA
    classe = "C" * (TETO - len(mensagem) + 10) + "AccessDeniedException"
    gatilho = _gatilhos_reais(mensagem, classe=classe)["message_head"]
    assert len(gatilho.attrs["matched_class"]) > TETO
    pool = [gatilho, *cenario_fta_append_sem_all()[1:]]
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["resource"] == TABELA


def test_segundo_permission_s_decide_onde_o_nome_termina():
    linha = ("Check permission(s) based on role. " + "y" * 200)[: TETO - len(FRASE) - 16]
    trecho = (linha + " " + FRASE + "default.dim_cliente_hist")[:TETO]
    assert trecho.endswith("default.dim_cli")
    pool = [
        _gatilho(linha=trecho),
        *cenario_fta_append_sem_all()[1:],
        _grant(["ALL"], tabela="default.dim_cli"),
    ]
    assert _razoes(build_missing_grant(pool)) == ["trecho_truncado"]


def test_truncado_das_duas_portas_e_uma_recusa_so():
    mensagem = _encostado(FRASE + "default.dim_cliente", "_hist (Service: AWSGlue)")
    gatilhos = list(_gatilhos_reais(mensagem).values())
    assert len(gatilhos) == 2
    pool = [*gatilhos, *cenario_fta_append_sem_all()[1:]]
    assert _razoes(build_missing_grant(pool)) == ["trecho_truncado"]


def test_fgac_escrita_cobra_iam_com_denied_by():
    (falta,) = _de(
        build_missing_grant(cenario_fgac_escrita_negada()), "lakeformation.missing_grant"
    )
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
    assert "secao 6" in recusa.attrs["unblocked_by"]
    assert "missing" not in recusa.attrs


def test_modelo_ou_runtime_desconhecido_recusa_por_nome():
    both = [_gatilho(), _modelo("both"), _escrita(), _grant(["SELECT"])]
    ausente = [_gatilho(), _escrita(), _grant(["SELECT"])]
    sem_runtime = [
        _gatilho(), _modelo("fgac"), _escrita(), _decisao("s3:PutObject", "implicitDeny")
    ]
    razoes = []
    for pool in (both, ausente, sem_runtime):
        (recusa,) = _de(build_missing_grant(pool), "lakeformation.missing_grant.unresolved")
        assert recusa.attrs["unblocked_by"], recusa.attrs
        razoes.append(recusa.attrs["reason"])
    assert razoes == ["modelo_both", "modelo_ausente", "runtime_ausente"]


def test_fgac_escrita_em_runtime_sem_suporte_nao_e_permissao():
    pool = [
        _gatilho(), _modelo("fgac"), _glue("5.0"), _escrita(),
        _decisao("s3:PutObject", "implicitDeny"),
    ]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _de(saida, "lakeformation.missing_grant.unresolved")
    assert recusa.attrs["reason"] == "escrita_fgac_nao_suportada_no_runtime"
    assert recusa.attrs["runtime"] == "5.0"


def test_fgac_negacao_de_outro_role_ao_lado_do_job_e_principal_ambiguo():
    base = [_gatilho(), _modelo("fgac"), _glue("5.1"), _registrada(False)]
    # A negacao e de outro role, ao lado de um allowed do role do job: com dois roles
    # decididos nada diz qual e o do job, e a negacao alheia nao vira acusacao.
    so_outro = [*base, _escrita(), _decisao("s3:PutObject", "allowed", role=ROLE),
                _decisao("s3:PutObject", "implicitDeny", role=OUTRO_ROLE)]
    assert _razoes(build_missing_grant(so_outro)) == ["principal_ambiguo"]


def test_fgac_registro_qualificado_por_catalogo_casa_pelo_sufixo():
    base = [_gatilho(), _modelo("fgac"), _glue("5.1")]
    # Registro de nome qualificado com catalogo casa pelo sufixo, como na T2.
    registrada = Fact(
        kind="lakeformation.registered_location",
        subject={"type": "table", "symbol": "glue_catalog.default.dim_cliente"},
        attrs={"registered": True},
        provenance=PROV,
    )
    pool = [*base, _escrita(), registrada, _decisao("s3:PutObject", "implicitDeny")]
    assert _razoes(build_missing_grant(pool)) == [
        "conflito_declarado_fgac_escrita_registrada"
    ]


def test_fgac_overwrite_sem_simulacao_recusa_cada_acao():
    pool = [
        _gatilho(), _modelo("fgac"), _glue("5.1"), _escrita(mode="overwrite"),
        _registrada(False),
    ]
    recusas = _so_recusas(build_missing_grant(pool))
    assert sorted(r.attrs["action"] for r in recusas) == ["s3:DeleteObject", "s3:PutObject"]
    assert {r.attrs["reason"] for r in recusas} == {"acao_iam_nao_simulada"}
    assert all("collect iam-access" in r.attrs["unblocked_by"] for r in recusas)


def _fgac_51(*resto: Fact) -> list[Fact]:
    return [_gatilho(), _modelo("fgac"), _glue("5.1"), _escrita(), *resto]


def test_fgac_sem_registro_coletado_recusa_e_nao_cobra_o_iam():
    # Sem saber se a tabela e registrada, cobrar o IAM seria escolher o lado que o
    # conflito declarado da secao 6 deixa em aberto.
    for extra in ([], [_registrada(False, tabela="staging.outra")]):
        pool = _fgac_51(*extra, _decisao("s3:PutObject", "implicitDeny"))
        (recusa,) = _so_recusas(build_missing_grant(pool))
        assert recusa.attrs["reason"] == "registro_nao_coletado"
        assert "conflito declarado" in recusa.attrs["unblocked_by"]
        assert "sparkforge collect lakeformation" in recusa.attrs["unblocked_by"]


def test_fgac_negacoes_da_mesma_acao_em_dois_recursos_nao_colapsam():
    # As duas falam pela tabela: explicitDeny em `*` contem a localizacao, e o
    # implicitDeny e no prefixo de objetos dela.
    explicita = _decisao(
        "s3:PutObject", "explicitDeny", denied_by="explicit_deny", recurso="*"
    )
    implicita = _decisao("s3:PutObject", "implicitDeny", recurso=LOCAL + "/*")
    ida = build_missing_grant(_fgac_51(_registrada(False), explicita, implicita))
    volta = build_missing_grant(_fgac_51(_registrada(False), implicita, explicita))
    assert [f.to_dict() for f in ida] == [f.to_dict() for f in volta]
    faltas = _de(ida, "lakeformation.missing_grant")
    assert len(faltas) == 2
    assert sorted(f.attrs["denied_by"] for f in faltas) == ["explicit_deny", "implicit_deny"]
    assert sorted(f.attrs["iam_resource"] for f in faltas) == ["*", LOCAL + "/*"]


def test_fgac_negacao_em_outro_bucket_nao_acusa_a_tabela():
    pool = _fgac_51(
        _registrada(False),
        _decisao("s3:PutObject", "allowed", recurso=LOCAL + "/*"),
        _decisao("s3:PutObject", "implicitDeny", recurso="arn:aws:s3:::outro-bucket/x/*"),
    )
    assert build_missing_grant(pool) == []


def test_fgac_negacao_implicita_num_objeto_da_tabela_nao_fala_pela_tabela():
    # Uma policy escopada ao prefixo da tabela tambem da implicitDeny num objeto
    # qualquer que ela nao nomeia; o objeto nao e o prefixo de objetos da tabela.
    pool = _fgac_51(
        _registrada(False),
        _decisao("s3:PutObject", "implicitDeny", recurso=LOCAL + "/part-0.parquet"),
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "acao_iam_nao_simulada"


def test_fgac_so_simulada_fora_da_tabela_recusa_nao_simulada():
    pool = _fgac_51(
        _registrada(False),
        _decisao("s3:PutObject", "implicitDeny", recurso="arn:aws:s3:::outro-bucket/x/*"),
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "acao_iam_nao_simulada"
    assert "localizacao da tabela" in recusa.attrs["unblocked_by"]


def test_fgac_sem_localizacao_e_dois_recursos_recusa():
    pool = _fgac_51(
        _registrada(False, arn=""),
        _decisao("s3:PutObject", "allowed", recurso=LOCAL + "/*"),
        _decisao("s3:PutObject", "implicitDeny", recurso="arn:aws:s3:::outro-bucket/x/*"),
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "recurso_iam_nao_ligado_a_tabela"
    assert recusa.attrs["action"] == "s3:PutObject"
    assert "localizacao" in recusa.attrs["unblocked_by"]
    assert "/*" in recusa.attrs["unblocked_by"]


def test_fgac_sem_localizacao_negacao_implicita_num_recurso_so_recusa():
    # Sem a localizacao, nenhum implicitDeny fala pela tabela, nem o de `*`: uma
    # policy escopada a ela tambem nega ali.
    um = _fgac_51(_registrada(False, arn=""), _decisao("s3:PutObject", "implicitDeny"))
    (recusa,) = _so_recusas(build_missing_grant(um))
    assert recusa.attrs["reason"] == "recurso_iam_nao_ligado_a_tabela"


def test_fgac_sem_localizacao_negacao_explicita_em_estrela_acusa():
    # explicitDeny em `*` vale para qualquer localizacao, conhecida ou nao.
    pool = _fgac_51(
        _registrada(False, arn=""),
        _decisao("s3:PutObject", "explicitDeny", denied_by="explicit_deny"),
    )
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["iam_resource"] == "*"
    assert falta.attrs["denied_by"] == "explicit_deny"


def _glue_com(distintas: int, versao: str) -> Fact:
    return Fact(
        kind="env.runtime_signal",
        subject={"type": "job_run", "symbol": "glue"},
        measures={"distinct_versions": distintas, "source_count": distintas},
        attrs={"component": "glue", "resolved": versao, "observed": [versao]},
        provenance={"extractor": "runtime_detect@0.1.0"},
    )


def _tf_glue(valor: str, literal: bool = True, block: str = "root") -> Fact:
    return Fact(
        kind="tf.attribute",
        subject={"type": "tf_resource", "file": "main.tf", "symbol": "aws_glue_job.etl"},
        attrs={
            "key": "glue_version", "value": valor, "present": True,
            "literal": literal, "block": block,
        },
        provenance=PROV,
    )


def _fgac_sem_runtime(*runtime: Fact) -> list[Fact]:
    return [
        _gatilho(), _modelo("fgac"), *runtime, _escrita(), _registrada(False),
        _decisao("s3:PutObject", "implicitDeny", recurso=LOCAL + "/*"),
    ]


def test_runtime_divergente_por_sinal_ou_por_terraform():
    for runtime in (
        [_glue("5.1"), _glue("5.0")],
        [_glue_com(2, "5.1")],
        [_tf_glue("5.1"), _tf_glue("4.0")],
    ):
        (recusa,) = _so_recusas(build_missing_grant(_fgac_sem_runtime(*runtime)))
        assert recusa.attrs["reason"] == "runtime_divergente", runtime
        assert recusa.attrs["unblocked_by"]


def test_runtime_sem_celula_na_matriz_recusa():
    (recusa,) = _so_recusas(build_missing_grant(_fgac_sem_runtime(_glue("6.0"))))
    assert recusa.attrs["reason"] == "runtime_sem_celula_na_matriz"
    assert recusa.attrs["runtime"] == "6.0"


def test_glue_version_do_terraform_so_conta_literal_na_raiz():
    (falta,) = _de(
        build_missing_grant(_fgac_sem_runtime(_tf_glue("5.1"))), "lakeformation.missing_grant"
    )
    assert falta.attrs["runtime"] == "5.1"
    for ignorado in (_tf_glue("var.glue", literal=False), _tf_glue("5.1", block="args")):
        (recusa,) = _so_recusas(build_missing_grant(_fgac_sem_runtime(ignorado)))
        assert recusa.attrs["reason"] == "runtime_ausente"


def test_fgac_em_runtime_sem_o_modelo_spark_native_recusa_por_nome_proprio():
    (recusa,) = _so_recusas(build_missing_grant(_fgac_sem_runtime(_glue("4.0"))))
    assert recusa.attrs["reason"] == "fgac_spark_native_inexistente_no_runtime"
    assert recusa.attrs["runtime"] == "4.0"
    assert "nao existia" in recusa.attrs["unblocked_by"]


def test_fta_registro_qualificado_por_catalogo_casa_no_lado_lf():
    pool = [
        *cenario_fta_append_sem_all(),
        _registrada(False, tabela="glue_catalog.default.dim_cliente"),
    ]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "fta_escrita_em_alvo_nao_registrado"


# SimulatePrincipalPolicy avalia cada par (acao, recurso) literalmente. Uma policy
# escopada ao prefixo da tabela da implicitDeny em `*`, no bucket nu, na localizacao
# sem `/*`, num prefixo mais largo e num objeto qualquer: nenhum deles e evidencia
# sobre a tabela. explicitDeny num recurso que contem a tabela vale para ela.
BUCKET = "arn:aws:s3:::sparkforge-demo"
PUT = "s3:PutObject"


def _explicito(recurso: str) -> Fact:
    return _decisao(PUT, "explicitDeny", denied_by="explicit_deny", recurso=recurso)


def test_implicita_em_estrela_ao_lado_de_allowed_escopado_nao_acusa():
    # a1
    pool = _fgac_51(
        _registrada(False),
        _decisao(PUT, "implicitDeny", recurso="*"),
        _decisao(PUT, "allowed", recurso=LOCAL + "/*"),
    )
    assert build_missing_grant(pool) == []


def test_so_implicita_em_estrela_recusa_nao_simulada():
    # a3
    pool = _fgac_51(_registrada(False), _decisao(PUT, "implicitDeny", recurso="*"))
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "acao_iam_nao_simulada"
    assert "--resource-arn <localizacao>/*" in recusa.attrs["unblocked_by"]


def test_explicita_em_estrela_vence_o_allowed_escopado():
    # a2: explicitDeny em `*` contem a tabela, e explicitDeny vence allowed.
    pool = _fgac_51(
        _registrada(False), _explicito("*"), _decisao(PUT, "allowed", recurso=LOCAL + "/*")
    )
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["iam_resource"] == "*"
    assert falta.attrs["decision"] == "explicitDeny"


def test_implicita_no_bucket_nu_ou_na_localizacao_sem_barra_nao_acusa():
    # a4 e a5
    for recurso in (BUCKET, LOCAL, LOCAL + "/"):
        pool = _fgac_51(
            _registrada(False),
            _decisao(PUT, "implicitDeny", recurso=recurso),
            _decisao(PUT, "allowed", recurso=LOCAL + "/*"),
        )
        assert build_missing_grant(pool) == [], recurso


def test_registro_no_bucket_nao_acusa_pelo_prefixo_de_outra_tabela():
    # C1: com a localizacao no bucket, `staging/outra/*` fica dentro dela e nao e
    # o prefixo de objetos de default.dim_cliente.
    pool = _fgac_51(
        _registrada(False, arn=BUCKET),
        _decisao(PUT, "allowed", recurso=BUCKET + "/default/dim_cliente/*"),
        _decisao(PUT, "implicitDeny", recurso=BUCKET + "/staging/outra/*"),
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "acao_iam_nao_simulada"


def test_prefixo_irmao_nao_pertence_a_tabela():
    for decisao in (
        _decisao(PUT, "implicitDeny", recurso=LOCAL + "_hist/*"),
        _explicito(LOCAL + "_hist/*"),
    ):
        pool = _fgac_51(_registrada(False), decisao)
        (recusa,) = _so_recusas(build_missing_grant(pool))
        assert recusa.attrs["reason"] == "acao_iam_nao_simulada"


def test_prefixo_do_bucket_acusa_so_com_explicit_deny():
    (falta,) = _de(
        build_missing_grant(_fgac_51(_registrada(False), _explicito(BUCKET + "/*"))),
        "lakeformation.missing_grant",
    )
    assert falta.attrs["iam_resource"] == BUCKET + "/*"
    implicita = _fgac_51(
        _registrada(False), _decisao(PUT, "implicitDeny", recurso=BUCKET + "/*")
    )
    (recusa,) = _so_recusas(build_missing_grant(implicita))
    assert recusa.attrs["reason"] == "acao_iam_nao_simulada"


def test_recurso_em_s3_uri_ou_arn_e_barra_final_normalizam():
    uri = "s3://sparkforge-demo/default/dim_cliente"
    for local, recurso in ((uri + "/", LOCAL + "/*"), (LOCAL, uri + "/*")):
        pool = _fgac_51(
            _registrada(False, arn=local), _decisao(PUT, "implicitDeny", recurso=recurso)
        )
        (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
        assert falta.attrs["iam_resource"] == recurso, local


def test_decisoes_da_tabela_isolada():
    from sparkforge.facts.lakeformation_missing_grant import _decisoes_da_tabela

    negada = _decisao(PUT, "implicitDeny", recurso=LOCAL + "/*")
    coberta = _decisao(PUT, "allowed", recurso=LOCAL + "/*")
    estrela = _decisao(PUT, "implicitDeny", recurso="*")
    assert _decisoes_da_tabela([negada, estrela], PUT, LOCAL) == ([negada], None)
    assert _decisoes_da_tabela([coberta, estrela], PUT, LOCAL) == ([], None)
    assert _decisoes_da_tabela([estrela], PUT, LOCAL) == ([], "acao_iam_nao_simulada")
    assert _decisoes_da_tabela([negada], "s3:DeleteObject", LOCAL) == (
        [],
        "acao_iam_nao_simulada",
    )


def test_fgac_acusacao_do_lado_iam_declara_o_escopo_do_registro():
    (falta,) = _de(
        build_missing_grant(cenario_fgac_escrita_negada()), "lakeformation.missing_grant"
    )
    assert falta.attrs["registration_scope"] == "exact_arn"
    assert "prefixo pai" in falta.attrs["caveat"]
    assert "conflito declarado" in falta.attrs["caveat"]


def test_decisao_sem_allowed_booleano_recusa_malformada():
    pool = _fgac_51(
        _registrada(False), _decisao(PUT, "implicitDeny", recurso=LOCAL + "/*", allowed=None)
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "decisao_iam_malformada"
    assert "allowed" in recusa.attrs["unblocked_by"]


def test_decisao_negada_com_nome_desconhecido_recusa():
    pool = _fgac_51(
        _registrada(False), _decisao(PUT, "denied", recurso=LOCAL + "/*")
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "decisao_iam_desconhecida"
    assert recusa.attrs["decision"] == "denied"


def test_duas_localizacoes_para_a_mesma_tabela_nao_escolhem_a_primeira():
    outra = "arn:aws:s3:::sparkforge-demo/staging/outra"
    negada = _decisao(PUT, "implicitDeny", recurso=LOCAL + "/*")
    for registros in (
        [_registrada(False), _registrada(False, arn=outra)],
        [_registrada(False, arn=outra), _registrada(False)],
    ):
        (recusa,) = _so_recusas(build_missing_grant(_fgac_51(*registros, negada)))
        assert recusa.attrs["reason"] == "recurso_iam_nao_ligado_a_tabela"


def test_duas_decisoes_do_mesmo_recurso_dao_a_mesma_evidencia_em_qualquer_ordem():
    a = _decisao(PUT, "implicitDeny", recurso=LOCAL + "/*", arquivo="a.json")
    b = _decisao(PUT, "implicitDeny", recurso=LOCAL + "/*", arquivo="b.json")
    ida = build_missing_grant(_fgac_51(_registrada(False), a, b))
    volta = build_missing_grant(_fgac_51(_registrada(False), b, a))
    assert [f.to_dict() for f in ida] == [f.to_dict() for f in volta]


def test_implicita_e_allowed_no_mesmo_prefixo_da_tabela_recusa_contraditoria():
    # Dois artefatos de iam-access dizem o oposto sobre o mesmo par (acao, recurso):
    # nenhum dos dois fala sozinho pela tabela.
    pool = _fgac_51(
        _registrada(False),
        _decisao(PUT, "implicitDeny", recurso=LOCAL + "/*", arquivo="iam_a.json"),
        _decisao(PUT, "allowed", recurso=LOCAL + "/*", arquivo="iam_b.json"),
    )
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "decisoes_iam_contraditorias"
    assert "mesmo recurso" in recusa.attrs["unblocked_by"]


def test_ressalva_do_registro_cobre_localizacao_mais_larga_que_a_tabela():
    saida = build_missing_grant(cenario_fgac_escrita_negada())
    (falta,) = _de(saida, "lakeformation.missing_grant")
    assert "mais larga que a tabela" in falta.attrs["caveat"]


def _escrita_modo_nao_lido(target: str | None = TABELA) -> Fact:
    """`pyspark.write` de `.mode(m)`, `mode=m` ou `insertInto(t, overwrite=m)`."""
    attrs: dict = {"api": "dataframe_writer_v1", "mode_unresolved": True}
    if target is not None:
        attrs["target"] = target
    return Fact(
        kind="pyspark.write",
        subject={"type": "source_location", "file": "job.py", "line": 30},
        attrs=attrs,
        provenance=PROV,
    )


def test_fgac_modo_nao_lido_nao_presume_write_e_nao_cala_delete_object():
    # PutObject allowed no prefixo da tabela cobriria um write presumido e a saida
    # seria [] -- "o grant cobre". Se o modo for overwrite, DeleteObject nao foi
    # simulado: a operacao e desconhecida e sai recusada por nome.
    pool = [
        _gatilho(),
        _modelo("fgac"),
        _glue("5.1"),
        _escrita_modo_nao_lido(),
        _registrada(False),
        _decisao("s3:PutObject", "allowed", recurso=LOCAL + "/*"),
    ]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    (recusa,) = _so_recusas(saida)
    assert recusa.attrs["reason"] == "modo_de_escrita_nao_lido"
    assert recusa.attrs["operation"] in OPERACOES_MAPEADAS
    assert "s3:DeleteObject" in recusa.attrs["unblocked_by"]


def test_fta_modo_nao_lido_recusa_em_vez_de_acusar_write():
    pool = [_gatilho(), _fta(), _escrita_modo_nao_lido(), _grant(["DESCRIBE", "SELECT"])]
    saida = build_missing_grant(pool)
    assert _de(saida, "lakeformation.missing_grant") == []
    assert _razoes(saida) == ["modo_de_escrita_nao_lido"]


def test_escrita_v1_sem_modo_e_sem_marca_continua_write():
    # saveAsTable/insertInto/save sem modo: o default e errorifexists (save,
    # saveAsTable) ou append (insertInto), e os dois sao write.
    pool = [_gatilho(), _fta(), _escrita(mode=None), _grant(["DESCRIBE", "SELECT"])]
    (falta,) = _de(build_missing_grant(pool), "lakeformation.missing_grant")
    assert falta.attrs["operation"] == "write"


def test_modo_nao_lido_sem_alvo_sai_como_alvo_nao_resolvido():
    pool = [_gatilho(), _fta(), _escrita_modo_nao_lido(target=None), _grant(["ALL"])]
    (recusa,) = _so_recusas(build_missing_grant(pool))
    assert recusa.attrs["reason"] == "operacao_com_alvo_nao_resolvido"
    assert recusa.attrs["operation"] in OPERACOES_MAPEADAS
