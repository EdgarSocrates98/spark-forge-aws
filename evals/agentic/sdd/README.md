# Suite agêntica `sdd`

Seis perguntas sobre specs do SDD próprio (`docs/sdd/README.md`), feitas a um
agente que recebe uma cópia de prova do repositório. Nasceu na feature
`SDD_EVAL` (`docs/sdd/SDD_EVAL/`).

## O que ela mede

Para cada pergunta, duas coisas, lado a lado e sem nota composta:

- **acerto**: a linha `ANSWER:` bate com o gabarito;
- **uso das tools exigidas**: o agente chamou `sdd_check` ou `sdd_status`
  (tool MCP ou `sparkforge sdd ...` na CLI), em vez de ler o YAML no olho.

| id | repositório | pergunta | tool exigida |
|---|---|---|---|
| `sdd-01` | `fixtures/sdd/cascata` | código da recusa | `sdd_check` |
| `sdd-02` | `fixtures/sdd/cascata` | artefato recusado | `sdd_check` |
| `sdd-03` | `fixtures/sdd/cobertura` | critério sem cobertura | `sdd_check` |
| `sdd-04` | `fixtures/sdd/tdd` | código da recusa | `sdd_check` |
| `sdd-05` | `fixtures/sdd/limpo` | fase atual da feature | `sdd_status` |
| `sdd-06` | `fixtures/sdd/operador` | código da recusa | `sdd_check` |

O gabarito não é escrito à mão:
`tests/test_sdd_eval_suite.py::test_gabarito_recomputado_pelo_gate` roda o gate
sobre cada fixture e reprova a suite se a resposta divergir.
`tests/test_fixtures_golden_sdd.py` trava que cada fixture dá uma recusa só.

## Como rodar

```bash
python scripts/run_agentic_eval.py --suite sdd --model haiku --repeat 1
python -m sparkforge.evals grade --suite sdd --run <run_id>
```

O runner copia `fixtures/` para o workspace de prova (sem `expected/`), gasta
token e grava tudo sob `~/.sparkforge/agentic-evals/`. Só o scorecard entra em
`baselines/`, no formato de `evals/agentic/fase0/baselines/`; transcript de
sessão real carrega caminho e contexto do operador e nunca entra no git.

## O que ela NÃO mede: a comparação com superpowers e AgentSpec

"O SDD próprio é melhor que o ciclo do superpowers ou do AgentSpec" **não é
medível aqui**, e a suite recusa a comparação por nome (regra 30):

- os plugins não produzem artefato que o gate leia, então um braço sem gate
  não responde às mesmas perguntas — não é o mesmo caso;
- a suite mede o uso de `sdd_check`/`sdd_status`, que só existe de um lado.

O que destravaria: um caso bem posto que os dois processos resolvem do começo
ao fim (a mesma mudança pedida, o mesmo repositório de partida), com uma medida
externa aos dois — testes de aceite escritos antes, fora de qualquer plugin —
rodando nos dois braços, com N execuções por braço. Até isso existir, nenhum
número desta suite vira afirmação de ganho sobre outro processo.

## Baseline

`baselines/2026-09-17-haiku-4-5/`: duas invocações separadas do mesmo
comando com `--repeat 1` (`r1.json` às 07:45Z, `r2.json` às 08:14Z, N=2) —
por isso o `run_id` de `r2` também termina em `r1` — com
`claude-haiku-4-5-20251001`, host `2.1.274`, superfície `full`, suite sha256
`47bdb24f…`.

| pergunta | acerto k/N | tools exigidas k/N |
|---|---|---|
| `sdd-01` | 2/2 | 2/2 |
| `sdd-02` | 2/2 | 2/2 |
| `sdd-03` | 2/2 | **1/2** |
| `sdd-04` | 2/2 | 2/2 |
| `sdd-05` | 2/2 | 2/2 |
| `sdd-06` | 2/2 | 2/2 |

Nenhuma pergunta usou a tool MCP; o gate foi alcançado pela CLI
`sparkforge sdd ...`. Em `r2`, `sdd-03` tentou `python -m sparkforge.cli sdd
check`, que não é o ponto de entrada da CLI, e respondeu certo **lendo o YAML**
com `Read` — exatamente o comportamento que a suite existe para distinguir.
O grader só reconhece a CLI chamada por `Bash` (`PowerShell` conta como
`other`). O `sparkforge` do PATH da máquina era instalação editável deste
repositório, não a cópia do workspace; o código de `sparkforge/` era o mesmo
nos dois. Duas amostras não são taxa: repetir com `--repeat 3` antes de citar
estabilidade, e comparar com `python -m sparkforge.evals compare`, que lista
transições e não conclui.
