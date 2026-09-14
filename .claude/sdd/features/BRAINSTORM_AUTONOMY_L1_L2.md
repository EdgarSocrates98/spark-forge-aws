# BRAINSTORM: Autonomia L1–L2 (produzir mudança, executar em sandbox)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L1_L2 |
| **Date** | 2026-09-13 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** §15 de `prompt_new_evo.md` (linhas 721–785): autonomia em níveis — L0 Diagnose (ler, analisar, recomendar), **L1 Produce Change** (gerar diff, comandos, migration e rollback sem aplicar), **L2 Sandbox Execute** (branch/worktree, ambiente isolado, aplicar, testar, benchmark, security scan), L3 propor PR, L4 remediação guardada, L5.

**Context Gathered:**
- Hoje o pacote inteiro é L0: `applied_changes` sai fixo em `false` em `_ARBITRATE_SUCCESS_SCHEMA`, `_DEBATE_DONE_SCHEMA`, `_RECEIPT_EMIT_SCHEMA` e em `agentic/executor/debate_run.py`. Nenhum verbo produz um diff.
- `sparkforge/agentic/autonomy.py` já tem um enum `AutonomyLevel` L0..L5 com **outra semântica**: L1 = Specialist (análise de domínio único), L2 = Cooperative (vários agentes), e `modify_code` está em `forbidden_actions`. A CLI `autonomy show --level` o expõe, e `tests/test_agentic_infra.py` o trava.
- `_core.tune_conf(facts_path)` já deriva o valor de configuração com procedência por chave: `current{value, provenance, evidence[fact ids]}` e `derived{value, formula, basis}`.
- Os facts de procedência trazem arquivo e linha: `tf.spark_conf` com `subject {"file":"main.tf","line":30,"symbol":"job#spark.sql.shuffle.partitions"}` e `pyspark.conf_set` com `subject {"file":"job.py","line":12}`. Isso basta para um diff determinístico de VALOR.
- `sparkforge/simulate/patch.py` (`parse_sets`, `Mudanca(camada, chave, valor)`, sintaxe `camada:chave=valor`) age sobre facts, não sobre arquivos.
- `_core.scan(repo)` (§22) roda plano por manifesto, `analyze`, `fuse` e `judge` em processo e grava em `<repo>/.sparkforge/scan/`. Serve de "antes" e "depois" dentro da cópia.
- `sparkforge/facts/scan.py::varrer_source_files` já tem a varredura que pula `.git`, `.venv`, credenciais e diretórios de estado.
- Nenhum `subprocess.run(` em `sparkforge/` fora do hook da policy. O §16 declara `.sparkforge/policy.yaml` com LOCAL_MUTATION pré-aprovada.
- Catálogo: 155 regras com `action` {kind, target, direction, …}. `validation` e `rollback` são listas de prosa por regra, e são elas que viram obrigações de prova no relatório do sandbox.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/change/` (novo) + `_core.change_plan/change_sandbox` + CLI `change plan\|sandbox` + tools MCP | Um módulo puro, com borda fina em `_core` e adapters, como `policy/` e `scan/` |
| Relevant KB Domains | `knowledge/` de Spark conf (shuffle partitions, AQE), regras 11/18/19/20/23 do CLAUDE.md | Procedência (regra 19) decide QUAL arquivo mudar; recusa tem nome (regra 20) |
| IaC Patterns | Terraform como fonte de `tf.spark_conf` (fixture sintética) | O diff edita `main.tf` lido, nunca roda `terraform` |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual recorte do §15 entra? | **L1 config + L2 sandbox** | L1 gera diff e diff de rollback de VALOR de configuração (do `tune` ou de `--set`), sem aplicar. L2 aplica QUALQUER diff (do L1 ou do host) numa cópia isolada e compara achados |
| 2 | O que o sandbox executa depois de aplicar? | **Só verbos do SparkForge** | `scan` (analyze+fuse+judge) antes e depois, diferença de achados e obrigações de prova. Nenhum comando arbitrário; o teste do usuário vira próximo passo nomeado |
| 3 | Como o sandbox isola a mudança? | **Cópia em diretório temporário** | Cópia da árvore para `.sparkforge/sandbox/<id>/`, aplicada em Python, sem git. Inclui o que não foi commitado e funciona fora de repositório git |
| 4 | De onde vêm as amostras? | **Domínio novo `fixtures/change/`** | Repo sintético (main.tf, job.py) + facts + `expected.json` com diff, rollback e recusas |
| 5 | Qual abordagem? | **Módulo novo `sparkforge/change`** | `plan.py` puro + `sandbox.py` com aplicador estrito próprio |
| 6 | O que fica fora? | L3/L4, migration e benchmark real, security scan externo, mudança de código gerada | Ver YAGNI |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/tuning/*/input/facts.json` | 7 | Só facts, sem o arquivo que o diff edita. Base para os facts dos casos novos |
| Output examples | `fixtures/change/<caso>/expected.json` (novo) | ~8 | Diff, rollback, `changes[]`, `refused[]`, e para o sandbox os achados novos/resolvidos/mantidos |
| Ground truth | `fixtures/change/<caso>/input/repo/` (novo) | ~8 | Repo sintético; o golden prova ida-e-volta byte a byte |
| Related code | `sparkforge/adapters/_core.py::tune_conf`, `::scan`; `sparkforge/simulate/patch.py`; `sparkforge/facts/scan.py::varrer_source_files`; `sparkforge/policy/load.py` (`resolve_within`) | 5 | Padrões a reusar: procedência, varredura, confinamento de caminho |

**How samples will be used:**

- Golden por caso (`tests/test_fixtures_golden_change.py`), com a linha literal `FIXTURES = ROOT / "fixtures" / "change"`.
- Casos: valor em terraform; valor em código; `--from-tune`; sem procedência em arquivo; linha que não confere; diff do host que não aplica; diff que escapa da raiz; diff que resolve um achado.
- `.gitattributes` com `fixtures/change/** -text` (bytes presos por sha256 quebram com autocrlf no CI Windows — lição do §22).
- Fixtures sintéticas: repo público, nada de empresa.

---

## Approaches Explored

### Approach A: Módulo novo `sparkforge/change` ⭐ Recommended

**Description:** `change/plan.py` é puro: recebe facts e valores, acha arquivo e linha pela procedência (`tf.spark_conf`/`pyspark.conf_set`), confere que o valor atual do fact está naquela linha, troca só o literal e gera diff unificado e diff de rollback com `difflib`. `change/sandbox.py` copia a árvore, roda `scan` na cópia pristina, aplica o diff com um aplicador próprio estrito (contexto tem que bater), roda `scan` de novo e compara achados por (`rule_id`, subject).

**Pros:**
- Determinístico e sem provider (regra 23): o diff de valor sai do que `tune` já sustenta.
- Sem subprocess e sem git: o aplicador é Python, confinado à cópia.
- Separa as duas perguntas do §15: "qual mudança" (L1) e "o que ela muda nos achados" (L2).

**Cons:**
- Aplicador de diff próprio é código a manter (parser de hunk, contexto, CRLF).
- Só cobre VALOR de configuração literal; expressão e variável saem recusadas.

**Why Recommended:** reusa procedência, `tune`, `scan` e `resolve_within`, que já existem e têm teste; o que é novo é pequeno e testável ida-e-volta.

---

### Approach B: Estender `simulate`

**Description:** L1 vira "simulate com diff", reaproveitando `camada:chave=valor` de `simulate/patch.py`.

**Pros:**
- Menos código novo; sintaxe `--set` já conhecida.

**Cons:**
- `simulate` age sobre facts, não sobre arquivos; misturar as duas semânticas no mesmo verbo confunde o que é hipótese e o que é mudança.
- Não resolve o L2.

---

### Approach C: Diff só do host

**Description:** O pacote não gera diff; o L1 fica com o host (LLM), e o pacote só valida e roda o L2.

**Pros:**
- Escopo menor.

**Cons:**
- Perde o diff determinístico de configuração que `tune` já sustenta, e toda mudança passa a depender de modelo.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-13 |
| **Reasoning** | Módulo puro que reusa procedência, `tune` e `scan`; nenhum comando arbitrário e nenhum toque na árvore principal |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | L1 gera diff só de VALOR literal de configuração, achado pela procedência | `tf.spark_conf`/`pyspark.conf_set` trazem arquivo e linha; valor é o que `tune` sustenta | Gerar mudança de código (exige modelo — regra 23) |
| 2 | L1 confere que o valor atual do fact está na linha antes de trocar | O repo pode ter mudado desde a extração; trocar às cegas edita a linha errada | Confiar só no número da linha |
| 3 | Recusas nomeadas do L1: `sem_procedencia_em_arquivo`, `linha_nao_confere`, `procedencia_ambigua`, `valor_nao_literal` | Regra 20: toda recusa diz a medida que a destravaria | Pular a chave em silêncio |
| 4 | `change plan` não escreve; tool READ_ONLY com o diff no payload; `--out` na CLI grava o `.patch` só se pedido | L1 é "produzir, não aplicar" | Gravar diff sempre |
| 5 | Sandbox é cópia em `.sparkforge/sandbox/<id>/`, com a varredura que pula `.git`, `.venv`, credenciais e `.sparkforge` | Isola, inclui mudança não commitada, funciona sem git, e o pacote não chama binário | `git worktree` (ignora não commitado, exige git); branch no repo (mexe no checkout do operador) |
| 6 | Aplicador de diff próprio e estrito: contexto tem que bater, senão `diff_nao_aplica` com o hunk | Aplicação parcial ou fuzzy produz árvore que ninguém revisou | Chamar `patch`/`git apply` (subprocess) |
| 7 | Sandbox roda só verbos do SparkForge: `scan` antes e depois, diferença por (`rule_id`, subject) | Comando arbitrário no sandbox é execução não confiável; o teste do usuário é dele | Rodar pytest/spark-submit do usuário |
| 8 | Relatório traz achados novos, resolvidos e mantidos, obrigações de prova (`validation`/`rollback` das regras tocadas) e `next_steps` nomeados (teste do usuário, `benchmark` com dois runs, `funcval`) | Regra 13: não estimar ganho; a prova de desempenho exige run medido | Afirmar melhoria a partir da diferença de achados |
| 9 | Confinamento do diff: `..`, caminho absoluto e symlink recusados (`caminho_fora_da_raiz`); sem binário; teto de 2 MB (`diff_grande_demais`) | Diff do host é entrada não confiável | Aceitar qualquer caminho |
| 10 | `<id>` do sandbox = sha256 curto do diff + hash da árvore copiada; recriado a cada execução | Determinístico e idempotente | Timestamp ou uuid |
| 11 | Sandbox fica em disco para inspeção; `change sandbox --clean` apaga só `.sparkforge/sandbox/` com `resolve_within` | Operador precisa ver a cópia; limpeza confinada | Apagar ao terminar |
| 12 | NÃO reusar `AutonomyLevel`; os verbos saem com campo próprio `stage: produce_change \| sandbox_execute` | O enum existente significa Specialist/Cooperative e proíbe `modify_code`; renomear quebraria perfis e testes com outra semântica | Redefinir L1/L2 do enum |
| 13 | `applied_changes` segue `false` nos schemas existentes | Nada destes verbos aplica na árvore principal | Virar `true` no sandbox |
| 14 | `change sandbox` é LOCAL_MUTATION (grava em `.sparkforge/sandbox/`); a policy padrão do §16 já pré-aprova a classe | Classe honesta; sem regra nova de policy | READ_ONLY |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| L3 (abrir branch/PR) e L4 (remediação na árvore principal) | O L2 termina num relatório; o operador decide | Yes |
| Migration de dado e benchmark real | Sem Spark no pacote; desempenho só se mede com dois runs (`benchmark`/`gain`), que viram próximo passo nomeado | Yes |
| Security scan externo (Snyk, Bandit) no sandbox | O "security scan" do §15 fica com o `judge` (regras de segurança) e a policy do §16; ferramenta externa é subprocess | Yes |
| Mudança de código gerada pelo pacote (tirar UDF, trocar collect) | Exige modelo (regra 23). Diff de código escrito pelo host passa pelo L2 normalmente | No (no pacote) |
| Comandos arbitrários do usuário no sandbox | Execução não confiável; o teste do usuário é próximo passo nomeado | Yes |
| `git worktree`/branch como isolamento | Ver decisão 5 | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura e componentes (dois verbos, recusas do L1, sandbox em cópia, comparação de achados, `stage` separado do `AutonomyLevel`) | ✅ | "Sim, segue" | No |
| Fluxo, erros e testes (determinismo do diff e do `<id>`, limpeza, confinamento, recusas, golden e ida-e-volta, registros de tool nova) | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Hoje o SparkForge só diagnostica (L0): o `tune` diz qual valor a medida sustenta, mas ninguém produz a mudança revisável nem mostra o que ela muda nos achados sem tocar no repositório do operador.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador de job Glue/Spark | Tem o valor proposto do `tune` e precisa achar arquivo e linha, editar à mão e escrever o rollback |
| Host/agente (Claude Code) | Escreve um diff e não tem como ver, sem aplicar na árvore, quais achados ele resolve ou cria |
| Revisor de PR | Recebe mudança de configuração sem rollback nem diferença de achados |

### Success Criteria (Draft)
- [ ] `change plan` sobre cada golden de `fixtures/change/` gera diff e rollback byte a byte iguais ao `expected.json`.
- [ ] Ida-e-volta: aplicar o diff e depois o rollback devolve os bytes originais, em todos os casos.
- [ ] Toda chave sem base sai em `refused[]` com um dos nomes da decisão 3 e a medida que a destravaria.
- [ ] `change sandbox` nunca altera um byte fora de `.sparkforge/sandbox/` (teste compara hash da árvore antes e depois).
- [ ] Diff que não aplica, que escapa da raiz ou que passa do teto sai recusado por nome, sem aplicação parcial.
- [ ] O caso "diff que resolve um achado" mostra o `rule_id` em `resolved` e as obrigações de prova da regra.
- [ ] Nenhum `subprocess` e nenhum import de provider em `sparkforge/change/`.
- [ ] Registros de tool nova, surface lock, claims, referência gerada e manual `docs/guia/usos/change.md` em dia; suíte em lotes verde.

### Constraints Identified
- Regra 23: o pacote não chama modelo; diff de código é do host.
- Regra 13: não estimar ganho a partir da diferença de achados.
- Regra 20: recusa tem nome.
- Regra 26: tool nova move o surface lock, declarado no commit.
- INV-007/INV-009: nenhum parâmetro de tool chamado command/cmd/shell/exec/script/argv nem com `url` no nome.
- Mensagem de erro de tool FAILABLE contém "sparkforge".
- Glob cru proibido em `sparkforge/`; confinamento por `resolve_within`.
- Repo público: fixtures sintéticas.

### Out of Scope (Confirmed)
- L3 (PR) e L4 (aplicar na árvore principal).
- Migration de dado, benchmark real, security scan externo.
- Mudança de código gerada pelo pacote.
- Comandos arbitrários no sandbox.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 6 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_AUTONOMY_L1_L2.md`
