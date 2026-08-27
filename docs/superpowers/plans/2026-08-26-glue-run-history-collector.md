# Coletor de histórico de runs Glue — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao SparkForge o baseline histórico que hoje não existe — um artefato por run Glue terminal, facts de distribuição por capacidade e estado, e o extrator que finalmente transforma o artefato CloudWatch já coletado em facts.

**Architecture:** Três peças independentes, cada uma no molde do vizinho que já existe. O coletor `collect_glue_job_runs` grava um JSON por run terminal em `.sparkforge/artifacts/glue_job_run/` (artefato imutável, hash estável, coleta incremental via `_offline_hit`). O extrator `facts/cloudwatch.py` lê o artefato de métricas e emite `glue.metric`. O extrator `facts/glue_job_run.py` lê o diretório de runs, emite fact por run, agrega distribuições por `(glue_version, worker_type, number_of_workers, autoscaling)` × estado terminal, e correlaciona por `job_run_id` com os facts de CloudWatch presentes. Nenhuma regra nova, nenhum custo em dinheiro.

**Tech Stack:** Python 3, `pytest`, `boto3` (opcional, importado sob demanda via `require_boto3`), `PyYAML`. Spec: [`../specs/2026-08-26-glue-run-history-collector-design.md`](../specs/2026-08-26-glue-run-history-collector-design.md).

**Convenções do repositório que valem em toda tarefa:**

- `now` é sempre parâmetro, nunca lido do relógio (`sparkforge/collect/aws.py:16`).
- `boto3` nunca é importado no topo de um módulo; só `require_boto3()` toca o import.
- Fact nunca aplica limiar, nunca atribui severidade (`sparkforge/findings/models.py:32`).
- Todo comando roda com prefixo `rtk` (ver `CLAUDE.md`): `rtk pytest`, `rtk git commit`.

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `knowledge/glue/observability.yaml` | Tabela de retenção do CloudWatch por período, legível por máquina |
| `sparkforge/facts/cloudwatch_retention.py` | Carregador fail-closed do YAML acima, no molde de `facts/pricing.py` |
| `sparkforge/facts/cloudwatch.py` | Extrator do artefato CloudWatch em facts `glue.metric` |
| `sparkforge/facts/glue_job_run.py` | Extrator do diretório de runs em facts de run, distribuição e outcome |
| `tests/test_facts_cloudwatch.py` | Testes do extrator de métricas |
| `tests/test_facts_glue_job_run.py` | Testes do extrator de histórico |
| `tests/test_cloudwatch_retention.py` | Testes do carregador de retenção |
| `fixtures/glue_job_run/` | Respostas sintéticas de `GetJobRuns` e artefatos CloudWatch pareados |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/collect/base.py:29` | `ARTIFACT_KINDS` ganha `"glue_job_run"` |
| `sparkforge/collect/aws.py` | `glue_job_run_path`, `collect_glue_job_runs`, período derivado em `collect_cloudwatch` |
| `sparkforge/adapters/_core.py` | `collect_glue_job_runs`, `analyze_cloudwatch`, `analyze_glue_job_runs` |
| `sparkforge/adapters/cli.py` | Três parsers, três handlers, três entradas de despacho |
| `sparkforge/adapters/tools.py` | Três schemas de tool, três handlers, três entradas de despacho |
| `manifest.json:80` | Lista `tools` ganha as três |
| `parity.yaml:438` | Capability de coleta ganha a CLI e a tool novas |
| `knowledge/glue/observability.md` | Seção de retenção apontando para o YAML |
| `knowledge/sources.lock.json` | Fonte da retenção com `retrieved`, `checked_at`, `sha256` |
| `tests/test_collect_aws.py` | Casos do coletor novo |
| `README.md`, `docs/superpowers/STATUS.md` | Os três comandos e a fase |

---

## Task 1: Conhecimento de retenção do CloudWatch

A derivação de período depende de quanto tempo o CloudWatch guarda pontos de cada granularidade. Esse número não pode nascer em constante Python: `sparkforge/facts/pricing.py` existe justamente porque número sem procedência envelhece em silêncio e passa por preciso.

**Files:**
- Create: `knowledge/glue/observability.yaml`
- Modify: `knowledge/glue/observability.md` (seção nova antes de `## Fontes`)
- Modify: `knowledge/sources.lock.json`

- [ ] **Step 1: Ler a fonte oficial e anotar os valores**

Abra `https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html` e localize a seção sobre retenção de dados de métrica. Anote, para cada granularidade de ponto, o período em segundos e a retenção em dias, e a data de hoje como `retrieved`.

Se os valores da documentação divergirem dos que aparecem no exemplo do Step 2, **a documentação vence** — escreva o que a fonte diz, não o que o exemplo mostra.

- [ ] **Step 2: Escrever o YAML**

Crie `knowledge/glue/observability.yaml` com os valores lidos. Substitua `<AAAA-MM-DD>` pela data de consulta e confira cada par contra a fonte:

```yaml
# Retencao de dados de metrica do CloudWatch, por granularidade do ponto.
#
# POR QUE ESTE ARQUIVO EXISTE. `collect_cloudwatch` consultava com
# `Period: 30` fixo. Ponto de granularidade sub-minuto sobrevive poucas
# horas; a mesma query sobre um run de vinte dias atras devolve serie
# vazia -- e vazio se parece com "observabilidade desligada no job", que e
# causa diferente e remedio diferente. Derivar o periodo da idade do run
# exige a tabela, e a tabela precisa de fonte com data.
#
# Numero de retencao codificado em Python seria o defeito que
# `sparkforge/facts/pricing.py` existe para nao repetir.

schema_version: 1

retention:
  - period_seconds: 60
    retention_days: 15
    source: "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html"
    source_type: official_doc
    retrieved: "<AAAA-MM-DD>"
  - period_seconds: 300
    retention_days: 63
    source: "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html"
    source_type: official_doc
    retrieved: "<AAAA-MM-DD>"
  - period_seconds: 3600
    retention_days: 455
    source: "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html"
    source_type: official_doc
    retrieved: "<AAAA-MM-DD>"
```

`source_type` precisa ser um dos valores de `SOURCE_TYPES` em `sparkforge/facts/runtime_matrix.py`. Abra o arquivo e confirme o valor exato antes de escrever; se `official_doc` não estiver na lista, use o que estiver.

- [ ] **Step 3: Apontar o Markdown para o YAML**

Em `knowledge/glue/observability.md`, imediatamente antes da seção `## Fontes`, insira:

```markdown
## 6. Retenção de métrica por período

A granularidade do ponto decide por quanto tempo o CloudWatch o guarda. A tabela está em
[`observability.yaml`](observability.yaml), legível por máquina e carregada por
`sparkforge/facts/cloudwatch_retention.py` — não é repetida aqui de propósito: duas cópias do
mesmo número divergem, e a que o código lê é a do YAML.

Consequência prática: consultar um run antigo com período curto devolve série vazia. Vazio por
expiração e vazio por observabilidade desligada no job têm remédios opostos, e a saída precisa
dizer qual dos dois é.
```

Acrescente à lista `## Fontes` do mesmo arquivo:

```markdown
- Amazon CloudWatch concepts — retenção de dados de métrica por granularidade. https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html (retrieved <AAAA-MM-DD>)
```

- [ ] **Step 4: Registrar a fonte no lock**

Calcule o sha256 normalizado da página com as funções que o repositório já tem:

```bash
rtk python -c "from scripts.refresh_knowledge import http_fetch, normalize, digest; url='https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html'; print(digest(normalize(http_fetch(url))))"
```

Adicione a entrada em `knowledge/sources.lock.json`, dentro de `sources`, com a mesma forma das existentes (`checked_at`, `docs`, `pinned`, `retrieved`, `rules`, `sha256`). `rules` fica `[]`: nenhuma regra consome retenção — quem consome é o coletor.

```json
"https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html": {
  "checked_at": "<AAAA-MM-DD>",
  "docs": [
    "knowledge/glue/observability.md",
    "knowledge/glue/observability.yaml"
  ],
  "pinned": false,
  "retrieved": [
    "<AAAA-MM-DD>"
  ],
  "rules": [],
  "sha256": "<saida do comando acima>"
}
```

- [ ] **Step 5: Rodar os gates de conhecimento**

```bash
rtk pytest tests/test_adapters_knowledge.py tests/test_docs_coverage.py -v
```

Esperado: PASS. Se um teste exigir que todo arquivo de `knowledge/` esteja indexado em `knowledge/INDEX.md`, acrescente a linha do YAML lá no formato das vizinhas e rode de novo.

- [ ] **Step 6: Commit**

```bash
rtk git add knowledge/glue/observability.yaml knowledge/glue/observability.md knowledge/sources.lock.json knowledge/INDEX.md
rtk git commit -m "docs(knowledge): retencao de metrica do CloudWatch, com data e sha256"
```

---

## Task 2: Carregador da retenção

**Files:**
- Create: `sparkforge/facts/cloudwatch_retention.py`
- Test: `tests/test_cloudwatch_retention.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes do carregador de retencao de metrica do CloudWatch."""
from __future__ import annotations

import pytest

from sparkforge.facts import cloudwatch_retention as cwr


class TestTable:
    def test_loads_entries_sorted_by_period(self):
        table = cwr.retention_table()
        assert table, "tabela de retencao vazia"
        periods = [entry["period_seconds"] for entry in table]
        assert periods == sorted(periods)

    def test_every_entry_declares_evidence(self):
        for entry in cwr.retention_table():
            for field in ("source", "source_type", "retrieved"):
                assert entry.get(field), f"entrada sem {field}: {entry}"


class TestPeriodForAge:
    def test_recent_run_gets_the_finest_period(self):
        assert cwr.period_for_age_days(0.0) == 60

    def test_run_older_than_the_finest_retention_escalates(self):
        assert cwr.period_for_age_days(20.0) == 300

    def test_run_older_than_every_retention_returns_none(self):
        assert cwr.period_for_age_days(100_000.0) is None

    def test_negative_age_is_rejected(self):
        with pytest.raises(ValueError, match="idade negativa"):
            cwr.period_for_age_days(-1.0)
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_cloudwatch_retention.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.cloudwatch_retention'`.

- [ ] **Step 3: Implementar o carregador**

```python
"""Carrega a retencao de metrica do CloudWatch como dado com data e fonte.

POR QUE ESTE MODULO NAO FIXA NUMERO. `collect_cloudwatch` consultava com
`Period: 30` fixo, e ponto de granularidade sub-minuto sobrevive poucas horas
no CloudWatch. A mesma query sobre um run de vinte dias atras devolve serie
vazia, e vazio se parece com observabilidade desligada no job -- causa
diferente, remedio diferente.

Derivar o periodo da idade do run exige a tabela de retencao, e a tabela
precisa vir de `knowledge/glue/observability.yaml`, com fonte e data, pela
mesma razao de `sparkforge/facts/pricing.py`: numero envelhecido nao parece
errado, parece preciso.

Fail-closed no mesmo molde: entrada sem `source`, `source_type` ou `retrieved`
carregaria em silencio e viraria, tres saltos adiante, uma query que devolve
vazio sem ninguem saber por que.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from sparkforge.facts.runtime_matrix import SOURCE_TYPES
from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

_ARQUIVO = "glue/observability.yaml"
_CAMPOS_DE_EVIDENCIA = ("source", "source_type", "retrieved")
_CAMPOS_DE_RETENCAO = ("period_seconds", "retention_days")


class RetentionError(ValueError):
    """Tabela de retencao ausente, vazia ou com entrada sem evidencia."""


def _validar(indice: int, entrada: Any) -> None:
    rotulo = f"retention[{indice}]"
    if not isinstance(entrada, dict):
        raise RetentionError(
            f"{rotulo}: entrada precisa ser um mapa, veio {type(entrada).__name__}"
        )
    for campo in _CAMPOS_DE_RETENCAO:
        valor = entrada.get(campo)
        if not isinstance(valor, int) or valor <= 0:
            raise RetentionError(f"{rotulo}: {campo} precisa ser inteiro positivo, veio {valor!r}")
    for campo in _CAMPOS_DE_EVIDENCIA:
        if not entrada.get(campo):
            raise RetentionError(
                f"{rotulo}: sem {campo}. Retencao sem procedencia carrega em silencio e "
                f"vira uma query que devolve vazio sem razao declarada"
            )
    if entrada["source_type"] not in SOURCE_TYPES:
        raise RetentionError(
            f"{rotulo}: source_type {entrada['source_type']!r} fora de {sorted(SOURCE_TYPES)}"
        )


@lru_cache(maxsize=1)
def retention_table() -> tuple[dict[str, Any], ...]:
    """A tabela lida do YAML, ordenada por periodo crescente."""
    caminho = safe_knowledge_file(knowledge_dir(), _ARQUIVO)
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    entradas = dados.get("retention") or []
    if not entradas:
        raise RetentionError(f"{_ARQUIVO}: lista `retention` ausente ou vazia")
    for indice, entrada in enumerate(entradas):
        _validar(indice, entrada)
    return tuple(sorted(entradas, key=lambda e: e["period_seconds"]))


def period_for_age_days(age_days: float) -> int | None:
    """O menor periodo cuja retencao ainda cobre um ponto com esta idade.

    Menor periodo primeiro porque granularidade mais fina e sempre preferivel
    enquanto o dado existe. `None` diz que nenhum periodo cobre -- o ponto
    expirou em todas as granularidades, e quem chamar precisa dizer isso em vez
    de consultar e receber vazio.
    """
    if age_days < 0:
        raise ValueError(f"idade negativa: {age_days}")
    for entrada in retention_table():
        if age_days <= entrada["retention_days"]:
            return int(entrada["period_seconds"])
    return None
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_cloudwatch_retention.py -v
```

Esperado: PASS, 6 testes. Se `test_recent_run_gets_the_finest_period` falhar porque o menor período do YAML não é 60, ajuste a asserção do teste para o valor que a fonte oficial declarou — o teste segue a fonte, não o contrário.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/cloudwatch_retention.py tests/test_cloudwatch_retention.py
rtk git commit -m "feat(knowledge): carregador fail-closed da retencao de metrica"
```

---

## Task 3: Novo kind de artefato e caminho do run

**Files:**
- Modify: `sparkforge/collect/base.py:29`
- Modify: `sparkforge/collect/aws.py` (após `glue_job_path`, linha 122)
- Test: `tests/test_collect_base.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_collect_base.py`:

```python
class TestGlueJobRunKind:
    def test_glue_job_run_is_an_accepted_kind(self):
        from sparkforge.collect.base import ArtifactEntry

        entry = ArtifactEntry(
            kind="glue_job_run",
            path=".sparkforge/artifacts/glue_job_run/job_jr_1.json",
            sha256="a" * 64,
            source="glue:get_job_runs:job",
            collect_command="sparkforge collect glue-job-runs --job-name job",
            collected_at="2026-08-26T00:00:00Z",
        )
        assert entry.kind == "glue_job_run"

    def test_path_helper_separates_job_from_run(self):
        from sparkforge.collect import aws

        assert (
            aws.glue_job_run_path("my-job", "jr_abc")
            == ".sparkforge/artifacts/glue_job_run/my-job_jr_abc.json"
        )
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_collect_base.py::TestGlueJobRunKind -v
```

Esperado: FAIL com `ValueError: kind desconhecido: 'glue_job_run'`.

- [ ] **Step 3: Implementar**

Em `sparkforge/collect/base.py`, dentro de `ARTIFACT_KINDS`, acrescente `"glue_job_run",` logo após `"cloudwatch",`:

```python
ARTIFACT_KINDS = (
    "event_log",
    "terraform",
    "explain",
    "cloudwatch",
    "glue_job_run",
    "iceberg_metadata",
    "athena_workgroup",
    "emr_cluster",
    "emr_serverless",
    "source",
)
```

Em `sparkforge/collect/aws.py`, logo após `glue_job_path`:

```python
def glue_job_run_path(job_name: str, job_run_id: str) -> str:
    return f".sparkforge/artifacts/glue_job_run/{job_name}_{job_run_id}.json"
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_collect_base.py -v
```

Esperado: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/collect/base.py sparkforge/collect/aws.py tests/test_collect_base.py
rtk git commit -m "feat(collect): kind glue_job_run e o caminho de um run por arquivo"
```

---

## Task 4: Coletor `collect_glue_job_runs`

**Files:**
- Modify: `sparkforge/collect/aws.py` (após `collect_glue_job`, linha 328)
- Test: `tests/test_collect_aws.py`

- [ ] **Step 1: Escrever o fake e o primeiro teste**

Acrescente a `tests/test_collect_aws.py`, depois de `FakeGlueClient`:

```python
class FakeGlueRunsClient:
    """`get_job_runs` paginado. Cada item de `pages` e uma resposta completa."""

    def __init__(self, pages: list[dict]):
        self.calls: list[tuple[str, dict]] = []
        self._pages = pages

    def get_job_runs(self, **kwargs):
        self.calls.append(("get_job_runs", kwargs))
        index = 0 if "NextToken" not in kwargs else int(kwargs["NextToken"])
        return self._pages[index]


class EntityNotFoundException(Exception):
    """Reproduz o nome da excecao que botocore levanta para job inexistente."""


class MissingJobGlueClient:
    def get_job_runs(self, **kwargs):
        raise EntityNotFoundException("Job with name: nope not found")


def _run(run_id: str, state: str = "SUCCEEDED", **extra) -> dict:
    base = {
        "Id": run_id,
        "JobName": "my-job",
        "JobRunState": state,
        "StartedOn": "2026-08-01T10:00:00+00:00",
        "CompletedOn": "2026-08-01T10:20:00+00:00",
        "ExecutionTime": 1200,
        "GlueVersion": "5.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 10,
        "Timeout": 60,
    }
    base.update(extra)
    return base


class TestCollectGlueJobRuns:
    def test_writes_one_artifact_per_terminal_run(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": [_run("jr_1"), _run("jr_2")]}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert len(result["artifacts"]) == 2
        assert (tmp_path / aws.glue_job_run_path("my-job", "jr_1")).is_file()
        assert (tmp_path / aws.glue_job_run_path("my-job", "jr_2")).is_file()
        kinds = {e["kind"] for e in load_manifest(tmp_path)}
        assert kinds == {"glue_job_run"}
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_collect_aws.py::TestCollectGlueJobRuns -v
```

Esperado: FAIL com `AttributeError: module 'sparkforge.collect.aws' has no attribute 'collect_glue_job_runs'`.

- [ ] **Step 3: Implementar o coletor**

Em `sparkforge/collect/aws.py`, acrescente perto do topo, junto das outras constantes de módulo:

```python
# Estados em que um job run nao muda mais. So estes viram artefato: gravar um
# run ainda em execucao produziria um arquivo cujo conteudo muda depois, e a
# proxima coleta veria o sha256 divergir -- o cache offline-first viraria um
# falso negativo permanente para aquele run.
TERMINAL_JOB_RUN_STATES: frozenset[str] = frozenset(
    {"SUCCEEDED", "FAILED", "TIMEOUT", "STOPPED", "ERROR"}
)

# Teto por pagina que a API aceita. `max_runs` do chamador ainda limita o total.
_GET_JOB_RUNS_PAGE_SIZE = 200
```

E, após `collect_glue_job`:

```python
def collect_glue_job_runs(
    job_name: str, root: Path, *, max_runs: int, now: str
) -> dict[str, Any]:
    """Baixa o historico de execucoes de um job via `glue.get_job_runs`.

    Um arquivo por run TERMINAL, e nao um arquivo por janela: `GetJobRuns`
    devolve uma janela movel, e o manifesto assume artefato imutavel verificado
    por sha256. Um run por arquivo reconcilia os dois -- e da coleta incremental
    de graca, porque `_offline_hit` reconhece o que ja esta em disco.

    Diferenca dos coletores de artefato unico: a listagem SEMPRE toca a rede.
    Nao ha como saber quais runs existem sem perguntar. O que o cache evita e
    reescrever e reregistrar o que ja esta integro no disco, e e isso que
    `cache_hit` por run informa.

    `max_runs` e teto de paginacao, nao filtro de data: a API devolve do mais
    recente para tras e nao aceita janela temporal. Expor `--start`/`--end` seria
    filtro do lado do cliente disfarcado de parametro de API.
    """
    if max_runs < 1:
        raise ValueError(f"max_runs precisa ser >= 1, veio {max_runs}")

    boto3 = require_boto3()
    client = boto3.client("glue")

    artifacts: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen = 0
    token: str | None = None

    while seen < max_runs:
        kwargs: dict[str, Any] = {
            "JobName": job_name,
            "MaxResults": min(_GET_JOB_RUNS_PAGE_SIZE, max_runs - seen),
        }
        if token:
            kwargs["NextToken"] = token
        try:
            page = client.get_job_runs(**kwargs)
        except Exception as exc:  # noqa: BLE001 -- botocore nao e importavel aqui
            # `botocore` gera as classes de excecao em tempo de execucao a
            # partir do modelo do servico, e este modulo nunca importa boto3 no
            # topo. Casar pelo NOME da classe e o unico jeito de distinguir
            # "job nao existe" de uma falha de rede sem acoplar ao botocore.
            if type(exc).__name__ == "EntityNotFoundException":
                raise CollectionFailed(
                    f"Job {job_name!r} nao existe na conta/regiao correntes. "
                    f"Confira o nome com `aws glue list-jobs`."
                ) from exc
            raise

        runs = page.get("JobRuns") or []
        for run in runs:
            seen += 1
            state = run.get("JobRunState") or ""
            run_id = run.get("Id") or ""
            if state not in TERMINAL_JOB_RUN_STATES:
                skipped.append({"job_run_id": run_id, "state": state})
                continue
            artifacts.append(_write_job_run(job_name, run_id, run, root, now=now))

        token = page.get("NextToken")
        if not token:
            break

    return {
        "job_name": job_name,
        "artifacts": artifacts,
        "skipped": skipped,
        "runs_listed": seen,
    }


def _write_job_run(
    job_name: str, run_id: str, run: dict[str, Any], root: Path, *, now: str
) -> dict[str, Any]:
    rel_path = glue_job_run_path(job_name, run_id)
    collect_command = (
        f"sparkforge collect glue-job-runs --job-name {job_name} --max-runs 30"
    )
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        payload = hit.to_dict()
        payload["cache_hit"] = True
        return payload

    content = json.dumps(
        run, indent=2, sort_keys=True, default=str, ensure_ascii=False
    ).encode("utf-8")
    entry = _write_and_register(
        root,
        rel_path,
        content,
        kind="glue_job_run",
        source=f"glue:get_job_runs:{job_name}/{run_id}",
        collect_command=collect_command,
        now=now,
    )
    payload = entry.to_dict()
    payload["cache_hit"] = False
    return payload
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_collect_aws.py::TestCollectGlueJobRuns -v
```

Esperado: PASS.

- [ ] **Step 5: Escrever os testes restantes do coletor**

Acrescente à mesma classe `TestCollectGlueJobRuns`:

```python
    def test_non_terminal_run_is_skipped_not_written(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient(
            [{"JobRuns": [_run("jr_1"), _run("jr_2", state="RUNNING")]}]
        )
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert len(result["artifacts"]) == 1
        assert result["skipped"] == [{"job_run_id": "jr_2", "state": "RUNNING"}]
        assert not (tmp_path / aws.glue_job_run_path("my-job", "jr_2")).exists()

    def test_second_collection_only_writes_the_new_runs(self, tmp_path, monkeypatch):
        first = FakeGlueRunsClient([{"JobRuns": [_run("jr_1"), _run("jr_2")]}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=first))
        aws.collect_glue_job_runs("my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z")

        second = FakeGlueRunsClient(
            [{"JobRuns": [_run("jr_3"), _run("jr_1"), _run("jr_2")]}]
        )
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=second))
        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-27T00:00:00Z"
        )

        cache_hits = [a for a in result["artifacts"] if a["cache_hit"]]
        fresh = [a for a in result["artifacts"] if not a["cache_hit"]]
        assert len(cache_hits) == 2
        assert len(fresh) == 1
        assert fresh[0]["path"] == aws.glue_job_run_path("my-job", "jr_3")

    def test_recollects_when_local_file_is_corrupted(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": [_run("jr_1")]}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))
        aws.collect_glue_job_runs("my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z")

        target = tmp_path / aws.glue_job_run_path("my-job", "jr_1")
        target.write_text("corrompido", encoding="utf-8")

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-27T00:00:00Z"
        )

        assert result["artifacts"][0]["cache_hit"] is False
        assert json.loads(target.read_text(encoding="utf-8"))["Id"] == "jr_1"
        assert all(v["hash_matches"] for v in verify_all(tmp_path))

    def test_follows_pagination_until_max_runs(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient(
            [
                {"JobRuns": [_run("jr_1")], "NextToken": "1"},
                {"JobRuns": [_run("jr_2")]},
            ]
        )
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert len(result["artifacts"]) == 2
        assert len(glue.calls) == 2

    def test_stops_at_max_runs_without_extra_calls(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": [_run("jr_1")], "NextToken": "1"}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=1, now="2026-08-26T00:00:00Z"
        )

        assert result["runs_listed"] == 1
        assert len(glue.calls) == 1

    def test_job_without_runs_succeeds_with_nothing_collected(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": []}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert result["artifacts"] == []
        assert result["skipped"] == []

    def test_missing_job_raises_collection_failed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            aws, "require_boto3", lambda: FakeBoto3(glue=MissingJobGlueClient())
        )
        with pytest.raises(aws.CollectionFailed, match="nao existe"):
            aws.collect_glue_job_runs(
                "nope", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
            )

    def test_raises_collector_unavailable_when_boto3_absent(self, tmp_path, monkeypatch):
        def boom():
            raise CollectorUnavailable("boto3 nao disponivel")

        monkeypatch.setattr(aws, "require_boto3", boom)
        with pytest.raises(CollectorUnavailable, match="boto3"):
            aws.collect_glue_job_runs(
                "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
            )
```

- [ ] **Step 6: Rodar e ver passar**

```bash
rtk pytest tests/test_collect_aws.py -v
```

Esperado: PASS, incluindo os 9 casos de `TestCollectGlueJobRuns`.

- [ ] **Step 7: Commit**

```bash
rtk git add sparkforge/collect/aws.py tests/test_collect_aws.py
rtk git commit -m "feat(collect): historico de runs Glue, um artefato por run terminal"
```

---

## Task 5: Período derivado em `collect_cloudwatch`

**Files:**
- Modify: `sparkforge/collect/aws.py:340-405`
- Test: `tests/test_collect_aws.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_collect_aws.py`:

```python
class TestCloudWatchPeriod:
    def test_recent_run_uses_the_finest_period(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        aws.collect_cloudwatch(
            "my-job",
            "jr_1",
            tmp_path,
            now="2026-08-26T00:00:00Z",
            start="2026-08-26T10:00:00Z",
            end="2026-08-26T10:20:00Z",
        )

        periods = {
            q["MetricStat"]["Period"]
            for _, kwargs in cw.calls
            for q in kwargs["MetricDataQueries"]
        }
        assert periods == {60}

    def test_old_run_escalates_the_period(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        aws.collect_cloudwatch(
            "my-job",
            "jr_old",
            tmp_path,
            now="2026-08-26T00:00:00Z",
            start="2026-08-01T10:00:00Z",
            end="2026-08-01T10:20:00Z",
        )

        periods = {
            q["MetricStat"]["Period"]
            for _, kwargs in cw.calls
            for q in kwargs["MetricDataQueries"]
        }
        assert periods == {300}

    def test_expired_run_fails_instead_of_querying(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        with pytest.raises(aws.CollectionFailed, match="expirad"):
            aws.collect_cloudwatch(
                "my-job",
                "jr_ancient",
                tmp_path,
                now="2026-08-26T00:00:00Z",
                start="2020-01-01T10:00:00Z",
                end="2020-01-01T10:20:00Z",
            )
        assert cw.calls == []

    def test_period_is_recorded_in_the_artifact(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        aws.collect_cloudwatch(
            "my-job",
            "jr_1",
            tmp_path,
            now="2026-08-26T00:00:00Z",
            start="2026-08-26T10:00:00Z",
            end="2026-08-26T10:20:00Z",
        )

        payload = json.loads(
            (tmp_path / aws.cloudwatch_path("my-job", "jr_1")).read_text(encoding="utf-8")
        )
        assert payload["period_seconds"] == 60
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_collect_aws.py::TestCloudWatchPeriod -v
```

Esperado: FAIL — o primeiro caso acusa `{30} != {60}`.

- [ ] **Step 3: Implementar**

No topo de `sparkforge/collect/aws.py`, junto dos outros imports:

```python
from sparkforge.facts.cloudwatch_retention import period_for_age_days
```

Substitua o corpo de `collect_cloudwatch` entre `client = boto3.client("cloudwatch")` e a montagem de `queries` por:

```python
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)

    # O periodo vem da idade do run, nunca fixo. Ponto de granularidade fina
    # expira; consultar um run antigo com periodo curto devolve serie vazia, e
    # vazio se parece com "observabilidade desligada no job" -- causa diferente
    # e remedio diferente. A tabela de retencao esta em
    # `knowledge/glue/observability.yaml`, com fonte e data.
    age_days = (_parse_iso(now) - end_dt).total_seconds() / 86400.0
    period = period_for_age_days(max(age_days, 0.0))
    if period is None:
        raise CollectionFailed(
            f"Metrica de {job_name}/{job_run_id} expirada: o run terminou em {end}, "
            f"fora da janela de retencao de toda granularidade publicada em "
            f"knowledge/glue/observability.yaml. Consultar assim mesmo devolveria "
            f"serie vazia, indistinguivel de observabilidade desligada no job."
        )

    dimensions = [
        {"Name": "JobName", "Value": job_name},
        {"Name": "JobRunId", "Value": job_run_id},
    ]
    queries = [
        {
            "Id": f"m{index}",
            "MetricStat": {
                "Metric": {"Namespace": "Glue", "MetricName": metric, "Dimensions": dimensions},
                "Period": period,
                "Stat": stat,
            },
            "Label": metric,
            "ReturnData": True,
        }
        for index, (metric, stat) in enumerate(CLOUDWATCH_METRICS)
    ]
```

E acrescente `period_seconds` ao payload gravado:

```python
    payload = {
        "job_name": job_name,
        "job_run_id": job_run_id,
        "start": start,
        "end": end,
        "period_seconds": period,
        "metric_data_results": response.get("MetricDataResults") or [],
    }
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_collect_aws.py -v
```

Esperado: PASS. Um teste antigo que asserte `Period == 30` deve ser atualizado para o período derivado — a mudança é intencional e o motivo está no comentário do código.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/collect/aws.py tests/test_collect_aws.py
rtk git commit -m "fix(collect): periodo do CloudWatch derivado da idade do run"
```

---

## Task 6: Extrator `analyze cloudwatch`

**Files:**
- Create: `sparkforge/facts/cloudwatch.py`
- Test: `tests/test_facts_cloudwatch.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes do extrator do artefato CloudWatch em Facts."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.cloudwatch import extract_cloudwatch_path


def _artifact(tmp_path: Path, results: list[dict], period: int = 60) -> Path:
    payload = {
        "job_name": "my-job",
        "job_run_id": "jr_1",
        "start": "2026-08-26T10:00:00Z",
        "end": "2026-08-26T10:20:00Z",
        "period_seconds": period,
        "metric_data_results": results,
    }
    target = tmp_path / "cw.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestExtract:
    def test_emits_one_fact_per_metric_with_values(self, tmp_path):
        target = _artifact(
            tmp_path,
            [
                {
                    "Id": "m0",
                    "Label": "glue.driver.workerUtilization",
                    "Timestamps": ["t1", "t2", "t3"],
                    "Values": [0.3, 0.9, 0.6],
                }
            ],
        )

        facts = extract_cloudwatch_path(target)
        metric = [f for f in facts if f.kind == "glue.metric"]

        assert len(metric) == 1
        assert metric[0].subject == {"job_name": "my-job", "job_run_id": "jr_1"}
        assert metric[0].attrs["name"] == "glue.driver.workerUtilization"
        assert metric[0].attrs["period_s"] == 60
        assert metric[0].measures["min"] == 0.3
        assert metric[0].measures["max"] == 0.9
        assert metric[0].measures["p50"] == 0.6
        assert metric[0].measures["datapoints"] == 3

    def test_carries_the_stat_the_metric_requires(self, tmp_path):
        target = _artifact(
            tmp_path,
            [{"Id": "m0", "Label": "glue.error.ALL", "Timestamps": ["t1"], "Values": [2.0]}],
        )

        fact = [f for f in extract_cloudwatch_path(target) if f.kind == "glue.metric"][0]
        assert fact.attrs["stat"] == "Sum"

    def test_empty_series_becomes_unresolved_not_a_zero(self, tmp_path):
        target = _artifact(
            tmp_path,
            [
                {
                    "Id": "m0",
                    "Label": "glue.driver.workerUtilization",
                    "Timestamps": [],
                    "Values": [],
                }
            ],
        )

        facts = extract_cloudwatch_path(target)
        assert not [f for f in facts if f.kind == "glue.metric"]
        unresolved = [f for f in facts if f.kind == "glue.metric.unresolved"]
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "empty_series"

    def test_analyzed_fact_declares_the_counts(self, tmp_path):
        target = _artifact(
            tmp_path,
            [
                {"Id": "m0", "Label": "glue.error.ALL", "Timestamps": ["t"], "Values": [1.0]},
                {
                    "Id": "m1",
                    "Label": "glue.driver.workerUtilization",
                    "Timestamps": [],
                    "Values": [],
                },
            ],
        )

        analyzed = [f for f in extract_cloudwatch_path(target) if f.kind == "glue.metric.analyzed"]
        assert len(analyzed) == 1
        assert analyzed[0].measures == {"metrics_with_data": 1, "metrics_empty": 1}
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_cloudwatch.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.cloudwatch'`.

- [ ] **Step 3: Implementar**

```python
"""Extrator do artefato de metricas do CloudWatch em Facts.

POR QUE ESTE MODULO NASCEU DEPOIS DO COLETOR. `collect_cloudwatch` existia,
gravava o artefato e o registrava no manifesto, e nenhum consumidor o lia --
`glue.driver.*` aparecia no catalogo de regras apenas em texto de
`validation:`, nunca como `kind` casado por um `when:`. Artefato coletado sem
extrator e custo de coleta sem retorno.

Um `kind` so, `glue.metric`, discriminado por `attrs.name`, no molde de
`tf.attribute` -- e nao dezessete kinds, um por metrica. Como nenhuma regra
consumia CloudWatch, a forma estava livre; a escolhida e a que o motor de
regras ja sabe casar.

Puro e deterministico como os extratores irmaos: nunca aplica limiar, nunca
atribui severidade, nunca toca a rede.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.collect.aws import CLOUDWATCH_METRICS
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "cloudwatch@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "glue.metric",
        "glue.metric.unresolved",
        "glue.metric.analyzed",
    }
)

# Estatistica exigida por metrica, de `CLOUDWATCH_METRICS`. Vai para dentro do
# fact porque `glue.error.ALL` e contador documentado como Sum: um leitor que
# nao souber a estatistica nao consegue interpretar o numero.
_STAT_BY_METRIC: dict[str, str] = dict(CLOUDWATCH_METRICS)


def _nearest_rank(sorted_values: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank` e `iceberg_metadata._nearest_rank`,
    reescrita aqui em vez de importada pela razao ja registrada por escrito em
    `iceberg_metadata.py:128`: os extratores sao modulos independentes por
    desenho. O que garante que as tres continuam iguais e teste, nao import.
    """
    n = len(sorted_values)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


def _provenance(path: str, label: str) -> dict[str, Any]:
    return {"extractor": EXTRACTOR_ID, "artifact": path, "metric": label}


def extract_cloudwatch(payload: dict[str, Any], path: str) -> list[Fact]:
    """Extrai Facts do conteudo ja carregado de um artefato CloudWatch."""
    job_name = payload.get("job_name") or ""
    job_run_id = payload.get("job_run_id") or ""
    period = payload.get("period_seconds")
    subject = {"job_name": job_name, "job_run_id": job_run_id}

    facts: list[Fact] = []
    with_data = 0
    empty = 0

    for result in payload.get("metric_data_results") or []:
        label = result.get("Label") or ""
        values = [float(v) for v in (result.get("Values") or [])]
        if not values:
            empty += 1
            facts.append(
                Fact(
                    kind="glue.metric.unresolved",
                    subject=dict(subject),
                    attrs={
                        "name": label,
                        "reason": "empty_series",
                        "detail": (
                            "CloudWatch devolveu a serie sem pontos. Duas causas possiveis e "
                            "distintas: observabilidade nao habilitada no job "
                            "(--enable-observability-metrics=true), ou a janela consultada nao "
                            "tem dado. Expiracao por retencao e recusada na coleta, nao aqui."
                        ),
                    },
                    provenance=_provenance(path, label),
                )
            )
            continue

        with_data += 1
        values.sort()
        facts.append(
            Fact(
                kind="glue.metric",
                subject=dict(subject),
                attrs={
                    "name": label,
                    "stat": _STAT_BY_METRIC.get(label, ""),
                    "period_s": period,
                },
                measures={
                    "min": values[0],
                    "p50": _nearest_rank(values, 50),
                    "p95": _nearest_rank(values, 95),
                    "max": values[-1],
                    "datapoints": len(values),
                },
                provenance=_provenance(path, label),
            )
        )

    facts.append(
        Fact(
            kind="glue.metric.analyzed",
            subject=dict(subject),
            measures={"metrics_with_data": with_data, "metrics_empty": empty},
            provenance={"extractor": EXTRACTOR_ID, "artifact": path},
        )
    )
    return sort_facts(facts)


def extract_cloudwatch_path(path: Path) -> list[Fact]:
    """Le o artefato do disco e delega para `extract_cloudwatch`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return extract_cloudwatch(payload, str(path))
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_cloudwatch.py -v
```

Esperado: PASS, 4 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/cloudwatch.py tests/test_facts_cloudwatch.py
rtk git commit -m "feat(facts): extrator do artefato CloudWatch que faltava"
```

---

## Task 7: Facts por run

**Files:**
- Create: `sparkforge/facts/glue_job_run.py`
- Test: `tests/test_facts_glue_job_run.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes do extrator de historico de runs Glue em Facts."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.facts.glue_job_run import extract_glue_job_runs_path


def _write_run(root: Path, run_id: str, **extra) -> Path:
    run = {
        "Id": run_id,
        "JobName": "my-job",
        "JobRunState": "SUCCEEDED",
        "StartedOn": "2026-08-01T10:00:00+00:00",
        "CompletedOn": "2026-08-01T10:20:00+00:00",
        "ExecutionTime": 1200,
        "GlueVersion": "5.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 10,
        "Timeout": 60,
    }
    run.update(extra)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"my-job_{run_id}.json"
    target.write_text(json.dumps(run), encoding="utf-8")
    return target


class TestRunFacts:
    def test_emits_one_fact_per_run(self, tmp_path):
        _write_run(tmp_path, "jr_1")
        _write_run(tmp_path, "jr_2")

        runs = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ]

        assert len(runs) == 2
        assert {f.subject["job_run_id"] for f in runs} == {"jr_1", "jr_2"}

    def test_static_capacity_derives_dpu_seconds(self, tmp_path):
        _write_run(tmp_path, "jr_1", WorkerType="G.2X", NumberOfWorkers=10, ExecutionTime=600)

        fact = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ][0]

        # 10 workers x 2 DPU x 600 s
        assert fact.measures["dpu_seconds"] == 12000
        assert fact.attrs["dpu_source"] == "derived"
        assert "formula" in fact.provenance

    def test_autoscaling_uses_the_observed_value(self, tmp_path):
        _write_run(
            tmp_path,
            "jr_1",
            DPUSeconds=4321.0,
            Arguments={"--enable-auto-scaling": "true"},
        )

        fact = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ][0]

        assert fact.measures["dpu_seconds"] == 4321.0
        assert fact.attrs["dpu_source"] == "observed"

    def test_autoscaling_without_dpu_seconds_refuses(self, tmp_path):
        _write_run(tmp_path, "jr_1", Arguments={"--enable-auto-scaling": "true"})

        facts = extract_glue_job_runs_path(tmp_path, "my-job")
        run = [f for f in facts if f.kind == "glue.job_run"][0]
        unresolved = [f for f in facts if f.kind == "glue.job_run.unresolved"]

        assert "dpu_seconds" not in run.measures
        assert any(f.attrs["reason"] == "dpu_unobservable_under_autoscaling" for f in unresolved)

    def test_error_message_never_enters_the_fact(self, tmp_path):
        _write_run(
            tmp_path,
            "jr_1",
            JobRunState="FAILED",
            ErrorMessage="s3://bucket-secreto/tabela/parte-0001 nao encontrado",
        )

        fact = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ][0]

        blob = json.dumps(fact.to_dict())
        assert "bucket-secreto" not in blob
        assert fact.attrs["state"] == "FAILED"

    def test_unknown_worker_type_refuses_to_derive(self, tmp_path):
        _write_run(tmp_path, "jr_1", WorkerType="Z.9X")

        facts = extract_glue_job_runs_path(tmp_path, "my-job")
        run = [f for f in facts if f.kind == "glue.job_run"][0]

        assert "dpu_seconds" not in run.measures
        assert any(
            f.attrs["reason"] == "unknown_worker_type"
            for f in facts
            if f.kind == "glue.job_run.unresolved"
        )


class TestPercentileParity:
    def test_matches_the_sibling_extractors(self):
        from sparkforge.facts.event_log import _nearest_rank as event_log_rank
        from sparkforge.facts.glue_job_run import _nearest_rank as run_rank
        from sparkforge.facts.iceberg_metadata import _nearest_rank as iceberg_rank

        values = [1, 2, 3, 10, 20, 1000]
        for pct in (50, 95, 99, 100):
            assert run_rank(values, pct) == event_log_rank(values, pct) == iceberg_rank(values, pct)
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_glue_job_run.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.glue_job_run'`.

- [ ] **Step 3: Implementar os facts por run**

```python
"""Extrator do historico de runs Glue em Facts.

Le o diretorio de artefatos `glue_job_run` -- um JSON por run terminal, escrito
por `sparkforge.collect.aws.collect_glue_job_runs` -- e emite tres camadas: o
fact por run, a distribuicao por grupo de capacidade e estado, e a contagem de
desfecho por grupo de capacidade.

O QUE ESTE MODULO RECUSA. Nao emite custo em dinheiro: `facts/pricing.py`
recusa deliberadamente combinar preco com regiao `UNQUALIFIED`, e furar essa
recusa aqui produziria um numero de custo que fonte nenhuma publica. Nao
classifica mensagem de erro por heuristica -- classificar e juizo, e fact nao
julga. E nao carrega a `ErrorMessage` para dentro do fact: ela pode trazer nome
de tabela, caminho de S3 ou trecho de dado.

Puro e deterministico: nunca aplica limiar, nunca toca a rede.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "glue_job_run@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "glue.job_run",
        "glue.job_run.distribution",
        "glue.job_run.outcome",
        "glue.job_run.unresolved",
        "glue.job_run.analyzed",
    }
)

# DPU por worker type, de `knowledge/glue/workers-and-capacity.md` linhas 10-13
# (fonte AWS, retrieved 2026-07-29). Worker fora desta tabela NAO recebe DPU
# derivado: inventar o fator produziria um numero com aparencia de medido.
DPU_BY_WORKER_TYPE: dict[str, int] = {
    "G.1X": 1,
    "G.2X": 2,
    "G.4X": 4,
    "G.8X": 8,
}

_DPU_FORMULA = "number_of_workers * DPU(worker_type) * execution_time_s"
_DPU_SOURCE_DOC = "knowledge/glue/workers-and-capacity.md:79"


def _nearest_rank(sorted_values: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank` e `iceberg_metadata._nearest_rank`,
    reescrita aqui em vez de importada pela razao ja registrada por escrito em
    `iceberg_metadata.py:128`: os extratores sao modulos independentes por
    desenho. O que garante que as tres continuam iguais e teste, nao import.
    """
    n = len(sorted_values)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


def _is_autoscaling(run: dict[str, Any]) -> bool:
    argumentos = run.get("Arguments") or {}
    return str(argumentos.get("--enable-auto-scaling", "")).lower() == "true"


def _capacity_subject(job_name: str, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_name": job_name,
        "glue_version": run.get("GlueVersion") or "",
        "worker_type": run.get("WorkerType") or "",
        "number_of_workers": run.get("NumberOfWorkers"),
        "autoscaling": _is_autoscaling(run),
    }


def _unresolved(
    job_name: str, run_id: str, reason: str, detail: str, collect_command: str = ""
) -> Fact:
    """Lacuna com nome, razao e -- quando existe -- o comando que a resolve.

    `Fact` e `@dataclass(frozen=True)`: os atributos entram na construcao, nunca
    por mutacao depois.
    """
    attrs: dict[str, Any] = {"reason": reason, "detail": detail}
    if collect_command:
        attrs["collect_command"] = collect_command
    return Fact(
        kind="glue.job_run.unresolved",
        subject={"job_name": job_name, "job_run_id": run_id},
        attrs=attrs,
        provenance={"extractor": EXTRACTOR_ID},
    )


def _dpu_seconds(
    job_name: str, run_id: str, run: dict[str, Any]
) -> tuple[float | None, str | None, dict[str, Any], Fact | None]:
    """Devolve (valor, dpu_source, provenance extra, fact de recusa)."""
    observed = run.get("DPUSeconds")
    if observed is not None:
        return float(observed), "observed", {"dpu_field": "DPUSeconds"}, None

    if _is_autoscaling(run):
        return (
            None,
            None,
            {},
            _unresolved(
                job_name,
                run_id,
                "dpu_unobservable_under_autoscaling",
                "Run com Auto Scaling e sem DPUSeconds na resposta da API. A capacidade "
                "alocada variou durante a execucao e number_of_workers e apenas o teto: "
                "multiplica-lo pela duracao produziria um numero superestimado com "
                "aparencia de medido.",
            ),
        )

    worker_type = run.get("WorkerType") or ""
    dpu = DPU_BY_WORKER_TYPE.get(worker_type)
    workers = run.get("NumberOfWorkers")
    duration = run.get("ExecutionTime")
    if dpu is None:
        return (
            None,
            None,
            {},
            _unresolved(
                job_name,
                run_id,
                "unknown_worker_type",
                f"WorkerType {worker_type!r} fora de {sorted(DPU_BY_WORKER_TYPE)}. O fator "
                f"DPU vem de {_DPU_SOURCE_DOC}; inventa-lo produziria numero com aparencia "
                f"de medido.",
            ),
        )
    if not isinstance(workers, int) or not isinstance(duration, (int, float)):
        return (
            None,
            None,
            {},
            _unresolved(
                job_name,
                run_id,
                "incomplete_capacity_fields",
                "NumberOfWorkers ou ExecutionTime ausentes na resposta da API; sem os dois "
                "a derivacao de DPU nao e possivel.",
            ),
        )
    return (
        float(workers * dpu * duration),
        "derived",
        {"formula": _DPU_FORMULA, "formula_source": _DPU_SOURCE_DOC, "dpu_per_worker": dpu},
        None,
    )


def _run_fact(job_name: str, run: dict[str, Any], path: str) -> tuple[Fact, list[Fact]]:
    run_id = run.get("Id") or ""
    extras: list[Fact] = []

    value, dpu_source, dpu_provenance, refusal = _dpu_seconds(job_name, run_id, run)
    if refusal is not None:
        extras.append(refusal)

    measures: dict[str, Any] = {}
    for chave, campo in (
        ("execution_time_s", "ExecutionTime"),
        ("number_of_workers", "NumberOfWorkers"),
        ("timeout_min", "Timeout"),
    ):
        if run.get(campo) is not None:
            measures[chave] = run[campo]
    if value is not None:
        measures["dpu_seconds"] = value

    attrs: dict[str, Any] = {
        "state": run.get("JobRunState") or "",
        "worker_type": run.get("WorkerType") or "",
        "glue_version": run.get("GlueVersion") or "",
        "execution_class": run.get("ExecutionClass") or "",
        "autoscaling": _is_autoscaling(run),
        "started_on": str(run.get("StartedOn") or ""),
        "completed_on": str(run.get("CompletedOn") or ""),
    }
    if dpu_source:
        attrs["dpu_source"] = dpu_source
    # `ErrorCategory` so entra se a resposta da API trouxer o campo. Nunca e
    # inferido do texto de `ErrorMessage`, e a mensagem em si nao entra no fact:
    # ela pode carregar nome de tabela, caminho de S3 ou trecho de dado.
    if run.get("ErrorCategory"):
        attrs["error_category"] = run["ErrorCategory"]

    provenance = {"extractor": EXTRACTOR_ID, "artifact": path}
    provenance.update(dpu_provenance)

    fact = Fact(
        kind="glue.job_run",
        subject={"job_name": job_name, "job_run_id": run_id},
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )
    return fact, extras


def _load_runs(directory: Path, job_name: str) -> list[tuple[dict[str, Any], str]]:
    """Carrega os artefatos de run do diretorio, filtrados pelo job."""
    loaded: list[tuple[dict[str, Any], str]] = []
    for target in sorted(Path(directory).glob("*.json")):
        run = json.loads(target.read_text(encoding="utf-8"))
        if (run.get("JobName") or "") != job_name:
            continue
        loaded.append((run, str(target)))
    return loaded


def extract_glue_job_runs_path(directory: Path, job_name: str) -> list[Fact]:
    """Extrai Facts do diretorio de artefatos de run de um job."""
    facts: list[Fact] = []
    runs = _load_runs(directory, job_name)

    for run, path in runs:
        fact, extras = _run_fact(job_name, run, path)
        facts.append(fact)
        facts.extend(extras)

    facts.append(
        Fact(
            kind="glue.job_run.analyzed",
            subject={"job_name": job_name},
            measures={"runs_analyzed": len(runs)},
            provenance={"extractor": EXTRACTOR_ID, "artifact": str(directory)},
        )
    )
    return sort_facts(facts)
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_glue_job_run.py -v
```

Esperado: PASS, 7 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/glue_job_run.py tests/test_facts_glue_job_run.py
rtk git commit -m "feat(facts): fact por run Glue, com DPU observado ou derivado"
```

---

## Task 8: Distribuição e desfecho por capacidade

**Files:**
- Modify: `sparkforge/facts/glue_job_run.py`
- Test: `tests/test_facts_glue_job_run.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_glue_job_run.py`:

```python
class TestDistribution:
    def test_groups_by_capacity_and_terminal_state(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)
        _write_run(tmp_path, "jr_2", ExecutionTime=300)
        _write_run(tmp_path, "jr_3", ExecutionTime=999, JobRunState="FAILED")
        _write_run(tmp_path, "jr_4", ExecutionTime=200, NumberOfWorkers=20)

        dists = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ]

        keys = {(f.subject["number_of_workers"], f.subject["state"]) for f in dists}
        assert keys == {(10, "SUCCEEDED"), (10, "FAILED"), (20, "SUCCEEDED")}

        ten_ok = [
            f
            for f in dists
            if f.subject["number_of_workers"] == 10 and f.subject["state"] == "SUCCEEDED"
        ][0]
        assert ten_ok.measures["n"] == 2
        assert ten_ok.measures["runtime_min_s"] == 100
        assert ten_ok.measures["runtime_max_s"] == 300
        assert ten_ok.measures["runtime_p50_s"] == 100

    def test_single_run_group_declares_n_of_one(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)

        dist = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ][0]

        assert dist.measures["n"] == 1
        assert dist.measures["runtime_p95_s"] == 100

    def test_mixed_dpu_source_is_marked_not_merged(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)
        _write_run(tmp_path, "jr_2", ExecutionTime=200, DPUSeconds=50.0)

        dist = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ][0]

        assert dist.attrs["dpu_source"] == "mixed"

    def test_window_bounds_come_from_the_runs(self, tmp_path):
        _write_run(tmp_path, "jr_1", StartedOn="2026-08-01T10:00:00+00:00")
        _write_run(tmp_path, "jr_2", StartedOn="2026-08-09T10:00:00+00:00")

        dist = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ][0]

        assert dist.attrs["window_first"] == "2026-08-01T10:00:00+00:00"
        assert dist.attrs["window_last"] == "2026-08-09T10:00:00+00:00"


class TestOutcome:
    def test_counts_states_within_one_capacity(self, tmp_path):
        _write_run(tmp_path, "jr_1")
        _write_run(tmp_path, "jr_2")
        _write_run(tmp_path, "jr_3", JobRunState="FAILED")
        _write_run(tmp_path, "jr_4", JobRunState="TIMEOUT")

        outcomes = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.outcome"
        ]

        assert len(outcomes) == 1
        assert outcomes[0].measures == {
            "n_total": 4,
            "n_succeeded": 2,
            "n_failed": 1,
            "n_timeout": 1,
            "n_stopped": 0,
        }

    def test_outcome_carries_counts_not_a_rate(self, tmp_path):
        _write_run(tmp_path, "jr_1")
        _write_run(tmp_path, "jr_2", JobRunState="FAILED")

        outcome = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.outcome"
        ][0]

        assert not any("rate" in k or "ratio" in k for k in outcome.measures)
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_glue_job_run.py::TestDistribution -v
```

Esperado: FAIL — `IndexError` ou lista vazia, porque nenhum fact `glue.job_run.distribution` é emitido.

- [ ] **Step 3: Implementar**

Acrescente o import que o agrupamento precisa, junto dos outros no topo de
`sparkforge/facts/glue_job_run.py` (ele não existia até aqui de propósito — import sem uso
reprova no lint):

```python
from collections import defaultdict
```

E acrescente, antes de `extract_glue_job_runs_path`:

```python
def _group_key(job_name: str, run: dict[str, Any]) -> tuple[Any, ...]:
    subject = _capacity_subject(job_name, run)
    return (
        subject["glue_version"],
        subject["worker_type"],
        subject["number_of_workers"],
        subject["autoscaling"],
    )


def _dpu_source_of_group(sources: set[str]) -> str:
    """`mixed` quando o grupo agrega observado e derivado.

    Fundir os dois em silencio produziria um p95 de DPU cuja metade foi medida
    e metade calculada, sem o leitor saber qual. `mixed` e o aviso.
    """
    if len(sources) == 1:
        return next(iter(sources))
    if not sources:
        return "none"
    return "mixed"


_STATE_TO_COUNTER = {
    "SUCCEEDED": "n_succeeded",
    "FAILED": "n_failed",
    "TIMEOUT": "n_timeout",
    "STOPPED": "n_stopped",
}


def _distribution_facts(job_name: str, rows: list[dict[str, Any]], path: str) -> list[Fact]:
    """Uma distribuicao por (capacidade, estado terminal)."""
    grupos: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grupos[_group_key(job_name, row["run"]) + (row["state"],)].append(row)

    facts: list[Fact] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling, state = chave
        runtimes = sorted(
            float(m["execution_time_s"]) for m in membros if m["execution_time_s"] is not None
        )
        dpus = sorted(float(m["dpu_seconds"]) for m in membros if m["dpu_seconds"] is not None)
        starts = sorted(m["started_on"] for m in membros if m["started_on"])

        measures: dict[str, Any] = {"n": len(membros)}
        if runtimes:
            measures.update(
                {
                    "runtime_min_s": runtimes[0],
                    "runtime_p50_s": _nearest_rank(runtimes, 50),
                    "runtime_p95_s": _nearest_rank(runtimes, 95),
                    "runtime_p99_s": _nearest_rank(runtimes, 99),
                    "runtime_max_s": runtimes[-1],
                }
            )
        if dpus:
            measures.update(
                {
                    "dpu_seconds_p50": _nearest_rank(dpus, 50),
                    "dpu_seconds_p95": _nearest_rank(dpus, 95),
                }
            )

        facts.append(
            Fact(
                kind="glue.job_run.distribution",
                subject={
                    "job_name": job_name,
                    "glue_version": glue_version,
                    "worker_type": worker_type,
                    "number_of_workers": workers,
                    "autoscaling": autoscaling,
                    "state": state,
                },
                measures=measures,
                attrs={
                    "window_first": starts[0] if starts else "",
                    "window_last": starts[-1] if starts else "",
                    "dpu_source": _dpu_source_of_group(
                        {m["dpu_source"] for m in membros if m["dpu_source"]}
                    ),
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )
    return facts


def _outcome_facts(job_name: str, rows: list[dict[str, Any]], path: str) -> list[Fact]:
    """Uma contagem de desfecho por capacidade, atravessando os estados.

    Contagens, nao taxa: a divisao e juizo e pertence a fase seguinte. O fact
    carrega numerador e denominador.
    """
    grupos: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grupos[_group_key(job_name, row["run"])].append(row)

    facts: list[Fact] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        measures = {
            "n_total": len(membros),
            "n_succeeded": 0,
            "n_failed": 0,
            "n_timeout": 0,
            "n_stopped": 0,
        }
        for membro in membros:
            counter = _STATE_TO_COUNTER.get(membro["state"])
            if counter:
                measures[counter] += 1
        starts = sorted(m["started_on"] for m in membros if m["started_on"])

        facts.append(
            Fact(
                kind="glue.job_run.outcome",
                subject={
                    "job_name": job_name,
                    "glue_version": glue_version,
                    "worker_type": worker_type,
                    "number_of_workers": workers,
                    "autoscaling": autoscaling,
                },
                measures=measures,
                attrs={
                    "window_first": starts[0] if starts else "",
                    "window_last": starts[-1] if starts else "",
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )
    return facts
```

Substitua o corpo de `extract_glue_job_runs_path` por:

```python
def extract_glue_job_runs_path(directory: Path, job_name: str) -> list[Fact]:
    """Extrai Facts do diretorio de artefatos de run de um job."""
    facts: list[Fact] = []
    rows: list[dict[str, Any]] = []
    runs = _load_runs(directory, job_name)

    for run, path in runs:
        fact, extras = _run_fact(job_name, run, path)
        facts.append(fact)
        facts.extend(extras)
        rows.append(
            {
                "run": run,
                "state": fact.attrs["state"],
                "started_on": fact.attrs["started_on"],
                "execution_time_s": fact.measures.get("execution_time_s"),
                "dpu_seconds": fact.measures.get("dpu_seconds"),
                "dpu_source": fact.attrs.get("dpu_source", ""),
            }
        )

    facts.extend(_distribution_facts(job_name, rows, str(directory)))
    facts.extend(_outcome_facts(job_name, rows, str(directory)))
    facts.append(
        Fact(
            kind="glue.job_run.analyzed",
            subject={"job_name": job_name},
            measures={"runs_analyzed": len(runs)},
            provenance={"extractor": EXTRACTOR_ID, "artifact": str(directory)},
        )
    )
    return sort_facts(facts)
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_glue_job_run.py -v
```

Esperado: PASS, 13 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/glue_job_run.py tests/test_facts_glue_job_run.py
rtk git commit -m "feat(facts): distribuicao por capacidade e estado, e a contagem de desfecho"
```

---

## Task 9: Correlação com os facts de CloudWatch

**Files:**
- Modify: `sparkforge/facts/glue_job_run.py`
- Test: `tests/test_facts_glue_job_run.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_glue_job_run.py`:

```python
def _write_cloudwatch(root: Path, run_id: str, value: float) -> Path:
    payload = {
        "job_name": "my-job",
        "job_run_id": run_id,
        "start": "2026-08-01T10:00:00Z",
        "end": "2026-08-01T10:20:00Z",
        "period_seconds": 60,
        "metric_data_results": [
            {
                "Id": "m0",
                "Label": "glue.driver.workerUtilization",
                "Timestamps": ["t1"],
                "Values": [value],
            }
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"my-job_{run_id}.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestCorrelation:
    def test_metric_facts_are_emitted_for_runs_with_artifacts(self, tmp_path):
        runs_dir = tmp_path / "runs"
        cw_dir = tmp_path / "cw"
        _write_run(runs_dir, "jr_1")
        _write_cloudwatch(cw_dir, "jr_1", 0.42)

        facts = extract_glue_job_runs_path(runs_dir, "my-job", cloudwatch_dir=cw_dir)
        metrics = [f for f in facts if f.kind == "glue.metric"]

        assert len(metrics) == 1
        assert metrics[0].subject["job_run_id"] == "jr_1"
        assert metrics[0].measures["p50"] == 0.42

    def test_run_without_metrics_names_the_command_that_fixes_it(self, tmp_path):
        runs_dir = tmp_path / "runs"
        cw_dir = tmp_path / "cw"
        cw_dir.mkdir(parents=True)
        _write_run(runs_dir, "jr_1")

        facts = extract_glue_job_runs_path(runs_dir, "my-job", cloudwatch_dir=cw_dir)
        missing = [
            f
            for f in facts
            if f.kind == "glue.job_run.unresolved"
            and f.attrs["reason"] == "cloudwatch_artifact_missing"
        ]

        assert len(missing) == 1
        assert "sparkforge collect cloudwatch" in missing[0].attrs["collect_command"]
        assert "--job-run jr_1" in missing[0].attrs["collect_command"]

    def test_without_the_directory_correlation_is_declared_not_silent(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "jr_1")

        facts = extract_glue_job_runs_path(runs_dir, "my-job")
        assert not [f for f in facts if f.kind == "glue.metric"]
        assert any(
            f.attrs["reason"] == "cloudwatch_not_requested"
            for f in facts
            if f.kind == "glue.job_run.unresolved"
        )
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_glue_job_run.py::TestCorrelation -v
```

Esperado: FAIL com `TypeError: extract_glue_job_runs_path() got an unexpected keyword argument 'cloudwatch_dir'`.

- [ ] **Step 3: Implementar**

Acrescente o import no topo de `sparkforge/facts/glue_job_run.py`:

```python
from sparkforge.facts.cloudwatch import extract_cloudwatch_path
```

E troque a assinatura e o corpo de `extract_glue_job_runs_path`:

```python
def extract_glue_job_runs_path(
    directory: Path, job_name: str, cloudwatch_dir: Path | None = None
) -> list[Fact]:
    """Extrai Facts do diretorio de artefatos de run de um job.

    `cloudwatch_dir` e opcional. Ausente, os facts de distribuicao saem
    completos e a correlacao inteira vai para `unresolved` -- correlacao que
    nao aconteceu e dita, nunca omitida.
    """
    facts: list[Fact] = []
    rows: list[dict[str, Any]] = []
    runs = _load_runs(directory, job_name)

    for run, path in runs:
        fact, extras = _run_fact(job_name, run, path)
        facts.append(fact)
        facts.extend(extras)
        rows.append(
            {
                "run": run,
                "state": fact.attrs["state"],
                "started_on": fact.attrs["started_on"],
                "execution_time_s": fact.measures.get("execution_time_s"),
                "dpu_seconds": fact.measures.get("dpu_seconds"),
                "dpu_source": fact.attrs.get("dpu_source", ""),
            }
        )
        facts.extend(_correlate(job_name, run.get("Id") or "", cloudwatch_dir))

    facts.extend(_distribution_facts(job_name, rows, str(directory)))
    facts.extend(_outcome_facts(job_name, rows, str(directory)))
    facts.append(
        Fact(
            kind="glue.job_run.analyzed",
            subject={"job_name": job_name},
            measures={
                "runs_analyzed": len(runs),
                "runs_with_metrics": sum(
                    1
                    for run, _ in runs
                    if _cloudwatch_artifact(job_name, run.get("Id") or "", cloudwatch_dir)
                ),
            },
            provenance={"extractor": EXTRACTOR_ID, "artifact": str(directory)},
        )
    )
    return sort_facts(facts)
```

E acrescente as duas funções auxiliares antes dela:

```python
def _cloudwatch_artifact(job_name: str, run_id: str, cloudwatch_dir: Path | None) -> Path | None:
    if cloudwatch_dir is None:
        return None
    candidate = Path(cloudwatch_dir) / f"{job_name}_{run_id}.json"
    return candidate if candidate.is_file() else None


def _correlate(job_name: str, run_id: str, cloudwatch_dir: Path | None) -> list[Fact]:
    """Junta por `job_run_id` os facts de metrica ja coletados.

    Run sem metrica nao e erro: e lacuna com nome, razao e o comando exato que a
    resolve -- a mesma convencao que o manifesto usa para nao deixar `resume()`
    cego.
    """
    if cloudwatch_dir is None:
        return [
            _unresolved(
                job_name,
                run_id,
                "cloudwatch_not_requested",
                "Correlacao com CloudWatch nao pedida nesta analise. Para incluir, passe "
                "--cloudwatch <diretorio de artefatos cloudwatch>.",
            )
        ]

    artifact = _cloudwatch_artifact(job_name, run_id, cloudwatch_dir)
    if artifact is None:
        return [
            _unresolved(
                job_name,
                run_id,
                "cloudwatch_artifact_missing",
                "Nenhum artefato de metrica para este run no diretorio informado.",
                collect_command=(
                    f"sparkforge collect cloudwatch --repo . --job-name {job_name} "
                    f"--job-run {run_id} --start <ISO8601> --end <ISO8601> --now <ISO8601>"
                ),
            )
        ]

    return list(extract_cloudwatch_path(artifact))
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_glue_job_run.py tests/test_facts_cloudwatch.py -v
```

Esperado: PASS, 16 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/glue_job_run.py tests/test_facts_glue_job_run.py
rtk git commit -m "feat(facts): correlacao run-metrica, com a lacuna nomeando o comando"
```

---

## Task 10: Camada `_core` e CLI

**Files:**
- Modify: `sparkforge/adapters/_core.py`
- Modify: `sparkforge/adapters/cli.py`
- Test: `tests/test_adapters_cli.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_adapters_cli.py`:

```python
class TestGlueJobRunsCommands:
    def test_analyze_cloudwatch_prints_metric_facts(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        artifact = tmp_path / "cw.json"
        artifact.write_text(
            json.dumps(
                {
                    "job_name": "my-job",
                    "job_run_id": "jr_1",
                    "start": "2026-08-01T10:00:00Z",
                    "end": "2026-08-01T10:20:00Z",
                    "period_seconds": 60,
                    "metric_data_results": [
                        {
                            "Id": "m0",
                            "Label": "glue.driver.workerUtilization",
                            "Timestamps": ["t"],
                            "Values": [0.5],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        assert main(["analyze", "cloudwatch", "--path", str(artifact)]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["by_kind"]["glue.metric"] == 1

    def test_analyze_glue_job_runs_writes_out_file(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        (runs_dir / "my-job_jr_1.json").write_text(
            json.dumps(
                {
                    "Id": "jr_1",
                    "JobName": "my-job",
                    "JobRunState": "SUCCEEDED",
                    "StartedOn": "2026-08-01T10:00:00+00:00",
                    "CompletedOn": "2026-08-01T10:20:00+00:00",
                    "ExecutionTime": 1200,
                    "GlueVersion": "5.0",
                    "WorkerType": "G.1X",
                    "NumberOfWorkers": 10,
                }
            ),
            encoding="utf-8",
        )
        out = tmp_path / "facts.json"

        code = main(
            [
                "analyze",
                "glue-job-runs",
                "--path",
                str(runs_dir),
                "--job-name",
                "my-job",
                "--out",
                str(out),
            ]
        )

        assert code == 0
        kinds = {f["kind"] for f in json.loads(out.read_text(encoding="utf-8"))}
        assert "glue.job_run" in kinds
        assert "glue.job_run.distribution" in kinds
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_cli.py::TestGlueJobRunsCommands -v
```

Esperado: FAIL — `SystemExit: 2`, argparse não conhece `cloudwatch` como subcomando de `analyze`.

- [ ] **Step 3: Implementar em `_core.py`**

Acrescente junto dos outros `analyze_*`:

```python
def _extract_cloudwatch_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um artefato gravado por `sparkforge collect cloudwatch`:\n"
            f"    sparkforge analyze cloudwatch "
            f"--path .sparkforge/artifacts/cloudwatch/<job>_<run>.json",
            exit_code=2,
        )
    return extract_cloudwatch_path(target)


def analyze_cloudwatch(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_cloudwatch_facts(path)
    return _facts_page(facts, "glue.metric.unresolved", kind, limit, cursor, detail_level)


def analyze_glue_job_runs(
    path: str,
    job_name: str,
    cloudwatch: str | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_dir():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o DIRETORIO de artefatos de run, nao para um arquivo:\n"
            f"    sparkforge analyze glue-job-runs "
            f"--path .sparkforge/artifacts/glue_job_run/ --job-name <job>",
            exit_code=2,
        )
    cw_dir = Path(cloudwatch) if cloudwatch else None
    if cw_dir is not None and not cw_dir.is_dir():
        raise AdapterError(
            f"--cloudwatch aponta para {cloudwatch}, que nao e um diretorio existente.",
            exit_code=2,
        )
    facts = extract_glue_job_runs_path(target, job_name, cloudwatch_dir=cw_dir)
    return _facts_page(facts, "glue.job_run.unresolved", kind, limit, cursor, detail_level)


def collect_glue_job_runs(
    repo: str, *, job_name: str, max_runs: int, now: str
) -> dict[str, Any]:
    try:
        return collect_aws.collect_glue_job_runs(
            job_name, Path(repo), max_runs=max_runs, now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(
            exc, repo, collect_aws.glue_job_run_path(job_name, "<run-id>")
        ) from exc
```

Acrescente os imports correspondentes no topo do arquivo, junto dos outros extratores:

```python
from sparkforge.facts.cloudwatch import extract_cloudwatch_path
from sparkforge.facts.glue_job_run import extract_glue_job_runs_path
```

- [ ] **Step 4: Implementar em `cli.py`**

Junto dos outros parsers de `analyze` (após o bloco de `event-log`, linha 183):

```python
    cw_analyze_p = analyze_sub.add_parser(
        "cloudwatch",
        help="Extrai facts de um artefato de metricas do CloudWatch ja coletado.",
    )
    cw_analyze_p.add_argument("--path", required=True, help="Artefato JSON do CloudWatch.")
    cw_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    cw_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    cw_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    cw_analyze_p.add_argument("--cursor")
    _add_detail_level(cw_analyze_p)

    runs_analyze_p = analyze_sub.add_parser(
        "glue-job-runs",
        help="Extrai facts de historico do diretorio de artefatos de run Glue.",
    )
    runs_analyze_p.add_argument(
        "--path", required=True, help="DIRETORIO de artefatos glue_job_run."
    )
    runs_analyze_p.add_argument("--job-name", required=True)
    runs_analyze_p.add_argument(
        "--cloudwatch",
        help="Diretorio de artefatos cloudwatch, para correlacionar por job_run_id.",
    )
    runs_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    runs_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    runs_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    runs_analyze_p.add_argument("--cursor")
    _add_detail_level(runs_analyze_p)
```

Junto dos parsers de `collect` (após o bloco de `cloudwatch`, linha 1031):

```python
    job_runs_p = collect_sub.add_parser(
        "glue-job-runs",
        help="Baixa o historico de execucoes de um job, um artefato por run terminal.",
    )
    job_runs_p.add_argument("--repo", required=True)
    job_runs_p.add_argument("--job-name", required=True)
    job_runs_p.add_argument(
        "--max-runs",
        type=int,
        default=30,
        help="Teto de paginacao. A API devolve do mais recente para tras.",
    )
    job_runs_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")
```

Os três handlers, junto dos vizinhos:

```python
def _cmd_analyze_cloudwatch(args: argparse.Namespace) -> int:
    full = _core.analyze_cloudwatch(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_glue_job_runs(args: argparse.Namespace) -> int:
    full = _core.analyze_glue_job_runs(
        args.path,
        job_name=args.job_name,
        cloudwatch=args.cloudwatch,
        kind=args.kind,
        limit=None,
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_collect_glue_job_runs(args: argparse.Namespace) -> int:
    payload = _core.collect_glue_job_runs(
        args.repo, job_name=args.job_name, max_runs=args.max_runs, now=args.now
    )
    _print(payload)
    return 0
```

E as três entradas no dicionário de despacho, junto das vizinhas:

```python
    ("analyze", "cloudwatch"): _cmd_analyze_cloudwatch,
    ("analyze", "glue-job-runs"): _cmd_analyze_glue_job_runs,
    ("collect", "glue-job-runs"): _cmd_collect_glue_job_runs,
```

`analyze_glue_job_runs` é chamada com `job_name=` nomeado; confira que a assinatura em `_core.py` aceita — se o segundo parâmetro for posicional obrigatório, chamar por nome funciona igual.

- [ ] **Step 5: Rodar e ver passar**

```bash
rtk pytest tests/test_adapters_cli.py -v
```

Esperado: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/adapters/_core.py sparkforge/adapters/cli.py tests/test_adapters_cli.py
rtk git commit -m "feat(cli): collect glue-job-runs e os dois analyze novos"
```

---

## Task 11: Tools MCP, manifesto e paridade

**Files:**
- Modify: `sparkforge/adapters/tools.py`
- Modify: `manifest.json:80`
- Modify: `parity.yaml:438`
- Test: `tests/test_adapters_tools.py`, `tests/test_adapters_mcp.py`, `tests/test_capability_parity.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_adapters_tools.py`:

```python
class TestGlueJobRunTools:
    def test_the_three_new_tools_are_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        novas = {
            "sparkforge_collect_glue_job_runs",
            "sparkforge_analyze_cloudwatch",
            "sparkforge_analyze_glue_job_runs",
        }
        assert novas <= set(tools.TOOLS)
        assert novas <= set(tools.HANDLERS)

    def test_the_three_new_tools_are_listed_in_the_manifest(self):
        import json
        from pathlib import Path

        manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
        listadas = set(manifest["tools"])
        assert {
            "sparkforge_collect_glue_job_runs",
            "sparkforge_analyze_cloudwatch",
            "sparkforge_analyze_glue_job_runs",
        } <= listadas
```

Se os nomes dos dicionários em `tools.py` não forem `TOOLS` e `HANDLERS`, abra o arquivo e use os nomes reais — a asserção é sobre o conteúdo, não sobre o nome.

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_tools.py::TestGlueJobRunTools -v
```

Esperado: FAIL com `AssertionError` — os três nomes não estão declarados.

- [ ] **Step 3: Declarar as tools**

Em `sparkforge/adapters/tools.py`, junto de `sparkforge_collect_cloudwatch` (linha 3405):

```python
    "sparkforge_collect_glue_job_runs": {
        "description": (
            "Baixa o historico de execucoes de um job via `glue.get_job_runs` e grava UM "
            "artefato por run em estado terminal. Run ainda em execucao nao vira artefato: "
            "seu conteudo mudaria depois e o sha256 do manifesto divergiria. Coleta "
            "incremental de graca -- run ja em disco com hash integro e no-op. `max_runs` e "
            "teto de paginacao, nao filtro de data: a API devolve do mais recente para tras."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "job_name", "now"],
            "properties": {
                "repo": {"type": "string"},
                "job_name": {"type": "string"},
                "max_runs": {"type": "integer", "minimum": 1, "default": 30},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "artifacts": {"type": "array", "items": _COLLECT_ARTIFACT_SCHEMA},
                    "skipped": {"type": "array", "items": {"type": "object"}},
                    "runs_listed": {"type": "integer"},
                },
            },
            "Artefatos coletados e runs pulados, ou erro de fronteira.",
        ),
        "annotations": _WRITE_LOCAL_OPEN_WORLD,
    },
```

E, junto das tools de `analyze`, as duas de análise. Copie a forma de `sparkforge_analyze_event_log` (mesmo `outputSchema` de página de facts e mesmas `annotations`), trocando descrição e `inputSchema`:

```python
    "sparkforge_analyze_cloudwatch": {
        "description": (
            "Extrai facts `glue.metric` de um artefato de metricas do CloudWatch ja "
            "coletado. Serie sem pontos vira `glue.metric.unresolved` com a razao, nunca "
            "um zero: vazio por observabilidade desligada no job e vazio por janela sem "
            "dado sao causas diferentes."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "detail_level": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(_FACTS_PAGE_SCHEMA, "Pagina de facts, ou erro de fronteira."),
        "annotations": _READ_ONLY_LOCAL,
    },
    "sparkforge_analyze_glue_job_runs": {
        "description": (
            "Extrai facts de historico do DIRETORIO de artefatos de run Glue: um "
            "`glue.job_run` por run, `glue.job_run.distribution` por capacidade e estado "
            "terminal, e `glue.job_run.outcome` por capacidade. DPU e observado quando a "
            "API o traz, derivado quando a capacidade e estatica, e recusado sob Auto "
            "Scaling sem DPUSeconds. Com `cloudwatch`, correlaciona por job_run_id; sem "
            "ele, a correlacao vai para unresolved com o comando que a resolve."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path", "job_name"],
            "properties": {
                "path": {"type": "string"},
                "job_name": {"type": "string"},
                "cloudwatch": {"type": "string"},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "detail_level": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(_FACTS_PAGE_SCHEMA, "Pagina de facts, ou erro de fronteira."),
        "annotations": _READ_ONLY_LOCAL,
    },
```

Se `_FACTS_PAGE_SCHEMA` e `_READ_ONLY_LOCAL` tiverem outros nomes no arquivo, use os que `sparkforge_analyze_event_log` já usa.

Os três handlers, junto dos vizinhos:

```python
def _h_collect_glue_job_runs(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_glue_job_runs(
        args["repo"],
        job_name=args["job_name"],
        max_runs=args.get("max_runs", 30),
        now=args["now"],
    )


def _h_analyze_cloudwatch(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_cloudwatch(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit"),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )


def _h_analyze_glue_job_runs(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_glue_job_runs(
        args["path"],
        job_name=args["job_name"],
        cloudwatch=args.get("cloudwatch"),
        kind=args.get("kind"),
        limit=args.get("limit"),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )
```

E as três entradas no dicionário de despacho de handlers.

- [ ] **Step 4: Atualizar manifesto e paridade**

Em `manifest.json`, na lista `tools`, acrescente em ordem alfabética:

```json
"sparkforge_analyze_cloudwatch",
"sparkforge_analyze_glue_job_runs",
"sparkforge_collect_glue_job_runs",
```

Em `parity.yaml`, na capability *collect real AWS artifacts and verify the manifest* (linha 438), acrescente `- sparkforge_collect_glue_job_runs` à lista `tools` e `- collect glue-job-runs` à lista `cli`. Acrescente também `knowledge/glue/observability.yaml` à lista `knowledge` dessa capability.

Localize a capability de análise (a que já lista `analyze event-log`) e acrescente lá `sparkforge_analyze_cloudwatch`, `sparkforge_analyze_glue_job_runs`, `analyze cloudwatch` e `analyze glue-job-runs`.

- [ ] **Step 5: Sincronizar os espelhos**

```bash
rtk python scripts/sync_skills.py
rtk pytest tests/test_arvore_versionada.py -v
```

Esperado: PASS. Se `sync_skills.py` não cobrir os espelhos de tools, o teste dirá qual arquivo está atrasado e o que copiar.

- [ ] **Step 6: Rodar os gates de superfície**

```bash
rtk pytest tests/test_adapters_tools.py tests/test_adapters_mcp.py tests/test_capability_parity.py tests/test_canonical_registry.py -v
```

Esperado: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add sparkforge/adapters/tools.py manifest.json parity.yaml tests/test_adapters_tools.py .claude .agents
rtk git commit -m "feat(mcp): tres tools de historico, com manifesto e paridade fechados"
```

---

## Task 12: Fixtures golden

**Files:**
- Create: `fixtures/glue_job_run/` (cenários sintéticos)
- Test: `tests/test_facts_glue_job_run.py`

Nenhum nome, número, dimensão ou particularidade de ambiente real. O documento de origem pede isso, e o teste 13 abaixo é o que o próprio documento chama de mais importante.

- [ ] **Step 1: Criar os cenários**

Crie um diretório por cenário, cada um com `runs/` e, quando fizer sentido, `cloudwatch/`:

```
fixtures/glue_job_run/
├── capacity_changed_midway/     runs em G.1X/10 e depois G.2X/20
├── mixed_dpu_source/            um run com autoscaling e DPUSeconds, outro estatico
├── autoscaling_without_dpu/     autoscaling sem DPUSeconds
├── all_failed/                  todos os runs em FAILED
├── single_run/                  n=1
└── correlated/                  runs com artefato CloudWatch pareado
```

Cada arquivo de run tem a forma da resposta de `GetJobRuns`, um run por arquivo, nome `<job>_<run_id>.json`. Use `synthetic-job` como nome de job e `jr_0001`, `jr_0002`… como ids.

- [ ] **Step 2: Escrever o teste sobre as fixtures**

Acrescente a `tests/test_facts_glue_job_run.py`:

```python
FIXTURES = Path("fixtures/glue_job_run")


class TestGoldenScenarios:
    def test_capacity_change_never_merges_groups(self):
        facts = extract_glue_job_runs_path(
            FIXTURES / "capacity_changed_midway" / "runs", "synthetic-job"
        )
        dists = [f for f in facts if f.kind == "glue.job_run.distribution"]

        capacidades = {
            (f.subject["worker_type"], f.subject["number_of_workers"]) for f in dists
        }
        assert len(capacidades) > 1
        for fact in dists:
            assert fact.measures["n"] >= 1

    def test_mixed_group_is_marked(self):
        facts = extract_glue_job_runs_path(
            FIXTURES / "mixed_dpu_source" / "runs", "synthetic-job"
        )
        dists = [f for f in facts if f.kind == "glue.job_run.distribution"]
        assert any(f.attrs["dpu_source"] == "mixed" for f in dists)

    def test_all_failed_produces_no_succeeded_distribution(self):
        facts = extract_glue_job_runs_path(FIXTURES / "all_failed" / "runs", "synthetic-job")
        dists = [f for f in facts if f.kind == "glue.job_run.distribution"]

        assert dists
        assert all(f.subject["state"] == "FAILED" for f in dists)
        outcome = [f for f in facts if f.kind == "glue.job_run.outcome"][0]
        assert outcome.measures["n_succeeded"] == 0

    def test_small_primary_input_never_implies_small_workload(self):
        """O teste que o documento de origem chama de mais importante.

        Um batch de entrada pequeno nao autoriza concluir que o job e pequeno.
        Este extrator nao ve entrada nenhuma -- ve duracao, capacidade e
        desfecho -- e o teste trava isso: nenhum fact emitido aqui carrega
        classificacao de tamanho, porque classificar workload e a fase seguinte.
        """
        facts = extract_glue_job_runs_path(FIXTURES / "single_run" / "runs", "synthetic-job")
        blob = json.dumps([f.to_dict() for f in facts])
        for palavra in ("micro", "small", "medium", "large", "workload_class"):
            assert palavra not in blob
```

- [ ] **Step 3: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_glue_job_run.py::TestGoldenScenarios -v
```

Esperado: PASS. Se um cenário não produzir o que a asserção espera, o defeito está na fixture: ajuste os JSONs até que o cenário represente de fato o que o nome diz.

- [ ] **Step 4: Commit**

```bash
rtk git add fixtures/glue_job_run tests/test_facts_glue_job_run.py
rtk git commit -m "test(fixtures): seis cenarios sinteticos de historico de runs"
```

---

## Task 13: Documentação e suíte completa

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/STATUS.md`

- [ ] **Step 1: Rodar a suíte inteira**

```bash
rtk pytest -q
```

Esperado: PASS. Qualquer falha aqui é regressão introduzida por esta entrega — corrija antes de documentar.

- [ ] **Step 2: Documentar os três comandos no README**

Na seção do README que lista os comandos de `collect` e `analyze`, acrescente as três linhas no formato das vizinhas:

```markdown
| `sparkforge collect glue-job-runs` | Histórico de execuções de um job, um artefato por run terminal |
| `sparkforge analyze cloudwatch` | Facts `glue.metric` de um artefato de métricas já coletado |
| `sparkforge analyze glue-job-runs` | Facts de histórico: run, distribuição por capacidade e desfecho |
```

Confira o formato real da tabela antes de colar — se a seção usar lista em vez de tabela, siga a lista.

- [ ] **Step 3: Registrar a fase no STATUS**

Acrescente a `docs/superpowers/STATUS.md`, no formato das fases existentes, uma entrada que declare: os três comandos, os cinco `kind` de fact novos, o número de testes que a entrega acrescentou (conte com `rtk pytest tests/test_facts_glue_job_run.py tests/test_facts_cloudwatch.py tests/test_cloudwatch_retention.py -q`), e a referência à spec.

Registre também, explicitamente, o que ficou fora e por quê: nenhuma regra nova (julgar histórico é a fase seguinte), nenhum custo em dinheiro (`facts/pricing.py` recusa combinar preço com região não qualificada), e `SF-GLUE-001` continua errado à espera do subprojeto A.

- [ ] **Step 4: Rodar o gate de números**

```bash
rtk python scripts/check_vnext_claims.py
```

Esperado: PASS. Se um número novo do STATUS não estiver em `docs/claims.lock.json`, o script diz qual — acrescente com o valor medido, nunca estimado.

- [ ] **Step 5: Commit**

```bash
rtk git add README.md docs/superpowers/STATUS.md docs/claims.lock.json
rtk git commit -m "docs: os tres comandos de historico, e o que ficou de fora"
```

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §3.1 um artefato por run | 3, 4 |
| §3.2 só estado terminal | 4 |
| §3.3 correlação sem encadeamento | 9 |
| §3.4 agrupamento por capacidade e estado | 8 |
| §3.5 DPU observado, derivado ou recusa | 7 |
| §4.1 `glue.metric` | 6 |
| §4.2 `glue.job_run` | 7 |
| §4.3 `glue.job_run.distribution` | 8 |
| §4.4 `glue.job_run.outcome` | 8 |
| §4.5 os dois `unresolved` | 6, 7, 9 |
| §4.6 os dois `analyzed` | 6, 7 |
| §5.1 CLI | 10 |
| §5.2 MCP, manifesto, paridade, espelhos | 11 |
| §5.3 novo `kind` de artefato | 3 |
| §6 erros nomeados | 4, 5, 6 |
| §7 testes 1–13 | 4, 5, 7, 8, 12 |
| §8 documentação | 1, 13 |
| §9 critérios de aceite | todas |
