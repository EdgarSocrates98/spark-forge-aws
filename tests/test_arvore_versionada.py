"""Todo modulo importado do pacote esta versionado no git.

POR QUE ESTE ARQUIVO EXISTE: `sparkforge/paths.py` ficou DEZ commits sem entrar
no git. O commit `4240035` acrescentou `from sparkforge.paths import
resolve_within` a `rules/loader.py`, `agents/autonomy.py` e `knowledge_ref.py`,
e nunca fez `git add` do arquivo. Um clone limpo de qualquer commit entre
`4240035` e `263917a` falha ao importar os tres.

E passou por TUDO: dez execucoes da suite completa, ruff, o gate de lastro, uma
revisao de conformidade e uma de qualidade. A razao e que o pacote esta
instalado em modo editavel, entao `sparkforge.paths` resolve para a arvore de
trabalho -- onde o arquivo existe. Nenhum gate deste repositorio olhava para o
que o GIT tem, so para o que o disco tem.

Foi encontrado por acidente, por alguem que conferiu num worktree limpo enquanto
media outra coisa.

Este gate compara as duas visoes. Ele nao substitui o teste de wheel
(`scripts/verify_wheel.py`), que exercita o pacote construido: aquele pega
arquivo que o BUILD nao leva, este pega arquivo que o COMMIT nao leva. Sao
falhas diferentes e o segundo e mais barato de rodar.

SEGUNDA RODADA -- O MESMO DEFEITO FORA DO `.py`
-----------------------------------------------
A cobertura acima so olha `sparkforge/**/*.py`, e duas vezes seguidas a mesma
familia de falha apareceu em arquivo GERADO, que o teste de `.py` nao ve:

  1. `agents/sf-context-engineer.md` ganhou o bloco "Indice de codigo" e foi
     commitado SOZINHO. Os tres espelhos -- `.claude/agents/`, `.agents/agents/`
     e `.github/agents/` -- so receberam as 66 linhas quando alguem rodou
     `scripts/sync_skills.py` DEPOIS do commit. O commit `c82a45e` ficou com a
     fonte nova e os tres espelhos velhos; `17ed2ed` consertou.
  2. `manifest.json` declarava 44 tools com o catalogo real em 50.

O que faz o caso 1 escapar de CINCO gates nao e falta de gate -- e o gate se
CONSERTAR sozinho antes de olhar. Mecanismo medido, em duas camadas:

  - `tests/test_agents_parity.py::TestMirrors::test_sync_check_passes_after_sync`
    roda `sync_skills.py` (modo ESCRITA) e so entao `--check`. Depois da
    regeneracao nao ha o que divergir: o teste e estruturalmente incapaz de
    falhar, e de quebra deixa o disco a frente do git.
  - `.github/workflows/ci.yml` roda `Test suite` (pytest) ANTES do passo
    `Mirror sync` (`sync_skills.py --check`). Quando o `--check` do CI chega, a
    suite ja regenerou os espelhos no disco do runner. O passo dedicado do CI
    tambem nao pode falhar.

Ou seja: o unico gate que existia para espelho olhava para um disco que ele
mesmo acabara de arrumar. A saida e olhar para uma fonte que
`sync_skills.sync()` nao consegue escrever -- os OBJETOS DO GIT. Ver
`test_espelho_gerado_esta_em_dia_no_commit`.

QUAL E A RELACAO REAL ENTRE OS ESPELHOS (e por que nao e byte a byte)
--------------------------------------------------------------------
Exigir igualdade byte a byte entre `agents/x.md` e os tres espelhos seria
FALSO, e um gate falso e desligado no primeiro alarme -- ai nao protege nada.
A relacao verdadeira, declarada em `scripts/sync_skills.py`, e:

  - `.claude/agents/x.md`        passthrough byte a byte da fonte
  - `.github/agents/x.agent.md`  passthrough byte a byte, so o NOME muda
                                 (sufixo `.agent.md`)
  - `.agents/agents/x.md`        RENDERIZADO: perde a chave `tools:` do
                                 frontmatter, porque o mapeamento de valores de
                                 tool do Devin nao esta documentado e chutar em
                                 campo de permissao erra nos dois sentidos
                                 (veto V-DV-8). O corpo sai identico.

Por isso este gate NAO compara espelho com fonte: ele compara espelho com
`render_agent(fonte, plataforma_do_alvo)`. E o mesmo invariante que
`sync_skills.check()` usa -- estritamente mais forte que byte-identidade e sem
falso positivo na divergencia legitima.
"""

from __future__ import annotations

import io
import pathlib
import subprocess
import sys
import tarfile

import pytest

# `tests/conftest.py` ja poe a raiz no `sys.path` -- e por isto que
# `tests/test_agents_parity.py` importa assim tambem.
from scripts import sync_skills

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def _versionados() -> set[str]:
    saida = subprocess.run(
        ["git", "ls-files", "sparkforge"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return {linha.strip() for linha in saida.splitlines() if linha.strip().endswith(".py")}


def _no_disco() -> set[str]:
    achados = set()
    for caminho in (RAIZ / "sparkforge").rglob("*.py"):
        if "__pycache__" in caminho.parts:
            continue
        achados.add(caminho.relative_to(RAIZ).as_posix())
    return achados


def test_todo_py_do_pacote_esta_no_git():
    """Arquivo no disco e fora do git quebra clone limpo, e so ele.

    O install editavel esconde isso: o import resolve para a arvore de trabalho,
    entao a suite inteira fica verde enquanto o repositorio publicado nao
    importa.
    """
    faltando = sorted(_no_disco() - _versionados())
    assert faltando == [], (
        "modulo(s) no disco e fora do git -- clone limpo nao importaria: "
        f"{faltando}"
    )


def test_todo_py_versionado_existe_no_disco():
    """O inverso: arquivo apagado sem `git rm` deixa o git com fantasma."""
    fantasmas = sorted(_versionados() - _no_disco())
    assert fantasmas == [], f"versionado(s) sem arquivo no disco: {fantasmas}"


# ---------------------------------------------------------------------------
# Espelhos gerados: o mesmo defeito, fora do `.py`
# ---------------------------------------------------------------------------

# Os diretorios que `sync_skills` LE e ESCREVE, derivados DELE, nunca escritos a
# mao aqui. Duas listas paralelas que precisam concordar sao a familia de
# defeito que a Fase 5c ja achou nos dois `EXTRACTORS`: uma cresce, a outra nao,
# e o desacordo e mudo. Um espelho novo em `sync_skills` entra neste gate
# sozinho.
def _raizes_governadas() -> list[str]:
    raizes = [
        sync_skills.CANONICAL,
        sync_skills.AGENTS_SRC,
        *sync_skills.MIRRORS,
        *(alvo for alvo, _ in sync_skills.AGENT_MIRRORS),
        *sync_skills.EXECUTOR_MIRRORS,
    ]
    # `STALE_AGENTS` fica de fora de proposito: sao caminhos que NAO podem
    # existir, e `git archive` recusa um pathspec que nao casa com nada. Eles ja
    # moram dentro de `.github/agents/`, entao se um voltar ele vem no tar junto
    # e `check_agents` acusa la dentro.
    rel = {p.relative_to(RAIZ).as_posix() for p in raizes}
    # `EXECUTOR_MIRRORS` mora DENTRO de `AGENT_MIRRORS`; passar os dois ao
    # `git archive` duplicaria entradas no tar. Fica so o ancestral.
    return sorted(
        c for c in rel
        if not any(o != c and c.startswith(f"{o}/") for o in rel)
    )


def _stdlib_aceita_filter() -> bool:
    """A stdlib desta interpreter aceita `extractall(..., filter=...)`?

    `tarfile.data_filter` chegou no MESMO backport do PEP 706 que o parametro
    (3.10.12, 3.11.4), entao a presenca de um responde pelo outro.

    E funcao, e nao expressao inline, para que o teste de compatibilidade possa
    fingir a stdlib antiga sem apagar `tarfile.data_filter` -- apagar o atributo
    de verdade quebra o proprio `tarfile` do 3.14, que o referencia por nome no
    caminho do filtro default.
    """
    return hasattr(tarfile, "data_filter")


def _tarinfo_link(nome: str, alvo: str) -> tarfile.TarInfo:
    """Um membro de tar que e link simbolico -- so os testes montam isto."""
    membro = tarfile.TarInfo(nome)
    membro.type = tarfile.SYMTYPE
    membro.linkname = alvo
    return membro


def _membro_recusado(membro: tarfile.TarInfo) -> str | None:
    """A razao para recusar `membro`, ou `None` se ele pode ser extraido.

    Regras, todas sobre o NOME que vem dentro do tar -- nunca sobre o caminho ja
    juntado ao destino, que e onde o escape acontece:

      - so arquivo regular e diretorio. Link (sim/hard) e device apontam para
        fora do tar por definicao, e o corpus governado nao tem nenhum: `git
        ls-files -s` sobre as raizes de `sync_skills` devolve so `100644`;
      - nada de caminho absoluto, nas tres formas que existem entre POSIX e
        Windows: `/x`, `\\x` e `C:\\x`. `PurePosixPath("C:/x").is_absolute()` e
        `False`, entao a letra de unidade precisa de teste proprio;
      - nada de componente `..`, que e o escape classico do TarSlip.
    """
    nome = membro.name
    if not (membro.isfile() or membro.isdir()):
        return f"membro que nao e arquivo nem diretorio: {nome!r}"
    if nome.startswith(("/", "\\")) or (len(nome) > 1 and nome[1] == ":"):
        return f"caminho absoluto no tar: {nome!r}"
    if ".." in nome.replace("\\", "/").split("/"):
        return f"componente '..' no tar: {nome!r}"
    return None


def _extrair_com_seguranca(dados: bytes, destino: pathlib.Path) -> None:
    """Extrai o tar em `destino` sem deixar nenhum membro sair de la.

    DUAS CAMADAS, de proposito:

      - `_membro_recusado` e o PISO. `pyproject.toml` promete
        `requires-python = ">=3.10"`, e o parametro `filter` do `extractall` so
        existe a partir de 3.10.12 e 3.11.4 (backport do PEP 706). Em 3.10.0 ate
        3.10.11 passar `filter=` levanta `TypeError` -- o gate QUEBRARIA, e
        justamente nas versoes onde a stdlib nao protege sozinha. A validacao
        explicita vale na faixa inteira que o `pyproject.toml` promete;
      - `filter="data"` e o TETO, aplicado so onde a stdlib o oferece. Ele cobre
        o que uma checagem de nome nao ve (permissoes, alvo de link resolvido) e
        e a mitigacao que o proprio PEP 706 desenhou.

    O piso sozinho ja basta para este tar -- a fonte e `git archive` do proprio
    repositorio, nao entrada externa. Manter o teto e barato e vale para o dia
    em que alguem apontar este helper para outro tar; e por isso ele fica, em
    vez de sair por ser redundante hoje.
    """
    with tarfile.open(fileobj=io.BytesIO(dados)) as tar:
        membros = tar.getmembers()
        recusas = [r for m in membros if (r := _membro_recusado(m))]
        assert recusas == [], f"tar com membro que escapa do destino: {recusas}"
        extra = {"filter": "data"} if _stdlib_aceita_filter() else {}
        # noqa S202: o ruff acusa todo `extractall`, e nao consegue ver que o
        # `filter` vai em `**extra` -- nem que `_membro_recusado` ja recusou o
        # `..`, o caminho absoluto e o link tres linhas acima. O alerta e sobre
        # extracao NAO VALIDADA; esta e validada duas vezes, e
        # `test_a_extracao_recusa_membro_que_escapa_do_destino` prova que morde.
        tar.extractall(destino, members=membros, **extra)  # noqa: S202


def _visao_do_commit(repo: pathlib.Path, destino: pathlib.Path) -> None:
    """Materializa em `destino` o que o COMMIT de `repo` tem, nao o disco dele.

    `git archive` le os objetos do git. E a propriedade que faz este gate
    morder: `sync_skills.sync()` escreve ARQUIVOS, e nenhum arquivo que ele
    escreva muda um objeto ja commitado. Um teste que regenere o espelho no meio
    da suite -- e ha um -- nao consegue apagar a evidencia daqui.

    O `scripts/sync_skills.py` tambem vem do commit, e nao do disco: assim o
    gate confere o espelho commitado contra o RENDERIZADOR COMMITADO. Uma
    mudanca no tradutor sem regenerar os espelhos tambem cai aqui.
    """
    alvos = ["scripts/sync_skills.py", *_raizes_governadas()]
    proc = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD", "--", *alvos],
        cwd=repo, capture_output=True, check=False,
    )
    assert proc.returncode == 0, (
        "`git archive HEAD` recusou um caminho governado por `sync_skills` -- "
        "provavelmente uma raiz de espelho que existe no disco e o commit nao "
        f"tem: {proc.stderr.decode('utf-8', 'replace')}"
    )
    _extrair_com_seguranca(proc.stdout, destino)


def _checar(vista: pathlib.Path) -> subprocess.CompletedProcess:
    """Roda o `--check` COMMITADO sobre a visao extraida."""
    return subprocess.run(
        [sys.executable, str(vista / "scripts" / "sync_skills.py"), "--check"],
        capture_output=True, text=True, cwd=vista,
    )


def test_espelho_gerado_esta_em_dia_no_commit(tmp_path):
    """Espelho que fica para tras da fonte NO COMMIT, pego em segundos.

    O defeito real (`c82a45e`): `agents/sf-context-engineer.md` entrou com 66
    linhas novas e os tres espelhos ficaram como estavam. O disco foi arrumado
    depois, por regeneracao, entao todo gate que olhava o disco disse OK -- e o
    commit publicado continuou inconsistente.

    Por que HEAD e nao o indice nem a arvore de trabalho:

      - a ARVORE DE TRABALHO e justamente o que a regeneracao conserta, e o que
        `test_sync_check_passes_after_sync` conserta sozinho antes de olhar;
      - o INDICE acusaria quem esta no meio de um `git add -p`, com a fonte ja
        preparada e o espelho ainda nao. Isso e trabalho em andamento, nao
        defeito, e gate que grita em trabalho em andamento e desligado;
      - HEAD responde a UNICA pergunta que importa e nao tem falso positivo
        nenhum vindo do estado local: "um clone limpo deste commit sai
        coerente?". E a mesma pergunta dos dois testes de `.py` acima.

    O preco e acusar um commit depois do erro, e nao antes -- ainda muito antes
    do push, e a suite completa levava 18 minutos para chegar perto disso.
    """
    _visao_do_commit(RAIZ, tmp_path)
    resultado = _checar(tmp_path)
    assert resultado.returncode == 0, (
        "o commit em HEAD carrega espelho fora de sincronia com a fonte -- um "
        "clone limpo dele sai incoerente. Rode `python scripts/sync_skills.py` "
        "e commite os espelhos junto com a fonte.\n" + resultado.stdout
    )


# Fotografia tirada na COLETA, nao na execucao. O pytest importa todos os
# modulos de teste antes de rodar qualquer teste, entao esta constante registra
# o estado do disco ANTES que `test_agents_parity.py` regenere os espelhos --
# em qualquer ordem de execucao. Chamar `check_*()` dentro do teste mediria um
# disco ja consertado, que e exatamente como o defeito escapou.
_DESSINCRONIA_NA_COLETA = (
    sync_skills.check_skills()
    + sync_skills.check_agents()
    + sync_skills.check_executors()
)


def test_espelho_gerado_esta_em_dia_no_disco():
    """O aviso ANTES do commit, e o antidoto para o gate que se conserta.

    Este e o mesmo `sync_skills.check()` que o CI ja roda -- a diferenca e QUE
    DISCO ele ve. No CI o passo `Mirror sync` vem depois do passo `Test suite`,
    e a suite regenera os espelhos; o passo dedicado sempre encontra tudo em
    ordem. Aqui a medicao acontece na coleta, antes de qualquer teste escrever.

    Falhou? A arvore de trabalho tem fonte editada sem o espelho correspondente.
    Rode `python scripts/sync_skills.py` e leve os espelhos no mesmo commit.
    """
    assert _DESSINCRONIA_NA_COLETA == [], (
        "espelho fora de sincronia com a fonte no disco (rode: "
        f"python scripts/sync_skills.py): {_DESSINCRONIA_NA_COLETA}"
    )


def _git(repo: pathlib.Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=gate@teste", "-c", "user.name=gate", *args],
        cwd=repo, capture_output=True, check=True,
    )


def test_o_gate_morde_quando_o_espelho_fica_para_tras(tmp_path):
    """A prova de que os dois testes acima NAO sao decorativos.

    Um gate escrito a mao neste repositorio ja trancou uma anotacao mentirosa
    por 405 commits porque ninguem verificou que ele mordia. Verde nao e
    evidencia de nada enquanto o vermelho nao for demonstrado.

    O corpus e o REAL, extraido do proprio HEAD: nao ha fixture sintetica que
    possa concordar com o gate por engano. A reproducao e literalmente o defeito
    de `c82a45e` -- fonte commitada sozinha, espelhos deixados para tras.

    O `assert` do baseline carrega a metade que costuma faltar: o corpus real ja
    contem a divergencia LEGITIMA (`.agents/agents/*.md` sem `tools:`) e o gate
    tem que ficar VERDE com ela no lugar. Gate que exigisse byte-identidade
    falharia aqui, seria desligado no primeiro alarme, e nao protegeria nada.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _visao_do_commit(RAIZ, repo)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "corpus real, coerente")

    base = tmp_path / "vista-base"
    _visao_do_commit(repo, base)
    assert _checar(base).returncode == 0, (
        "o corpus real reprovou no baseline -- o gate esta acusando a "
        "divergencia legitima do espelho do Devin como se fosse defeito"
    )

    # O defeito: uma linha na fonte, commitada SEM os espelhos.
    fonte = sorted((repo / "agents").glob("*.md"))[0]
    fonte.write_text(
        fonte.read_text(encoding="utf-8") + "\nLinha so na fonte.\n",
        encoding="utf-8",
    )
    _git(repo, "commit", "-q", "-o", f"agents/{fonte.name}", "-m", "fonte sem espelho")

    quebrada = tmp_path / "vista-quebrada"
    _visao_do_commit(repo, quebrada)
    resultado = _checar(quebrada)

    assert resultado.returncode == 1, (
        "o gate NAO mordeu: um commit com a fonte a frente dos tres espelhos "
        f"passou.\n{resultado.stdout}"
    )
    # Os TRES espelhos, nomeados. Acusar um so seria cobertura parcial passando
    # por completa -- e a plataforma silenciosa e a que fica sem metodo.
    for mirror_root, sufixo in ((".claude", ".md"), (".agents", ".md"), (".github", ".agent.md")):
        esperado = f"{fonte.stem}{sufixo}"
        assert any(
            mirror_root in linha and esperado in linha
            for linha in resultado.stdout.splitlines()
        ), f"{mirror_root} nao foi acusado:\n{resultado.stdout}"


@pytest.mark.parametrize(
    ("apelido", "monta"),
    [
        ("escape_com_pontos", lambda: tarfile.TarInfo("../fora.txt")),
        ("absoluto_posix", lambda: tarfile.TarInfo("/fora.txt")),
        ("absoluto_windows", lambda: tarfile.TarInfo("C:/fora.txt")),
        ("link_para_fora", lambda: _tarinfo_link("link.txt", "/etc/passwd")),
    ],
)
def test_a_extracao_recusa_membro_que_escapa_do_destino(apelido, monta, tmp_path):
    """A validacao morde -- e nao e decoracao.

    Este repositorio ja teve um gate que trancou uma anotacao mentirosa por 405
    commits porque ninguem verificou se ele mordia. Uma checagem de seguranca
    que nunca foi vista recusando nada e exatamente a mesma aposta.

    O `..` e o TarSlip classico; as duas formas de caminho absoluto e o link sao
    as outras portas para o mesmo lugar. Todas passam pelo PISO
    (`_membro_recusado`), que e o que roda em 3.10.0 -- onde `filter=` nem
    existe. Este teste, portanto, exercita a camada que a stdlib nao da.
    """
    destino = tmp_path / "destino"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        membro = monta()
        if membro.isfile():
            corpo = b"escapou"
            membro.size = len(corpo)
            tar.addfile(membro, io.BytesIO(corpo))
        else:
            tar.addfile(membro)

    with pytest.raises(AssertionError, match="escapa do destino"):
        _extrair_com_seguranca(buf.getvalue(), destino)

    # Recusar e so metade: nada pode ter sido escrito, nem dentro nem fora.
    assert not (tmp_path / "fora.txt").exists()
    assert not destino.exists() or list(destino.rglob("*")) == []


def test_a_extracao_funciona_sem_o_filter_da_stdlib(tmp_path, monkeypatch):
    """O piso sozinho, que e o unico que existe em 3.10.0 ate 3.10.11.

    `pyproject.toml` promete `requires-python = ">=3.10"`, e nessa faixa o
    parametro `filter` do `extractall` ainda nao existe (chegou em 3.10.12 e
    3.11.4, backport do PEP 706). Passa-lo la levanta
    `TypeError: extractall() got an unexpected keyword argument 'filter'` -- o
    gate inteiro QUEBRARIA, e exatamente nas versoes onde a stdlib nao protege.

    O que este teste prova, exatamente: com a stdlib se dizendo antiga, o helper
    NAO passa o parametro -- entao o `TypeError` nao acontece -- e o piso
    continua fazendo as duas coisas, extrair o que presta e recusar o que
    escapa. O que ele NAO pode provar nesta interpreter e o comportamento da
    stdlib de 3.10.0, que nao esta aqui para rodar; por isso a afirmacao
    verificada e sobre a NOSSA chamada e a NOSSA validacao, que sao as duas
    coisas que o defeito de compatibilidade estragava.
    """
    monkeypatch.setattr(sys.modules[__name__], "_stdlib_aceita_filter", lambda: False)

    # Espiao no `extractall`: sem ele este teste passaria mesmo que alguem
    # voltasse a passar `filter="data"` incondicionalmente, porque esta
    # interpreter ACEITA o parametro. O 3.10.0 que quebraria nao esta aqui para
    # reclamar, entao a regressao tem que ser pega pela CHAMADA, nao pelo efeito.
    kwargs_vistos: list[dict] = []
    original = tarfile.TarFile.extractall

    def espiao(self, *args, **kwargs):
        kwargs_vistos.append(kwargs)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "extractall", espiao)

    bom = io.BytesIO()
    with tarfile.open(fileobj=bom, mode="w") as tar:
        membro = tarfile.TarInfo("dentro/ok.txt")
        corpo = b"conteudo legitimo"
        membro.size = len(corpo)
        tar.addfile(membro, io.BytesIO(corpo))
    destino = tmp_path / "ok"
    _extrair_com_seguranca(bom.getvalue(), destino)
    assert (destino / "dentro" / "ok.txt").read_bytes() == b"conteudo legitimo"
    assert len(kwargs_vistos) == 1
    assert "filter" not in kwargs_vistos[0], (
        "`filter=` foi passado numa stdlib que nao o aceita -- em 3.10.0 isto e "
        f"TypeError e o gate inteiro para de rodar: {kwargs_vistos[0]}"
    )

    ruim = io.BytesIO()
    with tarfile.open(fileobj=ruim, mode="w") as tar:
        membro = tarfile.TarInfo("../fora.txt")
        membro.size = 0
        tar.addfile(membro, io.BytesIO(b""))
    with pytest.raises(AssertionError, match="escapa do destino"):
        _extrair_com_seguranca(ruim.getvalue(), tmp_path / "recusado")
    assert not (tmp_path / "fora.txt").exists()
