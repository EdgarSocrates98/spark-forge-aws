---
sdd: 1
feature: SDD_OPERATOR_DURAVEL
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_OPERATOR_DURAVEL/define.md
  sha256: "e8100f2f60f7d23d6658ce5ab55cb389967a4546eb9c34fecbefd51703d2b165"
files:
  - {path: sparkforge/sdd/checks.py, action: modify, reason: "change_id pelo sandbox ou pela proposal, referencia historica depois do ship done, seletor por kind, proof de tarefa e moved conferido no relatorio"}
  - {path: sparkforge/sdd/schema/plan.json, action: modify, reason: "tasks[].proof fechado (kind, ref)"}
  - {path: sparkforge/sdd/schema/build_report.json, action: modify, reason: "tasks[].moved fechado (change_id, resolved)"}
  - {path: tests/test_sdd.py, action: modify, reason: "AC2 a AC7"}
  - {path: tests/test_sdd_operator.py, action: modify, reason: "AC1 (ponta a ponta com raiz .sparkforge/sdd, proof, moved e change propose) e AC8"}
  - {path: skills/sdd-define/SKILL.md, action: modify, reason: "raiz do operador e seletor por kind"}
  - {path: skills/sdd-plan/SKILL.md, action: modify, reason: "proof de tarefa no operator"}
  - {path: skills/sdd-build/SKILL.md, action: modify, reason: "moved no operator, raiz do operador e comandos com as flags de evidencia"}
  - {path: skills/sdd-ship/SKILL.md, action: modify, reason: "raiz do operador, referencia historica depois do done e o pacote do PR com evidencia"}
  - {path: docs/sdd/README.md, action: modify, reason: "raiz do operador e onde a arvore do operador muda"}
  - {path: docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md, action: modify, reason: "paragrafo 5.0 com os codigos e regras novos"}
  - {path: .claude/skills/sdd-define/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .claude/skills/sdd-plan/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .claude/skills/sdd-build/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .claude/skills/sdd-ship/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .agents/skills/sdd-define/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .agents/skills/sdd-plan/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .agents/skills/sdd-build/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: .agents/skills/sdd-ship/SKILL.md, action: modify, reason: "espelho (sync_skills)"}
  - {path: docs/guia/referencia/skills/sdd-define.md, action: modify, reason: "referencia gerada (gen_reference_docs)"}
  - {path: docs/guia/referencia/skills/sdd-plan.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-build.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-ship.md, action: modify, reason: "referencia gerada"}
  - {path: docs/surface.lock.json, action: modify, reason: "bytes de skills (regra 26)"}
  - {path: docs/claims.lock.json, action: modify, reason: "alegacoes que o arquivo de teste maior move, remediadas por id"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "linha de Skills nomeia a entrega"}
decisions:
  - id: D1
    choice: "Os artefatos SDD do operador moram em .sparkforge/sdd no repositorio dele (--root .sparkforge/sdd); a arvore do job continua mudando so por change sandbox e change propose. A varredura do sandbox poda .sparkforge, entao escrever ali nao desatualiza a copia validada; a raiz passada a discover nunca e podada, so as subpastas."
    rejected:
      - "docs/sdd no repositorio do operador: muda a arvore que change sandbox copiou e change propose recusa com sandbox_desatualizado (medido no teste ponta a ponta)"
      - "uma pasta fora do repositorio: o upstream e resolvido dentro de --repo (resolve_within) e o stamp recusaria"
    rollback: "git revert dos commits de skill e README; o nucleo nao muda, porque --root ja existia."
  - id: D2
    choice: "change_id vale quando .sparkforge/sandbox/<id>/ OU .sparkforge/proposal/<id>/ existe como diretorio; o id e um segmento so e cada base e conferida pelo mesmo confinamento de hoje. O id da proposal e o do sandbox (proposal.montar grava em PROPOSAL_DIR/ident)."
    rejected:
      - "so o sandbox: change sandbox --clean apaga a unica prova e a feature entregue volta a ser recusada"
      - "ler o manifest.json da proposal para achar o id do sandbox: o nome da pasta ja e o id"
    rollback: "Voltar _gate_change a olhar so SANDBOX_DIR."
  - id: D3
    choice: "case_missing, change_missing, a conferencia de moved e a de proof finding so rodam enquanto o ship da feature nao carregou com status done; com o ship done, essas referencias sao historicas. Fact e funcval continuam conferidos sempre, porque o arquivo e do operador e nao e estado recriado."
    rejected:
      - "conferir sempre: o case.yaml atual pode ser de outro case e o sandbox pode ter sido limpo, e a feature entregue ficaria recusada para sempre"
      - "nunca conferir no operator: perde o gate enquanto a feature esta viva"
    rollback: "Remover o retorno antecipado por _ship_feito dos quatro gates."
  - id: D4
    choice: "O ref de verified_by kind fact aceita path#kind:<kind>, que passa com ao menos um fact daquele kind no arquivo; path#<id> segue igual. O mesmo leitor serve a proof kind fact."
    rejected:
      - "exigir o id: o id e hash de conteudo e so existe depois da coleta, entao o define nunca fecharia antes dela"
      - "casar por prefixo de kind: pertence ao judge e ao where das regras, nao ao gate de spec"
    rollback: "Voltar _gate_verified_by a comparar so ids."
  - id: D5
    choice: "No operator, tasks[].proof {kind funcval|fact|finding, ref} substitui test; finding e <change_id>#<rule_id>, e change_id vazio (#<rule_id>) usa o change_id do build_report, porque o id do sandbox e hash e nao existe na hora do plano. No dev, proof e schema_invalid e test segue obrigatorio (task_without_test). Antes do build pronto, achado nao observado e lacuna finding_not_observed; depois, recusa moved_not_observed."
    rejected:
      - "exigir sempre o id explicito no ref: o plano teria de ser reescrito e recarimbado depois do sandbox, e a cascata marcaria o build como stale"
      - "aceitar proof no dev: o dev tem pytest, e o vermelho antes do verde e a lei do build"
    rollback: "Remover proof do schema de plan e o ramo de _gate_task_test."
  - id: D6
    choice: "No operator, tasks[].moved {change_id, resolved} substitui red e green; o gate le .sparkforge/sandbox/<id>/report.json ou .sparkforge/proposal/<id>/evidence/sandbox_report.json e exige cada rule_id em resolved e ausente de new; senao, recusa moved_not_observed. No dev, moved e schema_invalid e red segue exigido."
    rejected:
      - "ler after/.sparkforge/scan/findings.json para provar a ausencia total da regra: o pacote de proposal nao carrega o scan, e o report ja e o que sandbox e propose gravam"
      - "aceitar moved sem ler o relatorio: seria um exit inventado com outro nome"
    rollback: "Remover moved do schema de build_report e o ramo de _gate_red."
covers:
  - {part: "raiz do operador e fluxo ponta a ponta", acceptance: [AC1]}
  - {part: "change_id pela proposal", acceptance: [AC2]}
  - {part: "referencia historica", acceptance: [AC3]}
  - {part: "seletor por kind", acceptance: [AC4]}
  - {part: "proof de tarefa", acceptance: [AC5, AC7]}
  - {part: "moved no build", acceptance: [AC6, AC7]}
  - {part: "skills, README e espelhos", acceptance: [AC8, AC9]}
---

# SDD_OPERATOR_DURAVEL — desenho

## Conhecimento consultado

Nada de Glue, Spark ou Iceberg: a mudança é no gate e no texto. Lido no código:

- `sparkforge/change/sandbox.py`: `SANDBOX_DIR`, `executar` grava
  `report.json` com `new` e `resolved` (cada item com `rule_id` e `subject`),
  e `inventariar` poda `.sparkforge` (só `.sparkforge/artifacts/` entra).
- `sparkforge/change/proposal.py`: `PROPOSAL_DIR`, `montar` grava em
  `PROPOSAL_DIR/<ident>` com o mesmo id e copia o relatório para
  `evidence/sandbox_report.json`; `desatualizados` recusa a proposta quando a
  árvore difere de `before/`.
- `sparkforge/facts/scan.py::varrer_source_files` só poda subpastas; a raiz
  passada nunca é podada.
- `.gitignore` deste repositório ignora `.sparkforge/sandbox/` e
  `.sparkforge/proposal/`, e não ignora `.sparkforge/sdd/`. O repositório do
  operador tem o próprio `.gitignore`; as skills dizem para não ignorar a pasta
  da spec.

## Gates

| gate | antes | depois |
|---|---|---|
| `_gate_case` | sempre no operator | pula com ship `done` |
| `_gate_change` | só `SANDBOX_DIR` | `SANDBOX_DIR` ou `PROPOSAL_DIR`; pula com ship `done` |
| `_gate_verified_by` (fact) | `#<id>` | `#<id>` ou `#kind:<kind>` |
| `_gate_task_test` | `test` obrigatório | operator: `test` ou `proof`; dev: `proof` é `schema_invalid` |
| `_gate_red` | `red` obrigatório | operator: `red` ou `moved`; dev: `moved` é `schema_invalid` |

Códigos novos: `refused: moved_not_observed` e
`unresolved: finding_not_observed`.
