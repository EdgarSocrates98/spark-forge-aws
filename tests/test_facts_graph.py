"""Testes do extrator de grafo (`sparkforge/facts/graph.py`).

Cada bloco prova uma decisao registrada no cabecalho do modulo ou um veto da
pesquisa (`knowledge/graph/graphframes-api.md`). Onde o teste existe para
IMPEDIR algo -- vocabulario fechado, regra vetada, acusacao falsa -- isso esta
dito no nome.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sparkforge.facts.graph import (
    EMITTED_KINDS,
    UNRESOLVED_REASONS,
    extract_graph,
    extract_graph_path,
    extract_graph_tree,
)


def _kinds(facts):
    return [f.kind for f in facts]


def _of(facts, kind):
    return [f for f in facts if f.kind == kind]


def _one(facts, kind):
    found = _of(facts, kind)
    assert len(found) == 1, [f.attrs for f in found]
    return found[0]


def _sentinel(facts):
    return _one(facts, "graph.module_analyzed")


# --------------------------------------------------------------------------
# Sentinela: o invariante que a §1 do spec mede quebrado no motor de hoje.
# --------------------------------------------------------------------------


def test_arquivo_sem_grafo_ainda_emite_sentinela():
    facts = extract_graph("x = 1\n", "sem_grafo.py")
    kinds = _kinds(facts)
    assert "graph.module_analyzed" in kinds
    sentinela = _sentinel(facts)
    assert sentinela.measures["algorithm_count"] == 0
    assert sentinela.measures["import_count"] == 0


def test_sentinela_conta_as_quatro_grandezas():
    src = (
        "from graphframes import GraphFrame\n"
        "g = GraphFrame(v, e)\n"
        "g.connectedComponents(algorithm=modo)\n"
    )
    sentinela = _sentinel(extract_graph(src, "j.py"))
    assert sentinela.measures == {
        "import_count": 1,
        "construction_count": 1,
        "algorithm_count": 1,
        "unresolved_count": 1,
    }


def test_fonte_que_nao_compila_vira_unresolved_e_nao_sentinela():
    facts = extract_graph("def f(\n", "quebrado.py")
    assert _kinds(facts) == ["graph.unresolved"]
    assert facts[0].attrs["reason"] == "syntax_error"


def test_sentinela_sai_para_arquivo_vazio():
    sentinela = _sentinel(extract_graph("", "vazio.py"))
    assert sentinela.measures["construction_count"] == 0


# --------------------------------------------------------------------------
# `graph.import` -- o alcance medido, e o que ele recusa seguir.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("linha", "form", "symbol", "alias"),
    [
        ("from graphframes import GraphFrame", "from", "GraphFrame", None),
        ("from graphframes import GraphFrame as GF", "from", "GraphFrame", "GF"),
        ("import graphframes", "plain", "graphframes", None),
        ("import graphframes as gf", "plain", "graphframes", "gf"),
        ("from graphframes.lib import Pregel", "from", "Pregel", None),
    ],
)
def test_as_quatro_formas_de_import_viram_fact(linha, form, symbol, alias):
    fact = _one(extract_graph(linha + "\n", "j.py"), "graph.import")
    assert fact.attrs["form"] == form
    assert fact.attrs["symbol"] == symbol
    assert fact.attrs.get("alias") == alias
    assert fact.measures["line"] == 1


def test_import_dentro_de_funcao_e_lido_e_marcado():
    src = "def build():\n    from graphframes import GraphFrame\n"
    fact = _one(extract_graph(src, "j.py"), "graph.import")
    assert fact.attrs["scope"] == "function"
    assert fact.subject["symbol"] == "build"


def test_import_sob_try_e_lido_e_marcado_como_guarded():
    src = (
        "try:\n    from graphframes import GraphFrame\n"
        "except ImportError:\n    GraphFrame = None\n"
    )
    fact = _one(extract_graph(src, "j.py"), "graph.import")
    assert fact.attrs["guarded"] is True
    assert fact.attrs["scope"] == "module"


def test_import_no_topo_nao_e_guarded():
    fact = _one(extract_graph("from graphframes import GraphFrame\n", "j.py"), "graph.import")
    assert fact.attrs["guarded"] is False


def test_import_de_outro_pacote_nao_vira_fact():
    src = "from pyspark.sql import SparkSession\nimport pandas as pd\n"
    assert _of(extract_graph(src, "j.py"), "graph.import") == []


@pytest.mark.parametrize(
    "linha",
    [
        'gf = importlib.import_module("graphframes")',
        'gf = __import__("graphframes")',
        "gf = importlib.import_module(nome)",
    ],
)
def test_import_dinamico_vira_ponto_cego_contado(linha):
    facts = extract_graph(linha + "\n", "j.py")
    assert _one(facts, "graph.unresolved").attrs["reason"] == "dynamic_import"
    assert _sentinel(facts).measures["unresolved_count"] == 1


def test_import_dinamico_de_outro_pacote_literal_nao_e_assunto_desta_area():
    facts = extract_graph('m = importlib.import_module("pandas")\n', "j.py")
    assert _of(facts, "graph.unresolved") == []


# --------------------------------------------------------------------------
# `graph.construction` -- `ast.Call` com `func=ast.Name`, que o laco de
# `pyspark_ast.py` descartaria.
# --------------------------------------------------------------------------


def test_construcao_por_nome_e_lida():
    src = "from graphframes import GraphFrame\ng = GraphFrame(vertices, arestas)\n"
    fact = _one(extract_graph(src, "j.py"), "graph.construction")
    assert fact.attrs["constructor"] == "GraphFrame"
    assert fact.attrs["vertices_ref"] == "vertices"
    assert fact.attrs["edges_ref"] == "arestas"
    assert fact.attrs["inside_loop"] is False


def test_construcao_por_alias_do_import_e_lida():
    src = "from graphframes import GraphFrame as GF\ng = GF(v, e)\n"
    assert _one(extract_graph(src, "j.py"), "graph.construction").attrs["constructor"] == "GF"


def test_construcao_por_atributo_do_pacote_e_lida():
    src = "import graphframes as gf\ng = gf.GraphFrame(v, e)\n"
    fact = _one(extract_graph(src, "j.py"), "graph.construction")
    assert fact.attrs["constructor"] == "gf.GraphFrame"


def test_graphframe_de_objeto_desconhecido_nao_vira_construcao():
    """Sem `import graphframes`, `qualquer.GraphFrame(...)` seria adivinhacao."""
    facts = extract_graph("g = outra_lib.GraphFrame(v, e)\n", "j.py")
    assert _of(facts, "graph.construction") == []


def test_construcao_em_laco_e_marcada():
    src = "from graphframes import GraphFrame\nfor i in range(3):\n    g = GraphFrame(v, e)\n"
    assert _one(extract_graph(src, "j.py"), "graph.construction").attrs["inside_loop"] is True


def test_construcao_sem_nome_no_argumento_omite_a_referencia():
    src = "from graphframes import GraphFrame\ng = GraphFrame(spark.read.parquet(p), e)\n"
    attrs = _one(extract_graph(src, "j.py"), "graph.construction").attrs
    assert "vertices_ref" not in attrs
    assert attrs["edges_ref"] == "e"


# --------------------------------------------------------------------------
# Persistencia de vertices e arestas: ATRIBUTO do mesmo fact, nunca kind
# proprio (`D-5d-17`). Omitir x emitir `false` decide pela direcao do erro.
# --------------------------------------------------------------------------


def test_persistencia_nao_e_kind_proprio():
    assert "graph.source_persisted" not in EMITTED_KINDS


def test_cache_na_propria_cadeia_do_argumento():
    src = "from graphframes import GraphFrame\ng = GraphFrame(v.cache(), e.persist())\n"
    attrs = _one(extract_graph(src, "j.py"), "graph.construction").attrs
    assert attrs["vertices_persisted"] is True
    assert attrs["edges_persisted"] is True


def test_cache_antes_da_construcao_conta():
    src = "from graphframes import GraphFrame\nv.cache()\ng = GraphFrame(v, e)\n"
    assert _one(extract_graph(src, "j.py"), "graph.construction").attrs["vertices_persisted"]


def test_nome_ligado_ao_resultado_do_cache_conta_como_persistido():
    """`v = vertices.cache()` e a forma comum; contar so a raiz acusaria certo."""
    src = "from graphframes import GraphFrame\nv = vertices.cache()\ng = GraphFrame(v, e)\n"
    assert _one(extract_graph(src, "j.py"), "graph.construction").attrs["vertices_persisted"]


def test_cache_depois_da_construcao_nao_conta():
    src = "from graphframes import GraphFrame\ng = GraphFrame(v, e)\nv.cache()\n"
    assert _one(extract_graph(src, "j.py"), "graph.construction").attrs["vertices_persisted"] is (
        False
    )


def test_unpersist_derruba_a_evidencia():
    src = "from graphframes import GraphFrame\nv.cache()\nv.unpersist()\ng = GraphFrame(v, e)\n"
    attrs = _one(extract_graph(src, "j.py"), "graph.construction").attrs
    assert attrs["vertices_persisted"] is False


def test_religacao_depois_do_cache_derruba_a_evidencia():
    src = (
        "from graphframes import GraphFrame\n"
        "v.cache()\n"
        "v = carrega()\n"
        "g = GraphFrame(v, e)\n"
    )
    assert _one(extract_graph(src, "j.py"), "graph.construction").attrs["vertices_persisted"] is (
        False
    )


def test_parametro_sem_evidencia_local_omite_a_chave():
    """A historia do parametro comeca no chamador; `false` acusaria quem persistiu."""
    src = (
        "from graphframes import GraphFrame\n"
        "def build(vertices, arestas):\n"
        "    return GraphFrame(vertices, arestas)\n"
    )
    attrs = _one(extract_graph(src, "j.py"), "graph.construction").attrs
    assert "vertices_persisted" not in attrs
    assert "edges_persisted" not in attrs


def test_parametro_com_evidencia_local_resolve():
    src = (
        "from graphframes import GraphFrame\n"
        "def build(vertices, arestas):\n"
        "    vertices.cache()\n"
        "    return GraphFrame(vertices, arestas)\n"
    )
    attrs = _one(extract_graph(src, "j.py"), "graph.construction").attrs
    assert attrs["vertices_persisted"] is True
    assert "edges_persisted" not in attrs


def test_cache_noutro_escopo_nao_vale_para_este():
    """Nome nu nao identifica objeto entre escopos."""
    src = (
        "from graphframes import GraphFrame\n"
        "def a():\n"
        "    vertices = le()\n"
        "    vertices.cache()\n"
        "def b():\n"
        "    vertices = le()\n"
        "    return GraphFrame(vertices, arestas)\n"
    )
    attrs = _one(extract_graph(src, "j.py"), "graph.construction").attrs
    assert attrs["vertices_persisted"] is False


# --------------------------------------------------------------------------
# `graph.algorithm` -- vocabulario fechado, duas convencoes, e o Pregel que
# nao e chamada (vetos V-GF-5 e V-GF-6).
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nome",
    [
        "connectedComponents",
        "stronglyConnectedComponents",
        "pageRank",
        "parallelPersonalizedPageRank",
        "shortestPaths",
        "labelPropagation",
        "triangleCount",
        "svdPlusPlus",
        "bfs",
        "aggregateMessages",
        "powerIterationClustering",
    ],
)
def test_algoritmos_camelcase_viram_fact(nome):
    fact = _one(extract_graph(f"r = g.{nome}()\n", "j.py"), "graph.algorithm")
    assert fact.attrs["name"] == nome
    assert fact.attrs["form"] == "call"
    assert fact.attrs["receiver"] == "g"


@pytest.mark.parametrize(
    "nome",
    [
        "k_core",
        "maximal_independent_set",
        "as_undirected",
        "as_reversed",
        "aggregate_neighbors",
        "hyper_anf",
        "neighborhood_aware_cdlp",
        "all_paths",
        "type_degree",
    ],
)
def test_algoritmos_snake_case_da_linhagem_corrente_viram_fact(nome):
    """As duas convencoes convivem no mesmo objeto (V-GF-6)."""
    assert _one(extract_graph(f"r = g.{nome}()\n", "j.py"), "graph.algorithm").attrs["name"] == nome


def test_pregel_e_property_e_ainda_assim_vira_fact():
    """V-GF-5: vocabulario casado so contra `ast.Call` perde o Pregel inteiro."""
    src = "r = g.pregel.setMaxIter(15).sendMsgToDst(m).aggMsgs(a).run()\n"
    fact = _one(extract_graph(src, "j.py"), "graph.algorithm")
    assert fact.attrs["name"] == "pregel"
    assert fact.attrs["form"] == "property"
    assert fact.attrs["receiver"] == "g"
    assert fact.attrs["iteration_arg"] == "setMaxIter"
    assert fact.measures["iteration_literal"] == 15


def test_pregel_sem_set_max_iter_nao_inventa_atributo():
    src = "r = g.pregel.sendMsgToDst(m).aggMsgs(a).run()\n"
    fact = _one(extract_graph(src, "j.py"), "graph.algorithm")
    assert "iteration_arg" not in fact.attrs
    assert "iteration_literal" not in fact.measures


@pytest.mark.parametrize("nome", ["triplets", "inDegrees", "outDegrees"])
def test_as_outras_properties_tambem_viram_fact(nome):
    fact = _one(extract_graph(f"r = g.{nome}\n", "j.py"), "graph.algorithm")
    assert fact.attrs["form"] == "property"


def test_algoritmo_em_laco_e_marcado():
    src = "for i in range(3):\n    g.aggregateMessages(a, b)\n"
    assert _one(extract_graph(src, "j.py"), "graph.algorithm").attrs["inside_loop"] is True


def test_receptor_sem_raiz_nomeada_vira_ponto_cego_contado():
    src = "from graphframes import GraphFrame\nGraphFrame(v, e).connectedComponents()\n"
    facts = extract_graph(src, "j.py")
    algoritmo = _one(facts, "graph.algorithm")
    assert "receiver" not in algoritmo.attrs
    assert _one(facts, "graph.unresolved").attrs["reason"] == "receiver_without_name"


# --------------------------------------------------------------------------
# Os dois niveis do vocabulario: nomes ambiguos exigem a evidencia do import.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("nome", ["find", "validate", "degrees"])
def test_nome_ambiguo_sem_import_nao_vira_fact(nome):
    facts = extract_graph(f"r = texto.{nome}\nr2 = texto.{nome}()\n", "j.py")
    assert _of(facts, "graph.algorithm") == []


@pytest.mark.parametrize(("nome", "fonte"), [("find", "g.find(m)"), ("degrees", "g.degrees")])
def test_nome_ambiguo_com_import_vira_fact(nome, fonte):
    src = f"from graphframes import GraphFrame\nr = {fonte}\n"
    assert _one(extract_graph(src, "j.py"), "graph.algorithm").attrs["name"] == nome


@pytest.mark.parametrize("metodo", ["cache", "persist", "unpersist"])
def test_metodos_herdados_de_dataframe_nao_sao_algoritmo(metodo):
    """Reemiti-los duplicaria o sujeito de `SF-PY-008` e apagaria a fronteira."""
    src = f"from graphframes import GraphFrame\ng = GraphFrame(v, e)\ng.{metodo}()\n"
    assert _of(extract_graph(src, "j.py"), "graph.algorithm") == []


# --------------------------------------------------------------------------
# Checkpoint: alcance de ARQUIVO, tres saidas no `.py` e a quarta que so
# aparece quando o proprio `.py` a declara.
# --------------------------------------------------------------------------


def test_set_checkpoint_dir_vira_fact_com_o_literal():
    src = 'spark.sparkContext.setCheckpointDir("s3://b/ckpt")\n'
    fact = _one(extract_graph(src, "j.py"), "graph.checkpoint_dir")
    assert fact.attrs["form"] == "set_checkpoint_dir"
    assert fact.attrs["literal"] == "s3://b/ckpt"
    assert fact.attrs["receiver"] == "spark"


def test_conf_checkpoint_dir_no_proprio_py_tambem_conta():
    src = 'spark.conf.set("spark.checkpoint.dir", "s3://b/c")\ng.connectedComponents()\n'
    facts = extract_graph(src, "j.py")
    assert _one(facts, "graph.checkpoint_dir").attrs["form"] == "conf_checkpoint_dir"
    assert _one(facts, "graph.algorithm").attrs["checkpoint_configured_in_module"] is True


def test_conf_de_local_checkpoints_ligada_conta():
    src = (
        'spark.conf.set("spark.graphframes.useLocalCheckpoints", "true")\n'
        "g.connectedComponents()\n"
    )
    facts = extract_graph(src, "j.py")
    fact = _one(facts, "graph.checkpoint_dir")
    assert fact.attrs == {"form": "conf_local_checkpoints", "enabled": True}
    assert _one(facts, "graph.algorithm").attrs["checkpoint_configured_in_module"] is True


def test_conf_de_local_checkpoints_desligada_nao_conta():
    src = (
        'spark.conf.set("spark.graphframes.useLocalCheckpoints", "false")\n'
        "g.connectedComponents()\n"
    )
    facts = extract_graph(src, "j.py")
    assert _one(facts, "graph.checkpoint_dir").attrs["enabled"] is False
    assert _one(facts, "graph.algorithm").attrs["checkpoint_configured_in_module"] is False


def test_conf_de_local_checkpoints_ilegivel_omite_a_decisao():
    src = 'spark.conf.set("spark.graphframes.useLocalCheckpoints", flag)\ng.connectedComponents()\n'
    facts = extract_graph(src, "j.py")
    algoritmo = _one(facts, "graph.algorithm")
    assert "checkpoint_required" not in algoritmo.attrs
    assert "checkpoint_configured_in_module" not in algoritmo.attrs
    assert any(f.attrs["reason"] == "non_literal_argument" for f in _of(facts, "graph.unresolved"))


def test_checkpoint_dir_noutra_funcao_vale_para_o_arquivo_inteiro():
    """Alcance de arquivo: o `SparkContext` e um so no processo."""
    src = (
        "def build_spark():\n"
        '    spark.sparkContext.setCheckpointDir("s3://b/c")\n'
        "def roda(g):\n"
        "    return g.connectedComponents()\n"
    )
    assert _one(extract_graph(src, "j.py"), "graph.algorithm").attrs[
        "checkpoint_configured_in_module"
    ]


# --------------------------------------------------------------------------
# `checkpoint_required` -- a decisao que o motor nao consegue exprimir.
# --------------------------------------------------------------------------


def test_connected_components_sem_saida_exige_checkpoint():
    facts = extract_graph("r = g.connectedComponents()\n", "j.py")
    attrs = _one(facts, "graph.algorithm").attrs
    assert attrs["checkpoint_required"] is True
    assert attrs["checkpoint_configured_in_module"] is False


@pytest.mark.parametrize(
    "chamada",
    [
        'g.connectedComponents(algorithm="graphx")',
        "g.connectedComponents(checkpointInterval=0)",
        "g.connectedComponents(checkpointInterval=-1)",
        "g.connectedComponents(checkpoint_interval=-1)",
        "g.connectedComponents(use_local_checkpoints=True)",
        "g.connectedComponents(useLocalCheckpoints=True)",
    ],
)
def test_as_tres_saidas_legitimas_dispensam_a_exigencia(chamada):
    """V-GF-1: exigir de quem declarou saida acusaria quem escreveu certo."""
    fact = _one(extract_graph(chamada + "\n", "j.py"), "graph.algorithm")
    assert fact.attrs["checkpoint_required"] is False


def test_alias_depreciado_two_phase_continua_exigindo():
    """`graphframes` e alias de `two_phase`, e nao e saida (V-GF-8)."""
    src = 'g.connectedComponents(algorithm="graphframes")\n'
    attrs = _one(extract_graph(src, "j.py"), "graph.algorithm").attrs
    assert attrs["algorithm_arg"] == "graphframes"
    assert attrs["checkpoint_required"] is True


def test_saida_ilegivel_omite_a_decisao_em_vez_de_arriscar_p0():
    src = "g.connectedComponents(algorithm=modo)\n"
    facts = extract_graph(src, "j.py")
    assert "checkpoint_required" not in _one(facts, "graph.algorithm").attrs
    assert _one(facts, "graph.unresolved").attrs == {
        "reason": "non_literal_argument",
        "param": "algorithm",
    }


def test_argumento_posicional_omite_a_decisao_e_conta_o_ponto_cego():
    """A ordem dos parametros mudou entre linhagens e nao foi medida."""
    facts = extract_graph('g.connectedComponents("graphx")\n', "j.py")
    assert "checkpoint_required" not in _one(facts, "graph.algorithm").attrs
    assert _one(facts, "graph.unresolved").attrs["reason"] == "positional_argument"


def test_kwargs_desempacotado_omite_a_decisao():
    facts = extract_graph("g.connectedComponents(**opcoes)\n", "j.py")
    assert "checkpoint_required" not in _one(facts, "graph.algorithm").attrs
    assert _one(facts, "graph.unresolved").attrs == {
        "reason": "non_literal_argument",
        "param": "**",
    }


@pytest.mark.parametrize(
    "chamada",
    [
        "g.labelPropagation(maxIter=5)",
        "g.shortestPaths(landmarks=['a'])",
        "g.pageRank(tol=0.01)",
        "g.k_core()",
    ],
)
def test_a_exigencia_nao_se_estende_a_outros_algoritmos(chamada):
    """V-GF-4: em `0.8.x` eles vao por GraphX e nao exigem diretorio nenhum."""
    attrs = _one(extract_graph(chamada + "\n", "j.py"), "graph.algorithm").attrs
    assert "checkpoint_required" not in attrs
    assert "checkpoint_configured_in_module" not in attrs


def test_checkpoint_interval_literal_vira_measure():
    """Unico limiar numerico com fonte primaria nesta area."""
    src = "g.connectedComponents(checkpointInterval=5)\n"
    fact = _one(extract_graph(src, "j.py"), "graph.algorithm")
    assert fact.measures["checkpoint_interval"] == 5
    assert fact.attrs["checkpoint_required"] is True


# --------------------------------------------------------------------------
# A regra vetada nao entra pela porta dos fundos (`D-6a-4`, V-GF-2, V-GF-3).
# --------------------------------------------------------------------------


def test_nenhum_fact_carrega_has_max_iter():
    src = (
        "from graphframes import GraphFrame\n"
        "g = GraphFrame(v, e)\n"
        "g.pageRank(tol=0.01)\n"
        "g.connectedComponents()\n"
        "g.pregel.sendMsgToDst(m).run()\n"
    )
    for fact in extract_graph(src, "j.py"):
        assert "has_max_iter" not in fact.attrs
        assert "max_iter_literal" not in fact.attrs


def test_page_rank_com_tol_nomeia_o_modo_que_veio():
    """V-GF-2: quem passou `tol` escreveu certo, e o fact tem de dizer qual veio."""
    fact = _one(extract_graph("g.pageRank(tol=0.01)\n", "j.py"), "graph.algorithm")
    assert fact.attrs["iteration_arg"] == "tol"
    assert fact.measures["iteration_literal"] == 0.01


def test_page_rank_com_max_iter_nomeia_o_outro_modo():
    fact = _one(extract_graph("g.pageRank(maxIter=10)\n", "j.py"), "graph.algorithm")
    assert fact.attrs["iteration_arg"] == "maxIter"
    assert fact.measures["iteration_literal"] == 10


def test_algoritmo_sem_parametro_de_iteracao_nao_afirma_nada():
    fact = _one(extract_graph("g.triangleCount()\n", "j.py"), "graph.algorithm")
    assert "iteration_arg" not in fact.attrs
    assert "iteration_literal" not in fact.measures


# --------------------------------------------------------------------------
# Invariantes do modulo.
# --------------------------------------------------------------------------


def test_todo_kind_emitido_esta_no_namespace_declarado():
    src = (
        "from graphframes import GraphFrame\n"
        'spark.sparkContext.setCheckpointDir("s3://b/c")\n'
        "g = GraphFrame(v.cache(), e)\n"
        "g.connectedComponents(algorithm=modo)\n"
    )
    facts = extract_graph(src, "j.py")
    assert {f.kind for f in facts} - EMITTED_KINDS == set()
    assert {f.kind for f in facts} == EMITTED_KINDS


def test_toda_razao_de_unresolved_esta_no_vocabulario_fechado():
    src = (
        "from graphframes import GraphFrame\n"
        'm = importlib.import_module("graphframes")\n'
        "g.connectedComponents(algorithm=modo)\n"
        'GraphFrame(v, e).connectedComponents("graphx")\n'
    )
    razoes = {f.attrs["reason"] for f in _of(extract_graph(src, "j.py"), "graph.unresolved")}
    assert razoes
    assert razoes <= UNRESOLVED_REASONS


def test_ids_de_fact_sao_unicos_num_arquivo_denso():
    src = (
        "from graphframes import GraphFrame\n"
        "g = GraphFrame(v, e); h = GraphFrame(v, e)\n"
        'g.connectedComponents("graphx", algorithm=modo)\n'
        "g.pageRank(tol=0.01); g.triangleCount()\n"
    )
    facts = extract_graph(src, "j.py")
    ids = [f.id for f in facts]
    assert len(ids) == len(set(ids))


def test_ordem_e_deterministica():
    src = "from graphframes import GraphFrame\ng = GraphFrame(v, e)\ng.pageRank(tol=0.1)\n"
    primeira = [(f.kind, f.id) for f in extract_graph(src, "j.py")]
    assert primeira == [(f.kind, f.id) for f in extract_graph(src, "j.py")]


def test_procedencia_carrega_extrator_e_sha():
    facts = extract_graph("x = 1\n", "j.py")
    provenance = facts[0].provenance
    assert provenance["extractor"].startswith("graph@")
    assert len(provenance["artifact_sha256"]) == 64


def test_o_modulo_nao_importa_pyspark_nem_boto3():
    """Criterio 1 do spec: le o `.py` e nada mais."""
    fonte = Path("sparkforge/facts/graph.py").read_text(encoding="utf-8")
    importados = set()
    for node in ast.walk(ast.parse(fonte)):
        if isinstance(node, ast.Import):
            importados.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            importados.add(node.module.split(".")[0])
    assert importados == {"__future__", "ast", "hashlib", "pathlib", "typing", "sparkforge"}


# --------------------------------------------------------------------------
# Entradas por caminho e por arvore.
# --------------------------------------------------------------------------


def test_extract_graph_path_ancora_relativo_ao_repo_root(tmp_path):
    alvo = tmp_path / "jobs" / "grafo.py"
    alvo.parent.mkdir()
    alvo.write_text("from graphframes import GraphFrame\n", encoding="utf-8")
    facts = extract_graph_path(alvo, tmp_path)
    assert _one(facts, "graph.import").subject["file"] == "jobs/grafo.py"


def test_extract_graph_path_de_arquivo_ausente_vira_read_error(tmp_path):
    facts = extract_graph_path(tmp_path / "nao_existe.py", tmp_path)
    assert _kinds(facts) == ["graph.unresolved"]
    assert facts[0].attrs["reason"] == "read_error"


def test_extract_graph_tree_varre_em_ordem_e_nao_para_no_arquivo_ruim(tmp_path):
    (tmp_path / "a.py").write_text("from graphframes import GraphFrame\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def f(\n", encoding="utf-8")
    facts = extract_graph_tree(tmp_path, tmp_path)
    arquivos = {f.subject["file"] for f in facts}
    assert arquivos == {"a.py", "b.py"}
    assert len(_of(facts, "graph.module_analyzed")) == 1
