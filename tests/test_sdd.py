"""Nucleo do SDD proprio: contrato conferivel e gates com nome.

Nenhuma fixture estatica: hash de upstream gravado em arquivo versionado e o caso
que o checkout do Windows com `core.autocrlf=true` ja quebrou (PR #63). Toda
feature e montada em `tmp_path`.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import jsonschema
import pytest
import yaml

from sparkforge.adapters import _core
from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import TOOLS, call_tool
from sparkforge.journal import journal_path, journaled
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.checks import change_kinds, check, schema_for
from sparkforge.sdd.load import discover, load_artifact, split_frontmatter
from sparkforge.sdd.stamp import StampError, stamp
from sparkforge.sdd.status import status

ROOT = Path(__file__).resolve().parents[1]


def test_fases_e_raiz_padrao():
    assert PHASES == ("explore", "define", "design", "plan", "build_report", "ship")
    assert DEFAULT_ROOT == "docs/sdd"


def test_split_frontmatter_separa_bloco_e_corpo():
    bloco, corpo = split_frontmatter("---\na: 1\n---\ncorpo\n")
    assert bloco == "a: 1\n"
    assert corpo == "corpo\n"


def test_split_frontmatter_sem_cerca_devolve_none():
    assert split_frontmatter("a: 1\n") == (None, "a: 1\n")
    assert split_frontmatter("---\na: 1\n")[0] is None


def test_load_artifact_yaml_quebrado_diz_a_linha(tmp_path):
    arquivo = tmp_path / "define.md"
    arquivo.write_bytes(b"---\nsdd: 1\nfeature: [\n---\n")
    artefato = load_artifact(arquivo)
    assert artefato.meta is None
    assert "YAML invalido" in artefato.error
    assert "linha" in artefato.error


def test_load_artifact_nao_mapeamento(tmp_path):
    arquivo = tmp_path / "define.md"
    arquivo.write_bytes(b"---\n- a\n---\n")
    assert load_artifact(arquivo).error == "frontmatter precisa ser um mapeamento YAML"


def test_discover_so_pega_fase_na_profundidade_certa(tmp_path):
    raiz = tmp_path / "docs" / "sdd"
    (raiz / "F1").mkdir(parents=True)
    (raiz / "F1" / "define.md").write_bytes(b"---\n---\n")
    (raiz / "F1" / "notas.md").write_bytes(b"x")
    (raiz / "templates").mkdir()
    (raiz / "templates" / "define.md").write_bytes(b"---\nfeature: <FEATURE>\n---\n")
    (raiz / "archive" / "F0").mkdir(parents=True)
    (raiz / "archive" / "F0" / "define.md").write_bytes(b"x")
    descoberta = discover(raiz)
    assert descoberta.features == {"F1": {"define": raiz / "F1" / "define.md"}}
    assert descoberta.pulos == ()


def test_pasta_fora_do_padrao_de_feature_nao_e_feature(tmp_path):
    feature_limpa(tmp_path)
    for nome in ("templates", "Minusculo", "com-hifen"):
        pasta = tmp_path / "docs" / "sdd" / nome
        pasta.mkdir()
        (pasta / "define.md").write_bytes(b"---\nfeature: <FEATURE>\n---\n")
    relatorio = check(tmp_path)
    assert relatorio["features"] == ["F1"]
    assert _codigos(relatorio) == ([], [])


def test_feature_com_nome_podado_pela_varredura_vira_lacuna(tmp_path):
    for nome in ("BUILD", "SECRETS"):
        feature_limpa(tmp_path, feature=nome)
    feature_limpa(tmp_path, feature="F1")
    relatorio = check(tmp_path)
    assert relatorio["ok"] is False
    assert relatorio["features"] == ["F1"]
    lacunas = relatorio["unresolved"]
    assert [(u["code"], u["feature"], u["path"]) for u in lacunas] == [
        ("path_skipped", "BUILD", "docs/sdd/BUILD"),
        ("path_skipped", "SECRETS", "docs/sdd/SECRETS"),
    ]
    assert all("renomeie" in u["unlock"] for u in lacunas)
    saida = status(tmp_path)
    assert [f["feature"] for f in saida["features"]] == ["F1"]
    assert [(u["code"], u["feature"]) for u in saida["unresolved"]] == [
        ("path_skipped", "BUILD"), ("path_skipped", "SECRETS"),
    ]


def test_pulo_de_arquivo_na_raiz_nao_tem_feature(tmp_path):
    feature_limpa(tmp_path)
    (tmp_path / "docs" / "sdd" / "secrets.md").write_bytes(b"x")
    lacunas = check(tmp_path)["unresolved"]
    assert [(u["code"], u["feature"], u["path"]) for u in lacunas] == [
        ("path_skipped", None, "docs/sdd/secrets.md"),
    ]


def test_pulo_dentro_da_feature_leva_o_nome_dela(tmp_path):
    feature_limpa(tmp_path)
    (tmp_path / "docs" / "sdd" / "F1" / "build").mkdir()
    lacunas = check(tmp_path)["unresolved"]
    assert [(u["code"], u["feature"], u["path"]) for u in lacunas] == [
        ("path_skipped", "F1", "docs/sdd/F1/build"),
    ]
    assert status(tmp_path)["features"][0]["unresolved"] == ["path_skipped"]


@pytest.mark.parametrize("fase", PHASES)
def test_todo_schema_carrega_e_fecha_propriedades(fase):
    schema = schema_for(fase)
    assert schema["additionalProperties"] is False
    for campo in ("sdd", "feature", "phase", "profile", "status"):
        assert campo in schema["required"]


def test_change_kinds_casa_com_os_titulos_do_documento():
    """Deriva nos dois sentidos: titulo sem chave, ou chave sem titulo."""
    texto = (ROOT / "docs" / "gates-por-mudanca.md").read_text(encoding="utf-8")
    linhas = texto.splitlines()
    titulos: set[str] = set()
    for i, linha in enumerate(linhas):
        if not linha.startswith("## "):
            continue
        titulo = linha[3:].strip()
        # o titulo da secao de lastro continua na linha seguinte
        if i + 1 < len(linhas) and linhas[i + 1].startswith("## `"):
            titulo = f"{titulo} {linhas[i + 1][3:].strip()}"
        titulos.add(titulo)
    titulos = {t for t in titulos if not t.startswith("`docs/")}
    titulos.discard("Quando nada acima serve")
    secoes = {v["section"] for v in change_kinds().values()}
    assert secoes == titulos
    for chave, valor in change_kinds().items():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", chave)
        assert valor["registries"], chave


_LINHA_SHA = re.compile(r"^(?P<recuo>[ \t]+)sha256: ['\"]?(?P<hex>[0-9a-f]*)['\"]?$", re.M)


def _dump(meta: dict) -> str:
    """YAML com a linha do hash no MESMO formato que `stamp` grava.

    `yaml.safe_dump` escolhe sozinho se poe aspas num hex (depende do valor);
    `stamp` sempre grava `sha256: "<hex>"`. Sem alinhar os dois, restampar um
    hash que nao mudou mudaria o texto e deixaria a fase de baixo stale.
    """
    texto = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return _LINHA_SHA.sub(lambda m: f'{m["recuo"]}sha256: "{m["hex"]}"', texto)


def _grava(repo: Path, feature: str, fase: str, meta: dict) -> Path:
    pasta = repo / "docs" / "sdd" / feature
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{fase}.md"
    texto = "---\n" + _dump(meta) + "---\ncorpo livre\n"
    arquivo.write_bytes(texto.encode("utf-8"))
    return arquivo


def _upstream(repo: Path, anterior: Path) -> dict:
    return {"path": anterior.relative_to(repo).as_posix(), "sha256": text_sha256(anterior)}


def feature_limpa(repo: Path, profile: str = "dev", feature: str = "F1") -> dict[str, Path]:
    """Uma feature que passa em tudo. Cada teste de recusa estraga UMA coisa."""
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "test_alvo.py").write_bytes(b"def test_alvo():\n    assert True\n")
    (repo / "sparkforge").mkdir(exist_ok=True)
    (repo / "sparkforge" / "existente.py").write_bytes(b"x = 1\n")
    comum = {"sdd": 1, "feature": feature, "profile": profile, "status": "done"}
    caminhos: dict[str, Path] = {}
    define = {
        **comum,
        "phase": "define",
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [
            {
                "id": "AC1",
                "statement": "s",
                "verified_by": {"kind": "test", "ref": "tests/test_alvo.py::test_alvo"},
            }
        ],
        "success": [{"id": "SC1", "metric": "m", "source": "tests/test_alvo.py"}],
        "out_of_scope": [],
        "change_kinds": ["tool_or_verb"],
    }
    if profile == "operator":
        (repo / ".sparkforge").mkdir(exist_ok=True)
        (repo / ".sparkforge" / "case.yaml").write_bytes(b"case_id: C1\n")
        (repo / ".sparkforge" / "sandbox" / "S1").mkdir(parents=True)
        define["case_id"] = "C1"
    caminhos["define"] = _grava(repo, feature, "define", define)
    caminhos["design"] = _grava(repo, feature, "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream(repo, caminhos["define"]),
        "files": [
            {"path": "sparkforge/novo.py", "action": "create", "reason": "r"},
            {"path": "sparkforge/existente.py", "action": "modify", "reason": "r"},
        ],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "git revert"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
    })
    caminhos["plan"] = _grava(repo, feature, "plan", {
        **comum,
        "phase": "plan",
        "upstream": _upstream(repo, caminhos["design"]),
        "tasks": [{
            "id": "T1",
            "files": ["sparkforge/novo.py"],
            "covers": ["AC1"],
            "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
        }],
    })
    build = {
        **comum,
        "phase": "build_report",
        "upstream": _upstream(repo, caminhos["plan"]),
        "tasks": [{
            "id": "T1",
            "status": "done",
            "red": {"command": "pytest tests/test_alvo.py", "exit": 1},
            "green": {"command": "pytest tests/test_alvo.py", "exit": 0},
        }],
        "claims": [{"text": "t", "evidence_ref": "tests/test_alvo.py::test_alvo"}],
    }
    if profile == "operator":
        build["change_id"] = "S1"
    caminhos["build_report"] = _grava(repo, feature, "build_report", build)
    caminhos["ship"] = _grava(repo, feature, "ship", {
        **comum,
        "phase": "ship",
        "upstream": _upstream(repo, caminhos["build_report"]),
        "hypothesis_outcome": "confirmed",
        "registries": ["surface_lock", "generated_reference"],
        "deviations": [],
    })
    return caminhos


def _codigos(relatorio: dict) -> tuple[list[str], list[str]]:
    return (
        sorted(r["code"] for r in relatorio["refused"]),
        sorted(r["code"] for r in relatorio["unresolved"]),
    )


def _reescreve(arquivo: Path, **mudancas) -> None:
    """Muda campos do frontmatter e NAO restampa quem esta abaixo."""
    texto = arquivo.read_bytes().decode("utf-8")
    bloco, corpo = split_frontmatter(texto)
    meta = yaml.safe_load(bloco)
    for chave, valor in mudancas.items():
        if valor is None:
            meta.pop(chave, None)
        else:
            meta[chave] = valor
    novo = "---\n" + _dump(meta) + "---\n" + corpo
    arquivo.write_bytes(novo.encode("utf-8"))


@pytest.mark.parametrize("profile", ["dev", "operator"])
def test_feature_limpa_passa_sem_nada(tmp_path, profile):
    feature_limpa(tmp_path, profile)
    relatorio = check(tmp_path)
    assert relatorio["ok"] is True, relatorio
    assert relatorio["features"] == ["F1"]
    assert _codigos(relatorio) == ([], [])


def test_raiz_inexistente_e_lacuna(tmp_path):
    relatorio = check(tmp_path)
    assert relatorio["ok"] is False
    assert _codigos(relatorio) == ([], ["root_missing"])


def test_schema_invalid_campo_desconhecido(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], inventado=1)
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["schema_invalid"]
    assert recusa[0]["path"] == "docs/sdd/F1/ship.md"


def test_schema_invalid_yaml_quebrado(tmp_path):
    caminhos = feature_limpa(tmp_path)
    caminhos["ship"].write_bytes(b"---\nsdd: [\n---\n")
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["schema_invalid"]
    assert "linha" in recusa[0]["unlock"]


def test_schema_invalid_fase_trocada(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], phase="plan")
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("schema_invalid", "phase")]


def test_schema_invalid_feature_de_outra_pasta(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], feature="F2")
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"], r["path"]) for r in recusa] == [
        ("schema_invalid", "feature", "docs/sdd/F1/ship.md")
    ]


def test_upstream_para_outro_arquivo_existente(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], upstream=_upstream(tmp_path, caminhos["plan"]))
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("upstream_missing", "upstream/path")]
    assert "docs/sdd/F1/build_report.md" in recusa[0]["unlock"]


_EXPLORE = {
    "sdd": 1, "feature": "F1", "phase": "explore", "profile": "dev", "status": "done",
    "approaches": [{"id": "a", "summary": "s"}], "chosen": "a",
}


def test_upstream_no_define_sem_explore_e_schema_invalid(tmp_path):
    caminhos = _so_define(tmp_path)
    _reescreve(caminhos["define"], upstream={"path": "docs/sdd/F1/explore.md", "sha256": ""})
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("schema_invalid", "upstream")]
    assert "explore.md" in recusa[0]["unlock"]


def test_upstream_no_explore_e_schema_invalid(tmp_path):
    caminhos = _so_define(tmp_path)
    explore = _grava(tmp_path, "F1", "explore", {
        **_EXPLORE, "upstream": _upstream(tmp_path, caminhos["define"]),
    })
    _reescreve(caminhos["define"], upstream=_upstream(tmp_path, explore))
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"], r["path"]) for r in recusa] == [
        ("schema_invalid", "upstream", "docs/sdd/F1/explore.md")
    ]


def test_define_com_explore_declara_upstream(tmp_path):
    caminhos = _so_define(tmp_path)
    explore = _grava(tmp_path, "F1", "explore", _EXPLORE)
    assert _codigos(check(tmp_path)) == (["upstream_missing"], [])
    _reescreve(caminhos["define"], upstream=_upstream(tmp_path, explore))
    assert _codigos(check(tmp_path)) == ([], [])


def test_phase_out_of_order(tmp_path):
    caminhos = feature_limpa(tmp_path)
    caminhos["plan"].unlink()
    assert _codigos(check(tmp_path)) == (["phase_out_of_order", "upstream_missing"], [])


def test_phase_out_of_order_por_status(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], status="draft")
    # ship em draft nao bloqueia ninguem; build_report em draft bloqueia o ship
    assert _codigos(check(tmp_path)) == ([], [])
    _reescreve(caminhos["build_report"], status="draft")
    refused, _ = _codigos(check(tmp_path))
    assert "phase_out_of_order" in refused


def test_feature_filtra(tmp_path):
    feature_limpa(tmp_path, feature="F1")
    feature_limpa(tmp_path, feature="F2")
    assert check(tmp_path, feature="F2")["features"] == ["F2"]


def test_upstream_stale_e_stamp_resolve(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["define"], out_of_scope=["mudou"])
    assert _codigos(check(tmp_path)) == (["upstream_stale"], [])
    saida = stamp(tmp_path, "docs/sdd/F1/design.md")
    assert saida["changed"] is True
    assert saida["path"] == "docs/sdd/F1/design.md"
    assert saida["upstream"] == "docs/sdd/F1/define.md"
    # restampar o design muda o texto dele: agora o plan fica stale, e so ele
    assert [r["path"] for r in check(tmp_path)["refused"]] == ["docs/sdd/F1/plan.md"]


def test_stamp_idempotente_nao_regrava(tmp_path):
    caminhos = feature_limpa(tmp_path)
    antes = caminhos["design"].stat().st_mtime_ns
    assert stamp(tmp_path, "docs/sdd/F1/design.md")["changed"] is False
    assert caminhos["design"].stat().st_mtime_ns == antes


def test_stamp_preserva_crlf_e_o_corpo(tmp_path):
    caminhos = feature_limpa(tmp_path)
    original = caminhos["design"].read_bytes().replace(b"\n", b"\r\n")
    original = original.replace(
        text_sha256(caminhos["define"]).encode(), b"0" * 64
    )
    caminhos["design"].write_bytes(original)
    stamp(tmp_path, "docs/sdd/F1/design.md")
    depois = caminhos["design"].read_bytes()
    assert b"\n" not in depois.replace(b"\r\n", b"")
    assert depois.endswith(b"corpo livre\r\n")
    assert _codigos(check(tmp_path))[0] == []


def test_stamp_recusa_sem_upstream(tmp_path):
    caminhos = feature_limpa(tmp_path)
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/define.md")
    assert erro.value.code == "upstream_missing"
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/nao-existe.md")
    assert erro.value.code == "artifact_missing"
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "../fora.md")
    assert erro.value.code == "artifact_missing"
    assert caminhos["define"].is_file()


BOM = b"\xef\xbb\xbf"


def _sha_do_design(tmp_path, caminhos, substituto: str) -> None:
    """Troca a linha do hash do design por `substituto` (texto sem a quebra)."""
    texto = caminhos["design"].read_bytes().decode("utf-8")
    novo, n = re.subn(r'^  sha256: "[0-9a-f]*"$', lambda _: substituto, texto, flags=re.M)
    assert n == 1
    caminhos["design"].write_bytes(novo.encode("utf-8"))


def test_stamp_comentario_na_coluna_zero_nao_fecha_o_bloco(tmp_path):
    caminhos = _ate(tmp_path, "design")
    texto = caminhos["design"].read_bytes().decode("utf-8")
    texto = texto.replace("upstream:\n", "upstream:\n# nota do autor\n", 1)
    caminhos["design"].write_bytes(texto.encode("utf-8"))
    _sha_do_design(tmp_path, caminhos, '  sha256: "' + "0" * 64 + '"')
    assert stamp(tmp_path, "docs/sdd/F1/design.md")["changed"] is True
    assert b"upstream:\n# nota do autor\n" in caminhos["design"].read_bytes()
    assert _codigos(check(tmp_path)) == ([], [])


@pytest.mark.parametrize("valor", ['"' + "0" * 64 + '"', "'" + "0" * 64 + "'", "0" * 64, ""])
def test_stamp_preserva_comentario_no_fim_da_linha(tmp_path, valor):
    caminhos = _ate(tmp_path, "design")
    _sha_do_design(tmp_path, caminhos, f"  sha256: {valor}  # confere no stamp")
    assert stamp(tmp_path, "docs/sdd/F1/design.md")["changed"] is True
    esperado = f'  sha256: "{text_sha256(caminhos["define"])}"  # confere no stamp\n'
    assert esperado.encode() in caminhos["design"].read_bytes()
    assert _codigos(check(tmp_path)) == ([], [])


@pytest.mark.parametrize(
    "linha",
    [
        '  sha256:\n    "' + "0" * 64 + '"',
        "  sha256: |\n    " + "0" * 64,
        "  sha256: " + "0" * 32 + "\n    " + "0" * 32,
        '  sha256: "' + "0" * 32 + "\n    " + "0" * 32 + '"',
        "  sha256: !!str " + "0" * 64,
        "  sha256: &ancora " + "0" * 64,
    ],
)
def test_stamp_recusa_linha_do_hash_que_nao_sabe_reescrever(tmp_path, linha):
    caminhos = _ate(tmp_path, "design")
    _sha_do_design(tmp_path, caminhos, linha)
    antes = caminhos["design"].read_bytes()
    assert load_artifact(caminhos["design"]).error is None
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/design.md")
    assert erro.value.code == "sha_line_unsupported"
    assert caminhos["design"].read_bytes() == antes


def test_stamp_recusa_upstream_em_fluxo(tmp_path):
    caminhos = _ate(tmp_path, "design")
    texto = caminhos["design"].read_bytes().decode("utf-8")
    texto, n = re.subn(
        r'^upstream:\n  path: (\S+)\n  sha256: "[0-9a-f]*"\n',
        lambda m: f'upstream: {{path: {m[1]}, sha256: ""}}\n',
        texto,
        flags=re.M,
    )
    assert n == 1
    caminhos["design"].write_bytes(texto.encode("utf-8"))
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/design.md")
    assert erro.value.code == "upstream_flow_style"


def test_stamp_recusa_frontmatter_quebrado(tmp_path):
    caminhos = _ate(tmp_path, "design")
    caminhos["design"].write_bytes(b"---\nupstream: [\n---\n")
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/design.md")
    assert erro.value.code == "schema_invalid"


def test_stamp_so_aceita_artefato(tmp_path):
    caminhos = feature_limpa(tmp_path)
    corpo = caminhos["design"].read_bytes()
    fora = {
        "README.md": corpo,
        "docs/sdd/templates/design.md": corpo,
        "docs/sdd/F1/notas.md": corpo,
        "docs/sdd/F1/sub/design.md": corpo,
        "docs/sdd/design.md": corpo,
        "outra/F1/design.md": corpo,
    }
    for relativo, conteudo in fora.items():
        destino = tmp_path / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        with pytest.raises(StampError) as erro:
            stamp(tmp_path, relativo)
        assert erro.value.code == "not_an_artifact", relativo
        assert destino.read_bytes() == conteudo
    assert stamp(tmp_path, "outra/F1/design.md", root="outra")["changed"] is False


def test_load_artifact_tolera_bom(tmp_path):
    caminhos = feature_limpa(tmp_path)
    caminhos["ship"].write_bytes(BOM + caminhos["ship"].read_bytes())
    artefato = load_artifact(caminhos["ship"])
    assert artefato.error is None
    assert artefato.meta["phase"] == "ship"
    assert _codigos(check(tmp_path)) == ([], [])


def test_stamp_preserva_bom(tmp_path):
    caminhos = _ate(tmp_path, "design")
    _sha_do_design(tmp_path, caminhos, '  sha256: "' + "0" * 64 + '"')
    caminhos["design"].write_bytes(BOM + caminhos["design"].read_bytes())
    assert stamp(tmp_path, "docs/sdd/F1/design.md")["changed"] is True
    depois = caminhos["design"].read_bytes()
    assert depois.startswith(BOM + b"---\n")
    assert not depois[len(BOM):].startswith(BOM)
    assert _codigos(check(tmp_path)) == ([], [])


def _define_meta(caminhos):
    bloco, _ = split_frontmatter(caminhos["define"].read_bytes().decode("utf-8"))
    return yaml.safe_load(bloco)


def _so_define(tmp_path):
    """Feature so com define: nada abaixo para ficar stale."""
    caminhos = feature_limpa(tmp_path)
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    return caminhos


def test_success_without_source(tmp_path):
    caminhos = _so_define(tmp_path)
    _reescreve(caminhos["define"], success=[{"id": "SC1", "metric": "m"}])
    assert _codigos(check(tmp_path)) == (["success_without_source"], [])


def test_change_kind_desconhecido_e_schema_invalid(tmp_path):
    caminhos = _so_define(tmp_path)
    _reescreve(caminhos["define"], change_kinds=["inventado"])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("schema_invalid", "change_kinds/0")]


def test_test_not_written_antes_do_build(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"]["ref"] = "tests/test_alvo.py::test_futuro"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["test_not_written"])


def test_verified_by_dangling_depois_do_build(tmp_path):
    feature_limpa(tmp_path)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(b"def test_outro():\n    pass\n")
    refused, unresolved = _codigos(check(tmp_path))
    # o plan aponta o mesmo teste: as duas referencias penduram
    assert refused == ["verified_by_dangling", "verified_by_dangling"]
    assert unresolved == []


def _restampa(repo: Path, feature: str = "F1") -> None:
    for fase in ("design", "plan", "build_report", "ship"):
        if (repo / "docs" / "sdd" / feature / f"{fase}.md").is_file():
            stamp(repo, f"docs/sdd/{feature}/{fase}.md")


def _ref_do_define(repo: Path, caminhos, ref: str) -> None:
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"]["ref"] = ref
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    _restampa(repo)


_ARQUIVO_DE_TESTE = b"""\
def test_alvo():
    pass


def _helper():
    pass


def helper():
    pass


class TestA:
    def test_m(self):
        pass

    def _aux(self):
        pass

    class TestB:
        def test_c(self):
            pass

    class Interna:
        def test_d(self):
            pass


class Suporte:
    def test_s(self):
        pass
"""


@pytest.mark.parametrize("ref", [
    "tests/test_alvo.py::test_alvo[a-1]",
    "tests/test_alvo.py::test_alvo[caso::com::dois-pontos]",
    "tests/test_alvo.py::TestA::test_m",
    "tests/test_alvo.py::TestA::test_m[x]",
    "tests/test_alvo.py::TestA::TestB::test_c",
])
def test_node_id_real_do_pytest_conta(tmp_path, ref):
    caminhos = feature_limpa(tmp_path)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(_ARQUIVO_DE_TESTE)
    _ref_do_define(tmp_path, caminhos, ref)
    assert _codigos(check(tmp_path)) == ([], [])


@pytest.mark.parametrize("ref", [
    "tests/test_alvo.py::_helper",
    "tests/test_alvo.py::helper",
    "tests/test_alvo.py::TestA::_aux",
    "tests/test_alvo.py::TestA::Interna::test_d",
    "tests/test_alvo.py::Suporte::test_s",
    "tests/test_alvo.py::TestB::test_c",
    "tests/test_alvo.py::TestA",
])
def test_so_nome_coletavel_pelo_pytest_conta(tmp_path, ref):
    caminhos = feature_limpa(tmp_path)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(_ARQUIVO_DE_TESTE)
    _ref_do_define(tmp_path, caminhos, ref)
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [
        ("verified_by_dangling", "acceptance/0/verified_by")
    ]


@pytest.mark.parametrize("ref", ["tests/test_alvo.py", "tests/test_alvo.py::", "::test_alvo"])
def test_ref_de_teste_sem_nome_e_schema_invalid(tmp_path, ref):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"]["ref"] = ref
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    recusa = check(tmp_path)
    assert [(r["code"], r["field"]) for r in recusa["refused"]] == [
        ("schema_invalid", "acceptance/0/verified_by/ref")
    ]
    assert recusa["unresolved"] == []


def test_ref_de_teste_sem_nome_depois_do_build_tambem(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _ref_do_define(tmp_path, caminhos, "tests/test_alvo.py")
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [
        ("schema_invalid", "acceptance/0/verified_by/ref")
    ]


def test_arquivo_de_teste_ilegivel_nao_derruba(tmp_path, monkeypatch):
    feature_limpa(tmp_path)
    original = Path.read_bytes

    def falha(self):
        if self.name == "test_alvo.py":
            raise PermissionError("negado")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", falha)
    refused, _ = _codigos(check(tmp_path))
    assert refused == ["verified_by_dangling", "verified_by_dangling"]


@pytest.mark.parametrize("estado,esperado", [
    ("draft", ([], ["test_not_written", "test_not_written"])),
    ("ready", (["verified_by_dangling", "verified_by_dangling"], [])),
])
def test_dangling_so_com_build_report_pronto(tmp_path, estado, esperado):
    caminhos = _ate(tmp_path, "build_report")
    _reescreve(caminhos["build_report"], status=estado)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(b"def test_outro():\n    pass\n")
    assert _codigos(check(tmp_path)) == esperado


def test_teste_em_classe_conta(tmp_path):
    caminhos = _so_define(tmp_path)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(
        b"class TestX:\n    def test_y(self):\n        pass\n"
    )
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"]["ref"] = "tests/test_alvo.py::TestX::test_y"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], [])


def test_fact_not_collected_e_fact_encontrado(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "fact", "ref": "facts.json#abc123"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])
    (tmp_path / "facts.json").write_text(json.dumps([{"id": "abc123"}]), encoding="utf-8")
    assert _codigos(check(tmp_path)) == ([], [])


def test_fact_no_formato_real_de_facts(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "fact", "ref": "facts.json#f_abc123"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    dado = {"items": [{"id": "f_abc123", "kind": "spark.stage.shuffle", "attrs": {}}]}
    (tmp_path / "facts.json").write_bytes(json.dumps(dado).encode("utf-8"))
    assert _codigos(check(tmp_path)) == ([], [])


@pytest.mark.parametrize("item", [{"kind": "x"}, {"id": None}, {"id": ""}])
def test_fact_sem_id_nao_casa_com_none(tmp_path, item):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "fact", "ref": "facts.json#None"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    (tmp_path / "facts.json").write_bytes(json.dumps({"items": [item]}).encode("utf-8"))
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])


def test_funcval_not_run(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "funcval", "ref": "out/compare.json"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["funcval_not_run"])


def test_command_e_declarado_e_nao_conferido(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "command", "ref": "make x"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], [])


def _meta(arquivo):
    bloco, _ = split_frontmatter(arquivo.read_bytes().decode("utf-8"))
    return yaml.safe_load(bloco)


def _ate(tmp_path, fase):
    """Feature cortada logo depois de `fase`: nada abaixo fica stale."""
    caminhos = feature_limpa(tmp_path)
    corta = False
    for nome in PHASES:
        if corta and nome in caminhos:
            caminhos[nome].unlink()
        if nome == fase:
            corta = True
    return caminhos


def test_manifest_path_unknown(tmp_path):
    caminhos = _ate(tmp_path, "design")
    meta = _meta(caminhos["design"])
    meta["files"].append({"path": "sparkforge/sumiu.py", "action": "delete", "reason": "r"})
    _reescreve(caminhos["design"], files=meta["files"])
    assert _codigos(check(tmp_path)) == (["manifest_path_unknown"], [])


def _design_apaga_velho(tmp_path, fase):
    """Feature cortada depois de `fase`, com o design apagando um arquivo que existe."""
    caminhos = _ate(tmp_path, fase)
    (tmp_path / "sparkforge" / "velho.py").write_bytes(b"y = 2\n")
    meta = _meta(caminhos["design"])
    meta["files"].append({"path": "sparkforge/velho.py", "action": "delete", "reason": "r"})
    _reescreve(caminhos["design"], files=meta["files"])
    _restampa(tmp_path)
    return caminhos


def test_delete_some_depois_do_build_pronto(tmp_path):
    caminhos = _design_apaga_velho(tmp_path, "build_report")
    assert _codigos(check(tmp_path)) == ([], [])
    # o build apagou o arquivo, como o design mandava: nao e erro de manifesto
    (tmp_path / "sparkforge" / "velho.py").unlink()
    assert _codigos(check(tmp_path)) == ([], [])
    # com o build ainda em draft, o arquivo sumido volta a ser caminho desconhecido
    _reescreve(caminhos["build_report"], status="draft")
    assert _codigos(check(tmp_path)) == (["manifest_path_unknown"], [])


def test_delete_sumido_sem_build_report_e_recusado(tmp_path):
    _design_apaga_velho(tmp_path, "plan")
    (tmp_path / "sparkforge" / "velho.py").unlink()
    assert _codigos(check(tmp_path)) == (["manifest_path_unknown"], [])


def test_modify_sumido_e_recusado_mesmo_com_build_pronto(tmp_path):
    _ate(tmp_path, "build_report")
    (tmp_path / "sparkforge" / "existente.py").unlink()
    assert _codigos(check(tmp_path)) == (["manifest_path_unknown"], [])


def test_rollback_missing(tmp_path):
    caminhos = _ate(tmp_path, "design")
    _reescreve(caminhos["design"], decisions=[{"id": "D1", "choice": "c"}])
    assert _codigos(check(tmp_path)) == (["rollback_missing"], [])


def test_acceptance_uncovered_no_design(tmp_path):
    caminhos = _ate(tmp_path, "design")
    _reescreve(caminhos["design"], covers=[{"part": "p", "acceptance": []}])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["path"]) for r in recusa] == [
        ("acceptance_uncovered", "docs/sdd/F1/design.md")
    ]


def test_acceptance_uncovered_no_plan(tmp_path):
    caminhos = _ate(tmp_path, "plan")
    meta = _meta(caminhos["plan"])
    meta["tasks"][0]["covers"] = []
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["path"]) for r in recusa] == [
        ("acceptance_uncovered", "docs/sdd/F1/plan.md")
    ]


def test_task_without_test(tmp_path):
    caminhos = _ate(tmp_path, "plan")
    meta = _meta(caminhos["plan"])
    del meta["tasks"][0]["test"]
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == (["task_without_test"], [])


def test_teste_do_plan_ainda_nao_escrito(tmp_path):
    caminhos = _ate(tmp_path, "plan")
    meta = _meta(caminhos["plan"])
    meta["tasks"][0]["test"]["name"] = "test_futuro"
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == ([], ["test_not_written"])


def test_red_not_declared_ausente(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    meta = _meta(caminhos["build_report"])
    del meta["tasks"][0]["red"]
    _reescreve(caminhos["build_report"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == (["red_not_declared"], [])


def test_red_not_declared_exit_zero(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    meta = _meta(caminhos["build_report"])
    meta["tasks"][0]["red"]["exit"] = 0
    _reescreve(caminhos["build_report"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == (["red_not_declared"], [])


def test_task_pulada_nao_exige_red(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    _reescreve(caminhos["build_report"], tasks=[{"id": "T1", "status": "skipped"}])
    assert _codigos(check(tmp_path)) == ([], [])


def test_claim_without_evidence(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    _reescreve(caminhos["build_report"], claims=[{"text": "ficou 3x mais rapido"}])
    assert _codigos(check(tmp_path)) == (["claim_without_evidence"], [])


def test_hypothesis_open_at_ship(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], hypothesis_outcome=None)
    assert _codigos(check(tmp_path)) == (["hypothesis_open_at_ship"], [])


def test_registry_unchecked(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], registries=["surface_lock"])
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["registry_unchecked"]
    assert "generated_reference" in recusa[0]["unlock"]


def test_case_missing_sem_case_id(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    _reescreve(caminhos["define"], case_id=None)
    assert _codigos(check(tmp_path)) == (["case_missing"], [])


def test_case_missing_case_diferente(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    (tmp_path / ".sparkforge" / "case.yaml").write_bytes(b"case_id: OUTRO\n")
    assert _codigos(check(tmp_path)) == (["case_missing"], [])


def test_change_missing(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    (tmp_path / ".sparkforge" / "sandbox" / "S1").rmdir()
    assert _codigos(check(tmp_path)) == (["change_missing"], [])


@pytest.mark.parametrize("ident", ["../..", ".", "..", "../../docs", "S1/../S1", "S1\\..\\S1", ""])
def test_change_id_nao_escapa_do_sandbox(tmp_path, ident):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    _reescreve(caminhos["build_report"], change_id=ident)
    assert _codigos(check(tmp_path)) == (["change_missing"], [])


def test_change_id_que_e_arquivo_nao_serve(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    (tmp_path / ".sparkforge" / "sandbox" / "ARQ").write_bytes(b"x")
    _reescreve(caminhos["build_report"], change_id="ARQ")
    assert _codigos(check(tmp_path)) == (["change_missing"], [])


def test_case_id_compara_como_texto(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    (tmp_path / ".sparkforge" / "case.yaml").write_bytes(b"case_id: 123\n")
    _reescreve(caminhos["define"], case_id="123")
    assert _codigos(check(tmp_path)) == ([], [])


@pytest.mark.parametrize("conteudo", [b"case_id:\n", b"case_id: ''\n", b"outro: 1\n", b"- x\n"])
def test_case_vazio_nao_casa_com_nada(tmp_path, conteudo):
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    (tmp_path / ".sparkforge" / "case.yaml").write_bytes(conteudo)
    _reescreve(caminhos["define"], case_id="")
    assert _codigos(check(tmp_path)) == (["case_missing"], [])


def test_perfil_dev_nao_pede_case_nem_change(tmp_path):
    feature_limpa(tmp_path, "dev")
    assert not (tmp_path / ".sparkforge").exists()
    assert _codigos(check(tmp_path)) == ([], [])


def test_status_mostra_fase_e_bloqueio(tmp_path):
    feature_limpa(tmp_path, feature="F1")
    caminhos = _ate(tmp_path / "outro", "design")  # repo separado so para montar
    destino = tmp_path / "docs" / "sdd" / "F2"
    destino.mkdir(parents=True)
    for fase in ("define", "design"):
        texto = caminhos[fase].read_bytes().decode("utf-8").replace("feature: F1", "feature: F2")
        texto = texto.replace("docs/sdd/F1/", "docs/sdd/F2/")
        (destino / f"{fase}.md").write_bytes(texto.encode("utf-8"))
    stamp(tmp_path, "docs/sdd/F2/design.md")
    _reescreve(destino / "design.md", decisions=[{"id": "D1", "choice": "c"}])
    saida = status(tmp_path)
    assert saida["root"] == "docs/sdd"
    por_nome = {f["feature"]: f for f in saida["features"]}
    assert por_nome["F1"] == {
        "feature": "F1", "phase": "ship", "status": "done", "profile": "dev",
        "next_phase": None, "refused": [], "unresolved": [],
    }
    assert por_nome["F2"]["phase"] == "design"
    assert por_nome["F2"]["next_phase"] == "plan"
    assert por_nome["F2"]["refused"] == ["rollback_missing"]


@pytest.mark.parametrize("estraga", ["campo_extra", "yaml_quebrado"])
def test_status_com_fase_atual_invalida(tmp_path, estraga):
    caminhos = feature_limpa(tmp_path)
    if estraga == "campo_extra":
        _reescreve(caminhos["ship"], inventado=1)
    else:
        caminhos["ship"].write_bytes(b"---\nsdd: [\n---\n")
    item = status(tmp_path)["features"][0]
    assert item["phase"] == "ship"
    assert item["status"] is None
    assert item["profile"] is None
    assert "schema_invalid" in item["refused"]


def test_status_varre_uma_vez_so(tmp_path, monkeypatch):
    import sparkforge.sdd.checks as modulo_checks
    import sparkforge.sdd.load as modulo_load

    feature_limpa(tmp_path)
    chamadas = []
    original = modulo_load.varrer_source_files

    def conta(*args, **kwargs):
        chamadas.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(modulo_load, "varrer_source_files", conta)
    assert status(tmp_path)["features"][0]["phase"] == "ship"
    assert len(chamadas) == 1
    assert modulo_checks.check(tmp_path)["ok"] is True
    assert len(chamadas) == 2


def test_registry_unchecked_nao_repete_registro_compartilhado(tmp_path, monkeypatch):
    import sparkforge.sdd.checks as modulo_checks

    tipos = {
        "tipo_a": {"section": "A", "registries": ["r1", "r2"]},
        "tipo_b": {"section": "B", "registries": ["r2", "r3"]},
    }
    monkeypatch.setattr(modulo_checks, "change_kinds", lambda: tipos)
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["define"], change_kinds=["tipo_a", "tipo_b"])
    _reescreve(caminhos["ship"], registries=[])
    _restampa(tmp_path)
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["registry_unchecked"] * 3
    assert [r["unlock"].split(" ")[0] for r in recusa] == ["r1", "r2", "r3"]


def test_status_sem_raiz(tmp_path):
    saida = status(tmp_path)
    assert saida["features"] == []
    assert [u["code"] for u in saida["unresolved"]] == ["root_missing"]


def test_cli_check_ok_e_recusa(tmp_path, capsys):
    caminhos = feature_limpa(tmp_path)
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    _reescreve(caminhos["ship"], hypothesis_outcome=None)
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 1
    saida = json.loads(capsys.readouterr().out)
    assert [r["code"] for r in saida["refused"]] == ["hypothesis_open_at_ship"]


def test_cli_so_lacuna_sai_zero(tmp_path, capsys):
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_cli_status_e_stamp(tmp_path, capsys):
    caminhos = feature_limpa(tmp_path)
    assert main(["sdd", "status", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["features"][0]["phase"] == "ship"
    _reescreve(caminhos["build_report"], claims=[{"text": "t", "evidence_ref": "x"}])
    assert main(["sdd", "stamp", "--repo", str(tmp_path), "docs/sdd/F1/ship.md"]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True


def test_cli_root_alternativo(tmp_path, capsys):
    feature_limpa(tmp_path)
    # copia: o upstream declarado continua apontando para docs/sdd, que segue existindo
    shutil.copytree(tmp_path / "docs" / "sdd", tmp_path / "specs")
    main(["sdd", "check", "--repo", str(tmp_path), "--root", "specs"])
    assert json.loads(capsys.readouterr().out)["features"] == ["F1"]
    assert main(["sdd", "status", "--repo", str(tmp_path), "--root", "specs"]) == 0
    assert json.loads(capsys.readouterr().out)["root"] == "specs"
    argv = ["sdd", "stamp", "--repo", str(tmp_path), "--root", "specs", "specs/F1/ship.md"]
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is False
    # sem --root, o mesmo arquivo nao e artefato da raiz padrao
    assert main(["sdd", "stamp", "--repo", str(tmp_path), "specs/F1/ship.md"]) == 2
    assert "not_an_artifact" in capsys.readouterr().err


def test_core_erros_acionaveis(tmp_path):
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_check(str(tmp_path / "nao-existe"))
    assert "sparkforge" in erro.value.message
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_status(str(tmp_path / "nao-existe"))
    assert "sparkforge sdd status" in erro.value.message
    # sem raiz, feature pedida nao e erro: a lacuna root_missing ja diz o que falta
    sem_raiz = _core.sdd_check(str(tmp_path), feature="NAO_HA")
    assert [u["code"] for u in sem_raiz["unresolved"]] == ["root_missing"]
    feature_limpa(tmp_path)
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_check(str(tmp_path), feature="NAO_HA")
    assert "sparkforge sdd status" in erro.value.message
    assert erro.value.exit_code == 2
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_stamp(str(tmp_path), "docs/sdd/F1/define.md")
    assert "sparkforge sdd stamp" in erro.value.message
    assert "upstream_missing" in erro.value.message
    assert erro.value.exit_code == 2


def test_core_feature_so_com_lacuna_de_pulo_nao_e_erro(tmp_path):
    # a feature existe no disco, mas a varredura a podou: a lacuna diz por que
    feature_limpa(tmp_path, feature="BUILD")
    relatorio = _core.sdd_check(str(tmp_path), feature="BUILD")
    assert relatorio["features"] == []
    assert [u["code"] for u in relatorio["unresolved"]] == ["path_skipped"]


def _valida(nome: str, resposta: dict) -> dict:
    jsonschema.validate(resposta, TOOLS[nome]["outputSchema"])
    return resposta


def test_paridade_cli_mcp(tmp_path, capsys):
    # `call_tool` devolve o payload do verbo sem envelope: compara direto
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], registries=[])
    (tmp_path / "docs" / "sdd" / "secrets.md").write_bytes(b"x")
    main(["sdd", "check", "--repo", str(tmp_path)])
    pela_cli = json.loads(capsys.readouterr().out)
    pelo_mcp = _valida(
        "sparkforge_sdd_check", call_tool("sparkforge_sdd_check", {"repo": str(tmp_path)})
    )
    assert pelo_mcp == pela_cli
    assert pelo_mcp["refused"] and pelo_mcp["unresolved"]
    main(["sdd", "status", "--repo", str(tmp_path)])
    pelo_mcp = _valida(
        "sparkforge_sdd_status", call_tool("sparkforge_sdd_status", {"repo": str(tmp_path)})
    )
    assert pelo_mcp == json.loads(capsys.readouterr().out)
    assert [u["code"] for u in pelo_mcp["unresolved"]] == ["path_skipped"]


def test_schemas_de_saida_cobrem_raiz_ausente_e_erro(tmp_path):
    _valida("sparkforge_sdd_status", call_tool("sparkforge_sdd_status", {"repo": str(tmp_path)}))
    _valida("sparkforge_sdd_check", call_tool("sparkforge_sdd_check", {"repo": str(tmp_path)}))
    ausente = {"repo": str(tmp_path / "nao-existe")}
    for nome in ("sparkforge_sdd_check", "sparkforge_sdd_status"):
        erro = _valida(nome, call_tool(nome, ausente))
        assert "sparkforge" in erro["error"]
    feature_limpa(tmp_path)
    erro = _valida(
        "sparkforge_sdd_stamp",
        call_tool("sparkforge_sdd_stamp", {"repo": str(tmp_path), "path": "docs/sdd/F1/define.md"}),
    )
    assert erro["exit_code"] == 2
    assert "sparkforge sdd stamp" in erro["error"]
    erro = _valida(
        "sparkforge_sdd_check",
        call_tool("sparkforge_sdd_check", {"repo": str(tmp_path), "feature": "NAO_HA"}),
    )
    assert "sparkforge sdd status" in erro["error"]


def test_classes_das_tools():
    assert TOOLS["sparkforge_sdd_check"]["annotations"]["readOnlyHint"] is True
    assert TOOLS["sparkforge_sdd_status"]["annotations"]["readOnlyHint"] is True
    assert TOOLS["sparkforge_sdd_stamp"]["annotations"]["readOnlyHint"] is False
    assert "sparkforge_sdd_stamp" in journaled()
    assert "sparkforge_sdd_check" not in journaled()
    assert "sparkforge_sdd_status" not in journaled()
    assert set(TOOLS["sparkforge_sdd_stamp"]["inputSchema"]["properties"]) == {
        "repo", "path", "root_path",
    }


def _eventos(repo: Path) -> list[dict]:
    linhas = journal_path(repo).read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas]


def test_stamp_pelo_mcp_grava_no_journal(tmp_path):
    # a raiz do journal e o `repo`; nao precisa de .sparkforge/case.yaml
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["build_report"], claims=[{"text": "t", "evidence_ref": "x"}])
    resposta = _valida(
        "sparkforge_sdd_stamp",
        call_tool("sparkforge_sdd_stamp", {"repo": str(tmp_path), "path": "docs/sdd/F1/ship.md"}),
    )
    assert resposta["changed"] is True
    assert "journal" not in resposta
    eventos = _eventos(tmp_path)
    assert [e["event"] for e in eventos] == ["started", "finished"]
    assert eventos[0]["tool"] == "sparkforge_sdd_stamp"
    assert eventos[0]["port"] == "mcp"
    assert eventos[1]["outcome"] == "ok"
    ship = caminhos["ship"].read_bytes()
    assert eventos[1]["outputs"] == {
        "docs/sdd/F1/ship.md": hashlib.sha256(ship).hexdigest(),
    }


def test_stamp_pela_cli_grava_no_journal_e_check_nao(tmp_path, capsys):
    caminhos = feature_limpa(tmp_path)
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 0
    assert not journal_path(tmp_path).exists()
    _reescreve(caminhos["build_report"], claims=[{"text": "t", "evidence_ref": "x"}])
    assert main(["sdd", "stamp", "--repo", str(tmp_path), "docs/sdd/F1/ship.md"]) == 0
    capsys.readouterr()
    eventos = _eventos(tmp_path)
    assert [(e["event"], e.get("port")) for e in eventos] == [
        ("started", "cli"), ("finished", None),
    ]
    assert list(eventos[1]["outputs"]) == ["docs/sdd/F1/ship.md"]
