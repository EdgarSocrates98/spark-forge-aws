---
sdd: 1
feature: SKILLS_QUALITY_EVOLUTION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SKILLS_QUALITY_EVOLUTION/plan.md
  sha256: "3824d549b025f73c94cf1e4db568de10ed773eeb82b1df13919fbe4f495e52c9"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_skill_quality.py::test_all_source_skills_follow_contract -q", exit: 1}
    green: {command: "python scripts/audit_skills.py --strict", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_skill_quality.py::test_offline_eval_runner_is_complete_and_has_no_provider_side_effect -q", exit: 1}
    green: {command: "python scripts/run_skill_evals.py --offline", exit: 0}
  - id: T3
    status: done
    red: {command: "python -X utf8 skill-creator/scripts/quick_validate.py skills/*", exit: 1}
    green: {command: "quick_validate.py em cada skills/*", exit: 0}
  - id: T4
    status: done
    red: {command: "pytest focused mirrors/content", exit: 1}
    green: {command: "pytest focused mirrors/content", exit: 0}
  - id: T5
    status: done
    red: {command: "python scripts/check_vnext_claims.py", exit: 1}
    green: {command: "python scripts/check_vnext_claims.py; python scripts/check_status_numbers.py --strict", exit: 0}
  - id: T6
    status: done
    red: {command: "suítes sequenciais iniciais", exit: 1}
    green: {command: "nove lotes pytest sequenciais, basetemp fora do repo", exit: 0}
claims:
  - {text: "O catálogo canônico tem 52 skills com contrato v1, referências, scripts e manifests de eval.", evidence_ref: "python scripts/audit_skills.py --strict"}
  - {text: "O runner offline cobre 104 casos sem provider, AWS, MCP ou rede.", evidence_ref: "python scripts/run_skill_evals.py --offline"}
  - {text: "As suítes finais executadas em nove lotes sequenciais passaram 13696 testes e pularam 14 casos declarados.", evidence_ref: "build_report.md tasks.T6.green"}
---

# SKILLS_QUALITY_EVOLUTION — relatório do build

## Resultado

As 52 skills canônicas foram evoluídas sem substituir conhecimento específico.
Cada uma agora carrega contrato evidence-first, referências, validador offline e
dois casos de eval. Espelhos Claude/Devin, documentação e locks foram
regenerados.

## Evidência final

- `audit_skills --strict`: 52/52.
- `skill-creator quick_validate`: 52/52.
- `check_skill_evals --strict`: 52/52 manifests.
- `run_skill_evals --offline`: 104/104, sem provider/AWS.
- Foco: 705 testes passados.
- Suíte final: 13.696 testes passados, 14 skips declarados, nove lotes sequenciais.
- Claims, status numbers, surface, offline bundle, mirrors, docs e SDD: verdes.

## Correções de qualidade encontradas durante build

O build revelou e fechou quatro classes de drift: parser legado que não
interpretava frontmatter YAML quoted; diretório `_shared` contado como skill;
inventário de integração que não conhecia assets gerados; e temporários de
pytest dentro do repositório contaminando o índice Code Intelligence. Os testes
agora codificam o critério correto: uma skill é diretório com `SKILL.md`.
