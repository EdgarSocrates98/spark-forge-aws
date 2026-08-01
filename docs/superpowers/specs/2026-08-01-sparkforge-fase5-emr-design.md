# SparkForge AWS — Fase 5: Cobertura de EMR e Escopo por Natureza

**Data:** 2026-08-01
**Status:** aprovado para planejamento
**Depende de:** [Fase 4](2026-07-31-sparkforge-fase4-agentes-design.md) — os coordenadores são onde a área nova se pendura
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o gap não é o que parecia

O foco do repositório é agente autônomo que avalia projetos Spark, PySpark, Glue e **EMR**. O `RuntimeContext` conhece `glue`, `spark`, `python`, `iceberg` e `athena` — **não conhece `emr`**.

A primeira leitura desse gap foi "44 das 48 regras já avaliam num runtime sem `glue`, falta só o eixo de infraestrutura". Medição mais fina mostra um problema anterior a esse, e pior.

**25 regras declaram `runtime_scope: {glue: "*"}`.** O curinga casa com qualquer coisa, então elas avaliam num job EMR. Mas `glue: "*"` significa **"qualquer versão de Glue"**, não **"qualquer runtime"** — e as duas coisas foram confundidas na escrita do catálogo.

Repartindo as 25 pela natureza do fact que exigem:

| Área | Regras | Facts de | Natureza |
|---|---|---|---|
| SF-PY | 12 | `pyspark` | código — agnóstica |
| SF-PQ | 3 | `catalog`, `s3` | armazenamento — agnóstica |
| SF-PLAN | 2 | `plan` | plano físico — agnóstica |
| SF-CG | 1 | `callgraph` | estrutura — agnóstica |
| SF-UI | 1 | `spark` | event log — agnóstica |
| SF-ENV | 1 | `env` | agnóstica |
| **SF-GLUE** | **5** | `tf`, `pyspark`, `spark` | **infra Glue — específica** |

**20 são agnósticas** e estão marcadas como se fossem de Glue. **5 são genuinamente de infra Glue** — leem `aws_glue_job` do Terraform.

### O defeito que isso produz

Num job EMR, as 5 SF-GLUE **avaliam e nunca disparam**, por falta de fact `tf.resource` do tipo certo. Não dá erro. Dá **silêncio**.

Para um agente autônomo, silêncio lê como "nada encontrado" — quando a verdade é "esse eixo não foi coberto". É a mesma distinção que `pyspark.unresolved` existe para preservar no analisador, um nível acima: a diferença entre *não há problema ali* e *ninguém olhou ali*.

O mecanismo de ausência explicada **já existe**: `judge --show-skipped` reporta regra pulada por guarda de versão, com o motivo. Ele não dispara hoje porque o curinga faz a regra passar pela guarda.

## 2. Objetivo

EMR on EC2 como runtime de primeira classe, e escopo de regra dizendo o que a regra realmente significa.

**Critério de sucesso:** uma investigação sobre job EMR produz achados de código, plano e armazenamento normalmente, e reporta as regras de infra Glue como **puladas por runtime, com motivo** — nunca em silêncio.

### Não-objetivos

| Fora de escopo | Razão |
|---|---|
| EMR Serverless | Modelo diferente (application, pre-initialized capacity, sem instance fleet). Fase seguinte, com o eixo já provado |
| EMR on EKS | Traz vocabulário de Kubernetes que não existe em lugar nenhum do repositório |
| Reescrever escopo das 23 regras já específicas | Só as 25 com curinga entram; as que já declaram `spark`, `iceberg` ou `athena` estão corretas |

## 3. Decisões

| # | Decisão | Alternativa rejeitada | Razão |
|---|---|---|---|
| F5-D1 | Reetiquetar as 20 agnósticas por natureza, antes de acrescentar EMR | Só somar `SF-EMR` e deixar o curinga | Sem isso, as 5 SF-GLUE seguem avaliando em silêncio num job EMR, e a área nova nasce sobre um escopo que mente |
| F5-D2 | As 5 SF-GLUE mantêm `{glue: "*"}` e passam a ser **puladas** em EMR | Escopo explícito por runtime em toda regra | Toca 48 regras e exige 48 decisões; o ganho está nas 25 com curinga, não nas que já são precisas |
| F5-D3 | EMR on EC2 primeiro | Os três sabores juntos | EC2 é o mais usado e o de artefato mais próximo do que os extratores já leem |
| F5-D4 | `emr` entra como chave de `RuntimeContext`, ao lado de `glue` | Um campo `platform` com valor `glue`/`emr` | A guarda de versão já opera por chave; um enum novo exigiria mudar `in_scope`, que é código provado e testado nas bordas |
| F5-D5 | Detecção de EMR não resolve divergência silenciosamente | Escolher a fonte mais confiável | Herdado da Fase 0: divergência vira `SF-ENV-001`, não é resolvida pelo extrator |

## 4. Arquitetura

### 4.1 Reetiquetagem, primeiro

As 20 agnósticas trocam `{glue: "*"}` pelo escopo que descreve o que elas de fato exigem:

- **SF-PY (12), SF-CG (1)** — análise de AST e de grafo de chamadas. Não dependem de versão de Spark para o padrão existir; o escopo honesto é o mais aberto que ainda diga algo. Candidato: `{spark: ">=3.0"}`, coerente com o que SF-PLAN e SF-UI já usam.
- **SF-PLAN (2), SF-UI (1)** — plano físico e event log. Mesmo escopo.
- **SF-PQ (3)** — catálogo e listagem S3. Armazenamento não depende do motor; candidato a escopo próprio ou ao mesmo.
- **SF-ENV (1)** — decidir caso a caso, lendo a regra.

O escopo exato de cada uma é decisão do plano, **regra a regra, lendo o que ela exige** — não uma substituição em massa. Uma reetiquetagem errada apaga a regra do relatório num runtime onde ela valia, que é o defeito que `tests/test_runtime_glue_versions.py` já existe para pegar.

### 4.2 `emr` no `RuntimeContext`

`RuntimeContext` ganha o campo `emr` — o **release label** (`emr-7.5.0`). A matriz de derivação ganha a tabela EMR → Spark/Python/Iceberg, no mesmo formato de `GLUE_MATRIX` e com o mesmo guard de drift contra o documento em `knowledge/`.

`glue` e `emr` são mutuamente exclusivos na prática: um job roda num ou noutro. Detectar os dois é divergência, e vira `SF-ENV-001`.

### 4.3 Extrator de EMR on EC2

`sparkforge/facts/emr_cluster.py`, lendo dump JSON já coletado (`describe-cluster`, `list-instance-groups`/`list-instance-fleets`, `list-bootstrap-actions`, `list-configurations`) — mesma disciplina dos outros: **entrada é artefato local, sem rede**, e a coleta fica em `collect/aws.py`, extra `[aws]`.

Kinds candidatos, a fechar no plano: release label, tipo e contagem de instância por grupo ou fleet, uso de spot, EBS, bootstrap actions, configurações de `spark-defaults`, e a sentinela `emr.analyzed` mais `emr.unresolved`.

### 4.4 Área `SF-EMR`

Regras de infra EMR, com fixture bidirecional por regra — o invariante da Fase 2 exige que toda regra tenha fixture que a faça disparar, e a contraparte negativa.

O conteúdo das regras é decisão do plano, com fonte pesquisada. Candidatos que a documentação da AWS sustenta: instância spot no nó master, ausência de EBS onde o workload derrama, configuração de `spark-defaults` conflitando com o que o job seta, e bootstrap action que falha silenciosamente.

### 4.5 Coordenador

`SF-EMR` precisa de coordenador, pelo invariante da Fase 4 (`test_no_area_is_orphan`). Duas saídas, a decidir no plano: `glue-infra-reviewer` alarga o escopo e vira algo como revisor de infraestrutura de job — mas o nome fica errado —, ou nasce um `emr-infra-reviewer` irmão. O invariante força a decisão; ele não a toma.

## 5. Testes

| Camada | Teste |
|---|---|
| reetiquetagem | Nenhuma regra agnóstica é pulada num runtime EMR; as 5 SF-GLUE **são**, com motivo |
| matriz EMR | `EMR_MATRIX` bate com o documento em `knowledge/`, como `GLUE_MATRIX` já faz |
| exclusividade | `glue` e `emr` detectados juntos produzem `SF-ENV-001` |
| extrator | Golden por fixture; `emr.unresolved` para dump não reconhecido |
| regras SF-EMR | Fixture positiva e negativa por regra |
| cobertura | `SF-EMR` com coordenador; tools novas alcançáveis |
| ausência explicada | Investigação sobre EMR reporta as SF-GLUE como puladas, e o teste falha se elas sumirem em silêncio |

O último é o que prova o objetivo desta fase.

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Reetiquetagem apaga regra de um runtime onde ela valia | Decisão regra a regra, com teste por runtime nas bordas — o padrão de `test_runtime_glue_versions.py` |
| `EMR_MATRIX` envelhecer | Guard de drift contra o documento, e a fonte entra na watchlist do `refresh_knowledge` |
| Escopo agnóstico virar novo curinga disfarçado | `{spark: ">=3.0"}` ainda é falso-fechado quando `spark` não é detectado; a guarda continua valendo |
| Nome do coordenador ficar errado ao alargar escopo | Decisão explícita no plano, não implícita na implementação |

## 7. Critérios de aceitação

1. As 20 regras agnósticas reetiquetadas, uma a uma, com justificativa.
2. As 5 SF-GLUE puladas num runtime EMR, com motivo visível em `judge --show-skipped`.
3. `emr` em `RuntimeContext`, com `EMR_MATRIX` e guard de drift contra o documento.
4. `glue` e `emr` juntos produzem `SF-ENV-001`.
5. Extrator de EMR on EC2, com sentinela e `unresolved`.
6. Área `SF-EMR` com fixture bidirecional por regra.
7. `SF-EMR` com coordenador; invariante de cobertura verde.
8. Investigação sobre EMR produz achados de código, plano e armazenamento normalmente.
9. Suíte verde e maior; ruff, espelhos e evals verdes.
10. `README.md`, `AGENTS.md`, `STATUS.md`, `knowledge/` e o spec da fase atualizados e referenciando o que é novo.
