"""Confere que um OTLP Collector de verdade leu os goldens de `fixtures/otel/`.

O job `otel-collector` do CI sobe o `otelcol-contrib` com o receiver
`otlp_json_file` (antes `otlpjsonfile`) apontado para
`fixtures/otel/*/expected/{traces,metrics}.jsonl` e o exporter `file` gravando
o que recebeu. Este script le essa saida e cobra, para
cada span dos goldens, o mesmo `spanId`, `traceId`, `parentSpanId`, nome e os
atributos que o export promete (`gen_ai.*`, `mcp.method.name`); e, para cada
ponto de metrica, o mesmo `count`, `sum` e `bucketCounts`. E a prova de que o
arquivo e aceito por um consumidor, e nao so bem formado -- o equivalente do
`sarif-upload` para o SARIF.

O receiver acrescenta atributos proprios (o nome do arquivo lido), entao a
comparacao de atributos e por subconjunto: tudo o que o golden tem, a saida tem
igual.

    python scripts/check_otel_collector.py --expected fixtures/otel \\
        --traces out/traces.json --metrics out/metrics.json --wait 60
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

CHAVES = (
    "gen_ai.operation.name",
    "gen_ai.tool.name",
    "gen_ai.tool.call.id",
    "gen_ai.provider.name",
    "gen_ai.request.model",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.usage.cache_read.input_tokens",
    "gen_ai.usage.cache_write.input_tokens",
    "mcp.method.name",
    "error.type",
)


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.is_file():
        return []
    dados = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            dados.append(json.loads(linha))
        except json.JSONDecodeError:
            # O exporter `file` pode estar no meio da escrita da linha. Ela conta
            # como "ainda nao chegou": o laco de `--wait` le de novo, e uma linha
            # que nunca fecha aparece como span faltando, com nome.
            continue
    return dados


def _attrs(no: dict[str, Any]) -> dict[str, Any]:
    return {a["key"]: next(iter(a["value"].values()), None) for a in no.get("attributes", [])}


def _mesmos_atributos_semanticos(recebido: dict[str, Any], alvo: dict[str, Any]) -> bool:
    """Igualdade nos atributos de semconv (`gen_ai.*`, `mcp.*`, `error.*`), e
    subconjunto no resto: o receiver pode acrescentar os seus, mas um ponto com
    `gen_ai.provider.name` a mais e OUTRO ponto, e nao o mesmo."""
    semanticos = ("gen_ai.", "mcp.", "error.")
    return all(recebido.get(k) == v for k, v in alvo.items()) and all(
        k in alvo for k in recebido if k.startswith(semanticos)
    )


def spans_de(dados: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        span["spanId"]: span
        for dado in dados
        for rs in dado.get("resourceSpans", [])
        for escopo in rs.get("scopeSpans", [])
        for span in escopo.get("spans", [])
    }


def pontos_de(dados: Iterable[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (metrica["name"], ponto)
        for dado in dados
        for rm in dado.get("resourceMetrics", [])
        for escopo in rm.get("scopeMetrics", [])
        for metrica in escopo.get("metrics", [])
        for ponto in (metrica.get("histogram") or {}).get("dataPoints", [])
    ]


def conferir(esperado: Path, traces: Path, metrics: Path) -> tuple[list[str], int, int]:
    """Problemas encontrados, spans conferidos e pontos conferidos."""
    recebidos = spans_de(_linhas(traces))
    pontos_recebidos = pontos_de(_linhas(metrics))
    problemas: list[str] = []
    n_spans = n_pontos = 0
    for caso in sorted(p for p in esperado.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for span_id, span in spans_de(_linhas(caso / "expected" / "traces.jsonl")).items():
            n_spans += 1
            outro = recebidos.get(span_id)
            if outro is None:
                problemas.append(f"{caso.name}: span {span_id} ({span['name']}) nao chegou")
                continue
            for campo in ("traceId", "parentSpanId", "name", "kind"):
                if span.get(campo) != outro.get(campo):
                    problemas.append(
                        f"{caso.name}: span {span_id} {campo} {span.get(campo)!r} "
                        f"!= {outro.get(campo)!r}"
                    )
            a, b = _attrs(span), _attrs(outro)
            for chave in CHAVES:
                if chave in a and a[chave] != b.get(chave):
                    problemas.append(
                        f"{caso.name}: span {span_id} {chave} {a[chave]!r} != {b.get(chave)!r}"
                    )
        for nome, ponto in pontos_de(_linhas(caso / "expected" / "metrics.jsonl")):
            n_pontos += 1
            alvo = _attrs(ponto)
            iguais = [
                p
                for n, p in pontos_recebidos
                if n == nome
                and _mesmos_atributos_semanticos(_attrs(p), alvo)
                and p.get("startTimeUnixNano") == ponto.get("startTimeUnixNano")
            ]
            if not iguais:
                problemas.append(f"{caso.name}: ponto de {nome} {alvo} nao chegou")
                continue
            for campo, igual in (
                ("count", lambda x, y: str(x) == str(y)),
                ("sum", lambda x, y: x is not None and y is not None and float(x) == float(y)),
                (
                    "bucketCounts",
                    lambda x, y: [str(v) for v in x or []] == [str(v) for v in y or []],
                ),
            ):
                if not igual(ponto.get(campo), iguais[0].get(campo)):
                    problemas.append(
                        f"{caso.name}: {nome} {campo} {ponto.get(campo)!r} "
                        f"!= {iguais[0].get(campo)!r}"
                    )
    return problemas, n_spans, n_pontos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expected", type=Path, default=Path("fixtures/otel"))
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--wait", type=float, default=0.0, help="Segundos de espera pela saida.")
    args = parser.parse_args(argv)

    prazo = time.monotonic() + args.wait
    while True:
        problemas, n_spans, n_pontos = conferir(args.expected, args.traces, args.metrics)
        if not problemas or time.monotonic() >= prazo:
            break
        time.sleep(2)
    for problema in problemas:
        print(problema, file=sys.stderr)
    if problemas:
        print(f"FALHOU: {len(problemas)} divergencia(s).", file=sys.stderr)
        return 1
    if n_spans == 0:
        print("FALHOU: nenhum span nos goldens; nada foi conferido.", file=sys.stderr)
        return 1
    print(f"OK: {n_spans} spans e {n_pontos} pontos de metrica chegaram iguais ao golden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
