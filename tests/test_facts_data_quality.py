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


def test_nome_igual_em_funcoes_diferentes_nao_se_datam():
    # `vendas` de `a` e `vendas` de `b` sao dois parametros distintos. Datar o
    # check de `b` contra o write de `a` e o alvo adivinhado que a fase recusa,
    # so que por colisao de nome em vez de por raiz de cadeia.
    facts = _facts(
        "def a(vendas):\n"
        "    vendas.write.parquet(1)\n"
        "def b(vendas):\n"
        "    return vendas.filter(1).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "no_write_in_module"


def test_dentro_da_mesma_funcao_a_correlacao_continua():
    facts = _facts(
        "def publica(vendas):\n"
        "    vendas.write.parquet(1)\n"
        "    return vendas.filter(1).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "after_write"


def test_action_de_homonimo_em_outra_funcao_nao_conta():
    facts = _facts(
        "def valida(vendas):\n"
        "    return vendas.filter(1).count()\n"
        "def publica(vendas):\n"
        "    vendas.write.parquet(1)\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["action_after_check"] is False
    assert check.attrs["position_vs_write"] == "no_write_in_module"


def test_cache_de_homonimo_em_outra_funcao_nao_persiste_o_alvo():
    facts = _facts(
        "def prepara(vendas):\n"
        "    vendas.cache()\n"
        "def valida(vendas):\n"
        "    return vendas.filter(1).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is False


def test_checks_homonimos_em_funcoes_diferentes_nao_se_contam():
    facts = _facts(
        "def a(vendas):\n"
        "    return vendas.filter(1).count()\n"
        "def b(vendas):\n"
        "    return vendas.filter(2).count()\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 2
    assert {c.measures["checks_on_target"] for c in checks} == {1}


def test_rebind_entre_write_e_check_omite_a_posicao():
    # O alvo do check e um DataFrame recem-carregado que nunca foi escrito.
    # Chave ausente e a forma de dizer "nao sei": `engine._where_matches`
    # reprova caminho ausente e a regra simplesmente nao avalia este check.
    facts = _facts(
        "vendas.write.parquet('s3://b/p')\n"
        "vendas = carrega('outra')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert "position_vs_write" not in check.attrs


def test_rebind_entre_check_e_write_omite_a_posicao():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas = carrega('outra')\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert "position_vs_write" not in check.attrs


@pytest.mark.parametrize(
    "rebind",
    [
        "vendas = carrega('outra')",
        "vendas: DataFrame = carrega('outra')",
        "vendas += extras",
        "for vendas in lotes: pass",
        "with abre('x') as vendas: pass",
    ],
)
def test_qualquer_forma_de_religar_o_nome_omite_a_posicao(rebind):
    facts = _facts(
        "vendas.write.parquet('s3://b/p')\n"
        f"{rebind}\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert "position_vs_write" not in check.attrs


def test_ligacao_fora_do_intervalo_nao_omite_a_posicao():
    # O `vendas =` da linha 1 esta antes do check E antes do write: nao ha
    # troca de objeto entre os dois, e a ordem continua apurada.
    facts = _facts(
        "vendas = carrega('vendas')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "before_write"


def test_unpersist_antes_do_check_desfaz_a_persistencia():
    facts = _facts(
        "vendas.cache()\n"
        "vendas.unpersist()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is False


def test_persist_depois_do_unpersist_volta_a_persistir():
    facts = _facts(
        "vendas.cache()\n"
        "vendas.unpersist()\n"
        "vendas.persist()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True


def test_unpersist_depois_do_check_nao_desfaz_a_persistencia():
    facts = _facts(
        "vendas.cache()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.unpersist()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True


def test_religar_o_nome_entre_o_cache_e_o_check_desfaz_a_persistencia():
    # O DataFrame que o check valida nao e o que foi cacheado. Aqui a chave NAO
    # e omitida: `target_persisted: false` e a resposta honesta, e omitir daria
    # ao rebind o poder de calar `SF-DQ-003`.
    facts = _facts(
        "vendas.cache()\n"
        "vendas = carrega('outra')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is False


def test_religacao_antes_do_cache_nao_desfaz_a_persistencia():
    facts = _facts(
        "vendas = carrega('vendas')\n"
        "vendas.cache()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True


def test_religacao_depois_do_check_nao_desfaz_a_persistencia():
    facts = _facts(
        "vendas.cache()\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas = carrega('outra')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True


def test_religacao_antes_da_unica_action_invalida_a_action():
    # A action da linha 3 e sobre outro DataFrame. Dizer `true` aqui faria
    # `SF-DQ-003` acusar um check cujo alvo nunca foi reusado.
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas = carrega('outra')\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["action_after_check"] is False


def test_religacao_depois_da_action_nao_a_invalida():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/p')\n"
        "vendas = carrega('outra')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["action_after_check"] is True


def test_religacao_nao_mata_a_action_que_veio_antes_dela():
    # Sao N actions candidatas, nao uma: a religacao da linha 3 invalida a
    # action da linha 4, e nao a da linha 2. O atributo continua `true`.
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "vendas.write.parquet('s3://b/p')\n"
        "vendas = carrega('outra')\n"
        "vendas.write.parquet('s3://b/q')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["action_after_check"] is True


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


def test_verification_suite_compartilha_varredura():
    facts = _facts(
        "from pydeequ.verification import VerificationSuite\n"
        "r = VerificationSuite(spark).onData(vendas).addCheck(c1).addCheck(c2).run()\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 1
    assert checks[0].attrs["framework"] == "pydeequ"
    assert checks[0].attrs["target"] == "vendas"
    assert checks[0].attrs["shares_scan"] is True
    assert "declared_checks" not in checks[0].measures


@pytest.mark.parametrize(
    "chain",
    [
        # A ordem e o numero de `addCheck` variam, e a API aceita encadeamento
        # livre: o que identifica a suite e conter `onData` e terminar em `run`.
        "VerificationSuite(spark).onData(vendas).run()",
        "VerificationSuite(spark).onData(vendas).addCheck(c1).run()",
        "VerificationSuite(spark).onData(vendas).addCheck(c1).addCheck(c2).addCheck(c3).run()",
        "VerificationSuite(spark).onData(vendas).useRepository(repo).saveOrAppendResult(k).run()",
    ],
)
def test_a_suite_e_reconhecida_pela_forma_e_nao_pela_sequencia(chain):
    facts = _facts(f"r = {chain}\n")
    checks = [f for f in facts if f.kind == "dq.check"]
    assert [c.attrs["check_type"] for c in checks] == ["verification_suite"]
    assert checks[0].attrs["target"] == "vendas"


def test_run_sem_ondata_nao_e_suite():
    facts = _facts("r = job.addCheck(c1).run()\n")
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_ondata_sobre_cadeia_de_leitura_vira_unresolved():
    # O alvo do PyDeequ e o argumento de `onData`, e argumento que nao e um nome
    # nao vira alvo adivinhado.
    facts = _facts("r = VerificationSuite(spark).onData(spark.table('t')).run()\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.unresolved"]
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert unresolved.attrs["reason"] == "unresolved_target"
    assert unresolved.attrs["check_type"] == "verification_suite"
    assert [f for f in facts if f.kind == "dq.module_analyzed"][0].measures["unresolved_count"] == 1


def test_ondata_sem_argumento_vira_unresolved():
    facts = _facts("r = VerificationSuite(spark).onData().run()\n")
    assert [f.attrs["reason"] for f in facts if f.kind == "dq.unresolved"] == ["unresolved_target"]


def test_a_suite_depois_do_write_e_datada_como_o_check_artesanal():
    facts = _facts(
        "vendas.write.parquet('s3://b/p')\n"
        "r = VerificationSuite(spark).onData(vendas).addCheck(c1).run()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "after_write"
    assert check.attrs["target_persisted"] is False
    assert check.attrs["action_after_check"] is False


def test_a_suite_sobre_alvo_cacheado_com_action_depois():
    facts = _facts(
        "vendas.cache()\n"
        "r = VerificationSuite(spark).onData(vendas).run()\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["target_persisted"] is True
    assert check.attrs["action_after_check"] is True


def test_rebind_entre_o_write_e_a_suite_omite_a_posicao():
    facts = _facts(
        "vendas.write.parquet('s3://b/p')\n"
        "vendas = carrega('outra')\n"
        "r = VerificationSuite(spark).onData(vendas).run()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert "position_vs_write" not in check.attrs


def test_suite_de_homonimo_em_outra_funcao_nao_e_datada_pelo_write():
    facts = _facts(
        "def a(vendas):\n"
        "    vendas.write.parquet(1)\n"
        "def b(vendas):\n"
        "    return VerificationSuite(spark).onData(vendas).run()\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "no_write_in_module"


def test_suite_e_check_artesanal_no_mesmo_alvo_se_contam():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "r = VerificationSuite(spark).onData(vendas).run()\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 2
    assert {c.measures["checks_on_target"] for c in checks} == {2}
    assert {c.attrs["framework"] for c in checks} == {"handmade", "pydeequ"}


def test_a_suite_nao_produz_dois_facts_para_a_mesma_chamada():
    facts = _facts("r = VerificationSuite(spark).onData(vendas).addCheck(c1).run()\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.check"]


def test_great_expectations_pela_chave_literal_do_batch_parameters():
    facts = _facts(
        "import great_expectations as gx\n"
        "res = validation_definition.run(batch_parameters={'dataframe': vendas})\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["framework"] == "great_expectations"
    assert check.attrs["target"] == "vendas"
    # Quantas expectativas rodam vive no store do contexto, FORA do .py.
    # Chave ausente e a forma de dizer "nao sei" sem virar `false`.
    assert "shares_scan" not in check.attrs


def test_checkpoint_com_batch_parameters_tambem_e_reconhecido():
    # O receptor varia -- Checkpoint e ValidationDefinition aceitam o mesmo
    # `batch_parameters` --, e a evidencia lida e a mesma.
    facts = _facts("res = checkpoint.run(batch_parameters={'dataframe': vendas})\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["framework"] == "great_expectations"
    assert check.attrs["check_type"] == "batch_parameters_dataframe"


def test_batch_parameters_sem_a_chave_dataframe_nao_e_check():
    facts = _facts("res = validation_definition.run(batch_parameters={'ano': 2026})\n")
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_batch_parameters_que_nao_e_dict_literal_nao_e_check():
    facts = _facts("res = validation_definition.run(batch_parameters=params)\n")
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_dataframe_do_batch_parameters_que_nao_e_variavel_vira_unresolved():
    facts = _facts(
        "res = validation_definition.run(batch_parameters={'dataframe': spark.table('t')})\n"
    )
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.unresolved"]
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert unresolved.attrs["reason"] == "unresolved_target"
    assert unresolved.attrs["check_type"] == "batch_parameters_dataframe"


def test_o_check_de_ge_recebe_os_atributos_de_correlacao():
    facts = _facts(
        "vendas.cache()\n"
        "res = validation_definition.run(batch_parameters={'dataframe': vendas})\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "before_write"
    assert check.attrs["target_persisted"] is True
    assert check.attrs["action_after_check"] is True
    assert check.measures["checks_on_target"] == 1


def test_rebind_entre_a_validacao_de_ge_e_o_write_omite_a_posicao():
    facts = _facts(
        "res = validation_definition.run(batch_parameters={'dataframe': vendas})\n"
        "vendas = carrega('outra')\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert "position_vs_write" not in check.attrs


def test_batch_parameters_por_variavel_e_a_forma_da_documentacao():
    # A forma oficial (§1.2 de knowledge/dq/validation-frameworks.md) monta o
    # dict numa linha e o passa por nome na seguinte. So o dict inline seria
    # reconhecer a forma que a documentacao NAO usa.
    facts = _facts(
        "batch_parameters = {'dataframe': vendas}\n"
        "res = validation_definition.run(batch_parameters=batch_parameters)\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["framework"] == "great_expectations"
    assert check.attrs["target"] == "vendas"
    assert "shares_scan" not in check.attrs


def test_o_nome_seguido_nao_precisa_ser_batch_parameters():
    facts = _facts(
        "params = {'dataframe': vendas}\nres = checkpoint.run(batch_parameters=params)\n"
    )
    assert [f.attrs["target"] for f in facts if f.kind == "dq.check"] == ["vendas"]


def test_dict_atribuido_em_outro_escopo_nao_e_seguido():
    # Nome nu nao identifica objeto entre escopos -- a mesma propriedade que faz
    # o indice ser por escopo.
    facts = _facts(
        "def prepara():\n"
        "    params = {'dataframe': vendas}\n"
        "res = validation_definition.run(batch_parameters=params)\n"
    )
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_religacao_entre_a_atribuicao_do_dict_e_o_run_invalida_a_evidencia():
    facts = _facts(
        "params = {'dataframe': vendas}\n"
        "params = outra_coisa()\n"
        "res = validation_definition.run(batch_parameters=params)\n"
    )
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_variavel_que_nao_vem_de_dict_literal_nao_e_seguida():
    facts = _facts("params = monta()\nres = validation_definition.run(batch_parameters=params)\n")
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_dict_atribuido_depois_do_run_nao_data_o_check():
    facts = _facts(
        "res = validation_definition.run(batch_parameters=params)\n"
        "params = {'dataframe': vendas}\n"
    )
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_o_ultimo_dict_antes_do_run_e_o_que_vale():
    facts = _facts(
        "params = {'dataframe': vendas}\n"
        "params = {'dataframe': clientes}\n"
        "res = validation_definition.run(batch_parameters=params)\n"
    )
    assert [f.attrs["target"] for f in facts if f.kind == "dq.check"] == ["clientes"]


def test_dataframe_nao_variavel_no_dict_seguido_tambem_vira_unresolved():
    facts = _facts(
        "params = {'dataframe': spark.table('t')}\n"
        "res = validation_definition.run(batch_parameters=params)\n"
    )
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert unresolved.attrs["reason"] == "unresolved_target"
    assert unresolved.attrs["check_type"] == "batch_parameters_dataframe"


def test_o_check_seguido_por_variavel_recebe_a_correlacao():
    facts = _facts(
        "params = {'dataframe': vendas}\n"
        "res = validation_definition.run(batch_parameters=params)\n"
        "vendas.write.parquet('s3://b/p')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    assert check.attrs["position_vs_write"] == "before_write"
    assert check.attrs["action_after_check"] is True


def test_suite_sem_run_e_ponto_cego_contado():
    # A cadeia pode ser guardada e executada depois, fora da vista do extrator.
    # Exclusao contada, nunca silenciosa.
    facts = _facts("s = VerificationSuite(spark).onData(vendas).addCheck(c).useRepository(rep)\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.unresolved"]
    unresolved = [f for f in facts if f.kind == "dq.unresolved"][0]
    assert unresolved.attrs["reason"] == "suite_run_not_visible"
    assert unresolved.attrs["check_type"] == "verification_suite"
    assert [f for f in facts if f.kind == "dq.module_analyzed"][0].measures["unresolved_count"] == 1


def test_suite_guardada_em_variavel_e_rodada_depois_conta_uma_vez_so():
    facts = _facts("s = VerificationSuite(spark).onData(vendas)\ns.run()\n")
    assert [f.attrs["reason"] for f in facts if f.kind == "dq.unresolved"] == [
        "suite_run_not_visible"
    ]
    assert [f for f in facts if f.kind == "dq.check"] == []


def test_suite_com_run_continua_check_e_nao_ponto_cego():
    facts = _facts("r = VerificationSuite(spark).onData(vendas).addCheck(c).run()\n")
    assert [f.kind for f in facts if f.kind != "dq.module_analyzed"] == ["dq.check"]


def test_metodo_encadeado_depois_do_run_nao_esconde_a_execucao():
    facts = _facts("VerificationSuite(spark).onData(vendas).run().printResults()\n")
    checks = [f for f in facts if f.kind == "dq.check"]
    assert [c.attrs["target"] for c in checks] == ["vendas"]
    assert [f for f in facts if f.kind == "dq.unresolved"] == []


def test_cadeia_sem_ondata_nao_vira_ponto_cego():
    facts = _facts("s = job.addCheck(c).useRepository(rep)\n")
    assert [f.kind for f in facts] == ["dq.module_analyzed"]


def test_nenhum_framework_declara_single_pass_nem_declared_checks():
    # `single_pass` afirmaria "N checks, uma passada", que a fonte primaria nega
    # (VLDB 2018, §4.1 e §5.1); `declared_checks` contaria objetos `Check` e nao
    # restricoes. Os dois nomes estao vetados nesta area.
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count()\n"
        "r = VerificationSuite(spark).onData(vendas).addCheck(c1).addCheck(c2).run()\n"
        "res = validation_definition.run(batch_parameters={'dataframe': vendas})\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len(checks) == 3
    for check in checks:
        assert "single_pass" not in check.attrs
        assert "declared_checks" not in check.measures


def test_check_com_raise_produz_enforcement_no_mesmo_subject():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('valor negativo')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    # Igualdade, e nao semelhanca: `_subject_group_key` canoniza o subject
    # inteiro, e e essa igualdade que poe check e enforcement no mesmo grupo de
    # `same_subject` para o `absent` de SF-DQ-002.
    assert enforcement.subject == check.subject
    assert enforcement.subject["line"] == 1
    assert enforcement.subject["symbol"] == ""
    assert enforcement.attrs["form"] == "raise"


def test_o_enforcement_mede_a_linha_da_propria_consequencia():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('valor negativo')\n"
    )
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.measures["line"] == 3


def test_resultado_lido_sem_aborto_nao_e_enforcement():
    # Protecao pela metade: o resultado e lido, e nada acontece com ele.
    facts = _facts("ruins = vendas.filter(vendas.valor < 0).count()\nprint(ruins)\n")
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_if_sobre_o_resultado_sem_aborto_no_corpo_nao_e_enforcement():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    logger.warning('tem ruim')\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_resultado_nunca_lido_nao_e_enforcement():
    facts = _facts("vendas.filter(vendas.valor < 0).count()\n")
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_aborto_sem_ler_o_resultado_nao_e_enforcement():
    # O `raise` existe, mas o teste do `if` nao toca no resultado do check: a
    # consequencia nao e consequencia DESTE check.
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if len(argv) < 2:\n"
        "    raise ValueError('faltou argumento')\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


@pytest.mark.parametrize(
    ("aborto", "forma"),
    [
        ("raise ValueError('x')", "raise"),
        ("sys.exit(1)", "exit"),
        ("os._exit(1)", "exit"),
        ("exit(1)", "exit"),
        ("assert False", "assert"),
    ],
)
def test_as_formas_de_aborto_reconhecidas(aborto, forma):
    facts = _facts(
        f"ruins = vendas.filter(vendas.valor < 0).count()\nif ruins > 0:\n    {aborto}\n"
    )
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.attrs["form"] == forma
    assert enforcement.measures["line"] == 3


def test_assert_sobre_o_resultado_conta_como_enforcement():
    # Desvio D-5c-4: `-O` apaga o `assert`, mas nenhuma fonte da AWS mostra Glue
    # ou EMR rodando o driver assim. `assert` conta, e NAO vira ponto cego --
    # knowledge/dq/validation-frameworks.md §3.4, veto V-AS-1.
    facts = _facts("ruins = vendas.filter(vendas.valor < 0).count()\nassert ruins == 0\n")
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.attrs["form"] == "assert"
    assert enforcement.measures["line"] == 2
    assert not [f for f in facts if f.kind == "dq.unresolved"]


def test_o_check_dentro_do_proprio_if_dispensa_a_variavel():
    facts = _facts("if vendas.filter(vendas.valor < 0).count() > 0:\n    raise ValueError('x')\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.subject == check.subject
    assert enforcement.measures["line"] == 2


def test_o_check_dentro_do_proprio_assert_dispensa_a_variavel():
    facts = _facts("assert vendas.filter(vendas.valor < 0).count() == 0\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.subject == check.subject
    assert enforcement.attrs["form"] == "assert"
    assert enforcement.measures["line"] == 1


def test_aborto_no_else_tambem_e_consequencia():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins == 0:\n"
        "    print('ok')\n"
        "else:\n"
        "    raise ValueError('x')\n"
    )
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.attrs["form"] == "raise"
    assert enforcement.measures["line"] == 5


def test_religacao_entre_o_check_e_a_leitura_derruba_a_evidencia():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "ruins = 0\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_religacao_depois_da_leitura_nao_derruba_a_evidencia():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
        "ruins = 0\n"
    )
    assert [f.attrs["form"] for f in facts if f.kind == "dq.enforcement"] == ["raise"]


def test_leitura_anterior_ao_check_nao_e_consequencia():
    facts = _facts(
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_consequencia_em_outro_escopo_nao_conta():
    facts = _facts(
        "def valida(vendas):\n"
        "    ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
    )
    assert [f for f in facts if f.kind == "dq.check"]
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_consequencia_dentro_da_mesma_funcao_conta():
    facts = _facts(
        "def valida(vendas):\n"
        "    ruins = vendas.filter(vendas.valor < 0).count()\n"
        "    if ruins > 0:\n"
        "        raise ValueError('x')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.subject == check.subject
    assert enforcement.measures["line"] == 4


@pytest.mark.parametrize(
    ("check_source", "leitura"),
    [
        (
            "r = VerificationSuite(spark).onData(vendas).addCheck(c).run()",
            "if r.status != 'Success':",
        ),
        (
            "r = validation_definition.run(batch_parameters={'dataframe': vendas})",
            "if not r.success:",
        ),
        ("r = vendas.filter(vendas.valor < 0).count()", "if r > 0:"),
    ],
)
def test_os_tres_frameworks_saem_pelo_mesmo_caminho(check_source, leitura):
    facts = _facts(f"{check_source}\n{leitura}\n    raise ValueError('x')\n")
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.subject == check.subject
    assert enforcement.attrs["form"] == "raise"
    assert enforcement.measures["line"] == 3


def test_dois_consumidores_produzem_dois_enforcements():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
        "assert ruins == 0\n"
    )
    enforcements = [f for f in facts if f.kind == "dq.enforcement"]
    assert sorted((f.attrs["form"], f.measures["line"]) for f in enforcements) == [
        ("assert", 4),
        ("raise", 3),
    ]


def test_alvo_nao_resolvido_nao_ganha_enforcement():
    # Sem `dq.check` nao ha subject a proteger: o enforcement seria um fact sem
    # o par que ele existe para acompanhar.
    facts = _facts(
        "ruins = spark.table('t').filter('x is null').count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


def test_o_enforcement_nao_entra_nas_contagens_da_sentinela():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
    )
    sentinela = [f for f in facts if f.kind == "dq.module_analyzed"][0]
    assert sentinela.measures["check_count"] == 1
    assert sentinela.measures["unresolved_count"] == 0


def test_cada_check_recebe_a_consequencia_que_le_o_seu_resultado():
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count()\n"
        "b = clientes.filter(clientes.cpf.isNull()).count()\n"
        "if b > 0:\n"
        "    raise ValueError('x')\n"
    )
    checks = {f.subject["line"]: f for f in facts if f.kind == "dq.check"}
    enforcements = [f for f in facts if f.kind == "dq.enforcement"]
    assert [f.subject for f in enforcements] == [checks[2].subject]


def test_dois_checks_na_mesma_linha_tem_ids_distintos():
    # `Fact.id` e sha de kind+subject+measures, e `attrs` fica de fora
    # (`models.py`): com `col` fixo em zero, dois checks na mesma linha viravam
    # uma identidade so, e o `fact_id` que um Finding cita deixava de
    # identificar evidencia.
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count(); "
        "b = clientes.filter(clientes.cpf.isNull()).count()\n"
        "if a > 0 or b > 0:\n"
        "    raise ValueError('x')\n"
    )
    checks = [f for f in facts if f.kind == "dq.check"]
    assert len({c.id for c in checks}) == len(checks) == 2
    # A coluna e a do inicio da cadeia do check, nao a do nome que a recebe.
    assert sorted(c.subject["col"] for c in checks) == [4, 49]


def test_dois_enforcements_na_mesma_linha_tem_ids_distintos():
    facts = _facts(
        "a = vendas.filter(vendas.valor < 0).count(); "
        "b = clientes.filter(clientes.cpf.isNull()).count()\n"
        "if a > 0 or b > 0:\n"
        "    raise ValueError('x')\n"
    )
    enforcements = [f for f in facts if f.kind == "dq.enforcement"]
    assert len({f.id for f in enforcements}) == len(enforcements) == 2


def test_dois_unresolved_na_mesma_linha_tem_ids_distintos():
    facts = _facts(
        "a = spark.table('t').filter('x').count(); b = spark.table('u').filter('y').count()\n"
    )
    unresolved = [f for f in facts if f.kind == "dq.unresolved"]
    assert len({f.id for f in unresolved}) == len(unresolved) == 2


def test_a_coluna_nao_muda_o_grupo_de_same_subject():
    # `_subject_group_key` usa `file:line` quando nao ha `symbol`, entao `col`
    # distingue identidade de fact SEM mexer no agrupamento que o `absent` de
    # SF-DQ-002 usa. Se isto quebrar, a regra passa a disparar sobre check
    # protegido.
    from sparkforge.rules.engine import _subject_group_key

    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "if ruins > 0:\n"
        "    raise ValueError('x')\n"
    )
    check = [f for f in facts if f.kind == "dq.check"][0]
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert _subject_group_key(enforcement) == _subject_group_key(check)


def test_alvo_de_tupla_ainda_liga_o_nome():
    facts = _facts(
        "ruins, limite = vendas.filter(vendas.valor < 0).count(), 10\n"
        "if ruins > limite:\n"
        "    raise ValueError('x')\n"
    )
    assert [f.attrs["form"] for f in facts if f.kind == "dq.enforcement"] == ["raise"]


def test_while_le_o_resultado_e_aborta():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "while ruins > 0:\n"
        "    raise ValueError('x')\n"
    )
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.attrs["form"] == "raise"
    assert enforcement.measures["line"] == 3


def test_match_le_o_resultado_e_aborta():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "match ruins:\n"
        "    case 0:\n"
        "        print('ok')\n"
        "    case _:\n"
        "        raise ValueError('x')\n"
    )
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.attrs["form"] == "raise"
    assert enforcement.measures["line"] == 6


def test_guarda_de_match_tambem_e_leitura():
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\n"
        "match estado:\n"
        "    case 'pronto' if ruins > 0:\n"
        "        raise ValueError('x')\n"
    )
    assert [f.attrs["form"] for f in facts if f.kind == "dq.enforcement"] == ["raise"]


@pytest.mark.parametrize(
    "expressao",
    [
        "ruins > 0 and sys.exit(1)",
        "sys.exit(1) if ruins > 0 else None",
    ],
)
def test_curto_circuito_e_ifexp_contam(expressao):
    facts = _facts(f"ruins = vendas.filter(vendas.valor < 0).count()\n{expressao}\n")
    enforcement = [f for f in facts if f.kind == "dq.enforcement"][0]
    assert enforcement.attrs["form"] == "exit"
    assert enforcement.measures["line"] == 2


def test_expressao_que_le_sem_abortar_continua_sem_enforcement():
    # A mesma porta que reconhece `ruins > 0 and sys.exit(1)` nao pode
    # reconhecer `print(ruins)`: protecao pela metade continua nao emitindo.
    facts = _facts(
        "ruins = vendas.filter(vendas.valor < 0).count()\nruins > 0 and logger.warning(1)\n"
    )
    assert not [f for f in facts if f.kind == "dq.enforcement"]


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
