from pathlib import Path

from sparkforge.tools import (
    OfflineKnowledgeIndex,
    compare_json_schemas,
    evaluate_golden_case,
    extract_lineage_edges,
    pack_context,
)


def test_offline_manifest_verifies_without_network():
    result = OfflineKnowledgeIndex(".").verify()
    assert result["offline"] is True
    assert result["ok"] is True
    assert result["checked"] >= 6

def test_offline_search_returns_local_documents():
    results = OfflineKnowledgeIndex(".").search("schema contracts streaming")
    assert results
    assert all(x["offline"] for x in results)
    assert all(Path(x["path"]).exists() for x in results)

def test_expansion_tools_are_deterministic():
    packed = pack_context(
        [
            {"kind": "fact", "content": "x"},
            {"kind": "fact", "content": "x"},
            {"kind": "decision", "content": "y"},
        ]
    )
    assert packed["deduplicated"] == 1
    compat = compare_json_schemas(
        {"properties": {"a": {"type": "string"}}},
        {"properties": {"a": {"type": "string"}, "b": {"type": "integer"}}},
    )
    assert compat["compatible"] is True
    assert evaluate_golden_case({"findings": ["A-1"]}, {"findings": ["A-1"]})["passed"] is True
    assert extract_lineage_edges("select * from db.table; read s3://bucket/key")


def test_manifest_holds_across_line_endings_and_still_catches_tampering(tmp_path: Path):
    """Regressao: o manifest gravado no Windows reprovava os 43 no Linux.

    Os 43 documentos sao markdown que o git converte na saida, entao o mesmo
    commit tem CRLF no Windows e LF no `ubuntu-latest`. Com hash sobre byte
    cru, `verify()` reprovava a arvore intacta -- e o gate so nao acusava
    porque nao rodava em lugar nenhum. `knowledge/model-selection-observability.md`
    ainda tem 25 sequencias `CR CR LF`, e e por isso que a normalizacao REMOVE
    CR em vez de traduzir `CRLF` para `LF`: traduzir devolveria `LF LF` ali no
    Windows e `LF` no Linux, e o hash voltaria a depender da plataforma.

    O teste tambem prova o outro lado: normalizar fim de linha nao pode ter
    cegado o gate para adulteracao de verdade.
    """
    import json
    import shutil

    manifest = json.loads(
        Path("knowledge/offline-manifest.json").read_text(encoding="utf-8")
    )

    def monta(nome, transform):
        raiz = tmp_path / nome
        for item in manifest["documents"]:
            destino = raiz / item["path"]
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(transform(Path(item["path"]).read_bytes()))
        (raiz / "knowledge").mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            "knowledge/offline-manifest.json", raiz / "knowledge" / "offline-manifest.json"
        )
        return raiz

    formas = {
        "lf": lambda b: b.replace(b"\r", b""),
        "crlf": lambda b: b.replace(b"\r", b"").replace(b"\n", b"\r\n"),
        "crcrlf": lambda b: b.replace(b"\r", b"").replace(b"\n", b"\r\r\n"),
    }
    for nome, transform in formas.items():
        resultado = OfflineKnowledgeIndex(monta(nome, transform)).verify()
        assert resultado["ok"] is True, (nome, resultado["failed"])
        assert resultado["checked"] == len(manifest["documents"])

    adulterado = monta("adulterado", formas["lf"])
    alvo = adulterado / manifest["documents"][0]["path"]
    alvo.write_bytes(alvo.read_bytes() + b"linha injetada\n")
    resultado = OfflineKnowledgeIndex(adulterado).verify()
    assert resultado["ok"] is False
    assert [f["path"] for f in resultado["failed"]] == [manifest["documents"][0]["path"]]
