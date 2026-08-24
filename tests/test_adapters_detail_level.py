"""O envelope devolvido pelo motor, e o que dele e repeticao.

Medido antes desta fase, na fixture `clean_job`: a procedencia respondia por
25,1% do payload de `analyze pyspark`, e o sha256 do MESMO arquivo aparecia uma
vez por fato. Declarar uma vez por artefato e referenciar por chave preserva a
rastreabilidade inteira e para de pagar por ela N vezes.

Tudo aqui e medido em BYTES. Existem quatro estimadores de token no repositorio,
todos `len/4`, e eles divergem entre si no arredondamento -- byte e observacao,
token seria estimativa vendida como medida.
"""

import json
import subprocess
import sys

import pytest

from sparkforge.adapters import _core

FIXTURE = "fixtures/pyspark/clean_job/input/lib/job.py"


def _analisar(*extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "sparkforge.adapters.cli", "analyze", "pyspark",
         "--path", FIXTURE, *extra],
        capture_output=True, text=True, check=True,
    )
    return json.loads(proc.stdout)


def _bytes(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def test_provenance_e_declarada_uma_vez_e_referenciada_por_chave():
    saida = _analisar("--detail-level", "normal")
    assert "provenance" in saida, "o envelope precisa declarar as procedencias"
    for item in saida["items"]:
        assert "provenance" not in item, "procedencia inline volta a custar por fato"
        assert item["provenance_ref"] in saida["provenance"]


def test_nada_de_rastreabilidade_se_perde():
    completo = _analisar("--detail-level", "full")
    compacto = _analisar("--detail-level", "normal")
    for inline, referenciado in zip(completo["items"], compacto["items"], strict=True):
        assert compacto["provenance"][referenciado["provenance_ref"]] == inline["provenance"]


def test_summary_tambem_carrega_a_procedencia_no_envelope():
    """`summary` corta campo, nunca rastreabilidade.

    Economia que apaga procedencia seria o defeito que o gate de lastro recusa,
    e nao uma versao mais barata do mesmo resultado.
    """
    saida = _analisar("--detail-level", "summary")
    assert saida["provenance"]
    for item in saida["items"]:
        assert item["provenance_ref"] in saida["provenance"]


@pytest.mark.parametrize("nivel", ["summary", "normal", "full"])
def test_id_sobrevive_a_todos_os_niveis(nivel):
    """Sem `id`, `summary` seria beco sem saida em vez de primeiro passo."""
    saida = _analisar("--detail-level", nivel)
    assert saida["items"], "a fixture precisa produzir ao menos um fato"
    for item in saida["items"]:
        assert item["id"]


def test_summary_e_menor_que_normal_que_e_menor_que_full():
    tamanhos = {n: _bytes(_analisar("--detail-level", n)) for n in ("summary", "normal", "full")}
    assert tamanhos["summary"] < tamanhos["normal"] < tamanhos["full"], tamanhos


def test_full_nao_mudou_de_forma():
    """`full` e o modo de reauditoria. Mudar a forma dele quebraria golden."""
    saida = _analisar("--detail-level", "full")
    for item in saida["items"]:
        assert "provenance" in item
        assert "provenance_ref" not in item
    assert "provenance" not in saida


def test_o_default_e_full():
    """O default e `full` de proposito: mudar a saida de todo chamador
    existente e de todo golden e decisao de contrato, separada desta fase."""
    assert _analisar() == _analisar("--detail-level", "full")


def test_detail_level_invalido_e_recusado():
    proc = subprocess.run(
        [sys.executable, "-m", "sparkforge.adapters.cli", "analyze", "pyspark",
         "--path", FIXTURE, "--detail-level", "nao_existe"],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0


def test_detail_level_invalido_e_recusado_tambem_no_core():
    """A CLI barra pelo `choices` do argparse; o MCP chama `project_items`
    direto. Sem esta guarda, um `detail_level` errado vindo do MCP passaria em
    silencio e devolveria `full` como se fosse o nivel pedido."""
    with pytest.raises(_core.AdapterError):
        _core.project_items([], "nao_existe")


def test_summary_devolve_menos_campos_que_normal():
    """Se `summary` devolvesse os mesmos campos de `normal`, os dois niveis
    seriam o mesmo nivel com dois nomes."""
    normal = _analisar("--detail-level", "normal")["items"][0]
    resumo = _analisar("--detail-level", "summary")["items"][0]
    assert set(resumo) < set(normal) | {"at"}
    assert "attrs" not in resumo
    assert "subject" not in resumo
    assert resumo["at"], "o `at` e o subject condensado; sem ele o resumo perde o onde"


class TestChaveDeProcedencia:
    """O `provenance_ref` trunca o sha em 12. Colisao ali seria SILENCIOSA:
    dois artefatos passariam a compartilhar procedencia e a rastreabilidade
    apontaria para o arquivo errado."""

    def _fact(self, ident: str, prov: dict) -> dict:
        return {
            "id": ident,
            "schema_version": 1,
            "kind": "t.exemplo",
            "subject": {"type": "source_location", "file": "a.py", "line": 1},
            "measures": {},
            "attrs": {},
            "provenance": prov,
        }

    def test_prefixo_igual_com_sha_diferente_nao_compartilha_procedencia(self):
        a = {"artifact": "a.py", "artifact_sha256": "0" * 12 + "a" * 52, "extractor": "x"}
        b = {"artifact": "b.py", "artifact_sha256": "0" * 12 + "b" * 52, "extractor": "x"}
        itens, procs = _core.project_items(
            [self._fact("f_1", a), self._fact("f_2", b)], "normal"
        )
        assert itens[0]["provenance_ref"] != itens[1]["provenance_ref"]
        assert procs[itens[0]["provenance_ref"]] == a
        assert procs[itens[1]["provenance_ref"]] == b

    def test_mesmo_sha_com_extrator_diferente_nao_compartilha_procedencia(self):
        """Acontece de verdade em `fuse`: facts de extratores distintos sobre o
        mesmo arquivo entram na mesma pagina. Escalar so ate o sha inteiro nao
        bastaria -- as duas procedencias tem o mesmo sha."""
        sha = "c" * 64
        a = {"artifact": "a.py", "artifact_sha256": sha, "extractor": "pyspark_ast"}
        b = {"artifact": "a.py", "artifact_sha256": sha, "extractor": "call_graph"}
        itens, procs = _core.project_items(
            [self._fact("f_1", a), self._fact("f_2", b)], "normal"
        )
        assert itens[0]["provenance_ref"] != itens[1]["provenance_ref"]
        assert procs[itens[0]["provenance_ref"]] == a
        assert procs[itens[1]["provenance_ref"]] == b

    def test_procedencias_iguais_compartilham_uma_unica_entrada(self):
        """E o ponto da fase: o mesmo artefato declarado uma vez, nao N."""
        prov = {"artifact": "a.py", "artifact_sha256": "d" * 64, "extractor": "x"}
        itens, procs = _core.project_items(
            [self._fact("f_1", dict(prov)), self._fact("f_2", dict(prov))], "normal"
        )
        assert len(procs) == 1
        assert itens[0]["provenance_ref"] == itens[1]["provenance_ref"]

    def test_fato_sem_procedencia_nao_ganha_ref(self):
        itens, procs = _core.project_items([self._fact("f_1", {})], "normal")
        assert "provenance_ref" not in itens[0]
        assert procs == {}


class TestSuperficieMCP:
    """A flag tem que existir nas duas superficies, e a saida projetada tem que
    validar contra o `outputSchema` que a propria tool declara."""

    def test_as_tools_de_fact_declaram_detail_level(self):
        from sparkforge.adapters.tools import TOOLS

        com_paginacao = {
            nome
            for nome, spec in TOOLS.items()
            if "limit" in spec["inputSchema"].get("properties", {})
        }
        sem_flag = {
            nome
            for nome in com_paginacao
            if "detail_level" not in TOOLS[nome]["inputSchema"]["properties"]
        }
        # `judge` devolve findings e `rules_lookup` devolve regras: nenhum dos
        # dois tem `provenance`, e o `summary` de fato (`id`/`kind`/`measures`)
        # nao existe nesses shapes.
        assert sem_flag == {"sparkforge_judge", "sparkforge_rules_lookup"}

    @pytest.mark.parametrize("nivel", ["summary", "normal", "full"])
    def test_saida_projetada_valida_contra_o_proprio_schema(self, nivel):
        import jsonschema

        from sparkforge.adapters.tools import TOOLS, call_tool

        resultado = call_tool(
            "sparkforge_analyze_pyspark", {"path": FIXTURE, "detail_level": nivel}
        )
        jsonschema.validate(resultado, TOOLS["sparkforge_analyze_pyspark"]["outputSchema"])

    def test_detail_level_invalido_vira_erro_estruturado_e_nao_excecao(self):
        from sparkforge.adapters.tools import call_tool

        resultado = call_tool(
            "sparkforge_analyze_pyspark", {"path": FIXTURE, "detail_level": "nao_existe"}
        )
        assert resultado["exit_code"] == 2
        assert "detail_level" in resultado["error"]


class TestEnvelopeDoCore:
    """A CLI REPAGINA por conta propria (`_core.analyze_*` e chamado com
    `limit=None` para o `--out` sair completo) e projeta a propria pagina. Isso
    quer dizer que testar so pela CLI nao toca o envelope que o `_core` monta --
    e e ESSE que o cliente MCP recebe. Medido: uma mutacao que apagava o
    `provenance` do envelope de `analyze_pyspark` passava na suite inteira
    quando ela so exercitava a CLI.

    Sao quatro envelopes de fact no `_core` -- `analyze_pyspark`,
    `analyze_catalog_schema`, `_facts_page` (compartilhado por 17 verbos) e
    `fuse_facts` -- e cada um monta o `provenance` no proprio codigo.
    """

    def _conferir(self, envelope: dict) -> None:
        assert envelope["provenance"], "o envelope do _core precisa declarar as procedencias"
        assert envelope["items"], "sem item o teste nao afirma nada"
        for item in envelope["items"]:
            assert "provenance" not in item
            assert item["provenance_ref"] in envelope["provenance"]

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_analyze_pyspark(self, nivel):
        self._conferir(_core.analyze_pyspark(FIXTURE, limit=None, detail_level=nivel))

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_analyze_catalog_schema(self, nivel):
        envelope = _core.analyze_catalog_schema(
            "fixtures/catalog/glue_table_schema/input/dump.json", limit=None, detail_level=nivel
        )
        self._conferir(envelope)

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_facts_page_o_helper_compartilhado_por_17_verbos(self, nivel):
        envelope = _core.analyze_sql(from_pyspark=FIXTURE, limit=None, detail_level=nivel)
        self._conferir(envelope)

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_fuse(self, nivel, tmp_path):
        arquivo = tmp_path / "facts.json"
        arquivo.write_text(
            json.dumps(_core.analyze_pyspark(FIXTURE, limit=None)["items"]), encoding="utf-8"
        )
        self._conferir(_core.fuse_facts([str(arquivo)], limit=None, detail_level=nivel))
