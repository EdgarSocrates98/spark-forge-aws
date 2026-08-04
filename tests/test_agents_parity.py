import filecmp
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import sync_skills
from scripts.sync_skills import render_agent

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
EXECUTORS = AGENTS / "executors"
NAMES = tuple(sorted(p.stem for p in AGENTS.glob("*.md")))
COORDENADORES = tuple(sorted(AGENTS.glob("*.md")))
EXECUTORES = tuple(sorted(EXECUTORS.glob("*.md")))
PERFIS = COORDENADORES + EXECUTORES


class TestSingleSource:
    def test_agents_dir_is_not_empty(self):
        """Antes este teste fixava os tres nomes literais. Lista fixa obriga a
        editar o teste a cada coordenador novo, e -- pior -- nao pega o caso que
        importa, que e um agente parar de ser espelhado. A byte-identidade dos
        espelhos e o invariante; o nome nao e."""
        assert len(NAMES) >= 3

    def test_each_agent_has_name_description_and_tools(self):
        for name in NAMES:
            text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            assert text.startswith("---")
            assert f"name: {name}" in text
            assert "description:" in text
            assert "tools:" in text

    def test_each_agent_references_the_protocol(self):
        for name in NAMES:
            assert "AGENT_PROTOCOL.md" in (AGENTS / f"{name}.md").read_text(encoding="utf-8")

    def test_copilot_name_drift_is_gone(self):
        """spark-performance-engineer era o nome divergente no Copilot."""
        assert not (ROOT / ".github" / "agents" / "spark-performance-engineer.agent.md").exists()


class TestProtocol:
    def _text(self):
        return (ROOT / "AGENT_PROTOCOL.md").read_text(encoding="utf-8")

    def test_protocol_exists(self):
        assert (ROOT / "AGENT_PROTOCOL.md").is_file()

    def test_declares_the_nine_hard_rules(self):
        text = self._text()
        for marker in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."):
            assert marker in text

    def test_forbids_numbers_without_a_fact(self):
        assert "fact_id" in self._text()

    def test_requires_next_step_before_choosing_a_skill(self):
        assert "next_step" in self._text()

    def test_requires_rules_lookup_instead_of_memory(self):
        assert "rules_lookup" in self._text()

    def test_requires_validate_output_before_presenting(self):
        assert "validate_output" in self._text()

    def test_requires_reporting_unresolved(self):
        assert "unresolved" in self._text()

    def test_requires_explicit_confirmation_for_destructive_maintenance(self):
        text = self._text()
        assert "expire_snapshots" in text
        assert "remove_orphan_files" in text


def secao_nao_faz(texto: str) -> str:
    """O corpo da secao `## Nao faz` de um perfil, ou "" quando ela nao existe.

    Delimitada pela proxima linha de nivel `## ` ou pelo fim do arquivo, para
    que o criterio olhe a secao e nao o arquivo inteiro.
    """
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if linha.strip() == "## Não faz":
            fim = i + 1
            while fim < len(linhas) and not linhas[fim].startswith("## "):
                fim += 1
            return "\n".join(linhas[i + 1 : fim])
    return ""


def falta_fronteira(texto: str) -> str | None:
    """O que falta para o perfil declarar a fronteira, ou None se nao falta nada.

    O criterio tem tres partes, e cada uma existe por um motivo medido:

    1. **A secao `## Nao faz` tem que existir.** E onde este repositorio ja
       escreve fronteira desde a Fase 5b, e ancorar nela e o que impede que uma
       mencao de passagem no corpo conte como declaracao. O
       `iceberg-performance-engineer` tinha uma secao inteira sobre
       `expire_snapshots` nao ter rollback -- conhecimento de dominio, nao
       fronteira -- e um criterio sobre o arquivo inteiro o daria por resolvido.

    2. **Dentro dela, o radical `destrutiv`.** Nomeia o ato. Radical, e nao
       frase canonica, porque um perfil que jamais chega perto de apagar dado e
       um coordenador de Iceberg que recomenda `expire_snapshots` chegam nesta
       fronteira por caminhos diferentes, e a frase honesta de um nao e a do
       outro. Casar frase literal obrigaria os treze a repetir o mesmo texto, que
       e o defeito que este teste existe para nao criar.

    3. **Dentro dela, o radical `confirma`.** Nomeia para onde vai a
       confirmacao. As duas metades falham de formas diferentes, e o modo de
       falha de subagente e mudo nas duas: quem declara so a primeira para sem
       dizer por que; quem declara so a segunda segue sem confirmar. Exigir as
       duas e o que faz o teste pegar meia fronteira.

    O que este criterio nao faz -- e nao tem como fazer -- e verificar sentido.
    Um perfil futuro pode enfileirar as duas palavras sem dizer nada. O que ele
    garante e que ninguem publica perfil sem ter escrito sobre as duas metades no
    unico lugar onde fronteira mora neste repositorio.
    """
    secao = secao_nao_faz(texto)
    if not secao:
        return "sem secao `## Não faz`"
    faltando = [radical for radical in ("destrutiv", "confirma") if radical not in secao]
    return f"`## Não faz` sem {' nem '.join(faltando)}" if faltando else None


class TestFronteiraDeManutencaoDestrutiva:
    """`ask_user_question` e SEMPRE negado a subagente -- e da plataforma, nao de
    configuracao (`knowledge/devin/agents-and-subagents.md`, V-DV-10). Logo a
    regra 10 do `CLAUDE.md` -- confirmacao explicita de escopo e retencao antes
    de manutencao destrutiva -- e inalcancavel de dentro de um subagente.

    Sem a fronteira escrita no proprio perfil, o modo de falha e mudo: o
    subagente segue sem confirmar, ou para sem dizer por que. Nenhum dos dois
    aparece em teste, em log ou em achado -- e e por isso que o invariante e
    sobre o texto do perfil, que e o unico lugar onde a garantia pode viver
    (V-DV-9: nao ha contrato de saida de subagente no Devin).
    """

    def test_o_recorte_cobre_as_duas_familias_de_perfil(self):
        """Guarda contra o teste vazio. Se um rename esvaziasse `PERFIS`, o teste
        seguinte passaria sem olhar nada -- cobertura aparente e o que esta fase
        inteira existe para nao produzir."""
        assert len(COORDENADORES) >= 8
        assert len(EXECUTORES) >= 5

    @pytest.mark.parametrize("perfil", PERFIS, ids=lambda p: p.stem)
    def test_perfil_declara_a_fronteira_de_manutencao_destrutiva(self, perfil):
        problema = falta_fronteira(perfil.read_text(encoding="utf-8"))
        assert problema is None, f"{perfil.relative_to(ROOT)}: {problema}"

    def test_mencao_fora_da_secao_nao_conta(self):
        """O criterio e por secao, e este teste e o que prova. Um perfil pode
        explicar manutencao destrutiva no corpo -- por que `expire_snapshots` nao
        tem rollback, por exemplo -- sem nunca dizer que nao a executa."""
        texto = (
            "## Manutenção destrutiva\n\n"
            "`expire_snapshots` destrutiva não tem rollback; peça confirmação.\n\n"
            "## Não faz\n\nNão julga.\n"
        )
        assert falta_fronteira(texto) == "`## Não faz` sem destrutiv nem confirma"

    def test_meia_fronteira_nao_conta(self):
        """Declarar que nao executa, sem dizer com quem a confirmacao acontece,
        e o perfil que para sem explicar."""
        texto = "## Não faz\n\nNão executa manutenção destrutiva.\n"
        assert falta_fronteira(texto) == "`## Não faz` sem confirma"

    def test_perfil_sem_a_secao_e_pego(self):
        """O caso do perfil novo: ninguem escreveu fronteira nenhuma."""
        assert falta_fronteira("---\nname: novo\n---\n\nCorpo.\n") == "sem secao `## Não faz`"


class TestMirrors:
    def test_sync_check_passes_after_sync(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_skills.py")],
            check=True, capture_output=True, cwd=ROOT,
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_skills.py"), "--check"],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0, result.stdout

    def test_claude_agents_mirror_matches_source(self):
        for name in NAMES:
            dst = ROOT / ".claude" / "agents" / f"{name}.md"
            assert dst.is_file()
            assert filecmp.cmp(AGENTS / f"{name}.md", dst, shallow=False), name

    def test_copilot_agents_mirror_exists_with_agent_md_suffix(self):
        for name in NAMES:
            assert (ROOT / ".github" / "agents" / f"{name}.agent.md").is_file()

    def test_devin_agents_mirror_matches_the_render(self):
        """Era `filecmp.cmp` contra a fonte. Deixou de ser na Task 2: o espelho
        do Devin nao leva `tools:`, entao byte-identidade com a fonte virou o
        DEFEITO que o gate tem que acusar, nao o invariante que ele exige."""
        for name in NAMES:
            src = AGENTS / f"{name}.md"
            dst = ROOT / ".agents" / "agents" / f"{name}.md"
            esperado = render_agent(src.read_bytes().decode("utf-8"), "devin")
            assert dst.read_bytes().decode("utf-8") == esperado, name

    def test_devin_agents_mirror_carries_no_tools_field(self):
        """O que a renderizacao existe para fazer, medido no espelho gravado --
        e nao so na funcao. `tools:` no corpo seria prosa; a checagem olha o
        frontmatter, que termina na segunda cerca."""
        for name in NAMES:
            texto = (ROOT / ".agents" / "agents" / f"{name}.md").read_text(encoding="utf-8")
            frontmatter = texto.split("\n---\n", 1)[0]
            assert "tools:" not in frontmatter, name


class TestGatePegaEspelhoEditadoAMao:
    """A Task 2 trocou o mecanismo do gate: de `filecmp.cmp(src, dst)` para
    comparacao contra `render_agent(src, plataforma_do_alvo)`. Troca de
    mecanismo pode afrouxar o gate sem ninguem perceber -- e gate afrouxado e
    pior que gate nenhum, porque parece cobertura. Estes testes provam que ele
    continua acusando, nas duas familias (agentes e executores) e nas tres
    plataformas.
    """

    ALVOS = (
        ROOT / ".claude" / "agents" / "spark-performance-architect.md",
        ROOT / ".agents" / "agents" / "spark-performance-architect.md",
        ROOT / ".github" / "agents" / "spark-performance-architect.agent.md",
        ROOT / ".claude" / "agents" / "executors" / "sf-inventory.md",
        ROOT / ".agents" / "agents" / "executors" / "sf-inventory.md",
        ROOT / ".github" / "agents" / "executors" / "sf-inventory.md",
    )

    @staticmethod
    def _problemas() -> list[str]:
        return sync_skills.check_agents() + sync_skills.check_executors()

    @pytest.fixture()
    def espelhos_em_dia(self):
        """Baseline: regenera antes e restaura depois, para que um teste que
        mexe no espelho nao contamine `TestNoPlatformKnowledge` nem o proximo
        arquivo da suite."""
        sync_skills.sync_agents()
        sync_skills.sync_executors()
        assert not self._problemas()
        yield
        sync_skills.sync_agents()
        sync_skills.sync_executors()
        assert not self._problemas()

    @pytest.mark.parametrize("alvo", ALVOS, ids=lambda p: str(p.relative_to(ROOT)))
    def test_um_byte_a_mais_no_espelho_vira_divergente(self, alvo, espelhos_em_dia):
        original = alvo.read_bytes()
        try:
            alvo.write_bytes(original + b"x")
            problemas = self._problemas()
        finally:
            alvo.write_bytes(original)
        assert f"DIVERGENTE {alvo}" in problemas, problemas

    def test_copia_literal_da_fonte_no_espelho_do_devin_vira_divergente(
        self, espelhos_em_dia
    ):
        """O teste que o gate ANTIGO nao poderia passar. `filecmp.cmp` exigia
        exatamente isto -- o espelho byte a byte igual a fonte -- e e justamente
        o estado errado hoje: o espelho do Devin sairia com `tools:`.

        E a direcao que o enunciado da Task 2 aponta: igualdade nao pega campo
        que a plataforma exige e a fonte nao tem, nem o contrario.
        """
        src = AGENTS / "spark-performance-architect.md"
        alvo = ROOT / ".agents" / "agents" / "spark-performance-architect.md"
        original = alvo.read_bytes()
        try:
            alvo.write_bytes(src.read_bytes())
            assert filecmp.cmp(src, alvo, shallow=False), "pre-condicao do teste"
            problemas = self._problemas()
        finally:
            alvo.write_bytes(original)
        assert f"DIVERGENTE {alvo}" in problemas, problemas

    def test_espelho_apagado_vira_ausente(self, espelhos_em_dia):
        alvo = ROOT / ".agents" / "agents" / "executors" / "sf-judge.md"
        original = alvo.read_bytes()
        try:
            alvo.unlink()
            problemas = self._problemas()
        finally:
            alvo.write_bytes(original)
        assert f"AUSENTE {alvo}" in problemas, problemas


class TestPlataformaSaiDoAlvo:
    """A plataforma nao e uma quarta lista mantida a mao ao lado das tres de
    espelho: ela e derivada do diretorio-raiz do alvo."""

    def test_cada_raiz_de_espelho_mapeia_para_a_sua_plataforma(self):
        assert sync_skills.platform_for(ROOT / ".agents" / "agents" / "x.md") == "devin"
        assert sync_skills.platform_for(ROOT / ".claude" / "agents" / "x.md") == "claude"
        assert sync_skills.platform_for(ROOT / ".github" / "agents" / "x.agent.md") == "github"

    def test_alvo_fora_das_tres_raizes_falha_alto(self):
        """Espelho novo tem que declarar como se traduz para ele. Default
        silencioso publicaria o arquivo cru na plataforma nova."""
        with pytest.raises(ValueError):
            sync_skills.platform_for(ROOT / ".cursor" / "agents" / "x.md")


class TestNoPlatformKnowledge:
    """Conhecimento nao pode viver em diretorio de plataforma, senao o drift volta."""

    FORBIDDEN = ("threshold:", "runtime_scope:", "retrieved:")

    def test_platform_dirs_carry_no_thresholds_or_sources(self):
        offenders = []
        for platform in (".claude", ".agents", ".github"):
            for path in (ROOT / platform).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for marker in self.FORBIDDEN:
                    if marker in text:
                        offenders.append(f"{path.relative_to(ROOT)}: {marker}")
        assert not offenders, offenders
