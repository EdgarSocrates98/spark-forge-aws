---
sdd: 1
feature: SDD_ENDURECIMENTO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_ENDURECIMENTO/define.md
  sha256: "fbeea62763d25acb4c019524e08513be84b2cb9a3aebc8c1d8bb00ada49c4b05"
files:
  - {path: sparkforge/sdd/checks.py, action: modify, reason: "historia so com a evidencia sumida, gate da evidence do ship, moved_change_mismatch, relatorio confinado"}
  - {path: sparkforge/sdd/schema/ship.json, action: modify, reason: "campo opcional evidence: [{change_id, report_sha256}]"}
  - {path: tests/test_sdd.py, action: modify, reason: "AC1 a AC6 e AC9; feature_limpa operator passa a gravar evidence"}
  - {path: tests/test_sdd_operator.py, action: modify, reason: "AC8 e AC10"}
  - {path: tests/test_sdd_eval_suite.py, action: modify, reason: "AC11"}
  - {path: docs/sdd/CONTRATO.md, action: create, reason: "contrato vivo: campos por fase e todo codigo com quando e fase"}
  - {path: docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md, action: modify, reason: "ponteiro no topo para o contrato vivo; o resto do texto fica"}
  - {path: docs/sdd/README.md, action: modify, reason: "evidence, historia com evidencia sumida, link para CONTRATO.md"}
  - {path: skills/sdd-ship/SKILL.md, action: modify, reason: "perfil operator grava evidence; codigos novos"}
  - {path: skills/sdd-build/SKILL.md, action: modify, reason: "moved_change_mismatch; link para o contrato"}
  - {path: .gitattributes, action: modify, reason: "comentario de fixtures/sdd: text_sha256, e -text pelos bytes iguais entre plataformas"}
  - {path: evals/agentic/sdd/README.md, action: modify, reason: "N=2 de duas invocacoes --repeat 1"}
  - {path: docs/surface.lock.json, action: modify, reason: "as duas skills mudam de tamanho (regra 26)"}
  - {path: .claude/skills, action: modify, reason: "espelho regenerado por scripts/sync_skills.py"}
decisions:
  - id: D1
    choice: "Depois do ship done, moved e finding so deixam de ser conferidos quando nenhum arquivo de relatorio existe nas duas pastas da mudanca; relatorio presente e sempre conferido, e relatorio presente mas ilegivel conta como nao observado."
    rejected: ["manter o desligamento total depois do ship done, que aceita change_id fabricado", "conferir sempre, que recusa todo sandbox limpo depois da entrega"]
    rollback: "git revert do commit da tarefa T3."
  - id: D2
    choice: "ship.evidence e obrigatorio no operator: uma entrada {change_id, report_sha256} para cada change_id que a feature cita (o do build, o de moved e o de finding explicito). Sem entrada, ship_evidence_missing; relatorio presente com text_sha256 diferente, ship_evidence_mismatch. Todo relatorio presente precisa casar: sandbox/report.json e proposal/evidence/sandbox_report.json sao a mesma serializacao (sparkforge/change/sandbox.py e sparkforge/change/proposal.py::_json)."
    rejected: ["guardar o relatorio inteiro no ship, que duplica o artefato e nao prova mais que o hash", "aceitar se qualquer um dos relatorios casar, que deixa um relatorio forjado ao lado do legitimo"]
    rollback: "git revert do commit da tarefa T3; o campo e opcional no schema, entao ships antigos continuam validos no dev."
  - id: D3
    choice: "evidence no perfil dev e schema_invalid, como proof e moved; o ship dev segue sem o campo."
    rejected: ["ignorar o campo no dev, que deixaria afirmacao sem conferencia"]
    rollback: "git revert do commit da tarefa T3."
  - id: D4
    choice: "case_missing continua desligado depois do ship done: o case nao tem relatorio, e case.yaml e reescrito por case open --reopen."
    rejected: ["gravar o case no evidence, sem arquivo que o sustente depois da reabertura"]
    rollback: "Nada a desfazer: comportamento mantido."
  - id: D5
    choice: "O teste de contrato le checks.py e stamp.py por ast: a primeira constante de texto passada a recusa, lacuna e StampError, mais os dicionarios com chave code; e le do CONTRATO.md os codigos da coluna codigo das tabelas. As duas listas precisam ser iguais."
    rejected: ["lista de codigos escrita a mao no teste, que envelhece calada", "regex sobre o fonte, que pega texto de docstring"]
    rollback: "git revert do commit da tarefa T4."
  - id: D6
    choice: "O teste de contrato mora em tests/test_sdd.py, nao em arquivo novo: arquivo .py novo move alegacoes do gate de lastro sem ganho."
    rejected: ["tests/test_sdd_contrato.py"]
    rollback: "Mover o teste; nada depende do arquivo."
covers:
  - {part: "historia com evidencia sumida e evidence do ship", acceptance: [AC1, AC2, AC3, AC4, AC7, AC8]}
  - {part: "moved do build e relatorio confinado", acceptance: [AC5, AC6]}
  - {part: "contrato vivo", acceptance: [AC9]}
  - {part: "skills e README", acceptance: [AC10]}
  - {part: "notas de hash e de baseline", acceptance: [AC11]}
---

# SDD_ENDURECIMENTO — desenho

## A regra depois do ship done

| situação da mudança citada | `moved` / `finding` | `ship.evidence` |
|---|---|---|
| nenhum relatório nas duas pastas | não conferidos (história) | a entrada precisa existir; o hash não tem com o que comparar |
| relatório presente | conferidos como antes do ship | `text_sha256` de **cada** relatório presente igual ao gravado |

Antes do ship done nada muda, exceto que `evidence`, quando já existe,
também é conferido contra relatório presente.

## Os ids citados

`_ids_citados`: o `change_id` do build (não vazio), o `change_id` de cada
`moved`, e o prefixo de cada `proof` `finding` do plan com prefixo não vazio.
Com AC5, o de `moved` é sempre o do build, mas o conjunto não depende disso.

## Códigos novos

- `refused: ship_evidence_missing` — ship operator sem entrada de `evidence`
  para um id citado (campo `evidence`).
- `refused: ship_evidence_mismatch` — relatório presente com `text_sha256`
  diferente do `report_sha256` gravado (campo `evidence/<i>/report_sha256`).
- `refused: moved_change_mismatch` — `moved.change_id` diferente do
  `change_id` do build (campo `tasks/<i>/moved/change_id`).

## Contrato vivo

`docs/sdd/CONTRATO.md`: campos comuns e por fase (lidos dos schemas), a tabela
de recusas e a de lacunas com quando e fase, as regras do operador (proof,
moved, seletor por kind, história, evidence) e as recusas do `stamp`. O spec
congelado ganha só um aviso no topo.
