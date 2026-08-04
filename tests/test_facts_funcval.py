"""Task 2 da Fase 4c: `funcval plan`.

Os tres primeiros testes sao os literais do plano. O resto prova o que a Task 2
mediu e decidiu: um plano POR ALVO, casamento de alvo por string identica,
`origin` em todo check, e o eixo ausente escrito em vez de calado.
"""
from sparkforge.facts.funcval import EMITTED_KINDS, EXTRACTOR_ID, build_plan
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
