"""Extrator de Facts a partir de uma execucao Amazon EMR on EKS (`emr-containers`,
`DescribeJobRun`).

Como `emr_cluster.py`/`emr_serverless.py`, este modulo NAO coleta nada: le o
JSON ja salvo em disco, em camelCase, sem traducao. Nunca levanta excecao por
payload malformado -- o que nao consegue ler vira `emrc.unresolved` CONTADO, e
a sentinela `emrc.analyzed` sai sempre, inclusive quando nada pode ser lido.

## Por que `emrc.` e nao `emr.eks.` nem `emrk.`

`emrc` vem de `emr-containers`, o nome do servico na API e no CLI
(`aws emr-containers describe-job-run`). Prefixo de kind e fronteira de
namespace verificada por `EMITTED_KINDS`, e um prefixo que e sub-caminho de
outro (`emr.` de `emr.eks.`) transforma toda checagem de pertencimento em
comparacao de string com armadilha: `kind.startswith("emr.")` casaria
`emr.cluster.foo` E `emr.eks.foo`, quando os dois modulos sao independentes.
A area de regra, essa, e `SF-EMRK` -- `SF-EMRC` colidiria visualmente com
`SF-EMR` numa lista de findings, e as duas areas nao tem nada em comum alem da
letra inicial.

## O limite que vale para TODOS os facts deste modulo

`DescribeJobRun` devolve o que UMA execucao PEDIU, nao o que o cluster virtual
oferece nem o que o pod efetivamente recebeu. Duas coisas ficam fora por
construcao:

(a) **O pod template nao e lido.** `spark.kubernetes.driver.podTemplateFile`
(e o par `executor.podTemplateFile`) aponta para um YAML quase sempre em S3, e
resolver path->conteudo e mecanismo que NENHUM extrator deste repositorio tem
-- ele exigiria uma segunda chamada de coleta (`GetObject`) que este modulo
nao faz. O path sai como `emrc.pod_template.unresolved` na Task 6.
`nodeSelector`, `tolerations` e `resources` moram DENTRO do template, entao
tambem ficam fora daqui.

(b) **O lado EKS nao existe aqui.** Nodegroup, Karpenter, capacidade de no e
pod pendente sao outro servico (`eks`/`ec2`), outro IAM e outra matriz de
versao. Um achado desta area NUNCA pode dizer "o pod ficou pendente por falta
de no" -- essa afirmacao exigiria fact de um extrator que este pacote ainda
nao tem.

## Shape esperado do payload

Um arquivo por execucao, com as DUAS respostas sob chaves de topo
`virtualCluster` e `jobRun` -- mesma decisao de `emr_cluster.py`, que junta
`describe-cluster` e cinco listagens num arquivo so:

```json
{
  "virtualCluster": {
    "id": "abcdef0123456789abcdef0123456789",
    "name": "meu-cluster",
    "state": "RUNNING",
    "containerProvider": {
      "type": "EKS",
      "id": "meu-cluster-eks",
      "info": {"eksInfo": {"namespace": "spark-jobs"}}
    }
  },
  "jobRun": {
    "id": "0000000abc123def4",
    "name": "etl-diario",
    "virtualClusterId": "abcdef0123456789abcdef0123456789",
    "state": "COMPLETED",
    "releaseLabel": "emr-7.5.0-latest",
    "jobDriver": {
      "sparkSubmitJobDriver": {
        "entryPoint": "s3://bucket/scripts/etl.py",
        "sparkSubmitParameters": "--conf spark.executor.cores=4"
      }
    },
    "configurationOverrides": {
      "applicationConfiguration": [
        {"classification": "spark-defaults", "properties": {"spark.executor.cores": "4"}}
      ],
      "monitoringConfiguration": {
        "persistentAppUI": "ENABLED",
        "cloudWatchMonitoringConfiguration": {"logGroupName": "/emr-containers/etl"}
      }
    }
  }
}
```

Como os demais extratores: puro e deterministico. Nunca aplica limiar, nunca
atribui severidade, nunca infere o que o payload nao diz.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
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

# Corpus medido na Task 1 (`knowledge/emr-eks/runtime-matrix.md`, secao sobre a
# forma do release label). A regex precisa CASAR os quatro primeiros e
# REJEITAR os dois ultimos:
#
#   emr-7.5.0-latest                          -> casa (sufixo de canal)
#   emr-7.7.0-java8-latest                     -> casa (DOIS segmentos de sufixo)
#   emr-7.7.0-spark-rapids-java8-latest        -> casa (TRES segmentos de sufixo)
#   emr-6.15.0                                 -> casa (sem sufixo)
#   emr-spark-8.0.0-latest                     -> NAO casa (nao e `emr-<major>.<minor>`)
#   notebook-spark/emr-7.13.0-latest           -> NAO casa (prefixado)
#
# `^emr-` ancorado impede o prefixo `notebook-spark/emr-...` de casar; exigir
# digito IMEDIATAMENTE apos `emr-` impede `emr-spark-8.0.0-...` de casar, pois
# "spark" nao e digito. O sufixo, quando existe, e `(?:-.+)?` -- qualquer
# numero de segmentos separados por hifen, sem validar o vocabulario deles: a
# Task 1 mediu `-latest`, `-yyyymmdd`, `-spark-rapids`, `-java8`, `-java11`,
# `-java17`, `-al2023` e os prefixos `notebook-spark/`, `notebook-python/`,
# `livy/`, e declarou essa lista NAO fechada. O par (major, minor) extraido
# NUNCA inclui o sufixo: o sufixo nomeia o canal ou a variante, nao a versao.
_RELEASE_RE = re.compile(r"^emr-(\d+)\.(\d+)\.\d+(?:-.+)?$", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# helpers de forma -- mesma convencao de `emr_serverless.py`
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# facts de conteudo -- Task 3 (virtual cluster e job run)
# --------------------------------------------------------------------------- #


def _release_numbers(label: str | None) -> tuple[int | None, int | None]:
    """Extrai (major, minor) de um release label no formato `emr-<major>.<minor>.<patch>`.

    O par sai como MEASURE, nao attr: uma regra do catalogo pergunta "serie
    7.x?" com um operador numerico, e o avaliador de expressoes do catalogo
    nao tem comparacao de string -- so measure sustenta esse tipo de condicao.
    Isso tambem evita depender de deteccao de runtime: o proprio payload prova
    a release. Formas fora do padrao (`emr-spark-8.0.0-latest`,
    `notebook-spark/emr-7.13.0-latest`, `custom-build`) devolvem `(None, None)`
    em vez de inventar um par. O sufixo, quando existe (`-latest`, `-java8`,
    `-spark-rapids-java8-latest`), NUNCA entra no par: ele nomeia o canal de
    distribuicao ou a variante de imagem, nao a versao.
    """
    if label is None:
        return None, None
    match = _RELEASE_RE.match(label)
    if match is None:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _virtual_cluster_fact(raw: Any, path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Constroi o fact `emrc.virtual_cluster` a partir do bloco `virtualCluster`.

    Bloco ausente (`None`) devolve lista vazia -- e isso NAO e erro: as duas
    respostas (`DescribeVirtualCluster` e `DescribeJobRun`) vem de chamadas
    separadas, e o operador pode ter trazido so uma. Bloco presente mas de
    tipo errado vira `emrc.unresolved` com `section="virtualCluster"`. `id`
    ausente vira `emrc.unresolved` com reason `"missing_virtual_cluster_id"`,
    porque e a chave de ancoragem do fact.
    """
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return [_unresolved(path, "malformed_json", provenance, section="virtualCluster")]

    virtual_cluster_id = _as_str(raw.get("id"))
    if virtual_cluster_id is None:
        return [_unresolved(path, "missing_virtual_cluster_id", provenance)]

    attrs: dict[str, Any] = {"virtual_cluster_id": virtual_cluster_id}

    name = _as_str(raw.get("name"))
    if name is not None:
        attrs["name"] = name

    state = _as_str(raw.get("state"))
    if state is not None:
        attrs["state"] = state

    # Guarda de tipo em cada nivel de aninhamento: `containerProvider`,
    # `info` e `eksInfo` podem vir com o tipo errado (ou ausentes) sem que
    # isso derrube a leitura das chaves de nivel mais alto.
    container_provider = raw.get("containerProvider")
    if isinstance(container_provider, dict):
        provider_type = _as_str(container_provider.get("type"))
        if provider_type is not None:
            attrs["container_provider_type"] = provider_type

        eks_cluster_name = _as_str(container_provider.get("id"))
        if eks_cluster_name is not None:
            attrs["eks_cluster_name"] = eks_cluster_name

        info = container_provider.get("info")
        if isinstance(info, dict):
            eks_info = info.get("eksInfo")
            if isinstance(eks_info, dict):
                namespace = _as_str(eks_info.get("namespace"))
                if namespace is not None:
                    attrs["namespace"] = namespace

    return [
        Fact(
            kind="emrc.virtual_cluster",
            subject=_file_subject(path),
            attrs=attrs,
            provenance=provenance,
        )
    ]


def _job_run_fact(
    raw: dict[str, Any], job_run_id: str, path: str, provenance: dict[str, Any]
) -> Fact:
    """Constroi o fact `emrc.job_run` a partir do bloco `jobRun`.

    `job_run_id` e obrigatorio (ja validado por quem chama). As demais chaves
    de `attrs` e as duas measures de release entram SO quando o valor
    correspondente existe e e legivel -- chave ausente do payload fica
    OMITIDA do fact, nunca escrita como `None`: o avaliador de regras rejeita
    caminho ausente, e e assim que o motor diz "nao sei". Escrever `None`
    diria "sei que nao ha", que e uma afirmacao diferente e mais forte do que
    o payload sustenta.
    """
    attrs: dict[str, Any] = {"job_run_id": job_run_id}

    name = _as_str(raw.get("name"))
    if name is not None:
        attrs["name"] = name

    virtual_cluster_id = _as_str(raw.get("virtualClusterId"))
    if virtual_cluster_id is not None:
        attrs["virtual_cluster_id"] = virtual_cluster_id

    state = _as_str(raw.get("state"))
    if state is not None:
        attrs["state"] = state

    release_label = _as_str(raw.get("releaseLabel"))
    if release_label is not None:
        attrs["release_label"] = release_label

    execution_role_arn = _as_str(raw.get("executionRoleArn"))
    if execution_role_arn is not None:
        attrs["execution_role_arn"] = execution_role_arn

    failure_reason = _as_str(raw.get("failureReason"))
    if failure_reason is not None:
        attrs["failure_reason"] = failure_reason

    measures: dict[str, Any] = {}
    release_major, release_minor = _release_numbers(release_label)
    # So entra measure quando os DOIS numeros existem -- release fora da
    # forma nao produz measure nenhuma, em vez de inventar um par parcial.
    if release_major is not None and release_minor is not None:
        measures["release_major"] = release_major
        measures["release_minor"] = release_minor

    return Fact(
        kind="emrc.job_run",
        subject=_file_subject(path),
        attrs=attrs,
        measures=measures,
        provenance=provenance,
    )


# --------------------------------------------------------------------------- #
# entrada
# --------------------------------------------------------------------------- #


def extract_emr_eks(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado (`dict`) de `DescribeJobRun`
    (mais `DescribeVirtualCluster`, sob a mesma chave de topo).

    Esqueleto: so os caminhos de FALHA estao implementados aqui -- os facts de
    conteudo (virtual cluster, job run, configuracao, monitoring, pod
    template) sao as Tasks 3 a 6. Nunca levanta excecao por payload
    malformado: chave ausente, secao com o tipo errado -- tudo vira
    `emrc.unresolved` e a extracao segue com o que sobrar, mesma convencao de
    `emr_cluster.extract_emr_cluster` e `emr_serverless.extract_emr_serverless`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
        return _finish(facts, path, provenance)

    raw = payload.get("jobRun")
    if raw is None:
        # Sem `DescribeJobRun` nao ha release label, nem identidade de
        # execucao, nem configuracao efetiva para ancorar os demais facts. O
        # operador precisa saber QUAL comando falta -- `virtualCluster` sozinho
        # descreve o cluster, nao a execucao que o achado precisa julgar.
        facts.append(_unresolved(path, "missing_job_run", provenance))
        return _finish(facts, path, provenance)
    if not isinstance(raw, dict):
        facts.append(_unresolved(path, "malformed_json", provenance, section="jobRun"))
        return _finish(facts, path, provenance)

    job_run_id = _as_str(raw.get("id"))
    if job_run_id is None:
        # Toda entidade deste extrator (Tasks 3-6) e ancorada em
        # `<job_run_id>/...`. Sem o id, dois payloads diferentes colidiriam no
        # mesmo subject e um substituiria o outro no relatorio.
        facts.append(_unresolved(path, "missing_job_run_id", provenance))
        return _finish(facts, path, provenance)

    # Task 3: virtual cluster e job run. As Tasks 4 a 6 acrescentam os quatro
    # kinds restantes (spark_submit_parameters, configuration, monitoring,
    # pod_template.unresolved) neste mesmo ponto.
    facts.extend(_virtual_cluster_fact(payload.get("virtualCluster"), path, provenance))
    facts.append(_job_run_fact(raw, job_run_id, path, provenance))

    return _finish(facts, path, provenance)


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho para todos
    os caminhos de saida, inclusive os que abortam cedo."""
    counts = {
        "virtual_cluster_count": sum(1 for f in facts if f.kind == "emrc.virtual_cluster"),
        "job_run_count": sum(1 for f in facts if f.kind == "emrc.job_run"),
        "configuration_count": sum(1 for f in facts if f.kind == "emrc.configuration"),
        "conf_parameter_count": sum(
            1 for f in facts if f.kind == "emrc.spark_submit_parameters"
        ),
        "unresolved_count": sum(1 for f in facts if f.kind == "emrc.unresolved"),
    }
    # Sentinela: prova de que a extracao rodou sobre ESTE payload. Sem ela,
    # uma condicao `absent:` sobre fact de EMR on EKS seria vacuamente
    # verdadeira quando o extrator nunca rodou. Subject de ARQUIVO, nao de job
    # run: ela fala do payload, e existe mesmo quando nenhum job run pode ser
    # lido.
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


def extract_emr_eks_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `emrc.unresolved` com reason "read_error"; JSON
    invalido vira "malformed_json". Nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty_provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return _finish(
            [_unresolved(anchor, "read_error", empty_provenance, detail=str(exc))],
            anchor,
            empty_provenance,
        )

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _finish([_unresolved(anchor, "malformed_json", provenance)], anchor, provenance)

    return extract_emr_eks(parsed, anchor, artifact_sha256=sha)


def extract_emr_eks_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico vira
    `emrc.unresolved` para aquele arquivo e a travessia continua.
    """
    facts: list[Fact] = []
    for json_file in iter_source_files(root, "*.json"):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_emr_eks_path(json_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
            facts.append(_unresolved(anchor, "read_error", provenance, detail=str(exc)))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_emr_eks",
    "extract_emr_eks_path",
    "extract_emr_eks_tree",
]
