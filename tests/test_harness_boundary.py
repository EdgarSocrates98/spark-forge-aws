"""A fronteira que o prompt do harness chama de critica (secao 43).

O runtime executa tasks. A avaliacao MEDE o runtime. Um import do runtime para
a avaliacao inverteria a relacao -- o medido passaria a depender do medidor --,
e o sintoma so apareceria muito depois, como um golden que passa porque o
runtime aprendeu a forma do grader.

Este teste tranca um invariante que JA VALE. E de proposito: separacao que vale
por acidente deixa de valer no primeiro import distraido, e a secao 43 nao pede
que a separacao exista, pede que ela seja garantida.
"""
from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUNTIME = RAIZ / "sparkforge"
AVALIACAO = RUNTIME / "evals"
PACOTE_AVALIACAO = "sparkforge.evals"


def _e_avaliacao(modulo: str) -> bool:
    """Prefixo COM fronteira, e nao `startswith` cru.

    `startswith("sparkforge.evals")` casaria um futuro `sparkforge.evalsuite`,
    que nao tem relacao nenhuma com a avaliacao. Vermelho falso custa a mesma
    confianca que verde falso: quem investiga um gate que acusa errado uma vez
    passa a nao acreditar nele.
    """
    return modulo == PACOTE_AVALIACAO or modulo.startswith(PACOTE_AVALIACAO + ".")


def _ancora_relativa(arquivo: Path, nivel: int, raiz: Path) -> str | None:
    """O pacote contra o qual um import relativo se resolve.

    Sem isto o gate tinha um buraco por onde passava exatamente o cruzamento
    que esta fase existe para proibir: `from ..evals.runner import X` guarda
    "evals.runner" em `no.module` e o 2 em `no.level`, e o texto
    "sparkforge.evals" nao aparece em lugar nenhum da AST. Pior, o pacote usa
    import relativo em varios modulos, entao o "import distraido" que a
    docstring do modulo preve tem chance real de nascer relativo -- fazer o
    caso permissivo por default no vetor que o proprio pacote mais usa seria o
    defeito, nao a simplificacao.

    Devolve None quando o nivel alcanca a raiz do repositorio ou passa dela.
    A comparacao e `>=` e nao `>` porque `subir == len(partes)` para exatamente
    na raiz, que nao e pacote nenhum: em Python isso ja e `attempted relative
    import beyond top-level package`, ou seja import quebrado e nao cruzamento
    de fronteira. Com `>` a funcao devolvia ancora vazia nessa borda e deixava
    o nome sair nu (`evals`), contrariando esta docstring.
    """
    partes = arquivo.relative_to(raiz).parts[:-1]
    subir = nivel - 1
    if subir >= len(partes):
        return None
    if subir:
        partes = partes[:-subir]
    return ".".join(partes)


def _modulos_importados(arquivo: Path, raiz: Path = RAIZ) -> set[str]:
    """Os modulos que este arquivo importa, por AST e nao por substring.

    Substring casaria a mencao de `sparkforge.evals` num comentario ou numa
    docstring, e comentario nao cria dependencia. O que cria e o `import`.

    `filename` vai para o `ast.parse` porque um erro de sintaxe em qualquer
    arquivo do pacote derrubaria o teste com `<unknown>` no lugar do nome, e
    entao alguem teria que procurar a mao qual dos arquivos quebrou.
    """
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom):
            if no.level:
                ancora = _ancora_relativa(arquivo, no.level, raiz)
                if ancora is None:
                    continue
                if no.module:
                    nomes.add(f"{ancora}.{no.module}" if ancora else no.module)
                else:
                    # `from . import evals`: quem nomeia o modulo importado e
                    # `names`, nao `module` -- que nesta forma e None.
                    nomes.update(
                        f"{ancora}.{a.name}" if ancora else a.name for a in no.names
                    )
            elif no.module:
                nomes.add(no.module)
    return nomes


def _arquivos_do_runtime() -> list[Path]:
    return sorted(
        p
        for p in RUNTIME.rglob("*.py")
        if AVALIACAO not in p.parents and "__pycache__" not in p.parts
    )


def _cruzamentos() -> list[str]:
    """Os modulos de runtime que importam a avaliacao.

    Extraido para que o proprio teste consiga exercitar a DETECCAO com uma
    violacao injetada. Sem isso, o teste da fronteira provaria apenas que a
    lista esta vazia hoje -- nunca que ela deixaria de estar se alguem
    cruzasse.
    """
    return [
        str(arquivo.relative_to(RAIZ))
        for arquivo in _arquivos_do_runtime()
        if any(_e_avaliacao(m) for m in _modulos_importados(arquivo))
    ]


class TestORuntimeNaoDependeDaAvaliacao:
    def test_nenhum_modulo_de_runtime_importa_sparkforge_evals(self):
        cruzaram = _cruzamentos()
        assert cruzaram == [], (
            f"estes modulos de RUNTIME importam a AVALIACAO: {cruzaram}.\n"
            f"A direcao permitida e a inversa -- a avaliacao mede o runtime. "
            f"Inverter faz o medido depender do medidor, e o sintoma aparece "
            f"muito depois, como golden que passa porque o runtime aprendeu a "
            f"forma do grader. Ver docs/harness/RUNTIME-VS-EVALUATION.md."
        )

    def test_a_avaliacao_importa_o_runtime_e_isso_e_a_direcao_certa(self):
        """O par positivo. Sem ele, o teste acima passaria tambem num
        repositorio em que os dois lados nao se falam -- e nao e isso que a
        secao 43 descreve.

        Varre o pacote inteiro em vez de abrir `runner.py` pelo nome: preso a
        um arquivo, renomear o modulo mataria o teste com `FileNotFoundError`
        em vez de dizer que a avaliacao parou de medir o runtime.
        """
        do_pacote: set[str] = set()
        for arquivo in sorted(AVALIACAO.rglob("*.py")):
            if "__pycache__" in arquivo.parts:
                continue
            do_pacote |= _modulos_importados(arquivo)
        assert any(
            m.startswith("sparkforge.") and not _e_avaliacao(m) for m in do_pacote
        ), "a avaliacao precisa medir ALGUM modulo de runtime"


class TestADeteccaoEnxergaImportRelativo:
    """O gate nasceu comparando `no.module` cru, e por ai passava o cruzamento
    escrito na forma que o proprio pacote mais usa. Estes testes fixam as duas
    formas relativas e provam que o gate as enxerga de ponta a ponta."""

    def _resolver(self, tmp_path: Path, origem: str, codigo: str) -> set[str]:
        arquivo = tmp_path / origem
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(codigo, encoding="utf-8")
        return _modulos_importados(arquivo, raiz=tmp_path)

    def test_from_pontos_modulo_vira_nome_absoluto(self, tmp_path):
        nomes = self._resolver(
            tmp_path,
            "sparkforge/migration/assessment.py",
            "from ..evals.runner import EvaluationRunner\n",
        )
        assert "sparkforge.evals.runner" in nomes

    def test_from_ponto_import_nome_vira_nome_absoluto(self, tmp_path):
        """`no.module` e None nesta forma, e o guard antigo a descartava."""
        nomes = self._resolver(
            tmp_path, "sparkforge/__init__.py", "from . import evals\n"
        )
        assert "sparkforge.evals" in nomes

    def test_nivel_acima_da_raiz_nao_inventa_modulo(self, tmp_path):
        """Import quebrado nao e cruzamento de fronteira, e nao pode virar um
        nome resolvido por acidente."""
        nomes = self._resolver(
            tmp_path, "sparkforge/mod.py", "from ....evals import runner\n"
        )
        assert nomes == set()

    def test_a_borda_exata_do_topo_do_pacote_nao_inventa_modulo(self, tmp_path):
        """`subir == len(partes)`: o nivel para EXATAMENTE na raiz, que nao e
        pacote.

        Precisa de teste proprio porque o caso acima usa `level=4` e passa
        longe da borda -- e foi justamente na borda que a primeira versao
        devolvia ancora vazia e deixava o nome sair nu (`evals`), enquanto a
        docstring prometia None. Sem fixar a borda, ela volta na proxima
        refatoracao.
        """
        nomes = self._resolver(
            tmp_path,
            "sparkforge/migration/assessment.py",
            "from ...evals import runner\n",
        )
        assert nomes == set()

    def test_o_ultimo_nivel_valido_abaixo_da_borda_ainda_resolve(self, tmp_path):
        """O par da borda: trocar `>` por `>=` nao pode ter comido o nivel
        legitimo imediatamente abaixo dela."""
        nomes = self._resolver(
            tmp_path,
            "sparkforge/migration/assessment.py",
            "from ..evals import runner\n",
        )
        assert nomes == {"sparkforge.evals"}

    def test_prefixo_parecido_nao_conta_como_avaliacao(self):
        assert _e_avaliacao("sparkforge.evals")
        assert _e_avaliacao("sparkforge.evals.runner")
        assert not _e_avaliacao("sparkforge.evalsuite")

    def test_violacao_relativa_injetada_num_modulo_real_fica_vermelha(self):
        """O par de ponta a ponta. Sem ele os testes acima provariam so que a
        resolucao sabe resolver, nunca que o gate usa a resolucao.

        E o procedimento do Step 3 do plano -- injetar, ver vermelho, desfazer
        --, aqui automatizado, porque procedimento manual so pega a regressao
        se alguem lembrar de repetir.
        """
        alvo = RUNTIME / "migration" / "assessment.py"
        nome = str(alvo.relative_to(RAIZ))
        original = alvo.read_bytes()
        assert nome not in _cruzamentos()
        try:
            alvo.write_bytes(
                b"from ..evals.runner import EvaluationRunner  # violacao\n" + original
            )
            assert nome in _cruzamentos()
        finally:
            alvo.write_bytes(original)
        assert nome not in _cruzamentos()
