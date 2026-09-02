# A fronteira entre o runtime e a avaliação

`prompt_evo_harness.md` §43 chama esta separação de **crítica** e manda não
misturar os dois conceitos. Neste repositório os dois lados já eram
fisicamente separados antes de existir este documento — o que faltava era
nomear a fronteira e defendê-la. Este documento nomeia; `tests/test_harness_boundary.py`
defende.

## Quem é quem

| | Runtime | Avaliação |
|---|---|---|
| O que faz | executa tasks | **mede** o runtime |
| Onde mora | `sparkforge/` menos `sparkforge/evals/` | `sparkforge/evals/`, `evals/`, `tests/test_fixtures_golden_*.py`, `scripts/check_evals.py` |
| Superfície | CLI `sparkforge analyze/judge/case/next-step/resume/migrate`, as tools MCP, `rules/catalog/` | `evals/fase0.xml`, `evals/holdout/`, os 34 corpora de `fixtures/` |

## O invariante, e a direção dele

**O runtime nunca importa `sparkforge.evals`. A avaliação importa o runtime.**

A direção não é simetria estética. Se o runtime dependesse do medidor, o sintoma
não apareceria como erro: apareceria muito depois, como um golden que passa
porque o runtime aprendeu a forma do grader. Um teste que mede código que
depende do teste não mede nada.

`tests/test_harness_boundary.py` verifica os dois lados — que ninguém cruzou, e
que a avaliação de fato mede alguma coisa. O segundo é o par positivo: sem ele,
o primeiro passaria também num repositório em que os dois lados simplesmente não
se falam, e não é isso que a §43 descreve.

## O que este documento NÃO afirma

Não afirma que a avaliação cobre o runtime inteiro. `docs/harness/BASELINE.md`
registra o que ainda não é medido — latência por operação, taxa de resolução
determinística sobre um corpus de tarefas reais, comportamento de CLI ponta a
ponta. A fronteira estar declarada não torna a cobertura completa; torna a
cobertura **interpretável**.

**Não afirma que todo grader mora do lado da avaliação.** Há uma exceção
conhecida, e ela é nomeada aqui em vez de ficar implícita:
`sparkforge/tools/evaluation.py` é lógica de grader — `evaluate_golden_case`
devolve `passed`, `missing`, `unexpected` e `match_rate` sobre ids de caso
golden — e está exportada na API pública do runtime (`sparkforge/tools/__init__.py`).
Ela fica do lado *runtime* da linha que o teste desenha. Isso significa que
"o runtime nunca importa `sparkforge.evals`" continua verdadeiro em parte
porque esse grader não está sob `sparkforge/evals/` — exatamente o tipo de
separação por acidente contra o qual este documento existe. Mover o módulo é
decisão de outra fase; enquanto não for tomada, a exceção fica declarada, não
escondida.

**Não afirma que o teste enxerga import dinâmico.**
`tests/test_harness_boundary.py` lê a AST, então resolve `import`,
`from x import y` e as formas relativas (`from ..evals.runner import X`,
`from . import evals`). Um `importlib.import_module("sparkforge.evals")` passa
por ele sem ser visto. Nenhum módulo de runtime faz isso hoje, e a resposta
certa não é um analisador mais esperto — que perseguiria strings construídas em
tempo de execução e nunca terminaria. A resposta é declarar o limite: a
garantia vale para import estático, que é como o cruzamento distraído nasce.

## Uma recusa registrada aqui, porque é do mesmo tipo

O §50 do prompt pede `readiness_score` no `MigrationAssessment`. Este
repositório não o implementa, e a razão é medível: `LakeFormationDoctor`
(`sparkforge/lakeformation/doctor.py`) já tem um `health_score` calculado como
`100 - fails*35 - warns*15`, e esse número não significa nada — 65 não é
"melhor" que 50 em unidade nenhuma, e os pesos não vieram de fonte.

Os gates nomeados de `MigrationAssessment` fazem o trabalho que o score faria, e
dizem **qual** eixo: `compatibilidade`, `lakeformation`, `consumidor`,
`iam_kms`, `rede`, `cross_account`, `dados`, `performance`, `custo`, `canary`.
Um score os colapsaria num inteiro, e a informação que o operador usa — *qual*
eixo está fechado e *qual* evidência o destrava — desapareceria no colapso.

Se um dia houver fonte que declare pesos, a recusa se reabre. O gatilho é a
fonte, não o pedido.
