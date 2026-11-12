# RELATÓRIO ONDA 4 — Spark Forge AWS SDD

Estado: **implementado e verificado** (276 testes SDD-scope verdes, ruff
limpo, surface lock 0 divergências). Data: sessão da onda 4/5/6.

## Por skill

| skill | preservado | adicionado |
|---|---|---|
| `sdd-explore` | explore opcional, alternativas múltiplas, trade-offs, aprovação do operador, proibição de implementação prematura, evidência, separação dev/operator, pergunta-uma-por-mensagem | `decisions.json` (`forge/DecisionTree/v1`-compatível: id/question/type/depends_on/status/alternatives+recommendation+rationale/evidence/answer/actor/impact/reopen_condition), modos sequencial/rodada/adaptativo/fronteiras, fatos investigáveis vs decisões humanas, contradições, risco de reversibilidade, histórico, retomada, confirmação final |
| `sdd-define` | hipótese/predição/experimento/acceptance/verified-by/success/unknowns/change-kinds/red gate | stories, `REQ-`/`NFR-` estáveis, cenários de aceite, checklist de qualidade, rastreabilidade REQ→decisão→task, source, constitution, change policy, análise de contradição, classificação crítica, validação de 8 defeitos |
| `sdd-design` | manifest, path validation, alternativas rejeitadas, rollback por decisão, cobertura, análise de dependências, citações de knowledge | ADR por risco, threat model, contratos de integração, data model, research, quickstart, impacto/compatibilidade, evolução de schema, concorrência, idempotência, recovery, consistência, fronteiras de transação; foco AWS (Glue/Catalog/Athena+UNLOAD/LakeFormation/cross-account/IAM/S3/EMR/StepFunctions/Iceberg/Delta/Parquet/SparkSQL/Terraform/Streaming); regra não-transferência-entre-runtimes |
| `sdd-plan` | tasks atômicas, testes nomeados, cobertura de critérios, dependência de design, comandos verificáveis, isolamento operador | task graph (`depends_on`, `parallel_safe`, `risk`, `write_scope`, `proof`, `blocking`, `decisions_needed`), critérios de paralelismo seguro (4 condições), priorização, checkpoints, retomada idempotente, política de ergonomia (6 papéis de conteúdo) |
| `sdd-build` | test-first, red/green, red gate, revisor separado, spec/quality review, sandbox operador, registro de evidência | `forge/TestExecutionReceipt` (baseline_sha, argv, exit_code, executor, per_test, artifact_sha256), revalidação pós-edição, checkpoint, retry seguro, recovery, detecção de conflito, reexecução idempotente, concorrência |
| `sdd-ship` | hypothesis_outcome, registros, evidência, desvios, gates, rollback, aprovação humana, merge/push protection, histórico | convergência semântica (9 artefatos comparados), classes de divergência (`missing|partial|contradicts|unrequested|unverified|stale`), verificação de fonte, cobertura de aceite, regressão, drift de requirement/test/plan, frescor de evidência, confirmação de decisões, `## Recibo`, feedback pós-entrega |

## Decisões de implementação

- **Novos campos no corpo, não no frontmatter**: os schemas de fase rejeitam
  chaves novas de frontmatter (`schema_invalid`). Árvore de decisões e
  receipts vivem como artefatos próprios (`decisions.json`,
  `receipt-*.json` + `.out`), referenciados pelo frontmatter existente.
- **`sdd converge`**: quarto verbo, read-only, emite
  `forge/ConvergenceReport/v1`; exit 1 com divergência, 2 com feature
  ausente. Nunca reescreve requirement — correção volta à fase dona.
- **Contrato da árvore**: local em `sparkforge_aws/sdd/decisions.py` e
  compatível com o federado `forge/DecisionTree/v1` (mesmos campos) —
  serve às ondas 4 e 5 sem duplicar schema.
- **Sem engine complexa**: grafo de decisões/tarefas = dict + DAG check;
  convergência = comparador por pares, sem motor de inferência.

## Testes e cobertura

- `tests/test_sdd_wave4.py`: 53 testes — decisões (DAG, contradictions,
  reopen), requirements (untestable/unapproved/dup/conflict), task graph
  (ciclo, ordem, paralelismo inseguro, cobertura REQ), receipts (tamper
  → `receipt_stale`, sintaxe não é prova TDD, inconclusivo), converge
  (todas as classes de divergência), domain SDD Glue/Iceberg
  (atomicidade…métricas funcionais), templates de regressão.
- `tests/test_sdd_operator_wave4.py`: 6 — sem `.git`, cópia manual,
  `.sparkforge_aws/sdd` independente de sandbox, runtime ausente
  (exit 127 → `receipt_inconclusive`), evidência all-skipped, green válido.
- Total SDD-scope: **276 verdes**; evals de skill: **161/161** offline,
  zero chamadas de provider/AWS (+39 casos novos de comportamento).
- `sparkforge_aws/sdd/`: `decisions.py`, `requirements.py`,
  `task_graph.py`, `receipts.py`, `converge.py`, `federated.py` novos.

## Compatibilidade

- Features `docs/sdd/<F>/` legadas: sem mudança obrigatória — artefatos
  novos são opt-in por frontmatter; gates novos emitem `unresolved` quando
  a informação não existe, não `refused` retroativo.
- `CONTRATO.md` atualizado: todo código novo de recusa/lacuna catalogado
  (o teste ast-enforced passa).
- Falha pré-existente não relacionada: `test_capability_parity` nos verbos
  `obsidian *` (trabalho in-flight separado, sem `parity.yaml`); SDD não
  está no gap.
- Unresolved esperado em repo real: `convergence_unverified` ×2
  (ACs command-verified que o gate não checa) — comportamento correto.

## Mapeamento Spec Kit / Grill Me

- Spec Kit: constitution (define), artifacts por fase, task graph (plan),
  ADRs/research/quickstart (design) — cobertos como artefatos, não como
  comandos novos (reuso > comando).
- Grill Me: modos de entrevista, uma-pergunta-por-mensagem, boundaries
  só para decisões independentes, contradições e recomendações
  registradas — cobertos em `sdd-explore` + `decisions.json`.

## Pendências conhecidas

- `test_skill_quality.py` atualizado p/ 161 casos (constante era 122).
- `docs/sdd/README.md` cita `sparkforge_sdd_*` sem `_aws` — drift
  pré-existente, não mexido.
EOF