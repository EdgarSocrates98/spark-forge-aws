---
name: sf-open
description: Abre um case SparkForge novo, detectando o runtime primeiro e parando se houver divergência (SF-ENV-001).
---

Você vai abrir um novo case de investigação SparkForge no repositório atual.

## Passo 1 — detectar o runtime antes de qualquer outra coisa

Rode primeiro:

```
sparkforge runtime detect --glue <versao-glue> [--spark <v>] [--python <v>] [--iceberg <v>] [--athena <v>]
```

Preencha `--glue` (e as demais flags que você conseguir confirmar) a partir do que
encontrar no Terraform, no `requirements.txt`/`pyproject.toml` do job, ou no que o
usuário informar. Nunca invente uma versão.

Se `divergences` no resultado não estiver vazio, **pare aqui**. Isso é
equivalente à regra `SF-ENV-001`: fontes diferentes reportaram versões diferentes
do runtime, e nenhuma recomendação de limiar ou API é segura até a divergência
ser resolvida. Explique a divergência ao usuário e peça para ele confirmar qual
fonte é confiável antes de prosseguir.

## Passo 2 — abrir o case

Só depois do runtime confirmado (sem divergência):

```
sparkforge case open --repo <raiz-do-repo> --case-id <id> --now <timestamp-ISO-8601> --glue <versao-glue> [--spark <v>] [--iceberg <v>]
```

`--now` é obrigatório e precisa ser um timestamp real (a CLI nunca lê o relógio
sozinha) — use a hora atual no formato ISO 8601, ex.: `2026-07-30T14:00:00Z`.

O case fica em `.sparkforge/case.yaml`, em fase `intake`. Depois de abrir, use
`/sf-next` para saber o próximo passo.
