from pathlib import Path

import pytest

from scripts import check_vnext_claims as gate

ROOT = Path(__file__).resolve().parents[1]


class TestDocumentosAuditados:
    def test_cobre_os_dois_diretorios_sem_repetir(self):
        docs = gate.audited_docs()
        nomes = {p.name for p in docs}
        assert "FINAL-REPORT.md" in nomes
        assert "ADR-001-canonical-registry.md" in nomes
        assert len(nomes) == len(docs), "documento contado duas vezes"
        assert any(p.parent.name == "adrs" for p in docs)
        assert any(p.parent.name == "vnext" for p in docs)

    def test_inclui_todo_adr_do_diretorio(self):
        no_disco = {p.name for p in (gate.VNEXT / "adrs").glob("*.md")}
        auditados = {p.name for p in gate.audited_docs()}
        assert no_disco <= auditados

    def test_o_caminho_e_relativo_a_raiz(self):
        doc = gate.audited_docs()[0]
        assert gate.rel(doc).startswith("docs/vnext/")
        assert "\\" not in gate.rel(doc)


DOC_SINTETICO = """# Titulo

Este relatorio declara uma economia de 81,8% no custo por mil tarefas
e 5.485 testes na suite, em 2026-08-21, versao 0.5.0, conforme ADR-003.
Sao 38 agentes no catalogo.

Fonte: https://docs.aws.amazon.com/glue/latest/dg/release-notes-5-1.html

```python
BATCH = 1000
```
"""


class TestExtracaoNumerica:
    def _extrai(self, tmp_path):
        doc = tmp_path / "SINTETICO.md"
        doc.write_text(DOC_SINTETICO, encoding="utf-8")
        return [item["text"] for item in gate.extract_numbers(doc)]

    def test_captura_percentual_e_contagem(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert "81,8%" in textos
        assert "5.485" in textos
        # Contagem de um ou dois digitos e a forma dominante de alegacao
        # nestes documentos -- perde-la e um buraco permanente na auditoria.
        assert "38" in textos

    def test_lookaround_descarta_data_e_identificador(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert not any("2026-08-21" in t for t in textos)
        assert not any(t == "003" for t in textos)

    def test_allowlist_descarta_versao_semantica_mesmo_com_pontuacao(self, tmp_path):
        doc = tmp_path / "VERSAO.md"
        doc.write_text("Pacote na versao 0.5.0, publicado.\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_allowlist_descarta_ano_isolado_mesmo_com_pontuacao(self, tmp_path):
        doc = tmp_path / "ANO.md"
        doc.write_text("Fechado em 2026, sem pendencia.\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_token_nao_carrega_pontuacao_final(self, tmp_path):
        doc = tmp_path / "PONTUACAO.md"
        doc.write_text("Sao 17, e depois 3.5, no total.\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["17", "3.5"]

    def test_ignora_bloco_de_codigo_e_linha_de_fonte(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert "1000" not in textos
        assert not any("5-1" in t for t in textos)

    def test_cada_padrao_da_allowlist_declara_a_razao(self):
        for _, razao in gate.IGNORED_TOKENS:
            assert razao and len(razao) > 10

    def test_fence_nao_fechado_estoura_com_nome_do_arquivo(self, tmp_path):
        doc = tmp_path / "FENCE_ABERTO.md"
        doc.write_text("Antes da cerca\n```python\nresto sem fechar\n", encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            gate.extract_numbers(doc)
        assert doc.name in str(exc_info.value)

    def test_doc_fora_da_raiz_usa_caminho_absoluto_posix(self, tmp_path):
        doc = tmp_path / "SINTETICO.md"
        doc.write_text(DOC_SINTETICO, encoding="utf-8")
        itens = gate.extract_numbers(doc)
        assert itens[0]["doc"] == doc.resolve().as_posix()
        assert "\\" not in itens[0]["doc"]
