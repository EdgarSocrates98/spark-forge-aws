"""Golden do Execution Receipt (§14), de ponta a ponta pela CLI.

O case e montado em `tmp_path` a cada teste, pelas mesmas portas do produto:
`report sign`, `arbitrate` e `receipt emit`. O `arbitrate` nao le hora, o
`--now` e fixo e os caminhos do recibo sao relativos ao repo, entao o arquivo
gravado e o mesmo em qualquer maquina -- o que o golden prova byte a byte.

Para regenerar o golden depois de mudanca DELIBERADA de formato:
`SPARKFORGE_REGEN_RECEIPT=1 pytest tests/test_fixtures_golden_receipt.py`.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import yaml

from sparkforge.adapters import _core
from sparkforge.adapters.cli import main
from sparkforge.case.store import SCHEMA_VERSION, save_case

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "receipt"
CASO = FIXTURES / "uniao_debate"
META = yaml.safe_load((CASO / "meta.yaml").read_text(encoding="utf-8"))
ESPERADO = CASO / "expected" / "receipt.json"
REGEN = os.environ.get("SPARKFORGE_REGEN_RECEIPT") == "1"


def montar(repo: Path) -> list[str]:
    repo.mkdir()
    save_case({"schema_version": SCHEMA_VERSION, "case_id": META["case_id"]}, repo)
    (repo / "facts").mkdir()
    facts: list[str] = []
    findings: list[dict] = []
    for indice, pasta in enumerate(META["uniao"]):
        origem = ROOT / pasta
        relativo = f"facts/f{indice}.json"
        shutil.copyfile(origem / "facts.json", repo / relativo)
        facts.append(relativo)
        findings += json.loads((origem / "findings.json").read_text(encoding="utf-8"))
    (repo / "findings.json").write_text(
        json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    shutil.copyfile(CASO / "input" / "report.md", repo / "report.md")
    _core.report_sign(str(repo / "report.md"), str(repo / "findings.json"))
    _core.arbitrate_findings(
        str(repo),
        findings_path=str(repo / "findings.json"),
        facts_path=[str(repo / relativo) for relativo in facts],
        glue="5.0",
    )
    return facts


def emitir(repo: Path, facts: list[str], capsys, *extra: str) -> tuple[int, dict]:
    argumentos = [
        "receipt", "emit", "--repo", str(repo), "--findings", "findings.json",
        "--report", "report.md", "--now", META["now"],
    ]
    for relativo in facts:
        argumentos += ["--facts", relativo]
    codigo = main([*argumentos, *extra])
    saida = capsys.readouterr().out
    return codigo, (json.loads(saida) if saida.strip() else {})


def conferir(repo: Path, recibo: str, capsys) -> tuple[int, dict]:
    codigo = main(["receipt", "verify", "--repo", str(repo), "--receipt", recibo])
    return codigo, json.loads(capsys.readouterr().out)


def test_golden_byte_a_byte(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    codigo, saida = emitir(repo, facts, capsys)
    assert codigo == 0
    texto = (repo / saida["receipt_path"]).read_text(encoding="utf-8")
    if REGEN:
        ESPERADO.parent.mkdir(parents=True, exist_ok=True)
        ESPERADO.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == ESPERADO.read_text(encoding="utf-8").replace("\r\n", "\n")


def _textos_de_conteudo(valor) -> set[str]:
    """Textos de 4+ caracteres: o que, se aparecer no recibo, so pode ter vindo
    do conteudo do fact. Numero fica de fora -- medido em 2026-09-12, os
    `measures` desta uniao sao so inteiros de 0 a 33, e casariam com contagem
    legitima do proprio recibo."""
    if isinstance(valor, dict):
        return {v for item in valor.values() for v in _textos_de_conteudo(item)}
    if isinstance(valor, list):
        return {v for item in valor for v in _textos_de_conteudo(item)}
    if isinstance(valor, str) and len(valor) >= 4:
        return {valor}
    return set()


def test_nenhum_conteudo_dos_facts_da_uniao_entra_no_recibo(tmp_path, capsys):
    """V2 sobre o golden real: nada de `measures`, `attrs` nem `subject` -- e
    ali que mora o caminho, a tabela e o job do caso."""
    repo = tmp_path / "case"
    facts = montar(repo)
    _, saida = emitir(repo, facts, capsys)
    recibo = (repo / saida["receipt_path"]).read_text(encoding="utf-8")
    textos: set[str] = set()
    for relativo in facts:
        for fato in json.loads((repo / relativo).read_text(encoding="utf-8")):
            for campo in ("measures", "attrs", "subject"):
                textos |= _textos_de_conteudo(fato.get(campo) or {})
    assert textos, "a uniao precisa ter conteudo para a varredura provar alguma coisa"
    valores = _textos_de_conteudo(json.loads(recibo))
    vazados = sorted(
        t for t in textos if t in valores or (len(t) >= 8 and any(t in v for v in valores))
    )
    assert vazados == []
    assert "metadata_json" not in recibo


def test_duas_emissoes_gravam_o_mesmo_arquivo(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    _, primeira = emitir(repo, facts, capsys)
    texto = (repo / primeira["receipt_path"]).read_bytes()
    _, segunda = emitir(repo, facts, capsys)
    assert segunda["receipt_id"] == primeira["receipt_id"]
    assert (repo / segunda["receipt_path"]).read_bytes() == texto


def test_bloco_de_decisao_vem_do_arbitrate(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    _, saida = emitir(repo, facts, capsys)
    recibo = json.loads((repo / saida["receipt_path"]).read_text(encoding="utf-8"))
    contagem = {
        item["path"].rsplit("/", 1)[-1]: item["count"] for item in recibo["decision"]["blackboard"]
    }
    assert contagem["claims.jsonl"] == 3
    assert contagem["contradictions.jsonl"] == 1
    assert recibo["judgment"]["report"]["signature"].startswith("sig_")


def test_sem_run_id_a_parte_tools_e_lacuna(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    _, saida = emitir(repo, facts, capsys)
    assert {"field": "tools", "reason": "run_id_nao_declarado"} in saida["unresolved"]


def test_verify_limpo_sai_0(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    _, saida = emitir(repo, facts, capsys)
    codigo, veredito = conferir(repo, saida["receipt_path"], capsys)
    assert codigo == 0
    assert veredito["valid"] is True
    assert veredito["not_rechecked"] == []


def test_verify_adulterado_sai_1_e_nomeia_a_parte(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    _, saida = emitir(repo, facts, capsys)
    alvo = repo / facts[0]
    alvo.write_text(alvo.read_text(encoding="utf-8") + " ", encoding="utf-8")
    codigo, veredito = conferir(repo, saida["receipt_path"], capsys)
    assert codigo == 1
    assert veredito["diverged"] == ["evidence"]


def test_recibo_ilegivel_sai_2(tmp_path, capsys):
    repo = tmp_path / "case"
    montar(repo)
    ruim = repo / ".sparkforge" / "receipts" / "ruim.json"
    ruim.parent.mkdir(parents=True)
    ruim.write_text("{nao e json", encoding="utf-8")
    codigo = main(["receipt", "verify", "--repo", str(repo), "--receipt", str(ruim)])
    assert codigo == 2
    assert "JSON ilegivel" in capsys.readouterr().err


def test_facts_fora_do_repo_e_recusado_e_nada_e_gravado(tmp_path, capsys):
    repo = tmp_path / "case"
    facts = montar(repo)
    fora = tmp_path / "fora.json"
    fora.write_text("[]", encoding="utf-8")
    argumentos = ["receipt", "emit", "--repo", str(repo), "--findings", "findings.json"]
    for relativo in [*facts, str(fora)]:
        argumentos += ["--facts", relativo]
    codigo = main([*argumentos, "--now", META["now"]])
    assert codigo == 2
    assert "fora de --repo" in capsys.readouterr().err
    assert not (repo / ".sparkforge" / "receipts").exists()
