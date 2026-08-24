"""A varredura e a fronteira entre o repositorio analisado e o motor.

Hoje ela nao existe como unidade: sao doze sitios de `rglob` espalhados, e so
tres pulam sequer `__pycache__`. Apontar o motor para um repositorio com `.venv`
varre o ambiente virtual inteiro -- custo, ruido, e leitura de qualquer `*.json`
que houver dentro.
"""

import pathlib

import pytest

from sparkforge.facts.scan import ScanError, iter_source_files


def _criar(raiz: pathlib.Path, caminho: str, conteudo: str = "x = 1\n") -> pathlib.Path:
    alvo = raiz / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")
    return alvo


def test_pula_arvore_de_dependencia_e_artefato_de_build(tmp_path):
    _criar(tmp_path, "job.py")
    for ruido in (
        ".venv/lib/site-packages/requests/api.py",
        "venv/lib/x.py",
        "node_modules/pacote/index.py",
        "vendor/terceiro/mod.py",
        "build/lib/copia.py",
        "__pycache__/job.cpython-312.py",
        ".git/hooks/pre-commit.py",
        ".tox/py310/x.py",
        "site-packages/y.py",
    ):
        _criar(tmp_path, ruido)
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_pula_caminho_sensivel_mesmo_com_extensao_pedida(tmp_path):
    _criar(tmp_path, "config.json", "{}")
    for sensivel in (
        ".aws/credentials.json",
        ".ssh/chave.json",
        "terraform.tfstate.json",
        "secrets.json",
        ".env.json",
    ):
        _criar(tmp_path, sensivel, "{}")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["config.json"]


def test_symlink_nao_e_seguido(tmp_path):
    fora = tmp_path.parent / "fora_do_alvo"
    fora.mkdir(exist_ok=True)
    (fora / "segredo.py").write_text("SENHA = 'x'\n", encoding="utf-8")
    alvo = tmp_path / "alvo"
    alvo.mkdir()
    _criar(alvo, "job.py")
    try:
        (alvo / "atalho").symlink_to(fora, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(alvo, "*.py"))
    assert achados == ["job.py"]


def test_raiz_inexistente_e_erro_nomeado_nao_lista_vazia(tmp_path):
    with pytest.raises(ScanError):
        list(iter_source_files(tmp_path / "nao_existe", "*.py"))


def test_arquivo_grande_demais_e_pulado_sem_derrubar_a_varredura(tmp_path):
    _criar(tmp_path, "pequeno.py")
    (tmp_path / "gigante.py").write_text("#" * (2 * 1024 * 1024), encoding="utf-8")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["pequeno.py"]


def test_apenas_arquivo_regular(tmp_path):
    _criar(tmp_path, "job.py")
    achados = list(iter_source_files(tmp_path, "*.py"))
    assert all(p.is_file() for p in achados)


def test_ordem_reproduz_a_de_rglob_ordenado(tmp_path):
    """Os goldens foram gravados sob `sorted(root.rglob(...))`.

    `os.walk` visita por nivel, o que intercala subpasta e arquivo em ordem
    diferente da ordenacao global por caminho. Se a varredura nao reproduzir a
    ordem antiga, todo extrator que nao reordena no fim muda de golden.
    """
    for caminho in ("a/b.py", "a/c/d.py", "a/e.py", "z.py", "a/c/a.py"):
        _criar(tmp_path, caminho)
    assert list(iter_source_files(tmp_path, "*.py")) == sorted(tmp_path.rglob("*.py"))


def test_raiz_relativa_devolve_caminho_relativo(tmp_path, monkeypatch):
    """Os extratores fazem `relative_to(repo_root)` no que a varredura devolve.

    Resolver a raiz antes de andar transformaria `.` em caminho absoluto, e o
    `relative_to(Path("."))` de quem chamou passaria a levantar ValueError.
    """
    _criar(tmp_path, "pacote/job.py")
    monkeypatch.chdir(tmp_path)
    achados = list(iter_source_files(pathlib.Path("."), "*.py"))
    assert [p.relative_to(pathlib.Path(".")).as_posix() for p in achados] == ["pacote/job.py"]


def test_raiz_que_e_arquivo_e_erro_nomeado(tmp_path):
    alvo = _criar(tmp_path, "job.py")
    with pytest.raises(ScanError):
        list(iter_source_files(alvo, "*.py"))


def test_extensao_fora_do_padrao_nao_entra(tmp_path):
    _criar(tmp_path, "job.py")
    _criar(tmp_path, "dados.json", "{}")
    _criar(tmp_path, "leia.txt", "oi")
    assert sorted(p.name for p in iter_source_files(tmp_path, "*.py")) == ["job.py"]


def test_arquivo_no_limite_de_tamanho_ainda_entra(tmp_path):
    """O limite e `>`, nao `>=`: arquivo exatamente no teto e legitimo.

    Sem este caso, trocar o limite por `>=` -- ou por qualquer teto menor --
    passaria despercebido.
    """
    from sparkforge.facts.scan import TAMANHO_MAXIMO_BYTES

    (tmp_path / "no_limite.py").write_bytes(b"#" * TAMANHO_MAXIMO_BYTES)
    (tmp_path / "um_a_mais.py").write_bytes(b"#" * (TAMANHO_MAXIMO_BYTES + 1))
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["no_limite.py"]


def test_symlink_para_arquivo_dentro_da_raiz_tambem_e_pulado(tmp_path):
    """Symlink e pulado por ser symlink, nao por apontar para fora.

    Um link que aponta para dentro da raiz continua sendo um segundo nome para
    o mesmo conteudo: segui-lo duplicaria facts do mesmo arquivo.
    """
    _criar(tmp_path, "job.py")
    try:
        (tmp_path / "copia.py").symlink_to(tmp_path / "job.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_subpasta_ignorada_nao_e_descida(tmp_path, monkeypatch):
    """A poda tem que impedir a DESCIDA, nao so filtrar o resultado.

    Filtrar no fim daria a mesma lista, mas teria pago o custo de listar o
    `.venv` inteiro -- que e exatamente o custo que esta varredura existe para
    evitar.
    """
    import os as _os

    _criar(tmp_path, "job.py")
    _criar(tmp_path, ".venv/lib/site-packages/requests/api.py")
    visitadas: list[str] = []
    walk_original = _os.walk

    def walk_espiao(*args, **kwargs):
        for pasta, subpastas, arquivos in walk_original(*args, **kwargs):
            visitadas.append(pasta)
            yield pasta, subpastas, arquivos

    monkeypatch.setattr("sparkforge.facts.scan.os.walk", walk_espiao)
    list(iter_source_files(tmp_path, "*.py"))
    assert not any(".venv" in pasta for pasta in visitadas)


def test_symlink_de_pasta_para_dentro_da_raiz_nao_duplica(tmp_path):
    """Isola `followlinks=False` do confinamento.

    Um link de pasta que aponta para DENTRO da raiz passa no confinamento --
    o destino esta mesmo la dentro. Se a travessia seguisse links, o mesmo
    arquivo entraria duas vezes e viraria fact duplicado.
    """
    _criar(tmp_path, "pkg/job.py")
    try:
        (tmp_path / "atalho").symlink_to(tmp_path / "pkg", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_caminho_entregue_de_fora_da_raiz_nao_passa(tmp_path, monkeypatch):
    """Isola o confinamento de `followlinks=False`.

    O confinamento existe para a corrida: entre podar e ler, um componente
    intermediario pode ser trocado por um link. Aqui a corrida e encenada --
    a travessia entrega uma pasta de fora -- porque so assim a guarda fica
    observavel enquanto `followlinks=False` tambem esta no lugar.
    """
    import os as _os

    fora = tmp_path.parent / "fora_do_confinamento"
    fora.mkdir(exist_ok=True)
    (fora / "segredo.py").write_text("SENHA = 'x'\n", encoding="utf-8")
    alvo = tmp_path / "alvo"
    alvo.mkdir()
    _criar(alvo, "job.py")
    walk_original = _os.walk

    def walk_com_intruso(*args, **kwargs):
        yield from walk_original(*args, **kwargs)
        yield str(fora), [], ["segredo.py"]

    monkeypatch.setattr("sparkforge.facts.scan.os.walk", walk_com_intruso)
    achados = sorted(p.name for p in iter_source_files(alvo, "*.py"))
    assert achados == ["job.py"]


def test_til_na_raiz_e_expandido(tmp_path, monkeypatch):
    """`~` chega de linha de comando e nao e nome de pasta.

    Sem expandir, a raiz `~/projeto` simplesmente nao existe e a varredura
    acusaria raiz inexistente para um caminho que o usuario ve funcionar no
    shell dele.
    """
    _criar(tmp_path, "projeto/job.py")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    achados = sorted(p.name for p in iter_source_files("~/projeto", "*.py"))
    assert achados == ["job.py"]


@pytest.mark.parametrize(
    "nome",
    [
        "id_rsa",
        "id_ed25519",
        "kubeconfig",
        "chave.pem",
        "servidor.key",
        "cofre.p12",
        "estado.tfstate",
        "prod.tfvars",
        ".npmrc",
        ".netrc",
    ],
)
def test_nome_sensivel_e_pulado_com_padrao_curinga(tmp_path, nome):
    """`*` casa qualquer nome, entao a denylist e a unica defesa aqui.

    Um extrator que varre por curinga passaria a ler credencial se a checagem
    de sensivel sumisse.
    """
    _criar(tmp_path, "job.py")
    _criar(tmp_path, nome, "conteudo")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*"))
    assert achados == ["job.py"]
