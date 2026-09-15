# Instruções arquivadas

Texto que morava em `CLAUDE.md` e em `AGENTS.md` até 2026-09-15 e saiu de lá porque
os dois arquivos são carregados em toda sessão, e histórico é custo fixo sem retorno.
Nada aqui é regra vigente: as regras vigentes continuam nos dois arquivos, com a
mesma numeração, e os números correntes estão na tabela *Números correntes* de
`docs/superpowers/STATUS.md`.

**Os números abaixo valem na data em que foram escritos**, e vários já mudaram. Este
documento não passa pelo gate de lastro de propósito: ele registra o que foi afirmado,
não o que é verdade hoje. `tests/test_bootstrap_budget.py` trava o teto dos dois
arquivos de instrução.

---

## Do `CLAUDE.md`

### Os números do índice de Code Intelligence e o gate que não os conferia

**O denominador decide o sinal, e ele precisa sair junto.** Medido na secao 10 de
`docs/harness/CODEINTEL-GAP.md`, e relido dela em 2026-09-09: contra ler os
arquivos o indice economiza **706,9x**; contra a saida de um `grep` pelo nome,
**10,0x**; contra um `grep` cirurgico pela definicao ele **custa 5,3x mais**. As
tres medidas sao verdadeiras e citar so a primeira escolheria o resultado.

**Os dois primeiros numeros MUDAM a cada arquivo `.py` novo**, porque o
denominador deles e o tamanho da arvore. Eram 675,6x e 9,6x em 2026-09-08, e a
entrega do footer do Parquet os moveu -- nao porque o indice melhorou, e sim
porque ha mais codigo para nao ler. Citar qualquer um dos dois sem a data e
citar uma medida que ja mudou.

Este paragrafo publicava **661,3x** e **9,4x**. Nenhum dos dois reproduz a
partir dos numeros que a secao 10 sustenta hoje — 1 493 002 sobre 2210 da 675,6,
e 21 273 sobre 2210 da 9,6 —, e o denominador que os produziria o documento
auditado nao publica mais. Nao adivinho qual era: o que da para afirmar e que os
dois estavam defasados, e a defasagem
sobreviveu porque **`CLAUDE.md` esta fora de `audited_roots()` do
`scripts/check_vnext_claims.py`**, que audita `docs/vnext/` e `docs/harness/` e
mais nada. O arquivo de instrucao que governa o projeto publica numero que gate
nenhum confere.

Medido em 2026-09-02, sobre o gold set de recuperacao: `full` 46 488 bytes
contra `summary` 45 878 — **1,3%**. Num corpus pequeno o envelope fixo do pacote
(840 bytes) domina. Recall conceitual medido: **0 de 27**.

### A receita de lotes que deixava 90 testes de fora

Enquanto a receita era prosa, `tests/test_fixtures_golden.py` — **90 testes** —
não caía em lote nenhum: o lote `f` se escrevia `ls tests/test_f*.py | grep -v
golden`, e o `grep` o excluía junto com os `test_fixtures_golden_*`, que ele não
é (falta o underscore). A suíte coletava 8662 e a receita somava 8572. Quem
seguisse o procedimento publicado fechava verde com 90 testes sem execução, e
nada acusava. Hoje `test_suite_batches.py` trava as três invariantes.

### O executor agêntico, em números de 2026-09-08 a 2026-09-11

`sparkforge/agentic/executor/` acrescenta **10 módulos** (remedido em
2026-09-11: 4185 linhas com o `__init__.py`, 168 889 bytes. Em 2026-09-08 eram
8, com 2727 linhas e 176 testes, e o executor de debate acrescentou
`debate_run` e `debate_evidence`, com 112 testes: 24 de unidade, 41 de
reextração e 47 golden). Ele é o **produtor** que faltava — a lacuna que a
auditoria de 2026-09-03 declarava governar todas as outras. Depois disso entrou
`gate.py` (§11, 2026-09-14).

### A regra 29 no texto integral de 2026-09-14

Medido em 2026-09-08 sobre `fixtures/graph/import_sem_jar_no_iac` unida a
`fixtures/infra_code/fgac_com_jar_extra` (3 findings, 60 facts): antes,
zero em tudo; depois, **3 claims, 11 evidências, 1 contradição e 1
contradição não resolvida**. Desde 2026-09-11 o plano de debate tem executor
(`sparkforge debate start|next|submit`). O Debate ROI Gate entrou em 2026-09-14.
O placar do debate é `python -m sparkforge.evals debate --run <nome>`. **Alcance
medido: um par.** Das 156 regras com `action`, `direct_conflicts` produz só
`SF-GRAPH-005` × `SF-LF-001`, e só na união de dois jobs. Status por componente em
`docs/agentic-evolution-report.md`.

**A metade da VERIFICAÇÃO do debate passou a existir em 2026-09-10, e a da
GERAÇÃO não.** `sparkforge debate referee` arbitra o protocolo e recusa quatro coisas.
`upheld` é binário, porque a garantia pedida é uma recusa e recusa graduada não
recusa. O sétimo estágio do protocolo (`VERIFICATION`) sai `modeled: false`:
consenso é acordo, não verificação, e `Debate.verdict` é texto livre que nada liga
a uma execução posterior.

### A justificativa da regra 30, antes de encolher

A justificativa desta regra **encolheu em 2026-09-08 e de novo em 2026-09-11, e a
conclusão não**. Em 2026-09-08 o executor determinístico passou a rodar. Em
2026-09-11 o debate também passou a rodar, e mesmo assim nenhuma comparação foi
feita, por dois motivos. O único par que o catálogo produz só existe na união de
dois jobs, e um smoke real argumentou que o conflito pode não existir em nenhum
deles sozinho. Por isso o baseline de modelo foi deliberadamente não rodado:
mediria um tópico mal posto (ver `evals/README.md`).

### O bloco RTK

O `CLAUDE.md` carregava a referência completa do RTK (Rust Token Killer), uma
ferramenta pessoal de proxy de CLI do mantenedor. Ela não é do projeto, e o
`~/.claude/CLAUDE.md` do mantenedor já a carrega. Saiu inteira em 2026-09-15.

---

## Do `AGENTS.md`

### Números que estavam desatualizados na data da poda

Em 2026-09-15 o `AGENTS.md` ainda publicava: 36 extractors e 210 fact kinds, 190
regras (155 executáveis) e 83 tools; "69 tool schemas = 376,854 bytes, 57 skills,
50 knowledge documents"; "112 executable rules" com "89 propõem mudança e 23 são
investigate"; o executor com "7 módulos, 2573 linhas, 163 testes"; e, na seção de
status, "não há executor que rode as rodadas [de debate]" e "MISSING:
checkpoint/resume" — o executor de debate existe desde 2026-09-11 e o journal
desde 2026-09-15. Os números correntes estão em `docs/superpowers/STATUS.md`.

### A fronteira SF-PY, SF-DQ e SF-GRAPH, medida

`analyze graph` é a **terceira** leitura do mesmo `.py`, então a fronteira entre
`SF-PY`, `SF-DQ` e `SF-GRAPH` é de três lados e nenhum corte de artefato separa
nenhuma delas: `tests/test_rules_graph_boundary.py` roda os três extratores sobre os
três corpora. Medido lá: `SF-PY` dispara **23 vezes em 20 das 25 fixtures de grafo**,
e isso é trabalho legítimo, não invasão — todas citam `pyspark.cache` ou
`pyspark.conf_set` e nunca um fact `graph.*`. A mesma medida decidiu que `SF-GRAPH`
fica com `pyspark-code-reviewer`: ele dispara em 6 das 25, e as 6 são subconjunto das
20. O precedente de `SF-DQ` mede o inverso (`SF-DQ` em 8 de 13 fixtures de dq contra
`SF-PY` em 2), e por isso aquele se separou.

### O custo medido do ledger

Escrever por chamada custa **5,5 a 7,0 ms** (média de 30, plana no tamanho do
payload — é o fsync do commit do SQLite), enquanto um `record()` em buffer custa
**0,0067 ms num payload de 63 bytes e 0,0204 ms num de 1 004** (mediana de cinco
lotes de 300). O ganho vai de **1 045× na ponta pequena a 273× na grande**. O preço é
perder spans num `SIGKILL`. Num fixture, `detail_level_effect` mediu 1 599 bytes em
`full` contra 849 em `summary`.

### O que o gate estrito prova e o que não prova

Medido, para ninguém ler demais um gate verde: duas linhas de JSON escritas à mão com
`provenance` vazia levam um case estrito de `intake` a `report`. Só um gate **com**
produtor pode ser fail-closed: `baseline_captured` (`bench.run_delta`),
`flows_mapped` (`callgraph.reachable_spark_work`) e `functional_validation_defined`
(`funcval.plan`). `dominant_bottleneck_identified` fica advisory, porque endurecer um
gate sem produtor é o impasse que o design da Fase 0 recusou.
