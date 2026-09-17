"""Gravacao do par `started`/`finished` em volta de um verbo de escrita.

`recording()` e o unico ponto de gravacao, chamado pelas duas portas:
`adapters.tools.call_tool` (MCP) e `adapters.cli._dispatch` (CLI). Ele nunca
derruba o verbo (regra 27): falha do journal vira `journal: "unrecorded"` com
`journal_reason` no resultado, e o verbo segue.

A raiz do journal e a raiz do case que o verbo toca: o argumento `repo` (ou
`raiz`, na CLI do `scan`). Os tres verbos sem `repo` (`report sign`,
`funcval plan`, `funcval compare`) usam o primeiro ancestral do arquivo de
saida que tem `.sparkforge/case.yaml`; sem ancestral, nao gravam
(`sem_raiz_de_case`) -- com o cwd na raiz do projeto, o journal sujaria o
repositorio.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from sparkforge.case.store import CASE_DIR, CASE_FILE
from sparkforge.durable import append_line
from sparkforge.journal import LITERAL_KEYS, SCHEMA_VERSION, journal_path, journaled
from sparkforge.paths import resolve_within

UNRECORDED = "unrecorded"
SEM_RAIZ_DE_CASE = "sem_raiz_de_case"
RAIZ_INEXISTENTE = "raiz_inexistente"
VERBO_SEM_DECLARACAO = "verbo_sem_declaracao_de_saida"

_CHAVES_DE_RAIZ = ("repo", "raiz")
_CHAVES_DE_SAIDA = ("report", "report_path", "out", "out_path")
_CASE_YAML = f"{CASE_DIR}/{CASE_FILE}"
_MANIFESTO = f"{CASE_DIR}/artifacts/manifest.json"

_SAIDAS_FIXAS: dict[str, tuple[str, ...]] = {
    "sparkforge_case_open": (_CASE_YAML,),
    "sparkforge_case_update": (_CASE_YAML,),
}
_SAIDAS_POR_CHAVE: dict[str, tuple[str, ...]] = {
    "sparkforge_scan": ("outputs",),
    "sparkforge_receipt_emit": ("receipt_path",),
    "sparkforge_sdd_stamp": ("path",),
}


def canonico(valor: Any) -> str:
    return json.dumps(
        valor, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _parece_caminho_absoluto(texto: str) -> bool:
    janela = PureWindowsPath(texto)
    return PurePosixPath(texto).is_absolute() or janela.is_absolute() or bool(janela.drive)


def _literal_seguro(valor: Any) -> bool:
    if valor is None or isinstance(valor, (bool, int)):
        return True
    if isinstance(valor, str):
        return not _parece_caminho_absoluto(valor)
    if isinstance(valor, (list, tuple)):
        return all(isinstance(item, (str, int)) and _literal_seguro(item) for item in valor)
    return False


def normalizar_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """Todo argumento vira `sha256:<hex>`, salvo `LITERAL_KEYS` com valor seguro."""
    saida: dict[str, Any] = {}
    for chave in sorted(args):
        valor = args[chave]
        if chave in LITERAL_KEYS and _literal_seguro(valor):
            saida[chave] = list(valor) if isinstance(valor, tuple) else valor
        else:
            saida[chave] = "sha256:" + sha256_texto(canonico(valor))
    return saida


def raiz_do_journal(args: Mapping[str, Any]) -> tuple[Path | None, str | None]:
    """`(raiz, None)` ou `(None, motivo)`."""
    for chave in _CHAVES_DE_RAIZ:
        valor = args.get(chave)
        if isinstance(valor, str) and valor:
            raiz = Path(valor)
            return (raiz, None) if raiz.is_dir() else (None, RAIZ_INEXISTENTE)
    for chave in _CHAVES_DE_SAIDA:
        valor = args.get(chave)
        if isinstance(valor, str) and valor:
            ancestral = _ancestral_com_case(Path(valor))
            return (ancestral, None) if ancestral else (None, SEM_RAIZ_DE_CASE)
    return None, SEM_RAIZ_DE_CASE


def _ancestral_com_case(caminho: Path) -> Path | None:
    inicio = caminho.resolve().parent
    for diretorio in (inicio, *inicio.parents):
        if (diretorio / CASE_DIR / CASE_FILE).is_file():
            return diretorio
    return None


def _encadear(evento: dict[str, Any]) -> Callable[[str | None], str]:
    def montar(ultima: str | None) -> str:
        if ultima is None:
            seq, prev = 1, None
        else:
            seq, prev = int(json.loads(ultima)["seq"]) + 1, sha256_texto(ultima)
        return canonico({**evento, "seq": seq, "prev": prev})

    return montar


def _relativo(raiz: Path, caminho: str) -> tuple[str, Path | None]:
    bruto = Path(caminho)
    candidato = bruto if bruto.is_absolute() else raiz / bruto
    if not bruto.is_absolute() and not candidato.exists() and bruto.exists():
        candidato = bruto.resolve()
    real = resolve_within(raiz, candidato)
    if real is None:
        return "fora_da_raiz:" + sha256_texto(str(bruto)), None
    return real.relative_to(raiz.resolve()).as_posix(), real


def _sha256_arquivo(caminho: Path | None) -> str | None:
    if caminho is None or not caminho.is_file():
        return None
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _caminhos_de_saida(tool: str, resultado: Any) -> list[str]:
    caminhos = list(_SAIDAS_FIXAS.get(tool, ()))
    dados = resultado if isinstance(resultado, Mapping) else {}
    if tool.startswith("sparkforge_collect_"):
        caminhos.append(_MANIFESTO)
        if isinstance(dados.get("path"), str):
            caminhos.append(dados["path"])
    for chave in _SAIDAS_POR_CHAVE.get(tool, ()):
        valor = dados.get(chave)
        if isinstance(valor, str):
            caminhos.append(valor)
        elif isinstance(valor, list):
            caminhos.extend(item for item in valor if isinstance(item, str))
    if tool == "sparkforge_debate_start" and isinstance(dados.get("state_dir"), str):
        caminhos.append(str(Path(dados["state_dir"]) / "plan.json"))
    return caminhos


def saidas(tool: str, raiz: Path, resultado: Any) -> dict[str, str | None] | None:
    """sha256 de cada arquivo que o verbo declara ter gravado; `None` sem declaracao."""
    caminhos = _caminhos_de_saida(tool, resultado)
    if not caminhos:
        return None
    mapa: dict[str, str | None] = {}
    for caminho in caminhos:
        relativo, real = _relativo(raiz, caminho)
        mapa[relativo] = _sha256_arquivo(real)
    return mapa


class Registro:
    """Estado de uma chamada: o `started` gravado (ou o motivo de nao gravar)."""

    def __init__(self, tool: str, port: str) -> None:
        self.tool = tool
        self.port = port
        self.ativo = False
        self.raiz: Path | None = None
        self.started_seq: int | None = None
        self.motivo: str | None = None
        self.fechado = False

    def start(self, args: Mapping[str, Any], now: Any = None) -> None:
        if self.tool not in journaled():
            return
        self.ativo = True
        raiz, motivo = raiz_do_journal(args)
        if raiz is None:
            self.motivo = motivo
            return
        normalizados = normalizar_args(args)
        evento = {
            "event": "started",
            "tool": self.tool,
            "port": self.port,
            "call": sha256_texto(self.tool + "\n" + canonico(normalizados)),
            "args": normalizados,
            "at": now if isinstance(now, str) and now else None,
            "schema_version": SCHEMA_VERSION,
        }
        linha = append_line(journal_path(raiz), _encadear(evento))
        self.started_seq = int(json.loads(linha)["seq"])
        self.raiz = raiz

    def falhou(self, exc: BaseException) -> None:
        self.ativo = self.tool in journaled()
        self.motivo = f"{type(exc).__name__}: {exc}"[:300]

    def finish(self, resultado: Any, outcome: str) -> Any:
        """Grava o `finished`; devolve o resultado (marcado so se o journal falhou)."""
        if not self.ativo or self.fechado:
            return resultado
        self.fechado = True
        if self.started_seq is not None and self.raiz is not None:
            try:
                self._gravar_finished(resultado, outcome)
            except Exception as exc:  # noqa: BLE001 -- journal nunca derruba o verbo
                self.motivo = f"{type(exc).__name__}: {exc}"[:300]
        if self.motivo and isinstance(resultado, dict):
            return {**resultado, "journal": UNRECORDED, "journal_reason": self.motivo}
        return resultado

    def _gravar_finished(self, resultado: Any, outcome: str) -> None:
        assert self.raiz is not None
        evento: dict[str, Any] = {
            "event": "finished",
            "tool": self.tool,
            "started_seq": self.started_seq,
            "outcome": outcome,
            "schema_version": SCHEMA_VERSION,
        }
        mapa = saidas(self.tool, self.raiz, resultado)
        if mapa is None:
            evento["outputs_unresolved"] = VERBO_SEM_DECLARACAO
        else:
            evento["outputs"] = mapa
        append_line(journal_path(self.raiz), _encadear(evento))


@contextlib.contextmanager
def recording(
    tool: str, port: str, args: Mapping[str, Any], now: Any = None
) -> Iterator[Registro]:
    """Grava `started` na entrada; `finished` pelo `finish` do chamador ou na saida."""
    registro = Registro(tool, port)
    try:
        registro.start(args, now)
    except Exception as exc:  # noqa: BLE001 -- journal nunca derruba o verbo
        registro.falhou(exc)
    try:
        yield registro
    except BaseException:
        registro.finish(None, "error")
        raise
    registro.finish(None, "ok")
