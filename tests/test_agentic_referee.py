"""O árbitro do protocolo de debate, e as quatro recusas que ele nomeia.

O §27 do prompt de origem pede o protocolo
`OBSERVE → HYPOTHESIZE → CHALLENGE → EVIDENCE → REBUTTAL → CONSENSUS →
VERIFICATION`, e fecha com a frase que decide tudo:

    "Nenhum agente pode declarar root cause final apenas com hipótese.
     O Coordinator precisa exigir evidence."

Metade destes testes existe para travar a RECUSA, e não a aprovação. Um refactor
que passe a aceitar hipótese no fechamento, ou a pontuar `upheld` em vez de
decidi-lo, derruba aqui.

O que eles cobram, em ordem de gravidade:

  1. hipótese que sobrevive ao fechamento é recusada — mesmo COM `evidence_refs`;
  2. claim sem evidência é recusada, de qualquer tipo;
  3. objeção sem réplica impede o fechamento;
  4. referência pendurada vale em QUALQUER status, porque é defeito de forma;
  5. durante o debate (`OPEN`) hipótese e claim desancorada são LEGÍTIMAS;
  6. claim revisada por `supersedes` não é cobrada — revisar é o que o protocolo
     permite;
  7. o sétimo estágio sai `modeled: false`, e as três recusas viajam na resposta.
"""
from __future__ import annotations

import json

import pytest

from sparkforge.adapters import _core
from sparkforge.agentic.debate import Debate, DebateRound, DebateStatus, DebateTrigger
from sparkforge.agentic.models import Claim, ClaimType, Objection, Rebuttal
from sparkforge.agentic.referee import (
    ESTAGIOS,
    VIOLACAO_HIPOTESE_FINAL,
    VIOLACAO_OBJECAO_VIVA,
    VIOLACAO_REFERENCIA_PENDURADA,
    VIOLACAO_SEM_EVIDENCIA,
    referee_over_blackboard,
    referee_verdict,
)


def _claim(
    quem: str,
    texto: str,
    tipo: ClaimType = ClaimType.INFERENCE,
    evidencia: tuple[str, ...] = (),
    supersedes: str | None = None,
) -> Claim:
    return Claim(
        claimant=quem,
        claim_type=tipo,
        statement=texto,
        evidence_refs=list(evidencia),
        assumptions=[],
        confidence="high",
        falsifiable=True,
        supersedes=supersedes,
    )


def _debate(rodadas: list[DebateRound], status: DebateStatus = DebateStatus.CONSENSUS) -> Debate:
    return Debate(
        topic="por que a escrita falha",
        participants=["fgac-spec", "iam-spec"],
        trigger=DebateTrigger.CONTRADICTORY_FINDINGS,
        rounds=rodadas,
        status=status,
    )


def _kinds(saida: dict) -> set[str]:
    return {v["kind"] for v in saida["violations"]}


class TestAFraseDoProtocolo:
    def test_hipotese_com_evidencia_ainda_e_recusada_no_fechamento(self):
        """O caso que separa esta violação da seguinte.

        Uma hipótese COM `evidence_refs` passaria pela checagem de evidência e
        seria publicada como causa raiz. O protocolo não diz "com evidência" —
        diz "não apenas com hipótese", e `ClaimType` já distinguia os quatro
        tipos. Nada lia essa distinção antes deste módulo.
        """
        hipotese = _claim("fgac-spec", "A falha é de FGAC.", ClaimType.HYPOTHESIS, ("f_abc123",))
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[hipotese])]))
        assert saida["upheld"] is False
        assert _kinds(saida) == {VIOLACAO_HIPOTESE_FINAL}

    def test_inferencia_sem_evidencia_cai_na_outra_violacao(self):
        """A segunda metade da frase: "o Coordinator precisa exigir evidence"."""
        inferencia = _claim("iam-spec", "Glue 5.1 usa IAM na escrita.", ClaimType.INFERENCE)
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[inferencia])]))
        assert saida["upheld"] is False
        assert _kinds(saida) == {VIOLACAO_SEM_EVIDENCIA}

    def test_observacao_ancorada_com_objecao_respondida_fecha(self):
        ok = _claim("iam-spec", "Glue 5.1 usa IAM.", ClaimType.OBSERVATION, ("f_abc123",))
        objecao = Objection(
            target_claim=ok.id,
            objector="fgac-spec",
            statement="É FGAC.",
            evidence_refs=["f_def456"],
        )
        replica = Rebuttal(
            target_objection=objecao.id,
            rebuttal_by="iam-spec",
            statement="A página de migração diz o contrário.",
            evidence_refs=["f_abc123"],
        )
        saida = referee_verdict(
            _debate(
                [
                    DebateRound(
                        round_number=1,
                        claims=[ok],
                        objections=[objecao],
                        rebuttals=[replica],
                    )
                ]
            )
        )
        assert saida["upheld"] is True
        assert saida["counts"]["objections_answered"] == 1

    def test_objecao_sem_replica_impede_o_fechamento(self):
        """Consenso não é silêncio: é objeção respondida."""
        ok = _claim("iam-spec", "Glue 5.1 usa IAM.", ClaimType.OBSERVATION, ("f_abc123",))
        objecao = Objection(
            target_claim=ok.id, objector="fgac-spec", statement="É FGAC.", evidence_refs=["f_x"]
        )
        saida = referee_verdict(
            _debate([DebateRound(round_number=1, claims=[ok], objections=[objecao])])
        )
        assert saida["upheld"] is False
        assert _kinds(saida) == {VIOLACAO_OBJECAO_VIVA}

    def test_resolved_fecha_igual_a_consensus(self):
        """Veredito de arbitragem sem evidência tem o mesmo defeito de um de
        consenso sem evidência."""
        hipotese = _claim("a", "É FGAC.", ClaimType.HYPOTHESIS, ("f_abc123",))
        saida = referee_verdict(
            _debate([DebateRound(round_number=1, claims=[hipotese])], DebateStatus.RESOLVED)
        )
        assert saida["upheld"] is False


class TestOQueEhLegitimoDuranteODebate:
    @pytest.mark.parametrize("status", [DebateStatus.OPEN, DebateStatus.DEADLOCKED])
    def test_hipotese_em_debate_aberto_ou_travado_e_legitima(self, status):
        """Hipótese é o estágio HYPOTHESIZE. Cobrá-la antes do fechamento
        proibiria o protocolo de acontecer."""
        hipotese = _claim("a", "É FGAC.", ClaimType.HYPOTHESIS)
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[hipotese])], status))
        assert saida["upheld"] is True

    def test_deadlock_nao_cobra_fechamento(self):
        """`deadlocked` é o desfecho HONESTO de um debate que não fechou, e
        `deadlock_resolution` já produz o plano de escalada dele."""
        objecao_viva = Objection(
            target_claim="claim_qualquer", objector="b", statement="x", evidence_refs=[]
        )
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        saida = referee_verdict(
            _debate(
                [DebateRound(round_number=1, claims=[ok], objections=[objecao_viva])],
                DebateStatus.DEADLOCKED,
            )
        )
        # A objeção pendurada continua sendo defeito de FORMA e sai; o que NÃO
        # sai é a cobrança de fechamento.
        assert VIOLACAO_OBJECAO_VIVA not in _kinds(saida)

    def test_claim_revisada_por_supersedes_nao_e_cobrada(self):
        """Revisar a própria posição é o que o estágio de REVISION permite.

        Cobrar evidência da claim substituída puniria o debate por ter
        funcionado.
        """
        hipotese = _claim("a", "É FGAC.", ClaimType.HYPOTHESIS)
        revisada = _claim(
            "a",
            "Na verdade é o catálogo.",
            ClaimType.OBSERVATION,
            ("f_xyz789",),
            supersedes=hipotese.id,
        )
        saida = referee_verdict(
            _debate(
                [
                    DebateRound(round_number=1, claims=[hipotese]),
                    DebateRound(round_number=2, claims=[revisada]),
                ]
            )
        )
        assert saida["upheld"] is True
        assert saida["counts"]["claims_superseded"] == 1
        assert saida["counts"]["claims_surviving"] == 1


class TestDefeitoDeForma:
    def test_replica_orfa_vale_em_debate_aberto(self):
        """Referência pendurada é defeito de FORMA e não de conclusão: ela faz um
        debate parecer completo sem ser, e por isso não espera o fechamento."""
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        orfa = Rebuttal(
            target_objection="obj_naoexiste", rebuttal_by="b", statement="x", evidence_refs=[]
        )
        saida = referee_verdict(
            _debate([DebateRound(round_number=1, claims=[ok], rebuttals=[orfa])], DebateStatus.OPEN)
        )
        assert saida["upheld"] is False
        assert _kinds(saida) == {VIOLACAO_REFERENCIA_PENDURADA}

    def test_objecao_apontando_claim_inexistente(self):
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        objecao = Objection(
            target_claim="claim_naoexiste", objector="b", statement="x", evidence_refs=[]
        )
        saida = referee_verdict(
            _debate(
                [DebateRound(round_number=1, claims=[ok], objections=[objecao])],
                DebateStatus.OPEN,
            )
        )
        assert VIOLACAO_REFERENCIA_PENDURADA in _kinds(saida)

    def test_a_objecao_atravessa_rodadas(self):
        """Uma objeção da rodada 1 pode receber réplica na rodada 2, e validar
        rodada a rodada perderia exatamente o caso que o debate permite."""
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        objecao = Objection(target_claim=ok.id, objector="b", statement="x", evidence_refs=["f_1"])
        replica = Rebuttal(
            target_objection=objecao.id, rebuttal_by="a", statement="z", evidence_refs=["f_2"]
        )
        saida = referee_verdict(
            _debate(
                [
                    DebateRound(round_number=1, claims=[ok], objections=[objecao]),
                    DebateRound(round_number=2, rebuttals=[replica]),
                ]
            )
        )
        assert saida["upheld"] is True


class TestOQueEleRecusaMedir:
    def test_o_setimo_estagio_sai_como_nao_modelado(self):
        """Consenso é acordo, não verificação. Publicar `VERIFICATION` como
        satisfeito porque houve consenso publicaria como verificado o que só foi
        acordado."""
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[ok])]))
        nao_modelados = [p["stage"] for p in saida["protocol"] if not p["modeled"]]
        assert nao_modelados == ["VERIFICATION"]

    def test_os_sete_estagios_do_protocolo_saem_na_ordem(self):
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[ok])]))
        assert [p["stage"] for p in saida["protocol"]] == [nome for nome, _ in ESTAGIOS]
        assert len(ESTAGIOS) == 7

    def test_as_tres_recusas_saem_com_o_que_destravaria(self):
        ok = _claim("a", "y", ClaimType.OBSERVATION, ("f_abc123",))
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[ok])]))
        recusas = {item["what"] for item in saida["refused"]}
        assert recusas == {"generate_debate", "verification_stage", "confidence_score"}
        gerar = next(i for i in saida["refused"] if i["what"] == "generate_debate")
        # A recusa tem de dizer POR QUE, e a razão é a regra 23: nada aqui chama
        # provider.
        assert "provider" in gerar["why"]
        assert gerar["unblocked_by"]

    def test_upheld_e_binario_e_nao_ha_nota_na_resposta(self):
        """Fail-closed contra score: `upheld` vem de contagem de violação."""
        hipotese = _claim("a", "É FGAC.", ClaimType.HYPOTHESIS)
        saida = referee_verdict(_debate([DebateRound(round_number=1, claims=[hipotese])]))
        assert isinstance(saida["upheld"], bool)

        def varrer(no):
            if isinstance(no, float):
                pytest.fail(f"float na saida: {no}")
            if isinstance(no, dict):
                for valor in no.values():
                    varrer(valor)
            if isinstance(no, list):
                for valor in no:
                    varrer(valor)

        varrer(json.loads(json.dumps(saida)))


class TestSobreOBlackboard:
    def test_blackboard_vazio_nao_e_aprovacao(self, tmp_path):
        """`upheld: True` com `closed: False` significa "nada foi fechado, logo
        nada a recusar" -- e é o campo `closed` que separa isso de aprovação."""
        saida = referee_over_blackboard(tmp_path)
        assert saida["upheld"] is True
        assert saida["closed"] is False
        assert saida["counts"]["claims"] == 0

    def test_rodada_sai_nula_e_nomeada_no_blackboard(self):
        """`rounds: 0` seria lido como "debate que não aconteceu". O blackboard
        simplesmente não modela rodada, e a resposta diz isso."""
        import tempfile

        saida = referee_over_blackboard(tempfile.mkdtemp())
        assert saida["counts"]["rounds"] is None
        assert "nao modela rodada" in saida["counts"]["rounds_note"]

    def test_o_nucleo_e_o_mesmo_para_as_duas_entradas(self):
        """Duas cópias do mesmo julgamento é o defeito que `ORDEM_DE_SEVERIDADE`
        teve por um dia. `_arbitrar` é a única implementação."""
        from sparkforge.agentic import referee

        fonte = referee.__file__
        with open(fonte, encoding="utf-8") as arquivo:
            texto = arquivo.read()
        assert texto.count("def _arbitrar(") == 1
        assert texto.count("VIOLACAO_HIPOTESE_FINAL,") >= 1

    def test_o_verbo_do_adaptador_devolve_o_mesmo(self, tmp_path):
        assert _core.debate_referee(str(tmp_path))["source"] == "blackboard"
