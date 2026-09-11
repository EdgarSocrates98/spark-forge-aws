# SparkForge no GitHub: Code Scanning e resumo de PR

`sparkforge report github` pega os findings que `judge` produziu e os mostra
onde o PR e revisado:

- **SARIF 2.1.0** (`.sparkforge/report/sparkforge.sarif`) para o GitHub Code
  Scanning: alerta na aba Security e no diff do PR, deduplicado entre commits;
- **resumo em Markdown** (`.sparkforge/report/summary.md`) para o
  `$GITHUB_STEP_SUMMARY`, com **todos** os findings;
- uma **anotacao** `::error` / `::warning` / `::notice` por finding com linha,
  impressa no stdout, que vira anotacao no diff mesmo sem Code Scanning.

O verbo compoe sobre findings e facts ja produzidos: nao le artefato, nao chama
rede e nao chama a API do GitHub. Quem sobe o SARIF e a action `upload-sarif`,
no workflow.

## O que entra no SARIF, e o que nao entra

O Code Scanning **descarta resultado sem localizacao**, e interpreta a `uri`
relativa a raiz do repositorio (documentacao de SARIF do GitHub). Por isso so
entra no SARIF o finding que tem **linha num arquivo que existe no
repositorio**, e a localizacao e procurada nesta ordem:

1. o `subject` do proprio finding (`source_location`, `tf_resource` ou
   `plan_node`, com `file` e `line`);
2. o primeiro fact de `evidence` que seja de **codigo** (`source_location` ou
   `tf_resource`) e tenha `file` e `line`. Um fact com linha num dump ou num
   `plan.txt` nao empresta localizacao: ele apontaria o revisor para algo que
   nao esta no diff;
3. o arquivo resolvido pelas `--source-root` (ver abaixo).

Todo o resto sai no resumo, na secao **"Sem localizacao no repositorio"**, com
o motivo. Nenhum finding some: SARIF mais recusas e sempre o total.

| Motivo | Quando |
|---|---|
| `runtime` | O finding vem de execucao (`job_run`, `stage`, `table`) e nenhuma evidencia de codigo o localiza |
| `sem_linha` | Ha arquivo, mas nao ha linha valida (>= 1) |
| `arquivo_fora_do_repo` | O arquivo nao existe sob nenhuma raiz (ex.: `plan.txt` de uma execucao) |
| `caminho_ambiguo` | O mesmo caminho existe em mais de uma raiz declarada |
| `evidencia_ausente` | Um fact citado em `evidence` nao esta na uniao passada em `--facts` |
| `limite_do_github` | Acima de 5 000 resultados por run, ou de 1 MiB no resumo |

Medido nos goldens de `fixtures/` em 2026-09-11: dos 222 findings, 98 entram no
SARIF e 124 ficam no resumo, 101 deles por serem de execucao. Eles nao somem: o
resumo do PR os lista com o motivo.

## `--source-root`: de onde o caminho do finding e relativo

`analyze <verbo> --path jobs` grava cada arquivo **relativo a `jobs/`**
(`lib/job.py`), e nao a raiz do git (`jobs/lib/job.py`). O `report github`
precisa das mesmas raizes, na mesma ordem dos `analyze`:

```bash
sparkforge analyze pyspark   --path jobs  --out .sparkforge/facts-pyspark.json
sparkforge analyze terraform --path infra --out .sparkforge/facts-terraform.json
sparkforge judge --facts .sparkforge/facts-pyspark.json \
                 --facts .sparkforge/facts-terraform.json \
                 --glue 5.0 --out .sparkforge/findings.json
sparkforge report github --findings .sparkforge/findings.json \
                         --facts .sparkforge/facts-pyspark.json \
                         --facts .sparkforge/facts-terraform.json \
                         --repo . --source-root jobs --source-root infra \
                         --fail-on P0
```

`--source-root` absoluta, com `..` ou que resolva fora de `--repo` e erro de uso
(codigo 2).

## Severidade, gate e codigo de saida

| Severidade | `level` no SARIF | Anotacao |
|---|---|---|
| P0, P1 | `error` | `::error` |
| P2 | `warning` | `::warning` |
| P3, P4 | `note` | `::notice` |

As regras sao de performance, custo e correcao, e **nao** de seguranca: o SARIF
nao usa `security-severity` nem a tag `security`, para que os findings nao
entrem na contagem de vulnerabilidades do repositorio.

`--fail-on P0` sai com **1** quando ha finding P0; `--fail-on P1`, quando ha P0
ou P1 -- com linha ou sem. Sem `--fail-on`, sai 0. Erro de uso ou de entrada
sai 2.

## Workflow

O exemplo completo esta em
[`examples/github/sparkforge.yml`](../examples/github/sparkforge.yml): copie para
`.github/workflows/` no repositorio de dados e ajuste os diretorios e a versao
do Glue. Ele precisa de `security-events: write` para o upload e sobe o SARIF
mesmo quando o gate deixa o check vermelho, para que o alerta chegue a aba
Security.

Acrescente `.sparkforge/report/` ao `.gitignore` do repositorio de dados: sao
arquivos gerados a cada execucao.

## Limites conhecidos

- Finding de `stage` so entra no SARIF quando um fact de evidencia de codigo o
  localiza. A ponte codigo-execucao (`spark.stage.callsite`) ainda nao e usada
  para isso.
- O verbo nao filtra "so os findings novos do PR": o proprio Code Scanning
  compara com a analise da base e marca o que o PR introduziu.
- A tool MCP `sparkforge_report_github` devolve o mesmo SARIF, resumo e
  anotacoes, mas **nao grava**: gravar e da CLI.
