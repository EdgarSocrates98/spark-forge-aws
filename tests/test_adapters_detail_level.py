"""O envelope devolvido pelo motor, e o que dele e repeticao.

Medido antes desta fase, na fixture `clean_job`: a procedencia respondia por
25,1% do payload de `analyze pyspark`, e o sha256 do MESMO arquivo aparecia uma
vez por fato. Declarar uma vez por artefato e referenciar por chave preserva a
rastreabilidade inteira e para de pagar por ela N vezes.

Tudo aqui e medido em BYTES. Os estimadores de token deste repositorio dividem
o comprimento do texto por uma constante e divergem entre si no arredondamento
-- byte e observacao, token seria estimativa vendida como medida.
"""

import json
import subprocess
import sys

import pytest

from sparkforge.adapters import _core

FIXTURE = "fixtures/pyspark/clean_job/input/lib/job.py"
CATALOGO = "fixtures/catalog/glue_table_schema/input/dump.json"
CATALOGO_MULTI = "fixtures/catalog/overpartitioned_multi_table/input/dump.json"


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
    """O `id` e estavel entre execucoes: e ele que casa a linha do resumo com o
    mesmo fato numa execucao `full`. Nao existe verbo que busque fato por id --
    ver `test_nenhuma_superficie_promete_buscar_fato_por_id`."""
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
        assert "schema_version" in item
    assert "provenance" not in saida
    assert "schema_version" not in saida


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
    assert set(resumo) < set(normal) | {"at", "symbol"}
    assert "attrs" not in resumo
    assert "subject" not in resumo


class TestOResumoPreservaAIdentidade:
    """`summary` reduz `subject` a `at` e `symbol`. Se reduzir demais, devolve
    um id opaco e o resumo deixa de responder "o que" -- e, como nao existe
    verbo que busque fato por id, nao ha como recuperar a resposta sem pagar o
    payload inteiro de novo."""

    def test_at_carrega_a_linha_e_nao_so_o_arquivo(self):
        """`at` sem a linha ainda seria truthy e ainda diria "job.py". O que o
        resumo promete e `arquivo:linha`, e e isso que precisa estar pinado."""
        completo = _analisar("--detail-level", "full")
        resumo = _analisar("--detail-level", "summary")
        for inteiro, curto in zip(completo["items"], resumo["items"], strict=True):
            sujeito = inteiro["subject"]
            assert curto["at"] == f"{sujeito['file']}:{sujeito['line']}"
            assert curto["at"].split(":")[-1].isdigit(), curto["at"]

    def test_symbol_sobrevive_quando_o_subject_identifica_por_simbolo(self):
        completo = _core.analyze_catalog_schema(CATALOGO, limit=None)
        resumo = _core.analyze_catalog_schema(CATALOGO, limit=None, detail_level="summary")
        for inteiro, curto in zip(completo["items"], resumo["items"], strict=True):
            simbolo = inteiro["subject"].get("symbol")
            assert curto.get("symbol", "") == (simbolo or "")

    def test_tabelas_diferentes_do_mesmo_dump_continuam_distinguiveis(self):
        """O caso que motivou a correcao: em `catalog.table_*` NENHUM fact tem
        `subject.line` e TODOS tem `subject.symbol`. Sem o simbolo, tres
        tabelas de um mesmo dump.json colapsam no mesmo `at` e o resumo devolve
        so um id opaco."""
        resumo = _core.analyze_catalog_schema(
            CATALOGO_MULTI, limit=None, detail_level="summary"
        )
        tabelas = [i for i in resumo["items"] if i["kind"] == "catalog.table_partitions"]
        assert len(tabelas) >= 3, "a fixture precisa ter varias tabelas"
        assert len({t["at"] for t in tabelas}) == 1, "o `at` sozinho nao distingue nada aqui"
        assert len({t["symbol"] for t in tabelas}) == len(tabelas)


class TestSchemaVersion:
    """`schema_version` e repeticao pela mesma razao que a procedencia: o mesmo
    inteiro em todo item da pagina. Ele sai do item -- mas sobe para o
    envelope. Sair sem subir seria apagar campo em silencio, que e defeito e
    nao compressao."""

    def _fact(self, ident: str, versao: int) -> dict:
        return {
            "id": ident,
            "schema_version": versao,
            "kind": "t.exemplo",
            "subject": {"type": "source_location", "file": "a.py", "line": 1},
            "measures": {},
            "attrs": {},
            "provenance": {"artifact": "a.py", "artifact_sha256": "d" * 64, "extractor": "x"},
        }

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_sai_do_item_e_sobe_para_o_envelope(self, nivel):
        saida = _analisar("--detail-level", nivel)
        assert saida["schema_version"] == 1
        for item in saida["items"]:
            assert "schema_version" not in item

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_versoes_divergentes_ficam_no_item_e_nao_no_envelope(self, nivel):
        """Um numero so no envelope estaria mentindo sobre metade da pagina.
        Possivel em `fuse`, que le facts gerados em momentos diferentes."""
        itens, _procs, versao = _core.project_items(
            [self._fact("f_1", 1), self._fact("f_2", 2)], nivel
        )
        assert versao is None
        assert [i["schema_version"] for i in itens] == [1, 2]


class TestChaveDeProcedencia:
    """`provenance_ref` e funcao SO do conteudo da procedencia. Antes ela era
    derivada do `artifact_sha256` com desempate por sufixo -- e como a projecao
    roda DEPOIS de paginar, o desempate so valia dentro de uma pagina."""

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

    def test_o_tamanho_da_chave_e_formato_de_fio(self):
        """16 hex chars. Encurtar aumenta a chance de duas procedencias
        diferentes caírem na mesma chave -- e ENTRE paginas isso nao e
        detectavel. Nao e detalhe interno: `provenance_ref` cita esta chave."""
        assert _core.TAMANHO_DA_CHAVE_DE_PROCEDENCIA == 16
        chave = _core.chave_de_procedencia({"artifact": "a.py", "extractor": "x"})
        assert len(chave) == 16
        assert all(c in "0123456789abcdef" for c in chave)

    def test_a_chave_e_a_mesma_em_qualquer_pagina(self):
        """A regressao concreta: `fuse` de py+sql em paginas de 9 dava a chave
        `7322f5e505a6` para `pyspark_ast` na pagina 1 e para `sql_literal` na
        pagina 2. Quem pagina e une os mapas -- o unico jeito de consumir
        resultado paginado -- atribuia o fato ao extrator errado, sem erro."""
        pyspark = _core.analyze_pyspark(FIXTURE, limit=None)["items"]
        sql = _core.analyze_sql(from_pyspark=FIXTURE, limit=None)["items"]
        todos = pyspark + sql

        inteiro, _, _ = _core.project_items(todos, "normal")
        esperado = {
            item["provenance_ref"]: original["provenance"]
            for item, original in zip(inteiro, todos, strict=True)
        }
        assert len(esperado) > 1, "o teste precisa de mais de uma procedencia"

        unido: dict[str, dict] = {}
        for inicio in range(0, len(todos), 3):
            pagina, procs, _ = _core.project_items(todos[inicio : inicio + 3], "normal")
            for chave, prov in procs.items():
                anterior = unido.get(chave)
                assert anterior in (None, prov), (
                    f"a chave {chave!r} mudou de significado entre paginas: "
                    f"{anterior} depois {prov}"
                )
                unido[chave] = prov
            for item in pagina:
                assert unido[item["provenance_ref"]] == esperado[item["provenance_ref"]]
        assert unido == esperado

    def test_prefixo_igual_com_sha_diferente_nao_compartilha_procedencia(self):
        a = {"artifact": "a.py", "artifact_sha256": "0" * 12 + "a" * 52, "extractor": "x"}
        b = {"artifact": "b.py", "artifact_sha256": "0" * 12 + "b" * 52, "extractor": "x"}
        itens, procs, _ = _core.project_items(
            [self._fact("f_1", a), self._fact("f_2", b)], "normal"
        )
        assert itens[0]["provenance_ref"] != itens[1]["provenance_ref"]
        assert procs[itens[0]["provenance_ref"]] == a
        assert procs[itens[1]["provenance_ref"]] == b

    def test_tres_extratores_sobre_o_mesmo_sha_nao_se_sobrescrevem(self):
        """`fuse` reune `pyspark_ast`, `sql_literal`, `call_graph` e `fusion`
        sobre o MESMO arquivo. Com dois, um desempate ingenuo ainda passa; com
        tres, o terceiro sobrescreve o segundo."""
        sha = "c" * 64
        provs = [
            {"artifact": "a.py", "artifact_sha256": sha, "extractor": nome}
            for nome in ("pyspark_ast", "sql_literal", "call_graph")
        ]
        itens, procs, _ = _core.project_items(
            [self._fact(f"f_{n}", p) for n, p in enumerate(provs)], "normal"
        )
        assert len({i["provenance_ref"] for i in itens}) == 3
        assert len(procs) == 3
        for item, prov in zip(itens, provs, strict=True):
            assert procs[item["provenance_ref"]] == prov

    def test_procedencias_iguais_compartilham_uma_unica_entrada(self):
        """E o ponto da fase: o mesmo artefato declarado uma vez, nao N."""
        prov = {"artifact": "a.py", "artifact_sha256": "d" * 64, "extractor": "x"}
        itens, procs, _ = _core.project_items(
            [self._fact("f_1", dict(prov)), self._fact("f_2", dict(prov))], "normal"
        )
        assert len(procs) == 1
        assert itens[0]["provenance_ref"] == itens[1]["provenance_ref"]

    def test_fato_sem_procedencia_nao_ganha_ref(self):
        itens, procs, _ = _core.project_items([self._fact("f_1", {})], "normal")
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

    def test_nenhuma_superficie_promete_buscar_fato_por_id(self):
        """A primeira versao dizia "peca o fato inteiro por id quando precisar"
        no help da CLI, na `description` das 20 tools e num comentario: 21
        superficies oferecendo uma afordancia que NAO EXISTE. Nenhuma das 44
        tools aceita id de fact -- o unico `id` do catalogo e o de REGRA, em
        `sparkforge_rules_lookup`."""
        from sparkforge.adapters.cli import _DETAIL_LEVEL_HELP
        from sparkforge.adapters.tools import _DETAIL_LEVEL_DESC, TOOLS

        por_id = {
            nome
            for nome, spec in TOOLS.items()
            if "id" in spec["inputSchema"].get("properties", {})
        }
        assert por_id == {"sparkforge_rules_lookup"}

        for texto in (_DETAIL_LEVEL_HELP, _DETAIL_LEVEL_DESC):
            assert "NAO existe" in texto, "o texto tem que dizer que o verbo nao existe"
            assert "reexecute" in texto, "e tem que dizer o que fazer no lugar"

    @pytest.mark.parametrize("nivel", ["summary", "normal", "full"])
    def test_saida_projetada_valida_contra_o_proprio_schema(self, nivel):
        import jsonschema

        from sparkforge.adapters.tools import TOOLS, call_tool

        resultado = call_tool(
            "sparkforge_analyze_pyspark", {"path": FIXTURE, "detail_level": nivel}
        )
        jsonschema.validate(resultado, TOOLS["sparkforge_analyze_pyspark"]["outputSchema"])

    def test_o_schema_de_full_ainda_exige_o_fato_inteiro(self):
        """Baixar `required` para o que os tres niveis tem em comum deixaria
        passar um item de `full` sem `subject` -- exatamente a regressao que o
        schema pegava antes de `detail_level` existir. Os tres ramos do `oneOf`
        devolvem esse contrato sem mentir sobre `normal` e `summary`."""
        import jsonschema

        from sparkforge.adapters.tools import TOOLS, call_tool

        schema = TOOLS["sparkforge_analyze_pyspark"]["outputSchema"]
        resultado = call_tool("sparkforge_analyze_pyspark", {"path": FIXTURE})
        jsonschema.validate(resultado, schema)

        mutilado = json.loads(json.dumps(resultado))
        del mutilado["items"][0]["subject"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(mutilado, schema)

        # Nao basta um discriminante: com so `subject`, este item casaria com o
        # ramo `summary` (que tambem nao tem `subject`) e o `oneOf` passaria.
        # E `provenance` que o separa de um resumo de verdade.
        misturado = json.loads(json.dumps(resultado))
        del misturado["items"][0]["subject"]
        del misturado["items"][0]["measures"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(misturado, schema)

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
    `fuse_facts` -- e cada um chama `declarar_no_envelope` no proprio codigo.
    """

    def _conferir(self, envelope: dict) -> None:
        assert envelope["provenance"], "o envelope do _core precisa declarar as procedencias"
        assert envelope["items"], "sem item o teste nao afirma nada"
        assert envelope["schema_version"] == 1, "o schema_version tem que subir junto"
        for item in envelope["items"]:
            assert "provenance" not in item
            assert "schema_version" not in item
            assert item["provenance_ref"] in envelope["provenance"]

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_analyze_pyspark(self, nivel):
        self._conferir(_core.analyze_pyspark(FIXTURE, limit=None, detail_level=nivel))

    @pytest.mark.parametrize("nivel", ["normal", "summary"])
    def test_analyze_catalog_schema(self, nivel):
        self._conferir(_core.analyze_catalog_schema(CATALOGO, limit=None, detail_level=nivel))

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
