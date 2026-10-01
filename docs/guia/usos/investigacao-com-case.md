# Investigação com case

O **case** é a memória da investigação. É um arquivo, `.sparkforge/case.yaml`, que
guarda a fase, a versão do runtime, as skills usadas e as hipóteses. Com ele, você
para hoje no Claude Code e continua amanhã no Devin sem perder nada. Veja também
[Case](../01-conceitos.md#case) no glossário.

## Receita rápida

Rode da raiz do repositório. Use uma pasta temporária para testar.

1. Abra o case. `--now` é a data e hora atual, em ISO 8601 (a CLI nunca lê o relógio).

   ```bash
   DEMO=/tmp/sf-case && mkdir -p "$DEMO"
   sparkforge case open --repo "$DEMO" --case-id demo-lento --now 2026-09-13T10:00:00Z --glue 5.0
   ```

2. Pergunte o próximo passo:

   ```bash
   sparkforge next-step --repo "$DEMO"
   ```

3. Registre a skill que você usou:

   ```bash
   sparkforge case update --repo "$DEMO" --skill analyze-library-call-graph \
     --outcome "facts extraidos: laco com write" --now 2026-09-13T10:15:00Z
   ```

4. Registre uma hipótese com as três partes:

   ```bash
   sparkforge case update --repo "$DEMO" \
     --hypothesis "O write dentro do laco refaz a leitura a cada volta" \
     --prediction "Tirar o write do laco reduz o tempo de task somado do stage de leitura" \
     --experiment "sparkforge benchmark --before antes.json --after depois.json" \
     --now 2026-09-13T10:25:00Z
   ```

5. Antes de parar, grave o resumo para quem continuar:

   ```bash
   sparkforge handoff --repo "$DEMO"
   ```

## Para que serve

- Guardar o estado da investigação num arquivo pequeno, que pode ir para o git.
- Deixar a escolha do próximo passo com o `next-step`, e não com a opinião do modelo.
- Registrar hipóteses de forma testável e fechá-las sem apagar o que foi afirmado.

**Quando usar:** toda investigação que dura mais de uma sessão, ou que passa por mais
de uma pessoa ou ferramenta.

**Quando não usar:** uma pergunta rápida e isolada, como consultar uma regra
(`sparkforge rules lookup`). Aí não há o que lembrar.

## Pré-requisitos

- SparkForge instalado ([Instalação](../02-instalacao.md)).
- Uma pasta para o case. Nos exemplos, uma pasta temporária. Num projeto real, a raiz
  do repositório do job.

## Passo a passo, com saída real

### 1. Abrir o case

```bash
sparkforge case open --repo "$DEMO" --case-id demo-lento --now 2026-09-13T10:00:00Z --glue 5.0
```

```json
{
  "case_id": "demo-lento",
  "runtime": {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1", "detected_from": ["cli"], "divergences": []},
  "phase": "intake",
  "gates": {"baseline_captured": false, "dominant_bottleneck_identified": false, "functional_validation_defined": false, "flows_mapped": false},
  "strict_gates": false,
  ...
}
```

Você informou só `--glue 5.0`. Spark, Python e Iceberg foram derivados da matriz de
versões do Glue. `divergences` vazio quer dizer que as fontes concordam.

Abrir de novo por cima é recusado, com código de saída 2:

```text
ja existe um case em .../.sparkforge/case.yaml, e abrir por cima dele apagaria: fase `intake`.
  Para continuar a investigacao: `sparkforge case get --repo <raiz>` e `sparkforge case update ...`.
  Para recomecar do zero mesmo assim: acrescente `--reopen` ...
```

### 2. Ler o case

```bash
sparkforge case get --repo "$DEMO"
```

Devolve o mesmo conteúdo do `case.yaml`, em JSON.

### 3. Perguntar o próximo passo

```bash
sparkforge next-step --repo "$DEMO"
```

```json
{
  "phase": "intake",
  "recommended_skill": "analyze-library-call-graph",
  "reason": "ROUTE-002: Nenhum fact extraído. Mapear entrypoint e biblioteca antes de qualquer hipótese.",
  "collect_commands": ["sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json"],
  "recommended_agent": null
}
```

`collect_commands` traz o comando exato para o próximo passo. Vamos segui-lo com um
job de exemplo (fixture sintética):

```bash
sparkforge analyze pyspark --path fixtures/pyspark/action_in_loop/input/lib --out "$DEMO/.sparkforge/facts.json"
sparkforge judge --facts "$DEMO/.sparkforge/facts.json" --glue 5.0 --out "$DEMO/.sparkforge/findings.json"
```

O `judge` achou 1 finding: `SF-PY-004`, "Action ou write dentro de loop", P0.
Depois de ter findings, passe o arquivo ao `next-step` para ele casar as rotas:
`sparkforge next-step --repo "$DEMO" --findings "$DEMO/.sparkforge/findings.json"`.

### 4. Mudar de fase e registrar o que foi feito

As fases válidas são: `intake`, `inventory`, `facts`, `diagnosis`, `hypothesis`,
`experiment`, `validation` e `report`. Nome errado é recusado:

```text
fase desconhecida: 'triage' (esperado uma de: intake, inventory, facts, diagnosis, hypothesis, experiment, validation, report)
```

```bash
sparkforge case update --repo "$DEMO" --phase facts --now 2026-09-13T10:20:00Z
sparkforge case update --repo "$DEMO" --skill analyze-library-call-graph \
  --outcome "facts extraidos: laco com write" --now 2026-09-13T10:15:00Z
```

Trecho do case depois:

```json
"skills_used": [
  {"skill": "analyze-library-call-graph", "at": "2026-09-13T10:15:00Z", "outcome": "facts extraidos: laco com write"}
]
```

Quando um coordenador roda um executor (`sf-judge`, por exemplo), ele registra o nome
do executor no lugar do nome da skill, pelo mesmo `--skill`.

### 5. Hipótese: três partes obrigatórias

Uma **hipótese** é uma afirmação que um experimento pode derrubar. Ela precisa de:

- `--hypothesis`: a afirmação;
- `--prediction`: o que muda no número se ela for verdadeira;
- `--experiment`: como medir.

Faltando uma parte, a CLI recusa (código 2):

```text
hipotese exige as TRES partes: `--hypothesis`, `--prediction` e `--experiment`. ...
```

Com as três (comando do passo 4 da receita), o case ganha:

```json
[{"id": "h1", "statement": "O write dentro do laco refaz a leitura a cada volta",
  "prediction": "Tirar o write do laco reduz o tempo de task somado do stage de leitura",
  "experiment": "sparkforge benchmark --before antes.json --after depois.json",
  "status": "open"}]
```

### 6. Fechar a hipótese

Feche com o desfecho e com onde ler a prova. Os desfechos são `confirmed`, `refuted`
e `abandoned` (o experimento nunca rodou).

```bash
sparkforge case update --repo "$DEMO" --close-hypothesis h1 --hypothesis-outcome confirmed \
  --evidence "bench.run_delta f_64c631" --now 2026-09-13T11:00:00Z
```

```json
{"id": "h1", "statement": "O write dentro do laco refaz a leitura a cada volta",
 "status": "confirmed", "closed_at": "2026-09-13T11:00:00Z", "evidence": "bench.run_delta f_64c631", ...}
```

A frase original **não muda**. Fechar é acréscimo. Nunca reescreva a afirmação para
ela combinar com o resultado. O `f_64c631` do exemplo veio de um `benchmark` real (veja
[Mudanças com prova](mudancas-com-prova.md)).

### 7. Handoff e resume: parar e continuar

- `handoff` grava `.sparkforge/handoff.md` e imprime o resumo.
- `resume` devolve o resumo para quem vai continuar.

```bash
sparkforge handoff --repo "$DEMO" --findings "$DEMO/.sparkforge/findings.json"
sparkforge resume --repo "$DEMO" --findings "$DEMO/.sparkforge/findings.json"
```

Início real do `handoff.md`:

```markdown
## Onde parou

- case: demo-lento
- fase: facts
- criado em: 2026-09-13T10:00:00Z

## Runtime detectado
...
## Baseline

- baseline: ausente
```

O `resume` traz, entre outras, as chaves `top_findings`, `open_hypotheses`,
`unsatisfied_gates`, `gate_overrides`, `missing_artifacts`, `next_step`, `coverage`,
`journal` e `in_flight_source`.

#### O que estava rodando quando a sessão caiu

Todo verbo que muda estado (27 hoje: `case open`, `case update`, `scan`, `arbitrate`,
`debate start|next|submit`, `change sandbox|propose`, os `collect *`, `receipt emit`,
`report sign`, `funcval plan|compare`) grava em `.sparkforge/journal.jsonl` um
`started` antes de rodar e um `finished` depois. Isso vale pela CLI e pelo MCP. Os
argumentos entram como hash, e só uma lista fechada de chaves, como `rules`,
`fail_on` e `debate_id`, entra literal.

Quando a sessão cai no meio de um verbo, sobra um `started` sem `finished`. O
`resume` lê esse evento e preenche `in_flight` sozinho:

```json
"in_flight": "sparkforge_arbitrate (cli, seq 5) sem finished",
"in_flight_source": "journal"
```

- `in_flight_source: caller` quer dizer que o texto de `--in-flight` venceu. O journal
  continua no bloco `journal` ao lado.
- Um `started` sem `finished` quer dizer **caiu ou ainda roda**. Outro processo rodando
  agora tem a mesma cara.

Para conferir que ninguém apagou nem editou evento, rode:

```bash
sparkforge journal verify --repo "$DEMO"
```

A saída é `intact`, `torn_tail` (a última linha foi cortada por uma queda),
`absent` ou `broken` com o `broken_at`. O comando sai com código 1 só em `broken`.
A cadeia não percebe edição da **última** linha, porque nenhuma linha depois dela
guarda o hash dela. Quem protege a última linha é o commit.

Depois de uma queda, `case.yaml`, os arquivos do blackboard e os do debate continuam
legíveis. A gravação troca o arquivo inteiro de uma vez, e uma linha cortada no fim
de um JSONL vai para `<arquivo>.torn` antes do próximo append.

Ao retomar, siga esta ordem:

1. Rode `resume`.
2. Leia `coverage.unresolved`. Zero achados com pontos cegos não é "tudo limpo".
3. Leia `runtime.divergences`. Com divergência, nenhum limiar é confiável ainda.
4. Recolete cada item de `missing_artifacts` com o comando registrado no manifesto.
5. Deixe o `next-step` decidir a rota.

**O que vai para o git:** `case.yaml`, `facts.json`, `findings.json`, `handoff.md`,
`journal.jsonl` e `artifacts/manifest.json`, dentro de `.sparkforge/`. Os artefatos
brutos (event logs, planos) **não** vão, porque podem ter dado de negócio. Os `*.torn`
também não vão: são evidência local de uma queda, não estado do case.

## Gates estritos (`--strict-gates`)

Um **gate** é uma condição para passar de fase. Há quatro: `baseline_captured`,
`dominant_bottleneck_identified`, `functional_validation_defined` e `flows_mapped`.
Por padrão eles só avisam. Com `--strict-gates`, eles bloqueiam, e o rigor fica
gravado no case para quem retomar.

```bash
DEMO2=/tmp/sf-estrito && mkdir -p "$DEMO2"
sparkforge case open --repo "$DEMO2" --case-id demo-estrito --now 2026-09-13T12:00:00Z --glue 5.0 --strict-gates
sparkforge case update --repo "$DEMO2" --phase hypothesis --now 2026-09-13T12:01:00Z
```

Saída real (código 2), depois de passar por `inventory`, `facts` e `diagnosis`:

```text
transição para `hypothesis` bloqueada: este case foi aberto com rigor de gates (`strict_gates`), e 1 gate(s) sem a evidência que os satisfaz:
    ou, se o dado genuinamente não existe (job descontinuado, ambiente que sumiu): sparkforge case update --override-gate flows_mapped --reason '<por que não existe>'
O gate checa a PRESENÇA do kind, não o conteúdo do fact: ...
```

- **O que destrava:** passar em `case update --facts <arquivo>` o fact que prova o
  gate. Quem produz cada um está no bloco `gates` de `rules/catalog/routing.yaml`
  (por exemplo, `flows_mapped` vem de `sparkforge analyze call-graph`).
- **Marcar `--gate <nome> --gate-value true` não destrava** num case estrito.
- **Passar por cima** exige motivo. Sem `--reason`, é recusado:

  ```text
  override do gate 'baseline_captured' recusado: falta o motivo. ...
  ```

  Com motivo, fica gravado:

  ```bash
  sparkforge case update --repo "$DEMO2" --override-gate baseline_captured \
    --reason "job de demonstracao sem event log" --now 2026-09-13T12:05:00Z
  ```

  ```json
  [{"gate": "baseline_captured", "reason": "job de demonstracao sem event log", "at": "2026-09-13T12:05:00Z"}]
  ```

Gate verde prova que a análise **rodou**, não que ela cobriu tudo. Diga isso no
relatório.

## Como ler o resultado

- **Código de saída 2** com texto explicando é recusa, não quebra. O SparkForge diz o
  que faltou e o comando para resolver.
- **`recommended_agent: null`**: nenhuma rota de agent casou. Siga `recommended_skill`.
- **`baseline: ausente`**: não há medida de antes. Sem ela, nenhum ganho pode ser
  provado.
- **`unresolved`** (no `resume` e nos facts): o que o SparkForge não conseguiu ler.
  É ele dizendo o que não sabe, e isso é parte do resultado.

## Erros comuns

| Mensagem | Causa | Solução |
|---|---|---|
| `ja existe um case em ...` | `case open` por cima de um case | use `case get` e `case update`; só use `--reopen` para recomeçar de propósito |
| `fase desconhecida` | nome de fase errado | use uma das oito fases listadas |
| `hipotese exige as TRES partes` | faltou `--prediction` ou `--experiment` | passe as três juntas |
| `transição ... bloqueada` | case estrito sem a evidência do gate | rode o verbo produtor e passe `--facts`, ou use `--override-gate` com `--reason` |
| `Nenhum case em .../case.yaml` | comando que precisa de case numa pasta sem case | rode `case open` antes |

## Próximos passos

- [Agents e skills](../05-agents-e-skills.md): quem segue o `next-step`.
- [Mudanças com prova](mudancas-com-prova.md): produzir a evidência que fecha a hipótese.
- [Arbitragem e debate](arbitragem-e-debate.md): quando dois achados do case se contradizem.
- Referência: [`case`](../referencia/cli/case.md), [`next-step`](../referencia/cli/next-step.md),
  [`handoff`](../referencia/cli/handoff.md), [`resume`](../referencia/cli/resume.md),
  [`playbook`](../referencia/cli/playbook.md); tools
  [`sparkforge_case_open`](../referencia/tools/sparkforge_case_open.md),
  [`sparkforge_case_update`](../referencia/tools/sparkforge_case_update.md),
  [`sparkforge_resume`](../referencia/tools/sparkforge_resume.md).
