"""Frescor, incremental, strict tree e worktree.

O teste central deste arquivo nao e nenhum dos casos isolados: e
`test_incremental_produz_o_mesmo_grafo_que_reconstrucao_completa`. Incremental
que erra, erra CALADO -- o grafo fica com uma aresta a menos e a travessia
devolve lista vazia, que e indistinguivel de "ninguem chama isto". Comparar o
resultado dos dois caminhos e a unica afirmacao que pega essa classe inteira de
defeito; os casos isolados existem para dizer QUAL deles quebrou quando ela
falhar.

Os testes de git NAO chamam `git`. Eles escrevem `.git/HEAD`, `.git/refs/...` e
`.git/packed-refs` a mao, porque e exatamente isso que o modulo le -- e porque
depender de um binario externo faria a suite falhar em maquina sem git por um
motivo que nao tem nada a ver com o que se afirma aqui.
"""

import sqlite3
import time

import pytest

from sparkforge.codeintel.db import abrir
from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.staleness import (
    ArvoreDivergente,
    IndiceAusente,
    IndiceDesatualizado,
    banco_da_arvore,
    conferir_arvore,
    detectar,
    estado_da_arvore,
    estado_gravado,
    garantir_frescor,
    sincronizar,
)

_SEM_COOLDOWN = {"cooldown_s": 0.0}


def _escrever(caminho, texto):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def _grafo(banco):
    """Nos e arestas por NOME, e nao por id.

    Por nome porque `node_id` deriva da assinatura: comparar ids entre dois
    bancos casaria por construcao e nao afirmaria nada sobre a aresta ter
    sobrevivido. O nome qualificado e o que um consumidor de verdade pergunta.
    """
    conexao = sqlite3.connect(banco)
    try:
        nos = sorted(
            conexao.execute(
                "SELECT files.path, nodes.qualified_name FROM nodes"
                " JOIN files ON files.id = nodes.file_id"
            )
        )
        arestas = sorted(
            conexao.execute(
                "SELECT origem.path, fonte.qualified_name, destino.path,"
                "       alvo.qualified_name, edges.kind, edges.line"
                "  FROM edges"
                "  JOIN nodes AS fonte ON fonte.id = edges.source_id"
                "  JOIN files AS origem ON origem.id = fonte.file_id"
                "  JOIN nodes AS alvo ON alvo.id = edges.target_id"
                "  JOIN files AS destino ON destino.id = alvo.file_id"
            )
        )
        cegos = sorted(
            conexao.execute(
                "SELECT files.path, unresolved_refs.reference_name,"
                "       unresolved_refs.line, unresolved_refs.reason"
                "  FROM unresolved_refs"
                "  JOIN files ON files.id = unresolved_refs.file_id"
            )
        )
    finally:
        conexao.close()
    return nos, arestas, cegos


def _arvore_com_chamada_cruzada(raiz):
    _escrever(raiz / "lib.py", "def processar(dado):\n    return dado\n")
    _escrever(
        raiz / "job.py",
        "from lib import processar\n\n\ndef executar():\n    return processar(1)\n",
    )
    _escrever(raiz / "outro.py", "def solto():\n    return 2\n")


# --------------------------------------------------------------------------
# SPEC 42 -- deteccao
# --------------------------------------------------------------------------


def test_detectar_classifica_cada_arquivo_pelo_que_ele_obriga(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    _escrever(tmp_path / "b.py", "def g():\n    pass\n")
    indexar(tmp_path, banco)

    _escrever(tmp_path / "b.py", "def g():\n    return 1\n")
    _escrever(tmp_path / "c.py", "def h():\n    pass\n")
    (tmp_path / "a.py").unlink()

    conexao = abrir(banco)
    try:
        mudancas = detectar(tmp_path, conexao)
    finally:
        conexao.close()

    assert mudancas.alterados == ("b.py",)
    assert mudancas.novos == ("c.py",)
    assert mudancas.removidos == ("a.py",)
    assert mudancas.quantidade == 3
    assert not mudancas.vazio


def test_detectar_sem_mudanca_devolve_vazio(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    indexar(tmp_path, banco)

    conexao = abrir(banco)
    try:
        mudancas = detectar(tmp_path, conexao)
    finally:
        conexao.close()

    assert mudancas.vazio
    assert mudancas.inalterados == ("a.py",)


def test_mtime_novo_com_mesmo_conteudo_nao_conta_como_alterado(tmp_path):
    """O sha existe para este caso: `git checkout` reescreve mtime sem mudar nada."""
    banco = tmp_path / "graph.sqlite3"
    alvo = _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    indexar(tmp_path, banco)

    informacao = alvo.stat()
    # Rebobina o mtime em vez de avancar: `time.sleep` para atravessar a
    # resolucao do relogio deixaria o teste lento e dependente da plataforma.
    novo = informacao.st_mtime_ns - 10_000_000_000
    import os

    os.utime(alvo, ns=(novo, novo))

    conexao = abrir(banco)
    try:
        mudancas = detectar(tmp_path, conexao)
    finally:
        conexao.close()

    assert mudancas.alterados == ()
    assert mudancas.tocados == ("a.py",)
    assert mudancas.vazio


def test_sincronizar_alinha_o_mtime_do_arquivo_so_tocado(tmp_path):
    """Sem isto, todo checkout faria rehashear os mesmos arquivos para sempre."""
    import os

    banco = tmp_path / "graph.sqlite3"
    alvo = _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    indexar(tmp_path, banco)

    novo = alvo.stat().st_mtime_ns - 10_000_000_000
    os.utime(alvo, ns=(novo, novo))
    sincronizar(tmp_path, banco)

    conexao = abrir(banco)
    try:
        (gravado,) = conexao.execute(
            "SELECT modified_ns FROM files WHERE path = 'a.py'"
        ).fetchone()
        mudancas = detectar(tmp_path, conexao)
    finally:
        conexao.close()

    assert gravado == alvo.stat().st_mtime_ns
    assert mudancas.tocados == ()


# --------------------------------------------------------------------------
# SPEC 42 -- sincronizacao
# --------------------------------------------------------------------------


def test_banco_ausente_cai_para_reconstrucao_completa(tmp_path):
    _arvore_com_chamada_cruzada(tmp_path)
    resultado = sincronizar(tmp_path, tmp_path / "graph.sqlite3")
    assert resultado.completa
    assert resultado.arquivos == 3


def test_sincronizacao_seguinte_nao_e_completa(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _arvore_com_chamada_cruzada(tmp_path)
    sincronizar(tmp_path, banco)

    _escrever(tmp_path / "outro.py", "def solto():\n    return 3\n")
    resultado = sincronizar(tmp_path, banco)

    assert not resultado.completa
    assert resultado.mudancas.alterados == ("outro.py",)
    assert resultado.arquivos == 1


def test_arquivo_apagado_sai_do_indice_e_do_fts(tmp_path):
    """FTS5 e tabela virtual: o `ON DELETE CASCADE` nao a alcanca."""
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "antigo.py", "def sumir():\n    pass\n")
    _escrever(tmp_path / "fica.py", "def ficar():\n    pass\n")
    sincronizar(tmp_path, banco)

    (tmp_path / "antigo.py").unlink()
    sincronizar(tmp_path, banco)

    conexao = sqlite3.connect(banco)
    try:
        caminhos = [linha[0] for linha in conexao.execute("SELECT path FROM files")]
        no_fts = [
            linha[0] for linha in conexao.execute("SELECT qualified_name FROM symbols_fts")
        ]
    finally:
        conexao.close()

    assert caminhos == ["fica.py"]
    assert "sumir" not in no_fts


def test_aresta_para_alvo_com_assinatura_nova_e_recriada(tmp_path):
    """O caso 1 da docstring do modulo: mudar a assinatura muda o `node_id`.

    Sem `_fontes_dependentes`, a aresta de `job.executar` para `lib.processar`
    cairia no CASCADE e ninguem a recriaria -- `job.py` nao foi tocado.
    """
    banco = tmp_path / "graph.sqlite3"
    _arvore_com_chamada_cruzada(tmp_path)
    sincronizar(tmp_path, banco)
    _, antes, _ = _grafo(banco)
    assert any(linha[3] == "processar" for linha in antes)

    _escrever(tmp_path / "lib.py", "def processar(dado, extra=None):\n    return dado\n")
    sincronizar(tmp_path, banco)

    _, depois, _ = _grafo(banco)
    assert any(
        linha[0] == "job.py" and linha[1] == "executar" and linha[3] == "processar"
        for linha in depois
    ), depois


def test_aresta_volta_mesmo_quando_o_alvo_e_reinserido_identico(tmp_path):
    """O caso 2: o no reinserido tem o mesmo id, e a aresta de terceiro nao volta sozinha."""
    banco = tmp_path / "graph.sqlite3"
    _arvore_com_chamada_cruzada(tmp_path)
    sincronizar(tmp_path, banco)

    # Corpo diferente, assinatura igual: o `node_id` nao muda, o arquivo muda.
    _escrever(tmp_path / "lib.py", "def processar(dado):\n    return dado + 0\n")
    sincronizar(tmp_path, banco)

    _, arestas, _ = _grafo(banco)
    assert any(
        linha[1] == "executar" and linha[3] == "processar" for linha in arestas
    ), arestas


def test_ponto_cego_vira_aresta_quando_a_definicao_aparece(tmp_path):
    """O caso 3: o arquivo que CHAMA nao mudou, e a resposta dele mudou."""
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "job.py", "def executar():\n    return ainda_nao_existe()\n")
    sincronizar(tmp_path, banco)
    _, arestas, cegos = _grafo(banco)
    assert arestas == []
    assert any(linha[1] == "ainda_nao_existe" for linha in cegos)

    _escrever(tmp_path / "job.py", "def executar():\n    return ainda_nao_existe()\n")
    _escrever(tmp_path / "lib.py", "def ainda_nao_existe():\n    return 1\n")
    # `job.py` foi reescrito identico ao que ja estava, entao ele conta como
    # INALTERADO -- e a afirmacao so vale por isso.
    resultado = sincronizar(tmp_path, banco)
    assert "job.py" not in resultado.mudancas.alterados
    assert "job.py" in resultado.reresolvidos

    _, arestas, _ = _grafo(banco)
    assert any(linha[3] == "ainda_nao_existe" for linha in arestas), arestas


def test_sincronizar_duas_vezes_nao_duplica_aresta(tmp_path):
    """`edges` nao tem chave unica de proposito -- entao duplicar nao levanta."""
    banco = tmp_path / "graph.sqlite3"
    _arvore_com_chamada_cruzada(tmp_path)
    sincronizar(tmp_path, banco)

    for corpo in ("    return dado\n", "    return dado + 0\n"):
        _escrever(tmp_path / "lib.py", f"def processar(dado):\n{corpo}")
        sincronizar(tmp_path, banco)

    _, arestas, cegos = _grafo(banco)
    assert len(arestas) == len(set(arestas))
    assert len(cegos) == len(set(cegos))


def test_incremental_produz_o_mesmo_grafo_que_reconstrucao_completa(tmp_path):
    """A afirmacao central: os dois caminhos tem que chegar ao mesmo grafo.

    Sete edicoes de formas diferentes -- assinatura nova, corpo novo, arquivo
    novo, arquivo apagado, definicao acrescentada que resolve ponto cego,
    definicao duplicada que cria ambiguidade -- e no fim os dois bancos sao
    comparados no, aresta e ponto cego a ponto cego.
    """
    incremental = tmp_path / "inc" / "graph.sqlite3"
    completo = tmp_path / "full" / "graph.sqlite3"
    incremental.parent.mkdir()
    completo.parent.mkdir()
    fonte = tmp_path / "src"
    fonte.mkdir()

    _arvore_com_chamada_cruzada(fonte)
    _escrever(fonte / "cego.py", "def chamar():\n    return orfao()\n")
    sincronizar(fonte, incremental)

    _escrever(fonte / "lib.py", "def processar(dado, extra=None):\n    return dado\n")
    _escrever(fonte / "orfao_def.py", "def orfao():\n    return 0\n")
    (fonte / "outro.py").unlink()
    _escrever(
        fonte / "pkg" / "mod.py",
        "from lib import processar\n\n\nclass Fluxo:\n"
        "    def rodar(self):\n        return processar(2)\n",
    )
    sincronizar(fonte, incremental)

    _escrever(fonte / "lib2.py", "def processar(dado):\n    return dado\n")
    sincronizar(fonte, incremental)

    indexar(fonte, completo)

    assert _grafo(incremental) == _grafo(completo)


def test_reconstruir_do_zero_e_sincronizar_dao_o_mesmo_grafo_sobre_este_repositorio(
    tmp_path,
):
    """Escala real. Tmpdir esconde defeito que so aparece com 391 arquivos.

    Tres sincronizacoes e nao duas, e a terceira e a afirmacao: a primeira cai
    para reconstrucao completa (banco ausente) e `indexar` NAO grava linha em
    `files` para o arquivo que nao parseia; a segunda grava -- ver o comentario
    em `_indexar_um` --; so a terceira pode ser vazia. Uma rodada de
    convergencia e o preco declarado da divergencia, e prende-lo aqui e o que
    impede que ele vire duas, ou infinitas.
    """
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1]
    incremental = tmp_path / "inc.sqlite3"
    completo = tmp_path / "full.sqlite3"

    primeira = sincronizar(raiz, incremental)
    indexar(raiz, completo)
    segunda = sincronizar(raiz, incremental)
    terceira = sincronizar(raiz, incremental)

    assert primeira.completa
    assert not segunda.completa
    assert segunda.mudancas.novos == (
        "fixtures/graph/fonte_que_nao_compila/input/carga_quebrada.py",
    )
    assert terceira.mudancas.vazio
    assert _grafo(incremental) == _grafo(completo)


# --------------------------------------------------------------------------
# SPEC 45 -- git lido, nunca executado
# --------------------------------------------------------------------------


def _fabricar_git(raiz, *, head="ref: refs/heads/main", refs=None, packed=None):
    git = raiz / ".git"
    git.mkdir(parents=True, exist_ok=True)
    (git / "HEAD").write_text(head + "\n", encoding="utf-8")
    for nome, sha in (refs or {}).items():
        _escrever(git / nome, sha + "\n")
    if packed is not None:
        (git / "packed-refs").write_text(packed, encoding="utf-8")
    return git


def test_le_sha_de_ref_solta(tmp_path):
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    estado = estado_da_arvore(tmp_path)
    assert estado.head == "a" * 40
    assert estado.ref == "refs/heads/main"
    assert estado.identidade


def test_ref_solta_ganha_de_packed_refs(tmp_path):
    """`git gc` empacota e um commit posterior reescreve a solta -- as duas existem."""
    _fabricar_git(
        tmp_path,
        refs={"refs/heads/main": "b" * 40},
        packed=f"# pack-refs with: peeled\n{'a' * 40} refs/heads/main\n",
    )
    assert estado_da_arvore(tmp_path).head == "b" * 40


def test_packed_refs_quando_nao_ha_ref_solta(tmp_path):
    _fabricar_git(
        tmp_path,
        packed=(
            "# pack-refs with: peeled fully-peeled sorted\n"
            f"{'c' * 40} refs/tags/v1\n"
            f"^{'d' * 40}\n"
            f"{'e' * 40} refs/heads/main\n"
        ),
    )
    assert estado_da_arvore(tmp_path).head == "e" * 40


def test_head_destacado_tem_sha_e_nao_tem_ref(tmp_path):
    _fabricar_git(tmp_path, head="f" * 40)
    estado = estado_da_arvore(tmp_path)
    assert estado.head == "f" * 40
    assert estado.ref == ""


def test_ref_que_sairia_de_refs_e_recusada(tmp_path):
    """`INV-014` e `INV-002`: `HEAD` e conteudo de repositorio, e vira caminho."""
    _fabricar_git(tmp_path, head="ref: ../../../../etc/passwd")
    estado = estado_da_arvore(tmp_path)
    assert estado.head == ""
    assert estado.ref == ""


def test_ref_com_ponto_ponto_no_meio_e_recusada(tmp_path):
    _fabricar_git(tmp_path, head="ref: refs/heads/../../../segredo")
    assert estado_da_arvore(tmp_path).ref == ""


def test_arvore_sem_git_nao_levanta_e_ainda_tem_impressao(tmp_path):
    estado = estado_da_arvore(tmp_path)
    assert estado.head == ""
    assert estado.identidade == ""
    assert estado.impressao


def test_branch_sem_commit_devolve_ref_e_sha_vazio(tmp_path):
    _fabricar_git(tmp_path)
    estado = estado_da_arvore(tmp_path)
    assert estado.ref == "refs/heads/main"
    assert estado.head == ""


def test_worktree_com_git_arquivo_encontra_head_proprio_e_refs_comuns(tmp_path):
    """SPEC 46: worktree tem `HEAD` proprio e `refs/` no diretorio comum."""
    principal = _fabricar_git(tmp_path / "principal", refs={"refs/heads/tema": "9" * 40})
    arvore = tmp_path / "arvore"
    arvore.mkdir()
    interno = principal / "worktrees" / "arvore"
    interno.mkdir(parents=True)
    (interno / "HEAD").write_text("ref: refs/heads/tema\n", encoding="utf-8")
    (interno / "commondir").write_text("../..\n", encoding="utf-8")
    (arvore / ".git").write_text(f"gitdir: {interno}\n", encoding="utf-8")

    estado = estado_da_arvore(arvore)
    assert estado.head == "9" * 40
    assert estado.ref == "refs/heads/tema"


# --------------------------------------------------------------------------
# SPEC 46 -- namespace de worktree
# --------------------------------------------------------------------------


def test_branches_diferentes_dao_bancos_diferentes(tmp_path):
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    um = banco_da_arvore(tmp_path)
    _fabricar_git(
        tmp_path,
        head="ref: refs/heads/feature/glue6",
        refs={"refs/heads/feature/glue6": "a" * 40},
    )
    outro = banco_da_arvore(tmp_path)

    assert um != outro
    assert um.name.startswith("main-")
    assert outro.name.startswith("feature-glue6-")
    assert um.parent == outro.parent


def test_commit_novo_nao_muda_o_nome_do_banco(tmp_path):
    """Incluir `head` no sufixo encheria o disco de um indice por commit."""
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    antes = banco_da_arvore(tmp_path)
    _fabricar_git(tmp_path, refs={"refs/heads/main": "b" * 40})
    assert banco_da_arvore(tmp_path) == antes


def test_arvores_diferentes_no_mesmo_branch_nao_compartilham_banco(tmp_path):
    uma = tmp_path / "uma"
    outra = tmp_path / "outra"
    uma.mkdir()
    outra.mkdir()
    _fabricar_git(uma, refs={"refs/heads/main": "a" * 40})
    _fabricar_git(outra, refs={"refs/heads/main": "a" * 40})
    assert banco_da_arvore(uma).name != banco_da_arvore(outra).name


def test_head_destacado_nao_vira_nome_de_caminho(tmp_path):
    _fabricar_git(tmp_path, head="f" * 40)
    assert banco_da_arvore(tmp_path).name.startswith("detached-")


# --------------------------------------------------------------------------
# SPEC 44 -- strict tree
# --------------------------------------------------------------------------


def test_indice_sem_estado_de_arvore_e_negado(tmp_path):
    """`indexar` nao grava estado -- e presumir fresco o desconhecido e o defeito."""
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    indexar(tmp_path, banco)

    conexao = abrir(banco)
    try:
        assert estado_gravado(conexao) is None
        with pytest.raises(ArvoreDivergente) as erro:
            conferir_arvore(tmp_path, conexao)
    finally:
        conexao.close()
    assert erro.value.payload["reason"] == "NO_TREE_STATE"
    assert erro.value.payload["error"] == "TREE_MISMATCH"


def test_sincronizar_grava_o_estado_e_a_conferencia_passa(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    conexao = abrir(banco)
    try:
        conferir_arvore(tmp_path, conexao)
        gravado = estado_gravado(conexao)
    finally:
        conexao.close()
    assert gravado.head == "a" * 40
    assert gravado.ref == "refs/heads/main"


def test_head_diferente_nega_a_query(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    _fabricar_git(tmp_path, refs={"refs/heads/main": "b" * 40})
    conexao = abrir(banco)
    try:
        with pytest.raises(ArvoreDivergente) as erro:
            conferir_arvore(tmp_path, conexao)
    finally:
        conexao.close()
    assert erro.value.payload["index_head"] == "a" * 40
    assert erro.value.payload["tree_head"] == "b" * 40


def test_troca_de_branch_nega_mesmo_sem_mudar_arquivo(tmp_path):
    """E o caso que staleness de conteudo NAO pega: nenhum `*.py` mudou."""
    banco = tmp_path / "graph.sqlite3"
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    _fabricar_git(
        tmp_path, head="ref: refs/heads/outro", refs={"refs/heads/outro": "a" * 40}
    )
    conexao = abrir(banco)
    try:
        mudancas = detectar(tmp_path, conexao)
        with pytest.raises(ArvoreDivergente):
            conferir_arvore(tmp_path, conexao)
    finally:
        conexao.close()
    assert mudancas.vazio


# --------------------------------------------------------------------------
# SPEC 43 -- frescor automatico
# --------------------------------------------------------------------------


def test_indice_ausente_recusa_em_vez_de_indexar(tmp_path):
    with pytest.raises(IndiceAusente) as erro:
        garantir_frescor(tmp_path, tmp_path / "nao_existe.sqlite3")
    assert erro.value.payload["error"] == "INDEX_MISSING"


def test_mudanca_pequena_e_sincronizada_na_hora(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _arvore_com_chamada_cruzada(tmp_path)
    sincronizar(tmp_path, banco)

    _escrever(tmp_path / "outro.py", "def solto():\n    return 99\n")
    frescor = garantir_frescor(tmp_path, banco, **_SEM_COOLDOWN)

    assert frescor.sincronizou
    assert frescor.mudancas.quantidade == 1
    conexao = abrir(banco)
    try:
        assert detectar(tmp_path, conexao).vazio
    finally:
        conexao.close()


def test_mudanca_grande_recusa_com_a_contagem_e_a_acao(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    for indice in range(4):
        _escrever(tmp_path / f"m{indice}.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    for indice in range(4):
        _escrever(tmp_path / f"m{indice}.py", f"def f():\n    return {indice}\n")

    with pytest.raises(IndiceDesatualizado) as erro:
        garantir_frescor(tmp_path, banco, max_auto_sync_files=3, **_SEM_COOLDOWN)

    assert erro.value.payload == {
        "error": "STALE_INDEX",
        "action": "sparkforge code sync",
        "changed_files": 4,
    }


def test_o_teto_default_da_spec_e_vinte_e_cinco(tmp_path):
    """Sem exercitar o DEFAULT, o valor da SPEC 43 podia ser qualquer um.

    Todo outro teste de recusa passa `max_auto_sync_files` explicito, entao
    trocar a constante por um numero enorme deixava a suite verde -- mutacao
    medida e sobrevivente antes deste teste existir. 26 arquivos alterados e o
    primeiro degrau acima do teto.
    """
    banco = tmp_path / "graph.sqlite3"
    for indice in range(26):
        _escrever(tmp_path / f"m{indice}.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    for indice in range(26):
        _escrever(tmp_path / f"m{indice}.py", f"def f():\n    return {indice}\n")

    with pytest.raises(IndiceDesatualizado) as erro:
        garantir_frescor(tmp_path, banco, **_SEM_COOLDOWN)
    assert erro.value.payload["changed_files"] == 26


def test_banco_de_outra_raiz_e_reconstruido_e_nao_reaproveitado(tmp_path):
    """Todo `files.path` e relativo a raiz que o gravou -- misturar produz caminho falso."""
    banco = tmp_path / "graph.sqlite3"
    uma = tmp_path / "uma"
    outra = tmp_path / "outra"
    _escrever(uma / "so_da_uma.py", "def da_uma():\n    pass\n")
    _escrever(outra / "so_da_outra.py", "def da_outra():\n    pass\n")

    sincronizar(uma, banco)
    resultado = sincronizar(outra, banco)

    assert resultado.completa
    nos, _, _ = _grafo(banco)
    assert [linha[0] for linha in nos] == ["so_da_outra.py"]


def test_sem_auto_sync_recusa_em_vez_de_escrever(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)
    _escrever(tmp_path / "a.py", "def f():\n    return 1\n")

    with pytest.raises(IndiceDesatualizado):
        garantir_frescor(tmp_path, banco, auto_sync=False, **_SEM_COOLDOWN)

    conexao = abrir(banco)
    try:
        assert detectar(tmp_path, conexao).alterados == ("a.py",)
    finally:
        conexao.close()


def test_sem_mudanca_nao_sincroniza_e_diz_que_conferiu(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    frescor = garantir_frescor(tmp_path, banco, **_SEM_COOLDOWN)
    assert frescor.verificou
    assert not frescor.sincronizou
    assert frescor.mudancas.vazio


def test_cooldown_pula_a_varredura_de_disco(tmp_path):
    """A janela de 30 s da SPEC 43 e uma escolha declarada, entao ela e afirmada."""
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    _escrever(tmp_path / "a.py", "def f():\n    return 1\n")
    frescor = garantir_frescor(tmp_path, banco)

    assert not frescor.verificou
    assert not frescor.sincronizou


def test_cooldown_nao_pula_depois_de_veredito_stale(tmp_path):
    """Cooldown que ignora o veredito daria 30 s respondendo com grafo velho."""
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)
    _escrever(tmp_path / "a.py", "def f():\n    return 1\n")

    with pytest.raises(IndiceDesatualizado):
        garantir_frescor(tmp_path, banco, max_auto_sync_files=0, **_SEM_COOLDOWN)

    # Cooldown default agora: o carimbo e de milissegundos atras, e mesmo assim
    # a porta nao pula, porque o veredito gravado foi STALE.
    frescor = garantir_frescor(tmp_path, banco)
    assert frescor.verificou
    assert frescor.sincronizou


def test_arvore_divergente_sem_arquivo_mudado_sincroniza_e_grava_o_estado(tmp_path):
    """Zero arquivo para reindexar, e ainda assim ha o que gravar: o estado."""
    banco = tmp_path / "graph.sqlite3"
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)

    _fabricar_git(tmp_path, refs={"refs/heads/main": "b" * 40})
    frescor = garantir_frescor(tmp_path, banco)

    assert frescor.sincronizou
    conexao = abrir(banco)
    try:
        conferir_arvore(tmp_path, conexao)
    finally:
        conexao.close()


def test_arvore_divergente_com_auto_sync_desligado_levanta_divergencia(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _fabricar_git(tmp_path, refs={"refs/heads/main": "a" * 40})
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    sincronizar(tmp_path, banco)
    _fabricar_git(tmp_path, refs={"refs/heads/main": "b" * 40})

    with pytest.raises(ArvoreDivergente):
        garantir_frescor(tmp_path, banco, auto_sync=False)


def test_veredito_fresco_e_carimbado_com_a_hora(tmp_path):
    banco = tmp_path / "graph.sqlite3"
    _escrever(tmp_path / "a.py", "def f():\n    pass\n")
    antes = time.time_ns()
    sincronizar(tmp_path, banco)

    conexao = abrir(banco)
    try:
        gravado = dict(
            conexao.execute(
                "SELECT key, value FROM metadata WHERE key IN"
                " ('freshness_checked_ns', 'freshness_verdict')"
            )
        )
    finally:
        conexao.close()
    assert gravado["freshness_verdict"] == "fresh"
    assert int(gravado["freshness_checked_ns"]) >= antes
