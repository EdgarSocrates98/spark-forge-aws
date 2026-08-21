from pathlib import Path

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
