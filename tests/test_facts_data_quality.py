import ast

import pytest

from sparkforge.facts.data_quality import (
    EMITTED_KINDS,
    extract_data_quality,
    extract_data_quality_path,
    extract_data_quality_tree,
)


def _facts(source: str):
    return extract_data_quality(ast.parse(source), "job.py")


def test_o_modulo_varrido_deixa_sentinela():
    facts = _facts("x = 1\n")
    kinds = [f.kind for f in facts]
    assert kinds == ["dq.module_analyzed"]
    assert facts[0].measures["check_count"] == 0


def test_filter_count_comparado_e_um_check_artesanal():
    facts = _facts(
        "ruins = clientes.filter(clientes.cpf.isNull()).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('cpf nulo')\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 1
    assert checks[0].attrs["framework"] == "handmade"
    assert checks[0].attrs["target"] == "clientes"
    assert checks[0].subject["line"] == 1


def test_alvo_que_nao_e_variavel_vira_unresolved():
    facts = _facts("ruins = spark.table('t').filter('x is null').count()\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.unresolved"]
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert unresolved.attrs["reason"] == "unresolved_target"


def test_o_alvo_nao_resolvido_e_contado_na_sentinela():
    facts = _facts("ruins = spark.table('t').filter('x is null').count()\n")
    sentinela = [f for f in facts if f.kind == "dq.module_analyzed"][0]
    assert sentinela.measures["unresolved_count"] == 1
    assert sentinela.measures["check_count"] == 0


@pytest.mark.parametrize(
    "source",
    [
        # Forma canonica de leitura Delta/Iceberg/JDBC: o terminal e `load`, e
        # `format` esta na frente dele.
        "r = spark.read.format('delta').load('s3://b/p').filter('x is null').count()",
        # O terminal nem sempre e o primeiro elo: `option`/`schema` configuram o
        # reader antes dele.
        "r = spark.read.option('mergeSchema', 'true').parquet('s3://b/p').filter('x').count()",
        "r = spark.read.schema(esquema).json('s3://b/p').filter('x').count()",
        "r = spark.table('t').filter('x').count()",
        "r = spark.sql('select * from t').filter('x').count()",
    ],
)
def test_nenhuma_cadeia_de_leitura_nomeia_a_sessao_como_alvo(source):
    facts = _facts(source + "\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.unresolved"]
    assert [f.attrs.get("target") for f in facts if f.kind == "dq.check"] == []


def test_kind_fora_do_namespace_declarado_e_erro():
    assert "dq.check" in EMITTED_KINDS
    assert "dq.module_analyzed" in EMITTED_KINDS


def test_arquivo_valido_e_lido_com_ancora_relativa_e_sha(tmp_path):
    job = tmp_path / "jobs" / "vendas.py"
    job.parent.mkdir()
    job.write_text("ruins = vendas.filter(vendas.valor < 0).count()\n", encoding="utf-8")

    facts = extract_data_quality_path(job, tmp_path)

    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 1
    assert checks[0].subject["file"] == "jobs/vendas.py"
    assert checks[0].provenance["artifact"] == "jobs/vendas.py"
    assert len(checks[0].provenance["artifact_sha256"]) == 64
    assert [f.kind for f in facts if f.kind == "dq.module_analyzed"] == ["dq.module_analyzed"]


def test_sintaxe_quebrada_vira_um_unico_unresolved(tmp_path):
    quebrado = tmp_path / "quebrado.py"
    quebrado.write_text("def f(:\n    pass\n", encoding="utf-8")

    facts = extract_data_quality_path(quebrado, tmp_path)

    assert [f.kind for f in facts] == ["dq.unresolved"]
    assert facts[0].attrs["reason"] == "syntax_error"
    assert facts[0].subject["file"] == "quebrado.py"


def test_arvore_varre_todos_os_py_e_um_quebrado_nao_derruba_os_outros(tmp_path):
    (tmp_path / "bom.py").write_text(
        "ruins = vendas.filter(vendas.valor < 0).count()\n", encoding="utf-8"
    )
    (tmp_path / "quebrado.py").write_text("def f(:\n    pass\n", encoding="utf-8")

    facts = extract_data_quality_tree(tmp_path, tmp_path)

    assert [f.kind for f in facts if f.kind == "dq.check"] == ["dq.check"]
    assert [f.subject["file"] for f in facts if f.kind == "dq.unresolved"] == ["quebrado.py"]
    # Sentinela por arquivo lido -- o quebrado nao produz sentinela, produz o
    # unresolved que o conta.
    assert [f.subject["file"] for f in facts if f.kind == "dq.module_analyzed"] == ["bom.py"]


def test_check_depois_do_write_marca_a_posicao():
    facts = _facts(
        "vendas.write.mode('overwrite').parquet('s3://b/p')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "after_write"


def test_check_antes_do_write_marca_a_posicao():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.mode('overwrite').parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "before_write"


def test_modulo_que_valida_e_nao_escreve_nao_e_before_write():
    facts = _facts("ruins = vendas.filter(vendas.valor < 0).count()\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "no_write_in_module"


def test_o_write_que_data_o_check_e_o_primeiro_do_modulo():
    # Write dentro de laco e write no fim: o primeiro do modulo esta na linha 2,
    # entao o check da linha 3 valida DEPOIS de ja ter publicado. A travessia de
    # `ast.walk` e por nivel, nao por linha -- o write aninhado e visitado por
    # ultimo -- entao so a menor linha responde certo.
    facts = _facts(
        "for p in particoes:\n"
        "    vendas.write.mode('append').parquet(p)\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/final')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "after_write"


def test_write_de_cadeia_de_leitura_nao_data_o_check_pela_sessao():
    # `spark.read.parquet(...).write...` tem raiz `spark`, que NAO e o dado
    # escrito. Se ela entrasse no registro de writes, um check cuja cadeia
    # tambem enraize em `spark` seria datado contra a publicacao de um dado que
    # nunca o tocou.
    facts = _facts(
        "spark.read.parquet('s3://b/in').write.parquet('s3://b/out')\n"
        "ruins = spark.filter('x is null').count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "no_write_in_module"


def test_write_sobre_retorno_de_funcao_nao_derruba_a_extracao():
    facts = _facts(
        "carrega('vendas').write.parquet('s3://b/p')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "no_write_in_module"


def test_check_sobre_df_nao_persistido_com_action_depois():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\nvendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is False
    assert check.attrs["action_after_check"] is True


def test_df_persistido_antes_do_check():
    facts = _facts(
        "vendas.cache()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True


def test_persist_depois_do_check_nao_torna_o_alvo_persistido():
    facts = _facts("ruins = vendas.filter(vendas.valor < 0).count()\nvendas.persist()\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is False


def test_o_proprio_check_nao_e_action_depois_de_si_mesmo():
    facts = _facts("ruins = vendas.filter(vendas.valor < 0).count()\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["action_after_check"] is False


def test_dois_checks_no_mesmo_alvo_contam_um_ao_outro():
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count()\n"
        "b = vendas.filter(vendas.cliente.isNull()).count()\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 2
    assert {c.measures["checks_on_target"] for c in checks} == {2}
    assert {c.attrs["shares_scan"] for c in checks} == {False}


def test_checks_em_alvos_diferentes_nao_se_contam():
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count()\n"
        "b = clientes.filter(clientes.cpf.isNull()).count()\n"
    )
    checks = {c.attrs["target"]: c for c in facts if c.kind == "dq.check"}
    assert checks["vendas"].measures["checks_on_target"] == 1
    assert checks["clientes"].measures["checks_on_target"] == 1


def test_check_unico_nao_compartilha_varredura():
    facts = _facts("a = vendas.filter(vendas.valor < 0).count()\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.measures["checks_on_target"] == 1
    assert check.attrs["shares_scan"] is False


def test_alvo_nao_resolvido_nao_ganha_atributo_de_correlacao():
    # Sem alvo nao ha posicao relativa a apurar: preencher qualquer um destes
    # seria adivinhar.
    facts = _facts(
        "spark.table('t').write.parquet('s3://b/p')\n"
        "ruins = spark.table('t').filter('x is null').count()\n"
    )
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert "position_vs_write" not in unresolved.attrs
    assert "target_persisted" not in unresolved.attrs
    assert "action_after_check" not in unresolved.attrs
    assert "shares_scan" not in unresolved.attrs
    assert "checks_on_target" not in unresolved.measures


def test_arquivo_indecodificavel_vira_fact_e_nao_derruba_a_arvore(tmp_path):
    # `read_text` levanta UnicodeDecodeError -- um ValueError, NAO um OSError --
    # entao a travessia so continua se a guarda for larga.
    (tmp_path / "bom.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "binario.py").write_bytes(b"\xff\xfe\x00nao e utf-8\n")

    facts = extract_data_quality_tree(tmp_path, tmp_path)

    unresolved = [f for f in facts if f.kind == "dq.unresolved"]
    assert [f.subject["file"] for f in unresolved] == ["binario.py"]
    assert unresolved[0].attrs["reason"] == "read_error"
    assert [f.subject["file"] for f in facts if f.kind == "dq.module_analyzed"] == ["bom.py"]
