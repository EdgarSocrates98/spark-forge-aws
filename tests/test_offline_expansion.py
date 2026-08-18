from pathlib import Path
from sparkforge.tools import OfflineKnowledgeIndex, compare_json_schemas, evaluate_golden_case, extract_lineage_edges, pack_context

def test_offline_manifest_verifies_without_network():
    result=OfflineKnowledgeIndex(".").verify()
    assert result["offline"] is True
    assert result["ok"] is True
    assert result["checked"] >= 6

def test_offline_search_returns_local_documents():
    results=OfflineKnowledgeIndex(".").search("schema contracts streaming")
    assert results
    assert all(x["offline"] for x in results)
    assert all(Path(x["path"]).exists() for x in results)

def test_expansion_tools_are_deterministic():
    packed=pack_context([{ "kind":"fact", "content":"x" },{ "kind":"fact", "content":"x" },{ "kind":"decision", "content":"y" }])
    assert packed["deduplicated"] == 1
    assert compare_json_schemas({"properties":{"a":{"type":"string"}}},{"properties":{"a":{"type":"string"},"b":{"type":"integer"}}})["compatible"] is True
    assert evaluate_golden_case({"findings":["A-1"]},{"findings":["A-1"]})["passed"] is True
    assert extract_lineage_edges("select * from db.table; read s3://bucket/key")
