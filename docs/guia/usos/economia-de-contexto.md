# Economia de contexto: medir o que cada chamada custa

Todo assistente de IA tem uma **janela de contexto**: o espaço limitado de texto
que ele consegue considerar de uma vez. Cada resposta de tool ocupa parte dela.
Este guia mostra como medir quanto o SparkForge colocou ali.

A regra de ouro: **meça antes de dizer que economizou.**

## Receita rápida

Da raiz do repositório:

```bash
mkdir -p /tmp/sf-guia && cp -r fixtures/pyspark/coalesce_one /tmp/sf-guia/job_exemplo
cd /tmp/sf-guia
export SPARKFORGE_RUN_ID=run_guia_demo
python -c "
from sparkforge.adapters.tools import call_tool
for nivel in ('full', 'normal', 'summary'):
    call_tool('sparkforge_analyze_pyspark', {'path': 'job_exemplo', 'detail_level': nivel, 'limit': 2})
"
sparkforge economy report --run-id run_guia_demo
```

1. Copia um exemplo sintético de job PySpark para uma pasta de teste.
2. Entra na pasta. As medições são gravadas em `.sparkforge/traces.db` da pasta
   **atual**.
3. `SPARKFORGE_RUN_ID` dá um nome ao **run** (a sua sessão de medição), para as
   chamadas caírem juntas.
4. Chama a mesma tool nos três níveis de `detail_level`.
5. `economy report` soma o que foi medido.

No PowerShell, o passo 3 é `$env:SPARKFORGE_RUN_ID = "run_guia_demo"`.

Saída real do passo 5, encurtada:

```json
{
 "run_id": "run_guia_demo",
 "by_tool": {
  "sparkforge_analyze_pyspark": {"calls": 3, "payload_bytes": 3529, "outcomes": {"ok": 3}}
 },
 "detail_level_effect": {
  "sparkforge_analyze_pyspark": {"full": 1382, "normal": 1290, "summary": 857}
 },
 "surface": { ... },
 "host_usage": null,
 "unresolved": [{"reason": "tokens_unresolved", "count": 1}]
}
```

Neste exemplo, feito em 2026-09-13 com `limit: 2` sobre `fixtures/pyspark/coalesce_one`,
`summary` pesou 857 bytes contra 1382 de `full`. Em outro corpus a diferença
muda, e pode ser quase nenhuma. Por isso se mede.

## Quando usar e quando não usar

Use quando for afirmar que algo "reduziu", "economizou" ou "pesa pouco". O
relatório dá o número.

Não use para estimar custo em dólar. O relatório mede bytes e não converte em
preço (ver [Byte, token e dólar](#byte-token-e-dólar-não-se-misturam)).

## Pré-requisitos

- O pacote instalado. Para medir chamadas do assistente, o [servidor MCP](../04-mcp.md).
- Chamadas feitas por `call_tool`. É por onde passam o servidor MCP e o exemplo
  em Python. Cada chamada vira um **span**: um registro com nome da tool,
  duração, bytes da resposta e desfecho.

## Passo a passo

### 1. Dê um nome ao run

Sem `SPARKFORGE_RUN_ID`, cada processo ganha um nome aleatório, e o relatório
não sabe juntar suas chamadas. No servidor MCP, ponha a variável no `env` da
configuração do servidor.

### 2. Faça as chamadas

Pelo assistente, via MCP, ou pelo `call_tool` em Python, como na receita. Os
spans ficam em memória e vão para `.sparkforge/traces.db` quando o processo
termina. Dentro do mesmo processo, o relatório já enxerga o que está em memória.

### 3. Leia o relatório

```bash
sparkforge economy report --run-id run_guia_demo
sparkforge economy report --run-id run_guia_demo --out relatorio.json
```

A tool equivalente é `sparkforge_economy_report`, com `run_id` e, opcionalmente,
`host_transcript`.

### 4. Acrescente o transcript do host, se tiver

O **host** é o programa que roda o assistente, como o Claude Code. Só ele sabe
quantos tokens o modelo gastou. Esse dado está no **transcript**, o arquivo JSONL
da sessão. Com um transcript sintético do repositório:

```bash
sparkforge economy report --run-id run_guia_demo --host-transcript <repo>/fixtures/otel/com_host/input/transcript.jsonl
```

Trecho real:

```json
{
 "host_usage": {
  "source": "claude_code_transcript",
  "input_tokens": 30,
  "output_tokens": 60,
  "cached_tokens": 300,
  "cache_creation_tokens": 15,
  "message_count": 3,
  "unresolved": []
 },
 "unresolved": []
}
```

## Como ler o resultado

| Campo | O que diz |
|---|---|
| `by_tool` | Por tool: quantas chamadas, quantos bytes de resposta, e quantas deram `ok`, `error` ou `unauthorized` |
| `detail_level_effect` | Os bytes de cada nível pedido. A chave vazia `""` é chamada sem `detail_level` |
| `surface` | O peso do que o assistente carrega **antes** de qualquer chamada: descrições das tools, skills e documentos de `knowledge/`, com a fórmula em `basis` |
| `host_usage` | Tokens do modelo, só com transcript |
| `unresolved` | O que o relatório não sabe, com nome |

As lacunas nomeadas são qualidade, e não falha:

- `run_unresolved`: não há span com esse `run_id`. O real, com um nome que não
  existe, sai com `by_tool` vazio e esse motivo. Somar spans de outra
  investigação seria pior que número nenhum.
- `tokens_unresolved`: não houve transcript, então não há token. O projeto não
  inventa um.

O relatório mostra os dois lados de `detail_level` e **não conclui por você**
(regra 28 do `CLAUDE.md`).

## Byte, token e dólar não se misturam

As regras 22 a 25 do [`CLAUDE.md`](../../../CLAUDE.md), em linguagem simples:

- **Byte** é o tamanho da resposta que o SparkForge produziu. É medido sempre
  (`payload_bytes`), pela fórmula
  `len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))`.
- **Token** é a unidade que o modelo cobra. Só o host sabe. Sem transcript, sai
  `tokens_unresolved`, e nunca uma conta como "bytes divididos por 4" vestida de
  token.
- **Byte e token nunca se somam.** Aparecem lado a lado, nunca num total comum.
- **Dólar exige `cost_basis`**, uma fonte de preço nomeada. Chamada de tool local
  não tem preço publicado.
- **O SparkForge não chama modelo nenhum** (regra 23). Quem gasta token é o host.

Quando algum lugar mostra `estimated_tokens` (por exemplo, `code context`), é
**estimativa declarada**, e nunca entra numa razão de economia.

Se a medição falhar (disco cheio, banco travado), a tool responde normalmente
(regra 27). Medir nunca derruba a chamada.

## `telemetry export`: ponte para o seu painel

Se o time já usa um backend de tracing (CloudWatch, Grafana, Datadog, Jaeger),
`telemetry export` converte os mesmos spans em arquivos **OTLP/JSON**, o formato
que um **OTLP Collector** lê. É só uma ponte: o SparkForge grava arquivo e não
envia nada pela rede.

```bash
sparkforge telemetry export --run-id run_guia_demo --repo .
```

Saída real, rodada na pasta de teste:

```json
{
  "run_id": "run_guia_demo",
  "files": [
    ".sparkforge/telemetry/run_guia_demo.metrics.jsonl",
    ".sparkforge/telemetry/run_guia_demo.traces.jsonl"
  ],
  "counts": {"sparkforge_spans": 6, "host_agent": 0, "host_tool_calls": 0, "exported": 6, "refused": 0},
  "refused": [],
  "unresolved": [],
  ...
}
```

Com `--host-transcript`, a sessão do host entra também. Com `--provider`
(`anthropic`, `aws.bedrock` ou `gcp.vertex_ai`), o provedor fica declarado e a
métrica de token sai. A tool `sparkforge_telemetry_export` devolve o mesmo
conteúdo, mas não grava arquivo. A configuração do Collector e a lista de
recusas estão em [`docs/opentelemetry.md`](../../opentelemetry.md).

## O surface lock

A **superfície** é o que o assistente carrega antes de fazer qualquer coisa:
descrição das tools, skills e documentos de `knowledge/`. Ela cresce quando
alguém acrescenta uma tool.

[`docs/surface.lock.json`](../../surface.lock.json) trava esse peso: bytes
totais, quantidade e um hash dos nomes, para `tools`, `skills` e `knowledge`.
Acrescentar tool é permitido, mas quem acrescenta tem de **dizer de quanto
cresceu**.

```bash
python scripts/check_surface_lock.py
```

Saída real hoje: `0 divergencia(s).`. Quem mantém o projeto e mudou a superfície
roda `python scripts/check_surface_lock.py --update` e declara o crescimento no
commit. Como usuário, você só precisa do comando de conferência.

## Compressão de saída (modo caveman)

O repositório traz o **caveman** em `vendor/`. Ele comprime o texto que o
assistente escreve: tira artigos, rodeios e cortesia, e mantém o conteúdo técnico.
O modo fica fixado em `full` em `.caveman/config.json`.

- **No Claude Code**, ativa sozinho. `/caveman lite`, `/caveman full` e
  `/caveman ultra` trocam o nível na sessão. `stop caveman` ou `normal mode`
  voltam ao texto normal.
- **Nos outros agentes** (Devin, Copilot, Codex), o agente aplica as regras de
  [`AGENTS.md`](../../../AGENTS.md), seção "Output compression — caveman mode".

O que a compressão **nunca** corta: o formato inteiro de `recommendation:` e
`Finding` (evidência, riscos, validação e rollback incluídos), números, versões,
`rule_id`, `fact_id`, mensagens de erro e blocos de código. Apagar evidência
para economizar é defeito, e não compressão. Mais detalhes em
[`GUIA_DE_USO.md`](../../../GUIA_DE_USO.md), seção 10.

## Erros comuns

| Sintoma | Causa | Como resolver |
|---|---|---|
| `by_tool` vazio e `run_unresolved` | O `run_id` não bate, ou você está em outra pasta | Use o mesmo `SPARKFORGE_RUN_ID` e rode na pasta onde as chamadas aconteceram |
| Chamadas pela CLI não aparecem | O registro é feito por `call_tool` (MCP ou Python) | Meça pelo servidor MCP ou por `call_tool` |
| `tokens_unresolved` | Não há transcript do host | Passe `--host-transcript`, se tiver. Senão, a lacuna é a resposta certa |
| Apareceu `.sparkforge/traces.db` no projeto | O processo que chamou as tools rodou na raiz do projeto | É o lugar esperado. Para testes, rode numa pasta temporária |
| `telemetry export` sem métrica de token | Faltou `--provider` ou transcript | Declare os dois |

## Próximos passos

- [Servidor MCP](../04-mcp.md), incluindo `detail_level` e paginação
- [Code intelligence](code-intelligence.md) e a honestidade das medidas de economia
- Referência: [`economy`](../referencia/cli/economy.md), [`telemetry`](../referencia/cli/telemetry.md), [`sparkforge_economy_report`](../referencia/tools/sparkforge_economy_report.md)
