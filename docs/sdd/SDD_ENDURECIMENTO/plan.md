---
sdd: 1
feature: SDD_ENDURECIMENTO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_ENDURECIMENTO/design.md
  sha256: "4d0186bbcee9e33897494b750d2a500d185affda770caa10fee3e0c74cc297ac"
tasks:
  - id: T1
    files: [.gitattributes, evals/agentic/sdd/README.md, tests/test_sdd_eval_suite.py]
    covers: [AC11]
    test: {path: tests/test_sdd_eval_suite.py, name: test_notas_de_hash_e_de_baseline}
  - id: T2
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC5]
    test: {path: tests/test_sdd.py, name: test_moved_de_outra_mudanca}
  - id: T3
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC6]
    test: {path: tests/test_sdd.py, name: test_relatorio_por_symlink_nao_escapa}
  - id: T4
    files: [sparkforge/sdd/checks.py, sparkforge/sdd/schema/ship.json, tests/test_sdd.py, tests/test_sdd_operator.py]
    covers: [AC1, AC2, AC3, AC4, AC7, AC8]
    test: {path: tests/test_sdd.py, name: test_ship_done_sem_evidencia_recusa}
  - id: T5
    files: [docs/sdd/CONTRATO.md, docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md, tests/test_sdd.py]
    covers: [AC9]
    test: {path: tests/test_sdd.py, name: test_contrato_lista_todo_codigo}
  - id: T6
    files: [skills/sdd-ship/SKILL.md, skills/sdd-build/SKILL.md, docs/sdd/README.md, docs/surface.lock.json, .claude/skills, tests/test_sdd_operator.py]
    covers: [AC10]
    test: {path: tests/test_sdd_operator.py, name: test_skills_ensinam_a_evidencia_do_ship}
---

# SDD_ENDURECIMENTO — plano

Regras que mordem toda tarefa: edição só pela ferramenta de edição, LF,
`.claude/agents/README.md` fica fora da árvore e fora do índice, commit por
`git commit -F <arquivo>`, um por tarefa. `SF` abaixo é
`python -c "import sys;from sparkforge.adapters.cli import main;sys.exit(main(sys.argv[1:]))"`.

## T1 — notas de hash e de baseline

1. Teste, em `tests/test_sdd_eval_suite.py`:

```python
def test_notas_de_hash_e_de_baseline():
    atributos = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    bloco = atributos.split("# `fixtures/sdd/`", 1)[1].split("fixtures/sdd/** -text", 1)[0]
    assert "text_sha256" in bloco
    assert "BYTES" not in bloco
    baseline = (SUITE_DIR / "README.md").read_text(encoding="utf-8").split("## Baseline", 1)[1]
    assert "--repeat 1" in baseline
    assert "duas invocações" in baseline
```

2. `python -m pytest tests/test_sdd_eval_suite.py::test_notas_de_hash_e_de_baseline -q`:
   `AssertionError` sobre `text_sha256`.
3. Reescrever o comentário de `fixtures/sdd/**` no `.gitattributes`: o gate
   compara `text_sha256` (CRLF normalizado), então o CRLF não põe a cascata em
   `upstream_stale`; `-text` fica para os bytes da fixture serem os mesmos em
   toda plataforma (o gerador gravou bytes, e o golden e a suíte leem a cópia
   do checkout). No README da suite, a seção *Baseline* diz que `r1` e `r2`
   vieram de duas invocações `--repeat 1` (por isso o `run_id` de `r2` termina
   em `r1`).
4. O mesmo comando, verde.
5. `python -m pytest tests/test_sdd_eval_suite.py tests/test_fixtures_golden_sdd.py -q`.
6. Commit `docs(sdd): text hash note and baseline provenance`.

## T2 — moved de outra mudança

1. Teste, em `tests/test_sdd.py`:

```python
def test_moved_de_outra_mudanca(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    _relatorio_de_mudanca(tmp_path, "sandbox", "S2", resolvidos=["SF-PY-012"])
    tarefa = {"id": "T1", "status": "done",
              "moved": {"change_id": "S2", "resolved": ["SF-PY-012"]}}
    _reescreve(caminhos["build_report"], tasks=[tarefa])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [
        ("moved_change_mismatch", "tasks/0/moved/change_id"),
    ]
    assert "S1" in recusa[0]["unlock"] and "S2" in recusa[0]["unlock"]
```

2. `python -m pytest tests/test_sdd.py::test_moved_de_outra_mudanca -q`: a
   lista de recusas sai vazia.
3. Em `sparkforge/sdd/checks.py::_conferir_movido`, antes de ler o relatório:

```python
    ident = movido["change_id"]
    do_build = _texto_ou_none(artefato.meta.get("change_id"))
    if ident != do_build:
        ctx.recusa("moved_change_mismatch", artefato.path, f"{campo}/change_id",
                   f"{dono}: moved.change_id {ident} nao e o change_id do build "
                   f"({do_build or 'vazio'}); a tarefa prova a mudanca que o build registrou")
        return
```

4. O mesmo comando, verde; depois `python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q`.
5. Commit `fix(sdd): refuse moved from another change`.

## T3 — relatório confinado

1. Teste, em `tests/test_sdd.py`:

```python
def test_relatorio_por_symlink_nao_escapa(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    tarefa = {"id": "T1", "status": "done",
              "moved": {"change_id": "S1", "resolved": ["SF-PY-012"]}}
    _reescreve(caminhos["build_report"], tasks=[tarefa])
    fora = tmp_path / "fora.json"
    fora.write_bytes(json.dumps({"new": [], "resolved": [{"rule_id": "SF-PY-012"}]})
                     .encode("utf-8"))
    try:
        (tmp_path / ".sparkforge" / "sandbox" / "S1" / "report.json").symlink_to(fora)
    except OSError as erro:
        pytest.skip(f"symlink indisponivel: {erro}")
    assert _codigos(check(tmp_path)) == (["moved_not_observed"], [])
```

2. `python -m pytest tests/test_sdd.py::test_relatorio_por_symlink_nao_escapa -q`:
   sai `([], [])`.
3. Em `checks.py`, os arquivos de relatório passam por `resolve_within`:

```python
def _arquivos_de_relatorio(repo: Path, ident: str) -> list[Path]:
    """Os relatorios de `ident` que existem, confinados a pasta da mudanca (symlink incluso)."""
    achados: list[Path] = []
    for pasta, nome in _pastas_da_mudanca(repo, ident):
        alvo = resolve_within(pasta, nome)
        if alvo is not None and alvo.is_file():
            achados.append(alvo)
    return achados


def _relatorio_da_mudanca(repo: Path, ident: str) -> dict[str, Any] | None:
    for arquivo in _arquivos_de_relatorio(repo, ident):
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(dado, dict):
            return dado
    return None
```

4. O mesmo comando, verde; `python -m pytest tests/test_sdd.py -q`.
5. Commit `fix(sdd): confine change report paths`.

## T4 — evidência do ship

1. Testes, em `tests/test_sdd.py` (o de T4 é o primeiro; os outros três e o
   ajuste de `feature_limpa` entram no mesmo passo):

```python
def _operator_com_moved(repo: Path, ident: str = "S1") -> dict[str, Path]:
    caminhos = feature_limpa(repo, "operator")
    tarefa = {"id": "T1", "status": "done",
              "moved": {"change_id": ident, "resolved": ["SF-PY-012"]}}
    _reescreve(caminhos["build_report"], change_id=ident, tasks=[tarefa])
    _restampa(repo)
    return caminhos


def _relatorio_sha(repo: Path, ident: str = "S1") -> str:
    return text_sha256(repo / ".sparkforge" / "sandbox" / ident / "report.json")


def test_ship_done_sem_evidencia_recusa(tmp_path):
    caminhos = _operator_com_moved(tmp_path, "FALSO")
    shutil.rmtree(tmp_path / ".sparkforge" / "sandbox")
    _reescreve(caminhos["ship"], evidence=None)
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("ship_evidence_missing", "evidence")]
    # no dev nada muda, e evidence nao e campo do dev
    dev = tmp_path / "dev"
    caminhos_dev = feature_limpa(dev)
    assert _codigos(check(dev)) == ([], [])
    _reescreve(caminhos_dev["ship"], evidence=[{"change_id": "S1", "report_sha256": "0" * 64}])
    assert [(r["code"], r["field"]) for r in check(dev)["refused"]] == [
        ("schema_invalid", "evidence"),
    ]


def test_ship_done_com_evidencia_e_sem_relatorio_e_historia(tmp_path):
    caminhos = _operator_com_moved(tmp_path, "FALSO")
    shutil.rmtree(tmp_path / ".sparkforge" / "sandbox")
    _reescreve(caminhos["ship"], evidence=[{"change_id": "FALSO", "report_sha256": "a" * 64}])
    assert _codigos(check(tmp_path)) == ([], [])
    # a entrada precisa nomear o id citado
    _reescreve(caminhos["ship"], evidence=[{"change_id": "OUTRO", "report_sha256": "a" * 64}])
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["ship_evidence_missing"]
    assert "FALSO" in recusa[0]["unlock"]


def test_ship_done_com_relatorio_que_contradiz(tmp_path):
    caminhos = _operator_com_moved(tmp_path)
    _relatorio_de_mudanca(tmp_path, "sandbox", "S1")
    _reescreve(caminhos["ship"], evidence=[
        {"change_id": "S1", "report_sha256": _relatorio_sha(tmp_path)},
    ])
    assert _codigos(check(tmp_path)) == (["moved_not_observed"], [])
    _relatorio_de_mudanca(tmp_path, "sandbox", "S1", resolvidos=["SF-PY-012"])
    _reescreve(caminhos["ship"], evidence=[
        {"change_id": "S1", "report_sha256": _relatorio_sha(tmp_path)},
    ])
    assert _codigos(check(tmp_path)) == ([], [])


def test_ship_done_com_sha_divergente(tmp_path):
    caminhos = _operator_com_moved(tmp_path)
    _relatorio_de_mudanca(tmp_path, "sandbox", "S1", resolvidos=["SF-PY-012"])
    _reescreve(caminhos["ship"], evidence=[{"change_id": "S1", "report_sha256": "f" * 64}])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [
        ("ship_evidence_mismatch", "evidence/0/report_sha256"),
    ]
    assert _relatorio_sha(tmp_path) in recusa[0]["unlock"]
```

   `feature_limpa`, no operator, grava no ship
   `evidence: [{change_id: S1, report_sha256: "0"*64}]` (S1 sem relatório:
   nada a comparar).

2. `python -m pytest tests/test_sdd.py::test_ship_done_sem_evidencia_recusa -q`:
   a recusa sai vazia (o furo).
3. Código, em `checks.py`:

```python
def _historia(ctx: _Contexto, ident: str) -> bool:
    """Ship done E nenhum relatorio da mudanca: a referencia virou historia."""
    return _ship_feito(ctx) and not _arquivos_de_relatorio(ctx.repo, ident)


def _ids_citados(ctx: _Contexto) -> list[str]:
    """Os change_id em que a feature se apoia: o do build, o de moved e o de finding."""
    ids: list[str] = []
    build = ctx.artefatos.get("build_report")
    if build is not None:
        principal = _texto_ou_none(build.meta.get("change_id"))
        if principal:
            ids.append(principal)
        ids.extend(t["moved"]["change_id"] for t in build.meta["tasks"] if t.get("moved"))
    plano = ctx.artefatos.get("plan")
    if plano is not None:
        for tarefa in plano.meta["tasks"]:
            prova = tarefa.get("proof")
            if prova and prova["kind"] == "finding" and prova["ref"].partition("#")[0]:
                ids.append(prova["ref"].partition("#")[0])
    return list(dict.fromkeys(ids))


def _gate_evidence(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    entradas = artefato.meta.get("evidence")
    if artefato.meta["profile"] != "operator":
        if entradas is not None:
            ctx.recusa("schema_invalid", artefato.path, "evidence",
                       "evidence so vale no perfil operator; o ship dev nao cita mudanca")
        return
    citados = _ids_citados(ctx)
    gravados = {entrada["change_id"] for entrada in entradas or []}
    faltam = [ident for ident in citados if ident not in gravados]
    if not entradas or faltam:
        vistos = "; ".join(filter(None, (_hashes_vistos(ctx, i) for i in faltam or citados)))
        ctx.recusa("ship_evidence_missing", artefato.path, "evidence",
                   "grave evidence: [{change_id, report_sha256}] para "
                   f"{', '.join(faltam or citados) or 'o change_id do build'}, com o "
                   f"text_sha256 do relatorio que o ship leu ({vistos or 'nenhum relatorio'})")
    for indice, entrada in enumerate(entradas or []):
        for arquivo in _arquivos_de_relatorio(ctx.repo, entrada["change_id"]):
            atual = _sha_ou_vazio(arquivo)
            if atual != entrada["report_sha256"]:
                ctx.recusa("ship_evidence_mismatch", artefato.path,
                           f"evidence/{indice}/report_sha256",
                           f"{ctx.rel(arquivo)} tem text_sha256 {atual or 'ilegivel'}, e o "
                           f"ship gravou {entrada['report_sha256']}; o relatorio mudou depois "
                           "do ship: leia-o de novo antes de regravar o hash")


def _sha_ou_vazio(arquivo: Path) -> str:
    try:
        return text_sha256(arquivo)
    except OSError:
        return ""


def _hashes_vistos(ctx: _Contexto, ident: str) -> str:
    """`ident: <rel>=<sha>, ...` dos relatorios presentes, para o ship copiar."""
    pares = [f"{ctx.rel(a)}={_sha_ou_vazio(a)}" for a in _arquivos_de_relatorio(ctx.repo, ident)]
    return f"{ident}: {', '.join(pares)}" if pares else ""
```

Uma recusa só por ship: sem `evidence`, ou com ids citados sem entrada.

   O `unlock` de `ship_evidence_missing` traz o `text_sha256` de cada relatório
   presente do id, para o ship gravá-lo depois de ler o relatório; o de
   `ship_evidence_mismatch` traz os dois hashes. `_conferir_movido` e
   `_conferir_achado` trocam `_ship_feito(ctx)` por `_historia(ctx, ident)`
   (o `ident` resolvido primeiro); `_gate_case` e `_gate_change` ficam. O
   `_gate_evidence` entra no fim de `_GATES["ship"]`. `schema/ship.json`
   ganha `evidence` (lista de `{change_id: texto não vazio, report_sha256:
   64 hex}`, sem campo extra).

4. `python -m pytest tests/test_sdd.py -q` verde. Em
   `tests/test_sdd_operator.py`, `_feature_operator` recebe `evidence` e o
   fluxo grava o `text_sha256` do `report.json` do sandbox; depois de
   `change propose`, com os dois relatórios presentes, o check segue limpo
   (prova de D2); depois de limpar sandbox e proposal, segue limpo pela
   evidência. `python -m pytest tests/test_sdd.py tests/test_sdd_operator.py tests/test_sdd_eval_suite.py tests/test_fixtures_golden_sdd.py -q`
   e `SF sdd check --repo .`.
5. Commit `fix(sdd): keep operator evidence checked after ship`.

## T5 — contrato vivo

1. Teste, em `tests/test_sdd.py`:

```python
_EMISSORES = ("recusa", "lacuna", "StampError")


def _codigos_emitidos() -> set[str]:
    codigos: set[str] = set()
    dinamicos: list[str] = []
    for nome in ("checks.py", "stamp.py"):
        arvore = ast.parse((ROOT / "sparkforge" / "sdd" / nome).read_bytes())
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call):
                funcao = no.func
                chamado = funcao.attr if isinstance(funcao, ast.Attribute) else getattr(
                    funcao, "id", None)
                if chamado not in _EMISSORES:
                    continue
                primeiro = no.args[0] if no.args else None
                if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
                    codigos.add(primeiro.value)
                else:
                    dinamicos.append(f"{nome}:{no.lineno}")
            elif isinstance(no, ast.Dict):
                for chave, valor in zip(no.keys, no.values):
                    if (isinstance(chave, ast.Constant) and chave.value == "code"
                            and isinstance(valor, ast.Constant)):
                        codigos.add(valor.value)
    assert not dinamicos, dinamicos
    return codigos


_LINHA_DE_CODIGO = re.compile(r"^\| `([a-z_]+)` \|")


def _codigos_do_contrato() -> set[str]:
    codigos: set[str] = set()
    dentro = False
    for linha in (ROOT / "docs" / "sdd" / "CONTRATO.md").read_text(encoding="utf-8").splitlines():
        if linha.startswith("| código |"):
            dentro = True
            continue
        if not linha.startswith("|"):
            dentro = False
            continue
        achado = _LINHA_DE_CODIGO.match(linha)
        if dentro and achado:
            codigos.add(achado.group(1))
    return codigos


def test_contrato_lista_todo_codigo():
    emitidos = _codigos_emitidos()
    assert {"ship_evidence_missing", "moved_change_mismatch", "path_skipped",
            "not_an_artifact"} <= emitidos
    assert _codigos_do_contrato() == emitidos
```

2. `python -m pytest tests/test_sdd.py::test_contrato_lista_todo_codigo -q`:
   `FileNotFoundError` do `CONTRATO.md`, o documento sob teste.
3. Escrever `docs/sdd/CONTRATO.md` a partir de `checks.py`, `stamp.py` e
   `schema/*.json`; no topo do spec congelado, um aviso de uma linha
   apontando o contrato vivo.
4. O mesmo comando, verde.
5. Commit `docs(sdd): live gate contract with a code-level lock`.

## T6 — skills e README

1. Teste, em `tests/test_sdd_operator.py`:

```python
def test_skills_ensinam_a_evidencia_do_ship():
    def operador(nome):
        texto = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        return texto, texto.split("## Perfil operator", 1)[1].split("\n## ", 1)[0]

    ship, ship_operador = operador("sdd-ship")
    for trecho in ("evidence", "report_sha256", "ship_evidence_missing",
                   "ship_evidence_mismatch"):
        assert trecho in ship_operador, trecho
    build, build_operador = operador("sdd-build")
    assert "moved_change_mismatch" in build_operador
    for texto in (ship, build):
        assert "docs/sdd/CONTRATO.md" in texto
    readme = (ROOT / "docs" / "sdd" / "README.md").read_text(encoding="utf-8")
    for trecho in ("evidence", "ship_evidence_missing", "moved_change_mismatch",
                   "CONTRATO.md"):
        assert trecho in readme, trecho
    congelado = (ROOT / "docs" / "superpowers" / "specs"
                 / "2026-09-16-sdd-nucleo-design.md").read_text(encoding="utf-8")
    assert "docs/sdd/CONTRATO.md" in "\n".join(congelado.splitlines()[:12])
```

2. `python -m pytest tests/test_sdd_operator.py::test_skills_ensinam_a_evidencia_do_ship -q`:
   `AssertionError` em `evidence`.
3. Editar as duas skills e o README (a regra da história com evidência sumida
   substitui a frase "a conferência de moved/finding para").
4. O mesmo comando, verde; `python scripts/sync_skills.py`,
   `python scripts/sync_skills.py --check`,
   `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_sdd_skills.py -q`,
   `python scripts/gen_reference_docs.py`,
   `python scripts/check_surface_lock.py --update`.
5. Commit `docs(sdd): teach ship evidence in skills` com o delta de bytes.
