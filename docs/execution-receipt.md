# Execution Receipt

O recibo de uma execução do case (§14 de `prompt_new_evo.md`). Ele amarra num
arquivo só, por caminho e sha256, os artefatos que uma execução deixou
espalhados — o `case.yaml`, a união dos facts, os findings, o relatório
assinado, o blackboard, os ADRs, os debates, os spans de tool de um run e o host
que o transcript declara — e deixa qualquer um conferir depois se algum deles
mudou.

```bash
sparkforge receipt emit --repo . --facts facts/pyspark.json --facts facts/tf.json \
  --findings findings.json --report report.md --now 2026-09-12T00:00:00Z \
  --run-id "$SPARKFORGE_RUN_ID" --host-transcript ~/.claude/projects/<p>/<sessao>.jsonl \
  --provider anthropic
sparkforge receipt verify --repo . --receipt .sparkforge/receipts/<receipt_id>.json
```

As tools MCP são `sparkforge_receipt_emit` (`LOCAL_MUTATION`) e
`sparkforge_receipt_verify` (`READ_ONLY`). O executor `sf-synthesizer` emite o
recibo no fim da sessão, depois de `report_sign` e `telemetry_export`.

## O que o recibo prova, e o que ele recusa

Ele prova **correspondência** entre o recibo e os artefatos: o `receipt_id` é
`rcpt_` + sha256 do JSON canônico do recibo, e o `now` da emissão entra no hash.
A mesma entrada com o mesmo `now` produz o mesmo arquivo, byte a byte.

Ele **não** prova autoria. Não há chave, e qualquer um com os mesmos artefatos
produz o mesmo recibo — por isso `refused` traz sempre `authorship`
(`content_addressed_sem_chave`). Quem precisa de autoria assina o **arquivo**
fora do pacote, com a ferramenta de assinatura da organização (por exemplo,
`cosign attest-blob` num workflow do CI). O pacote não tem chave nenhuma e não
chama rede.

Ele também não prova o que cada tool recebeu ou devolveu: o span de tool guarda
nome, status, bytes e horários, e nenhum hash de entrada ou saída —
`refused: tool_io` (`span_sem_hash_de_io`). O conteúdo que importa já está
amarrado pelo sha256 dos arquivos de facts e de findings.

## O que ele carrega, e o que nunca carrega

| Parte | O que guarda |
|---|---|
| `case` | caminho, sha256 e `case_id` do `case.yaml` |
| `evidence` | caminho, sha256 e contagem de cada arquivo de facts; o digest dos ids da união |
| `judgment` | sha256 dos findings, `rule_ids`, `fact_ids`, `catalog_version`, `schema_version`; sha256 e assinatura declarada do report |
| `decision` | sha256 e contagem de cada arquivo do blackboard; ids das decisões; sha256 dos ADRs com `rollback_present`; sha256 dos arquivos de cada debate |
| `proof` | fact_ids `funcval.*` (testes) e `bench.*` (antes/depois) presentes na união — nenhuma comparação, nenhum ganho |
| `tools` | `run_id` e, por span, `span_id`, `name`, `status`, `outcome`, `payload_bytes`, `detail_level`, `start_time`, `end_time`; o span do próprio emit fica fora, em `excluded` |
| `host` | provider **declarado**, modelo, agente e versão do transcript, e o sha256 do transcript |
| `actions` | sempre `autonomy: L0`, `applied_changes: false` |

Nunca entra: valor de `measures`, `metadata_json` de span, caminho absoluto
(o transcript entra só pelo sha256, porque o caminho dele tem o usuário da
máquina) ou qualquer texto de fact. `.sparkforge/` pode ser commitado, e caso
real nunca entra em arquivo. Toda lacuna sai em `unresolved` com a razão:
`run_id_nao_declarado`, `transcript_ausente`, `provider_nao_declarado`,
`modelos_multiplos`, `sem_arbitragem`, `sem_prova_funcional`, `sem_benchmark`,
`adr_ausente`.

## Os estados do verify

A ordem é fixa: `version`, `integrity`, `case`, `evidence`, `judgment`,
`decision`, `proof`, `tools`, `host`.

| Estado | Quer dizer | Derruba `valid`? |
|---|---|---|
| `match` | o disco confere com o recibo | não |
| `diverged` | o arquivo mudou (ou o recibo foi editado, em `integrity`) | sim |
| `missing` | o arquivo declarado não existe mais — apagado não é adulterado | sim |
| `not_rechecked` | a fonte não está aqui: `traces.db` de outra máquina, transcript não informado | não, mas sai listado |
| `not_evaluable` | o recibo é de outra `receipt_version`, e a regra de normalização mudou | o status é `version_mismatch` |
| `not_declared` | a parte não foi declarada na emissão | não |

Os spans são reconferidos pelos `span_id` que o recibo listou. O run continua
ganhando spans depois da emissão — o próprio emit, os verifies —, e esses
aparecem em `spans_after_emit` sem entrar na comparação. Arquivos de texto são
hasheados com `\r\n` normalizado para `\n`, então um recibo emitido no Windows
confere no Linux.

`receipt verify` sai com código 1 quando o recibo não corresponde e 2 em erro de
uso (recibo ilegível, caminho fora do repo).

## Onde está provado

- `tests/test_receipt_build.py` e `tests/test_receipt_verify.py`: determinismo,
  CRLF, lacunas nomeadas, adulteração de cada parte, spans por `span_id`.
- `tests/test_fixtures_golden_receipt.py` e `fixtures/receipt/uniao_debate/`: o
  recibo da união das duas fixtures do único par de conflito do catálogo (63
  facts), montado pelas portas do produto e comparado byte a byte; nenhum texto
  de fact vaza para o recibo.
