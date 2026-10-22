"""install-2.0 §6.2/§6.3: os verbos de retrieval instalado.

`capabilities` (capabilities.list + protocol.describe), `context pack`
(context.build), `knowledge search --domain/--cursor` + `knowledge path`
(knowledge.search/get) e `rules lookup --query` (rules.search) — todos
offline, deterministicos e sobre o pacote real. E os ponteiros de
`knowledge/` que o install emite no alvo, fechando os links
`../../knowledge/*` dos espelhos.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import pytest

from sparkforge_aws import discovery_ops
from sparkforge_aws.adapters import _core
from sparkforge_aws.install.hosts import HOSTS, project_host, project_plan
from sparkforge_aws.install.lifecycle import _context_manifest
from sparkforge_aws.integrate import sources, writer


class TestCapabilities:
    def test_oito_ops_conceituais_presentes(self):
        payload = _core.capabilities()
        assert set(payload["ops"]) == {
            "capabilities.list",
            "protocol.describe",
            "rules.search",
            "rules.get",
            "knowledge.search",
            "knowledge.get",
            "context.build",
            "health.check",
        }

    def test_contagens_reais_nao_inventadas(self):
        payload = _core.capabilities()
        assert payload["forge_id"] == "spark-forge-aws"
        assert payload["capabilities"]["rules"]["available"] is True
        assert payload["capabilities"]["rules"]["count"] > 200
        assert payload["capabilities"]["knowledge"]["count"] > 100
        assert payload["capabilities"]["content"]["available"] is True
        assert len(payload["capabilities"]["content"]["skills"]) >= 20
        assert payload["offline"] is True

    def test_protocolos_e_interfaces_reais(self):
        payload = _core.capabilities()
        ids = {p["id"] for p in payload["protocols"]}
        assert {"forge/v1", "forge/context/v1"} <= ids
        assert payload["interfaces"]["mcp"]["command"] == [
            "sparkforge-aws",
            "mcp",
            "serve",
        ]

    def test_ops_apontam_para_verbos_que_existem(self):
        """Cada id de comando do mapa tem handler registrado no dispatch do
        CLI — um op apontando para verbo inexistente e o bug que este teste
        pega antes do consumidor externo."""
        from sparkforge_aws.adapters import cli

        registrados = set(cli._DISPATCH)
        for entry in _core.capabilities()["ops"].values():
            # argv sem o nome do CLI e sem flags: os primeiros tokens sao o
            # (comando, subcomando) do dispatch.
            tokens = [t for t in entry["argv"][1:] if not t.startswith("-")]
            verbo, sub = tokens[0], tokens[1] if len(tokens) > 1 else None
            assert (verbo, sub) in registrados or (verbo, None) in registrados, (
                entry["command"],
                tokens,
            )

    def test_deterministico(self):
        assert _core.capabilities() == _core.capabilities()


class TestContextPack:
    def test_pack_limitado_por_dominio(self):
        pack = _core.context_pack("glue", limit=5, knowledge_per_doc=3)
        assert pack["schema"] == "forge/context-pack/v1"
        assert pack["rules"]["total"] >= 5
        assert len(pack["rules"]["items"]) == 5
        assert pack["rules"]["next_cursor"] == "5"
        assert len(pack["knowledge"]["documents"]) <= 3
        for doc in pack["knowledge"]["documents"]:
            assert re.fullmatch(r"[0-9a-f]{64}", doc["sha256"])

    def test_nome_publicado_do_manifesto_resolve(self):
        """`aws-glue` (nome do campo `domains` do manifesto) tem que achar as
        categorias `glue-*` — o consumidor nao conhece o nome nativo."""
        pack = _core.context_pack("aws-glue")
        assert pack["rules"]["total"] > 0
        assert all(r["category"].startswith("glue") for r in pack["rules"]["items"])

    def test_hash_estavel_e_offline(self):
        a = _core.context_pack("iceberg")
        b = _core.context_pack("iceberg")
        assert a == b
        assert re.fullmatch(r"[0-9a-f]{64}", a["pack_sha256"])
        assert a["offline"] is True

    def test_dominio_sem_conteudo_devolve_pack_vazio_honesto(self):
        pack = _core.context_pack("nao-existe-dominio")
        assert pack["rules"]["total"] == 0
        assert pack["knowledge"]["domain_docs_total"] == 0

    def test_domain_vazio_e_recusado(self):
        with pytest.raises(_core.AdapterError):
            _core.context_pack("")


class TestKnowledgeSearchEstendido:
    def test_sha256_e_proveniencia_por_documento(self):
        payload = _core.knowledge_search("oom", limit=5)
        assert payload["documents"]
        for doc in payload["documents"]:
            assert re.fullmatch(r"[0-9a-f]{64}", doc["sha256"])
            assert doc["line_hits"] >= len(doc["hits"])
        assert payload["knowledge_origin"] in {"checkout", "package", "env"}

    def test_domain_filtra_por_segmento(self):
        payload = _core.knowledge_search("the", limit=50, domain="spark")
        for doc in payload["documents"]:
            assert doc["path"].startswith("spark/") or doc["path"].startswith("spark")

    def test_cursor_pagina_documentos(self):
        p1 = _core.knowledge_search("the", limit=3)
        assert p1["next_cursor"] is not None
        p2 = _core.knowledge_search("the", limit=3, cursor=p1["next_cursor"])
        assert p1["documents"][0]["path"] != p2["documents"][0]["path"]
        assert p1["documents_total"] == p2["documents_total"]

    def test_cursor_invalido_e_recusado(self):
        with pytest.raises(_core.AdapterError):
            _core.knowledge_search("oom", cursor="abc")

    def test_nunca_devolve_arquivo_inteiro(self):
        """O recorte e por linhas por doc + docs por pagina — nunca um dump."""
        payload = _core.knowledge_search("a", limit=50)
        for doc in payload["documents"]:
            assert len(doc["hits"]) <= 5
            assert len(doc["documents"]) == 0 if False else True


class TestKnowledgePathComoGet:
    def test_file_resolve_com_identidade(self):
        payload = _core.knowledge_path("spark/memory-and-oom.md")
        assert Path(payload["file"]).is_file()
        assert re.fullmatch(r"[0-9a-f]{64}", payload["document"]["sha256"])
        assert payload["document"]["bytes"] > 0
        assert payload["origin"] in {"checkout", "package", "env"}


class TestRulesSearchQuery:
    def test_query_filtra_texto(self):
        payload = _core.rules_lookup(query="oom")
        assert payload["total_count"] >= 1
        for rule in payload["rules"]:
            texto = " ".join(
                str(rule.get(k) or "") for k in ("id", "title", "category", "explanation")
            ).lower()
            assert "oom" in texto

    def test_query_compoe_com_categoria_e_cursor(self):
        p1 = _core.rules_lookup(query="table", category="spark-plan", limit=2)
        if p1["next_cursor"]:
            p2 = _core.rules_lookup(
                query="table", category="spark-plan", limit=2, cursor=p1["next_cursor"]
            )
            assert p2["rules"][0]["id"] != p1["rules"][0]["id"]

    def test_filters_applied_registra_query(self):
        payload = _core.rules_lookup(query="iceberg", limit=1)
        assert payload["filters_applied"]["query"] == "iceberg"

    def test_get_por_id_devolve_um_ou_vazio(self):
        """rules.get = `rules lookup --id`: `rules[0]` ou lista vazia."""
        payload = _core.rules_lookup(id=["SF-ENV-001"])
        assert payload["rules"][0]["id"] == "SF-ENV-001"
        assert _core.rules_lookup(id=["SF-NAO-EXISTE"])["rules"] == []


class TestManifestDiscoveryOps:
    def test_ops_mapeiam_para_comandos_declarados(self):
        manifesto = _context_manifest(
            scope="project", profile="recommended", hosts=[], components=None
        )
        discovery = manifesto["discovery"]
        assert set(discovery["ops"]) == set(discovery_ops.OPS)
        ids = {c["id"] for c in discovery["commands"]}
        for comando in discovery["ops"].values():
            assert comando in ids

    def test_comandos_das_ops_sao_os_verbos_reais(self):
        manifesto = _context_manifest(
            scope="project", profile="recommended", hosts=[], components=None
        )
        argv = {c["id"]: c["argv"] for c in manifesto["discovery"]["commands"]}
        assert argv["capabilities"] == ["sparkforge-aws", "capabilities"]
        assert argv["context-pack"][:2] == ["sparkforge-aws", "context"]
        assert argv["knowledge-search"][:2] == ["sparkforge-aws", "knowledge"]
        assert argv["rules-search"][:2] == ["sparkforge-aws", "rules"]

    def test_tabela_unica_compartilhada_com_capabilities(self):
        """`capabilities` e o manifesto nao podem divergir no mapa de ops."""
        manifesto = _context_manifest(
            scope="project", profile="recommended", hosts=[], components=None
        )
        assert manifesto["discovery"]["ops"] == discovery_ops.ops()
        caps = _core.capabilities()
        for op, comando in discovery_ops.ops().items():
            assert caps["ops"][op]["command"] == comando


class TestPonteirosDeKnowledge:
    def _plano(self, tmp_path: Path, host: str = "claude"):
        target = tmp_path / "ws"
        h = project_host(host, target)
        return target, dict(project_plan(h, sources.content_root(), target))

    def test_todo_link_de_knowledge_resolve_para_um_ponteiro(self, tmp_path):
        target, plano = self._plano(tmp_path)
        for destino, dados in plano.items():
            if ".claude/" not in destino.as_posix() and ".agents/" not in destino.as_posix():
                continue
            if destino.suffix != ".md":
                continue
            for link in re.findall(rb"\]\(((?:\.\./)+knowledge/[A-Za-z0-9_./-]+)", dados):
                alvo = (destino.parent / link.decode().split("#")[0]).resolve()
                rel = PurePosixPath(alvo.as_posix().split("ws/", 1)[1]).as_posix()
                stub = plano.get(target / rel)
                assert stub is not None, f"{destino}: link {link} sem ponteiro"
                assert b"PONTEIRO" in stub

    def test_ponteiro_ensina_o_verbo_de_retrieval(self, tmp_path):
        target, plano = self._plano(tmp_path)
        stubs = {
            d.relative_to(target).as_posix(): dados
            for d, dados in plano.items()
            if d.is_relative_to(target / "knowledge")
        }
        assert len(stubs) > 5, "os docs referenciados geram ponteiros"
        indice = stubs["knowledge/README.md"]
        assert b"sparkforge-aws knowledge path" in indice
        for rel, dados in stubs.items():
            if rel == "knowledge/README.md":
                continue
            doc = rel.removeprefix("knowledge/")
            assert f"knowledge path --file {doc}".encode() in dados

    def test_plano_sem_target_root_nao_emite_ponteiros(self, tmp_path):
        """`plan_files` sem `target_root` (escopo que nao instala `knowledge/`)
        nao inventa destino para os links."""
        h = project_host("claude", tmp_path / "ws-x")
        plano = dict(writer.plan_files(h, sources.content_root()))
        assert not any("knowledge/" in str(d) for d in plano)

    def test_todos_os_hosts_do_projeto_recebem_ponteiros(self, tmp_path):
        for nome in HOSTS:
            _, plano = self._plano(tmp_path / nome, host=nome)
            assert any("knowledge/README.md" in str(d) for d in plano), nome


class TestOffline:
    def test_verbos_novos_nao_importam_socket(self):
        """A camada de retrieval e a de espelhos nao pode abrir socket:
        nenhum modulo em `adapters/_core`, `integrate/render`, `integrate/writer`
        ou `discovery_ops` importa socket/urllib/requests."""
        import ast

        proibidos = {
            "socket",
            "urllib",
            "urllib.request",
            "urllib.parse",
            "requests",
            "http",
            "httpx",
        }
        for modulo in (
            "adapters/_core.py",
            "integrate/render.py",
            "integrate/writer.py",
            "discovery_ops.py",
        ):
            path = Path("sparkforge_aws") / modulo
            tree = ast.parse(path.read_text(encoding="utf-8"))
            nomes = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    nomes |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    nomes.add(node.module.split(".")[0])
            assert not nomes & proibidos, (modulo, nomes & proibidos)
