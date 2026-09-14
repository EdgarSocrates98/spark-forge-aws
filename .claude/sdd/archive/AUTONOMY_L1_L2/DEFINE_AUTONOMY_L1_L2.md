# DEFINE: Autonomia L1–L2

> Dois verbos novos: `change plan` (L1, produce change) e `change sandbox` (L2, sandbox execute). O primeiro produz o diff e o diff de rollback de um valor de configuração a partir da procedência dos facts, sem aplicar. O segundo aplica qualquer diff numa cópia isolada e compara os achados antes e depois, sem tocar a árvore do operador.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L1_L2 |
| **Date** | 2026-09-13 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O SparkForge só diagnostica (L0). O `tune` diz qual valor de `spark.sql.shuffle.partitions` a medida sustenta e de onde veio o valor atual (`terraform`, `code`), mas ninguém transforma isso numa mudança revisável com rollback. Um diff escrito pelo host não tem como ser conferido contra os achados sem aplicá-lo na árvore do operador. Por isso `applied_changes` sai fixo em `false` em todos os schemas e o §15 continua sem L1 e sem L2.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador de job Glue/Spark | Recebe a proposta do `tune` | Tem que achar arquivo e linha, editar à mão (no Terraform, dentro de uma string `--conf` com várias chaves) e escrever o rollback |
| Host/agente (Claude Code) | Escreve diffs de código e de configuração | Não consegue ver, sem aplicar na árvore, quais achados o diff resolve, cria ou mantém |
| Revisor de PR | Aprova mudança de configuração | Recebe a mudança sem rollback, sem a evidência que a sustenta e sem a diferença de achados |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `sparkforge change plan --facts <f>... --repo <r> (--from-tune \| --set chave=valor ...)` devolve `diff` unificado, `rollback_diff`, `changes[]` (chave, arquivo, linha, de, para, procedência, evidência) e `refused[]`. Não escreve nada, e o campo `stage` sai `produce_change` |
| **MUST** | O L1 localiza a mudança pela procedência: `tf.spark_conf` troca o par `chave=valor` dentro da string `--conf` da linha apontada, sem mexer nas outras chaves da mesma linha; `pyspark.conf_set` troca o literal do valor na chamada. Antes de trocar, confere que o valor atual do fact está naquela linha |
| **MUST** | Recusas nomeadas do L1, cada uma com a medida que a destravaria: `sem_procedencia_em_arquivo` (runtime, unset ou default), `linha_nao_confere` (o repo mudou desde a extração), `procedencia_ambigua` (a chave é pedida em mais de um lugar), `valor_nao_literal` e `valor_redigido` (fact com `redacted`) |
| **MUST** | `sparkforge change sandbox --repo <r> --diff <arquivo>` copia a árvore para `.sparkforge/sandbox/<id>/` com a varredura de `facts/scan.py`, roda `scan` na cópia pristina, aplica o diff com um aplicador estrito, roda `scan` de novo e devolve os achados `new`, `resolved` e `kept` por (`rule_id`, subject). O campo `stage` sai `sandbox_execute` |
| **MUST** | O relatório do sandbox traz as obrigações de prova (`validation` e `rollback` do catálogo) das regras em `new` e `resolved`, mais `next_steps` nomeados: o teste do operador, `benchmark` com dois runs e `funcval`. Não afirma ganho |
| **MUST** | O aplicador é estrito e confinado. Contexto que não bate vira `diff_nao_aplica`, com o hunk. `..`, caminho absoluto e symlink viram `caminho_fora_da_raiz`. Binário ou criação/remoção de arquivo vira `diff_nao_suportado`. Acima de 2 MB, `diff_grande_demais`. Arquivo que a cópia pulou (sensível, podado ou grande demais) vira `arquivo_fora_da_copia`. Em nenhum desses casos há aplicação parcial |
| **MUST** | Nenhum byte fora de `.sparkforge/sandbox/` muda. `sparkforge/change/` não usa `subprocess` nem git e não importa provider (regra 23) |
| **MUST** | Domínio golden `fixtures/change/` com repos sintéticos, `expected.json` e `.gitattributes` `-text` |
| **MUST** | Tools `sparkforge_change_plan` (READ_ONLY) e `sparkforge_change_sandbox` (LOCAL_MUTATION), com todos os registros de tool nova, surface lock, claims e a referência gerada em dia |
| **SHOULD** | `change plan --out <arquivo>` grava o `.patch` só quando pedido (só CLI) |
| **SHOULD** | `change sandbox --clean` apaga só `.sparkforge/sandbox/`, confinado por `resolve_within` |
| **SHOULD** | Manual `docs/guia/usos/change.md` escrito para leigo, com o fluxo `tune`, `change plan`, `change sandbox` e o que fazer depois |
| **COULD** | `autonomy show` passa a citar os verbos `change` e a divergência entre as duas escalas L1/L2 |

---

## Success Criteria

- [ ] SC1: `change plan` reproduz byte a byte o `diff` e o `rollback_diff` do `expected.json` em 100% dos casos de plano de `fixtures/change/`.
- [ ] SC2: ida e volta. Aplicar o `diff` e depois o `rollback_diff` com o próprio aplicador devolve os bytes originais (sha256 igual) em 100% dos casos com mudança.
- [ ] SC3: das 6 recusas do L1 (as 5 nomeadas mais `sem_procedencia_em_arquivo` por default explícito), cada uma aparece em pelo menos um golden, com `reason` e `detail` não vazio.
- [ ] SC4: no caso terraform com 4 chaves na mesma linha `--conf`, o diff muda exatamente 1 par `chave=valor` e mantém os outros 3 pares, a ordem deles e o resto da linha.
- [ ] SC5: `change sandbox` deixa o hash de todos os arquivos do repo fora de `.sparkforge/sandbox/` igual ao de antes da execução, em todos os casos de sandbox.
- [ ] SC6: as 5 recusas do aplicador saem por nome sem nenhum arquivo modificado na cópia; o teste compara os hashes da cópia antes e depois da tentativa.
- [ ] SC7: no caso "diff que resolve um achado", o `rule_id` aparece em `resolved`, as obrigações de prova da regra aparecem e `next_steps` não fica vazio.
- [ ] SC8: duas execuções de `change sandbox` com a mesma entrada devolvem o mesmo `<id>` e o mesmo relatório, byte a byte.
- [ ] SC9: `sparkforge/change/` sem `subprocess`, sem `git` e sem import de provider, conferido por teste.
- [ ] SC10: 100 tools (98 + 2), registros de tool nova, surface lock e claims em dia; suíte nos 9 lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Terraform, uma chave | repo com `main.tf` e `--conf spark.sql.shuffle.partitions=800 --conf ...` na mesma linha; facts com `tf.spark_conf` apontando a linha | `change plan --set spark.sql.shuffle.partitions=320` | diff troca só `=800` por `=320`; rollback faz o inverso; `changes[0].provenance = terraform` |
| AT-002 | Código | repo com `job.py` contendo `spark.conf.set("spark.sql.shuffle.partitions", "800")`; facts com `pyspark.conf_set` | `change plan --set ...=320` | diff troca o literal na linha 12; `provenance = code` |
| AT-003 | Do tune | facts de `valor_atual_vem_do_terraform` + shuffle medido | `change plan --from-tune` | usa `derived.value` do `tune`; `changes[0].basis` traz a fórmula e a base do `tune` |
| AT-004 | Sem procedência | chave só em `spark.conf_effective` (runtime) | `change plan --set` | `refused[0].reason = sem_procedencia_em_arquivo`; diff vazio |
| AT-005 | Linha não confere | repo editado depois da extração (a linha não contém mais `800`) | `change plan --set` | `linha_nao_confere` com arquivo e linha; diff vazio |
| AT-006 | Ambígua | a mesma chave em `main.tf` e em `job.py` | `change plan --set` | `procedencia_ambigua`, listando os dois lugares |
| AT-007 | Não literal | `spark.conf.set(K, n)` com variável | `change plan --set` | `valor_nao_literal` |
| AT-008 | Plano não escreve | qualquer caso de plano | `change plan` sem `--out` | nenhum arquivo criado ou alterado no repo |
| AT-009 | Sandbox resolve achado | repo que dispara uma regra; diff que tira a causa | `change sandbox --diff` | a regra em `resolved`, com obrigações de prova e `next_steps` |
| AT-010 | Diff não aplica | diff com contexto que não existe no arquivo | `change sandbox --diff` | `diff_nao_aplica` com o hunk; a cópia fica intacta |
| AT-011 | Escapa da raiz | diff com `+++ b/../fora.txt` ou caminho absoluto | `change sandbox --diff` | `caminho_fora_da_raiz`; nada gravado |
| AT-012 | Arquivo pulado pela cópia | diff que toca um `*.tfvars` ou algo em `vendor/` | `change sandbox --diff` | `arquivo_fora_da_copia` com a razão da varredura |
| AT-013 | Árvore principal intacta | qualquer caso de sandbox | hash de todos os arquivos fora de `.sparkforge/sandbox/` antes e depois | iguais |
| AT-014 | Idempotente | mesmo repo e mesmo diff | `change sandbox` duas vezes | mesmo `<id>` e mesmo relatório |
| AT-015 | Limpeza | sandbox existente | `change sandbox --clean` | `.sparkforge/sandbox/` removido; o resto intacto |

---

## Out of Scope

- L3 (abrir branch ou PR) e L4 (aplicar na árvore principal).
- Migration de dado, benchmark real, rodar Spark.
- Security scan externo (Snyk, Bandit) no sandbox.
- Mudança de código gerada pelo pacote (regra 23). O diff de código escrito pelo host passa pelo L2 normalmente.
- Comando arbitrário do operador no sandbox (pytest, spark-submit).
- Diff que cria, remove ou renomeia arquivo, ou que toca binário.
- Redefinir o enum `AutonomyLevel` ou os perfis de `sparkforge/agentic/autonomy.py`.
- Chaves além das que têm procedência em arquivo (`tf.spark_conf`, `pyspark.conf_set`). O `tune` deriva hoje só `spark.sql.shuffle.partitions`.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 23: nada chama provider | O L1 só troca VALOR literal; código gerado é do host |
| Technical | Regra 13: não estimar ganho | O sandbox compara achados e nomeia a medição que falta, nunca ganho |
| Technical | Regra 20: recusa tem nome | Toda recusa com `reason` e `detail` que diga a medida que destrava |
| Technical | Regra 26: tool nova move o surface lock | Crescimento declarado no commit |
| Technical | INV-007/INV-009 | Nenhum parâmetro de tool chamado command/cmd/shell/exec/script/argv nem com `url` no nome (o diff entra como `diff_path`) |
| Technical | Tool FAILABLE: a mensagem de erro contém "sparkforge" | Recusas de entrada inválida seguem o padrão |
| Technical | Glob cru proibido em `sparkforge/`; confinamento por `resolve_within` | A cópia usa `varrer_source_files`; a limpeza usa `resolve_within` |
| Technical | Domínio novo exige a linha literal `FIXTURES = ROOT / "fixtures" / "change"` | Golden em `tests/test_fixtures_golden_change.py` |
| Technical | CI Windows com `core.autocrlf=true` | `.gitattributes` com `fixtures/change/** -text`; aplicador e diff com LF fixo |
| Legal | Repo público | Fixtures sintéticas, sem nada de empresa |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/change/` (novo: `plan`, `apply`, `sandbox`); `sparkforge/adapters/{_core,cli,tools}.py`; `fixtures/change/`; `tests/test_change_*.py`, `tests/test_fixtures_golden_change.py`; `docs/guia/usos/change.md` | O módulo não importa `adapters`; `_core` compõe `tune_conf` e `scan` |
| **KB Domains** | Nenhum domínio do KB do agentspec. Fontes internas: regras 11/13/18/19/20/23 do CLAUDE.md, `sparkforge/tuning/spark_conf.py` (procedência), `sparkforge/facts/scan.py` (varredura), `rules/catalog/*` (`validation`/`rollback`) | O design consulta estas |
| **IaC Impact** | None | O diff edita `.tf` como texto; nada é provisionado nem roda `terraform` |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `tf.spark_conf.subject.line` é a linha do atributo `--conf`, e várias chaves dividem a mesma linha | O L1 trocaria a linha errada ou a linha inteira | [x] medido: `fixtures/terraform/spark_conf_in_arguments` tem 4 `tf.spark_conf` na linha 21 |
| A-002 | `pyspark.conf_set.subject.line` é a linha onde está o literal do valor | Num builder encadeado em várias linhas, a linha pode ser o início da cadeia, e o L1 sairia `linha_nao_confere` | [ ] conferir `_subject(node)` no design; a recusa protege caso a suposição caia |
| A-003 | `.sparkforge` está em `DIRETORIOS_IGNORADOS`, e o `scan` do repo principal não desce nas cópias | Os facts das cópias se duplicariam no scan principal | [x] medido: `sparkforge/facts/scan.py:184` |
| A-004 | A cópia por `varrer_source_files` pula `vendor/`, `build/`, `dist/`, `target/`, diretórios e nomes sensíveis e `.py` acima de 1 MiB, e entrega a lista `pulos` | Diff sobre esses arquivos não teria o que aplicar | [x] medido: listas em `facts/scan.py`; vira a recusa `arquivo_fora_da_copia` |
| A-005 | `_core.scan` roda duas vezes em processo, sobre raízes diferentes, sem estado global que vaze de uma para a outra | Os achados de "antes" contaminariam os de "depois" | [ ] conferir no design (ledger, cache de catálogo, codeintel) |
| A-006 | O `tune` deriva hoje só `spark.sql.shuffle.partitions` | `--from-tune` gera no máximo 1 mudança | [x] medido: `build_conf_advice` só acrescenta uma propriedade |
| A-007 | Quando a mesma chave é pedida em código e em Terraform, o código vence (`_procedencia`) | Editar só o Terraform não mudaria o valor efetivo | [x] medido: `tuning/spark_conf.py:154`; por isso a recusa `procedencia_ambigua` |
| A-008 | Comparar achados pela chave (`rule_id`, subject) é estável entre as duas execuções do `scan` | Um achado mantido apareceria como resolvido mais novo | [ ] o `simulate` já compara por chave estável; conferir se reusa |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | `applied_changes` fixo em false; o §15 sem L1 e sem L2; a dor do `tune` sem mudança revisável |
| Users | 3 | Três personas com dor nomeada |
| Goals | 3 | MoSCoW com os dois verbos, as recusas e o confinamento |
| Success | 3 | Dez critérios com número ou hash conferível |
| Scope | 2 | A-002, A-005 e A-008 abertos para o design |
| **Total** | **14/15** | |

---

## Open Questions

- A-002 (linha do `pyspark.conf_set` num builder em várias linhas), A-005 (estado entre dois `scan` no mesmo processo) e A-008 (chave estável de achado, possível reuso do `simulate`): resolver no design, medindo.
- Formato do `<id>` (quantos hex do sha256) e se o relatório também é gravado em `.sparkforge/sandbox/<id>/report.json`: fica para o design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | define-agent | Versão inicial a partir de BRAINSTORM_AUTONOMY_L1_L2.md. Medido: linha do `--conf` compartilhada, poda de `.sparkforge`, `tune` com uma propriedade, código vence Terraform. Recusas acrescentadas: `valor_redigido` e `arquivo_fora_da_copia` |
| 1.1 | 2026-09-14 | ship-agent | Shipped and archived (PR #65, CI verde) |

---

## Next Step

**Shipped:** `.claude/sdd/archive/AUTONOMY_L1_L2/SHIPPED_2026-09-14.md`
