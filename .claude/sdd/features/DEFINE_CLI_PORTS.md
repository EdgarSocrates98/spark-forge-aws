# DEFINE: Portas de CLI faltando

> Três capacidades que o motor já tem, mas que hoje só teste alcança, ganham porta pública: o SLA declarado em `workload.yaml`, o resumo de utilização que sustenta SF-WASTE-001/002 e a coleta do footer Parquet.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CLI_PORTS |
| **Date** | 2026-09-14 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Três extratores têm golden e ficam de fora do caminho do operador:
- `extract_workload_path` só é chamado por teste, e nenhum verbo lê `workload.yaml`;
- `extract_utilization` só é chamado por teste, e por isso SF-WASTE-001/002 não disparam pelo `judge`, pelo `fuse`, pelo `scan` nem pelo MCP;
- `collect_parquet_footer` existe sem porta, e mesmo assim o `--help` de `analyze parquet-footer` e a descrição da tool mandam rodar `sparkforge collect parquet-footer`.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador que dimensiona capacidade | Usa `capacity`, `finops` e `workload` | Declara o SLA num YAML que nenhum verbo lê; precisa montar `workload.declared` à mão |
| FinOps | Procura desperdício | SF-WASTE nunca aparece fora do teste, mesmo com CloudWatch coletado |
| Quem cuida de layout Parquet | Segue o `--help` | O comando citado não existe |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `sparkforge analyze workload --path <workload.yaml> [--out]` emite `workload.declared`, `workload.declared_analyzed` e `workload.unresolved` pelo `extract_workload_path`, no molde de `analyze consumers` (paginação, `by_kind`, `unresolved`). Tool `sparkforge_analyze_workload` READ_ONLY |
| **MUST** | O `fuse` deriva `glue.utilization.summary` (ou `glue.utilization.unresolved`) quando o pool tem `glue.metric`, guardado como o diagnóstico de timeout. Pool sem `glue.metric` fica byte a byte igual |
| **MUST** | `sparkforge collect parquet-footer --repo R --prefix <dir local ou s3://> [--max-files N] --now T` chama `collect_parquet_footer`, registra o artefato no manifesto com o kind `parquet_footer` e sha256, e sai no mesmo formato dos outros `collect`. Tool `sparkforge_collect_parquet_footer`, na mesma classe e com as mesmas anotações dos outros coletores |
| **MUST** | Sem pyarrow, `collect parquet-footer` sai com erro de fronteira que contém `sparkforge` e o `pip install` que resolve |
| **MUST** | O `scan` roda `analyze workload` quando existe `workload.yaml` na raiz, com a origem `nome` no plano |
| **MUST** | Registros de tool nova, surface lock, claims e referência gerada em dia |
| **SHOULD** | Manuais: `custo-e-capacidade.md` (o SLA pela porta pública e SF-WASTE pelo `fuse`), `iceberg-e-parquet.md` (o `collect`) e `scan-e-doctor.md` (a linha do `workload.yaml`) |
| **SHOULD** | Memória `lacunas-achadas-pela-doc-guia` com as lacunas 1 a 3 fechadas |
| **COULD** | O `doctor` avisa quando há `glue.metric` sem `spark.stage.task_duration`, que deixa o skew sem medida |

---

## Success Criteria

- [ ] SC1: `analyze workload` sobre os dois `fixtures/workload/*/input/workload.yaml` devolve em `items` exatamente os facts de `expected/facts.json`.
- [ ] SC2: `fuse` seguido de `judge` sobre os cinco `fixtures/waste/*/input/facts.json` devolve os mesmos `rule_id` e subjects de `expected/findings.json`, sem o test harness chamar `extract_utilization`.
- [ ] SC3: todo golden que passa pelo `fuse` e não tem `glue.metric` fica byte a byte igual; a suíte dos goldens de fusion e do `scan` passa sem regravar nada.
- [ ] SC4: `collect parquet-footer` sobre um Parquet local gerado pelo pyarrow em `tmp_path` grava o artefato e uma entrada de manifesto com `kind: parquet_footer` e sha256 que o `collect verify` confere. Depois disso o `scan` lista esse artefato com a origem `manifesto`.
- [ ] SC5: com pyarrow indisponível (simulado), o `collect` sai com código 2 e a mensagem cita `pip install`.
- [ ] SC6: o `scan` de um repositório com `workload.yaml` na raiz tem uma entrada `analyze: workload, origin: nome`, e com `workload.yaml` numa subpasta não tem.
- [ ] SC7: 102 tools, e as que declaram caminho vão de 92 para 94. Registros em dia, suíte nos 9 lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | SLA pela CLI | `fixtures/workload/declared_only/input/workload.yaml` | `analyze workload --path ... --out f.json` | `f.json` contém `workload.declared` igual ao golden |
| AT-002 | YAML ausente | caminho inexistente | `analyze workload --path x.yaml` | erro de fronteira com o comando que resolve (o molde do `consumers`) |
| AT-003 | YAML malformado | arquivo com YAML inválido | `analyze workload` | `workload.unresolved` com `read_error` |
| AT-004 | SF-WASTE pelo fuse | `fixtures/waste/ocioso_por_skew/input/facts.json` | `fuse` e depois `judge` | SF-WASTE-002 no mesmo subject do golden |
| AT-005 | Folga medida | `fixtures/waste/folga_medida_sem_skew` | `fuse` + `judge` | SF-WASTE-001 |
| AT-006 | Sem CloudWatch | pool sem `glue.metric` | `fuse` | nenhum `glue.utilization.*` e saída igual à de hoje |
| AT-007 | Coleta local | Parquet gerado em `tmp_path` | `collect parquet-footer --repo R --prefix <dir> --now T` | artefato e entrada no manifesto; `collect verify` ok |
| AT-008 | Scan pega o footer | repo do AT-007 | `scan R --dry-run` | entrada `parquet-footer` com a origem `manifesto` |
| AT-009 | Sem pyarrow | `require_pyarrow` falhando | `collect parquet-footer` | código 2, mensagem com `pip install` |
| AT-010 | SLA no scan | repo com `workload.yaml` na raiz | `scan --dry-run` | entrada `workload` com a origem `nome`; em subpasta, nenhuma |
| AT-011 | Tools | catálogo | `len(TOOLS)` | 102 |

---

## Out of Scope

- `collect` do Glue Data Catalog.
- Exit code 1 na recusa do `debate`.
- Reproduzir a medida da regra 29 do CLAUDE.md.
- `workload.yaml` fora da raiz no `scan`.
- Verbo `analyze utilization`.
- Mudar a regra SF-WASTE ou o extrator de utilização.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regras 13 e 17: utilização baixa não é capacidade sobrando, e nada quantifica economia | O resumo sai como está; a regra decide |
| Technical | pyarrow opcional (`require_pyarrow`) | O import fica dentro do coletor; o núcleo segue sem a dependência |
| Technical | INV-009: nenhum parâmetro com `url` no nome | O S3 entra como `prefix` |
| Technical | `fuse` com asserção de namespace por módulo | Os kinds derivados saem de `utilization.EMITTED_KINDS` |
| Technical | Domínio golden novo exige a linha literal `FIXTURES = ...` | Se o `scan` ganhar um caso novo, ele fica em `fixtures/scan/` (domínio existente) |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/adapters/{_core,cli,tools}.py`, `sparkforge/facts/fusion.py`, `sparkforge/scan/plan.py`, `fixtures/scan/`, testes | Nenhum módulo novo |
| **KB Domains** | Nenhum domínio do KB do agentspec. Fontes internas: `facts/workload.py`, `facts/utilization.py`, `collect/parquet_footer.py`, `rules/catalog/waste.yaml` | |
| **IaC Impact** | None | |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Os goldens de `fixtures/waste` foram gerados a partir de `extract_utilization(input_facts)`, e o `fuse` não mexe no que o resumo lê | SC2 falharia | [ ] conferir no design rodando `run_fuse` sobre os inputs |
| A-002 | Nenhum golden que passa pelo `fuse` tem `glue.metric` fora de `fixtures/waste` | Goldens de fusion ou do `scan` mudariam | [x] medido: `glue.metric` só em 4 `input/facts.json` de `fixtures/waste` |
| A-003 | `collect_parquet_footer` já grava no manifesto com o kind `parquet_footer`, e o `scan` o mapeia | Precisaria registrar à mão | [x] medido: `parquet_footer.py:298-309`, `scan/plan.py:40` |
| A-004 | `analyze workload` com `repo_root` igual ao diretório pai do YAML reproduz o `anchor` do golden (`workload.yaml`) | SC1 divergiria no subject | [ ] conferir no design |
| A-005 | O `fuse` recebe o pool com `glue.metric` e `spark.stage.task_duration` juntos no caso de uso real (`analyze cloudwatch` + `analyze event-log`) | O skew ficaria sem medida | [x] é o que o `scan` e a união de `--facts` fazem |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Três lacunas medidas pela doc, com chamadores contados |
| Users | 3 | Três personas |
| Goals | 3 | MoSCoW por porta |
| Success | 3 | Sete critérios conferíveis por golden |
| Scope | 2 | A-001 e A-004 abertos |
| **Total** | **14/15** | |

---

## Open Questions

- A-001 e A-004: conferir no design rodando o código.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | define-agent | Versão inicial a partir de BRAINSTORM_CLI_PORTS.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_CLI_PORTS.md`
