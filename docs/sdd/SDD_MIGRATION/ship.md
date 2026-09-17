---
sdd: 1
feature: SDD_MIGRATION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_MIGRATION/build_report.md
  sha256: "b9a69e7f0e0591f17beaa64203a4f73a2f890370eae28c3652b1b5060e687463"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity]
deviations:
  - "Arquivos fora do manifesto: docs/superpowers/STATUS.md (nota sobre os ponteiros .claude/sdd antigos), GUIA_DE_USO.md (linha do laco /spec aponta o SDD), docs/claims.lock.json e docs/harness/CODEINTEL-GAP.md (VNX-640, 738 -> 739)."
  - "T2: rodados tambem os testes que varrem docs/ e .claude/; nenhum le docs/sdd/archive/, entao nenhum gate ganhou exclusao."
  - "Recusa transitoria manifest_path_unknown em design.md (.claude/sdd com action delete) entre T2 e o build_report pronto, como o gate preve."
  - "Documentos revistos sem mudanca: .github/copilot-instructions.md, .devin/README.md, docs/guia/05-agents-e-skills.md; GEMINI.md nao existe."
  - "Build num agente so: sem subagente por tarefa, sem revisao em dois estagios e sem revisor novo na revisao final."
---

# SDD_MIGRATION — entrega

## Hipótese

**Confirmada: as três partes da previsão foram medidas.**

1. Nenhum arquivo rastreado sob `.claude/sdd/`: `git ls-files .claude/sdd`
   devolve 0 linhas (`SC1` = 0), e
   `test_historico_agentspec_arquivado` passa.
2. `.claude/settings.json` desliga `agentspec@agentspec`
   (`test_agentspec_desligado_no_projeto`).
3. `CLAUDE.md`, `AGENTS.md` e `CONTRIBUTING.md` citam `sdd-define` e
   `sparkforge sdd check` (`test_documentos_de_entrada_apontam_o_sdd`).

O experimento pedia também o `sdd check` sobre `docs/sdd` depois da migração:
ele descobre as mesmas seis features, sem tomar `docs/sdd/archive/` por
feature e sem `path_skipped`.

A previsão mede os sinais que um agente lê ao abrir o repositório, não o
comportamento do agente. Se ele de fato chama `sdd_check`/`sdd_status` é o que
`SDD_EVAL` mede.

## Registros

`change_kinds` do define: `agent_or_skill`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `sync_skills` | Alterar agent, skill ou seus espelhos | `python scripts/sync_skills.py --check`: OK, exit 0 |
| `agents_parity` | Alterar agent, skill ou seus espelhos | `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q`: verdes |

O define não tem critério de `kind: command`.

Fora do mapa, rodados porque a entrega os move:
`python scripts/gen_reference_docs.py` (0 páginas regravadas),
`python scripts/check_surface_lock.py --update` (sem mudança),
`python scripts/check_vnext_claims.py` (0 divergências, depois de VNX-640) e
`python scripts/check_status_numbers.py --strict` (0 divergências).

Bateria de 13 arquivos: 1316 verdes. A suíte inteira em lotes não rodou.

## Lições

- Mover diretório citado num `design.md` com `action: delete` deixa o gate
  recusando até o `build_report` ficar pronto; o relatório registra isso para
  não parecer defeito.
- Arquivo `.py` novo move VNX-640 mesmo quando a entrega é só de documentação:
  o teste da feature entra no corpus.

## O que fica para depois

- Plugins no nível do usuário continuam instalados; desligar lá é decisão do
  operador.
