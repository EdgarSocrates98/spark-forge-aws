---
sdd: 1
feature: SDD_OPERATOR_DURAVEL
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_OPERATOR_DURAVEL/plan.md
  sha256: "a29b5e186edecb3d2286e5d37a396e92bddc0d73a84ce1ca5b029a573335c3bc"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_change_id_aceita_proposal -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_case_e_change_historicos_depois_do_ship -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_fact_por_kind -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_proof_de_tarefa_operator -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_sdd.py::test_moved_confere_o_relatorio tests/test_sdd.py::test_proof_e_moved_fecham_propriedades -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_sdd_operator.py -q (git worktree em 4c9fa9e5, nucleo antes de T1)", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py -q", exit: 0}
  - id: T7
    status: done
    red: {command: "python -m pytest tests/test_sdd_operator.py::test_skills_ensinam_o_operador_duravel -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd.py tests/test_sdd_operator.py tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py -q", exit: 0}
claims:
  - text: "change_id vale com .sparkforge/sandbox/<id>/ ou .sparkforge/proposal/<id>/, as duas confinadas a um segmento; arquivo com o nome do id nao serve."
    evidence_ref: "tests/test_sdd.py::test_change_id_aceita_proposal"
  - text: "Com o ship done, case trocado e sandbox apagado nao recusam; com o ship ready ou ausente, case_missing e change_missing voltam."
    evidence_ref: "tests/test_sdd.py::test_case_e_change_historicos_depois_do_ship"
  - text: "path#kind:<kind> passa com um fact daquele kind, path#<id> segue valendo e kind: vazio nao casa."
    evidence_ref: "tests/test_sdd.py::test_fact_por_kind"
  - text: "proof finding e lacuna finding_not_observed antes do build e recusa moved_not_observed depois; ref sem rule_id e schema_invalid; no dev, proof e schema_invalid mais task_without_test."
    evidence_ref: "tests/test_sdd.py::test_proof_de_tarefa_operator"
  - text: "moved exige cada regra em resolved e fora de new no relatorio do sandbox ou da proposal; no dev, moved e schema_invalid mais red_not_declared."
    evidence_ref: "tests/test_sdd.py::test_moved_confere_o_relatorio"
  - text: "proof e moved fecham propriedades no schema."
    evidence_ref: "tests/test_sdd.py::test_proof_e_moved_fecham_propriedades"
  - text: "O fluxo operator com case_open, change_sandbox, change_propose e analyze_pyspark reais, raiz .sparkforge/sdd, proof finding e moved sobre o report.json real passa no check; passa depois do sandbox limpo e com outro case e o ship done; com o ship ready sai case_missing, change_missing e dois moved_not_observed."
    evidence_ref: "tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta"
  - text: "A mesma spec em docs/sdd faz change propose recusar com sandbox_desatualizado."
    evidence_ref: "tests/test_sdd_operator.py::test_spec_em_docs_sdd_desatualiza_o_sandbox"
  - text: "As quatro skills e o README ensinam a raiz .sparkforge/sdd, o seletor por kind, proof, moved e as flags de evidencia."
    evidence_ref: "tests/test_sdd_operator.py::test_skills_ensinam_o_operador_duravel"
  - text: "A superficie de skills cresceu 3066 bytes (529195 para 532261)."
    evidence_ref: "docs/surface.lock.json"
  - text: "O gate de lastro fecha com zero divergencia depois de remediar VNX-674 por id (228364 para 228370)."
    evidence_ref: "docs/claims.lock.json"
change_id: null
---

# SDD_OPERATOR_DURAVEL — relatório do build

Sete tarefas, um commit cada: `273e6bda` (T1), `d1226261` (T2), `54f4ced0`
(T3), `40f8f9a7` (T4), `dbf64b92` (T5), `2116adca` (T6), `f67c9763` (T7).
Todo vermelho acima foi visto na hora, com o comando e a falha pelo motivo
certo.

## Sem subagente

Este build rodou num agente só, que não despacha subagente. Não houve um
implementador novo por tarefa nem a revisão em dois estágios (spec e depois
qualidade) que `sdd-build` descreve. Cada tarefa rodou os gates vizinhos do
plano.

## Desvios do plano

1. **T2, vermelho vizinho.** `tests/test_sdd_operator.py` (versão de
   `SDD_OPERATOR`) esperava `change_missing` depois do `clean` com o ship
   `done`. Pela D3 isso virou histórico; o teste antigo passou a conferir os
   dois lados (`done` limpo, `ready` recusa) no mesmo commit de T2. T6
   reescreveu o arquivo depois.
2. **T6, vermelho fora da árvore.** Com T1 a T5 feitos, o teste ponta a ponta
   passou de primeira. O vermelho é o mesmo arquivo num `git worktree` em
   `4c9fa9e5`: dois `schema_invalid` (`proof` e `moved` desconhecidos).
   Entrou um segundo teste, `test_spec_em_docs_sdd_desatualiza_o_sandbox`,
   que o plano já trazia; ele passa nas duas árvores, porque mede o
   comportamento do `change propose`, não do gate.
3. **T6, erro de ambiente visto no T1.** As sondas desta sessão chamaram
   `call_tool` a partir da raiz e criaram `.sparkforge/traces.db`, que o
   `conftest` recusa; o arquivo (ignorado pelo git) foi apagado antes do
   primeiro vermelho, e as sondas seguintes rodaram fora da raiz.
4. **Registros fora do manifesto:** `docs/harness/CODEINTEL-GAP.md` (o número
   de VNX-674).

## Gates rodados no fechamento

- `python scripts/sync_skills.py` com `.claude/agents/README.md` fora da
  árvore (8 cópias), depois `--check`: OK.
- `python scripts/gen_reference_docs.py`: 268 páginas, 4 regravadas.
- `python scripts/check_surface_lock.py`: 2 divergências; com `--update`,
  skills de 529195 para 532261 bytes (+3066).
- `python scripts/check_vnext_claims.py`: 1 divergência (VNX-674, 228364 →
  228370, a linha de `success.source` do teste ponta a ponta), remediada por
  id e relida da própria prova; depois 0.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.
