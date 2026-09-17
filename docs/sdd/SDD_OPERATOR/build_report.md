---
sdd: 1
feature: SDD_OPERATOR
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_OPERATOR/plan.md
  sha256: "62e44085faac5da58ba34fe26aa5f0b41e6ddfbdd670c47ba2712bbd4afd1042"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_funcval_not_comparison -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_funcval_blind_spot -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd_operator.py -q (worktree em 2bed741a, nucleo antes de T1)", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_operator.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd_operator.py::test_coordenadores_apontam_o_sdd -q (worktree em fde015b6, agents antes de T4)", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_operator.py tests/test_sdd.py tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py tests/test_agent_coverage.py -q", exit: 0}
claims:
  - text: "verified_by kind funcval sem nenhum funcval.check_delta (ou com JSON que nao e lista de facts) sai refused funcval_not_comparison."
    evidence_ref: "tests/test_sdd.py::test_funcval_not_comparison"
  - text: "Cada funcval.unresolved sai unresolved funcval_blind_spot com o subject.symbol (ou o subject cru) e o attrs.reason no unlock."
    evidence_ref: "tests/test_sdd.py::test_funcval_blind_spot"
  - text: "Uma feature operator montada com case_open e change_sandbox reais passa no sdd check; sem check_delta sai funcval_not_comparison e, depois de change sandbox clean, change_missing."
    evidence_ref: "tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta"
  - text: "Os quatro coordenadores citam sdd-define e sdd-build na prosa, com sparkforge case open e sparkforge sdd check, e nenhum as lista no skills do frontmatter."
    evidence_ref: "tests/test_sdd_operator.py::test_coordenadores_apontam_o_sdd"
  - text: "Os espelhos .claude, .agents e .github dos quatro agents e das tres skills conferem com a renderizacao."
    evidence_ref: "python scripts/sync_skills.py --check"
  - text: "A superficie de skills cresceu 770 bytes (528425 para 529195)."
    evidence_ref: "docs/surface.lock.json"
  - text: "O gate de lastro fecha com zero divergencia depois de remediar VNX-640, VNX-674 e VNX-726 por id."
    evidence_ref: "docs/claims.lock.json"
change_id: null
---

# SDD_OPERATOR — relatório do build

Quatro tarefas, um commit cada: `058691c6` (T1), `fdd4f5a0` (T2), `fde015b6`
(T3), `c9489e21` (T4, com o acréscimo T5). Registros em `9f720e05`. Todo
vermelho acima foi visto na hora, com o exit que o comando devolveu.

## Sem subagente

Este build rodou num agente só, que não despacha subagente. Não houve um
implementador novo por tarefa nem a revisão em dois estágios (spec e depois
qualidade) que `sdd-build` descreve. Cada tarefa rodou os gates vizinhos de
`docs/gates-por-mudanca.md` ("Alterar agent, skill ou seus espelhos" e "a
referência gerada").

## Desvios do plano

1. **T1, teste mais forte.** Além do caso do plano, o teste grava um arquivo que
   nem é JSON e exige a mesma recusa. O leitor `_itens_de_fact` foi extraído de
   `_ids_de_fact`, como o plano pedia; a conferência mora em `_conferir_funcval`.
2. **T2, forma real do funcval.** O caso do plano (`subject: {"check": ...}`)
   ficou. Um segundo caso usa a forma que `sparkforge/facts/funcval.py` emite de
   fato: `subject {type, symbol}` e o motivo em `attrs.reason`. O `unlock` nomeia
   o `symbol` (ou o subject cru, `chave=valor`, quando não há `symbol`) e o
   `reason`. Os dois códigos entraram no §5.0 do spec do núcleo no commit de T2.
3. **T3, vermelho fora da árvore.** Com T1 e T2 feitos, o teste ponta a ponta
   passou de primeira, porque exercita comportamento que essas tarefas já
   construíram. O vermelho registrado é o mesmo arquivo de teste rodado num
   `git worktree` em `2bed741a` (o núcleo antes de T1): falha em
   `funcval_not_comparison`, pelo motivo certo. A árvore principal não foi
   tocada. O arquivo de comparação é sintético, na forma de `_check_delta`,
   como o design pedia; `sparkforge funcval compare` não roda no teste. O
   negativo "sem sandbox" usa a própria tool (`change sandbox` com `clean`) em
   vez de um id inventado.
4. **T4, D2 revista: prosa, e não o `skills:`.** O design mandava listar
   `sdd-define` e `sdd-build` no `skills:` dos quatro coordenadores. Ao rodar
   os gates vizinhos, `tests/test_sync_render.py::TestRelacaoDerivada` ficou
   vermelho, e a leitura mostrou a causa: as `sdd-*` estão em
   `scripts/sync_skills.py::NON_DISPATCHABLE_SKILLS` porque perguntam ao
   operador e despacham subagentes, e o comentário do teste diz que declará-las
   no `skills:` de um coordenador as tornaria despacháveis. O coordenador roda
   como subagente e não faz nenhuma das duas coisas. O precedente é
   `diagnose-lakeformation-access`, citada só na prosa. A escolha foi seguir
   esse precedente: frontmatter intacto e um parágrafo "Mudança no job pede
   spec" em cada coordenador. O teste de T4 inverteu a asserção (nada de `sdd-`
   no frontmatter, as duas skills no corpo, mais `sparkforge case open`). D2 e
   a seção T4 do plano foram reescritas, e o plano recarimbado. A alternativa
   que ficou de fora foi acrescentar as duas skills a `RELACAO_MEDIDA` e
   contrariar o registro de não-despacho.
5. **T4, vermelho do teste revisto.** O primeiro vermelho (versão do plano) saiu
   com exit 1 na árvore. O teste revisto foi conferido contra os agents de
   `fde015b6` num `git worktree`: exit 1 em `spark-performance-architect`.
6. **T5, acréscimo pedido no build (dentro do commit de T4).** As seções
   "Perfil operator" de `sdd-define`, `sdd-plan` e `sdd-build` deixaram de
   adiar para o "subprojeto C" e passaram a dar o caminho concreto:
   - o `case_id` vem de `sparkforge case open` e fica em `.sparkforge/case.yaml`;
   - o aceite é `funcval` ou `fact`;
   - o `test` de tarefa do operador é a checagem que falha antes da mudança;
   - `red` e `green` no sandbox;
   - o PR sai de `change propose`.
   A linha de `funcval` da tabela do define e a lista de recusas passaram a
   citar os códigos novos. Os três arquivos entraram no manifesto do design e
   em `files` da T4, com recarimbo. Em `sdd-plan`, a primeira redação citava
   `sparkforge judge` e acendeu `tests/test_skill_content.py` (skill que chama
   `judge` precisa explicar o runtime). O texto passou a dizer "os achados
   `SF-FVAL`", porque a skill de plano não roda `judge`.
7. **Registros fora do manifesto:** `docs/guia/referencia/` (sete páginas),
   `docs/surface.lock.json`, `docs/claims.lock.json`,
   `docs/harness/CODEINTEL-GAP.md`,
   `docs/vnext/adrs/ADR-010-code-intelligence-indice-local.md` e
   `docs/superpowers/STATUS.md` (linha de Skills, contagem inalterada em 66).

## Gates rodados no fechamento

- `python scripts/sync_skills.py --check`: OK.
- `python scripts/gen_reference_docs.py`: 268 páginas, 7 regravadas. Antes
  disso, `tests/test_reference_docs.py::test_referencia_em_dia` saiu com
  exit 1.
- `python scripts/check_surface_lock.py --update`: skills de 528425 para
  529195 bytes. Sem `--update`, o mesmo comando tinha mostrado 2 divergências.
- `python scripts/check_vnext_claims.py`: 3 divergências e depois 0.
  - VNX-640 (corpus `*.py`): de 737 para 738.
  - VNX-674 (bytes das linhas com `source`): de 228253 para 228364. A diferença
    é uma linha de `tests/test_sdd_operator.py`, com 111 bytes.
  - VNX-726 (receptor desconhecido): de 89,8 para 89,7.
  - Cada valor foi relido da própria prova.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.
- A bateria pedida de testes está no `ship.md`, que registra a rodada final.
