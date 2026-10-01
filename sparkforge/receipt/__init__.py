"""Execution Receipt: o recibo content-addressed de uma execucao do case (§14).

`build` amarra, por caminho relativo e sha256 e sem copiar conteudo, o
`case.yaml`, a uniao dos arquivos de facts, os findings, o report, o
blackboard, os ADRs, os debates, os spans de um run declarado e o host que o
transcript declara. `verify` recalcula cada parte a partir do disco e diz qual
divergiu.

O recibo prova CORRESPONDENCIA entre ele e os artefatos, nunca autoria: nao ha
chave, e qualquer um com os mesmos artefatos e o mesmo `now` produz o mesmo
`receipt_id`. Este pacote nao le findings, report, spans nem transcript por
conta propria -- recebe o que o adapter ja leu -- e nao importa `adapters` nem
provider.
"""
from sparkforge.receipt._hash import RECEIPT_PREFIX, RECEIPT_VERSION
from sparkforge.receipt.build import build
from sparkforge.receipt.verify import verify

__all__ = ["RECEIPT_PREFIX", "RECEIPT_VERSION", "build", "verify"]
