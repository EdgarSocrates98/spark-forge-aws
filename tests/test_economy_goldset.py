"""O gold set deriva das regras, e a derivacao nao inventa nada.

Ver `sparkforge/economy/goldset.py` para por que ele e derivado e nunca
versionado como arquivo.
"""

from __future__ import annotations

import json

import pytest

from sparkforge.economy.goldset import (
    _RAIZ,
    EXTENSOES_INDEXADAS,
    ForaDoAlcance,
    derivar_goldset,
    fora_do_alcance,
)

# Medido em 2026-09-02, e SUBIU de 23 para 27 na entrega da ponte, cujas tres
# fixtures ancoram simbolo. Subir e progresso, e o piso sobe no commit que o
# fez subir. PISO, nunca igualdade -- ver a mesma decisao em
# `scripts/check_recall_economy.py:PISO_DE_PERGUNTAS`.
PISO_DE_PERGUNTAS = 27
PISO_DE_REGRAS = 18  # inalterado: as 4 novas vem de regras ja cobertas


@pytest.fixture(scope="module")
def goldset():
    return derivar_goldset()


def test_o_goldset_nao_existe_como_arquivo_versionado():
    """Gold set em arquivo e a segunda copia da verdade, e envelhece calada.

    Este teste falha se alguem "otimizar" a derivacao congelando-a em JSON. O
    ganho seria alguns milissegundos; o custo seria um gate que afirma sobre
    regras que mudaram sem ele saber.
    """
    suspeitos = [
        p.relative_to(_RAIZ).as_posix()
        for p in _RAIZ.rglob("*goldset*")
        if p.suffix in {".json", ".yaml", ".yml"}
    ]
    assert not suspeitos, (
        f"o gold set aparece como arquivo versionado em {suspeitos}. Ele e "
        f"DERIVADO das regras a cada execucao de proposito: congelado, ele passa "
        f"a afirmar sobre a ancoragem de ontem enquanto as regras mudam hoje."
    )


def test_o_piso_de_perguntas_se_sustenta(goldset):
    assert len(goldset) >= PISO_DE_PERGUNTAS, (
        f"{len(goldset)} perguntas derivadas, piso {PISO_DE_PERGUNTAS}. Cair "
        f"significa que alguma regra perdeu ancoragem de simbolo `.py` na "
        f"evidencia -- e defeito, nao ajuste de piso."
    )


def test_o_piso_de_regras_cobertas_se_sustenta(goldset):
    regras = {p.rule_id for p in goldset}
    assert len(regras) >= PISO_DE_REGRAS, (
        f"{len(regras)} regras cobertas, piso {PISO_DE_REGRAS}."
    )


def test_toda_pergunta_exige_pelo_menos_um_simbolo(goldset):
    """Pergunta sem simbolo exigido nao mede recall -- mede que algo voltou."""
    vazias = [p.chave for p in goldset if not p.simbolos_exigidos]
    assert not vazias, f"perguntas sem simbolo exigido: {vazias}"


def test_todo_simbolo_exigido_esta_em_arquivo_indexavel(goldset):
    """Exigir simbolo de arquivo que o indexador nao le seria vermelho sem defeito."""
    fora = [
        f"{p.chave}: {arquivo}"
        for p in goldset
        for arquivo, _ in p.simbolos_exigidos
        if not arquivo.endswith(EXTENSOES_INDEXADAS)
    ]
    assert not fora, (
        f"simbolo exigido em arquivo que `codeintel.index.indexar` nao percorre: "
        f"{fora}. Ou o arquivo entra em EXTENSOES_INDEXADAS junto com um extrator "
        f"que o leia, ou a pergunta sai para `fora_do_alcance`."
    )


def test_toda_entrada_de_fixture_existe(goldset):
    ausentes = [p.chave for p in goldset if not p.entrada.is_dir()]
    assert not ausentes, f"fixtures sem `input/`: {ausentes}"


def test_o_simbolo_exigido_esta_de_fato_no_arquivo(goldset):
    """A ancoragem que a regra cita tem de existir no fonte.

    Este e o teste que separa "derivei da evidencia" de "derivei de um campo que
    ninguem manteve": se um extrator passar a ancorar simbolo que nao existe no
    arquivo, o gold set exigiria do pack algo impossivel, e o vermelho apontaria
    para o lugar errado.
    """
    faltando = []
    for pergunta in goldset:
        for arquivo, simbolo in pergunta.simbolos_exigidos:
            achou = False
            for caminho in pergunta.entrada.rglob(arquivo):
                texto = caminho.read_text(encoding="utf-8", errors="replace")
                achou = f"def {simbolo}" in texto or f"class {simbolo}" in texto
                break
            if not achou:
                faltando.append(f"{pergunta.chave}: {arquivo}::{simbolo}")
    assert not faltando, (
        f"a evidencia ancora simbolo que nao esta definido no arquivo: {faltando}"
    )


def test_a_pergunta_vem_do_titulo_da_regra(goldset):
    """Pergunta escrita a mao aqui mediria a minha suposicao, nao a do repo."""
    from sparkforge.rules.loader import load_catalog

    titulos = {r["id"]: r.get("title", r["id"]) for r in load_catalog()}
    divergentes = [
        p.chave for p in goldset if p.pergunta != titulos.get(p.rule_id, p.rule_id)
    ]
    assert not divergentes, f"pergunta divergente do titulo da regra: {divergentes}"


def test_as_duas_razoes_de_recusa_tem_medidas_diferentes():
    """Somar as duas razoes num rotulo so apagaria a diferenca que importa.

    Uma destrava no INDEXADOR (ler outra extensao), a outra no EXTRATOR
    (preencher `subject.symbol`). Um rotulo unico mandaria quem for consertar
    para o modulo errado.
    """
    a = ForaDoAlcance("f", "R", "extensao_nao_indexada", (".tf",))
    b = ForaDoAlcance("f", "R", "evidencia_sem_simbolo")
    assert a.medida_que_destravaria != b.medida_que_destravaria
    assert "EXTENSOES_INDEXADAS" in a.medida_que_destravaria
    assert "subject.symbol" in b.medida_que_destravaria


def test_toda_recusa_declara_razao_conhecida():
    conhecidas = {"extensao_nao_indexada", "evidencia_sem_simbolo"}
    desconhecidas = {f.razao for f in fora_do_alcance()} - conhecidas
    assert not desconhecidas, f"razao de recusa sem tratamento: {desconhecidas}"


def test_a_recusa_e_maior_que_o_goldset_e_isso_esta_declarado(goldset):
    """Metade dos achados destas fixtures nao rende pergunta, e o gate diz isso.

    Medido em 2026-09-02: 23 perguntas contra 25 recusas em 48 achados. Um gate
    que reportasse so as 23 esconderia o proprio denominador -- "cobre 23
    achados" seria lido como "existem 23 achados".
    """
    recusas = fora_do_alcance()
    assert recusas, "nenhuma recusa: ou o corpus mudou, ou a derivacao parou de listar"
    assert len(goldset) + len(recusas) > len(goldset), (
        "a soma tem de exceder o gold set, ou nada esta sendo recusado"
    )


def test_a_derivacao_e_estavel_entre_chamadas(goldset):
    """Ordem instavel faria o gate divergir sem que nada mudasse."""
    assert [p.chave for p in derivar_goldset()] == [p.chave for p in goldset]


def test_json_malformado_nao_derruba_a_derivacao(tmp_path, monkeypatch):
    """Medicao nunca derruba a chamada (regra 27) -- vale para a derivacao tambem."""
    from sparkforge.economy import goldset as modulo

    raiz = tmp_path
    base = raiz / "fixtures" / "x" / "quebrada"
    (base / "input").mkdir(parents=True)
    (base / "input" / "job.py").write_text("def f():\n    pass\n", encoding="utf-8")
    (base / "expected").mkdir()
    (base / "expected" / "findings.json").write_text("{ nao e json", encoding="utf-8")
    (base / "expected" / "facts.json").write_text(json.dumps([]), encoding="utf-8")

    monkeypatch.setattr(modulo, "_RAIZ", raiz)
    assert derivar_goldset() == ()
