import ast

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
