---
sdd: 1
feature: STREAMING_MANAGED_FLINK_COLLECTOR
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_COLLECTOR/build_report.md
  sha256: "262ca365f0e63a460dc0222473af8e19b9f30ab1e5a6f2ca5a9e184d02f785c8"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock]
deviations:
  - "O fact managed_flink.application também preserva application_version_id, service_execution_role e application_mode, pois são campos observados no mesmo DescribeApplication."
  - "A execução dos gates regenerou locks e páginas derivadas do knowledge/surface; nenhuma nova tool além de sparkforge_collect_managed_flink foi criada."
---

# STREAMING_MANAGED_FLINK_COLLECTOR — entrega

## Hipótese

Confirmada pelos testes focados: o cliente falso reproduziu o retorno de
`DescribeApplication`, o artifact foi consumido por `analyze flink
--artifact managed_flink`, os campos observados foram preservados, lacunas de
métricas/conectores ficaram unresolved e a segunda coleta veio do cache sem
chamada AWS. Não há claim de execução live, latência, custo ou job plan.

## Gates rodados

- `python scripts/gen_reference_docs.py --check` (exit 0)
- `python scripts/check_surface_lock.py` (exit 0)
- `python scripts/verify_offline_bundle.py --check` (exit 0)
- `python scripts/refresh_knowledge.py --check --offline` (exit 0)
- `python -m pytest tests/test_collect_managed_flink.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q -p no:cacheprovider` (exit 0; 60 passed)

## Lições

- Descrição/configuração AWS deve ter artifact próprio; misturar Managed Flink
  em `streaming_integrations` esconderia identidade e limite de API.
- `IncludeAdditionalDetails=false` reduz exposição de código/job plan, mas torna
  a ausência uma evidência explícita que precisa de artifact complementar.
