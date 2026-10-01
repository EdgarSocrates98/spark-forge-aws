"""Travas de seguranca do subsistema de code intelligence: a estatica e as de runtime.

POR QUE ESTE MODULO EXISTE
--------------------------
O threat model (`docs/harness/THREAT-MODEL.md`) fecha 13 ameacas e deixa 14
parciais, e a leitura do conjunto diz que a maior parte das parciais e a MESMA
ausencia vista de angulos diferentes: nao existe nada que o processo FACA
enquanto roda. "Nao ha `socket` no pacote", "nao ha `subprocess` no pacote" sao
verdades de HOJE, garantidas pela forma do codigo e por mais nada -- e garantia
estrutural e a mais forte que existe enquanto a estrutura nao muda, e a mais
fragil no dia seguinte, porque o defeito entra por ACRESCIMO e acrescimo e o que
ninguem revisa como mudanca de seguranca.

Este modulo transforma parte dessas afirmacoes em coisas que falham.

AS DUAS METADES NAO TEM O MESMO PRECO, E ISSO IMPORTA
-----------------------------------------------------
`imports_proibidos` e ESTATICA: le arquivo, nao muda nada do processo, custa
milissegundos e roda no CI a cada push. E a trava mais barata do arquivo e a de
maior alcance, porque nenhum dos outros controles impede alguem de escrever
`import requests` -- eles so impediriam a conexao DEPOIS que o import existisse.

`install_audit_hook` e `apply_resource_limits` sao de RUNTIME, custam
irreversibilidade (a primeira) e portabilidade (a segunda). Estao aqui porque a
SPEC as pede na secao 11, nao porque substituam a estatica.

O QUE ESTE MODULO NAO FAZ
--------------------------
Nao chama nenhuma das tres. Instalar hook de auditoria no import de um modulo
seria decidir pelo processo inteiro a partir de um `from ... import ...` que
alguem escreveu sem ler isto aqui. Quem entra em `offline-strict` chama; o
modulo so oferece.

Nao implementa `lock_security_profile` da secao 11 da SPEC: a cadeia de
autorizacao vive em `sparkforge/agents/autonomy.py` e a lacuna dela esta
registrada em `docs/harness/AUTHORIZATION-CHAIN.md`. Travar aqui um perfil que
ninguem consulta seria acrescentar a segunda metade de um mecanismo cuja
primeira metade nao e chamada.
"""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Gate estatico de import de rede (SPEC secao 7, INV-001)
# ---------------------------------------------------------------------------

# A lista da SPEC, secao 7, literal. Sem excecao na primeira versao -- e a
# ausencia de excecao e proposital: uma allowlist de "so neste arquivo" e o
# lugar por onde a proibicao vaza, porque o proximo arquivo herda o precedente.
MODULOS_DE_REDE = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "websocket",
        "grpc",
        "boto3",
        "botocore",
    }
)

# `urllib.request` entra QUALIFICADO e nao pela raiz, porque `urllib.parse` e
# legitimo e usado para manipular string. Proibir `urllib` inteiro seria fechar
# uma porta que ninguem abriu e obrigar o proximo a reabrir a lista.
MODULOS_DE_REDE_QUALIFICADOS = ("urllib.request",)

# As duas construcoes que importam sem escrever `import`. Sem elas o gate
# checaria a grafia e nao o efeito, e `import_module("socket")` passaria limpo.
FUNCOES_DE_IMPORT_DINAMICO = frozenset({"__import__", "import_module"})


@dataclass(frozen=True)
class Violacao:
    """Um import de rede encontrado, com onde ele esta e o que ele traz.

    Carrega `arquivo`, `linha` e `modulo` porque uma violacao sem posicao vira
    uma discussao sobre onde ela esta, e o gate existe para acabar a discussao
    antes dela comecar.
    """

    arquivo: str
    linha: int
    modulo: str


def _modulo_proibido(nome: str) -> str | None:
    """Devolve o nome proibido que `nome` traz, ou None.

    Compara pela RAIZ pontuada (`grpc.aio` cai por `grpc`) e por prefixo
    qualificado (`urllib.request.urlopen` cai por `urllib.request`), porque
    comparacao por igualdade exata deixaria passar qualquer submodulo -- que e
    a forma mais obvia de contornar uma lista de nomes.
    """
    if not nome:
        return None
    raiz = nome.split(".", 1)[0]
    if raiz in MODULOS_DE_REDE:
        return raiz
    for qualificado in MODULOS_DE_REDE_QUALIFICADOS:
        if nome == qualificado or nome.startswith(qualificado + "."):
            return qualificado
    return None


def _nome_da_chamada(no: ast.Call) -> str | None:
    """Nome final da funcao chamada, seja `f(...)` ou `mod.f(...)`."""
    alvo = no.func
    if isinstance(alvo, ast.Name):
        return alvo.id
    if isinstance(alvo, ast.Attribute):
        return alvo.attr
    return None


def _violacoes_do_modulo(arvore: ast.AST, arquivo: str) -> list[Violacao]:
    achados: list[Violacao] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                proibido = _modulo_proibido(alias.name)
                if proibido:
                    achados.append(Violacao(arquivo, no.lineno, proibido))
        elif isinstance(no, ast.ImportFrom):
            # `level > 0` e import relativo do proprio pacote: nao ha como ele
            # alcancar `socket`, e tratar `from . import x` como absoluto daria
            # falso positivo em qualquer submodulo que se chamasse igual.
            if no.level:
                continue
            base = no.module or ""
            proibido = _modulo_proibido(base)
            if proibido:
                achados.append(Violacao(arquivo, no.lineno, proibido))
                continue
            for alias in no.names:
                # `from urllib import request` so e visivel juntando os dois.
                proibido = _modulo_proibido(f"{base}.{alias.name}" if base else alias.name)
                if proibido:
                    achados.append(Violacao(arquivo, no.lineno, proibido))
        elif isinstance(no, ast.Call):
            if _nome_da_chamada(no) not in FUNCOES_DE_IMPORT_DINAMICO:
                continue
            for argumento in no.args:
                if isinstance(argumento, ast.Constant) and isinstance(argumento.value, str):
                    proibido = _modulo_proibido(argumento.value)
                    if proibido:
                        achados.append(Violacao(arquivo, no.lineno, proibido))
    return achados


def imports_proibidos(raiz: str | os.PathLike[str] | None = None) -> tuple[Violacao, ...]:
    """Varre `*.py` sob `raiz` e devolve todo import de rede encontrado.

    `raiz` default e o proprio pacote `sparkforge/codeintel/`, que e o escopo
    que a SPEC proibe. O parametro existe para o teste poder rodar a mutacao
    sobre uma COPIA em tmpdir em vez de sujar a arvore -- gate que so sabe se
    pronunciar sobre si mesmo nao tem como provar que acusaria.

    Arquivo que nao parseia conta como violacao com modulo `<nao-parseia>`, e
    isso e INV-015 e nao descuido: um gate que pula o que nao entende ensina
    como contorna-lo.
    """
    base = Path(raiz) if raiz is not None else Path(__file__).resolve().parent
    achados: list[Violacao] = []
    for caminho in sorted(base.rglob("*.py")):
        relativo = caminho.relative_to(base).as_posix()
        try:
            fonte = caminho.read_text(encoding="utf-8")
            arvore = ast.parse(fonte, filename=str(caminho))
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            achados.append(Violacao(relativo, 0, "<nao-parseia>"))
            continue
        achados.extend(_violacoes_do_modulo(arvore, relativo))
    return tuple(achados)


# ---------------------------------------------------------------------------
# 2. sanitize_environment (SPEC secao 11, INV-003)
# ---------------------------------------------------------------------------

# Os nomes literais do INV-003. Ficam explicitos mesmo quando um marcador
# adiante ja os pegaria, porque a lista da SPEC e o contrato: apagar
# `GITHUB_TOKEN` daqui confiando em `TOKEN` deixaria o teste do contrato
# passando a depender de uma heuristica.
VARIAVEIS_SEGREDO = frozenset(
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

# `AWS_*` inteiro, e nao so as tres do INV-003: `AWS_PROFILE` e
# `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` nao sao segredo em si e sao
# exatamente o que faria um SDK ir buscar um -- e nao existe parser de AST que
# precise de qualquer variavel comecada em `AWS_`.
PREFIXOS_SEGREDO = ("AWS_",)

# O "ou qualquer variavel classificada como segredo" do INV-003. E heuristica,
# e ela erra para o lado de apagar demais de proposito (INV-015): o custo de
# tirar do parser uma variavel que nao era segredo e zero, porque ele nao le
# variavel nenhuma; o custo de deixar uma passar e o INV-003 inteiro.
MARCADORES_SEGREDO = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "APIKEY",
    "ACCESS_KEY",
    "CREDENTIAL",
    "PRIVATE_KEY",
    "SESSION_KEY",
)

def e_variavel_de_segredo(nome: str) -> bool:
    """Diz se `nome` deve sair do ambiente do processo de parsing.

    Normaliza para maiuscula antes de decidir porque em POSIX o ambiente
    diferencia caixa e `http_proxy` minusculo e tao honrado quanto o maiusculo
    -- decidir so sobre a grafia da SPEC deixaria a metade minuscula no lugar.
    """
    canonico = nome.upper()
    if canonico in VARIAVEIS_SEGREDO:
        return True
    if any(canonico.startswith(prefixo) for prefixo in PREFIXOS_SEGREDO):
        return True
    return any(marcador in canonico for marcador in MARCADORES_SEGREDO)


class SanitizacaoIncompleta(RuntimeError):
    """Uma variavel de segredo continuou legivel depois da remocao.

    Existe como excecao propria porque o caso e indistinguivel de sucesso pelo
    valor de retorno: `sanitize_environment` devolveria o nome como removido, e
    ele estaria la. INV-015 manda bloquear na duvida, e aqui nem duvida ha.
    """


def sanitize_environment(env: MutableMapping[str, str] | None = None) -> tuple[str, ...]:
    """Remove do ambiente toda variavel classificada como segredo. Devolve os nomes.

    `env` default e `os.environ`, ou seja, o ambiente REAL do processo -- e nao
    uma copia. Copiar seria mais seguro para quem chama e inutil para o
    INV-003: qualquer biblioteca que decidisse buscar credencial leria
    `os.environ`, nao a copia.

    O RETORNO NAO E A MEDICAO. Depois de apagar, a funcao LE DE VOLTA cada nome
    e so entao devolve. Uma implementacao que iterasse sobre `env` enquanto
    apaga -- ou que apagasse de uma copia por engano -- devolveria a mesma lista
    com o ambiente intacto, e "nao levantou" nao prova nada. Se algum nome
    sobreviver, levanta `SanitizacaoIncompleta`.
    """
    alvo = os.environ if env is None else env
    # `list(...)` antes de apagar: mutar o mapa durante a propria iteracao e
    # RuntimeError em `os.environ` como em qualquer dict.
    removidos = tuple(sorted(nome for nome in list(alvo) if e_variavel_de_segredo(nome)))
    for nome in removidos:
        del alvo[nome]
    sobreviventes = tuple(nome for nome in removidos if nome in alvo)
    if sobreviventes:
        raise SanitizacaoIncompleta(
            "variavel de segredo continuou legivel depois da remocao: "
            + ", ".join(sobreviventes)
        )
    return removidos


# ---------------------------------------------------------------------------
# 3. install_audit_hook (SPEC secao 11.1, INV-001)
# ---------------------------------------------------------------------------

# Os quatro eventos que a SPEC secao 11.1 nomeia.
EVENTOS_BLOQUEADOS = frozenset(
    {
        "socket.connect",
        "socket.bind",
        "os.system",
        "subprocess.Popen",
    }
)

# Acrescentados a lista da secao 11.1 porque o INV-001 diz "TCP, UDP, HTTP,
# HTTPS, DNS ou socket" e resolucao de nome e DNS: bloquear `connect` e deixar
# `getaddrinfo` permitiria exfiltrar por consulta DNS sem abrir conexao
# nenhuma. Ficam num conjunto separado para que a diferenca entre "o que a SPEC
# lista" e "o que acrescentamos" continue legivel.
EVENTOS_BLOQUEADOS_DNS = frozenset(
    {
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.sethostname",
    }
)

EVENTOS_RECUSADOS = EVENTOS_BLOQUEADOS | EVENTOS_BLOQUEADOS_DNS

_HOOK_INSTALADO = False


class OperacaoBloqueada(RuntimeError):
    """Uma operacao de rede ou de processo foi tentada sob o hook de auditoria.

    Herda de `RuntimeError` e nao de `Exception` nua para que um `except
    Exception` generico no caminho de parsing nao a engula silenciosamente sem
    aparecer em lugar nenhum -- ela ainda e capturavel, mas o nome sai no
    traceback.
    """


def install_audit_hook() -> bool:
    """Instala o hook que recusa socket, DNS e criacao de processo. True se instalou.

    IRREVERSIVEL E GLOBAL, e isto nao e detalhe de implementacao: `sys`
    nao tem `removeaudithook`. Instalado, o hook vale para o processo inteiro
    ate ele morrer -- incluindo bibliotecas que nada tem a ver com o parsing, e
    incluindo o proprio runner de teste, motivo pelo qual os testes deste modulo
    exercitam o hook em SUBPROCESSO e nao na suite.

    Devolve `False` quando ja havia instalado nesta mesma execucao. A guarda
    existe porque chamar duas vezes empilharia dois hooks -- o segundo nao faz
    mal, mas o custo por evento auditado dobra, e todo `open()` do processo
    passa pelos dois.

    A guarda e por MODULO, nao por processo: quem reimportar o modulo num
    interpretador ja endurecido reinstala. Nao ha como consultar a lista de
    hooks instalados em CPython, entao a alternativa seria mentir sobre saber.
    """
    global _HOOK_INSTALADO
    if _HOOK_INSTALADO:
        return False

    def _hook(evento: str, args: tuple[object, ...]) -> None:
        if evento in EVENTOS_RECUSADOS:
            raise OperacaoBloqueada(
                f"evento `{evento}` recusado: o code intelligence nao tem "
                "caminho autorizado de rede nem de subprocesso (INV-001)"
            )

    sys.addaudithook(_hook)
    _HOOK_INSTALADO = True
    return True


def hook_instalado() -> bool:
    """Diz se `install_audit_hook` ja rodou NESTE modulo. Nao consulta o interpretador.

    Existe para o teste poder afirmar a idempotencia sem inspecionar estado
    privado. Nao serve como prova de que o processo esta protegido: um hook
    instalado por outro caminho nao aparece aqui, e CPython nao expoe a lista.
    """
    return _HOOK_INSTALADO


# ---------------------------------------------------------------------------
# 4. apply_resource_limits (SPEC secao 41)
# ---------------------------------------------------------------------------

# Tetos duros. A SPEC secao 41 manda que os limites sejam configuraveis "porem
# com hard ceiling": o parametro pode APERTAR, nunca afrouxar.
TETO_MEMORIA_BYTES = 2 * 1024 * 1024 * 1024
TETO_CPU_SEGUNDOS = 300
TETO_RECURSAO = 1000


@dataclass(frozen=True)
class Limites:
    """O que foi aplicado, o que nao foi, e por que -- com valor LIDO DE VOLTA.

    `aplicados` guarda `(nome, soft, hard)` conforme devolvido por
    `getrlimit` DEPOIS do `setrlimit`, nunca o valor pedido. A diferenca e a
    unica coisa que separa este dataclass de uma promessa: `setrlimit` pode
    aceitar e o kernel entregar outro numero, e "nao levantou" nao e medicao.
    """

    aplicados: tuple[tuple[str, int, int], ...]
    nao_aplicados: tuple[tuple[str, str], ...]
    disponivel: bool
    motivo: str | None


class LimiteNaoAplicado(RuntimeError):
    """Pedido em modo estrito e o limite nao ficou de pe."""


def _clampar(pedido: int, soft: int, hard: int, infinito: int) -> int:
    """Escolhe o menor valor entre o pedido e o que ja vale. Nunca afrouxa.

    Um `setrlimit` que AUMENTASSE o limite herdado seria o oposto do controle:
    o processo pai pode ter apertado por um motivo que este modulo nao conhece,
    e reabrir seria decidir contra ele com menos informacao.
    """
    candidatos = [pedido]
    if soft != infinito:
        candidatos.append(soft)
    if hard != infinito:
        candidatos.append(hard)
    return min(candidatos)


def apply_resource_limits(
    *,
    memoria_bytes: int = TETO_MEMORIA_BYTES,
    cpu_segundos: int = TETO_CPU_SEGUNDOS,
    recursao: int = TETO_RECURSAO,
    estrito: bool = False,
) -> Limites:
    """Aperta memoria, CPU e recursao ate onde a plataforma permitir. Mede e relata.

    `resource` NAO EXISTE NO WINDOWS, e isto foi medido e nao suposto:
    `import resource` em CPython 3.14.6 no Windows 11 levanta
    `ModuleNotFoundError: No module named 'resource'`. O modulo e listado na
    documentacao como "Availability: Unix". Nao ha equivalente de `setrlimit`
    na biblioteca padrao para Windows -- um teto de memoria por processo ali
    exigiria Job Object via `ctypes`, que e codigo de plataforma que ninguem
    pediu e que nenhuma parte deste repositorio hoje sustenta.

    Por isso a funcao NAO finge: no Windows devolve `disponivel=False` com
    `motivo` nomeando a plataforma, e `aplicados` traz somente o limite de
    recursao, que e do `sys` e vale em todo lugar. Devolver um `Limites` cheio
    com valores que nao existem seria a pior saida das tres.

    `estrito=True` levanta `LimiteNaoAplicado` quando algum limite nao ficou de
    pe -- e a leitura INV-015 da funcao, e ela e OPCIONAL de proposito: fazer
    dela o default tornaria o pacote inutilizavel no Windows por decisao de um
    modulo que nao e dono dessa politica. Quem entra em `offline-strict`
    escolhe; quem so indexa nao paga.

    Os tres parametros so APERTAM. Pedir mais que o teto do modulo, ou mais que
    o limite ja herdado do processo pai, e reduzido em silencio ao menor deles
    -- ver `_clampar`.
    """
    aplicados: list[tuple[str, int, int]] = []
    nao_aplicados: list[tuple[str, str]] = []

    # Recursao primeiro: e o unico limite portavel, e ele vale mesmo quando
    # `resource` nao existe. `min` com o valor corrente porque baixar o teto de
    # recursao ja aplicado por quem chamou seria seguro, e subi-lo nao.
    alvo_recursao = min(recursao, TETO_RECURSAO, sys.getrecursionlimit())
    sys.setrecursionlimit(alvo_recursao)
    efetivo_recursao = sys.getrecursionlimit()
    if efetivo_recursao == alvo_recursao:
        aplicados.append(("RECURSAO", efetivo_recursao, efetivo_recursao))
    else:
        nao_aplicados.append(
            ("RECURSAO", f"pedido {alvo_recursao}, efetivo {efetivo_recursao}")
        )

    try:
        import resource
    except ImportError as erro:
        motivo = f"modulo `resource` indisponivel em sys.platform={sys.platform!r}: {erro}"
        nao_aplicados.append(("RLIMIT_AS", motivo))
        nao_aplicados.append(("RLIMIT_CPU", motivo))
        limites = Limites(
            aplicados=tuple(aplicados),
            nao_aplicados=tuple(nao_aplicados),
            disponivel=False,
            motivo=motivo,
        )
        if estrito:
            raise LimiteNaoAplicado(motivo) from erro
        return limites

    infinito = resource.RLIM_INFINITY
    pedidos = (
        ("RLIMIT_AS", resource.RLIMIT_AS, min(memoria_bytes, TETO_MEMORIA_BYTES)),
        ("RLIMIT_CPU", resource.RLIMIT_CPU, min(cpu_segundos, TETO_CPU_SEGUNDOS)),
    )
    for nome, recurso, pedido in pedidos:
        soft, hard = resource.getrlimit(recurso)
        alvo = _clampar(pedido, soft, hard, infinito)
        try:
            resource.setrlimit(recurso, (alvo, hard))
        except (ValueError, OSError) as erro:
            nao_aplicados.append((nome, f"setrlimit recusou {alvo}: {erro}"))
            continue
        # A medicao. `setrlimit` nao levantar nao prova que o valor ficou.
        efetivo_soft, efetivo_hard = resource.getrlimit(recurso)
        if efetivo_soft == alvo:
            aplicados.append((nome, efetivo_soft, efetivo_hard))
        else:
            nao_aplicados.append((nome, f"pedido {alvo}, efetivo {efetivo_soft}"))

    limites = Limites(
        aplicados=tuple(aplicados),
        nao_aplicados=tuple(nao_aplicados),
        disponivel=True,
        motivo=None,
    )
    if estrito and nao_aplicados:
        raise LimiteNaoAplicado(
            "limite pedido nao ficou de pe: "
            + "; ".join(f"{nome}: {razao}" for nome, razao in nao_aplicados)
        )
    return limites


__all__ = [
    "EVENTOS_BLOQUEADOS",
    "EVENTOS_BLOQUEADOS_DNS",
    "EVENTOS_RECUSADOS",
    "MARCADORES_SEGREDO",
    "MODULOS_DE_REDE",
    "MODULOS_DE_REDE_QUALIFICADOS",
    "PREFIXOS_SEGREDO",
    "TETO_CPU_SEGUNDOS",
    "TETO_MEMORIA_BYTES",
    "TETO_RECURSAO",
    "VARIAVEIS_SEGREDO",
    "LimiteNaoAplicado",
    "Limites",
    "OperacaoBloqueada",
    "SanitizacaoIncompleta",
    "Violacao",
    "apply_resource_limits",
    "e_variavel_de_segredo",
    "hook_instalado",
    "imports_proibidos",
    "install_audit_hook",
    "sanitize_environment",
]
