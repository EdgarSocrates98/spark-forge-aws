---
sdd: 1
feature: AC_VERMELHO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/AC_VERMELHO/plan.md
  sha256: "3f98dde5777f922deccd7214db07df1b50fe2f91aad3fea1f957dc83bc847e09"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1 tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida tests/test_sdd_ac_vermelho.py::test_feature_operator_nao_e_conferida -q", exit: 1}
    green: {command: "python -m pytest tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1 tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida tests/test_sdd_ac_vermelho.py::test_feature_operator_nao_e_conferida -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_skills_match -q", exit: 1}
    green: {command: "python -m pytest tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_skills_match -q", exit: 0}
claims:
  - text: "Criterio kind test sem tarefa done que o cubra com red citando o node id, ou o arquivo com exit 2, sai recusado com acceptance_never_red."
    evidence_ref: "tests/test_sdd_ac_vermelho.py::test_criterio_sem_vermelho_ligado_e_recusado"
  - text: "Arquivo com exit 1 nao conta; com exit 2 conta; exit 5 (nenhum teste coletado) nao e vermelho."
    evidence_ref: "tests/test_sdd_ac_vermelho.py::test_arquivo_conta_com_exit_2_e_nao_com_exit_1"
  - text: "guard com motivo isenta; guard sem letra nem digito, inclusive espaco Unicode invisivel, sai schema_invalid."
    evidence_ref: "tests/test_sdd_ac_vermelho.py::test_guarda_declarada_e_isenta_e_sem_motivo_e_recusada"
  - text: "Feature com ship done e feature operator nao sao conferidas; remover a isencao de historico faz o teste falhar."
    evidence_ref: "tests/test_sdd_ac_vermelho.py::test_feature_entregue_e_historico_e_nao_e_conferida"
---

# AC_VERMELHO — relatorio do build

| tarefa | commit | entregou |
|---|---|---|
| T1 | `be93ebb0` | schema `guard`, `_gate_acceptance_red`, 5 testes, ajustes em `test_sdd.py` |
| T2 | `c5d51ad4` | contrato, template, skills `sdd-define` e `sdd-build`, espelhos, referencia |
| correcao | `bbff4d4a`, `682b04fa` | achados da revisao final |

O `red` da T1 cita os node ids de cada criterio: esta feature e conferida pelo gate que
ela cria.

## Revisao final

Nenhum critico -- primeira vez em seis features. Um importante e seis menores:

- **Importante:** a referencia com `./` ou `\` nao era normalizada como o token do comando,
  e recusava um `red` correto. Corrigido com `_caminho_normal` aplicado aos tres.
- Tarefa `skipped`/`blocked` contava como vermelho: so `done` conta agora.
- `exit 5` do pytest (nenhum teste coletado) contava: agora nao.
- `guard` de espaco Unicode invisivel passava: o schema exige letra ou digito.
- O contrato diz que o gate confere **citacao** do node id, nao execucao.
- Dois arquivos entraram fora do manifesto (`CODEINTEL-GAP.md`, `ADR-010`), movidos pelo
  gate de lastro; acrescentados ao design.

A revisao testou mutacao: remover a isencao de historico faz o teste do AC4 falhar.

## Desvios

1. **O explore mediu por arquivo; a regra liga por node id.** Aplicada retroativamente, ela
   recusaria **45 criterios em 15 features**, nao 14 em 12. A isencao de historico e o que
   segura isso.
2. **"12 features entregues"** no define e no explore: hoje sao 18 `ship.md` em `done`.
3. Na T1 os lotes vizinhos rodaram em paralelo, nao um por vez; todos passaram.
4. Sete arquivos entraram no manifesto do design na fase de plano, e dois na correcao.

## O que fica de fora

A classe do `CONFIG_OCA:AC2` -- teste vermelho de verdade que cobre pouco -- e o `red`
declarado com `--deselect` ou em comentario. O gate confere citacao; so mutacao por
criterio chegaria na propriedade real.
