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

- `D-5d-1` — reservado para a medição da guarda de namespace (Task 2, Step 1).

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
