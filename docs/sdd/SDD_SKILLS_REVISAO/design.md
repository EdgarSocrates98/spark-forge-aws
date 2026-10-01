---
sdd: 1
feature: SDD_SKILLS_REVISAO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_SKILLS_REVISAO/define.md
  sha256: "24dfb14be5ff1b524d6cb05c476f9bcdfeff0d2f0b476ec41619440afe5d7c02"
files:
  - {path: tests/test_sdd_skills.py, action: modify, reason: "flags no teste de comandos (AC1) e os testes de texto AC2 a AC6"}
  - {path: skills/sdd-explore/SKILL.md, action: modify, reason: "descricao, chosen, blocos no README"}
  - {path: skills/sdd-define/SKILL.md, action: modify, reason: "descricao, sign-off, previsao mensuravel, blocos no README"}
  - {path: skills/sdd-design/SKILL.md, action: modify, reason: "descricao, blocos no README"}
  - {path: skills/sdd-plan/SKILL.md, action: modify, reason: "descricao, nomes de teste, vermelho por import, blocos no README"}
  - {path: skills/sdd-build/SKILL.md, action: modify, reason: "descricao, flags de evidencia, command refs, revisao final, leitura critica, red/green, vermelho por import, blocos no README"}
  - {path: skills/sdd-ship/SKILL.md, action: modify, reason: "descricao, flags de evidencia, command refs, desfecho inteiro, regra 21, opcoes de fechamento, Licoes, blocos no README"}
  - {path: docs/sdd/README.md, action: modify, reason: "secoes O laco de cada fase, Caminho da mudanca do operador e Conhecimento citado; ready com lacunas esperadas"}
  - {path: docs/sdd/templates/explore.md, action: modify, reason: "acentos, trocar EXEMPLO e status draft"}
  - {path: docs/sdd/templates/define.md, action: modify, reason: "acentos, trocar EXEMPLO e status draft"}
  - {path: docs/sdd/templates/design.md, action: modify, reason: "acentos, trocar EXEMPLO e status draft"}
  - {path: docs/sdd/templates/plan.md, action: modify, reason: "acentos, trocar EXEMPLO e status draft, vermelho por import"}
  - {path: docs/sdd/templates/build_report.md, action: modify, reason: "acentos, trocar EXEMPLO e status draft"}
  - {path: docs/sdd/templates/ship.md, action: modify, reason: "acentos, trocar EXEMPLO e status draft, secao Licoes"}
  - {path: .claude/skills/sdd-explore/SKILL.md, action: modify, reason: "espelho"}
  - {path: .claude/skills/sdd-define/SKILL.md, action: modify, reason: "espelho"}
  - {path: .claude/skills/sdd-design/SKILL.md, action: modify, reason: "espelho"}
  - {path: .claude/skills/sdd-plan/SKILL.md, action: modify, reason: "espelho"}
  - {path: .claude/skills/sdd-build/SKILL.md, action: modify, reason: "espelho"}
  - {path: .claude/skills/sdd-ship/SKILL.md, action: modify, reason: "espelho"}
  - {path: .agents/skills/sdd-explore/SKILL.md, action: modify, reason: "espelho"}
  - {path: .agents/skills/sdd-define/SKILL.md, action: modify, reason: "espelho"}
  - {path: .agents/skills/sdd-design/SKILL.md, action: modify, reason: "espelho"}
  - {path: .agents/skills/sdd-plan/SKILL.md, action: modify, reason: "espelho"}
  - {path: .agents/skills/sdd-build/SKILL.md, action: modify, reason: "espelho"}
  - {path: .agents/skills/sdd-ship/SKILL.md, action: modify, reason: "espelho"}
  - {path: docs/guia/referencia/skills/sdd-explore.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-define.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-design.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-plan.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-build.md, action: modify, reason: "referencia gerada"}
  - {path: docs/guia/referencia/skills/sdd-ship.md, action: modify, reason: "referencia gerada"}
  - {path: docs/surface.lock.json, action: modify, reason: "bytes de skills (regra 26)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "linha de Skills nomeia a entrega"}
decisions:
  - id: D1
    choice: "O teste de comandos passa a navegar ate o subparser do verbo e exigir que cada token --flag do comando citado esteja nas option_strings dele; marcador <...> vira um valor ficticio antes de separar os tokens, e comando cujo verbo e marcador (sparkforge <verbo>) fica fora."
    rejected:
      - "parse_args do comando inteiro com valores ficticios: fragmentos como `sparkforge funcval compare --out` nao trazem os obrigatorios e seriam recusados sem erro de flag"
      - "lista manual de flags por verbo: envelhece sem que nada acuse"
    rollback: "git revert do commit do teste."
  - id: D2
    choice: "Os blocos repetidos vao para tres secoes do docs/sdd/README.md (O laco de cada fase, Caminho da mudanca do operador, Conhecimento citado, nunca memoria); cada skill aponta para a secao numa linha e guarda so o comando da propria fase, para continuar agindo sozinha."
    rejected:
      - "manter as copias: e o que a revisao apontou como custo de contexto"
      - "tirar tambem o comando de cada skill: a skill deixaria de ser suficiente para agir, e test_seis_skills_existem exige sparkforge sdd check no texto"
    rollback: "git revert do commit de texto e python scripts/sync_skills.py."
  - id: D3
    choice: "As descricoes ficam so com o gatilho, com teto de 320 caracteres travado por teste; o resumo do fluxo sai da description e fica no corpo."
    rejected:
      - "teto so por convencao: a revisao achou descricoes de 388 a 525 caracteres"
    rollback: "git revert do commit das descricoes."
  - id: D4
    choice: "O SDD_SKILLS/ship.md fica intocado; o desfecho prematuro e registrado por acrescimo nos desvios desta feature, e um AC de kind command (git diff --exit-code) prova que o arquivo nao mudou."
    rejected:
      - "editar o hypothesis_outcome de SDD_SKILLS: reescreveria a hipotese contra a regra 21 e deixaria nada stale, escondendo a mudanca"
    rollback: "Remover o desvio e o AC8 do define desta feature."
covers:
  - {part: "teste de comandos com flags", acceptance: [AC1]}
  - {part: "descricoes", acceptance: [AC2]}
  - {part: "README com os blocos comuns", acceptance: [AC3]}
  - {part: "texto de build e ship", acceptance: [AC4]}
  - {part: "texto de define, explore, plan e ship", acceptance: [AC5, AC8]}
  - {part: "templates", acceptance: [AC6]}
  - {part: "espelhos", acceptance: [AC7]}
---

# SDD_SKILLS_REVISAO — desenho

## Conhecimento consultado

Nada de Glue ou Spark. Lido no código: `sparkforge/adapters/cli.py`
(`build_parser`, subparsers `sdd`, `funcval compare --out`,
`benchmark --out`, `change propose --sandbox --repo --funcval --benchmark`),
`tests/test_skill_content.py` (description começa com "Use quando", seções
obrigatórias, `REF_PATTERN` só para `templates/`, `checklists/`, `knowledge/`,
`examples/`) e `tests/test_sdd_skills.py`.

## Partes

| parte | arquivos | critério |
|---|---|---|
| teste de comandos | `tests/test_sdd_skills.py` | AC1 |
| descrições | as seis skills | AC2 |
| README | `docs/sdd/README.md` e as seis skills | AC3 |
| build e ship | `sdd-build`, `sdd-ship` | AC4 |
| define, explore, plan, ship | quatro skills | AC5, AC8 |
| templates | `docs/sdd/templates/*.md` | AC6 |
