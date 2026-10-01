---
sdd: 1
feature: DATABRICKS_PHOTON_PLAN
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/DATABRICKS_PHOTON_PLAN/define.md
  sha256: "4f29b538b3832afad06a3f0736b76dee710381b46206d2cbe509d642369dd75a"
files:
  - {path: tests/test_databricks_photon_plan.py, action: create, reason: "testes de AC1 a AC8, escritos antes do codigo"}
  - {path: fixtures/plan/photon_join, action: create, reason: "plano Photon de groupBy com join, derivado da observacao de 2026-09-18 (dados sinteticos spark.range)"}
  - {path: fixtures/plan/photon_udf, action: create, reason: "plano Photon com ArrowEvalPython entre operadores PhotonArrow, mesma origem"}
  - {path: tests/test_fixtures_golden_plan.py, action: modify, reason: "REQUIRED_FIXTURES com os dois casos Photon"}
  - {path: sparkforge/facts/spark_plan.py, action: modify, reason: "reconhece operadores de prefixo Photon e a secao == Photon Explanation ==, emite plan.photon; ArrowEvalPython passa a udf_type arrow; EMITTED_KINDS"}
  - {path: sparkforge/rules/engine.py, action: modify, reason: "a recusa das regras de plano dispara tambem quando plan.photon esta entre os facts, sem depender do runtime"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "_runtime_reading le plan.photon como observacao de photon on, fonte plan"}
  - {path: sparkforge/facts/runtime_detect.py, action: modify, reason: "_photon da precedencia a observacao sobre a declaracao, registra divergencia quando a declaracao discorda, e databricks.photon carrega a fonte"}
  - {path: rules/catalog/spark-plan.yaml, action: modify, reason: "SF-PLAN-002 casa udf_type pandas ou arrow, e o texto deixa de afirmar pandas_udf para o caso arrow"}
  - {path: fixtures/plan/python_udf_in_plan, action: modify, reason: "golden regenerado: o ArrowEvalPython passa a udf_type arrow e o texto de SF-PLAN-002 muda; o veredito nao"}
  - {path: knowledge/databricks/runtime-matrix.md, action: modify, reason: "secao 4: o extrator deixa de ser lacuna aberta e passa a dizer o que faz com o plano Photon; U1 e U2 desta feature nomeados"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 do documento editado"}
  - {path: docs/surface.lock.json, action: modify, reason: "bytes do knowledge editado"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo e bytes de spark_plan.py/_core.py movem alegacoes do gate de lastro"}
decisions:
  - id: D1
    choice: "Fact novo plan.photon, um por plano, com measures.photon_operators (quantos nos de prefixo Photon), measures.operators (total de nos), attrs.operators (nomes Photon distintos, ordenados) e attrs.explanation (primeira linha da secao == Photon Explanation ==, ou vazio). Subject no formato dos outros facts de plano (arquivo e linha do primeiro no Photon)."
    rejected: ["plan.unresolved com motivo photon: esconderia a informacao positiva (o plano E Photon) atras de um fact de falha, e o engine teria de ler motivo textual", "um fact por operador Photon: o engine so precisa saber se ha Photon, e N facts multiplicariam o golden sem consumidor"]
    rollback: "git revert do commit do extrator e python scripts/regen_fixtures.py"
  - id: D2
    choice: "O engine recusa regra que exige kind de plano quando plan.photon esta entre os facts presentes, alem do caminho de runtime (databricks e photon on) que ja existe; a excecao de plan.python_udf vale igual, e plan.aqe entra nela: o no AdaptiveSparkPlan continua no plano Photon observado, e SF-PLAN-004 le esse no, nao um operador Photon."
    rejected: ["_runtime_e_facts traduzir plan.photon em photon on no runtime: so os verbos de _core passariam por ele, e todo runner golden que chama judge direto ficaria de fora; misturaria declaracao com observacao no mesmo campo", "exigir plataforma databricks para a recusa por fact: Photon no plano ja e evidencia de Databricks, e exigir a flag reabre o silencio que a feature fecha"]
    rollback: "git revert do commit do engine"
  - id: D3
    choice: "A deteccao de runtime le plan.photon como observacao (fonte plan) e da precedencia a ela sobre a declaracao cli: plano Photon com --photon off vira divergencia photon: e o estado fica on; databricks.photon registra a fonte, e SF-ENV-006 deixa de disparar porque o estado nao e mais undeclared."
    rejected: ["declaracao vencer a observacao: contraria a precedencia do resto da deteccao (event_log acima de cli)", "ignorar a discordancia: o operador que declarou off nunca saberia que o plano diz outra coisa"]
    rollback: "git revert do commit da deteccao"
  - id: D4
    choice: "ArrowEvalPython passa a udf_type arrow: o plano nao distingue pandas_udf de UDF Python otimizada para Arrow. SF-PLAN-002 passa a casar pandas ou arrow, com texto que nao afirma pandas_udf quando o tipo e arrow. SF-PLAN-001 (UDF com pickle) nao muda."
    rejected: ["manter pandas: afirma o que o plano nao mostra, e a observacao de 2026-09-18 foi um @F.udf comum", "mapear arrow para python e disparar SF-PLAN-001: a UDF serializada em Arrow nao tem o custo de pickle que SF-PLAN-001 descreve"]
    rollback: "git revert do commit da regra e do extrator, e python scripts/regen_fixtures.py"
  - id: D5
    choice: "AC3 compara veredito (rule_id, severidade, subject) das fixtures de plano sem Photon, antes e depois; texto e attrs podem mudar so em python_udf_in_plan, pela D4."
    rejected: ["comparar o finding inteiro: tornaria AC3 e AC6 contraditorios, porque a D4 muda o texto de SF-PLAN-002 de proposito"]
    rollback: "sem codigo proprio: e criterio do teste de AC3"
covers:
  - {part: "extrator", acceptance: [AC1, AC3, AC6, AC7]}
  - {part: "engine", acceptance: [AC2, AC7]}
  - {part: "deteccao", acceptance: [AC4, AC5]}
  - {part: "regra", acceptance: [AC6]}
  - {part: "knowledge", acceptance: [AC8]}
---

# DATABRICKS_PHOTON_PLAN — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| extrator | `sparkforge/facts/spark_plan.py`, `fixtures/plan/photon_*`, `tests/test_fixtures_golden_plan.py` | AC1, AC3, AC6, AC7 |
| engine | `sparkforge/rules/engine.py` | AC2, AC7 |
| detecção | `sparkforge/adapters/_core.py`, `sparkforge/facts/runtime_detect.py` | AC4, AC5 |
| regra | `rules/catalog/spark-plan.yaml`, `fixtures/plan/python_udf_in_plan` | AC6 |
| knowledge | `knowledge/databricks/runtime-matrix.md` e registros | AC8 |

## Medidas que sustentam o desenho

- `spark_plan.py` casa operador por nome exato e ignora raiz fora de
  `_KNOWN_OPERATOR_ROOTS`; `emit()` despacha por conjunto. Por isso o reconhecimento
  de Photon é pelo prefixo do nome do nó, contado uma vez por nó (os blocos de
  detalhe numerados, no modo formatado; as linhas da árvore, fora dele).
- `_PYTHON_UDF_OPERATORS` mapeia `ArrowEvalPython` para `pandas`.
  `fixtures/plan/python_udf_in_plan` tem dois `ArrowEvalPython` e dois
  `BatchEvalPython`; SF-PLAN-002 lê `attrs.udf_type` com `where` de igualdade.
- A recusa por Photon mora hoje em `engine.py::_photon_recusa`, que olha só o
  runtime. O engine já calcula o conjunto de kinds presentes (`present_kinds`), e
  é ali que o fact entra (D2).
- `databricks.photon` e `_photon` vêm de DATABRICKS_SPARK; SF-ENV-006 dispara em
  `attrs.state: undeclared`.

## Conhecimento consultado

- `knowledge/databricks/runtime-matrix.md` §4: os planos observados, os nomes dos
  operadores e a seção de explicação; é a origem das duas fixtures.
- Regras que leem `plan.*`, por `load_catalog`: SF-PLAN-001 a 004, SF-PQ-002, SF-PQ-004.

## O que U1 e U2 significam para o build

O reconhecimento vale para a forma observada (prefixo `Photon`, seção de explicação
com uma linha). O teste de AC1 prova essa forma; o documento e o ship dizem que outra
versão do Databricks Runtime, ou um plano com suporte parcial, podem trazer outra.
