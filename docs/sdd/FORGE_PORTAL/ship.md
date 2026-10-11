---
sdd: 1
feature: FORGE_PORTAL
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/FORGE_PORTAL/build_report.md
  sha256: "ce54f76452821634a452b84419cc9adc84959b8c7f63d26fdefe003e6c3a90db"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, verify_wheel, requirements_mirror, hash_locks]
deviations:
  - "Os artefatos SDD foram escritos apos a implementacao (ordem invertida nesta feature); os red/green registrados sao os observados de verdade no desenvolvimento, declarados a posteriori — nao reexecutados contra codigo quebrado."
  - "O E2E de install real aconteceu no proprio checkout durante validacao (o scratch foi o repo), nao num tmp: o apply devolveu refused[] honesto (host all incluia copilot ausente e .mcp.json preexistente) — a recusa e o comportamento correto, preservado."
  - "Copilot permanece UNVERIFIED (binario ausente neste host); linux/macOS nao executados — validacao Windows-native apenas."
---

# FORGE_PORTAL — entrega

## Hipótese

Confirmada: o portal serve dados reais do pacote sem fabricar estado —
jornada `NOT_INSTALLED → plano → apply → VERIFIED → MCP handshake →
primeira tarefa` fechada sobre o lifecycle real, com recibos `forge/*`
idênticos aos do CLI e recusas nomeadas preservadas.

## O que foi entregue

- `sparkforge-aws portal` — verbo que sobe o servidor stdlib vendored em
  `127.0.0.1` com token de sessão na URL, `--no-browser/--port/--root`.
- `sparkforge_aws/portal_adapter.py` — adapter `forge/PortalApi/1` sobre
  lifecycle, open_host, CanonicalRegistry, graphview e docs reais.
- `portal/assets/` — SPA Angular vendored + manifest sha256 (23 assets);
  force-included no wheel como `sparkforge_aws/portal_assets`.
- `tests/test_portal_adapter.py` — 17 testes do contrato HTTP real.
- Receita `docs/learn/recipes/portal.md`, rationale do verbo, referência
  gerada `docs/guia/referencia/cli/portal.md`, seção no README.

## Limites explícitos

O portal não substitui CLI/TUI/MCP, não roda dentro de fluxo MCP, não
lança host sem TTY (devolve o comando), não inventa estado: o que o
lifecycle não prova sai `unverified`, e mutação fora de plan→token→confirm
é recusa nomeada.

## Gates

- `tests/test_portal_adapter.py`: 17/17.
- `python scripts/check_surface_lock.py`: 0 divergências.
- `python -m pytest tests/test_reference_docs.py -q`: 5/5.
- `python -m pytest tests/test_adapters_cli.py -q`: verde.
- `python scripts/gen_requirements.py --check` / `gen_lock.py --check`: OK.
- `python scripts/verify_wheel.py`: wheel com `portal_assets` + bundle.
- E2E HTTP real: bootstrap, health, hosts, mcp (146 tools), skills (61),
  agents (19), plan/apply, task plan/execute, docs search, graphs.
