---
sdd: 1
feature: SDD_SKILLS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_SKILLS/build_report.md
  sha256: "89af530da2b97f90c4301c94ee7fb6a3690f9767039810a5726600189de9cedd"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity, surface_lock, generated_reference]
deviations:
  - "T1: o teste dos templates exige tambem unresolved vazio e ok verdadeiro, e um segundo teste prova que docs/sdd/templates/ fica fora da descoberta."
  - "T1: templates ajustados ao nucleo real (define com upstream para o explore, verified_by existente no repositorio temporario, change_kinds [agent_or_skill] com os dois registros no ship)."
  - "Registros fora do manifesto do design: manifest.json, tests/test_sync_render.py, docs/superpowers/STATUS.md, docs/claims.lock.json, docs/vnext/CURRENT-STATE.md, docs/harness/CODEINTEL-GAP.md, docs/guia/05-agents-e-skills.md e docs/guia/referencia/."
  - "T3: o vermelho veio dos auxiliares ausentes (NameError); nenhuma skill precisou de correcao; entrou um teste de guarda do detector."
  - "T4: o teste de credito exige tambem o nome das seis skills."
  - "T5: o teste nomeado no plano ficou verde no T2; o vermelho registrado e tests/test_reference_docs.py antes da regeneracao."
  - "Build sem subagente e sem a revisao em dois estagios que sdd-build descreve."
---

# SDD_SKILLS — entrega

## Hipótese

**Confirmada na parte que se mede hoje.** A previsão do define tem duas partes:

1. *Os gates de skill passam com as seis* — medido agora:
   `python scripts/sync_skills.py --check` OK e a bateria de testes de skill,
   espelho, cobertura, referência, árvore versionada, orçamento de bootstrap e
   núcleo SDD com 1179 testes verdes. A própria feature `SDD_SKILLS` fecha com
   `sparkforge sdd check --repo . --feature SDD_SKILLS` sem recusa e sem lacuna.
2. *As features `SDD_OPERATOR`, `SDD_MIGRATION` e `SDD_EVAL`, escritas com essas
   skills, fecham com `sparkforge sdd check` sem recusa* — **pendente**. As três
   ainda serão escritas (subprojetos C, D e E). A verificação mora no ship de
   cada uma e, consolidada, em `SDD_EVAL`, que também é onde a métrica `SC1`
   (recusas do `sdd check` sobre `docs/sdd` depois de B, C, D e E) é lida. Se
   alguma delas fechar com recusa que as skills deveriam ter evitado, o desfecho
   desta hipótese é revisto lá, por acréscimo.

`SC1` depois de B: `sparkforge sdd check --repo .` devolve zero recusa e zero
lacuna sobre `docs/sdd` (uma feature, `SDD_SKILLS`).

## Registros

`change_kinds` do define: `agent_or_skill` e `tool_or_verb`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `sync_skills` | Alterar agent, skill ou seus espelhos | `python scripts/sync_skills.py --check` — OK |
| `agents_parity` | Alterar agent, skill ou seus espelhos | `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q` — verde (dentro da bateria de 1179) |
| `surface_lock` | Acrescentar ou alterar tool, verbo de CLI, agent ou skill: a referência gerada | `python scripts/check_surface_lock.py --update`, depois 0 divergência; +39828 bytes declarados no commit `01efeafd` |
| `generated_reference` | idem | `python scripts/gen_reference_docs.py` e `python -m pytest tests/test_reference_docs.py -q` — verde |

Gates fora do mapa, rodados porque a entrega os move: `python
scripts/check_vnext_claims.py` (0 divergência, VNX-053 e VNX-640 remediados por
id) e `python scripts/check_status_numbers.py --strict` (0 divergência). A suíte
inteira em lotes (`tests/test_suite_batches.py`) não foi rodada nesta entrega;
só a bateria dirigida acima.

## Desvios

Detalhados no `build_report.md`. O mais útil para as próximas features: a
entrega tocou oito registros que o manifesto do design não listava, e a skill
`sdd-design` agora manda listá-los desde o desenho.

## O que fica para depois

- `SDD_OPERATOR` (C): o detalhe do perfil operator nas skills, inclusive o que o
  campo `test` de tarefa significa quando a mudança sai de `change sandbox`.
- `SDD_MIGRATION` (D): desativar os plugins e apontar `CLAUDE.md`/`AGENTS.md`
  para as skills.
- `SDD_EVAL` (E): medir, com caso bem posto dos dois lados, se o ciclo próprio
  rende melhor que os dois plugins. Nenhuma afirmação desse tipo é feita aqui.
