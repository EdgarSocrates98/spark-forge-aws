---
sdd: 1
feature: AC_VERMELHO
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/AC_VERMELHO/build_report.md
  sha256: "df0e7885621c0706d9931dce97c7ebe477572d411f246c4225614fd5290b9295"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity, claims_gate]
deviations:
  - "O explore mediu por ARQUIVO (14 criterios em 12 features); a regra liga por NODE ID. Aplicada retroativamente, recusaria 45 criterios em 15 features. A isencao de historico segura isso, e o teste dela mata o mutante que a remove."
  - "O define fala em 12 features entregues; hoje sao 18 ship.md em done."
  - "Sete arquivos entraram no manifesto na fase de plano (6 testes do SDD quebravam com o gate) e dois na correcao (movidos pelo gate de lastro)."
  - "D5 veio do plano, nao do design: a regra vale so no perfil dev. Decidido pelo operador em 2026-09-21."
  - "A revisao final nao achou critico -- primeira vez em seis features. Um importante e seis menores, corrigidos em bbff4d4a e 682b04fa."
  - "Na T1 os lotes vizinhos rodaram em paralelo, nao um por vez."
---

# AC_VERMELHO — entrega

## Hipotese

**Confirmada.** Sobre features sinteticas: criterio `kind: test` sem vermelho ligado sai
`acceptance_never_red`; guarda declarada passa; guarda sem letra nem digito e recusada;
arquivo com `exit 1` nao conta; e o `sdd check --repo .` segue sem recusa em nenhuma feature
entregue.

**Esta feature passou no gate que ela cria.** O `build_report` dela e conferido pela regra
nova, e o `red` da T1 cita o node id de cada criterio.

## O que entrega

- Recusa `acceptance_never_red` no `sdd check`, perfil `dev`, com o `build_report` pronto e o
  ship ainda nao entregue.
- `guard: <motivo>` no `acceptance`, para guarda de regressao legitima.
- Contrato, template e skills `sdd-define`/`sdd-build` dizendo a regra.

## O que ela NAO pega, dito

- Teste vermelho de verdade que cobre pouco (a classe do `CONFIG_OCA:AC2`).
- `red` declarado com `--deselect` ou com o node num comentario: o gate confere **citacao**
  no comando declarado, nao execucao.

So mutacao por criterio chegaria na propriedade real. Fica como proxima feature possivel.

## Gates rodados

| gate | resultado |
|---|---|
| SDD, AC_VERMELHO, operator, skills, golden SDD (5 arquivos) | 198 passed |
| `python scripts/sync_skills.py --check` (AC5) | exit 0 |
| `python scripts/check_vnext_claims.py` (AC6) | 0 divergencias |
| `python scripts/check_surface_lock.py` | 0 divergencias |
| `python scripts/check_status_numbers.py --strict` | 0 divergencias |
| `python -m ruff check sparkforge scripts tests` | limpo |
| `sparkforge sdd check --repo .` | sem recusa |

## Licoes

- **A revisao que tenta fazer o gate passar indevidamente acha mais que a que confere se ele
  falha.** O unico importante foi uma recusa INDEVIDA -- referencia com `./` -- e ela so
  aparece testando o caso legitimo que o gate deveria aceitar.
- **Medida de explore feita com a regra frouxa subestima o alcance.** Por arquivo, 14; por
  node id, 45.
