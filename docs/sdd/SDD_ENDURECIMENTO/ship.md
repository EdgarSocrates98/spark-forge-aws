---
sdd: 1
feature: SDD_ENDURECIMENTO
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_ENDURECIMENTO/build_report.md
  sha256: "fe7661d2005e2a9e07efcb9a82a762378e9df33446c8fe80ab54e2a7904542ee"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity]
deviations:
  - "Commit a mais (8218bc3e) da revisao final: build operator sem change_id com ship done deixava proof finding virar historia; agora sai ship_evidence_missing."
  - "T4 ganhou casos a mais nos mesmos testes (finding explicito, #<rule_id>, copia divergente da proposal)."
  - "Arquivos fora do manifesto: .agents/skills/sdd-build/SKILL.md, .agents/skills/sdd-ship/SKILL.md, docs/guia/referencia/skills/sdd-build.md, docs/guia/referencia/skills/sdd-ship.md e, no ship, docs/superpowers/STATUS.md (nota na linha Skills; contagem igual)."
  - "O teste de T1 entrou por heredoc (cat >>), nao pela ferramenta de edicao; o arquivo ficou sem CR."
  - "Um git stash foi feito com check_vnext_claims.py rodando em segundo plano; o gate rodou de novo no ship, com 0."
  - "Arquivo vazio str apareceu na raiz durante o define; apagado, fora de commit."
  - "Nota conhecida, sem edicao: SDD_MIGRATION/build_report.md sustenta 'sdd check descobre as mesmas seis features' com evidence_ref sparkforge/sdd/checks.py, um arquivo e nao um teste ou saida. Fica como esta; a feature entregue nao e reescrita."
  - "Build num agente so: sem subagente por tarefa, sem revisao em dois estagios, sem revisor novo na revisao final, e sem a leitura do operador por fase (o escopo veio fechado pelo chamador)."
---

# SDD_ENDURECIMENTO — entrega

## Hipótese

**Confirmada: todas as partes da previsão foram medidas.**

1. Os quatro casos de ship `done` dão exatamente o previsto:
   `test_ship_done_sem_evidencia_recusa` (`ship_evidence_missing`),
   `test_ship_done_com_evidencia_e_sem_relatorio_e_historia` (zero recusa),
   `test_ship_done_com_relatorio_que_contradiz` (`moved_not_observed`) e
   `test_ship_done_com_sha_divergente` (`ship_evidence_mismatch`). O de AC1 saiu
   vermelho antes do código com a lista vazia: o furo existia.
2. `moved` de outra mudança sai `moved_change_mismatch`
   (`test_moved_de_outra_mudanca`), e o `report.json` symlink para fora é
   ignorado (`test_relatorio_por_symlink_nao_escapa`).
3. O teste de contrato falha nos dois sentidos. Medido sobre cópias em
   diretório temporário, sem tocar a árvore, trocando o `ROOT` do módulo de
   teste: sem a linha de `ship_evidence_mismatch`, FALHA; com uma linha
   `codigo_inventado` a mais, FALHA; com o documento igual, PASSA.
4. `sdd check --repo .` sai com zero recusa e zero lacuna nas sete features,
   todas `profile: dev` (35 artefatos).

`SC1`: `ok: true`, 7 features, `refused: []`, `unresolved: []`.
`SC2`: `sdd-ship` 8162 → 8886 bytes, `sdd-build` 10635 → 10786; skills no
surface lock 532007 → 532882 (+875).

## Registros

`change_kinds` do define: `agent_or_skill`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `sync_skills` | Alterar agent, skill ou seus espelhos | `python scripts/sync_skills.py --check`: OK |
| `agents_parity` | Alterar agent, skill ou seus espelhos | `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q`: 233 verdes |

Critério de `kind: command`, rodado agora:

- `AC7`: `python -c "import sys;from sparkforge.adapters.cli import main;sys.exit(main(sys.argv[1:]))" sdd check --repo .`
  — exit 0, `ok: true`.

Fora do mapa, rodados porque a entrega os move:
`python scripts/gen_reference_docs.py` (2 páginas em T6, depois 0),
`python scripts/check_surface_lock.py --update` (+875 bytes em skills),
`python scripts/check_vnext_claims.py` (0 divergências),
`python scripts/check_status_numbers.py --strict` (0 divergências) e
`python -m ruff check sparkforge/sdd tests` (limpo).

Bateria de 15 arquivos pedida pelo chamador: 1455 verdes. A suíte inteira em
lotes não rodou.

## Pendências

- O relatório da mudança não é assinado: um `report.json` forjado, com o
  hash gravado e depois apagado, passa como história. Fechar isso é assinar o
  relatório no sandbox, outra feature.
- O `unlock` de `ship_evidence_missing` mostra o hash para copiar; ler o
  relatório continua sendo disciplina da skill.
- Nenhum caso operator real ainda; o fluxo ponta a ponta é sintético.

## Lições

- O furo morava num atalho de uma linha (`if _ship_feito: return`) que servia
  a dois casos opostos — pasta limpa e id inventado. Atalho de "histórico"
  precisa dizer qual evidência sumiu e o que ficou no lugar dela.
- A primeira correção deixou passar um atalho vizinho (build sem
  `change_id`); só a releitura do diff inteiro contra o define o achou.
- Um contrato em spec congelado envelhece calado; travá-lo por `ast` contra o
  código custou um teste.
