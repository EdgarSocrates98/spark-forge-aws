# Como este repositório prova o que afirma sobre Glue 6.0

Quatro camadas, e cada uma existe porque a anterior não conseguia provar alguma coisa. A
lista de qual gate rodar para cada tipo de mudança está em
[`../../../gates-por-mudanca.md`](../../../gates-por-mudanca.md) — ela é a referência
operacional; este documento explica o que cada camada mede.

## 1. Golden por kind

`fixtures/migration/`, no formato `meta.yaml` mais `input/` e `expected/`, com **um caso por
kind emitido**. O que ele prova: o extrator observa o que diz observar, e observa a mesma
coisa amanhã.

`sparkforge/facts/migration.py` declara os kinds que emite em `EMITTED_KINDS`, e
`tests/test_fixtures_kind_coverage.py` cobra a correspondência. Kind declarado e nunca
emitido torna **inalcançável** qualquer regra que dependa dele — por isso a checagem é
estrutural e não uma revisão de código.

Testes: `tests/test_fixtures_golden_migration.py`, `tests/test_fixtures_kind_coverage.py`.

## 2. Golden por regra

O mesmo corpus, olhado por outro eixo: **toda regra precisa de um golden que a dispare, e
todo ramo de severidade precisa de golden**. Regra sem fixture é regra que ninguém sabe se
dispara; ramo de severidade sem golden é um caminho que nunca foi executado.

Junto disso andam os **negativos**, que são o que separa "esta regra lê a coisa certa" de
"esta regra acusa qualquer coisa parecida":

- **negativo por versão** — mesmo artefato, runtime que não cruza a fronteira da regra;
- **negativo por valor** — mesmo kind, valor que satisfaz o limiar.

Teste: `tests/test_fixtures_kind_coverage.py`.

## 3. Cenário por par de versões

`fixtures/scenarios/` — um job inteiro atravessando um par origem → alvo, com mais de um
artefato e mais de um kind. O golden é o `to_dict()` do `MigrationAssessment`, não facts mais
findings, porque a informação que **só** o cenário produz é **em qual degrau cada achado
nasceu**.

O que os goldens por kind não conseguem provar, e o cenário prova:

- **acumulação por degrau** — `assess()` expande o par em degraus derivados da matriz e julga
  cada um com o runtime daquele degrau; regras diferentes nascem em degraus diferentes, e
  isso é o que responde se um salto intermediário resolveria parte do problema;
- **deduplicação num caso realista** — `by_step` e `report()` têm cardinalidades diferentes
  de propósito, e as duas visões respondem perguntas diferentes ("quantos problemas eu
  tenho?" e "isto ainda vale depois do próximo salto?");
- **o motor não é de uma área só** — `assess()` chama o julgamento com o catálogo inteiro,
  então regra de qualquer área com `runtime_scope` compatível entra pelo degrau;
- **o que o par não sustenta** — kind observado que não alimenta regra nenhuma continua no
  corpus, para provar que a presença do fact não inventa achado.

O `meta.yaml` de cada cenário registra o que ele exercita **e o que foi deixado de fora, com
o motivo**. Teste: `tests/test_fixtures_scenarios.py`. Regeneração:
`python scripts/regen_fixtures.py <nome>` — golden escrito à mão descreve o que alguém achou
que o código faz.

## 4. Holdout

`evals/holdout/` — mesmo formato dos cenários, com uma regra a mais:

> Nenhum arquivo de `skills/`, `agents/` ou `knowledge/` cita o nome de um diretório deste
> corpus.

`tests/test_evals_holdout.py` **prova** essa regra a cada execução, incluindo os espelhos que
a ferramenta de fato carrega, e com guarda de não-vacuidade. Sem esse teste, "holdout" seria
só um nome de pasta.

Ele fica **fora** de `fixtures/` de propósito: os invariantes de `fixtures/` cobram cobertura
por kind e por regra, e holdout não é cobertura — é a amostra retida justamente para não ser
otimizada contra. Mantê-lo ali o transformaria em mais um alvo do gate de cobertura, que é o
oposto do que ele mede.

O jeito natural de destruir um holdout não é malicioso, é distraído: citar o cenário num
`SKILL.md` para ilustrar um exemplo. A partir dali, um agente que acerta pode estar
lembrando. Ver [`../../../../evals/holdout/README.md`](../../../../evals/holdout/README.md).

## Gates que cercam o conhecimento, não o código

- **Bundle offline** — `knowledge/offline-manifest.json` guarda o `sha256` de cada documento
  de `knowledge/`. Editar o `.md` sem regravar o hash reprova o bundle inteiro
  (`scripts/verify_offline_bundle.py`).
- **Lock de fontes** — toda URL citada por um documento de `knowledge/` ou por uma linha da
  matriz de runtime precisa estar em `knowledge/sources.lock.json`, com data de recuperação.
- **Caso instalado** — `scripts/verify_wheel.py` prova que o pacote instalado carrega o
  catálogo e os goldens. Teste em árvore passa dos dois jeitos; wheel, não.
- **Gate de lastro** — `scripts/check_vnext_claims.py` audita todo número e toda alegação de
  capacidade publicados em `docs/vnext/` e `docs/harness/`, fail-closed nos dois sentidos.

**Esta pasta não está sob o gate de lastro.** `docs/aws/` não está em `audited_roots()`, e
nenhum teste cobra os documentos daqui. É por isso que eles apontam para o arquivo que
sustenta cada afirmação em vez de copiá-la: sem gate, o ponteiro é a única coisa que
envelhece junto com a fonte. Ver [`known-unknowns.md`](known-unknowns.md).
