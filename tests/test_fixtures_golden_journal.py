"""Golden do journal: cenarios de queda gravados no estado exato em que a queda os deixa.

Cada caso de `fixtures/journal/` traz `input/` (a raiz de um case sintetico, com
`.sparkforge/journal.jsonl` e, quando o cenario pede, blackboard e debate) e
`expected/observado.json`: o que `verify`, `estado`, `resume` e os leitores do
blackboard e do debate devolvem sobre ela. A entrada e copiada para `tmp_path`
antes de qualquer leitura -- o journal e commitavel, e a arvore nao pode mudar.

Regravar: `SPARKFORGE_REGEN_JOURNAL=1 pytest tests/test_fixtures_golden_journal.py`.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.adapters.cli import main
from sparkforge.agentic.blackboard import read_claims
from sparkforge.case.resume import render_handoff
from sparkforge.durable import read_jsonl
from sparkforge.journal import journal_path
from sparkforge.journal.read import estado, verify
from sparkforge.journal.record import recording

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "journal"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
REGRAVAR = os.environ.get("SPARKFORGE_REGEN_JOURNAL") == "1"


def _copiar(caso: str, tmp_path: Path) -> Path:
    raiz = tmp_path / "caso"
    shutil.copytree(FIXTURES / caso / "input", raiz)
    return raiz


def _secao_em_voo(markdown: str) -> list[str]:
    bloco = markdown.split("## Em voo na interrupcao", 1)[1].split("\n## ", 1)[0]
    return [linha for linha in bloco.strip().splitlines() if linha.strip()]


def _observado(raiz: Path) -> dict:
    payload = _core.resume_case(str(raiz))
    observado: dict = {
        "verify": verify(raiz),
        "estado": estado(raiz),
        "resume": {
            "in_flight": payload["in_flight"],
            "in_flight_source": payload["in_flight_source"],
            "journal": payload["journal"],
        },
        "handoff_em_voo": _secao_em_voo(render_handoff(payload)),
    }
    if (raiz / ".sparkforge" / "blackboard" / "claims.jsonl").is_file():
        observado["claims"] = [r["id"] for r in read_claims(raiz)]
    debates = raiz / ".sparkforge" / "debate"
    if debates.is_dir():
        observado["submissions"] = {
            d.name: {
                "registros": len(read_jsonl(d / "submissions.jsonl")[0]),
                "torn_tail": read_jsonl(d / "submissions.jsonl")[1] is not None,
            }
            for d in sorted(debates.iterdir())
            if d.is_dir()
        }
    return observado


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso: str, tmp_path: Path) -> None:
    observado = _observado(_copiar(caso, tmp_path))
    esperado = FIXTURES / caso / "expected" / "observado.json"
    if REGRAVAR:
        esperado.parent.mkdir(parents=True, exist_ok=True)
        esperado.write_text(
            json.dumps(observado, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    assert observado == json.loads(esperado.read_text(encoding="utf-8"))


@pytest.mark.parametrize("caso", CASOS)
def test_cli_verify_sai_1_so_na_quebra(caso: str, tmp_path: Path, capsys) -> None:
    raiz = _copiar(caso, tmp_path)
    codigo = main(["journal", "verify", "--repo", str(raiz)])
    status = json.loads(capsys.readouterr().out)["status"]
    assert codigo == (1 if status == "broken" else 0)


def test_append_depois_da_cauda_cortada_continua_a_cadeia(tmp_path: Path) -> None:
    raiz = _copiar("cauda_cortada", tmp_path)
    with recording("sparkforge_case_update", "cli", {"repo": str(raiz)}) as registro:
        registro.finish({}, "ok")
    assert verify(raiz)["status"] == "intact"
    assert journal_path(raiz).with_name("journal.jsonl.torn").is_file()


def test_fixture_sem_crlf() -> None:
    for caso in CASOS:
        dado = (FIXTURES / caso / "input" / ".sparkforge" / "journal.jsonl").read_bytes()
        assert b"\r\n" not in dado, caso
