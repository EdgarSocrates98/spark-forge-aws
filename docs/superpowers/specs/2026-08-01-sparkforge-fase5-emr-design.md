# SparkForge AWS — Fase 5: Cobertura de EMR e Escopo por Natureza

**Data:** 2026-08-01
**Status:** implementado em parte. A fase foi **partida em duas**.

- **5a — correção de escopo: CONCLUÍDA** em 2026-08-01, branch `feat/fase5a-escopo`.
  Fecha §3.1, §3.2 e os critérios 10, 11 e 13. Plano:
  [`../plans/2026-08-01-sparkforge-fase5a-escopo.md`](../plans/2026-08-01-sparkforge-fase5a-escopo.md).
  A execução encontrou três famílias do mesmo erro de camada que este spec não
  previu — `{athena: "*"}`, `{iceberg: ">=1.0.0"}` e o `{spark: ">=3.0"}` que a
  própria correção introduziu. Ver `STATUS.md`, seção "Fase 5a".
- **5b — EMR on EC2: CONCLUÍDA** em 2026-08-01, branch `feat/fase5b-emr`. Fecha
  os critérios 3, 4, 5, 6, 7, 8, 9, 12 e 14. Plano:
  [`../plans/2026-08-01-sparkforge-fase5b-emr.md`](../plans/2026-08-01-sparkforge-fase5b-emr.md).
  A pesquisa de fontes derrubou três premissas deste documento — `aws emr
  list-configurations` não existe, faltavam dois dumps na lista da §4.3, e três
  dos quatro candidatos de regra da §4.4 não sobreviveram na forma escrita. Ver
  `STATUS.md`, seção "Fase 5b". **EMR Serverless e EMR on EKS ficam de fora**,
  por decisão registrada aqui: esta fase é EMR on EC2.
- **O restante deste documento** — `emr` no
  `RuntimeContext`, `EMR_MATRIX`, extrator de cluster, área `SF-EMR`, coordenador,
  e a divergência de plataforma da §3.3 — segue válido e sem plano escrito.
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

O mecanismo de ausência explicada **já existe e funciona**: `judge --show-skipped` reporta regra pulada, com o motivo (`runtime_scope`, `blocked_on` ou `requires_facts`). Confirmado por execução na revisão deste spec — não é o caso de documento afirmando caminho inexistente.

Ele não dispara para as SF-GLUE por **dois** motivos independentes, e a §3.1 e a §3.2 tratam cada um: o curinga `"*"` faz a regra passar pela guarda de versão, e `SF-GLUE-002` ainda satisfaz `requires_facts` por ancorar num sentinela genérico.

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
| F5-D2 | **`in_scope` passa a exigir presença da chave no curinga `"*"`** | Manter o curinga como está; ou dar escopo explícito por runtime às 5 SF-GLUE | Ver §3.1 — sem isto a fase não tem como cumprir o próprio objetivo |
| F5-D2b | `SF-GLUE-002` é reancorada em fact específico de `aws_glue_job` | Deixar como está | Ver §3.2 — hoje ela some de findings **e** de skipped |
| F5-D3 | EMR on EC2 primeiro | Os três sabores juntos | EC2 é o mais usado e o de artefato mais próximo do que os extratores já leem |
| F5-D4 | `emr` entra como chave de `RuntimeContext`, ao lado de `glue` | Um campo `platform` com valor `glue`/`emr` | A guarda de versão já opera por chave; um enum novo exigiria mudar `in_scope`, que é código provado e testado nas bordas |
| F5-D5 | Detecção de EMR não resolve divergência silenciosamente | Escolher a fonte mais confiável | Herdado da Fase 0: divergência é reportada, não resolvida pelo extrator. **Mas `SF-ENV-001` não cobre este caso hoje** — ver §3.3 |

### 3.1 O curinga não filtra nada — e é por isso que a fase existe

Achado de revisão adversarial deste spec, provado por execução antes de qualquer código.

`sparkforge/rules/version_scope.py:41-42`:

```python
if spec == "*":
    continue
```

O ramo do curinga **pula a checagem de presença**. Não lê `runtime.get(key)`. Medido:

```
in_scope({'glue': '*'}, {'spark': '3.5.6', 'emr': '7.5.0'})  -> True
in_scope({'glue': '*'}, {})                                  -> True
in_scope({'glue': '>=3.0'}, {'spark': '3.5.6', 'emr': '7.5.0'}) -> False
```

Consequência: **`{glue: "*"}` nunca pode produzir skip por `runtime_scope`, em runtime nenhum.** A versão anterior desta decisão dizia que as 5 SF-GLUE seriam "puladas em EMR" mantendo o curinga — isso era impossível, e o critério de aceitação que dependia disso era inatingível.

A correção não é contornar. É fazer o curinga significar o que todo leitor assume: **"qualquer versão deste componente, mas ele precisa estar presente"**. Foi exatamente essa ambiguidade — "qualquer versão de Glue" lido como "qualquer runtime" — que produziu as 20 regras mal etiquetadas em primeiro lugar.

**A ordem importa e é inegociável:** reetiquetar as 20 agnósticas **antes** de mudar a semântica do curinga. Invertido, as 20 param de disparar no instante em que a semântica muda.

`in_scope` é função provada, com teste nas bordas (`tests/test_rules_version_scope.py`). A mudança exige teste novo para o curinga com chave ausente e com chave presente, e revisão de toda regra que dependa do comportamento antigo.

### 3.2 `SF-GLUE-002` some de findings *e* de skipped

O revisor reproduziu o cenário da §1 — repositório com Terraform de infra EMR, sem bloco `aws_glue_job` — e rodou `judge` contra o catálogo real:

```
SF-GLUE em findings: 0
SF-GLUE em skipped:  4   (por requires_facts, não por runtime_scope)
SF-GLUE-002:         AUSENTE dos dois — silêncio total
```

`SF-GLUE-002` ancora em `tf.module_analyzed`, o sentinela que o extrator emite para **qualquer** arquivo `.tf` escaneado, tenha ou não `aws_glue_job`. `requires_facts` fica satisfeito, o `when` fica falso, e a regra não aparece em lugar nenhum.

É o defeito da §1 reproduzido sob o desenho que o próprio spec propunha. Corrigir a semântica do curinga (§3.1) resolve o caso EMR, mas não este: num runtime que **é** Glue e não tem `aws_glue_job` no Terraform, ela continua sumindo. `SF-GLUE-002` precisa exigir um fact específico de `aws_glue_job` em `requires_facts`.

Nota do revisor a registrar: `SF-GLUE-003/004/005/006` não filtram por `resource_type` — dependem de `tf.attribute`, que só existe hoje porque `sparkforge/facts/terraform.py:678` faz `if resource_type != "aws_glue_job": continue`. A classificação delas como "infra Glue" está correta **hoje**, mas por acidente do extrator, não por declaração da regra. Se o extrator de Terraform for generalizado, elas disparam sobre atributo não-Glue de nome coincidente. Não é urgente — o extrator EMR desta fase lê JSON de `describe-cluster`, não HCL — mas é base frágil para uma decisão tratada como permanente.

### 3.3 Divergência de plataforma não é divergência de versão

A versão anterior deste spec dizia que detectar `glue` e `emr` juntos "vira `SF-ENV-001`, herdado da Fase 0". O revisor leu o código e derrubou.

`sparkforge/facts/runtime_detect.py` coleta `glue_observations` **apenas** para derivar spark/python/iceberg via `GLUE_MATRIX` e popular `divergences` — a própria docstring diz que `glue_version` "não vira um fact `env.runtime_signal`". E `_build_facts` itera só `observations` (spark, python, iceberg, athena). `SF-ENV-001` dispara sobre `env.runtime_signal` com `measures.distinct_versions > 1`.

Logo: detectar Glue e EMR juntos só produziria `SF-ENV-001` se as versões **derivadas** discordassem. Se coincidirem — plausível, já que Glue 4.0 deriva Spark 3.3.0 e algum release EMR também pode — a dupla detecção **passa sem sinal nenhum**.

"Herdado da Fase 0" está certo sobre o padrão de reportar divergência, e **errado** sobre este caso já estar coberto. Divergência de *identidade de plataforma* é pergunta diferente de divergência de *versão de componente*, e exige desenho novo: ou plataforma vira componente rastreado, com fact próprio, ou nasce uma regra irmã de `SF-ENV-001` para o caso.

A decisão de qual caminho fica para o plano. O que este spec registra é que **não está coberto**, para ninguém assumir que está.

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
| **Reetiquetar apaga as 20 regras quando o runtime não é passado** | Real, não teórico: `build_runtime_context` (`_core.py:104-121`) monta o contexto **só** de flags da CLI (`--glue/--spark/...`), nunca dos facts coletados. Hoje `{glue: "*"}` faz as 20 avaliarem sempre; com `{spark: ">=3.0"}`, qualquer `judge` sem `--spark` nem `--glue` as apaga — com motivo, mas apaga. As skills que chamam `judge` precisam passar runtime; `review-pyspark-pr` já passa `--glue`, as outras precisam ser conferidas uma a uma |
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
10. `SF-GLUE-002` aparece em `judge --show-skipped` — nunca em silêncio — tanto num runtime EMR quanto num Glue sem `aws_glue_job`.
11. Curinga `"*"` exige presença da chave, com teste para chave ausente e presente, e nenhuma regressão nas 23 regras já específicas.
12. Detectar Glue e EMR juntos produz sinal **mesmo quando as versões derivadas coincidem**.
13. Toda skill que chama `judge` passa runtime, ou declara por que não precisa — conferido uma a uma.
14. `README.md`, `AGENTS.md`, `STATUS.md`, `knowledge/`, as `skills/` afetadas e o spec da fase atualizados e referenciando o que é novo.
