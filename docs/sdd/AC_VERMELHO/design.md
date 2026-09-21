---
sdd: 1
feature: AC_VERMELHO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/AC_VERMELHO/define.md
  sha256: "b5c21733458e22a326813765e35ab39fca5e5919535df967df1f9aa1e2cfc1f7"
files:
  - {path: tests/test_sdd_ac_vermelho.py, action: create, reason: "os quatro testes de AC1 a AC4, sobre features sinteticas em tmp_path"}
  - {path: sparkforge/sdd/checks.py, action: modify, reason: "_gate_acceptance_red novo, registrado na tupla de gates do build_report ao lado de _gate_red"}
  - {path: sparkforge/sdd/schema/define.json, action: modify, reason: "campo opcional guard (string, minLength 1) no item de acceptance, que hoje tem additionalProperties false"}
  - {path: docs/sdd/CONTRATO.md, action: modify, reason: "a recusa acceptance_never_red entra na tabela de recusas, e guard entra no campo acceptance"}
  - {path: docs/sdd/templates/define.md, action: modify, reason: "o template mostra como declarar guard"}
  - {path: skills/sdd-define/SKILL.md, action: modify, reason: "quando declarar guard, e que o verified_by precisa ser visto vermelho"}
  - {path: skills/sdd-build/SKILL.md, action: modify, reason: "o red de cada tarefa cita o node id do criterio que prova; recusa nova na lista da fase"}
  - {path: docs/surface.lock.json, action: modify, reason: "editar SKILL.md move os bytes da superficie de skills (regra 26)"}
  - {path: docs/claims.lock.json, action: modify, reason: "o .py novo move alegacoes de corpus; so as que o gate de lastro listar"}
  - {path: tests/test_sdd.py, action: modify, reason: "feature_limpa registra red com o arquivo e exit 1, que nao conta; medido com o gate dev-only, 6 testes caem. O red passa a citar o node id, e test_task_pulada_nao_exige_red passa a esperar acceptance_never_red (a tarefa pulada deixa o AC1 sem vermelho)"}
  - {path: .claude/skills/sdd-define/SKILL.md, action: modify, reason: "espelho gerado por scripts/sync_skills.py; o AC5 e sync_skills.py --check"}
  - {path: .claude/skills/sdd-build/SKILL.md, action: modify, reason: "espelho gerado por scripts/sync_skills.py; o AC5 e sync_skills.py --check"}
  - {path: .agents/skills/sdd-define/SKILL.md, action: modify, reason: "espelho gerado por scripts/sync_skills.py; o AC5 e sync_skills.py --check"}
  - {path: .agents/skills/sdd-build/SKILL.md, action: modify, reason: "espelho gerado por scripts/sync_skills.py; o AC5 e sync_skills.py --check"}
  - {path: docs/guia/referencia/skills/sdd-define.md, action: modify, reason: "referencia gerada do corpo da skill por scripts/gen_reference_docs.py; tests/test_reference_docs.py::test_referencia_em_dia cai sem ela"}
  - {path: docs/guia/referencia/skills/sdd-build.md, action: modify, reason: "referencia gerada do corpo da skill por scripts/gen_reference_docs.py; tests/test_reference_docs.py::test_referencia_em_dia cai sem ela"}
decisions:
  - id: D1
    choice: "A ligacao e derivada, nao registrada: para cada acceptance de kind test sem guard, procurar no plan as tarefas com o AC em covers, e no build_report o red delas. Conta se red.exit != 0 e (o node id do verified_by.ref esta em red.command, ou o arquivo esta em red.command e red.exit == 2)."
    rejected:
      - "Campo acceptance_red no build_report (abordagem B do explore): mais escrituracao e mais um lugar para exit inventado."
      - "Contar qualquer red no arquivo do teste: deixa escapar a guarda que passa sempre, como o SFN_TENTATIVA:AC4, que so apareceu no explore porque o red da T2 rodou o arquivo inteiro."
    rollback: "git revert do commit do gate; a tupla de gates volta ao que era."
  - id: D2
    choice: "O gate so roda com o build_report em ready ou done E o ship ausente ou fora de done. Feature entregue e historico, como no perfil operator; as 12 entregues nao se reescrevem (regra 21)."
    rejected: ["Aplicar a todas e marcar as antigas com guard: seria reescrever define de feature fechada, e 14 criterios historicos precisariam de motivo inventado depois do fato."]
    rollback: "o mesmo revert de D1."
  - id: D3
    choice: "guard e string com o motivo, nao booleano. A revisao le o motivo; um true nao diz nada."
    rejected: ["guard: true mais um campo guard_reason: dois campos para uma declaracao, e o motivo pode faltar sem que o schema perceba."]
    rollback: "git revert; o schema volta a ter additionalProperties false sem o campo."
  - id: D4
    choice: "Criterios de kind command, funcval e fact ficam fora da regra: o red de tarefa e um comando de pytest, e ligar outro kind a ele seria inventar semantica."
    rejected: ["Exigir red tambem para kind command: o command do verified_by nao e o red de tarefa nenhuma, e nao ha o que comparar."]
    rollback: "nenhum: e ausencia de regra."
  - id: D5
    choice: "O gate so age no perfil dev: com profile operator ele retorna sem conferir. No operator os criterios sao quase todos funcval ou fact, e a tarefa prova por moved, cujo contrato fica intocado."
    rejected:
      - "Aplicar nos dois perfis: um AC de kind test coberto so por tarefa com moved e sem red sairia recusado, e o caso operador do corpus dourado e tres testes operator de tests/test_sdd.py mudariam de contrato."
      - "Contar moved como vermelho: moved prova que uma regra saiu do relatorio do sandbox, nao que o teste do criterio falhou; seria inventar semantica (a mesma razao de D4)."
    rollback: "git revert do commit do gate; a checagem de perfil sai junto com o gate."
covers:
  - {part: "o gate", acceptance: [AC1, AC2, AC4]}
  - {part: "a guarda no schema", acceptance: [AC3]}
  - {part: "documentacao e skills", acceptance: [AC5]}
  - {part: "registros", acceptance: [AC6]}
---

# AC_VERMELHO — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| o gate | `sparkforge/sdd/checks.py`, `tests/test_sdd_ac_vermelho.py` | AC1, AC2, AC4 |
| a guarda no schema | `sparkforge/sdd/schema/define.json` | AC3 |
| documentação e skills | `docs/sdd/CONTRATO.md`, `docs/sdd/templates/define.md`, `skills/sdd-define/SKILL.md`, `skills/sdd-build/SKILL.md` | AC5 |
| registros | `docs/surface.lock.json`, `docs/claims.lock.json` | AC6 |

## Onde o gate mora

`sparkforge/sdd/checks.py::_GATES["build_report"]` já roda `_gate_red`, que confere
`red.exit != 0` **por tarefa**. O gate novo roda na mesma tupla e confere **por critério**:
ele lê `ctx.artefatos["define"]`, `["plan"]` e `["ship"]`, e só age com o ship ausente ou
fora de `done`.

## O vermelho desta feature

Natural: sobre uma feature sintética com um critério sem tarefa que o cubra, o gate novo
não existe e o `sdd check` passa. O teste do AC1 afirma a recusa, e falha por asserção.

## O que fica de fora, dito

A classe do `CONFIG_OCA:AC2` — teste vermelho de verdade que cobre pouco. Visto vermelho
não é o mesmo que cobre o critério; só mutação por critério chegaria lá.
