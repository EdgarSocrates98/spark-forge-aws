"""Journal de eventos: o par `started`/`finished` pelas duas portas, sem derrubar o verbo."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sparkforge.adapters import _core
from sparkforge.adapters.cli import _tool_da_cli, build_parser, main
from sparkforge.adapters.tools import TOOLS, call_tool
from sparkforge.journal import journal_path, journaled
from sparkforge.journal.read import verify
from sparkforge.journal.record import (
    SEM_RAIZ_DE_CASE,
    UNRECORDED,
    Registro,
    normalizar_args,
    raiz_do_journal,
    sha256_texto,
)

NOW = "2026-09-15T10:00:00Z"


def _linhas(raiz: Path) -> list[str]:
    return journal_path(raiz).read_text(encoding="utf-8").splitlines()


def _eventos(raiz: Path) -> list[dict]:
    return [json.loads(linha) for linha in _linhas(raiz)]


def _abrir_pela_cli(raiz: Path) -> None:
    assert main(["case", "open", "--repo", str(raiz), "--case-id", "c1", "--now", NOW]) == 0


def _verbos_de_cli() -> set[str]:
    import argparse

    def sub(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
        return next(
            (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None
        )

    nomes: set[str] = set()
    raiz = sub(build_parser())
    assert raiz is not None
    for comando, parser in raiz.choices.items():
        aninhado = sub(parser)
        if aninhado:
            nomes.update(_tool_da_cli(comando, folha) for folha in aninhado.choices)
        else:
            nomes.add(_tool_da_cli(comando, None))
    return nomes


class TestConjunto:
    def test_e_o_das_anotacoes(self) -> None:
        esperado = {
            nome
            for nome, spec in TOOLS.items()
            if spec["annotations"].get("readOnlyHint") is False
            and not nome.startswith("sparkforge_code_")
        }
        assert journaled() == esperado
        # 27 -> 28 com `sdd_stamp` (2026-09-16): `_WRITE_IDEMPOTENT`, grava a linha
        # `upstream.sha256` do artefato SDD. `sdd_check` e `sdd_status` so leem.
        assert len(esperado) == 28

    def test_todo_verbo_do_journal_tem_porta_de_cli_pela_convencao(self) -> None:
        assert journaled() <= _verbos_de_cli()


class TestPortas:
    def test_case_open_pela_cli_grava_o_par(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)
        linhas = _linhas(tmp_path)
        inicio, fim = (json.loads(linha) for linha in linhas)
        assert (inicio["event"], inicio["seq"], inicio["prev"]) == ("started", 1, None)
        assert (inicio["tool"], inicio["port"]) == ("sparkforge_case_open", "cli")
        assert inicio["at"] == NOW
        assert (fim["event"], fim["seq"], fim["started_seq"]) == ("finished", 2, 1)
        assert fim["prev"] == sha256_texto(linhas[0])
        assert fim["outcome"] == "ok"
        caso = tmp_path / ".sparkforge" / "case.yaml"
        assert fim["outputs"] == {
            ".sparkforge/case.yaml": hashlib.sha256(caso.read_bytes()).hexdigest()
        }

    def test_case_update_pelo_mcp_encadeia(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)
        argumentos = {"repo": str(tmp_path), "phase": "inventory"}
        resultado = call_tool("sparkforge_case_update", argumentos)
        assert "journal" not in resultado
        eventos = _eventos(tmp_path)
        assert [e["port"] for e in eventos if e["event"] == "started"] == ["cli", "mcp"]
        assert eventos[2]["prev"] == sha256_texto(_linhas(tmp_path)[1])
        assert verify(tmp_path)["status"] == "intact"

    def test_as_duas_portas_gravam_o_mesmo_verbo_desfecho_e_saidas(
        self, tmp_path: Path, capsys
    ) -> None:
        pela_cli, pelo_mcp = tmp_path / "cli", tmp_path / "mcp"
        pela_cli.mkdir()
        pelo_mcp.mkdir()
        _abrir_pela_cli(pela_cli)
        call_tool("sparkforge_case_open", {"repo": str(pelo_mcp), "case_id": "c1", "now": NOW})
        fim_cli, fim_mcp = _eventos(pela_cli)[1], _eventos(pelo_mcp)[1]
        assert (fim_cli["tool"], fim_cli["outcome"]) == (fim_mcp["tool"], fim_mcp["outcome"])
        assert set(fim_cli["outputs"]) == set(fim_mcp["outputs"])

    def test_verbo_de_leitura_nao_grava(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)
        call_tool("sparkforge_resume", {"repo": str(tmp_path)})
        assert len(_linhas(tmp_path)) == 2

    def test_recusa_da_policy_nao_grava(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)

        class Recusa:
            def decide(self, _nome: str, _args: dict) -> SimpleNamespace:
                return SimpleNamespace(authorized=False, reason="teste", required_approval=None)

        resultado = call_tool(
            "sparkforge_case_update", {"repo": str(tmp_path), "phase": "inventory"}, policy=Recusa()
        )
        assert resultado["error_code"] == "UNAUTHORIZED"
        assert len(_linhas(tmp_path)) == 2

    def test_verbo_que_falha_grava_finished_com_erro(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)
        argumentos = {"repo": str(tmp_path), "phase": "nao_existe"}
        resultado = call_tool("sparkforge_case_update", argumentos)
        assert "error" in resultado
        assert _eventos(tmp_path)[-1]["outcome"] == "error"


class TestRegra27:
    def test_journal_indisponivel_nao_derruba_o_verbo(self, tmp_path: Path) -> None:
        journal_path(tmp_path).mkdir(parents=True)
        resultado = call_tool(
            "sparkforge_case_open", {"repo": str(tmp_path), "case_id": "c1", "now": NOW}
        )
        assert resultado["journal"] == UNRECORDED
        assert resultado["journal_reason"]
        assert (tmp_path / ".sparkforge" / "case.yaml").is_file()

    def test_cli_avisa_em_stderr(self, tmp_path: Path, capsys) -> None:
        journal_path(tmp_path).mkdir(parents=True)
        _abrir_pela_cli(tmp_path)
        assert "journal: unrecorded" in capsys.readouterr().err

    def test_sem_raiz_de_case_nao_grava(self, tmp_path: Path) -> None:
        resultado = call_tool(
            "sparkforge_report_sign",
            {"report_path": str(tmp_path / "r.md"), "findings_path": str(tmp_path / "f.json")},
        )
        assert resultado["journal_reason"] == SEM_RAIZ_DE_CASE
        assert not journal_path(tmp_path).exists()

    def test_raiz_pelo_ancestral_com_case(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)
        (tmp_path / "saidas").mkdir()
        assert raiz_do_journal({"out_path": str(tmp_path / "saidas" / "plano.json")}) == (
            tmp_path.resolve(),
            None,
        )


class TestSemLiteral:
    def test_valor_sensivel_vira_hash(self) -> None:
        sensiveis = {
            "repo": "C:\\clientes\\acme",
            "role_arn": "arn:aws:iam::123456789012:role/r",
            "job_name": "job_do_cliente",
            "debate_id": "/abs/caminho",
        }
        normalizados = normalizar_args({**sensiveis, "fail_on": "P1", "rules": ["SF-A-001"]})
        texto = json.dumps(normalizados)
        for valor in sensiveis.values():
            assert valor not in texto
        assert normalizados["fail_on"] == "P1"
        assert normalizados["rules"] == ["SF-A-001"]
        assert normalizados["debate_id"].startswith("sha256:")

    def test_caminho_da_raiz_nao_aparece_no_journal(self, tmp_path: Path, capsys) -> None:
        _abrir_pela_cli(tmp_path)
        texto = journal_path(tmp_path).read_text(encoding="utf-8")
        assert str(tmp_path) not in texto
        assert str(tmp_path).replace("\\", "\\\\") not in texto


class TestResume:
    def _em_voo(self, raiz: Path) -> None:
        _abrir_pela_cli(raiz)
        Registro("sparkforge_scan", "cli").start({"repo": str(raiz)})

    def test_em_voo_vem_do_journal(self, tmp_path: Path, capsys) -> None:
        self._em_voo(tmp_path)
        payload = _core.resume_case(str(tmp_path))
        assert payload["in_flight_source"] == "journal"
        assert payload["in_flight"] == "sparkforge_scan (cli, seq 3) sem finished"
        assert payload["journal"]["open_calls"] == [
            {"seq": 3, "tool": "sparkforge_scan", "port": "cli", "at": None}
        ]

    def test_texto_de_quem_chama_vence(self, tmp_path: Path, capsys) -> None:
        self._em_voo(tmp_path)
        payload = _core.resume_case(str(tmp_path), in_flight="rodando scan")
        assert (payload["in_flight"], payload["in_flight_source"]) == ("rodando scan", "caller")
        assert payload["journal"]["open_calls"]

    def test_handoff_diz_caiu_ou_ainda_roda(self, tmp_path: Path, capsys) -> None:
        self._em_voo(tmp_path)
        _core.handoff(str(tmp_path))
        texto = (tmp_path / ".sparkforge" / "handoff.md").read_text(encoding="utf-8")
        assert "sem finished (caiu ou ainda roda)" in texto

    def test_sem_journal_nada_muda(self, tmp_path: Path) -> None:
        assert verify(tmp_path)["status"] == "absent"


class TestLimiteDaCadeia:
    def test_editar_a_ultima_linha_nao_e_detectavel_pela_cadeia(
        self, tmp_path: Path, capsys
    ) -> None:
        _abrir_pela_cli(tmp_path)
        caminho = journal_path(tmp_path)
        linhas = caminho.read_bytes().split(b"\n")[:-1]
        editada = linhas[-1].replace(b'"outcome":"ok"', b'"outcome":"error"')
        assert editada != linhas[-1]
        caminho.write_bytes(b"\n".join([*linhas[:-1], editada]) + b"\n")
        assert verify(tmp_path)["status"] == "intact"

    def test_editar_uma_linha_do_meio_quebra_no_seq_seguinte(
        self, tmp_path: Path, capsys
    ) -> None:
        _abrir_pela_cli(tmp_path)
        call_tool("sparkforge_case_update", {"repo": str(tmp_path), "phase": "inventory"})
        caminho = journal_path(tmp_path)
        linhas = caminho.read_bytes().split(b"\n")[:-1]
        editada = linhas[1].replace(b'"outcome":"ok"', b'"outcome":"error"')
        caminho.write_bytes(b"\n".join([linhas[0], editada, *linhas[2:]]) + b"\n")
        resultado = verify(tmp_path)
        assert (resultado["status"], resultado["broken_at"]) == ("broken", 3)


@pytest.mark.parametrize("status, esperado", [("absent", 0)])
def test_journal_verify_pela_cli(tmp_path: Path, capsys, status: str, esperado: int) -> None:
    assert main(["journal", "verify", "--repo", str(tmp_path)]) == esperado
    assert json.loads(capsys.readouterr().out)["status"] == status
