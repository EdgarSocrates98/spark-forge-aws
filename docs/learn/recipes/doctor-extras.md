# Receita — minha instalação está completa?

**O quê:** `sparkforge-aws doctor` checa pacote, extras, CLI e ambiente com
`unlock` acionável por check.
**Por que:** "modulo ausente" tem remédio explícito, não stacktrace.
**Quando:** pós-install, troca de máquina, antes de collectors/skills.
**Quando não:** health de serviços AWS — doctor é local, offline.

## Problema

"Erro de import ao rodar um skill que usa parquet/boto3."

## Passo a passo

```bash
sparkforge-aws doctor --json
```

Saída real observada:

```json
{"id": "pacote",   "status": "ok",   "detail": "sparkforge-aws 0.5.0, Python 3.12.13"},
{"id": "extras",   "status": "warn", "detail": "modulos ausentes: boto3, pyarrow",
 "unlock": "pip install \"sparkforge-aws[aws,parquet]\""}
```

## Saída esperada / interpretação

`ok`/`warn`/`fail` por check; `warn` vem com `unlock` — o comando exato que
resolve. Nada é ambíguo.

## Verificação

Após o `unlock`, re-rodar `doctor` deve virar `ok` no check correspondente.

## Limitações

Doctor verifica o ambiente local — não valida credenciais AWS nem conecta
em endpoints (collectors fazem isso, com credencial).

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `extras: warn` | extras não instalados | rode o `unlock` mostrado |
| `cli: fail` | launcher fora do PATH | re-rodar setup/`pip install -e .` |

## Uso por agentes

Workflow `doctor` do `forge.agentic.json`; `--json` é máquina-first — um
agente lê `unlock` e propõe o remédio sem rodá-lo.
