"""Todo nome declarado num registro de `config/` aponta para algo que existe.

O SF_STUBS (`docs/sdd/SF_STUBS/`) apagou 19 agentes `sf-*` ocos, e dois incrementos
depois a mesma doenca foi encontrada uma camada abaixo, em `config/`: sete tools
declaradas que nao existem em `TOOLS`. Ela sobreviveu porque NADA impedia.

Este e o gate que impede. Ele nao afirma que aquelas sete sairam -- afirma que nada
declarado deixa de resolver, e por isso continua valendo para o proximo registro.

O mapa abaixo e declarado de proposito. Varrer todo YAML de `config/` e adivinhar quais
strings sao nomes a resolver produziria falso positivo em campo de politica
(`forbidden_by_default` nao e um agente), e um teste que precisa de lista de excecao
para nao mentir acaba desligado.

O que ele cobre, e por que os TRES registros (2026-09-20): a primeira versao conferia so
`config/agentic-expansion.yaml` -- exatamente o que o D1 do design rejeitou por escrito,
"resolveria hoje e deixaria o proximo registro sem trava". Duas provas de que a lacuna era
real: `config/agents.yaml` declarava `sparkforge_inventory`, ausente de `TOOLS`; e os tres
`handoffs` que a propria T2 quebrou em `config/teams-expansion.yaml` passaram batido.

Declarar e obrigatorio, nao opcional: `test_toda_chave_de_lista_do_registro_tem_veredito`
percorre `config/*.yaml` por GLOB e exige que toda chave de valor-lista tenha entrada no
MAPA -- com resolvedor, ou com `NAO_E_NOME` e a razao. Declarar o que NAO e nome da a
cobertura sem o falso positivo que o D1 temia.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]

# Por glob, nao por lista: registro NOVO em `config/` entra na cobertura sozinho. Lista
# literal de arquivos repetiria, um nivel acima, a lacuna que o D1 rejeitou por escrito.
REGISTROS = tuple(sorted(ROOT.glob("config/*.yaml")) + sorted(ROOT.glob("config/*.yml")))

# As sete que a feature `docs/sdd/CONFIG_OCA/` removeu de `config/agentic-expansion.yaml`:
# nenhuma existia em `TOOLS`, e nenhuma tinha artefato coletavel definido.
TOOLS_QUE_SAIRAM = (
    "sparkforge_context_pack",
    "sparkforge_cost_estimate",
    "sparkforge_eval_golden_case",
    "sparkforge_lineage_extract",
    "sparkforge_offline_knowledge_search",
    "sparkforge_offline_knowledge_verify",
    "sparkforge_schema_compare",
)


def _agente_existe(nome: str) -> bool:
    """Um agente e um contrato em `agents/` -- coordenador na raiz, executor em `executors/`.

    Os dois sao arquivo de contrato lido de verdade: `agents/executors/*.md` e o alvo do
    campo `executors:` no frontmatter dos coordenadores. Conferir so a raiz poria vermelho
    um nome que TEM artefato, e gate que da falso positivo acaba desligado.
    """
    return (ROOT / "agents" / f"{nome}.md").exists() or (
        ROOT / "agents" / "executors" / f"{nome}.md"
    ).exists()


def _caminho_existe(rel: str) -> bool:
    return (ROOT / rel).exists()


def _tool_existe(nome: str) -> bool:
    return nome in TOOLS


# O veredito "esta chave tem valor-lista, e o que ha nela NAO e nome a resolver".
NAO_E_NOME = None


# (registro, caminho, resolvedor, o que o nome deveria apontar)
#
# O caminho desce por lista de dicionarios: `("agents", "allowed_tools")` colhe o campo
# `allowed_tools` de cada item da lista `agents`. O D1 rejeitou por escrito conferir so
# `config/agentic-expansion.yaml` -- "resolveria hoje e deixaria o proximo registro sem
# trava" --, e era exatamente ai que o gate estava.
#
# So REFERENCIA sai. `config/agents.yaml::agents[].name` NAO entra: `sparkforge/registry/
# loader.py` sintetiza o `AgentManifest` a partir do proprio registro, e cinco dos seis
# nomes nao tem `agents/<nome>.md` por desenho. Definicao nao resolve para arquivo.
MAPA = (
    ("config/agentic-expansion.yaml", ("agents",), _agente_existe, "arquivo em agents/"),
    ("config/agentic-expansion.yaml", ("knowledge",), _caminho_existe, "caminho no repositorio"),
    (
        "config/agentic-expansion.yaml",
        ("tools",),
        _tool_existe,
        "entrada em sparkforge.adapters.tools.TOOLS",
    ),
    (
        "config/agents.yaml",
        ("agents", "allowed_tools"),
        _tool_existe,
        "entrada em sparkforge.adapters.tools.TOOLS",
    ),
    ("config/agents.yaml", ("agents", "knowledge_refs"), _caminho_existe, "caminho no repositorio"),
    ("config/teams-expansion.yaml", ("teams", "coordinator"), _agente_existe, "arquivo em agents/"),
    ("config/teams-expansion.yaml", ("teams", "members"), _agente_existe, "arquivo em agents/"),
    ("config/teams-expansion.yaml", ("teams", "handoffs"), _agente_existe, "arquivo em agents/"),
    # Declaradas NAO-nome. Nao sao excecao ao gate: sao veredito, e o teste de cobertura
    # abaixo torna o veredito OBRIGATORIO. O D1 rejeitou adivinhar quais strings sao nomes
    # -- declarar qual NAO e resolve o mesmo problema sem o falso positivo.
    (
        "config/agents.yaml",
        ("agents",),
        NAO_E_NOME,
        "definicao, nao referencia: loader.py sintetiza o manifesto do proprio registro",
    ),
    ("config/agents.yaml", ("autonomy_focus",), NAO_E_NOME, "vocabulario de politica"),
    (
        "config/agents.yaml",
        ("defaults", "preserve_kinds"),
        NAO_E_NOME,
        "vocabulario de politica: kind de mensagem, nao artefato",
    ),
    (
        "config/teams-expansion.yaml",
        ("teams",),
        NAO_E_NOME,
        "definicao, nao referencia: o time e definido aqui",
    ),
)


class FormaInesperada(AssertionError):
    """A chave existe mas nao tem forma de nome, e passar calado seria o defeito."""


def _carrega(registro: str) -> dict:
    return yaml.safe_load((ROOT / registro).read_text(encoding="utf-8")) or {}


def _nomes(valor, onde: str) -> list[str]:
    """Um nome, ou uma lista de nomes. Qualquer outra forma levanta.

    A versao anterior fazia `list(valor) if isinstance(valor, list) else []`, e com isso
    `tools` virando mapping devolvia lista vazia: o gate ficava VERDE sobre uma chave que
    nunca olhou. Forma inesperada e lacuna, e lacuna tem nome (regra 20).
    """
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, list):
        fora = [v for v in valor if not isinstance(v, str)]
        if fora:
            raise FormaInesperada(f"{onde}: lista com item que nao e nome: {fora!r}")
        return list(valor)
    raise FormaInesperada(
        f"{onde}: esperava nome ou lista de nomes, veio {type(valor).__name__}"
    )


def _colher(no, caminho: tuple[str, ...], onde: str) -> list[str]:
    """Os nomes no fim de `caminho`, ou lista vazia se a chave nao existe.

    Chave ausente e resposta legitima: o D2 removeu o bloco `tools` inteiro em vez de
    deixar `tools: []`, porque chave vazia e convite a reencher sem criterio.
    """
    if not caminho:
        return _nomes(no, onde)
    chave, resto = caminho[0], caminho[1:]
    if isinstance(no, list):
        colhidos: list[str] = []
        for item in no:
            if isinstance(item, dict):
                colhidos += _colher(item, caminho, f"{onde}[]")
        return colhidos
    if not isinstance(no, dict) or chave not in no:
        return []
    return _colher(no[chave], resto, f"{onde}.{chave}")


def _declarados(registro: str, caminho: tuple[str, ...]) -> list[str]:
    return _colher(_carrega(registro), caminho, registro)


def test_todo_nome_declarado_resolve():
    """AC2: a trava. A falha nomeia registro, chave e nome."""
    quebrados = []
    for registro, caminho, resolve, alvo in MAPA:
        if resolve is NAO_E_NOME:
            continue
        chave = ".".join(caminho)
        for nome in _declarados(registro, caminho):
            if not resolve(nome):
                quebrados.append(f"{registro} :: {chave} :: {nome} (deveria ser {alvo})")
    assert not quebrados, (
        "nome declarado em config/ que nao resolve:\n  "
        + "\n  ".join(quebrados)
        + "\n\nColoque o artefato antes do nome, ou tire o nome. Ver "
        "docs/sdd/CONFIG_OCA/define.md."
    )


def _listas(no, caminho: tuple[str, ...] = ()):
    """Todo caminho do documento cujo valor e lista, descendo por lista de dicionarios."""
    if isinstance(no, list):
        yield caminho
        for item in no:
            if isinstance(item, dict):
                yield from _listas(item, caminho)
    elif isinstance(no, dict):
        for chave, valor in no.items():
            yield from _listas(valor, caminho + (chave,))


def test_toda_chave_de_lista_do_registro_tem_veredito():
    """O MAPA e fixo, e chave nova entrava sem ninguem olhar. Agora nao entra calada.

    Cobertura, nao adivinhacao: a chave nova nao precisa ser nome a resolver -- precisa
    estar DECLARADA no MAPA, com resolvedor ou com o veredito `NAO_E_NOME`. E por isso
    que registro novo em `config/` tambem cai aqui: a varredura e por glob, nao por lista.

    O que este teste NAO alcanca, e a recusa tem nome: chave nova de valor ESCALAR. Uma
    referencia unica como `teams[].coordinator` so e conferida porque esta no MAPA; uma
    `teams[].revisor: sf-foo` inventada amanha passaria por aqui sem veredito.
    """
    declarados = {(registro, caminho) for registro, caminho, _, _ in MAPA}
    orfas = []
    for path in sorted(REGISTROS):
        registro = path.relative_to(ROOT).as_posix()
        dados = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for caminho in sorted(set(_listas(dados))):
            if (registro, caminho) not in declarados:
                orfas.append(f"{registro} :: {'.'.join(caminho)}")
    assert not orfas, (
        "chave de valor-lista em config/ sem veredito no MAPA:\n  "
        + "\n  ".join(orfas)
        + "\n\nAcrescente a entrada com o resolvedor, ou com NAO_E_NOME e a razao."
    )


def test_forma_inesperada_levanta_em_vez_de_passar_calado():
    """`tools` virando mapping passava com lista vazia, e o gate ficava verde a toa."""
    # Forma que nao e nome nenhum: levanta em vez de devolver [].
    with pytest.raises(FormaInesperada):
        _colher({"tools": {"sparkforge_x": {"ref": "y"}}}, ("tools",), "<memoria>")
    with pytest.raises(FormaInesperada):
        _colher({"tools": None}, ("tools",), "<memoria>")
    # Lista com item que nao e nome: levanta em vez de virar nome por `str()`.
    with pytest.raises(FormaInesperada):
        _colher({"tools": [{"name": "sparkforge_x"}]}, ("tools",), "<memoria>")
    # Chave AUSENTE continua legitima: o D2 removeu o bloco inteiro de proposito.
    assert _colher({}, ("tools",), "<memoria>") == []
    # Nome unico e forma legitima, e e conferido: `teams[].coordinator` e escalar.
    assert _colher({"coordinator": "sf-x"}, ("coordinator",), "<memoria>") == ["sf-x"]
    assert _colher({"tools": ["sparkforge_judge"]}, ("tools",), "<memoria>") == ["sparkforge_judge"]


def test_toda_tool_declarada_existe():
    """AC1: as sete que sairam nao voltam, por nome.

    Esta asercao e o par NAO-VACUO do teste acima: com o bloco `tools` removido, aquele
    passa por ausencia. Este falha se qualquer uma das sete for reintroduzida em
    `config/`, tenha ou nao bloco.
    """
    texto = (ROOT / "config" / "agentic-expansion.yaml").read_text(encoding="utf-8")
    voltaram = [t for t in TOOLS_QUE_SAIRAM if t in texto]
    assert not voltaram, f"tool sem lastro de volta no registro: {voltaram}"
    assert all(t not in TOOLS for t in TOOLS_QUE_SAIRAM), (
        "uma das sete passou a existir de verdade: tire-a de TOOLS_QUE_SAIRAM e deixe o "
        "gate do declarado cuidar dela"
    )


_COM_CORPO = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _literais_executaveis(texto: str) -> list[str]:
    """As strings do modulo que o interpretador USA, sem as docstrings.

    Comentario nao entra na AST, entao sai de graca. Docstring e o primeiro `Expr` de
    modulo, classe ou funcao, e sai por identidade.
    """
    arvore = ast.parse(texto)
    prosa = set()
    for no in ast.walk(arvore):
        corpo = getattr(no, "body", None) if isinstance(no, _COM_CORPO) else None
        if corpo and isinstance(corpo[0], ast.Expr):
            primeiro = corpo[0].value
            if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
                prosa.add(id(primeiro))
    return [
        no.value
        for no in ast.walk(arvore)
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in prosa
    ]


SUBAGENTS_QUE_SAIRAM = (
    "benchmark-comparator",
    "cost-estimator",
    "cross-reviewer",
    "evidence-extractor",
    "experiment-designer",
    "handoff-preparer",
    "hypothesis-generator",
    "intake-packager",
    "lineage-impact-analyzer",
    "mutation-risk-checker",
    "regression-judge",
    "release-gate",
    "rollback-planner",
    "schema-compatibility-checker",
    "security-gate",
    "source-verifier",
)


def test_o_registro_de_subagents_saiu_e_ninguem_o_le():
    """AC3: os 16 stubs sairam, e a medida que autorizou continua valendo.

    Os contratos existiam -- 16 de 16 -- e eram BYTE-IDENTICOS abaixo de `## Contract`;
    a descricao de cada um era o proprio nome com o hifen trocado por espaco. Nenhum
    modulo de `sparkforge/`, `scripts/` ou `tests/` os lia, ao contrario de `skills/` e
    `agents/`, que varios leem. A lacuna U1 do define -- um consumidor FORA do
    repositorio -- nao e alcancavel daqui, e o rollback do D3 e a rede dela.
    """
    assert not (ROOT / "config" / "subagents.yaml").exists()
    assert not (ROOT / "subagents").exists()

    # E nenhum modulo passou a LER o que saiu.
    eu = Path(__file__).resolve()
    for diretorio in ("sparkforge", "scripts", "tests"):
        for arquivo in sorted((ROOT / diretorio).rglob("*.py")):
            if arquivo.resolve() == eu:
                continue  # o guarda nao e sujeito de si mesmo: a agulha mora aqui
            literais = _literais_executaveis(arquivo.read_text(encoding="utf-8"))
            citados = [
                caminho
                for caminho in ("config/subagents.yaml", "subagents/")
                if any(caminho in literal for literal in literais)
            ]
            assert not citados, (arquivo, citados)


def test_mencao_explicativa_nao_conta_como_leitura():
    """A versao anterior varria o TEXTO do arquivo, e punia ate a explicacao.

    Docstring e comentario que citam `subagents/` -- inclusive para explicar por que ele
    nao existe -- ficavam vermelhos. O que o AC3 mede e LEITURA, e leitura mora em
    literal executavel, nao em prosa.
    """
    explicativo = (
        '"""Por que `config/subagents.yaml` saiu: docs/sdd/CONFIG_OCA/."""\n'
        "# o diretorio subagents/ saiu junto, com os 16 contratos\n"
        'CAMINHO = "config/agents.yaml"\n'
    )
    assert _literais_executaveis(explicativo) == ["config/agents.yaml"]

    leitura = 'dados = open("config/subagents.yaml", encoding="utf-8")\n'
    assert "config/subagents.yaml" in _literais_executaveis(leitura)
