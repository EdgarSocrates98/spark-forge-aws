---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_EVOLUTION/build_report.md
  sha256: "8ed859df8723af66a0211f611776aa72328913ebbbc3bc0a0081d5c363733fab"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, sync_skills, agents_parity, surface_lock, generated_reference, status_numbers_gate, claims_gate]
deviations:
  - "O change kind fixture_corpus foi removido porque a entrega não acrescentou corpus novo; os goldens derivados atualizados foram declarados no T3."
  - "A superfície MCP passou de 114 para 115 tools, com 52 skills e 19 skills despacháveis; locks, manifestos, referências, status e testes de contagem foram atualizados pelos medidores."
  - "O cenário de fronteira de import relativo foi isolado em runtime temporário para evitar mutação do checkout e falha de restauração no Windows."
  - "Não houve chamada AWS, concessão de permissão, alteração de infraestrutura ou claim de custo/performance."
---

# LAKE_FORMATION_FGAC_FTA_EVOLUTION — entrega

## Hipótese

Confirmada pelos AC1–AC12: o contrato declarativo compõe runtime/engine,
FGAC/FTA, formato, operação, ownership, cross-account e credential vending;
preserva `unresolved`/`blocked` quando a evidência ou capability não fecha; e
CLI/MCP retornam o mesmo payload. A hipótese não afirma ganho de custo,
latência ou tokens.

## Gates rodados

- `python scripts/refresh_knowledge.py --update --offline` — exit 0; 276 fontes,
  261 móveis, 15 fixas.
- `python scripts/verify_offline_bundle.py` — exit 0; 57 verificadas.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py` — exit 0; 242 páginas sem divergência.
- `python scripts/check_surface_lock.py` — exit 0; lock atualizado e conferido.
- `python scripts/check_status_numbers.py --strict` — exit 0; 0 divergências.
- `python scripts/check_vnext_claims.py` — exit 0; 0 divergências.
- `python -m pytest tests/test_vnext_claims.py tests/test_installed_provenance.py -q` — exit 0; 147 passed, 5 skipped.
- `python -m pytest tests/test_sync_render.py tests/test_docs_coverage.py tests/test_agents_parity.py tests/test_agent_coverage.py -q` — exit 0; 203 passed.
- `python -m pytest tests/test_reference_docs.py -q` — exit 0; 5 passed.
- `ruff check` nos módulos e testes tocados — exit 0.
- Suíte completa em nove lotes disjuntos — exit 0: 13675 passed, 14 skipped.

## Entrega

- Matriz version-aware e loader para Glue, EMR EC2 e EMR Serverless.
- Routing de ownership de catálogo sem aliasar `glue.id` e `glue.account-id`.
- Decision engine offline para FGAC/FTA, read/write, credential vending e
  cross-account, com checks nomeados, riscos e rollback.
- Verbo `sparkforge lakeformation architect` e tool MCP
  `sparkforge_lakeformation_architect` com paridade de payload.
- Knowledge, skill, coordenadores, espelhos, referências geradas, manifesto,
  locks de surface/sources/claims, guia e VNX atualizados.

## Lições

- Contadores de superfície devem ser atualizados junto com a tool, os goldens e
  a documentação corrente; a suíte encontrou cada expectativa histórica que
  ainda dizia 114.
- Testes que injetam código em arquivos reais não são seguros sob a suíte
  Windows; runtime sintético temporário preserva a prova e evita contaminar o
  teste seguinte.
- Fonte oficial ausente deve permanecer `unknown`/`unresolved`; Glue 6.x não
  foi preenchido por analogia com 5.1.
