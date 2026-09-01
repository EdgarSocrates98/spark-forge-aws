# SparkForge AWS — `MigrationAssessment` para EMR: a ponte é o Spark, não o EMR

**Data:** 2026-08-31
**Status:** **proposta**.
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

Vazio.
