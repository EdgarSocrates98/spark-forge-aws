#!/usr/bin/env python3
"""Golden de paridade do servidor MCP: o que o cliente recebe, byte a byte.

Existe por causa da migracao do SDK `mcp` 1.x para 2.x. O 1.x fazia calado
tres coisas que `sparkforge/adapters/mcp.py` nunca escreveu -- validar
`arguments` contra o `inputSchema`, validar o resultado contra o
`outputSchema` e montar `structuredContent` com o texto em
`json.dumps(indent=2)` -- e o 2.x nao faz nenhuma delas. "A migracao nao mudou
nada" so tem sentido comparando contra uma referencia que o PROPRIO 1.x
produziu. Este script produz essa referencia e compara contra ela.

Dois subcomandos, e nada do argv chega a caminho:

  python scripts/mcp_parity.py snapshot   # SO sob mcp<2: grava fixtures/mcp_parity/
  python scripts/mcp_parity.py diff       # qualquer versao: compara contra o golden

`snapshot` roda a amostra DUAS vezes e recusa gravar se as duas divergirem:
saida nao deterministica (horario, caminho absoluto) nao entra no golden, porque
golden instavel ensina a ignorar o diff. Sob `mcp>=2` ele recusa rodar, exceto
com `--force-regenerate-under-2x --reason "<texto>"`, e o motivo fica gravado
em `meta.json` -- regenerar sob a versao nova apagaria justamente a referencia.

A comparacao e no nivel do FIO: cada resultado vira
`model_dump(mode="json", by_alias=True, exclude_none=True)`. Com alias, as
chaves sao as do protocolo (`inputSchema`, `isError`, `structuredContent`) e
nao os nomes Python, que no 2.x viraram snake_case.

As chamadas rodam com o diretorio corrente num temporario com copia das
fixtures, para que o ledger de `call_tool` e o `.sparkforge/` nao escrevam na
arvore e para que os caminhos na saida sejam relativos e iguais entre maquinas.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "fixtures" / "mcp_parity"
TRANSPORTES = ("stdio", "http")
FIXTURES_COPIADAS = ("pyspark/action_in_loop", "debate/consenso_com_vencedor")

AMOSTRA: tuple[dict[str, Any], ...] = (
    {
        "id": "sucesso_analyze",
        "transport": "stdio",
        "name": "sparkforge_analyze_pyspark",
        "arguments": {"path": "action_in_loop/input"},
        "motivo": "extrator puro sobre fixture versionada; caminhos relativos na saida",
    },
    {
        "id": "sucesso_verbo_lookup",
        "transport": "stdio",
        "name": "sparkforge_rules_lookup",
        "arguments": {"id": ["SF-TIMEOUT-002"]},
        "motivo": "le o catalogo de regras, sem I/O de AWS",
    },
    {
        "id": "sucesso_verbo_release",
        "transport": "stdio",
        "name": "sparkforge_release_describe",
        "arguments": {"platform": "glue", "release": "5.0"},
        "motivo": "le a matriz de releases, sem I/O de AWS",
    },
    {
        "id": "sucesso_debate",
        "transport": "stdio",
        "name": "sparkforge_debate_referee",
        "arguments": {"repo": "consenso_com_vencedor/input"},
        "motivo": "familia debate, so leitura sobre caso de fixtures/debate/",
    },
    {
        "id": "sucesso_collect_offline",
        "transport": "stdio",
        "name": "sparkforge_collect_verify",
        "arguments": {"repo": "."},
        "motivo": "unico collect com caminho offline deterministico: confere o manifesto local",
    },
    {
        "id": "erro_fronteira",
        "transport": "stdio",
        "name": "sparkforge_analyze_pyspark",
        "arguments": {"path": "nao/existe.py"},
        "motivo": "AdapterError vira {error, exit_code}: envelope compacto",
    },
    {
        "id": "input_tipo_invalido",
        "transport": "stdio",
        "name": "sparkforge_rules_lookup",
        "arguments": {"id": "SF-TIMEOUT-002"},
        "motivo": "string onde o inputSchema pede array: Input validation error do 1.x",
    },
    {
        "id": "input_obrigatorio_ausente",
        "transport": "stdio",
        "name": "sparkforge_release_describe",
        "arguments": {"release": "5.0"},
        "motivo": "campo obrigatorio ausente: Input validation error do 1.x",
    },
    {
        "id": "fora_do_catalogo_http",
        "transport": "http",
        "name": "sparkforge_code_read",
        "arguments": {},
        "motivo": "SPEC 71: tool de fonte escondida e recusada no transporte http",
    },
    {
        "id": "nome_desconhecido",
        "transport": "stdio",
        "name": "sparkforge_nao_existe",
        "arguments": {},
        "motivo": "nome fora de qualquer catalogo: mesma porta do transporte",
    },
)


def mcp_version() -> str:
    from importlib.metadata import version

    return version("mcp")


def mcp_major() -> int:
    return int(mcp_version().split(".")[0])


def canonico(modelo: Any) -> Any:
    """O resultado como ele sai no fio: chaves do protocolo, sem `None`."""
    return modelo.model_dump(mode="json", by_alias=True, exclude_none=True)


@contextlib.contextmanager
def workspace() -> Iterator[Path]:
    """Diretorio temporario com as fixtures da amostra, como diretorio corrente."""
    anterior = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="mcp_parity_") as tmp:
        base = Path(tmp)
        for rel in FIXTURES_COPIADAS:
            origem = ROOT / "fixtures" / rel
            shutil.copytree(origem, base / origem.name)
        os.chdir(base)
        try:
            yield base
        finally:
            os.chdir(anterior)


@contextlib.asynccontextmanager
async def _cliente(server: Any, modo: str):
    if mcp_major() >= 2:
        from mcp import Client

        async with Client(server, mode=modo) as cliente:
            yield cliente
    else:
        from mcp.shared.memory import create_connected_server_and_client_session

        async with create_connected_server_and_client_session(server) as sessao:
            yield sessao


async def _pedir(cliente: Any, modo: str, metodo: str, params: dict[str, Any]) -> Any:
    """Uma requisicao, como o cliente a recebeu.

    Sob o 2.x no modo `legacy` a resposta e o JSON CRU do fio, lido pelo
    despachante da sessao: o modelo do cliente 2.x preenche campos com default
    (`resultType`, e o cache local acrescenta `ttlMs`/`cacheScope`) que o
    servidor NAO mandou, e compara-lo contra o golden acusaria bytes que nao
    existem. `_dispatcher` e API privada, e o pin `mcp<3` e o que a sustenta.

    No modo `auto` (era 2026-07-28) e no 1.x a resposta e o modelo do cliente
    com alias: na era nova o envelope por requisicao nao se manda cru sem
    reimplementar o handshake, e o que se compara ali e o conteudo, nao o
    envelope.
    """
    if mcp_major() >= 2 and modo == "legacy":
        return await cliente.session._dispatcher.send_raw_request(metodo, params, None)
    if metodo == "tools/list":
        return canonico(await cliente.list_tools())
    return canonico(await cliente.call_tool(params["name"], params["arguments"]))


async def _coletar_async(modo: str) -> dict[str, Any]:
    from sparkforge.adapters.mcp import build_server

    listas: dict[str, Any] = {}
    chamadas: dict[str, Any] = {}
    for transport in TRANSPORTES:
        async with _cliente(build_server(transport), modo) as cliente:
            listas[transport] = await _pedir(cliente, modo, "tools/list", {})
            for item in AMOSTRA:
                if item["transport"] != transport:
                    continue
                pedido = {"name": item["name"], "arguments": item["arguments"]}
                chamadas[item["id"]] = {
                    "transport": transport,
                    "name": item["name"],
                    "arguments": item["arguments"],
                    "motivo": item["motivo"],
                    "result": await _pedir(cliente, modo, "tools/call", pedido),
                }
    return {"tools_list": listas, "calls": chamadas}


def coletar(modo: str = "legacy") -> dict[str, Any]:
    """Dirige o servidor em processo e devolve listas e chamadas canonicas.

    `modo` so tem efeito sob o 2.x: `"legacy"` e o handshake `initialize` que o
    1.x falava -- o mesmo fio do golden --, e `"auto"` negocia a era
    `2026-07-28`, onde o SDK acrescenta `resultType` e o carimbo
    `_meta.serverInfo` em toda resposta. Sob o 1.x so existe o legado.
    """
    import anyio

    with workspace():
        return anyio.run(_coletar_async, modo)


def _dump(dado: Any) -> str:
    return json.dumps(dado, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _golden_files(coleta: dict[str, Any], meta: dict[str, Any]) -> dict[str, str]:
    return {
        "tools_list_stdio.json": _dump(coleta["tools_list"]["stdio"]),
        "tools_list_http.json": _dump(coleta["tools_list"]["http"]),
        "calls.json": _dump(coleta["calls"]),
        "meta.json": _dump(meta),
    }


def carregar_golden() -> dict[str, Any]:
    return {
        "tools_list": {
            t: json.loads((GOLDEN_DIR / f"tools_list_{t}.json").read_text(encoding="utf-8"))
            for t in TRANSPORTES
        },
        "calls": json.loads((GOLDEN_DIR / "calls.json").read_text(encoding="utf-8")),
        "meta": json.loads((GOLDEN_DIR / "meta.json").read_text(encoding="utf-8")),
    }


def diferencas(esperado: Any, obtido: Any, caminho: str = "$") -> list[tuple[str, Any, Any]]:
    """Lista `(caminho, esperado, obtido)` de toda folha que difere."""
    if isinstance(esperado, dict) and isinstance(obtido, dict):
        saida: list[tuple[str, Any, Any]] = []
        for chave in sorted(set(esperado) | set(obtido)):
            filho = f"{caminho}.{chave}"
            if chave not in obtido:
                saida.append((filho, esperado[chave], "<ausente>"))
            elif chave not in esperado:
                saida.append((filho, "<ausente>", obtido[chave]))
            else:
                saida.extend(diferencas(esperado[chave], obtido[chave], filho))
        return saida
    if isinstance(esperado, list) and isinstance(obtido, list) and len(esperado) == len(obtido):
        saida = []
        for i, (a, b) in enumerate(zip(esperado, obtido, strict=True)):
            saida.extend(diferencas(a, b, f"{caminho}[{i}]"))
        return saida
    return [] if esperado == obtido else [(caminho, esperado, obtido)]


def diff_contra_golden(coleta: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    golden = carregar_golden()
    return diferencas(
        {"tools_list": golden["tools_list"], "calls": golden["calls"]},
        {"tools_list": coleta["tools_list"], "calls": coleta["calls"]},
    )


def _cmd_snapshot(args: argparse.Namespace) -> int:
    if mcp_major() >= 2 and not args.force_regenerate_under_2x:
        print(
            f"snapshot recusado sob mcp {mcp_version()}: o golden e a referencia do 1.x. "
            "Use --force-regenerate-under-2x --reason '<motivo>' se a mudanca e legitima.",
            file=sys.stderr,
        )
        return 2
    if args.force_regenerate_under_2x and not (args.reason or "").strip():
        print("--force-regenerate-under-2x exige --reason", file=sys.stderr)
        return 2
    primeira = coletar()
    segunda = coletar()
    instaveis = diferencas(primeira, segunda)
    if instaveis:
        for caminho, _, _ in instaveis:
            print(f"instavel entre duas execucoes: {caminho}", file=sys.stderr)
        return 1
    from importlib.metadata import version

    import jsonschema  # noqa: F401 -- so para registrar a versao

    meta = {
        "mcp": mcp_version(),
        "jsonschema": version("jsonschema"),
        "python": platform.python_version(),
        "amostra": [item["id"] for item in AMOSTRA],
        "regenerado_sob_2x": bool(args.force_regenerate_under_2x),
        "motivo_regeneracao": args.reason or None,
    }
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for nome, texto in _golden_files(primeira, meta).items():
        (GOLDEN_DIR / nome).write_bytes(texto.encode("utf-8"))
    print(f"golden gravado sob mcp {mcp_version()}: {len(AMOSTRA)} chamadas")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    difs = diff_contra_golden(coletar(args.modo))
    for caminho, esperado, obtido in difs:
        print(f"{caminho}\n  golden: {json.dumps(esperado, ensure_ascii=False)[:300]}"
              f"\n  agora:  {json.dumps(obtido, ensure_ascii=False)[:300]}")
    print(f"{len(difs)} diferenca(s) sob mcp {mcp_version()}")
    return 1 if difs else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/mcp_parity.py", description=__doc__.splitlines()[0]
    )
    sub = parser.add_subparsers(dest="action", required=True)
    snap = sub.add_parser("snapshot", help="Grava o golden (so sob mcp<2).")
    snap.add_argument("--force-regenerate-under-2x", action="store_true")
    snap.add_argument("--reason", default=None)
    diff = sub.add_parser("diff", help="Compara o servidor atual contra o golden.")
    diff.add_argument("--modo", choices=("legacy", "auto"), default="legacy")
    args = parser.parse_args(argv)
    return _cmd_snapshot(args) if args.action == "snapshot" else _cmd_diff(args)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
