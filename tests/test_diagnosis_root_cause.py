"""O verbo que ordena a causa raiz, e as tres coisas que ele RECUSA fazer.

O §24 do prompt de origem pede sete campos por candidato. Seis tem produtor. O
setimo -- `CONFIDENCE` -- tem produtor com ressalva, e metade destes testes
existe para travar a ressalva: um refactor que passe a CALCULAR confianca a
partir de severidade e contagem de evidencia derruba aqui, e nao seis meses
depois num relatorio que publicou o numero como se fosse medido.

O que estes testes cobram, em ordem de gravidade:

  1. nenhum score novo e calculado -- `confidence_declared` e o campo da regra,
     igual, e nada na saida e um numero de confianca;
  2. a ordem e a DECLARADA, e ela e deterministica;
  3. `missing_evidence` tem as duas fontes, e a segunda nomeia o modulo que
     emite o kind que falta;
  4. o recorte por area publica o TOTAL ao lado da lista;
  5. `summary` corta texto e nunca resultado.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from sparkforge.adapters import _core
from sparkforge.diagnosis import ORDEM_DE_SEVERIDADE, rank_root_causes
from sparkforge.facts.lakeformation import build_lakeformation
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.models import Fact, Finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = {"glue": "5.1", "spark": "3.5.6", "python": "3.11", "iceberg": "1.10.0"}


def _caso_de_lakeformation():
    entrada = ROOT / "fixtures" / "infra_code" / "fgac_com_catalogo_nomeado" / "input"
    facts = list(extract_terraform_tree(entrada, repo_root=entrada))
    facts.extend(build_lakeformation(facts))
    findings, skipped = judge(facts, load_catalog(), RUNTIME, return_skipped=True)
    return facts, findings, skipped


def _finding(rule_id: str, severity: str, evidencia: list[str], confidence: str = "high"):
    return Finding(
        rule_id=rule_id,
        title=f"titulo de {rule_id}",
        severity=severity,
        confidence=confidence,
        status="structural",
        subject={"type": "source_location", "file": "x.py", "line": 1, "col": 0, "symbol": ""},
        evidence=list(evidencia),
        measured={},
        threshold={},
        runtime_scope={},
        explanation="",
        proposed_change=["faca isto"],
        risks=["o raio disto e maior que o job"],
        validation=["compare contagem"],
        rollback=["restaure"],
        sources=[],
        action={"kind": "config.remove_property", "target": "x", "direction": "remove"},
    )


class TestNaoInventaConfianca:
    def test_confidence_e_repassado_como_declarado(self):
        alvo = _finding("SF-X-001", "P0", ["f_aaaaaa"], confidence="low")
        saida = rank_root_causes([], [alvo], [], RUNTIME)
        candidato = saida["candidates"][0]
        assert candidato["confidence_declared"] == "low"
        # O nome do campo carrega a ressalva. Um `confidence` cru seria lido como
        # medida deste case.
        assert "confidence" not in candidato

    def test_severidade_alta_com_confianca_baixa_nao_vira_score(self):
        """O par mais perigoso: P0 com `confidence: low`.

        Um score que combinasse os dois produziria um numero intermediario que
        nao significa nada -- nem a consequencia que a regra declara, nem a
        medida que ela admite nao ter. Os dois campos saem SEPARADOS.
        """
        alvo = _finding("SF-X-001", "P0", ["f_aaaaaa"], confidence="low")
        saida = rank_root_causes([], [alvo], [], RUNTIME)
        candidato = saida["candidates"][0]
        assert candidato["severity"] == "P0"
        assert candidato["confidence_declared"] == "low"
        for chave, valor in candidato.items():
            if chave in {"position", "evidence_count"}:
                continue
            assert not isinstance(valor, float), (chave, valor)

    def test_nenhum_float_na_saida_inteira(self):
        """Fail-closed contra score: um numero fracionario na resposta e, neste
        verbo, quase certamente uma confianca calculada."""
        facts, findings, skipped = _caso_de_lakeformation()
        texto = json.dumps(rank_root_causes(facts, findings, skipped, RUNTIME))
        carregado = json.loads(texto)

        def varrer(no):
            if isinstance(no, float):
                pytest.fail(f"float na saida: {no}")
            if isinstance(no, dict):
                for v in no.values():
                    varrer(v)
            if isinstance(no, list):
                for v in no:
                    varrer(v)

        varrer(carregado)

    def test_as_tres_recusas_saem_com_o_que_destravaria(self):
        saida = rank_root_causes([], [], [], RUNTIME)
        recusas = {item["what"] for item in saida["refused"]}
        assert recusas == {
            "confidence_score",
            "security_impact_assessment",
            "expected_gain",
        }
        for item in saida["refused"]:
            assert item["why"]

    def test_a_ordem_declara_o_que_ela_nao_e(self):
        saida = rank_root_causes([], [], [], RUNTIME)
        assert "ORDEM" in saida["ordering"]["is_not"]
        assert "probabilidade" in saida["ordering"]["is_not"]


class TestAOrdemEDeclaradaEDeterministica:
    def test_severidade_decide_primeiro(self):
        entrada = [
            _finding("SF-A-001", "P2", ["f_1", "f_2", "f_3"]),
            _finding("SF-B-001", "P0", ["f_4"]),
        ]
        saida = rank_root_causes([], entrada, [], RUNTIME)
        assert [c["rule_id"] for c in saida["candidates"]] == ["SF-B-001", "SF-A-001"]

    def test_dentro_da_mesma_severidade_mais_evidencia_vem_primeiro(self):
        entrada = [
            _finding("SF-A-001", "P1", ["f_1"]),
            _finding("SF-B-001", "P1", ["f_2", "f_3"]),
        ]
        saida = rank_root_causes([], entrada, [], RUNTIME)
        assert [c["rule_id"] for c in saida["candidates"]] == ["SF-B-001", "SF-A-001"]

    def test_a_ordem_e_a_do_schema_e_nao_uma_copia(self):
        """A primeira versao deste modulo declarou `P0..P3` a mao, e o schema
        aceita `P0..P4`.

        O efeito era silencioso e errado: um achado `P4` legitimo caia no balde
        de "severidade desconhecida" e ia para o FIM da ordem. O conserto NAO foi
        corrigir a copia -- foi apagar a copia: `ORDEM_DE_SEVERIDADE` E
        `SEVERITY_ORDER`, o mesmo objeto. Este teste trava a identidade, entao
        uma copia nova reintroduzida derruba aqui.
        """
        from sparkforge.findings.models import SEVERITY_ORDER

        assert ORDEM_DE_SEVERIDADE is SEVERITY_ORDER
        assert "P4" in ORDEM_DE_SEVERIDADE

    def test_severidade_fora_do_vocabulario_cai_no_fim(self):
        """`Finding` recusa severidade desconhecida, entao este caso nao chega
        pelo caminho normal -- e a ordenacao e testada DIRETO.

        A guarda existe para o dia em que o vocabulario crescer e esta tupla
        ficar para tras: ali o valor novo tem de ir para o fim, e nao para o
        comeco. Ordenar desconhecido como o mais grave faria a saida mentir na
        PRIMEIRA linha, que e a que alguem le.
        """
        from sparkforge.diagnosis.root_cause import _ordem

        conhecida = _finding("SF-B-001", "P4", ["f_2"])
        desconhecida = _finding("SF-A-001", "P0", ["f_1"])
        desconhecida.severity = "P9"  # forcado depois da validacao, de proposito
        assert _ordem(conhecida) < _ordem(desconhecida)

    def test_desempate_por_rule_id_e_estavel(self):
        entrada = [
            _finding("SF-B-001", "P1", ["f_1"]),
            _finding("SF-A-001", "P1", ["f_2"]),
        ]
        primeiro = rank_root_causes([], entrada, [], RUNTIME)
        segundo = rank_root_causes([], list(reversed(entrada)), [], RUNTIME)
        assert [c["rule_id"] for c in primeiro["candidates"]] == ["SF-A-001", "SF-B-001"]
        assert [c["rule_id"] for c in primeiro["candidates"]] == [
            c["rule_id"] for c in segundo["candidates"]
        ]

    def test_a_ordem_de_severidade_publicada_e_a_usada(self):
        saida = rank_root_causes([], [], [], RUNTIME)
        assert saida["ordering"]["severity_order"] == list(ORDEM_DE_SEVERIDADE)


class TestALacunaNomeada:
    def test_recusa_de_extrator_entra_com_reason_e_unblocked_by(self):
        facts, findings, skipped = _caso_de_lakeformation()
        saida = rank_root_causes(facts, findings, skipped, RUNTIME)
        recusas = [
            item for item in saida["missing_evidence"] if item["source"] == "extractor_refusal"
        ]
        assert recusas
        assert any(item["reason"] for item in recusas)
        assert any(item["unblocked_by"] for item in recusas)

    def test_regra_pulada_nomeia_o_modulo_que_emite_o_kind(self):
        """E o que transforma "esta regra nao disparou" em "colete isto"."""
        facts, findings, skipped = _caso_de_lakeformation()
        saida = rank_root_causes(facts, findings, skipped, RUNTIME)
        puladas = [
            item for item in saida["missing_evidence"] if item["source"] == "rule_not_evaluated"
        ]
        assert puladas
        for item in puladas:
            assert item["missing_kinds"]
            for kind, modulo in item["emitted_by"].items():
                assert modulo, f"kind sem dono: {kind}"

    def test_o_modulo_e_descoberto_por_varredura_e_nao_por_lista(self):
        """`lakeformation.grant` e emitido por `lakeformation_grants`, e nenhuma
        lista escrita a mao neste teste diz isso -- a varredura de
        `EMITTED_KINDS` diz."""
        from sparkforge.diagnosis.root_cause import _modulo_por_kind

        mapa = _modulo_por_kind()
        assert mapa["lakeformation.grant"] == "lakeformation_grants"
        assert mapa["lakeformation.access_model"] == "lakeformation"
        assert mapa["sql.write_statement"] == "sql_literal"
        # `matcher` mora fora de `sparkforge/facts/` e entra nomeado.
        assert mapa["error.signature_match"] == "errors.matcher"

    def test_o_recorte_por_area_publica_o_total_ao_lado_da_lista(self):
        facts, findings, skipped = _caso_de_lakeformation()
        saida = rank_root_causes(facts, findings, skipped, RUNTIME)
        escopo = saida["missing_evidence_scope"]
        assert escopo["rules_not_evaluated_listed"] < escopo["rules_not_evaluated_total"]
        assert escopo["areas_in_play"] == ["SF-LF"]
        assert "all_missing" in escopo["filter"]

    def test_all_missing_devolve_tudo_e_o_total_bate(self):
        facts, findings, skipped = _caso_de_lakeformation()
        saida = rank_root_causes(facts, findings, skipped, RUNTIME, all_missing=True)
        escopo = saida["missing_evidence_scope"]
        assert escopo["rules_not_evaluated_listed"] == escopo["rules_not_evaluated_total"]

    def test_so_requires_facts_entra_na_lacuna(self):
        """`runtime_scope` e `blocked_on` sao silencios que NAO se consertam
        coletando artefato, e por isso nao entram."""
        skipped = [
            {"rule_id": "SF-A-001", "reason": "requires_facts", "missing": ["pyspark.udf"]},
            {"rule_id": "SF-B-001", "reason": "runtime_scope", "scope": {"glue": ">=6.0"}},
            {"rule_id": "SF-C-001", "reason": "blocked_on", "blocked_on": "extrator X"},
        ]
        saida = rank_root_causes([], [_finding("SF-A-002", "P1", ["f_aaaaaa"])], skipped, RUNTIME)
        ids = {
            item["rule_id"]
            for item in saida["missing_evidence"]
            if item["source"] == "rule_not_evaluated"
        }
        assert ids == {"SF-A-001"}

    def test_area_e_o_prefixo_ate_o_ultimo_hifen(self):
        """`SF-EMR` e prefixo de `SF-EMRS`: comparar por `startswith` mediria a
        fronteira ao contrario."""
        from sparkforge.diagnosis.root_cause import _area

        assert _area("SF-LF-003") == "SF-LF"
        assert _area("SF-EMRS-001") == "SF-EMRS"
        assert _area("SF-EMR-001") == "SF-EMR"


class TestEvidencia:
    def test_fact_citado_e_ausente_do_conjunto_e_nomeado(self):
        alvo = _finding("SF-X-001", "P0", ["f_nao_existe"])
        saida = rank_root_causes([], [alvo], [], RUNTIME)
        assert saida["candidates"][0]["evidence"][0]["status"] == "ausente"

    def test_fact_presente_traz_kind_e_ancora(self):
        fact = Fact(
            kind="pyspark.udf",
            subject={
                "type": "source_location",
                "file": "job.py",
                "line": 3,
                "col": 0,
                "symbol": "minha_udf",
                "snippet": "",
            },
            attrs={"udf_type": "python"},
            provenance={
                "artifact": "job.py",
                "artifact_sha256": "a" * 64,
                "extractor": "pyspark_ast@0.1.0",
            },
        )
        alvo = _finding("SF-X-001", "P0", [fact.id])
        saida = rank_root_causes([fact], [alvo], [], RUNTIME)
        evidencia = saida["candidates"][0]["evidence"][0]
        assert evidencia["status"] == "presente"
        assert evidencia["kind"] == "pyspark.udf"
        assert evidencia["anchor"] == "minha_udf"


class TestPosturaEVersao:
    def test_acao_de_seguranca_e_classificada_pelo_namespace(self):
        alvo = _finding("SF-X-001", "P0", ["f_aaaaaa"])
        alvo.action = {
            "kind": "security.verify_access_chain",
            "target": "x",
            "direction": "investigate",
        }
        saida = rank_root_causes([], [alvo], [], RUNTIME)
        postura = saida["candidates"][0]["security_posture"]
        assert postura["classification"] == "touches_access_control"
        assert "namespace" in postura["basis"]

    def test_acao_fora_do_namespace_e_nao_indicada_e_nao_segura(self):
        """`not_indicated` NAO e "nao toca seguranca": e "o namespace da acao nao
        indica". A diferenca e a mesma de `not_declared` na matriz de versao."""
        saida = rank_root_causes([], [_finding("SF-X-001", "P0", ["f_aaaaaa"])], [], RUNTIME)
        assert saida["candidates"][0]["security_posture"]["classification"] == "not_indicated"

    def test_o_risco_da_regra_viaja_verbatim(self):
        alvo = _finding("SF-X-001", "P0", ["f_aaaaaa"])
        saida = rank_root_causes([], [alvo], [], RUNTIME)
        assert saida["candidates"][0]["security_posture"]["rule_declared_risks"] == [
            "o raio disto e maior que o job"
        ]

    def test_escopo_vazio_e_afirmacao_e_nao_omissao(self):
        saida = rank_root_causes([], [_finding("SF-X-001", "P0", ["f_aaaaaa"])], [], RUNTIME)
        impacto = saida["candidates"][0]["version_impact"]
        assert impacto["scope"] == {}
        assert "nao depende de fronteira" in impacto["reading"]

    def test_escopo_declarado_viaja_com_o_runtime_observado(self):
        facts, findings, skipped = _caso_de_lakeformation()
        saida = rank_root_causes(facts, findings, skipped, RUNTIME)
        impacto = saida["candidates"][0]["version_impact"]
        assert impacto["scope"] == {"glue": ">=5.0"}
        assert impacto["runtime_observed"]["glue"] == "5.1"


class TestOVerboDoAdaptador:
    def test_roda_sobre_arquivo_de_facts(self, tmp_path):
        facts, _, _ = _caso_de_lakeformation()
        arquivo = tmp_path / "facts.json"
        arquivo.write_text(
            json.dumps([f.to_dict() for f in facts], ensure_ascii=False), encoding="utf-8"
        )
        saida = _core.root_cause(facts_path=str(arquivo))
        assert saida["status"] == "ok"
        assert saida["candidate_count"] == 1
        assert saida["candidates"][0]["rule_id"] == "SF-LF-003"
        assert saida["fact_count"] == len(facts)

    def test_summary_corta_texto_e_nunca_resultado(self, tmp_path):
        facts, _, _ = _caso_de_lakeformation()
        arquivo = tmp_path / "facts.json"
        arquivo.write_text(
            json.dumps([f.to_dict() for f in facts], ensure_ascii=False), encoding="utf-8"
        )
        cheio = _core.root_cause(facts_path=str(arquivo), detail_level="full")
        resumo = _core.root_cause(facts_path=str(arquivo), detail_level="summary")

        assert cheio["candidates"][0]["remediation"]
        assert "remediation" not in resumo["candidates"][0]
        # O resultado sobrevive: apagar evidencia para economizar token e
        # defeito, nao compressao.
        for saida in (cheio, resumo):
            candidato = saida["candidates"][0]
            assert candidato["rule_id"]
            assert candidato["severity"]
            assert candidato["confidence_declared"]
            assert candidato["evidence"]
            assert candidato["evidence_count"]
        assert resumo["missing_evidence"] == cheio["missing_evidence"]

    def test_sem_facts_e_sem_facts_path_recusa_com_exit_2(self):
        with pytest.raises(_core.AdapterError) as erro:
            _core.root_cause()
        assert erro.value.exit_code == 2

    def test_lista_vazia_de_caminhos_recusa(self):
        with pytest.raises(_core.AdapterError):
            _core.root_cause(facts_path=[])
