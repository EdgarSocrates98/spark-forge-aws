from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("claude_code", "devin_desktop", "devin_cli", "codex", "copilot_ci")
MECHANISMS = ("mcp", "cli", "files", "playbook")


def manifest():
    return yaml.safe_load((ROOT / "parity.yaml").read_text(encoding="utf-8"))


class TestManifestShape:
    def test_exists(self):
        assert (ROOT / "parity.yaml").is_file()

    def test_declares_the_five_platforms(self):
        assert tuple(manifest()["platforms"]) == PLATFORMS

    def test_declares_the_four_mechanisms(self):
        assert tuple(manifest()["mechanisms"]) == MECHANISMS


class TestEveryCapabilityHasAPathEverywhere:
    def test_no_capability_is_missing_a_platform(self):
        gaps = []
        for capability in manifest()["capabilities"]:
            for platform in PLATFORMS:
                if not capability["platforms"].get(platform):
                    gaps.append(f"{capability['name']} sem {platform}")
        assert not gaps, gaps

    def test_every_declared_mechanism_is_known(self):
        for capability in manifest()["capabilities"]:
            for platform, mechanisms in capability["platforms"].items():
                for mechanism in mechanisms:
                    assert mechanism in MECHANISMS, (capability["name"], platform, mechanism)

    def test_every_capability_reaches_the_files_rung(self):
        """Terceiro degrau: sem MCP e sem Python, o conhecimento ainda chega."""
        for capability in manifest()["capabilities"]:
            for platform in PLATFORMS:
                assert "files" in capability["platforms"][platform], capability["name"]


class TestManifestMatchesReality:
    def test_every_declared_tool_exists_in_the_tool_surface(self):
        from sparkforge.adapters.tools import TOOLS

        for capability in manifest()["capabilities"]:
            for tool in capability.get("tools") or []:
                assert tool in TOOLS, tool

    def test_every_declared_cli_verb_is_reachable(self):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        subparsers = next(
            a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
        )
        available = set(subparsers.choices)
        for capability in manifest()["capabilities"]:
            for verb in capability.get("cli") or []:
                assert verb.split()[0] in available, verb

    def test_every_declared_knowledge_file_exists(self):
        for capability in manifest()["capabilities"]:
            for path in capability.get("knowledge") or []:
                assert (ROOT / path).is_file(), path

    def test_every_phase_zero_tool_appears_in_some_capability(self):
        """Tool que nao aparece no manifesto e capacidade nao declarada."""
        from sparkforge.adapters.tools import TOOLS

        declared = {t for c in manifest()["capabilities"] for t in (c.get("tools") or [])}
        assert set(TOOLS) - declared == set()


class TestNoCliVerbIsAnUndeclaredMcpGap:
    """A reciproca de `TestManifestMatchesReality`: nao basta cada verbo
    DECLARADO em parity.yaml existir de verdade -- todo verbo que a CLI real
    (`build_parser()`) de fato expoe precisa aparecer em alguma capacidade do
    manifesto, e essa capacidade precisa ter pelo menos um tool MCP, a menos
    que a ausencia esteja documentada e justificada aqui. Sem este teste, um
    verbo novo pode ser adicionado a `cli.py` sem que nada perceba que ficou
    fora do alcance do MCP -- exatamente a classe de drift que esta fase
    existe para fechar."""

    ALLOWED_CLI_ONLY = {
        # `resume` e `handoff` sao a MESMA capacidade em parity.yaml (o mesmo
        # payload de `_core.resume_case`): `handoff` so acrescenta a escrita
        # de um markdown em disco para commit no git, o que nao faz sentido
        # para um cliente MCP -- ele ja recebe o payload estruturado direto
        # via `sparkforge_resume`, sem precisar de um artefato em arquivo.
        "handoff": (
            "mesma capacidade que 'resume'; escreve markdown em disco, sem uso "
            "para um cliente MCP."
        ),
        # CLI `validate` valida um ARQUIVO de findings (JSON no disco);
        # `sparkforge_validate_output` valida um finding inline -- mesma
        # `_core.validate_output` por baixo, granularidade de I/O diferente
        # porque um cliente MCP ja tem o finding em mao, nunca um arquivo no
        # disco do lado do host MCP.
        "validate": (
            "mesma _core.validate_output que sparkforge_validate_output, so que "
            "sobre arquivo."
        ),
    }

    def _leaf_cli_verbs(self):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        sub = next(
            a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
        )
        leaves = []
        for name, subparser in sub.choices.items():
            nested = next(
                (
                    a
                    for a in subparser._actions  # noqa: SLF001
                    if hasattr(a, "choices") and a.choices
                ),
                None,
            )
            if nested:
                leaves.extend(f"{name} {leaf}" for leaf in sorted(nested.choices))
            else:
                leaves.append(name)
        return leaves

    def test_every_cli_verb_has_an_mcp_tool_or_a_declared_reason(self):
        from sparkforge.adapters.tools import TOOLS

        declared_cli_to_tools: dict[str, set[str]] = {}
        for capability in manifest()["capabilities"]:
            tools = set(capability.get("tools") or [])
            for verb in capability.get("cli") or []:
                declared_cli_to_tools.setdefault(verb, set()).update(tools)

        gaps = []
        for verb in self._leaf_cli_verbs():
            if verb in self.ALLOWED_CLI_ONLY:
                continue
            tools = declared_cli_to_tools.get(verb) or set()
            if not (tools & set(TOOLS)):
                gaps.append(verb)
        assert not gaps, gaps


class TestOrchestrationParity:
    """A capacidade que faltava no manifesto.

    Os 3 agentes eram espelhados com byte-identidade travada, mas nada
    verificava que "coordenar investigacao" tinha caminho por plataforma --
    exatamente o que o gate da secao 8.4 da Fase 0 existe para pegar. Agentes
    escaparam dele porque agente nao era mecanismo declarado.
    """

    def test_codex_is_a_declared_platform(self):
        assert "codex" in manifest()["platforms"]

    def test_playbook_is_a_declared_mechanism(self):
        assert "playbook" in manifest()["mechanisms"]

    def test_coordination_capability_exists(self):
        names = [c["name"] for c in manifest()["capabilities"]]
        assert any("coorden" in n.lower() for n in names), names

    def test_coordination_reaches_every_platform(self):
        capability = next(
            c for c in manifest()["capabilities"] if "coorden" in c["name"].lower()
        )
        for platform in manifest()["platforms"]:
            assert capability["platforms"].get(platform), platform

    def test_only_claude_code_claims_subagent_dispatch(self):
        """Despacho de subagente e capacidade de HARNESS. Declarar para outra
        plataforma seria afirmar paridade que nao existe -- o defeito exato do
        transporte HTTP na Fase 1, que `parity.yaml` afirmava e nenhum teste
        tocava."""
        capability = next(
            c for c in manifest()["capabilities"] if "coorden" in c["name"].lower()
        )
        for platform, mechanisms in capability["platforms"].items():
            if platform != "claude_code":
                assert "subagent" not in mechanisms, platform


class TestNoRuntimeAxisIsAnUndeclaredFlagGap:
    """Paridade um nivel abaixo do verbo: a SUPERFICIE DE CADA VERBO.

    `TestNoCliVerbIsAnUndeclaredMcpGap` pergunta se todo verbo alcanca o MCP, e
    nao percebeu que `--emr` faltava nos tres verbos que aceitam runtime -- o
    eixo `emr` entrou em `RuntimeContext` na Fase 5b e ficou so como saida.
    Assimetria de superficie e o tipo de coisa que ninguem percebe ate
    precisar: quem SABE a release e nao tem dump nao tinha como declara-la, nem
    pela CLI nem pelo MCP.

    O conjunto esperado e derivado do proprio `RuntimeContext`, nunca de uma
    lista literal aqui: eixo novo no contexto passa a exigir flag e propriedade
    de tool no mesmo commit, em vez de virar a mesma divida de novo.
    """

    # verbo da CLI -> tool MCP que espelha a mesma funcao de `_core`.
    VERBS = {
        ("judge",): "sparkforge_judge",
        ("case", "open"): "sparkforge_case_open",
        ("runtime", "detect"): "sparkforge_runtime_detect",
    }

    def _runtime_axes(self):
        from sparkforge.findings.models import RuntimeContext

        # `detected_from` e `divergences` sao SAIDA -- o que a deteccao concluiu
        # sobre si mesma --, nunca entrada declaravel.
        return set(RuntimeContext().to_dict()) - {"detected_from", "divergences"}

    def _subparser(self, path):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        for name in path:
            sub = next(
                a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
            )
            parser = sub.choices[name]
        return parser

    def test_every_runtime_axis_is_declarable_on_the_cli(self):
        axes = self._runtime_axes()
        for path in self.VERBS:
            flags = {
                option.lstrip("-")
                for action in self._subparser(path)._actions  # noqa: SLF001
                for option in action.option_strings
            }
            assert axes <= flags, (" ".join(path), sorted(axes - flags))

    def test_every_runtime_axis_is_declarable_over_mcp(self):
        from sparkforge.adapters.tools import TOOLS

        axes = self._runtime_axes()
        for tool in self.VERBS.values():
            properties = set(TOOLS[tool]["inputSchema"]["properties"])
            assert axes <= properties, (tool, sorted(axes - properties))

    def test_the_cli_and_the_tool_expose_the_same_axes(self):
        """Nao basta os dois cobrirem o contexto: eles precisam cobrir o MESMO
        conjunto. Um eixo so na CLI e a assimetria de novo, virada do avesso."""
        from sparkforge.adapters.tools import TOOLS

        axes = self._runtime_axes()
        for path, tool in self.VERBS.items():
            flags = {
                option.lstrip("-")
                for action in self._subparser(path)._actions  # noqa: SLF001
                for option in action.option_strings
            } & axes
            properties = set(TOOLS[tool]["inputSchema"]["properties"]) & axes
            assert flags == properties, (" ".join(path), tool)


class TestOsControlesDeGateChegamAosTresAdaptadores:
    """A mesma assimetria da Fase 5b (`--emr` so na saida), aplicada ao rigor de
    gate: uma capacidade que exista na CLI e nao no MCP e uma decisao que um
    cliente MCP nao consegue tomar, e ninguem percebe ate precisar.

    O mapa e explicito porque os nomes divergem de proposito -- a CLI ja chamava
    `--facts` o que a tool chama `facts_path` desde a Fase 0, e alinhar um dos
    dois agora quebraria chamada existente.
    """

    OPEN = {"strict-gates": "strict_gates"}
    UPDATE = {
        "override-gate": "override_gate",
        "reason": "reason",
        "facts": "facts_path",
    }

    def _flags(self, path):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        for name in path:
            sub = next(
                a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
            )
            parser = sub.choices[name]
        return {
            option.lstrip("-")
            for action in parser._actions  # noqa: SLF001
            for option in action.option_strings
        }

    def _properties(self, tool):
        from sparkforge.adapters.tools import TOOLS

        return set(TOOLS[tool]["inputSchema"]["properties"])

    def test_case_open_declara_o_rigor_nos_dois(self):
        flags = self._flags(("case", "open"))
        properties = self._properties("sparkforge_case_open")
        for flag, prop in self.OPEN.items():
            assert flag in flags, flag
            assert prop in properties, prop

    def test_case_update_declara_override_motivo_e_evidencia_nos_dois(self):
        flags = self._flags(("case", "update"))
        properties = self._properties("sparkforge_case_update")
        for flag, prop in self.UPDATE.items():
            assert flag in flags, flag
            assert prop in properties, prop

    def test_o_core_e_a_terceira_ponta_e_expoe_os_mesmos_parametros(self):
        """CLI e MCP so podem oferecer o que `_core` aceita: se o parametro
        sumir de la, os dois quebram juntos, e este teste falha primeiro."""
        import inspect

        from sparkforge.adapters import _core

        assert "strict_gates" in inspect.signature(_core.case_open).parameters
        update = inspect.signature(_core.case_update).parameters
        for name in ("override_gate", "reason", "facts_path"):
            assert name in update, name


class TestNoRuntimeAxisIsAnUndeclaredProducerGap:
    """A mesma assimetria, virada para o outro lado: eixo com FLAG e sem
    PRODUTOR.

    `TestNoRuntimeAxisIsAnUndeclaredFlagGap` cobra a entrada declarada -- flag e
    propriedade de tool -- para cada eixo de `RuntimeContext`. Ela nao ve o
    inverso, que e a divida que este teste fecha: `athena` tinha flag nos tres
    verbos e nas tres tools desde sempre, `athena.workgroup` carregava
    `measures.engine_version` com artefato e sha256, e `_runtime_reading` nao
    lia -- o eixo so era preenchivel por alguem digitar o numero. A Fase 5a
    esvaziou o `runtime_scope` das cinco regras `SF-ATH` exatamente por isso: um
    guarda que falha fechado em TODO runtime nao guarda nada.

    Assimetria assim nao aparece em teste de comportamento: cada teste de
    deteccao prova o eixo que ele exercita, e o eixo que ninguem exercita passa
    por nao existir em lugar nenhum. So um invariante derivado a pega.

    COMO O PRODUTOR E DERIVADO, e por que assim. `_runtime_reading` e o unico
    lugar do projeto onde um fact vira leitura de runtime; tudo depois dele
    (`runtime_sources_from_facts`, `detect_runtime`) so agrega o que ele
    devolveu. Entao a pergunta "existe produtor para o eixo X?" e a pergunta
    "algum ramo de `_runtime_reading` nomeia uma chave crua de X?", e a resposta
    sai do AST da propria funcao -- nunca de uma lista mantida aqui, que viraria
    a mesma divida um nivel acima.

    As duas fronteiras da leitura de AST, declaradas para que ninguem confie
    nela mais do que ela merece:

    - Mencao nao e prova de retorno. Um ramo que nomeasse `athena_version` so
      para RECUSAR ainda contaria como produtor. E alarme de fumaca, nao
      certificado.
    - Chave montada em tempo de execucao e invisivel. Foi por isso que
      `f"{component}_version"` virou dict literal no ramo de `emr.application`,
      no mesmo commit deste teste: sem essa troca, `iceberg` so era visto pelo
      `"iceberg"` solto da tupla de guarda -- passava por acidente, e um
      refactor que movesse a tupla para fora da funcao quebraria o invariante
      sem quebrar o codigo.

    SEM EXCECAO DECLARADA, e isso e resultado medido, nao omissao. `glue` e
    `emr` sao identidade de plataforma e poderiam precisar de regra propria --
    mas os dois TEM produtor (`tf.attribute`/`glue_version` e
    `emr.cluster`/`emr_release`), entao a regra geral vale para os seis eixos
    sem ressalva. Declarar excecao que nao e exercida seria criar a permissao
    antes do caso, no padrao oposto ao de `AREA_MAY_VANISH_WHEN` em
    `tests/test_rule_scope_by_nature.py`, que existe porque `SF-GLUE` de fato
    some.
    """

    def _axes(self):
        from sparkforge.findings.models import RuntimeContext

        return set(RuntimeContext().to_dict()) - {"detected_from", "divergences"}

    def _raw_keys_by_axis(self):
        """eixo -> chaves cruas que `detect_runtime` aceita para ele.

        Derivado de `_DIRECT_KEYS`/`_PLATFORM_KEYS`, que sao o vocabulario que
        `_collect` de fato le. Eixo sem chave crua nenhuma nao tem como ser
        alimentado por fonte alguma, e cai como gap -- que e o veredito certo.
        """
        from sparkforge.facts.runtime_detect import _DIRECT_KEYS, _PLATFORM_KEYS

        merged = {**_PLATFORM_KEYS, **_DIRECT_KEYS}
        return {axis: set(merged.get(axis, ())) for axis in self._axes()}

    def _named_in_the_reader(self):
        """Todo literal de texto do CORPO de `_runtime_reading`.

        Escopo na funcao, e nao no modulo, de proposito: `build_runtime` monta
        um dict com TODAS as chaves cruas para as flags da CLI, e varrer o
        modulo faria todo eixo parecer produzido pelo simples fato de existir
        uma flag -- o teste provaria a si mesmo. O docstring fica de fora pelo
        mesmo motivo: prosa citando uma chave nao alimenta ninguem.
        """
        import ast
        import inspect
        import textwrap

        from sparkforge.adapters import _core

        tree = ast.parse(textwrap.dedent(inspect.getsource(_core._runtime_reading)))  # noqa: SLF001
        function = tree.body[0]
        body = function.body
        if ast.get_docstring(function) is not None:
            body = body[1:]

        return {
            node.value
            for statement in body
            for node in ast.walk(statement)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }

    def test_every_runtime_axis_has_a_producer(self):
        named = self._named_in_the_reader()
        gaps = sorted(
            axis for axis, keys in self._raw_keys_by_axis().items() if not (keys & named)
        )
        assert not gaps, (
            f"eixo de RuntimeContext sem produtor em _runtime_reading: {gaps}. "
            f"Ha flag para declara-lo e nenhum extrator o alimenta -- o guarda "
            f"runtime_scope desse eixo falha fechado em todo runtime."
        )

    def test_the_flag_surface_and_the_producer_surface_cover_the_same_axes(self):
        """Os dois lados TEM que fechar no mesmo conjunto. Produtor sem flag e a
        assimetria original (`--emr`, commit `b9c2c87`); flag sem produtor e
        esta. Sao a mesma falha em espelho, e nenhuma sobrevive a este par."""
        from sparkforge.adapters.tools import TOOLS

        axes = self._axes()
        named = self._named_in_the_reader()
        produced = {axis for axis, keys in self._raw_keys_by_axis().items() if keys & named}
        declared = set(TOOLS["sparkforge_judge"]["inputSchema"]["properties"]) & axes

        assert produced == declared, sorted(produced ^ declared)

    def test_the_derivation_is_not_vacuous(self):
        """Um invariante derivado por AST falha para o lado errado quando a
        derivacao para de achar qualquer coisa: `getsource` mudando de forma,
        `_runtime_reading` sendo renomeada, o corpo virando uma tabela de
        despacho. Ai `named` fica vazio, `produced` fica vazio, e o teste acima
        vira `set() == set()` -- verde permanente sobre nada. Esta e a linha que
        transforma esse modo de falha silencioso em falha barulhenta."""
        named = self._named_in_the_reader()

        assert "spark.runtime_version" in named, sorted(named)
        assert "athena.workgroup" in named, sorted(named)


class TestNoPrecedenceSourceIsAnUndeclaredProducerGap:
    """A terceira face da mesma assimetria: FONTE declarada e sem produtor.

    `TestNoRuntimeAxisIsAnUndeclaredProducerGap` cobra produtor por EIXO de
    `RuntimeContext` -- spark, python, iceberg, athena, glue, emr. Ela nao ve o
    outro eixo da mesma tabela: a FONTE. `_PRECEDENCE` e um vocabulario fechado
    de nomes de fonte, e um nome que ninguem emite nao ranqueia nada -- e
    superficie que parece existir, no sentido exato do `pyspark.unresolved`.

    `requirements` era esse nome, e sobreviveu quatro fases: `knowledge/glue/
    runtime-matrix.md` secao 5 lista `requirements.txt`/`pyproject.toml` como a
    fonte de MENOR confiabilidade ("indica intencao, nao runtime"), a
    precedencia foi desenhada com ela no fim por isso, e nenhum modulo de
    `sparkforge/facts/` le manifesto de dependencia. Saiu da tupla em vez de
    ganhar extrator -- ver o comentario de `_PRECEDENCE`, que declara a decisao
    e o que teria que ser verdade para ela voltar.

    O MESMO ALARME DE FUMACA, e as mesmas duas fronteiras: mencao nao e prova de
    emissao, e nome de fonte montado em tempo de execucao e invisivel. Os dois
    unicos lugares do projeto que nomeiam fonte sao `_runtime_reading` (o que os
    extratores observaram) e `build_runtime` (a fonte `cli`, que e a flag
    digitada); varrer o modulo inteiro faria o `_PRECEDENCE` provar a si mesmo.
    """

    def _emitted_sources(self):
        import ast
        import inspect
        import textwrap

        from sparkforge.adapters import _core

        named: set[str] = set()
        for function in (_core._runtime_reading, _core.build_runtime):  # noqa: SLF001
            tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
            node = tree.body[0]
            body = node.body[1:] if ast.get_docstring(node) is not None else node.body
            named |= {
                child.value
                for statement in body
                for child in ast.walk(statement)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
        return named

    def test_every_declared_source_has_someone_that_emits_it(self):
        from sparkforge.facts.runtime_detect import _PRECEDENCE

        named = self._emitted_sources()
        gaps = sorted(source for source in _PRECEDENCE if source not in named)
        assert not gaps, (
            f"fonte declarada em _PRECEDENCE que ninguem emite: {gaps}. "
            f"Nome de fonte sem produtor nao ranqueia nada -- ou escreva o "
            f"extrator, ou tire o nome da tupla com a decisao declarada."
        )

    def test_the_derivation_is_not_vacuous(self):
        """Se a leitura de AST parar de achar nomes, o teste acima vira 'nenhum
        gap' sobre nada. Estas duas fontes tem produtor conhecido e nomeado."""
        named = self._emitted_sources()

        assert "event_log" in named, sorted(named)
        assert "cli" in named, sorted(named)
