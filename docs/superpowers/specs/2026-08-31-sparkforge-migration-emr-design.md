# SparkForge AWS — `MigrationAssessment` para EMR: a ponte é o Spark, não o EMR

**Data:** 2026-08-31
**Status:** **CONCLUÍDA** em 2026-09-01.
**Origem:** terceiro sub-projeto da decomposição do
`PROMPT MESTRE — EVOLUÇÃO TOTAL GLUE + EMR DO SPARKFORGE AWS.md` (§8.2, §11-E).
Depende do segundo — [`ReleaseDescriptor` / `ReleaseDiff`](2026-08-31-sparkforge-release-diff-design.md) —, que está fechado.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. O que existe, e por que ele é só de Glue

`sparkforge/migration/assessment.py` responde *"o que quebra ao migrar de X para Y"*
e faz isso **sem bifurcar o motor**: `version_path.steps(source, target)` decompõe
o caminho em degraus, e cada degrau chama o mesmo `judge` do catálogo, com o
runtime do **alvo** daquele degrau. O que o módulo acrescenta é agregação — em
qual salto cada finding nasceu — mais dois gates: compatibilidade e consumidor.

Ele funciona para Glue porque **existem regras guardadas por versão de Glue**.

## 2. A medição que decide a forma deste sub-projeto

Contado no catálogo de 140 regras, em 2026-08-31:

```
runtime_scope por eixo:  {'glue': 13, 'spark': 5, 'iceberg': 1}
```

**Zero regras têm `emr` em `runtime_scope`.**

Isso mata a leitura ingênua deste sub-projeto — "é só trocar `glue` por `emr` no
`version_path`". Um `assess` de EMR construído assim rodaria o catálogo inteiro
por degrau e **não acharia nada**, porque nenhuma regra fala de versão de EMR. E
o pior: sairia verde, que o operador leria como "nada quebra".

### A ponte, e ela existe desde o sub-projeto 2

**Cinco regras são guardadas por versão de Spark**, não de plataforma. E as quatro
matrizes de runtime — normalizadas na frente A do sub-projeto 2 — publicam a
versão de Spark de cada release, das quatro plataformas.

Ou seja: o caminho `emr-6.15.0 → emr-7.5.0` **tem** runtime derivável por degrau,
e as cinco regras `spark` passam a ser alcançáveis para EMR pela primeira vez.

O que o assessment de EMR afirma, portanto, é o que a evidência sustenta:

1. **o que muda de componente** por degrau (`ReleaseDiff`, do sub-projeto 2);
2. **as regras guardadas por Spark** que o degrau ativa;
3. **os gates que já existem** — compatibilidade e consumidor;
4. **e, em voz alta, o que ele NÃO cobre**: breaking change específico de EMR,
   porque nenhuma regra o descreve ainda.

## 3. Objetivo

Estender `sparkforge/migration/` para as quatro plataformas, sem bifurcar o motor
e sem prometer cobertura que o catálogo não tem.

### Não-objetivos, com razão registrada

- **Escrever regras `SF-MIG` para EMR.** Regra exige fonte primária, golden
  positivo e negativo e área com rota. É trabalho próprio, e fazê-lo como efeito
  colateral deste sub-projeto produziria regra sem corpus.
- **Inventar `runtime_scope: {emr: ...}`.** O eixo não existe no `version_scope`
  hoje; acrescentá-lo sem regra que o use seria mecanismo sem consumidor.
- **Iceberg × consumidores × Lake Formation.** É o sub-projeto 4.

## 4. Decisões de desenho

### D-1 — `version_path` ganha plataforma, e a ordenação é da matriz

`steps(source, target)` hoje conhece a ordem das versões de Glue. Para EMR, a
ordem vem da **matriz**, não de uma lista nova em código — é a mesma disciplina
da D-2 do sub-projeto 2, que tirou `EMR_MATRIX` de dentro do `.py`.

Cuidado medido: EMR tem **duas séries** (6.x e 7.x) e rótulos fora do padrão
(`emr-spark-8.0.0`). Caminho que atravessa séries é legítimo; caminho que inclui
rótulo fora do padrão de versão precisa **recusar por nome**, não ordenar
alfabeticamente.

### D-2 — o runtime de cada degrau vem da matriz da plataforma, nunca de outra

Repetição deliberada da regra que este repositório já pagou duas vezes: a
`EMR_MATRIX` de EC2 **não** descreve EKS nem Serverless, e o sub-projeto 1 mediu
que ela **diverge** — Iceberg em 6 de 26 releases comparáveis. `build_runtime` já
recusa `--emr` sobre facts `emrc.*`; o assessment não pode reabrir a porta por
outro caminho.

### D-3 — cobertura declarada, e ela é a entrega mais importante

A saída carrega, obrigatoriamente, **quais eixos de `runtime_scope` o caminho
ativou** e **quantas regras do catálogo eram alcançáveis**. Para um caminho de
EMR isso hoje é: 5 regras por `spark`, 0 por `emr`.

Sem esse campo, um assessment de EMR sem achados é indistinguível de um job sem
problemas. Com ele, o operador lê "nenhuma regra deste catálogo descreve breaking
change de EMR; o que foi avaliado foi Spark e componente" — que é a verdade.

É a §20 do `CLAUDE.md` aplicada ao verbo inteiro em vez de a uma propriedade.

### D-4 — sem área de regra nova, sem tool nova se a existente servir

`sparkforge_migration_assess` já existe. **Meça** se ela aceita plataforma; se
aceitar por parâmetro novo, é extensão e não tool nova. Tool nova só se a
fronteira medida exigir.

## 5. Testes e gates

- Caminho de EMR entre séries (`6.15.0 → 7.5.0`) produz degraus na ordem da
  matriz, e cada degrau tem runtime com `spark` preenchido.
- **O contrafactual da cobertura:** um assessment de EMR sem achados declara
  `0 regras por eixo emr` — há teste que reprova se o campo sumir.
- Rótulo fora do padrão (`emr-spark-8.0.0`) é recusado por nome, não ordenado.
- Nenhuma regressão no assessment de Glue: os goldens de `fixtures/migration/`
  passam sem mudança.
- Runtime de um degrau de EKS nunca sai da matriz de EC2 — o contrafactual da
  dívida que o sub-projeto 1 fechou vale aqui também.
- Gates de sempre: paridade CLI/MCP, `check_surface_lock.py --update`,
  `check_vnext_claims.py` em exit 0, suíte em lotes.

## 6. Critérios de conclusão

- `version_path` e `assess` aceitam as quatro plataformas, com a ordem vinda da
  matriz.
- A saída declara a cobertura por eixo, e há teste que a prende.
- Nenhum runtime de uma plataforma é derivado da matriz de outra.
- Assessment de Glue inalterado, goldens intactos.
- Gates verdes.

## 7. Desvios

Três, todos medidos durante a construção. Nenhum muda o objetivo da §3.

**D-a — a CLI ganhou um verbo, `migrate emr`, e não uma flag em `migrate glue`.**
A D-4 falava da tool MCP, e ali a medida deu extensão: `sparkforge_migration_assess`
já compunha os artefatos, já expandia o par e já agregava, e o que faltava era só a
plataforma — virou o parâmetro `platform`, sem tool nova (63 antes, 63 depois). Na
CLI a mesma leitura não cabe: `migrate glue` carrega a plataforma **no nome**, e um
`--platform` ali criaria `migrate glue --platform emr_eks`. As três de EMR, ao
contrário, dividem tudo o que importa aqui — o mesmo vocabulário de rótulo, a mesma
normalização do prefixo `emr-`, o mesmo eixo `emr` valendo zero —, e o que as separa
é qual matriz responde: isso é parâmetro, e `migrate emr --platform` o expõe. A
união dos dois verbos cobre as quatro plataformas que a tool aceita, que é o que a
paridade CLI/MCP cobra.

**D-b — a declaração de cobertura separa *julgável* de *alcançada*, e a §2 falava
só de uma.** A §2 lê "5 regras por `spark`, 0 por `emr`", e as duas contagens são do
CATÁLOGO. Medido no caminho da §5 (`emr_ec2`, `6.15.0 → 7.5.0`): as cinco regras de
`spark` ficam **julgáveis** — a chave `spark` existe no runtime de todo degrau,
porque a matriz publica o Spark de cada release —, e **zero** delas entram no escopo,
porque quatro pedem Spark 4 e a série 7.x do EMR está na 3.5. Dizer "5 alcançáveis"
seria falso; dizer só "0" esconderia que a ponte existe e funciona. `coverage` emite
as três medidas por eixo (`catalog_rules`, `reachable_rules`, `runtime_key_present`)
e a prosa as usa nessa ordem.

**D-c — `component_diff` separa a recusa do degrau da recusa da plataforma.** A §2
pede "o que muda de componente por degrau", e a implementação projeta o `ReleaseDiff`
uma vez por degrau. O que a construção obrigou a decidir foi o `unresolved`: as cinco
dimensões do §8.2 sem lastro são constantes do verbo, e um eixo que a fonte daquela
plataforma não publica em release nenhuma (`hudi` e `delta` no EC2, `hadoop` no EKS)
é constante da plataforma — repetir os textos inteiros em cada degrau de um caminho
de seis degraus é payload sem informação nova. Os dois grupos sobem para
`component_diff_unresolved`, uma vez; `RELEASE_CELL_ABSENT`, que é de um lado
específico, fica no degrau que a encontrou. Nada é omitido: lista vazia seria lida
como "não mudou nada".
