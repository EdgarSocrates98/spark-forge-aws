---
sdd: 1
feature: SDD_ENDURECIMENTO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_ENDURECIMENTO/plan.md
  sha256: "2318147a0d600a626aeb2be6f810bda81f2723aa7ef3fadd03164cc258338946"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_eval_suite.py::test_notas_de_hash_e_de_baseline -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_eval_suite.py tests/test_fixtures_golden_sdd.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_moved_de_outra_mudanca -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_relatorio_por_symlink_nao_escapa -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_ship_done_sem_evidencia_recusa -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py tests/test_sdd_eval_suite.py tests/test_fixtures_golden_sdd.py tests/test_sdd_skills.py tests/test_sdd_migration.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_contrato_lista_todo_codigo -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_sdd_operator.py::test_skills_ensinam_a_evidencia_do_ship -q", exit: 1}
    green: {command: "python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_sdd_skills.py tests/test_sdd_operator.py tests/test_reference_docs.py tests/test_skill_content.py -q", exit: 0}
claims:
  - text: "Change_id fabricado com moved, ship done, sem relatorio e sem evidence sai ship_evidence_missing; antes da mudanca saia sem recusa."
    evidence_ref: "tests/test_sdd.py::test_ship_done_sem_evidencia_recusa"
  - text: "Com evidence gravada e o relatorio apagado, a feature e aceita como historia; entrada que nao nomeia um id citado, inclusive o prefixo de um proof finding, sai ship_evidence_missing."
    evidence_ref: "tests/test_sdd.py::test_ship_done_com_evidencia_e_sem_relatorio_e_historia"
  - text: "Com o ship done e o relatorio presente, moved e finding continuam conferidos e o relatorio que contradiz sai moved_not_observed."
    evidence_ref: "tests/test_sdd.py::test_ship_done_com_relatorio_que_contradiz"
  - text: "Relatorio presente com text_sha256 diferente do gravado sai ship_evidence_mismatch, no sandbox e na copia da proposal."
    evidence_ref: "tests/test_sdd.py::test_ship_done_com_sha_divergente"
  - text: "Build operator sem change_id com ship done sai ship_evidence_missing, em vez de deixar proof finding virar historia."
    evidence_ref: "tests/test_sdd.py::test_ship_done_sem_change_id_no_build_recusa"
  - text: "moved.change_id diferente do change_id do build sai moved_change_mismatch."
    evidence_ref: "tests/test_sdd.py::test_moved_de_outra_mudanca"
  - text: "report.json que e symlink para fora da pasta da mudanca nao e lido."
    evidence_ref: "tests/test_sdd.py::test_relatorio_por_symlink_nao_escapa"
  - text: "No fluxo operator real, report.json do sandbox e evidence/sandbox_report.json da proposal tem o mesmo text_sha256, e o ship done sem evidence sai ship_evidence_missing."
    evidence_ref: "tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta"
  - text: "Os 32 codigos literais de checks.py e stamp.py sao exatamente os das tabelas de docs/sdd/CONTRATO.md."
    evidence_ref: "tests/test_sdd.py::test_contrato_lista_todo_codigo"
  - text: "sdd-ship, sdd-build, docs/sdd/README.md e o topo do spec congelado ensinam evidence, os codigos novos e o contrato vivo."
    evidence_ref: "tests/test_sdd_operator.py::test_skills_ensinam_a_evidencia_do_ship"
  - text: "Skills no surface lock: 532007 para 532882 bytes (sdd-ship 8162 para 8886, sdd-build 10635 para 10786)."
    evidence_ref: "docs/surface.lock.json"
change_id: null
---

# SDD_ENDURECIMENTO — relatório do build

Seis tarefas, um commit cada: `e1330dbb` (T1), `b67642f2` (T2), `4e75dd98`
(T3), `10f60159` (T4), `a889aa87` (T5), `f1fce093` (T6); mais `8218bc3e`, o
achado da revisão final. O plano está em `57c3012c`.

Todo vermelho foi visto na hora, pelo motivo certo:

- T1: `AssertionError` sobre `text_sha256` no bloco do `.gitattributes`.
- T2: `assert [] == [('moved_change_mismatch', ...)]` — o gate aceitava.
- T3: `assert ([], []) == (['moved_not_observed'], [])` — o symlink era lido.
- T4: `assert [] == [('ship_evidence_missing', 'evidence')]` — o furo em si.
- T5: `FileNotFoundError` de `docs/sdd/CONTRATO.md`, o documento sob teste.
- T6: `AssertionError: evidence` na seção operator de `sdd-ship`.
- Revisão final: `assert [] == [('ship_evidence_missing', 'evidence')]`.

## Sem subagente

Este build rodou num agente só, que não despacha subagente. Não houve
implementador novo por tarefa, revisão em dois estágios nem revisor novo na
revisão final. A leitura do operador em cada fase foi substituída pelo pedido
do chamador, que fixou o escopo, os códigos e os casos de teste. A releitura
do diff inteiro (`57c3012c..f1fce093`) foi feita pelo mesmo agente contra o
define e o design.

## Revisão final

- **Importante, corrigido (`8218bc3e`).** Build operator com `change_id`
  nulo e ship `done` com qualquer entrada em `evidence`: `_ids_citados` saía
  vazio, e um `proof` `#<rule_id>` virava história sem mudança nenhuma. O gate
  do ship agora recusa `ship_evidence_missing` quando o build não registrou
  `change_id`. Teste: `test_ship_done_sem_change_id_no_build_recusa`.
- **Menor, corrigido no mesmo commit.** `ruff` B905: `zip` sem `strict=` no
  teste de contrato (T5).
- **Aceito, registrado.** O `unlock` de `ship_evidence_missing` mostra o hash
  de cada relatório presente; um agente pode copiá-lo sem ler o relatório. O
  gate não distingue leitura de cópia, e a skill manda ler antes.
- **Aceito, registrado.** O relatório não é assinado: quem escreve um
  `report.json` falso, grava o hash e apaga o arquivo passa como história. O
  gate prende o que o ship afirmou ter lido; provar que o sandbox o produziu
  seria assinatura (`sparkforge report sign`), fora desta feature.

## Desvios do plano

1. **Commit a mais:** `8218bc3e`, da revisão final, fora das seis tarefas.
2. **T4, testes a mais no mesmo passo:** o caso do `proof` `finding`
   explícito em AC2, o `#<rule_id>` em AC3 e a cópia divergente da proposal
   em AC4. No fluxo ponta a ponta, o helper da primeira versão
   (`_sem_evidencia`) virou `_ship_done_sem_evidencia`: o primeiro não voltava
   o ship a `done`, e o vermelho que ele deu era do teste, não do gate.
3. **T6, arquivos fora do manifesto:** `.agents/skills/sdd-build/SKILL.md`,
   `.agents/skills/sdd-ship/SKILL.md` (espelho), e
   `docs/guia/referencia/skills/sdd-build.md` e `sdd-ship.md` (referência
   gerada).
4. **T1 por heredoc.** O teste de T1 foi acrescentado ao arquivo por `cat >>`,
   e não pela ferramenta de edição; o arquivo ficou sem CR.
5. **Arquivo solto.** Um arquivo vazio `str` apareceu na raiz às 06:14, logo
   depois da escrita do design; foi apagado e não entrou em commit.
6. **`git stash` com gate rodando.** Para medir o `ruff` antes da correção,
   a árvore foi guardada e restaurada enquanto `check_vnext_claims.py` rodava
   em segundo plano; o gate foi rodado de novo no fechamento.

## Decisões tomadas sozinho

- `case_missing` continua histórico depois do ship (D4): o chamador pediu
  para desligar só o que tem relatório.
- A recusa por falta de entrada é uma só por ship, nomeando todos os ids que
  faltam, e não uma por id.
- Relatório presente mas ilegível conta como "presente": `moved` segue
  conferido e sai `moved_not_observed`, e o hash sai `(ilegivel)` na recusa.

## Gates rodados

- `python scripts/sync_skills.py --check`: OK.
- `python scripts/gen_reference_docs.py`: 2 páginas regravadas em T6, depois 0.
- `python scripts/check_surface_lock.py --update`: skills 532007 → 532882.
- `python scripts/check_vnext_claims.py`: 0 divergências.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.
- `python -m ruff check sparkforge/sdd tests`: limpo depois de `8218bc3e`.
- Bateria de 15 arquivos pedida pelo chamador: 1455 verdes.
