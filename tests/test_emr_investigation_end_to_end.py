"""A prova do objetivo da Fase 5b, ponta a ponta.

O criterio 8 do spec: *investigacao sobre EMR produz achados de codigo, plano e
armazenamento normalmente*. E o ultimo da tabela da secao 5: *reporta as
SF-GLUE como puladas, e o teste falha se elas sumirem em silencio*.

Os dois juntos sao a fase inteira. Antes dela, um job em EMR produzia um
relatorio em que as regras de infraestrutura Glue avaliavam, nunca disparavam,
e nao apareciam em `skipped` -- e silencio, para um agente autonomo, le como
"nada encontrado". Depois dela, o eixo que nao se aplica aparece dito.

Os testes desta suite montam facts de EMR e de codigo PySpark ao mesmo tempo,
que e a forma real de uma investigacao, e afirmam sobre o relatorio inteiro em
vez de sobre uma regra de cada vez. Regra individual ja tem cobertura nas
fixtures golden; o que so aqui se prova e a **composicao**.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.adapters._core import build_runtime_context
from sparkforge.facts.emr_cluster import extract_emr_cluster_path
from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "emr"

# Um cluster EMR real do corpus, com Spot no TASK e sem protecao do AM. Nao
# inventado aqui: e a mesma entrada que as fixtures golden exercitam, para esta
# suite nao poder divergir delas em silencio.
CLUSTER = FIXTURES / "instance_groups_spot_task" / "input" / "cluster.json"

# Codigo com defeitos que NAO dependem da plataforma: `collect` traz tudo para o
# driver, `coalesce(1)` serializa a escrita. Se a Fase 5b tivesse errado o
# escopo, estes sumiriam num runtime EMR -- e e isso que o criterio 8 nega.
CODIGO = '''
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

def carregar(caminho):
    df = spark.read.parquet(caminho)
    linhas = df.collect()
    return linhas

def gravar(df, destino):
    df.coalesce(1).write.mode("overwrite").parquet(destino)
'''

GLUE_INFRA = {
    "SF-GLUE-001",
    "SF-GLUE-002",
    "SF-GLUE-003",
    "SF-GLUE-004",
    "SF-GLUE-005",
    "SF-GLUE-006",
}


def _investigar() -> tuple[list, list]:
    """Uma investigacao de EMR como ela realmente acontece: cluster mais codigo.

    Sem flag de runtime nenhuma -- desde a Fase 5a.2 o `judge` infere dos facts,
    e passar `--emr` aqui esconderia justamente o que esta suite tem que provar.
    """
    facts = list(extract_emr_cluster_path(CLUSTER, repo_root=ROOT))
    facts += list(extract_source(CODIGO, path="job.py"))
    runtime = build_runtime_context(facts=facts).to_dict()
    achados, pulados = judge(facts, load_catalog(), runtime, return_skipped=True)
    return achados, pulados


@pytest.fixture(scope="module")
def relatorio() -> tuple[list, list]:
    return _investigar()


class TestCodeFindingsSurviveOnEmr:
    """Criterio 8. A analise de codigo julga o job, nao o servico que o hospeda."""

    def test_the_code_rules_fire_on_an_emr_investigation(self, relatorio):
        achados, _ = relatorio
        de_codigo = sorted({f.rule_id for f in achados if f.rule_id.startswith("SF-PY")})
        assert de_codigo, (
            "nenhum achado de codigo num runtime EMR. O gatilho de SF-PY e AST puro: "
            "se ele sumiu, algum `runtime_scope` voltou a ser etiqueta de plataforma, "
            "que e o defeito que as Fases 5a e 5a.2 fecharam."
        )

    def test_the_emr_rules_fire_too(self, relatorio):
        achados, _ = relatorio
        de_emr = sorted({f.rule_id for f in achados if f.rule_id.startswith("SF-EMR")})
        assert de_emr, "nenhuma regra SF-EMR disparou sobre um cluster EMR real"


class TestGlueRulesAreReportedNotSilenced:
    """O ultimo teste da secao 5 do spec, e o que prova a fase.

    Uma regra que nao dispara TEM que aparecer em `skipped`, com motivo. Sumir
    dos dois lados e indistinguivel, para quem le, de "revisei e esta certo".
    """

    def test_no_glue_infra_rule_vanishes_from_both_sides(self, relatorio):
        achados, pulados = relatorio
        visiveis = {f.rule_id for f in achados} | {s["rule_id"] for s in pulados}
        sumidas = sorted(GLUE_INFRA - visiveis)
        assert not sumidas, (
            f"{sumidas} nao aparecem nem em findings nem em skipped numa investigacao "
            f"de EMR. O operador nao fica sabendo que o eixo de infraestrutura Glue "
            f"nao foi coberto."
        )

    def test_every_skipped_rule_carries_a_reason(self, relatorio):
        _, pulados = relatorio
        sem_motivo = sorted(s["rule_id"] for s in pulados if not s.get("reason"))
        assert not sem_motivo, (
            f"{sem_motivo} foram puladas sem motivo declarado. `--show-skipped` e o "
            f"mecanismo de ausencia explicada; skip sem razao e silencio com passos "
            f"extras."
        )


class TestTheRuntimeIsInferredNotDeclared:
    """A Fase 5a.2 fez o runtime vir dos facts. Aqui isso e usado de verdade."""

    def test_the_release_reaches_the_context_without_any_flag(self):
        facts = list(extract_emr_cluster_path(CLUSTER, repo_root=ROOT))
        contexto = build_runtime_context(facts=facts).to_dict()
        assert contexto["emr"], (
            "a release do cluster nao chegou ao contexto. `build_runtime_context` "
            "deveria deriva-la do fact `emr.cluster`, sem flag nenhuma."
        )
        assert contexto["glue"] == "", "nenhuma fonte declarou Glue nesta investigacao"

    def test_the_inferred_release_is_comparable(self):
        """Guarda a release numerica, nao o label -- `emr-7.5.0` nao e comparavel.

        `version_scope._parse` leria `emr` como 0, e todo range falharia fechado:
        regra pulada, cobertura apagada em silencio. Fixado aqui porque nenhuma
        regra da area usa `runtime_scope` hoje, entao so este teste segura.
        """
        from sparkforge.rules.version_scope import in_scope

        facts = list(extract_emr_cluster_path(CLUSTER, repo_root=ROOT))
        contexto = build_runtime_context(facts=facts).to_dict()
        assert not contexto["emr"].lower().startswith("emr-")
        assert in_scope({"emr": ">=6.0"}, contexto) is True
        assert in_scope({"emr": ">=99.0"}, contexto) is False


class TestNoAreaIsSilentlyEmpty:
    """A ponta agregada: nenhuma area do catalogo pode sumir sem ser dita.

    `TestNoCatalogAreaVanishesEntirely` em test_rule_scope_by_nature.py mede
    isso pelo `runtime_scope`. Aqui a medida e mais forte, porque passa pelo
    motor inteiro -- `requires_facts` e `blocked_on` tambem contam.
    """

    def test_every_area_either_fires_or_is_reported_as_skipped(self, relatorio):
        achados, pulados = relatorio
        area = lambda rid: rid.rsplit("-", 1)[0]  # noqa: E731
        todas = {area(r["id"]) for r in load_catalog()}
        vistas = {area(f.rule_id) for f in achados} | {area(s["rule_id"]) for s in pulados}
        mudas = sorted(todas - vistas)
        assert not mudas, (
            f"areas que nao aparecem de lado nenhum do relatorio: {mudas}. Uma area "
            f"inteira ausente sem motivo e o falso negativo mais caro que existe: o "
            f"operador conclui que aquele eixo esta limpo."
        )
