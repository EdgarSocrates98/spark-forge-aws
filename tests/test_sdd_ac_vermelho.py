"""AC_VERMELHO: criterio de `kind: test` precisa ter sido visto vermelho por uma tarefa.

Cada teste cobre um criterio de `docs/sdd/AC_VERMELHO/define.md`, sobre a feature
sintetica de `tests/test_sdd.py::feature_limpa` -- a mesma que o resto do SDD usa. Ela
nasce com o ship em `done`, e feature entregue e historico: o gate so age com o ship
ausente ou fora de `done`. Por isso quase todo teste tira o ship antes de estragar UMA
coisa.

A ligacao entre criterio e vermelho e derivada, nunca registrada (D1 do design): o
`covers` do plan diz que tarefas cobrem o criterio, e o `red` de cada uma, no
build_report, diz o que ela viu falhar.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge.sdd.checks import check
from tests.test_sdd import _codigos, _define_meta, _meta, _reescreve, _restampa, feature_limpa

ROOT = Path(__file__).resolve().parents[1]
NODE = "tests/test_alvo.py::test_alvo"


def _sem_ship(repo: Path) -> dict[str, Path]:
    """A feature construida e ainda nao entregue: `feature_limpa` sem o ship."""
    caminhos = feature_limpa(repo)
    caminhos.pop("ship").unlink()
    return caminhos


def _red(caminhos: dict[str, Path], comando: str, saida: int) -> None:
    """Troca o `red` da T1 no build_report (o ultimo artefato: ninguem abaixo fica stale)."""
    meta = _meta(caminhos["build_report"])
    meta["tasks"][0]["red"] = {"command": comando, "exit": saida}
    _reescreve(caminhos["build_report"], tasks=meta["tasks"])


def test_criterio_sem_vermelho_ligado_e_recusado(tmp_path):
    """AC1: o red de uma tarefa que cobre o criterio cita o node id, ou sai a recusa."""
    caminhos = _sem_ship(tmp_path)
    _red(caminhos, f"python -m pytest {NODE} -q", 1)
    assert _codigos(check(tmp_path)) == ([], [])

    # o red viu OUTRO teste falhar
    _red(caminhos, "python -m pytest tests/test_alvo.py::test_outro -q", 1)
    recusas = check(tmp_path)["refused"]
    assert [(r["code"], r["path"], r["field"]) for r in recusas] == [
        ("acceptance_never_red", "docs/sdd/F1/build_report.md", "tasks"),
    ]
    assert "AC1" in recusas[0]["unlock"] and NODE in recusas[0]["unlock"]

    # prefixo do node id nao e o node id
    _red(caminhos, f"python -m pytest {NODE}_outro -q", 1)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])

    # o node id aparece, mas o exit e zero: red_not_declared ja nomeia a causa
    _red(caminhos, f"python -m pytest {NODE} -q", 0)
    assert _codigos(check(tmp_path)) == (["red_not_declared"], [])

    # o node id aparece no red de uma tarefa que NAO cobre o criterio
    plano = _meta(caminhos["plan"])
    plano["tasks"].append({
        "id": "T2", "files": [], "covers": [],
        "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
    })
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    build = _meta(caminhos["build_report"])
    build["tasks"] = [
        {"id": "T1", "status": "done",
         "red": {"command": "python -m pytest tests/test_alvo.py::test_outro -q", "exit": 1},
         "green": {"command": f"python -m pytest {NODE} -q", "exit": 0}},
        {"id": "T2", "status": "done",
         "red": {"command": f"python -m pytest {NODE} -q", "exit": 1},
         "green": {"command": f"python -m pytest {NODE} -q", "exit": 0}},
    ]
    _reescreve(caminhos["build_report"], tasks=build["tasks"])
    _restampa(tmp_path)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])


def test_arquivo_conta_com_exit_2_e_nao_com_exit_1(tmp_path):
    """AC2: so o arquivo conta com exit 2 (erro de coleta), nunca com exit 1."""
    caminhos = _sem_ship(tmp_path)
    for comando in ("python -m pytest tests/test_alvo.py -q",
                    "python -m pytest tests\\test_alvo.py -q",
                    "python -m pytest ./tests/test_alvo.py -q"):
        _red(caminhos, comando, 2)
        assert _codigos(check(tmp_path)) == ([], []), comando

    _red(caminhos, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])

    # exit 2 em OUTRO arquivo nao e o arquivo do criterio
    _red(caminhos, "python -m pytest tests/test_outro.py -q", 2)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])


def test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada(tmp_path):
    """AC3: `guard` com motivo isenta o criterio; `guard` vazio e schema_invalid."""
    caminhos = _sem_ship(tmp_path)
    _red(caminhos, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])

    meta = _define_meta(caminhos)
    meta["acceptance"][0]["guard"] = "guarda de regressao: passa antes e depois por desenho"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    _restampa(tmp_path)
    assert _codigos(check(tmp_path)) == ([], [])

    for vazio in ("", "   ", True):
        meta["acceptance"][0]["guard"] = vazio
        _reescreve(caminhos["define"], acceptance=meta["acceptance"])
        _restampa(tmp_path)
        recusas = check(tmp_path)["refused"]
        assert {(r["code"], r["path"], r["field"]) for r in recusas} == {
            ("schema_invalid", "docs/sdd/F1/define.md", "acceptance/0/guard"),
        }, vazio


def test_feature_entregue_e_historico_e_nao_e_conferida(tmp_path):
    """AC4: com o ship em done a regra nao confere; fora de done, confere."""
    caminhos = feature_limpa(tmp_path)
    _red(caminhos, "python -m pytest tests/test_alvo.py -q", 1)
    _restampa(tmp_path)  # o build_report mudou; o ship volta a casar com ele
    assert _codigos(check(tmp_path)) == ([], [])

    for status in ("ready", "draft"):
        _reescreve(caminhos["ship"], status=status)
        assert _codigos(check(tmp_path)) == (["acceptance_never_red"], []), status

    # build_report em draft: o build nao aconteceu, e a regra nao confere
    _reescreve(caminhos["build_report"], status="draft")
    refused, _ = _codigos(check(tmp_path))
    assert "acceptance_never_red" not in refused

    # as features do repositorio -- as entregues, e esta mesma -- passam na regra
    relatorio = check(ROOT)
    assert [r for r in relatorio["refused"] if r["code"] == "acceptance_never_red"] == []


def test_referencia_normalizada_como_o_token(tmp_path):
    """F1: `./` e `\\` no `verified_by.ref` somem como somem no token do comando."""
    caminhos = _sem_ship(tmp_path)
    meta = _define_meta(caminhos)
    for ref in (f"./{NODE}", NODE.replace("/", "\\")):
        meta["acceptance"][0]["verified_by"]["ref"] = ref
        _reescreve(caminhos["define"], acceptance=meta["acceptance"])
        _restampa(tmp_path)
        _red(caminhos, f"pytest ./{NODE}", 1)
        assert "acceptance_never_red" not in _codigos(check(tmp_path))[0], ref
        # so o arquivo, com exit 2, tambem casa a referencia normalizada
        _red(caminhos, "pytest tests/test_alvo.py", 2)
        assert "acceptance_never_red" not in _codigos(check(tmp_path))[0], ref


def test_so_tarefa_done_conta_como_vermelho(tmp_path):
    """F2: tarefa `skipped` ou `blocked` que cita o node nao viu o criterio vermelho."""
    caminhos = _sem_ship(tmp_path)
    plano = _meta(caminhos["plan"])
    plano["tasks"].append({
        "id": "T2", "files": [], "covers": ["AC1"],
        "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
    })
    _reescreve(caminhos["plan"], tasks=plano["tasks"])
    for status in ("skipped", "blocked"):
        build = _meta(caminhos["build_report"])
        build["tasks"] = [
            {"id": "T1", "status": "done",
             "red": {"command": "python -m pytest tests/test_alvo.py::test_outro -q", "exit": 1},
             "green": {"command": f"python -m pytest {NODE} -q", "exit": 0}},
            {"id": "T2", "status": status,
             "red": {"command": f"python -m pytest {NODE} -q", "exit": 1}},
        ]
        _reescreve(caminhos["build_report"], tasks=build["tasks"])
        _restampa(tmp_path)
        assert "acceptance_never_red" in _codigos(check(tmp_path))[0], status


def test_exit_5_nao_e_vermelho(tmp_path):
    """F3: exit 5 do pytest e nenhum teste coletado, nao falha vista."""
    caminhos = _sem_ship(tmp_path)
    _red(caminhos, f"python -m pytest {NODE} -q", 5)
    assert _codigos(check(tmp_path)) == (["acceptance_never_red"], [])


def test_guarda_so_de_espaco_unicode_e_recusada(tmp_path):
    """F4: `guard` feito so de espaco Unicode (ex.: U+200B) nao e motivo."""
    caminhos = _sem_ship(tmp_path)
    meta = _define_meta(caminhos)
    for vazio in ("​", "  ", "﻿", "_ - ."):
        meta["acceptance"][0]["guard"] = vazio
        _reescreve(caminhos["define"], acceptance=meta["acceptance"])
        _restampa(tmp_path)
        recusas = check(tmp_path)["refused"]
        assert ("schema_invalid", "docs/sdd/F1/define.md", "acceptance/0/guard") in {
            (r["code"], r["path"], r["field"]) for r in recusas
        }, repr(vazio)
    # motivo com letra acentuada passa no schema
    meta["acceptance"][0]["guard"] = "ávido por regressão"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    _restampa(tmp_path)
    assert "schema_invalid" not in _codigos(check(tmp_path))[0]


def test_feature_operator_nao_e_conferida(tmp_path):
    """D5: so o perfil dev e conferido; no operator o contrato de `moved` fica como era."""
    operador = feature_limpa(tmp_path / "operador", "operator")
    operador.pop("ship").unlink()
    _red(operador, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path / "operador")) == ([], [])

    # o mesmo red no dev e recusado: o que isenta o operator e o perfil, nao o red
    dev = _sem_ship(tmp_path / "dev")
    _red(dev, "python -m pytest tests/test_alvo.py -q", 1)
    assert _codigos(check(tmp_path / "dev")) == (["acceptance_never_red"], [])
