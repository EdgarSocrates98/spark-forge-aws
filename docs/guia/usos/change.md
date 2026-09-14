# Mudança de configuração e sandbox: gerar o diff e testar numa cópia

## Receita rápida

```bash
# 1. Extraia os facts do repositório: Terraform e código
sparkforge analyze terraform --path . --out facts_tf.json
sparkforge analyze pyspark --path . --out facts_py.json

# 2. Gere o diff e o diff de rollback de um valor (nada é aplicado)
sparkforge change plan --facts facts_tf.json --facts facts_py.json --repo . \
  --set spark.sql.shuffle.partitions=320 --out mudanca.patch

# 3. Veja numa cópia o que o diff muda nos achados
sparkforge change sandbox --repo . --diff mudanca.patch

# 4. Apague as cópias quando terminar
sparkforge change sandbox --repo . --clean
```

## Para que serve

- **`change plan`** transforma um valor de configuração num **diff** que você pode revisar, e já traz o **diff de rollback**. Ele descobre sozinho em que arquivo e em que linha o valor foi pedido: no `--conf` de um job Glue no Terraform ou numa chamada `spark.conf.set`/`.config` no código. Não grava nada no seu repositório.
- **`change sandbox`** pega **qualquer** diff (o do `change plan` ou um escrito à mão ou por um agente), aplica numa **cópia** do repositório e roda o `scan` na cópia antes e depois. Assim você vê quais achados somem e quais aparecem **sem mexer na sua árvore**.

Os dois são os níveis L1 ("produzir a mudança") e L2 ("executar numa cópia isolada") do plano de autonomia do projeto. Nenhum deles aplica nada no seu repositório, abre PR ou chama a AWS.

## Quando usar e quando não usar

| Use | Não use |
|---|---|
| O `tune` propôs um valor e você quer o diff pronto, com rollback | Para decidir QUAL valor usar: isso é o `tune` (ou você) |
| Um agente escreveu um diff e você quer ver o que ele muda antes de aplicar | Para medir desempenho: a diferença de achados não é ganho (use `benchmark` e `gain` com dois runs) |
| Revisar uma mudança de configuração num PR | Para mudar código (tirar uma UDF, trocar um `collect`): o `change plan` só troca valor de configuração |

## change plan passo a passo

1. Extraia os facts do repositório inteiro, a partir da raiz. Os facts guardam o caminho do arquivo **relativo à raiz que você passou**, e o `--repo` do `change plan` precisa ser essa mesma raiz.
2. Escolha de onde vem o valor:
   - `--set chave=valor` (repetível): você diz o valor;
   - `--from-tune`: usa o valor que o [`tune`](custo-e-capacidade.md) deriva do shuffle medido. Para isso, junte também os facts do event log (`sparkforge analyze event-log --path <log> --out facts_run.json` e mais um `--facts facts_run.json`).
3. Rode e leia o resultado.

Saída real, encurtada, num `main.tf` que tem quatro chaves na mesma linha do `--conf`:

```json
{
  "stage": "produce_change",
  "applied": false,
  "changes": [
    {"key": "spark.sql.shuffle.partitions", "file": "main.tf", "line": 13,
     "from": "800", "to": "320", "provenance": "terraform", "evidence": ["f_ea876c"],
     "basis": null}
  ],
  "refused": [],
  "files": ["main.tf"],
  "diff": "--- a/main.tf\n+++ b/main.tf\n@@ -10,6 +10,6 @@\n ...\n-    \"--conf\" = \"spark.sql.shuffle.partitions=800 --conf spark.sql.adaptive.enabled=true ...\"\n+    \"--conf\" = \"spark.sql.shuffle.partitions=320 --conf spark.sql.adaptive.enabled=true ...\"\n ...",
  "rollback_diff": "--- a/main.tf\n+++ b/main.tf\n ..."
}
```

Só o par `spark.sql.shuffle.partitions=800` mudou. As outras três chaves da linha ficaram como estavam.

Como ler:

| Campo | Quer dizer |
|---|---|
| `changes` | Cada valor trocado: arquivo, linha, de, para, quem pediu (`terraform` ou `code`) e o fact que prova |
| `basis` | Com `--from-tune`, a fórmula e a medida que sustentam o valor; com `--set`, vazio |
| `diff` / `rollback_diff` | Os dois diffs. Entregue sempre os dois juntos: mudança sem rollback não é recomendação completa |
| `refused` | O que não virou diff, com o motivo e o que fazer (`unlock`) |
| `tune_refused` | As propriedades que o `tune` recusou por falta de medida |

No código Python, ele troca exatamente o valor, mesmo quando a chamada ocupa várias linhas:

```python
spark = (
    SparkSession.builder
    .appName("etl-sintetico")
    .config("spark.sql.shuffle.partitions", 800)   # vira 320; o resto fica igual
    .getOrCreate()
)
```

### As recusas do plano

| Recusa | Quer dizer | O que fazer |
|---|---|---|
| `sem_procedencia_em_arquivo` | Nenhum arquivo do repositório pede essa chave; o valor vem do runtime ou do cluster | Declare a chave em arquivo e extraia de novo |
| `linha_nao_confere` | A linha que o fact aponta não tem mais aquele valor: o arquivo mudou depois da extração, ou o `--repo` não é a raiz da extração | Extraia de novo sobre a árvore atual |
| `procedencia_ambigua` | A chave é pedida em mais de um lugar (ex.: no código e no Terraform) | Deixe num lugar só. O código vence o Terraform em runtime |
| `valor_nao_literal` | O valor é uma variável ou expressão | Escreva como valor literal, ou mude à mão |
| `valor_redigido` | O valor parece segredo e foi escondido na extração | Mude à mão |
| `valor_invalido` | O valor novo não cabe (tipo diferente, espaço, aspas) | Passe um valor do mesmo tipo do atual |
| `valor_ja_igual` | O arquivo já pede esse valor | Nada a fazer |
| `caminho_fora_da_raiz` | O fact aponta para fora do repositório | Confira a raiz usada na extração |

O comando sai com código 1 quando nada virou diff e alguma chave foi recusada.

## change sandbox passo a passo

```bash
sparkforge change sandbox --repo . --diff mudanca.patch
```

O que ele faz, em ordem:

1. Lê o diff e recusa, **antes de gravar qualquer coisa**, o que ele não aplica.
2. Copia o repositório para `.sparkforge/sandbox/<id>/before/` (intacta) e `.sparkforge/sandbox/<id>/after/` (com o diff). A cópia pula `.venv`, `vendor`, `build`, arquivos grandes e arquivos com nome de credencial (`*.tfvars`, `.env`...), e leva junto `.sparkforge/artifacts/`, onde ficam os artefatos coletados.
3. Roda o `scan` em cada cópia e compara os achados.

Saída real, encurtada, de um diff que tira um `spark.conf.set` do código:

```json
{
  "stage": "sandbox_execute",
  "applied": true,
  "main_tree_touched": false,
  "sandbox": ".sparkforge/sandbox/a6dd7ad28357b7f3",
  "files_changed": ["lib/job.py"],
  "new": [],
  "resolved": [{"rule_id": "SF-PY-012", "subject": {"file": "job.py", "line": 2}}],
  "kept_count": 0,
  "moved_candidates": [],
  "proof_obligations": [
    {"rule_id": "SF-PY-012", "side": "resolved",
     "validation": ["Valor efetivo de cada chave conferido na aba Environment antes e depois.", "..."],
     "rollback": ["Reverter o commit."]}
  ],
  "next_steps": [
    {"action": "run_your_tests", "detail": "rode os seus testes sobre .sparkforge/sandbox/a6dd7ad28357b7f3/after: ..."},
    {"action": "sparkforge benchmark", "detail": "desempenho so se afirma com dois runs medidos ..."},
    {"action": "sparkforge funcval plan", "detail": "confira que o resultado continua o mesmo ..."}
  ]
}
```

Como ler:

| Campo | Quer dizer |
|---|---|
| `resolved` | Achados que existiam antes e sumiram depois do diff |
| `new` | Achados que o diff fez aparecer |
| `kept_count` | Quantos achados ficaram iguais |
| `moved_candidates` | O mesmo achado, no mesmo arquivo, que só mudou de linha. **Não conte como resolvido** |
| `proof_obligations` | Como validar e como desfazer, para cada regra tocada |
| `next_steps` | O que o sandbox **não** faz por você: seus testes, a medida de desempenho, a conferência do resultado |
| `copy_skipped` | O que ficou fora da cópia, e por quê |

O que fica em disco:

| Caminho | Conteúdo |
|---|---|
| `.sparkforge/sandbox/<id>/before/` | A cópia sem o diff, com o `.sparkforge/scan/` dela |
| `.sparkforge/sandbox/<id>/after/` | A cópia com o diff, onde você roda seus testes |
| `.sparkforge/sandbox/<id>/report.json` | O mesmo relatório do terminal |

O `<id>` sai do diff e do conteúdo dos arquivos: rodar de novo com a mesma entrada cai no mesmo diretório e dá o mesmo relatório. A pasta `.sparkforge/sandbox/` está no `.gitignore`.

### As recusas do sandbox

Nenhuma recusa aplica o diff pela metade, e nenhuma grava nada.

| Recusa | Quer dizer |
|---|---|
| `diff_vazio` | O arquivo não tem nenhum trecho de diff |
| `diff_grande_demais` | Passa de 2 MB |
| `diff_nao_suportado` | Cria, apaga ou renomeia arquivo, ou mexe em binário |
| `diff_malformado` | Cabeçalho ou contagem de linhas inválidos |
| `diff_nao_aplica` | O diff foi feito sobre outra versão do arquivo: a linha de contexto não bate. A mensagem mostra qual linha |
| `caminho_fora_da_raiz` | Caminho com `..` ou absoluto |
| `arquivo_fora_da_copia` | O arquivo não foi copiado (credencial, pasta ignorada ou grande demais) |

Única tolerância: um diff com fim de linha LF aplica num arquivo com CRLF, e as linhas novas seguem o fim de linha do arquivo.

## O que nenhum dos dois faz

- Não aplica nada no seu repositório: `applied: false` no plano e `main_tree_touched: false` no sandbox.
- Não roda comando do seu repositório (testes, `spark-submit`) nem git.
- Não chama a AWS nem modelo de linguagem.
- Não afirma ganho. Para desempenho, compare dois runs medidos com [`gain`](custo-e-capacidade.md); para o resultado dos dados, [`funcval`](mudancas-com-prova.md).

## Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `linha_nao_confere` logo depois de extrair | O `--repo` do plano não é a mesma raiz do `analyze` | Extraia e rode o plano a partir da mesma raiz |
| `procedencia_ambigua` | A chave está no código e no Terraform | Tire de um dos dois lugares |
| `change plan: use --from-tune OU --set` (código 2) | Passou os dois, ou nenhum | Escolha um |
| `diff_nao_aplica` num diff do agente | O agente escreveu sobre uma versão antiga do arquivo | Peça o diff de novo sobre a árvore atual |
| `arquivo_fora_da_copia` num `.tfvars` | O sandbox não copia arquivo com nome de credencial | Mude esse arquivo à mão |

## Próximos passos

- Referência: [`sparkforge change`](../referencia/cli/change.md), [`sparkforge_change_plan`](../referencia/tools/sparkforge_change_plan.md) e [`sparkforge_change_sandbox`](../referencia/tools/sparkforge_change_sandbox.md).
- Depois de aplicar de verdade, prove o que a mudança fez: [Mudanças com prova](mudancas-com-prova.md).
