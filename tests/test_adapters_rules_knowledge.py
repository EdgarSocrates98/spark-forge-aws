"""`rules lookup` entrega o caminho do knowledge que a regra cita.

A regra 4 do AGENT_PROTOCOL obriga consultar em vez de lembrar. Se a consulta
devolve a citacao `knowledge/glue/runtime-matrix.md` como texto solto, o agente
instalado por pip nao consegue abrir o arquivo -- ele esta no site-packages.
Devolver o caminho resolvido fecha isso sem passo novo.
"""
from pathlib import Path

from sparkforge.adapters import _core


def _rule(payload: dict, rule_id: str) -> dict:
    for rule in payload["rules"]:
        if rule["id"] == rule_id:
            return rule
    raise AssertionError(f"{rule_id} ausente na resposta")


class TestKnowledgeRefsAreResolved:
    def test_a_rule_that_cites_knowledge_gets_resolved_paths(self):
        payload = _core.rules_lookup(id=["SF-ENV-001"])
        rule = _rule(payload, "SF-ENV-001")
        refs = rule["knowledge_refs"]
        assert refs, "SF-ENV-001 cita knowledge/glue/runtime-matrix.md"
        assert refs[0]["ref"] == "knowledge/glue/runtime-matrix.md"
        assert Path(refs[0]["path"]).is_file()

    def test_a_rule_without_citation_gets_an_empty_list_not_a_missing_key(self):
        """Chave ausente obriga o consumidor a usar `.get`; lista vazia e um
        contrato estavel."""
        payload = _core.rules_lookup(limit=100)
        for rule in payload["rules"]:
            assert isinstance(rule["knowledge_refs"], list)

    def test_every_resolved_path_exists(self):
        payload = _core.rules_lookup(limit=100)
        for rule in payload["rules"]:
            for ref in rule["knowledge_refs"]:
                # Asserts separados de proposito: `Path(None)` levanta
                # `TypeError` antes do segundo assert rodar, e a mensagem
                # acionavel (qual regra, qual ref) nunca apareceria.
                assert ref["path"] is not None, f"{rule['id']} cita {ref['ref']}, que nao resolve"
                assert Path(ref["path"]).is_file(), (rule["id"], ref)

    def test_a_citation_inside_sources_note_is_not_omitted(self):
        """SF-PY-002 cita `knowledge/spark/memory-and-oom.md` dentro de
        `sources[0].note`, fora dos campos de texto direto da regra. A
        primeira versao desta funcao so varria explanation/proposed_change/
        validation/risks/tradeoffs e omitia essa citacao real."""
        payload = _core.rules_lookup(id=["SF-PY-002"])
        rule = _rule(payload, "SF-PY-002")
        cited = {ref["ref"] for ref in rule["knowledge_refs"]}
        assert "knowledge/spark/memory-and-oom.md" in cited

    def test_a_url_containing_knowledge_slash_is_not_a_false_positive(self):
        """`https://exemplo.com/knowledge/glue/x.md` nao e uma citacao de
        knowledge local -- e uma URL que por coincidencia contem o prefixo
        `knowledge/`. Sem exigir borda de token antes do prefixo, isso vira
        uma citacao fantasma com `path: None`, indistinguivel de uma citacao
        quebrada de verdade."""
        rule = {
            "id": "SF-TEST-URL",
            "explanation": "veja https://exemplo.com/knowledge/glue/x.md para mais detalhes",
        }
        assert _core.knowledge_refs_of(rule) == []

    def test_a_citation_pointing_nowhere_is_reported_not_silently_dropped(self):
        """Citacao quebrada e defeito de catalogo. Sumir com ela esconderia o
        defeito; `path: null` o mostra ao operador."""
        rule = {
            "id": "SF-X-001",
            "explanation": "Ver knowledge/glue/arquivo-inexistente.md secao 1.",
        }
        refs = _core.knowledge_refs_of(rule)
        assert refs == [{"ref": "knowledge/glue/arquivo-inexistente.md", "path": None}]

    def test_the_same_file_cited_twice_appears_once(self):
        rule = {
            "id": "SF-X-002",
            "explanation": "Ver knowledge/glue/runtime-matrix.md.",
            "validation": ["Conferir knowledge/glue/runtime-matrix.md de novo."],
        }
        assert len(_core.knowledge_refs_of(rule)) == 1
