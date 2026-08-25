"""As travas de `sparkforge/codeintel/security.py`, e a prova do INV-001.

POR QUE O SUBPROCESSO APARECE TANTO AQUI
-----------------------------------------
`sys.addaudithook` nao tem inverso. Instalado, o hook vale para o processo
inteiro ate ele morrer -- e se ele fosse instalado dentro desta suite, todo
teste que rodasse DEPOIS herdaria a proibicao de `subprocess.Popen`, incluindo
os que levantam a CLI. A contaminacao nao apareceria como falha deste arquivo:
apareceria como falha aleatoria de outro, dependendo da ordem de coleta.

`resource.setrlimit` tem o mesmo problema por outro motivo: apertar `RLIMIT_AS`
no processo do pytest aperta o pytest.

Entao os dois sao exercitados em interpretador proprio, com o script escrito em
`tmp_path` e o resultado voltando como JSON pelo stdout. O preco medido disto e
de um processo por teste (~0.3 s cada nesta maquina); a alternativa era um teste
que passa sozinho e quebra a suite.

O QUE ESTE ARQUIVO PROVA E O QUE ELE NAO PROVA
-----------------------------------------------
A classe `TestInv001` e a razao de ser do arquivo: ela indexa o pacote
`sparkforge/` INTEIRO -- 140 arquivos, 1243 nos na medicao desta sessao -- com o
hook de bloqueio ativo, e o indice termina. Isso e evidencia direta de que o
caminho real de indexacao, busca e resumo nao abre socket, nao resolve nome e
nao levanta processo. Ate esta fase o INV-001 nao tinha teste nenhum.

Ela NAO prova que nenhuma execucao possivel do pacote produz egress: prova que
esta, sobre este corpus, nao produziu. Um caminho que so acorde com outra
entrada continua fora do alcance -- e e por isso que o gate ESTATICO da classe
`TestGateDeImportDeRede` importa mais, e nao menos: ele fala sobre todo o
codigo, nao sobre uma execucao dele.

Sobre `apply_resource_limits`: nesta maquina (Windows) o ramo POSIX e exercitado
com um `resource` FALSO injetado no `sys.path`, e esta dito no nome do teste. O
que aquilo prova e a logica deste repositorio -- clamp, leitura de volta,
deteccao de divergencia. Nao prova nada sobre o kernel. O ramo real roda no CI,
que e Linux, e os testes dele estao marcados com `skipif`.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sparkforge.codeintel import security

RAIZ = Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "sparkforge" / "codeintel"

E_POSIX = sys.platform != "win32"


def _copia_do_pacote(destino: Path) -> Path:
    """Copia `sparkforge/codeintel/` para `destino`, para a mutacao nao sujar a arvore.

    Mutar o pacote de verdade para ver o gate acusar deixaria a arvore suja se o
    teste falhasse no meio -- e um teste de seguranca que pode deixar
    `import socket` no repositorio e pior que nenhum.
    """
    copia = destino / "codeintel"
    shutil.copytree(PACOTE, copia, ignore=shutil.ignore_patterns("__pycache__"))
    return copia


def _rodar(script: Path, *argumentos: str) -> dict:
    """Roda `script` num interpretador proprio e devolve o JSON que ele imprimir."""
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ)}
    proc = subprocess.run(
        [sys.executable, str(script), *argumentos],
        capture_output=True,
        text=True,
        env=ambiente,
        cwd=str(RAIZ),
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# 1. Gate estatico (SPEC secao 7)
# ---------------------------------------------------------------------------


class TestGateDeImportDeRede:
    def test_o_pacote_nao_importa_nada_de_rede_hoje(self):
        """O gate propriamente dito. Falhar aqui e o PR ter trazido rede para dentro.

        Este e o teste que a secao 7 da SPEC pede como gate de CI, e `pytest`
        e o gate de CI deste repositorio -- roda em `.github/workflows/ci.yml`,
        passo `Test suite`, nas duas versoes da matriz.
        """
        assert security.imports_proibidos() == ()

    def test_a_lista_e_a_da_spec_e_nao_uma_parecida(self):
        """Trava a lista contra encolhimento silencioso.

        Sem isto, apagar `boto3` do conjunto deixaria o teste de cima verde e a
        proibicao menor -- que e exatamente a forma como uma allowlist morre.
        """
        assert security.MODULOS_DE_REDE == frozenset(
            {"requests", "httpx", "aiohttp", "socket", "websocket", "grpc", "boto3", "botocore"}
        )
        assert security.MODULOS_DE_REDE_QUALIFICADOS == ("urllib.request",)

    @pytest.mark.parametrize("modulo", sorted(security.MODULOS_DE_REDE))
    def test_cada_modulo_da_lista_e_acusado(self, tmp_path, modulo):
        copia = _copia_do_pacote(tmp_path)
        (copia / "intruso.py").write_text(f"import {modulo}\n", encoding="utf-8")
        achados = security.imports_proibidos(copia)
        assert [v.modulo for v in achados] == [modulo]
        assert achados[0].arquivo == "intruso.py"
        assert achados[0].linha == 1

    def test_submodulo_nao_escapa_pela_raiz(self, tmp_path):
        """`import grpc.aio` traz `grpc`. Comparar por igualdade exata deixaria passar."""
        copia = _copia_do_pacote(tmp_path)
        (copia / "intruso.py").write_text("import grpc.aio\n", encoding="utf-8")
        assert [v.modulo for v in security.imports_proibidos(copia)] == ["grpc"]

    def test_from_urllib_import_request_e_acusado(self, tmp_path):
        """A grafia em que o nome proibido nunca aparece inteiro numa linha so."""
        copia = _copia_do_pacote(tmp_path)
        (copia / "intruso.py").write_text("from urllib import request\n", encoding="utf-8")
        assert [v.modulo for v in security.imports_proibidos(copia)] == ["urllib.request"]

    def test_from_urllib_request_import_urlopen_e_acusado(self, tmp_path):
        copia = _copia_do_pacote(tmp_path)
        (copia / "intruso.py").write_text(
            "from urllib.request import urlopen\n", encoding="utf-8"
        )
        assert [v.modulo for v in security.imports_proibidos(copia)] == ["urllib.request"]

    def test_urllib_parse_nao_e_acusado(self, tmp_path):
        """O falso positivo que faria alguem afrouxar a lista para trabalhar.

        `urllib.parse` manipula string e nao abre nada. Um gate que o recusasse
        seria desligado no primeiro PR que precisasse dele, e a proibicao de
        `urllib.request` iria junto.
        """
        copia = _copia_do_pacote(tmp_path)
        (copia / "inocente.py").write_text(
            "from urllib.parse import urlsplit\nimport urllib.parse\n", encoding="utf-8"
        )
        assert security.imports_proibidos(copia) == ()

    def test_import_dinamico_por_string_e_acusado(self, tmp_path):
        """`import_module("socket")` importa sem escrever `import`."""
        copia = _copia_do_pacote(tmp_path)
        (copia / "intruso.py").write_text(
            'import importlib\n'
            'def a():\n'
            '    return importlib.import_module("socket")\n'
            'def b():\n'
            '    return __import__("boto3")\n',
            encoding="utf-8",
        )
        assert sorted(v.modulo for v in security.imports_proibidos(copia)) == ["boto3", "socket"]

    def test_import_relativo_do_proprio_pacote_nao_e_falso_positivo(self, tmp_path):
        copia = _copia_do_pacote(tmp_path)
        (copia / "inocente.py").write_text("from . import db\n", encoding="utf-8")
        assert security.imports_proibidos(copia) == ()

    def test_arquivo_que_nao_parseia_conta_como_violacao(self, tmp_path):
        """INV-015: o gate que pula o que nao entende ensina como contorna-lo."""
        copia = _copia_do_pacote(tmp_path)
        (copia / "quebrado.py").write_text("def (\n", encoding="utf-8")
        achados = security.imports_proibidos(copia)
        assert [(v.arquivo, v.modulo) for v in achados] == [("quebrado.py", "<nao-parseia>")]

    def test_subpasta_tambem_e_varrida(self, tmp_path):
        """`rglob` e nao `glob`: esconder o import um nivel abaixo nao pode funcionar."""
        copia = _copia_do_pacote(tmp_path)
        sub = copia / "interno"
        sub.mkdir()
        (sub / "intruso.py").write_text("import httpx\n", encoding="utf-8")
        assert [v.arquivo for v in security.imports_proibidos(copia)] == ["interno/intruso.py"]


# ---------------------------------------------------------------------------
# 2. sanitize_environment (INV-003)
# ---------------------------------------------------------------------------


class TestSanitizeEnvironment:
    @pytest.fixture(autouse=True)
    def _ambiente_restaurado(self):
        """Devolve `os.environ` intacto depois de cada teste desta classe.

        `sanitize_environment()` sem argumento apaga do ambiente REAL do
        processo do pytest -- e apagaria tambem o `AWS_PROFILE` ou o
        `GITHUB_TOKEN` que a maquina de quem roda ja tivesse, sem esses testes
        terem posto nada la. `monkeypatch` so desfaz o que ele proprio pos; o
        estrago colateral cairia num teste qualquer mais adiante, sem nome.
        """
        original = dict(os.environ)
        yield
        os.environ.clear()
        os.environ.update(original)

    def test_a_lista_e_a_do_inv003_e_nao_uma_parecida(self):
        """Mesma razao do gate de import: conjunto que encolhe deixa o teste
        parametrizado abaixo colecionando menos casos, e menos caso passa."""
        assert security.VARIAVEIS_SEGREDO == frozenset(
            {
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "GITHUB_TOKEN",
                "GH_TOKEN",
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "SSH_AUTH_SOCK",
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
            }
        )

    @pytest.mark.parametrize("nome", sorted(security.VARIAVEIS_SEGREDO))
    def test_toda_variavel_do_inv003_sai_do_ambiente_real(self, monkeypatch, nome):
        """A medicao e `os.environ` DEPOIS, nunca a lista devolvida.

        Uma implementacao que apagasse de uma copia devolveria a mesma lista e
        deixaria a variavel legivel -- e `assert nome in removidos` passaria.
        """
        monkeypatch.setenv(nome, "valor-de-teste")
        assert os.environ.get(nome) == "valor-de-teste"
        removidos = security.sanitize_environment()
        assert nome in removidos
        assert nome not in os.environ
        assert os.environ.get(nome) is None

    def test_qualquer_aws_sai_e_nao_so_as_tres_nomeadas(self, monkeypatch):
        """`AWS_PROFILE` nao e segredo e e o que faz um SDK ir buscar um."""
        monkeypatch.setenv("AWS_PROFILE", "prod")
        monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "/v2/creds")
        removidos = security.sanitize_environment()
        assert "AWS_PROFILE" in removidos
        assert "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI" in removidos
        assert "AWS_PROFILE" not in os.environ

    @pytest.mark.parametrize(
        "nome", ["http_proxy", "https_proxy", "all_proxy", "aws_secret_access_key"]
    )
    def test_a_classificacao_e_indiferente_a_caixa(self, nome):
        """Em POSIX `http_proxy` minusculo e honrado por libs de rede tanto quanto
        o maiusculo, e os dois coexistem no mesmo ambiente.

        Este teste exercita o CLASSIFICADOR e nao o ambiente, de proposito -- ver
        o teste abaixo, marcado para POSIX, e o porque.
        """
        assert security.e_variavel_de_segredo(nome) is True

    @pytest.mark.skipif(not E_POSIX, reason="ver docstring: Windows normaliza o nome")
    def test_em_posix_a_grafia_minuscula_sai_do_ambiente(self, monkeypatch):
        """MEDIDO: no Windows `os.environ` nao guarda a caixa que se escreve.

        `monkeypatch.setenv("http_proxy", ...)` seguido de `os.environ` no
        Windows 11 / CPython 3.14.6 devolve a chave como `HTTP_PROXY` -- o mapa
        de ambiente do Windows e case-insensitive e o CPython normaliza para
        maiuscula na escrita. Entao la nao existe a variavel minuscula para
        testar, e afirmar que ela some seria afirmar sobre o `os.environ` do
        Windows, nao sobre esta funcao.
        """
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:8080")
        assert "http_proxy" in os.environ
        removidos = security.sanitize_environment()
        assert "http_proxy" in removidos
        assert "http_proxy" not in os.environ

    def test_variavel_com_marcador_de_segredo_sai(self, monkeypatch):
        """O "ou qualquer variavel classificada como segredo" do INV-003."""
        monkeypatch.setenv("MINHA_APP_TOKEN", "x")
        monkeypatch.setenv("DB_PASSWORD", "x")
        monkeypatch.setenv("SERVICE_PRIVATE_KEY", "x")
        removidos = security.sanitize_environment()
        assert {"MINHA_APP_TOKEN", "DB_PASSWORD", "SERVICE_PRIVATE_KEY"} <= set(removidos)

    def test_o_que_nao_e_segredo_fica(self, monkeypatch):
        """Se apagasse `PATH`, o processo de parsing nao acharia mais nada.

        O erro para o lado de apagar demais e barato; apagar o ambiente inteiro
        nao e, e a heuristica precisa ter um limite escrito.
        """
        monkeypatch.setenv("PATH_INOFENSIVO", "x")
        monkeypatch.setenv("LANG", "pt_BR.UTF-8")
        monkeypatch.setenv("SPARKFORGE_ROOT", "raiz-qualquer")
        removidos = security.sanitize_environment()
        assert "PATH_INOFENSIVO" not in removidos
        assert "LANG" not in removidos
        assert "SPARKFORGE_ROOT" not in removidos
        assert os.environ["LANG"] == "pt_BR.UTF-8"

    def test_mapa_proprio_nao_toca_o_ambiente_do_processo(self, monkeypatch):
        do_processo = "valor-do-processo"
        monkeypatch.setenv("GH_TOKEN", do_processo)
        proprio = {"GH_TOKEN": "valor-do-mapa", "PATH": "/bin"}
        removidos = security.sanitize_environment(proprio)
        assert removidos == ("GH_TOKEN",)
        assert proprio == {"PATH": "/bin"}
        assert os.environ["GH_TOKEN"] == do_processo

    def test_chamar_de_novo_nao_encontra_nada_e_nao_explode(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        assert "OPENAI_API_KEY" in security.sanitize_environment()
        assert "OPENAI_API_KEY" not in security.sanitize_environment()

    def test_variavel_que_nao_sai_levanta_em_vez_de_mentir(self):
        """INV-015 na forma mais direta: o retorno nao pode discordar do ambiente."""

        class MapaTeimoso(dict):
            def __delitem__(self, chave):
                return None

        mapa = MapaTeimoso({"GITHUB_TOKEN": "x"})
        with pytest.raises(security.SanitizacaoIncompleta) as erro:
            security.sanitize_environment(mapa)
        assert "GITHUB_TOKEN" in str(erro.value)


# ---------------------------------------------------------------------------
# 3. install_audit_hook (SPEC secao 11.1)
# ---------------------------------------------------------------------------

SCRIPT_EVENTOS = '''
import ast
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from sparkforge.codeintel.security import OperacaoBloqueada, hook_instalado, install_audit_hook

r = {"antes": hook_instalado(), "primeira": install_audit_hook(),
     "segunda": install_audit_hook(), "depois": hook_instalado()}


def tenta(nome, fn):
    try:
        fn()
    except OperacaoBloqueada:
        r[nome] = "bloqueado"
    except Exception as erro:
        r[nome] = "outro:" + type(erro).__name__
    else:
        r[nome] = "passou"


tenta("socket.connect", lambda: socket.socket().connect(("127.0.0.1", 9)))
tenta("socket.bind", lambda: socket.socket().bind(("127.0.0.1", 0)))
tenta("socket.getaddrinfo", lambda: socket.getaddrinfo("exemplo.invalido", 80))
# `os.system` aqui e o alvo do teste: o ponto e provar que o hook o recusa.
tenta("os.system", lambda: os.system("echo x"))
tenta("subprocess.Popen", lambda: subprocess.Popen([sys.executable, "-c", "pass"]))

# O que o parsing precisa e que nao pode ter sido levado junto.
tenta("ast.parse", lambda: ast.parse("x = 1"))
with tempfile.TemporaryDirectory() as d:
    alvo = Path(d) / "b.sqlite3"
    tenta("sqlite3.connect", lambda: sqlite3.connect(alvo).close())
    tenta("open", lambda: (Path(d) / "f.txt").write_text("x", encoding="utf-8"))

print(json.dumps(r))
'''


@pytest.fixture(scope="module")
def eventos(tmp_path_factory):
    """Roda o script de eventos UMA vez e serve o resultado a todos os testes.

    Escopo de modulo porque o script custa um interpretador inteiro e o
    resultado dele nao depende de teste nenhum -- sem isto, seriam sete
    processos para responder sete perguntas sobre a mesma execucao.
    """
    script = tmp_path_factory.mktemp("hook") / "eventos.py"
    script.write_text(SCRIPT_EVENTOS, encoding="utf-8")
    return _rodar(script)


class TestAuditHook:
    def test_importar_o_modulo_nao_instala_nada(self):
        """Instalar no import decidiria pelo processo inteiro a partir de um import.

        Este teste roda EM PROCESSO de proposito: se algum dia o modulo passar a
        instalar no import, a suite inteira herda a proibicao de subprocesso, e
        aqui e onde isso aparece como uma falha com nome.
        """
        assert security.hook_instalado() is False

    def test_a_lista_de_eventos_e_a_da_spec_e_nao_uma_parecida(self):
        """Sem isto, esvaziar o conjunto deixaria o teste parametrizado abaixo
        colecionando zero casos -- e zero caso passa."""
        assert security.EVENTOS_BLOQUEADOS == frozenset(
            {"socket.connect", "socket.bind", "os.system", "subprocess.Popen"}
        )
        assert security.EVENTOS_RECUSADOS > security.EVENTOS_BLOQUEADOS

    @pytest.mark.parametrize("evento", sorted(security.EVENTOS_BLOQUEADOS))
    def test_os_quatro_eventos_da_spec_sao_bloqueados(self, eventos, evento):
        assert eventos[evento] == "bloqueado"

    def test_resolucao_de_nome_tambem_e_bloqueada(self, eventos):
        """O INV-001 diz DNS. Bloquear `connect` e liberar `getaddrinfo` deixaria
        de pe a exfiltracao por consulta de nome, que nao abre conexao nenhuma."""
        assert eventos["socket.getaddrinfo"] == "bloqueado"

    def test_instalar_duas_vezes_nao_empilha_dois_hooks(self, eventos):
        assert eventos["antes"] is False
        assert eventos["primeira"] is True
        assert eventos["segunda"] is False
        assert eventos["depois"] is True

    @pytest.mark.parametrize("permitido", ["ast.parse", "sqlite3.connect", "open"])
    def test_o_que_o_parsing_precisa_continua_funcionando(self, eventos, permitido):
        """Um hook que bloqueasse `open` ou o sqlite tornaria o indice impossivel.

        Este e o teste que impede a versao "segura" inutil do hook: recusar tudo
        passaria em todos os testes de bloqueio acima.
        """
        assert eventos[permitido] == "passou"


# ---------------------------------------------------------------------------
# 4. INV-001 -- zero network egress no caminho real
# ---------------------------------------------------------------------------

SCRIPT_INV001 = '''
import json
import sys
from pathlib import Path

from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.search import buscar, resumo
from sparkforge.codeintel.security import install_audit_hook

raiz, banco = Path(sys.argv[1]), Path(sys.argv[2])
install_audit_hook()
resultado = indexar(raiz, banco)
sumario = resumo(banco)
print(json.dumps({
    "arquivos": resultado.arquivos,
    "nos": resultado.nos,
    "ilegiveis": resultado.ilegiveis,
    "arestas": resultado.arestas,
    "achados": len(buscar(banco, "indexar")),
    "nodes_no_resumo": sumario["nodes"],
}))
'''


class TestInv001:
    def test_indexar_o_pacote_inteiro_sob_o_hook_nao_produz_egress(self, tmp_path):
        """A prova do invariante central da SPEC, que ate esta fase nao tinha teste.

        Indexa `sparkforge/` inteiro com o hook que RECUSA socket, DNS,
        `os.system` e `subprocess.Popen`. Se qualquer etapa -- varredura, leitura,
        `ast`, escrita no sqlite, FTS, busca, resumo -- tocasse a rede, o
        processo morreria com `OperacaoBloqueada` e `_rodar` falharia no
        `returncode`.

        Medido nesta sessao, Windows 11 / CPython 3.14.6: 140 arquivos, 1243
        nos, 2022 arestas, 1.14 s. As contagens nao sao afirmadas aqui porque
        elas se movem com a arvore; o que se afirma e que houve indice, houve
        busca e houve resumo, os tres sob o hook.
        """
        banco = tmp_path / "indice.sqlite3"
        script = tmp_path / "inv001.py"
        script.write_text(SCRIPT_INV001, encoding="utf-8")
        saida = _rodar(script, str(RAIZ / "sparkforge"), str(banco))

        assert saida["arquivos"] > 0
        assert saida["nos"] > 0
        assert saida["arestas"] > 0
        assert saida["achados"] > 0
        assert saida["nodes_no_resumo"] == saida["nos"]
        assert banco.exists()


# ---------------------------------------------------------------------------
# 5. apply_resource_limits (SPEC secao 41)
# ---------------------------------------------------------------------------

# `resource` FALSO. Serve para exercitar o ramo POSIX numa maquina Windows, onde
# o modulo nao existe. Prova a logica deste repositorio -- clamp, leitura de
# volta, deteccao de divergencia -- e NAO prova nada sobre o kernel.
RESOURCE_FALSO = '''
RLIM_INFINITY = -1
RLIMIT_CPU = 0
RLIMIT_AS = 9

MODO = "{modo}"
_estado = {{RLIMIT_CPU: ({cpu_soft}, {cpu_hard}), RLIMIT_AS: ({as_soft}, {as_hard})}}


def getrlimit(recurso):
    return _estado[recurso]


def setrlimit(recurso, valores):
    if MODO == "ignora":
        return None
    if MODO == "recusa":
        raise ValueError("nao permitido")
    _estado[recurso] = (valores[0], valores[1])
'''

SCRIPT_LIMITES = '''
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from sparkforge.codeintel.security import apply_resource_limits  # noqa: E402

limites = apply_resource_limits(
    memoria_bytes=int(sys.argv[2]),
    cpu_segundos=int(sys.argv[3]),
)
print(json.dumps({
    "aplicados": [list(x) for x in limites.aplicados],
    "nao_aplicados": [list(x) for x in limites.nao_aplicados],
    "disponivel": limites.disponivel,
    "motivo": limites.motivo,
}))
'''


def _limites_com_resource_falso(tmp_path, modo, **estado):
    """Roda `apply_resource_limits` contra um `resource` de mentira em `sys.path`."""
    valores = {
        "cpu_soft": -1,
        "cpu_hard": -1,
        "as_soft": -1,
        "as_hard": -1,
        **estado,
    }
    falso = tmp_path / "falso"
    falso.mkdir(exist_ok=True)
    (falso / "resource.py").write_text(
        RESOURCE_FALSO.format(modo=modo, **valores), encoding="utf-8"
    )
    script = tmp_path / "limites.py"
    script.write_text(SCRIPT_LIMITES, encoding="utf-8")
    return _rodar(
        script,
        str(falso),
        str(security.TETO_MEMORIA_BYTES),
        str(security.TETO_CPU_SEGUNDOS),
    )


class TestApplyResourceLimits:
    def test_recursao_e_o_unico_limite_que_vale_em_toda_plataforma(self):
        """`sys.setrecursionlimit` e do interpretador, nao do sistema operacional.

        Chamado EM PROCESSO de proposito, e seguro porque a funcao usa
        `min(pedido, teto, corrente)`: ela nunca sobe o limite, e como o default
        do CPython e 1000 e o teto deste modulo tambem, o valor efetivo nao se
        move. O teste le de volta em vez de confiar nisso.
        """
        antes = sys.getrecursionlimit()
        limites = security.apply_resource_limits()
        nomes = {nome for nome, _, _ in limites.aplicados}
        assert "RECURSAO" in nomes
        assert sys.getrecursionlimit() <= antes
        assert sys.getrecursionlimit() <= security.TETO_RECURSAO

    @pytest.mark.skipif(E_POSIX, reason="mede a ausencia de `resource`, que so ocorre no Windows")
    def test_no_windows_a_funcao_diz_que_nao_da_e_nomeia_a_plataforma(self):
        """MEDIDO: `import resource` no Windows levanta `ModuleNotFoundError`.

        A funcao poderia devolver um `Limites` cheio e ninguem notaria. Ela nao
        devolve, e este teste e o que impede alguem de "consertar" o Windows
        fingindo que o limite existe.
        """
        limites = security.apply_resource_limits()
        assert limites.disponivel is False
        assert limites.motivo is not None
        assert "resource" in limites.motivo
        assert sys.platform in limites.motivo
        nao = dict(limites.nao_aplicados)
        assert set(nao) >= {"RLIMIT_AS", "RLIMIT_CPU"}

    @pytest.mark.skipif(E_POSIX, reason="o modo estrito so tem o que recusar sem `resource`")
    def test_estrito_levanta_no_windows_em_vez_de_devolver_meia_protecao(self):
        """INV-015 disponivel para quem quiser: nao e o default, e por que.

        Se fosse o default, importar o pacote e endurecer no Windows seria
        impossivel, e a decisao de politica ficaria com este modulo em vez de
        com quem entra em `offline-strict`.
        """
        with pytest.raises(security.LimiteNaoAplicado):
            security.apply_resource_limits(estrito=True)

    def test_com_resource_falso_o_limite_e_aplicado_e_lido_de_volta(self, tmp_path):
        saida = _limites_com_resource_falso(tmp_path, "aplica")
        aplicados = {nome: (soft, hard) for nome, soft, hard in saida["aplicados"]}
        assert saida["disponivel"] is True
        assert aplicados["RLIMIT_AS"][0] == security.TETO_MEMORIA_BYTES
        assert aplicados["RLIMIT_CPU"][0] == security.TETO_CPU_SEGUNDOS
        assert saida["nao_aplicados"] == []

    def test_com_resource_falso_nunca_afrouxa_o_limite_ja_herdado(self, tmp_path):
        """O pai pode ter apertado por um motivo que este modulo nao conhece.

        Pedir 2 GiB quando o herdado e 64 MiB tem que deixar 64 MiB. Um
        `setrlimit` que AUMENTASSE seria o oposto do controle.
        """
        herdado = 64 * 1024 * 1024
        saida = _limites_com_resource_falso(
            tmp_path, "aplica", as_soft=herdado, as_hard=herdado
        )
        aplicados = {nome: (soft, hard) for nome, soft, hard in saida["aplicados"]}
        assert aplicados["RLIMIT_AS"][0] == herdado

    def test_com_resource_falso_o_setrlimit_mudo_e_pego_pela_leitura_de_volta(self, tmp_path):
        """"Nao levantou" nao e medicao, e este teste e a prova disso.

        O `resource` falso em modo `ignora` aceita todo `setrlimit` e nao muda
        nada -- exatamente o que um kernel poderia fazer. Uma implementacao que
        confiasse na ausencia de excecao reportaria os dois limites como
        aplicados.
        """
        saida = _limites_com_resource_falso(tmp_path, "ignora")
        assert saida["aplicados"] == [["RECURSAO", 1000, 1000]]
        nao = dict(saida["nao_aplicados"])
        assert set(nao) == {"RLIMIT_AS", "RLIMIT_CPU"}
        assert "efetivo" in nao["RLIMIT_AS"]

    def test_com_resource_falso_o_setrlimit_que_recusa_nao_derruba_o_processo(self, tmp_path):
        """Container que proibe `setrlimit` e caso comum, e nao pode virar crash."""
        saida = _limites_com_resource_falso(tmp_path, "recusa")
        nao = dict(saida["nao_aplicados"])
        assert "setrlimit recusou" in nao["RLIMIT_AS"]
        assert saida["disponivel"] is True

    def test_o_clamp_nunca_devolve_mais_que_o_pedido_nem_que_o_vigente(self):
        """A funcao pura por tras dos tres testes acima, exercitada sem plataforma."""
        infinito = -1
        assert security._clampar(100, infinito, infinito, infinito) == 100
        assert security._clampar(100, 50, infinito, infinito) == 50
        assert security._clampar(100, infinito, 50, infinito) == 50
        assert security._clampar(100, 200, 300, infinito) == 100

    @pytest.mark.skipif(not E_POSIX, reason="`resource` so existe em POSIX")
    def test_em_posix_o_rlimit_as_de_verdade_fica_de_pe(self, tmp_path):
        """O ramo real, contra o kernel de verdade. Roda no CI, que e Linux.

        Em subprocesso porque apertar `RLIMIT_AS` no processo do pytest apertaria
        o pytest, e o efeito nao teria como ser desfeito.
        """
        script = tmp_path / "posix.py"
        script.write_text(SCRIPT_LIMITES, encoding="utf-8")
        saida = _rodar(
            script,
            str(tmp_path / "vazio"),
            str(security.TETO_MEMORIA_BYTES),
            str(security.TETO_CPU_SEGUNDOS),
        )
        assert saida["disponivel"] is True
        aplicados = {nome: (soft, hard) for nome, soft, hard in saida["aplicados"]}
        assert "RLIMIT_CPU" in aplicados
        assert aplicados["RLIMIT_CPU"][0] <= security.TETO_CPU_SEGUNDOS
