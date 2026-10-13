# Portable SparkForge AWS

[Guia completo em português](SPARKFORGE_AWS_PORTABLE.pt-BR.md)

These new verbs require a release. To test branch
`codex/portable-parity-api-forge`, run `python -m pip install .` from its checkout
or install its built wheel by absolute path. Examples installing the published
package below assume a release containing this change; older published versions
do not gain these commands automatically.

Install in a user-owned virtual environment, or use a local wheelhouse offline:

```bash
python -m venv "$HOME/tools/sparkforge-env"
"$HOME/tools/sparkforge-env/bin/python" -m pip install sparkforge-aws
"$HOME/tools/sparkforge-env/bin/sparkforge-aws" distribution doctor --root /work/job
# Offline installation: pip install --no-index --find-links /offline/wheels sparkforge-aws
```

PowerShell uses `E:\tools\sparkforge-env\Scripts\sparkforge-aws.exe` after
`python -m venv E:\tools\sparkforge-env`. No administrator, symlink or host is
required. Optional AWS/parquet/MCP extras are installed only when needed.

```bash
sparkforge-aws distribution inspect --root /work/job
sparkforge-aws distribution init --root /work/job
sparkforge-aws distribution status --root /work/job
sparkforge-aws context resolve --root /work/job --scope repo
sparkforge-aws workspace discover --root /work/platform
sparkforge-aws workspace init --root /work/platform --name platform
sparkforge-aws workspace add /work/orders --root /work/platform --name orders
sparkforge-aws workspace status --root /work/platform
sparkforge-aws context resolve --root /work/platform --scope target --target repository:orders --impact transitive
```

Initialization writes only project/workspace manifests. Existing valid manifests
are preserved; malformed/colliding/symlink declarations are refused. Inspection,
status, doctor and locality resolution are offline and read-only. Discovery is
bounded to 4 levels/2000 directories by default, recognizes Git worktree markers
without reading gitdir files, reports limits, and does not inspect source files.
Assets remain owned by the installation; hashes are observed inventory, not
trusted signatures.

`SPARKFORGE_AWS_HOME` and `SPARKFORGE_AWS_CACHE` namespace paths under
`projects/<project_id>`. Initialize before external state creation for stable
identity after relocation. Without a manifest the fallback hashes the absolute
root and changes after relocation. Copies with the same project ID deliberately
share a namespace; independently initialized projects get different IDs.
Relative override paths are anchored to the requested project root. HOME never
automatically migrates or reads legacy local state.

Without HOME, legacy commands preserve their explicit `--repo` root and can
create module-local state when launched from a module. Run them at the repository
root or pass its `--repo`. Portable resolution and HOME-aware consumers normalize
the nearest root; explicit sandboxes are not automatically rerooted.

HOME is wired to central case/state paths (case, journal, blackboard, traces,
codeintel and other consumers), and Lab run creation. CACHE is wired to default
artifact cache and CLI/MCP Context Gateway. Explicit output paths, repo artifact
collectors and independently confined sandbox/proposal operations keep their
existing contracts. This is **not universal redirection of every legacy write**.
An explicit ArtifactCache directory takes precedence.

`SPARKFORGE_AWS_CONFIG` applies to portable locality resolution, not existing
analyzer tuning or policy. Precedence is defaults → explicit CONFIG file →
workspace `config` → project `config` → explicit resolver override (CLI scope).
Supported settings are `scope.default` (repo/workspace/target), `network.mode`
(offline), and `host.activation` (plan_only). Missing explicit config, unknown
settings, duplicate YAML keys, aliases and secret-like keys are named refusals.

Virtual workspaces declare relative member paths; external members require
`external: true`. Legacy manifests retain containment. Cross-volume members use
explicit absolute external declarations; edit these references after moving
volumes. Symlink roots are refused. Declare `relationships: {orders: {depends_on:
[billing]}}` only with evidence. Direct follows one declared dependency edge;
transitive computes bounded closure; all includes declared members. Workspace
scope with direct/transitive requires a target or a root inside one member.
Unknown targets refuse; missing repos, unknown relationships and unmeasured
fingerprints remain unresolved. Domain graph commands remain explicit reads.

Portable baseline parity covers user-owned installation, asset separation,
lifecycle, workspaces, locality, explicit paths/config and hostless operation.
API-specific autonomous runtime/scorecards, auto-update and asset signing are
not introduced. Existing integrate/detach previews and confirmation/rollback
handle optional hosts; preview with `sparkforge-aws integrate codex --scope user --dry-run`.
No new MCP tool or automatic host setup is added.

Some existing advanced verbs still require checkout assets (Lab registry or
Decision Plane configuration). This delivery verifies the packaged diagnostic
core and new portable verbs, not universal wheel availability of every advanced
verb. Supply their declared configuration explicitly when required.
