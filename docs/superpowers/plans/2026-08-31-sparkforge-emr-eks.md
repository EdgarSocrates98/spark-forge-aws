# EMR on EKS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o SparkForge ler `describe-virtual-cluster` e `describe-job-run` de Amazon EMR on EKS, produzir facts `emrc.*` com namespace fechado, e julgar o que a fonte primária sustentar — fechando a única lacuna binária do inventário de 2026-08-31.

**Architecture:** Terceira plataforma no molde exato da Fase 5d (EMR Serverless). Área de regra própria (`SF-EMRK`), namespace de fact próprio (`emrc.`, de `emr-containers`), coordenador reusado (`emr-infra-reviewer` ganha a área), skill nova (`review-emr-eks`). Um extrator puro que nunca levanta exceção, um coletor de duas chamadas, duas tools MCP e dois subcomandos de CLI em paridade. Nenhuma linha de `SF-EMR` ou `SF-EMRS` muda.

**Tech Stack:** Python 3.11+, `pytest`, YAML para catálogo de regras, `boto3` (opcional, só no coletor), `argparse` para CLI, JSON-RPC para MCP.

**Spec:** [`../specs/2026-08-31-sparkforge-emr-eks-design.md`](../specs/2026-08-31-sparkforge-emr-eks-design.md)

---

## Antes de começar: o que este repositório cobra e que não é óbvio

Leia estes cinco pontos antes da Task 1. Cada um já derrubou uma fase aqui.

1. **A suíte inteira num processo só não sobrevive.** Rode `tests/test_*.py` em seis lotes alfabéticos, um por vez. O lote dos `test_fixtures_golden_*` precisa ser quebrado outra vez, porque cada golden reextrai o corpus. **Nunca edite a árvore com a suíte rodando.**
2. **Golden nunca se escreve à mão.** `python scripts/regen_fixtures.py <nome-da-fixture>` gera; você **lê o diff**. Regenerar sem ler destrói a defesa contra falso positivo, que é a única razão de o golden existir.
3. **Extrator novo entra em DUAS listas manuais**, no mesmo commit, **antes** de a área de regra existir: `EXTRACTORS` em `tests/test_fixtures_kind_coverage.py:55` e a lista de imports/módulos em `tests/test_rules_catalog_reachability.py:35,82`. Esquecer uma **não quebra nada** — é o modo de falha silencioso que os comentários da 5d documentam nos dois arquivos.
4. **Fact transcreve artefato; default não se materializa.** Chave ausente do payload → chave **omitida** do fact (`engine._where_matches` rejeita caminho ausente, e é assim que este motor diz "não sei"). Escrever `False` diz "sei que não", que é outra afirmação.
5. **Candidata sem fonte primária não vira regra** (D-5 da spec). A Task 1 decide quantas regras a Task 10 escreve. Não invente a resposta.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `knowledge/emr-eks/job-run-configuration.md` | Prosa + fontes: shape da API, precedência entre as duas superfícies de config, blocos de monitoring, e o que a fonte **não** sustenta | 1 |
| `knowledge/emr-eks/runtime-matrix.md` | Matriz de release **ou** a declaração medida de que a AWS não publica uma (D-4) | 1 |
| `sparkforge/facts/emr_eks.py` | Extrator puro: JSON em disco → `list[Fact]`. Nunca levanta exceção. Não coleta nada | 2–6 |
| `sparkforge/collect/aws.py` | `emr_eks_path()` + `collect_emr_eks()`, ao lado dos coletores irmãos | 8 |
| `sparkforge/adapters/_core.py` | `_extract_emr_eks_facts()` + `analyze_emr_eks()` | 9 |
| `sparkforge/adapters/tools.py` | Schema e handler de `sparkforge_analyze_emr_eks` e `sparkforge_collect_emr_eks` | 9 |
| `sparkforge/adapters/cli.py` | Subparsers `analyze emr-eks` e `collect emr-eks` + handlers | 9 |
| `rules/catalog/emr-eks.yaml` | Área `SF-EMRK`. Conteúdo decidido pela Task 1 | 10 |
| `rules/catalog/routing.yaml` | `AGENT-007` passa a casar `SF-EMRK` | 11 |
| `agents/emr-infra-reviewer.md` | `rule_areas` ganha `SF-EMRK`; `description` ganha vocabulário de EKS | 11 |
| `skills/review-emr-eks/SKILL.md` | Skill nova, declarando na abertura o que **não** julga | 11 |
| `fixtures/emr_eks/*/` | Corpus: `meta.yaml` + `input/*.json` + `expected/{facts,findings}.json` | 7, 10 |
| `tests/test_facts_emr_eks.py` | Testes de unidade do extrator | 2–6 |
| `tests/test_emr_eks_area_boundary.py` | Fronteira em três direções | 12 |
| `scripts/regen_fixtures.py` | Ganha o import e o ramo de `emr_eks` | 7 |

---

## Task 1: Pesquisa — `knowledge/emr-eks/` e a bifurcação D-4

Esta task **não escreve código** e **decide o escopo das Tasks 6 e 10**. `knowledge/` inteiro tem hoje zero linhas sobre EMR on EKS.

**Files:**
- Create: `knowledge/emr-eks/job-run-configuration.md`
- Create: `knowledge/emr-eks/runtime-matrix.md`
- Modify: `knowledge/sources.lock.json` (via script, nunca à mão)
- Modify: `knowledge/INDEX.md`

- [ ] **Step 1: Ler o formato que o repositório já usa**

Leia `knowledge/emr-serverless/application-configuration.md` inteiro. O formato é: prosa e tabelas, seção `## Fontes` com linhas `Título. URL (retrieved AAAA-MM-DD)`, e — o item que mais importa — **parágrafos finais que declaram o que a fonte não sustenta**. Copie a estrutura, não o conteúdo.

- [ ] **Step 2: Responder as três perguntas da §7 da spec, com fonte**

Escreva `knowledge/emr-eks/job-run-configuration.md` respondendo, cada uma com URL e data de leitura:

1. **Qual o shape exato de `DescribeJobRun` e `DescribeVirtualCluster`?** Fonte: `https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_DescribeJobRun.html` e `API_DescribeVirtualCluster.html`.
2. **Qual a precedência declarada entre `sparkSubmitParameters` e `configurationOverrides.applicationConfiguration` quando as duas tocam a mesma propriedade?** Sem essa resposta a regra pode acusar a superfície errada. Se a documentação não declarar, **escreva que não declara** — é fact sobre a fonte.
3. **`spark.dynamicAllocation` sem `spark.dynamicAllocation.shuffleTracking.enabled` no Kubernetes é defeito que a fonte nomeia?** Fonte candidata: `https://spark.apache.org/docs/latest/running-on-kubernetes.html`. Sem fonte que nomeie, a candidata **não vira regra** na Task 10 (D-5).

- [ ] **Step 3: Resolver a bifurcação D-4 e escrever `runtime-matrix.md`**

Procure em `https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-release-app-versions-7.x.html` e nas *Release versions for Amazon EMR on EKS* se existe matriz que ligue `releaseLabel` a versão de Spark, Python e Iceberg **para EMR on EKS**.

- **Se existe** → escreva a matriz com fonte, data e confiança por célula. As regras da Task 10 **podem** carregar `runtime_scope`, e as fixtures da Task 7 carregam `runtime:`.
- **Se não existe** → escreva a declaração medida de que não existe, no molde do que a 5d escreveu para o Serverless. As regras da Task 10 carregam `runtime_scope: {}` **todas**, e as fixtures carregam `runtime: {}` com a razão no `meta.yaml`.

Escreva no topo do arquivo, em qualquer dos dois casos, esta frase literal:

```markdown
A `EMR_MATRIX` de EMR on EC2 (`knowledge/emr/runtime-matrix.md`) **não** se aplica
a EMR on EKS e não pode ser reusada para preencher eixo nenhum deste runtime.
O `STATUS.md` registra a dívida aberta em que exatamente isso aconteceu com EMR
Serverless: `judge --emr` grava `spark`, `python` e `iceberg` derivados da matriz
de EC2 sobre facts que não têm um único fact de EC2 — três campos inventados sobre
um artefato que não declara nenhum deles.
```

- [ ] **Step 4: Registrar as fontes no lock**

Run: `python scripts/refresh_knowledge.py --offline --update`
Expected: `knowledge/sources.lock.json` ganha as URLs novas com hash. O comando sai 0.

- [ ] **Step 5: Apontar os dois documentos no índice**

Acrescente a `knowledge/INDEX.md` as duas linhas novas, no formato que as linhas de `emr-serverless/` já usam ali.

- [ ] **Step 6: Commit**

```bash
git add knowledge/emr-eks/ knowledge/sources.lock.json knowledge/INDEX.md
git commit -m "docs(knowledge): EMR on EKS, o shape da API e a pergunta de versao"
```

---

## Task 2: Extrator — esqueleto, `emrc.unresolved` e `emrc.analyzed`

O caminho de falha vem **antes** do caminho feliz, de propósito: é o que garante que payload malformado nunca derrube quem chamou.

**Files:**
- Create: `sparkforge/facts/emr_eks.py`
- Create: `tests/test_facts_emr_eks.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_facts_emr_eks.py`:

```python
"""Testes do extrator de Amazon EMR on EKS (`emr-containers`)."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.emr_eks import (
    EMITTED_KINDS,
    extract_emr_eks,
    extract_emr_eks_path,
)


def _reasons(facts: list) -> list[str]:
    return sorted(f.attrs["reason"] for f in facts if f.kind == "emrc.unresolved")


def _kinds(facts: list) -> set[str]:
    return {f.kind for f in facts}


def test_payload_que_nao_e_dict_vira_unresolved_e_nao_excecao():
    facts = extract_emr_eks(["nao", "sou", "dict"], "x.json")
    assert _reasons(facts) == ["malformed_json"]
    assert "emrc.analyzed" in _kinds(facts)


def test_payload_sem_job_run_diz_qual_comando_falta():
    facts = extract_emr_eks({"virtualCluster": {"id": "abc"}}, "x.json")
    assert _reasons(facts) == ["missing_job_run"]
    assert "emrc.analyzed" in _kinds(facts)


def test_job_run_sem_id_nao_ancora_nada():
    facts = extract_emr_eks({"jobRun": {"name": "etl"}}, "x.json")
    assert _reasons(facts) == ["missing_job_run_id"]


def test_a_sentinela_sai_sempre_inclusive_quando_nada_pode_ser_lido():
    facts = extract_emr_eks({}, "x.json")
    sentinelas = [f for f in facts if f.kind == "emrc.analyzed"]
    assert len(sentinelas) == 1
    assert sentinelas[0].measures["unresolved_count"] == 1


def test_nenhum_kind_escapa_do_namespace_declarado():
    facts = extract_emr_eks({}, "x.json")
    assert {f.kind for f in facts} <= EMITTED_KINDS


def test_arquivo_ilegivel_vira_read_error(tmp_path: Path):
    alvo = tmp_path / "ausente.json"
    assert _reasons(extract_emr_eks_path(alvo, repo_root=tmp_path)) == ["read_error"]


def test_json_invalido_vira_malformed_json(tmp_path: Path):
    alvo = tmp_path / "quebrado.json"
    alvo.write_text("{isto nao e json", encoding="utf-8")
    assert _reasons(extract_emr_eks_path(alvo, repo_root=tmp_path)) == ["malformed_json"]
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sparkforge.facts.emr_eks'`

- [ ] **Step 3: Escrever o módulo mínimo**

Crie `sparkforge/facts/emr_eks.py`:

```python
"""Extrator de Facts a partir de uma execucao Amazon EMR on EKS
(`aws emr-containers describe-virtual-cluster` + `describe-job-run`).

Como `emr_serverless.py`/`emr_cluster.py`, este modulo NAO coleta nada: le o JSON
ja salvo em disco, em camelCase, sem traducao. Nunca levanta excecao por payload
malformado -- o que nao consegue ler vira `emrc.unresolved` CONTADO, e a sentinela
`emrc.analyzed` sai sempre, inclusive quando nada pode ser lido.

## Por que `emrc.` e nao `emr.eks.` nem `emrk.`

`emrc` vem de `emr-containers`, que e o nome do servico na API e no CLI. Prefixo
de kind e fronteira de namespace verificada por `EMITTED_KINDS`, e um prefixo que
e sub-caminho de outro (`emr.` de `emr.eks.`) transforma toda checagem de
pertencimento em comparacao de string com armadilha. A area de regra, essa, e
`SF-EMRK`: `SF-EMRC` colidiria visualmente com `SF-EMR` numa lista de findings.

## O limite que vale para TODOS os facts deste modulo

`DescribeJobRun` devolve o que UMA execucao pediu, nao o que o cluster virtual
oferece nem o que o pod efetivamente recebeu. Duas coisas ficam fora do alcance
deste extrator por construcao, e toda regra que cite estes facts precisa redigir
o achado dentro desse limite:

1. **O pod template nao e lido.** `spark.kubernetes.driver.podTemplateFile` e
   `...executor.podTemplateFile` apontam para YAML quase sempre em S3, e resolver
   path->conteudo e mecanismo que nenhum extrator deste repositorio tem. O path
   sai como `emrc.pod_template.unresolved`: o operador ve que existe e que nao
   foi lido. `nodeSelector`, `tolerations` e `resources` moram la, e este modulo
   nao sabe nada sobre eles.
2. **O lado EKS nao existe aqui.** Nodegroup, Karpenter, capacidade de no e pod
   pendente sao outro servico, outro IAM e outra matriz de versao. Um achado
   desta area nunca pode dizer "o pod ficou pendente por falta de no".

## Shape esperado do payload

Um arquivo por execucao, com as DUAS respostas sob chaves de topo -- mesma
decisao de `emr_cluster.py`, que junta `describe-cluster` e cinco listagens num
arquivo so. A correlacao mora no extrator, nao no leitor:

```json
{
  "virtualCluster": {
    "id": "0abc", "name": "analytics", "state": "RUNNING",
    "containerProvider": {
      "type": "EKS", "id": "meu-cluster-eks",
      "info": {"eksInfo": {"namespace": "spark"}}
    }
  },
  "jobRun": {
    "id": "0000000abc", "name": "etl-diario", "virtualClusterId": "0abc",
    "state": "COMPLETED", "releaseLabel": "emr-7.5.0-latest",
    "executionRoleArn": "arn:aws:iam::111122223333:role/EMRContainers-JobRole",
    "jobDriver": {
      "sparkSubmitJobDriver": {
        "entryPoint": "s3://bucket/etl.py",
        "entryPointArguments": ["--data", "s3://bucket/in/"],
        "sparkSubmitParameters": "--conf spark.executor.instances=4 --conf spark.executor.memory=8g"
      }
    },
    "configurationOverrides": {
      "applicationConfiguration": [
        {"classification": "spark-defaults", "properties": {"spark.sql.shuffle.partitions": "400"}}
      ],
      "monitoringConfiguration": {
        "persistentAppUI": "ENABLED",
        "s3MonitoringConfiguration": {"logUri": "s3://bucket/logs/"}
      }
    }
  }
}
```

`releaseLabel` no EKS carrega sufixo (`emr-7.5.0-latest`), que o Serverless nao
tem -- a regex deste modulo o aceita, e a do `emr_serverless.py` nao aceitaria.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "emr_eks@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "emrc.virtual_cluster",
        "emrc.job_run",
        "emrc.spark_submit_parameters",
        "emrc.configuration",
        "emrc.monitoring",
        "emrc.pod_template.unresolved",
        "emrc.unresolved",
        "emrc.analyzed",
    }
)

# ATENCAO -- a regex abaixo esta ERRADA e foi corrigida na execucao. Ver DV-7 da
# spec. Ela nao casa `emr-7.7.0-java8-latest` (DOIS segmentos de sufixo) nem
# `emr-7.7.0-spark-rapids-java8-latest` (tres). As seis formas medidas pela
# Task 1 que a regex precisa tratar, e o que ela deve fazer com cada uma:
#
#   emr-7.5.0-latest                      casa -> (7, 5)
#   emr-7.7.0-java8-latest                casa -> (7, 7)
#   emr-7.7.0-spark-rapids-java8-latest   casa -> (7, 7)
#   emr-6.15.0                            casa -> (6, 15)
#   emr-spark-8.0.0-latest                REJEITA
#   notebook-spark/emr-7.13.0-latest      REJEITA
#
# O sufixo NAO entra no par: ele nomeia o canal (`-latest`) ou a variante
# (`-java8`), nao a versao.
_RELEASE_RE = re.compile(r"^emr-(\d+)\.(\d+)(?:\.\d+)?(?:-[a-z0-9-]+)?$", re.IGNORECASE)


def _file_subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="emrc.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho para todos os
    caminhos de saida, inclusive os que abortam cedo."""
    counts = {
        "virtual_cluster_count": sum(1 for f in facts if f.kind == "emrc.virtual_cluster"),
        "job_run_count": sum(1 for f in facts if f.kind == "emrc.job_run"),
        "configuration_count": sum(1 for f in facts if f.kind == "emrc.configuration"),
        "conf_parameter_count": sum(
            1 for f in facts if f.kind == "emrc.spark_submit_parameters"
        ),
        "unresolved_count": sum(1 for f in facts if f.kind == "emrc.unresolved"),
    }
    # Sentinela: prova de que a extracao rodou sobre ESTE payload. Sem ela, uma
    # condicao `absent:` sobre fact de EKS seria vacuamente verdadeira quando o
    # extrator nunca rodou. Subject de arquivo, nao de job run: ela fala do
    # payload, e existe mesmo quando nenhum job run pode ser lido.
    facts.append(
        Fact(
            kind="emrc.analyzed",
            subject=_file_subject(path),
            measures=counts,
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")
    return sort_facts(facts)


def extract_emr_eks(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado (`dict`) com `virtualCluster` e
    `jobRun`.

    Nunca levanta excecao por payload malformado: chave ausente, secao com o tipo
    errado -- tudo vira `emrc.unresolved` e a extracao segue com o que sobrar,
    mesma convencao de `emr_serverless.extract_emr_serverless`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
        return _finish(facts, path, provenance)

    raw_run = payload.get("jobRun")
    if raw_run is None:
        # Sem `describe-job-run` nao ha release, nem configuracao, nem identidade
        # para ancorar os demais facts. O operador precisa saber qual comando falta.
        facts.append(_unresolved(path, "missing_job_run", provenance))
        return _finish(facts, path, provenance)
    if not isinstance(raw_run, dict):
        facts.append(_unresolved(path, "malformed_json", provenance, section="jobRun"))
        return _finish(facts, path, provenance)

    job_run_id = _as_str(raw_run.get("id"))
    if job_run_id is None:
        # Toda entidade deste extrator e ancorada em `<job_run_id>/...`. Sem o id,
        # nenhum fact tem identidade estavel e dois payloads colidiriam no mesmo
        # subject.
        facts.append(_unresolved(path, "missing_job_run_id", provenance))
        return _finish(facts, path, provenance)

    return _finish(facts, path, provenance)


def extract_emr_eks_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `emrc.unresolved` com reason "read_error"; JSON invalido
    vira "malformed_json". Nunca uma excecao que derruba quem chamou -- mesma
    convencao de `athena_workgroup.extract_athena_workgroup_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty_provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}

    try:
        content = path.read_bytes()
    except OSError:
        return _finish([_unresolved(anchor, "read_error", empty_provenance)], anchor, empty_provenance)

    import hashlib

    digest = hashlib.sha256(content).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": digest, "extractor": EXTRACTOR_ID}
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _finish([_unresolved(anchor, "malformed_json", provenance)], anchor, provenance)

    return extract_emr_eks(payload, anchor, digest)


def extract_emr_eks_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `.json` sob `root`, em ordem determinística de path."""
    facts: list[Fact] = []
    for target in sorted(root.rglob("*.json")):
        facts.extend(extract_emr_eks_path(target, repo_root=repo_root or root))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_emr_eks",
    "extract_emr_eks_path",
    "extract_emr_eks_tree",
]
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: PASS, 7 testes.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/emr_eks.py tests/test_facts_emr_eks.py
git commit -m "feat(facts): extrator de EMR on EKS, caminhos de falha primeiro"
```

---

## Task 3: `emrc.virtual_cluster` e `emrc.job_run`

**Files:**
- Modify: `sparkforge/facts/emr_eks.py`
- Modify: `tests/test_facts_emr_eks.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/test_facts_emr_eks.py`:

```python
_PAYLOAD_COMPLETO = {
    "virtualCluster": {
        "id": "0abc",
        "name": "analytics",
        "state": "RUNNING",
        "containerProvider": {
            "type": "EKS",
            "id": "meu-cluster-eks",
            "info": {"eksInfo": {"namespace": "spark"}},
        },
    },
    "jobRun": {
        "id": "0000000abc",
        "name": "etl-diario",
        "virtualClusterId": "0abc",
        "state": "COMPLETED",
        "releaseLabel": "emr-7.5.0-latest",
        "executionRoleArn": "arn:aws:iam::111122223333:role/EMRContainers-JobRole",
    },
}


def _um(facts: list, kind: str):
    encontrados = [f for f in facts if f.kind == kind]
    assert len(encontrados) == 1, f"esperado 1 {kind}, achei {len(encontrados)}"
    return encontrados[0]


def test_virtual_cluster_carrega_eks_e_namespace():
    fato = _um(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json"), "emrc.virtual_cluster")
    assert fato.attrs["virtual_cluster_id"] == "0abc"
    assert fato.attrs["state"] == "RUNNING"
    assert fato.attrs["container_provider_type"] == "EKS"
    assert fato.attrs["eks_cluster_name"] == "meu-cluster-eks"
    assert fato.attrs["namespace"] == "spark"


def test_job_run_carrega_release_e_role():
    fato = _um(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json"), "emrc.job_run")
    assert fato.attrs["job_run_id"] == "0000000abc"
    assert fato.attrs["release_label"] == "emr-7.5.0-latest"
    assert fato.attrs["execution_role_arn"].endswith("EMRContainers-JobRole")
    assert fato.measures["release_major"] == 7
    assert fato.measures["release_minor"] == 5


def test_sufixo_latest_nao_impede_a_leitura_da_serie():
    # O Serverless publica `emr-7.5.0`; o EKS publica `emr-7.5.0-latest`. Uma
    # regex que rejeitasse o sufixo deixaria TODO job run de EKS sem serie.
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["releaseLabel"] = "emr-6.15.0"
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.job_run")
    assert fato.measures["release_major"] == 6
    assert fato.measures["release_minor"] == 15


def test_release_ilegivel_omite_a_serie_em_vez_de_inventar():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["releaseLabel"] = "custom-build"
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.job_run")
    assert "release_major" not in fato.measures
    assert fato.attrs["release_label"] == "custom-build"


def test_virtual_cluster_ausente_nao_impede_o_job_run():
    # Os dois artefatos sao coletados por chamadas separadas, e o operador pode
    # trazer so um. O job run sozinho ainda sustenta regra.
    payload = {"jobRun": _PAYLOAD_COMPLETO["jobRun"]}
    facts = extract_emr_eks(payload, "x.json")
    assert _kinds(facts) >= {"emrc.job_run", "emrc.analyzed"}
    assert "emrc.virtual_cluster" not in _kinds(facts)
    assert _reasons(facts) == []
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: FAIL, 5 testes novos — `esperado 1 emrc.virtual_cluster, achei 0`

- [ ] **Step 3: Implementar**

Em `sparkforge/facts/emr_eks.py`, acrescente antes de `extract_emr_eks`:

```python
def _release_numbers(label: str | None) -> tuple[int | None, int | None]:
    """`emr-7.5.0-latest` -> `(7, 5)`; qualquer outra forma -> `(None, None)`.

    O par sai como measure para que uma regra possa perguntar "serie 6.x?" sem
    depender da deteccao de runtime -- o proprio payload prova a release, e
    comparacao de string nao existe no avaliador de expressoes do catalogo.
    """
    if label is None:
        return None, None
    match = _RELEASE_RE.match(label)
    if match is None:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _virtual_cluster_fact(
    raw: Any, path: str, provenance: dict[str, Any]
) -> tuple[list[Fact], str | None]:
    """Devolve (facts, virtual_cluster_id). Bloco ausente NAO e erro: os dois
    artefatos vem de chamadas separadas e o operador pode trazer so um."""
    if raw is None:
        return [], None
    if not isinstance(raw, dict):
        return [_unresolved(path, "malformed_json", provenance, section="virtualCluster")], None

    vc_id = _as_str(raw.get("id"))
    if vc_id is None:
        return [_unresolved(path, "missing_virtual_cluster_id", provenance)], None

    provider = raw.get("containerProvider")
    provider = provider if isinstance(provider, dict) else {}
    info = provider.get("info")
    info = info if isinstance(info, dict) else {}
    eks_info = info.get("eksInfo")
    eks_info = eks_info if isinstance(eks_info, dict) else {}

    # Chave ausente do payload -> chave OMITIDA do fact. `engine._where_matches`
    # rejeita caminho ausente, e e assim que este motor diz "nao sei"; escrever
    # `None` diria "sei que nao ha", que e outra afirmacao.
    attrs: dict[str, Any] = {"virtual_cluster_id": vc_id}
    for chave, valor in (
        ("name", _as_str(raw.get("name"))),
        ("state", _as_str(raw.get("state"))),
        ("container_provider_type", _as_str(provider.get("type"))),
        ("eks_cluster_name", _as_str(provider.get("id"))),
        ("namespace", _as_str(eks_info.get("namespace"))),
    ):
        if valor is not None:
            attrs[chave] = valor

    return [
        Fact(
            kind="emrc.virtual_cluster",
            subject=_file_subject(path),
            attrs=attrs,
            provenance=provenance,
        )
    ], vc_id


def _job_run_fact(
    raw: dict[str, Any], job_run_id: str, path: str, provenance: dict[str, Any]
) -> Fact:
    attrs: dict[str, Any] = {"job_run_id": job_run_id}
    for chave, valor in (
        ("name", _as_str(raw.get("name"))),
        ("virtual_cluster_id", _as_str(raw.get("virtualClusterId"))),
        ("state", _as_str(raw.get("state"))),
        ("release_label", _as_str(raw.get("releaseLabel"))),
        ("execution_role_arn", _as_str(raw.get("executionRoleArn"))),
        ("failure_reason", _as_str(raw.get("failureReason"))),
    ):
        if valor is not None:
            attrs[chave] = valor

    measures: dict[str, Any] = {}
    major, minor = _release_numbers(_as_str(raw.get("releaseLabel")))
    if major is not None and minor is not None:
        measures["release_major"] = major
        measures["release_minor"] = minor

    return Fact(
        kind="emrc.job_run",
        subject=_file_subject(path),
        attrs=attrs,
        measures=measures,
        provenance=provenance,
    )
```

E substitua o `return _finish(facts, path, provenance)` final de `extract_emr_eks` (o que vem depois da checagem de `job_run_id`) por:

```python
    vc_facts, _ = _virtual_cluster_fact(payload.get("virtualCluster"), path, provenance)
    facts.extend(vc_facts)
    facts.append(_job_run_fact(raw_run, job_run_id, path, provenance))

    return _finish(facts, path, provenance)
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: PASS, 12 testes.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/emr_eks.py tests/test_facts_emr_eks.py
git commit -m "feat(facts): virtual cluster e job run de EMR on EKS"
```

---

## Task 4: `emrc.spark_submit_parameters` — os dois drivers e a separação do argumento

**Files:**
- Modify: `sparkforge/facts/emr_eks.py`
- Modify: `tests/test_facts_emr_eks.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/test_facts_emr_eks.py`:

```python
def _confs(facts: list) -> dict[str, str]:
    return {
        f.attrs["key"]: f.attrs["value"]
        for f in facts
        if f.kind == "emrc.spark_submit_parameters"
    }


def test_conf_do_spark_submit_sai_par_a_par():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://bucket/etl.py",
            "sparkSubmitParameters": (
                "--conf spark.executor.instances=4 --conf spark.executor.memory=8g"
            ),
        }
    }
    confs = _confs(extract_emr_eks(payload, "x.json"))
    assert confs == {
        "spark.executor.instances": "4",
        "spark.executor.memory": "8g",
    }


def test_entry_point_arguments_nao_vira_configuracao():
    # Argumento de aplicacao NAO e configuracao de Spark. Confundir os dois faria
    # o detector de segredo varrer a superficie errada.
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://bucket/etl.py",
            "entryPointArguments": ["--conf", "spark.nao.sou.conf=1"],
            "sparkSubmitParameters": "--conf spark.executor.cores=2",
        }
    }
    confs = _confs(extract_emr_eks(payload, "x.json"))
    assert confs == {"spark.executor.cores": "2"}


def test_flag_do_spark_submit_que_nao_e_conf_e_ignorada():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {
            "sparkSubmitParameters": "--class Main --conf spark.executor.cores=2 --verbose"
        }
    }
    confs = _confs(extract_emr_eks(payload, "x.json"))
    assert confs == {"spark.executor.cores": "2"}


def test_conf_sem_igual_vira_unresolved_em_vez_de_par_torto():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {"sparkSubmitParameters": "--conf spark.sem.valor"}
    }
    facts = extract_emr_eks(payload, "x.json")
    assert _reasons(facts) == ["malformed_conf"]
    assert _confs(facts) == {}


def test_spark_sql_job_driver_tambem_e_lido():
    # A API aceita `sparkSqlJobDriver` no lugar de `sparkSubmitJobDriver`. Ler so
    # o primeiro deixaria todo job SQL sem um unico fact de configuracao.
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSqlJobDriver": {
            "entryPoint": "s3://bucket/query.sql",
            "sparkSqlParameters": "--conf spark.sql.shuffle.partitions=800",
        }
    }
    confs = _confs(extract_emr_eks(payload, "x.json"))
    assert confs == {"spark.sql.shuffle.partitions": "800"}


def test_o_fact_diz_de_qual_superficie_o_valor_veio():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {"sparkSubmitParameters": "--conf spark.executor.cores=2"}
    }
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.spark_submit_parameters")
    assert fato.attrs["surface"] == "spark_submit_parameters"
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_facts_emr_eks.py -q -k conf or driver`
Expected: FAIL, 6 testes novos.

- [ ] **Step 3: Implementar**

Em `sparkforge/facts/emr_eks.py`, acrescente antes de `extract_emr_eks`:

```python
# As duas formas de `jobDriver` documentadas, e o campo de parametros de cada
# uma. Ler so a primeira deixaria todo job SQL sem um unico fact de configuracao.
_DRIVERS: tuple[tuple[str, str], ...] = (
    ("sparkSubmitJobDriver", "sparkSubmitParameters"),
    ("sparkSqlJobDriver", "sparkSqlParameters"),
)


def _spark_submit_facts(
    raw_driver: Any, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    """Separa os `--conf` do texto de parametros, par a par.

    `entryPointArguments` fica DE FORA de proposito: argumento de aplicacao nao e
    configuracao de Spark, e confundir os dois faria o detector de segredo varrer
    a superficie errada.

    Uma flag que nao seja `--conf` (`--class`, `--verbose`, `--jars`) e ignorada
    em silencio: este fact responde por configuracao de Spark, e mais nada.
    """
    if not isinstance(raw_driver, dict):
        return []

    facts: list[Fact] = []
    for driver_key, params_key in _DRIVERS:
        driver = raw_driver.get(driver_key)
        if not isinstance(driver, dict):
            continue
        texto = _as_str(driver.get(params_key))
        if texto is None:
            continue

        tokens = texto.split()
        indice = 0
        while indice < len(tokens):
            if tokens[indice] != "--conf":
                indice += 1
                continue
            if indice + 1 >= len(tokens):
                facts.append(_unresolved(path, "malformed_conf", provenance, surface=params_key))
                break
            par = tokens[indice + 1]
            if "=" not in par:
                # `--conf spark.sem.valor` nao e um par. Aceita-lo produziria um
                # fact com valor vazio, indistinguivel de uma propriedade
                # legitimamente vazia.
                facts.append(
                    _unresolved(path, "malformed_conf", provenance, surface=params_key, token=par)
                )
                indice += 2
                continue
            chave, _, valor = par.partition("=")
            facts.append(
                Fact(
                    kind="emrc.spark_submit_parameters",
                    subject=_file_subject(path),
                    attrs={
                        "key": chave,
                        "value": valor,
                        # Procedencia: qual das DUAS superficies de configuracao
                        # pediu este valor. A §19 do CLAUDE.md cobra que o
                        # extrator nao destrua isso antes de a regra chegar.
                        "surface": "spark_submit_parameters",
                        "driver": driver_key,
                    },
                    provenance=provenance,
                )
            )
            indice += 2
    return facts
```

E, dentro de `extract_emr_eks`, acrescente depois de `facts.append(_job_run_fact(...))`:

```python
    facts.extend(_spark_submit_facts(raw_run.get("jobDriver"), path, provenance))
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: PASS, 18 testes.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/emr_eks.py tests/test_facts_emr_eks.py
git commit -m "feat(facts): --conf do spark-submit, sem confundir com argumento da aplicacao"
```

---

## Task 5: `emrc.configuration` e `emrc.monitoring`

**Files:**
- Modify: `sparkforge/facts/emr_eks.py`
- Modify: `tests/test_facts_emr_eks.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/test_facts_emr_eks.py`:

```python
def test_application_configuration_sai_por_propriedade():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["configurationOverrides"] = {
        "applicationConfiguration": [
            {
                "classification": "spark-defaults",
                "properties": {"spark.sql.shuffle.partitions": "400"},
            }
        ]
    }
    fatos = [f for f in extract_emr_eks(payload, "x.json") if f.kind == "emrc.configuration"]
    assert len(fatos) == 1
    assert fatos[0].attrs["classification"] == "spark-defaults"
    assert fatos[0].attrs["key"] == "spark.sql.shuffle.partitions"
    assert fatos[0].attrs["value"] == "400"
    assert fatos[0].attrs["surface"] == "application_configuration"


def test_as_duas_superficies_convivem_sem_se_apagar():
    # A mesma propriedade nas DUAS superficies produz DOIS facts. Fundi-las
    # apagaria a unica pergunta que importa quando divergem: qual venceu.
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {"sparkSubmitParameters": "--conf spark.executor.cores=2"}
    }
    payload["jobRun"]["configurationOverrides"] = {
        "applicationConfiguration": [
            {"classification": "spark-defaults", "properties": {"spark.executor.cores": "8"}}
        ]
    }
    facts = extract_emr_eks(payload, "x.json")
    superficies = {
        (f.attrs["surface"], f.attrs["value"])
        for f in facts
        if f.attrs.get("key") == "spark.executor.cores"
    }
    assert superficies == {
        ("spark_submit_parameters", "2"),
        ("application_configuration", "8"),
    }


def test_monitoring_conta_os_destinos_de_log():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["configurationOverrides"] = {
        "monitoringConfiguration": {
            "persistentAppUI": "ENABLED",
            "s3MonitoringConfiguration": {"logUri": "s3://bucket/logs/"},
        }
    }
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.attrs["s3_log_uri_present"] is True
    assert fato.attrs["cloudwatch_enabled"] is False
    assert fato.attrs["persistent_app_ui_enabled"] is True
    assert fato.measures["log_destination_count"] == 1


def test_monitoring_ausente_e_zero_destinos_e_nao_silencio():
    # Sem bloco de monitoramento, EMR on EKS nao grava log em lugar nenhum -- ao
    # contrario do Serverless, cujo armazenamento gerenciado tem default LIGADO.
    # Omitir o fact aqui deixaria a regra "nenhum destino de log" sem ingrediente
    # justamente no caso mais comum do estado que ela acusa.
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.measures["log_destination_count"] == 0
    assert fato.attrs["monitoring_declared"] is False


def test_cloudwatch_conta_como_destino():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["configurationOverrides"] = {
        "monitoringConfiguration": {
            "cloudWatchMonitoringConfiguration": {
                "logGroupName": "/emr-containers/jobs",
                "logStreamNamePrefix": "etl",
            }
        }
    }
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.attrs["cloudwatch_enabled"] is True
    assert fato.measures["log_destination_count"] == 1
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: FAIL, 5 testes novos.

- [ ] **Step 3: Implementar**

Em `sparkforge/facts/emr_eks.py`, acrescente antes de `extract_emr_eks`:

```python
def _configuration_facts(
    raw: Any, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    """Achata `applicationConfiguration` em um fact por propriedade.

    A lista e recursiva na API (`configurations` dentro de `configurations`), e
    este extrator desce nela: uma classificacao aninhada que nao fosse lida
    esconderia exatamente o valor que alguem enterrou.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        return [
            _unresolved(
                path, "malformed_json", provenance, section="applicationConfiguration"
            )
        ]

    facts: list[Fact] = []
    for entrada in raw:
        if not isinstance(entrada, dict):
            facts.append(
                _unresolved(
                    path, "malformed_json", provenance, section="applicationConfiguration"
                )
            )
            continue
        classification = _as_str(entrada.get("classification")) or ""
        propriedades = entrada.get("properties")
        if isinstance(propriedades, dict):
            for chave, valor in sorted(propriedades.items()):
                facts.append(
                    Fact(
                        kind="emrc.configuration",
                        subject=_file_subject(path),
                        attrs={
                            "classification": classification,
                            "key": str(chave),
                            "value": "" if valor is None else str(valor),
                            "surface": "application_configuration",
                        },
                        provenance=provenance,
                    )
                )
        aninhadas = entrada.get("configurations")
        if aninhadas is not None:
            facts.extend(_configuration_facts(aninhadas, path, provenance))
    return facts


def _monitoring_fact(raw: Any, path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Responde por destino, com `log_destination_count` resumindo os dois.

    ATENCAO -- isto e o INVERSO do EMR Serverless. La, `monitoringConfiguration`
    ausente significa armazenamento gerenciado LIGADO por default, e uma regra que
    disparasse por ausencia acusaria toda application no default seguro. No EMR on
    EKS nao ha armazenamento gerenciado: sem bloco, nao ha destino nenhum. Por isso
    o fact sai SEMPRE, inclusive quando o bloco nao veio, e `monitoring_declared`
    distingue "a API nao devolveu o bloco" de "o bloco veio vazio".

    `persistentAppUI` NAO conta como destino de log: e a UI de aplicacao, nao um
    lugar onde o log sobrevive ao pod.
    """
    declarado = isinstance(raw, dict)
    bloco = raw if declarado else {}

    s3 = bloco.get("s3MonitoringConfiguration")
    s3_uri = _as_str(s3.get("logUri")) if isinstance(s3, dict) else None
    s3_present = s3_uri is not None

    cw = bloco.get("cloudWatchMonitoringConfiguration")
    cw_enabled = isinstance(cw, dict) and _as_str(cw.get("logGroupName")) is not None

    # `persistentAppUI` e uma STRING (`ENABLED`/`DISABLED`), nao um booleano, e o
    # default documentado e ENABLED.
    app_ui = _as_str(bloco.get("persistentAppUI"))
    app_ui_enabled = app_ui is None or app_ui.upper() == "ENABLED"

    attrs: dict[str, Any] = {
        "monitoring_declared": declarado,
        "s3_log_uri_present": s3_present,
        "cloudwatch_enabled": cw_enabled,
        "persistent_app_ui_enabled": app_ui_enabled,
        "persistent_app_ui_declared": app_ui is not None,
    }
    if s3_uri is not None:
        attrs["s3_log_uri"] = s3_uri

    return [
        Fact(
            kind="emrc.monitoring",
            subject=_file_subject(path),
            attrs=attrs,
            measures={"log_destination_count": int(s3_present) + int(cw_enabled)},
            provenance=provenance,
        )
    ]
```

E, dentro de `extract_emr_eks`, acrescente depois da linha de `_spark_submit_facts`:

```python
    overrides = raw_run.get("configurationOverrides")
    overrides = overrides if isinstance(overrides, dict) else {}
    facts.extend(
        _configuration_facts(overrides.get("applicationConfiguration"), path, provenance)
    )
    facts.extend(_monitoring_fact(overrides.get("monitoringConfiguration"), path, provenance))
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: PASS, 23 testes.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/emr_eks.py tests/test_facts_emr_eks.py
git commit -m "feat(facts): as duas superficies de configuracao e os destinos de log"
```

---

## Task 6: `emrc.pod_template.unresolved` — a recusa que se vê

**Files:**
- Modify: `sparkforge/facts/emr_eks.py`
- Modify: `tests/test_facts_emr_eks.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `tests/test_facts_emr_eks.py`:

```python
def _templates(facts: list) -> dict[str, str]:
    return {
        f.attrs["role"]: f.attrs["path"]
        for f in facts
        if f.kind == "emrc.pod_template.unresolved"
    }


def test_pod_template_declarado_sai_como_recusa_com_o_path():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["configurationOverrides"] = {
        "applicationConfiguration": [
            {
                "classification": "spark-defaults",
                "properties": {
                    "spark.kubernetes.driver.podTemplateFile": "s3://bucket/driver.yaml",
                    "spark.kubernetes.executor.podTemplateFile": "s3://bucket/executor.yaml",
                },
            }
        ]
    }
    assert _templates(extract_emr_eks(payload, "x.json")) == {
        "driver": "s3://bucket/driver.yaml",
        "executor": "s3://bucket/executor.yaml",
    }


def test_pod_template_pedido_pelo_spark_submit_tambem_e_visto():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {
            "sparkSubmitParameters": (
                "--conf spark.kubernetes.driver.podTemplateFile=s3://bucket/d.yaml"
            )
        }
    }
    assert _templates(extract_emr_eks(payload, "x.json")) == {"driver": "s3://bucket/d.yaml"}


def test_sem_pod_template_nao_ha_recusa():
    # Recusa sem objeto seria ruido: o operador leria "nao li o template" onde
    # nenhum template foi pedido.
    assert _templates(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json")) == {}
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_facts_emr_eks.py -q -k pod_template`
Expected: FAIL, 2 dos 3 testes novos.

- [ ] **Step 3: Implementar**

Em `sparkforge/facts/emr_eks.py`, acrescente antes de `extract_emr_eks`:

```python
# As duas propriedades que apontam para YAML fora do artefato. O valor delas e um
# path -- quase sempre em S3 --, e resolver path->conteudo e mecanismo que nenhum
# extrator deste repositorio tem. O fact existe para que a recusa seja VISIVEL:
# o operador ve que o template existe e que nao foi lido.
_POD_TEMPLATE_KEYS = {
    "spark.kubernetes.driver.podTemplateFile": "driver",
    "spark.kubernetes.executor.podTemplateFile": "executor",
}


def _pod_template_facts(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Varre os facts de configuracao JA extraidos das DUAS superficies.

    Varrer os facts em vez do payload evita duplicar a leitura das duas
    superficies -- e garante que uma superficie nova, no dia em que existir,
    entre aqui de graca.
    """
    achados: list[Fact] = []
    vistos: set[str] = set()
    for fato in facts:
        if fato.kind not in {"emrc.configuration", "emrc.spark_submit_parameters"}:
            continue
        papel = _POD_TEMPLATE_KEYS.get(fato.attrs.get("key", ""))
        if papel is None or papel in vistos:
            continue
        vistos.add(papel)
        achados.append(
            Fact(
                kind="emrc.pod_template.unresolved",
                subject=_file_subject(path),
                attrs={
                    "role": papel,
                    "path": fato.attrs["value"],
                    "surface": fato.attrs["surface"],
                    "reason": "not_fetched",
                },
                provenance=provenance,
            )
        )
    return achados
```

E, dentro de `extract_emr_eks`, acrescente **depois** das linhas de `_configuration_facts` e `_monitoring_fact` (a ordem importa: a varredura consome os facts já extraídos):

```python
    facts.extend(_pod_template_facts(facts, path, provenance))
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python -m pytest tests/test_facts_emr_eks.py -q`
Expected: PASS, 26 testes.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/emr_eks.py tests/test_facts_emr_eks.py
git commit -m "feat(facts): pod template declarado sai como recusa visivel, nao silencio"
```

---

## Task 7: As duas listas manuais, o regenerador e as fixtures

Esta task é onde a fase mais fácil de errar em silêncio. Leia o ponto 3 do preâmbulo antes.

**Files:**
- Modify: `tests/test_fixtures_kind_coverage.py:55` (dicionário `EXTRACTORS`)
- Modify: `tests/test_rules_catalog_reachability.py:35,82`
- Modify: `scripts/regen_fixtures.py`
- Create: `fixtures/emr_eks/job_run_saudavel/{meta.yaml,input/job.json}`
- Create: `fixtures/emr_eks/sem_destino_de_log/{meta.yaml,input/job.json}`
- Create: `fixtures/emr_eks/payload_vazio/{meta.yaml,input/job.json}`
- Create: `fixtures/emr_eks/pod_template_declarado/{meta.yaml,input/job.json}`

- [ ] **Step 1: Entrar nas duas listas, no mesmo commit**

Em `tests/test_fixtures_kind_coverage.py`, acrescente ao bloco de imports do topo `emr_eks,` (ordem alfabética, depois de `emr_cluster`) e ao dicionário `EXTRACTORS`, logo depois da linha `"emr_cluster": emr_cluster,`:

```python
    # `emr_eks` entra nas DUAS listas no mesmo commit desta Task, ANTES de a area
    # SF-EMRK existir. Sem ele aqui, os oito kinds `emrc.*` nao sao verificados
    # por ninguem e o criterio de golden -- todo kind de `EMITTED_KINDS` em algum
    # golden -- passa sem ser avaliado, que e pior do que falhar. Medido pelo
    # contrafactual: tirando esta linha,
    # `test_no_golden_carries_a_kind_that_no_extractor_declares` reprova nomeando
    # os oito.
    "emr_eks": emr_eks,
```

Em `tests/test_rules_catalog_reachability.py`, acrescente `emr_eks,` ao bloco de import da linha 35 e à lista de módulos da linha 82, com o mesmo comentário resumido.

- [ ] **Step 2: Rodar e verificar que falha por falta de golden**

Run: `python -m pytest tests/test_fixtures_kind_coverage.py -q`
Expected: FAIL — `test_every_kind_of_every_extractor_appears_in_some_golden[emr_eks]`, nomeando os oito kinds. **Vermelho de propósito**, não em silêncio: as fixtures são o Step 4.

- [ ] **Step 3: Ensinar o regenerador**

Em `scripts/regen_fixtures.py`, acrescente ao bloco de imports (ordem alfabética, depois de `emr_cluster`):

```python
from sparkforge.facts.emr_eks import extract_emr_eks_tree  # noqa: E402
```

E, no despacho por domínio de fixture, o ramo de `emr_eks` no molde exato do ramo de `emr_serverless` que já está ali — o domínio é o nome do diretório sob `fixtures/`, e o extrator recebe `input/` como raiz.

- [ ] **Step 4: Escrever as quatro fixtures**

`fixtures/emr_eks/job_run_saudavel/input/job.json`:

```json
{
  "virtualCluster": {
    "id": "0abcdefghijklmnop",
    "name": "analytics",
    "state": "RUNNING",
    "containerProvider": {
      "type": "EKS",
      "id": "producao-eks",
      "info": {"eksInfo": {"namespace": "spark"}}
    }
  },
  "jobRun": {
    "id": "0000000abcdefghij",
    "name": "etl-diario",
    "virtualClusterId": "0abcdefghijklmnop",
    "state": "COMPLETED",
    "releaseLabel": "emr-7.5.0-latest",
    "executionRoleArn": "arn:aws:iam::111122223333:role/EMRContainersJobRole",
    "jobDriver": {
      "sparkSubmitJobDriver": {
        "entryPoint": "s3://bucket/etl.py",
        "entryPointArguments": ["--data", "s3://bucket/in/"],
        "sparkSubmitParameters": "--conf spark.executor.instances=4"
      }
    },
    "configurationOverrides": {
      "applicationConfiguration": [
        {
          "classification": "spark-defaults",
          "properties": {"spark.sql.shuffle.partitions": "400"}
        }
      ],
      "monitoringConfiguration": {
        "persistentAppUI": "ENABLED",
        "s3MonitoringConfiguration": {"logUri": "s3://bucket/logs/"}
      }
    }
  }
}
```

`fixtures/emr_eks/job_run_saudavel/meta.yaml`:

```yaml
name: job_run_saudavel
proves: >
  O negativo de toda a area: uma execucao que declara destino de log, nao
  esconde segredo, nao pede pod template e nao contradiz a si mesma. Se
  qualquer regra SF-EMRK disparar aqui, ela acusa configuracao correta -- que
  e o pior tipo de defeito de regra segundo rules/catalog/README.md.
# RESOLVIDO pela Task 1 (commit c724c80) -- ver DV-1 e DV-2 da spec.
# A AWS PUBLICA matriz de release para EMR on EKS, na linha `Supported
# applications` de cada release note. Preencha `spark` a partir dela.
# NAO preencha `iceberg`: a linha e publicada por FAMILIA e nao por variante, e
# `emr-7.7.0-java8-latest` nao tem Iceberg nenhum -- derivar do label erraria
# exatamente nas imagens Java 8.
# NAO preencha `python` nem `hadoop`: 2 de 34 paginas declaram Python (em prosa,
# nao em tabela) e 0 de 34 declaram Hadoop.
# A EMR_MATRIX de EMR on EC2 continua proibida, e agora por razao mais forte que
# a da D-4 original: ela nao e inaplicavel por falta de fonte como no Serverless
# -- ela e MEDIDAMENTE ERRADA aqui (Iceberg diverge em 6 de 26 releases, Spark em
# 4; `emr-6.5.0` no EKS nao publica Iceberg e no EC2 publica 0.12.0).
# Preencha `spark` com o valor que a §2 de knowledge/emr-eks/runtime-matrix.md
# publica PARA A RELEASE DESTA FIXTURE (`emr-7.5.0-latest`), copiado da tabela --
# nao de memoria, e nao da coluna de EC2, que e a coluna ao lado e diverge.
runtime:
  spark: "<da §2 de knowledge/emr-eks/runtime-matrix.md, linha emr-7.5.0>"
expects_kinds:
  - emrc.analyzed
  - emrc.configuration
  - emrc.job_run
  - emrc.monitoring
  - emrc.spark_submit_parameters
  - emrc.virtual_cluster
expects_rules: []
```

`fixtures/emr_eks/sem_destino_de_log/input/job.json` — igual ao anterior, com `configurationOverrides.monitoringConfiguration` **removido inteiro** e `id`/`name` do job run trocados para `0000000klmnopqrst` / `etl-sem-log`.

`fixtures/emr_eks/sem_destino_de_log/meta.yaml`:

```yaml
name: sem_destino_de_log
proves: >
  Nenhum destino de log na execucao. E o analogo de SF-EMRS-003 e SF-EMR-006, com
  a diferenca que muda a leitura: no EMR Serverless o armazenamento gerenciado tem
  default LIGADO e zero destinos exige tres atos deliberados; no EMR on EKS nao ha
  armazenamento gerenciado, e o bloco ausente JA e zero destino. Por isso
  `emrc.monitoring` sai mesmo sem o bloco, com `monitoring_declared: false` --
  omiti-lo deixaria a regra sem ingrediente no caso mais comum do estado que ela
  acusa.
runtime: {}
expects_kinds:
  - emrc.analyzed
  - emrc.configuration
  - emrc.job_run
  - emrc.monitoring
  - emrc.spark_submit_parameters
  - emrc.virtual_cluster
expects_rules: []
```

`fixtures/emr_eks/payload_vazio/input/job.json`:

```json
{}
```

`fixtures/emr_eks/payload_vazio/meta.yaml`:

```yaml
name: payload_vazio
proves: >
  A sentinela sai mesmo quando nada pode ser lido, e `emrc.unresolved` nomeia o
  comando que falta em vez de o extrator levantar excecao. Sem esta fixture,
  nenhum golden carrega `emrc.unresolved` e o kind fica sem prova.
runtime: {}
expects_kinds:
  - emrc.analyzed
  - emrc.unresolved
expects_rules: []
```

`fixtures/emr_eks/pod_template_declarado/input/job.json` — igual a `job_run_saudavel`, com `id`/`name` trocados para `0000000uvwxyzabcd` / `etl-com-template` e as duas propriedades de template acrescentadas ao bloco `spark-defaults`:

```json
"spark.kubernetes.driver.podTemplateFile": "s3://bucket/templates/driver.yaml",
"spark.kubernetes.executor.podTemplateFile": "s3://bucket/templates/executor.yaml"
```

`fixtures/emr_eks/pod_template_declarado/meta.yaml`:

```yaml
name: pod_template_declarado
proves: >
  A recusa VISIVEL. `emrc.pod_template.unresolved` e o unico kind desta area que
  nao alimenta regra nenhuma, e ainda assim precisa de golden: ele existe para
  que o operador veja que o template foi pedido e nao foi lido. Sem fixture, o
  kind fica sem prova e o gate de cobertura passa sem avaliar.
runtime: {}
expects_kinds:
  - emrc.analyzed
  - emrc.configuration
  - emrc.job_run
  - emrc.monitoring
  - emrc.pod_template.unresolved
  - emrc.spark_submit_parameters
  - emrc.virtual_cluster
expects_rules: []
```

- [ ] **Step 5: Gerar os goldens e LER o diff**

Run: `python scripts/regen_fixtures.py job_run_saudavel sem_destino_de_log payload_vazio pod_template_declarado`
Expected: cria `expected/facts.json` e `expected/findings.json` nas quatro.

Run: `git diff --stat fixtures/emr_eks/`
Confira, antes de seguir: `sem_destino_de_log` tem `log_destination_count: 0` e `monitoring_declared: false`; `pod_template_declarado` tem exatamente dois `emrc.pod_template.unresolved`; `payload_vazio` tem `unresolved_count: 1`.

- [ ] **Step 6: Rodar o gate de cobertura**

Run: `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q`
Expected: PASS. Os oito kinds de `emrc.*` aparecem em algum golden.

- [ ] **Step 7: Commit**

```bash
git add tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py scripts/regen_fixtures.py fixtures/emr_eks/
git commit -m "test(fixtures): corpus de EMR on EKS e as duas listas manuais no mesmo commit"
```

---

## Task 8: Coletor `collect_emr_eks` — duas chamadas, um arquivo

**Files:**
- Modify: `sparkforge/collect/aws.py` (helper de path perto da linha 159; coletor perto de `collect_emr_serverless`; `__all__` no fim)
- Modify: `tests/test_collect_aws.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_collect_aws.py` (siga o padrão de cliente falso que os testes de `collect_emr_serverless` já usam no arquivo):

```python
def test_collect_emr_eks_grava_as_duas_respostas_num_arquivo(tmp_path, monkeypatch):
    class _Fake:
        def describe_virtual_cluster(self, **kw):
            assert kw == {"id": "0abc"}
            return {"virtualCluster": {"id": "0abc", "state": "RUNNING"}}

        def describe_job_run(self, **kw):
            assert kw == {"id": "0run", "virtualClusterId": "0abc"}
            return {"jobRun": {"id": "0run", "virtualClusterId": "0abc"}}

    _instalar_boto3_falso(monkeypatch, {"emr-containers": _Fake()})

    entrada = collect_emr_eks("0abc", "0run", tmp_path, now="2026-08-31T00:00:00Z")

    gravado = json.loads((tmp_path / entrada.path).read_text(encoding="utf-8"))
    assert set(gravado) == {"virtualCluster", "jobRun"}
    assert gravado["jobRun"]["id"] == "0run"
    assert entrada.path == ".sparkforge/artifacts/emr_eks/0abc_0run.json"
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_collect_aws.py -q -k emr_eks`
Expected: FAIL — `ImportError: cannot import name 'collect_emr_eks'`

- [ ] **Step 3: Implementar**

Em `sparkforge/collect/aws.py`, logo depois de `emr_serverless_path` (linha ~161):

```python
def emr_eks_path(virtual_cluster_id: str, job_run_id: str) -> str:
    return f".sparkforge/artifacts/emr_eks/{virtual_cluster_id}_{job_run_id}.json"
```

E, ao lado de `collect_emr_serverless`:

```python
def collect_emr_eks(
    virtual_cluster_id: str, job_run_id: str, root: Path, *, now: str
) -> ArtifactEntry:
    """Baixa `describe-virtual-cluster` e `describe-job-run` e grava os dois no
    MESMO arquivo, sob chaves de topo.

    DUAS chamadas, nao uma, e nao seis. O cluster virtual e o job run moram em
    APIs separadas -- ao contrario do Serverless, onde `GetApplication` ja traz
    tudo --, e junta-los aqui e a mesma decisao que `collect_emr_cluster` toma ao
    reunir `describe-cluster` e cinco listagens: a correlacao mora no extrator, e
    um arquivo autocontido por execucao e o que permite ancorar todo fact no mesmo
    subject.

    **Os dois ids sao obrigatorios, e nao ha resolucao por nome.** `DescribeJobRun`
    exige `virtualClusterId` junto do `id`, e `name` e opcional na API dos dois
    lados. Um coletor que aceitasse nome escolheria uma entre N homonimas em
    silencio e gravaria o artefato errado com aparencia de certo -- mesma
    disciplina de `collect_emr_cluster`, que so aceita `j-XXXX`, e de
    `collect_emr_serverless`, que so aceita `applicationId`.

    O que fica de fora por escopo desta fase (spec secao 2), nao por limitacao da
    API: `list-job-runs`, o pod template apontado pela configuracao, e todo o lado
    EKS (nodegroup, autoscaling, pods).
    """
    rel_path = emr_eks_path(virtual_cluster_id, job_run_id)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("emr-containers")

    virtual_cluster = (
        client.describe_virtual_cluster(id=virtual_cluster_id).get("virtualCluster") or {}
    )
    job_run = (
        client.describe_job_run(id=job_run_id, virtualClusterId=virtual_cluster_id).get("jobRun")
        or {}
    )
    payload: dict[str, Any] = {"virtualCluster": virtual_cluster, "jobRun": job_run}

    content = json.dumps(payload, indent=2, sort_keys=True, default=str, ensure_ascii=False).encode(
        "utf-8"
    )
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="emr_eks",
        source=f"emr-containers:describe_job_run:{virtual_cluster_id}:{job_run_id}",
        collect_command=(
            f"sparkforge collect emr-eks --virtual-cluster-id {virtual_cluster_id} "
            f"--job-run-id {job_run_id}"
        ),
        now=now,
    )
```

Acrescente `"collect_emr_eks"` e `"emr_eks_path"` a `__all__`, em ordem alfabética.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python -m pytest tests/test_collect_aws.py -q -k emr_eks`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/collect/aws.py tests/test_collect_aws.py
git commit -m "feat(collect): describe-virtual-cluster e describe-job-run num arquivo autocontido"
```

---

## Task 9: Superfície — `_core`, MCP e CLI em paridade

**Files:**
- Modify: `sparkforge/adapters/_core.py`
- Modify: `sparkforge/adapters/tools.py`
- Modify: `sparkforge/adapters/cli.py`
- Modify: `tests/test_cli_mcp_parity.py`

- [ ] **Step 1: Escrever o teste de paridade que falha**

Acrescente a `tests/test_cli_mcp_parity.py`:

```python
def test_emr_eks_tem_as_quatro_superficies():
    from sparkforge.adapters import cli, tools

    assert "sparkforge_analyze_emr_eks" in tools.TOOLS
    assert "sparkforge_collect_emr_eks" in tools.TOOLS
    assert ("analyze", "emr-eks") in cli.COMMANDS
    assert ("collect", "emr-eks") in cli.COMMANDS
```

(Se o dicionário de despacho em `cli.py` tiver outro nome que `COMMANDS`, use o nome real — ele está logo acima da linha 2217.)

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_cli_mcp_parity.py -q -k emr_eks`
Expected: FAIL — `assert 'sparkforge_analyze_emr_eks' in ...`

- [ ] **Step 3: `_core.py`**

Ao lado de `_extract_emr_serverless_facts` e `analyze_emr_serverless`:

```python
def _extract_emr_eks_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps de EMR on EKS ou para um arquivo .json:\n"
            f"    sparkforge collect emr-eks --repo . --virtual-cluster-id 0abc "
            f"--job-run-id 0run --now <iso>\n"
            f"    sparkforge analyze emr-eks --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_emr_eks.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_emr_eks_tree(target, repo_root=target)
    return extract_emr_eks_path(target, repo_root=target.parent)


def analyze_emr_eks(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_emr_eks_facts(path)
    return _facts_page(facts, "emrc.unresolved", kind, limit, cursor, detail_level)


def collect_emr_eks(
    repo: str, virtual_cluster_id: str, job_run_id: str, now: str
) -> dict[str, Any]:
    from sparkforge.collect.aws import collect_emr_eks as _collect

    entrada = _collect(virtual_cluster_id, job_run_id, Path(repo), now=now)
    return {"artifact": entrada.path, "sha256": entrada.sha256}
```

Acrescente ao bloco de imports do topo:

```python
from sparkforge.facts.emr_eks import extract_emr_eks_path, extract_emr_eks_tree
```

- [ ] **Step 4: `tools.py`**

Acrescente ao dicionário `TOOLS`, ao lado de `sparkforge_analyze_emr_serverless`:

```python
    "sparkforge_analyze_emr_eks": {
        "description": (
            "Extrai facts de uma execucao Amazon EMR on EKS (describe-virtual-cluster "
            "+ describe-job-run num arquivo). Descreve o que UMA execucao pediu, nunca "
            "o que o pod recebeu: pod template nao e lido (sai como recusa com o path) "
            "e o lado EKS -- nodegroup, autoscaling, pod pendente -- nao existe aqui. "
            "O JSON precisa estar salvo em disco (`sparkforge_collect_emr_eks` ou "
            "`aws emr-containers describe-job-run ...` a mao fazem isso)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Arquivo .json ou diretorio."},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "detail_level": {"type": "string", "enum": ["full", "compact", "minimal"]},
            },
            "required": ["path"],
        },
    },
```

E, ao lado de `sparkforge_collect_emr_serverless`:

```python
    "sparkforge_collect_emr_eks": {
        "description": (
            "Baixa describe-virtual-cluster e describe-job-run e grava os dois no mesmo "
            "arquivo. Os DOIS ids sao obrigatorios: DescribeJobRun exige virtualClusterId "
            "junto do id, e nome nao serve -- e opcional na API e nao ha fonte que o "
            "declare unico. Coleta manual e automatica produzem o mesmo arquivo, que e o "
            "que `sparkforge_analyze_emr_eks` le."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "virtual_cluster_id": {"type": "string", "description": "`0abcXXXX`"},
                "job_run_id": {"type": "string", "description": "`0000000XXXX`"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
            "required": ["repo", "virtual_cluster_id", "job_run_id", "now"],
        },
    },
```

E os dois handlers, ao lado dos irmãos:

```python
def _h_analyze_emr_eks(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_emr_eks(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )


def _h_collect_emr_eks(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_emr_eks(
        args["repo"], args["virtual_cluster_id"], args["job_run_id"], args["now"]
    )
```

E as duas linhas no mapa de despacho (perto das linhas 5260 e 5291):

```python
    "sparkforge_analyze_emr_eks": _h_analyze_emr_eks,
    "sparkforge_collect_emr_eks": _h_collect_emr_eks,
```

- [ ] **Step 5: `cli.py`**

Depois do bloco `emrs_analyze_p` (linha ~307), o subparser de análise:

```python
    emrk_analyze_p = analyze_sub.add_parser(
        "emr-eks",
        help="Extrai facts de uma execucao Amazon EMR on EKS (describe-virtual-cluster "
        "+ describe-job-run). Descreve o que UMA execucao pediu; pod template nao e "
        "lido e o lado EKS nao existe aqui.",
    )
    emrk_analyze_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps de EMR on EKS."
    )
    emrk_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    emrk_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    emrk_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    emrk_analyze_p.add_argument("--cursor")
    _add_detail_level(emrk_analyze_p)
```

Depois do bloco `emrs_collect_p` (linha ~1268), o subparser de coleta:

```python
    emrk_collect_p = collect_sub.add_parser(
        "emr-eks",
        help="Baixa describe-virtual-cluster e describe-job-run de EMR on EKS e grava "
        "os dois no mesmo arquivo.",
    )
    emrk_collect_p.add_argument("--repo", required=True)
    emrk_collect_p.add_argument(
        "--virtual-cluster-id", required=True, help="Id do cluster virtual (`0abcXXXX`)."
    )
    emrk_collect_p.add_argument(
        "--job-run-id",
        required=True,
        help="Id da execucao. DescribeJobRun exige os DOIS ids; nome NAO serve.",
    )
    emrk_collect_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")
```

Os dois handlers, ao lado dos irmãos:

```python
def _cmd_analyze_emr_eks(args: argparse.Namespace) -> int:
    full = _core.analyze_emr_eks(args.path, kind=args.kind, limit=None)
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


def _cmd_collect_emr_eks(args: argparse.Namespace) -> int:
    _print(_core.collect_emr_eks(args.repo, args.virtual_cluster_id, args.job_run_id, args.now))
    return 0
```

E as duas entradas no mapa de despacho (perto das linhas 2217 e 2270):

```python
    ("analyze", "emr-eks"): _cmd_analyze_emr_eks,
    ("collect", "emr-eks"): _cmd_collect_emr_eks,
```

- [ ] **Step 6: Rodar paridade e ponta a ponta**

Run: `python -m pytest tests/test_cli_mcp_parity.py -q`
Expected: PASS.

Run: `python -m sparkforge.cli.forge analyze emr-eks --path fixtures/emr_eks/job_run_saudavel/input`
Expected: JSON com `by_kind` listando os seis kinds da fixture e `unresolved: 0`.

- [ ] **Step 7: Commit**

```bash
git add sparkforge/adapters/_core.py sparkforge/adapters/tools.py sparkforge/adapters/cli.py tests/test_cli_mcp_parity.py
git commit -m "feat(adapters): analyze e collect de EMR on EKS em CLI e MCP"
```

---

## Task 10: Área `SF-EMRK` — as regras que a Task 1 sustentar

**Entrada obrigatória:** `knowledge/emr-eks/job-run-configuration.md` e `runtime-matrix.md`, da Task 1. Nenhuma regra desta task se escreve sem citar uma URL que já está em `knowledge/sources.lock.json`.

**Files:**
- Create: `rules/catalog/emr-eks.yaml`
- Modify: `fixtures/emr_eks/*/meta.yaml` (campo `expects_rules`)
- Create: fixtures negativas conforme as regras que entrarem

- [ ] **Step 1: Triar as cinco candidatas contra o que a Task 1 mediu**

Para cada candidata da §5 da spec, decida e **escreva a decisão**:

**A triagem já foi feita pela Task 1** (commit `c724c80`). O resultado está nas
DV-3, DV-4 e DV-5 da spec, e é este — leia a DV correspondente antes de escrever
cada regra, porque a ressalva de cada uma muda o texto dela:

| Candidata | Veredito medido | Ressalva que entra na regra |
|---|---|---|
| segredo em claro em `applicationConfiguration` ou em `--conf` | **entra**, com fonte mais fraca que a das áreas irmãs (DV-5) | o apoio é o *Response Syntax* de `DescribeJobRun`, que devolve `properties` sem redação — **não** o *Warning* da ReleaseGuide, que é de EC2. **Não recomendar `EMR.secret@` como remédio**: não há fonte que o declare disponível aqui. Terceiro exemplar do julgamento (`SF-EMRS-002`, `SF-EMR-002`) — anote a triplicação (D-6) |
| nenhum destino de log em `monitoringConfiguration` | **entra, e mais forte que no Serverless** (DV-4) | não existe armazenamento gerenciado no EKS — `managedLogs.allowAWSToRetainLogs` cobre só *"system namespace logs when running a job using Native FGAC"*, sem default nem retenção publicados. Há `must` literal em duas páginas: *"you must configure your jobs to send log information to Amazon S3, Amazon CloudWatch Logs, or both."* A ausência do bloco **já é** zero destino |
| `persistentAppUI` desligado | **entra, só com `DISABLED` explícito** (DV-5) | o default não é publicado em lugar nenhum — API, CLI nem guia. Presumi-lo seria materializar default sem fonte |
| `dynamicAllocation` sem `shuffleTracking.enabled` | **entra como relação entre propriedades** (DV-5) | o requisito é nomeado por **composição de duas páginas**, e nenhuma o chama de defeito: `configuration.html` declara a disjunção, `running-on-kubernetes.html` a fecha (*"since Kubernetes doesn't support an external shuffle service at this time"*) — mas dentro de *Stage Level Scheduling Overview*. §16 do `CLAUDE.md`: relação entre duas propriedades é conferível, valor isolado não é. A composição fica escrita na regra |
| imagem em tag mutável | **VETADA** (DV-3) | não por falta de fonte — **por fonte que diz o oposto**. O exemplo oficial é `.../spark/emr-7.13.0:latest`, `-latest` é recomendado *"to ensure that your Amazon EMR version always includes the latest security updates"*, e as *Considerations for customizing images* têm seis itens e nenhum sobre imutabilidade de tag. A regra acusaria o que a AWS ensina |

A candidata vetada vira comentário de veto no cabeçalho de
`rules/catalog/emr-eks.yaml`, no molde dos vetos `V-GR-1`/`V-GR-2` no topo de
`rules/catalog/graph.yaml`: o que falta, e a medida que destravaria. No caso da
(e), o que "destravaria" não é medida nenhuma — é a AWS mudar de recomendação, e
o veto precisa dizer isso.

**Antes de escrever a regra (d)**, releia a página de configuração do Spark **na
versão fixada** que o repositório vigia (`docs/3.5.6/...`, `docs/4.1.1/...`), não
em `docs/latest/`. A Task 1 citou de `latest`, e o repositório fixa versão nas
fontes de Spark que sustentam regra.

- [ ] **Step 2: Escrever o cabeçalho do catálogo**

`rules/catalog/emr-eks.yaml` começa com o bloco de metadados no formato que `rules/catalog/emr-serverless.yaml` usa (leia as linhas 1–242 dele antes de escrever), com `area: SF-EMRK`, os vetos do Step 1, e este comentário literal:

```yaml
# `runtime_scope` -- RESOLVIDO pela Task 1 (commit c724c80), ver DV-1 e DV-2.
# A AWS PUBLICA matriz de release para EMR on EKS. Regra desta area PODE
# restringir por versao de `spark`.
# NAO PODE restringir por `iceberg`: a linha `Supported applications` e publicada
# por FAMILIA e nao por variante, e `emr-7.7.0-java8-latest` nao tem Iceberg
# ("Iceberg is excluded from the following Java 8 images"). Derivar `iceberg` do
# release label erraria exatamente nas imagens Java 8.
# NAO PODE restringir por `python` nem `hadoop`: 2 de 34 paginas declaram Python,
# em prosa e nao em tabela; 0 de 34 declaram Hadoop.
# A EMR_MATRIX de EMR on EC2 nao entra aqui em hipotese nenhuma, e a razao ficou
# MAIS forte que a da D-4 original: ela nao e inaplicavel por falta de fonte como
# no Serverless -- ela e MEDIDAMENTE ERRADA aqui. Iceberg diverge em 6 de 26
# releases comparaveis e Spark em 4; `emr-7.7.0` roda Iceberg 1.6.1-amzn-2 no EKS
# e 1.7.1-amzn-0 no EC2, que e MINOR diferente.
```

- [ ] **Step 3: Escrever cada regra que passou na triagem**

Cada uma preenche **todos** estes campos — sem exceção, e nenhum deles é opcional neste catálogo:

```yaml
  - id: SF-EMRK-00N
    category: emr-eks
    title: <o achado, não o sintoma>
    requires_facts: [<kinds emrc.* que a condição lê>]
    when:
      all:
        - fact: <kind>
          where: {<attrs.campo>: <valor>}     # ou `expr:` para measure
    status: confirmed
    severity_default: <P0|P1|P2>
    runtime_scope: <decidido no Step 2>
    explanation: >
      <prosa citando knowledge/emr-eks/*.md por seção, e declarando o limite:
       este fact descreve o que UMA execução pediu, não o que o pod recebeu>
    proposed_change: [<ações concretas>]
    risks: [<o que a mudança pode quebrar>]
    tradeoffs: [<o que se perde ao aplicar>]
    validation: [<como conferir que resolveu — eixo de resultado obrigatório>]
    rollback: [<como desfazer, e o que não volta>]
    sources:
      - {url: "<URL que já está em sources.lock.json>", retrieved: 2026-08-31}
```

Para a regra de destino de log, o `where` é `{attrs.monitoring_declared: false}` **ou** o `expr` `measures.log_destination_count == 0` — prefira o `expr`, porque cobre também o bloco declarado e vazio.

- [ ] **Step 4: Fixture positiva e negativa por regra**

Para cada regra que entrou, garanta o par. `sem_destino_de_log` já é o positivo da regra de log e `job_run_saudavel` é o negativo. Para a regra de segredo, crie `fixtures/emr_eks/segredo_em_conf/` — igual a `job_run_saudavel`, com uma propriedade cujo **valor** dispare o detector, e com `expects_rules: [SF-EMRK-00N]`.

Atualize o `expects_rules` de cada `meta.yaml` afetado.

- [ ] **Step 5: Regenerar e ler o diff**

Run: `python scripts/regen_fixtures.py` (só as fixtures de `emr_eks/`, nomeando-as)
Run: `git diff fixtures/emr_eks/*/expected/findings.json`

Confira que `job_run_saudavel` continua com `findings: []`. Se alguma regra disparar ali, ela acusa configuração correta — pare e conserte a regra, não a fixture.

- [ ] **Step 6: Rodar os gates de catálogo**

Run: `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_rules_result_axis.py tests/test_rules_catalog_reachability.py -q`
Expected: PASS. Toda regra tem golden que a dispara, todo ramo de severidade tem golden que o produz, e toda regra tem eixo de resultado no `validation`.

- [ ] **Step 7: Commit**

```bash
git add rules/catalog/emr-eks.yaml fixtures/emr_eks/
git commit -m "feat(rules): area SF-EMRK, com o veto escrito para cada candidata sem fonte"
```

---

## Task 11: Roteamento, coordenador e skill

**Files:**
- Modify: `rules/catalog/routing.yaml` (regra `AGENT-007`, linha ~406)
- Modify: `agents/emr-infra-reviewer.md` (frontmatter + corpo)
- Create: `skills/review-emr-eks/SKILL.md`
- Modify: `parity.yaml`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_agent_coverage.py`:

```python
def test_sf_emrk_tem_coordenador_e_rota():
    from sparkforge.rules.loader import load_catalog

    catalogo = load_catalog()
    areas = {r.id.rsplit("-", 1)[0].replace("SF-", "SF-") for r in catalogo.rules}
    assert any(r.id.startswith("SF-EMRK-") for r in catalogo.rules)

    rota = next(r for r in catalogo.routes if r.id == "AGENT-007")
    condicoes = {c["findings_area"] for c in rota.when["any"]}
    assert condicoes == {"SF-EMR", "SF-EMRS", "SF-EMRK"}
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python -m pytest tests/test_agent_coverage.py -q -k emrk`
Expected: FAIL — o conjunto tem duas áreas, não três.

- [ ] **Step 3: Roteamento**

Em `rules/catalog/routing.yaml`, na regra `AGENT-007`, acrescente a terceira condição e o comentário:

```yaml
      # `SF-EMRK` entra AQUI pela MESMA razão que `SF-EMRS` entrou na Fase 5d, e o
      # precedente esta escrito acima: `all:` com uma condição já virou `any:` com
      # duas porque um case só de Serverless voltava de `next_step` com
      # `recommended_agent: None`. Um case só de EMR on EKS teria o mesmo destino
      # sem esta linha. O agente é o mesmo, então não há pergunta de precedência
      # dentro desta rota.
        - {findings_area: SF-EMRK, count_gt: 0}
```

E acrescente ao `reason` da rota, ao fim do período sobre Serverless: `; cluster virtual, papel de execução por job run e destino de log por execução no EMR on EKS, onde não há armazenamento gerenciado e a ausência do bloco já é ausência de log.`

- [ ] **Step 4: Coordenador**

Em `agents/emr-infra-reviewer.md`, no frontmatter:

```yaml
rule_areas: [SF-EMR, SF-EMRS, SF-EMRK, SF-ENV]
skills:
  - review-emr-cluster
  - review-emr-eks
  - analyze-spark-ui
  - benchmark-pyspark-job
```

E acrescente à `description`, ao fim: `; EMR on EKS com cluster virtual, namespace, papel de execucao, as duas superficies de configuracao do job run e destino de log por execucao.`

No corpo, na seção *Quando você entra*, acrescente um parágrafo dizendo que EMR on EKS entra por artefato de `emr-containers`, e que capacidade de nó, pod pendente e pod template **não** são julgados por nenhuma regra desta área.

- [ ] **Step 5: Skill**

Crie `skills/review-emr-eks/SKILL.md` no formato de `skills/review-emr-cluster/SKILL.md` (leia-o antes). Abra com a fronteira, não com a capacidade:

```markdown
## O que esta skill NÃO julga

Três coisas, e nomeá-las é o que separa "não achei problema" de "não olhei":

1. **Capacidade de nó e pod pendente.** Nodegroup, Karpenter, Cluster Autoscaler
   e `capacityType` são do EKS, não do `emr-containers`. Nenhum achado desta
   skill pode dizer que o pod ficou pendente por falta de nó.
2. **Pod template.** `spark.kubernetes.driver.podTemplateFile` sai como
   `emrc.pod_template.unresolved` com o path: você vê que existe e que não foi
   lido. `nodeSelector`, `tolerations` e `resources` moram lá.
3. **O que o pod recebeu.** `DescribeJobRun` diz o que UMA execução pediu.
```

- [ ] **Step 6: Sincronizar skills e paridade**

Run: `python scripts/sync_skills.py`
Run: `python -m pytest tests/test_sync_render.py tests/test_agent_coverage.py -q`
Expected: PASS. Se `test_sync_render.py` cobrar entrada em `RELACAO_MEDIDA`, acrescente-a **na declaração do dicionário**, não num `update()` — o `STATUS.md` registra que o `update()` no meio do arquivo deixa seis chaves com valor morto.

- [ ] **Step 7: Commit**

```bash
git add rules/catalog/routing.yaml agents/emr-infra-reviewer.md skills/review-emr-eks/ .agents/skills/ .claude/skills/ parity.yaml tests/test_agent_coverage.py
git commit -m "feat(agents): SF-EMRK alcancavel, e a skill que declara o que nao julga"
```

---

## Task 12: Fronteira em três direções, locks e fechamento

**Files:**
- Create: `tests/test_emr_eks_area_boundary.py`
- Modify: `docs/surface.lock.json` (via script)
- Modify: `docs/superpowers/STATUS.md`
- Modify: `README.md`

- [ ] **Step 1: Escrever o teste de fronteira**

Crie `tests/test_emr_eks_area_boundary.py`:

```python
"""A fronteira entre as TRES areas de EMR, medida e nao afirmada.

Duas direcoes bastavam com duas plataformas. Com tres, sao seis pares, e o par
que mais importa e o novo: uma regra SF-EMR ou SF-EMRS disparando sobre artefato
de EKS produziria um achado com vocabulario de outra plataforma sobre uma
configuracao que talvez esteja correta.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def _facts_de(dominio: str, fixture: str) -> list:
    caminho = ROOT / "fixtures" / dominio / fixture / "expected" / "facts.json"
    from sparkforge.findings.models import Fact

    return [Fact(**item) for item in json.loads(caminho.read_text(encoding="utf-8"))]


def _areas_disparadas(facts: list) -> set[str]:
    achados = judge(facts, load_catalog(), runtime={})
    return {f.rule_id.rsplit("-", 1)[0] for f in achados}


@pytest.mark.parametrize(
    "dominio,fixture",
    [("emr", "cluster_saudavel"), ("emr_serverless", "app_saudavel")],
)
def test_nenhuma_regra_de_eks_dispara_sobre_as_outras_plataformas(dominio, fixture):
    assert "SF-EMRK" not in _areas_disparadas(_facts_de(dominio, fixture))


@pytest.mark.parametrize("fixture", ["job_run_saudavel", "sem_destino_de_log"])
def test_nenhuma_regra_de_ec2_ou_serverless_dispara_sobre_eks(fixture):
    areas = _areas_disparadas(_facts_de("emr_eks", fixture))
    assert "SF-EMR" not in areas
    assert "SF-EMRS" not in areas


def test_judge_nao_deriva_runtime_de_eks_da_matriz_de_ec2():
    """O contrafactual da divida aberta que o STATUS.md registra.

    `judge --emr 7.5.0` sobre facts de EMR Serverless grava `spark`, `python` e
    `iceberg` derivados da EMR_MATRIX de EMR on EC2 -- tres campos inventados
    sobre um artefato que nao declara nenhum deles. Este teste garante que a
    terceira plataforma nao repete o erro.
    """
    from sparkforge.adapters import _core

    facts = _facts_de("emr_eks", "job_run_saudavel")
    resultado = _core.judge_facts(facts, emr="7.5.0")
    contexto = resultado["runtime"]
    assert "python" not in contexto
    assert "iceberg" not in contexto
```

Se `_core.judge_facts` tiver outra assinatura, use a real — ela está no mesmo arquivo que `analyze_emr_eks`; o que o teste precisa provar é que passar `--emr` junto de facts `emrc.*` não enche eixos que a matriz de EKS não sustenta.

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/test_emr_eks_area_boundary.py -q`
Expected: PASS. Se o último falhar, o conserto é no `_core`, não no teste: recusar `--emr` quando o conjunto tem fact `emrc.*`, ou derivar só o que a matriz de EKS publica.

- [ ] **Step 3: Declarar o crescimento da superfície**

Run: `python scripts/check_surface_lock.py --update`
Run: `git diff docs/surface.lock.json`

Anote o número: duas tools, uma skill e dois documentos de `knowledge/`. O crescimento vai no corpo do commit desta task.

- [ ] **Step 4: Rodar a suíte em seis lotes**

Rode um lote por vez, nesta ordem, e **não edite a árvore enquanto rodam**:

```bash
python -m pytest $(ls tests/test_[a-c]*.py) -q
python -m pytest $(ls tests/test_[d-e]*.py) -q
python -m pytest $(ls tests/test_f*.py | grep -v golden) -q
python -m pytest $(ls tests/test_fixtures_golden_*.py | head -n 5) -q
python -m pytest $(ls tests/test_fixtures_golden_*.py | tail -n +6) -q
python -m pytest $(ls tests/test_[g-z]*.py) -q
```

Expected: todos passam. O total sobe de 6716 pelo número de testes que esta fase acrescentou — meça, não copie.

- [ ] **Step 5: Atualizar `STATUS.md`**

Acrescente uma seção nova ao fim das fases, no formato das seções irmãs, com: o que entrou, o número **medido** de regras que entraram (e quais candidatas ficaram de fora, com o veto), o número medido de fixtures e de testes, e — obrigatoriamente — as linhas novas de dívida ou limite declarado que a implementação mediu.

Atualize os *Números correntes*: extratores (27 → 28), fact kinds distintos (158 → medido), regras de diagnóstico, tools MCP (59 → 61), skills (44 → 45), fixtures (194 → medido), rotas, e fontes vigiadas. **Meça cada um; não some o que esta seção escreveu.**

Feche a linha que a Fase 5d encolheu: "EMR Serverless e EMR on EKS" já nomeava só EKS, e agora fecha.

- [ ] **Step 6: `README.md`**

Acrescente `analyze emr-eks` e `collect emr-eks` à tabela de comandos, e `review-emr-eks` à lista de skills, nos mesmos lugares onde os equivalentes de Serverless aparecem.

- [ ] **Step 7: Commit**

```bash
git add tests/test_emr_eks_area_boundary.py docs/surface.lock.json docs/superpowers/STATUS.md README.md
git commit -m "test: a fronteira das tres plataformas de EMR, medida em seis pares"
```

---

## Auto-revisão do plano

**Cobertura da spec**, seção a seção:

| Spec | Task |
|---|---|
| §2 não-objetivos (pod template, EKS, Terraform, histórico) | 6 (recusa visível), 8 (docstring do coletor), 11 (skill declara) |
| §3 D-1 área nova + coordenador estendido | 10, 11 |
| §3 D-2 namespace `emrc.` | 2 |
| §3 D-3 duas superfícies separadas | 4, 5 |
| §3 D-4 release não deriva de EC2 | 1 (bifurcação), 7 (`meta.yaml`), 10 (cabeçalho), 12 (contrafactual) |
| §3 D-5 candidata sem fonte não vira regra | 1, 10 Step 1 |
| §3 D-6 overlap medido | 10 Step 1 e Step 3 |
| §4 os oito kinds | 2, 3, 4, 5, 6 |
| §5 cinco candidatas | 10 |
| §6 superfície | 8, 9, 11 |
| §7 pesquisa | 1 |
| §8 testes e gates | 7, 10, 11, 12 |
| §9 critérios de conclusão | 12 |

Nenhuma lacuna.

**Consistência de nomes** entre tasks: `EMITTED_KINDS`, `EXTRACTOR_ID`, `_file_subject`, `_as_str`, `_unresolved`, `_finish`, `extract_emr_eks`, `extract_emr_eks_path`, `extract_emr_eks_tree`, `emr_eks_path`, `collect_emr_eks`, `_extract_emr_eks_facts`, `analyze_emr_eks` — cada um definido uma vez e usado com a mesma assinatura depois. `surface` é `"spark_submit_parameters"` na Task 4 e `"application_configuration"` na Task 5, e a Task 6 lê os dois valores.

**O que este plano deliberadamente NÃO fixa:** o número de regras da Task 10 e o valor de `runtime_scope`. Os dois saem da Task 1, por decisão registrada na §D-4 e §D-5 da spec — e a Task 10 Step 1 dá a tabela de decisão para que a triagem seja mecânica, não opinião.
