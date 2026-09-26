# Scan e doctor: rodar tudo de uma vez e conferir o ambiente

## Receita rápida

```bash
# 1. O ambiente está pronto?
sparkforge doctor --repo .

# 2. O que o scan vai rodar em cada arquivo (não roda nada ainda)
sparkforge scan . --dry-run

# 3. Rodar: extrai, junta, julga e grava em .sparkforge/scan/
sparkforge scan .

# 4. No CI: gerar SARIF e falhar se houver achado P0
sparkforge scan . --format sarif --fail-on P0
```

## Para que serve

- **`doctor`** diz se a instalação está pronta, antes de você perder tempo com um erro no meio do caminho. São treze checagens, e cada uma diz o que fazer quando não está `ok`.
- **`scan`** poupa você de saber qual `analyze` roda em cada arquivo. Ele olha o repositório, escolhe o extrator certo para cada arquivo, junta os facts, roda `fuse` e `judge`, e resume o resultado.

Nenhum dos dois acessa a AWS. O `scan` só analisa o que já está no disco; para trazer artefatos da conta, veja [Coleta na AWS](coleta-na-aws.md).

## Quando usar e quando não usar

| Use | Não use |
|---|---|
| Primeiro contato com um repositório | Quando você já sabe exatamente qual `analyze` quer (rode ele direto) |
| No CI, para ter SARIF e um gate por severidade | Para coletar da AWS: o `scan` nunca coleta |
| Depois de coletar artefatos com `sparkforge collect ...` | Para decidir capacidade ou custo: isso é `capacity`, `finops` e `gain` |

## doctor passo a passo

```bash
sparkforge doctor --repo .
```

Saída real (encurtada), numa máquina sem `boto3`:

```json
{
  "checks": [
    {"id": "pacote", "status": "ok", "detail": "sparkforge 0.5.0, Python 3.14.6", "unlock": null},
    {"id": "extras", "status": "warn", "detail": "modulos ausentes: boto3",
     "unlock": "pip install \"sparkforge-aws[aws]\""},
    ...
    {"id": "packs", "status": "skip",
     "detail": "nenhum pack configurado (SPARKFORGE_PACKS vazia)", "unlock": null},
    ...
    {"id": "credencial_aws", "status": "skip", "detail": "boto3 ausente",
     "unlock": "pip install \"sparkforge-aws[aws]\""}
  ],
  "counts": {"ok": 4, "warn": 1, "fail": 0, "skip": 4},
  "healthy": true,
  "online": false
}
```

Como ler:

| Status | Quer dizer | O que fazer |
|---|---|---|
| `ok` | Pronto | Nada |
| `warn` | Funciona, mas algo pede atenção | Rode o comando de `unlock` |
| `fail` | Quebrado: o comando sai com código 1 | Rode o `unlock` antes de continuar |
| `skip` | Não se aplica (ex.: você não usa packs) | Nada, a menos que queira a capacidade |

As treze checagens: `pacote`, `extras`, `mcp`, `catalogo`, `packs`, `knowledge`, `indice_de_codigo`, `artefatos`, `credencial_aws` e uma por host da integração de usuário (`integracao_claude`, `integracao_devin`, `integracao_codex` e `integracao_copilot`), que dizem se o host está integrado, em que versão do pacote, e se há cópia vendorizada em dobro no repositório atual (veja [Integrar uma vez por máquina](../02-instalacao.md#integrar-uma-vez-por-máquina-sparkforge-integrate)).

- **`indice_de_codigo`**: o doctor só confere se o índice existe. Conferir se ele está atualizado grava no índice, e o doctor só lê. Para isso, use `sparkforge code status --root .`.
- **`credencial_aws`**: por padrão, o doctor só vê se a cadeia do boto3 acha uma credencial, sem chamar a AWS. `sparkforge doctor --online` confirma na AWS (STS) e mostra a conta. Essa é a única forma do doctor que usa rede, e ela existe só na CLI.

## scan passo a passo

1. Veja o plano sem rodar nada:

   ```bash
   sparkforge scan . --dry-run
   ```

   Cada entrada diz o analyze, o arquivo e a origem: `manifesto` (artefato coletado) ou `extensao` (código).

2. Rode:

   ```bash
   sparkforge scan .
   ```

3. Leia o resultado. Saída real (encurtada) num repositório com um `job.py` e um `dump.json` solto:

   ```json
   {
     "analyzes": {"pyspark": {"files": 1, "facts": 3}, "sql": {"files": 1, "facts": 1}},
     "facts": {"extracted": 4, "after_fuse": 5},
     "findings": {"total": 1, "by_severity": {"P1": 1}, "rule_ids": ["SF-PY-001"]},
     "refused": [
       {"path": "dump.json", "reason": "sem_manifesto",
        "detail": "JSON fora do manifesto nao e classificado pelo conteudo"}
     ],
     "gate": {"fail_on": null, "tripped": false}
   }
   ```

O que o scan grava em `.sparkforge/scan/`:

| Arquivo | Conteúdo |
|---|---|
| `facts_<analyze>.json` | O que cada extrator emitiu |
| `facts.json` | A união depois do `fuse` (o que o `judge` viu) |
| `findings.json` | Os achados do `judge` |
| `summary.json` | O mesmo resumo do terminal |

Com `--format sarif`, ele grava também o SARIF e o resumo de PR em `.sparkforge/report/`, os mesmos arquivos do [`report github`](ci-e-github.md).

### Como o scan decide o que rodar

| O que ele acha | O que roda |
|---|---|
| Artefato no `.sparkforge/artifacts/manifest.json` com sha256 conferido | O analyze do `kind` que o coletor gravou |
| `.py` | `analyze pyspark` e `analyze sql` (literais `spark.sql`) |
| `.sql` | `analyze sql` |
| `.tf` | `analyze terraform` |
| `.jsonl` fora de `.sparkforge/` | `analyze event-log` |
| `workload.yaml` na raiz do repositório (origem `nome`) | `analyze workload`; em subpasta, nada |
| `.json` fora do manifesto | Nada: recusa `sem_manifesto` |

Um JSON solto nunca é classificado pelo conteúdo: vários extratores leem `.json`, e adivinhar mandaria o arquivo ao extrator errado. Para o scan analisar um dump, colete-o com `sparkforge collect ...`: o coletor grava o tipo no manifesto.

### As recusas

O scan sempre diz o que não rodou e por quê. Isso é informação, não erro:

| Recusa | Quer dizer |
|---|---|
| `sem_manifesto` | JSON fora do manifesto |
| `sha256_divergente` | O artefato mudou ou sumiu depois da coleta |
| `kind_sem_analyze` | Nenhum extrator lê esse tipo (ex.: a definição do job do `collect glue-job`) |
| `exige_job_name` | Run do Glue sem o nome do job no manifesto |
| `fora_da_raiz` | O manifesto aponta para fora do repositório; o scan não lê |
| `analyze_falhou` | O extrator deu erro nesse arquivo; os outros seguem |

## Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `scan: diretorio nao encontrado` (código 2) | Caminho errado | `sparkforge scan <raiz> --dry-run` |
| Muitas recusas `sem_manifesto` | O repositório tem muitos `.json` de configuração | Normal; elas ficam só no resumo |
| `doctor` sai 1 | Alguma checagem deu `fail` | Rode o `unlock` dela |
| Achado de Lake Formation não aparece com `analyze` + `judge` feitos à mão, mas aparece no scan | O scan roda `fuse` antes do `judge` | Rode `fuse` quando fizer à mão (ver [Lake Formation e acesso](lake-formation-e-acesso.md)) |

## Próximos passos

- Referência: [`sparkforge scan`](../referencia/cli/scan.md), [`sparkforge doctor`](../referencia/cli/doctor.md), [`sparkforge_scan`](../referencia/tools/sparkforge_scan.md) e [`sparkforge_doctor`](../referencia/tools/sparkforge_doctor.md).
- Levar o scan para o PR: [CI e GitHub](ci-e-github.md).
