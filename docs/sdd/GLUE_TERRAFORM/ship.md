---
sdd: 1
feature: GLUE_TERRAFORM
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/GLUE_TERRAFORM/build_report.md
  sha256: "0a851b4cd6be9102b983253d2ab35a973edd1a90f3a7351f03f21455fe20eebe"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, status_numbers_gate, claims_gate]
deviations:
  - "O gate de lastro reprovava a branch, e eu tinha aceitado o contrario. O implementador relatou exit 0 porque rodou o gate ANTES de criar os dois .py novos; a revisao final mediu, e o gate listou SEIS ids. Duas das alegacoes CAIRAM em vez de subir, porque stepfunctions.py e airflow_dag.py encolheram ~56 linhas cada dentro do corpus medido."
  - "O manifesto do design estava incompleto para o AC5: docs/vnext/adrs/ADR-010-code-intelligence-indice-local.md carrega uma das alegacoes remediadas e nao estava no files:. A linha entrou e a cascata foi recarimbada."
  - "A docstring do modulo novo afirmava as TRES varreduras do repositorio. Sao SETE, contadas na correcao -- a revisao achara seis e perdera uma. Uma delas e codigo de PRODUCAO (sparkforge/diagnosis/root_cause.py). A frase nova nao tem numeral fechado."
  - "A docstring datava a duplicacao no incremento do Step Functions; ela nasceu no do Airflow (f155fddf), e a mensagem do proprio commit que introduziu a docstring ja acertava."
  - "A docstring dizia que tres revisoes finais conferiram a mao que as copias nao divergiram. Varridos os 17 ship.md, existe UM registro de conferencia."
  - "O subagente da T1 travou esperando o proprio gate e nunca entregou relato. Em vez de herdar o buraco como na SFN_HISTORY, reproduzi o vermelho tirando o modulo do lugar e rodando o teste: o exit 2 do build_report e meu, visto."
  - "O plano escrevia `git commit -F <arquivo com a mensagem>`, e o marcador foi executado literalmente: tres arquivos vazios sobraram na raiz, removidos. Planos futuros precisam de caminho real ou aviso."
  - "A revisao em dois estagios por tarefa nao rodou; a revisao final do diff inteiro rodou."
---

# GLUE_TERRAFORM — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de três jeitos, e nenhum aconteceu:

- **As duas funções existem uma vez só**, em `sparkforge/facts/glue_terraform.py`, e
  nenhum dos dois extratores guarda cópia local. O teste confere por **identidade**, não
  por nome — um `from ... import` que trouxesse uma segunda cópia passaria num teste de
  nome e falha nesse.
- **O módulo não é contado como extrator**: sem `EMITTED_KINDS`, ele fica fora de todas as
  varreduras, e `check_status_numbers --strict` fecha em 0 divergências **sem** o
  `STATUS.md` ser editado.
- **Nenhum golden mudou.** `pytest tests/test_fixtures_golden*.py` deu **3299 passed, 4
  skipped** — exatamente o número de antes da refatoração, sem regeneração.

## O que a feature entrega

`_glue_jobs_por_nome` e `_max_retries` existiam duas vezes, com corpos idênticos. A
duplicação foi deliberada quando o domínio do Airflow entrou, e o docstring dizia onde ela
deveria morar. Agora moram lá.

O módulo **lê facts**, não artefato: sem `EXTRACTOR_ID`, sem `EMITTED_KINDS`, sem
`extract_*`. Essa ausência é o que o mantém fora das varreduras, e um teste diz isso de
forma executável — as listas manuais fazem `union` de `EMITTED_KINDS`, então acrescentá-lo
a elas levantaria `AttributeError` sem explicação.

## Medidas

| | antes (`e4141869`) | depois |
|---|---|---|
| definições de cada leitor de Terraform | 2 | 1 |
| arquivos `.py` no corpus medido | 774 | 776 |
| extratores de facts publicados | 41 | 41 |
| goldens passando | 3299 | 3299 |

## Gates rodados

| gate | resultado |
|---|---|
| módulo, extratores, goldens dos dois domínios, fusão, SDD (8 arquivos) | 323 passed |
| as varreduras de extrator, causa raiz, árvore versionada, lotes (9 arquivos) | 876 passed, 2 skipped |
| `python -m ruff check sparkforge scripts tests` | limpo |
| `python scripts/sync_skills.py --check` | exit 0 |
| `python scripts/verify_offline_bundle.py` | `"ok": true` |
| `python scripts/check_surface_lock.py` | 0 divergências |
| `python scripts/check_status_numbers.py --strict` (AC5) | 0 divergências |
| `python scripts/check_vnext_claims.py` | 0 divergências |
| `python -m pytest tests/test_fixtures_golden*.py -q` | 3299 passed, 4 skipped |
| `sparkforge sdd check --repo . --feature GLUE_TERRAFORM` | `ok: true`, 0 recusas, 0 lacunas |

O `verified_by` de `kind: command` do define:

| critério | comando | exit |
|---|---|---|
| AC5 | `python scripts/check_status_numbers.py --strict` | 0 |

## Pendências

- **Três peculiaridades preservadas**, fora do escopo declarado e agora nomeadas na
  docstring: o truncamento silencioso de `value` float; o `name` literal sem `value`
  indexando sob a chave `"None"`; e o `subject.file` ausente virando `""` — que, medido na
  correção, faz `max_retries` devolver um `("absent", 0, None)` que ninguém leu, justo o
  que a conservadoria do `not_literal` existe para evitar. São candidatas a feature
  própria.
- **Outras duplicações entre os extratores de orquestração** não foram procuradas: só
  estas duas tinham sido medidas como gêmeas idênticas.

## Lições

- **Relato de gate é afirmação, e afirmação se reconfere.** Eu aceitei "gate de lastro:
  exit 0" de um subagente que o rodou antes de criar os arquivos que ele mesmo ia criar. A
  regra que a sessão aplica aos subagentes — rodar o gate com a árvore no estado final —
  vale para quem lê o relato deles.
- **Refatoração que remove código move alegação para baixo.** Duas das seis alegações
  caíram, porque os arquivos encolheram dentro do corpus medido. A expectativa mental era
  de crescimento.
- **Numeral exaustivo em prosa é dívida.** "As TRÊS varreduras" estava errado; a revisão
  achou seis e a correção achou sete, uma delas em produção. A frase que sobrevive é a que
  diz "o que foi conferido, nesta data", sem fechar o conjunto.
- **Subagente pendurado não precisa custar o vermelho.** Desta vez o vermelho foi
  reproduzido tirando o módulo do lugar — um minuto de trabalho contra uma tarefa
  `skipped` para sempre.
