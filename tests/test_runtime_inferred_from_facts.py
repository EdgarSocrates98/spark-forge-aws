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


# --------------------------------------------------------------------------- #
# 9. A flag `--emr`: declaracao, e o que acontece quando ela discorda do dump
# --------------------------------------------------------------------------- #


def test_the_emr_flag_fills_the_platform_without_any_dump():
    """A razao de a flag existir. Havia `--glue`, `--spark`, `--python`,
    `--iceberg` e `--athena`, e a release do EMR so entrava pelo fact
    `emr.cluster` -- quem SABE a release e nao tem dump nao conseguia
    declara-la, o que e assimetria com as outras cinco plataformas."""
    context = _core.build_runtime_context(emr="emr-7.5.0")

    assert context.emr == "7.5.0"
    assert context.detected_from == ["cli"]
    # A matriz deriva a partir da flag como derivaria a partir do dump: a flag
    # e outra FONTE, nao um caminho paralelo.
    assert context.spark == "3.5.2-amzn-1"


@pytest.mark.parametrize("digitado", ["emr-7.5.0", "7.5.0"])
def test_both_spellings_of_the_release_reach_the_same_row(digitado):
    """`_emr_key` ja normaliza as duas grafias, e a flag nao pode obrigar o
    operador a saber qual delas o projeto guarda. `RuntimeContext.emr` fica com
    a NUMERICA nos dois casos, por decisao do commit a38242c: `in_scope` roda
    `_parse` sobre este valor, e `_parse("emr-7.5.0")` le `emr` como 0."""
    context = _core.build_runtime_context(emr=digitado)

    assert context.emr == "7.5.0"
    assert context.divergences == []


def test_the_flag_disagreeing_with_the_dump_is_a_divergence_never_a_resolution(tmp_path):
    """O ponto inteiro da precedencia. `cli` esta ABAIXO de `describe_cluster`
    em `_PRECEDENCE`: o dump observou o cluster, a flag e declaracao sem
    artefato. Entao o valor REPORTADO e o do dump -- mas a discordancia nao
    desaparece, porque versao errada invalida toda recomendacao versionada que
    vier depois, e o operador precisa ver que as duas fontes nao batem."""
    context = _core.build_runtime_context(emr="emr-6.15.0", facts=_emr_facts(tmp_path))

    assert context.emr == "7.5.0"  # o dump vence
    assert any("emr" in d for d in context.divergences), context.divergences
    # E a divergencia imprime o valor CRU de cada fonte, nao a forma
    # normalizada: quem le precisa saber exatamente o que cada uma disse.
    assert "cli=emr-6.15.0" in " ".join(context.divergences)
    assert "describe_cluster=emr-7.5.0" in " ".join(context.divergences)


def test_the_flag_agreeing_in_the_other_spelling_is_not_a_divergence(tmp_path):
    """O falso positivo que a normalizacao de identidade existe para evitar. O
    dump carrega `emr-7.5.0` e alguem digita `7.5.0`: e a MESMA release, e
    contar as duas strings como identidades distintas transformaria uma flag
    que concorda num P0 -- ruido que treina o operador a ignorar o canal de
    divergencia, que e o oposto do que ele existe para fazer."""
    context = _core.build_runtime_context(emr="7.5.0", facts=_emr_facts(tmp_path))

    assert context.emr == "7.5.0"
    assert context.divergences == []


def test_the_flag_does_not_shadow_a_directly_observed_version(tmp_path):
    """Precedencia, do outro lado: a flag esta ACIMA de `terraform` e de
    `requirements` (declaracao mais especifica e mais recente), e ABAIXO do que
    foi observado com artefato. Aqui ela declara a release e o dump reporta o
    Spark instalado; a leitura direta continua vencendo a derivacao por matriz
    que a flag alimentou."""
    dump = json.loads(json.dumps(EMR_CLUSTER_DUMP))
    dump["Cluster"]["Applications"] = [{"Name": "Spark", "Version": "3.5.2-amzn-9"}]

    context = _core.build_runtime_context(emr="7.5.0", facts=_emr_facts(tmp_path, dump))

    assert context.spark == "3.5.2-amzn-9"


# --------------------------------------------------------------------------- #
# 10. `PYSPARK_PYTHON`: o unico lugar do dump que diz qual Python o PySpark usa
# --------------------------------------------------------------------------- #
#
# A `EMR_MATRIX` omite `python` na serie 6.x inteira de proposito -- a AWS lista
# `"2.7, 3.7"` como INSTALADOS e nao reafirma o default do PySpark por release,
# e escolher um dos dois seria inventar. O dump resolve, quando o operador
# declarou: `spark-env`/`PYSPARK_PYTHON`. O extrator ja emitia isso como
# `emr.configuration` com o valor cru, e nada lia. Existia o dado, existia o
# consumidor, e ninguem ligava os dois.


def _with_pyspark_python(value, *, level="cluster", release="emr-6.15.0"):
    dump = json.loads(json.dumps(EMR_CLUSTER_DUMP))
    dump["Cluster"]["ReleaseLabel"] = release
    dump["Cluster"]["Applications"] = [{"Name": "Hadoop", "Version": "3.3.6-amzn-1"}]
    config = [
        {
            "Classification": "spark-env",
            "Properties": {},
            "Configurations": [
                {"Classification": "export", "Properties": {"PYSPARK_PYTHON": value}}
            ],
        }
    ]
    if level == "cluster":
        dump["Cluster"]["Configurations"] = config
    else:
        dump["InstanceGroups"][0]["Configurations"] = config
    return dump


def test_pyspark_python_resolves_the_python_the_matrix_refuses_to_guess(tmp_path):
    """6.15.0 nao declara `python` na matriz. Com `PYSPARK_PYTHON` no dump, o
    valor deixa de ser desconhecido -- e passa a ser LIDO, nao escolhido."""
    from sparkforge.facts.runtime_detect import EMR_MATRIX

    assert "python" not in EMR_MATRIX["6.15.0"]

    context = _core.build_runtime_context(
        facts=_emr_facts(tmp_path, _with_pyspark_python("/usr/bin/python3.11"))
    )

    assert context.python == "3.11"


@pytest.mark.parametrize(
    "caminho",
    [
        "/usr/bin/python3",  # so o major: 3.7? 3.9? 3.11? o caminho nao diz
        "/usr/bin/python",  # nem o major
        "/opt/tools/bin/run-pyspark",  # wrapper com nome arbitrario
        "/usr/bin/env python3.11",  # o executavel e `env`; o resto e linha de comando
    ],
)
def test_an_ambiguous_interpreter_path_emits_nothing(tmp_path, caminho):
    """A fronteira. Emitir aqui entraria como `describe_cluster`, ACIMA da
    matriz e da flag em `_PRECEDENCE` -- versao errada com precedencia alta
    alimentando `runtime_scope`. Vazio e falha fechada, que e a semantica do
    projeto para `nao detectada`; chute e versao errada com cara de fato."""
    from sparkforge.rules.version_scope import in_scope

    context = _core.build_runtime_context(facts=_emr_facts(tmp_path, _with_pyspark_python(caminho)))

    assert context.python == ""
    assert in_scope({"python": ">=3.7"}, context.to_dict()) is False


def test_the_declared_interpreter_beats_the_matrix_and_the_disagreement_is_reported(tmp_path):
    """7.12.0 tem `python: 3.9` na matriz, e um cluster com
    `PYSPARK_PYTHON=/usr/bin/python3.11` esta rodando 3.11 -- e o par que a
    propria doc da AWS chama de armadilha operacional (o `pip3` do bootstrap
    continua no site-packages do 3.9). A leitura direta vence a derivacao, e a
    discordancia aparece em vez de ser resolvida em silencio."""
    context = _core.build_runtime_context(
        facts=_emr_facts(
            tmp_path, _with_pyspark_python("/usr/bin/python3.11", release="emr-7.12.0")
        )
    )

    assert context.python == "3.11"
    assert any("python" in d for d in context.divergences), context.divergences


def test_an_instance_group_property_is_not_a_reading_about_the_cluster(tmp_path):
    """Propriedade de grupo vale para AQUELE grupo, e `emr.configuration` de
    grupo e a configuracao PEDIDA -- e por isso que `emr.configuration.unapplied`
    existe. Ler runtime de algo que pode nao estar em vigor seria afirmar sobre
    o cluster o que nao se sabe nem sobre o grupo."""
    facts = _emr_facts(
        tmp_path, _with_pyspark_python("/usr/bin/python3.11", level="instance_group")
    )

    # O fact continua existindo, com o valor cru: a leitura de runtime e que nao
    # sai dele.
    assert any(
        f.attrs.get("key") == "PYSPARK_PYTHON" for f in facts if f.kind == "emr.configuration"
    )
    assert _core.build_runtime_context(facts=facts).python == ""


def test_another_configuration_key_never_becomes_a_python_reading(tmp_path):
    """`PYSPARK_PYTHON` e a chave, nao qualquer coisa que pareca um caminho de
    interpretador."""
    dump = _with_pyspark_python("/usr/bin/python3.11")
    dump["Cluster"]["Configurations"][0]["Configurations"][0]["Properties"] = {
        "PYSPARK_DRIVER_PYTHON": "/usr/bin/python3.11"
    }

    assert _core.build_runtime_context(facts=_emr_facts(tmp_path, dump)).python == ""


# --------------------------------------------------------------------------- #
# 11. `athena`: o eixo que tinha flag, tinha dado, e nao tinha ligacao
# --------------------------------------------------------------------------- #
#
# `athena.workgroup` carrega `measures.engine_version` -- numero, observado, com
# artefato e sha256 -- desde que o extrator existe, e `_runtime_reading` nao o
# lia: `RuntimeContext.athena` so era preenchivel pela flag `--athena`. E a
# divida de `PYSPARK_PYTHON` virada do avesso, e foi ela que obrigou a Fase 5a a
# ESVAZIAR o `runtime_scope` das cinco regras `SF-ATH` -- um guarda que falha
# fechado em todo runtime nao guarda nada.


def _athena_facts(tmp_path, workgroups, name: str = "artifacts/workgroups.json"):
    from sparkforge.facts.athena_workgroup import extract_athena_workgroup_path

    path = _write(tmp_path, name, json.dumps({"workgroups": workgroups}))
    return extract_athena_workgroup_path(path, repo_root=tmp_path)


def _workgroup(name: str, effective: str, **extra):
    return {
        "name": name,
        "engine_version": {
            "effective_engine_version": effective,
            "selected_engine_version": "AUTO",
        },
        "state": "ENABLED",
        **extra,
    }


def test_the_workgroup_dump_fills_athena_without_any_flag(tmp_path):
    """O numero ja estava no fact. So faltava alguem ler."""
    facts = _athena_facts(tmp_path, [_workgroup("primary", "Athena engine version 3")])

    context = _core.build_runtime_context(facts=facts)

    assert context.athena == "3"
    assert "get_work_group" in context.detected_from


def test_athena_is_an_integer_generation_never_a_dotted_version(tmp_path):
    """A AWS publica "Athena engine version 2" e "version 3", e nada entre elas.
    `"3.0"` afirmaria um segmento que a API nao diz -- e nao compraria
    comparacao nenhuma, porque `_compare` ja preenche com zeros."""
    from sparkforge.rules.version_scope import in_scope

    context = _core.build_runtime_context(
        facts=_athena_facts(tmp_path, [_workgroup("primary", "Athena engine version 3")])
    )

    assert context.athena == "3"
    assert in_scope({"athena": ">=3"}, context.to_dict()) is True
    assert in_scope({"athena": "==3"}, context.to_dict()) is True
    assert in_scope({"athena": "<3"}, context.to_dict()) is False


def test_two_workgroups_on_the_same_engine_are_one_observation(tmp_path):
    """Varios workgroups nao sao varias fontes. Dois na mesma geracao respondem
    a pergunta uma vez, e nao ha divergencia a reportar."""
    context = _core.build_runtime_context(
        facts=_athena_facts(
            tmp_path,
            [
                _workgroup("primary", "Athena engine version 3"),
                _workgroup("analytics", "Athena engine version 3"),
            ],
        )
    )

    assert context.athena == "3"
    assert not [d for d in context.divergences if "athena" in d]


def test_workgroups_on_different_engines_are_not_a_divergence_and_not_a_pick(tmp_path):
    """O caso que decide o desenho. Uma conta com `legacy-etl` na 2 e `primary`
    na 3 esta CORRETA -- e configuracao normal, nao uma contradicao sobre "qual
    e o runtime". Chamar isso de divergencia geraria SF-ENV-001 em P0 sobre nada,
    e falso P0 treina o operador a ignorar o canal. Escolher um dos dois seria
    resolucao arbitraria com cara de fato. Sobra a unica saida honesta: nao ha
    "a" engine version desta conta, o campo fica vazio, e a regra com `athena` em
    `runtime_scope` e pulada por ausencia."""
    from sparkforge.rules.version_scope import in_scope

    facts = _athena_facts(
        tmp_path,
        [
            _workgroup("legacy-etl", "Athena engine version 2"),
            _workgroup("primary", "Athena engine version 3"),
        ],
    )

    context = _core.build_runtime_context(facts=facts)

    assert context.athena == ""
    assert not [d for d in context.divergences if "athena" in d]
    assert in_scope({"athena": ">=3"}, context.to_dict()) is False


def test_the_per_workgroup_number_survives_the_silence(tmp_path):
    """A prova de que nada e escondido pelo silencio acima: o numero de CADA
    workgroup continua no seu proprio fact, e `SF-ATH-004` avalia workgroup a
    workgroup -- que e a granularidade onde a pergunta tem resposta. O eixo de
    runtime e uma pergunta sobre a conta inteira; a regra e sobre um workgroup."""
    facts = _athena_facts(
        tmp_path,
        [
            _workgroup("legacy-etl", "Athena engine version 2"),
            _workgroup("primary", "Athena engine version 3"),
        ],
    )

    lidos = {
        f.subject["symbol"]: f.measures["engine_version"]
        for f in facts
        if f.kind == "athena.workgroup"
    }

    assert lidos == {"legacy-etl": 2, "primary": 3}


def test_an_unreadable_workgroup_voids_the_reading_instead_of_being_ignored(tmp_path):
    """`athena.unresolved` e o extrator dizendo "vi um workgroup e nao consegui
    ler a engine dele". Com um ilegivel, "todos dizem 3" deixa de ser
    demonstravel -- entao a leitura nao sai. O ponto cego nao e ignorado pela
    afirmacao: ele e o que a impede."""
    facts = _athena_facts(
        tmp_path,
        [
            _workgroup("primary", "Athena engine version 3"),
            _workgroup("preview", "Athena engine version PREVIEW"),
        ],
    )

    assert any(
        f.attrs.get("reason") == "unparseable_engine_version"
        for f in facts
        if f.kind == "athena.unresolved"
    )
    assert _core.build_runtime_context(facts=facts).athena == ""


def test_the_blind_spot_stays_counted_where_the_report_reads_it(tmp_path):
    """Silenciar a deteccao nao pode silenciar o ponto cego. Ele continua com
    fact proprio e contado em `athena.analyzed`, que e onde o relatorio le."""
    facts = _athena_facts(tmp_path, [_workgroup("preview", "Athena engine version PREVIEW")])

    analyzed = next(f for f in facts if f.kind == "athena.analyzed")

    assert analyzed.measures["unresolved_count"] == 1
    assert _core.build_runtime_context(facts=facts).athena == ""


def test_the_dump_beats_the_flag_and_the_disagreement_is_reported(tmp_path):
    """`get_work_group` esta ACIMA de `cli` em `_PRECEDENCE`: o dump e a AWS
    reportando a engine EFETIVA, com artefato; a flag e uma declaracao. Discordar
    vira divergencia registrada -- SF-ENV-001 em P0 --, nunca resolucao
    silenciosa. Aqui a multiplicidade e de FONTES, e ai divergencia e o veredito
    certo."""
    context = _core.build_runtime_context(
        athena="2",
        facts=_athena_facts(tmp_path, [_workgroup("primary", "Athena engine version 3")]),
    )

    assert context.athena == "3"
    assert any("athena" in d for d in context.divergences), context.divergences


def test_a_dump_with_no_workgroups_reads_nothing(tmp_path):
    """Dump valido e vazio nao e leitura. Sem workgroup nenhum, nao ha engine
    version a afirmar -- e `athena.analyzed` sozinho nunca vira versao."""
    context = _core.build_runtime_context(facts=_athena_facts(tmp_path, []))

    assert context.athena == ""
    assert "get_work_group" not in context.detected_from
