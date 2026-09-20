---
sdd: 1
feature: GLUE_TERRAFORM
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/GLUE_TERRAFORM/define.md
  sha256: "ede1f10b79f168c368b2c84e942926a231bbba108e0905535a588559a93d631e"
files:
  - {path: tests/test_glue_terraform.py, action: create, reason: "os tres testes de AC1, AC2 e AC3, escritos antes do codigo. O de AC1 falha na COLETA enquanto o modulo nao existe, e e esse o vermelho da refatoracao"}
  - {path: sparkforge/facts/glue_terraform.py, action: create, reason: "as duas funcoes, uma vez so, com a docstring que diz por que o modulo existe e por que ele NAO tem EMITTED_KINDS"}
  - {path: sparkforge/facts/stepfunctions.py, action: modify, reason: "a copia local sai e entra o import; os dois chamadores (build_sfn_glue_link, linhas 619 e 661) trocam um token cada"}
  - {path: sparkforge/facts/airflow_dag.py, action: modify, reason: "o mesmo, nos chamadores das linhas 1000 e 1040. A docstring que declarava a duplicacao de proposito sai junto: ela deixa de ser verdade"}
  - {path: docs/claims.lock.json, action: modify, reason: "um .py novo em sparkforge/ move as alegacoes de bytes e de contagem do corpus. As que caírem saem na lista de ids do gate, e so essas sao remediadas"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "os numeros auditados que as mesmas alegacoes publicam. Se o gate nao listar nenhuma, este arquivo nao e tocado -- e isso e desvio a relatar, nao a forcar"}
  - {path: docs/vnext/adrs/ADR-010-code-intelligence-indice-local.md, action: modify, reason: "o manifesto so previa CODEINTEL-GAP.md, mas a alegacao VNX-726 (proporcao de referencias nao resolvidas por UNKNOWN_RECEIVER) e publicada AQUI e mede o mesmo corpus de *.py. O gate a listou, e documento auditado que o gate lista entra no manifesto -- senao a remediacao toca arquivo que o design nao previu"}
decisions:
  - id: D1
    choice: "Modulo auxiliar `sparkforge/facts/glue_terraform.py`, SEM `EMITTED_KINDS`. O precedente esta na docstring de `scripts/check_status_numbers.py::_extratores`: `runtime_matrix` e `pricing` moram em `facts/` e nao sao extratores, porque nao emitem kind."
    rejected:
      - "Deixar as duas copias e travar a igualdade dos corpos num teste (abordagem B do explore): DETECTA a divergencia em vez de impedi-la, e so depois de ela existir. Os docstrings ja diferem hoje, entao o teste teria de normalizar texto de codigo, e isso envelhece mal."
      - "Mover as duas para `terraform.py` (abordagem C): poe um leitor de FACTS dentro de um extrator de ARTEFATO, e faz crescer um arquivo que a mudanca nao precisava tocar."
    rollback: "git revert do commit; as duas copias voltam e os dois extratores voltam a nao importar nada novo."
  - id: D2
    choice: "Os nomes publicos sao `glue_jobs_por_nome` e `glue_max_retries`, importados DIRETAMENTE (`from sparkforge.facts.glue_terraform import glue_jobs_por_nome, glue_max_retries`), no molde de `from sparkforge.facts.scan import iter_source_files`, que os dois extratores ja usam. Cada chamada muda um token."
    rejected:
      - "Importar o modulo e qualificar a chamada (`glue_terraform.jobs_por_nome(facts)`): mais explicito no ponto de uso, e foge do molde que os dois arquivos ja seguem para o modulo irmao `scan`."
      - "Manter os nomes com sublinhado inicial: nome privado que atravessa modulo mente sobre o proprio alcance."
    rollback: "o mesmo revert de D1."
  - id: D3
    choice: "O teste do AC3 afirma DUAS coisas: que o modulo nao tem `EMITTED_KINDS`, e que ele nao esta nas duas listas manuais -- importando as listas e conferindo a ausencia. A mensagem de falha diz por que, citando a regra do `CLAUDE.md` que ela contraria de proposito."
    rejected:
      - "Conferir so `hasattr(modulo, 'EMITTED_KINDS')`: nao pegaria quem acrescentasse o modulo as listas manuais seguindo o habito, e essa pessoa levaria um `AttributeError` sem contexto no `union`."
      - "Nao escrever o teste e confiar no `AttributeError`: o erro acontece, mas nao explica, e o proximo a tropecar gasta a mesma meia hora."
    rollback: "git revert do commit do teste."
  - id: D4
    choice: "A docstring do modulo novo guarda o que as duas copias diziam e mais o criterio: por que ele existe, que ele LE facts em vez de ler artefato, e que a ausencia de `EMITTED_KINDS` e o que o mantem fora das tres varreduras. As duas docstrings antigas que declaravam a duplicacao de proposito somem, porque deixam de ser verdade."
    rejected: ["Copiar as docstrings como estavam: a de `airflow_dag.py` diz 'duplicada de proposito NESTE incremento' e apontava para esta feature como o conserto -- mante-la seria publicar uma frase falsa."]
    rollback: "o mesmo revert de D1."
covers:
  - {part: "o modulo auxiliar", acceptance: [AC1, AC2]}
  - {part: "os dois extratores importando", acceptance: [AC1, AC4]}
  - {part: "a trava contra o habito", acceptance: [AC3]}
  - {part: "registros", acceptance: [AC5]}
---

# GLUE_TERRAFORM — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| o módulo auxiliar | `sparkforge/facts/glue_terraform.py`, `tests/test_glue_terraform.py` | AC1, AC2 |
| os dois extratores importando | `sparkforge/facts/stepfunctions.py`, `sparkforge/facts/airflow_dag.py` | AC1, AC4 |
| a trava contra o hábito | `tests/test_glue_terraform.py` | AC3 |
| registros | `docs/claims.lock.json`, `docs/harness/CODEINTEL-GAP.md` | AC5 |

## O vermelho de uma refatoração

Mover código não quebra teste nenhum — é essa a dificuldade da fase. O vermelho que o
build vai registrar é o do **AC1**, e ele é de **coleta**:
`tests/test_glue_terraform.py` importa `sparkforge.facts.glue_terraform`, que não existe,
e o pytest falha antes de rodar qualquer asserção. Isso conta como vermelho legítimo pela
regra da casa — o que falta é a unidade sob teste, não um auxiliar.

O que **não** se pode fazer é declarar o AC4 como vermelho: os goldens já estão verdes e
vão continuar. Ele é a prova de que nada mudou, e por isso o build o roda no fim, sobre a
suíte inteira e sem regenerar.

## O que o módulo não é

Ele **lê facts**, não artefato. Não tem `EXTRACTOR_ID`, não tem `EMITTED_KINDS`, não tem
`extract_*`, não emite `Fact` nenhum — devolve estruturas Python que as duas derivações
usam para montar os seus. É o mesmo lugar de `runtime_matrix` e `pricing`, que moram em
`facts/` e não são extratores.

## Conhecimento consultado

Medido nesta árvore em 2026-09-20, com `main` em `e4141869`:

- `scripts/check_status_numbers.py::_extratores` —
  `[m for m in _modulos_de_fact() if getattr(m, "EMITTED_KINDS", None)]`.
- `tests/test_harness_untrusted.py::extratores_com_snippet` —
  `if not hasattr(modulo, "EMITTED_KINDS")` na varredura por `pkgutil.iter_modules`, com o
  comentário ao lado: *"`EMITTED_KINDS` e o que distingue extrator de modulo auxiliar"*.
- `tests/test_rules_catalog_reachability.py::EMITTABLE` e
  `tests/test_fixtures_kind_coverage.py::EMITTABLE` —
  `frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))`, que é por onde o
  `AttributeError` apareceria.
- `sparkforge/facts/stepfunctions.py` e `airflow_dag.py` — os dois já trazem
  `from sparkforge.facts import scan` e `from sparkforge.facts.scan import
  iter_source_files`, que é o molde do D2.

As citações de linha no manifesto acima (619, 661, 1000, 1040) são instantâneo desta
árvore, para quem for executar o plano agora; o que identifica cada ponto de forma estável
é o nome da derivação, `build_sfn_glue_link` e `build_af_glue_link`.
