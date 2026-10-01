"""Recall e economia do `ContextPack`, e o contrafactual que prova o gate.

Ver `sparkforge/economy/recall.py` para por que ha duas perguntas por fixture e
por que economia nao tem piso.
"""

from __future__ import annotations

import pytest

from sparkforge.economy.goldset import derivar_goldset
from sparkforge.economy.recall import (
    NIVEIS,
    MedidaDeRecall,
    SimboloExigido,
    _bytes_do_grep,
    _no_nivel,
    _nomes_do_pack,
    medir,
)

# Uma fixture so nos testes que nao precisam do corpus inteiro: cada medida
# indexa e monta duas vezes, e 23 delas custam ~40 s.
UMA = 1


@pytest.fixture(scope="module")
def medidas():
    return medir(derivar_goldset())


def test_recall_nominal_e_cem_por_cento(medidas):
    """O piso duro. Perguntado pelo NOME, o pack entrega o simbolo.

    Se `buscar(banco, nome)` acha o no e `montar(banco, nome)` nao o entrega, o
    funil perdeu no caminho -- e isso e defeito do produto, nao limite dele.
    """
    falhas = [(m.chave, m.faltaram, m.erro) for m in medidas if not m.respondeu]
    assert not falhas, f"recall nominal abaixo de 100%: {falhas}"


def test_recall_conceitual_e_medido_e_nao_tem_piso(medidas):
    """MEDIDO em 2026-09-02: 0 de 23. Este teste grava o numero, nao o exige.

    O titulo da regra descreve o DEFEITO (`connectedComponents sem diretorio de
    checkpoint`) e o indice guarda o NOME (`componentes`). Ninguem construiu a
    ponte entre os dois, e a SPEC nao a promete.

    O teste falha apenas se o numero SUBIR sem que ninguem tenha atualizado esta
    docstring -- porque uma melhoria que ninguem registrou vira, no mes seguinte,
    uma afirmacao sem dono sobre quando ela apareceu.
    """
    passaram = sum(1 for m in medidas if m.respondeu_conceitual)
    assert passaram == 0, (
        f"recall conceitual subiu para {passaram}/{len(medidas)}. Isso e "
        f"PROGRESSO, e ele precisa ser registrado: atualize este teste e a "
        f"docstring de `MedidaDeRecall`, dizendo o que passou a ligar o titulo "
        f"da regra ao nome do simbolo."
    )


def test_nenhuma_medida_erra(medidas):
    """Erro de indexacao ou de montagem e defeito, nao recall baixo."""
    erros = [(m.chave, m.erro) for m in medidas if m.erro]
    assert not erros, f"medidas com erro: {erros}"


def test_o_contrafactual_da_ancoragem_no_grafo(monkeypatch):
    """Desligada a ancoragem no grafo, o pack MUDA -- e o quanto esta medido.

    ## O que este teste prova, e o que ele NAO prova

    MEDIDO em 2026-09-02 sobre `SF-CG-001@fixtures/callgraph/mutual_recursion`,
    desligando `_profundidades`:

        recall  True -> True     (nao mudou)
        bytes   2405 -> 2403     (2 bytes)

    Os 2 bytes sao a componente `graph` do `score_breakdown` caindo de valor.
    Entao o que fica **provado** e estreito: a ancoragem no grafo esta LIGADA ao
    escore, e o pack reflete isso. Se um dia ela for desligada por acidente,
    este teste fica vermelho.

    O que **nao** fica provado -- e dizer o contrario seria vender a medicao que
    nao foi feita -- e que a ancoragem muda o que se RECUPERA. Nestas fixtures
    ela nao tem como mudar: sao um arquivo e um punhado de simbolos, e nao ha o
    que reordenar. Recall continua `True` dos dois lados porque o FTS sozinho ja
    bastava para um corpus deste tamanho.

    A medida que destravaria a pergunta forte -- "a proximidade no grafo melhora
    a recuperacao?" -- e um corpus onde varios simbolos disputem a mesma
    consulta. Ele nao existe hoje, e e a mesma lacuna que faz
    `scripts/check_recall_economy.py` recusar publicar razao de economia.
    """
    from sparkforge.codeintel import context

    pergunta = derivar_goldset()[0]
    antes = medir([pergunta])[0]

    monkeypatch.setattr(context, "_profundidades", lambda banco, sementes: {})
    depois = medir([pergunta])[0]

    assert antes.bytes_pack != depois.bytes_pack or antes.respondeu != depois.respondeu, (
        f"desligar `_profundidades` nao mudou NADA em {pergunta.chave}: "
        f"recall {antes.respondeu}->{depois.respondeu}, "
        f"bytes {antes.bytes_pack}->{depois.bytes_pack}. A ancoragem no grafo "
        f"deixou de chegar ao pack -- ou o degrau foi removido, ou o escore "
        f"parou de consumi-lo."
    )


def test_nomes_do_pack_le_entry_points_e_symbols():
    """`montar()` fatia a lista ordenada em duas, e ler so uma da recall zero.

    `context.py:775` manda os primeiros para `entry_points` e o resto para
    `symbols`; `context.py:861` soma os dois para reportar `selected_symbols`.
    Ler so `symbols` daria zero justamente quando o simbolo exigido e o MAIS
    relevante -- o caso que a ferramenta acertou.
    """
    pacote = {
        "entry_points": [{"path": "a/job.py", "name": "principal", "qualified_name": "principal"}],
        "symbols": [{"path": "a/util.py", "name": "auxiliar", "qualified_name": "auxiliar"}],
    }
    achados = _nomes_do_pack(pacote)
    assert ("job.py", "principal") in achados
    assert ("util.py", "auxiliar") in achados


def test_nomes_do_pack_casa_metodo_pelo_nome_curto():
    """O extrator ancora `metodo`; o indice guarda `Classe.metodo`.

    Exigir so a forma qualificada perderia o caso em que o indice resolveu
    MELHOR do que o extrator ancorou.
    """
    pacote = {
        "symbols": [
            {"path": "x/job.py", "name": "roda", "qualified_name": "Pipeline.roda"}
        ]
    }
    achados = _nomes_do_pack(pacote)
    assert ("job.py", "roda") in achados
    assert ("job.py", "Pipeline.roda") in achados


def test_recall_e_booleano_por_simbolo_e_nunca_media():
    """9 de 10 simbolos exigidos e 90% e NAO responde a pergunta.

    O que falta pode ser exatamente o que a regra ancora, entao a media esconde
    o unico caso que importa.
    """
    medida = MedidaDeRecall(
        chave="R@f",
        pergunta_conceitual="t",
        nominal=(
            SimboloExigido("a.py", "um", True),
            SimboloExigido("a.py", "dois", False),
        ),
        conceitual=(),
        bytes_pack=1,
        bytes_arquivos=1,
        bytes_grep=1,
        bytes_por_nivel={},
    )
    assert medida.respondeu is False
    assert medida.faltaram == ("a.py::dois",)


def test_erro_derruba_o_recall_e_nao_a_medicao():
    """Regra 27: medicao nunca derruba a chamada -- mas erro nao vira aprovacao."""
    medida = MedidaDeRecall(
        chave="R@f",
        pergunta_conceitual="t",
        nominal=(SimboloExigido("a.py", "um", True),),
        conceitual=(),
        bytes_pack=0,
        bytes_arquivos=0,
        bytes_grep=0,
        bytes_por_nivel={},
        erro="indexar: boom",
    )
    assert medida.respondeu is False


def test_bytes_do_grep_conta_o_formato_do_grep_n(tmp_path):
    """O denominador adversarial precisa ser o que `grep -n` de fato imprime."""
    (tmp_path / "job.py").write_text(
        "import os\n\n\ndef alvo(x):\n    return x\n", encoding="utf-8"
    )
    medido = _bytes_do_grep(tmp_path, [("job.py", "alvo")])
    esperado = len(b"job.py:4:def alvo(x):\n")
    assert medido == esperado


def test_bytes_do_grep_ignora_mencao_que_nao_e_definicao(tmp_path):
    """`grep` pela DEFINICAO e o piso adversarial; mencao nao conta."""
    (tmp_path / "job.py").write_text(
        "def alvo(x):\n    return alvo(x - 1)\n", encoding="utf-8"
    )
    medido = _bytes_do_grep(tmp_path, [("job.py", "alvo")])
    assert medido == len(b"job.py:1:def alvo(x):\n")


def test_todos_os_niveis_de_detalhe_saem_medidos(medidas):
    esperados = {str(n) for n in NIVEIS}
    for medida in medidas:
        assert set(medida.bytes_por_nivel) == esperados, medida.chave


def test_summary_nao_e_maior_que_full(medidas):
    """`summary` que cresce nao e resumo -- e nome errado."""
    piores = [
        m.chave
        for m in medidas
        if m.bytes_por_nivel.get("summary", 0) > m.bytes_por_nivel.get("full", 0)
    ]
    assert not piores, f"summary maior que full em {piores}"


def test_o_efeito_de_detail_level_e_medido_e_pequeno(medidas):
    """Regra 28: antes de afirmar que `detail_level` reduz, leia o numero.

    MEDIDO em 2026-09-02 sobre as 23 perguntas: `full` 39220 bytes, `summary`
    38610 -- **1.5%**. O teste nao exige que reduza mais; ele impede que alguem
    escreva "detail_level reduz o pacote" sem olhar isto.
    """
    cheio = sum(m.bytes_por_nivel.get("full", 0) for m in medidas)
    resumo = sum(m.bytes_por_nivel.get("summary", 0) for m in medidas)
    reducao = (cheio - resumo) / cheio if cheio else 0.0
    assert 0.0 <= reducao < 0.10, (
        f"a reducao de `summary` sobre `full` e {reducao:.1%}, fora da faixa "
        f"medida em 2026-09-02 (1.5%). Se ela cresceu, algo passou a cortar de "
        f"verdade e o numero publicado precisa acompanhar."
    )


def test_no_nivel_full_nao_altera_o_pacote():
    corpo = {"symbols": [{"name": "a", "score_breakdown": {"fts": 1}}], "snippets": [1]}
    assert _no_nivel(corpo, "full") == corpo


def test_no_nivel_summary_derruba_snippet_e_quebra_de_escore():
    corpo = {"symbols": [{"name": "a", "score_breakdown": {"fts": 1}}], "snippets": [1]}
    magro = _no_nivel(corpo, "summary")
    assert magro["snippets"] == []
    assert "score_breakdown" not in magro["symbols"][0]
    assert magro["symbols"][0]["name"] == "a"


def test_a_medicao_nao_escreve_na_arvore_do_repositorio(medidas):
    """Indice deixado em `fixtures/` viraria artefato bruto que o CI teria de perdoar."""
    from sparkforge.economy.goldset import _RAIZ

    sujeira = [
        p.relative_to(_RAIZ).as_posix()
        for p in (_RAIZ / "fixtures").rglob("*.sqlite3")
    ]
    assert not sujeira, f"a medicao deixou indice na arvore: {sujeira}"
