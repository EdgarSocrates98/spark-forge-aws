"""Golden test do corpus de processamento de grafo (GraphFrames).

Arquivo dedicado, mesma razao de `test_fixtures_golden_dq.py`: o golden guarda
so os facts `graph.*` (mais os `tf.*` das duas fixtures que cruzam com o IaC).
Os de `pyspark_ast` sobre os mesmos `.py` ja tem o corpus `fixtures/pyspark/` --
repetidos aqui, uma mudanca em `pyspark_ast` quebraria dois goldens pelo mesmo
motivo, escondendo qual dos dois contratos regrediu.

TODO `expects_rules` NASCEU VAZIO na Task 4, e isso era o correto e nao uma
pendencia: a area `SF-GRAPH` so existe a partir da Task 5. Ate la os dezenove
goldens de findings eram NEGATIVOS -- se alguma regra ja existente disparasse
sobre um fact deste corpus, o diff apareceria aqui.

Com a Task 5, CINCO das dezenove ganharam regra -- a Task 4 previa "tres ou
quatro", e a quinta e o segundo lado do par de disponibilidade: SF-GRAPH-002
dispara nas DUAS fixtures de Spark 3.3, com e sem `--extra-jars`, porque a fonte
recusa tratar jar de outro minor como garantia (`rules/catalog/graph.yaml`,
veto V-GR-1).

A REVISAO DA FASE 6a levou o corpus a VINTE E CINCO. Cinco fixtures novas sao a
conf de checkpoint que o extrator nao lia -- cada uma disparava P0 sobre codigo
correto --, e a sexta e a primeira com DOIS sujeitos defeituosos, sem a qual os
dois `same_subject` da area eram apagaveis com a suite inteira verde. Hoje SEIS
das vinte e cinco tem regra e as outras DEZENOVE continuam vazias DE PROPOSITO:
nove existem justamente para provar que o motor CALA sobre codigo correto.

O corpus e desenhado por eixo: cada fixture tem no maximo um defeito, e o resto
dela e a forma certa. Sem isso, uma regra que dispare sobre qualquer
`connectedComponents` passaria em todo o corpus e ninguem notaria que ela acusa
quem acertou -- que e o pior modo de falha desta area, porque o codigo correto
de grafo e minoritario e quem o escreveu pagou para aprender.

`TestAdversarial` trava, fixture a fixture, o atributo que cada uma existe para
provar: o golden sozinho prova que a saida nao mudou, mas nao prova que ela diz
o que o nome da fixture promete.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.graph import EMITTED_KINDS, extract_graph_path, extract_graph_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "graph"

REQUIRED_FIXTURES = {
    # A sentinela, nas duas pontas: arquivo sem grafo nenhum, e o negativo de
    # referencia com o job de grafo feito do jeito certo.
    "sem_grafo",
    "grafo_correto",
    # O positivo da exigencia de checkpoint, isolado num eixo so.
    "connected_components_sem_checkpoint",
    # AS FORMAS DE ESCREVER CERTO, uma fixture cada. Acusar qualquer uma delas e
    # acusar quem acertou, e uma so nao cobre as outras: sao caminhos diferentes
    # no extrator (argumento, argumento, argumento, conf de modulo).
    "saida_graphx",
    "saida_intervalo_nao_positivo",
    "saida_local_checkpoints",
    "conf_checkpoint_dir_no_job",
    "conf_local_checkpoints_no_job",
    # AS DUAS FORMAS DE DECLARAR A CONF que a revisao da Fase 6a mediu faltando.
    # As duas produziam `checkpoint_configured_in_module: false` sobre codigo que
    # configurou o checkpoint, e cada uma disparava a P0 da area.
    "checkpoint_por_builder_config",
    "conf_chave_por_keyword",
    # O que nao da para ler cala a decisao, e sai contado -- pelo lado do
    # modulo e pelo lado da chamada.
    "conf_local_checkpoints_ilegivel",
    "exigencia_indecidivel",
    # AS DUAS METADES DA CONF ILEGIVEL, que ate a revisao caiam em lados
    # opostos: valor ilegivel omitia a decisao, chave ilegivel afirmava `false`.
    # Constante e laco tem fixture propria porque um constant folding hipotetico
    # resolveria a primeira e nunca resolveria a segunda.
    "conf_chave_por_constante",
    "conf_chave_por_laco",
    # Literal que EXISTE e nao converte para booleano: o rotulo do ponto cego
    # mandava procurar uma variavel que nao ha.
    "conf_local_checkpoints_nao_booleano",
    # DOIS sujeitos defeituosos no mesmo arquivo, que e o unico corpus capaz de
    # reprovar a remocao do `same_subject` de SF-GRAPH-003 e de SF-GRAPH-004.
    "dois_grafos_no_mesmo_arquivo",
    # O PAR do vocabulario de dois niveis, e ele so prova junto.
    "nomes_comuns_sem_import",
    "nomes_comuns_com_import",
    # O Pregel, que e `@property` e exigiu travessia para fora da cadeia.
    "pregel_como_propriedade",
    # Os dois eixos que sobram do fact de construcao.
    "arestas_nao_persistidas",
    "graphframe_em_laco",
    # A maquinaria de ponto cego, que e a que apodrece em silencio.
    "import_dinamico",
    "fonte_que_nao_compila",
    # O PAR da disponibilidade: mesmo `.py`, mesmo runtime sem jar, e a unica
    # diferenca e o `--extra-jars` no IaC.
    "import_sem_jar_no_iac",
    "import_com_jar_declarado",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def run_fixture(directory: Path):
    """A MESMA derivacao de `scripts/regen_fixtures.py::regen_graph`.

    Inclusive a escolha de `extract_graph_tree` em vez de um laco por arquivo:
    ver `test_the_tree_order_is_the_one_the_product_emits`, que e o teste que
    torna a diferenca visivel em vez de deixa-la como convencao.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = list(extract_graph_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _facts_of(name: str):
    _, facts, _, _ = run_fixture(FIXTURES / name)
    return facts


def _only(name: str, kind: str):
    facts = _by_kind(_facts_of(name), kind)
    assert len(facts) == 1, [f.attrs for f in facts]
    return facts[0]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = extract_graph_tree(directory / "input", repo_root=directory / "input")
        second = extract_graph_tree(directory / "input", repo_root=directory / "input")
        assert [f.to_dict() for f in first] == [f.to_dict() for f in second]

    def test_module_analyzed_counts_agree_with_the_emitted_facts(self, directory):
        """A sumarizacao nao pode divergir dos facts que ela resume, POR ARQUIVO.

        `unresolved_count` e a medida que um agente le para saber quanto do
        arquivo o extrator NAO enxergou. Se ela deixar de bater, o ponto cego
        passa a ser subnotificado -- e subnotificar ponto cego e indistinguivel
        de nao ter nenhum.

        Por arquivo e nao no agregado: `fonte_que_nao_compila` tem um `.py` que
        nao produz sentinela nenhuma, e uma soma global esconderia justamente o
        arquivo que ficou de fora da contagem.
        """
        _, facts, _, _ = run_fixture(directory)
        graph_facts = [f for f in facts if f.kind.startswith("graph.")]
        modules = _by_kind(graph_facts, "graph.module_analyzed")
        assert modules, "todo corpus deste dominio tem ao menos um `.py` que compila"
        for module in modules:
            arquivo = module.subject["file"]
            do_arquivo = [f for f in graph_facts if f.subject["file"] == arquivo]
            for kind, chave in (
                ("graph.import", "import_count"),
                ("graph.construction", "construction_count"),
                ("graph.algorithm", "algorithm_count"),
                ("graph.unresolved", "unresolved_count"),
            ):
                assert module.measures[chave] == len(_by_kind(do_arquivo, kind)), (
                    f"{arquivo}: {chave} diverge dos facts `{kind}` do mesmo arquivo"
                )

    def test_every_fact_id_is_unique(self, directory):
        """`Fact.id` e sha de kind + subject + measures, e deixa `attrs` de FORA.

        Dois facts com id igual fazem o `fact_id` que um Finding cita deixar de
        identificar evidencia -- o achado passa a apontar para "um dos dois". O
        risco e concreto neste extrator: `graph.unresolved` nao tem measures, e
        dois deles sobre o mesmo no sairiam identicos. E por isso que o extrator
        emite no maximo UM ponto cego por chamada.
        """
        _, facts, _, _ = run_fixture(directory)
        ids = [f.id for f in facts]
        assert len(ids) == len(set(ids))


class TestAdversarial:
    """Cada fixture prova o que o nome dela diz -- conferido, nunca presumido.

    O golden prova que a saida nao mudou; ele nao prova que a saida esta certa.
    Uma fixture chamada `saida_graphx` cujo fact saisse com
    `checkpoint_required: true` continuaria com golden verde, e a Task 5
    escreveria a regra P0 contra um corpus que nao a exercita.
    """

    # ---------------------------------------------------------------- sentinela
    def test_sem_grafo_still_emits_the_sentinel_zeroed(self):
        """"Nao ha grafo aqui" e "nao rodei aqui" precisam ser saidas diferentes."""
        facts = _facts_of("sem_grafo")
        assert [f.kind for f in facts] == ["graph.module_analyzed"]
        assert facts[0].measures == {
            "import_count": 0,
            "construction_count": 0,
            "algorithm_count": 0,
            "unresolved_count": 0,
        }
        assert facts[0].attrs == {"parsed": True}

    def test_grafo_correto_is_clean_on_every_axis(self):
        """A metade negativa, e ela e a que impede a regra de nascer larga."""
        construcoes = _by_kind(_facts_of("grafo_correto"), "graph.construction")
        assert len(construcoes) == 2
        for construcao in construcoes:
            assert construcao.attrs["vertices_persisted"] is True
            assert construcao.attrs["edges_persisted"] is True
            assert construcao.attrs["inside_loop"] is False
        componentes = next(
            f
            for f in _by_kind(_facts_of("grafo_correto"), "graph.algorithm")
            if f.attrs["name"] == "connectedComponents"
        )
        assert componentes.attrs["checkpoint_required"] is True
        assert componentes.attrs["checkpoint_configured_in_module"] is True

    def test_the_persist_evidence_survives_the_assignment_form(self):
        """`v = vertices.cache()` persiste OS DOIS nomes (D-6a-14).

        E a forma mais comum de persistir em job real. Contar so a raiz da
        cadeia faria `GraphFrame(v, e)` sair com `vertices_persisted: false` --
        acusacao falsa sobre codigo correto, e nao subnotificacao.
        """
        construcao = _by_kind(_facts_of("grafo_correto"), "graph.construction")[0]
        assert construcao.attrs["vertices_ref"] == "v"
        assert construcao.attrs["vertices_persisted"] is True

    def test_the_checkpoint_reaches_the_call_from_another_function(self):
        """Alcance de ARQUIVO, e o argumento e o objeto (D-6a-13).

        `setCheckpointDir` esta em `build_spark()` e o algoritmo em
        `componentes()`. `SparkContext` e singleton do processo: correlacionar
        por escopo produziria P0 sobre a forma canonica de job Glue/EMR.
        """
        checkpoint = _only("grafo_correto", "graph.checkpoint_dir")
        componentes = next(
            f
            for f in _by_kind(_facts_of("grafo_correto"), "graph.algorithm")
            if f.attrs["name"] == "connectedComponents"
        )
        assert checkpoint.attrs["form"] == "set_checkpoint_dir"
        assert checkpoint.measures["line"] < componentes.measures["line"]
        assert componentes.attrs["checkpoint_configured_in_module"] is True

    # ------------------------------------------------------ exigencia e saidas
    def test_the_positive_is_required_and_unconfigured(self):
        algoritmo = _only("connected_components_sem_checkpoint", "graph.algorithm")
        assert algoritmo.attrs["name"] == "connectedComponents"
        assert algoritmo.attrs["checkpoint_required"] is True
        assert algoritmo.attrs["checkpoint_configured_in_module"] is False
        # O resto da fixture e correto: um unico eixo defeituoso.
        construcao = _only("connected_components_sem_checkpoint", "graph.construction")
        assert construcao.attrs["vertices_persisted"] is True
        assert construcao.attrs["edges_persisted"] is True
        assert construcao.attrs["inside_loop"] is False

    @pytest.mark.parametrize(
        ("fixture", "chave", "valor"),
        [
            ("saida_graphx", "algorithm_arg", "graphx"),
            ("saida_local_checkpoints", "use_local_checkpoints", True),
        ],
    )
    def test_the_declared_exits_turn_the_requirement_off(self, fixture, chave, valor):
        """Duas das quatro formas de escrever certo, lidas do argumento.

        As duas mantem `checkpoint_configured_in_module: false` -- nao ha
        diretorio nenhum no arquivo --, e e isso que prova que a diferenca com a
        fixture positiva veio do ARGUMENTO e nao da configuracao.
        """
        algoritmo = _only(fixture, "graph.algorithm")
        assert algoritmo.attrs[chave] == valor
        assert algoritmo.attrs["checkpoint_required"] is False
        assert algoritmo.attrs["checkpoint_configured_in_module"] is False

    def test_a_non_positive_interval_is_read_with_its_sign(self):
        """`-1` e `UnaryOp(USub, Constant)` na arvore, nao constante negativa.

        Um `_literal` que nao desembrulhe o unario devolve `None`, a saida cai
        em ilegivel, e a forma legitima vira ponto cego -- silencio no lugar de
        evidencia.
        """
        algoritmo = _only("saida_intervalo_nao_positivo", "graph.algorithm")
        assert algoritmo.measures["checkpoint_interval"] == -1
        assert algoritmo.attrs["checkpoint_required"] is False

    @pytest.mark.parametrize(
        ("fixture", "form"),
        [
            ("conf_checkpoint_dir_no_job", "conf_checkpoint_dir"),
            ("conf_local_checkpoints_no_job", "conf_local_checkpoints"),
        ],
    )
    def test_the_conf_inside_the_job_satisfies_the_requirement(self, fixture, form):
        """A quarta saida as vezes ESTA no `.py` (D-6a-12).

        Tratar `spark.conf.set(...)` como sempre externa faria a regra P0
        disparar sobre codigo que configurou o checkpoint na linha de cima.
        `checkpoint_required` continua `true` -- a exigencia se aplica --, e o
        que muda e a outra metade da pergunta.
        """
        checkpoint = _only(fixture, "graph.checkpoint_dir")
        assert checkpoint.attrs["form"] == form
        algoritmo = _only(fixture, "graph.algorithm")
        assert algoritmo.attrs["checkpoint_required"] is True
        assert algoritmo.attrs["checkpoint_configured_in_module"] is True

    def test_the_string_true_of_a_spark_conf_is_read_as_true(self):
        """Valor de conf do Spark e STRING. `bool("false")` seria `True`."""
        checkpoint = _only("conf_local_checkpoints_no_job", "graph.checkpoint_dir")
        assert checkpoint.attrs["enabled"] is True

    def test_an_unreadable_conf_silences_the_decision_of_the_whole_file(self):
        """Ignorancia OMITE a chave, e o ponto cego sai contado.

        A chave ausente e o que o motor nao consegue exprimir por regra
        (`_where_matches` reprova caminho ausente), e e exatamente por isso que
        ela e o lado seguro: nenhuma regra dispara sobre o que nao esta la.
        """
        algoritmo = _only("conf_local_checkpoints_ilegivel", "graph.algorithm")
        assert "checkpoint_required" not in algoritmo.attrs
        assert "checkpoint_configured_in_module" not in algoritmo.attrs
        cego = _only("conf_local_checkpoints_ilegivel", "graph.unresolved")
        assert cego.attrs["reason"] == "non_literal_argument"
        assert cego.attrs["param"] == "spark.graphframes.useLocalCheckpoints"

    def test_three_blind_spots_one_per_call_and_no_accusation(self):
        """Um `graph.unresolved` por chamada, com argumento antes de receptor."""
        facts = _facts_of("exigencia_indecidivel")
        cegos = _by_kind(facts, "graph.unresolved")
        assert [c.attrs["reason"] for c in sorted(cegos, key=lambda f: f.subject["line"])] == [
            "positional_argument",
            "non_literal_argument",
            "receiver_without_name",
        ]
        for algoritmo in _by_kind(facts, "graph.algorithm"):
            assert "checkpoint_required" not in algoritmo.attrs
        # O receptor anonimo nao vira nome inventado: sem nome, sem chave.
        algoritmos = _by_kind(facts, "graph.algorithm")
        anonimo = next(f for f in algoritmos if f.attrs["name"] == "pageRank")
        assert "receiver" not in anonimo.attrs

    # ---------------------------------------------- vocabulario de dois niveis
    def test_the_common_names_stay_silent_without_the_import(self):
        """`"abc".find("b")` NAO e um motif finder de grafo.

        Sem esta fixture, alguem "simplifica" o vocabulario de dois niveis para
        um `frozenset` unico, a suite continua verde, e o motor passa a acusar
        grafo em todo modulo que manipula string -- acusacao falsa, que e o pior
        modo de falha desta area.
        """
        facts = _facts_of("nomes_comuns_sem_import")
        assert _by_kind(facts, "graph.algorithm") == []
        assert _only("nomes_comuns_sem_import", "graph.module_analyzed").measures[
            "algorithm_count"
        ] == 0

    def test_the_same_names_count_once_the_module_imports_graphframes(self):
        """A outra metade do par: um portao que nunca abre e letra morta."""
        facts = _facts_of("nomes_comuns_com_import")
        nomes = sorted(f.attrs["name"] for f in _by_kind(facts, "graph.algorithm"))
        assert nomes == ["degrees", "find", "validate"]
        assert _only("nomes_comuns_com_import", "graph.import").attrs["form"] == "plain"

    def test_the_pair_differs_only_in_the_import_line(self):
        """O par so isola o portao se o resto dos dois arquivos for identico."""
        sem = (FIXTURES / "nomes_comuns_sem_import" / "input" / "job.py").read_text(
            encoding="utf-8"
        ).splitlines()
        com = (FIXTURES / "nomes_comuns_com_import" / "input" / "job.py").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(com) == len(sem) + 1
        assert [linha for linha in com if linha not in sem] == ["import graphframes"]

    def test_cache_and_persist_are_not_algorithms_here(self):
        """A fronteira com `SF-PY-008`, medida sobre o corpus inteiro (D-6a-11).

        `cache`, `persist` e `unpersist` existem na API do `GraphFrame`, e
        `pyspark.cache` ja os emite sobre o MESMO artefato. Reemiti-los aqui
        duplicaria o sujeito da regra vizinha e apagaria justamente a fronteira
        que a Task 6 tem de provar. Eles entram so como evidencia de
        persistencia -- e ha `cache()` em quase toda fixture deste corpus.
        """
        proibidos = {"cache", "persist", "unpersist"}
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            nomes = {f.attrs["name"] for f in _by_kind(facts, "graph.algorithm")}
            assert not (nomes & proibidos), f"{directory.name}: {sorted(nomes & proibidos)}"

    def test_no_fact_claims_a_missing_iteration_limit(self):
        """A regra de `maxIter` foi VETADA, e o veto se prova na forma do fact.

        V-GF-2 e V-GF-3: em nenhum dos dezesseis algoritmos com nocao de
        iteracao "ausente" e defeito -- em seis e `TypeError`, em tres e default
        documentado, em `pageRank` e o modo `tol` oficial, e em
        `connectedComponents` a doc recomenda NAO mexer. Um booleano de ausencia
        de limite seria a regra vetada entrando pela porta dos fundos: bastaria
        alguem escrever `where: {attrs.has_max_iter: false}`.
        """
        proibidos = {
            "has_max_iter",
            "max_iter_missing",
            "iteration_limited",
            "unbounded",
            "has_iteration_limit",
        }
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            for fact in facts:
                assert not (proibidos & set(fact.attrs)), f"{directory.name}: {fact.attrs}"

    def test_tol_is_observed_and_named_never_judged(self):
        """Quem passou `tol` escreveu certo, e o fact diz QUAL limite veio.

        Sem `iteration_arg` nomeando o parametro, uma regra sobre "limite de
        iteracao" nao teria como distinguir `maxIter` de `tol` e acusaria o modo
        oficial e recomendado do `pageRank`.
        """
        page_rank = next(
            f
            for f in _by_kind(_facts_of("grafo_correto"), "graph.algorithm")
            if f.attrs["name"] == "pageRank"
        )
        assert page_rank.attrs["iteration_arg"] == "tol"
        assert page_rank.measures["iteration_literal"] == 0.01
        assert "checkpoint_required" not in page_rank.attrs

    # -------------------------------------------------------------- o Pregel
    def test_pregel_comes_out_as_a_property_with_its_iteration_limit(self):
        """`@property` nas duas linhagens (D-6a-3, D-6a-10).

        Um vocabulario casado so contra `ast.Call` nao emitiria fact nenhum
        aqui, e o Pregel e o unico algoritmo cujo limite de iteracao o usuario
        controla de fato. `setMaxIter(10)` so e recuperado porque a cadeia e
        percorrida para FORA a partir de `g.pregel` -- travessia que nenhum
        outro extrator do repositorio faz.
        """
        pregel = _only("pregel_como_propriedade", "graph.algorithm")
        assert pregel.attrs["name"] == "pregel"
        assert pregel.attrs["form"] == "property"
        assert pregel.attrs["receiver"] == "g"
        assert pregel.attrs["iteration_arg"] == "setMaxIter"
        assert pregel.measures["iteration_literal"] == 10

    def test_a_parameter_source_omits_the_persistence_key(self):
        """Subnotificacao declarada, e NUNCA `false`.

        Vertices e arestas chegam por parametro: a historia comecou fora deste
        escopo. `false` acusaria quem persistiu no chamador, e a regra de
        persistencia dispara sobre `false`.
        """
        construcao = _only("pregel_como_propriedade", "graph.construction")
        assert construcao.attrs["vertices_ref"] == "vertices"
        assert "vertices_persisted" not in construcao.attrs
        assert "edges_persisted" not in construcao.attrs

    def test_a_submodule_import_counts_as_the_package(self):
        importados = _by_kind(_facts_of("pregel_como_propriedade"), "graph.import")
        modulos = sorted(f.attrs["module"] for f in importados)
        assert modulos == ["graphframes", "graphframes.lib"]

    # ------------------------------------------ os dois eixos da construcao
    def test_only_the_edges_are_unpersisted(self):
        """Um eixo defeituoso, e a persistencia mora no fact da CONSTRUCAO.

        Um `graph.source_persisted` separado teria de ser reunido por nome de
        variavel, que e a correlacao que `D-5d-17` mostrou casar objeto errado
        quando ha varios grafos no mesmo diretorio.
        """
        construcao = _only("arestas_nao_persistidas", "graph.construction")
        assert construcao.attrs["vertices_persisted"] is True
        assert construcao.attrs["edges_persisted"] is False
        algoritmo = _only("arestas_nao_persistidas", "graph.algorithm")
        assert algoritmo.attrs["checkpoint_configured_in_module"] is True

    def test_the_loop_marks_both_the_construction_and_the_algorithm(self):
        facts = _facts_of("graphframe_em_laco")
        assert _only("graphframe_em_laco", "graph.construction").attrs["inside_loop"] is True
        assert _only("graphframe_em_laco", "graph.algorithm").attrs["inside_loop"] is True
        # E o unico lugar do corpus onde o import nao esta no topo do modulo.
        importado = _by_kind(facts, "graph.import")[0]
        assert importado.attrs["scope"] == "function"
        assert importado.attrs["guarded"] is True
        assert importado.attrs["alias"] == "GF"
        assert _only("graphframe_em_laco", "graph.construction").attrs["constructor"] == "GF"

    # ------------------------------------------------------------ ponto cego
    def test_a_dynamic_import_is_counted_and_never_guessed(self):
        """`unresolved_count: 2` com `import_count: 0` e a assinatura que separa
        "nao ha grafo" de "nao consegui ver o grafo"."""
        facts = _facts_of("import_dinamico")
        cegos = _by_kind(facts, "graph.unresolved")
        assert {c.attrs["reason"] for c in cegos} == {"dynamic_import"}
        assert sorted(c.attrs["detail"] for c in cegos) == ["", "graphframes"]
        assert _by_kind(facts, "graph.import") == []
        assert _by_kind(facts, "graph.construction") == []
        sentinela = _only("import_dinamico", "graph.module_analyzed")
        assert sentinela.measures["unresolved_count"] == 2
        assert sentinela.measures["import_count"] == 0

    def test_a_file_that_does_not_compile_has_no_sentinel_and_stops_nothing(self):
        """A unica saida daquele arquivo e o ponto cego, e a varredura segue.

        A MENSAGEM do `SyntaxError` entra no golden, entao ela e contrato com o
        interpretador. Medida identica em CPython 3.10.20, 3.11.15 e 3.14.6 --
        `'(' was never closed`, linha 5, coluna 16 --, e as duas primeiras sao
        as versoes da matriz do CI. Se um interpretador futuro reescrever a
        frase, e aqui que aparece, com o nome certo, em vez de virar diff mudo
        no golden.
        """
        facts = _facts_of("fonte_que_nao_compila")
        cego = _only("fonte_que_nao_compila", "graph.unresolved")
        assert cego.subject["file"] == "carga_quebrada.py"
        assert cego.attrs["reason"] == "syntax_error"
        assert cego.attrs["detail"] == "'(' was never closed"
        analisados = {f.subject["file"] for f in _by_kind(facts, "graph.module_analyzed")}
        assert analisados == {"job.py"}, "arquivo que nao compila nao produz sentinela"
        assert _by_kind(facts, "graph.algorithm"), "o `.py` seguinte saiu completo"

    def test_the_tree_order_is_the_one_the_product_emits(self):
        """O regenerador usa `extract_graph_tree`, e a diferenca e MEDIDA.

        `adapters/_core.py` chama `extract_graph_tree` quando o `--path` e
        diretorio, e ela ordena GLOBALMENTE por (kind, subject, id), intercalando
        os arquivos. Um laco por arquivo concatena blocos ja ordenados e produz
        uma ordem que nenhuma superficie do produto emite (D-5d-24). Com um `.py`
        so as duas coincidem -- por isso o teste roda sobre a unica fixture com
        dois, e por isso ela precisa existir.
        """
        input_dir = FIXTURES / "fonte_que_nao_compila" / "input"
        arvore = [f.to_dict() for f in extract_graph_tree(input_dir, repo_root=input_dir)]
        laco = []
        for py_file in sorted(input_dir.rglob("*.py")):
            laco.extend(f.to_dict() for f in extract_graph_path(py_file, repo_root=input_dir))
        assert arvore != laco, "as duas ordens coincidiram: a fixture parou de ter dois `.py`"
        assert sorted(map(json.dumps, arvore)) == sorted(map(json.dumps, laco)), (
            "a diferenca entre as duas formas tem de ser SO de ordem"
        )
        golden = json.loads(
            (FIXTURES / "fonte_que_nao_compila" / "expected" / "facts.json").read_text(
                encoding="utf-8"
            )
        )
        assert golden == arvore

    # ------------------------------------------------- a disponibilidade
    def test_the_availability_pair_differs_only_in_the_declared_jar(self):
        """O par so prova junto, e o `.py` dos dois e o mesmo arquivo.

        Sem o lado que declara o jar, a regra da Task 5 acusaria todo job de
        grafo em Spark 3.3 -- inclusive quem resolveu o problema --, e o golden
        do lado positivo sozinho nao perceberia.
        """
        sem = FIXTURES / "import_sem_jar_no_iac"
        com = FIXTURES / "import_com_jar_declarado"
        assert (sem / "input" / "job.py").read_text(encoding="utf-8") == (
            com / "input" / "job.py"
        ).read_text(encoding="utf-8")
        argumentos = {}
        for fixture in (sem, com):
            _, facts, _, _ = run_fixture(fixture)
            argumentos[fixture.name] = {
                f.attrs.get("key")
                for f in facts
                if f.kind == "tf.attribute" and f.attrs.get("block") == "default_arguments"
            }
        so_no_declarado = argumentos[com.name] - argumentos[sem.name]
        assert "--extra-jars" in so_no_declarado

    def test_the_availability_fixtures_declare_the_runtime_without_a_jar(self):
        """Spark 3.3.x e o discriminador, e nao a release (D-6a-6).

        Nenhuma linhagem publicou artefato para Spark 3.3: `0.8.2` para em 3.2,
        `0.8.3` comeca em 3.4, `io.graphframes` compila contra 3.5. Uma fixture
        em Glue 5.0 nao poderia exercitar a regra, e o `runtime_scope` da Task 5
        tem de ser escrito por Spark para cobrir as nove celulas de uma vez.
        """
        for nome in ("import_sem_jar_no_iac", "import_com_jar_declarado"):
            meta, facts, _, _ = run_fixture(FIXTURES / nome)
            assert meta["runtime"]["spark"] == "3.3.0"
            assert meta["runtime"]["glue"] == "4.0"
            assert _by_kind(facts, "graph.import"), "sem import nao ha o que a regra afirme"

    # ------------------------------------------------------------- invariantes
    def test_the_corpus_covers_every_kind_the_extractor_emits(self):
        """Recorte local do invariante global de `test_fixtures_kind_coverage`.

        Aqui a falha aponta para a fixture que falta neste corpus, em vez de
        para "algum golden do repositorio inteiro".
        """
        covered = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            covered.update(f.kind for f in facts)
        assert set(EMITTED_KINDS) - covered == set()

    def test_the_corpus_exercises_every_unresolved_reason_it_can(self):
        """As razoes de ponto cego que dependem do `.py`, todas exercitadas.

        `read_error` fica de fora e a razao e declarada: ele exige um arquivo
        ilegivel pelo SISTEMA DE ARQUIVOS (permissao, encoding invalido), que
        nao se versiona em corpus de forma portavel entre Windows e Linux --
        `tests/test_facts_graph.py` o cobre por unidade.
        """
        razoes = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            razoes.update(f.attrs["reason"] for f in _by_kind(facts, "graph.unresolved"))
        assert razoes == {
            "dynamic_import",
            "non_literal_argument",
            "non_boolean_value",
            "unreadable_conf_key",
            "positional_argument",
            "receiver_without_name",
            "syntax_error",
        }

    def test_only_sf_graph_rules_fire_over_this_corpus(self):
        """Ate a Task 5 este teste exigia golden VAZIO em todas as fixtures.

        Com a area `SF-GRAPH` escrita, a metade que continua valendo e a que
        importava: nenhuma regra de OUTRA area pode disparar sobre facts de
        grafo. O diff aparece aqui antes de a fronteira da Task 6 existir, e
        continua aparecendo depois -- ela mede as tres direcoes entre corpora,
        esta mede o corpus proprio.
        """
        for directory in fixture_dirs():
            _, _, findings, _ = run_fixture(directory)
            intrusos = sorted(
                {f.rule_id for f in findings if not f.rule_id.startswith("SF-GRAPH-")}
            )
            assert not intrusos, f"{directory.name}: {intrusos}"

    def test_the_seven_correct_forms_stay_silent(self):
        """As sete saidas legitimas da exigencia de checkpoint, nomeadas.

        Elas sao o corpus que separa uma regra que le o ARGUMENTO de uma que so
        percebe a ausencia do diretorio. Vermelho aqui significa que a area
        passou a acusar quem escreveu certo -- e o nome da fixture diz qual das
        sete formas foi acusada, em vez de um diff mudo em sete goldens.

        Eram cinco ate a revisao da Fase 6a. As duas ultimas -- a conf declarada
        no builder e a conf declarada por keyword -- ja eram formas correntes de
        escrever certo naquela altura, e o extrator as acusava com P0.
        """
        for nome in (
            "saida_graphx",
            "saida_intervalo_nao_positivo",
            "saida_local_checkpoints",
            "conf_checkpoint_dir_no_job",
            "conf_local_checkpoints_no_job",
            "checkpoint_por_builder_config",
            "conf_chave_por_keyword",
        ):
            meta, _, findings, _ = run_fixture(FIXTURES / nome)
            assert meta["expects_rules"] == [], nome
            assert findings == [], f"{nome}: {[f.rule_id for f in findings]}"
