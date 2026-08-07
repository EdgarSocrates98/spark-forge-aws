"""Gates do ecossistema caveman vendorizado.

Três coisas quebram silenciosamente aqui, e cada uma tem teste próprio:

1. **Procedência.** `vendor/` é código de terceiro commitado. Uma edição local
   acidental transformaria "pinado em `<sha>` do upstream" em mentira. O gate é
   `vendor/MANIFEST.sha256`, e ele não usa rede.
2. **Ativação.** O valor inteiro da vendorização é "quem clonar já tem ligado".
   Um `path` absoluto em `.claude/settings.json` ou um plugin desabilitado
   deixam a árvore em disco e a ativação em lugar nenhum — e nada acusa, porque
   o repositório continua passando em todo o resto.
3. **Crédito.** MIT autoriza a cópia *com* o aviso de copyright. LICENSE
   apagado num pruning futuro é violação de licença, não descuido de docs.
"""
import json
import re
from pathlib import Path

import pytest

from scripts import vendor_caveman

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestProcedencia:
    def test_arvore_confere_com_o_manifest(self):
        """O gate central. Sem rede: compara disco contra sha256 declarado."""
        assert vendor_caveman.check() == []

    def test_manifest_nao_esta_vazio(self):
        """`check()` de uma árvore vazia contra um manifest vazio passaria."""
        assert len(vendor_caveman.expected_manifest()) > 100

    def test_cada_projeto_declara_repo_sha_e_licenca(self):
        for entry in vendor_caveman.load_pins()["vendored"]:
            assert entry["repo"].startswith("https://github.com/")
            assert re.fullmatch(r"[0-9a-f]{40}", entry["sha"]), entry["name"]
            assert entry["license"] == "MIT"
            assert entry["author"]

    def test_o_manifest_cita_o_sha_de_cada_projeto(self):
        """O manifest é o que o gate lê; o SHA precisa viajar junto dele.

        Sem isto, `PINS.json` poderia apontar para um commit e o manifest
        descrever outro, e as duas metades continuariam internamente coerentes.
        """
        header = (VENDOR / "MANIFEST.sha256").read_text(encoding="utf-8")
        for entry in vendor_caveman.load_pins()["vendored"]:
            assert entry["sha"] in header
            assert entry["repo"] in header

    def test_licenca_original_preservada_em_cada_projeto(self):
        for entry in vendor_caveman.load_pins()["vendored"]:
            license_file = VENDOR / entry["dest"] / "LICENSE"
            assert license_file.is_file(), entry["name"]
            assert "MIT" in license_file.read_text(encoding="utf-8")

    def test_todo_caminho_do_pins_e_recusado_se_escapar_do_vendor(self, tmp_path):
        """Achado da revisão de 2026-08-07, corrigido no mesmo passe.

        `Path("vendor") / "/etc/x"` devolve `/etc/x` — o operador `/` do pathlib
        **descarta** o lado esquerdo quando o direito é absoluto, e `..` nunca é
        normalizado. `materialize()` fazia `dest / entry["keep"]` e
        `dest / patch["to"]` sem guarda, com `shutil.rmtree`/`copytree` em
        seguida: um `to` de `../../.claude/settings.json` num PR de "bump de
        pin" escreveria fora de `vendor/`.

        O que tornava isso pior que um write qualquer: `actual_manifest()` só
        varre `VENDOR.rglob`, então o arquivo escrito fora ficava invisível para
        o único gate que este script existe para sustentar.
        """
        for escape in ("../fora", "/etc/passwd", "C:/Windows/x", "..\\fora", "a/../../b"):
            with pytest.raises(SystemExit):
                vendor_caveman._confinado(tmp_path, escape, campo="teste", entrada="t")

    def test_caminho_normal_continua_passando(self, tmp_path):
        alvo = vendor_caveman._confinado(
            tmp_path, "skills/caveman/SKILL.md", campo="k", entrada="t"
        )
        assert alvo == tmp_path / "skills/caveman/SKILL.md"

    def test_repo_e_sha_sao_validados_no_codigo_e_nao_so_no_teste(self, tmp_path):
        """Teste não protege quem roda o script antes da suíte.

        O valor é consumido em `clone_at`, então a guarda mora lá também.
        """
        sha = "0" * 40
        for repo in ("ext::sh -c id", "--upload-pack=id", "https://evil.example/a/b"):
            with pytest.raises(SystemExit):
                vendor_caveman.clone_at(repo, sha, tmp_path / "x")
        for ruim in ("--upload-pack=id", "HEAD", "z" * 40):
            with pytest.raises(SystemExit):
                vendor_caveman.clone_at("https://github.com/a/b", ruim, tmp_path / "x")

    def test_o_patch_declarado_esta_aplicado(self):
        """O `SKILL.md` de caveman-compress roda `python3 -m scripts` do próprio
        diretório, e o upstream só publica esses scripts sob `plugins/`.

        Reclonar sem reaplicar o patch deixa a skill carregando e falhando na
        execução -- que é o modo de falha mais caro, porque só aparece em uso.
        """
        assert (VENDOR / "caveman/skills/caveman-compress/scripts/__main__.py").is_file()


class TestMarketplaceVendorizado:
    def _marketplace(self) -> dict:
        return _json(VENDOR / ".claude-plugin" / "marketplace.json")

    def test_declara_os_dois_plugins_vendorizados(self):
        names = {p["name"] for p in self._marketplace()["plugins"]}
        assert names == {"caveman", "ck"}

    def test_cada_source_e_relativo_e_existe_em_disco(self):
        for plugin in self._marketplace()["plugins"]:
            source = plugin["source"]
            assert isinstance(source, str) and source.startswith("./"), plugin["name"]
            assert (VENDOR / source[2:] / ".claude-plugin" / "plugin.json").is_file() or (
                VENDOR / source[2:] / "plugin.json"
            ).is_file(), plugin["name"]

    def test_credita_o_autor_em_cada_entrada(self):
        for plugin in self._marketplace()["plugins"]:
            assert plugin["author"]["name"] == "Julius Brussee"
            assert plugin["license"] == "MIT"

    def test_os_hooks_do_plugin_caveman_apontam_para_arquivo_existente(self):
        """`plugin.json` do caveman declara dois hooks por caminho.

        Um pruning futuro que tirasse `src/hooks/` deixaria o plugin instalável
        e inerte: o Claude Code carrega o manifesto e o hook falha em silêncio.
        """
        manifest = _json(VENDOR / "caveman" / ".claude-plugin" / "plugin.json")
        commands = [
            hook["command"]
            for group in manifest["hooks"].values()
            for entry in group
            for hook in entry["hooks"]
        ]
        assert len(commands) == 2
        for command in commands:
            match = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"]+)", command)
            assert match, command
            assert (VENDOR / "caveman" / match.group(1)).is_file(), command


class TestAtivacao:
    def _settings(self) -> dict:
        return _json(ROOT / ".claude" / "settings.json")

    def test_o_marketplace_local_esta_declarado_por_caminho_relativo(self):
        """Caminho absoluto é o que o `claude plugin marketplace add` escreve, e
        é exatamente o que não sobrevive ao clone de outra pessoa."""
        source = self._settings()["extraKnownMarketplaces"]["sparkforge-caveman"]["source"]
        assert source["source"] == "directory"
        assert source["path"] == "./vendor"

    def test_os_dois_plugins_vendorizados_estao_habilitados(self):
        enabled = self._settings()["enabledPlugins"]
        assert enabled["caveman@sparkforge-caveman"] is True
        assert enabled["ck@sparkforge-caveman"] is True

    def test_as_copias_upstream_estao_desligadas_dentro_do_projeto(self):
        """Dois caveman ligados injetam o ruleset duas vezes por sessão.

        O projeto existe para cortar token; ativar em dobro custa token. Quem
        tem o plugin do upstream instalado globalmente continua com ele em todo
        lugar, menos aqui.
        """
        enabled = self._settings()["enabledPlugins"]
        assert enabled["caveman@caveman"] is False
        assert enabled["ck@cavekit"] is False

    def test_o_modo_full_esta_fixado_no_repositorio(self):
        assert _json(ROOT / ".caveman" / "config.json")["defaultMode"] == "full"

    def test_existe_fallback_em_shell_para_maquina_sem_node(self):
        """Os dois hooks do plugin caveman são `node ...`.

        Sem Node eles não rodam, e "ligado por padrão" viraria "ligado quando
        alguém digitar `/caveman`" -- silenciosamente, porque as skills
        continuam carregando. O fallback só dispara quando `node` não está no
        PATH, então com Node não há injeção dupla.
        """
        commands = [
            h["command"]
            for entry in self._settings()["hooks"]["SessionStart"]
            for h in entry["hooks"]
        ]
        fallback = [c for c in commands if "caveman-activate.md" in c]
        assert len(fallback) == 1
        assert "command -v node" in fallback[0]
        assert (ROOT / "vendor/caveman/src/rules/caveman-activate.md").is_file()

    def test_os_servidores_do_projeto_estao_pre_aprovados(self):
        """Servidor declarado em `.mcp.json` e não pré-aprovado fica inerte.

        `enabledMcpjsonServers` no settings **commitado** é o que faz "já
        ativado" valer para quem clonou, e não só para quem já tinha o
        `settings.local.json` da máquina de origem.
        """
        enabled = set(self._settings()["enabledMcpjsonServers"])
        assert set(_json(ROOT / ".mcp.json")["mcpServers"]) <= enabled


class TestSemNpm:
    """O invariante que o resto deste arquivo existe para proteger.

    A economia de token tem que sair do repositório clonado e de mais nada.
    `npm install` e `npx` são a forma mais fácil de essa propriedade vazar sem
    ninguém perceber: basta alguém acrescentar um `package.json` "só para uma
    ferramentinha" e o clone volta a depender de rede, de registry e de
    compilação nativa.
    """

    def test_nao_existe_package_json_na_raiz(self):
        assert not (ROOT / "package.json").exists()
        assert not (ROOT / "package-lock.json").exists()

    def test_nenhum_hook_ou_servidor_mcp_invoca_npm_ou_npx(self):
        settings = _json(ROOT / ".claude" / "settings.json")
        commands = [
            hook["command"]
            for groups in settings.get("hooks", {}).values()
            for entry in groups
            for hook in entry["hooks"]
        ]
        for server in _json(ROOT / ".mcp.json")["mcpServers"].values():
            commands.append(" ".join([server["command"], *server.get("args", [])]))
        for command in commands:
            assert not re.search(r"\bnpm\b|\bnpx\b|node_modules", command), command

    def test_os_hooks_do_plugin_vendorizado_tambem_nao(self):
        """O plugin é de terceiro: o `plugin.json` dele podia mudar num bump."""
        manifest = _json(VENDOR / "caveman" / ".claude-plugin" / "plugin.json")
        for groups in manifest["hooks"].values():
            for entry in groups:
                for hook in entry["hooks"]:
                    assert not re.search(r"\bnpm\b|\bnpx\b", hook["command"]), hook["command"]

    def test_o_que_ficou_de_fora_esta_declarado_com_a_razao(self):
        """Peça removida sem registro vira "por que isso sumiu?" seis meses depois."""
        excluded = vendor_caveman.load_pins()["nao_vendorizado"]
        names = {entry["name"] for entry in excluded}
        assert names == {"cavemem", "caveman-code", "caveman-shrink"}
        for entry in excluded:
            assert entry["why"], entry["name"]
            assert entry["license"] == "MIT"
            assert entry["author"] == "Julius Brussee"

    def test_o_caveman_shrink_esta_em_disco_mas_desligado(self):
        """Vendorizado e sem dependência, mas medido em 0,1% neste catálogo.

        O teste guarda as duas metades: o código continua disponível para quem
        quiser reavaliar, e nada o coloca no caminho do MCP sem uma medição nova.
        """
        shrink = VENDOR / "caveman/src/mcp-servers/caveman-shrink"
        assert (shrink / "index.js").is_file()
        assert "dependencies" not in _json(shrink / "package.json")
        mcp = (ROOT / ".mcp.json").read_text(encoding="utf-8")
        assert "caveman-shrink" not in mcp
        assert "0,1 %" in (VENDOR / "CREDITS.md").read_text(encoding="utf-8")


class TestCreditos:
    def test_credits_nomeia_o_autor_o_que_entrou_e_o_que_ficou_de_fora(self):
        """Crédito não é só do que foi copiado.

        MIT autoriza a cópia *com* o aviso de copyright preservado, e o que
        ficou de fora continua sendo do mesmo autor -- some do disco, não da
        atribuição.
        """
        credits = (VENDOR / "CREDITS.md").read_text(encoding="utf-8")
        assert "Julius Brussee" in credits
        for project in ("caveman", "cavekit", "cavemem", "caveman-code", "caveman-shrink"):
            assert project in credits
        for entry in vendor_caveman.load_pins()["vendored"]:
            assert entry["sha"] in credits

    def test_readme_e_sources_apontam_para_os_creditos(self):
        for name in ("README.md", "SOURCES.md"):
            assert "vendor/CREDITS.md" in (ROOT / name).read_text(encoding="utf-8"), name

    def test_agents_md_carrega_o_ruleset_para_agente_sem_plugin(self):
        """Devin e Copilot não carregam plugin nem hook.

        Sem o ruleset inline, "caveman ativado por padrão" valeria só para o
        Claude Code -- e o repositório declara os três como plataformas.
        """
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        assert "caveman" in agents.lower()
        assert "Respond terse like smart caveman" in agents
        assert "Julius Brussee" in agents

    def test_o_manifesto_do_projeto_declara_o_ferramental(self):
        """`manifest.json` é o que uma plataforma lê em vez do disco.

        Ferramental que existe e não é declarado ali é invisível para quem
        instala o pacote -- mesmo modo de falha que já custou duas skills
        omitidas (ver `test_skills_list_equals_the_skills_on_disk`).
        """
        pins = vendor_caveman.load_pins()
        tooling = _json(ROOT / "manifest.json")["agent_tooling"]
        assert tooling["vendored"] == [e["dest"] for e in pins["vendored"]]
        assert tooling["requires_install"] == []
        assert tooling["caveman_mode"] == _json(ROOT / ".caveman/config.json")["defaultMode"]
        assert Path(ROOT / tooling["credits"]).is_file()
        assert Path(ROOT / tooling["pins"]).is_file()
        assert Path(ROOT / tooling["manifest"]).is_file()
        assert Path(ROOT / tooling["marketplace"]).is_file()

    def test_gitignore_nao_engole_o_dist_vendorizado(self):
        """`dist/` solto casava com `vendor/caveman/dist/`, que é vendorizado.

        O arquivo some do commit sem erro nenhum: `git add` simplesmente ignora.
        """
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "/dist/" in ignore
        assert "\ndist/" not in ignore
        assert "node_modules/" in ignore
        assert (VENDOR / "caveman" / "dist" / "caveman.skill").is_file()
