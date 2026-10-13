"""Behavioral portable distribution contracts, including hostile declarations."""

import json
import shutil

import pytest
import yaml

from sparkforge_aws.distribution.config import PortableError, resolve_config
from sparkforge_aws.distribution.paths import resolve_paths
from sparkforge_aws.distribution.service import init_project, inspect_distribution, resolve_context
from sparkforge_aws.workspace.portable import (
    add_repository,
    discover,
    init_workspace,
    workspace_status,
)


def test_read_only_hostless_and_minimal_init(tmp_path):
    before = list(tmp_path.rglob("*"))
    result = inspect_distribution(tmp_path)
    assert result["offline"] is True
    assert list(tmp_path.rglob("*")) == before
    first = init_project(tmp_path)
    assert init_project(tmp_path) == first
    assert [p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()] == [
        ".sparkforge_aws/project.yaml"
    ]
    data = yaml.safe_load((tmp_path / ".sparkforge_aws/project.yaml").read_text())
    assert data["root"] == "."
    assert "package_root" not in data


def test_relocation_and_isolated_state(tmp_path, monkeypatch):
    repo = tmp_path / "one"
    repo.mkdir()
    init_project(repo)
    monkeypatch.setenv("SPARKFORGE_AWS_HOME", str(tmp_path / "state"))
    from sparkforge_aws.case.store import case_path, state_path

    original = case_path(repo)
    moved = tmp_path / "moved"
    shutil.move(repo, moved)
    assert case_path(moved) == original
    other = tmp_path / "two"
    other.mkdir()
    init_project(other)
    assert case_path(other) != original
    assert state_path(moved, "codeintel/index.json").is_relative_to(tmp_path / "state")
    assert not (moved / ".sparkforge_aws/case.yaml").exists()


def test_config_precedence_and_strict_errors(tmp_path, monkeypatch):
    user = tmp_path / "user.yaml"
    user.write_text("scope:\n  default: workspace\n")
    monkeypatch.setenv("SPARKFORGE_AWS_CONFIG", str(user))
    init_project(tmp_path)
    path = tmp_path / ".sparkforge_aws/project.yaml"
    data = yaml.safe_load(path.read_text())
    data["config"] = {"scope": {"default": "target"}}
    path.write_text(yaml.safe_dump(data))
    paths = resolve_paths(tmp_path)
    assert resolve_config(paths, project_path=path)["scope"]["default"] == "target"
    assert (
        resolve_config(paths, project_path=path, overrides={"scope": {"default": "repo"}})["scope"][
            "default"
        ]
        == "repo"
    )
    for content in ["a: 1\na: 2\n", "x: &x [*x]\n", "password: abc\n", "scope: [repo]\n"]:
        user.write_text(content)
        with pytest.raises(PortableError):
            resolve_config(paths)
    user.unlink()
    with pytest.raises(PortableError, match="CONFIG-MISSING"):
        resolve_config(paths)


def test_discovery_bounded_nested_and_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    module = repo / "module"
    module.mkdir()
    (module / "pyproject.toml").write_text('[project]\nname="module"')
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: ../../outside")
    skipped = tmp_path / "node_modules" / "bad"
    skipped.mkdir(parents=True)
    (skipped / ".git").mkdir()
    result = discover(tmp_path)
    assert {x["path"] for x in result["repositories"]} == {"repo", "wt"}
    assert result["modules"] == [{"path": "repo/module", "marker": "pyproject.toml"}]
    assert discover(tmp_path, max_depth=0)["repositories"] == []
    with pytest.raises(PortableError):
        discover(tmp_path, max_depth=-1)


def test_workspace_external_missing_and_locality(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    one = tmp_path / "one"
    one.mkdir()
    init_project(one)
    two = workspace / "two"
    two.mkdir()
    init_project(two)
    init_workspace(workspace)
    add_repository(workspace, one, name="one")
    add_repository(workspace, two, name="two")
    assert (
        add_repository(workspace, one, name="one")["repositories"]
        == workspace_status(workspace)["repositories"]
    )
    path = workspace / ".sparkforge_aws/workspace.yaml"
    data = yaml.safe_load(path.read_text())
    assert data["repositories"][0]["path"] == "../one"
    data["relationships"] = {"one": {"depends_on": ["two", "missing"]}}
    path.write_text(yaml.safe_dump(data))
    result = resolve_context(workspace, scope="target", target="repository:one", impact="direct")
    assert result["included_repositories"] == ["one", "two"]
    assert any(x["code"] == "relationship_target_unresolved" for x in result["unresolved"])
    with pytest.raises(PortableError, match="TARGET-NOT-FOUND"):
        resolve_context(workspace, scope="target", target="repository:unknown")
    shutil.rmtree(one)
    assert any(x["code"] == "repository_missing" for x in workspace_status(workspace)["unresolved"])


def test_manifest_collision_symlinks_and_legacy_confinement(tmp_path):
    init_project(tmp_path)
    path = tmp_path / ".sparkforge_aws/project.yaml"
    path.write_text("bad: data")
    with pytest.raises(PortableError):
        init_project(tmp_path)
    assert path.read_text() == "bad: data"
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    path.unlink()
    (tmp_path / ".sparkforge_aws").rmdir()
    (tmp_path / ".sparkforge_aws").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PortableError):
        init_project(tmp_path)
    assert list(outside.iterdir()) == []
    from sparkforge_aws.workspace.manifest import WorkspaceManifestError, load_manifest

    old = tmp_path.parent / (tmp_path.name + "-legacy.yaml")
    old.write_text("workspace: old\nrepositories:\n- name: escape\n  path: ../escape\n")
    with pytest.raises(WorkspaceManifestError):
        load_manifest(old)


def test_cli_additive_surface(tmp_path, capsys):
    from sparkforge_aws.adapters.cli import main

    assert main(["distribution", "inspect", "--root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["offline"] is True
    assert main(["distribution", "init", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["context", "resolve", "--root", str(tmp_path), "--scope", "repo"]) == 0
    assert json.loads(capsys.readouterr().out)["scope"] == "repo"


def test_persisted_external_lifecycle_cache_and_relocation(tmp_path, monkeypatch, capsys):
    from sparkforge_aws.adapters.cli import main
    from sparkforge_aws.agentic.blackboard import init_blackboard
    from sparkforge_aws.case.store import load_case
    from sparkforge_aws.decision.cache import ArtifactCache
    from sparkforge_aws.journal import journal_path

    repo = tmp_path / "repo"
    repo.mkdir()
    init_project(repo)
    monkeypatch.setenv("SPARKFORGE_AWS_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("SPARKFORGE_AWS_CACHE", str(tmp_path / "cache"))
    monkeypatch.chdir(repo)
    assert (
        main(
            [
                "case",
                "open",
                "--repo",
                str(repo),
                "--case-id",
                "portable",
                "--now",
                "2026-10-09T00:00:00Z",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert load_case(repo)["case_id"] == "portable"
    journal = [json.loads(line) for line in journal_path(repo).read_text().splitlines()]
    assert len(journal) == 2
    import hashlib

    from sparkforge_aws.case.store import case_path

    assert (
        journal[-1]["outputs"][".sparkforge_aws/case.yaml"]
        == hashlib.sha256(case_path(repo).read_bytes()).hexdigest()
    )
    from sparkforge_aws.journal.record import _relativo

    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    assert _relativo(repo, str(outside))[1] is None
    assert init_blackboard(repo).is_relative_to(tmp_path / "state")
    cache = ArtifactCache()
    cache.set("portable", {"input": 1}, {"result": "ok"})
    assert ArtifactCache().get("portable", {"input": 1}) == {"result": "ok"}
    assert list((tmp_path / "cache").rglob("*.json"))
    moved = tmp_path / "moved"
    monkeypatch.chdir(tmp_path)
    shutil.move(repo, moved)
    assert load_case(moved)["case_id"] == "portable"
    assert [p.name for p in (moved / ".sparkforge_aws").iterdir()] == ["project.yaml"]


def test_nested_git_boundary_and_symlink_control_reads(tmp_path, monkeypatch):
    init_project(tmp_path)
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / ".git").write_text("gitdir: /do/not/read")
    result = inspect_distribution(nested)
    assert result["roots"]["project_root"] == str(nested)
    control = nested / ".sparkforge_aws"
    control.symlink_to(tmp_path / ".sparkforge_aws", target_is_directory=True)
    monkeypatch.setenv("SPARKFORGE_AWS_HOME", str(tmp_path / "state"))
    with pytest.raises(PortableError):
        resolve_paths(nested)
    with pytest.raises(PortableError):
        inspect_distribution(nested)
    control.unlink()
    monkeypatch.setenv("SPARKFORGE_AWS_HOME", str(resolve_paths(tmp_path, env={}).package_root))
    with pytest.raises(PortableError, match="overlap package"):
        resolve_paths(nested)


def test_discovery_budget_and_context_impact_refusals(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / name).mkdir()
    result = discover(tmp_path, max_directories=1)
    assert result["visited_directories"] == 1
    assert result["unresolved"][0]["code"] == "discovery_directory_limit"
    init_workspace(tmp_path)
    add_repository(tmp_path, tmp_path / "a")
    add_repository(tmp_path, tmp_path / "b")
    add_repository(tmp_path, tmp_path / "c")
    path = tmp_path / ".sparkforge_aws/workspace.yaml"
    data = yaml.safe_load(path.read_text())
    data["relationships"] = {"a": {"depends_on": ["b"]}, "b": {"depends_on": ["c"]}}
    path.write_text(yaml.safe_dump(data))
    assert resolve_context(tmp_path, scope="target", target="repository:a", impact="direct")[
        "included_repositories"
    ] == ["a", "b"]
    assert resolve_context(tmp_path, scope="workspace", target="repository:a", impact="transitive")[
        "included_repositories"
    ] == ["a", "b", "c"]
    with pytest.raises(PortableError, match="TARGET-REQUIRED"):
        resolve_context(tmp_path, scope="workspace", impact="direct")


def test_nested_paths_and_initialization_preserve_external_namespace(tmp_path, monkeypatch):
    from sparkforge_aws.case.store import case_path

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    module = repo / "module"
    module.mkdir()
    monkeypatch.setenv("SPARKFORGE_AWS_HOME", str(tmp_path / "state"))
    before = case_path(module)
    init_project(repo)
    assert case_path(repo) == before == case_path(module)
    assert resolve_paths(module).project_root == repo
    assert inspect_distribution(module)["paths"]["state_root"] == str(before.parent)


@pytest.mark.parametrize("config", [None, [], "repo"])
def test_invalid_embedded_config_is_named_and_preserved(tmp_path, config, capsys):
    from sparkforge_aws.adapters.cli import main

    init_project(tmp_path)
    path = tmp_path / ".sparkforge_aws/project.yaml"
    data = yaml.safe_load(path.read_text())
    data["config"] = config
    path.write_text(yaml.safe_dump(data))
    original = path.read_bytes()
    assert main(["distribution", "inspect", "--root", str(tmp_path)]) == 2
    assert "SF-CONFIG-INVALID" in capsys.readouterr().err
    with pytest.raises(PortableError):
        init_project(tmp_path)
    assert path.read_bytes() == original


def test_explicit_absolute_external_root_and_cross_volume_fallback(tmp_path, monkeypatch):
    from sparkforge_aws.workspace.portable import load_workspace

    workspace = tmp_path / "ws"
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    init_workspace(workspace)

    def cross_volume(*args):
        raise ValueError("different drive")

    monkeypatch.setattr("sparkforge_aws.workspace.portable.os.path.relpath", cross_volume)
    add_repository(workspace, external)
    path = workspace / ".sparkforge_aws/workspace.yaml"
    assert yaml.safe_load(path.read_text())["repositories"][0]["path"] == external.as_posix()
    assert load_workspace(path).repositories[0].path == external


@pytest.mark.parametrize("config", [None, [], {"unknown": True}])
def test_invalid_workspace_config_is_refused_without_writes(tmp_path, config):
    init_workspace(tmp_path)
    path = tmp_path / ".sparkforge_aws/workspace.yaml"
    data = yaml.safe_load(path.read_text())
    data["config"] = config
    path.write_text(yaml.safe_dump(data))
    before = path.read_bytes()
    with pytest.raises(PortableError, match="SF-CONFIG-INVALID"):
        workspace_status(tmp_path)
    with pytest.raises(PortableError):
        init_workspace(tmp_path)
    with pytest.raises(PortableError):
        add_repository(tmp_path, tmp_path)
    assert path.read_bytes() == before


def test_workspace_loader_preserves_tilde_input(tmp_path, monkeypatch):
    from sparkforge_aws.workspace.manifest import load_manifest

    workspace = tmp_path / "ws"
    workspace.mkdir()
    init_workspace(workspace)
    monkeypatch.setenv("HOME", str(tmp_path))
    # Windows expanduser ignores HOME — it reads USERPROFILE.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert load_manifest("~/ws/.sparkforge_aws/workspace.yaml").root == workspace
