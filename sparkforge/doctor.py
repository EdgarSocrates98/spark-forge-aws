"""`sparkforge doctor` (§22): o ambiente esta pronto?

A sondagem mora em `_core.doctor` (ela toca o ambiente); a AVALIACAO mora aqui e
e pura: cada `avaliar_<id>` recebe a saida crua de uma porta que ja existe e
devolve uma `Checagem`. Isso deixa cada status testavel com um dicionario, sem
montar um ambiente quebrado.

`unlock` e o comando que resolve, escrito pelo projeto -- nunca saida de rede.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sparkforge.integrate.hosts import HOSTS

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"
STATUS = (OK, WARN, FAIL, SKIP)
PYTHON_MINIMO = (3, 10)
EXTRA_DO_MODULO = {"mcp": "mcp", "boto3": "aws", "pyarrow": "parquet"}


@dataclass(frozen=True)
class Checagem:
    id: str
    status: str
    detail: str
    unlock: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "detail": self.detail, "unlock": self.unlock}


def _instalar(extras: list[str]) -> str:
    return f'pip install "sparkforge-aws[{",".join(extras)}]"'


def avaliar_pacote(versao: str | None, python: tuple[int, ...]) -> Checagem:
    py = ".".join(str(n) for n in python)
    if tuple(python[:2]) < PYTHON_MINIMO:
        return Checagem("pacote", FAIL, f"Python {py} abaixo do minimo 3.10",
                        "use Python 3.10 ou mais novo")
    if not versao:
        return Checagem("pacote", WARN, f"versao do sparkforge nao resolvida (Python {py})",
                        "pip install -e .")
    return Checagem("pacote", OK, f"sparkforge {versao}, Python {py}")


def avaliar_extras(disponiveis: Mapping[str, bool]) -> Checagem:
    faltando = sorted(m for m, ok in disponiveis.items() if not ok)
    if faltando:
        extras = sorted({EXTRA_DO_MODULO.get(m, m) for m in faltando})
        return Checagem("extras", WARN, f"modulos ausentes: {', '.join(faltando)}",
                        _instalar(extras))
    return Checagem("extras", OK, f"instalados: {', '.join(sorted(disponiveis))}")


def avaliar_mcp(extra: bool, tools: int | None, erro: str | None) -> Checagem:
    if not extra:
        return Checagem("mcp", SKIP, "SDK do MCP ausente", _instalar(["mcp"]))
    if erro:
        return Checagem("mcp", FAIL, f"servidor nao monta: {erro}",
                        "python -m sparkforge.adapters.mcp --help")
    return Checagem("mcp", OK, f"servidor montavel, {tools} tools")


def avaliar_catalogo(regras: int | None, erro: str | None) -> Checagem:
    if erro:
        return Checagem("catalogo", FAIL, f"catalogo invalido: {erro}",
                        "confira SPARKFORGE_CATALOG ou reinstale o pacote")
    return Checagem("catalogo", OK, f"{regras} regras carregadas")


def avaliar_packs(saida: Mapping[str, Any] | None, erro: str | None) -> Checagem:
    if erro:
        return Checagem("packs", FAIL, f"pack list falhou: {erro}", "sparkforge pack list")
    saida = saida or {}
    recusados = list(saida.get("refused") or [])
    # `env` e o NOME da variavel, sempre presente; o que diz se ha pack
    # configurado e haver algum ativo ou recusado.
    if not saida.get("active") and not recusados:
        return Checagem("packs", SKIP, "nenhum pack configurado (SPARKFORGE_PACKS vazia)")
    if recusados:
        motivos = sorted({str(r.get("reason")) for r in recusados if isinstance(r, Mapping)})
        return Checagem("packs", WARN,
                        f"{len(recusados)} pack(s) recusado(s): {', '.join(motivos)}",
                        "sparkforge pack check <pasta-do-pack>")
    return Checagem("packs", OK, f"{len(saida.get('active') or [])} pack(s) ativo(s)")


def avaliar_knowledge(contagem: Mapping[str, int] | None, erro: str | None) -> Checagem:
    if erro:
        return Checagem("knowledge", FAIL, f"knowledge nao resolvido: {erro}",
                        "sparkforge knowledge path")
    contagem = contagem or {}
    resumo = ", ".join(f"{k} {v}" for k, v in sorted(contagem.items()) if v)
    if contagem.get("stale", 0):
        return Checagem("knowledge", WARN, f"fontes que mudaram depois da leitura: {resumo}",
                        "sparkforge knowledge drift")
    return Checagem("knowledge", OK, f"fontes vigiadas: {resumo or 'nenhuma'}")


def avaliar_indice(status: Mapping[str, Any] | None, erro: str | None) -> Checagem:
    if erro:
        return Checagem("indice_de_codigo", WARN, f"estado do indice nao lido: {erro}",
                        "sparkforge code status --root .")
    status = status or {}
    if not status.get("initialized"):
        return Checagem("indice_de_codigo", SKIP, "indice de codigo nao criado",
                        "sparkforge code init --root .")
    if status.get("fresh") is None:
        # O doctor NAO confere frescor: conferir grava `freshness_checked_ns` no
        # indice (e por isso `code_status` e tool que escreve), e o doctor so le.
        return Checagem("indice_de_codigo", OK,
                        "indice criado; o frescor se confere com code status",
                        "sparkforge code status --root .")
    if not status.get("fresh"):
        razao = status.get("stale_reason") or "arquivos mudaram desde a indexacao"
        return Checagem("indice_de_codigo", WARN, f"indice velho: {razao}",
                        "sparkforge code sync --root .")
    return Checagem("indice_de_codigo", OK, "indice fresco")


def avaliar_artefatos(verificacao: Mapping[str, Any] | None, erro: str | None) -> Checagem:
    if erro:
        return Checagem("artefatos", WARN, f"manifesto nao conferido: {erro}",
                        "sparkforge collect verify --repo .")
    verificacao = verificacao or {}
    if not verificacao.get("total_count"):
        return Checagem("artefatos", SKIP, "sem manifesto de artefatos coletados")
    ruins = int(verificacao.get("missing_count", 0)) + int(verificacao.get("mismatched_count", 0))
    if ruins:
        return Checagem("artefatos", WARN, f"{ruins} artefato(s) ausente(s) ou divergente(s)",
                        "sparkforge collect verify --repo .")
    return Checagem("artefatos", OK, f"{verificacao.get('ok_count', 0)} artefato(s) integro(s)")


def avaliar_credencial(
    boto3: bool, metodo: str | None, conta: str | None, erro: str | None, online: bool
) -> Checagem:
    if not boto3:
        return Checagem("credencial_aws", SKIP, "boto3 ausente", _instalar(["aws"]))
    if erro:
        return Checagem("credencial_aws", WARN, f"credencial nao confirmada: {erro}",
                        "aws sts get-caller-identity")
    if not metodo:
        return Checagem("credencial_aws", WARN,
                        "nenhuma credencial resolvida pela cadeia do boto3",
                        "aws configure, ou defina AWS_PROFILE")
    if online:
        return Checagem("credencial_aws", OK, f"credencial ({metodo}) confirmada, conta {conta}")
    return Checagem("credencial_aws", OK,
                    f"credencial resolvida localmente ({metodo}); sem chamada de rede",
                    "sparkforge doctor --online")


def _arquivos_do_host(manifesto: Mapping[str, Any], host: str) -> int:
    """Quantos arquivos o manifesto (formato 2) registra com `host` entre os donos."""
    arquivos = manifesto.get("files") or {}
    return sum(
        1 for registro in arquivos.values()
        if isinstance(registro, Mapping) and host in (registro.get("owners") or [])
    )


def avaliar_integracoes(
    manifesto: Mapping[str, Any] | None,
    erro: str | None,
    em_dobro: Mapping[str, list[str]] | None,
) -> list[Checagem]:
    """Uma checagem por host: integrado ou nao, em que versao do pacote, e a copia
    vendorizada em dobro no repositorio atual (INTEGRACAO_USUARIO, AC11)."""
    if erro:
        return [Checagem("integracao", WARN, f"manifesto de integracao nao lido: {erro}",
                         "sparkforge integrate all --scope user --dry-run")]
    hosts = (manifesto or {}).get("hosts") or {}
    checagens = []
    for host in HOSTS:
        ident = f"integracao_{host}"
        entrada = hosts.get(host)
        if entrada is None:
            checagens.append(Checagem(ident, SKIP, "integracao de usuario ausente",
                                      f"sparkforge integrate {host} --scope user"))
            continue
        versao = entrada.get("package_version") or "?"
        detalhe = (
            f"integrado pelo sparkforge {versao}, "
            f"{_arquivos_do_host(manifesto or {}, host)} arquivo(s)"
        )
        dobro = sorted((em_dobro or {}).get(host) or [])
        if dobro:
            checagens.append(Checagem(
                ident, WARN,
                f"{detalhe}; copia vendorizada em dobro no repositorio: {', '.join(dobro)}",
                f"sparkforge integrate {host} --scope user --on-conflict merge",
            ))
            continue
        checagens.append(Checagem(ident, OK, detalhe))
    return checagens


def resumo(checagens: list[Checagem], online: bool) -> dict[str, Any]:
    contagem = {s: sum(1 for c in checagens if c.status == s) for s in STATUS}
    return {
        "checks": [c.to_dict() for c in checagens],
        "counts": contagem,
        "healthy": contagem[FAIL] == 0,
        "online": online,
    }
