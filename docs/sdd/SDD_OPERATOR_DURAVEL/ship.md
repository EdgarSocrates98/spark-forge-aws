---
sdd: 1
feature: SDD_OPERATOR_DURAVEL
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_OPERATOR_DURAVEL/build_report.md
  sha256: "c9fb45a8e67501e0d199315f9c0329b69403dcdf17184fe26c79bb232860706c"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity]
deviations:
  - "T2: o teste ponta a ponta antigo esperava change_missing com o ship done; passou a conferir os dois lados no commit de T2 (vermelho vizinho da propria tarefa)."
  - "T6: o teste passou de primeira depois de T1 a T5; o vermelho foi visto num git worktree em 4c9fa9e5."
  - "T6: .sparkforge/traces.db criado pelas sondas da sessao foi apagado antes do primeiro vermelho."
  - "D5 acrescenta ao pedido: finding aceita #<rule_id> sem change_id, lido do build_report, porque o id do sandbox nao existe na hora do plano."
  - "D3 estende a referencia historica a moved e a proof finding, alem de case_missing e change_missing, pelo mesmo motivo (sandbox limpo depois do done)."
  - "Registros fora do manifesto: docs/harness/CODEINTEL-GAP.md (VNX-674)."
  - "Build num agente so, sem subagente por tarefa e sem a revisao em dois estagios."
---

# SDD_OPERATOR_DURAVEL — entrega

## Hipótese

**Confirmada no que o experimento mede.** A previsão tinha quatro
observações, todas medidas em `tests/test_sdd_operator.py`:

1. O fluxo com `case_open`, `change_sandbox`, `change_propose` e
   `analyze_pyspark` reais, raiz `.sparkforge/sdd`, uma tarefa provada por
   `finding` e um `moved` sobre o `report.json` real passa no `sdd check`
   (`test_fluxo_operator_ponta_a_ponta`).
2. Depois de `change sandbox --clean`, continua passando pelo pacote de
   proposal (mesmo teste).
3. Com o ship `done`, outro case (`case open --reopen`) e nenhuma pasta de
   mudança, continua passando; com o ship `ready`, saem `case_missing`,
   `change_missing` e dois `moved_not_observed` (mesmo teste).
4. A mesma spec em `docs/sdd` faz `change propose` recusar com
   `sandbox_desatualizado` (`test_spec_em_docs_sdd_desatualiza_o_sandbox`).

Ressalva dita: a comparação do funcval continua sintética (a forma de
`_check_delta`); `sparkforge funcval compare` não roda no teste. Um operador
de verdade usando o perfil fora da sessão fica para `SDD_EVAL`.

`SC1`: códigos novos exercitados — `moved_not_observed` (recusa) e
`finding_not_observed` (lacuna), mais `change_missing`, `case_missing`,
`fact_not_collected`, `funcval_not_run`, `funcval_not_comparison`,
`schema_invalid`, `task_without_test` e `red_not_declared` nos lados do perfil.
`SC2`: skills de 529195 para 532261 bytes (+3066).

## Registros

`change_kinds` do define: `agent_or_skill`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `sync_skills` | Alterar agent, skill ou seus espelhos | `python scripts/sync_skills.py` (README de `.claude/agents/` fora), depois `--check`: OK |
| `agents_parity` | Alterar agent, skill ou seus espelhos | `tests/test_agents_parity.py`, `tests/test_agent_coverage.py`, `tests/test_sync_render.py`: verdes na bateria abaixo |

`AC9` (`verified_by: command`) é o `python scripts/sync_skills.py --check`
acima, com exit 0.

Gates fora do mapa, rodados porque a entrega os move:

- `python scripts/gen_reference_docs.py`: 4 páginas regravadas.
- `python scripts/check_surface_lock.py --update`: +3066 bytes em skills,
  declarados no commit.
- `python scripts/check_vnext_claims.py`: 0 divergências depois de VNX-674.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.

Bateria: 1605 testes verdes, nenhuma falha.

```
python -m pytest tests/test_sdd.py tests/test_sdd_operator.py tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_arvore_versionada.py tests/test_adapters_tools.py tests/test_harness_authorization.py tests/test_bootstrap_budget.py -q
```

A suíte inteira em lotes não rodou nesta entrega.

## Lições

- O perfil operator só é conferível se a spec não mexer na árvore que o
  sandbox validou; a poda de `.sparkforge` é o que torna isso verdade.
- Referência a estado recriado (case, sandbox) precisa de prazo de validade;
  o `done` do ship é esse prazo.
- Id que é hash não pode ser pedido antes de existir: o seletor por kind e o
  `#<rule_id>` resolvem o mesmo problema em dois lugares.

## O que fica para depois

- `SDD_SKILLS_REVISAO`: o resto da revisão de texto das skills.
- `SDD_EVAL`: um caso operator real, com `funcval compare` de verdade.
