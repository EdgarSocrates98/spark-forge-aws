# BRAINSTORM: Portas de CLI faltando

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CLI_PORTS |
| **Date** | 2026-09-14 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Primeira das três candidatas pedidas depois do §15: as portas de CLI que a escrita dos manuais `docs/guia/` (2026-09-13) mediu como faltando. Nenhum verbo lê `workload.yaml`; SF-WASTE não dispara pela CLI; `collect parquet-footer` é citado e não existe.

**Context Gathered:**
- `extract_workload_path(path, repo_root)` (`sparkforge/facts/workload.py:194`) só é chamado por teste e pelos planos em `docs/superpowers/plans/`. `capacity`, `finops` e `workload` só veem o SLA se `workload.declared` já estiver no arquivo de facts. Nenhum parser da CLI tem argumento para o YAML.
- `extract_utilization(facts, path)` (`sparkforge/facts/utilization.py:71`) só é chamado por `tests/test_facts_utilization.py`. Ele emite `glue.utilization.summary` (utilização p50, memória e disco p95, razão de skew do pior stage) ou `glue.utilization.unresolved` (`utilization_not_observed`). Os `input/facts.json` de `fixtures/waste/` já trazem `glue.metric` e `spark.stage.task_duration`.
- O `fuse` (`sparkforge/facts/fusion.py:537`) já deriva o diagnóstico de timeout só quando o pool tem kind de origem (`timeout_diagnosis.SOURCE_KINDS`). A utilização cabe no mesmo molde.
- `collect_parquet_footer(prefix, root, *, now, ...)` existe em `sparkforge/collect/parquet_footer.py`, com pyarrow opcional (`require_pyarrow`) e teste próprio (`tests/test_collect_parquet_footer.py`). Faltam a porta de CLI e a tool. `cli.py:312` e a descrição da tool em `tools.py:5398`/`5420` citam `collect parquet-footer`.
- O `scan` já mapeia o kind `parquet_footer` do manifesto para `analyze parquet-footer` (`sparkforge/scan/plan.py:40`).
- pyarrow 25.0.1 está instalado no ambiente de desenvolvimento.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/adapters/{_core,cli,tools}.py`, `sparkforge/facts/fusion.py`, `sparkforge/scan/plan.py` | Três portas sobre código que já existe; nenhum extrator novo |
| Relevant KB Domains | CLAUDE.md regras 13, 14 e 17 (utilização baixa não é capacidade sobrando) | O resumo não quantifica economia |
| IaC Patterns | N/A | Nada provisionado |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como organizar as três candidatas? | Três frentes em sequência, cada uma com SDD, PR e merge. Ordem: portas de CLI, `tune`, L3 | Esta é a primeira |
| 2 | No L3, quem abre o PR? | O pacote monta e o host abre | Registrado para a terceira frente |
| 3 | Quais lacunas entram? | `workload.yaml` na CLI, utilização no `fuse`, `collect parquet-footer` | Lacunas 1, 2 e 3 da memória |
| 4 | Como o `workload.yaml` chega ao `scan`? | Pelo nome, na raiz do repositório | Sem chute entre vários arquivos em monorepo |
| 5 | Por onde entra o resumo de utilização? | Derivado no `fuse` | `judge` depois de `fuse`, o `scan` e o MCP ganham SF-WASTE sem passo novo |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/workload/*/input/workload.yaml` | 2 | `declared_only`, `declared_source_not_observed` |
| Input files | `fixtures/waste/*/input/facts.json` | 5 | `glue.metric` de CloudWatch e `spark.stage.task_duration` |
| Output examples | `fixtures/waste/*/expected/findings.json` | 5 | SF-WASTE-001/002 esperados quando o resumo existe |
| Related code | `tests/test_collect_parquet_footer.py`, `tests/test_facts_utilization.py` | 2 | Coletor e extrator já testados por unidade |

**How samples will be used:**

- Golden de `analyze workload` sobre os dois `workload.yaml`.
- Golden de `fuse` + `judge` sobre os cinco casos de `fixtures/waste/`, provando SF-WASTE pela porta pública.
- Parquet gerado pelo pyarrow em `tmp_path` para o `collect`. Nenhum binário é commitado.

---

## Approaches Explored

### Approach A: Três portas sobre o que existe ⭐ Recommended

**Description:** `analyze workload` (verbo e tool READ_ONLY); derivação de utilização no `fuse`, guardada pela presença de `glue.metric`; `collect parquet-footer` (verbo e tool de coleta, com o artefato registrado no manifesto com o kind `parquet_footer`). O `scan` lê `workload.yaml` da raiz.

**Pros:**
- Nenhum extrator novo, e o código que já tem teste é reusado.
- SF-WASTE passa a disparar onde o operador já roda `fuse` e `scan`.

**Cons:**
- Mexer no `fuse` pode mover golden de fusion. Mitigação: a guarda pela presença de `glue.metric`, igual à do timeout.

**Why Recommended:** fecha as três lacunas com o menor código novo e segue o precedente medido do PR #58.

### Approach B: Verbos explícitos para tudo

**Description:** `analyze workload`, `analyze utilization` e `collect parquet-footer`, todos explícitos.

**Pros:** Cada passo fica visível na CLI.

**Cons:** Repete o defeito do timeout. O `judge` sozinho continua sem SF-WASTE, e o operador precisa lembrar de mais um passo.

### Approach C: As duas portas para a utilização

**Description:** Deriva no `fuse` e também expõe `analyze utilization`.

**Cons:** Duas portas para o mesmo fact, e uma superfície maior sem ganho.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-14 |
| **Reasoning** | Fecha as lacunas pelo caminho que o operador já usa, sem extrator novo |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | `analyze workload --path <yaml> [--out]` com tool READ_ONLY | Porta pública para o SLA declarado | Ler o YAML dentro de `capacity`/`finops` (cada verbo com seu argumento) |
| 2 | O `scan` roda o analyze de `workload.yaml` só na raiz, com a origem `nome` no plano | Um repositório com vários jobs pode ter vários arquivos | Qualquer profundidade (conflito de SLA sem aviso) |
| 3 | O `fuse` deriva o resumo de utilização só quando existe `glue.metric` no pool | Pool sem CloudWatch fica byte a byte igual, como no diagnóstico de timeout | Derivar sempre (sentinela nova em todo golden) |
| 4 | `collect parquet-footer --repo --prefix --max-files`, registrando o kind `parquet_footer` no manifesto com sha256 | O `scan` já mapeia esse kind | Artefato solto fora do manifesto |
| 5 | Tool de coleta na classe dos outros coletores (`CLOUD_MUTATION`, openWorld) | O prefixo pode ser S3 e o coletor grava localmente | READ_ONLY |
| 6 | pyarrow ausente vira erro que diz o `pip install` | O núcleo continua sem a dependência | Importar pyarrow no topo |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `collect` do Glue Data Catalog | É um coletor inteiro com boto3, e não uma porta que falta | Yes |
| Exit code 1 na recusa do `debate` | Muda contrato de CLI | Yes |
| Reproduzir a regra 29 do CLAUDE.md | Frente própria | Yes |
| `workload.yaml` em subpasta no `scan` | Decisão 2; o verbo explícito cobre o caso | Yes |
| Verbo `analyze utilization` | Approach B/C rejeitados | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura: três portas, 100 → 102 tools | ✅ | "Sim, segue" | No |
| Fluxo, erros e testes | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Três capacidades que o motor já tem só são alcançadas por teste: o SLA declarado em `workload.yaml`, o resumo de utilização que sustenta SF-WASTE-001/002 e a coleta do footer Parquet. O `--help` e a descrição da tool citam um comando que não existe.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador que dimensiona capacidade | Declara o SLA num YAML que nenhum verbo lê |
| FinOps | SF-WASTE nunca dispara pela CLI, pelo `scan` nem pelo MCP |
| Quem cuida de layout Parquet | O `--help` manda rodar um `collect` que não existe |

### Success Criteria (Draft)
- [ ] `analyze workload` sobre os dois `fixtures/workload/` emite os mesmos facts que `extract_workload_path`.
- [ ] `fuse` + `judge` sobre os cinco `fixtures/waste/` produzem os findings de `expected/findings.json`.
- [ ] Todo golden de fusion sem `glue.metric` fica byte a byte igual.
- [ ] `collect parquet-footer` sobre um Parquet local grava o artefato e a entrada do manifesto; o `scan` o analisa.
- [ ] Nenhum texto do repositório cita comando inexistente.
- [ ] 102 tools, registros em dia, suíte nos 9 lotes com zero falha.

### Constraints Identified
- Regra 13 e regra 17: o resumo não quantifica economia.
- pyarrow opcional; o núcleo sem a dependência.
- INV-009: nenhum parâmetro com `url` no nome (o S3 entra como `prefix`).

### Out of Scope (Confirmed)
- `collect` do Glue Catalog, exit code do `debate`, regra 29, `workload.yaml` em subpasta.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_CLI_PORTS.md`
