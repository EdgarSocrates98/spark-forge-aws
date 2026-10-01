---
sdd: 1
feature: SDD_SKILLS_REVISAO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_SKILLS_REVISAO/design.md
  sha256: "2eeb6410e80ebed1002039f75a5912bf5041365b2b6b20b2820404be5fea2ea0"
tasks:
  - id: T1
    files: [tests/test_sdd_skills.py]
    covers: [AC1]
    test: {path: tests/test_sdd_skills.py, name: test_o_detector_recusa_flag_inventada}
  - id: T2
    files: [skills/sdd-explore/SKILL.md, skills/sdd-define/SKILL.md, skills/sdd-design/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-build/SKILL.md, skills/sdd-ship/SKILL.md, tests/test_sdd_skills.py]
    covers: [AC2]
    test: {path: tests/test_sdd_skills.py, name: test_descricoes_so_com_gatilho}
  - id: T3
    files: [docs/sdd/README.md, skills/sdd-explore/SKILL.md, skills/sdd-define/SKILL.md, skills/sdd-design/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-build/SKILL.md, skills/sdd-ship/SKILL.md, tests/test_sdd_skills.py]
    covers: [AC3]
    test: {path: tests/test_sdd_skills.py, name: test_blocos_comuns_moram_no_readme}
  - id: T4
    files: [skills/sdd-build/SKILL.md, skills/sdd-ship/SKILL.md, tests/test_sdd_skills.py]
    covers: [AC4]
    test: {path: tests/test_sdd_skills.py, name: test_revisao_de_build_e_ship}
  - id: T5
    files: [skills/sdd-define/SKILL.md, skills/sdd-explore/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-ship/SKILL.md, tests/test_sdd_skills.py]
    covers: [AC5, AC8]
    test: {path: tests/test_sdd_skills.py, name: test_revisao_de_define_explore_plan_ship}
  - id: T6
    files: [docs/sdd/templates/explore.md, docs/sdd/templates/define.md, docs/sdd/templates/design.md, docs/sdd/templates/plan.md, docs/sdd/templates/build_report.md, docs/sdd/templates/ship.md, tests/test_sdd_skills.py]
    covers: [AC6, AC7]
    test: {path: tests/test_sdd_skills.py, name: test_templates_revisados}
---

# SDD_SKILLS_REVISAO — plano

Regras de toda tarefa: edição só por ferramenta de edição, LF, comentário de
código em português sem acento, um commit por tarefa (`git commit -F`). Tarefa
que toca skill roda `python scripts/sync_skills.py` com
`.claude/agents/README.md` fora da árvore, e os gates vizinhos
`python -m pytest tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q`.

Vermelho por `NameError` vale só quando o nome ausente é a unidade sob teste
(aqui, `_flags_recusadas` em T1). Nas tarefas de texto, o vermelho é a
asserção sobre o texto de hoje.

## T1 — flags no teste de comandos

Em `tests/test_sdd_skills.py`, depois de `_aceito_pelo_parser`, e dentro de
`test_comandos_citados_existem`:

```python
# o comando inteiro entre crases; `<...>` vira valor ficticio antes de separar
_COMANDO_CITADO = re.compile(r"`sparkforge ([^`]*)`")
_MARCADOR = re.compile(r"<[^<>]*>")


def _subcomandos(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            return acao.choices
    return {}


def _flags_recusadas(parser: argparse.ArgumentParser, comando: str) -> list[str]:
    """As `--flags` do comando citado que o subparser do proprio verbo nao conhece."""
    tokens = _MARCADOR.sub("X", comando).split()
    atual = parser
    while tokens and tokens[0] in _subcomandos(atual):
        atual = _subcomandos(atual)[tokens.pop(0)]
    conhecidas = {opcao for acao in atual._actions for opcao in acao.option_strings}
    return [token for token in tokens if token.startswith("--") and token not in conhecidas]
```

```python
        flags = [
            (comando, flag)
            for comando in _COMANDO_CITADO.findall(texto)
            for flag in _flags_recusadas(parser, comando)
        ]
        assert not flags, (nome, flags)
```

Teste novo, depois de `test_o_detector_recusa_verbo_inventado`:

```python
def test_o_detector_recusa_flag_inventada():
    """Guarda da conferencia de flags: sem isto, o AC3 de SDD_SKILLS passaria por vacuidade."""
    parser = build_parser()
    assert _flags_recusadas(parser, "funcval compare --plan <p> --out <ref do AC>") == []
    assert _flags_recusadas(parser, "change propose --sandbox <id> --funcaval x") == ["--funcaval"]
    assert _flags_recusadas(parser, "sdd check --repo . --raiz docs") == ["--raiz"]
    # flag de outro verbo nao vale aqui
    assert _flags_recusadas(parser, "benchmark --before a --funcval b") == ["--funcval"]
```

Vermelho: `python -m pytest tests/test_sdd_skills.py::test_o_detector_recusa_flag_inventada -q`
(`NameError: _flags_recusadas`, a unidade sob teste). Commit
`test(sdd): check the flags of every sparkforge command the skills cite`.

## T2 — descrições

```python
def _descricao(nome: str) -> str:
    return re.search(r"^description: (.*)$", _texto_da_skill(nome), re.M).group(1)


def test_descricoes_so_com_gatilho():
    for nome in SKILLS_SDD:
        descricao = _descricao(nome)
        assert descricao.startswith("Use quando"), nome
        assert len(descricao) <= 320, (nome, len(descricao))
        for resumo in ("Grava ", "fecha com", "fechando com"):
            assert resumo not in descricao, (nome, resumo)
```

Vermelho: `python -m pytest tests/test_sdd_skills.py::test_descricoes_so_com_gatilho -q`.
Texto: cada `description` fica com a fase anterior pronta, as frases que
disparam e, quando útil, o perfil. Commit `docs(sdd): trim skill descriptions to their triggers`.

## T3 — blocos comuns no README

```python
_SECOES_COMUNS = {
    "o-laço-de-cada-fase": ("## O laço de cada fase", SKILLS_SDD),
    "caminho-da-mudança-do-operador": (
        "## Caminho da mudança do operador",
        ("sdd-define", "sdd-design", "sdd-plan", "sdd-build", "sdd-ship"),
    ),
    "conhecimento-citado-nunca-memória": (
        "## Conhecimento citado, nunca memória",
        ("sdd-explore", "sdd-define", "sdd-design", "sdd-build"),
    ),
}


def test_blocos_comuns_moram_no_readme():
    readme = (ROOT / "docs" / "sdd" / "README.md").read_text(encoding="utf-8")
    assert "lacunas esperadas" in readme and "zero recusa" in readme
    for ancora, (titulo, skills) in _SECOES_COMUNS.items():
        assert titulo in readme, titulo
        for nome in skills:
            assert f"docs/sdd/README.md#{ancora}" in _texto_da_skill(nome), (nome, ancora)
```

Vermelho: `python -m pytest tests/test_sdd_skills.py::test_blocos_comuns_moram_no_readme -q`.
Texto: as três seções entram no README (o laço rascunho → stamp → check →
leitura do operador → `ready`, com as lacunas esperadas por fase; o caminho
`funcval plan` → `change plan` → `change sandbox` → `funcval compare --out` →
`benchmark --out` → `change propose --funcval --benchmark`; a regra de citar
`rules lookup`/`knowledge path`/`code symbol` com a versão). Cada skill troca a
cópia por uma linha com o link e fica com o comando da própria fase. Commit
`docs(sdd): move the repeated skill blocks into the SDD README`.

## T4 — build e ship

```python
def test_revisao_de_build_e_ship():
    build = _texto_da_skill("sdd-build")
    ship = _texto_da_skill("sdd-ship")
    for nome, texto in (("sdd-build", build), ("sdd-ship", ship)):
        assert "--out <ref do AC>" in texto, nome
        assert "--out bench.json" in texto, nome
        assert "--funcval <cmp.json> --benchmark bench.json" in texto, nome
        assert "kind: command" in texto and "exit 0" in texto, nome
        for comando in _COMANDO_CITADO.findall(texto):
            if comando.startswith("funcval compare --plan"):
                assert "--out" in comando, (nome, comando)
    assert "## Revisão final" in build
    assert "olho crítico" in build
    assert "O controlador escreve `red` e `green`" in build
    assert "unidade sob teste" in build
```

Vermelho: `python -m pytest tests/test_sdd_skills.py::test_revisao_de_build_e_ship -q`.
Texto de `sdd-build`: leitura crítica do plano (dúvida sobe ao operador, nada
de adivinhar); o controlador escreve `red`/`green` a partir do relato do
subagente, que traz o comando e o exit que viu; vermelho por erro de import ou
coleta só quando o que falta é a unidade sob teste; revisão final da
implementação inteira depois da última tarefa e antes do ship; na verificação
antes de fechar, cada `verified_by` de `kind: command` roda e exige exit 0.
Texto de `sdd-ship`: rodar cada `kind: command` com exit 0 e registrar no
corpo; comandos de evidência com as flags. Commit
`docs(sdd): close the evidence and review gaps in sdd-build and sdd-ship`.

## T5 — define, explore, plan e ship

```python
def test_revisao_de_define_explore_plan_ship():
    define = _texto_da_skill("sdd-define")
    assert "leitura do operador" in define
    assert "mensurável no ship" in define
    assert "`approaches[].id`" in _texto_da_skill("sdd-explore")
    plan = _texto_da_skill("sdd-plan")
    assert "TestClasse::test_x" in plan and "`[...]`" in plan
    ship = _texto_da_skill("sdd-ship")
    assert "regra 21" in ship
    assert "previsão inteira" in ship
    for opcao in ("merge local", "push e PR", "manter a branch", "descartar"):
        assert opcao in ship, opcao
    assert "confirmação digitada" in ship
    assert "## Lições" in ship
```

Vermelho: `python -m pytest tests/test_sdd_skills.py::test_revisao_de_define_explore_plan_ship -q`.
Commit `docs(sdd): require sign-off, whole-prediction outcomes and finishing options`.

## T6 — templates

```python
_PALAVRA_ACENTUADA = {
    "explore": "exploração",
    "define": "critérios",
    "design": "decisão",
    "plan": "código",
    "build_report": "relatório",
    "ship": "hipótese",
}


def test_templates_revisados():
    origem = ROOT / "docs" / "sdd" / "templates"
    for fase, palavra in _PALAVRA_ACENTUADA.items():
        texto = (origem / f"{fase}.md").read_text(encoding="utf-8")
        assert palavra in texto.lower(), (fase, palavra)
        assert "`feature: EXEMPLO`" in texto, fase
        assert "`status: draft`" in texto, fase
    assert "unidade sob teste" in (origem / "plan.md").read_text(encoding="utf-8")
    assert "## Lições" in (origem / "ship.md").read_text(encoding="utf-8")
```

Vermelho: `python -m pytest tests/test_sdd_skills.py::test_templates_revisados -q`.
Os templates seguem `status: ready` no frontmatter, porque
`test_templates_formam_feature_valida` os confere como feature pronta; a nota
de cada um manda trocar `feature: EXEMPLO` e pôr `status: draft` ao copiar.
Commit `docs(sdd): accent the templates and add the lessons section`.
