# Mudança de configuração, sandbox e PR: gerar o diff, testar numa cópia e propor

## Receita rápida

```bash
# 1. Extraia os facts do repositório: Terraform e código
sparkforge analyze terraform --path . --out facts_tf.json
sparkforge analyze pyspark --path . --out facts_py.json

# 2. Gere o diff e o diff de rollback de um valor (nada é aplicado)
sparkforge change plan --facts facts_tf.json --facts facts_py.json --repo . \
  --set spark.sql.shuffle.partitions=320 --out mudanca.patch

# 3. Veja numa cópia o que o diff muda nos achados (guarde o "id" da saída)
sparkforge change sandbox --repo . --diff mudanca.patch

# 4. Monte o pacote do PR a partir desse sandbox (nada é aplicado, git não roda)
sparkforge change propose --sandbox <id> --repo .

# 5. Abra o PR seguindo .sparkforge/proposal/<id>/commands.md (você, ou o agente
#    pela skill propose-change-pr, que para antes de git push e de gh pr create)

# 6. Apague as cópias do sandbox quando terminar
sparkforge change sandbox --repo . --clean
```

## Para que serve

- **`change plan`** transforma um valor de configuração num **diff** que você pode revisar, e já traz o **diff de rollback**. Ele descobre sozinho em que arquivo e em que linha o valor foi pedido: no `--conf` de um job Glue no Terraform ou numa chamada `spark.conf.set`/`.config` no código. Não grava nada no seu repositório.
- **`change sandbox`** pega **qualquer** diff (o do `change plan` ou um escrito à mão ou por um agente), aplica numa **cópia** do repositório e roda o `scan` na cópia antes e depois. Assim você vê quais achados somem e quais aparecem **sem mexer na sua árvore**.

- **`change propose`** pega um sandbox que já rodou e monta em `.sparkforge/proposal/<id>/` tudo o que um PR precisa: o patch, o patch de rollback, o texto do PR (assinado), a mensagem de commit, o nome da branch, um recibo da evidência e os comandos git/gh. Ele **não roda** esses comandos: quem abre o PR é você.

Os três são os níveis L1 ("produzir a mudança"), L2 ("executar numa cópia isolada") e L3 ("propor para produção") do plano de autonomia do projeto. Nenhum deles aplica nada no seu repositório, roda git, abre PR ou chama a AWS.

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

## change propose passo a passo

Rode depois de um `change sandbox` que aplicou o diff (`applied: true`), passando o `id` que ele devolveu:

```bash
sparkforge change propose --sandbox fc778c4f8222e1b0 --repo .
```

Se você tiver medidas de verdade, anexe os facts: `--benchmark bench.json` (facts `bench.*` de dois runs) e `--funcval funcval.json` (facts `funcval.*`). Sem elas, o texto do PR diz que a medida está **PENDENTE**, e está certo sair assim.

O pacote fica em `.sparkforge/proposal/<id>/` (o git ignora essa pasta):

| Arquivo | O que é |
|---|---|
| `change.patch` | O diff, conferido: aplicado sobre a cópia validada, ele reproduz a cópia com a mudança |
| `rollback.patch` | O caminho de volta |
| `pr_body.md` | O texto do PR: o que muda, achados que somem, achados novos de baixa gravidade, obrigações de prova, medidas e o que a proposta **não** afirma. Termina com a seção **Assinatura** |
| `commit_message.txt` e `branch.txt` | Mensagem do commit e nome da branch (`sparkforge/change-<8 letras do id>`) |
| `commands.md` | Os comandos git/gh, na ordem, com duas paradas: antes de `git push` e antes de `gh pr create` |
| `evidence/sandbox_report.json` | O relatório do sandbox, para o revisor |
| `evidence/receipt.json` | O recibo do scan da cópia com a mudança |
| `manifest.json` | O sha256 de cada arquivo do pacote |

Para conferir depois que o texto do PR não foi editado:

```bash
sparkforge report verify --report .sparkforge/proposal/<id>/pr_body.md \
  --findings .sparkforge/sandbox/<id>/after/.sparkforge/scan/findings.json
```

Se o scan da cópia não deixar nenhum achado, não há o que assinar: o texto do PR diz isso, e o pacote sai sem recibo.

A política padrão do repositório (`.sparkforge/policy.yaml`) pede confirmação para `git push` e `gh pr create`. Rodar `sparkforge policy sync-settings` leva isso para o Claude Code.

### As recusas do propose

Nada é gravado quando uma delas sai:

| Recusa | Quando | O que fazer |
|---|---|---|
| `sandbox_inexistente` | Não há sandbox com esse `id` | Rode o `change sandbox` e use o `id` da saída |
| `sandbox_nao_aplicado` | O sandbox recusou o diff | Resolva a recusa do sandbox e rode de novo |
| `sandbox_desatualizado` | Algum arquivo mudou depois do sandbox | Rode o `change sandbox` de novo sobre a árvore atual |
| `achado_novo_bloqueante` | O diff faz aparecer achado P0 ou P1 | Corrija a mudança antes de propor |

## O que nenhum dos três faz

- Não aplica nada no seu repositório: `applied: false` no plano e no propose, e `main_tree_touched: false` no sandbox e no propose.
- Não roda comando do seu repositório (testes, `spark-submit`) nem git: o propose só escreve os comandos em `commands.md` (`git_run: false`).
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

- Referência: [`sparkforge change`](../referencia/cli/change.md), [`sparkforge_change_plan`](../referencia/tools/sparkforge_change_plan.md), [`sparkforge_change_sandbox`](../referencia/tools/sparkforge_change_sandbox.md), [`sparkforge_change_propose`](../referencia/tools/sparkforge_change_propose.md) e a skill [`propose-change-pr`](../referencia/skills/propose-change-pr.md).
- Depois de aplicar de verdade, prove o que a mudança fez: [Mudanças com prova](mudancas-com-prova.md).
