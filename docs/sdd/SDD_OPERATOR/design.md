---
sdd: 1
feature: SDD_OPERATOR
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_OPERATOR/define.md
  sha256: "81590210f2d3e517fbe2b5ad59c544877becd1dee22ab34ba7b9eb1c73a6df04"
files:
  - {path: sparkforge/sdd/checks.py, action: modify, reason: "funcval_not_comparison e funcval_blind_spot no gate de verified_by"}
  - {path: tests/test_sdd.py, action: modify, reason: "AC2 e AC3"}
  - {path: tests/test_sdd_operator.py, action: create, reason: "AC1 e AC4"}
  - {path: agents/spark-performance-architect.md, action: modify, reason: "paragrafo que cita sdd-define e sdd-build e diz quando abrir a spec"}
  - {path: agents/glue-incremental-performance-architect.md, action: modify, reason: "idem"}
  - {path: agents/glue-infra-reviewer.md, action: modify, reason: "idem"}
  - {path: agents/pyspark-code-reviewer.md, action: modify, reason: "idem"}
  - {path: skills/sdd-define/SKILL.md, action: modify, reason: "perfil operator: case_id e aceite por funcval ou fact (acrescimo do build)"}
  - {path: skills/sdd-plan/SKILL.md, action: modify, reason: "perfil operator: o test da tarefa (acrescimo do build)"}
  - {path: skills/sdd-build/SKILL.md, action: modify, reason: "perfil operator: red, green e o pacote do PR (acrescimo do build)"}
  - {path: docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md, action: modify, reason: "os dois codigos novos na tabela do paragrafo 5"}
decisions:
  - id: D1
    choice: "O gate confere a FORMA do arquivo do funcval (ha check_delta, ha unresolved), nunca o veredito."
    rejected: ["recusar quando algum delta passa de um limiar, o que poria limiar dentro do gate de spec (regra 11)"]
    rollback: "Voltar _gate_verified_by a conferir so a existencia do arquivo."
  - id: D2
    choice: "Os coordenadores ganham um paragrafo curto que cita as skills sdd-define e sdd-build na PROSA, fora do skills do frontmatter; o texto da skill continua o unico lugar do procedimento."
    rejected:
      - "copiar o procedimento do SDD para cada coordenador"
      - "listar as skills no skills do frontmatter (revisto no build): as sdd-* estao em NON_DISPATCHABLE_SKILLS porque perguntam e despacham, e o coordenador roda como subagente; o precedente e diagnose-lakeformation-access, citada so na prosa"
    rollback: "Remover o paragrafo de cada coordenador e rodar python scripts/sync_skills.py."
  - id: D3
    choice: "O teste ponta a ponta usa call_tool com sparkforge_case_open e sparkforge_change_sandbox reais sobre um repositorio sintetico em tmp_path."
    rejected: ["fabricar .sparkforge/case.yaml e .sparkforge/sandbox/<id> a mao, que e o que o teste do nucleo ja faz"]
    rollback: "git revert do commit do teste."
covers:
  - {part: "gate funcval", acceptance: [AC2, AC3]}
  - {part: "fluxo ponta a ponta", acceptance: [AC1]}
  - {part: "coordenadores e skills", acceptance: [AC4]}
---

# SDD_OPERATOR — desenho

## Gate do funcval

`_gate_verified_by`, ramo `funcval`, depois de achar o arquivo:

- le como lista de facts (lista crua ou `{"items": [...]}`, o mesmo leitor de
  `_ids_de_fact`);
- nenhum `kind == "funcval.check_delta"` → recusa `funcval_not_comparison`, com
  unlock `sparkforge funcval compare --plan ... --before ... --after ... --out <ref>`;
- cada `funcval.unresolved` → lacuna `funcval_blind_spot` nomeando o `subject`
  do fact.

## Fluxo operator ponta a ponta

1. `call_tool("sparkforge_case_open", {"repo", "case_id", "now"})`.
2. Repositorio sintetico com um arquivo de job; um diff unificado que muda uma
   linha; `call_tool("sparkforge_change_sandbox", {"repo", "diff_path"})` e o id
   devolvido vira `change_id`.
3. Arquivo de comparacao sintetico com um `funcval.check_delta` (a forma exata
   sai de `sparkforge/facts/funcval.py::_check_delta`).
4. Feature operator (define com `case_id`, `verified_by` funcval; build_report
   com `change_id`), carimbada em ordem; `check` sai sem recusa.
5. Negativos: sem o sandbox → `change_missing`; comparacao sem delta →
   `funcval_not_comparison`.
