# Change Proof

Depois que o operador aplica uma recomendação, `sparkforge proof` diz o que
cada obrigação de prova daquela mudança concluiu (§20 de `prompt_new_evo.md`).

```bash
sparkforge proof --findings findings.json \
  --facts pyspark.json --facts funcval.json --facts bench.json \
  --after-facts depois-pyspark.json \
  --applied SF-PY-002
```

A tool MCP é `sparkforge_proof` (`READ_ONLY`). O dono é o `sf-verifier`
(checagem 7).

## As obrigações

Cada finding de `--applied` (`RULE_ID` aplica todos os findings da regra;
`RULE_ID:simbolo`, só o daquele símbolo) recebe:

1. **Resolução.** O `judge` roda sobre `--after-facts`.
   - A regra dispara de novo na mesma **chave estável** do subject → `refuted`.
   - A regra não disparou → `not_refuted`.
   - O kind que a regra lê sumiu **e** o extrator que o emite rodou no depois →
     `not_refuted` (`padrao_ausente_com_extrator_rodado`): a correção tirou o
     padrão. Se o extrator não rodou → `unproven`, com o kind e o módulo.
   - `runtime_scope` ou `blocked_on` → `inconclusive`: não é resolução.
2. **Um eixo por item de `action.moves`**, pela política
   `rules/catalog/proof_axes.yaml`:
   - `correctness.*` pelos veredictos de `funcval compare` (`SF-FVAL-001..004`
     refutam, `SF-FVAL-005` deixa inconclusivo);
   - `runtime.wall_clock`, `shuffle.spill_bytes`, `scan.bytes_read` e
     `scan.task_count` pelo `benchmark`;
   - os outros 17 eixos não têm comparador, e saem `unproven` com a medida que
     os destravaria (`unlock`).

## Os desfechos

| Desfecho | Quer dizer |
|---|---|
| `refuted` | Uma medida ou um veredito contrariou a obrigação |
| `not_refuted` | Foi medida e nada a contrariou |
| `inconclusive` | Foi medida, mas a comparação não vale ou não é atribuível |
| `unproven` | Nada a mede; `unlock` diz o que mediria |

Nunca "provado": os quatro proxies de `funcval` passam mesmo com duas linhas
trocando valores entre si, e um delta de benchmark não separa o efeito da
mudança do resto. `refused` traz sempre `proven` e `gain_estimate`.

## A chave estável

A resolução compara por tipo de subject, sem os campos que mudam entre antes e
depois sem que nada tenha sido resolvido (`line`, `col`, `snippet`,
`stage_id`, `job_run_id`, `event`):

| Tipo | Chave |
|---|---|
| `source_location` | `file`, `symbol` |
| `tf_resource`, `stage`, `table`, `plan_node` | `symbol` |
| `job_run` | `job_name` (sem ele, `inconclusive`) |

Renomear a função que contém o problema muda a chave; a saída devolve a chave
usada, e o revisor vê.

## A ordem do benchmark

O primeiro que casa decide:

1. `SF-BENCH-004` (stages não casados) → `inconclusive`.
2. `SF-BENCH-001` (volumes de entrada diferentes) → `inconclusive`. No eixo
   `scan.bytes_read` a razão é `volume_ou_leitura_indistinguiveis`: ler menos é
   o que as regras desse eixo recomendam, e o `SF-BENCH-001` dispara do mesmo
   jeito quando só a entrada mudou.
3. Event log ausente num lado, ou a medida sem delta → `inconclusive`.
4. Mais de uma mudança aplicada → `inconclusive` (`attribution_shared`): separar
   o delta exigiria o run que não aconteceu (regra 13).
5. A regra que julga o eixo (`SF-BENCH-002` no tempo, `SF-BENCH-003` no spill)
   → `refuted`.
6. Sem regra, o sinal do delta pela convenção declarada na política
   (`delta_pct >= 0` refuta) → `refuted` ou `not_refuted`.

`runtime.wall_clock` sai com `proxy: task_ms_nao_e_wall_clock`: o benchmark
soma tempo de task, não mede relógio.

## Cobertura, medida em 2026-09-12

Das 155 regras com `action`, **61** têm algum eixo que `funcval` ou `benchmark`
já medem, **43** só têm eixos sem comparador e **51** não declaram eixo. Todas
recebem a obrigação de resolução.

## Onde está provado

- `tests/test_proof_policy.py`: a política contra o catálogo real.
- `tests/test_proof_outcomes.py`: cada ramo dos desfechos.
- `tests/test_fixtures_golden_proof.py` e `fixtures/proof/`: dez casos de ponta a
  ponta pela CLI, cada um com as expectativas declaradas no `meta.yaml`.
