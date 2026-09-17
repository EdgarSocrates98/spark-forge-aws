<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `sdd-ship`

Use quando o build_report.md da feature está pronto e é hora de fechar — "entrega a feature", "fecha o ciclo", "fase ship", "posso abrir o PR?". Deriva a lista de gates das seções de docs/gates-por-mudanca.md pelos change_kinds do define, roda cada um, registra os registros conferidos, fecha a hipótese sem reescrevê-la, lista os desvios, atualiza STATUS e manifestos e grava docs/sdd/<FEATURE>/ship.md, fechando com sparkforge sdd stamp e sparkforge sdd check.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/sdd-ship/SKILL.md` |

## Procedimento (texto integral)

## SDD Ship

Fase 4 do SDD próprio. Fecha a feature com três coisas que o gate confere: os
registros que o tipo de mudança exige foram rodados, a hipótese do define tem
desfecho, e o build veio antes. O resto — desvios, STATUS, a mensagem do PR — é
disciplina desta skill.

### Antes de começar

1. `sparkforge sdd check --repo . --feature <F>` com o `build_report.md` em
   `ready` ou `done`, e sem recusa. Ship sobre build incompleto é
   `phase_out_of_order`.
2. Todas as tarefas do relatório em `done`, ou `skipped`/`blocked` com o motivo
   no corpo. Tarefa bloqueada sem saída combinada com o operador volta ao build.
3. Copie `docs/sdd/templates/ship.md` para `docs/sdd/<FEATURE>/ship.md`, com
   `status: draft` e `upstream.path` no build_report da feature.

### Derivar os gates

1. Leia `change_kinds` do define.
2. Para cada chave, `sparkforge/sdd/change_kinds.yaml` dá a `section` de
   `docs/gates-por-mudanca.md` e os `registries` exigidos. Exemplo: skill nova é
   `agent_or_skill` (`sync_skills`, `agents_parity`) mais `tool_or_verb`
   (`surface_lock`, `generated_reference`).
3. Abra cada seção e rode os comandos **como estão escritos lá**. O mapa diz o
   nome do registro; o comando mora na seção.
4. Liste em `registries` só o nome de registro cujo gate você rodou e viu
   passar. O que faltar sai `registry_unchecked`, nomeando a seção.
5. Arquivo `.py` novo move alegações do gate de lastro:
   `python scripts/check_vnext_claims.py`, remediado pela lista de ids da saída,
   nunca por varredura.
6. Crescimento da superfície (`python scripts/check_surface_lock.py --update`)
   vai declarado em bytes na mensagem do commit.
7. A suíte roda em lotes, um por vez (`tests/test_suite_batches.py`).

### Fechar a hipótese

`hypothesis_outcome` recebe `confirmed`, `refuted` ou `abandoned`. Sem ele,
`hypothesis_open_at_ship`.

- **Só acrescenta.** A afirmação, a previsão e o experimento do define ficam como
  estão. Editar o define agora para casar com o resultado é reescrever a
  hipótese — e ainda deixaria todas as fases de baixo em `upstream_stale`.
- **Previsão com parte que só se mede depois:** `confirmed` só se a parte
  mensurável agora se confirmou, e o corpo diz qual parte segue pendente e onde
  ela será verificada. Se a parte mensurável falhou, é `refuted`.
- **`abandoned`** quando o experimento não rodou, com o motivo.

### Desvios

`deviations` lista o que o build fez diferente do plano e do design: arquivo que
entrou fora do manifesto, teste ajustado, decisão tomada no caminho. "Nenhum" só
quando for verdade. Spec antigo que ficou obsoleto ganha uma seção de desvios;
não é reescrito.

### Documentação

- `docs/superpowers/STATUS.md`: os números que a entrega move, conferidos por
  `python scripts/check_status_numbers.py --strict`.
- `manifest.json`, `README.md` e o guia, quando a entrega muda o que eles
  listam. Número medido, não copiado.

### O laço

1. Rode os gates e anote o que passou.
2. Escreva `ship.md` com `registries`, `hypothesis_outcome`, `deviations` e o
   corpo (hipótese, pendências, gates rodados).
3. `sparkforge sdd stamp --repo . docs/sdd/<F>/ship.md`.
4. `sparkforge sdd check --repo . --feature <F>`: `ok` verdadeiro, zero recusa e
   zero lacuna. Então `status: done`.
5. Commit.
6. Integração: apresente as opções (abrir PR, manter a branch) e **espere a
   escolha do operador** antes de `git push`, `gh pr create` ou merge.

Nada é movido para arquivo morto: a pasta da feature é o registro. Uma fase
substituída depois vira `status: superseded`.

### Perfil operator

- O `ship.md` mora em `.sparkforge/sdd/<F>/`, como as outras fases:
  `sparkforge sdd check --repo . --root .sparkforge/sdd --feature <F>`.
- O pacote do PR sai de
  `sparkforge change propose --sandbox <id> --repo . --funcval <cmp.json> --benchmark bench.json`,
  sobre o `change_id` que o build registrou, e o PR pela skill
  `propose-change-pr`. Sem `--funcval` e `--benchmark`, o pacote diz PENDENTE.
- `confirmed` exige medida: `sparkforge funcval compare` para a semântica e
  `sparkforge benchmark` entre runs para o desempenho. Economia estimada não
  fecha hipótese.
- Com `status: done`, o case e a mudança citados viram histórico: o
  `case.yaml` pode passar a ser de outro case e `change sandbox --clean` pode
  rodar, sem `case_missing` nem `change_missing`. Antes do `done`, os dois
  valem; o id serve enquanto existir `.sparkforge/sandbox/<id>/` ou
  `.sparkforge/proposal/<id>/`.
- Os registros de `change_kinds` são do repositório SparkForge; mudança só no
  job do operador costuma ter `change_kinds: []`.

### Quando NÃO usar

- Build com tarefa pendente ou teste vermelho: volte a `sdd-build`.
- Para medir se o SDD próprio é melhor que outro processo: isso exige caso bem
  posto rodando nos dois lados, e não é o ship de uma feature.
- Para fazer `git push`, merge ou abrir PR sem a escolha explícita do operador.

### Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| conferir o build | `sparkforge sdd check --repo . --feature <F>` | `sparkforge_sdd_check` |
| carimbar | `sparkforge sdd stamp --repo . docs/sdd/<F>/ship.md` | `sparkforge_sdd_stamp` |
| estado geral | `sparkforge sdd status --repo .` | `sparkforge_sdd_status` |
| semântica (operator) | `sparkforge funcval compare --plan <p> --before <a> --after <b> --out <ref do AC>` | `sparkforge_funcval_compare` |
| PR (operator) | `sparkforge change propose --sandbox <id> --repo . --funcval <cmp.json> --benchmark bench.json` | `sparkforge_change_propose` |

Gates que aparecem em quase toda entrega de dev:

```
python scripts/sync_skills.py --check
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py --update
python scripts/check_vnext_claims.py
python scripts/check_status_numbers.py --strict
```

Recusas desta fase: `phase_out_of_order`, `hypothesis_open_at_ship`,
`registry_unchecked`, `upstream_stale`. Template: `docs/sdd/templates/ship.md`.

### Red flags

- Registro listado sem o gate ter rodado.
- Define editado no ship para a hipótese "fechar".
- `confirmed` com a parte mensurável ainda por medir.
- `deviations: []` numa entrega que tocou arquivo fora do manifesto.
- Crescimento de superfície sem os bytes no commit.
- `check_vnext_claims.py --seed` para "limpar" divergências.
- `git push` ou PR aberto sem a escolha do operador.
- Afirmação de ganho sem medida nos dois lados.
