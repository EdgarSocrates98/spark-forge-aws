"""Escrita que sobrevive a uma queda no meio -- o estado do case nunca fica pela metade.

Quatro primitivas, e so quatro, para os arquivos que `resume`, o debate e o
blackboard LEEM como estado (`case.yaml`, `plan.json`, `decision.json`, os JSONL
do blackboard, `submissions.jsonl`, `facts.jsonl` do debate e o journal):

- `write_atomic` grava num temporario do MESMO diretorio, faz `fsync` e troca
  por `os.replace`. Uma queda antes da troca deixa o arquivo antigo inteiro; a
  troca em si nao tem estado intermediario legivel. No Windows, `os.replace`
  levanta `PermissionError` quando outro processo tem o destino aberto sem
  `FILE_SHARE_DELETE` -- tenta de novo algumas vezes antes de desistir.
- `write_atomic_bytes` e a mesma troca em modo binario, para arquivo que alguem
  rele por hash e cuja quebra de linha nao pode mudar na gravacao.
- `append_line` anexa UMA linha sob trava de arquivo. Se o arquivo termina sem
  `\\n`, sobrou a cauda de uma queda anterior: JSON valido so ganha o `\\n` que
  faltou; lixo vai para `<arquivo>.torn` (quarentena, nunca apagado) e o
  arquivo volta ao ultimo `\\n` antes do append. Sem isso o append seguinte
  transformaria a cauda numa linha corrompida NO MEIO.
- `read_jsonl` tolera so a cauda cortada e a devolve em `torn_tail`. Linha
  invalida no meio nao e queda, e outro defeito: levanta `DurableError` com o
  numero da linha.

A trava no Windows cai num byte muito alem do fim do arquivo, e nao no byte 0:
`msvcrt.locking` e obrigatoria, e travar o byte 0 faria quem so LE (sem trava)
receber `PermissionError` enquanto alguem anexa.

Nada aqui gera hora, e nada chama rede.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

_TENTATIVAS_REPLACE = 5
_ESPERA_REPLACE_S = 0.02
_BYTE_DA_TRAVA = 2**31 - 2
QUARENTENA_SUFIXO = ".torn"


class DurableError(ValueError):
    """Arquivo de estado ilegivel por um defeito que nao e queda."""


def write_atomic(path: Path | str, text: str) -> None:
    """Troca o conteudo de `path` por `text` de uma vez, ou nao troca."""
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(
        prefix=f".{destino.name}.", suffix=".tmp", dir=destino.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _replace(temporario, destino)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporario)
        raise


def write_atomic_bytes(path: Path | str, data: bytes) -> None:
    """`write_atomic` sem traducao de quebra de linha: grava os bytes como vieram.

    `write_atomic` abre em modo texto, e no Windows isso troca `\\n` por
    `\\r\\n`. Para quem rele o arquivo por hash (o `sdd stamp`), a troca muda o
    conteudo que o proprio hash descreve.
    """
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(
        prefix=f".{destino.name}.", suffix=".tmp", dir=destino.parent
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _replace(temporario, destino)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporario)
        raise


def _replace(temporario: str, destino: Path) -> None:
    for tentativa in range(_TENTATIVAS_REPLACE):
        try:
            os.replace(temporario, destino)
            return
        except PermissionError:
            if os.name != "nt" or tentativa == _TENTATIVAS_REPLACE - 1:
                raise
            time.sleep(_ESPERA_REPLACE_S)


def append_line(path: Path | str, montar: Callable[[str | None], str]) -> str:
    """Anexa a linha que `montar` devolver, sob trava; devolve a linha gravada.

    `montar` recebe a ultima linha valida do arquivo (sem `\\n`) ou `None`, e
    roda DENTRO da trava: quem encadeia (o journal) calcula `seq` e `prev` sem
    disputa com outro processo.
    """
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a+b") as fh:
        _travar(fh)
        try:
            fh.seek(0)
            conteudo = fh.read()
            conteudo = _reparar_cauda(destino, fh, conteudo)
            linhas = [linha for linha in conteudo.split(b"\n") if linha.strip()]
            ultima = linhas[-1].rstrip(b"\r").decode("utf-8") if linhas else None
            linha = montar(ultima)
            if "\n" in linha:
                raise DurableError(f"{destino}: linha a anexar contem quebra de linha")
            fh.seek(0, os.SEEK_END)
            fh.write(linha.encode("utf-8") + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
            return linha
        finally:
            _destravar(fh)


def append_text_line(path: Path | str, linha: str) -> str:
    """`append_line` para quem ja tem a linha pronta (sem encadeamento)."""
    return append_line(path, lambda _ultima: linha)


def _reparar_cauda(destino: Path, fh: IO[bytes], conteudo: bytes) -> bytes:
    corte = conteudo.rfind(b"\n") + 1
    cauda = conteudo[corte:]
    if not cauda:
        return conteudo
    if _e_json(cauda):
        fh.seek(0, os.SEEK_END)
        fh.write(b"\n")
        return conteudo + b"\n"
    with destino.with_name(destino.name + QUARENTENA_SUFIXO).open("ab") as quarentena:
        quarentena.write(cauda + b"\n")
    fh.truncate(corte)
    return conteudo[:corte]


def _e_json(dado: bytes) -> bool:
    try:
        json.loads(dado.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return True


def read_jsonl(path: Path | str) -> tuple[list[dict[str, Any]], str | None]:
    """`(registros, torn_tail)`; arquivo ausente e `([], None)`."""
    origem = Path(path)
    if not origem.is_file():
        return [], None
    conteudo = origem.read_bytes()
    pedacos = conteudo.split(b"\n")
    termina_em_quebra = conteudo.endswith(b"\n")
    registros: list[dict[str, Any]] = []
    torn: str | None = None
    for indice, bruto in enumerate(pedacos, start=1):
        pedaco = bruto.rstrip(b"\r")
        if not pedaco.strip():
            continue
        ultimo = indice == len(pedacos) and not termina_em_quebra
        try:
            registros.append(json.loads(pedaco.decode("utf-8")))
        except (UnicodeDecodeError, ValueError) as exc:
            if ultimo:
                torn = pedaco.decode("utf-8", errors="replace")
                continue
            raise DurableError(
                f"{origem}: linha {indice} nao e JSON valido ({type(exc).__name__}); "
                f"so a ultima linha cortada por uma queda e tolerada. Confira o "
                f"arquivo com `sparkforge journal verify` se ele for o journal."
            ) from exc
    return registros, torn


def read_records(path: Path | str) -> list[dict[str, Any]]:
    """So os registros de `read_jsonl`, para quem nao precisa saber da cauda."""
    return read_jsonl(path)[0]


def _travar(fh: IO[bytes]) -> None:
    if os.name == "nt":
        import msvcrt

        fh.seek(_BYTE_DA_TRAVA)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)


def _destravar(fh: IO[bytes]) -> None:
    if os.name == "nt":
        import msvcrt

        fh.seek(_BYTE_DA_TRAVA)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
