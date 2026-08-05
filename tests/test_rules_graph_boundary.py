"""A fronteira entre SF-GRAPH, SF-DQ e SF-PY, medida sobre o MESMO artefato.

Esta e a fronteira mais apertada do repositorio, e a razao e o artefato. Na Fase
5d, `SF-EMR` e `SF-EMRS` liam JSONs diferentes -- `describe-cluster` e
`get-application` --, entao a porta natural de cada corpus ja separava as duas
areas antes de qualquer regra. Aqui as tres areas leem o **mesmo `.py`**:
`pyspark_ast.py`, `data_quality.py` e `graph.py` varrem o mesmo arquivo, cada um
com o seu vocabulario, e as tres sentinelas de modulo saem juntas em todo
`.py` que compila -- medido em `test_os_tres_extratores_leem_o_mesmo_arquivo`.
Nenhum recorte de artefato separa as areas aqui. So a construcao das regras.

**A porta deste arquivo e a uniao dos tres extratores, e nao a de nenhum
golden.** `tests/test_fixtures_golden_graph.py` extrai `graph.*` (mais os `tf.*`
das duas fixtures de IaC) e nada mais, porque um golden com facts de
`pyspark_ast` sobre o mesmo `.py` quebraria duas vezes pelo mesmo motivo. Isso
torna o `expects_rules: []` de catorze fixtures de grafo uma afirmacao sobre
facts de GRAFO -- nunca sobre o arquivo. A fronteira entre areas so existe onde
os facts das duas convivem, entao aqui os tres extratores rodam sobre os tres
corpora, que e o que um agente faz numa investigacao real de job de grafo:
`analyze pyspark` e `analyze graph` sobre o mesmo `src/`.

**Tres armadilhas decidem se este arquivo mede alguma coisa.**

1. `rule["area"]` nao existe. O `load_catalog` propaga `catalog_version` e
   `_source_file`, nunca o `area:` do cabecalho -- medido na Fase 5d. O
   mecanismo que le o documento e casa por `_source_file` esta em
   `test_rules_emrs_boundary.py` e e **importado**, nao reescrito: uma fronteira
   nova nao e razao para um segundo jeito de responder "de que area e esta
   regra".

2. Verde por skip, e aqui ele e real e nao hipotetico. `SF-GRAPH-002` declara
   `runtime_scope: {spark: [">=3.3", "<3.4"]}` (D-6a-29), e os corpora de `dq/` e
   `pyspark/` declaram Spark 3.5.4: sob o runtime das proprias fixtures essa
   regra e **calada por escopo em todas as trinta**, e um teste que so olhasse
   `findings` a daria por inocente sem que ela tivesse chegado perto de um fact.
   Por isso a direcao `SF-GRAPH` -> vizinhos e julgada **duas vezes**: sob o
   runtime declarado, que e o que o produto faz, e sob o runtime da faixa
   (Spark 3.3.0, lido de `fixtures/graph/import_sem_jar_no_iac/meta.yaml`), onde
   as quatro regras estao em escopo e o silencio so pode vir de `requires_facts`.

3. Silencio por sentinela. As tres sentinelas de modulo estao presentes nos tres
   corpora, entao uma regra ancorada nelas seria AVALIADA sobre todo `.py` do
   repositorio, e a fronteira passaria a depender do `when` -- que e onde erro de
   regra mora. `test_toda_regra_exige_kind_proprio_que_nao_seja_a_sentinela` e o
   que faz a fronteira ser por construcao com o artefato compartilhado.

**SF-PY dispara sobre `fixtures/graph/`, e isso NAO e invasao.** Sao dezesseis
achados: `SF-PY-008` em catorze fixtures e `SF-PY-012` em duas. Cada um cita
`pyspark.cache` ou `pyspark.conf_set` -- nunca um `graph.*` --, e o `subject` de
cada um aponta para uma linha que existe no arquivo e que e literalmente um
`.cache()` ou um `spark.conf.set(...)`. As dezenove fixtures de grafo persistem
vertices e arestas e **nenhuma** chama `unpersist`, porque o eixo delas e grafo e
nao ciclo de vida de cache; `SF-PY-008` esta certa sobre elas. E a construcao
funcionando, e nao apesar dela: `V-GR-4` deixou `cache`/`persist`/`unpersist`
fora do vocabulario de `graph.algorithm` justamente porque `pyspark.cache` ja os
emite, e a explicacao de `SF-GRAPH-003` declara a fronteira com `SF-PY-008` por
escrito. `TestOQuePYDizSobreOCorpusDeGrafo` lista os dezesseis um a um: nenhum e
silenciado, e um decimo setimo obriga alguem a repetir o argumento.

O caso que mais parece defeito e o que melhor mostra a diferenca:
`grafo_correto`, o negativo de referencia da area, e acusado por `SF-PY-008` na
linha 28. Ele e correto **como job de grafo** -- e o `expects_rules: []` do
golden diz exatamente isso, sobre facts de grafo. Como exemplo de ciclo de vida
de cache ele nao e correto, e nenhuma das duas areas mente ao dizer a sua
metade.
"""
from __future__ import annotations

from functools import cache, lru_cache
from pathlib import Path

import pytest
import yaml
from test_rules_emrs_boundary import (
    _area_declarada,
    _area_do_id,
    _kinds_lidos,
    _regras_da_area,
)

from sparkforge.facts.data_quality import extract_data_quality_tree
from sparkforge.facts.graph import extract_graph_tree
from sparkforge.facts.pyspark_ast import extract_tree as extract_pyspark_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]

GRAFO = "SF-GRAPH"
DQ = "SF-DQ"
PY = "SF-PY"
AREAS = (GRAFO, DQ, PY)

# O namespace de fact de cada area. Ler o do vizinho e a unica forma de um achado
# citar evidencia que descreve outra coisa -- e com o artefato compartilhado essa
# e a unica forma que sobra.
NAMESPACE = {GRAFO: "graph.", DQ: "dq.", PY: "pyspark."}

# A sentinela de cada extrator: emitida por `.py` que compila, em TODO corpus.
# Ela prova que o arquivo foi varrido, nunca que ha algo daquela area nele.
SENTINELA = {
    GRAFO: "graph.module_analyzed",
    DQ: "dq.module_analyzed",
    PY: "pyspark.module_analyzed",
}

CORPUS = {
    GRAFO: ROOT / "fixtures" / "graph",
    DQ: ROOT / "fixtures" / "dq",
    PY: ROOT / "fixtures" / "pyspark",
}

# O runtime que poe `SF-GRAPH-002` em escopo, LIDO do corpus em vez de escrito
# aqui: se a faixa da regra mudar, a fixture que a exercita muda junto e este
# valor a acompanha.
FIXTURE_NA_FAIXA = CORPUS[GRAFO] / "import_sem_jar_no_iac"

# Os vinte e dois achados de SF-PY sobre o corpus de grafo, nomeados. Nao e
# supressao: `TestOQuePYDizSobreOCorpusDeGrafo` mede, para cada um, que a
# evidencia e `pyspark.*` e que o `subject` aponta para uma linha real do
# arquivo. Um achado a mais aqui nao e bug automatico -- e uma pergunta que
# alguem precisa responder por escrito antes de acrescentar a linha.
ESPERADO_PY_SOBRE_GRAFO = {
    # `.cache()` sem `unpersist`: verdadeiro em todas as vinte, e o eixo destas
    # fixtures e grafo, nao ciclo de vida de cache.
    "arestas_nao_persistidas": ("SF-PY-008",),
    # As seis fixtures da revisao da Fase 6a. Todas persistem vertices e arestas
    # com `.cache()` e nenhuma libera -- pelo mesmo motivo das doze acima: o eixo
    # em teste e a conf de checkpoint, ou a contagem de sujeitos, e escrever
    # `unpersist` nelas so trocaria o ruido de lugar.
    "checkpoint_por_builder_config": ("SF-PY-008",),
    "conf_chave_por_constante": ("SF-PY-008",),
    "conf_chave_por_keyword": ("SF-PY-008",),
    "conf_chave_por_laco": ("SF-PY-008",),
    "conf_local_checkpoints_ilegivel": ("SF-PY-008",),
    "connected_components_sem_checkpoint": ("SF-PY-008",),
    "exigencia_indecidivel": ("SF-PY-008",),
    "fonte_que_nao_compila": ("SF-PY-008",),
    "grafo_correto": ("SF-PY-008",),
    "graphframe_em_laco": ("SF-PY-008",),
    "import_com_jar_declarado": ("SF-PY-008",),
    "import_sem_jar_no_iac": ("SF-PY-008",),
    "saida_graphx": ("SF-PY-008",),
    "saida_intervalo_nao_positivo": ("SF-PY-008",),
    "saida_local_checkpoints": ("SF-PY-008",),
    # As duas que configuram o checkpoint por `spark.conf.set` -- a quarta e a
    # quinta formas de escrever certo para SF-GRAPH-001 -- disparam TAMBEM
    # SF-PY-012 (P3): conf de runtime sobrescreve default argument do IaC em
    # silencio. As duas afirmacoes convivem sobre a mesma linha e nenhuma e sobre
    # grafo.
    "conf_checkpoint_dir_no_job": ("SF-PY-008", "SF-PY-012"),
    "conf_local_checkpoints_no_job": ("SF-PY-008", "SF-PY-012"),
    # A sexta da revisao cai no mesmo par: ela tambem chama `spark.conf.set`, com
    # um valor que SF-GRAPH nao consegue converter para booleano e que SF-PY nao
    # precisa converter para nada -- a afirmacao dele e sobre a conf sobrescrever
    # o default argument, e independe do valor.
    "conf_local_checkpoints_nao_booleano": ("SF-PY-008", "SF-PY-012"),
}

# As cinco de grafo em que SF-PY nao tem o que dizer, e a razao e a mesma da
# fronteira: nao ha `pyspark.cache` nem `pyspark.conf_set` nelas.
SILENCIOSAS_PARA_PY = (
    "import_dinamico",
    "nomes_comuns_com_import",
    "nomes_comuns_sem_import",
    "pregel_como_propriedade",
    "sem_grafo",
)


# ---------------------------------------------------------------------------
# Extracao: os tres extratores sobre o mesmo diretorio, que e o que separa esta
# fronteira da da Fase 5d.
# ---------------------------------------------------------------------------


def _dirs(raiz: Path) -> list[Path]:
    return sorted(p for p in raiz.iterdir() if p.is_dir())


@cache
def _facts(input_dir: Path) -> tuple:
    """Os tres extratores sobre o mesmo `.py`, na ordem em que um agente os
    chamaria: `analyze graph`, `analyze data-quality`, `analyze pyspark`.

    `lru_cache` porque cada corpus e julgado sob dois runtimes e a extracao e a
    parte cara; sem ele o arquivo faz o trabalho de AST duas vezes por fixture.
    """
    return (
        tuple(extract_graph_tree(input_dir, repo_root=input_dir))
        + tuple(extract_data_quality_tree(input_dir, repo_root=input_dir))
        + tuple(extract_pyspark_tree(input_dir, repo_root=input_dir))
    )


@lru_cache(maxsize=1)
def _catalogo() -> tuple[dict, ...]:
    """O catalogo inteiro, uma vez. `judge` recebe TODAS as regras de proposito:
    a fronteira e sobre o que o produto faz, e o produto nunca filtra o catalogo
    por area antes de julgar."""
    return tuple(load_catalog())


def _runtime(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))["runtime"]


def _julgar(directory: Path, runtime: dict | None = None) -> dict:
    declarado = _runtime(directory)
    usado = declarado if runtime is None else runtime
    facts = list(_facts(directory / "input"))
    findings, skipped = judge(facts, _catalogo(), usado, return_skipped=True)
    return {
        "nome": directory.name,
        "dir": directory,
        "runtime": usado,
        "declarado": declarado,
        "facts": facts,
        "findings": findings,
        "skipped": skipped,
    }


def _julgados(area: str, runtime: dict | None = None) -> list[dict]:
    return [_julgar(d, runtime) for d in _dirs(CORPUS[area])]


@pytest.fixture(scope="module")
def catalogo() -> list[dict]:
    return list(_catalogo())


@pytest.fixture(scope="module")
def sobre_grafo() -> list[dict]:
    return _julgados(GRAFO)


@pytest.fixture(scope="module")
def sobre_dq() -> list[dict]:
    return _julgados(DQ)


@pytest.fixture(scope="module")
def sobre_py() -> list[dict]:
    return _julgados(PY)


@pytest.fixture(scope="module")
def vizinhos_no_runtime_declarado(sobre_dq, sobre_py) -> list[dict]:
    return sobre_dq + sobre_py


@pytest.fixture(scope="module")
def vizinhos_na_faixa_de_spark() -> list[dict]:
    """Os dois corpora vizinhos julgados com o Spark que poe SF-GRAPH-002 em
    escopo. Sem esta passagem, a direcao `SF-GRAPH` -> vizinhos e verde por skip
    para uma das quatro regras."""
    faixa = _runtime(FIXTURE_NA_FAIXA)
    return _julgados(DQ, faixa) + _julgados(PY, faixa)


def _findings_da_area(julgados: list[dict], area: str) -> list[tuple]:
    return sorted(
        (j["nome"], f.rule_id, tuple(f.evidence))
        for j in julgados
        for f in j["findings"]
        if _area_do_id(f.rule_id) == area
    )


# ---------------------------------------------------------------------------


class TestComoAAreaEComparada:
    """O mecanismo, antes da medida -- e ele vem da Fase 5d inteiro.

    `test_rules_emrs_boundary.py` ja mede que o `loader` nao propaga `area:`, que
    todo documento a declara e que id e cabecalho concordam. Repetir aquelas tres
    asercoes aqui nao mediria nada de novo; o que este arquivo precisa afirmar e
    que o mecanismo importado responde certo para AS TRES areas desta fronteira.
    """

    def test_o_mecanismo_importado_recorta_as_tres_areas(self, catalogo):
        for area in AREAS:
            regras = _regras_da_area(catalogo, area)
            assert regras, (
                f"nenhuma regra na area {area} pelo recorte da Fase 5d (area do "
                f"documento E area do id). Ou a area sumiu do catalogo, ou o "
                f"mecanismo importado deixou de responder por ela -- e nos dois "
                f"casos toda medida deste arquivo passa a ser vacua."
            )

    def test_toda_regra_das_tres_areas_esta_no_documento_da_propria_area(self, catalogo):
        """O buraco que o recorte por DUAS leituras abre, fechado aqui.

        `_regras_da_area` exige que a area do documento e a area do id concordem
        -- e uma regra que discorde some das duas listas. Uma `SF-GRAPH-003`
        escrita dentro de `data-quality.yaml` nao entraria no recorte de
        `SF-GRAPH` nem no de `SF-DQ`, e TODA medida deste arquivo continuaria
        verde sobre uma regra que nenhuma delas olhou -- inclusive
        `test_cada_corpus_dispara_a_propria_area_inteira`, cuja lista de
        esperadas encolheria junto.

        Medido: com a regra movida, so `test_rules_emrs_boundary.py` reprovava,
        porque ele caminha o catalogo inteiro. Depender do arquivo do vizinho
        para nao ficar vacuo e a forma como este arquivo apodreceria em silencio.
        """
        divergentes = sorted(
            (r["id"], r["_source_file"], _area_declarada(r))
            for r in catalogo
            if _area_do_id(r["id"]) in AREAS and _area_declarada(r) != _area_do_id(r["id"])
        )
        assert not divergentes, (
            f"(id, documento, area declarada) = {divergentes}. Regra de uma das tres "
            f"areas desta fronteira escrita num documento que declara outra area: "
            f"ela sai do recorte dos dois lados e este arquivo inteiro passa a "
            f"medi-la em lugar nenhum."
        )

    def test_os_tres_prefixos_de_id_nao_colidem(self, catalogo):
        """A armadilha da 5d nao existe aqui, e isso e medido em vez de assumido.

        La `SF-EMR` era prefixo de `SF-EMRS`, e classificar por `startswith`
        entregava as quinze regras a area errada. `SF-GRAPH`, `SF-DQ` e `SF-PY`
        sao disjuntos, mas o dia em que uma area `SF-PYSPARK` nascer, este teste
        e que avisa -- em vez de a fronteira virar verde vacuo.
        """
        for area in AREAS:
            outras = [o for o in AREAS if o != area]
            colisoes = [o for o in outras if o.startswith(area) or area.startswith(o)]
            assert not colisoes, (
                f"{area} colide por prefixo com {colisoes}. O recorte por igualdade "
                f"exata continua correto, mas qualquer teste do repositorio que "
                f"classifique area por `startswith` passou a mentir."
            )


class TestOMesmoArtefatoLidoTresVezes:
    """O que torna esta fronteira mais apertada que a da Fase 5d."""

    def test_os_tres_namespaces_sao_disjuntos_por_prefixo(self):
        for area in AREAS:
            for outra in AREAS:
                if area is outra:
                    continue
                assert not NAMESPACE[area].startswith(NAMESPACE[outra])

    @pytest.mark.parametrize("corpus", AREAS)
    def test_os_tres_extratores_leem_o_mesmo_arquivo(self, corpus):
        """A medida que justifica o arquivo inteiro.

        Se cada corpus so produzisse facts da sua propria area, nao haveria
        fronteira a medir: o recorte do artefato ja separaria tudo, como separava
        na 5d. Aqui as tres sentinelas saem juntas em toda fixture dos tres
        corpora -- os tres extratores varreram o mesmo `.py` e os tres tiveram a
        chance de falar.
        """
        for directory in _dirs(CORPUS[corpus]):
            kinds = {f.kind for f in _facts(directory / "input")}
            faltando = sorted(s for s in SENTINELA.values() if s not in kinds)
            assert not faltando, (
                f"em `fixtures/{CORPUS[corpus].name}/{directory.name}` faltam as "
                f"sentinelas {faltando}. Ou um extrator deixou de ler o corpus do "
                f"vizinho -- e ai a fronteira volta a ser recorte de artefato, nao "
                f"construcao de regra --, ou o corpus deixou de ter `.py` que "
                f"compila."
            )


class TestNenhumaAreaLeONamespaceDaVizinha:
    """A fronteira no CATALOGO, antes de qualquer fixture."""

    @pytest.mark.parametrize("area", AREAS)
    def test_nenhuma_regra_le_kind_de_area_vizinha(self, catalogo, area):
        alheios = tuple(NAMESPACE[o] for o in AREAS if o != area)
        for regra in _regras_da_area(catalogo, area):
            invasores = sorted(k for k in _kinds_lidos(regra) if k.startswith(alheios))
            assert not invasores, (
                f"{regra['id']} le {invasores}, de fora do namespace `"
                f"{NAMESPACE[area]}`. As tres areas leem o mesmo `.py`, entao ler o "
                f"kind do vizinho nao e erro de artefato: e um achado que cita "
                f"evidencia sobre outra pergunta feita ao mesmo arquivo."
            )

    @pytest.mark.parametrize("area", AREAS)
    def test_toda_regra_exige_kind_proprio_que_nao_seja_a_sentinela(self, catalogo, area):
        """O que faz a fronteira ser por CONSTRUCAO com artefato compartilhado.

        `judge` pula regra cujo `requires_facts` nao esta presente -- e as tres
        sentinelas de modulo estao presentes nos TRES corpora. Uma regra ancorada
        so na sentinela da propria area seria avaliada sobre todo `.py` do
        repositorio, e o silencio dela passaria a depender do `when`.

        `SF-DQ-002` e o caso a olhar: ela exige `dq.module_analyzed` de proposito
        -- acusa suite de validacao sem consumo, e para isso precisa do modulo
        inteiro --, e o que a segura e a conjuncao com `dq.check`. Sobre as
        dezenove fixtures de grafo ela e calada por `requires_facts` por causa
        dessa segunda exigencia, nao da primeira.
        """
        proprio = NAMESPACE[area]
        sentinela = SENTINELA[area]
        for regra in _regras_da_area(catalogo, area):
            exigidos = set(regra.get("requires_facts") or [])
            ancoras = {k for k in exigidos if k.startswith(proprio) and k != sentinela}
            assert ancoras, (
                f"{regra['id']} exige {sorted(exigidos)}: nenhum kind `{proprio}*` "
                f"alem da sentinela `{sentinela}`. Como a sentinela sai em todo "
                f"`.py` que compila, esta regra passa a ser AVALIADA sobre os "
                f"corpora das outras duas areas, e a fronteira deixa de ser por "
                f"construcao."
            )


class TestOsTresCorporaEstaoVivos:
    """Sem isto, toda afirmacao de silencio seria verde sobre nada.

    Zero achado em todo lugar satisfaz "nenhuma regra da area vizinha disparou".
    Cada corpus precisa disparar a SUA area, inteira, antes de qualquer
    afirmacao sobre a de fora.
    """

    @pytest.mark.parametrize("area", AREAS)
    def test_cada_corpus_dispara_a_propria_area_inteira(
        self, catalogo, sobre_grafo, sobre_dq, sobre_py, area
    ):
        julgados = {GRAFO: sobre_grafo, DQ: sobre_dq, PY: sobre_py}[area]
        disparadas = {f.rule_id for j in julgados for f in j["findings"]}
        esperadas = {r["id"] for r in _regras_da_area(catalogo, area)}
        assert esperadas <= disparadas, (
            f"regras {sorted(esperadas - disparadas)} nao dispararam em nenhuma "
            f"fixture de `fixtures/{CORPUS[area].name}/`. Fronteira medida sobre "
            f"corpus mudo nao mede nada."
        )


class TestFronteiraSobreOCorpusDeGrafo:
    """Direcoes 2 e 3: SF-DQ e SF-PY sobre `fixtures/graph/`."""

    def test_nenhuma_regra_dq_dispara_sobre_o_corpus_de_grafo(self, sobre_grafo):
        invasoes = _findings_da_area(sobre_grafo, DQ)
        assert not invasoes, (
            f"regra de qualidade de dado disparou sobre job de grafo: {invasoes}. "
            f"O extrator de `dq` LE esses arquivos -- a sentinela `dq.module_analyzed` "
            f"sai nas dezenove --, entao o achado nao vem de artefato trocado: vem "
            f"de uma regra que chamou de validacao alguma coisa que e construcao de "
            f"grafo. `SF-DQ-003` e `SF-GRAPH-003` fazem a mesma pergunta sobre "
            f"sujeitos diferentes, e e exatamente ai que a confusao cabe."
        )

    def test_toda_regra_dq_e_calada_por_falta_de_fact(self, catalogo, sobre_grafo):
        """A afirmacao positiva: nao e que a regra nao disparou, e que ela foi
        alcancada e nao teve com que se sustentar."""
        vizinha = {r["id"] for r in _regras_da_area(catalogo, DQ)}
        for j in sobre_grafo:
            por_falta = {s["rule_id"] for s in j["skipped"] if s["reason"] == "requires_facts"}
            faltando = sorted(vizinha - por_falta)
            visto = [s for s in j["skipped"] if s["rule_id"] in vizinha]
            assert not faltando, (
                f"em `{j['nome']}`, as regras {faltando} de {DQ} nao foram puladas "
                f"por `requires_facts`. Ou foram avaliadas sobre facts de grafo, ou "
                f"foram caladas por outro motivo -- e escopo calando a vizinha "
                f"deixaria esta fronteira verde sem que ela existisse. Skips de {DQ} "
                f"nesta fixture: {visto}"
            )

    def test_nenhuma_regra_da_area_vizinha_e_calada_por_escopo(self, catalogo, sobre_grafo):
        """O guarda da 5d, na direcao em que ele ainda vale inteiro.

        `fixtures/graph/` roda em Glue 5.0 e em Glue 4.0, com Spark real
        declarado. Se alguma regra de `SF-DQ` ou `SF-PY` fosse calada ali por
        `runtime_scope` ou `blocked_on`, o silencio dela nao provaria fronteira
        nenhuma -- e voltaria a vermelho no dia em que o escopo mudasse, longe
        daqui.
        """
        vizinhas = {
            r["id"] for area in (DQ, PY) for r in _regras_da_area(catalogo, area)
        }
        culpados = sorted(
            (j["nome"], j["runtime"].get("spark"), s["rule_id"], s["reason"])
            for j in sobre_grafo
            for s in j["skipped"]
            if s["rule_id"] in vizinhas and s["reason"] in {"runtime_scope", "blocked_on"}
        )
        assert not culpados, (
            f"regra vizinha calada por `{{runtime_scope, blocked_on}}` sobre o corpus "
            f"de grafo: {culpados}. A fronteira ficaria verde sem nunca ter sido "
            f"avaliada."
        )


class TestOQuePYDizSobreOCorpusDeGrafo:
    """SF-PY dispara aqui, e a diferenca entre invasao e trabalho e argumento.

    A pergunta nao e "disparou?", e "o achado cita evidencia sobre outra
    pergunta?". Os dezesseis citam `pyspark.cache` e `pyspark.conf_set`, e o
    `subject` de cada um aponta para uma linha que esta no arquivo. Nenhum cita
    um `graph.*`. E SF-PY fazendo o trabalho dela sobre codigo que e PySpark
    comum -- que todo job de grafo tambem e.
    """

    def test_os_achados_py_sobre_grafo_sao_exatamente_os_medidos(self, sobre_grafo):
        medido = {
            j["nome"]: tuple(
                sorted({f.rule_id for f in j["findings"] if _area_do_id(f.rule_id) == PY})
            )
            for j in sobre_grafo
        }
        esperado = {
            j["nome"]: tuple(sorted(ESPERADO_PY_SOBRE_GRAFO.get(j["nome"], ())))
            for j in sobre_grafo
        }
        diferenca = sorted(
            (nome, medido[nome], esperado[nome])
            for nome in medido
            if medido[nome] != esperado[nome]
        )
        assert not diferenca, (
            f"(fixture, medido, esperado) = {diferenca}. Um achado de {PY} a mais "
            f"sobre uma fixture de grafo pode ser as duas coisas: invasao -- a regra "
            f"citando fact que descreve outra pergunta -- ou trabalho legitimo, "
            f"porque job de grafo tambem e job PySpark. As duas respostas exigem o "
            f"mesmo: medir a evidencia do achado e escrever o argumento em "
            f"`ESPERADO_PY_SOBRE_GRAFO`. Apagar a linha e a unica saida errada."
        )

    def test_as_cinco_fixtures_sem_pyspark_relevante_ficam_mudas(self, sobre_grafo):
        por_nome = {j["nome"]: j for j in sobre_grafo}
        for nome in SILENCIOSAS_PARA_PY:
            achados = sorted(
                f.rule_id for f in por_nome[nome]["findings"] if _area_do_id(f.rule_id) == PY
            )
            assert not achados, f"{nome}: {achados}"

    def test_todo_achado_py_sobre_grafo_cita_so_fact_de_pyspark(self, sobre_grafo):
        """O criterio que separa invasao de trabalho, medido fact a fact."""
        for j in sobre_grafo:
            por_id = {f.id: f.kind for f in j["facts"]}
            for finding in j["findings"]:
                if _area_do_id(finding.rule_id) != PY:
                    continue
                citados = sorted({por_id[e] for e in finding.evidence})
                assert all(k.startswith(NAMESPACE[PY]) for k in citados), (
                    f"{j['nome']}/{finding.rule_id} cita {citados}. Um achado de {PY} "
                    f"ancorado num `graph.*` e a invasao que este arquivo existe para "
                    f"pegar: a regra afirma sobre PySpark citando evidencia que "
                    f"descreve um grafo."
                )

    def test_todo_achado_py_sobre_grafo_aponta_para_uma_linha_que_existe(self, sobre_grafo):
        """A outra metade do argumento: a linha acusada esta no arquivo.

        Citar o namespace certo nao basta -- um fact de `pyspark.cache` derivado
        de outro lugar apontaria para uma linha que nao e a do `.cache()`. Aqui o
        `snippet` do `subject` e conferido contra o texto do arquivo, na linha
        que o achado nomeia.
        """
        for j in sobre_grafo:
            for finding in j["findings"]:
                if _area_do_id(finding.rule_id) != PY:
                    continue
                sujeito = finding.subject
                fonte = (j["dir"] / "input" / sujeito["file"]).read_text(encoding="utf-8")
                linha = fonte.splitlines()[sujeito["line"] - 1]
                assert linha.strip() == sujeito["snippet"].strip(), (
                    f"{j['nome']}/{finding.rule_id}: o achado diz "
                    f"`{sujeito['file']}:{sujeito['line']}` com o trecho "
                    f"`{sujeito['snippet']}`, e a linha do arquivo e `{linha.strip()}`."
                )

    def test_o_corpus_de_grafo_realmente_nunca_chama_unpersist(self):
        """Por que `SF-PY-008` esta CERTA sobre catorze fixtures de grafo.

        Se alguma fixture ganhar `unpersist`, o achado correspondente some e
        `ESPERADO_PY_SOBRE_GRAFO` fica errado -- e o motivo de ter sumido precisa
        aparecer aqui, e nao como uma linha a menos numa lista.
        """
        com_unpersist = sorted(
            f"{d.name}/{py.name}"
            for d in _dirs(CORPUS[GRAFO])
            for py in sorted((d / "input").rglob("*.py"))
            if ".unpersist(" in py.read_text(encoding="utf-8")
        )
        assert not com_unpersist, (
            f"{com_unpersist} passaram a chamar `unpersist`. `SF-PY-008` deixa de "
            f"disparar sobre elas, e o argumento escrito em "
            f"`ESPERADO_PY_SOBRE_GRAFO` deixa de valer para essas linhas."
        )


class TestFronteiraSobreOsCorporaVizinhos:
    """Direcao 1: SF-GRAPH sobre `fixtures/dq/` e `fixtures/pyspark/`."""

    def test_nenhuma_regra_graph_dispara_sobre_dq_nem_pyspark(self, vizinhos_no_runtime_declarado):
        invasoes = _findings_da_area(vizinhos_no_runtime_declarado, GRAFO)
        assert not invasoes, (
            f"regra de grafo disparou sobre job que nao e de grafo: {invasoes}. O "
            f"extrator de grafo LE esses arquivos e emite a sentinela nas trinta "
            f"fixtures; um achado aqui e uma regra que confundiu `cache`, `join` ou "
            f"laco com processamento de grafo."
        )

    def test_sob_o_runtime_declarado_o_silencio_de_graph_002_e_por_escopo(
        self, catalogo, vizinhos_no_runtime_declarado
    ):
        """O buraco, nomeado em vez de escondido.

        Este teste nao e uma exigencia: e o registro do que a passagem anterior
        NAO prova. Sob o Spark 3.5.4 dos dois corpora vizinhos, `SF-GRAPH-002`
        esta fora de escopo e nem chega a olhar para um fact -- entao
        `test_nenhuma_regra_graph_dispara_sobre_dq_nem_pyspark` nao afirma nada
        sobre ela. Quem fecha o buraco e
        `test_na_faixa_de_spark_nenhuma_regra_graph_dispara`. Se a lista abaixo
        mudar, e a segunda passagem que precisa ser relida.
        """
        da_area = {r["id"] for r in _regras_da_area(catalogo, GRAFO)}
        por_escopo = {
            s["rule_id"]
            for j in vizinhos_no_runtime_declarado
            for s in j["skipped"]
            if s["rule_id"] in da_area and s["reason"] == "runtime_scope"
        }
        assert por_escopo == {"SF-GRAPH-002"}, (
            f"caladas por `runtime_scope` sobre os corpora vizinhos: "
            f"{sorted(por_escopo)}. O arquivo foi escrito medindo que so "
            f"`SF-GRAPH-002` tem escopo nao-vazio nesta area (D-6a-29). Se a lista "
            f"esvaziou, a passagem declarada passou a cobrir as quatro regras e este "
            f"teste virou registro de uma epoca -- apague-o. Se ela cresceu, ha regra "
            f"nova cujo escopo a passagem declarada nao alcanca, e o que precisa ser "
            f"conferido e se o runtime da faixa alcanca."
        )

    def test_na_faixa_de_spark_nenhuma_regra_graph_dispara(self, vizinhos_na_faixa_de_spark):
        """A mesma direcao, com o escopo fora do caminho.

        Os corpora vizinhos julgados com o Spark 3.3.0 de
        `fixtures/graph/import_sem_jar_no_iac`, onde as QUATRO regras da area
        estao em escopo. Vermelho aqui e a fronteira de verdade quebrando;
        vermelho so na passagem anterior seria escopo mudando.
        """
        invasoes = _findings_da_area(vizinhos_na_faixa_de_spark, GRAFO)
        assert not invasoes, (
            f"com Spark na faixa de `SF-GRAPH-002`, regra de grafo disparou sobre "
            f"corpus vizinho: {invasoes}."
        )

    def test_na_faixa_toda_regra_graph_e_calada_por_falta_de_fact(
        self, catalogo, vizinhos_na_faixa_de_spark
    ):
        """A afirmacao positiva da direcao 1, na passagem em que ela e possivel.

        As quatro regras exigem `graph.algorithm`, `graph.import` ou
        `graph.construction`, e nenhuma delas exige a sentinela -- que e o unico
        kind `graph.*` que os corpora vizinhos produzem. Por isso o silencio e
        `requires_facts` nas trinta fixtures, e nao escopo, e nao `when` falso.
        """
        da_area = {r["id"] for r in _regras_da_area(catalogo, GRAFO)}
        for j in vizinhos_na_faixa_de_spark:
            por_falta = {s["rule_id"] for s in j["skipped"] if s["reason"] == "requires_facts"}
            faltando = sorted(da_area - por_falta)
            visto = [s for s in j["skipped"] if s["rule_id"] in da_area]
            assert not faltando, (
                f"em `{j['nome']}`, as regras {faltando} de {GRAFO} nao foram puladas "
                f"por `requires_facts` mesmo com o Spark dentro da faixa. Skips de "
                f"{GRAFO} nesta fixture: {visto}"
            )


class TestNenhumAchadoCitaFactDeOutraArea:
    """O criterio da fronteira, aplicado as tres areas nos tres corpora.

    E a generalizacao de `test_todo_achado_py_sobre_grafo_cita_so_fact_de_pyspark`:
    com o artefato compartilhado, o defeito nao aparece como "achado no corpus
    errado" -- aparece como achado citando um fact que responde outra pergunta
    sobre o mesmo arquivo. Este e o teste que pegaria uma regra escrita para ler
    os dois vocabularios ao mesmo tempo.
    """

    @pytest.mark.parametrize("corpus", AREAS)
    def test_toda_regra_das_tres_areas_cita_so_o_proprio_namespace(
        self, sobre_grafo, sobre_dq, sobre_py, corpus
    ):
        julgados = {GRAFO: sobre_grafo, DQ: sobre_dq, PY: sobre_py}[corpus]
        for j in julgados:
            por_id = {f.id: f.kind for f in j["facts"]}
            for finding in j["findings"]:
                area = _area_do_id(finding.rule_id)
                if area not in NAMESPACE:
                    continue
                citados = sorted({por_id[e] for e in finding.evidence})
                fora = [k for k in citados if not k.startswith(NAMESPACE[area])]
                assert not fora, (
                    f"`fixtures/{CORPUS[corpus].name}/{j['nome']}`: "
                    f"{finding.rule_id} ({area}) cita {fora}, de fora de "
                    f"`{NAMESPACE[area]}`. O achado sai do relatorio afirmando uma "
                    f"coisa e apontando para a evidencia de outra."
                )
