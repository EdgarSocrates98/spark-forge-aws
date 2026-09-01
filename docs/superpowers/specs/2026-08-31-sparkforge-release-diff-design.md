# SparkForge AWS — `ReleaseDescriptor` e `ReleaseDiff`: a pergunta "o que mudou entre duas releases"

**Data:** 2026-08-31
**Status:** **proposta**.
**Origem:** segundo sub-projeto da decomposição do
`PROMPT MESTRE — EVOLUÇÃO TOTAL GLUE + EMR DO SPARKFORGE AWS.md` (§8.2 e §4).
O primeiro — [EMR on EKS](2026-08-31-sparkforge-emr-eks-design.md) — está
fechado.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: a busca que não retorna nada

A busca por `release_diff`, `ReleaseDescriptor` e `release_descriptor` em
`sparkforge/`, `rules/` e `knowledge/` **não retorna nada**. O motor sabe dizer
em que runtime um job rodou; não sabe dizer **o que mudou** entre dois runtimes.

Isso é o que falta para responder a pergunta que o operador traz antes de toda
migração: *"vou de `emr-6.15.0` para `emr-7.5.0` — o que quebra?"*

## 2. A lacuna que vem antes, e ela é de dado

Medido em 2026-08-31, as quatro matrizes de runtime deste repositório estão em
**três formas diferentes**:

| Plataforma | Forma | Onde |
|---|---|---|
| AWS Glue | **YAML** com fonte e data por célula | `knowledge/glue/runtime-matrix.yaml`, carregada por `runtime_matrix.load()` |
| EMR Serverless | **YAML** com vocabulário fechado | `knowledge/emr-serverless/runtime-matrix.yaml`, `load_emr_serverless()` — criada no sub-projeto 1 |
| EMR on EC2 | **dicionário Python, em código** | `EMR_MATRIX`, `sparkforge/facts/runtime_detect.py:111`, 30 releases |
| EMR on EKS | **só prosa Markdown** | `knowledge/emr-eks/runtime-matrix.md` |

E há **duplicação medida**: `GLUE_MATRIX` (`runtime_detect.py:70`) repete as cinco
versões de `knowledge/glue/runtime-matrix.yaml` com os mesmos valores — mas a
cópia em código **não tem fonte, não tem data de leitura e tem menos colunas**
(falta `scala` e `java`). Duas cópias do mesmo fato, uma delas sem lastro.

**Diff determinístico exige as quatro na mesma forma.** Um `ReleaseDiff` que lesse
YAML para Glue, um `dict` de código para EC2 e prosa para EKS não seria
determinístico — seria três mecanismos com um nome só, que é exatamente a
segunda arquitetura que a §2.2 do prompt mestre proíbe.

## 3. Objetivo

Três coisas, nesta ordem, porque cada uma é pré-requisito da seguinte:

1. **Uma forma só de matriz**, com fonte e data por célula, para as quatro
   plataformas — e o código lendo dela, não de cópia.
2. **`ReleaseDescriptor`** — o que uma release *é*: plataforma, rótulo,
   componentes com versão, e a procedência de cada valor.
3. **`ReleaseDiff`** — o que mudou entre dois descritores, de forma determinística
   e com o que **não** se pode afirmar saindo nomeado.

### Não-objetivos, com razão registrada

- **`MigrationAssessment` para EMR.** É o sub-projeto 3, e depende deste.
- **Release notes estruturadas.** Ver §5: o diff afirma o que a matriz sustenta,
  e recusa o resto por nome.
- **Regras novas de diagnóstico.** Este sub-projeto entrega dado e verbo; se o
  diff revelar julgamento que mereça regra, ele entra depois, com fixture.

## 4. Decisões de desenho

### D-1 — uma matriz por plataforma, em YAML, com o guard de drift que já existe

`knowledge/<plataforma>/runtime-matrix.yaml` para as quatro, no molde do que
Glue e EMR Serverless já usam: célula com valor, `sources` e `retrieved`.

O par `.md` + `.yaml` **fica**, e a razão está medida no sub-projeto 1: o
Markdown é onde a prosa explica o que a fonte não sustenta, e o YAML é o espelho
executável. O que os liga é um **guard de drift** que compara o YAML contra a
tabela do `.md` — se divergirem, o teste reprova. Sem ele, o espelho envelhece
calado.

### D-2 — o código lê a matriz; não a repete

`GLUE_MATRIX` e `EMR_MATRIX` em `sparkforge/facts/runtime_detect.py` deixam de
ser literais e passam a ser carregados de `knowledge/`. É remoção de duplicação
com defeito já medido: a cópia de Glue em código não carrega fonte nem data.

**Cuidado que a implementação precisa ter:** `runtime_detect` é caminho quente e
tem 30 releases de EMR; carregar YAML a cada chamada seria regressão. Use o mesmo
`lru_cache` que `runtime_matrix.load()` já usa.

### D-3 — `ReleaseDescriptor` é leitura, não julgamento

```
ReleaseDescriptor:
  platform: glue | emr_ec2 | emr_serverless | emr_eks
  release: str                    # o rótulo como a fonte o publica
  components: {nome: Component}   # spark, python, scala, java, iceberg, hudi, delta, hadoop...
  unresolved: [str]               # componente que a fonte daquela plataforma NAO publica
  sources: [...]
```

`Component` carrega `version`, `sources` e `retrieved`. **Componente que a fonte
não publica entra em `unresolved`, nomeado** — não sai como string vazia nem
ausente em silêncio. É a §20 do `CLAUDE.md`: recusa tem nome.

Isso importa porque as quatro plataformas publicam conjuntos **diferentes**: o
sub-projeto 1 mediu que EMR on EKS publica Spark, Iceberg, Hudi e Delta, e **não**
publica Hadoop (0 de 34 páginas) nem Python (2 de 34, em prosa). Um descritor que
apagasse essa diferença mentiria por omissão.

### D-4 — `ReleaseDiff` compara dentro da plataforma, e recusa entre plataformas

Diff entre `emr-6.15.0` e `emr-7.5.0` **na mesma plataforma** é comparação
legítima. Diff entre `emr-7.7.0` no EC2 e `emr-7.7.0` no EKS **também é** — e é
justamente onde mora o achado que o sub-projeto 1 mediu: o mesmo rótulo publica
Iceberg `1.7.1-amzn-0` no EC2 e `1.6.1-amzn-2` no EKS.

O que **não** é comparação legítima é somar as duas: um diff que apresentasse
"Iceberg mudou de 1.6.1 para 1.7.1" sem dizer que a mudança é de **plataforma** e
não de **release** inverteria a causa. Por isso o diff carrega o eixo da
comparação (`release` ou `platform`) e o declara na saída.

### D-5 — o diff afirma o que a matriz sustenta, e nomeia o resto

O §8.2 do prompt mestre pede sete dimensões:

```
added, removed, deprecated, default_changes,
compatibility_changes, security_changes, performance_changes
```

Medido: as matrizes sustentam **versão de componente**, e mais nada. `deprecated`,
`security_changes` e `performance_changes` vivem em release notes, que não estão
estruturadas em `knowledge/`.

A saída, portanto, preenche o que tem lastro e emite as demais como
`*.unresolved` **com a medida que as destravaria** — nunca como lista vazia, que
o operador leria como "não mudou nada".

Listar a recusa é a diferença entre "não sei" e "não perguntei".

### D-6 — sem área de regra nova

Este sub-projeto entrega dado (`knowledge/`), modelo (`ReleaseDescriptor`),
verbo (`ReleaseDiff`) e superfície (CLI/MCP). **Nenhuma regra.** Se o diff
revelar julgamento que mereça uma, ela entra depois com fixture positiva e
negativa, como toda regra deste catálogo.

Isso mantém a §2.2 do prompt mestre: estende o que existe, não cria arquitetura
paralela.

## 5. Superfície

```
sparkforge_release_describe   plataforma + release -> ReleaseDescriptor
sparkforge_release_diff       plataforma(s) + duas releases -> ReleaseDiff
CLI: sparkforge release describe / sparkforge release diff
```

Paridade CLI/MCP obrigatória, como toda capacidade determinística deste
repositório.

## 6. Testes e gates

- **Guard de drift por plataforma**: YAML × tabela do `.md`, as quatro.
- **Todo componente de todo descritor** ou tem versão com fonte, ou está em
  `unresolved` — nunca vazio em silêncio.
- **Diff determinístico**: mesma entrada, mesma saída, ordenação estável.
- **O contrafactual de plataforma**: `emr-7.7.0` no EC2 contra o mesmo rótulo no
  EKS produz diff **não vazio**, e ele declara eixo `platform`. É o teste que
  prova que a normalização não apagou a divergência que o sub-projeto 1 mediu.
- **Nenhuma regressão em `runtime_detect`**: os testes de detecção de runtime
  passam sem mudança de comportamento depois de a matriz sair do código.
- Gates de sempre: `check_surface_lock.py --update` com o crescimento declarado,
  `refresh_knowledge.py --offline --update` para fonte nova, `check_vnext_claims.py`
  em exit 0, suíte em lotes.

## 7. Critérios de conclusão

- As quatro plataformas têm matriz YAML com fonte e data por célula, e um guard
  que a compara com a prosa.
- `GLUE_MATRIX` e `EMR_MATRIX` não existem mais como literais em código.
- `ReleaseDescriptor` nomeia em `unresolved` todo componente que a fonte daquela
  plataforma não publica.
- `ReleaseDiff` é determinístico, declara o eixo da comparação, e emite
  `*.unresolved` para as dimensões que a matriz não sustenta.
- O diff `emr-7.7.0` EC2 × EKS reproduz a divergência medida no sub-projeto 1.
- CLI e MCP em paridade; gates verdes; suíte em lotes.

## 8. Desvios

Vazio. Preenchido quando a implementação medir algo que torne o texto acima
errado.
