# sarif-schema-2.1.0.json

Schema oficial do SARIF 2.1.0, publicado pela OASIS. E a fonte T1 contra a qual
`tests/test_fixtures_golden_sarif.py` valida todo SARIF que
`sparkforge report github` produz nos testes.

| Campo | Valor |
|---|---|
| URL | https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json |
| Recuperado em | 2026-09-11 |
| Bytes | 112768 |
| sha256 (LF) | c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e |
| Dialeto | JSON Schema draft-04 |

O sha256 e calculado sobre o arquivo com fim de linha LF. O teste normaliza
CRLF para LF antes de conferir, porque o checkout do Windows converte arquivo
de texto (a mesma armadilha do golden de `host_transcript`, CI do PR #48).

Nao edite este arquivo. Uma versao nova do schema entra por download, com a
URL, a data e o sha256 atualizados aqui no mesmo commit.
