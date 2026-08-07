"""Tudo que este repositório faz EXECUTAR na máquina de quem o clona.

Clonar este repositório e abrir o Claude Code executa código antes de qualquer
pessoa digitar qualquer coisa: hooks de `SessionStart`/`UserPromptSubmit` e o
comando de cada servidor MCP. Um PR que toque nesses arquivos não muda "a
configuração do projeto" — ele muda **o que roda na máquina de todo
contribuidor**, e num diff grande passa como linha de JSON.

Este arquivo é a lista fechada disso. Não é allowlist de *padrão*: é a string
exata. Padrão vaza (`node .*` autoriza `node -e "..."`); string exata obriga
quem quiser mudar a passar por aqui, e a mudança aparece na revisão como o que
de fato é.

Camada dois, para o caso de alguém atualizar a lista sem pensar: um deny-list
das construções que transformam um hook em canal de execução arbitrária —
baixar e rodar, decodificar e rodar, substituição de comando.

Cobre três superfícies:

1. `.claude/settings.json` — nosso, commitado.
2. `vendor/caveman/.claude-plugin/plugin.json` — de terceiro. Os bytes já estão
   pinados em `MANIFEST.sha256`, mas o pin diz "mudou"; este teste diz **o quê**.
3. `.mcp.json` — o binário que cada servidor levanta.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"

# ---------------------------------------------------------------------------
# A lista fechada. Mudar qualquer string aqui é mudar o que executa na máquina
# de quem clona -- que é exatamente a revisão que este arquivo força.
# ---------------------------------------------------------------------------

# `.claude/settings.json`. Único hook nosso: imprime o ruleset caveman quando,
# e somente quando, `node` não está no PATH (ver .caveman/README.md).
HOOKS_DO_PROJETO = frozenset(
    {
        "command -v node >/dev/null 2>&1 || { echo 'CAVEMAN MODE ACTIVE - level: full "
        "(fallback sem Node)'; cat \"$CLAUDE_PROJECT_DIR/vendor/caveman/src/rules/"
        'caveman-activate.md"; }',
    }
)

# `vendor/caveman/.claude-plugin/plugin.json`, do upstream. Auditado em
# 2026-08-07 no SHA pinado: sem rede, um único `execFileSync` em forma argv
# (sem shell), escritas confinadas a `~/.claude/.caveman-*` e aos arquivos de
# agente do próprio plugin.
HOOKS_DO_PLUGIN_VENDORIZADO = frozenset(
    {
        'node "${CLAUDE_PLUGIN_ROOT}/src/hooks/caveman-activate.js"',
        'node "${CLAUDE_PLUGIN_ROOT}/src/hooks/caveman-mode-tracker.js"',
    }
)

# `.mcp.json`. O binário, não o argumento.
BINARIOS_MCP_PERMITIDOS = frozenset({"python"})

# Construções que transformam um comando de hook em execução arbitrária.
# `>/dev/null` e `2>&1` NÃO entram: redirecionar não busca nem decodifica nada,
# e o hook legítimo usa os dois.
CONSTRUCOES_PROIBIDAS = (
    (r"\bcurl\b", "baixa da rede"),
    (r"\bwget\b", "baixa da rede"),
    (r"\bnc\b|\bncat\b|\bnetcat\b", "abre socket"),
    (r"Invoke-WebRequest|Invoke-RestMethod", "baixa da rede"),
    (r"\|\s*(sh|bash|zsh|pwsh|powershell)\b", "canaliza para shell"),
    (r"\bbase64\b", "decodifica payload"),
    (r"\beval\b", "avalia string como codigo"),
    (r"\$\(", "substituicao de comando"),
    (r"`", "substituicao de comando"),
    (r"\bchmod\s+\+x", "torna executavel"),
    (r"\bnpm\b|\bnpx\b", "instala pacote"),
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _hook_commands(manifest: dict) -> list[str]:
    return [
        hook["command"]
        for groups in manifest.get("hooks", {}).values()
        for entry in groups
        for hook in entry["hooks"]
    ]


class TestHooksDoProjeto:
    def _commands(self) -> list[str]:
        return _hook_commands(_json(ROOT / ".claude" / "settings.json"))

    def test_todo_hook_esta_na_lista_fechada(self):
        for command in self._commands():
            assert command in HOOKS_DO_PROJETO, (
                "hook novo em .claude/settings.json. Isso executa na maquina de "
                "todo mundo que clonar. Se for intencional, acrescente a string "
                f"exata em HOOKS_DO_PROJETO: {command!r}"
            )

    def test_a_lista_nao_acumula_permissao_morta(self):
        """Entrada que sobra vira autorização que ninguém revisou de novo."""
        assert set(self._commands()) == set(HOOKS_DO_PROJETO)

    def test_nenhum_hook_usa_construcao_de_execucao_arbitraria(self):
        for command in self._commands():
            for pattern, porque in CONSTRUCOES_PROIBIDAS:
                assert not re.search(pattern, command), f"{porque}: {command!r}"

    def test_o_fallback_le_um_arquivo_que_existe_e_e_pinado(self):
        """Um `cat` para caminho inexistente falharia a cada sessão; para um
        caminho fora de `vendor/` sairia do que o `MANIFEST.sha256` cobre."""
        alvo = VENDOR / "caveman/src/rules/caveman-activate.md"
        assert alvo.is_file()
        manifest = (VENDOR / "MANIFEST.sha256").read_text(encoding="utf-8")
        assert "caveman/src/rules/caveman-activate.md" in manifest


class TestHooksDoPluginVendorizado:
    def test_sao_exatamente_os_dois_auditados(self):
        manifest = _json(VENDOR / "caveman" / ".claude-plugin" / "plugin.json")
        assert set(_hook_commands(manifest)) == set(HOOKS_DO_PLUGIN_VENDORIZADO)

    def test_nenhum_deles_usa_construcao_de_execucao_arbitraria(self):
        manifest = _json(VENDOR / "caveman" / ".claude-plugin" / "plugin.json")
        for command in _hook_commands(manifest):
            for pattern, porque in CONSTRUCOES_PROIBIDAS:
                assert not re.search(pattern, command), f"{porque}: {command!r}"

    def test_cada_um_aponta_para_arquivo_que_existe_no_vendor(self):
        manifest = _json(VENDOR / "caveman" / ".claude-plugin" / "plugin.json")
        for command in _hook_commands(manifest):
            rel = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"]+)", command).group(1)
            assert (VENDOR / "caveman" / rel).is_file(), command


class TestServidoresMcp:
    def _servers(self) -> dict:
        return _json(ROOT / ".mcp.json")["mcpServers"]

    def test_so_levantam_binario_da_lista(self):
        for name, server in self._servers().items():
            assert server["command"] in BINARIOS_MCP_PERMITIDOS, name

    def test_nenhum_argumento_carrega_metacaractere_de_shell(self):
        """Servidor MCP é spawn de argv, não linha de shell -- mas um argumento
        com `;` ou `|` denuncia que alguém montou uma linha de comando ali."""
        for name, server in self._servers().items():
            for arg in server.get("args", []):
                assert not re.search(r"[;|&`]|\$\(", arg), f"{name}: {arg!r}"

    def test_variavel_de_ambiente_so_expande_o_que_o_claude_code_define(self):
        permitidas = {"CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"}
        for name, server in self._servers().items():
            for value in server.get("env", {}).values():
                for referida in re.findall(r"\$\{(\w+)\}", str(value)):
                    assert referida in permitidas, f"{name}: {referida}"


class TestSettingsLocalNaoVaza:
    def test_o_settings_local_esta_ignorado_pelo_repositorio(self):
        """`.claude/settings.local.json` é por máquina: guarda o allowlist de
        permissões de quem trabalha ali, com caminhos e comandos.

        Até 2026-08-07 ele só estava protegido pelo gitignore **global** de uma
        máquina (`~/.config/git/ignore`). Em qualquer outro clone, um `git add -A`
        o commitaria -- e o arquivo não é neutro: descreve o que aquele operador
        autorizou a rodar sem confirmação.
        """
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".claude/settings.local.json" in ignore

    def test_e_ele_nao_esta_rastreado(self):
        import subprocess

        tracked = subprocess.run(
            ["git", "ls-files", ".claude/settings.local.json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        assert tracked.strip() == ""
