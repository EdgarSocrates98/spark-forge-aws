"""Testes do leitor de usage do host.

E o unico nivel desta fase que le artefato que o SparkForge NAO produz e cujo
formato ele nao controla -- e por isso entra pela porta do `collect *`, com a
mesma disciplina: le o que sabe ler, e recusa por nome o resto.
"""
from __future__ import annotations

import json

from sparkforge.collect.host_usage import read_host_usage


def _transcript(tmp_path, linhas):
    destino = tmp_path / "sessao.jsonl"
    destino.write_text(
        "\n".join(json.dumps(linha) for linha in linhas) + "\n", encoding="utf-8"
    )
    return destino


class TestOFormatoConhecido:
    def test_usage_of_each_assistant_message_is_summed(self, tmp_path):
        caminho = _transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "cache_read_input_tokens": 40,
                        }
                    },
                },
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 200,
                            "output_tokens": 30,
                            "cache_read_input_tokens": 60,
                        }
                    },
                },
            ],
        )
        leitura = read_host_usage(caminho)

        assert leitura["input_tokens"] == 300
        assert leitura["output_tokens"] == 50
        assert leitura["cached_tokens"] == 100
        assert leitura["message_count"] == 2
        assert leitura["source"] == "claude_code_transcript"

    def test_a_message_without_usage_is_counted_as_a_gap(self, tmp_path):
        caminho = _transcript(
            tmp_path,
            [
                {"type": "assistant", "message": {"usage": {"input_tokens": 10}}},
                {"type": "assistant", "message": {}},
            ],
        )
        leitura = read_host_usage(caminho)

        assert leitura["input_tokens"] == 10
        assert leitura["unresolved"] == [{"reason": "usage_field_absent", "count": 1}]

    def test_non_assistant_lines_are_ignored_without_a_gap(self, tmp_path):
        """Linha de usuario nao tem usage por natureza -- ignorar nao e lacuna."""
        caminho = _transcript(
            tmp_path,
            [
                {"type": "user", "message": {"content": "oi"}},
                {"type": "assistant", "message": {"usage": {"input_tokens": 10}}},
            ],
        )
        leitura = read_host_usage(caminho)

        assert leitura["message_count"] == 1
        assert leitura["unresolved"] == []


class TestRecusas:
    def test_an_unknown_format_is_refused_by_name(self, tmp_path):
        caminho = tmp_path / "outro_host.json"
        caminho.write_text(json.dumps({"tokens": 123}), encoding="utf-8")

        leitura = read_host_usage(caminho)

        assert leitura["input_tokens"] == 0
        assert leitura["unresolved"] == [
            {"reason": "host_format_unknown", "count": 1}
        ]

    def test_a_missing_file_is_refused_by_name(self, tmp_path):
        leitura = read_host_usage(tmp_path / "nao_existe.jsonl")

        assert leitura["unresolved"] == [{"reason": "transcript_not_found", "count": 1}]

    def test_a_malformed_line_does_not_abort_the_read(self, tmp_path):
        destino = tmp_path / "sessao.jsonl"
        destino.write_text(
            '{"nao valido\n'
            + json.dumps(
                {"type": "assistant", "message": {"usage": {"input_tokens": 7}}}
            )
            + "\n",
            encoding="utf-8",
        )
        leitura = read_host_usage(destino)

        assert leitura["input_tokens"] == 7
        assert {"reason": "malformed_line", "count": 1} in leitura["unresolved"]
