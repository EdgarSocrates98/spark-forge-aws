# Precisão de versão — quatro proibições, e o que o repositório já faz para cumpri-las

Este documento existe porque quatro princípios que o projeto **pratica** nunca
estiveram escritos como regra. Eles vinham de um prompt de origem que não é
artefato deste repositório (insumo de sessão, ignorado pelo git), e o que
sobrevive a ele é isto: a proibição, mais o mecanismo medido que a cumpre.

A regra 18 do `CLAUDE.md` já diz o essencial — *"a versão muda o significado do
número, não o número"*. As quatro abaixo são as formas concretas de violá-la.

---

## 1. Não generalizar comportamento de versão para o produto

Proibido transformar:

| Errado | Certo |
|---|---|
| `Spark 3.5 behavior` → `Spark behavior` | manter a versão |
| `Glue 5.1 behavior` → `Glue behavior` | manter a versão |
| `Iceberg 1.x behavior` → `Iceberg behavior` | manter a versão |

**O mecanismo que cumpre:** `runtime_scope` por regra, e o gate que o cobra.
Medido — seis regras declaram faixa com precisão de patch ou de minor:

```
SF-ENV-002        iceberg >=1.10.0
SF-GRAPH-002      spark   [">=3.3", "<3.4"]
SF-SPARK4-001/002/004  spark >=4.0.0
SF-SPARK4-003     spark   >=4.1.0
```

`SF-GRAPH-002` é o caso que prova a precisão: a faixa é de **um minor**, e um
Glue 5.1 (Spark 3.5.6) cai fora dela — corretamente pulado.

**Como isso falha em silêncio:** `runtime_scope: {}` não é omissão, é afirmação
("o defeito não depende de fronteira de versão"). Escrever `{}` por preguiça faz
a regra falar do produto quando ela devia falar da versão. Ver a seção ESCOPO do
cabeçalho de `rules/catalog/iceberg.yaml`, que documenta as três razões pelas
quais cinco regras **abandonaram** o guarda de versão — e ali abandonar era o
certo, porque o guarda era derivado de Glue para regras que nada têm de Glue.

---

## 2. Não generalizar patch para minor

Quando a correção depende de patch, os três são versões diferentes:

```
Spark 3.5.4    Spark 3.5.5    Spark 3.5.6
```

Colapsá-los em `Spark 3.5` apaga a informação que decide.

**O mecanismo que cumpre:** `knowledge/glue/runtime-matrix.yaml` guarda o patch,
não o minor. Medido:

| Glue | Spark |
|---|---|
| 3.0 | 3.1.1 |
| 4.0 | 3.3.0 |
| 5.0 | **3.5.4** |
| 5.1 | **3.5.6** |
| 6.0 | 4.1.1 |

O 5.0 e o 5.1 são o mesmo minor e **patches diferentes**, e a diferença entre
eles é onde mora metade do diagnóstico de Lake Formation (o conector S3 default
mudou de EMRFS para S3A). Uma matriz que dissesse "Glue 5.x → Spark 3.5" tornaria
esse diagnóstico impossível.

---

## 3. Não confundir a distribuição com o upstream

São três produtos, mesmo quando o número parece igual:

```
Apache Spark        Amazon EMR Spark        AWS Glue Spark
```

**O mecanismo que cumpre:** as matrizes guardam o rótulo do vendor quando ele
existe. `knowledge/emr/runtime-matrix.yaml` e a §0 de
`knowledge/glue/lakeformation-fgac.md` carregam formas como `3.3.0-amzn-1` — o
sufixo é parte da versão, não ruído.

**Consequência prática:** uma fonte do Apache que afirma comportamento de
`3.5.6` é T1 para o Apache Spark e **não** decide sozinha o comportamento do
Glue 5.1, que embarca uma build própria. É a mesma distinção que a §6 de
`lakeformation-fgac.md` mantém entre o que o Iceberg declara e o que a AWS
declara — e ali as duas não fecham.

O `Evidence.scope` da camada agêntica existe para isso: uma T1 fora da versão
alvo **tem autoridade e não sustenta a claim**, e `has_fresh_in_scope` separa as
duas perguntas.

---

## 4. Uma regra tem de poder declarar a fronteira que ela precisa

O prompt de origem propunha uma forma expandida de `runtime_scope`, com
`min`/`max` por componente e listas de release.

**Medido: a forma atual já cobre os quatro eixos**, e por dois formatos —
comparador único (`>=1.10.0`) ou **lista** de comparadores
(`[">=3.3", "<3.4"]`), que é como uma faixa fechada se escreve. Os componentes
aceitos são `glue`, `spark`, `python`, `iceberg` e `athena`.

O que **não** existe é `emr: {releases: [...]}`, e a razão é medida, não
esquecimento: **nada alimenta `RuntimeContext` a partir de um fact de EMR on
EKS**. As quatro regras `SF-EMRK` declaram `runtime_scope: {}` por isso, e o
limite está registrado no `STATUS.md` — a matriz de release existe e é
publicada; o produtor que a ligaria ao contexto não. Acrescentar a chave sem o
produtor criaria um guarda que nunca dispara, que é o defeito que a Fase 5a
desfez no resto do catálogo.

---

## O teste que impede a regressão

`tests/test_runtime_inferred_from_facts.py::test_the_catalog_still_guards_exactly_the_rules_this_file_names`
trava a igualdade entre "regras com `runtime_scope` não-vazio no catálogo" e a
lista escrita à mão naquele arquivo. Regra nova que ganhe guarda de versão sem
entrar na lista derruba o gate; regra que perca o guarda também.

Ele existe porque a alternativa — confiar em revisão — já falhou: **seis regras
`SF-LF` ficaram fora da lista por uma entrega inteira**, e o teste ficou vermelho
na árvore sem que nada acusasse até a auditoria de 2026-09-10.
