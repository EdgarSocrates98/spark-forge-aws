---
sdd: 1
feature: LAKE_FORMATION_PROMPT_GAP_AUDIT
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_PROMPT_GAP_AUDIT/build_report.md
  sha256: "7f3f48d02c67d796bfc503f339facf9d91752bbc09f0dc9f41123892676af8ed"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, sync_skills, agents_parity, surface_lock, generated_reference, claims_gate]
deviations:
  - "A suíte completa local não foi repetida por orientação do operador; a validação ampla fica no CI do PR e no histórico da main."
  - "A auditoria completa de proofs do claims gate foi interrompida por duração; a consistência estrutural e o teste do manifesto passaram."
  - "A aceitação documental foi marcada como guard de regressão porque não houve vermelho isolado honesto antes da edição dos docs."
---

# LAKE_FORMATION_PROMPT_GAP_AUDIT — entrega

## Resultado

Confirmado. A auditoria final do prompt agora possui casos executáveis para as
combinações antes implícitas e regressões explícitas dos cinco gaps críticos.
O migration report publica seções estruturadas sem transformar hipótese em
capability, e progressive disclosure separa referências de Glue e EMR.

## Gates rodados

- `pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q` — exit 0; 16 passed.
- `pytest --basetemp .pytest-temp tests/test_lakeformation_architecture.py tests/test_lakeformation_fgac_fta_improvements.py tests/test_lakeformation_prompt_acceptance.py -q` — exit 0; 37 passed.
- `ruff check sparkforge_aws/lakeformation/architecture.py tests/test_lakeformation_prompt_acceptance.py` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0; 58 checked.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `pytest --basetemp E:\pytest-sf-temp tests/test_vnext_claims.py::TestGateReal::test_o_manifesto_do_repositorio_esta_consistente -q` — exit 0.
- `sparkforge-aws sdd check --repo . --feature LAKE_FORMATION_PROMPT_GAP_AUDIT` — exit 0.

## Limites

Nenhuma coleta AWS, mutação, benchmark, DPUSeconds, CloudTrail, IAM, grant,
RAM, KMS ou medição de tokens foi feita. O CI do PR continua a validação de
integração; `consistent` permanece limitado aos facts declarados no payload.

## Lições

- Uma matriz declarativa pode aparentar cobertura enquanto um cenário cross-account
  ainda está local por falta de `cross_account=true`; cada caso precisa afirmar a
  topologia, não apenas o nome da rota.
- O migration report só é auditável quando suas dimensões aparecem como campos
  estruturados; listas legadas sozinhas escondem lacunas de Python, Terraform e IDs.
