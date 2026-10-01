---
sdd: 1
feature: INTEGRACAO_USUARIO
phase: ship
profile: dev
status: draft
upstream:
  path: docs/sdd/INTEGRACAO_USUARIO/build_report.md
  sha256: "cdb3cb1a645aebab49d4bddce1b0fd3df7f0178494c0952218ec35c153b9f776"
registries: [surface_lock, generated_reference, sync_skills, agents_parity, requirements_mirror, hash_locks, status_numbers_gate, claims_gate]
deviations:
  - "Revisao por grupo de tarefas (T1-T3, T4-T6, T7-T9) em vez de duas por tarefa, e gates pesados so na T10, por pedido do operador."
  - "Tres rodadas de correcao de revisao e uma da revisao final mudaram o writer, o manifesto (formato 2) e o conflito depois do plano; registradas no build_report."
  - "Arquivos fora do manifesto do design: tests/test_facts_scan.py, tests/test_verify_wheel.py, scripts/verify_wheel.py, tests/test_forge_cli_doctor.py, tests/test_fixtures_golden_mcp_parity.py, docs/guia/usos/scan-e-doctor.md, docs/harness/CURRENT-HARNESS-GAP.md."
  - "verify_wheel completo nao rodou nesta maquina (morto tres vezes por falta de memoria); rodou a checagem leve do bundle no pacote instalado; o completo e o passo do CI do PR."
---

# INTEGRACAO_USUARIO — entrega

## Hipótese

Aberta. Medido nesta máquina, com HOME e APPDATA temporários: Devin, Codex e Copilot CLI
recebem exatamente os arquivos que cada formato descobre; o conteúdo é o da renderização
do `sync_skills.py` (o teste compara o gravado com os espelhos do repo, e fica vermelho por
mutação da tabela de hosts); o `detach` remove só o que o manifesto registrou e devolve a
config byte a byte; nada é escrito no repositório (guarda pela API e pela CLI). Falta
medir, antes de fechar: o `verify_wheel` completo (CI do PR) e o fluxo do Claude contra o
CLI real (`claude plugin marketplace add` / `install` / `list --json`), que só rodou contra
um CLI falso. Por isso o ship fica em `draft` e o `verify_wheel` fora de `registries`.

## Gates rodados

| Registro | Comando | Exit |
|---|---|---|
| surface_lock | `python scripts/check_surface_lock.py` | 0 |
| generated_reference | `python scripts/gen_reference_docs.py --check` | 0 |
| sync_skills, agents_parity | `python scripts/sync_skills.py --check`, `pytest tests/test_agents_parity.py tests/test_sync_render.py` | 0 |
| requirements_mirror, hash_locks | `pytest tests/test_supply_chain.py tests/test_requirements_mirror.py tests/test_ci_workflow.py` | 0 |
| status_numbers_gate | `python scripts/check_status_numbers.py --strict` | 0 |
| claims_gate | `python scripts/check_vnext_claims.py` | 0 |

Suíte em lotes: 61 unidades, um vermelho da feature (varredura crua), corrigido.

## Comandos `kind: command` do define

- AC12: `check_surface_lock`, `check_vnext_claims` e `check_status_numbers --strict`, exit 0;
  `verify_wheel` pendente no CI.

## Lições

- Rodar `integrate` com o terminal no HOME fazia `repo/.agents/skills` ser o próprio destino
  da integração; só a revisão final achou, e o doctor ainda sugeria o comando destrutivo.
  Feature que remove arquivo por nome precisa testar o caso em que a origem e o destino são
  o mesmo diretório.
- Revisão por grupo encontrou um crítico e vinte e poucos importantes em quatro rodadas; o
  plano "já rodado numa cópia" não substitui a revisão de comportamento.
- O `verify_wheel` roda a suíte inteira e não cabe nesta máquina; a checagem leve do bundle
  no pacote instalado deveria ser um passo próprio, barato, do gate.
