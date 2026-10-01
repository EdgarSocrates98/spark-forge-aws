"""Exportacao no formato de extracao do Graphify, e o que ela declara NAO ter.

O valor destes testes nao esta em provar que o JSON sai -- isso e trivial. Esta
em travar as DUAS metades da declaracao de compatibilidade: os campos que vem da
fonte, e a recusa de importar, com a razao medida.
"""

from __future__ import annotations

import json
from pathlib import Path

from sparkforge.codeintel import export
from sparkforge.codeintel.export import FONTE_CONFERIDA, exportar, exportar_json
from sparkforge.codeintel.index import indexar

# Os nomes que `ARCHITECTURE.md` da fonte publica para o formato de EXTRACAO,
# lidos em 2026-09-02. Este teste e o guarda contra a deriva silenciosa: se
# alguem acrescentar campo ao bloco de cima achando que "e compativel", o teste
# reprova e obriga a conferir a fonte de novo.
CAMPOS_DE_NO_DA_FONTE = {"id", "label", "source_file", "source_location"}
CAMPOS_DE_ARESTA_DA_FONTE = {"source", "target", "relation", "confidence"}

FONTE = """
def folha():
    return 1


def raiz():
    return folha()
"""


def _banco(tmp_path: Path) -> Path:
    (tmp_path / "job.py").write_text(FONTE, encoding="utf-8")
    banco = tmp_path / "indice.sqlite3"
    indexar(tmp_path, banco)
    return banco


def test_o_no_traz_os_campos_da_fonte_e_MAIS_NADA_no_nivel_de_cima(tmp_path):
    """A separacao e o que torna a compatibilidade conferivel.

    Misturar os campos deste motor com os da fonte produziria um artefato que se
    PARECE com o dela e nao e -- quem o lesse assumiria que todo campo veio de
    la. Tudo o que este motor sabe e a fonte nao nomeia vive em `sparkforge`.
    """
    dados = exportar(_banco(tmp_path))
    assert dados["nodes"], "o corpus precisa render no"
    for no in dados["nodes"]:
        do_topo = set(no) - {"sparkforge"}
        assert do_topo == CAMPOS_DE_NO_DA_FONTE, (
            f"campo fora do que a fonte nomeia: {sorted(do_topo - CAMPOS_DE_NO_DA_FONTE)}. "
            f"O que este motor sabe e a fonte nao nomeia vai em `sparkforge`."
        )


def test_a_aresta_traz_exatamente_os_campos_da_fonte(tmp_path):
    dados = exportar(_banco(tmp_path))
    assert dados["edges"], "o corpus precisa render aresta"
    for aresta in dados["edges"]:
        assert set(aresta) == CAMPOS_DE_ARESTA_DA_FONTE


def test_confidence_e_EXTRACTED_e_isso_e_afirmacao(tmp_path):
    """A fonte publica `EXTRACTED` e `INFERRED`. Toda aresta aqui e a primeira.

    O que `resolve.resolver` nao conseguiu ligar virou `unresolved_refs` e NAO E
    ARESTA -- entao nada do que sai daqui foi inferido. Marcar `INFERRED` alguma
    delas seria afirmar uma inferencia que nao houve.
    """
    dados = exportar(_banco(tmp_path))
    assert {a["confidence"] for a in dados["edges"]} == {"EXTRACTED"}


def test_a_relacao_declarada_e_a_unica_que_o_indice_produz(tmp_path):
    """Declarar mais tipos prometeria aresta que nada emite."""
    dados = exportar(_banco(tmp_path))
    assert {a["relation"] for a in dados["edges"]} == {"calls"}


def test_a_recusa_de_importar_esta_declarada_com_a_razao(tmp_path):
    """A razao e MEDIDA, e o artefato a carrega.

    O `README.md` da fonte nao especifica o `graph.json` final, e o
    `ARCHITECTURE.md` diz literalmente que o schema que ele mostra e o da
    extracao, anterior a `build()`. Sem essa razao no artefato, "nao importa"
    se leria como omissao em vez de decisao.
    """
    meta = exportar(_banco(tmp_path))["sparkforge"]
    assert "not_implemented" in meta
    assert "importacao" in meta["not_implemented"]
    assert "build()" in meta["not_implemented"]
    assert not hasattr(export, "importar"), (
        "importar exigiria adivinhar o formato de destino, que a fonte nao "
        "publica -- se alguem o escrever, a razao acima precisa deixar de valer "
        "primeiro"
    )


def test_o_artefato_diz_contra_QUE_VERSAO_a_compatibilidade_foi_medida(tmp_path):
    """Sem isso, uma divergencia futura vira discussao em vez de comparacao."""
    meta = exportar(_banco(tmp_path))["sparkforge"]
    assert meta["source_checked"] == FONTE_CONFERIDA
    assert "graphify" in FONTE_CONFERIDA.lower()
    assert "2026-09-02" in FONTE_CONFERIDA


def test_as_duas_metades_da_compatibilidade_saem_juntas(tmp_path):
    """O que casa E o que nao existe, na mesma estrutura.

    Um artefato que so declarasse a primeira metade convidaria quem o le a
    assumir a segunda.
    """
    meta = exportar(_banco(tmp_path))["sparkforge"]
    assert set(meta["compatible_fields"]["nodes"]) == CAMPOS_DE_NO_DA_FONTE
    assert set(meta["compatible_fields"]["edges"]) == CAMPOS_DE_ARESTA_DA_FONTE
    assert meta["not_from_source"]
    assert meta["not_implemented"]


def test_nada_importa_graphifyy(tmp_path):
    """A compatibilidade e de FORMATO, nunca de codigo.

    A versao 0.9.53 traz 29 dependencias obrigatorias -- `networkx`, `numpy`,
    `rapidfuzz` e 26 gramaticas `tree-sitter`. O wheel minimo deste projeto tem
    DUAS.
    """
    fonte = Path(export.__file__).read_text(encoding="utf-8")
    assert "import graphify" not in fonte
    assert "graphifyy" not in fonte.replace("`graphifyy`", "")


def test_a_exportacao_e_deterministica(tmp_path):
    banco = _banco(tmp_path)
    primeira = exportar_json(banco)
    for _ in range(3):
        assert exportar_json(banco) == primeira


def test_a_ordem_dos_nos_e_por_id_e_nao_pelo_plano_do_sqlite(tmp_path):
    dados = exportar(_banco(tmp_path))
    ids = [n["id"] for n in dados["nodes"]]
    assert ids == sorted(ids)


def test_a_ordem_das_arestas_tambem(tmp_path):
    dados = exportar(_banco(tmp_path))
    pares = [(a["source"], a["target"]) for a in dados["edges"]]
    assert pares == sorted(pares)


def test_a_comunidade_viaja_em_sparkforge_e_nao_no_topo(tmp_path):
    """`community` nao e campo que a fonte nomeie no formato de extracao."""
    dados = exportar(_banco(tmp_path))
    for no in dados["nodes"]:
        assert "community" not in no
        assert "community" in no["sparkforge"]


def test_sem_comunidades_o_bloco_sai_declarado_e_nao_ausente(tmp_path):
    """`algorithm: null` diz 'nao calculei'; a chave ausente nao diz nada."""
    dados = exportar(_banco(tmp_path), incluir_comunidades=False)
    meta = dados["sparkforge"]["communities"]
    assert meta["algorithm"] is None
    assert meta["converged"] is None
    for no in dados["nodes"]:
        assert "community" not in no["sparkforge"]


def test_o_json_e_legivel_para_quem_abrir_o_arquivo(tmp_path):
    """`ensure_ascii=False`: nome de simbolo em portugues nao vira `\\uXXXX`."""
    (tmp_path / "job.py").write_text(
        "def particao_de_producao():\n    return 1\n", encoding="utf-8"
    )
    banco = tmp_path / "i.sqlite3"
    indexar(tmp_path, banco)
    texto = exportar_json(banco)
    assert "particao_de_producao" in texto
    assert json.loads(texto)["nodes"]


def test_banco_sem_no_exporta_estrutura_vazia_e_nao_levanta(tmp_path):
    """Arvore sem Python e resposta, nao erro."""
    (tmp_path / "leiame.txt").write_text("sem python\n", encoding="utf-8")
    banco = tmp_path / "i.sqlite3"
    indexar(tmp_path, banco)
    dados = exportar(banco)
    assert dados["nodes"] == []
    assert dados["edges"] == []
    assert dados["sparkforge"]["source_checked"] == FONTE_CONFERIDA
