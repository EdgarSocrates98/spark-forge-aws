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
| `runtime` | O finding vem de execucao (`job_run`, `table`), nenhuma evidencia de codigo o localiza e nenhum fact de stage o liga a um callsite |
| `callsite_ausente` | O finding e de stage (ou cita um stage na evidencia), mas o event log nao traz `spark.stage.callsite` para aquele stage |
| `callsite_sem_forma` | O nome do stage nao tem a forma `acao at arquivo:linha` (ex.: nome sintetico) |
| `callsite_nao_python` | O callsite e da JVM (`save at Etl.scala:120`) e o arquivo nao esta sob as raizes |
| `callsite_ambiguo` | O finding de stage nao cita o fact do stage, e o mesmo `stage_id` existe em mais de um event log |
| `sem_linha` | Ha arquivo, mas nao ha linha valida (>= 1) |
| `arquivo_fora_do_repo` | O arquivo nao existe sob nenhuma raiz (ex.: `plan.txt` de uma execucao) |
| `caminho_ambiguo` | O mesmo caminho existe em mais de uma raiz declarada |
| `evidencia_ausente` | Um fact citado em `evidence` nao esta na uniao passada em `--facts` |
| `limite_do_github` | Acima de 5 000 resultados por run, ou de 1 MiB no resumo |

Medido nos goldens de `fixtures/` em 2026-09-11: dos 222 findings, 98 entram no
SARIF e 124 ficam no resumo, 101 deles por serem de execucao. Eles nao somem: o
resumo do PR os lista com o motivo.

## Findings de stage: a linha da acao, nao a causa

Um finding de `stage` (ou um `job_run`/`table` que cita um stage na evidencia)
procura o `spark.stage.callsite` que o event log registrou para aquele stage --
`collect at /opt/spark/work/jobs/lib/job.py:42` -- no mesmo event log (o
`stage_id` recomeca em 0 em cada aplicacao). O caminho do cluster e casado com
o repositorio pelo **maior sufixo unico** contra as `--source-root`
(`jobs/lib/job.py`, depois `lib/job.py`, depois `job.py`); um empate e
`caminho_ambiguo`, e a busca nao cai para o sufixo mais curto. Callsite da JVM
(`save at Etl.scala:120`) usa a linha do nome do stage.

O alerta diz **"linha da acao `collect` que originou o stage 4 (nao e a causa)"**:
skew e spill nascem num join ou shuffle antes da acao, e o event log so sabe
onde a acao foi chamada.

Medido em 2026-09-11 nos goldens de `fixtures/`: dos 28 findings de stage, 0 sao
localizados, porque os event logs das fixtures tem nomes de stage sinteticos ou
de Scala. Em event log real de PySpark o nome do stage costuma ter a forma
`acao at caminho:linha`; os casos `fixtures/sarif/stage_*` provam o caminho.

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

- Um `job_run` sem fact de stage na evidencia nao ganha linha: escolher "o stage
  mais caro" seria heuristica, e fica fora ate haver criterio medido.
- O verbo nao filtra "so os findings novos do PR": o proprio Code Scanning
  compara com a analise da base e marca o que o PR introduziu.
- A tool MCP `sparkforge_report_github` devolve o mesmo SARIF, resumo e
  anotacoes, mas **nao grava**: gravar e da CLI.
