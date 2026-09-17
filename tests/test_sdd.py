"""Nucleo do SDD proprio: contrato conferivel e gates com nome.

Nenhuma fixture estatica: hash de upstream gravado em arquivo versionado e o caso
que o checkout do Windows com `core.autocrlf=true` ja quebrou (PR #63). Toda
feature e montada em `tmp_path`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

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


def test_status_sem_raiz(tmp_path):
    saida = status(tmp_path)
    assert saida["features"] == []
    assert [u["code"] for u in saida["unresolved"]] == ["root_missing"]
