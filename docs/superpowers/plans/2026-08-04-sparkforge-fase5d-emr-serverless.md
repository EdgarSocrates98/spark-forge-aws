# Fase 5d — EMR Serverless: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans para implementar tarefa a tarefa. Os passos usam checkbox (`- [ ]`).

**Goal:** Uma área `SF-EMRS` que julga a definição de uma application EMR Serverless — capacidade pré-inicializada, auto-stop, destino de log e `runtimeConfiguration` — a partir do JSON de `get-application`.

**Architecture:** Extrator novo (`sparkforge/facts/emr_serverless.py`) no padrão de `emr_cluster.py`: função pura sobre um payload já em disco, `EMITTED_KINDS` fechado, sentinela sempre emitida, `unresolved` com vocabulário fechado em vez de valor adivinhado. Catálogo próprio (`rules/catalog/emr-serverless.yaml`). Coordenador existente estendido, não duplicado.

**Tech Stack:** Python 3, pytest, PyYAML. Sem dependência nova. Nenhuma chamada AWS fora do verbo `collect`.

**Spec:** [`../specs/2026-08-04-sparkforge-fase5d-emr-serverless-design.md`](../specs/2026-08-04-sparkforge-fase5d-emr-serverless-design.md)
**Branch:** `feat/fase5d-emr-serverless`

---

## Aviso a quem implementa — leia antes da Task 1

**Este plano erra sistematicamente onde eu escrevi código sem executar.** Nas Fases 4a, 4b e 4c os implementadores mediram entre 25 e 40 divergências por fase entre o que o plano afirmava e o que o repositório fazia. Todas foram registradas como `D-*` e todas as vezes a medição venceu.

Portanto:

1. **Meça antes de copiar.** Se um trecho deste plano afirma que um arquivo tem tal função, tal assinatura ou tal linha, abra e confira. Divergiu? A sua medição vence. Registre como `D-5d-N` no fim deste arquivo e siga.
2. **O JSON de `get-application` que aparece aqui é memória minha, não medição.** A Task 1 confere o formato real contra a documentação da AWS **antes** de qualquer código depender dele. Se o formato divergir, corrija o plano e registre.
3. **Número no `STATUS.md` se mede, nunca se copia.** Rode e conte.
4. **Nada entra no catálogo sem fonte.** Regra sem `sources` com URL e `retrieved`, ou sem `origin: field-heuristic` com nota, não passa na revisão.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `knowledge/emr-serverless/runtime-matrix.md` | matriz de release do Serverless, e se coincide com a do EC2 | 1 |
| `knowledge/emr-serverless/application-configuration.md` | capacidade, auto-stop, monitoring, runtimeConfiguration — com fonte por afirmação | 1 |
| `knowledge/sources.lock.json` | índice de fontes; ganha as URLs novas | 1, 5 |
| `sparkforge/facts/emr_serverless.py` | extrator: payload → `Fact`s. Único lugar que conhece o formato da AWS | 2 |
| `tests/test_facts_emr_serverless.py` | testes de unidade do extrator | 2 |
| `sparkforge/collect/aws.py` | `collect emr-serverless` | 3 |
| `sparkforge/adapters/_core.py` | verbo `analyze emr-serverless`, compartilhado pelos adaptadores | 3 |
| `sparkforge/adapters/cli.py` | sub-parser | 3 |
| `sparkforge/adapters/tools.py` | tool MCP | 3 |
| `parity.yaml`, `manifest.json` | as cinco superfícies concordando | 3 |
| `fixtures/emr_serverless/*/` | golden bidirecional, domínio novo | 4 |
| `scripts/regen_fixtures.py` | regenerador do domínio novo | 4 |
| `rules/catalog/emr-serverless.yaml` | área `SF-EMRS` | 5 |
| `tests/test_rules_emrs_boundary.py` | a fronteira entre `SF-EMR` e `SF-EMRS`, medida | 6 |
| `agents/emr-infra-reviewer.md` + 4 espelhos | `rule_areas` ganha `SF-EMRS` | 7 |
| `skills/review-emr-cluster/SKILL.md` + espelhos | a frase que vira meia-verdade | 7 |
| `docs/superpowers/STATUS.md`, `README.md`, `AGENTS.md`, `GUIA_DE_USO.md` | números medidos | 7 |

---

## Task 1: A pesquisa, e as duas perguntas que decidem o resto

**Nenhuma linha de código nesta task.** A Fase 5b produziu `knowledge/emr/` antes do extrator, e é por isso que as nove regras `SF-EMR` têm fonte datada. Aqui é igual.

**Files:**
- Create: `knowledge/emr-serverless/runtime-matrix.md`
- Create: `knowledge/emr-serverless/application-configuration.md`
- Modify: `knowledge/sources.lock.json`
- Modify: `knowledge/INDEX.md`

- [ ] **Step 1: Leia o formato de um arquivo de knowledge antes de escrever um**

```bash
cat knowledge/emr/cluster-configuration.md | head -40
sed -n '225,246p' knowledge/emr/cluster-configuration.md
python -c "import json;d=json.load(open('knowledge/sources.lock.json'));print(json.dumps(list(d.items())[:1],indent=2,ensure_ascii=False))"
```

Repare em três coisas, porque elas são o padrão que você vai seguir:

- o link do espelho executável no topo (`knowledge/emr/cluster-configuration.md:5` aponta para `rules/catalog/emr-infra.yaml`);
- a seção `## Fontes` no fim, uma linha por página: `Título. URL (retrieved AAAA-MM-DD)`;
- **os parágrafos finais que declaram o que a fonte NÃO sustenta** (`:245-246`). Este é o item que mais importa. "Não citar número" é uma frase que um arquivo de knowledge deste repositório pode e deve conter.

- [ ] **Step 2: Responda a pergunta 1 — a matriz do Serverless coincide com a do EC2?**

`sparkforge/facts/runtime_detect.py` tem `EMR_MATRIX`, espelho de `knowledge/emr/runtime-matrix.md`, cujo título diz **"Matriz de runtime Amazon EMR on EC2"**.

Busque a página de release notes do EMR Serverless na documentação da AWS. Para **cada release** que `EMR_MATRIX` cobre hoje, registre: Spark, Hadoop, Iceberg e Python no Serverless, e se bate com o EC2.

Escreva `knowledge/emr-serverless/runtime-matrix.md` com o resultado — **inclusive se o resultado for "idênticas"**. "São iguais" é afirmação, e afirmação neste repositório precisa de fonte com data.

Se a documentação não cobrir alguma release, escreva isso explicitamente na seção final, no padrão de `cluster-configuration.md:245-246`. Não interpole, não assuma continuidade.

- [ ] **Step 3: Responda a pergunta 2 — pré-init fatura com a application parada?**

A regra P0 mais cara desta fase afirma que **capacidade pré-inicializada é faturada enquanto a application está `STARTED`, mesmo sem job rodando**. Se isso for verdade, auto-stop desligado com pré-init é dinheiro queimando. Se não for, a regra não existe.

Busque a página de preços do EMR Serverless e a de capacidade pré-inicializada. Registre a frase exata que sustenta ou derruba a afirmação, com URL e data.

**Se a fonte não sustentar, a regra não entra e o veto fica escrito** no cabeçalho do catálogo na Task 5, no padrão de `rules/catalog/emr-infra.yaml:22-148`.

- [ ] **Step 4: Registre o formato real de `get-application`**

Busque a referência de API do EMR Serverless (`GetApplication`). Registre em `application-configuration.md` os campos que esta fase lê, **com o tipo real de cada um**.

Atenção a um ponto que este plano assume e você precisa confirmar: acredito que `workerConfiguration.cpu`, `.memory` e `.disk` são **strings com unidade** (`"4 vCPU"`, `"16 GB"`), não números. Se for verdade, comparar `initialCapacity` contra `maximumCapacity` exige converter, e converter exige saber quais unidades aparecem. Registre as unidades documentadas. Se a doc não fechar o conjunto, isso é limite declarado, e o extrator emite `unresolved` para unidade desconhecida em vez de adivinhar.

- [ ] **Step 5: Documente as outras quatro perguntas candidatas**

Uma seção por pergunta da §5 do spec: auto-stop com timeout longo, `initialCapacity` acima de `maximumCapacity`, destino de log ausente, segredo em `runtimeConfiguration`. Para cada uma, a fonte que a sustenta, ou o registro de que só há leitura de campo (`field-heuristic`).

Para "destino de log ausente", registre também quais destinos existem — S3, managed persistence, CloudWatch — e se a ausência dos três é possível. Se a AWS habilitar managed persistence por padrão, a regra muda de forma, e melhor descobrir agora que na Task 5.

- [ ] **Step 6: Atualize `sources.lock.json` e `INDEX.md`**

Toda URL nova entra em `sources.lock.json` com `checked_at`, `retrieved` e `sha256`. O campo `rules` fica vazio agora e é preenchido na Task 5, quando as regras existirem.

- [ ] **Step 7: Rode a suíte**

```bash
python -m pytest -q --no-header
```

Esperado: verde. Nada de código mudou, mas há testes que leem `knowledge/` e `sources.lock.json` — se algum quebrar, é porque o formato que você escreveu diverge do que o repositório espera, e isso é melhor descobrir aqui.

- [ ] **Step 8: Commit**

```bash
git add knowledge/
git commit -m "docs(knowledge): EMR Serverless, e as duas perguntas que decidem a fase"
```

**Relate ao coordenador:** qual foi a resposta de cada uma das duas perguntas, quais das cinco regras candidatas sobreviveram, e quais unidades `workerConfiguration` usa.

---

## Task 2: O extrator

**Files:**
- Create: `sparkforge/facts/emr_serverless.py`
- Create: `tests/test_facts_emr_serverless.py`

- [ ] **Step 1: Meça a guarda de namespace antes de escolher o prefixo**

A D-2 do spec propõe `emrs.`, mas manda medir primeiro.

```bash
sed -n '195,215p' sparkforge/facts/emr_cluster.py
sed -n '1205,1220p' sparkforge/facts/emr_cluster.py
grep -rn "EMITTED_KINDS" tests/ | head -20
```

Descubra: existe teste que exija que os kinds de um extrator compartilhem prefixo? Existe teste que proíba dois extratores de emitirem o mesmo prefixo? Um extrator novo emitindo `emr.serverless.application` passaria?

Escreva a resposta como `D-5d-1` no fim deste plano, com o `arquivo:linha` que a sustenta, e só então escolha. Se `emr.serverless.` passar limpo, ainda assim prefira `emrs.` **se** a medição mostrar que algum teste agrupa por prefixo — mas diga qual medição decidiu.

O resto deste plano escreve `emrs.`. Se você escolher diferente, ajuste em tudo e registre.

- [ ] **Step 2: Leia o extrator que é o modelo**

```bash
sed -n '1,60p' sparkforge/facts/emr_cluster.py
sed -n '190,215p' sparkforge/facts/emr_cluster.py
sed -n '300,330p' sparkforge/facts/emr_cluster.py
sed -n '1140,1220p' sparkforge/facts/emr_cluster.py
```

Anote: como `_unresolved` monta o fact, como `_finish` fecha com a sentinela, como a proveniência viaja, e por que `extract_emr_cluster` **nunca levanta exceção**.

- [ ] **Step 3: Escreva o teste que falha — a sentinela sai mesmo sem nada**

```python
# tests/test_facts_emr_serverless.py
from sparkforge.facts.emr_serverless import extract_emr_serverless


def test_payload_vazio_emite_unresolved_e_sentinela():
    facts = extract_emr_serverless({}, path_hint="vazio.json")
    kinds = [f.kind for f in facts]
    assert "emrs.unresolved" in kinds
    assert "emrs.analyzed" in kinds
    sentinela = next(f for f in facts if f.kind == "emrs.analyzed")
    assert sentinela.measures["application_count"] == 0
    assert sentinela.measures["unresolved_count"] == 1
```

- [ ] **Step 4: Rode e veja falhar**

```bash
python -m pytest tests/test_facts_emr_serverless.py -q
```

Esperado: `ModuleNotFoundError: No module named 'sparkforge.facts.emr_serverless'`.

- [ ] **Step 5: Escreva o mínimo que passa**

```python
"""Extrai facts da definicao de uma application EMR Serverless.

Le o JSON de `aws emr-serverless get-application`, em camelCase, sem traducao.
Nunca chama AWS, nunca levanta excecao: o que nao consegue ler vira
`emrs.unresolved` contado, e a sentinela `emrs.analyzed` sai sempre.
"""
from __future__ import annotations

from typing import Any

from sparkforge.findings.models import Fact

EXTRACTOR_ID = "emr_serverless@0.1.0"

EMITTED_KINDS = (
    "emrs.application",
    "emrs.initial_capacity",
    "emrs.configuration",
    "emrs.monitoring",
    "emrs.unresolved",
    "emrs.analyzed",
)


def extract_emr_serverless(payload: Any, path_hint: str = "") -> list[Fact]:
    facts: list[Fact] = []
    raw = payload.get("application") if isinstance(payload, dict) else None
    if raw is None:
        facts.append(_unresolved(path_hint, "missing_application"))
    return _finish(facts, path_hint)
```

Escreva `_unresolved` e `_finish` seguindo a forma medida no Step 2 — **não copie a minha, copie a de `emr_cluster.py`**, incluindo como a proveniência é montada.

- [ ] **Step 6: Rode e veja passar**

```bash
python -m pytest tests/test_facts_emr_serverless.py -q
```

- [ ] **Step 7: Commit**

```bash
git add sparkforge/facts/emr_serverless.py tests/test_facts_emr_serverless.py
git commit -m "feat(emrs): o extrator nasce pela sentinela, nao pelo caminho feliz"
```

- [ ] **Step 8: `emrs.application`, com teste primeiro**

Escreva o teste com o payload real medido na Task 1. Exemplo da forma esperada — **confira contra o que a Task 1 registrou**:

```python
def test_application_carrega_release_e_auto_stop():
    payload = {"application": {
        "applicationId": "00fabc", "name": "etl", "releaseLabel": "emr-7.5.0",
        "type": "Spark", "state": "STARTED", "architecture": "X86_64",
        "autoStartConfiguration": {"enabled": True},
        "autoStopConfiguration": {"enabled": True, "idleTimeoutMinutes": 15},
    }}
    facts = extract_emr_serverless(payload, path_hint="app.json")
    app = next(f for f in facts if f.kind == "emrs.application")
    assert app.attrs["release_label"] == "emr-7.5.0"
    assert app.attrs["auto_stop_enabled"] is True
    assert app.measures["release_major"] == 7
    assert app.measures["idle_timeout_minutes"] == 15
```

Implemente. **Onde o campo não existir no payload, omita a chave** — não escreva `False` nem `0`. `engine._where_matches` rejeita caminho ausente, e é assim que este motor diz "não sei". Escrever `False` diria "sei que não", que é outra afirmação.

A exceção: quando a ausência **é** a informação. `auto_stop_enabled` ausente do payload significa que a AWS não devolveu a configuração — omita. `autoStopConfiguration.enabled == false` significa desligado — escreva `False`. A Task 1 registrou qual dos dois a AWS faz.

- [ ] **Step 9: `emrs.initial_capacity`, um fact por worker type**

Teste primeiro, com `workerCount` e a configuração de cada worker. Se a Task 1 confirmou que `cpu`/`memory`/`disk` são strings com unidade, converta para `measures` numéricos (`cpu`, `memory_gb`, `disk_gb`) e emita `emrs.unresolved` com `reason: "unknown_capacity_unit"` para unidade fora do conjunto documentado.

**Não adivinhe unidade.** `"16 GB"` e `"16384 MB"` são o mesmo número em unidades diferentes; tratar a segunda como GB produziria um fact errado, e um fact errado neste motor vira achado confiante e falso.

- [ ] **Step 10: A decisão de capacidade — o extrator correlaciona**

`initialCapacity` total acima de `maximumCapacity` exige olhar dois campos ao mesmo tempo. `engine._condition_candidates` avalia **um fact por vez**, então isso não é expressável no catálogo (D-4 do spec).

Some os três eixos da capacidade inicial (soma de `workerCount × cpu`, idem memória e disco) e compare com o teto. Emita em `emrs.application`:

- `attrs.initial_exceeds_maximum: True` quando algum eixo excede;
- **omita a chave** quando faltar dado para decidir — `maximumCapacity` ausente, unidade desconhecida em qualquer worker;
- `attrs.capacity_axes_exceeded` com a lista dos eixos que excederam, para o achado poder dizer qual.

Teste os três casos: excede, não excede, e não dá para decidir. O terceiro é o que mais erra.

- [ ] **Step 11: `emrs.configuration` e `emrs.monitoring`**

`runtimeConfiguration` tem a forma de `Configurations` do EMR on EC2. Leia como `emr_cluster.py` achata classification/properties e **como ele redige segredo antes de virar `Fact`**:

```bash
grep -n "secret_pattern_match\|redacted" sparkforge/facts/emr_cluster.py | head -20
```

Reaproveite o mesmo mecanismo. Se ele estiver em função utilitária compartilhável, use-a; se estiver embutido em `emr_cluster.py`, **não copie o corpo** — extraia para onde os dois alcancem, e diga no commit que extraiu.

`emrs.configuration` **não carrega `level`** (D-3 do spec): Serverless não tem grupo de instância, logo não tem override.

`emrs.monitoring` sai sempre que a application é lida, com `s3_log_uri_present`, `managed_persistence_enabled` e `cloudwatch_enabled` — os três conforme a Task 1 mediu.

- [ ] **Step 12: Suíte inteira e commit**

```bash
python -m pytest -q --no-header && ruff check .
git add sparkforge/facts/emr_serverless.py tests/test_facts_emr_serverless.py
git commit -m "feat(emrs): capacidade, configuracao e monitoramento da application"
```

**Relate:** os kinds finais, quantos testes, e o que a Task 1 disse que mudou o desenho.

---

## Task 3: Os dois verbos, nas cinco superfícies

**Files:**
- Modify: `sparkforge/collect/aws.py`
- Modify: `sparkforge/adapters/_core.py`
- Modify: `sparkforge/adapters/cli.py`
- Modify: `sparkforge/adapters/tools.py`
- Modify: `parity.yaml`, `manifest.json`
- Modify: `tests/test_adapters_cli.py`, `tests/test_adapters_tools.py`

- [ ] **Step 1: Meça as listas que precisam concordar**

```bash
grep -n "EXTRACTORS" sparkforge/adapters/_core.py sparkforge/adapters/cli.py sparkforge/adapters/tools.py
grep -n "emr-cluster" sparkforge/adapters/*.py sparkforge/collect/aws.py parity.yaml manifest.json
```

A Fase 4b mediu que `tests/test_adapters_tools.py` tem **quatro** listas que precisam ganhar a entrada nova. Confirme quantas são hoje — o número pode ter mudado desde então, e é isso que este passo existe para descobrir.

- [ ] **Step 2: `collect emr-serverless`**

Leia `sparkforge/collect/aws.py:654-712` (`collect emr-cluster`) e siga a forma. EMR on EC2 une seis subcomandos num JSON; Serverless precisa de `get-application` — e só, porque job runs estão fora (§2 do spec).

Se a application exigir também `list-applications` para resolver o id a partir do nome, isso é decisão sua com base no que a Task 1 mediu. Registre.

- [ ] **Step 3: `analyze emr-serverless` no `_core.py`**

Siga o verbo `analyze emr-cluster`. Repare que `_core.py:203-207` faz `emr.cluster.attrs.release_label` virar produtor de `RuntimeContext`.

**Não faça o equivalente aqui.** A D-5 do spec proíbe: até a Task 1 provar que a matriz do Serverless coincide com a do EC2, `emrs.application.release_label` **não** alimenta `RuntimeContext.emr`.

Se a Task 1 provou que coincidem, o produtor entra — e o commit cita a fonte. Se divergem, não entra, e a divergência vira dívida registrada na Task 7.

- [ ] **Step 4: CLI, MCP, `parity.yaml`, `manifest.json`**

Um de cada vez, rodando os testes de adaptador entre eles. `manifest.json` tem contagem de tools que precisa bater com `tools.py`.

- [ ] **Step 5: Suíte, ruff, `sync_skills.py --check`, commit**

```bash
python -m pytest -q --no-header && ruff check . && python scripts/sync_skills.py --check
git add -A
git commit -m "feat(emrs): collect e analyze nas cinco superficies"
```

---

## Task 4: Fixtures, com golden bidirecional

**Files:**
- Create: `fixtures/emr_serverless/*/`
- Modify: `scripts/regen_fixtures.py`
- Create: `tests/test_fixtures_golden_emr_serverless.py`

- [ ] **Step 1: Leia o que o repositório já previu sobre este domínio**

```bash
sed -n '170,185p' tests/test_fixtures_kind_coverage.py
ls fixtures/emr/
cat fixtures/emr/empty_dump/meta.yaml
```

`tests/test_fixtures_kind_coverage.py:177` já diz que EMR Serverless nasce como `fixtures/<domínio>/` novo, e que **esquecer o módulo golden é o erro natural**. Não o cometa.

- [ ] **Step 2: Regenerador antes das fixtures**

Adicione `regen_emr_serverless` em `scripts/regen_fixtures.py`, no padrão dos existentes. Golden se regenera, nunca se escreve à mão — a Fase 4c registrou `plan_ref` vazio em sete goldens exatamente por alguém ter feito à mão.

- [ ] **Step 3: As fixtures, uma por condição de regra**

Mínimo, e ajuste conforme as regras que sobreviveram à Task 1:

| Fixture | O que exercita |
|---|---|
| `empty_payload` | `missing_application` + sentinela zerada |
| `app_saudavel` | auto-stop ligado, log em S3, sem pré-init excessiva — **nenhum achado** |
| `preinit_sem_autostop` | a P0 de custo |
| `autostop_longo` | timeout acima do limiar |
| `capacidade_excede_teto` | `initial_exceeds_maximum` |
| `sem_destino_de_log` | os três destinos ausentes |
| `segredo_em_runtime_config` | `secret_pattern_match` |
| `unidade_desconhecida` | `unresolved` em vez de número adivinhado |

**Toda regra precisa de golden positivo E negativo, e cada condição precisa ser apagável com golden vermelho.** A Fase 4c mediu que "positivo por regra" não basta: a `SF-FVAL-004` tinha duas condições e a exata podia ser apagada sem nenhum golden reclamar. Antes de fechar esta task, **apague cada condição do catálogo uma por vez e confirme que algum golden fica vermelho**. Se não ficar, falta fixture.

(Esta verificação depende da Task 5. Faça as fixtures aqui e a verificação de apagabilidade no fim da Task 5.)

- [ ] **Step 4: Registre o domínio nos testes de invariante**

Duas listas precisam saber que `emr_serverless` existe. Meça quais são antes de editar:

```bash
grep -n "emr_cluster\|terraform" tests/test_fixtures_kind_coverage.py | head
grep -n "SF-EMR\|areas" tests/test_rules_catalog_reachability.py | head
```

`test_fixtures_kind_coverage.py` prova o critério 3 do spec — todo kind de `EMITTED_KINDS` aparecendo em algum golden. Se o extrator novo não estiver registrado ali, o critério passa sem ser verificado, que é pior do que falhar.

`test_rules_catalog_reachability.py` foi tocado na Fase 4c quando a área `SF-FVAL` nasceu. Confira se área nova exige entrada lá.

- [ ] **Step 5: Suíte e commit**

```bash
python -m pytest -q --no-header
git add fixtures/emr_serverless/ scripts/regen_fixtures.py tests/
git commit -m "feat(emrs): o corpus da application, e o vazio que continua contado"
```

---

## Task 5: A área `SF-EMRS`

**Files:**
- Create: `rules/catalog/emr-serverless.yaml`
- Modify: `knowledge/sources.lock.json`
- Modify: `rules/catalog/README.md`

- [ ] **Step 1: Leia o cabeçalho que é o modelo**

```bash
sed -n '1,150p' rules/catalog/emr-infra.yaml
sed -n '50,65p' rules/catalog/README.md
```

O cabeçalho de `emr-infra.yaml` carrega **os vetos**: o que foi considerado e recusado, com razão. Faça igual — inclusive com o que a Task 1 vetou por falta de fonte.

- [ ] **Step 2: As regras que sobreviveram**

Uma por vez, cada uma com fixture já pronta da Task 4. Para cada uma:

- `runtime_scope: {}` — pelo argumento de `emr-infra.yaml:8-19`;
- `requires_facts` ancorado em `emrs.application`, **nunca na sentinela** (`emr-infra.yaml:474-480` registra a lição);
- `sources` com URL e `retrieved` da Task 1, ou `origin: field-heuristic` com nota;
- `explanation` que diz o que o achado significa e o que ele não prova.

**Dois erros que este repositório já cometeu e que custam caro:**

- `threshold` é **singular**. Escrever `thresholds` deixa a regra silenciosamente inerte: o motor monta contexto vazio, `_expr_matches` engole o `ExprError`, e a regra nunca dispara sem ninguém notar.
- Número em notação científica no YAML precisa de **ponto na mantissa**: `1.0e-9`, nunca `1e-9`. O segundo vira `str`, e `float > str` levanta `TypeError` — que `_expr_matches` **não** engole. Derruba o `judge` inteiro.

- [ ] **Step 3: Preencha `rules` em `sources.lock.json`**

Cada URL da Task 1 ganha os IDs das regras que a citam. É o que liga fonte a regra e permite detectar drift.

- [ ] **Step 4: A verificação de apagabilidade**

Para **cada condição** de **cada regra**: comente a condição, rode a suíte, confirme que algum golden fica vermelho, descomente.

```bash
python -m pytest tests/test_fixtures_golden_emr_serverless.py -q
```

Condição que pode sumir sem deixar vermelho **não está testada**. Ou você escreve a fixture que falta, ou registra como dívida de fixture com a razão — como a 4c fez com a `SF-FVAL-004`.

- [ ] **Step 5: Suíte, e commit**

```bash
python -m pytest -q --no-header && ruff check .
git add rules/catalog/ knowledge/sources.lock.json
git commit -m "feat(rules): area SF-EMRS, e os vetos que a pesquisa escreveu"
```

**Relate:** quantas regras entraram, quantas foram vetadas e por quê, e o resultado da apagabilidade condição a condição.

---

## Task 6: A fronteira, medida

**Files:**
- Create: `tests/test_rules_emrs_boundary.py`

A §10.5 do spec exige: nenhuma regra `SF-EMR` dispara sobre artefato de Serverless, nenhuma `SF-EMRS` sobre `describe-cluster`. **Provado por teste, não afirmado.**

- [ ] **Step 1: O teste nas duas direções**

```python
# tests/test_rules_emrs_boundary.py
"""A fronteira entre SF-EMR (EC2) e SF-EMRS (Serverless), medida.

As duas areas leem definicao de infraestrutura EMR. Se uma disparar sobre o
artefato da outra, o achado cita um fact que descreve outra coisa.
"""


class TestFronteiraEntreAsDuasAreas:
    def test_nenhuma_regra_emr_dispara_sobre_serverless(self):
        # para cada fixture de fixtures/emr_serverless/: carregue os facts do
        # golden, rode judge com o catalogo inteiro, e afirme que nenhum
        # finding pertence a area SF-EMR
        ...

    def test_nenhuma_regra_emrs_dispara_sobre_ec2(self):
        # o inverso, sobre os goldens de fixtures/emr/
        ...
```

Deixei o corpo vazio de propósito: **não invente a API de carregamento**. Copie a forma de um teste golden que já existe —

```bash
sed -n '1,60p' tests/test_fixtures_golden_emr.py
grep -rn "def judge\|run_judge" sparkforge/rules/engine.py sparkforge/adapters/_core.py | head
```

— e reaproveite o helper que ele usa. Plano que afirma assinatura de função sem medir foi a origem da maioria dos desvios das Fases 4a e 4c.

Cuidado com um detalhe que decide o teste: `SF-EMR-` é prefixo de `SF-EMRS-` se você comparar com `startswith`. Compare pela **área declarada na regra**, não pelo prefixo do id — senão `SF-EMRS-001` conta como `SF-EMR` e o teste passa por engano na direção errada.

- [ ] **Step 2: Rode, e desconfie se passar de primeira**

Um teste de fronteira que passa sem nunca ter falhado pode estar medindo nada. Quebre-o de propósito — troque a área de uma regra `SF-EMRS` para `SF-EMR` no catálogo em memória — e confirme que fica vermelho. Depois desfaça.

- [ ] **Step 3: Commit**

```bash
python -m pytest -q --no-header
git add tests/test_rules_emrs_boundary.py
git commit -m "test(emrs): a fronteira com SF-EMR deixa de ser afirmacao"
```

---

## Task 7: Coordenador, docs, e o fechamento

**Files:**
- Modify: `agents/emr-infra-reviewer.md` + os quatro espelhos
- Modify: `skills/review-emr-cluster/SKILL.md` + espelhos
- Modify: `docs/superpowers/STATUS.md`, `README.md`, `AGENTS.md`, `GUIA_DE_USO.md`, `AGENT_PROTOCOL.md`
- Modify: `docs/superpowers/specs/2026-08-04-sparkforge-fase5d-emr-serverless-design.md`

- [ ] **Step 1: Rode os testes de cobertura de agente e veja a órfã**

```bash
python -m pytest tests/test_agent_coverage.py -q
```

Esperado: vermelho em `test_no_area_is_orphan`, com `SF-EMRS` na lista, e possivelmente em `test_no_tool_is_orphan` com a tool nova. É o repositório cobrando a Task 7.

- [ ] **Step 2: Estenda o coordenador — sem duplicar**

`SF-EMRS` entra em `rule_areas` de `emr-infra-reviewer`, pela D-1 do spec. **Não crie coordenador novo.**

O corpo do agente precisa dizer quando é um modelo e quando é o outro, e — mais importante — que **quem pergunta muitas vezes não sabe qual tem**. O agente descobre pelo artefato disponível, não perguntando.

Edite o arquivo fonte e rode `python scripts/sync_skills.py` para gerar os espelhos. **Não edite espelho à mão**: `sync_skills.py` é tradutor, e o invariante é "o espelho é exatamente o que o tradutor produz".

- [ ] **Step 3: A frase que virou meia-verdade**

`skills/review-emr-cluster/SKILL.md:153` afirma que "esta área cobre EMR on EC2, e nenhum dos facts descreve os outros dois modelos de execução". Metade disso deixa de ser verdade.

Corrija para dizer o que passou a existir e o que continua sem existir — EKS. Ensine o verbo novo onde a skill ensina os outros.

- [ ] **Step 4: Meça os números, não copie**

```bash
python -c "import json;print(len(json.load(open('manifest.json'))['tools']))"
python -m pytest -q --no-header 2>&1 | tail -2
```

Conte regras, áreas, extratores, kinds, fixtures e domínios rodando, não lendo o plano. `README.md` e `STATUS.md` costumam estar certos; `AGENTS.md` é o espelho em inglês que envelhece — a rodada de revisão da 4c achou dois números parados lá.

- [ ] **Step 5: `GUIA_DE_USO.md` ensina o verbo**

A revisão da 4c achou que o guia listava capacidade **sem nomear o verbo produtor** — o mesmo defeito que o motor acusa no código do usuário. Não repita: o verbo novo entra onde o guia ensina os outros comandos.

Existe teste que amarra o guia ao parser real (adicionado na rodada de revisão da 4c). Se o verbo estiver escrito errado no guia, ele pega.

- [ ] **Step 6: Aplique a §11 ao spec**

O spec **não é reescrito** — ganha seção `## 11. Desvios` com os `D-5d-*` que este plano acumulou, e o `Status:` deixa de dizer "não implementado". É a convenção do repositório: spec é registro do que se pretendia; `STATUS.md` é a fonte da verdade do que é.

- [ ] **Step 7: `STATUS.md` — a linha do roadmap muda de forma**

A linha "EMR Serverless e EMR on EKS" da seção *Trabalho previsto* (`STATUS.md:1501`) passa a nomear **só EKS**. Diga o que esta fase entregou, e registre as dívidas:

| Linha | Natureza |
|---|---|
| EMR on EKS | fase |
| Job runs e `billedResourceUtilization` | fase |
| `RuntimeContext.emr` a partir de Serverless | dívida ou fase, conforme a Task 1 mediu |
| Julgar `architecture` | limite declarado |

Some o que você mediu. Recontagem de dívidas/fases/limites com os números novos.

- [ ] **Step 8: Fechamento**

```bash
python -m pytest -q --no-header && ruff check . && python scripts/sync_skills.py --check
git add -A
git commit -m "docs(fase5d): SF-EMRS ganha coordenador, e o roadmap perde metade de uma linha"
```

**Relate:** o que cada número mediu, quais dívidas registrou, e onde o plano não sobreviveu ao contato com o repositório.

---

## Desvios (`D-5d-*`)

Registre aqui, durante a execução, cada ponto em que a medição contrariou este plano. Formato: `**D-5d-N** — o que o plano dizia; o que a medição mostrou, com `arquivo:linha`; o que você fez.`

**D-5d-1** (Task 2, Step 1) — a medição da guarda de namespace, que o plano reservou. **Nenhum teste exige que os kinds de um extrator compartilhem prefixo, e nenhum proíbe dois extratores no mesmo prefixo.** As duas agregações que existem unem `EMITTED_KINDS` módulo a módulo, sem olhar o texto do kind: `tests/test_fixtures_kind_coverage.py:69` e `tests/test_rules_catalog_reachability.py:77`. A guarda que a D-2 do spec citou (`emr_cluster.py:1214-1216`) é **local ao módulo** — compara os kinds emitidos contra o `EMITTED_KINDS` daquele arquivo —, então um segundo extrator emitindo `emr.serverless.*` passaria por ela sem tocá-la. O motor também não ajudaria a errar: `rules/engine.py:58` e `:70` comparam kind por igualdade, e os produtores de `RuntimeContext` em `adapters/_core.py:205,216,241` usam `==`, nunca `startswith`. Tecnicamente, portanto, `emr.serverless.` passava limpo.

**Escolhi `emrs.` mesmo assim, e a medição que decidiu é outra.** `tests/test_dq_investigation_end_to_end.py:194-214` é o precedente do repositório para "área não lê o namespace da vizinha", e ele mede invasão com `k.startswith(alheio)`, onde `alheio` é `"pyspark."` ou `"dq."` (`:206,208`). A Task 6 precisa escrever exatamente esse teste para `SF-EMR` × `SF-EMRS`. Com `emr.serverless.`, **todo kind do Serverless começaria com `emr.`**, e a fronteira só seria mensurável com exceção escrita à mão dentro do próprio teste — a mesma classe de armadilha que o Step 1 da Task 6 já registra para `SF-EMR-` ser prefixo de `SF-EMRS-`. Prefixo disjunto torna a fronteira mensurável por construção. O resto do plano não precisou de ajuste.

**D-5d-12** (Task 2, Steps 3 e 5) — o snippet do plano chama `extract_emr_serverless({}, path_hint="vazio.json")`. Nenhum extrator do repositório tem esse parâmetro: `emr_cluster.py:1138` e `athena_workgroup.py:172` recebem `payload, path, artifact_sha256=""`, e é assim que `adapters/_core.py` e `scripts/regen_fixtures.py` chamam todos eles. O que fiz: assinatura `extract_emr_serverless(payload, path, artifact_sha256="")`, mais `_path` e `_tree` no mesmo formato. A Task 3 e a Task 4 dependem dessa forma, não da do plano.

**D-5d-13** (Task 2, Step 11) — o plano mandou reaproveitar a redação de segredo e, se ela estivesse embutida, **extrair para onde os dois alcancem**. A medição mostra que a duplicação é decisão registrada, não descuido: `emr_cluster.py:179-182` diz que `_looks_like_secret` "é duplicada, e não importada de `terraform.py`, pela mesma razão que `iceberg_metadata._nearest_rank` é duplicada de `event_log`: extratores são módulos independentes por desenho". A função já existe idêntica em dois arquivos (`terraform.py:259`, `emr_cluster.py:299`). Extrair reverteria uma decisão escrita, tocaria dois extratores com golden e estouraria a lista de arquivos desta task, que cria dois arquivos e não modifica nenhum. O que fiz: **duplicei os quatro padrões**, com a razão citada na docstring do módulo — e acrescentei o que é próprio desta área, a precedência de `EMR.secret@`, que não existe nos outros dois. Se o coordenador preferir a extração, ela é uma task própria sobre três extratores, não um efeito colateral desta.

**D-5d-14** (spec §4, tabela de facts) — a tabela do spec lista `scope` entre os `attrs` de `emrs.configuration`, e a D-3 remove só `level`. `scope` em `emr.configuration` é o id do grupo de instância (`emr_cluster.py:99`), e Serverless não tem grupo de instância — o campo só poderia ser string vazia. O que fiz: `emrs.configuration` não carrega `level` **nem** `scope`, pelo mesmo argumento da D-3.

**D-5d-15** (spec §4 e Task 2, Step 11) — o spec pediu `emrs.monitoring` com três booleanos. Medido contra a D-5d-4, três booleanos crus não bastam, e o motivo é assimétrico: managed persistence tem default `true` e CloudWatch tem default `false`. Omitir `managed_persistence_enabled` quando o bloco não vem faria a regra acusar o default seguro; omitir `cloudwatch_enabled` faria a regra "nenhum destino de log" **não casar justamente o caso mais comum** do estado que ela acusa, porque `engine._where_matches:34` rejeita caminho ausente. O que fiz: `emrs.monitoring` é o **único** fact deste módulo que aplica default documentado, com a razão escrita; ganhou `monitoring_declared`, `managed_persistence_declared` e `cloudwatch_declared` para o achado distinguir lido de presumido, e `measures.log_destination_count`, que é a conjunção dos três num fact só. `prometheusMonitoringConfiguration` não entra na conta (D-5d-10).

**D-5d-16** (Task 2, Step 8) — o plano mandou decidir entre materializar o default de auto-stop e omitir. **Omiti**, e a razão que decide não é de princípio, é de efeito: as duas regras que consomem esses campos acusam o estado **perigoso** (`auto_stop_enabled == false`, janela ociosa longa), e o default da AWS é o estado **seguro**; caminho ausente já produz o silêncio correto. Materializar seria trabalho extra para chegar ao mesmo lugar, correndo o risco de uma regra futura ler `auto_stop_enabled: true` como observação quando ninguém observou nada. Para que a Task 5 ainda consiga distinguir "a AWS não devolveu o bloco" de "o bloco veio", `emrs.application` ganhou `auto_stop_declared` e `auto_start_declared` — booleanos sobre o **payload**, no mesmo papel de `log_uri_present` em `emr.cluster` (`emr_cluster.py:469-474`). Não estavam previstos no spec.

**D-5d-17** (spec §4 e Task 2, Step 10) — a correlação que o spec previu é `initialCapacity` contra `maximumCapacity`. Medindo o que a Task 5 vai precisar, falta uma segunda: a P0 de custo pergunta **pré-init E auto-stop desligado**, e pela §3 do knowledge a cobrança de worker só corre com pré-init, então "auto-stop desligado" sozinho não é o mesmo defeito. Escrever isso como duas condições, uma em `emrs.application` e outra em `emrs.initial_capacity`, casaria a application A com a capacidade da application B num diretório com vários payloads — `_condition_candidates` procura candidatos em toda a lista, e `same_subject` não agrupa os dois porque os `symbol` diferem por construção. Acusar duas configurações corretas é o defeito que a D-4 existe para evitar. O que fiz: `emrs.application` carrega `measures.initial_capacity_worker_type_count`, contagem das entradas **lidas** do map, sempre emitida (zero incluso, como os contadores da sentinela). Limite escrito no módulo: zero significa que o payload não trouxe entrada, e uma regra que leia zero como "não há pré-init" afirma a partir do silêncio do payload.

**D-5d-18** (Task 2, Steps 7 e 12) — o plano previu dois commits de código, um pela sentinela e outro pelo resto. Os dois artefatos desta task são **dois arquivos novos** e um par indivisível: o teste do Step 3 importa o módulo do Step 5, e separar exigiria commitar uma versão reduzida do módulo escrita para ser desfeita no commit seguinte — narrativa fabricada, não história. O que fiz: um commit de código e um de registro de desvio, que são naturezas de fato diferentes.

**D-5d-2** (Task 1, Step 6) — o plano mandava pôr as URLs novas em `knowledge/sources.lock.json` com `rules` vazio, para preencher na Task 5. A medição mostra que isso **quebra a suíte**: `tests/test_refresh_knowledge.py:195-204` (`test_the_committed_lock_matches_the_catalog`) afirma `set(lock["sources"]) == set(watchlist())`, e `scripts/refresh_knowledge.py:158-183` deriva a watchlist **exclusivamente** dos `sources[].url` das regras do catálogo. URL sem regra que a cite não existe na watchlist, logo o lock deixa de bater. Verificado rodando a comparação com uma entrada de Serverless injetada: `False`. O que fiz: **não toquei em `sources.lock.json`**. As URLs entram na Task 5, junto com as regras que as citam — que é o Step 3 daquela task e sempre foi o lugar certo. `knowledge/INDEX.md` registra a razão para quem chegar antes de ler isto, e a lista completa de URLs está na seção `## Fontes` dos dois arquivos novos.

**D-5d-3** (Task 1, Step 4 e Task 2, Step 9) — o plano supôs `workerConfiguration.cpu`/`.memory`/`.disk` como strings com unidade **e espaço** (`"4 vCPU"`, `"16 GB"`), e alertou para a armadilha `"16 GB"` × `"16384 MB"`. A medição na referência de API é mais restritiva e desmonta metade do alerta: `cpu` é `[1-9][0-9]*(\s)?(vCPU|vcpu|VCPU)?`, `memory` é `[1-9][0-9]*(\s)?(GB|gb|gB|Gb)?`, `disk` é `[1-9][0-9]*(\s)?(GB|gb|gB|Gb)`. Ou seja: o espaço é **opcional** e os exemplos oficiais da AWS **não o usam** (`"2vCPU"`, `"4GB"`); a unidade é **opcional em `cpu` e `memory` e obrigatória em `disk`**; o número é **inteiro sem decimal**; e **`MB` não é expressável** — a armadilha do plano não pode ocorrer neste artefato. O que fiz: registrado em `knowledge/emr-serverless/application-configuration.md` §2, com os cinco desdobramentos para o extrator. O `unresolved` de unidade **continua necessário**, mas por outra razão: os patterns restringem a **entrada** da API, e nada declara que a resposta os satisfaça sempre.

**D-5d-4** (spec §5, quarta candidata) — o spec propôs *"nenhum destino de log declarado"* como transposição do `SF-EMR-006`, isto é, disparando por **ausência**. A medição derruba a forma: `ManagedPersistenceMonitoringConfiguration.enabled` *"defaults to true"*, e *"By default, EMR Serverless stores application logs securely in Amazon EMR managed storage for a maximum of 30 days."* `monitoringConfiguration` ausente significa **protegido**, não desprotegido — uma regra por ausência acusaria toda application no default seguro. O que fiz: a regra sobrevive com forma mudada, documentada em `application-configuration.md` §6 — conjunção exigindo `managedPersistenceMonitoringConfiguration.enabled == false` explícito **e** sem `s3MonitoringConfiguration.logUri` **e** CloudWatch não habilitado. A Task 5 escreve assim, e a Task 4 precisa da fixture `sem_destino_de_log` com o `enabled: false` explícito, não com o campo omitido. Bônus da mesma fonte: mesmo **com** S3, desligar managed storage custa a UI de aplicação (*"Amazon S3 bucket → Application UI: Not supported"*) — segundo achado possível, decisão da Task 5.

**D-5d-5** (spec D-5 e Task 3, Step 3) — a D-5 previa dois desfechos: matrizes idênticas (o produtor de `RuntimeContext` entra) ou divergentes (não entra). A medição encontrou um terceiro, que o spec não previu: **a documentação do EMR Serverless não publica a matriz.** As 24 páginas por release trazem só Spark, Hive e Tez; **Hadoop, Iceberg e Python não aparecem em nenhuma**, e o Spark vem **sem o sufixo `-amzn-N`** (`3.5.6`, não `3.5.6-amzn-2`). Nas 24 releases comparáveis a versão de comunidade do Spark **coincide, uma a uma** — mas três das quatro colunas de `EMR_MATRIX` não têm fonte do lado do Serverless. O que fiz: **o produtor não entra**, e a razão escrita é "sem fonte", não "divergente" (`runtime-matrix.md` §6). Para a Task 7, a linha do `STATUS.md` é **dívida**, não fase, e o texto da dívida é "a AWS não publica a matriz", não "as matrizes divergem".

**D-5d-6** (Task 2, Step 8) — o teste de exemplo do plano assume `emr-7.5.0` → `release_major == 7`, o que está certo, mas a forma do label **não é única**. A lista oficial de releases do Serverless traz `emr-spark-8.0.0` (GA, Spark 4.0.2-amzn-0) e `emr-spark-8.0-preview`, e a página do primeiro mostra `create-application --release-label emr-spark-8.0.0`. Nenhum dos dois casa com `emr-<major>.<minor>.<patch>`; o segundo tem **dois** segmentos numéricos. O que fiz: registrado em `runtime-matrix.md` §4. O extrator deve **omitir** `release_major`/`release_minor` para forma não reconhecida — nunca forçar número —, e a Task 4 deve incluir uma fixture com um desses labels. Corolário: `EMR_MATRIX` não tem chave para `emr-spark-8.0.0`, então derivar por ela falharia calada exatamente na release mais nova — mais um argumento para a D-5d-5.

**D-5d-7** (spec §5, terceira candidata) — o spec propôs `initialCapacity` acima de `maximumCapacity` como **P0**, "contradição interna". A aritmética é sustentada (unidades comparáveis, `maximumCapacity` com os mesmos patterns, e *"No new resources will be created once any one of the defined limits is hit"* autoriza tratar os eixos independentemente). O que a fonte **não** diz é se o estado é atingível: não há declaração de que a API aceite nem de que rejeite essa configuração. O que fiz: a regra sobrevive apenas como `field-heuristic`, com a reachability marcada como não documentada (`application-configuration.md` §5). A Task 5 decide entre vetar e admitir com a nota; se admitir, o golden precisa registrar que a fixture positiva é **construída, não observada**. Medição colateral que o plano vai precisar: `maximumCapacity` é `Required: No` na referência de API — o caso "não dá para decidir" do Step 10 é comum, não excepcional.

**D-5d-8** (spec §5, quinta candidata, e §4) — o spec chamou a regra de segredo de *"transposição direta do `SF-EMR-002`, sobre o mesmo formato de dado"*. O formato é o mesmo (`Configuration` com `classification`/`properties`/`configurations` aninhado), mas **a fonte não é**: o bloco *Warning* que sustenta o `SF-EMR-002` — *"Amazon EMR Describe and List API operations emit (...) in plaintext"* — **não foi encontrado na documentação do EMR Serverless**. O que sustenta a regra aqui é a frase invertida da página de Secrets Manager (*"you don't pass sensitive configuration data (...) in plain text and expose it to external APIs"*) mais o *Response Syntax* de `GetApplication`. O que fiz: a regra sobrevive, mas a Task 5 **não pode citar a URL do EC2** como fonte de uma regra `SF-EMRS`. Acréscimo de mecanismo que o spec §4 não previu: o EMR Serverless tem anotação própria, `EMR.secret@{{SecretName}}`, e um valor anotado é **ID de segredo, não segredo** — o extrator precisa reconhecê-la e **não** acusá-la, sob pena de acusar exatamente a correção que o achado pede. Isso não existe em `emr_cluster.py` e é acréscimo desta área.

**D-5d-9** (spec §5, segunda candidata) — o spec chamou a regra de auto-stop de *"mesma pergunta [do `SF-EMR-009`], unidade diferente (minutos, não segundos)"*. A unidade é o menor dos desvios. Três medições mudam a pergunta: (a) `autoStopConfiguration.enabled` *"defaults to true"* com 15 minutos, então **ausência do campo significa protegido** — o inverso do EC2, onde a política precisa ser anexada; (b) o teto é 10080 minutos = 7 dias, que é o mesmo teto do EC2 e dá número de fonte ao ramo mais permissivo; (c) **o custo da janela depende de haver pré-init**, porque a cobrança é por worker existente e *"The state of an application with no pre-initialized capacity can immediately change from `CREATED` to `STARTED`"*. Num cluster EC2 ocioso a fatura corre sempre; numa application Serverless ociosa sem pré-init, não há worker de que cobrar. O que fiz: documentado em `application-configuration.md` §3 e §4, com a tabela das quatro combinações. A Task 5 deve decidir se a regra de janela longa exige pré-init na condição — e a linha "sem pré-init não custa worker" está marcada como **dedução do modelo de cobrança**, não frase da AWS.

**D-5d-10** (spec §4, `emrs.monitoring`) — o spec listou os três destinos como `s3_log_uri_present`, `managed_persistence_enabled` e `cloudwatch_enabled`, o que está correto. Duas correções de detalhe medidas no *Response Syntax*: existe um **quarto** membro em `monitoringConfiguration`, `prometheusMonitoringConfiguration`, e ele carrega `remoteWriteUrl` (string) e **não** `enabled` — é destino de **métrica**, não de log, e não conta como destino de log. E `cloudWatchLoggingConfiguration.enabled` é `Required: Yes` **dentro do objeto**: se o objeto existe, o campo existe; o que é opcional é o objeto. O que fiz: registrado em `application-configuration.md` §6.

**D-5d-11** (transversal, não previsto em lugar nenhum do spec nem do plano) — `get-application` descreve **o padrão da application**, e `StartJobRun` o sobrepõe: *"The priority of configurations that you provide at `StartJobRun` supersede the configurations that you provide at the application level"*, com merge por classificação em `applicationConfiguration` e por tipo em `monitoringConfiguration` — inclusive **remoção** (`properties: {}`, `s3MonitoringConfiguration: {}`). Nenhum achado desta área prova o que um job run executou. O que fiz: escrito como §0 de `application-configuration.md`, antes de tudo. Toda `explanation` da Task 5 precisa carregar esse limite, e a §9 do spec ganha uma linha de **limite declarado** na Task 7. É a mesma classe de assimetria com o EC2 que a §0 explica: lá o override mora no mesmo dump; aqui mora noutro artefato, que esta fase não lê.

**D-5d-19** (Task 3, Step 1) — a medição das listas, que o Step 1 existe para fazer. **A afirmação da Fase 4b sobreviveu: são quatro**, e nenhuma mudou de lugar desde então. As quatro que a suíte REPROVA sem a entrada nova, medidas por falha e não por leitura: o `set` de `test_the_full_tool_surface_is_declared` (`tests/test_adapters_tools.py:30`, duas entradas — analyze e collect), o `set` de `test_only_collect_tools_are_open_world` (`:95`), a tupla de nomes que exigem `monkeypatch` em `_real_output_for` (`:1058`) e o dict de argumentos logo abaixo dela (`:1066`). Três achados que a contagem esconde: (a) o branch `if name == "sparkforge_analyze_emr_serverless"` de `_real_output_for` também é obrigatório, e **não é lista** — é cadeia de `if`, e falha com `AssertionError: sem construtor de argumentos reais para ...`; (b) a tupla `FAILABLE` (`:1177`) é uma **quinta** coleção onde todo `analyze_*` com `path` aparece, mas nenhum teste a deriva de `TOOLS`, então ela não reprova — entrou por simetria, não por obrigação; (c) `test_only_case_and_report_writers_are_not_read_only` é a "quarta lista manual" que o docstring do arquivo cita, e ela **não** muda aqui, porque os dois verbos novos são read-only. O docstring de `test_the_full_tool_surface_is_declared` dizia "os seis coletores AWS" e passou a dizer sete: `collect_emr_serverless` é o sétimo que toca rede.

**D-5d-20** (Task 3, Steps 2 e 4) — o plano nomeia **cinco** superfícies que precisam concordar. A medição achou uma **sexta**, que nenhuma seção do plano nem do spec cita: `ARTIFACT_KINDS` em `sparkforge/collect/base.py:29`, tupla fechada validada em `ArtifactEntry.__post_init__` (`:64-68`). Um coletor novo com `kind` fora dela levanta `ValueError` em tempo de escrita do manifesto — descoberto exatamente assim, com a suíte reprovando em `_write_and_register`. O que fiz: `"emr_serverless"` entrou na tupla, entre `emr_cluster` e `source`. Vale como aviso para quem acrescentar coletor: a lista de superfícies do plano é de superfícies *declarativas*; esta é executável e falha tarde.

**D-5d-21** (Task 3, Step 4, e fronteira com a Task 7) — o plano põe coordenador e docs na Task 7, e a Task 3 fecha com a suíte verde. **As duas coisas não cabem juntas sem tocar `agents/`.** `tests/test_agent_coverage.py:63-71` (`TestEveryToolIsReachable`) reprova toda tool que não apareça no texto de nenhum coordenador nem no das skills/executores que ele declara — tool nova é órfã por construção, e a suíte acusou as duas com nome e contagem (`2 de 40`). O que fiz, e por que **não** foi no coordenador: `agents/emr-infra-reviewer.md` declara `rule_areas: [SF-EMR, SF-ENV]` e uma `description` que diz "EMR on EC2", e a `description` é o gatilho de seleção — citar tool de Serverless ali faria o manifesto de agente afirmar cobertura que a Task 7 ainda não decidiu. As tools entraram nos dois **executores genéricos**, onde a afirmação é verdadeira sem depender de decisão futura: `sparkforge_analyze_emr_serverless` na tabela artefato→tool de `agents/executors/sf-extractor.md`, com o limite do `StartJobRun` escrito junto (D-5d-11), e `sparkforge_collect_emr_serverless` na lista de recoleta de `agents/executors/sf-inventory.md`, com a razão de exigir `applicationId`. Efeito colateral obrigatório: `python scripts/sync_skills.py` re-renderiza os três espelhos (`.claude/`, `.agents/`, `.github/`), então esta task modifica **oito** arquivos de agente, nenhum previsto na lista de arquivos do plano. `agents/executors/` e os espelhos ficam para a Task 7 apenas no que for coordenador.

**D-5d-22** (Task 3, Step 2 — a decisão que o plano delegou) — **`collect emr-serverless` NÃO chama `list-applications`.** O plano deixou a escolha em aberto "se a application exigir também `list-applications` para resolver o id a partir do nome". Ela não exige, e resolver por nome seria pior do que não resolver: `knowledge/emr-serverless/application-configuration.md` §1 mede `name` como **`Required: No`** — uma application pode não ter nenhum —, e a seção "O que estas fontes NÃO sustentam" da mesma página não lista unicidade de nome entre o que foi encontrado declarado. Um coletor que aceitasse nome escolheria uma entre N homônimas em silêncio e gravaria o artefato errado com aparência de certo. `GetApplication` aceita `applicationId` e só, então uma chamada basta e é a mesma disciplina de `collect_emr_cluster`, que aceita `j-XXXX` e nunca o `Name` do cluster. O `--application-id` da CLI carrega a razão no próprio `help`, e `TestCollectEmrServerless.test_one_call_and_only_get_application` trava a decisão contra regressão: mede que a lista de chamadas ao client é exatamente `["get_application"]`.

**D-5d-23** (Task 3, Step 4 — o alerta do coordenador sobre `--out`) — a cadeia inteira foi rodada na CLI, e **não** faltou `--out`: `analyze emr-serverless` o declara como os outros treze `analyze`, e ele grava a lista COMPLETA de facts, não a página. Medido sobre um payload de 64 facts (60 propriedades em `runtimeConfiguration`, que é o caminho fácil de estourar o teto): stdout devolve `total_count: 64, returned_count: 50, next_cursor: "50"`, `--cursor 50` devolve os 14 restantes com `next_cursor: null`, e o arquivo do `--out` tem os 64 — que `sparkforge judge --facts` lê sem erro, devolvendo zero findings porque `SF-EMRS` só existe na Task 5. Comando exato no relatório da task. Registro do que isso implica para a Task 5: **uma application real estoura a página default facilmente** — o teto de `runtimeConfiguration` é 100 itens, cada um com um map de propriedades, e cada propriedade vira um `emrs.configuration` —, então quem consumir o verbo pela tela e não pelo `--out` vê metade da configuração e não sabe.

**D-5d-24** (Task 4, Step 2) — o plano manda escrever `regen_emr_serverless` "no padrão dos existentes", e o padrão dos dois corpus de dump AWS (`regen_emr:270`, `regen_athena:257`) é um laço `for dump in sorted(input_dir.glob("*.json"))` chamando a variante `_path`. **Não segui**, e a razão é medida: três fixtures deste corpus têm mais de um payload (`capacidade_indecidivel`, `release_sem_serie`, `identidade_ausente`), e um laço por arquivo concatena blocos já ordenados, produzindo uma ordem GLOBAL diferente da que `sort_facts` devolve sobre a união. `adapters/_core.py:882` chama `extract_emr_serverless_tree` quando o `--path` é diretório, então o laço faria o golden descrever uma ordenação que nenhuma superfície do produto emite. O que fiz: `regen_emr_serverless` usa `extract_emr_serverless_tree`, e `tests/test_fixtures_golden_emr_serverless.py` extrai pela mesma porta. `regen_emr` e `regen_athena` podem continuar com o laço porque todas as fixtures deles têm um arquivo só, e com um arquivo as duas ordens coincidem.

**D-5d-25** (Task 4, Step 3) — a tabela do plano lista **oito** fixtures; o corpus fechou com **quinze**. As sete acrescentadas não são zelo, cada uma fecha um desvio já medido nas tasks anteriores: `autostop_ausente_default_seguro` (D-5d-16 — bloco ausente é o default SEGURO, e sem o par o motor não tem golden que separe "desligado de propósito" de "nunca declarado"); `capacidade_indecidivel` (D-5d-7 — `maximumCapacity` é `Required: No` e `disk` é opcional, então o indecidível é o caso COMUM, e ele traz dois payloads porque as duas causas produzem `detail` diferente); `s3_sem_managed_storage` (D-5d-4, bônus — há destino de log e mesmo assim se perde a UI de aplicação, e é o golden negativo que impede a regra de "nenhum destino" de nascer larga); `segredo_anotado_nao_e_achado` (D-5d-8 — `EMR.secret@{{Nome}}` é a CORREÇÃO, e sem golden a regra da Task 5 pode acusar o conserto que ela própria recomenda); `release_sem_serie` (D-5d-6 — os dois labels reais que não casam `emr-<major>.<minor>.<patch>`); e `secoes_malformadas` mais `identidade_ausente`, que nenhuma tabela previu e sem as quais **metade do vocabulário de `emrs.unresolved` não aparece em golden nenhum** — nove pontos cegos no primeiro, três no segundo.

**D-5d-26** (Task 4, Step 4 — a medição das duas listas) — o plano diz "duas listas precisam saber que `emr_serverless` existe". As duas foram editadas, mas **só uma reprova hoje**, e a diferença importa para quem revisar: sem a entrada em `tests/test_fixtures_kind_coverage.py:47`, `test_no_golden_carries_a_kind_that_no_extractor_declares` falha com os **seis** kinds `emrs.*` (medido rodando a agregação sem o módulo), e `test_every_kind_of_every_extractor_appears_in_some_golden` deixa de avaliar o extrator inteiro — o critério 3 do spec passaria sem ser verificado. Já `tests/test_rules_catalog_reachability.py:47` **não reprova**: a lista de regras órfãs sem `emr_serverless` é vazia, porque nenhuma regra cita kind `emrs.*` até a Task 5. Ela entra assim mesmo, no mesmo commit, exatamente pela razão que o comentário do `funcval` registra na Fase 4c: sem ela, a primeira regra `SF-EMRS` seria obrigada a declarar `blocked_on` sobre um extrator que está no repositório desde a Task 2. Nenhuma terceira lista apareceu — `scripts/verify_wheel.py:63` deriva os módulos golden do disco e o novo entrou sozinho, e `pyproject.toml:150` exclui `fixtures/` do pacote, então não há manifesto a tocar.

**D-5d-27** (Task 4, Step 3 — o `runtime` das fixtures, que o plano não menciona) — todo corpus deste repositório declara um `runtime` no `meta.yaml`, e os de dump AWS declaram a versão do serviço (`fixtures/emr/*/meta.yaml` traz `emr`, `spark`, `iceberg`). **Este corpus declara `runtime: {}`**, e a razão é a D-5d-5: a AWS não publica a matriz de release do EMR Serverless, então não há versão de Spark, Hadoop, Iceberg ou Python que o artefato sustente, e copiar a do EMR on EC2 seria a invenção que a fase inteira recusou. A razão está escrita em cada `meta.yaml`, não só aqui. **Consequência que vira contrato para a Task 5, e é o que torna a decisão útil em vez de meramente honesta:** regra `SF-EMRS` com `runtime_scope` não vazio seria PULADA neste corpus, e o golden ficaria verde sem ter avaliado nada — verde por skip é pior que vermelho, porque ninguém investiga o que passou. `TestGolden.test_no_rule_of_this_area_is_skipped_for_runtime_scope` lê o `skipped` de `judge(..., return_skipped=True)` e transforma esse silêncio em falha no minuto em que a regra entrar.

**D-5d-28** (Task 4, Step 5) — o plano fecha a task com um commit só, de `fixtures/`, `scripts/` e `tests/`. Mantive, e registro o que ele **não** contém: `expects_rules` é uniformemente `[]` nas quinze fixtures e `expected/findings.json` é `[]` em todas, porque `SF-EMRS` só nasce na Task 5. Isso é a ordem do repositório (extrator e corpus antes de regra, como na Fase 5b para `SF-EMR` e na 4c para `SF-FVAL`), não corpus incompleto. A Task 5 regenera com `python scripts/regen_fixtures.py` e os `[]` que sobrarem viram goldens NEGATIVOS reais. A verificação de apagabilidade por condição — apagar cada `when` uma por vez e conferir que algum golden fica vermelho — é do fim da Task 5, como o próprio Step 3 já dizia.

**D-5d-29** (Task 5, Step 3 — a decisão que a D-5d-4 delegou) — o bônus medido pela Task 1 virou regra: além de "nenhum destino de log" (`SF-EMRS-003`), entrou `SF-EMRS-004`, armazenamento gerenciado desligado **com** S3 presente. A fonte sustenta as duas separadamente — a tabela de opções de `logging.html` marca `Amazon S3 bucket → Application UI: Not supported`, com a recomendação explícita *"We suggest that you keep the Managed storage option selected. Otherwise, you can't use the built-in application UIs."* As duas nunca disparam juntas por construção: `SF-EMRS-003` exige contagem zero de destinos e `SF-EMRS-004` exige `s3_log_uri_present: true`. O efeito colateral é que `s3_sem_managed_storage`, que a Task 4 criou como golden NEGATIVO da regra de log, virou golden POSITIVO de `SF-EMRS-004` — e continua sendo o negativo de `SF-EMRS-003`, que é exatamente o papel que a D-5d-25 lhe deu. Total: **seis regras para cinco candidatas do spec**, nenhuma vetada por falta de fonte, duas com a forma mudada pela pesquisa.

**D-5d-30** (Task 5, Step 4 — o que a apagabilidade mediu, e o que ela custou) — o plano previa que a verificação de apagabilidade fosse só medição. **Ela reprovou duas condições e obrigou a criar uma décima sexta fixture.** `measures.initial_capacity_worker_type_count >= 1` é termo de `SF-EMRS-001` e de `SF-EMRS-005`, e nenhuma das quinze fixtures tinha application com auto-stop desligado **sem** pré-init, nem janela larga **sem** pré-init: apagar o termo dos dois `when` deixava a suíte inteira verde, isto é, a metade mais cara da conjunção não estava provada por nada. O que fiz: `fixtures/emr_serverless/sem_preinit_nada_a_cobrar/`, com dois payloads — as duas condições de auto-stop são mutuamente exclusivas e não cabem numa application só —, mais a entrada em `REQUIRED_FIXTURES` de `tests/test_fixtures_golden_emr_serverless.py`. Medido depois: apagar qualquer um dos dois termos deixa vermelha **exatamente** `sem_preinit_nada_a_cobrar`, e nenhuma outra. Consequência para a lista de arquivos: esta task cria fixture e modifica `tests/`, que o plano atribuía inteiramente à Task 4.

**D-5d-31** (Task 5, Step 2 — a forma da regra de log, contra o que a D-5d-4 desenhou) — a D-5d-4 descreveu `SF-EMRS-003` como "conjunção exigindo `managedPersistenceMonitoringConfiguration.enabled == false` **e** sem `s3MonitoringConfiguration.logUri` **e** CloudWatch não habilitado". Escrevi **uma** condição, `expr: "measures.log_destination_count == 0"`, e a razão é a própria D-5d-15: o extrator já é quem aplica os defaults documentados campo a campo, e eles são **assimétricos** — managed persistence nasce `true`, CloudWatch nasce `false`. Três `where` no catálogo teriam que carregar cada default junto para não mentir, e `_where_matches` só compara igualdade. A measure É a conjunção, calculada uma vez, sobre um fact só. Efeito sobre a apagabilidade: a condição vira uma unidade só, e apagá-la deixa `sem_destino_de_log` vermelha; a decomposição em três termos continua provada, mas em `TestAdversarial::test_the_three_points_of_the_log_destination_scale_are_in_the_corpus`, que é onde ela sempre esteve. `SF-EMRS-004`, essa sim, tem dois `where` explícitos, e os dois foram medidos apagáveis.

**D-5d-32** (Task 5, Step 2 — as duas decisões que a D-5d-9 e a D-5d-7 deixaram em aberto) — as duas foram decididas para o lado mais restritivo, e as duas com o limite escrito na própria regra. (a) **`SF-EMRS-005` EXIGE pré-init**, porque a cobrança documentada é por worker existente e uma application sem pré-init vai de `CREATED` a `STARTED` sem provisionar nada; a linha "sem pré-init não há worker de que cobrar" continua sendo **dedução do modelo de cobrança**, e está declarada como tal no item 2 do cabeçalho do catálogo e no `meta.yaml` de `sem_preinit_nada_a_cobrar` — que é o golden negativo dessa decisão e o lugar onde ela precisa mudar de lado se a AWS publicar cobrança por application existente. (b) **`SF-EMRS-006` entrou em vez de ser vetada**, como `field-heuristic`, **P1 e não a P0 que o spec pediu**: o mecanismo do dano não está declarado, só o número que se contradiz. O `explanation` carrega a leitura que torna a reachability não-documentada útil em vez de constrangedora — se a API rejeitasse o estado, `get-application` nunca o devolveria e o achado não poderia existir sobre artefato real; ele aparecer é, ele próprio, a evidência de que o estado é atingível.

**D-5d-33** (Task 5, Step 2 — três vetos que nem o spec nem a Task 1 listaram) — o cabeçalho registra sete itens, e três são desta task. **`autoStartConfiguration`** (a §4 do knowledge já o marcava como não-candidato; fica escrito no catálogo com a razão, que é ausência de custo e de risco, não ausência de fonte). **Pré-init subdimensionada** — o veto mais doloroso, porque a fonte descreve o defeito com precisão (*"the initial capacity memory configuration should be greater than the memory that the job and the overhead request"*), e o que falta é o outro lado da comparação, que mora no `StartJobRun`; uma regra que só acusasse quando o job declara a memória na application produziria silêncio exatamente onde a prática comum está. **`schedulerConfiguration`** — candidato sem fonte lida: nenhuma página desta coleta declara o default de `queueTimeoutMinutes` nem o efeito da expiração. Nenhum dos três nasce `blocked_on`, pela razão que `emr-infra.yaml` já registrava: `test_every_rule_has_a_fixture_that_fires_it` exige golden positivo para toda regra, e o motor pula regra com `blocked_on` antes de olhar os facts.

**D-5d-34** (Task 5, Step 5 — a suíte reprovou em dois lugares que nenhuma lista do plano cita) — área de regra nova não é só um arquivo YAML. `tests/test_agent_coverage.py:73` (`TestEveryRuleAreaHasACoordinator`) deriva as áreas de `{r["id"].rsplit("-", 1)[0] for r in load_catalog()}` e reprova área que nenhum coordenador declare em `rule_areas`; `tests/test_docs_coverage.py:263` compara `manifest.json::knowledge_base.rule_count` com `len(load_catalog())`, que passou de 71 para 77. **Isso contraria a D-5d-21 em parte:** lá as tools novas ficaram fora de `agents/emr-infra-reviewer.md` de propósito, para não afirmar cobertura que a Task 7 ainda não decidiu. A área não dá essa folga — alguém precisa ser dono dela, hoje. O que fiz, e é **provisório por declaração**: `SF-EMRS` entrou em `rule_areas` de `emr-infra-reviewer`, a `description` passou a nomear as duas plataformas (declarar a área sem a `description` seria o defeito que a D-5d-21 evitava, ao contrário), a tabela artefato→coordenador ganhou a linha de `get-application`, e o corpo ganhou a armadilha de `SF-EMR-` ser prefixo de `SF-EMRS-`. `python scripts/sync_skills.py` re-renderizou os três espelhos. **A Task 7 continua livre para partir isso num coordenador próprio**; o que ela não pode mais fazer é deixar a área órfã. `manifest.json` foi atualizado no mesmo commit, e ele não estava na lista de arquivos de task nenhuma.

**D-5d-35** (Task 5, Step 3 — um drift pré-existente que o lock escondia) — `tests/test_refresh_knowledge.py:195` compara apenas o **conjunto de URLs** do lock com o da watchlist; `rules` e `retrieved` de cada entrada não são verificados por teste nenhum. Ao regravar o lock com a watchlist derivada do catálogo, apareceu que `.../tuning-aws-glue-for-apache-spark/optimize-shuffles.html` tinha ganhado um segundo `retrieved` (`2026-08-03`) numa fase anterior sem que o lock fosse atualizado. Corrigido junto, porque o arquivo já estava sendo tocado. Registro do que isso significa para quem vier depois: **o lock envelhece em silêncio em tudo o que não seja a lista de URLs**, e a próxima fase que quiser fechar esse buraco precisa estender `test_the_committed_lock_matches_the_catalog` para comparar as entradas, não só as chaves.

**D-5d-36** (Task 6, Step 1 — "compare pela área declarada na regra", que não existe) — o plano manda comparar pela área declarada, e a regra carregada **não carrega área nenhuma**. `sparkforge/rules/loader.py:load_catalog` propaga do documento para dentro da regra exatamente dois campos, `catalog_version` e `_source_file` (`loader.py:222-223`); o `area:` do cabeçalho — que os quinze documentos de `rules/catalog/` declaram, `emr-infra.yaml:152` e `emr-serverless.yaml:205` incluídos — fica no documento. O mecanismo que escrevi: `_area_por_arquivo()` abre cada `*.yaml` do `catalog_dir()` e devolve `nome do arquivo -> area`, e `_source_file` é a ponte. **Robustez a regra nova no arquivo errado**, que era o requisito: `_regras_da_area` só aceita a regra se a área do documento **e** a área do id (`rsplit("-", 1)[0]`, igualdade exata) concordarem, e `test_area_do_documento_e_area_do_id_concordam` reprova sobre o catálogo inteiro quando não concordam — uma `SF-EMRS-007` escrita dentro de `emr-infra.yaml` sairia do recorte de `SF-EMRS` em silêncio, e a fronteira continuaria verde sobre uma regra que ela nunca olhou. Um detalhe de custo, porque ele explica o `lru_cache`: sem cache, reabrir os quinze documentos por regra fez o arquivo passar de **120 s**; com `@lru_cache(maxsize=1)` em `_area_por_arquivo` e em `_catalogo`, os dezessete testes rodam em segundos. Registro também um tripwire deliberado: `test_o_loader_nao_propaga_a_area_para_dentro_da_regra` reprova no dia em que o loader passar a propagar `area`, e a mensagem manda apagar o mecanismo.

**D-5d-37** (Task 6, Step 2 — a quebra proposta não é expressável; quebrei de outras duas formas) — o plano sugere "troque a área de uma regra `SF-EMRS` para `SF-EMR` no catálogo em memória". Pela D-5d-36 não há área em memória para trocar. As duas quebras que fiz usam `SPARKFORGE_CATALOG` apontando para uma **cópia mutada** do catálogo em scratch, o que também evita sujar a árvore do repositório. (a) **Regra no arquivo errado**: movi o bloco de `SF-EMRS-006` de `emr-serverless.yaml` para o fim de `emr-infra.yaml`. Vermelho em 1 de 17, e é o guarda: `AssertionError: regra em documento de outra area: [('SF-EMRS-006', 'emr-infra.yaml', 'SF-EMR')]`. (b) **Kind do outro lado**: troquei `requires_facts: [emrs.application]` por `[emr.cluster]` e o `fact:` do `when` junto, na mesma regra. Vermelho em 5 de 17, e as três mensagens que importam são `SF-EMRS-006 le ['emr.cluster'], do namespace de SF-EMR`, `SF-EMRS-006 nao exige nenhum kind 'emrs.*' em requires_facts`, e a fronteira propriamente dita: `regra de EMR Serverless disparou sobre 'describe-cluster': [('all_spot_groups_maximize', 'SF-EMRS-006', ('f_814b5a',)), ...]` — **doze** das treze fixtures de `fixtures/emr/`, cada uma com o `fact_id` que o achado citaria. Nenhum dos dois vermelhos foi erro de carregamento. Efeito colateral que vale registrar: em (b) o corpus Serverless ficou mudo para `SF-EMRS-006` e `TestOsDoisCorporaEstaoVivos` também reprovou — a classe existe para que "nenhum achado da área vizinha" nunca possa ser satisfeito por extração quebrada.

**D-5d-38** (Task 6, Step 1 — a armadilha do prefixo, medida em vez de comentada) — o plano avisa que `SF-EMR-` é prefixo de `SF-EMRS-`. O número: classificando por "primeiro prefixo que casa" sobre `["SF-EMR", "SF-EMRS"]`, o catálogo devolve **`SF-EMR` com 15 regras e `SF-EMRS` com nenhuma** — e aí `test_nenhuma_regra_emrs_dispara_sobre_ec2` passa **vacuamente**, com o conjunto vetado vazio, provando o oposto do que promete. Já a forma ingênua `[r for r in cat if r["id"].startswith(area)]` produz o defeito espelhado, um falso VERMELHO na outra direção. Só a igualdade exata sobre `rsplit` separa as duas. `test_prefixo_de_id_nao_discrimina_as_duas_areas` fixa a armadilha como asserção: afirma que todo id `SF-EMRS` casa `startswith("SF-EMR")` **e** que a comparação exata os separa mesmo assim, para que quem trocar uma pela outra encontre o teste que já disse por quê. (`startswith("SF-EMR-")`, com o hífen, seria seguro — mas depende de um caractere invisível na leitura, e não é assim que o precedente de `test_dq_investigation_end_to_end.py:194` compara área.)

**D-5d-39** (Task 6, Step 1 — os dois corpora não julgam com o mesmo runtime, e o guarda de skip é por isso) — a D-5d-27 registrou `runtime: {}` para o corpus Serverless; medido agora, os treze `meta.yaml` de `fixtures/emr/` declaram runtime **real** (`emr: "6.15.0"`, `spark`, `iceberg`). Julgar as duas direções com `{}` seria a escolha uniforme e errada: a direção "nenhuma `SF-EMRS` sobre EC2" precisa rodar no contexto em que o produto julga um cluster. Cada direção usa o `runtime` do `meta.yaml` da própria fixture, e `TestOSilencioNaoEPorEscopo` fecha o buraco que isso abre — `test_a_area_vizinha_nunca_e_pulada_por_escopo_ou_bloqueio` reprova se alguma regra da área vizinha aparecer em `skipped` por `runtime_scope` ou `blocked_on`, e `test_toda_regra_vizinha_e_calada_por_falta_de_fact` afirma o positivo: em **toda** fixture dos dois corpora, **toda** regra da área de fora aparece em `skipped` com `reason: requires_facts`. Não é que ela não disparou; é que ela foi alcançada e não teve com que se sustentar. Medido, e é o que torna a fronteira "por construção" verificável: as quinze regras das duas áreas exigem ao menos um kind do próprio namespace em `requires_facts` (`test_toda_regra_exige_ao_menos_um_kind_do_proprio_namespace`), então nenhuma delas chega a ser avaliada sobre o artefato do outro modelo de execução.

**D-5d-40** (Task 7, Steps 1 e 2 — o repositório não cobrava mais nada, e a decisão do coordenador teve de ser tomada por outro argumento) — o Step 1 esperava **vermelho** em `test_no_area_is_orphan` e possivelmente em `test_no_tool_is_orphan`, "o repositório cobrando a Task 7". Medido: `python -m pytest tests/test_agent_coverage.py -q` devolve **23 passed**. As duas cobranças foram pagas antes, e não por zelo — a D-5d-21 pôs as tools nos dois executores genéricos porque tool órfã reprova no mesmo commit que a cria, e a D-5d-34 pôs `SF-EMRS` em `rule_areas` porque área órfã reprova no mesmo commit que a cria. A suíte verde tirou da Task 7 o único sinal que o plano lhe dava, e sobrou a decisão nua: **manter estendido, ou partir**. **Mantive estendido, e o argumento não é o do spec.** A D-1 sustentava a extensão dizendo *"coordenador novo exige fronteira medida; aqui não há"* — e agora **há**: a Task 6 mediu 17 casos, zero invasões. O que salva a decisão é que **fronteira de catálogo e fronteira de despacho não são a mesma coisa**. Os 13 testes da Task 6 operam todos sobre `requires_facts`, kinds e `judge` de corpora **já roteados ao extrator certo**: nenhum deles olha nada que exista antes de o artefato ser lido. A fronteira de despacho eu medi, e ela **não existe**: `_PLATFORM_KEYS` (`sparkforge/facts/runtime_detect.py:403`) tem exatamente duas identidades, `emr` e `glue`, e nenhum fact `emrs.*` alimenta qualquer uma. Rodado sobre os dois corpora, `build_runtime(facts=...)` devolve, para `fixtures/emr/all_spot_groups_maximize`, `env.platform` com `resolved: emr` e `RuntimeContext.emr == "6.15.0"`; para `fixtures/emr_serverless/preinit_sem_autostop`, **zero** `env.platform`, **zero** `env.runtime_signal` e `ctx.emr` vazio. O par que **está** partido no repositório — `glue-infra-reviewer` × `emr-infra-reviewer` — é separado exatamente pelas duas chaves daquele dict, e `SF-ENV-005` existe para acusar quando as duas aparecem juntas. Partir `SF-EMRS` num coordenador próprio seria criar o único par sem discriminador em dado, roteado só pela `description` — prosa. O que a Task 7 fez além de manter: o `provisório por declaração` da D-5d-34 virou decisão com argumento escrito no corpo do agente, junto com a consequência operacional que ninguém tinha registrado (num artefato de Serverless o motor é **mudo** sobre plataforma, e ausência de `env.platform` ali não é evidência de que não é EMR).

**D-5d-41** (Task 7, Step 4 — a previsão sobre qual documento envelhece estava certa pela metade) — o plano diz que "`README.md` e `STATUS.md` costumam estar certos; `AGENTS.md` é o espelho em inglês que envelhece". A primeira metade **falhou**. `AGENTS.md` de fato tinha os dois números parados que o plano previu (`Seventeen extractors` e `106 distinct fact kinds`), mais a linha do `emr-infra-reviewer` declarando `SF-EMR, SF-ENV` quando o frontmatter do agente já dizia `SF-EMR, SF-EMRS, SF-ENV` desde a Task 5 — três, não dois. Mas o `STATUS.md` tinha **dois erros que nenhuma fase desta cadeia introduziu**, e os dois são de contagem sobre o próprio arquivo: (a) a linha *"Contagem corrente, depois da Fase 4c: 5 dívidas, 3 fases, 14 limites declarados — 22 linhas abertas"* contra **6, 3 e 14 — 23** linhas contadas nas três tabelas na mesma data, ou seja, a soma foi copiada e não medida; (b) *"12 de 20, sendo **3** com `agent:`"* contra **2** medidos por `sync_skills.agent_for_skill` — três skills têm declarante único, mas `diagnose-oom` cai fora porque o único declarante é o orquestrador, que foi exatamente a correção da revisão final da 4c: a linha de *Limites declarados* registrou a queda ("Sobram **duas** atribuições") e a tabela de *Números correntes* não foi ajustada junto. Os dois corrigidos, o primeiro com o registro do erro no lugar em vez de apagado. Lição para a próxima fase: "costuma estar certo" não é critério — o `README.md` estava certo em tudo o que a fase anterior mediu e errado em **seis** números que esta fase mudou, que é o comportamento normal de qualquer documento.

**D-5d-42** (Task 7, Step 3 — a `description` da skill tem teto, e o teto decide o que cabe nela) — ao ensinar o verbo novo escrevi na `description` de `skills/review-emr-cluster/SKILL.md` a mesma prosa que o corpo carrega, e a suíte reprovou: `tests/test_skill_content.py::test_frontmatter_valido` exige `len(desc) <= 1024`, e o texto foi a **1263**. A `description` já tinha 888 caracteres, então o orçamento para a plataforma nova era **136**. O que fiz: a `description` ganhou só o gatilho de seleção — o artefato (`get-application`), o verbo (`analyze emr-serverless`) e a área (`SF-EMRS`), em 124 caracteres —, e o ensino inteiro (as cinco assimetrias contra o EC2, a paginação, o limite do `StartJobRun`) foi para uma seção própria do corpo. É a divisão certa por acaso, e vale registrar por quê: a `description` é lida para **escolher** a skill, não para segui-la, e um agente que precise da regra de paginação já escolheu.
