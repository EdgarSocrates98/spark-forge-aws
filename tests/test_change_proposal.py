"""L3 do §15: o pacote de proposta de PR, por unidade e pela porta publica.

O golden em `fixtures/change/proposta_*` prende o pacote byte a byte; aqui ficam
as garantias que um golden sozinho nao prova: as recusas, que nada e gravado
quando uma delas sai, que o patch reproduz as duas copias, e que o modulo nao
chama git nem subprocess.
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.adapters._core import AdapterError
from sparkforge.change import apply_patches, parse_unified_diff
from sparkforge.change.proposal import classificar

ROOT = Path(__file__).resolve().parents[1]
CASO = ROOT / "fixtures" / "change" / "plano_pelo_sandbox" / "input"
BENCH = ROOT / "fixtures" / "bench" / "clean_improvement" / "expected" / "facts.json"
NOW = "2026-09-14T00:00:00Z"
PACOTE = [
    "branch.txt",
    "change.patch",
    "commands.md",
    "commit_message.txt",
    "evidence/receipt.json",
    "evidence/sandbox_report.json",
    "manifest.json",
    "pr_body.md",
    "rollback.patch",
]


def _sandbox(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    shutil.copytree(CASO / "repo", repo)
    plano = _core.change_plan(
        [str(CASO / "facts.json")], str(repo), sets=["spark.sql.shuffle.partitions=320"]
    )
    diff = tmp_path / "plano.patch"
    diff.write_text(plano["diff"], encoding="utf-8", newline="\n")
    sandbox = _core.change_sandbox(str(repo), diff_path=str(diff))
    assert sandbox["applied"], sandbox
    return repo, sandbox["id"]


def _arvore(pasta: Path) -> dict[str, bytes]:
    return {
        p.relative_to(pasta).as_posix(): p.read_bytes() for p in pasta.rglob("*") if p.is_file()
    }


class TestPacote:
    def test_grava_os_nove_arquivos_sem_rodar_git(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)

        assert resultado["refused"] == []
        assert resultado["files"] == PACOTE
        assert resultado["git_run"] is False and resultado["main_tree_touched"] is False
        assert sorted(_arvore(repo / resultado["proposal"])) == PACOTE

    def test_o_mesmo_now_grava_os_mesmos_bytes(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        primeiro = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)
        antes = _arvore(repo / primeiro["proposal"])
        segundo = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)

        assert segundo == primeiro
        assert _arvore(repo / segundo["proposal"]) == antes

    def test_o_corpo_lista_a_medida_pendente_e_nao_afirma_ganho(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)
        corpo = (repo / resultado["proposal"] / "pr_body.md").read_text(encoding="utf-8")

        assert resultado["pending_measures"] == ["benchmark", "funcval"]
        assert "### benchmark: PENDENTE" in corpo and "### funcval: PENDENTE" in corpo
        assert "## O que esta proposta nao afirma" in corpo

    def test_a_assinatura_do_corpo_confere(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)
        achados = repo / ".sparkforge" / "sandbox" / ident / "after" / ".sparkforge" / "scan"

        assert resultado["signed"] is True
        verificado = _core.report_verify(
            str(repo / resultado["proposal"] / "pr_body.md"), str(achados / "findings.json")
        )
        assert verificado["status"] == "signed", verificado

    def test_o_recibo_tem_raiz_no_after_e_nao_carrega_spans(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)
        recibo = json.loads(
            (repo / resultado["proposal"] / "evidence" / "receipt.json").read_text(encoding="utf-8")
        )

        assert recibo["receipt_id"] == resultado["receipt_id"]
        texto = json.dumps(recibo)
        assert ".sparkforge/scan/findings.json" in texto
        assert "before" not in texto.replace("\\", "/").split(".sparkforge/scan")[0]

    def test_o_patch_e_o_rollback_reproduzem_as_duas_copias(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)
        pasta = repo / resultado["proposal"]
        base = repo / ".sparkforge" / "sandbox" / ident
        original = {"main.tf": (base / "before" / "main.tf").read_bytes()}
        mudado = {"main.tf": (base / "after" / "main.tf").read_bytes()}

        ida = parse_unified_diff((pasta / "change.patch").read_text(encoding="utf-8"))
        volta = parse_unified_diff((pasta / "rollback.patch").read_text(encoding="utf-8"))
        assert apply_patches(dict(original), ida) == mudado
        assert apply_patches(dict(mudado), volta) == original

    @pytest.mark.skipif(shutil.which("git") is None, reason="sem git na maquina")
    def test_git_apply_check_aceita_o_patch(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)
        feito = subprocess.run(
            ["git", "apply", "--check", str(repo / resultado["proposal"] / "change.patch")],
            cwd=repo, capture_output=True, text=True, check=False,
        )
        assert feito.returncode == 0, feito.stderr

    def test_a_medida_anexada_entra_no_corpo(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        resultado = _core.change_propose(
            str(repo), sandbox_id=ident, benchmark_paths=[str(BENCH)], now=NOW
        )
        corpo = (repo / resultado["proposal"] / "pr_body.md").read_text(encoding="utf-8")

        assert resultado["pending_measures"] == ["funcval"]
        assert "### benchmark: anexado" in corpo and "`bench.run_delta`" in corpo


class TestRecusas:
    def test_sandbox_inexistente_nao_grava_nada(self, tmp_path):
        repo, _ = _sandbox(tmp_path)
        resultado = _core.change_propose(str(repo), sandbox_id="0" * 16, now=NOW)

        assert [r["reason"] for r in resultado["refused"]] == ["sandbox_inexistente"]
        assert not (repo / ".sparkforge" / "proposal").exists()

    def test_arvore_mudada_depois_do_sandbox(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        (repo / "main.tf").write_bytes((repo / "main.tf").read_bytes() + b"# depois\n")
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)

        assert [r["reason"] for r in resultado["refused"]] == ["sandbox_desatualizado"]
        assert "main.tf" in resultado["refused"][0]["detail"]
        assert not (repo / ".sparkforge" / "proposal").exists()

    def test_sandbox_que_nao_aplicou(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        relatorio = repo / ".sparkforge" / "sandbox" / ident / "report.json"
        dados = json.loads(relatorio.read_text(encoding="utf-8"))
        dados.update(applied=False, refused=[{"reason": "diff_nao_aplica"}])
        relatorio.write_text(json.dumps(dados), encoding="utf-8")
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)

        assert [r["reason"] for r in resultado["refused"]] == ["sandbox_nao_aplicado"]

    def test_achado_novo_p1_bloqueia_e_nao_grava(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        base = repo / ".sparkforge" / "sandbox" / ident
        sujeito = {"type": "tf_resource", "file": "main.tf", "line": 13, "symbol": "x"}
        relatorio = base / "report.json"
        dados = json.loads(relatorio.read_text(encoding="utf-8"))
        dados["new"] = [{"rule_id": "SF-TESTE-001", "subject": sujeito}]
        relatorio.write_text(json.dumps(dados), encoding="utf-8")
        achados = base / "after" / ".sparkforge" / "scan" / "findings.json"
        lista = json.loads(achados.read_text(encoding="utf-8"))
        lista.append({"rule_id": "SF-TESTE-001", "severity": "P1", "subject": sujeito})
        achados.write_text(json.dumps(lista), encoding="utf-8")
        resultado = _core.change_propose(str(repo), sandbox_id=ident, now=NOW)

        assert [r["reason"] for r in resultado["refused"]] == ["achado_novo_bloqueante"]
        assert resultado["blocking_findings"][0]["severity"] == "P1"
        assert not (repo / ".sparkforge" / "proposal").exists()

    def test_id_malformado_e_erro_de_entrada(self, tmp_path):
        repo, _ = _sandbox(tmp_path)
        with pytest.raises(AdapterError) as erro:
            _core.change_propose(str(repo), sandbox_id="../fora", now=NOW)
        assert erro.value.exit_code == 2

    def test_anexo_sem_o_kind_esperado_e_erro_de_entrada(self, tmp_path):
        repo, ident = _sandbox(tmp_path)
        with pytest.raises(AdapterError) as erro:
            _core.change_propose(
                str(repo), sandbox_id=ident, funcval_path=str(CASO / "facts.json"), now=NOW
            )
        assert erro.value.exit_code == 2
        assert "funcval." in str(erro.value)


class TestSeveridade:
    def test_p2_e_p3_vao_para_atencao_e_p0_p1_bloqueiam(self):
        novos = [
            {"rule_id": r, "subject": {"file": "a.tf", "line": i}}
            for i, r in enumerate(["SF-A", "SF-B", "SF-C", "SF-D"])
        ]
        achados = [
            {"rule_id": n["rule_id"], "severity": s, "subject": n["subject"]}
            for n, s in zip(novos, ["P0", "P1", "P2", "P3"], strict=True)
        ]
        bloqueantes, atencao = classificar(novos, achados)

        assert [b["rule_id"] for b in bloqueantes] == ["SF-A", "SF-B"]
        assert [a["rule_id"] for a in atencao] == ["SF-C", "SF-D"]

    def test_severidade_desconhecida_bloqueia(self):
        bloqueantes, atencao = classificar([{"rule_id": "SF-X", "subject": {}}], [])

        assert [b["rule_id"] for b in bloqueantes] == ["SF-X"] and atencao == []


class TestSemGit:
    def test_o_modulo_nao_importa_subprocess_nem_chama_o_sistema(self):
        """O pacote monta e o host executa: nenhum caminho do modulo roda comando."""
        arvore = ast.parse(
            (ROOT / "sparkforge" / "change" / "proposal.py").read_text(encoding="utf-8")
        )
        importados = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados |= {a.name.split(".")[0] for a in no.names}
            elif isinstance(no, ast.ImportFrom) and no.module:
                importados.add(no.module.split(".")[0])
        assert not importados & {"subprocess", "os", "pty", "shlex", "multiprocessing"}
        chamadas = {
            no.func.attr
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }
        assert not chamadas & {"system", "popen", "Popen", "run", "call", "check_output"}
