---
sdd: 1
feature: SDD_SKILLS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_SKILLS/define.md
  sha256: "8a2a65d2c7f9362e390acadd0cc1fb14466b8de7022cc1c75597109eacf062f7"
files:
  - {path: skills/sdd-explore/SKILL.md, action: create, reason: "fase explore: uma pergunta por vez, 2-3 abordagens, perfil escolhido no inicio"}
  - {path: skills/sdd-define/SKILL.md, action: create, reason: "fase define: hipotese, acceptance com verified_by, success com source, unknowns, change_kinds"}
  - {path: skills/sdd-design/SKILL.md, action: create, reason: "fase design: manifesto conferido com code_symbol, decisoes com rollback, covers"}
  - {path: skills/sdd-plan/SKILL.md, action: create, reason: "fase plan: tarefas pequenas com teste e codigo completo, sem placeholder"}
  - {path: skills/sdd-build/SKILL.md, action: create, reason: "fase build: TDD vermelho-verde declarado, um subagente por tarefa, revisao em dois estagios"}
  - {path: skills/sdd-ship/SKILL.md, action: create, reason: "fase ship: gates de docs/gates-por-mudanca.md, hipotese fechada, desvios, arquivo"}
  - {path: docs/sdd/templates/explore.md, action: create, reason: "esqueleto valido da fase"}
  - {path: docs/sdd/templates/define.md, action: create, reason: "esqueleto valido da fase"}
  - {path: docs/sdd/templates/design.md, action: create, reason: "esqueleto valido da fase"}
  - {path: docs/sdd/templates/plan.md, action: create, reason: "esqueleto valido da fase"}
  - {path: docs/sdd/templates/build_report.md, action: create, reason: "esqueleto valido da fase"}
  - {path: docs/sdd/templates/ship.md, action: create, reason: "esqueleto valido da fase"}
  - {path: docs/sdd/README.md, action: create, reason: "o que e o SDD proprio, onde moram as features, os tres verbos"}
  - {path: tests/test_sdd_skills.py, action: create, reason: "AC1 a AC4"}
  - {path: vendor/CREDITS.md, action: modify, reason: "credito ao AgentSpec e ao superpowers (MIT)"}
  - {path: scripts/sync_skills.py, action: modify, reason: "entrada das seis skills na tabela de despacho, se exigida"}
decisions:
  - id: D1
    choice: "As seis skills sao nao despachaveis: dirigem a sessao e o operador, nao investigam artefato fechado (criterio D-6 de scripts/sync_skills.py)."
    rejected: ["sdd-build despachavel, porque ele mesmo despacha subagentes e precisa do contexto do pai"]
    rollback: "Remover as entradas das seis skills da tabela de despacho e rodar python scripts/sync_skills.py."
  - id: D2
    choice: "Templates sao artefatos validos de uma feature de exemplo, e nao texto com marcadores <...>, para que um teste prove que o formato ensinado passa no gate."
    rejected: ["templates com placeholders livres, que ensinariam um formato que o gate recusa"]
    rollback: "git revert do commit dos templates; as skills continuam apontando o schema em sparkforge/sdd/schema/."
  - id: D3
    choice: "TDD e execucao por subagente moram dentro de sdd-build, e nao numa skill tdd separada."
    rejected: ["skill sdd-tdd a parte, que duplicaria o laco vermelho-verde e o registro no build_report"]
    rollback: "Extrair a secao de TDD para skills/sdd-tdd/SKILL.md e citar a partir de sdd-build."
  - id: D4
    choice: "Skills em portugues, description comecando por 'Use quando', com as secoes Quando NAO usar, Referencia rapida e Red flags (tests/test_skill_content.py)."
    rejected: ["copiar o texto em ingles dos plugins"]
    rollback: "Reescrever o texto; o contrato das secoes e do teste existente."
covers:
  - {part: "skills", acceptance: [AC1, AC3, AC5]}
  - {part: "templates", acceptance: [AC2]}
  - {part: "credito", acceptance: [AC4]}
---

# SDD_SKILLS — desenho

## As seis skills

| skill | substitui | o que ela exige do agente | onde o gate confere |
|---|---|---|---|
| `sdd-explore` | superpowers brainstorming, AgentSpec brainstorm | perfil (`dev`/`operator`) escolhido primeiro; uma pergunta por vez; 2-3 abordagens com trade-offs e recomendacao | schema de explore |
| `sdd-define` | AgentSpec define, parte de brainstorming | hipotese em tres partes; acceptance com `verified_by` real; `success` com `source`; `unknowns` com `unlock`; `change_kinds` da lista fechada | `success_without_source`, `schema_invalid`, `test_not_written`, `case_missing` |
| `sdd-design` | AgentSpec design | manifesto conferido com `sparkforge_code_symbol`/`code_path` antes de marcar `modify`; conhecimento por `rules_lookup`/`knowledge_path`, nunca memoria; decisao com `rejected` e `rollback` | `manifest_path_unknown`, `rollback_missing`, `acceptance_uncovered` |
| `sdd-plan` | superpowers writing-plans | tarefa de 2-5 minutos com teste nomeado e codigo completo; zero placeholder; cobertura de todo AC | `task_without_test`, `acceptance_uncovered` |
| `sdd-build` | superpowers executing-plans, subagent-driven-development, test-driven-development; AgentSpec build | lei do vermelho antes do verde; `red`/`green` registrados com comando e exit; um subagente por tarefa com o texto da tarefa; revisao de spec e depois de qualidade; claim so com `evidence_ref`; perfil operator so por `change sandbox` | `red_not_declared`, `claim_without_evidence`, `change_missing`, `verified_by_dangling` |
| `sdd-ship` | AgentSpec ship, superpowers finishing-a-development-branch (parte) | rodar os gates das secoes de `change_kinds`; listar os registros; fechar a hipotese sem reescreve-la; desvios; STATUS | `hypothesis_open_at_ship`, `registry_unchecked` |

Toda skill termina a fase do mesmo jeito: `sparkforge sdd stamp` na fase escrita
(quando ela tem upstream) e `sparkforge sdd check --feature <F>`; `status: ready`
so com zero recusa.

## Cascata

Mudou uma fase? `sparkforge sdd status` mostra quem ficou `upstream_stale`. A
skill da fase de baixo revisa o conteudo **antes** de carimbar: carimbar sem
revisar e o erro que a cascata existe para pegar.
