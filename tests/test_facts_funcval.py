"""Fase 4c: `funcval plan` (Task 2) e `funcval compare` (Task 3).

Os tres primeiros testes sao os literais do plano. O resto prova o que a Task 2
mediu e decidiu: um plano POR ALVO, casamento de alvo por string identica,
`origin` em todo check, e o eixo ausente escrito em vez de calado.

A partir de `TestAComparacaoVemDoPlano` comeca a Task 3: o modo de comparacao vem
do plano, o limiar vem do catalogo, os tres estados de cobertura ficam distintos,
e a sentinela declara o limite dos proxies na SAIDA.
"""
from sparkforge.facts.funcval import (
    EMITTED_KINDS,
    EXTRACTOR_ID,
    build_comparison,
    build_plan,
)
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact


def _write(target: str) -> Fact:
    return Fact(
        kind="pyspark.write",
        subject={"type": "source_location", "file": "job.py", "line": 10,
                 "col": 0, "symbol": "", "snippet": ""},
        attrs={"mode": "overwrite", "target": target},
        provenance={"artifact": "job.py", "extractor": "pyspark_ast@0.1.0"},
    )


def test_o_plano_deriva_o_alvo_do_write():
    facts = build_plan([_write("db.vendas")])
    plano = [f for f in facts if f.kind == "funcval.plan"][0]
    assert plano.attrs["target"] == "db.vendas"
    assert "count" in plano.attrs["checks"]


def test_cada_check_cita_o_fact_de_origem():
    """Plano sem procedencia seria julgamento vestido de derivacao."""
    facts = build_plan([_write("db.vendas")])
    plano = [f for f in facts if f.kind == "funcval.plan"][0]
    assert plano.attrs["derived_from"]


def test_sem_write_nao_ha_alvo_e_o_plano_nao_e_inventado():
    facts = build_plan([])
    assert [f.kind for f in facts if f.kind == "funcval.plan"] == []
    assert [f.kind for f in facts if f.kind == "funcval.unresolved"] == ["funcval.unresolved"]


# --------------------------------------------------------------------------
# Helpers de fixture sintetica, na forma MEDIDA dos facts reais.
# --------------------------------------------------------------------------


def _write_at(target: str | None, line: int, col: int = 4, mode: str = "overwrite") -> Fact:
    """Um `pyspark.write` na forma medida: `target` mora em `attrs`, o subject e
    `source_location`, e `mode` PODE FALTAR (`insertInto`)."""
    attrs: dict = {}
    if mode:
        attrs["mode"] = mode
    if target is not None:
        attrs["target"] = target
    return Fact(
        kind="pyspark.write",
        subject={"type": "source_location", "file": "job.py", "line": line,
                 "col": col, "symbol": "executar", "snippet": ""},
        attrs=attrs,
        provenance={"artifact": "job.py", "artifact_sha256": "", "extractor": "pyspark_ast@0.1.0"},
    )


def _schema(symbol: str, column_types: dict[str, str], partition_keys=()) -> Fact:
    """Forma medida em `fixtures/catalog/glue_table_schema/expected/facts.json`."""
    measures: dict = {"column_count": len(column_types)}
    if partition_keys:
        measures["partition_key_count"] = len(partition_keys)
    return Fact(
        kind="catalog.table_schema",
        subject={"type": "table", "file": "dump.json", "symbol": symbol},
        measures=measures,
        attrs={
            "table": symbol,
            "storage_format": "parquet",
            "columnar": True,
            "partition_keys": list(partition_keys),
            "column_types": dict(column_types),
        },
        provenance={"artifact": "dump.json", "artifact_sha256": "",
                    "extractor": "catalog_schema@0.1.0"},
    )


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _plan_for(facts, target):
    return [f for f in _by_kind(facts, "funcval.plan") if f.attrs["target"] == target][0]


def _reasons(facts):
    return sorted(f.attrs["reason"] for f in _by_kind(facts, "funcval.unresolved"))


# --------------------------------------------------------------------------
# A decisao que a Task 2 mediu: quantos planos para varios alvos.
# --------------------------------------------------------------------------


class TestUmPlanoPorAlvo:
    def test_alvos_diferentes_produzem_planos_diferentes(self):
        """Medido: `pyspark_ast` sobre um arquivo com cinco writes emite CINCO
        facts e QUATRO alvos distintos. As chaves de `checks` (`count`,
        `schema`) nao tem namespace de alvo -- dois alvos num plano so colidiriam
        nelas -- e o contrato do resultado fixa `target` como string SINGULAR."""
        facts = build_plan([_write_at("db.vendas", 2), _write_at("db.clientes", 3)])
        planos = _by_kind(facts, "funcval.plan")
        assert len(planos) == 2
        assert sorted(p.attrs["target"] for p in planos) == ["db.clientes", "db.vendas"]

    def test_dois_planos_tem_ids_diferentes(self):
        facts = build_plan([_write_at("db.vendas", 2), _write_at("db.clientes", 3)])
        planos = _by_kind(facts, "funcval.plan")
        assert len({p.id for p in planos}) == 2

    def test_o_mesmo_alvo_escrito_duas_vezes_e_um_plano_com_as_duas_origens(self):
        """Medido: `db.vendas` sai duas vezes do mesmo arquivo
        (`saveAsTable` e `insertInto`). A chave e o ALVO, nao o fact."""
        a = _write_at("db.vendas", 2)
        b = _write_at("db.vendas", 4, mode="")
        facts = build_plan([a, b])
        planos = _by_kind(facts, "funcval.plan")
        assert len(planos) == 1
        assert planos[0].attrs["checks"]["count"]["derived_from"] == sorted({a.id, b.id})


class TestCasamentoDeAlvoPorStringIdentica:
    def test_o_schema_do_alvo_casado_entra_no_plano(self):
        facts = build_plan([
            _write_at("db.vendas", 2),
            _schema("db.vendas", {"cliente_id": "bigint", "valor": "double", "dt": "string"}),
        ])
        plano = _plan_for(facts, "db.vendas")
        assert plano.attrs["checks"]["schema"]["origin"] == "derived"
        assert _by_kind(facts, "funcval.unresolved") == []

    def test_nome_de_tres_partes_nao_casa_com_simbolo_de_duas(self):
        """`cat.db.tbl` contra `db.tbl` NAO casa: vira `funcval.unresolved`,
        nunca alvo adivinhado por sufixo."""
        facts = build_plan([_write_at("cat.db.tbl", 2), _schema("db.tbl", {"a": "bigint"})])
        plano = _plan_for(facts, "cat.db.tbl")
        assert "schema" not in plano.attrs["checks"]
        assert "catalog_schema_unmatched" in _reasons(facts)

    def test_o_quase_casamento_fica_nomeado_sem_virar_casamento(self):
        facts = build_plan([_write_at("cat.db.tbl", 2), _schema("db.tbl", {"a": "bigint"})])
        nao_casou = [f for f in _by_kind(facts, "funcval.unresolved")
                     if f.attrs["reason"] == "catalog_schema_unmatched"][0]
        assert nao_casou.attrs["near_symbols"] == ["db.tbl"]

    def test_alvo_que_e_caminho_s3_nao_casa_com_catalogo_e_mantem_a_contagem(self):
        facts = build_plan([
            _write_at("s3://lake/curated/vendas/", 2),
            _schema("db.vendas", {"valor": "double"}),
        ])
        plano = _plan_for(facts, "s3://lake/curated/vendas/")
        assert list(plano.attrs["checks"]) == ["count"]
        assert plano.attrs["undeclared_axes"] == ["aggregates", "keys", "schema"]

    def test_dois_schemas_para_o_mesmo_simbolo_nao_escolhem_um(self):
        """Escolher entre dois dumps que discordam seria chute com cara de
        derivacao."""
        facts = build_plan([
            _write_at("db.vendas", 2),
            _schema("db.vendas", {"valor": "double"}),
            _schema("db.vendas", {"valor": "double", "extra": "bigint"}),
        ])
        plano = _plan_for(facts, "db.vendas")
        assert "schema" not in plano.attrs["checks"]
        assert "catalog_schema_ambiguous" in _reasons(facts)


class TestAgregadosSaemDoTipoDeclarado:
    def _facts(self):
        return build_plan([
            _write_at("db.vendas", 2),
            _schema("db.vendas", {
                "cliente_id": "bigint",
                "valor": "double",
                "preco": "decimal(18,2)",
                "dt": "string",
            }),
        ])

    def test_so_coluna_numerica_vira_agregado(self):
        plano = _plan_for(self._facts(), "db.vendas")
        aggs = sorted(k for k in plano.attrs["checks"] if k.startswith("agg:"))
        assert aggs == ["agg:sum:cliente_id", "agg:sum:preco", "agg:sum:valor"]

    def test_o_tipo_vai_verbatim_porque_e_ele_que_escolhe_exata_contra_tolerante(self):
        """`catalog_schema.py` copia o tipo SEM normalizar -- `decimal(18,2)`
        sobrevive -- e a Task 3 le esse tipo para decidir o modo."""
        plano = _plan_for(self._facts(), "db.vendas")
        checks = plano.attrs["checks"]
        assert checks["agg:sum:preco"]["type"] == "decimal(18,2)"
        assert checks["agg:sum:valor"]["type"] == "double"
        assert checks["agg:sum:cliente_id"]["type"] == "bigint"

    def test_schema_sem_coluna_numerica_declara_o_eixo_vazio(self):
        facts = build_plan([_write_at("db.legado", 2), _schema("db.legado", {"id": "string"})])
        plano = _plan_for(facts, "db.legado")
        assert "aggregates" in plano.attrs["undeclared_axes"]
        assert plano.attrs["undeclared_axes_reason"]["aggregates"]
        assert "schema" in plano.attrs["checks"]

    def test_tipo_que_o_modulo_nao_classifica_vira_unresolved_e_nao_silencio(self):
        facts = build_plan([
            _write_at("db.vendas", 2),
            _schema("db.vendas", {"valor": "double", "esquisito": "hll_sketch"}),
        ])
        plano = _plan_for(facts, "db.vendas")
        assert "agg:sum:esquisito" not in plano.attrs["checks"]
        assert "column_type_unclassified" in _reasons(facts)


class TestProcedenciaEmTodoCheck:
    def test_todo_check_derivado_carrega_origin(self):
        """Se `origin` aparecesse so no declarado, seria excecao -- e excecao nao
        e procedencia."""
        facts = build_plan(
            [_write_at("db.vendas", 2), _schema("db.vendas", {"valor": "double"})],
            keys=["pedido_id"],
        )
        checks = _plan_for(facts, "db.vendas").attrs["checks"]
        assert len(checks) == 4
        for name, check in checks.items():
            assert check["origin"] in {"derived", "declared"}, name
            assert "type" in check, name
            assert isinstance(check["derived_from"], list), name

    def test_derivado_cita_fact_id_e_declarado_cita_lista_vazia(self):
        schema = _schema("db.vendas", {"valor": "double"})
        facts = build_plan([_write_at("db.vendas", 2), schema], keys=["pedido_id"])
        checks = _plan_for(facts, "db.vendas").attrs["checks"]
        assert checks["schema"] == {"origin": "derived", "type": "schema",
                                    "derived_from": [schema.id]}
        assert checks["key:pedido_id"] == {"origin": "declared", "type": "bigint",
                                           "derived_from": []}

    def test_o_derived_from_do_plano_e_a_uniao_dos_derivados(self):
        write = _write_at("db.vendas", 2)
        schema = _schema("db.vendas", {"valor": "double"})
        facts = build_plan([write, schema], keys=["pedido_id"])
        plano = _plan_for(facts, "db.vendas")
        assert plano.attrs["derived_from"] == sorted({write.id, schema.id})

    def test_o_plano_conta_derivados_e_declarados_separadamente(self):
        facts = build_plan(
            [_write_at("db.vendas", 2), _schema("db.vendas", {"valor": "double"})],
            keys=["pedido_id", "loja_id"],
        )
        plano = _plan_for(facts, "db.vendas")
        assert plano.measures["derived_check_count"] == 3
        assert plano.measures["declared_check_count"] == 2
        assert plano.measures["check_count"] == 5


class TestOEixoDeChaves:
    def test_sem_key_o_eixo_fica_escrito_e_nao_calado(self):
        facts = build_plan([_write_at("db.vendas", 2), _schema("db.vendas", {"valor": "double"})])
        plano = _plan_for(facts, "db.vendas")
        assert plano.attrs["undeclared_axes"] == ["keys"]
        assert plano.attrs["undeclared_axes_reason"]["keys"]
        assert not [k for k in plano.attrs["checks"] if k.startswith("key:")]

    def test_com_key_o_eixo_sai_da_lista_de_ausentes(self):
        facts = build_plan(
            [_write_at("db.vendas", 2), _schema("db.vendas", {"valor": "double"})],
            keys=["pedido_id"],
        )
        plano = _plan_for(facts, "db.vendas")
        assert plano.attrs["undeclared_axes"] == []
        assert "keys" not in plano.attrs["undeclared_axes_reason"]

    def test_chave_composta_vira_uma_chave_so(self):
        facts = build_plan([_write_at("db.vendas", 2)], keys=["loja_id,pedido_id"])
        checks = _plan_for(facts, "db.vendas").attrs["checks"]
        assert "key:loja_id+pedido_id" in checks

    def test_a_chave_declarada_vale_para_todos_os_alvos_do_corpus(self):
        facts = build_plan([_write_at("db.a", 2), _write_at("db.b", 3)], keys=["pedido_id"])
        for target in ("db.a", "db.b"):
            assert "key:pedido_id" in _plan_for(facts, target).attrs["checks"]

    def test_key_vazia_nao_vira_check_fantasma(self):
        facts = build_plan([_write_at("db.vendas", 2)], keys=["", " , "])
        assert not [k for k in _plan_for(facts, "db.vendas").attrs["checks"] if k.startswith("key")]
        assert "empty_key_declaration" in _reasons(facts)

    def test_a_chave_declarada_nao_e_conferida_contra_o_catalogo(self):
        """D-4c-3: o plano usa o catalogo para saber QUAIS colunas existem, e
        nunca para julgar o que o operador declarou. Isso seria asserção absoluta
        sobre o dado -- `SF-DQ`, nao `SF-FVAL`."""
        facts = build_plan(
            [_write_at("db.vendas", 2), _schema("db.vendas", {"valor": "double"})],
            keys=["coluna_que_nao_existe"],
        )
        plano = _plan_for(facts, "db.vendas")
        assert "key:coluna_que_nao_existe" in plano.attrs["checks"]
        assert _by_kind(facts, "funcval.unresolved") == []


class TestOQueOPlanoNaoAfirma:
    def test_o_check_de_schema_nao_carrega_o_schema_declarado(self):
        """D-4c-3 de novo: se o plano levasse o mapa coluna->tipo do catalogo, a
        Task 3 teria como comparar o observado contra o DECLARADO -- asserção
        absoluta, fora do escopo da fase. O valor vem sempre do resultado."""
        schema = _schema("db.vendas", {"valor": "double", "dt": "string"})
        facts = build_plan([_write_at("db.vendas", 2), schema])
        check = _plan_for(facts, "db.vendas").attrs["checks"]["schema"]
        assert set(check) == {"origin", "type", "derived_from"}

    def test_particao_nao_vira_chave(self):
        """B rejeitado com numero: `distinct_values == partition_count` para a
        tabela inteira acusaria dado correto."""
        facts = build_plan([
            _write_at("db.eventos", 2),
            _schema("db.eventos", {"cliente_id": "bigint", "dt": "string"}, partition_keys=["dt"]),
        ])
        checks = _plan_for(facts, "db.eventos").attrs["checks"]
        assert not [k for k in checks if k.startswith("key:")]


class TestOQueNaoDaParaLer:
    def test_write_sem_alvo_e_nomeado_em_vez_de_ignorado(self):
        """Medido: `fixtures/pyspark/action_in_loop` emite `pyspark.write` com
        `attrs` VAZIO -- nem `mode` nem `target`."""
        facts = build_plan([_write_at(None, 3, mode="")])
        assert _by_kind(facts, "funcval.plan") == []
        assert _reasons(facts) == ["no_write_target", "write_without_target"]

    def test_dois_writes_mudos_nao_colidem_no_fact_id(self):
        """`Fact.id` ignora `attrs` (D-4a-2): sem o local no subject, os dois
        unresolved teriam o mesmo id e um sumiria da saida."""
        facts = build_plan([_write_at(None, 3, mode=""), _write_at(None, 9, mode="")])
        mudos = [f for f in _by_kind(facts, "funcval.unresolved")
                 if f.attrs["reason"] == "write_without_target"]
        assert len(mudos) == 2
        assert len({f.id for f in mudos}) == 2

    def test_unresolved_de_alvos_diferentes_pelo_mesmo_motivo_nao_colidem(self):
        facts = build_plan([_write_at("db.a", 2), _write_at("db.b", 3)])
        nao_casaram = [f for f in _by_kind(facts, "funcval.unresolved")
                       if f.attrs["reason"] == "catalog_schema_unmatched"]
        assert len(nao_casaram) == 2
        assert len({f.id for f in nao_casaram}) == 2

    def test_alvo_nao_string_nao_vira_alvo(self):
        fact = Fact(
            kind="pyspark.write",
            subject={"type": "source_location", "file": "job.py", "line": 1, "col": 0},
            attrs={"target": 7},
            provenance={"artifact": "job.py", "extractor": "pyspark_ast@0.1.0"},
        )
        facts = build_plan([fact])
        assert _by_kind(facts, "funcval.plan") == []
        assert "write_without_target" in _reasons(facts)

    def test_write_mudo_junto_com_write_util_nao_apaga_o_plano(self):
        facts = build_plan([_write_at(None, 3, mode=""), _write_at("db.vendas", 5)])
        assert len(_by_kind(facts, "funcval.plan")) == 1
        assert _reasons(facts) == ["catalog_schema_unmatched", "write_without_target"]


class TestOModuloSegueOPadraoDosDerivados:
    def test_o_namespace_declarado_tem_os_quatro_kinds(self):
        assert EMITTED_KINDS == {
            "funcval.plan",
            "funcval.check_delta",
            "funcval.analyzed",
            "funcval.unresolved",
        }

    def test_o_id_do_deriver_segue_a_convencao_do_repositorio(self):
        assert EXTRACTOR_ID == "funcval@0.1.0"

    def test_todo_fact_emitido_esta_no_namespace(self):
        facts = build_plan(
            [_write_at("db.vendas", 2), _write_at(None, 3, mode=""),
             _schema("db.vendas", {"valor": "double", "x": "hll_sketch"})],
            keys=["pedido_id"],
        )
        assert {f.kind for f in facts} <= EMITTED_KINDS

    def test_a_saida_e_ordenada_deterministicamente(self):
        entrada = [_write_at("db.b", 3), _write_at("db.a", 2)]
        facts = build_plan(entrada)
        assert facts == sort_facts(facts)
        assert [f.id for f in build_plan(list(reversed(entrada)))] == [f.id for f in facts]

    def test_todo_fact_emitido_passa_no_schema(self):
        facts = build_plan(
            [_write_at("db.vendas", 2), _write_at(None, 3, mode=""),
             _schema("db.vendas", {"valor": "double"})],
            keys=["pedido_id"],
        )
        for fact in facts:
            validate_fact(fact.to_dict())

    def test_a_procedencia_nomeia_o_deriver_e_o_path_hint(self):
        facts = build_plan([_write_at("db.vendas", 2)], path_hint="facts.json")
        plano = _plan_for(facts, "db.vendas")
        assert plano.provenance == {
            "artifact": "facts.json",
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
        }

    def test_o_modulo_nao_importa_pyspark_nem_boto(self):
        """Criterio 1 da §9: funcao pura sobre Facts."""
        import sparkforge.facts.funcval as modulo
        fonte = open(modulo.__file__, encoding="utf-8").read()
        for proibido in ("import pyspark", "import boto3", "open(", "subprocess"):
            assert proibido not in fonte, proibido


# ==========================================================================
# Task 3: `funcval compare`.
#
# Os seis primeiros sao os literais do plano, com UM desvio nomeado no proprio
# teste (D-4c-10): o limiar da comparacao relativa mora no catalogo, entao o fact
# carrega `relative_delta` e nao um `diverged` que so um limiar decidiria.
# ==========================================================================


def _plano(**checks):
    return {"target": "t", "checks": checks}


def _resultado(**checks):
    return {"target": "t", "checks": checks}


def _derivado(type_: str, *fact_ids: str) -> dict:
    return {"origin": "derived", "type": type_, "derived_from": list(fact_ids)}


def _delta(facts):
    return [f for f in facts if f.kind == "funcval.check_delta"]


def _sentinela(facts):
    return [f for f in facts if f.kind == "funcval.analyzed"][0]


def test_contagem_divergente_vira_check_delta():
    facts = build_comparison(
        _plano(count=_derivado("bigint", "f_1")),
        _resultado(count={"value": 1000}),
        _resultado(count={"value": 998}),
    )
    delta = _delta(facts)[0]
    assert delta.attrs["check"] == "count"
    assert delta.attrs["diverged"] is True


def test_float_dentro_da_tolerancia_nao_diverge():
    """Soma de float depende da ordem de reducao: um repartition legitimo muda o
    total nos ultimos bits. Comparacao exata daria falso positivo justamente na
    mudanca que a fase existe para aprovar.

    D-4c-10: o modulo declara a comparacao RELATIVA e entrega o delta relativo;
    quem aplica o limiar e `SF-FVAL-004`, porque o numero e heuristica de campo e
    heuristica de campo mora no catalogo -- e um Fact nunca contem limiar.
    """
    plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
    facts = build_comparison(
        plano,
        _resultado(**{"agg:sum:valor": {"value": 1_000_000.0}}),
        _resultado(**{"agg:sum:valor": {"value": 1_000_000.000001}}),
    )
    delta = _delta(facts)[0]
    assert delta.attrs["comparison"] == "relative"
    assert "diverged" not in delta.attrs
    assert delta.measures["relative_delta"] < 1e-9


def test_inteiro_e_comparado_exato():
    facts = build_comparison(
        _plano(count=_derivado("bigint", "f_1")),
        _resultado(count={"value": 1000}),
        _resultado(count={"value": 1001}),
    )
    assert _delta(facts)[0].attrs["diverged"] is True


def test_o_tipo_vem_do_plano_e_nao_do_resultado():
    """Se o resultado escolhesse o modo, o operador decidiria se o proprio numero
    e comparado exato ou com tolerancia. Contrato minimo, regra 5."""
    plano = _plano(**{"agg:sum:n": _derivado("bigint", "f_3")})
    facts = build_comparison(
        plano,
        _resultado(**{"agg:sum:n": {"value": 1_000_000, "type": "double"}}),
        _resultado(**{"agg:sum:n": {"value": 1_000_001, "type": "double"}}),
    )
    assert _delta(facts)[0].attrs["diverged"] is True


def test_check_do_plano_ausente_no_resultado_e_contado():
    """Validacao parcial lida como aprovacao e o encontro de 'nenhum problema'
    com 'nao coletei'. SF-FVAL-005 le esta contagem."""
    plano = _plano(
        count=_derivado("bigint", "f_1"),
        schema=_derivado("schema", "f_4"),
    )
    facts = build_comparison(
        plano, _resultado(count={"value": 1}), _resultado(count={"value": 1})
    )
    sentinela = _sentinela(facts)
    assert sentinela.measures["planned_check_count"] == 2
    assert sentinela.measures["reported_check_count"] == 1


def test_valor_nulo_com_razao_nao_e_zero_nem_ausencia():
    """O terceiro estado do contrato: 'rodei e nao consegui'. Vira unresolved e
    NAO conta como reportado."""
    plano = _plano(count=_derivado("bigint", "f_1"))
    facts = build_comparison(
        plano,
        _resultado(count={"value": None, "unavailable_reason": "tabela indisponivel"}),
        _resultado(count={"value": 10}),
    )
    assert _delta(facts) == []
    assert _by_kind(facts, "funcval.unresolved")
    assert _sentinela(facts).measures["reported_check_count"] == 0


class TestOModoVemDoPlano:
    def test_double_no_plano_e_relativo_mesmo_com_bigint_no_resultado(self):
        """A porta pela qual o operador escolheria o rigor do proprio numero fica
        fechada nos DOIS sentidos, nao so no de apertar."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 10.0, "type": "bigint"}}),
            _resultado(**{"agg:sum:valor": {"value": 10.5, "type": "bigint"}}),
        )
        delta = _delta(facts)[0]
        assert delta.attrs["comparison"] == "relative"
        assert "diverged" not in delta.attrs

    def test_decimal_e_exato_porque_decimal_e_aritmetica_exata(self):
        """Tolerancia em decimal esconderia diferenca de centavo."""
        plano = _plano(**{"agg:sum:preco": _derivado("decimal(18,2)", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:preco": {"value": 1000.00}}),
            _resultado(**{"agg:sum:preco": {"value": 1000.01}}),
        )
        assert _delta(facts)[0].attrs["diverged"] is True

    def test_chave_e_exata_e_carrega_os_dois_valores(self):
        """SF-FVAL-003 le antes == 0 e depois > 0 das measures."""
        plano = _plano(**{"key:pedido_id": {"origin": "declared", "type": "bigint",
                                            "derived_from": []}})
        facts = build_comparison(
            plano,
            _resultado(**{"key:pedido_id": {"value": 0}}),
            _resultado(**{"key:pedido_id": {"value": 3}}),
        )
        delta = _delta(facts)[0]
        assert delta.attrs["axis"] == "key"
        assert delta.attrs["diverged"] is True
        assert delta.measures["value_before"] == 0
        assert delta.measures["value_after"] == 3

    def test_o_eixo_fica_em_attrs_porque_o_catalogo_nao_tem_funcao_de_string(self):
        """`rules/expr.py` proibe `ast.Call`: sem `axis`, `SF-FVAL-004` nao teria
        como falar so dos agregados."""
        plano = _plano(
            count=_derivado("bigint", "f_1"),
            schema=_derivado("schema", "f_4"),
            **{"agg:sum:valor": _derivado("double", "f_2")},
        )
        limpo = _resultado(
            count={"value": 1},
            schema={"value": {"a": "bigint"}},
            **{"agg:sum:valor": {"value": 1.0}},
        )
        facts = build_comparison(plano, limpo, limpo)
        assert sorted(d.attrs["axis"] for d in _delta(facts)) == [
            "aggregate", "count", "schema"
        ]

    def test_tipo_que_o_modulo_nao_classifica_nao_vira_exata_por_omissao(self):
        plano = _plano(**{"agg:sum:x": _derivado("hll_sketch", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:x": {"value": 1}}),
            _resultado(**{"agg:sum:x": {"value": 2}}),
        )
        assert _delta(facts) == []
        assert _reasons(facts) == ["check_type_unclassified"]


class TestOLimiarMoraNoCatalogo:
    def test_o_modulo_nunca_decide_divergencia_de_ponto_flutuante(self):
        """Nem perto, nem longe: o veredito relativo nao e deste modulo, entao
        `diverged` nao aparece nem quando a diferenca e gritante."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 1_000_000.0}}),
            _resultado(**{"agg:sum:valor": {"value": 500_000.0}}),
        )
        delta = _delta(facts)[0]
        assert "diverged" not in delta.attrs
        assert delta.measures["relative_delta"] == 0.5

    def test_a_omissao_do_veredito_vem_escrita(self):
        """Chave que some sem explicacao e o defeito que este repositorio
        persegue."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 1.0}}),
            _resultado(**{"agg:sum:valor": {"value": 1.0}}),
        )
        assert "catalogo" in _delta(facts)[0].attrs["diverged_omitted_reason"]

    def test_o_delta_relativo_sobrevive_ao_arredondamento(self):
        """`round(x, 3)` zeraria 1e-12 e entregaria 0.0 para o catalogo comparar
        com a tolerancia -- toda divergencia pequena passaria."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 1.0}}),
            _resultado(**{"agg:sum:valor": {"value": 1.000000000001}}),
        )
        assert _delta(facts)[0].measures["relative_delta"] > 0

    def test_base_zero_nao_omite_o_delta_relativo(self):
        """A forma simetrica fecha o furo que obriga `benchmark._delta_pct` a
        omitir a chave: antes zero e depois nao-zero e distancia maxima."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 0.0}}),
            _resultado(**{"agg:sum:valor": {"value": 5.0}}),
        )
        assert _delta(facts)[0].measures["relative_delta"] == 1.0

    def test_zero_contra_zero_e_distancia_zero(self):
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 0.0}}),
            _resultado(**{"agg:sum:valor": {"value": 0.0}}),
        )
        assert _delta(facts)[0].measures["relative_delta"] == 0.0

    def test_a_sentinela_conta_os_deltas_que_ela_nao_julgou(self):
        """Sem isso, `diverged_check_count == 0` seria lido como 'nada divergiu'
        quando significa 'ninguem aqui decidiu'."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 1.0}}),
            _resultado(**{"agg:sum:valor": {"value": 2.0}}),
        )
        sentinela = _sentinela(facts)
        assert sentinela.measures["diverged_check_count"] == 0
        assert sentinela.measures["relative_delta_check_count"] == 1


class TestOsTresEstadosDeCobertura:
    def _facts(self):
        plano = _plano(
            count=_derivado("bigint", "f_1"),
            schema=_derivado("schema", "f_4"),
            **{"agg:sum:valor": _derivado("double", "f_2")},
        )
        lado = _resultado(
            count={"value": 0},
            **{"agg:sum:valor": {"value": None, "unavailable_reason": "coluna ausente"}},
        )
        return build_comparison(plano, lado, lado)

    def test_zero_e_valor_e_conta_como_reportado(self):
        facts = self._facts()
        assert _sentinela(facts).measures["reported_check_count"] == 1
        assert _delta(facts)[0].measures["value_before"] == 0

    def test_rodou_e_nao_deu_vira_unresolved_e_nao_conta(self):
        assert "check_value_unavailable" in _reasons(self._facts())

    def test_nao_reportado_e_o_unico_que_e_cobertura_faltante(self):
        facts = self._facts()
        assert "check_not_reported" in _reasons(facts)
        sentinela = _sentinela(facts)
        assert sentinela.measures["planned_check_count"] == 3
        assert sentinela.measures["reported_check_count"] == 1

    def test_os_tres_estados_nao_colidem_no_fact_id(self):
        """`Fact.id` ignora `attrs` (D-4a-2): sem check e motivo no subject, os
        unresolved sem measures sairiam com o mesmo id."""
        naos = _by_kind(self._facts(), "funcval.unresolved")
        assert len(naos) == 2
        assert len({f.id for f in naos}) == 2

    def test_valor_nulo_sem_razao_viola_o_contrato_e_nao_vira_ausencia(self):
        plano = _plano(count=_derivado("bigint", "f_1"))
        facts = build_comparison(
            plano,
            _resultado(count={"value": None}),
            _resultado(count={"value": 10}),
        )
        assert _reasons(facts) == ["check_entry_malformed"]

    def test_um_lado_so_nao_e_comparacao(self):
        plano = _plano(count=_derivado("bigint", "f_1"))
        facts = build_comparison(plano, _resultado(count={"value": 10}), _resultado())
        assert _delta(facts) == []
        assert _reasons(facts) == ["check_absent_one_side"]
        assert _by_kind(facts, "funcval.unresolved")[0].attrs["sides"] == ["after"]

    def test_valor_nao_numerico_onde_a_comparacao_exige_numero_nao_vira_zero(self):
        plano = _plano(count=_derivado("bigint", "f_1"))
        facts = build_comparison(
            plano,
            _resultado(count={"value": "1000"}),
            _resultado(count={"value": 1000}),
        )
        assert _delta(facts) == []
        assert _reasons(facts) == ["value_not_numeric"]

    def test_infinito_nao_e_numero_comparavel(self):
        """`json.loads` aceita `Infinity` e `NaN`: eles chegam de um resultado
        escrito a mao, e um `nan` em `measures` sairia do `json.dumps` como JSON
        invalido -- o golden nao voltaria a ser lido."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": float("inf")}}),
            _resultado(**{"agg:sum:valor": {"value": 1.0}}),
        )
        assert _delta(facts) == []
        assert _reasons(facts) == ["value_not_numeric"]

    def test_booleano_nao_e_numero(self):
        plano = _plano(count=_derivado("bigint", "f_1"))
        facts = build_comparison(
            plano, _resultado(count={"value": True}), _resultado(count={"value": 1})
        )
        assert _reasons(facts) == ["value_not_numeric"]


class TestOSchemaComparaColunaAColuna:
    def _facts(self, antes, depois):
        return build_comparison(
            _plano(schema=_derivado("schema", "f_4")),
            _resultado(schema={"value": antes}),
            _resultado(schema={"value": depois}),
        )

    def test_schema_identico_nao_diverge(self):
        assert _delta(self._facts({"a": "bigint"}, {"a": "bigint"}))[0].attrs["diverged"] is False

    def test_coluna_ausente_e_tipo_mudado_saem_nomeados(self):
        """`column_count` nao distingue coluna removida de coluna renomeada, e a
        SF-FVAL-002 fala das duas."""
        facts = self._facts(
            {"a": "bigint", "b": "string", "c": "double"},
            {"a": "string", "c": "double", "d": "bigint"},
        )
        delta = _delta(facts)[0]
        assert delta.attrs["diverged"] is True
        assert delta.attrs["removed_columns"] == ["b"]
        assert delta.attrs["added_columns"] == ["d"]
        assert delta.attrs["type_changed_columns"] == ["a"]
        assert delta.measures["type_changed_column_count"] == 1

    def test_schema_que_nao_e_mapa_nao_vira_mapa_vazio(self):
        facts = self._facts({"a": "bigint"}, 3)
        assert _delta(facts) == []
        assert _reasons(facts) == ["schema_value_not_mapping"]

    def test_o_comparador_nunca_confere_o_observado_contra_o_catalogo(self):
        """D-4c-3: o plano nao carrega o mapa declarado, entao o unico lado
        'verdadeiro' possivel nao existe. O delta so cita o que os dois
        resultados disseram."""
        delta = _delta(self._facts({"a": "bigint"}, {"a": "bigint"}))[0]
        assert set(delta.attrs) == {
            "added_columns", "axis", "check", "comparison", "diverged", "planned",
            "removed_columns", "target", "type", "type_changed_columns",
        }


class TestCheckQueOPlanoNaoPediu:
    """D-4c-11: comparado e marcado. Ignorar perde divergencia observada; contar
    como cobertura acusaria quem mediu a mais."""

    def _facts(self, **extra):
        return build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            _resultado(count={"value": 1}, **extra),
            _resultado(count={"value": 1}, **extra),
        )

    def test_o_nao_planejado_fica_dito(self):
        facts = self._facts(**{"agg:sum:x": {"value": 1, "type": "bigint"}})
        assert "check_not_planned" in _reasons(facts)
        assert _sentinela(facts).measures["unplanned_check_count"] == 1

    def test_o_nao_planejado_e_comparado_e_marcado(self):
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            _resultado(count={"value": 1}, **{"agg:sum:x": {"value": 1, "type": "bigint"}}),
            _resultado(count={"value": 1}, **{"agg:sum:x": {"value": 9, "type": "bigint"}}),
        )
        extra = [d for d in _delta(facts) if d.attrs["check"] == "agg:sum:x"][0]
        assert extra.attrs["planned"] is False
        assert extra.attrs["diverged"] is True

    def test_o_nao_planejado_nao_paga_a_cobertura_do_plano(self):
        facts = self._facts(**{"agg:sum:x": {"value": 1, "type": "bigint"}})
        sentinela = _sentinela(facts)
        assert sentinela.measures["planned_check_count"] == 1
        assert sentinela.measures["reported_check_count"] == 1
        assert sentinela.measures["compared_check_count"] == 2

    def test_o_tipo_do_resultado_so_e_lido_no_nao_planejado(self):
        facts = self._facts(**{"agg:sum:x": {"value": 1.0, "type": "double"}})
        extra = [d for d in _delta(facts) if d.attrs["check"] == "agg:sum:x"][0]
        assert extra.attrs["comparison"] == "relative"

    def test_nao_planejado_sem_tipo_nao_vira_comparacao_adivinhada(self):
        facts = self._facts(**{"agg:sum:x": {"value": 1}})
        assert [d for d in _delta(facts) if d.attrs["check"] == "agg:sum:x"] == []
        nao_planejado = [f for f in _by_kind(facts, "funcval.unresolved")
                         if f.attrs["reason"] == "check_not_planned"][0]
        assert nao_planejado.attrs["compared"] is False

    def test_tipo_em_conflito_entre_os_lados_nao_escolhe_um(self):
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            _resultado(count={"value": 1}, **{"agg:sum:x": {"value": 1, "type": "bigint"}}),
            _resultado(count={"value": 1}, **{"agg:sum:x": {"value": 1, "type": "double"}}),
        )
        nao_planejado = [f for f in _by_kind(facts, "funcval.unresolved")
                         if f.attrs["reason"] == "check_not_planned"][0]
        assert nao_planejado.attrs["type_conflict"] is True
        assert nao_planejado.attrs["compared"] is False

    def test_nao_planejado_num_lado_so_e_nomeado_sem_delta(self):
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            _resultado(count={"value": 1}, **{"agg:sum:x": {"value": 1, "type": "bigint"}}),
            _resultado(count={"value": 1}),
        )
        nao_planejado = [f for f in _by_kind(facts, "funcval.unresolved")
                         if f.attrs["reason"] == "check_not_planned"][0]
        assert nao_planejado.attrs["sides"] == ["before"]
        assert nao_planejado.attrs["compared"] is False


class TestOQueImpedeAComparacaoInteira:
    def test_alvo_diferente_nao_e_comparacao(self):
        """Comparar numeros de tabelas diferentes e pior que nao comparar."""
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            {"target": "outra", "checks": {"count": {"value": 1}}},
            _resultado(count={"value": 1}),
        )
        assert _delta(facts) == []
        assert _reasons(facts) == ["target_mismatch"]

    def test_lado_declarado_ao_contrario_nao_vira_comparacao_invertida(self):
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            {"target": "t", "side": "after", "checks": {"count": {"value": 1}}},
            {"target": "t", "side": "before", "checks": {"count": {"value": 2}}},
        )
        assert _delta(facts) == []
        assert _reasons(facts) == ["side_mismatch", "side_mismatch"]

    def test_plan_ref_diferente_entre_os_lados_bloqueia(self):
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            {"target": "t", "plan_ref": "f_aaaaaa", "checks": {"count": {"value": 1}}},
            {"target": "t", "plan_ref": "f_bbbbbb", "checks": {"count": {"value": 1}}},
        )
        assert _delta(facts) == []
        assert _reasons(facts) == ["plan_ref_conflict"]

    def test_a_sentinela_sai_mesmo_bloqueada_e_diz_o_que_bloqueou(self):
        """Sem ela, 'nao comparei' e 'comparei e estava tudo bem' ficariam
        indistinguiveis."""
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            {"target": "outra", "checks": {}},
            _resultado(count={"value": 1}),
        )
        sentinela = _sentinela(facts)
        assert sentinela.attrs["blocked_by"] == ["target_mismatch"]
        assert sentinela.measures["reported_check_count"] == 0
        assert sentinela.measures["planned_check_count"] == 1

    def test_plano_sem_checks_fica_dito(self):
        facts = build_comparison({"target": "t", "checks": {}}, _resultado(), _resultado())
        assert _reasons(facts) == ["plan_without_checks"]

    def test_dois_bloqueios_diferentes_nao_colidem_no_fact_id(self):
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            {"target": "outra", "side": "after", "checks": {}},
            _resultado(count={"value": 1}),
        )
        naos = _by_kind(facts, "funcval.unresolved")
        assert len(naos) == 2
        assert len({f.id for f in naos}) == 2


class TestASentinelaDeclaraOLimite:
    def test_os_quatro_sao_proxies_e_isso_esta_na_saida(self):
        """Criterio 8 da §9: nao e comentario no codigo, e campo na saida."""
        facts = build_comparison(
            _plano(count=_derivado("bigint", "f_1")),
            _resultado(count={"value": 1}),
            _resultado(count={"value": 1}),
        )
        sentinela = _sentinela(facts)
        assert sentinela.attrs["proxies"] == ["count", "schema", "keys", "aggregates"]
        assert "NAO provam que o dado e o mesmo" in sentinela.attrs["proxy_limit"]

    def test_o_caso_limpo_nao_produz_unresolved_nenhum(self):
        limpo = _resultado(
            count={"value": 10},
            schema={"value": {"a": "bigint"}},
            **{"agg:sum:valor": {"value": 1.0}},
        )
        facts = build_comparison(
            _plano(
                count=_derivado("bigint", "f_1"),
                schema=_derivado("schema", "f_4"),
                **{"agg:sum:valor": _derivado("double", "f_2")},
            ),
            limpo,
            limpo,
        )
        assert _by_kind(facts, "funcval.unresolved") == []
        assert _sentinela(facts).measures["diverged_check_count"] == 0
        assert _sentinela(facts).attrs["blocked_by"] == []

    def test_o_eixo_que_o_plano_nunca_pediu_viaja_para_a_sentinela(self):
        """Quem le a sentinela nao tem o plano na mao."""
        plano = {"target": "t", "checks": {"count": _derivado("bigint", "f_1")},
                 "undeclared_axes": ["keys", "aggregates"]}
        facts = build_comparison(
            plano, _resultado(count={"value": 1}), _resultado(count={"value": 1})
        )
        assert _sentinela(facts).attrs["undeclared_axes"] == ["aggregates", "keys"]


class TestAComparacaoSegueOPadraoDosDerivados:
    def _facts(self):
        return build_comparison(
            _plano(
                count=_derivado("bigint", "f_1"),
                schema=_derivado("schema", "f_4"),
                **{"agg:sum:valor": _derivado("double", "f_2"),
                   "agg:sum:x": _derivado("hll_sketch", "f_2")},
            ),
            _resultado(
                count={"value": 1000},
                schema={"value": {"a": "bigint"}},
                **{"agg:sum:valor": {"value": 1.0}, "agg:sum:x": {"value": 1},
                   "extra": {"value": 2, "type": "bigint"}},
            ),
            _resultado(
                count={"value": 998},
                schema={"value": {"a": "string"}},
                **{"agg:sum:valor": {"value": 2.0}, "agg:sum:x": {"value": 1},
                   "extra": {"value": 2, "type": "bigint"}},
            ),
            path_hint="antes..depois",
        )

    def test_todo_fact_emitido_esta_no_namespace(self):
        assert {f.kind for f in self._facts()} <= EMITTED_KINDS

    def test_todo_fact_emitido_passa_no_schema(self):
        for fact in self._facts():
            validate_fact(fact.to_dict())

    def test_a_saida_e_ordenada_deterministicamente(self):
        facts = self._facts()
        assert facts == sort_facts(facts)
        assert [f.id for f in self._facts()] == [f.id for f in facts]

    def test_dois_checks_do_mesmo_alvo_nao_colidem_no_fact_id(self):
        deltas = _delta(self._facts())
        assert len({d.id for d in deltas}) == len(deltas)

    def test_a_procedencia_nomeia_o_deriver_e_o_par_comparado(self):
        for fact in self._facts():
            assert fact.provenance == {
                "artifact": "antes..depois",
                "artifact_sha256": "",
                "extractor": EXTRACTOR_ID,
            }

    def test_o_float_nao_entra_cru_nas_measures(self):
        """Ruido de bit entraria no `Fact.id` e o golden dependeria dele."""
        plano = _plano(**{"agg:sum:valor": _derivado("double", "f_2")})
        facts = build_comparison(
            plano,
            _resultado(**{"agg:sum:valor": {"value": 0.1 + 0.2}}),
            _resultado(**{"agg:sum:valor": {"value": 0.3}}),
        )
        assert _delta(facts)[0].measures["value_before"] == 0.3
