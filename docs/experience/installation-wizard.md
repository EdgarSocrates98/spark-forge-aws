# Installation wizard

Bare `sparkforge-aws install` on a TTY opens the guided wizard. On a non-TTY it
returns the structured approval refusal without reading stdin or writing files.
Explicit flags keep the deterministic CLI contract.

## Steps

1. **Environment check** — real evidence: Python version, git, host
   binaries on PATH.
2. **Scope** — `project` / `workspace` / `user`.
3. **Profile** — Balanced (recommended), Economy (minimal), Full.
4. **Execution profile** — Economy, Balanced or Deep; independent from the
   component profile and forwarded as `gateway_profile`.
5. **Optional components** — multi-select with profile defaults:
   `skills`, `agents`, `mcp`, `tui`, `graph-studio`. Unchecked components
   are persisted to `components.json`; e.g. declining `graph-studio`
   makes `graph ui` refuse with an unlock hint.
6. **Hosts** — multi-select over detected AI hosts.
7. **Review** — the real dry-run plan (managed writes count + paths). Dry-run
   does not create lock, ledger or state directories.
8. **Confirm** — explicit approval; Esc cancels with zero writes.
9. **Apply** — the governed install runs (`--yes` equivalent, with
   locking, ledger, rollback on failure).
10. **Verify** — `install doctor` health report; string and nested health
    envelopes are both rendered without assuming one shape.

Non-interactive equivalent:

```bash
sparkforge-aws install --scope project --profile recommended --host all --dry-run
sparkforge-aws install --scope project --profile recommended --host all --yes
# execution profile:
sparkforge-aws install --scope project --profile recommended --gateway-profile balanced --host all --yes
# optional components:
sparkforge-aws install --yes --components skills,mcp,tui,graph-studio
sparkforge-aws install doctor
```

## States shown

The wizard and dashboards distinguish honestly:

- `INSTALLED` — ledger records the install (not proof of health).
- `CONFIGURED` — CLI probe passes.
- `READY`/`HEALTHY` — verification checks pass.
- `RESTART_REQUIRED` — host assets written; the host reads them next
  session (never claimed as ACTIVE).
- `UNVERIFIED` — no evidence either way.

## Evidence

The focused install gate covers dry-run state cleanliness, doctor output after
apply, TTY routing and independent `gateway_profile` propagation. Real host
handshake remains `UNVERIFIED` when the optional MCP extra or host binary is
absent.
