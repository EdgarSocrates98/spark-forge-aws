"""O renderizador por plataforma de `scripts/sync_skills.py`.

Fundamento medido: `knowledge/devin/agents-and-subagents.md` (retrieved
2026-08-04), vetos `V-DV-2`, `V-DV-3` e `V-DV-8`. Spec: D-1, D-2 e D-3 de
`docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md`.
"""
from pathlib import Path

import pytest

from scripts.sync_skills import render_agent

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"
PERFIS = tuple(sorted(AGENTS.glob("*.md")) + sorted(EXECUTORS.glob("*.md")))


SOURCE = """---
name: emr-infra-reviewer
description: Use quando o Spark roda em EMR on EC2.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - review-emr-cluster
rule_areas: [SF-EMR]
executors: [sf-inventory]
---

Corpo do perfil.
"""


# `tools:` em forma de bloco. Nenhum dos treze perfis reais usa esta forma hoje
# (medido), mas um regex ingenuo que apagasse so a linha `tools:` deixaria
# `  - Read` orfao e quebraria o YAML do espelho no dia em que alguem escrevesse
# assim. O teste fixa a forma antes de ela existir.
SOURCE_TOOLS_EM_BLOCO = """---
name: perfil-em-bloco
description: Frontmatter com tools em forma de lista.
tools:
  - Read
  - Grep
  - Bash
skills:
  - review-emr-cluster
rule_areas: [SF-EMR]
---

Corpo do perfil.
"""


def test_claude_recebe_o_arquivo_inalterado():
    assert render_agent(SOURCE, platform="claude") == SOURCE


def test_github_recebe_o_arquivo_inalterado():
    assert render_agent(SOURCE, platform="github") == SOURCE


def test_devin_perde_o_campo_tools():
    """O mapeamento de valores de `tools:` NAO esta documentado (V-DV-8 da
    pesquisa). Chute em campo de permissao concede ou nega errado, e nos dois
    sentidos o erro e caro. Omitido, o subagente herda o que o harness da."""
    out = render_agent(SOURCE, platform="devin")
    assert "tools:" not in out
    assert "name: emr-infra-reviewer" in out
    assert "rule_areas: [SF-EMR]" in out
    assert "Corpo do perfil." in out


def test_devin_nunca_ganha_model():
    """O default resolve por roteador no spawn e o admin da org sobrescreve.
    Escrever `model:` seria fingir controle sobre o que o harness decide."""
    assert "model:" not in render_agent(SOURCE, platform="devin")


def test_render_e_idempotente():
    once = render_agent(SOURCE, platform="devin")
    assert render_agent(once, platform="devin") == once


class TestFormaDoCampo:
    def test_devin_leva_as_continuacoes_de_tools_em_bloco(self):
        """Regex ingenuo deixaria `  - Read` orfao, e o frontmatter do espelho
        deixaria de ser YAML valido."""
        out = render_agent(SOURCE_TOOLS_EM_BLOCO, platform="devin")
        assert "tools:" not in out
        assert "  - Read" not in out
        assert "  - Grep" not in out
        assert "  - Bash" not in out

    def test_bloco_de_tools_nao_leva_junto_a_lista_de_skills(self):
        """`skills:` vem logo depois e tambem e lista indentada. Se a remocao
        nao parar na proxima chave de topo, ela come a chave seguinte inteira."""
        out = render_agent(SOURCE_TOOLS_EM_BLOCO, platform="devin")
        assert "skills:\n  - review-emr-cluster\n" in out
        assert "rule_areas: [SF-EMR]" in out

    def test_forma_em_bloco_tambem_e_idempotente(self):
        once = render_agent(SOURCE_TOOLS_EM_BLOCO, platform="devin")
        assert render_agent(once, platform="devin") == once


class TestCamposQueSaoNossos:
    """`skills:`, `rule_areas:` e `executors:` sao deste repositorio. O Devin
    ignora campo que nao conhece; removê-los perderia a informacao que os
    invariantes das fases anteriores usam."""

    def test_skills_rule_areas_e_executors_sobrevivem(self):
        out = render_agent(SOURCE, platform="devin")
        assert "skills:\n  - review-emr-cluster\n" in out
        assert "rule_areas: [SF-EMR]" in out
        assert "executors: [sf-inventory]" in out


class TestPerfisReais:
    """Os treze arquivos que o espelho do Devin vai receber na Task 2."""

    def test_o_corpus_tem_treze_perfis(self):
        assert len(PERFIS) == 13

    def test_passthrough_devolve_byte_a_byte(self):
        for perfil in PERFIS:
            texto = perfil.read_text(encoding="utf-8")
            for plataforma in ("claude", "github"):
                assert render_agent(texto, platform=plataforma) == texto, perfil.name

    def test_devin_perde_tools_em_todos(self):
        for perfil in PERFIS:
            out = render_agent(perfil.read_text(encoding="utf-8"), platform="devin")
            assert "tools:" not in out, perfil.name

    def test_devin_nao_ganha_model_em_nenhum(self):
        for perfil in PERFIS:
            out = render_agent(perfil.read_text(encoding="utf-8"), platform="devin")
            assert "model:" not in out, perfil.name

    def test_devin_so_perde_a_linha_de_tools(self):
        """A remocao e cirurgica: o resto do arquivo sai igual, linha a linha.
        Round-trip de YAML reordenaria chaves e produziria diff onde nao houve
        mudanca -- e o gate da Task 2 viraria ruido."""
        for perfil in PERFIS:
            texto = perfil.read_text(encoding="utf-8")
            out = render_agent(texto, platform="devin")
            antes = texto.splitlines(keepends=True)
            removidas = [linha for linha in antes if linha not in out.splitlines(keepends=True)]
            assert out == "".join(
                linha for linha in antes if not linha.startswith("tools:")
            ), (perfil.name, removidas)

    def test_o_corpo_sobrevive_inteiro(self):
        for perfil in PERFIS:
            texto = perfil.read_text(encoding="utf-8")
            corpo = texto.split("\n---\n", 1)[1]
            assert corpo in render_agent(texto, platform="devin"), perfil.name

    def test_render_dos_perfis_reais_e_idempotente(self):
        for perfil in PERFIS:
            once = render_agent(perfil.read_text(encoding="utf-8"), platform="devin")
            assert render_agent(once, platform="devin") == once, perfil.name


class TestBordas:
    def test_plataforma_desconhecida_falha_alto(self):
        """Erro de digitacao em nome de plataforma nao pode virar passthrough
        silencioso: o espelho sairia com `tools:` e ninguem saberia."""
        with pytest.raises(ValueError):
            render_agent(SOURCE, platform="cursor")

    def test_texto_sem_frontmatter_sai_inalterado(self):
        texto = "Sem frontmatter nenhum.\ntools: Read\n"
        assert render_agent(texto, platform="devin") == texto

    def test_tools_no_corpo_nao_e_tocado(self):
        """Fora do frontmatter, `tools:` e prosa. Remover ali seria editar o
        metodo do perfil."""
        texto = SOURCE + "\nA secao abaixo cita tools: Read no corpo.\n"
        out = render_agent(texto, platform="devin")
        assert "A secao abaixo cita tools: Read no corpo." in out

    def test_fim_de_linha_e_preservado(self):
        """O espelho e comparado byte a byte pelo gate; normalizar CRLF para LF
        produziria DIVERGENTE em toda regeneracao numa arvore com autocrlf."""
        crlf = SOURCE.replace("\n", "\r\n")
        out = render_agent(crlf, platform="devin")
        assert "\r\n" in out
        assert "\n" not in out.replace("\r\n", "")
        assert "tools:" not in out
