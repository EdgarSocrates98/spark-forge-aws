"""Escrita que sobrevive a queda: `sparkforge.durable` e os donos de estado que o usam.

A queda e simulada pelo estado do arquivo (cauda cortada, `os.replace` que
falha), nunca matando processo: o teste precisa ser estavel no Windows e no CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge import durable
from sparkforge.agentic import blackboard
from sparkforge.agentic.executor import debate_run
from sparkforge.case import store


def _sabotar_replace(monkeypatch: pytest.MonkeyPatch) -> None:
    def falha(*_args: object, **_kwargs: object) -> None:
        raise OSError("queda simulada entre o temporario e a troca")

    monkeypatch.setattr(durable.os, "replace", falha)


def _temporarios(diretorio: Path) -> list[Path]:
    return [p for p in diretorio.iterdir() if p.name.endswith(".tmp")]


class TestWriteAtomic:
    def test_troca_o_conteudo(self, tmp_path: Path) -> None:
        alvo = tmp_path / "estado.json"
        durable.write_atomic(alvo, "um\n")
        durable.write_atomic(alvo, "dois\n")
        assert alvo.read_text(encoding="utf-8") == "dois\n"
        assert _temporarios(tmp_path) == []

    def test_falha_na_troca_deixa_o_original_intacto(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        alvo = tmp_path / "estado.json"
        alvo.write_bytes(b"original\n")
        _sabotar_replace(monkeypatch)
        with pytest.raises(OSError, match="queda simulada"):
            durable.write_atomic(alvo, "novo\n")
        assert alvo.read_bytes() == b"original\n"
        assert _temporarios(tmp_path) == []

    def test_case_yaml_intacto_apos_falha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        case = store.new_case("c1", "2026-09-15T00:00:00Z", {"glue": "5.0"}, repo=str(tmp_path))
        caminho = store.save_case(case, tmp_path)
        antes = caminho.read_bytes()
        _sabotar_replace(monkeypatch)
        with pytest.raises(OSError):
            store.save_case(store.set_phase(case, "inventory"), tmp_path)
        assert caminho.read_bytes() == antes
        assert store.load_case(tmp_path)["phase"] == "intake"

    def test_plan_json_intacto_apos_falha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plano = tmp_path / "plan.json"
        debate_run._escreve_json(plano, {"rules": ["A", "B"]})
        antes = plano.read_bytes()
        _sabotar_replace(monkeypatch)
        with pytest.raises(OSError):
            debate_run._escreve_json(plano, {"rules": ["C", "D"]})
        assert plano.read_bytes() == antes


class TestAppendLine:
    def test_cria_e_anexa(self, tmp_path: Path) -> None:
        alvo = tmp_path / "sub" / "x.jsonl"
        durable.append_text_line(alvo, '{"a":1}')
        durable.append_text_line(alvo, '{"a":2}')
        assert alvo.read_bytes() == b'{"a":1}\n{"a":2}\n'

    def test_montar_recebe_a_ultima_linha_valida(self, tmp_path: Path) -> None:
        alvo = tmp_path / "x.jsonl"
        vistas: list[str | None] = []

        def montar(ultima: str | None) -> str:
            vistas.append(ultima)
            return json.dumps({"n": len(vistas)})

        durable.append_line(alvo, montar)
        durable.append_line(alvo, montar)
        assert vistas == [None, '{"n": 1}']

    def test_cauda_de_lixo_vai_para_quarentena(self, tmp_path: Path) -> None:
        alvo = tmp_path / "x.jsonl"
        alvo.write_bytes(b'{"a":1}\n{"a":2, "cort')
        durable.append_text_line(alvo, '{"a":3}')
        assert alvo.read_bytes() == b'{"a":1}\n{"a":3}\n'
        quarentena = tmp_path / ("x.jsonl" + durable.QUARENTENA_SUFIXO)
        assert quarentena.read_bytes() == b'{"a":2, "cort\n'

    def test_cauda_json_valido_so_ganha_a_quebra(self, tmp_path: Path) -> None:
        alvo = tmp_path / "x.jsonl"
        alvo.write_bytes(b'{"a":1}\n{"a":2}')
        durable.append_text_line(alvo, '{"a":3}')
        assert alvo.read_bytes() == b'{"a":1}\n{"a":2}\n{"a":3}\n'
        assert not (tmp_path / ("x.jsonl" + durable.QUARENTENA_SUFIXO)).exists()

    def test_linha_com_quebra_e_recusada(self, tmp_path: Path) -> None:
        with pytest.raises(durable.DurableError):
            durable.append_text_line(tmp_path / "x.jsonl", "a\nb")


class TestReadJsonl:
    def test_ausente(self, tmp_path: Path) -> None:
        assert durable.read_jsonl(tmp_path / "nada.jsonl") == ([], None)

    def test_tolera_so_a_cauda_cortada(self, tmp_path: Path) -> None:
        alvo = tmp_path / "x.jsonl"
        alvo.write_bytes(b'{"a":1}\r\n{"a":2}\n{"a":3, "co')
        registros, cauda = durable.read_jsonl(alvo)
        assert registros == [{"a": 1}, {"a": 2}]
        assert cauda == '{"a":3, "co'

    def test_linha_ruim_no_meio_levanta_com_o_numero(self, tmp_path: Path) -> None:
        alvo = tmp_path / "x.jsonl"
        alvo.write_bytes(b'{"a":1}\nlixo\n{"a":3}\n')
        with pytest.raises(durable.DurableError, match="linha 2"):
            durable.read_jsonl(alvo)

    def test_blackboard_le_com_cauda_cortada_e_anexa_depois(self, tmp_path: Path) -> None:
        arquivo = blackboard.blackboard_path(tmp_path) / "claims.jsonl"
        arquivo.parent.mkdir(parents=True)
        arquivo.write_bytes(b'{"id": "c1"}\n{"id": "c2", "trunc')
        assert [r["id"] for r in blackboard.read_claims(tmp_path)] == ["c1"]
        blackboard._append_jsonl(arquivo, {"id": "c3"})
        assert [r["id"] for r in blackboard.read_claims(tmp_path)] == ["c1", "c3"]
