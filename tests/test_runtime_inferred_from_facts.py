"""O runtime sai dos FACTS, nao so das flags que alguem digitou.

A maquina de deteccao (`sparkforge/facts/runtime_detect.py`) sempre soube
resolver precedencia, derivar `GLUE_MATRIX` e reportar divergencia. Ela so
nunca era alimentada: `build_runtime_context` montava `{"cli": ...}` e nada
mais. Como `in_scope` falha fechada -- chave ausente ou vazia reprova a regra
--, as 8 regras que ainda guardam versao (`SF-ENV-002`, `SF-ENV-003`,
`SF-GLUE-001..006`) so avaliavam se o operador soubesse e digitasse a versao do
Glue. Um `sparkforge judge` sobre um repositorio Terraform inteiro, sem flag,
pulava as 8 em silencio -- e para um agente autonomo silencio le como "nada
encontrado".

Este arquivo trava o invariante nos dois sentidos: com fact que carrega versao,
as 8 avaliam sem flag nenhuma; sem fact que carregue versao, as 8 continuam
sendo puladas com motivo VISIVEL (`reason: runtime_scope` em
`judge --show-skipped`), porque adivinhar versao seria pior que nao ter.
"""

import json

import pytest

from sparkforge.adapters import _core
from sparkforge.facts.runtime_detect import GLUE_MATRIX

# As 8 regras que ainda declaram `runtime_scope` nao-vazio, todas guardadas por
# `glue`. Lista literal de proposito: derivar do catalogo faria o teste
# concordar com qualquer coisa que o catalogo virasse, inclusive com o catalogo
# perdendo o guarda por acidente. Se esta lista divergir do catalogo, o primeiro
# teste abaixo falha e diz qual dos dois mudou.
GLUE_GUARDED_RULES = (
    "SF-ENV-002",
    "SF-ENV-003",
    "SF-GLUE-001",
    "SF-GLUE-002",
    "SF-GLUE-003",
    "SF-GLUE-004",
    "SF-GLUE-005",
    "SF-GLUE-006",
)

# `ids=` precomputado, NUNCA `ids=lambda`: com lista vazia o pytest 8.x aborta a
# coleta da suite inteira em vez de reportar um teste vazio. Ja aconteceu neste
# repositorio.
GLUE_GUARDED_IDS = list(GLUE_GUARDED_RULES)

# Terraform de um job Glue plausivel de producao. `glue_version` literal na raiz
# do recurso e a UNICA coisa que este arquivo precisa provar; o resto existe
# para o recurso ser um `aws_glue_job` real e nao um esqueleto.
GLUE_JOB_TF = """
resource "aws_glue_job" "etl" {
  name              = "etl-diario"
  glue_version      = "5.1"
  worker_type       = "G.1X"
  number_of_workers = 10
  role_arn          = "arn:aws:iam::123456789012:role/glue"

  command {
    script_location = "s3://bucket/scripts/etl.py"
  }

  default_arguments = {
    "--enable-spark-ui"        = "true"
    "--spark-event-logs-path"  = "s3://bucket/sparkui/"
    "--job-bookmark-option"    = "job-bookmark-disable"
  }
}
"""

# O mesmo job, com a versao vindo de uma variavel. O extrator registra o TEXTO
# da referencia (`var.glue_version`) com `literal: false` -- e texto de
# referencia nao e versao observada.
GLUE_JOB_TF_VAR = GLUE_JOB_TF.replace('glue_version      = "5.1"', "glue_version      = var.gv")

# Um event log minimo: `SparkListenerLogStart` e a primeira linha de todo event
# log moderno e a leitura mais confiavel da versao, porque nao e uma propriedade
# que o job possa definir.
EVENT_LOG_JSONL = "\n".join(
    [
        json.dumps({"Event": "SparkListenerLogStart", "Spark Version": "3.5.4-amzn-0"}),
        json.dumps(
            {
                "Event": "SparkListenerApplicationStart",
                "App Name": "etl",
                "App ID": "app-20260801-0001",
                "Timestamp": 1,
            }
        ),
        json.dumps({"Event": "SparkListenerApplicationEnd", "Timestamp": 2}),
    ]
)

# PySpark sem nenhuma pista de versao. Existe para provar a fronteira negativa:
# `df.coalesce(1)` nao autoriza ninguem a afirmar qual Spark roda isso.
PYSPARK_NO_VERSION = """
def run(spark):
    df = spark.read.parquet("s3://bucket/in/")
    df.coalesce(1).write.parquet("s3://bucket/out/")
"""


def _write(tmp_path, name: str, text: str):
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def _facts_file(tmp_path, name: str, facts) -> str:
    path = tmp_path / name
    path.write_text(
        json.dumps([f.to_dict() for f in facts], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return str(path)


def _terraform_facts(tmp_path, body: str = GLUE_JOB_TF):
    from sparkforge.facts.terraform import extract_terraform_tree

    infra = tmp_path / "infra"
    _write(infra, "glue.tf", body)
    return extract_terraform_tree(infra, repo_root=tmp_path)


def _event_log_facts(tmp_path, text: str = EVENT_LOG_JSONL):
    from sparkforge.facts.event_log import extract_event_log_path

    log = _write(tmp_path, "logs/app.jsonl", text)
    return extract_event_log_path(log, repo_root=tmp_path)


def _pyspark_facts(tmp_path):
    from sparkforge.facts.pyspark_ast import extract_tree

    src = tmp_path / "src"
    _write(src, "job.py", PYSPARK_NO_VERSION)
    return extract_tree(src, repo_root=tmp_path)


def _skipped_for_scope(payload) -> set[str]:
    return {
        entry["rule_id"] for entry in payload["skipped"] if entry["reason"] == "runtime_scope"
    }


# --------------------------------------------------------------------------- #
# 1. Terraform observou a versao -> as 8 avaliam, sem flag nenhuma
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("rule_id", GLUE_GUARDED_RULES, ids=GLUE_GUARDED_IDS)
def test_terraform_glue_version_puts_a_glue_guarded_rule_in_scope_without_any_flag(
    tmp_path, rule_id
):
    """`judge --facts <terraform>` e SO isso -- nenhuma `--glue`."""
    facts_path = _facts_file(tmp_path, "facts.json", _terraform_facts(tmp_path))
    payload = _core.judge_findings(facts_path=facts_path, limit=None, show_skipped=True)

    assert rule_id not in _skipped_for_scope(payload), (
        f"{rule_id} foi pulada por runtime_scope mesmo com glue_version=5.1 observado no "
        f"Terraform. runtime detectado: {payload['runtime']}"
    )


def test_the_catalog_still_guards_exactly_the_eight_rules_this_file_names(tmp_path):
    """Se o catalogo ganhar ou perder um guarda de versao, este arquivo mente.

    Sem esta trava, um `runtime_scope` novo entraria sem cobertura e um
    removido deixaria o teste acima verde por vacuidade.
    """
    from sparkforge.rules.loader import load_catalog

    guarded = {r["id"] for r in load_catalog() if r.get("runtime_scope")}
    assert guarded == set(GLUE_GUARDED_RULES)


def test_glue_version_from_terraform_alone_fills_the_whole_matrix(tmp_path):
    """`GLUE_MATRIX` faz o resto: ninguem digitou spark, python nem iceberg."""
    context = _core.build_runtime_context(facts=list(_terraform_facts(tmp_path)))

    expected = GLUE_MATRIX["5.1"]
    assert context.glue == "5.1"
    assert context.spark == expected["spark"]
    assert context.python == expected["python"]
    assert context.iceberg == expected["iceberg"]
    assert context.detected_from == ["terraform"]
    assert context.divergences == []


# --------------------------------------------------------------------------- #
# 2. Event log observou a versao do Spark
# --------------------------------------------------------------------------- #


def test_event_log_runtime_version_fills_spark_in_the_context(tmp_path):
    context = _core.build_runtime_context(facts=list(_event_log_facts(tmp_path)))

    assert context.spark == "3.5.4-amzn-0"
    assert context.detected_from == ["event_log"]
    # Nao inventa Glue: o event log observou Spark, e so. Sem `glue_version`,
    # `GLUE_MATRIX` nao roda ao contrario -- e nao deve.
    assert context.glue == ""


def test_event_log_without_a_version_header_leaves_spark_empty(tmp_path):
    """Log truncado pelo inicio nao vira palpite -- vira campo vazio."""
    truncated = json.dumps({"Event": "SparkListenerApplicationEnd", "Timestamp": 2})
    context = _core.build_runtime_context(facts=list(_event_log_facts(tmp_path, truncated)))

    assert context.spark == ""
    assert context.detected_from == []


# --------------------------------------------------------------------------- #
# 3. Flag e fact discordando -> divergencia, nunca silencio
# --------------------------------------------------------------------------- #


def test_event_log_beats_the_flag_and_the_disagreement_is_reported(tmp_path):
    """`cli` entra na precedencia ABAIXO de `event_log` -- ver `_PRECEDENCE`.

    O que importa mais que a ordem: o valor perdedor nao some. Ele continua em
    `divergences` e em `observed` do fact `env.runtime_signal`, que e o gatilho
    de SF-ENV-001 em P0.
    """
    context, facts = _core.build_runtime(spark="3.1.1", facts=list(_event_log_facts(tmp_path)))

    assert context.spark == "3.5.4-amzn-0"  # o run reportou; a flag so declarou
    assert sorted(context.detected_from) == ["cli", "event_log"]

    signal = [f for f in facts if f.attrs.get("component") == "spark"]
    assert len(signal) == 1
    assert signal[0].kind == "env.runtime_signal"
    assert signal[0].attrs["observed"] == ["3.1.1", "3.5.4-amzn-0"]
    assert signal[0].measures["distinct_versions"] == 2
    assert any("3.1.1" in text and "3.5.4-amzn-0" in text for text in context.divergences)


def test_the_flag_beats_terraform_and_the_disagreement_is_still_reported(tmp_path):
    """Entre duas DECLARACOES (flag e IaC), a flag do operador vence.

    Ele pode saber de uma mudanca aplicada no console que o Terraform ainda nao
    reflete. Mas vencer nao e apagar: a discordancia continua reportada.
    """
    context, _facts = _core.build_runtime(glue="4.0", facts=list(_terraform_facts(tmp_path)))

    assert context.glue == "4.0"
    assert sorted(context.detected_from) == ["cli", "terraform"]
    assert any("4.0" in text and "5.1" in text for text in context.divergences)


def test_judge_reports_the_runtime_it_used_so_divergence_is_not_silent(tmp_path):
    """A divergencia tem que ser VISIVEL na saida de `judge`, nao so no objeto.

    Sem `runtime` no payload, o operador que passou `--glue 4.0` sobre um
    Terraform que diz 5.1 nunca saberia que as duas versoes existem -- e um
    limiar de versao errado invalida toda recomendacao seguinte.
    """
    facts_path = _facts_file(tmp_path, "facts.json", _terraform_facts(tmp_path))
    payload = _core.judge_findings(facts_path=facts_path, glue="4.0", limit=None)

    assert payload["runtime"]["glue"] == "4.0"
    assert payload["runtime"]["divergences"], "divergencia resolvida em silencio"


def test_two_modules_with_different_glue_version_diverge_instead_of_one_winning(tmp_path):
    """Dois `tf.attribute` glue_version distintos e caso real, nao patologia.

    Colapsar num dict escolheria um em silencio. Viram duas observacoes, com a
    origem qualificada pelo arquivo, e a divergencia aparece.
    """
    from sparkforge.facts.terraform import extract_terraform_tree

    infra = tmp_path / "infra"
    _write(infra, "a/glue.tf", GLUE_JOB_TF)
    _write(infra, "b/glue.tf", GLUE_JOB_TF.replace('"5.1"', '"4.0"'))
    facts = extract_terraform_tree(infra, repo_root=tmp_path)

    context, signals = _core.build_runtime(facts=list(facts))

    assert sorted(context.divergences)[0].startswith("glue: valores divergentes")
    assert any("a/glue.tf" in text and "b/glue.tf" in text for text in context.divergences)
    # A divergencia de glue propaga para os componentes derivados da matriz:
    # 5.1 e 4.0 nao trazem o mesmo Spark.
    spark_signal = [f for f in signals if f.attrs.get("component") == "spark"]
    assert spark_signal[0].attrs["observed"] == sorted(
        {GLUE_MATRIX["4.0"]["spark"], GLUE_MATRIX["5.1"]["spark"]}
    )


def test_repeating_the_same_glue_version_is_one_observation_not_a_divergence(tmp_path):
    """Tres modulos com a MESMA versao nao sao tres fontes discordantes."""
    from sparkforge.facts.terraform import extract_terraform_tree

    infra = tmp_path / "infra"
    for name in ("a", "b", "c"):
        _write(infra, f"{name}/glue.tf", GLUE_JOB_TF.replace('"etl"', f'"etl_{name}"'))
    facts = extract_terraform_tree(infra, repo_root=tmp_path)

    context = _core.build_runtime_context(facts=list(facts))

    assert context.glue == "5.1"
    assert context.divergences == []
    # Sem qualificacao por arquivo quando nao ha o que desambiguar: o operador
    # le "terraform", nao tres caminhos.
    assert context.detected_from == ["terraform"]


# --------------------------------------------------------------------------- #
# 4. Nenhum fact carrega versao -> contexto vazio, e o skip APARECE
# --------------------------------------------------------------------------- #


def test_no_fact_carries_a_version_leaves_the_context_empty(tmp_path):
    context = _core.build_runtime_context(facts=list(_pyspark_facts(tmp_path)))

    assert context.to_dict() == {
        "glue": "",
        # `emr` entrou na Fase 5b: `to_dict()` emite TODA chave, sempre, e um
        # dict literal aqui e o teste que registra isso. Vazio e o valor certo
        # -- nenhum fact PySpark observa plataforma, e adivinhar seria
        # julgamento entrando na camada de fato.
        "emr": "",
        "spark": "",
        "python": "",
        "iceberg": "",
        "athena": "",
        "detected_from": [],
        "divergences": [],
    }


def test_glue_rules_are_skipped_with_reason_and_it_shows_in_show_skipped(tmp_path):
    """Pular com motivo e o comportamento CORRETO, nao a lacuna a consertar.

    O que nao pode acontecer e o skip ser invisivel.
    """
    facts_path = _facts_file(tmp_path, "facts.json", _pyspark_facts(tmp_path))
    payload = _core.judge_findings(facts_path=facts_path, limit=None, show_skipped=True)

    assert set(GLUE_GUARDED_RULES) <= _skipped_for_scope(payload)
    assert payload["runtime"]["glue"] == ""


def test_a_non_literal_glue_version_is_not_an_observation(tmp_path):
    """`glue_version = var.gv` nao e a versao -- e o nome de uma variavel.

    O extrator guarda o texto da referencia em `attrs.value` com
    `literal: false`. Lido como versao, o contexto reportaria "var.gv" e
    `in_scope` compararia lixo contra `>=3.0`.
    """
    facts = list(_terraform_facts(tmp_path, GLUE_JOB_TF_VAR))
    assert any(
        f.kind == "tf.attribute" and f.attrs.get("key") == "glue_version" for f in facts
    ), "a fixture precisa produzir o tf.attribute nao-literal para o teste valer"

    context = _core.build_runtime_context(facts=facts)

    assert context.glue == ""
    assert context.detected_from == []


def test_pyspark_api_syntax_never_infers_a_version(tmp_path):
    """A fronteira negativa, dita como teste.

    Derivar e ler o que o extrator OBSERVOU. Adivinhar versao a partir de
    sintaxe de API, nome de bucket ou presenca de import seria julgamento
    entrando na camada de fato. Se alguem acrescentar essa heuristica, este
    teste fica vermelho -- e e para ficar.
    """
    facts = list(_pyspark_facts(tmp_path))
    assert facts, "a fixture precisa produzir facts de PySpark"

    assert _core.runtime_sources_from_facts(facts) == {}


# --------------------------------------------------------------------------- #
# 5. Sensibilidade: com a inferencia desligada, o invariante cai
# --------------------------------------------------------------------------- #


def test_with_the_inference_disabled_the_eight_rules_go_back_to_being_skipped(
    tmp_path, monkeypatch
):
    """Contraprova do teste 1: sem derivar fontes dos facts, o Terraform com
    `glue_version = "5.1"` volta a nao servir para nada, e as 8 somem.

    Sem isto, o teste 1 poderia estar verde por qualquer outro motivo.
    """
    facts_path = _facts_file(tmp_path, "facts.json", _terraform_facts(tmp_path))
    monkeypatch.setattr(_core, "runtime_sources_from_facts", lambda facts: {})

    payload = _core.judge_findings(facts_path=facts_path, limit=None, show_skipped=True)

    assert set(GLUE_GUARDED_RULES) <= _skipped_for_scope(payload)
    assert payload["runtime"]["glue"] == ""


# --------------------------------------------------------------------------- #
# 6. Os outros caminhos que montam contexto
# --------------------------------------------------------------------------- #


def test_the_cli_judge_payload_carries_the_runtime_too(tmp_path, capsys):
    """A CLI remonta o payload campo a campo -- `_core` devolver `runtime` nao
    basta, o verbo tem que repassar. Este teste existe porque a primeira versao
    da mudanca esqueceu exatamente isso, e a prova de ponta a ponta foi quem
    pegou: a saida de `sparkforge judge` saiu sem `runtime`.
    """
    from sparkforge.adapters import cli

    facts_path = _facts_file(tmp_path, "facts.json", _terraform_facts(tmp_path))
    assert cli.main(["judge", "--facts", facts_path, "--limit", "0"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["runtime"]["glue"] == "5.1"
    assert payload["runtime"]["detected_from"] == ["terraform"]


def test_runtime_detect_verb_also_reads_the_facts(tmp_path):
    facts_path = _facts_file(tmp_path, "facts.json", _terraform_facts(tmp_path))

    assert _core.runtime_detect()["glue"] == ""  # sem facts: comportamento anterior
    assert _core.runtime_detect(facts_path=facts_path)["glue"] == "5.1"


def test_case_open_records_the_runtime_detected_from_the_facts(tmp_path):
    facts_path = _facts_file(tmp_path, "facts.json", _terraform_facts(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()

    case = _core.case_open(
        str(repo), "case-1", "2026-08-01T00:00:00Z", facts_path=facts_path
    )

    assert case["runtime"]["glue"] == "5.1"
    assert case["runtime"]["spark"] == GLUE_MATRIX["5.1"]["spark"]


# --------------------------------------------------------------------------- #
# 8. O dump de EMR observou o runtime, e e por isso que ele vira fonte
# --------------------------------------------------------------------------- #

EMR_CLUSTER_DUMP = {
    "Cluster": {
        "Id": "j-1EXAMPLE",
        "ReleaseLabel": "emr-7.5.0",
        "InstanceCollectionType": "INSTANCE_GROUP",
        "LogUri": "s3://bucket/elasticmapreduce/",
        "AutoTerminate": False,
        "Status": {"State": "RUNNING"},
        "Applications": [
            {"Name": "Spark", "Version": "3.5.2-amzn-1"},
            {"Name": "Hadoop", "Version": "3.4.0-amzn-1"},
        ],
    },
    "InstanceGroups": [
        {
            "Id": "ig-MASTER",
            "InstanceGroupType": "MASTER",
            "Market": "ON_DEMAND",
            "InstanceType": "m5.xlarge",
            "RequestedInstanceCount": 1,
        }
    ],
}


def _emr_facts(tmp_path, dump=None):
    from sparkforge.facts.emr_cluster import extract_emr_cluster_path

    path = _write(
        tmp_path,
        "artifacts/cluster.json",
        json.dumps(dump if dump is not None else EMR_CLUSTER_DUMP),
    )
    return extract_emr_cluster_path(path, repo_root=tmp_path)


def test_emr_release_from_the_cluster_dump_fills_the_platform_and_the_matrix(tmp_path):
    """`emr.cluster` carrega o `ReleaseLabel`, que e chave de plataforma E
    entrada da EMR_MATRIX. Sem esta leitura, `RuntimeContext.emr` fica vazio
    num cluster que o dump descreve inteiro, e toda regra com `emr` em
    `runtime_scope` e pulada por ausencia."""
    from sparkforge.facts.runtime_detect import EMR_MATRIX

    context = _core.build_runtime_context(facts=_emr_facts(tmp_path))

    assert context.emr == "7.5.0"
    assert context.iceberg == EMR_MATRIX["7.5.0"]["iceberg"]
    assert "describe_cluster" in context.detected_from


def test_the_observed_spark_version_beats_the_matrix_derivation(tmp_path):
    """`Applications[].Version` e a AWS reportando o que INSTALOU: observacao
    com artefato, e por isso `describe_cluster` esta acima da derivacao por
    matriz. O sufixo `-amzn-N` observado sobrevive cru no valor resolvido: ele
    e a unica pista de um erro que so existe no fork da AWS."""
    dump = json.loads(json.dumps(EMR_CLUSTER_DUMP))
    dump["Cluster"]["Applications"] = [{"Name": "Spark", "Version": "3.5.2-amzn-9"}]

    context = _core.build_runtime_context(facts=_emr_facts(tmp_path, dump))

    assert context.spark == "3.5.2-amzn-9"
    # Mesmo Spark da Apache com patch diferente da AWS nao e divergencia de
    # versao -- e a decisao 1 de `_divergent_count`, que existe para nao virar
    # um P0 com o remedio errado.
    assert context.divergences == []


def test_a_spark_the_matrix_does_not_predict_is_reported_as_divergence(tmp_path):
    """Release 7.5.0 declara Spark 3.5.2; um cluster reportando 3.4.1 significa
    que uma das duas leituras descreve outra coisa. Resolver em silencio pela
    observacao esconderia do operador que a matriz e o cluster discordam."""
    dump = json.loads(json.dumps(EMR_CLUSTER_DUMP))
    dump["Cluster"]["Applications"] = [{"Name": "Spark", "Version": "3.4.1-amzn-0"}]

    context = _core.build_runtime_context(facts=_emr_facts(tmp_path, dump))

    assert context.spark == "3.4.1-amzn-0"
    assert any("spark" in d for d in context.divergences), context.divergences


def test_an_application_without_a_version_never_becomes_a_runtime_reading(tmp_path):
    """Aplicacao instalada sem versao reportada e fato; versao inventada a
    partir dela seria juizo entrando na camada de fato."""
    dump = json.loads(json.dumps(EMR_CLUSTER_DUMP))
    dump["Cluster"]["Applications"] = [{"Name": "Spark"}]
    dump["Cluster"]["ReleaseLabel"] = "emr-preview"

    context = _core.build_runtime_context(facts=_emr_facts(tmp_path, dump))

    assert context.spark == ""


def test_hadoop_is_read_from_the_dump_but_has_nowhere_to_go(tmp_path):
    """`Hadoop` vira `emr.application` como qualquer outra, mas nao alimenta o
    contexto: nao ha campo em `RuntimeContext` nem regra que o consulte, e
    inventar um so para guardar o valor seria custo sem consumidor -- a mesma
    decisao ja tomada para `hadoop` na EMR_MATRIX."""
    facts = _emr_facts(tmp_path)
    assert "Hadoop" in {f.attrs.get("name") for f in facts if f.kind == "emr.application"}
    assert "hadoop" not in _core.build_runtime_context(facts=facts).to_dict()
