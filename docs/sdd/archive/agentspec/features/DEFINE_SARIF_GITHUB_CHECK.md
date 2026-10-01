# DEFINE: SARIF + GitHub Check

> Um verbo `sparkforge report github` que projeta os findings ja julgados em SARIF 2.1.0 (Code Scanning), num resumo Markdown e em anotacoes de workflow para o PR, com recusa nomeada para todo finding sem linha no repositorio, sem rede e sem provider.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SARIF_GITHUB_CHECK |
| **Date** | 2026-09-11 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Os findings do SparkForge existem so como JSON e texto de CLI. Quem abre ou revisa um PR de job PySpark ou de Terraform nao os ve onde trabalha: nem na linha do diff, nem na aba Security, nem no status do PR. E nao ha como bloquear o merge por severidade sem integrar a API do GitHub a mao.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Engenheiro de dados | Abre o PR do job ou do Terraform | So descobre o P0 se alguem rodar a CLI e ler o `findings.json` |
| Revisor do PR | Revisa o diff | Nao ve o finding na linha que esta revisando |
| Dono da plataforma de dados | Mantem o CI do repositorio de dados | Nao tem gate por severidade que deixe o check vermelho sem escrever integracao propria |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: `sparkforge report github --findings F --facts X [--facts Y...] --repo . [--fail-on P0\|P1] [--category <nome>]` compoe sobre findings e facts, sem ler artefato |
| **MUST** | G2: SARIF 2.1.0 em `.sparkforge/report/sparkforge.sarif` (nome fixo, sob `--repo`) so com os findings localizados. Resolucao: `subject` com `file` e `line`; senao, o primeiro fact de `evidence` cujo `subject` tenha `file` e `line`; e o arquivo precisa existir sob `--repo` |
| **MUST** | G3: resumo Markdown em `.sparkforge/report/summary.md` com TODOS os findings. Os sem localizacao ficam numa secao propria, com o motivo (`runtime`, `arquivo_fora_do_repo`, `sem_linha`) |
| **MUST** | G4: nenhum finding some. Para toda entrada, SARIF + recusa = total de findings |
| **MUST** | G5: `tool.driver.rules` a partir dos proprios findings: `id`, `name`, `shortDescription` (titulo), `fullDescription` (explicacao), `help` (proposed_change, validation, rollback) e `helpUri` (primeira `sources[].url`); `level` por severidade (P0/P1 `error`, P2 `warning`, P3/P4 `note`); `precision` pelo `confidence`; sem `security-severity`; sem `partialFingerprints` |
| **MUST** | G6: nenhuma chamada de rede no pacote e nenhum caminho do argv usado para escrita |
| **SHOULD** | G7: `--fail-on P0\|P1`: exit 1 quando ha finding localizado ou nao daquela severidade ou pior; 0 caso contrario; 2 para erro de uso (convencao do repositorio) |
| **SHOULD** | G8: anotacoes `::error\|warning\|notice file=,line=,title=::` no stdout, uma por finding localizado, com os valores escapados |
| **SHOULD** | G9: tool MCP `sparkforge_report_github`, `READ_ONLY`, que devolve SARIF, resumo, contagens e recusas, sem gravar |
| **SHOULD** | G10: `docs/github-code-scanning.md` + `examples/github/sparkforge.yml` (analyze → judge → report github → `upload-sarif` + step summary) |
| **COULD** | G11: job do `ci.yml` so por `workflow_dispatch` que sobe o SARIF das fixtures (`category: sparkforge-fixtures`) e prova que o GitHub aceitou |

---

## Success Criteria

- [ ] SC1: todo SARIF gerado nos testes valida contra o `sarif-schema-2.1.0.json` da OASIS, versionado no repositorio com URL e sha256 de origem.
- [ ] SC2: **4** casos em `fixtures/sarif/` (PySpark, Terraform, so runtime, misto) batem byte a byte com os goldens `sparkforge.sarif`, `summary.md` e `annotations.txt`.
- [ ] SC3: sobre os findings de todos os `fixtures/**/expected/findings.json` (**222** hoje), a soma de resultados SARIF e de recusas e igual ao total, e **0** resultados SARIF tem arquivo inexistente ou linha ausente.
- [ ] SC4: `--fail-on P0` sai **1** com um P0 e **0** so com P1; `--fail-on P1` sai **1** com um P1; sem `--fail-on`, sai **0**.
- [ ] SC5: um valor de anotacao com `%`, `\r`, `\n`, `:` e `,` sai escapado conforme o `actions/toolkit` (A-003), e o teste cobre os cinco caracteres.
- [ ] SC6 (G11): um upload real por `workflow_dispatch` aparece em `gh api repos/{repo}/code-scanning/analyses` com `results_count` igual ao numero de resultados do SARIF enviado.
- [ ] SC7: `check_surface_lock.py --update` com o crescimento declarado; `check_vnext_claims.py`, `check_status_numbers.py --strict`, `check_evals.py` e `ruff` verdes; suite por lotes com **0** falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Finding PySpark com linha | Finding `source_location` com `file` e `line`, arquivo presente | `report github` | 1 resultado SARIF com `uri` relativo, `startLine` = `line`, `level` pela severidade; 1 anotacao |
| AT-002 | Finding Terraform | Finding `tf_resource` com `file` e `line` | `report github` | Resultado SARIF no `.tf`; `ruleId` = `rule_id` |
| AT-003 | Localizacao pela evidencia | Finding cujo `subject` nao tem linha, com um fact de `evidence` que tem `file` e `line` | `report github` | Resultado SARIF na linha do fact de evidencia |
| AT-004 | So runtime | Findings `job_run`/`stage` | `report github` | SARIF valido com `results: []`; resumo lista cada um em "sem localizacao no repositorio" com motivo `runtime` |
| AT-005 | Arquivo fora do repo | Finding `plan_node` com `file: plan.txt` inexistente sob `--repo` | `report github` | Fora do SARIF; recusa `arquivo_fora_do_repo` |
| AT-006 | Arquivo sem linha | `source_location` com `file` e sem `line`, e nenhuma evidencia com linha | `report github` | Fora do SARIF; recusa `sem_linha` |
| AT-007 | Gate | Um P0 e um P1 | `--fail-on P0` / `--fail-on P1` / sem flag | exit 1 / 1 / 0 |
| AT-008 | Gate so com P1 | So P1 | `--fail-on P0` | exit 0 |
| AT-009 | Escape | Titulo com `%`, `:`, `,` e mensagem com quebra de linha | `report github` | Anotacao com `%25`, `%3A`, `%2C`, `%0A`/`%0D` |
| AT-010 | Nenhum finding some | Todos os goldens de `fixtures/` | Projecao | SARIF + recusa = total, por fixture |
| AT-011 | Tool MCP | Mesmos findings e facts | `sparkforge_report_github` | Mesmo SARIF e mesmo resumo da CLI; nada gravado em disco |
| AT-012 | Entrada invalida | `--findings` inexistente, ou fact de evidencia ausente da uniao | `report github` | Exit 2 com mensagem acionavel; a evidencia ausente vira recusa `evidencia_ausente`, sem excecao |
| AT-013 | Upload real | Workflow manual no GitHub | `upload-sarif` | Analise aceita, com `results_count` igual ao do SARIF |

---

## Out of Scope

- `sparkforge scan .` (descobrir, extrair e julgar tudo de uma vez).
- Mostrar so os findings novos do PR: o proprio Code Scanning ja compara com a base.
- Checks API, check com nome proprio e PR Review Bot: exigem rede e token no pacote.
- `doctor`, TUI e GitHub Action publicada no Marketplace.
- `security-severity` e tag `security`.
- Localizar findings de `stage` pela ponte codigo-execucao (`spark.stage.callsite`). E o proximo passo natural, e fica fora.
- Mudar `Finding`, os schemas das tools existentes ou o catalogo.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 20: recusa tem nome | Todo finding fora do SARIF sai com motivo, nunca descartado |
| Technical | Regra 23 e perfil `offline-strict` | Nenhuma rede no pacote; o upload e do workflow |
| Technical | Regra 26 e os 7 registros manuais de tool nova | `surface.lock --update`, com o crescimento declarado no commit |
| Technical | Escrita so sob `--repo`, com nomes fixos | Nenhum `--out`; o scanner de seguranca nao acusa caminho vindo do argv |
| Technical | Limites do GitHub: 5 000 resultados exibidos por run, 10 MB compactado, 1 MiB por step summary | Acima deles, a saida recusa por nome (`limite_do_github`) em vez de truncar calada |
| Technical | Dominio novo em `fixtures/` exige modulo golden (`test_fixtures_kind_coverage.py`) | `tests/test_fixtures_golden_sarif.py` |
| Technical | O SARIF e deterministico: ordem estavel de regras e resultados, sem horario nem caminho absoluto | Golden byte a byte |
| Resource | Upload real consome uma analise na aba Security deste repositorio | So por `workflow_dispatch`, com `category` propria |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Projecao em modulo novo (`sparkforge/report/github.py` ou equivalente, a fixar no DESIGN); verbo em `adapters/_core.py` (ao lado de `report_sign` e `report_verify`), `adapters/cli.py` e `adapters/tools.py`; `fixtures/sarif/`; schema OASIS versionado; `docs/` e `examples/github/`; um job em `.github/workflows/ci.yml` | O modulo de projecao nao importa o adapter |
| **KB Domains** | CI/CD (GitHub Actions), testing (golden e validacao por JSON Schema), static analysis reporting (SARIF 2.1.0) | — |
| **IaC Impact** | Modify existing (`ci.yml`, um job manual) | Nenhum recurso de nuvem |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O `upload-sarif` aceita resultado com `region.startLine` e sem `startColumn` | Teriamos de emitir `startColumn: 1`, ou `col` quando o subject tiver | [ ] (SC6) |
| A-002 | Resultado com `uri` relativo a raiz do repositorio e mostrado na linha certa (confirmado na doc T1 de SARIF do GitHub) | — | [x] |
| A-003 | Escape dos comandos de workflow segundo o `actions/toolkit` (`command.ts`): dados `%`→`%25`, `\r`→`%0D`, `\n`→`%0A`; propriedades acrescentam `:`→`%3A` e `,`→`%2C`. A pagina T1 de workflow commands NAO documenta o escape | Anotacao quebrada ou truncada | [x] conferido no fonte T2 (`escapeData`/`escapeProperty` em `packages/core/src/command.ts`) |
| A-004 | O GitHub limita as anotacoes exibidas por step e por job, e o limite nao esta na pagina T1 | Anotacoes alem do limite somem da UI, mas o SARIF e o resumo continuam completos | [ ] |
| A-005 | O fact de evidencia com `file` e `line` aponta o mesmo arquivo do repositorio que o finding descreve | Localizacao errada; o DESIGN restringe a evidencia a subjects `source_location`/`tf_resource` | [ ] |
| A-006 | Caminho em `subject.file` e relativo a raiz do que foi analisado, que coincide com `--repo` no workflow de exemplo | Arquivo "fora do repo" falso; o DESIGN define a raiz de resolucao | [ ] |
| A-007 | O repositorio e publico, e o Code Scanning funciona sem GitHub Advanced Security pago | SC6 fica sem prova | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Onde o finding nao aparece, e para quem |
| Users | 3 | Tres papeis, cada um com a dor ligada a uma saida |
| Goals | 3 | MoSCoW com 11 metas, cada uma ligada a SC ou AT |
| Success | 3 | Contagens exatas (4 casos, 222 findings, 0 resultados sem arquivo, exit codes) |
| Scope | 2 | Escopo claro; a raiz de resolucao dos caminhos (A-006) e a forma da evidencia (A-005) ficam para o DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-003, A-005 e A-006 sao decididas no DESIGN; A-001, A-004 e A-007 sao respondidas pelo upload real (SC6).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | define-agent | Versao inicial, a partir de `BRAINSTORM_SARIF_GITHUB_CHECK.md` |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_SARIF_GITHUB_CHECK.md`
