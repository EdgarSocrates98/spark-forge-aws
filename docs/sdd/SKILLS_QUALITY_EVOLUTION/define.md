---
sdd: 1
feature: SKILLS_QUALITY_EVOLUTION
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Um contrato comum de evidência, referências, scripts e evals offline em todas as 52 skills fonte torna a superfície verificável sem remover os procedimentos específicos."
  prediction: "A auditoria encontra 52 skills conformes, a suíte offline passa 104/104 casos, os espelhos sincronizam e nenhum gate atribui ganho de modelo, token ou custo."
  experiment: "Executar audit_skills, check_skill_evals, run_skill_evals --offline, quick_validate em amostra, sync_skills --check, gen_reference_docs e as suítes finais do repositório."
acceptance:
  - id: AC1
    statement: "Todas as 52 skills canônicas têm contrato v1, limite, evidência, unresolved, validação e rollback."
    verified_by: {kind: test, ref: "tests/test_skill_quality.py::test_all_source_skills_follow_contract"}
  - id: AC2
    statement: "Todas as 52 skills têm evals/evals.json no schema skill-creator, com ao menos dois casos e expectations verificáveis."
    verified_by: {kind: test, ref: "tests/test_skill_quality.py::test_all_source_skills_have_skill_creator_evals"}
  - id: AC3
    statement: "A execução offline cobre 104 casos, sem provider ou AWS, e todos passam."
    verified_by: {kind: test, ref: "tests/test_skill_quality.py::test_offline_eval_runner_is_complete_and_has_no_provider_side_effect"}
  - id: AC4
    statement: "Os espelhos Claude e Devin são renderizações atuais da fonte e os recursos auxiliares não introduzem drift."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check"}
  - id: AC5
    statement: "As páginas de referência, superfície e claims ficam regeneradas e auditáveis após a evolução dos assets."
    verified_by: {kind: command, ref: "python scripts/gen_reference_docs.py"}
  - id: AC6
    statement: "A suíte completa de testes do repositório passa nos lotes sequenciais finais, com contagem registrada no build_report."
    verified_by: {kind: command, ref: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest_final <lote> -q"}
success:
  - id: SC1
    metric: "Skills fonte em conformidade"
    source: "python scripts/audit_skills.py --strict"
  - id: SC2
    metric: "Casos eval offline passados"
    source: "python scripts/run_skill_evals.py --offline"
  - id: SC3
    metric: "Espelhos e referências regenerados"
    source: "python scripts/sync_skills.py --check e python scripts/gen_reference_docs.py"
out_of_scope:
  - "Benchmark de modelo, comparação with-skill/baseline, tokens de provider, latência ou custo."
  - "Mudança no núcleo de extração/julgamento SparkForge ou em infraestrutura AWS live."
  - "Inventar referências externas quando a fonte local offline não as registra."
unknowns:
  - id: U1
    blocks: []
    unlock: "Provider benchmark separado, com transcripts e grader, se houver caso e autorização explícitos."
change_kinds: [agent_or_skill, claims]
---

# SKILLS_QUALITY_EVOLUTION — definição

O trabalho transforma qualidade de skill em artefato verificável: cada skill
continua dona do seu procedimento, mas publica o mesmo contrato de evidência e
um caminho determinístico para validar handoff. O runner offline é piso de
estrutura, não avaliação de inteligência do modelo.
