import argparse
import json
import re
from pathlib import Path

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _cli_verbs() -> set[str]:
    """Os verbos de topo, lidos do parser REAL e nunca de uma lista à mão.

    Mesma disciplina de `test_agents_md_lists_every_coordinator`, que deriva os
    coordenadores do diretório: lista copiada envelhece sem que nada acuse.
    """
    from sparkforge.adapters.cli import build_parser

    verbs: set[str] = set()
    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            verbs |= set(action.choices)
    return verbs


def _commands_cited(text: str) -> set[str]:
    """Os verbos que um documento cita como comando.

    Duas formas, e só elas: linha de bloco de código que começa com
    `sparkforge `, e trecho inline entre crases. A prosa "a CLI `sparkforge`
    faz tudo" fica de fora de propósito — ali não há verbo citado.
    """
    cited: set[str] = set()
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("sparkforge "):
            cited.add(stripped.split()[1])
    cited |= set(re.findall(r"`sparkforge\s+([a-z][a-z0-9-]*)", text))
    return cited


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


class TestReadme:
    README = None

    @classmethod
    def setup_class(cls):
        cls.README = _read("README.md")

    def test_documents_the_four_distribution_channels(self):
        for channel in ("Claude Code", "MCP", "pip", "markdown"):
            assert channel.lower() in self.README.lower(), channel

    def test_documents_devin_and_copilot_as_mcp_clients(self):
        assert "Devin" in self.README
        assert "Copilot" in self.README

    def test_documents_the_cli(self):
        assert "sparkforge" in self.README
        assert "runtime detect" in self.README
        assert "analyze pyspark" in self.README
        assert "judge" in self.README
        assert "next-step" in self.README

    def test_documents_the_handoff_flow(self):
        assert "handoff" in self.README.lower()
        assert "git add" in self.README
        assert ".sparkforge" in self.README

    def test_documents_why_artifacts_are_not_committed(self):
        assert "artifacts/**" in self.README or "artifacts/" in self.README
        assert "sha256" in self.README.lower()

    def test_documents_pip_install(self):
        """O canal pip da secao 9 so vale se estiver documentado; agente que
        nao sabe instalar nao instala."""
        assert "pip install sparkforge-aws" in self.README

    def test_documents_that_the_installed_package_carries_the_catalog(self):
        lowered = self.README.lower()
        assert "catálogo" in lowered or "catalogo" in lowered
        assert "knowledge" in lowered

    def test_readme_documents_the_playbook(self):
        assert "sparkforge playbook" in self.README

    def test_readme_documents_the_two_agent_layers(self):
        lowered = self.README.lower()
        assert "coordenador" in lowered
        assert "executor" in lowered


class TestGuia:
    GUIA = None

    @classmethod
    def setup_class(cls):
        cls.GUIA = _read("GUIA_DE_USO.md")

    def test_documents_sparkforge_resume(self):
        assert "sparkforge resume" in self.GUIA

    def test_documents_what_is_committed_versus_not(self):
        lowered = self.GUIA.lower()
        assert "committ" in lowered
        assert "artifacts" in lowered or "artefatos" in lowered

    def test_documents_the_no_mcp_no_python_fallback(self):
        assert "rules/catalog" in self.GUIA

    def test_every_command_the_guide_teaches_is_a_real_verb(self):
        """O guia não é coberto por `scripts/sync_skills.py --check`, então o que
        o impede de envelhecer é este teste.

        Ele não exige que o guia documente TODOS os verbos — documentar
        `collect` ou `rules` é decisão editorial, não invariante. Ele exige o
        contrário, que é o que de fato quebra o leitor: verbo citado no guia que
        a CLI não tem. Renomear ou remover um verbo passa a acusar aqui.
        """
        cited = _commands_cited(self.GUIA)
        assert cited, "o guia deixou de citar qualquer comando `sparkforge`"
        unknown = cited - _cli_verbs()
        assert not unknown, f"o guia ensina verbo que a CLI não tem: {sorted(unknown)}"

    def test_the_conclusion_criteria_name_a_producing_verb(self):
        """Item de conclusão sem verbo produtor é a prosa que `SF-FVAL` e
        `SF-BENCH` existem para acusar no job do usuário.

        A §8 listava "benchmark" e "validação funcional" como texto solto, sem
        dizer o que os produz — o motor cobrando do usuário o que o próprio guia
        não fazia. Os dois itens agora nomeiam o verbo, e este teste é o que
        impede a regressão.
        """
        criterio = _section(self.GUIA, "## 8. Critério de conclusão")
        assert "sparkforge benchmark" in criterio
        assert "sparkforge funcval plan" in criterio
        assert "sparkforge funcval compare" in criterio

    def test_documents_the_two_funcval_verbs_where_it_teaches_commands(self):
        """`funcval` é a entrega da Fase 4c, e o guia é o único documento de uso
        que um operador lê antes de abrir o repositório. Os dois verbos precisam
        aparecer com os argumentos que os tornam utilizáveis."""
        assert "funcval plan" in self.GUIA
        assert "funcval compare" in self.GUIA
        # `--out` obrigatório no `plan` e ausente no `compare` é a assimetria que
        # mais confunde; o guia tem de declarar as duas metades.
        assert "--out .sparkforge/facts_funcval_plan.json" in self.GUIA
        assert "next_cursor" in self.GUIA


class TestPromptMestre:
    PROMPT = None

    @classmethod
    def setup_class(cls):
        cls.PROMPT = _read("PROMPT_INICIAL_MESTRE.md")

    def test_requires_opening_a_case(self):
        assert "case open" in self.PROMPT or "abrir o case" in self.PROMPT.lower()

    def test_references_agent_protocol(self):
        assert "AGENT_PROTOCOL.md" in self.PROMPT

    def test_requires_runtime_detection_first(self):
        assert "SF-ENV-001" in self.PROMPT

    def test_requires_fact_id_traceability(self):
        assert "fact_id" in self.PROMPT


class TestAgentsMd:
    AGENTS = None

    @classmethod
    def setup_class(cls):
        cls.AGENTS = _read("AGENTS.md")

    def test_references_agent_protocol_and_fact_finding_model(self):
        assert "AGENT_PROTOCOL.md" in self.AGENTS
        assert "Fact" in self.AGENTS
        assert "Finding" in self.AGENTS

    def test_agents_md_lists_every_coordinator(self):
        from pathlib import Path

        for path in Path(ROOT / "agents").glob("*.md"):
            assert path.stem in self.AGENTS, path.stem


class TestSourcesMd:
    SOURCES = None

    @classmethod
    def setup_class(cls):
        cls.SOURCES = _read("SOURCES.md")

    def test_documents_field_heuristic_origin(self):
        assert "field-heuristic" in self.SOURCES

    def test_lists_unreconfirmed_items(self):
        assert "2026-07-29" in self.SOURCES


class TestManifest:
    def test_version_matches_the_package(self):
        """A concordancia entre as quatro fontes vive em
        `tests/test_package_importable.py`. Aqui so se garante que o manifesto
        nao ficou para tras do pacote."""
        import sparkforge

        manifest = json.loads(_read("manifest.json"))
        assert manifest["version"] == sparkforge.__version__

    def test_tools_list_equals_the_real_tools_keys(self):
        manifest = json.loads(_read("manifest.json"))
        assert set(manifest["tools"]) == set(TOOLS.keys())
        assert len(manifest["tools"]) == len(TOOLS)

    def test_skills_list_equals_the_skills_on_disk(self):
        """O irmao de `test_tools_list_equals_the_real_tools_keys`, que faltava.

        A lista de tools e derivada de `TOOLS` desde a Fase 0 e nunca divergiu.
        A de skills nao tinha teste nenhum, e divergiu DUAS vezes sem que nada
        acendesse: `review-emr-cluster` ficou de fora na Fase 5b e
        `review-data-validation` na 5c -- a segunda omissao aconteceu com a
        primeira ainda aberta, que e a assinatura de invariante ausente e nao de
        descuido.

        Skill que existe e nao e declarada no manifesto e invisivel para quem le
        o manifesto em vez do disco, que e exatamente o caso de uma plataforma
        que instala o pacote: o mesmo modo de falha que a Fase 3a corrigiu no
        wheel, um nivel acima.
        """
        manifest = json.loads(_read("manifest.json"))
        on_disk = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}
        assert set(manifest["skills"]) == on_disk

    def test_rule_count_equals_the_real_catalog(self):
        """Este numero ja apodreceu tres vezes.

        Foi 59 (43 diagnosticas + 16 rotas somadas, contagem da Fase 0) e 43
        (anterior a Fase 2 desbloquear o catalogo), enquanto `load_catalog()`
        devolvia outra coisa. Duas dessas vezes o valor errado estava no
        `README.md`, que um agente autonomo le como verdade; a terceira estava
        aqui no manifesto, onde nenhum teste olhava.

        `load_catalog()` exclui `routing.yaml` por construcao, entao o numero
        certo e o de regras de DIAGNOSTICO -- as rotas se contam a parte.
        """
        from sparkforge.rules.loader import load_catalog

        manifest = json.loads(_read("manifest.json"))
        assert manifest["knowledge_base"]["rule_count"] == len(load_catalog())
