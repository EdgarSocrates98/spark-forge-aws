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


def _modulos_importados(arquivo: Path) -> set[str]:
    """Os modulos que este arquivo importa, por AST e nao por substring.

    Substring casaria a mencao de `sparkforge.evals` num comentario ou numa
    docstring, e comentario nao cria dependencia. O que cria e o `import`.
    """
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


def _arquivos_do_runtime() -> list[Path]:
    return sorted(
        p
        for p in RUNTIME.rglob("*.py")
        if AVALIACAO not in p.parents and "__pycache__" not in p.parts
    )


class TestORuntimeNaoDependeDaAvaliacao:
    def test_nenhum_modulo_de_runtime_importa_sparkforge_evals(self):
        cruzaram = [
            str(arquivo.relative_to(RAIZ))
            for arquivo in _arquivos_do_runtime()
            if any(m.startswith("sparkforge.evals") for m in _modulos_importados(arquivo))
        ]
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
        secao 43 descreve."""
        do_runner = _modulos_importados(AVALIACAO / "runner.py")
        assert any(
            m.startswith("sparkforge.") and not m.startswith("sparkforge.evals")
            for m in do_runner
        ), "a avaliacao precisa medir ALGUM modulo de runtime"
