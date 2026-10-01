---
sdd: 1
feature: SDD_OPERATOR_DURAVEL
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_OPERATOR_DURAVEL/design.md
  sha256: "8e009ca0926d2111c0c25bd84eab88fdde36360fc4563fa790a1eff089eaaa8c"
tasks:
  - id: T1
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC2]
    test: {path: tests/test_sdd.py, name: test_change_id_aceita_proposal}
  - id: T2
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC3]
    test: {path: tests/test_sdd.py, name: test_case_e_change_historicos_depois_do_ship}
  - id: T3
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC4]
    test: {path: tests/test_sdd.py, name: test_fact_por_kind}
  - id: T4
    files: [sparkforge/sdd/checks.py, sparkforge/sdd/schema/plan.json, tests/test_sdd.py]
    covers: [AC5]
    test: {path: tests/test_sdd.py, name: test_proof_de_tarefa_operator}
  - id: T5
    files: [sparkforge/sdd/checks.py, sparkforge/sdd/schema/build_report.json, tests/test_sdd.py]
    covers: [AC6, AC7]
    test: {path: tests/test_sdd.py, name: test_moved_confere_o_relatorio}
  - id: T6
    files: [tests/test_sdd_operator.py]
    covers: [AC1]
    test: {path: tests/test_sdd_operator.py, name: test_fluxo_operator_ponta_a_ponta}
  - id: T7
    files: [skills/sdd-define/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-build/SKILL.md, skills/sdd-ship/SKILL.md, docs/sdd/README.md, docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md, tests/test_sdd_operator.py]
    covers: [AC8, AC9]
    test: {path: tests/test_sdd_operator.py, name: test_skills_ensinam_o_operador_duravel}
---

# SDD_OPERATOR_DURAVEL — plano

Regras que mordem toda tarefa: edição só por ferramenta de edição (nada de
`write_text` em script), fim de linha LF, comentários de código em português sem
acento, um commit por tarefa com `git commit -F <arquivo>`. Gates vizinhos de
cada tarefa de código: `python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q`.

Auxiliar de teste usado por T4 e T5, criado em T4 logo abaixo de
`test_perfil_dev_nao_pede_case_nem_change` em `tests/test_sdd.py`:

```python
def _relatorio_de_mudanca(repo: Path, base: str, ident: str, novos=(), resolvidos=()) -> None:
    """Grava o relatorio que `change sandbox` (ou `change propose`) deixaria."""
    nome = "report.json" if base == "sandbox" else "evidence/sandbox_report.json"
    arquivo = repo / ".sparkforge" / base / ident / nome
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    dado = {
        "id": ident,
        "new": [{"rule_id": r, "subject": {"file": "job.py"}} for r in novos],
        "resolved": [{"rule_id": r, "subject": {"file": "job.py"}} for r in resolvidos],
    }
    arquivo.write_bytes(json.dumps(dado).encode("utf-8"))
```

## T1 — `change_id` pela proposal

Teste, depois de `test_change_id_que_e_arquivo_nao_serve`:

```python
def test_change_id_aceita_proposal(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    (tmp_path / ".sparkforge" / "sandbox" / "S1").rmdir()
    assert _codigos(check(tmp_path)) == (["change_missing"], [])
    # o sandbox foi limpo, mas o pacote de `change propose` guarda o mesmo id
    (tmp_path / ".sparkforge" / "proposal" / "S1").mkdir(parents=True)
    assert _codigos(check(tmp_path)) == ([], [])
    # a proposal passa pelo mesmo confinamento: arquivo com o nome do id nao serve
    (tmp_path / ".sparkforge" / "proposal" / "S1").rmdir()
    (tmp_path / ".sparkforge" / "proposal" / "S1").write_bytes(b"x")
    assert _codigos(check(tmp_path)) == (["change_missing"], [])
```

Vermelho: `python -m pytest tests/test_sdd.py::test_change_id_aceita_proposal -q`
falha no segundo `assert` (`change_missing` com a proposal presente).

Código, em `sparkforge/sdd/checks.py`: importar
`from sparkforge.change.proposal import PROPOSAL_DIR` e `PurePosixPath`, e trocar
o corpo de `_gate_change`:

```python
_BASES_DA_MUDANCA: tuple[tuple[PurePosixPath, str], ...] = (
    (SANDBOX_DIR, "report.json"),
    (PROPOSAL_DIR, "evidence/sandbox_report.json"),
)


def _pastas_da_mudanca(repo: Path, ident: str) -> list[tuple[Path, str]]:
    """As pastas de `ident` que existem, com o relatorio que cada uma guarda."""
    # um segmento so, sem separador: `..`, `.` e `a/../b` nao sao id de mudanca
    if not ident or "/" in ident or "\\" in ident or ident in (".", ".."):
        return []
    achadas: list[tuple[Path, str]] = []
    for base_rel, relatorio in _BASES_DA_MUDANCA:
        base = repo / base_rel
        alvo = resolve_within(base, ident)
        if alvo is not None and alvo.parent == base.resolve() and alvo.is_dir():
            achadas.append((alvo, relatorio))
    return achadas


def _gate_change(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if artefato.meta["profile"] != "operator":
        return
    ident = str(artefato.meta.get("change_id") or "")
    if not _pastas_da_mudanca(ctx.repo, ident):
        ctx.recusa("change_missing", artefato.path, "change_id",
                   "o build do operador passa por `sparkforge change sandbox`; registre o id "
                   "em change_id (vale enquanto existir .sparkforge/sandbox/<id>/ ou "
                   ".sparkforge/proposal/<id>/)")
```

Verde: o mesmo comando, depois `python -m pytest tests/test_sdd.py -q`. Commit
`feat(sdd): accept a proposal package as the operator change`.

## T2 — referência histórica depois do ship

Teste, depois de `test_change_id_aceita_proposal`:

```python
def test_case_e_change_historicos_depois_do_ship(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    # depois da entrega: outro case aberto e o sandbox limpo
    (tmp_path / ".sparkforge" / "case.yaml").write_bytes(b"case_id: OUTRO\n")
    (tmp_path / ".sparkforge" / "sandbox" / "S1").rmdir()
    assert _codigos(check(tmp_path)) == ([], [])
    # com o ship ainda aberto, as duas referencias voltam a valer
    _reescreve(caminhos["ship"], status="ready")
    assert _codigos(check(tmp_path)) == (["case_missing", "change_missing"], [])
    # sem ship nenhum, idem
    caminhos["ship"].unlink()
    assert _codigos(check(tmp_path)) == (["case_missing", "change_missing"], [])
```

Vermelho: `python -m pytest tests/test_sdd.py::test_case_e_change_historicos_depois_do_ship -q`
falha no primeiro `assert`.

Código:

```python
def _ship_feito(ctx: _Contexto) -> bool:
    """O ship carregou com status done: case e mudanca citados viraram historia."""
    ship = ctx.artefatos.get("ship")
    return ship is not None and ship.meta["status"] == "done"
```

e a primeira linha de `_gate_case` e de `_gate_change` passa a ser
`if artefato.meta["profile"] != "operator" or _ship_feito(ctx): return`.
Commit `feat(sdd): treat case and change as history once ship is done`.

## T3 — fact por kind

Teste, depois de `test_fact_sem_id_nao_casa_com_none`:

```python
def test_fact_por_kind(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {
        "kind": "fact", "ref": "facts.json#kind:pyspark.conf_set",
    }
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])
    dado = {"items": [{"id": "f1", "kind": "spark.stage.shuffle"}]}
    (tmp_path / "facts.json").write_bytes(json.dumps(dado).encode("utf-8"))
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])
    dado["items"].append({"id": "f2", "kind": "pyspark.conf_set"})
    (tmp_path / "facts.json").write_bytes(json.dumps(dado).encode("utf-8"))
    assert _codigos(check(tmp_path)) == ([], [])
    # o id continua valendo, e `kind:` vazio nao casa com nada
    meta["acceptance"][0]["verified_by"]["ref"] = "facts.json#f1"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], [])
    meta["acceptance"][0]["verified_by"]["ref"] = "facts.json#kind:"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])
```

Vermelho: `python -m pytest tests/test_sdd.py::test_fact_por_kind -q` falha no
terceiro `assert`.

Código: `_ids_de_fact` sai; entram

```python
_SELETOR_KIND = "kind:"


def _fact_presente(arquivo: Path, seletor: str) -> bool:
    """`#<id>` casa o id; `#kind:<kind>` casa qualquer fact daquele kind."""
    itens = _itens_de_fact(arquivo)
    if seletor.startswith(_SELETOR_KIND):
        kind = seletor[len(_SELETOR_KIND):]
        return bool(kind) and any(item.get("kind") == kind for item in itens)
    return seletor in {str(item["id"]) for item in itens if item.get("id")}


def _conferir_fact(ctx: _Contexto, artefato: Artifact, referencia: str) -> None:
    caminho, _, seletor = referencia.partition("#")
    alvo = resolve_within(ctx.repo, caminho) if caminho else None
    if alvo is None or not alvo.is_file() or not _fact_presente(alvo, seletor):
        ctx.lacuna("fact_not_collected", artefato.path,
                   f"{seletor or referencia} nao esta em {caminho}; colete o artefato e "
                   "rode o `sparkforge analyze` que o extrai")
```

e o ramo `fact` de `_gate_verified_by` vira `_conferir_fact(ctx, artefato, referencia)`.
Commit `feat(sdd): let a fact reference select by kind`.

## T4 — `proof` de tarefa

`sparkforge/sdd/schema/plan.json`, em `tasks.items.properties`, ao lado de `test`:

```json
"proof": {
  "type": "object",
  "additionalProperties": false,
  "required": ["kind", "ref"],
  "properties": {
    "kind": {"enum": ["funcval", "fact", "finding"]},
    "ref": {"type": "string", "minLength": 1}
  }
}
```

Teste, depois de `_relatorio_de_mudanca`:

```python
def _plano_operator(tmp_path):
    """Feature operator cortada no plan."""
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("build_report", "ship"):
        caminhos[fase].unlink()
    return caminhos


def _prova(caminhos, prova) -> None:
    meta = _meta(caminhos["plan"])
    meta["tasks"][0].pop("test", None)
    meta["tasks"][0]["proof"] = prova
    _reescreve(caminhos["plan"], tasks=meta["tasks"])


def test_proof_de_tarefa_operator(tmp_path):
    caminhos = _plano_operator(tmp_path)
    # finding: antes do sandbox, lacuna; com a regra saindo no relatorio, limpo
    _prova(caminhos, {"kind": "finding", "ref": "S1#SF-PY-012"})
    assert _codigos(check(tmp_path)) == ([], ["finding_not_observed"])
    _relatorio_de_mudanca(tmp_path, "sandbox", "S1", resolvidos=["SF-PY-012"])
    assert _codigos(check(tmp_path)) == ([], [])
    # regra que tambem entra em new nao saiu
    _relatorio_de_mudanca(
        tmp_path, "sandbox", "S1", novos=["SF-PY-012"], resolvidos=["SF-PY-012"]
    )
    assert _codigos(check(tmp_path)) == ([], ["finding_not_observed"])
    # sem rule_id o ref nao tem forma
    _prova(caminhos, {"kind": "finding", "ref": "S1"})
    assert [(r["code"], r["field"]) for r in check(tmp_path)["refused"]] == [
        ("schema_invalid", "tasks/0/proof/ref"),
    ]
    # `#<rule_id>` sem build ainda nao tem change_id para ler
    _prova(caminhos, {"kind": "finding", "ref": "#SF-PY-012"})
    assert _codigos(check(tmp_path)) == ([], ["finding_not_observed"])
    # funcval e fact reaproveitam as conferencias do define
    _prova(caminhos, {"kind": "funcval", "ref": "compare.json"})
    assert _codigos(check(tmp_path)) == ([], ["funcval_not_run"])
    _prova(caminhos, {"kind": "fact", "ref": "facts.json#kind:pyspark.conf_set"})
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])
    (tmp_path / "facts.json").write_bytes(b'[{"id": "f1", "kind": "pyspark.conf_set"}]')
    assert _codigos(check(tmp_path)) == ([], [])
    # no dev, proof nao substitui test
    dev = tmp_path / "dev"
    caminhos_dev = _ate(dev, "plan")
    _prova(caminhos_dev, {"kind": "fact", "ref": "facts.json#kind:x"})
    assert _codigos(check(dev)) == (["schema_invalid", "task_without_test"], [])
```

Vermelho: `python -m pytest tests/test_sdd.py::test_proof_de_tarefa_operator -q`
(o schema ainda recusa `proof`).

Código:

```python
def _conferir_ref_funcval(
    ctx: _Contexto, artefato: Artifact, campo: str, referencia: str, dono: str
) -> None:
    alvo = resolve_within(ctx.repo, referencia)
    if alvo is None or not alvo.is_file():
        ctx.lacuna("funcval_not_run", artefato.path,
                   f"rode `sparkforge funcval compare --out {referencia}` para {dono}")
        return
    _conferir_funcval(ctx, artefato, campo, alvo, referencia)


def _relatorio_da_mudanca(repo: Path, ident: str) -> dict[str, Any] | None:
    for pasta, nome in _pastas_da_mudanca(repo, ident):
        try:
            dado = json.loads((pasta / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(dado, dict):
            return dado
    return None


def _regras(itens: Any) -> set[str]:
    if not isinstance(itens, list):
        return set()
    return {str(i["rule_id"]) for i in itens if isinstance(i, dict) and i.get("rule_id")}


def _nao_movidas(relatorio: dict[str, Any] | None, regras: list[str]) -> list[str]:
    """As regras que o relatorio NAO mostra saindo: fora de `resolved`, ou em `new`."""
    if relatorio is None:
        return list(regras)
    saiu = _regras(relatorio.get("resolved"))
    entrou = _regras(relatorio.get("new"))
    return [regra for regra in regras if regra not in saiu or regra in entrou]


_ONDE_O_RELATORIO_MORA = (
    ".sparkforge/sandbox/<id>/report.json ou "
    ".sparkforge/proposal/<id>/evidence/sandbox_report.json"
)


def _conferir_achado(
    ctx: _Contexto, artefato: Artifact, campo: str, referencia: str, dono: str
) -> None:
    ident, _, regra = referencia.partition("#")
    if not regra:
        ctx.recusa("schema_invalid", artefato.path, f"{campo}/ref",
                   f"'{referencia}' nao e <change_id>#<rule_id>; use #<rule_id> para o "
                   "change_id do build_report")
        return
    if _ship_feito(ctx):
        return  # referencia historica: o sandbox pode ter sido limpo
    if not ident:
        build = ctx.artefatos.get("build_report")
        ident = str((build.meta.get("change_id") if build is not None else None) or "")
    if not _nao_movidas(_relatorio_da_mudanca(ctx.repo, ident), [regra]):
        return
    alvo = ident or "<change_id>"
    if _build_pronto(ctx):
        ctx.recusa("moved_not_observed", artefato.path, campo,
                   f"{regra} nao sai no relatorio de {alvo} ({_ONDE_O_RELATORIO_MORA}); "
                   "a regra precisa estar em resolved e fora de new")
    else:
        ctx.lacuna("finding_not_observed", artefato.path,
                   f"{dono} prova que {regra} sai; rode `sparkforge change sandbox` e "
                   f"registre o id em change_id ({_ONDE_O_RELATORIO_MORA})")


def _conferir_prova(
    ctx: _Contexto, artefato: Artifact, campo: str, prova: dict[str, Any], dono: str
) -> None:
    if prova["kind"] == "funcval":
        _conferir_ref_funcval(ctx, artefato, campo, prova["ref"], dono)
    elif prova["kind"] == "fact":
        _conferir_fact(ctx, artefato, prova["ref"])
    else:
        _conferir_achado(ctx, artefato, campo, prova["ref"], dono)


def _gate_task_test(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    operador = artefato.meta["profile"] == "operator"
    for indice, tarefa in enumerate(artefato.meta["tasks"]):
        teste = tarefa.get("test")
        prova = tarefa.get("proof")
        campo = f"tasks/{indice}/test"
        if prova and not operador:
            ctx.recusa("schema_invalid", artefato.path, f"tasks/{indice}/proof",
                       "proof so vale no perfil operator; no dev a tarefa declara test")
        if teste:
            _conferir_teste(ctx, artefato, campo, f"{teste['path']}::{teste['name']}",
                            tarefa["id"])
        if prova and operador:
            _conferir_prova(ctx, artefato, f"tasks/{indice}/proof", prova, tarefa["id"])
        elif not teste:
            extra = " (no operator, ou proof: funcval, fact ou finding)" if operador else ""
            ctx.recusa("task_without_test", artefato.path, campo,
                       f"{tarefa['id']} precisa do teste que falha antes do codigo{extra}")
```

O ramo `funcval` de `_gate_verified_by` passa a chamar `_conferir_ref_funcval`.
Commit `feat(sdd): let an operator task prove itself without pytest`.

## T5 — `moved` no build

`sparkforge/sdd/schema/build_report.json`, em `tasks.items.properties`:

```json
"moved": {
  "type": "object",
  "additionalProperties": false,
  "required": ["change_id", "resolved"],
  "properties": {
    "change_id": {"type": "string", "minLength": 1},
    "resolved": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}
  }
}
```

Testes, depois de `test_proof_de_tarefa_operator`:

```python
def test_moved_confere_o_relatorio(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    tarefa = {"id": "T1", "status": "done",
              "moved": {"change_id": "S1", "resolved": ["SF-PY-012"]}}
    _reescreve(caminhos["build_report"], tasks=[tarefa])
    # sem relatorio, nada foi observado
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("moved_not_observed", "tasks/0/moved")]
    assert "SF-PY-012" in recusa[0]["unlock"]
    _relatorio_de_mudanca(tmp_path, "sandbox", "S1", resolvidos=["SF-PY-012"])
    assert _codigos(check(tmp_path)) == ([], [])
    # regra que tambem entra em new nao saiu
    _relatorio_de_mudanca(
        tmp_path, "sandbox", "S1", novos=["SF-PY-012"], resolvidos=["SF-PY-012"]
    )
    assert _codigos(check(tmp_path)) == (["moved_not_observed"], [])
    # o sandbox limpo nao apaga a prova que o pacote de proposal guarda
    shutil.rmtree(tmp_path / ".sparkforge" / "sandbox" / "S1")
    _relatorio_de_mudanca(tmp_path, "proposal", "S1", resolvidos=["SF-PY-012"])
    assert _codigos(check(tmp_path)) == ([], [])
    # o plano que prova por #<rule_id> le o change_id do build; com o build pronto,
    # achado nao observado e recusa
    meta = _meta(caminhos["plan"])
    del meta["tasks"][0]["test"]
    meta["tasks"][0]["proof"] = {"kind": "finding", "ref": "#SF-PY-012"}
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    _restampa(tmp_path)
    assert _codigos(check(tmp_path)) == ([], [])
    meta["tasks"][0]["proof"]["ref"] = "#SF-OUTRA"
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    _restampa(tmp_path)
    assert _codigos(check(tmp_path)) == (["moved_not_observed"], [])
    # no dev, moved nao substitui red
    dev = tmp_path / "dev"
    caminhos_dev = _ate(dev, "build_report")
    _reescreve(caminhos_dev["build_report"], tasks=[tarefa])
    assert _codigos(check(dev)) == (["red_not_declared", "schema_invalid"], [])


def test_proof_e_moved_fecham_propriedades():
    tarefa_plan = schema_for("plan")["properties"]["tasks"]["items"]
    prova = tarefa_plan["properties"]["proof"]
    tarefa_build = schema_for("build_report")["properties"]["tasks"]["items"]
    movido = tarefa_build["properties"]["moved"]
    for bloco in (tarefa_plan, prova, tarefa_build, movido):
        assert bloco["additionalProperties"] is False
    validador = jsonschema.Draft202012Validator(prova)
    assert validador.is_valid({"kind": "finding", "ref": "S1#SF-X"})
    assert not validador.is_valid({"kind": "finding", "ref": "S1#SF-X", "extra": 1})
    assert not validador.is_valid({"kind": "test", "ref": "x"})
    validador = jsonschema.Draft202012Validator(movido)
    assert validador.is_valid({"change_id": "S1", "resolved": ["SF-X"]})
    assert not validador.is_valid({"change_id": "S1", "resolved": []})
    assert not validador.is_valid({"change_id": "S1", "resolved": ["SF-X"], "exit": 0})
```

Vermelho: `python -m pytest tests/test_sdd.py::test_moved_confere_o_relatorio tests/test_sdd.py::test_proof_e_moved_fecham_propriedades -q`.

Código:

```python
def _conferir_movido(
    ctx: _Contexto, artefato: Artifact, campo: str, movido: dict[str, Any], dono: str
) -> None:
    if _ship_feito(ctx):
        return  # referencia historica: o sandbox pode ter sido limpo
    ident = movido["change_id"]
    faltam = _nao_movidas(_relatorio_da_mudanca(ctx.repo, ident), movido["resolved"])
    if faltam:
        ctx.recusa("moved_not_observed", artefato.path, campo,
                   f"{dono}: {', '.join(faltam)} nao sai no relatorio de {ident} "
                   f"({_ONDE_O_RELATORIO_MORA}); a regra precisa estar em resolved e fora "
                   "de new: rode `sparkforge change sandbox` de novo ou corrija moved")


def _gate_red(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    operador = artefato.meta["profile"] == "operator"
    for indice, tarefa in enumerate(artefato.meta["tasks"]):
        movido = tarefa.get("moved")
        if movido is not None and not operador:
            ctx.recusa("schema_invalid", artefato.path, f"tasks/{indice}/moved",
                       "moved so vale no perfil operator; no dev a tarefa declara red e green")
        if tarefa["status"] != "done":
            continue
        vermelho = tarefa.get("red")
        if movido is not None and operador:
            _conferir_movido(ctx, artefato, f"tasks/{indice}/moved", movido, tarefa["id"])
            if vermelho is None:
                continue
        if not vermelho or vermelho["exit"] == 0:
            ctx.recusa("red_not_declared", artefato.path, f"tasks/{indice}/red",
                       f"registre o comando que falhou antes do codigo de {tarefa['id']} "
                       "(exit diferente de zero)")
```

Commit `feat(sdd): accept an observed finding move as operator build proof`.

## T6 — ponta a ponta durável

Reescrever o fluxo de `tests/test_sdd_operator.py` com a raiz `.sparkforge/sdd`:

- `_grava(repo, fase, meta, raiz=RAIZ)` grava em `<raiz>/JOB_SHUFFLE/` e chama
  `stamp(repo, ..., root=raiz)`;
- `_feature_operator(repo, case_id, change_id, raiz=RAIZ)` monta: `AC1`
  funcval (`<raiz>/JOB_SHUFFLE/compare.json`), `AC2` fact por kind
  (`<raiz>/JOB_SHUFFLE/facts.json#kind:pyspark.conf_set`); T1 com `test`,
  T2 com `proof {kind: finding, ref: "#SF-PY-012"}`; no build, T1 com
  `red`/`green` e T2 com `moved {change_id, resolved: [SF-PY-012]}`;
- os facts saem de `call_tool("sparkforge_analyze_pyspark", {"path": lib})`.

O teste:

```python
def test_fluxo_operator_ponta_a_ponta(tmp_path):
    repo = tmp_path / "repo"
    diff = _repositorio_do_operador(repo)
    caso = call_tool("sparkforge_case_open", {"repo": str(repo), "case_id": "C-42", "now": _NOW})
    assert caso.get("case_id") == "C-42", caso
    sandbox = call_tool("sparkforge_change_sandbox", {"repo": str(repo), "diff_path": str(diff)})
    change_id = sandbox.get("id")
    assert change_id and (repo / ".sparkforge" / "sandbox" / change_id).is_dir(), sandbox
    assert REGRA in {r["rule_id"] for r in sandbox["resolved"]}, sandbox
    assert (repo / "lib" / "job.py").read_bytes() == _JOB

    comparacao = _evidencias(repo, RAIZ)
    _feature_operator(repo, caso["case_id"], change_id)
    assert _check(repo) == ([], [])

    # a spec em .sparkforge/sdd nao desatualiza a copia validada
    proposta = call_tool("sparkforge_change_propose",
                         {"repo": str(repo), "sandbox_id": change_id, "now": _NOW})
    assert proposta["refused"] == [], proposta
    assert (repo / ".sparkforge" / "proposal" / change_id).is_dir()

    # comparacao sem nenhum check_delta nao e comparacao
    comparacao.write_bytes(json.dumps({"items": [{"id": "x", "kind": "funcval.analyzed"}]})
                           .encode("utf-8"))
    assert _check(repo) == (["funcval_not_comparison"], [])
    comparacao.write_bytes(json.dumps({"items": [_DELTA]}).encode("utf-8"))

    # sandbox limpo: o pacote de proposal guarda o id e o relatorio
    call_tool("sparkforge_change_sandbox", {"repo": str(repo), "clean": True})
    assert not (repo / ".sparkforge" / "sandbox" / change_id).exists()
    assert _check(repo) == ([], [])

    # sem nenhum dos dois e com outro case: o ship done deixa as referencias historicas
    shutil.rmtree(repo / ".sparkforge" / "proposal" / change_id)
    outro = call_tool("sparkforge_case_open",
                      {"repo": str(repo), "case_id": "C-43", "now": _NOW, "reopen": True})
    assert outro.get("case_id") == "C-43", outro
    assert _check(repo) == ([], [])
    # com o ship ainda aberto, tudo volta a ser conferido
    _reescreve_status(repo, "ship", "ready")
    assert _check(repo) == (
        ["case_missing", "change_missing", "moved_not_observed", "moved_not_observed"], []
    )


def test_spec_em_docs_sdd_desatualiza_o_sandbox(tmp_path):
    """O contraste de D1: a mesma spec em docs/sdd muda a arvore que o sandbox copiou."""
    repo = tmp_path / "repo"
    diff = _repositorio_do_operador(repo)
    caso = call_tool("sparkforge_case_open", {"repo": str(repo), "case_id": "C-42", "now": _NOW})
    sandbox = call_tool("sparkforge_change_sandbox", {"repo": str(repo), "diff_path": str(diff)})
    _evidencias(repo, "docs/sdd")
    _feature_operator(repo, caso["case_id"], sandbox["id"], raiz="docs/sdd")
    proposta = call_tool("sparkforge_change_propose",
                         {"repo": str(repo), "sandbox_id": sandbox["id"], "now": _NOW})
    assert [r["reason"] for r in proposta["refused"]] == ["sandbox_desatualizado"], proposta
```

com os auxiliares:

```python
def _evidencias(repo: Path, raiz: str) -> Path:
    """Facts reais do job e a comparacao do funcval, na pasta da feature."""
    pasta = repo / raiz / FEATURE
    pasta.mkdir(parents=True, exist_ok=True)
    fatos = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
    assert "pyspark.conf_set" in {f["kind"] for f in fatos["items"]}, fatos
    (pasta / "facts.json").write_bytes(json.dumps({"items": fatos["items"]}).encode("utf-8"))
    comparacao = pasta / "compare.json"
    comparacao.write_bytes(json.dumps({"items": [_DELTA]}).encode("utf-8"))
    return comparacao


def _check(repo: Path) -> tuple[list[str], list[str]]:
    return _codigos(check(repo, root=RAIZ, feature=FEATURE))


def _reescreve_status(repo: Path, fase: str, status: str) -> None:
    arquivo = repo / RAIZ / FEATURE / f"{fase}.md"
    texto = arquivo.read_bytes().decode("utf-8")
    arquivo.write_bytes(texto.replace("status: done", f"status: {status}", 1).encode("utf-8"))
```

Vermelho: `python -m pytest tests/test_sdd_operator.py -q` com o núcleo antes de
T1 (num `git worktree` no commit anterior a T1, porque T1 a T5 já constroem o
comportamento): `moved` é `schema_invalid` lá. Commit
`test(sdd): prove the durable operator flow end to end`.

## T7 — skills, README e spec

Teste, no fim de `tests/test_sdd_operator.py`:

```python
_OPERADOR_DURAVEL = {
    "sdd-define": ("--root .sparkforge/sdd", "#kind:"),
    "sdd-plan": ("--root .sparkforge/sdd", "proof", "finding"),
    "sdd-build": ("--root .sparkforge/sdd", "moved", "--out", "--funcval", "--benchmark"),
    "sdd-ship": ("--root .sparkforge/sdd", "--funcval", "--benchmark", "done"),
}


def test_skills_ensinam_o_operador_duravel():
    for nome, trechos in _OPERADOR_DURAVEL.items():
        texto = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        operador = texto.split("## Perfil operator", 1)[1].split("\n## ", 1)[0]
        for trecho in trechos:
            assert trecho in operador, (nome, trecho)
    readme = (ROOT / "docs" / "sdd" / "README.md").read_text(encoding="utf-8")
    for trecho in ("--root .sparkforge/sdd", "sparkforge change sandbox",
                   "sparkforge change propose", "#kind:"):
        assert trecho in readme, trecho
```

Vermelho: `python -m pytest tests/test_sdd_operator.py::test_skills_ensinam_o_operador_duravel -q`.

Texto: a seção "Perfil operator" de cada skill ganha a raiz
`--root .sparkforge/sdd` nos comandos, e:

- `sdd-define`: `{kind: fact, ref: <arquivo>#kind:<kind>}` na hora do define (o
  id de fact é hash de conteúdo); `case_missing` deixa de valer com o ship
  `done`.
- `sdd-plan`: `proof {kind: funcval|fact|finding, ref}` no lugar de `test`;
  `finding` é `<change_id>#<rule_id>` ou `#<rule_id>`; lacuna
  `finding_not_observed` até o sandbox.
- `sdd-build`: `moved {change_id, resolved}` no lugar de `red`/`green`;
  `funcval compare ... --out <ref do AC>`, `benchmark ... --out bench.json`,
  `change propose --sandbox <id> --repo . --funcval <cmp.json> --benchmark bench.json`;
  evidências dentro de `.sparkforge/sdd/<F>/`.
- `sdd-ship`: o mesmo `change propose` com as duas flags; com `status: done`,
  case e mudança citados viram histórico.

`docs/sdd/README.md` ganha a seção "Perfil operator: onde mora a spec". O §5.0
do spec do núcleo ganha os itens `change_id` pela proposal, referência
histórica, seletor `kind:`, `proof`, `moved`, `finding_not_observed` e
`moved_not_observed`. Rodar `python scripts/sync_skills.py` (com
`.claude/agents/README.md` fora da árvore) e
`python -m pytest tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q`.
Commit `docs(sdd): teach the durable operator profile in skills and README`.
