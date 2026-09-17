---
sdd: 1
feature: SDD_ENDURECIMENTO
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Com o ship done no perfil operator, um change_id fabricado com moved deixa de passar no gate, e o contrato dos codigos passa a morar num documento vivo que um teste confronta com o codigo, sem mudar o que o gate diz das features dev ja entregues."
  prediction: "Os quatro casos de ship done dao exatamente: sem relatorio e sem evidence, ship_evidence_missing; com evidence e relatorio apagado, zero recusa; com relatorio que contradiz moved, moved_not_observed; com relatorio de sha diferente do gravado, ship_evidence_mismatch. moved com change_id diferente do build sai moved_change_mismatch, e report.json que e symlink para fora da pasta e ignorado. O teste de contrato falha quando um codigo emitido em checks.py ou stamp.py falta em docs/sdd/CONTRATO.md, e quando o documento declara codigo que o codigo nao emite. `sdd check --repo .` sai com zero recusa e zero lacuna nas sete features dev. Qualquer resultado diferente de um desses refuta a hipotese."
  experiment: "Os testes nomeados em acceptance, rodados antes (vermelho) e depois (verde) de cada tarefa, e o comando de AC7 no fechamento."
acceptance:
  - id: AC1
    statement: "Feature operator com ship done, sem relatorio da mudanca e sem ship.evidence, sai com ship_evidence_missing."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_ship_done_sem_evidencia_recusa"}
  - id: AC2
    statement: "Feature operator com ship done, evidence gravada e o relatorio apagado e aceita como historia."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_ship_done_com_evidencia_e_sem_relatorio_e_historia"}
  - id: AC3
    statement: "Com o ship done e o relatorio ainda presente, moved e finding continuam conferidos: relatorio que contradiz sai moved_not_observed."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_ship_done_com_relatorio_que_contradiz"}
  - id: AC4
    statement: "Relatorio presente com text_sha256 diferente do report_sha256 gravado no ship sai ship_evidence_mismatch."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_ship_done_com_sha_divergente"}
  - id: AC5
    statement: "moved.change_id diferente do change_id do build_report sai moved_change_mismatch."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_moved_de_outra_mudanca"}
  - id: AC6
    statement: "report.json que e symlink para fora da pasta da mudanca nao e lido."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_relatorio_por_symlink_nao_escapa"}
  - id: AC7
    statement: "O perfil dev nao muda: ship dev sem evidence continua limpo, evidence no dev e schema_invalid, e o repositorio passa no check."
    verified_by: {kind: command, ref: "python -c \"import sys;from sparkforge.adapters.cli import main;sys.exit(main(sys.argv[1:]))\" sdd check --repo ."}
  - id: AC8
    statement: "O fluxo operator ponta a ponta grava evidence com o sha do relatorio real e continua limpo depois do sandbox e da proposal limpos."
    verified_by: {kind: test, ref: "tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta"}
  - id: AC9
    statement: "docs/sdd/CONTRATO.md lista todo codigo que checks.py e stamp.py emitem, e so eles."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_contrato_lista_todo_codigo"}
  - id: AC10
    statement: "sdd-ship, sdd-build e docs/sdd/README.md ensinam evidence, os codigos novos e o contrato vivo; o spec congelado aponta o contrato."
    verified_by: {kind: test, ref: "tests/test_sdd_operator.py::test_skills_ensinam_a_evidencia_do_ship"}
  - id: AC11
    statement: "O comentario de fixtures/sdd no .gitattributes diz text_sha256, e o README da suite sdd diz que r1 e r2 vieram de duas invocacoes --repeat 1."
    verified_by: {kind: test, ref: "tests/test_sdd_eval_suite.py::test_notas_de_hash_e_de_baseline"}
success:
  - id: SC1
    metric: "Recusas e lacunas do sdd check sobre o repositorio"
    source: "saida do comando de AC7"
  - id: SC2
    metric: "Bytes de sdd-build e sdd-ship no surface lock, antes e depois"
    source: "docs/surface.lock.json"
out_of_scope:
  - "Reescrever hypothesis_outcome de feature ja entregue (regra 21)."
  - "O evidence_ref fraco de SDD_MIGRATION: vira nota nos desvios do ship, nao edicao."
  - "case_missing depois do ship done continua historico: o case nao tem relatorio que o sustente, e reabrir outro case e o uso normal."
  - "Conferir hash de facts e de funcval: continuam conferidos pela forma em qualquer fase."
change_kinds: [agent_or_skill]
---

# SDD_ENDURECIMENTO — o que a revisão final achou

A revisão final da branch `sdd/nucleo-spec` achou um furo e cinco arestas.

## O furo

`_ship_feito` desliga toda conferência de evidência do operador assim que o
ship fica `done`. Um `change_id` inventado, com `moved` apontando uma regra,
passa, porque "o sandbox pode ter sido limpo". A correção separa as duas
situações: evidência **sumida** é história; evidência **presente** continua
conferida. E o ship passa a gravar o que viu (`evidence`: o `change_id` e o
`text_sha256` do relatório), para que "sumida" não seja o mesmo que "nunca
existiu".

## As arestas

- O contrato dos códigos mora num spec congelado; ganha um documento vivo,
  travado por teste contra o código.
- O comentário do `.gitattributes` fala de hash de bytes; o gate usa hash de
  texto.
- O README da suite `sdd` não diz que as duas amostras vieram de duas
  invocações.
- `moved.change_id` pode divergir do `change_id` do build sem recusa.
- O relatório da mudança é lido sem confinamento contra symlink.
