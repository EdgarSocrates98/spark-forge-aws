"""`scripts/run_debate.py` sem gastar: o host e trocado por um responder gravado.

O driver e o unico lugar, com o runner de eval, que chama `claude -p`. Aqui
`chamar_lado` e substituido por um fake que responde texto com (ou sem) bloco
```json, e o resto do driver roda de verdade: workspace de prova, `arbitrate`,
`debate start`, o laco `next` -> resposta -> `submit`, os passes do driver, o
`result.json` e o placar. O smoke com modelo real e manual (AT-012).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from scripts import run_debate
from sparkforge.adapters import _core
from tests.test_debate_suite import PONTEIRO, ROTEIRO_LF_VENCE, _grant_id, _resolve

ROOT = Path(__file__).resolve().parents[1]
COM_USAGE = ROOT / "fixtures" / "host_transcript" / "correct_mcp" / "input" / "q-mcp.jsonl"


# --------------------------------------------------------------------------
# a resposta do host
# --------------------------------------------------------------------------


def test_o_ultimo_bloco_json_vence():
    texto = 'antes\n```json\n{"side": "A"}\n```\nmeio\n```json\n{"side": "B", "round": 2}\n```'
    assert run_debate.ultimo_bloco_json(texto) == ({"side": "B", "round": 2}, None)


@pytest.mark.parametrize(
    ("texto", "motivo"),
    [
        ("sem bloco nenhum", "no_json_block"),
        ("```python\n{}\n```", "no_json_block"),
        ("", "no_json_block"),
    ],
)
def test_sem_bloco_json_e_no_json_block(texto, motivo):
    assert run_debate.ultimo_bloco_json(texto) == (None, motivo)


def test_bloco_quebrado_e_invalid_json():
    payload, motivo = run_debate.ultimo_bloco_json("```json\n{\"side\": \n```")
    assert payload is None
    assert motivo.startswith("invalid_json")


# --------------------------------------------------------------------------
# workspace de prova
# --------------------------------------------------------------------------


@pytest.mark.parametrize("caso", run_debate.CASOS)
def test_o_workspace_nao_leva_o_gabarito(caso, tmp_path):
    ws = run_debate.montar_caso(run_debate.SUITE_DIR / caso, tmp_path / "caso-1")
    arquivos = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*") if p.is_file())
    assert arquivos == [
        ".sparkforge/case.yaml",
        "artifacts/lakeformation/curated_arestas.json",
        "facts.json",
        "findings.json",
    ]


def test_o_prompt_do_ultimo_turno_cabe_na_linha_de_comando(tmp_path):
    """O prompt vai no argv, e o Windows corta em 32 767 caracteres. O turno
    mais longo e o ultimo: todas as submissoes anteriores e o fact reextraido."""
    ws = run_debate.montar_caso(run_debate.SUITE_DIR / "lf_vence", tmp_path / "caso-1")
    grant = _grant_id(ws)
    inicio = run_debate.preparar(ws)["start"]
    debate_id = inicio["debate_id"]
    aceitas: dict[int, dict[str, list[str]]] = {}
    for candidatas in ROTEIRO_LF_VENCE[:-1]:
        brief = _core.debate_next(str(ws), debate_id)["brief"]
        corpo = _resolve(candidatas[0], aceitas, grant)
        resposta = _core.debate_submit(
            str(ws), debate_id, payload={"side": brief["side"], "round": brief["round"], **corpo}
        )
        assert resposta["status"] == "accepted", resposta
        aceitas[resposta["seq"]] = resposta["entities"]
    brief = _core.debate_next(str(ws), debate_id)["brief"]
    assert (brief["side"], brief["round"]) == ("B", 3)
    prompt = run_debate.montar_prompt(brief, ws, debate_id, "refused: exemplo")
    assert len(prompt) < run_debate.LIMITE_DO_PROMPT
    # o fact reextraido chega ao lado COM os atributos, e nao so o id
    assert grant in prompt and "is_iam_allowed_principals" in prompt
    assert PONTEIRO["path"] not in prompt.split("ainda nao extraidos")[1].split("##")[0]


# --------------------------------------------------------------------------
# o laco inteiro, com o host fake
# --------------------------------------------------------------------------


class _HostGravado:
    """Responde como um lado que abre com uma claim nas ancoras da regra e
    depois passa. Antes disso, erra duas vezes: sem bloco, e claim sem
    evidencia -- as duas recusas que o placar precisa contar."""

    def __init__(self) -> None:
        self.chamadas: list[dict[str, Any]] = []

    def __call__(self, claude, args, prompt, ws, destino, rotulo):
        lado, rodada = re.search(r'"side": "([AB])" e "round": (\d+)', prompt).groups()
        n = len(self.chamadas)
        self.chamadas.append({"rotulo": rotulo, "cwd": ws.name, "chars": len(prompt)})
        shutil.copyfile(COM_USAGE, destino / f"{rotulo}.jsonl")
        if n == 0:
            texto = "esqueci o bloco"
        elif n == 1:
            texto = _bloco({"side": lado, "round": int(rodada), "claims": [
                {"claim_type": "inference", "statement": "x", "evidence_refs": [],
                 "confidence": "low"}]})
        elif rodada == "1":
            ancoras = re.search(r"Defende: (SF-[A-Z]+-\d+)", prompt).group(1)
            refs = {"SF-GRAPH-005": ["f_32bc0d"], "SF-LF-001": ["f_55f5ac"]}[ancoras]
            texto = _bloco({"side": lado, "round": 1, "claims": [
                {"claim_type": "inference", "statement": f"defendo {ancoras}",
                 "evidence_refs": refs, "confidence": "medium"}]})
        else:
            texto = _bloco({"side": lado, "round": int(rodada)})
        return {"session_id": f"s{n}", "transcript": f"{rotulo}.jsonl", "exit_code": 0,
                "status": "ok", "text": texto}


def _bloco(payload: dict[str, Any]) -> str:
    return f"jogada\n```json\n{json.dumps(payload)}\n```"


@pytest.fixture
def driver(tmp_path, monkeypatch):
    base = tmp_path / "debate-evals"
    monkeypatch.setattr(run_debate, "OUT_BASE", base)
    monkeypatch.setattr(run_debate, "_claude", lambda: "claude")
    host = _HostGravado()
    monkeypatch.setattr(run_debate, "chamar_lado", host)
    return base, host


def test_o_laco_conduz_ate_done_e_o_placar_conta_as_recusas(driver):
    base, host = driver
    assert run_debate.main(["--only", "lf_vence"]) == 0
    [execucao] = [p for p in base.iterdir() if p.name.startswith("debate-")]
    [workspace] = [p for p in base.iterdir() if p.name.startswith("workspace-")]

    # o workspace tem nome neutro e nao tem gabarito
    assert [p.name for p in workspace.iterdir()] == ["caso-1"]
    assert not list(workspace.rglob("expected.yaml"))
    assert {c["cwd"] for c in host.chamadas} == {"caso-1"}

    resultado = json.loads((execucao / "lf_vence" / "result.json").read_text(encoding="utf-8"))
    assert resultado["status"] == "done"
    assert [t["status"] for t in resultado["attempts"]][:3] == [
        "no_json_block",
        "refused",
        "accepted",
    ]
    assert resultado["attempts"][1]["reason"] == "claim_without_evidence"
    # ninguem concedeu: a rodada 2 fecha por consenso sem vencedor
    assert resultado["done"]["outcome"] == "unresolved"

    placar = json.loads((execucao / "grade.json").read_text(encoding="utf-8"))
    [linha] = [c for c in placar["cases"] if c["status"] != "not_run"]
    assert linha["outcome"] == "missed_resolution"
    assert linha["refused_submissions"] == 2
    assert linha["cost"]["transcripts_found"] == len(host.chamadas)
    assert placar["totals"]["not_run"] == 2
    run = json.loads((execucao / "run.json").read_text(encoding="utf-8"))
    assert run["workspace"]["case_files"] == ["case.yaml"]


def test_vez_da_rodada_1_esgotada_aborta_o_caso(driver, monkeypatch):
    base, host = driver
    monkeypatch.setattr(
        run_debate,
        "chamar_lado",
        lambda *a: {"session_id": "s", "transcript": None, "status": "ok", "text": "nada"},
    )
    assert run_debate.main(["--only", "sem_fato"]) == 0
    [execucao] = [p for p in base.iterdir() if p.name.startswith("debate-")]
    resultado = json.loads((execucao / "sem_fato" / "result.json").read_text(encoding="utf-8"))
    assert resultado["status"] == "aborted"
    assert resultado["reason"] == "round_1_exhausted_by_side_A"
    assert len(resultado["attempts"]) == run_debate.MAX_TENTATIVAS_POR_VEZ
    placar = json.loads((execucao / "grade.json").read_text(encoding="utf-8"))
    [linha] = [c for c in placar["cases"] if c["case"] == "sem_fato"]
    assert linha["status"] == "ungraded"


def test_dry_run_nao_grava_nem_chama_o_host(tmp_path, monkeypatch, capsys):
    base = tmp_path / "debate-evals"
    monkeypatch.setattr(run_debate, "OUT_BASE", base)

    def _proibido(*_a, **_k):
        raise AssertionError("dry-run chamou o host")

    monkeypatch.setattr(run_debate, "chamar_lado", _proibido)
    assert run_debate.main(["--dry-run", "--model", "haiku"]) == 0
    saida = capsys.readouterr().out
    assert "nada foi executado" in saida
    assert saida.count("primeiro brief de") == len(run_debate.CASOS)
    assert not base.exists()


def test_argv_fora_da_allowlist_e_recusado():
    with pytest.raises(SystemExit):
        run_debate.main(["--only", "../evals"])
    with pytest.raises(SystemExit):
        run_debate.main(["--model", "gpt"])
    with pytest.raises(SystemExit):
        run_debate.main(["--max-budget-usd", "0", "--dry-run"])
