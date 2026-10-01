---
sdd: 1
feature: SDD_EVAL
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_EVAL/define.md
  sha256: "2eae0fbbaa09f42f955489cb9e5764258fd9527227d85c5726935384e5bf52d9"
files:
  - {path: fixtures/sdd, action: create, reason: "cinco repositorios sinteticos: limpo, cascata, cobertura, tdd, operador"}
  - {path: .gitattributes, action: modify, reason: "fixtures/sdd/** -text"}
  - {path: evals/agentic/sdd/suite.yaml, action: create, reason: "seis perguntas inline com answer e required_tools"}
  - {path: evals/agentic/sdd/README.md, action: create, reason: "o que a suite mede e a comparacao recusada"}
  - {path: scripts/run_agentic_eval.py, action: modify, reason: "suite sdd como constante"}
  - {path: tests/test_sdd_eval_suite.py, action: create, reason: "AC1 a AC4"}
  - {path: evals/agentic/sdd/baselines, action: create, reason: "baseline Haiku (AC5)"}
decisions:
  - id: D1
    choice: "Fixtures estaticas em fixtures/sdd/ com .gitattributes -text, porque o agente precisa de arquivos no workspace copiado pelo runner."
    rejected: ["gerar a fixture em tempo de execucao, que o runner nao faz"]
    rollback: "git rm -r fixtures/sdd e a linha do .gitattributes."
  - id: D2
    choice: "Gabarito recomputado por teste, no molde de scripts/check_evals.py."
    rejected: ["resposta escrita a mao sem conferencia"]
    rollback: "Remover o teste; a suite continua carregavel."
  - id: D3
    choice: "A suite entra no runner como constante nomeada, seguindo a regra do proprio script de nao escolher diretorio pelo argv livre."
    rejected: ["--suite-dir com caminho"]
    rollback: "Remover a constante e voltar ao runner so com fase0."
covers:
  - {part: "gabarito", acceptance: [AC1, AC2]}
  - {part: "fixtures", acceptance: [AC3]}
  - {part: "runner e baseline", acceptance: [AC4, AC5]}
---

# SDD_EVAL — desenho

## Perguntas

| id | fixture | pergunta (resumo) | resposta | tools |
|---|---|---|---|---|
| sdd-01 | cascata | codigo de recusa | `upstream_stale` | sdd_check |
| sdd-02 | cascata | arquivo recusado | caminho relativo do artefato | sdd_check |
| sdd-03 | cobertura | acceptance id sem cobertura | `AC2` | sdd_check |
| sdd-04 | tdd | codigo de recusa | `red_not_declared` | sdd_check |
| sdd-05 | limpo | fase atual da feature | `ship` | sdd_status |
| sdd-06 | operador | codigo de recusa | `change_missing` | sdd_check |

Cada pergunta diz o formato do valor e manda usar a fixture como `--repo`.

## Gabarito recomputado

O teste carrega a suite, e para cada pergunta roda `check`/`status` na fixture
e extrai o valor pela mesma regra declarada no campo `derive` do teste (nao no
YAML: o leitor de suite recusa campo desconhecido).
