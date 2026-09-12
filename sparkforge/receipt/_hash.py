"""Digest do recibo de execucao: texto com CRLF normalizado e JSON canonico.

Todo artefato que o recibo amarra e texto, e o checkout do git no Windows pode
trocar os finais de linha. Hashear os bytes crus faria um recibo emitido numa
maquina divergir na outra sem que nada tivesse mudado; por isso o `\\r\\n` vira
`\\n` antes do sha256. A regra entra no hash por `RECEIPT_VERSION`: se um dia
ela mudar, a versao muda junto, e o verify diz "regra mudou" em vez de
"artefato adulterado".

O JSON canonico e o de `findings.models._canonical` (chaves ordenadas, sem
espacos, ASCII). O pacote ja tem seis helpers desse tipo; este modulo usa um
deles em vez de criar o setimo.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sparkforge.findings.models import _canonical

RECEIPT_VERSION = 1
RECEIPT_PREFIX = "rcpt_"


def text_sha256(path: Path | str) -> str:
    """sha256 do texto com `\\r\\n` normalizado para `\\n`."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def digest_of(value: Any) -> str:
    """sha256 do JSON canonico de `value`."""
    return hashlib.sha256(_canonical(value).encode("ascii")).hexdigest()


def receipt_id_of(doc: dict[str, Any]) -> str:
    """`rcpt_` + digest do recibo sem o proprio `receipt_id`."""
    sem_id = {chave: valor for chave, valor in doc.items() if chave != "receipt_id"}
    return RECEIPT_PREFIX + digest_of(sem_id)
