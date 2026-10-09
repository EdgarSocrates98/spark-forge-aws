---
sdd: 1
feature: FORGE_LAB_DIGITAL_TWIN
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/FORGE_LAB_DIGITAL_TWIN/build_report.md
  sha256: "2bfbb818d2bf6e2608142fbdbcedef1794f33191f9ad565ae134f7ea39ed5f52"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, requirements_mirror, hash_locks, surface_lock, generated_reference, status_numbers_gate]
deviations:
  - "T1–T3 foram implementadas em commits anteriores ao fechamento SDD; o build registrou as tarefas como skipped porque o plano exigia adiar a suíte até o fechamento do Forge Lab, sem inventar red/green retroativo."
  - "O Compose contém serviços auxiliares além dos nove componentes mínimos do contrato; eles não são promovidos a componentes do analisador sem declaração correspondente no lab.yaml."
---

# FORGE_LAB_DIGITAL_TWIN — entrega

## Hipótese

Confirmada no escopo offline: o contrato topológico permite validar os nove
componentes, ordenar dependências e selecionar os sete cenários declarados,
preservando `mode: offline_spec_only`, `requires_confirmation` e a prontidão
unresolved até que o operador valide imagens e runtime. A análise não executa
Docker nem failure injection.

## Gates rodados

- `python -m pytest tests/test_forge_lab.py -q -p no:cacheprovider --basetemp .pytest-tmp-forge-digital-twin-final` — `3 passed`.
- `python -m sparkforge_aws.adapters.cli analyze forge-lab --path labs/forge-lab/lab.yaml` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — `0 divergencia(s)`.
- `python scripts/verify_offline_bundle.py` — `offline=true`, `70` artefatos, `failed=[]`.
- `python scripts/refresh_knowledge.py --check --offline` — `341` fontes, exit 0.
- `python scripts/gen_requirements.py --check` — exit 0.
- `python scripts/gen_lock.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — `0 divergencia(s)`.
- `python scripts/check_vnext_claims.py` — 27 divergências históricas de provas
  command; não entra em `registries` porque o gate não passou e não pertence aos
  `change_kinds` desta feature.

## Limites

O ship fecha contrato e blueprint offline. Não prova disponibilidade de imagens,
execução L1/L2/L3, latência, throughput, custo, compatibilidade de versões,
semântica AWS ou exactly-once. Essas perguntas continuam dependentes de receipt
de execução e evidência real do laboratório. As 27 divergências de claims
históricas permanecem dívida documental fora do escopo desta feature.

## Lições

- O SDD precisa ser fechado na mesma fase dos commits de implementação; quando a
  execução foi adiada por instrução operacional, a exceção deve ser guardada como
  `guard` no acceptance, nunca como red fabricado.
- O catálogo mínimo e o Compose podem crescer em ritmos diferentes; preservar a
  diferença explicitamente evita transformar serviços auxiliares em fatos não
  declarados.
