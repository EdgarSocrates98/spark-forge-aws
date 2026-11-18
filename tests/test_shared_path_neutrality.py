"""Neutralidade dos paths compartilhados entre forges (install-2.1, federacao).

Num workspace federado, `spark-forge-aws` e `spark-forge-azure` instalam no
mesmo alvo. Dois paths sao compartilhados por construcao:

- `<host>/skills/_shared/references/*.md` — copia byte a byte do canonico;
- `{rules,evals}/<rel>` — stubs PONTEIRO emitidos por `plan_files`
  (`evals/evals.json` e o caso real observado: os dois forges o emitem).

Se os bytes divergirem, o segundo install encontra arquivo estrangeiro no
caminho e falha com `preserved_foreign`. Portanto o conteudo desses paths
nao pode nomear forge nem os verbos nativos dele — o leitor acha o dono no
registro da federacao (`.forge/installations/`, `.forge/context/`).

`knowledge/` nao entra: ele ja e namespacado (`knowledge/sparkforge-aws/`).
"""
from __future__ import annotations

import re
from pathlib import Path

from sparkforge_aws.integrate import integrate, render

ROOT = Path(__file__).resolve().parents[1]
SHARED_REFS = ROOT / "skills" / "_shared" / "references"
MIRRORS = (ROOT / ".claude" / "skills" / "_shared" / "references",
           ROOT / ".agents" / "skills" / "_shared" / "references")

# Identidade de UM forge ou de UMA nuvem — nunca "SparkForge", que e o nome
# da familia e ja e compartilhado entre os siblings. Nem "Iceberg"/"Delta",
# formatos que os dois lados usam.
FORGE_TOKEN = re.compile(
    r"spark[-_]?forge[-_](aws|azure)"
    r"|\b(?:aws|azure|AWS|Azure|Amazon)\b"
    r"|\b(?:Glue|Athena|EMR|IAM|KMS|SCP|ADLS|RBAC|Databricks|Synapse|Fabric)\b"
    r"|Unity Catalog|Key Vault"
)


def _sem_forge(texto: str, onde: str) -> None:
    achados = FORGE_TOKEN.findall(texto)
    assert not achados, f"{onde} nomeia forge/nuvem: {sorted(set(achados))}"


def test_shared_references_nao_nomeiam_forge_nem_nuvem():
    arquivos = sorted(SHARED_REFS.glob("*.md"))
    assert arquivos, "nenhum _shared/references/*.md encontrado"
    for arquivo in arquivos:
        _sem_forge(arquivo.read_text(encoding="utf-8"), arquivo.name)


def test_shared_references_espelhos_byte_identicos():
    """`.claude/skills/_shared/` e `.agents/skills/_shared/` sao a mesma
    coisa que o canonico — no workspace federado os dois forges gravam o
    mesmo path, entao o conteudo tem que ser literalmente identico."""
    for canonico in sorted(SHARED_REFS.glob("*.md")):
        dados = canonico.read_bytes()
        for espelho in MIRRORS:
            copia = espelho / canonico.name
            assert copia.is_file(), f"espelho ausente: {copia}"
            assert copia.read_bytes() == dados, f"espelho diverge: {copia}"


def test_asset_stub_e_index_nao_nomeiam_forge():
    """O stub de `{rules,evals}/<rel>` e o `README.md` indice nao podem
    nomear este forge nem os verbos nativos dele — o mesmo path e emitido
    pelo sibling, e bytes diferentes viram `preserved_foreign`."""
    for kind in ("rules", "evals"):
        for rel in ("evals.json", "catalog/x.yaml"):
            _sem_forge(
                render.asset_stub(kind, rel).decode("utf-8"), f"{kind}/{rel}"
            )
        _sem_forge(
            render.asset_index_stub(kind, 3).decode("utf-8"), f"{kind}/README.md"
        )


def test_stub_aponta_para_o_registro_da_federacao():
    """Sem verbo nativo no texto, o leitor precisa de um lugar para achar o
    dono: o registro `.forge/` da federacao."""
    stub = render.asset_stub("evals", "evals.json").decode("utf-8")
    assert ".forge/" in stub


def test_ponteiro_evals_json_instalado_e_neutro(tmp_path):
    """Caminho da colisao real: `evals/evals.json` citado por uma skill vira
    stub em `<alvo>/evals/evals.json`. Os bytes gravados nao podem nomear
    este forge."""
    home = tmp_path / "home"
    raiz = tmp_path / "raiz"
    (raiz / "agents").mkdir(parents=True)
    (raiz / "agents" / "sf-falso.md").write_text(
        "---\nname: sf-falso\ndescription: agent de teste\n---\ncorpo\n",
        encoding="utf-8",
    )
    (raiz / "skills" / "sdd-plan").mkdir(parents=True)
    (raiz / "skills" / "sdd-plan" / "SKILL.md").write_text(
        "---\nname: sdd-plan\ndescription: skill de teste\n---\n"
        "corpo — veja `evals/evals.json` e `rules/catalog/x.yaml`\n",
        encoding="utf-8",
    )

    assert integrate("devin", home=home, windows=False, root=raiz)["refused"] == []

    evals_pointer = home / "evals" / "evals.json"
    rules_pointer = home / "rules" / "catalog" / "x.yaml"
    assert evals_pointer.is_file()
    assert rules_pointer.is_file()
    _sem_forge(evals_pointer.read_text(encoding="utf-8"), "evals/evals.json")
    _sem_forge(rules_pointer.read_text(encoding="utf-8"), "rules/catalog/x.yaml")
    _sem_forge(
        (home / "evals" / "README.md").read_text(encoding="utf-8"),
        "evals/README.md",
    )
