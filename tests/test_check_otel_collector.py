"""`scripts/check_otel_collector.py`: o conferidor do job `otel-collector`.

O Collector so roda no CI. Aqui fica o que o conferidor aceita e o que recusa,
usando os proprios goldens como a "saida do Collector": identidade passa, um
token adulterado, um span faltando ou uma saida vazia falham.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDENS = ROOT / "fixtures" / "otel"


def _conferidor():
    spec = importlib.util.spec_from_file_location(
        "check_otel_collector", ROOT / "scripts" / "check_otel_collector.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _saida(tmp_path: Path, sinal: str, trocar: tuple[str, str] | None = None) -> Path:
    texto = "".join(
        (p / "expected" / f"{sinal}.jsonl").read_text(encoding="utf-8")
        for p in sorted(GOLDENS.iterdir())
        if p.is_dir()
    )
    if trocar:
        assert trocar[0] in texto
        texto = texto.replace(trocar[0], trocar[1], 1)
    destino = tmp_path / f"{sinal}.json"
    destino.write_text(texto, encoding="utf-8")
    return destino


def test_os_goldens_como_saida_passam(tmp_path, capsys):
    codigo = _conferidor().main(
        ["--traces", str(_saida(tmp_path, "traces")), "--metrics", str(_saida(tmp_path, "metrics"))]
    )
    assert codigo == 0
    assert "OK:" in capsys.readouterr().out


def test_token_adulterado_falha(tmp_path):
    traces = _saida(
        tmp_path,
        "traces",
        (
            '"gen_ai.usage.output_tokens","value":{"intValue":"',
            '"gen_ai.usage.output_tokens","value":{"intValue":"9',
        ),
    )
    assert (
        _conferidor().main(["--traces", str(traces), "--metrics", str(_saida(tmp_path, "metrics"))])
        == 1
    )


def test_saida_vazia_falha(tmp_path):
    assert (
        _conferidor().main(
            ["--traces", str(tmp_path / "nada.json"), "--metrics", str(tmp_path / "nada.json")]
        )
        == 1
    )


def test_ponto_de_metrica_com_atributo_de_semconv_a_mais_nao_conta_como_o_mesmo():
    mesmo = _conferidor()._mesmos_atributos_semanticos
    alvo = {"gen_ai.operation.name": "invoke_agent"}
    assert mesmo({"gen_ai.operation.name": "invoke_agent", "log.file.name": "x"}, alvo)
    assert not mesmo({"gen_ai.operation.name": "invoke_agent", "gen_ai.provider.name": "a"}, alvo)


def test_linha_incompleta_no_fim_conta_como_ainda_nao_chegou(tmp_path, capsys):
    """O exporter `file` pode estar no meio da escrita: a linha truncada nao
    derruba o conferidor (primeiro run do job no CI, 2026-09-11)."""
    traces = _saida(tmp_path, "traces")
    with traces.open("a", encoding="utf-8") as arquivo:
        arquivo.write('{"resourceSpans":[{"par')
    codigo = _conferidor().main(
        ["--traces", str(traces), "--metrics", str(_saida(tmp_path, "metrics"))]
    )
    assert codigo == 0
