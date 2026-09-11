"""Golden da maquina de estados do executor de debate -- submissoes GRAVADAS.

Nenhum modelo roda aqui. Cada fixture de `fixtures/debate/<caso>/` declara uma
sequencia de passos (`input/steps.json`: `start`, `submit` com a submissao
gravada, `next`) sobre o UNICO par de contradicao direta do catalogo --
`SF-GRAPH-005` x `SF-LF-001`, que so aparece na uniao das duas fixtures da regra
29 (`fixtures/graph/import_sem_jar_no_iac` + `fixtures/infra_code/
fgac_com_jar_extra`). O golden (`expected/debate.json`) e o RASTRO: o status e o
motivo de cada passo, e o desfecho do fechamento.

O rastro guarda nomes e desfechos, e nao os ids content-addressed: o
`debate_id` e o hash do plano congelado, e qualquer mudanca de texto no plano
(o motivo do `unresolved`, o agente de roteamento) moveria todos os ids sem que
a maquina de estados tivesse mudado. O unico golden byte a byte e o brief de
`retomada`, porque o SC2 pede exatamente isso.

Sem `expected/facts.json` nem `expected/findings.json` de proposito: outros
testes varrem `fixtures/*/*/expected/` atras desses dois nomes, e eles
pertencem a golden de extrator.

A cada passo recusado o teste confere que o estado do case ficou byte a byte
igual (SC3): recusa que grava meia submissao e a falha que o contrato proibe.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from sparkforge.agentic.blackboard import (
    read_claims,
    read_decisions,
    read_objections,
    read_rebuttals,
)
from sparkforge.agentic.executor.debate_run import next_step, start, submit
from sparkforge.case.store import SCHEMA_VERSION, save_case

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "debate"

REQUIRED_FIXTURES = {
    "budget_esgotado",
    "consenso_com_vencedor",
    "consenso_sem_concessao",
    "debate_fechado",
    "evidencia_reextraida",
    "hipotese_fechando",
    "objecao_sem_replica",
    "recusas_de_forma_e_vez",
    "recusas_de_referencia",
    "retomada",
    "sem_budget",
    "sem_debate_aberto",
    "sem_max_rounds",
}


def fixture_dirs() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _json(caminho: Path) -> Any:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _uniao(meta: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Findings e facts da uniao declarada no `meta.yaml`, na ordem declarada."""
    findings: list[dict] = []
    facts: list[dict] = []
    for relativo in meta["union"]:
        pasta = ROOT / "fixtures" / relativo / "expected"
        findings += _json(pasta / "findings.json")
        facts += _json(pasta / "facts.json")
    return findings, facts


def _monta_case(directory: Path, raiz: Path) -> dict[str, Any]:
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    raiz.mkdir(parents=True, exist_ok=True)
    if meta.get("budget") is not None:
        save_case(
            {"schema_version": SCHEMA_VERSION, "case_id": meta["name"], "budget": meta["budget"]},
            raiz,
        )
    artefatos = directory / "input" / "artifacts"
    if artefatos.is_dir():
        shutil.copytree(artefatos, raiz / "artifacts")
    return meta


def _estado(raiz: Path) -> dict[str, bytes]:
    """Todo byte sob `.sparkforge/` -- a foto que a recusa nao pode mudar."""
    base = raiz / ".sparkforge"
    foto: dict[str, bytes] = {}
    if not base.exists():
        return foto
    for pasta, _dirs, arquivos in os.walk(base):
        for nome in arquivos:
            caminho = Path(pasta) / nome
            foto[caminho.relative_to(raiz).as_posix()] = caminho.read_bytes()
    return foto


def _resolve(valor: Any, aceitas: dict[int, dict[str, list[str]]]) -> Any:
    """Troca `@<seq>.<secao>.<i>` pelo id que a submissao `seq` produziu.

    Os ids sao content-addressed sobre o autor, e o autor carrega o
    `debate_id`: gravar o id literal na fixture a amarraria ao hash do plano.
    """
    if isinstance(valor, str) and valor.startswith("@"):
        seq, secao, indice = valor[1:].split(".")
        return aceitas[int(seq)][secao][int(indice)]
    if isinstance(valor, list):
        return [_resolve(v, aceitas) for v in valor]
    if isinstance(valor, dict):
        return {k: _resolve(v, aceitas) for k, v in valor.items()}
    return valor


def _resumo(op: str, saida: dict[str, Any]) -> dict[str, Any]:
    """O que o rastro guarda de cada passo: nome e desfecho, sem hash."""
    linha: dict[str, Any] = {"op": op, "status": saida["status"]}
    if saida["status"] == "refused":
        linha["reason"] = saida["reason"]
    elif saida["status"] == "started":
        linha["created"] = saida["created"]
        linha["max_rounds"] = saida["max_rounds"]
    elif saida["status"] == "accepted":
        linha["entities"] = {k: len(v) for k, v in saida["entities"].items()}
        linha["facts_added"] = len(saida["facts_added"])
        linha["next"] = _resumo("next", saida["next"])["status"]
    elif saida["status"] == "brief":
        brief = saida["brief"]
        linha.update(
            side=brief["side"],
            round=brief["round"],
            rounds_remaining=brief["rounds_remaining"],
            extracted_facts=len(brief["extracted_facts"]),
            open_objections_against_you=len(brief["open_objections_against_you"]),
            prior_submissions=len(brief["prior_submissions"]),
        )
    elif saida["status"] == "done":
        linha.update(
            outcome=saida["outcome"],
            winner_rule=saida["winner_rule"],
            closed_by=saida["closed_by"],
            rounds_completed=saida["rounds_completed"],
            candidate=saida["candidate"]["outcome"],
            candidate_winner=saida["candidate"]["winner_rule"],
            referee_upheld=saida["referee"]["upheld"],
            violation_kinds=sorted({v["kind"] for v in saida["referee"]["violations"]}),
            selected_option=saida["decision"]["selected_option"],
        )
    return linha


def run_fixture(directory: Path, raiz: Path) -> dict[str, Any]:
    """Executa os passos da fixture e devolve o rastro mais o que foi gravado."""
    meta = _monta_case(directory, raiz)
    findings, facts = _uniao(meta)
    passos = _json(directory / "input" / "steps.json")

    debate_id: str | None = None
    aceitas: dict[int, dict[str, list[str]]] = {}
    rastro: list[dict[str, Any]] = []
    saidas: list[dict[str, Any]] = []
    for passo in passos:
        antes = _estado(raiz)
        if passo["op"] == "start":
            saida = start(raiz, findings, facts, meta["runtime"], passo.get("rules", meta["rules"]))
            if saida["status"] == "started":
                debate_id = saida["debate_id"]
        elif passo["op"] == "next":
            saida = next_step(raiz, debate_id)
        else:
            saida = submit(raiz, debate_id, _resolve(passo["payload"], aceitas))
            if saida["status"] == "accepted":
                aceitas[saida["seq"]] = saida["entities"]
        if saida["status"] == "refused":
            assert _estado(raiz) == antes, f"a recusa {saida['reason']} mudou o estado do case"
        rastro.append(_resumo(passo["op"], saida))
        saidas.append(saida)

    prefixo = f"{debate_id}/" if debate_id else None
    return {
        "meta": meta,
        "debate_id": debate_id,
        "saidas": saidas,
        "golden": {
            "trace": rastro,
            "blackboard": {
                "decisions": len(read_decisions(raiz)),
                "debate_claims": sum(
                    1 for c in read_claims(raiz) if prefixo and c["claimant"].startswith(prefixo)
                ),
                "debate_objections": sum(
                    1
                    for o in read_objections(raiz)
                    if prefixo and o["objector"].startswith(prefixo)
                ),
                "debate_rebuttals": sum(
                    1
                    for r in read_rebuttals(raiz)
                    if prefixo and r["rebuttal_by"].startswith(prefixo)
                ),
            },
        },
    }


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


def test_fixtures_nao_carregam_golden_de_extrator():
    """`expected/facts.json` e `findings.json` sao nomes de golden de EXTRATOR:
    outros testes os varrem em `fixtures/*/*/expected/`, e um arquivo daqueles
    aqui entraria no corpus deles como se fosse extracao."""
    for pasta in fixture_dirs():
        assert not (pasta / "expected" / "facts.json").exists(), pasta.name
        assert not (pasta / "expected" / "findings.json").exists(), pasta.name


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_trace_matches_golden(self, directory, tmp_path):
        resultado = run_fixture(directory, tmp_path / "case")
        esperado = _json(directory / "expected" / "debate.json")
        assert resultado["golden"] == esperado

    def test_declared_outcome(self, directory, tmp_path):
        """O `expects_outcome` do meta, conferido contra o rastro.

        Desfecho de debate (`winner:<regra>`, `unresolved`) e lido do ULTIMO
        `done`; recusa, da ultima recusa; o resto, do status do ultimo passo.
        """
        resultado = run_fixture(directory, tmp_path / "case")
        rastro = resultado["golden"]["trace"]
        declarado = resultado["meta"]["expects_outcome"]
        if declarado.startswith("winner:") or declarado == "unresolved":
            done = [p for p in rastro if p["status"] == "done"][-1]
            vencedor = declarado[7:] if declarado.startswith("winner:") else None
            assert (done["outcome"], done["winner_rule"]) == (
                "winner" if vencedor else "unresolved",
                vencedor,
            )
        elif declarado.startswith("refused:"):
            assert [p for p in rastro if p["status"] == "refused"][-1]["reason"] == declarado[8:]
        else:
            assert rastro[-1]["status"] == declarado

    def test_run_is_deterministic(self, directory, tmp_path):
        """Dois cases novos, a mesma entrada: as mesmas saidas, byte a byte."""
        um = run_fixture(directory, tmp_path / "um")
        dois = run_fixture(directory, tmp_path / "dois")
        primeira = json.dumps(um["saidas"], sort_keys=True)
        assert primeira == json.dumps(dois["saidas"], sort_keys=True)


class TestRetomada:
    """SC2 / AT-010: o brief sai dos arquivos, e so deles."""

    def test_brief_e_o_mesmo_byte_a_byte_em_chamadas_separadas(self, tmp_path):
        resultado = run_fixture(FIXTURES / "retomada", tmp_path / "case")
        raiz, debate_id = tmp_path / "case", resultado["debate_id"]
        antes = json.dumps(next_step(raiz, debate_id), sort_keys=True, indent=2) + "\n"
        depois = json.dumps(next_step(raiz, debate_id), sort_keys=True, indent=2) + "\n"
        golden = (FIXTURES / "retomada" / "expected" / "brief.json").read_text(encoding="utf-8")
        assert antes == depois == golden


class TestFechamento:
    def test_consenso_com_vencedor_grava_exatamente_uma_decisao(self, tmp_path):
        """SC1: sobre o caso da regra 29, o fluxo termina com 1 Decision gravada."""
        resultado = run_fixture(FIXTURES / "consenso_com_vencedor", tmp_path / "case")
        assert resultado["golden"]["blackboard"]["decisions"] == 1
        done = resultado["saidas"][-1]
        assert done["decision"]["debate_id"] == resultado["debate_id"]
        assert done["autonomy"] == {"level": "L0", "applied_changes": False}

    @pytest.mark.parametrize(
        ("caso", "violacao"),
        [
            ("objecao_sem_replica", "consenso_sobre_objecao_viva"),
            ("hipotese_fechando", "fechamento_sobre_hipotese"),
            ("budget_esgotado", "consenso_sobre_objecao_viva"),
        ],
    )
    def test_referee_recusado_vira_unresolved_citando_a_violacao(self, caso, violacao, tmp_path):
        """SC4: `upheld: false` produz Decision `unresolved`, e o motivo viaja nela."""
        done = run_fixture(FIXTURES / caso, tmp_path / "case")["saidas"][-1]
        assert done["referee"]["upheld"] is False
        assert done["outcome"] == "unresolved"
        assert any(violacao in risco for risco in done["decision"]["risks"])

    def test_candidato_recusado_nao_deixa_vencedor_no_blackboard(self, tmp_path):
        """O blackboard e append-only: o candidato recusado nunca e gravado."""
        raiz = tmp_path / "case"
        run_fixture(FIXTURES / "objecao_sem_replica", raiz)
        decisoes = read_decisions(raiz)
        assert len(decisoes) == 1
        assert decisoes[0]["selected_option"].startswith("unresolved")
