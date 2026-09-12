# DESIGN: Change Proof

> Technical design for CHANGE_PROOF

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHANGE_PROOF |
| **Date** | 2026-09-12 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_CHANGE_PROOF.md](./DEFINE_CHANGE_PROOF.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 CLI  sparkforge proof            MCP  sparkforge_proof (READ_ONLY)
            └──────────────┬──────────────┘
                           v
 adapters/_core.py  proof_change(findings_path, facts_path[], after_facts_path[], applied[])
   - _load_findings_file(findings)            -> recomendacoes julgadas no antes
   - _merge_facts_files(facts)   -> judge(uniao, return_skipped)      -> VEREDICTOS
   - _merge_facts_files(after)   -> judge(depois, return_skipped)     -> RESOLUCAO
   - load_catalog(), build_runtime_context()  (as mesmas chamadas de root_cause)
                           │  dados ja lidos
                           v
 sparkforge/proof/  (modulo puro; nao importa adapters nem provider)
   axes.py        load_policy() le rules/catalog/proof_axes.yaml e valida a forma
   keys.py        stable_key(subject, policy) -> dict | None
   resolution.py  resolve(applied, after_findings, after_skipped, policy) -> obrigacao
   axis.py        axis_outcome(axis, policy, verdicts, facts, shared) -> obrigacao
   prove.py       prove(applied, findings, verdicts, union, after, policy) -> dict
                           │
                           v
 {results: [{rule_id, stable_key, obligations[], summary}], refused, unresolved, policy}
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `rules/catalog/proof_axes.yaml` | Politica versionada: fonte, medida, `improves_when`, `proxy`, `refuted_by` e `unlock` de cada um dos 23 eixos; chave estavel por tipo de subject; convencao do sinal do delta com a razao | YAML sem chave `rules:` (o loader so pega regra dessa chave) |
| `sparkforge/proof/axes.py` | Carrega a politica por `safe_catalog_file` e recusa forma invalida | `yaml`, stdlib |
| `sparkforge/proof/keys.py` | Chave estavel do subject | stdlib |
| `sparkforge/proof/resolution.py` | Desfecho da resolucao | stdlib |
| `sparkforge/proof/axis.py` | Desfecho de um eixo (funcval, bench, none) | stdlib |
| `sparkforge/proof/prove.py` | Monta o resultado por finding aplicado, `refused`, `unresolved`, `policy` | stdlib |
| `adapters/_core.py` | `proof_change`: le arquivos, roda o `judge` duas vezes | — |
| `adapters/cli.py`, `adapters/tools.py` | Verbo `proof` e tool `sparkforge_proof` | argparse |
| `agents/executors/sf-verifier.md` (+ espelhos) | Checagem 7 | — |

---

## Key Decisions

### Decision 1: a prova julga a uniao e o depois ela mesma

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** DEFINE A-006. Os veredictos `SF-FVAL-*` e `SF-BENCH-*` saem do `judge` sobre os facts de comparacao, e a resolucao precisa do `skipped`, que um arquivo de findings nao carrega.

**Choice:** o adapter roda `judge(fatos, regras, runtime, return_skipped=True)` duas vezes, com as mesmas chamadas de `root_cause` (`load_catalog`, `build_runtime_context`):
- sobre a uniao `--facts`, e dela so interessam os findings `SF-FVAL-*` e `SF-BENCH-*` (os veredictos);
- sobre `--after-facts`, e dele interessam os findings e o `skipped` das regras aplicadas.

`--findings` continua sendo a fonte das recomendacoes aplicadas (o que o operador leu e escolheu aplicar).

**Rationale:** nenhum veredicto ou resolucao depende de arquivo gerado por outra ferramenta; o que a prova le sao facts, como todo verbo de topo.

**Alternatives Rejected:**
1. Receber os veredictos em `--findings`: a prova confiaria num arquivo que pode ter sido julgado com outro catalogo.
2. `--after-findings`: sem `skipped`, "resolvida" e "muda por falta de artefato" ficam iguais.

**Consequences:**
- Dois julgamentos por chamada. Custo medido no build; o `judge` de um case e da ordem do que o `root_cause` ja faz.

---

### Decision 2: a politica mora em `rules/catalog/proof_axes.yaml`, e nao na regra

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** DEFINE A-001. `action.direction` e o sentido da ACAO: nas 26 regras com eixo de bench, 13 `replace`, 8 `add`, 4 `decrease`, 1 `remove`. Para que lado um eixo melhora nao esta em regra nenhuma.

**Choice:** um arquivo so, versionado (`policy_version: 1`), com tres blocos:

```yaml
policy_version: 1
stable_keys:
  source_location: [file, symbol]
  tf_resource: [symbol]
  stage: [symbol]
  table: [symbol]
  plan_node: [symbol]
  job_run: [job_name]          # sem job_name: resolucao inconclusive
delta_sign_convention:
  refutes_when: delta_pct >= 0
  reason: >
    Sem regra de veredito para o eixo, "nao melhorou" e qualquer delta que nao
    seja negativo. E convencao declarada, nao limiar medido (regra 11), e vale
    so onde nenhuma regra do catalogo julga o eixo.
axes:
  correctness.write_result: {source: funcval}
  correctness.read_result:  {source: funcval}
  runtime.wall_clock:
    source: bench
    measure: total_task_ms
    improves_when: decreases
    proxy: task_ms_nao_e_wall_clock
    refuted_by: [SF-BENCH-002]
  shuffle.spill_bytes:
    source: bench
    measure: total_spill_bytes
    improves_when: decreases
    refuted_by: [SF-BENCH-003]
  scan.bytes_read:
    source: bench
    measure: total_input_bytes
    improves_when: decreases
    confounded_by: [SF-BENCH-001]
  scan.task_count:
    source: bench
    measure: total_task_count
    improves_when: decreases
  dependency.delivered_artifacts:
    source: none
    unlock: "comparar o artefato entregue antes e depois (hoje nenhum extrator compara)"
  # ... os 23 eixos, cada um com fonte e, quando `none`, o `unlock`
```

**Rationale:** a politica e uma decisao do SparkForge sobre como ler medidas, nao um fato da regra; separada, ela e testavel contra o catalogo e contra `EMITTED_KINDS`.

**Alternatives Rejected:**
1. Campo novo em cada regra: 155 regras para editar e 26 direcoes para inventar regra a regra.
2. Inferir de `action.direction`: A-001 mediu que ela nao diz isso.

**Consequences:**
- Eixo novo em `moves` exige entrada no mapa, e o teste do mapa (G11) derruba o gate ate ela existir.

---

### Decision 3: precedencia do bench, e o eixo de leitura confundido

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** medido nas regras do catalogo:
- `SF-BENCH-001` dispara com `|total_input_bytes_delta_pct| > input_divergence_pct`, nos dois sentidos;
- `SF-BENCH-002` olha so `total_task_ms_delta_pct`;
- `SF-BENCH-003` exige tempo melhor e spill ou GC pior;
- `SF-BENCH-004` diz que os stages nao casaram;
- `different_input_volume` dispara `001` e `002` juntos.

Reduzir bytes lidos e exatamente o que as regras de `scan.bytes_read` recomendam, e isso tambem dispara o `SF-BENCH-001`. O benchmark nao distingue "a entrada mudou" de "a mudanca passou a ler menos".

**Choice:** para um eixo de fonte `bench`, na ordem, o primeiro que casa decide:
1. `SF-BENCH-004` nos veredictos -> `inconclusive` (`stages_nao_casados`).
2. `SF-BENCH-001` nos veredictos -> `inconclusive`; no eixo que o declara em `confounded_by` (`scan.bytes_read`) a razao e `volume_ou_leitura_indistinguiveis`, nos demais `volumes_de_entrada_diferentes`.
3. `bench.unresolved` com `measure` igual a medida do eixo, ou `<medida>_delta_pct` ausente em `bench.run_delta` -> `inconclusive` (com a `reason` do benchmark).
4. Uma regra de `refuted_by` do eixo nos veredictos -> `refuted`.
5. Sinal do `<medida>_delta_pct` contra `improves_when`, pela convencao declarada -> `refuted`; a favor -> `not_refuted`.
6. Mais de um finding em `--applied` -> passos 4 e 5 viram `inconclusive` (`attribution_shared`); 1 a 3 continuam valendo.
7. Sem `bench.analyzed` na uniao -> `unproven` (`unlock: sparkforge benchmark --before <facts> --after <facts>`).

**Rationale:** a comparacao invalida vence qualquer leitura de delta; a regra que ja julga o eixo vence a convencao; e o que o benchmark nao consegue separar sai dito.

**Alternatives Rejected:**
1. `SF-BENCH-001` como sucesso no eixo de leitura: ele tambem dispara quando so a entrada mudou, e a prova diria "melhorou" sobre um volume diferente.
2. Limiar proprio de melhoria: seria limiar sem regra.

**Consequences:**
- Toda mudanca de `scan.bytes_read` bem-sucedida o bastante para passar do `input_divergence_pct` sai `inconclusive`. A saida diz por que, e o `unlock` diz o que resolveria (medir a leitura com a mesma entrada).

---

### Decision 4: resolucao pelo `skipped` e pela chave estavel

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Context:** `skipped` traz `reason` `requires_facts`, `runtime_scope` ou `blocked_on`. So o primeiro quer dizer "faltou artefato". Os tipos de subject dos goldens sao seis: `source_location` (73), `job_run` (60), `table` (28), `stage` (28), `tf_resource` (25), `plan_node` (8).

**Choice:** para cada finding aplicado:
1. A chave estavel do subject pelo mapa; tipo sem chave, ou `job_run` sem `job_name` -> `inconclusive` (`subject_sem_chave_estavel`).
2. A regra em `skipped` do depois com `requires_facts` -> `unproven`, com `missing_kinds` e o modulo que os emite (`_modulo_por_kind`, o mesmo do `root_cause`).
3. Com `runtime_scope` -> `inconclusive` (`regra_fora_do_escopo_no_depois`); com `blocked_on` -> `inconclusive` (`regra_bloqueada`).
4. Um finding da mesma regra no depois com a mesma chave -> `refuted`, com o `fact_id` que o sustenta.
5. Senao -> `not_refuted`, com a sentinela do depois que prova que o extrator rodou.

**Rationale:** ausencia so e resolucao quando a regra podia disparar; a chave ignora o que muda sem que nada tenha sido resolvido.

**Alternatives Rejected:**
1. Comparar o subject inteiro: toda edicao de codigo moveria a linha e daria `not_refuted` falso.

**Consequences:**
- Renomear a funcao que contem o problema da `not_refuted` (a chave mudou). A saida devolve a chave usada, e o revisor ve.

---

### Decision 5: `--applied` seleciona por regra e, opcionalmente, por simbolo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Choice:** `--applied SF-PY-002` aplica todos os findings dessa regra em `--findings`; `--applied SF-PY-002:principal` so o de `symbol` igual. Regra sem finding correspondente -> `unresolved` (`applied_nao_encontrado`). `attribution_shared` conta findings selecionados, nao regras.

**Rationale:** o operador pensa em "apliquei a recomendacao X"; o sufixo resolve o caso de uma regra em varios lugares.

**Consequences:**
- Dois findings da mesma regra aplicados juntos ja sao `attribution_shared` no bench, e e o certo.

---

### Decision 6: superficie, dono e registros

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-12 |

**Choice:**
- CLI `sparkforge proof --findings F --facts U [--facts ...] --after-facts A [--after-facts ...] --applied R[:symbol] [--applied ...]`, com as flags de runtime do `judge` (`--glue`, `--spark` etc.).
- Tool `sparkforge_proof`: `_READ_ONLY`, declara `findings_path`, `facts_path` e `after_facts_path` (fica fora de `SEM_CAMINHO`; a contagem de tools com caminho vai de 84 para 85; o catalogo de 90 para 91).
- Dono `sf-verifier`, checagem 7; `parity.yaml` com "prove what an applied change did and did not break".
- Registros: lista literal, amostra real, formas de erro, contagem de caminhos, `NOVAS_DEPOIS_DO_GOLDEN`, `manifest.json`, `parity.yaml`, executor e espelhos, surface lock, claims por ids. O conjunto de escritoras nao muda.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `rules/catalog/proof_axes.yaml` | Create | Politica dos 23 eixos, chaves estaveis, convencao | (general) | None |
| 2 | `sparkforge/proof/{__init__,axes,keys}.py` | Create | Carga da politica e chave estavel | @agentspec:python:python-developer | 1 |
| 3 | `sparkforge/proof/{resolution,axis,prove}.py` | Create | Desfechos e montagem | @agentspec:python:python-developer | 2 |
| 4 | `tests/test_proof_policy.py` | Create | Teste do mapa (G11): 23 eixos, fontes em `EMITTED_KINDS`, regras citadas existem | @agentspec:test:test-generator | 1, 2 |
| 5 | `tests/test_proof_outcomes.py` | Create | Unidade: resolucao (5 ramos), eixo funcval (3), eixo bench (7 passos), chave estavel, `attribution_shared` | @agentspec:test:test-generator | 3 |
| 6 | `sparkforge/adapters/_core.py` | Modify | `proof_change` | (general) | 3 |
| 7 | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py` | Modify | Verbo e tool | (general) | 6 |
| 8 | `fixtures/proof/` + `tests/test_fixtures_golden_proof.py` | Create | Casos montados a partir de `pyspark/collect_unbounded`, `bench/*` e `funcval/*`, com `FIXTURES = ROOT / "fixtures" / "proof"` | @agentspec:test:test-generator | 6, 7 |
| 9 | Registros de teste (`test_adapters_tools`, `test_harness_authorization`, `test_fixtures_golden_mcp_parity`) | Modify | Tool nova | (general) | 7 |
| 10 | `parity.yaml`, `manifest.json`, `agents/executors/sf-verifier.md` + espelhos | Modify | Capacidade, chave `tools`, checagem 7 | (general) | 7 |
| 11 | `docs/change-proof.md`, `docs/superpowers/STATUS.md` | Create/Modify | Guia e distribuicao datada (61/43/51) | (general) | all |
| 12 | `docs/surface.lock.json`, `docs/claims.lock.json` + docs auditados | Modify (pelo gate) | Regra 26; claims por ids | (general) | all |
| 13 | `.claude/sdd/reports/BUILD_REPORT_CHANGE_PROOF.md` | Create | Relatorio | (general) | all |

**Total Files:** 13 entradas.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 2, 3 | Funcoes puras sobre dicts |
| @agentspec:test:test-generator | 4, 5, 8 | Pares por desfecho e golden |
| (general) | 1, 6, 7, 9–13 | Politica e registros deste repositorio |

**Agent Discovery:**
- Scanned: agentes do plugin agentspec e os da sessao.
- Como nas frentes anteriores, o build pode ser direto: cada passo depende de medida do anterior.

---

## Code Patterns

### Pattern 1: chave estavel

```python
from typing import Any


def stable_key(subject: dict[str, Any], stable_keys: dict[str, list[str]]) -> dict[str, Any] | None:
    tipo = str(subject.get("type") or "")
    campos = stable_keys.get(tipo)
    if not campos or any(subject.get(campo) in (None, "") for campo in campos):
        return None
    return {"type": tipo, **{campo: subject[campo] for campo in campos}}
```

### Pattern 2: resolucao

```python
def resolve(rule_id: str, key: dict | None, after_findings: list[dict], after_skipped: list[dict],
            stable_keys: dict, emitted_by: dict[str, str]) -> dict:
    if key is None:
        return {"kind": "resolution", "outcome": "inconclusive", "reason": "subject_sem_chave_estavel"}
    for item in after_skipped:
        if item.get("rule_id") != rule_id:
            continue
        if item.get("reason") == "requires_facts":
            faltam = list(item.get("missing") or [])
            return {"kind": "resolution", "outcome": "unproven", "missing_kinds": faltam,
                    "unlock": {kind: emitted_by.get(kind, "") for kind in faltam}}
        razao = {"runtime_scope": "regra_fora_do_escopo_no_depois"}.get(item.get("reason"), "regra_bloqueada")
        return {"kind": "resolution", "outcome": "inconclusive", "reason": razao}
    for finding in after_findings:
        if finding.get("rule_id") == rule_id and stable_key(finding["subject"], stable_keys) == key:
            return {"kind": "resolution", "outcome": "refuted", "evidence": list(finding.get("evidence") or [])}
    return {"kind": "resolution", "outcome": "not_refuted"}
```

### Pattern 3: eixo de bench (ordem da Decision 3)

```python
def bench_outcome(axis: str, spec: dict, verdicts: set[str], run_delta: dict | None,
                  unresolved_measures: set[str], shared: bool) -> dict:
    base = {"kind": "axis", "axis": axis, "source": "bench", **({"proxy": spec["proxy"]} if spec.get("proxy") else {})}
    if run_delta is None:
        return {**base, "outcome": "unproven", "unlock": "sparkforge benchmark --before <facts> --after <facts>"}
    if "SF-BENCH-004" in verdicts:
        return {**base, "outcome": "inconclusive", "reason": "stages_nao_casados"}
    if "SF-BENCH-001" in verdicts:
        razao = "volume_ou_leitura_indistinguiveis" if "SF-BENCH-001" in spec.get("confounded_by", []) else "volumes_de_entrada_diferentes"
        return {**base, "outcome": "inconclusive", "reason": razao}
    pct = run_delta.get(f"{spec['measure']}_delta_pct")
    if spec["measure"] in unresolved_measures or pct is None:
        return {**base, "outcome": "inconclusive", "reason": "medida_sem_delta"}
    if shared:
        return {**base, "outcome": "inconclusive", "reason": "attribution_shared", "delta_pct": pct}
    if verdicts & set(spec.get("refuted_by", [])):
        return {**base, "outcome": "refuted", "verdicts": sorted(verdicts & set(spec["refuted_by"])), "delta_pct": pct}
    return {**base, "outcome": "refuted" if pct >= 0 else "not_refuted", "delta_pct": pct}
```

---

## Data Flow

```text
1. adapter: le --findings; seleciona os aplicados (--applied)
   │
   ▼
2. judge(uniao) -> veredictos SF-FVAL/SF-BENCH ; bench.run_delta, bench.unresolved, funcval.analyzed da uniao
   │
   ▼
3. judge(depois, return_skipped) -> findings e skipped do depois
   │
   ▼
4. prove(): por finding aplicado -> resolucao + um eixo por item de action.moves
   │
   ▼
5. {results, refused: [proven, gain_estimate], unresolved, policy: {policy_version, convencao}}
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| `rules.engine.judge` | Chamada interna (duas) | N/A |
| `diagnosis.root_cause._modulo_por_kind` | Kind -> modulo que o emite | N/A |
| `rules/catalog/proof_axes.yaml` | Politica versionada, no wheel pelo `force-include` | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Policy | 23 eixos, fontes em `EMITTED_KINDS`, `refuted_by`/`confounded_by` existem, `unlock` nao vazio para `none` | `tests/test_proof_policy.py` | pytest | SC4, G11 |
| Unit | Resolucao (5 ramos), funcval (3), bench (7 passos na ordem), chave estavel (SC3), `attribution_shared` | `tests/test_proof_outcomes.py` | pytest | AT-001..AT-012 em nivel de funcao |
| Golden | Casos pela CLI sobre pares reais | `tests/test_fixtures_golden_proof.py` | pytest | SC1, SC2, SC5 |
| Contract | Tool com amostra real valida contra o schema; formas de erro | `tests/test_adapters_tools.py` | pytest | SC6, AT-013, AT-014 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `--after-facts` ausente | Exit 2 com a dica | No |
| `--applied` vazio | Exit 2 (a prova sem mudanca aplicada nao prova nada) | No |
| Regra de `--applied` sem finding | `unresolved` `applied_nao_encontrado`, exit 0 | No |
| `proof_axes.yaml` invalido | Exit 2 nomeando o campo | No |
| Eixo de `moves` sem entrada no mapa | Obrigacao `unproven` (`eixo_sem_politica`); o teste do mapa pega antes | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `policy_version` | int (YAML) | 1 | Versao da politica, devolvida na saida |
| `delta_sign_convention` | YAML | `delta_pct >= 0` refuta | Convencao declarada, com a razao |

---

## Security Considerations

- Leitura so; nenhuma escrita, nenhuma rede.
- Os tres parametros de caminho sao confinados pela cadeia de autorizacao.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Metrics | `summary` por finding com a contagem por desfecho |
| Tracing | O span de tool existente |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Itens 1, 2, 4 | Teste do mapa verde contra o catalogo real |
| B2 | Itens 3, 5 | Unidade verde |
| B3 | Itens 6, 7 | Tool com amostra real valida; AT-013/014 |
| B4 | Item 8 | Golden verde |
| B5 | Itens 9–12; registros rapidos, gates, suite por lotes | Tudo verde |
| B6 | Commit, push, PR; item 13 | CI verde |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | design-agent | Versao inicial. A-005 e A-006 decididas; `SF-BENCH-001` confunde o eixo de leitura (Decision 3); `skipped` por razao (Decision 4) |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_CHANGE_PROOF.md`
