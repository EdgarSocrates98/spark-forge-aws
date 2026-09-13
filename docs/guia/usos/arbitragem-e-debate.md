# Arbitragem e debate

Às vezes duas regras mandam fazer coisas opostas. No catálogo de hoje há um par
assim: `SF-GRAPH-005` manda **acrescentar** o JAR do GraphFrames nos argumentos do
job, e `SF-LF-001` manda **remover** JAR extra, porque o controle de acesso fino do
Lake Formation (FGAC) não o aceita. Este manual mostra como o SparkForge registra
esse conflito, o que ele decide e o que ele se recusa a decidir.

## Receita rápida

Rode da raiz do repositório. Os arquivos são fixtures sintéticas.

1. Prepare uma pasta de teste e aponte os dois conjuntos de facts:

   ```bash
   DEMO=/tmp/sf-arb && mkdir -p "$DEMO"
   A=fixtures/graph/import_sem_jar_no_iac/expected
   B=fixtures/infra_code/fgac_com_jar_extra/expected
   ```

2. Julgue a **união** dos facts:

   ```bash
   sparkforge judge --facts $A/facts.json --facts $B/facts.json --out "$DEMO/findings.json"
   ```

3. Arbitre sobre os mesmos insumos. Este comando grava no blackboard:

   ```bash
   sparkforge arbitrate --findings "$DEMO/findings.json" --facts $A/facts.json --facts $B/facts.json --repo "$DEMO"
   ```

4. Veja o resumo do que foi gravado:

   ```bash
   sparkforge blackboard summary --repo "$DEMO"
   ```

5. Leia a contradição:

   ```bash
   sparkforge blackboard list --repo "$DEMO" --type contradictions
   ```

## Para que serve

- **`arbitrate`**: roda depois do `judge`. Transforma cada finding em uma *claim*
  (afirmação), cada fact de apoio em *evidence*, e detecta *contradictions*
  (duas ações opostas sobre o mesmo alvo). Também registra *unknowns* (lacunas) e,
  quando não consegue decidir, um plano de debate.
- **`debate`**: conduz esse plano em rodadas, lado A contra lado B, com regras
  fixas. Quem escreve os argumentos é você ou o seu agente, nunca o SparkForge.

**Quando usar:** quando o `judge` mostra `contradictions` no bloco `plan`, ou quando
você quer um registro auditável das decisões do case.

**Quando não usar:** para achados que não conflitam. Aí basta o `judge`.

## Pré-requisitos

- Facts e findings de um `judge` (veja [Investigação com case](investigacao-com-case.md)).
- Uma pasta de case. `arbitrate` grava em `<repo>/.sparkforge/blackboard/`.
- Para o debate: um case aberto **com** o bloco `budget:` declarado (passo 4).

## Passo a passo, com saída real

### 1. Julgar a união

Por que a união? A contradição só aparece quando os dois jobs estão juntos. Cada
fixture tem seu `expected/findings.json`, mas o `arbitrate` precisa dos findings que
o `judge` produziu **sobre o mesmo conjunto de facts** que ele vai receber.

Trecho real do `judge` (passo 2 da receita):

```json
{
  "total_count": 2,
  "by_severity": {"P0": 1, "P1": 1},
  "plan": {
    "order": ["SF-LF-001", "SF-GRAPH-005"],
    "contradictions": [
      {"rules": ["SF-GRAPH-005", "SF-LF-001"], "target": "glue.default_arguments", "directions": ["add", "remove"]}
    ],
    "unresolved": [{"question": "lakeformation.unresolved: que medida fecha a lacuna do fact f_4d32fe?", ...}],
    "persisted": false,
    "note": "calculado, nao gravado. O registro auditavel e `sparkforge arbitrate`."
  },
  ...
}
```

### 2. Arbitrar

Trecho real do `arbitrate` (passo 3 da receita):

```json
{
  "kind": "executor.run",
  "autonomy": {"level": "L0", "applied_changes": false, ...},
  "claims": [
    {"id": "claim_deac5a64", "claimant": "SF-LF-001", "confidence": "medium", "evidence_refs": ["f_55f5ac", "f_6ab9b2"]},
    {"id": "claim_d9232d56", "claimant": "SF-GRAPH-005", "confidence": "high", "evidence_refs": ["f_32bc0d", "f_e231b7", "f_d9303b", "f_ae7d17", "f_ebc474"]}
  ],
  "contradictions": [{"id": "ctr_825ea97b", "rules": ["SF-GRAPH-005", "SF-LF-001"], "target": "glue.default_arguments", "resolution": null}],
  "debate_plans": [{
    "rules": ["SF-GRAPH-005", "SF-LF-001"],
    "recommendation": "experiment",
    "plan": {
      "participants": [{"agent": "pyspark-code-reviewer", ...}, {"agent": "sf-lake-formation-specialist", ...}],
      "budget": {"status": "unresolved", "reason": "o case.yaml nao declara o bloco `budget:`. ..."},
      "executed": false,
      "unresolved": {"reason": "debate.unresolved", ...}
    }
  }],
  "persistence": {"written": {"claims": 2, "evidences": 5, "contradictions": 1, "unknowns": 1, "traces": 1}}
}
```

Medido em 2026-09-13 com estas fixtures: 2 claims, 5 evidências, 1 contradição e
1 lacuna gravadas.

- `applied_changes: false`: nada foi mudado no job. O nível de autonomia é **L0**
  (só determinístico).
- `executed: false` e `debate.unresolved`: o conflito continua aberto. Plano não é
  resolução.
- `--facts` é repetível **e deve** receber a mesma união que o `judge` recebeu.
  Passar só metade fabrica claims sem âncora.

### 3. Ler o blackboard

O **blackboard** é o registro do case, em arquivos `.jsonl` dentro de
`.sparkforge/blackboard/`.

```bash
sparkforge blackboard summary --repo "$DEMO"
```

```json
{
  "claims": 2, "evidence": 5, "hypotheses": 0, "objections": 0, "rebuttals": 0,
  "contradictions": 1, "experiments": 0, "decisions": 0, "unknowns": 1,
  "open_unknowns": 1, "open_hypotheses": 0, "unresolved_contradictions": 1
}
```

Para ver um tipo: `sparkforge blackboard list --repo "$DEMO" --type <tipo>`. Os tipos
são `claims`, `evidence`, `hypotheses`, `objections`, `rebuttals`, `contradictions`,
`experiments`, `decisions` e `unknowns`. A lacuna real deste exemplo:

```json
{"id": "unk_c1b596af", "status": "open",
 "question": "lakeformation.unresolved: que medida fecha a lacuna do fact f_4d32fe?",
 "resolution_method": "coletar os grants do Lake Formation sobre a tabela alvo, a policy do runtime role e o registro da localizacao S3 -- nenhum dos tres entra em artefato que este motor colete hoje"}
```

### 4. Budget: o teto do debate

O debate exige um teto declarado no case. Sem ele, nada começa.

```bash
sparkforge case open --repo "$DEMO" --case-id demo-conflito --now 2026-09-13T13:00:00Z --glue 5.0
sparkforge budget show --repo "$DEMO"
```

```json
{
  "case_id": "demo-conflito",
  "limits": {"status": "unresolved", "reason": "case.yaml nao declara o bloco `budget:`. ..."},
  "consumption": {
    "status": "unresolved",
    "tokens": "tokens_unresolved -- exige transcript do host (regra 24)",
    "cost_usd": "unresolved -- exige cost_basis nomeado (regra 25)"
  }
}
```

`budget show --template` mostra os valores padrão do código, rotulados como
`"kind": "template"`. Eles **não** são o budget do case.

Declare o teto com o dono da investigação e acrescente ao fim do
`.sparkforge/case.yaml`:

```yaml
budget:
  max_debates: 1
  max_rounds: 3
```

Agora `budget show` responde `"status": "declared"`.

### 5. Debate: start, next, submit

```bash
sparkforge debate start --rules SF-GRAPH-005,SF-LF-001 --findings "$DEMO/findings.json" \
  --facts $A/facts.json --facts $B/facts.json --repo "$DEMO"
```

Sem o bloco `budget:`, a resposta é:

```json
{"status": "refused", "reason": "budget_undeclared", "detail": "o case.yaml nao declara o bloco `budget:`. ..."}
```

Com o bloco:

```json
{"status": "started", "debate_id": "dbt_ea104601", "created": true,
 "rules": ["SF-GRAPH-005", "SF-LF-001"], "max_rounds": 3, "state_dir": ".sparkforge/debate/dbt_ea104601"}
```

O lado A defende a primeira regra, o lado B a segunda. `next` diz de quem é a vez e
entrega o **brief**: o que o lado defende, o que ele contesta, os `fact_id` que ele
pode citar e o formato da submissão (`submission_schema`).

```bash
sparkforge debate next --repo "$DEMO" --debate dbt_ea104601
```

```json
{"status": "brief", "debate_id": "dbt_ea104601",
 "brief": {"side": "A", "round": 1, "max_rounds": 3,
           "defends": {"rule_id": "SF-GRAPH-005", "action": {"direction": "add", "target": "glue.default_arguments"}, ...},
           "opposes": {"rule_id": "SF-LF-001", ...}, ...}}
```

Uma submissão é um arquivo JSON. Exemplo para o lado A, rodada 1 (`sub_a1.json`):

```json
{"side": "A", "round": 1, "claims": [{"claim_type": "inference",
  "statement": "o job importa GraphFrames e o IaC nao entrega o JAR da biblioteca",
  "evidence_refs": ["f_32bc0d", "f_d9303b"], "confidence": "high"}]}
```

```bash
sparkforge debate submit --repo "$DEMO" --debate dbt_ea104601 --file sub_a1.json
```

Recusas reais, sempre com nome e sem gravar nada:

| Situação | `reason` |
|---|---|
| lado B enviou na vez do A | `out_of_turn` |
| submissão depois do fechamento | `debate_closed` |
| debate sem teto declarado | `budget_undeclared` |

Neste exemplo, A e B enviaram uma claim cada, sem objeção. A rodada terminou sem
objeção nova, então o debate fechou por consenso (`closed_by: consensus`):

```json
{"status": "done", "outcome": "unresolved", "winner_rule": null, "closed_by": "consensus",
 "candidate": {"outcome": "unresolved", "reason": "nenhum lado concedeu"},
 "referee": {"upheld": true, "violation_count": 0},
 "decision": {"id": "dec_074f1c3d", "selected_option": "unresolved: nenhuma das duas acoes e escolhida",
              "rollback": "nada a desfazer: nenhuma acao foi escolhida nem aplicada (autonomia L0); a contradicao continua aberta"},
 "autonomy": {"applied_changes": false, "level": "L0"}}
```

Só existe vencedor quando **exatamente um** lado concede (`"concede": true`) e o
árbitro aceita. Nunca por contagem de argumentos.

### 6. Árbitro e decisões

```bash
sparkforge debate referee --repo "$DEMO"
sparkforge decisions list --repo "$DEMO"
sparkforge decisions explain --repo "$DEMO" --id dec_074f1c3d
```

O `referee` recusa quatro coisas: hipótese que sobrevive ao fechamento, claim sem
`evidence_refs`, objeção sem réplica e referência pendurada. `upheld` é sim ou não,
nunca uma nota. Trecho real:

```json
{"upheld": true, "violation_count": 0,
 "protocol": [..., {"stage": "VERIFICATION", "observed_in": "not_modeled", "modeled": false}],
 "refused": [
   {"what": "generate_debate", "why": "Gerar claim, objecao e replica exige provider, e nada em `sparkforge/` chama provider (regra 23 do CLAUDE.md). ..."},
   {"what": "verification_stage", ...},
   {"what": "confidence_score", ...}
 ],
 "closed": true, "decision_count": 1}
```

`VERIFICATION` sai `modeled: false`: consenso é acordo, não verificação.

### 7. Níveis de autonomia

```bash
sparkforge autonomy show --level L0
```

```json
{"level": "L0", "name": "Deterministic", "description": "Extração e julgamento determinístico. Sem LLM.",
 "allowed_actions": ["extract_facts", "judge_rules", "validate_output"],
 "forbidden_actions": ["spawn_agent", "debate", "experiment", "modify_code"], ...}
```

Os níveis vão de `L0` a `L5`. `L3` ("Debate") permite `debate` e proíbe `experiment`,
`deploy` e `destructive_action`. `arbitrate` e o debate deste pacote rodam em L0: eles
gravam decisão e **nunca** aplicam mudança.

## O que o pacote NÃO faz

- **Não gera argumento e não chama modelo nenhum.** O código de `sparkforge/` não
  chama provider de IA (regra 23). Quem escreve as submissões é o host: a skill
  [`run-debate`](../referencia/skills/run-debate.md) numa sessão, ou
  `scripts/run_debate.py`, que roda `claude -p` **fora** do pacote. O placar dessas
  execuções sai de `python -m sparkforge.evals debate --run <nome>`.
- **Não estima ganho** e **não publica score** como confiança medida. Os pesos
  internos da arbitragem são convenção, sem calibração.
- **Não aplica mudança.** `applied_changes` é sempre `false`. O ADR (registro de
  decisão) é proposta, com rollback obrigatório.
- **Não afirma que a camada agêntica é melhor** que o fluxo sem ela (regra 30). Não
  existe benchmark que compare os dois lados sobre o mesmo caso bem posto.
- **Alcance medido: um par.** Hoje só `SF-GRAPH-005` × `SF-LF-001` produz contradição
  direta, e só na união de dois jobs (regra 29).

## Como ler o resultado

- `debate.unresolved`, `outcome: unresolved`, `status: unresolved`: o SparkForge está
  dizendo o que **não** decidiu, e por quê. Isso é qualidade, não falha.
- `status: refused` com `reason`: recusa com nome. Note que `debate start` e
  `debate submit` devolvem a recusa em JSON com código de saída 0. Leia o `status`.
- `open_unknowns`: lacunas que só uma coleta nova fecha. O `resolution_method` diz qual.

## Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `budget show` diz `case ausente ou invalido` | pasta sem case | rode `case open --repo <pasta>` antes |
| `budget_undeclared` | `case.yaml` sem `budget:` | declare `max_debates` e `max_rounds` com o dono do case |
| claims sem âncora ou contradição que some | `--facts` com só parte da união | passe a mesma união que o `judge` recebeu |
| `autonomy show` com `unrecognized arguments: --repo` | `autonomy show` não aceita `--repo` | use só `--level` |
| `out_of_turn` | lado ou rodada errados | rode `debate next` e siga `side` e `round` do brief |

## Próximos passos

- [Mudanças com prova](mudancas-com-prova.md): o experimento que a arbitragem pede.
- [Lake Formation e acesso](lake-formation-e-acesso.md): a coleta que fecha a lacuna deste exemplo.
- [Agents e skills](../05-agents-e-skills.md): quem conduz o debate.
- Referência: [`arbitrate`](../referencia/cli/arbitrate.md), [`blackboard`](../referencia/cli/blackboard.md),
  [`decisions`](../referencia/cli/decisions.md), [`budget`](../referencia/cli/budget.md),
  [`autonomy`](../referencia/cli/autonomy.md), [`debate`](../referencia/cli/debate.md); tools
  [`sparkforge_arbitrate`](../referencia/tools/sparkforge_arbitrate.md),
  [`sparkforge_debate_start`](../referencia/tools/sparkforge_debate_start.md),
  [`sparkforge_debate_next`](../referencia/tools/sparkforge_debate_next.md),
  [`sparkforge_debate_submit`](../referencia/tools/sparkforge_debate_submit.md),
  [`sparkforge_debate_referee`](../referencia/tools/sparkforge_debate_referee.md).
