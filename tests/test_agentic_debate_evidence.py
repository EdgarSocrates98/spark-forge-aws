"""Reextracao da evidencia de debate (`debate_evidence.py`, Decisao 3 do DESIGN).

O agente entrega um PONTEIRO (`extractor` + `path`), nunca o fact. Estes testes
cobram as quatro portas por onde um fact fabricado entraria: extrator fora da
allowlist, caminho fora do case (por `..`, absoluto ou link), o diretorio de
estado do proprio debate, e o JSON de fact colado na submissao.
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

from sparkforge.agentic.executor import debate_evidence as de

TF = (
    'resource "aws_glue_job" "etl_grafo" {\n'
    '  name = "etl-grafo"\n'
    "  default_arguments = {\n"
    '    "--extra-jars" = "s3://artefatos/jars/graphframes.jar"\n'
    "  }\n"
    "}\n"
)


def _case(tmp_path: Path) -> Path:
    raiz = tmp_path / "case"
    (raiz / "artifacts").mkdir(parents=True)
    (raiz / "artifacts" / "job.tf").write_text(TF, encoding="utf-8")
    return raiz


def _recusa(raiz: Path, artefatos) -> str:
    with pytest.raises(de.EvidenceRefused) as exc:
        de.extract_evidence(raiz, artefatos)
    return exc.value.reason


class TestAllowlist:
    def test_extrator_fora_da_lista_e_recusado(self, tmp_path):
        raiz = _case(tmp_path)
        pedido = [{"extractor": "shell", "path": "artifacts/job.tf"}]
        assert _recusa(raiz, pedido) == de.EXTRACTOR_NOT_ALLOWED

    def test_o_nome_nao_compoe_import(self, tmp_path):
        """Nome de modulo real de `sparkforge.facts` fora da tabela tambem e recusado."""
        raiz = _case(tmp_path)
        pedido = [{"extractor": "host_transcript", "path": "artifacts/job.tf"}]
        assert _recusa(raiz, pedido) == de.EXTRACTOR_NOT_ALLOWED

    def test_transcript_do_host_nao_e_evidencia(self):
        assert not any("transcript" in modulo for modulo, _ in de.EVIDENCE_EXTRACTORS.values())

    @pytest.mark.parametrize("nome", sorted(de.EVIDENCE_EXTRACTORS))
    def test_todo_extrator_da_lista_recebe_path_e_repo_root(self, nome):
        funcao = de._extrator(nome)
        parametros = list(inspect.signature(funcao).parameters)
        assert parametros[:2] == ["path", "repo_root"], (nome, parametros)


class TestConfinamento:
    @pytest.mark.parametrize("caminho", ["../fora.tf", "artifacts/../../fora.tf"])
    def test_caminho_que_sobe_para_fora_e_recusado(self, tmp_path, caminho):
        raiz = _case(tmp_path)
        (tmp_path / "fora.tf").write_text(TF, encoding="utf-8")
        pedido = [{"extractor": "terraform", "path": caminho}]
        assert _recusa(raiz, pedido) == de.ARTIFACT_OUTSIDE_CASE

    def test_caminho_absoluto_para_fora_e_recusado(self, tmp_path):
        raiz = _case(tmp_path)
        fora = tmp_path / "fora.tf"
        fora.write_text(TF, encoding="utf-8")
        pedido = [{"extractor": "terraform", "path": str(fora)}]
        assert _recusa(raiz, pedido) == de.ARTIFACT_OUTSIDE_CASE

    def test_diretorio_de_estado_do_case_e_recusado(self, tmp_path):
        raiz = _case(tmp_path)
        estado = raiz / ".sparkforge" / "debate"
        estado.mkdir(parents=True)
        (estado / "forjado.tf").write_text(TF, encoding="utf-8")
        pedido = [{"extractor": "terraform", "path": ".sparkforge/debate/forjado.tf"}]
        assert _recusa(raiz, pedido) == de.ARTIFACT_OUTSIDE_CASE

    def test_a_propria_raiz_nao_e_artefato(self, tmp_path):
        raiz = _case(tmp_path)
        assert _recusa(raiz, [{"extractor": "terraform", "path": "."}]) == de.ARTIFACT_OUTSIDE_CASE

    def test_link_simbolico_para_fora_e_recusado(self, tmp_path):
        raiz = _case(tmp_path)
        fora = tmp_path / "fora.tf"
        fora.write_text(TF, encoding="utf-8")
        link = raiz / "artifacts" / "link.tf"
        try:
            os.symlink(fora, link)
        except (OSError, NotImplementedError):
            pytest.skip("o sistema nao permite criar link simbolico aqui")
        pedido = [{"extractor": "terraform", "path": "artifacts/link.tf"}]
        assert _recusa(raiz, pedido) == de.ARTIFACT_OUTSIDE_CASE

    def test_artefato_ausente_e_recusado_por_nome(self, tmp_path):
        raiz = _case(tmp_path)
        pedido = [{"extractor": "terraform", "path": "artifacts/nao_existe.tf"}]
        assert _recusa(raiz, pedido) == de.ARTIFACT_NOT_FOUND


class TestForma:
    @pytest.mark.parametrize(
        "artefatos",
        [
            "artifacts/job.tf",
            [{"extractor": "terraform"}],
            [{"extractor": "terraform", "path": "artifacts/job.tf", "fact": {"id": "f_x"}}],
            [{"extractor": "terraform", "path": ""}],
            [["terraform", "artifacts/job.tf"]],
        ],
    )
    def test_ponteiro_malformado_e_invalid_schema(self, tmp_path, artefatos):
        """Inclusive o fact colado ao lado do ponteiro: o executor nao le fact do agente."""
        assert _recusa(_case(tmp_path), artefatos) == de.INVALID_ARTIFACT_REF

    def test_extrator_que_levanta_vira_extractor_failed(self, tmp_path):
        raiz = _case(tmp_path)
        (raiz / "artifacts" / "lf.json").write_text("isto nao e json", encoding="utf-8")
        pedido = [{"extractor": "lakeformation-grants", "path": "artifacts/lf.json"}]
        assert _recusa(raiz, pedido) == de.EXTRACTOR_FAILED


class TestReextracao:
    def test_o_fact_sai_do_extrator_com_procedencia_relativa_e_sha1(self, tmp_path):
        raiz = _case(tmp_path)
        registros = de.extract_evidence(
            raiz, [{"extractor": "terraform", "path": "artifacts/job.tf"}]
        )
        kinds = {r["fact"]["kind"] for r in registros}
        assert "tf.graphframes.jar" in kinds
        assert {r["path"] for r in registros} == {"artifacts/job.tf"}
        assert all(len(r["artifact_sha1"]) == 40 for r in registros)
        assert str(tmp_path) not in json.dumps(registros)

    def test_reextracao_e_deterministica(self, tmp_path):
        raiz = _case(tmp_path)
        pedido = [{"extractor": "terraform", "path": "artifacts/job.tf"}]
        assert de.extract_evidence(raiz, pedido) == de.extract_evidence(raiz, pedido)

    def test_extract_nao_grava_e_append_deduplica(self, tmp_path):
        raiz = _case(tmp_path)
        pedido = [{"extractor": "terraform", "path": "artifacts/job.tf"}]
        registros = de.extract_evidence(raiz, pedido)
        destino = tmp_path / "debate"
        assert de.read_evidence_facts(destino) == []

        primeiro_id = registros[0]["fact"]["id"]
        gravados = de.append_evidence_facts(destino, registros + registros, {primeiro_id})
        assert primeiro_id not in gravados
        assert len(gravados) == len(registros) - 1
        assert de.append_evidence_facts(destino, registros, set(gravados) | {primeiro_id}) == []
        assert [r["fact"]["id"] for r in de.read_evidence_facts(destino)] == gravados
