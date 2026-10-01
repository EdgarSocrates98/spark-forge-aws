# SparkForge AWS — Migração de Control-M: a capacidade que o job usa, degrau a degrau

**Data:** 2026-09-02
**Status:** **proposta**.
**Origem:** quarto incremento de `prompt_evo_spark_bmc.md` (§66), depois da auditoria
que as §64–69 nunca tinham tido.
**Depende de:** [incremento 1](2026-09-01-sparkforge-controlm-conhecimento-design.md)
(matriz de 31 versões, PR #23) e [incremento 2](2026-09-01-sparkforge-controlm-jobs-as-code-design.md)
(extrator `ctm.*` e o cruzamento de `SF-CTM-001`, PR #24).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. A auditoria que faltava, e o que ela mediu

As §64–69 nunca tinham sido auditadas — o operador recusou a auditoria de propósito
para priorizar entrega, e a memória do projeto registra isso. Feita em 2026-09-02:

| Seção | Estado | Prova |
|---|---|---|
| **§64** ingestão de conhecimento | **EXISTE, parcial** | `scripts/refresh_knowledge.py` + `knowledge/sources.lock.json` com **225 fontes, 5 da BMC**. O mecanismo está pronto; falta largura — só a página `API/Monthly` está vigiada |
| **§65** release watcher | **NÃO EXISTE** como agente; o guard de drift **existe** (`tests/test_runtime_matrix_drift.py`, Control-M é a quinta plataforma nele) |
| **§66** migration engine | **EXISTE, sem Control-M** | `migration_assess(path, source, target, platform="glue")`, com `version_path.platforms()` devolvendo `('glue', 'emr_ec2', 'emr_serverless', 'emr_eks')` |
| **§68/69** Git e CI-CD | **parcial** | `ctm build`/`ctm deploy` já citados em `facts/controlm_jobs.py` e nas descrições de tool |

**O padrão do prompt irmão se repete:** o motor já faz a maior parte, e o que falta é
mais estreito do que o prompt sugere.

## 2. As duas formas NÃO são a mesma, e essa é a decisão central

`migration.release_descriptor.describe(platform, version)` devolve
`components: {nome: Component(version)}` — mapa componente → versão. É o que
`_runtime_for` consome para montar o `runtime` de cada degrau.

`controlm.descriptor.describe(version)` devolve `VersionDescriptor` com dez campos, e
os que importam aqui são outros: **`capabilities`** (cada uma com `boundary` ∈
`introduced_in`, `changed_in`, `deprecated_from`, `discontinued_in`) e **`deprecated`**.

Ou seja: a forma de Control-M é **mais rica para migração** do que a de Glue e EMR.
Glue compara versão de componente; Control-M compara **conjuntos de capacidade com
fronteira declarada**, que é exatamente o que uma migração precisa saber.

### Não-objetivos, com razão registrada

- **Não haverá eixo `controlm` em `runtime_scope`.** A D-f do incremento 2 já decidiu
  isso e a razão não mudou: `runtime_scope` guarda a versão do `RuntimeContext` (Glue,
  Spark, Python, Iceberg), e nada ali conhece `9.0.2x.yyy`. A versão de Control-M é
  **dado do artefato**, e viaja em `declared_version` — que já é parâmetro de
  `extract_controlm_jobs`.
- **Não haverá interpolação entre versões.** A regra 12 do `CLAUDE.md` vale aqui:
  compare as versões que a matriz **publica**, e recuse extrapolar. A fonte anda de 5
  em 5, e `9.0.21.301` não existe.
- **Não haverá plano de deploy nem test suite gerada.** A §66 pede `deployment plan`,
  `generated definitions` e `test suite`. Gerar definição de job seria escrever o
  artefato do cliente a partir de uma matriz — e a matriz nomeia capacidade, não
  sintaxe. Vira veto escrito.

## 3. Objetivo

`migration_assess(..., platform="controlm")` responde, para um artefato de
`Jobs-as-Code`: **qual capacidade que este job usa muda entre a versão de origem e a de
destino, e em qual degrau.**

## 4. Decisões de desenho

### D-1 — o degrau reexecuta o cruzamento que já existe

O incremento 2 entregou `ctm.capability_supported` / `_incompatible` / `_unresolved`,
emitidos pelo extrator ao cruzar as capacidades do job contra a matriz numa versão
declarada. Migrar de `A` para `B` é rodar esse mesmo cruzamento **uma vez por versão do
caminho**, e reportar onde o veredito muda.

Nada de mecanismo novo: `version_path` expande o par em degraus, e cada degrau chama o
extrator com `declared_version` daquele degrau.

**O contrafactual que prova que o cruzamento é real:** o mesmo job em
`9.0.21.300` e em `9.0.22.005` produz vereditos **diferentes** para
`Job:DetachedEmbeddedScript`. Se não produzir, o assessment está passando adiante o
mesmo resultado com rótulos diferentes.

### D-2 — o eixo de Control-M é CAPACIDADE, e o de Glue é componente

`_runtime_for` não serve, e forçá-lo a servir achataria os dois eixos — que é
exatamente o erro que a D-1 do incremento 1 recusou por escrito.

Então o caminho de Control-M tem composição própria: em vez de `runtime` → `judge`, ele
compara os conjuntos de `ctm.capability_*` entre degraus. O resultado sai na **mesma
forma** de `MigrationAssessment` (degraus, achados por degrau, agregado, gate), porque a
forma do relatório é contrato com quem consome — só a fonte do veredito muda.

### D-3 — as quatro fronteiras não valem o mesmo

`introduced_in` migrando **para frente** é ganho, não risco. `deprecated_from` é aviso.
`discontinued_in` é quebra. `changed_in` é o mais traiçoeiro: a capacidade continua lá e
se comporta diferente.

O gate de compatibilidade precisa distinguir as quatro, e um relatório que as some num
"N mudanças" esconderia a única que quebra o job.

### D-4 — migração para TRÁS é caso legítimo, e é onde `introduced_in` morde

Descer de `9.0.22.005` para `9.0.21.300` inverte o sinal de toda fronteira: o que era
ganho vira perda. O motor não pode assumir que `source < target`.

## 5. Testes e gates

- **O contrafactual da D-1**, com o par de versões que o incremento 1 já usa como prova.
- **As quatro fronteiras** têm caso: uma capacidade `introduced_in` no meio do caminho,
  uma `deprecated_from`, uma `discontinued_in`, uma `changed_in`.
- **Migração para trás** com a mesma capacidade, e o veredito oposto.
- **Versão fora da faixa** e **versão que a fonte não publica** continuam recusas
  distintas (`version_outside_covered_range` e `version_not_published_by_source`, a D-g
  do incremento 1).
- Zero regressão no assessment de Glue e das três de EMR — o ramo delas não é tocado.
- Gates de sempre, incluindo `check_recall_economy.py` e o gate de lastro **em cada
  commit que acrescente `.py`**.

## 6. Critérios de conclusão

- `platform="controlm"` responde, e `version_path.platforms()` a inclui.
- As quatro fronteiras saem separadas, e o gate distingue quebra de aviso.
- Migração para trás inverte o sinal, com teste.
- Nenhum eixo `controlm` em `runtime_scope`, e a razão escrita.
- Os vetos da §66 que não têm fonte estão declarados.

## 7. Fora do escopo

| | |
|---|---|
| §65 release watcher | o guard de drift já dispara; transformar alarme em proposta é fase própria |
| §64 largura de fontes | medir o que cada página sustenta **antes** de vigiar — a varredura anterior achou 3 defeitos de janela, 2 de dependência e **zero** de SLA |
| §68/69 Git e CI-CD | são processo, não artefato. A única coisa conferível seria julgar YAML de CI, que este motor não lê |
| `deployment plan`, `generated definitions`, `test suite` | veto: a matriz nomeia capacidade, não sintaxe |
