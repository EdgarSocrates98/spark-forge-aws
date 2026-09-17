---
sdd: 1
feature: SDD_EVAL
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_EVAL/plan.md
  sha256: "7b40b636d79591cda3d1afbf154bc7688eb7ab0ac7c43be38924f87c4c16100a"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_eval_suite.py::test_fixtures_sem_conversao_de_quebra -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_eval_suite.py tests/test_fixtures_golden_sdd.py tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py tests/test_arvore_versionada.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd_eval_suite.py::test_gabarito_recomputado_pelo_gate -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_eval_suite.py tests/test_evals_suite.py tests/test_evals_invariants.py tests/test_evals.py tests/test_arvore_versionada.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd_eval_suite.py::test_runner_conhece_a_suite_sdd -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_eval_suite.py tests/test_evals_invariants.py tests/test_evals_suite.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd_eval_suite.py::test_suite_carrega_e_exige_as_tools -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_eval_suite.py -q", exit: 0}
claims:
  - text: "fixtures/sdd/** esta fora da conversao de quebra de linha, e os cinco casos tem docs/sdd."
    evidence_ref: "tests/test_sdd_eval_suite.py::test_fixtures_sem_conversao_de_quebra"
  - text: "Cada fixture da exatamente a recusa para a qual foi montada (limpo: nenhuma, e fase ship), rodando o gate do repositorio."
    evidence_ref: "tests/test_fixtures_golden_sdd.py::test_cada_caso_da_so_a_recusa_que_foi_montada"
  - text: "As seis respostas da suite sdd saem do gate rodado sobre a fixture citada na pergunta."
    evidence_ref: "tests/test_sdd_eval_suite.py::test_gabarito_recomputado_pelo_gate"
  - text: "A suite carrega por load_suite, tem seis perguntas e exige sdd_check ou sdd_status em todas; o baseline gravado foi pontuado contra o sha256 desta suite."
    evidence_ref: "tests/test_sdd_eval_suite.py::test_suite_carrega_e_exige_as_tools"
  - text: "O runner escolhe fase0 ou sdd por comparacao entre constantes, recusa caminho no --suite, aceita --runs como --repeat e, no braco suite, deixa visiveis so sdd_check e sdd_status."
    evidence_ref: "tests/test_sdd_eval_suite.py::test_runner_conhece_a_suite_sdd"
  - text: "Baseline Haiku (N=2): acerto 2/2 nas seis perguntas; tools exigidas 2/2 em cinco e 1/2 em sdd-03; nenhuma chamada pelo MCP."
    evidence_ref: "evals/agentic/sdd/baselines/2026-09-17-haiku-4-5/r1.json"
  - text: "O corpus de *.py foi de 739 para 746, os modulos golden de 54 para 55, os dominios de fixture de 55 para 56 e as fixtures golden de 505 para 510, relidos pelas proprias provas."
    evidence_ref: "docs/claims.lock.json"
change_id: null
---

# SDD_EVAL — relatório do build

Quatro tarefas, um commit cada: `9e5b47a2` (T1), `067183e1` (T2), `fedf400e`
(T3), `c8dee457` (T4); mais `bb5df09f` com alegações e STATUS. Todo vermelho foi visto na
hora: T1 a asserção sobre o `.gitattributes`; T2 `SuiteError: suite.yaml
ausente` (a suite é a unidade sob teste); T3 `AttributeError` de
`SDD_SUITE_DIR` (a constante sob teste); T4 "nenhum baseline gravado".

## Sem subagente

Este build rodou num agente só, que não despacha subagente. Não houve
implementador novo por tarefa, revisão em dois estágios nem revisão final por
revisor novo. A releitura do diff inteiro (de `5327c7b7` até o último commit)
foi feita pelo mesmo agente: os cinco critérios têm entrega, e nenhum arquivo
de fixture tem CR.

## Baseline (AC5)

`python scripts/run_agentic_eval.py --suite sdd --model haiku --runs 1`, exit
0, em 2026-09-17T07:45:19Z, `claude-haiku-4-5-20251001`, host `2.1.274`,
superfície `full`. Pontuado de novo com
`python -m sparkforge.evals grade --suite sdd --run sdd-2026-09-17T07-45-19Z-r1`
(exit 0, scorecard idêntico). Só o scorecard foi copiado para
`evals/agentic/sdd/baselines/2026-09-17-haiku-4-5/r1.json`, com LF.

| pergunta | acerto | tools | chamadas de tool | erros de tool |
|---|---|---|---|---|
| sdd-01 | correct | ok | 4 | 4 |
| sdd-02 | correct | ok | 8 | 6 |
| sdd-03 | correct | ok | 7 | 2 |
| sdd-04 | correct | ok | 5 | 1 |
| sdd-05 | correct | ok | 4 | 1 |
| sdd-06 | correct | ok | 6 | 4 |

k/N: acerto 6/6, tools 6/6, N=1. Nenhuma pergunta chamou a tool MCP; todas
chegaram ao gate pela CLI `sparkforge sdd ...`. Nos transcripts de `sdd-01`,
`sdd-02` e `sdd-06`, lidos um a um, os erros de tool são tentativas de caminho
e de shell (PowerShell e Bash com caminho Windows) antes do comando que
funcionou; os outros três não foram lidos. O `sparkforge` do PATH era a
instalação editável deste repositório, não a cópia do workspace.

**Segunda amostra (`r2`, commit `6f569393`).** O ship roda de novo o comando
de AC5 (exit 0, 08:14:52Z), e o scorecard entrou como `r2.json` do mesmo
baseline. Acerto 6/6; tools 5/6: em `sdd-03` o agente tentou
`python -m sparkforge.cli sdd check`, que não é o ponto de entrada da CLI, e
respondeu certo lendo o YAML com `Read`. Com as duas amostras, `compare` dá
acerto 2/2 em todas as perguntas e tools 2/2 em cinco, 1/2 em `sdd-03`.
Nenhuma afirmação de ganho sobre outro processo.

## Desvios do plano

1. **Golden module novo, fora do manifesto:** `tests/test_fixtures_golden_sdd.py`
   com `FIXTURES = ROOT / "fixtures" / "sdd"`, exigido por
   `tests/test_fixtures_kind_coverage.py::test_every_fixture_domain_has_a_golden_module`
   para o gate de wheel rodar o domínio. A tabela dele é a intenção de cada
   caso, escrita antes de gerar.
2. **Operador em `docs/sdd/`.** O caso `operador` usa `profile: operator` sob
   `docs/sdd/`, como `feature_limpa` em `tests/test_sdd.py`, e não
   `.sparkforge/sdd/`: o teste de T1 pede `docs/sdd` nos cinco casos, e a
   recusa `change_missing` não depende da raiz. A pergunta `sdd-06` diz "raiz
   padrão".
3. **Gerador fora do repositório.** As fixtures saíram de um script de
   scratchpad com o `stamp` real, gravando bytes; ele não entrou em
   `scripts/regen_fixtures.py`. Regenerar exige reescrever o gerador.
4. **`--runs`.** O define escreve `--runs 1`; o runner só tinha `--repeat`.
   `--runs` entrou como sinônimo, para o comando de AC5 rodar como está escrito.
5. **T4, teste ampliado.** O teste do plano passaria de primeira (a suite nasceu
   em T2). Acrescentei a conferência do baseline gravado — sha256 da suite e os
   seis ids —, que é a entrega de T4 e deu o vermelho.
6. **T4, arquivos fora da lista da tarefa:** `tests/test_sdd_eval_suite.py` e
   `evals/agentic/sdd/README.md` (resultado do baseline).
7. **Registros fora do manifesto:** `docs/claims.lock.json`,
   `docs/harness/CODEINTEL-GAP.md` (VNX-640, 739 → 746),
   `docs/harness/CURRENT-HARNESS-GAP.md` (VNX-357 e VNX-358, 54 → 55),
   `docs/harness/RUNTIME-VS-EVALUATION.md` (VNX-469, 55 → 56) e
   `docs/superpowers/STATUS.md` (Fixtures golden 505 → 510, 56 domínios).
8. **Arquivo solto.** Um arquivo vazio `modulo` apareceu na raiz durante T3 e
   T4; foi apagado, não entrou em commit e não reapareceu nos testes.

## Decisões tomadas sozinho

- Fixtures em `fixtures/sdd/` (D1), e não em `evals/agentic/sdd/cases/`: o
  runner já copia `fixtures/` para o workspace, e `evals/` fica fora dele.
- `_suite_dir` compara o nome com cada constante em vez de indexar um dict: o
  valor do argv não participa de nenhuma expressão que monte caminho.

## Gates rodados no fechamento

- `python scripts/sync_skills.py --check`: OK.
- `python scripts/gen_reference_docs.py`: 0 páginas regravadas.
- `python scripts/check_surface_lock.py --update`: sem mudança.
- `python scripts/check_vnext_claims.py`: 4 divergências (VNX-640, VNX-357,
  VNX-358, VNX-469), remediadas por id; depois 0.
- `python scripts/check_status_numbers.py --strict`: 1 divergência (Fixtures
  golden), remediada; depois 0.
- `python scripts/check_evals.py`: 10 respostas reproduzem.
- `python scripts/verify_wheel.py`: **não concluiu.** Rodei com `timeout 900`;
  os dois builds e a instalação passaram, os módulos golden chegaram a 37% sem
  nenhuma falha no log, e o limite de 15 minutos o matou (exit 124). Não é
  prova de que `tests/test_fixtures_golden_sdd.py` passa contra o pacote
  instalado; o CI é quem roda o gate inteiro.
- Bateria de 19 arquivos: 1453 verdes.
