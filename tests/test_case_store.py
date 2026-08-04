import pytest
import yaml

from sparkforge.case.router import load_gate_contract
from sparkforge.case.store import (
    GATES,
    PHASES,
    CaseError,
    add_hypothesis,
    load_case,
    new_case,
    override_gate,
    record_skill_use,
    save_case,
    set_gate,
    set_phase,
)

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}

# Medido na Task 1 da Fase 4b, nao escolhido: `validation` e a primeira fase que
# `baseline_captured` guarda (`experiment` seria insatisfazivel -- `bench.run_delta`
# exige o lado `--after`), e `hypothesis` e a primeira que `flows_mapped` guarda.
PHASE_GUARDADA = "validation"
PHASE_SO_DE_FLOWS = "hypothesis"
PHASE_ANTES_DE_QUALQUER_GATE = "diagnosis"
KIND_BASELINE = "bench.run_delta"
KIND_FLOWS = "callgraph.reachable_spark_work"
# `validation` e `report` sao guardadas pelos DOIS gates com produtor. Satisfazer
# so um deixaria o outro bloquear, e o teste passaria (ou falharia) pelo motivo
# errado -- a armadilha que a Task 1 deixou escrita.
TODOS_OS_KINDS = {KIND_BASELINE, KIND_FLOWS}


class TestNewCase:
    def test_has_required_top_level_keys(self):
        case = new_case("sf-2026-07-29-a", "2026-07-29T14:02:11Z", RUNTIME, repo="/r")
        for key in (
            "schema_version", "case_id", "created_at", "runtime", "scope", "phase",
            "artifacts", "facts_index", "findings_index", "baseline", "hypotheses",
            "gates", "strict_gates", "gate_overrides", "skills_used", "open_questions",
        ):
            assert key in case

    def test_rigor_e_desligado_por_omissao(self):
        """A escolha e do case, e o padrao e o comportamento de sempre."""
        case = new_case("c", "2026-08-04T00:00:00Z", RUNTIME)
        assert case["strict_gates"] is False
        assert case["gate_overrides"] == []

    def test_rigor_pedido_na_abertura_fica_gravado(self):
        case = new_case("c", "2026-08-04T00:00:00Z", RUNTIME, strict_gates=True)
        assert case["strict_gates"] is True

    def test_starts_in_intake_phase(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["phase"] == "intake"

    def test_gates_start_false(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["gates"] == {
            "baseline_captured": False,
            "dominant_bottleneck_identified": False,
            "functional_validation_defined": False,
            "flows_mapped": False,
        }

    def test_baseline_starts_null(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["baseline"] is None

    def test_timestamp_is_injected_never_generated(self):
        """Timestamp vem do processo, nunca do LLM, e nunca de relogio interno."""
        case = new_case("c", "2026-07-29T09:15:00Z", RUNTIME)
        assert case["created_at"] == "2026-07-29T09:15:00Z"


class TestRoundTrip:
    def test_save_then_load_is_identical(self, tmp_path):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME, repo=str(tmp_path))
        path = save_case(case, tmp_path)
        assert path == tmp_path / ".sparkforge" / "case.yaml"
        assert load_case(tmp_path) == case

    def test_saved_yaml_is_deterministic(self, tmp_path):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME)
        first = save_case(case, tmp_path).read_text(encoding="utf-8")
        second = save_case(case, tmp_path).read_text(encoding="utf-8")
        assert first == second

    def test_load_missing_case_raises_with_actionable_message(self, tmp_path):
        with pytest.raises(CaseError, match="sparkforge case open"):
            load_case(tmp_path)

    def test_load_rejects_unknown_schema_version(self, tmp_path):
        target = tmp_path / ".sparkforge"
        target.mkdir()
        (target / "case.yaml").write_text(
            yaml.safe_dump({"schema_version": 99, "case_id": "c"}), encoding="utf-8"
        )
        with pytest.raises(CaseError, match="schema_version"):
            load_case(tmp_path)


class TestMutators:
    def _case(self):
        return new_case("c", "2026-07-29T00:00:00Z", RUNTIME)

    def test_set_phase_accepts_known_phase(self):
        assert set_phase(self._case(), "diagnosis")["phase"] == "diagnosis"

    def test_set_phase_rejects_unknown_phase(self):
        with pytest.raises(CaseError, match="fase"):
            set_phase(self._case(), "vibes")

    def test_set_gate_flips_value(self):
        assert set_gate(self._case(), "baseline_captured", True)["gates"]["baseline_captured"]

    def test_set_gate_rejects_unknown_gate(self):
        with pytest.raises(CaseError, match="gate"):
            set_gate(self._case(), "vibes_ok", True)

    def test_add_hypothesis_assigns_sequential_id(self):
        case = add_hypothesis(
            self._case(), "loop recomputa DAG", "N jobs identicos", "materializar"
        )
        case = add_hypothesis(case, "skew na chave nula", "max/p50 cai", "separar nulls")
        assert [h["id"] for h in case["hypotheses"]] == ["h1", "h2"]

    def test_new_hypothesis_starts_open(self):
        assert add_hypothesis(self._case(), "s", "p", "e")["hypotheses"][0]["status"] == "open"

    def test_record_skill_use_appends_with_outcome(self):
        case = record_skill_use(
            self._case(), "diagnose-data-skew", "2026-07-29T10:00:00Z", "skew confirmado"
        )
        entry = case["skills_used"][0]
        assert entry["skill"] == "diagnose-data-skew"
        assert entry["at"] == "2026-07-29T10:00:00Z"
        assert entry["outcome"] == "skew confirmado"

    def test_mutators_do_not_alter_the_input(self):
        original = self._case()
        set_phase(original, "diagnosis")
        assert original["phase"] == "intake"


class TestGateContract:
    """O contrato do `routing.yaml` — a decisao da Task 1 travada como dado."""

    def test_os_quatro_gates_aparecem_no_contrato(self):
        """Gate ausente do bloco e ambiguo entre 'esqueceram' e 'advisory de proposito'."""
        assert set(load_gate_contract()) == set(GATES)

    def test_gate_sem_produtor_declara_o_motivo(self):
        for gate, contract in load_gate_contract().items():
            if contract.get("satisfied_by"):
                continue
            assert contract.get("advisory_reason", "").strip(), gate

    def test_gate_com_produtor_declara_comando_e_fases_conhecidas(self):
        for gate, contract in load_gate_contract().items():
            if not contract.get("satisfied_by"):
                continue
            assert contract.get("produced_by", "").startswith("sparkforge "), gate
            phases = contract["guards_phases"]
            assert phases and set(phases) <= set(PHASES), gate

    def test_guards_phases_e_sufixo_de_phases(self):
        """R3: `set_phase` nao impoe ordem, entao uma fase so seria contornada
        pulando fase. A lista precisa ir da primeira guardada ate o fim."""
        for gate, contract in load_gate_contract().items():
            phases = contract.get("guards_phases")
            if not phases:
                continue
            primeira = PHASES.index(phases[0])
            assert list(phases) == list(PHASES[primeira:]), gate


class TestStrictGates:
    def _case(self, strict=True):
        return new_case("c", "2026-08-04T00:00:00Z", RUNTIME, strict_gates=strict)

    def test_gate_com_produtor_bloqueia_a_transicao_sob_rigor(self):
        with pytest.raises(CaseError) as exc:
            set_phase(self._case(), PHASE_GUARDADA, fact_kinds=set())
        assert "baseline_captured" in str(exc.value)
        assert "sparkforge benchmark" in str(exc.value)

    def test_a_mensagem_nomeia_fase_gate_fact_e_comando(self):
        """D-5: a Fase 4a mediu que mensagem inacionavel passa no CI quando o
        teste so cobre `code == 2` e a string "sparkforge". Este assere conteudo."""
        with pytest.raises(CaseError) as exc:
            set_phase(self._case(), PHASE_SO_DE_FLOWS, fact_kinds=set())
        message = str(exc.value)
        assert PHASE_SO_DE_FLOWS in message
        assert "flows_mapped" in message
        assert KIND_FLOWS in message
        assert (
            "sparkforge analyze call-graph --facts .sparkforge/facts.json "
            "--out .sparkforge/facts_callgraph.json"
        ) in message

    def test_a_mensagem_declara_o_limite_da_checagem(self):
        """A checagem e por PRESENCA de kind. O limite vai escrito onde ele
        opera, do mesmo jeito que `dq.unresolved` declara o recorte dele."""
        with pytest.raises(CaseError) as exc:
            set_phase(self._case(), PHASE_GUARDADA, fact_kinds=set())
        message = str(exc.value).lower()
        assert "presen" in message
        assert "scope.entrypoints" in message

    def test_o_fact_produtor_satisfaz_o_gate(self):
        novo = set_phase(self._case(), PHASE_GUARDADA, fact_kinds=TODOS_OS_KINDS)
        assert novo["phase"] == PHASE_GUARDADA

    def test_satisfazer_so_um_dos_dois_gates_ainda_bloqueia(self):
        """`validation` e guardada pelos dois: o outro precisa aparecer na mensagem."""
        with pytest.raises(CaseError) as exc:
            set_phase(self._case(), PHASE_GUARDADA, fact_kinds={KIND_BASELINE})
        assert "flows_mapped" in str(exc.value)
        assert "baseline_captured" not in str(exc.value)

    def test_gate_sem_produtor_declarado_nunca_bloqueia(self):
        """O criterio da secao 1 do spec, travado: `functional_validation_defined`
        e `dominant_bottleneck_identified` nao tem `satisfied_by`, entao nem sob
        rigor eles impedem a transicao -- e continuam falsos no case.

        `report` e guardada pelos dois gates COM produtor, entao os kinds deles
        vao junto: sem isso o teste falharia por causa deles, e nao provaria nada
        sobre os gates sem produtor."""
        case = self._case()
        novo = set_phase(case, "report", fact_kinds=TODOS_OS_KINDS)
        assert novo["phase"] == "report"
        assert novo["gates"]["functional_validation_defined"] is False
        assert novo["gates"]["dominant_bottleneck_identified"] is False

    def test_o_booleano_manual_nao_destrava_sob_rigor(self):
        """Desvio D-4b-2: `case update --gate X --gate-value true` seria override
        sem motivo e sem registro."""
        case = set_gate(self._case(), "baseline_captured", True)
        with pytest.raises(CaseError, match="baseline_captured"):
            set_phase(case, PHASE_GUARDADA, fact_kinds=set())

    def test_gate_nao_morde_antes_da_fase_que_guarda(self):
        """R1: o gate nao pode bloquear uma fase onde a rota que o destrava ainda
        opera -- ROUTE-003 opera em `diagnosis`."""
        novo = set_phase(self._case(), PHASE_ANTES_DE_QUALQUER_GATE, fact_kinds=set())
        assert novo["phase"] == PHASE_ANTES_DE_QUALQUER_GATE

    def test_flows_mapped_destrava_com_o_kind_do_call_graph(self):
        novo = set_phase(self._case(), PHASE_SO_DE_FLOWS, fact_kinds={KIND_FLOWS})
        assert novo["phase"] == PHASE_SO_DE_FLOWS

    def test_callgraph_summary_nao_destrava(self):
        """`callgraph.summary` e emitido incondicionalmente: um gate satisfeito
        por ele destravaria rodando `analyze call-graph` sobre facts vazios."""
        with pytest.raises(CaseError, match="flows_mapped"):
            set_phase(self._case(), PHASE_SO_DE_FLOWS, fact_kinds={"callgraph.summary"})

    def test_fase_desconhecida_ainda_e_recusada_antes_do_gate(self):
        with pytest.raises(CaseError, match="fase"):
            set_phase(self._case(), "vibes", fact_kinds=set())

    def test_contrato_com_gate_desconhecido_e_recusado(self, tmp_path, monkeypatch):
        """Nome de gate com typo no `routing.yaml` seria gate inerte em silencio."""
        (tmp_path / "routing.yaml").write_text(
            yaml.safe_dump(
                {
                    "rules": [],
                    "fallback": {"recommended_skill": "x", "reason": "y"},
                    "gates": {
                        "baseline_capturd": {
                            "satisfied_by": "bench.run_delta",
                            "produced_by": "sparkforge benchmark",
                            "guards_phases": ["validation"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))
        with pytest.raises(CaseError, match="baseline_capturd"):
            set_phase(self._case(), PHASE_GUARDADA, fact_kinds=set())


class TestOverrideDeGate:
    """D-4: o dado as vezes genuinamente nao existe, e gate sem escapatoria
    reabre o impasse que a secao 5.5 da Fase 0 recusou. A escapatoria custa uma
    frase escrita, e a frase fica no case."""

    def _case(self):
        return new_case("c", "2026-08-04T00:00:00Z", RUNTIME, strict_gates=True)

    def test_override_sem_motivo_e_recusado(self):
        with pytest.raises(CaseError) as exc:
            override_gate(self._case(), "baseline_captured", reason="")
        assert "motivo" in str(exc.value).lower()

    def test_a_recusa_diz_o_que_falta(self):
        with pytest.raises(CaseError) as exc:
            override_gate(self._case(), "baseline_captured", reason="   ")
        assert "--reason" in str(exc.value)

    def test_override_de_gate_desconhecido_e_recusado(self):
        with pytest.raises(CaseError, match="gate desconhecido"):
            override_gate(self._case(), "vibes_ok", reason="porque sim")

    def test_override_com_motivo_fica_gravado_e_destrava(self):
        case = override_gate(
            self._case(), "baseline_captured", reason="job descontinuado"
        )
        registro = case["gate_overrides"][0]
        assert registro["gate"] == "baseline_captured"
        assert registro["reason"] == "job descontinuado"
        # `validation` e guardada pelos dois gates com produtor: o override
        # cobre um, a evidencia cobre o outro.
        novo = set_phase(case, PHASE_GUARDADA, fact_kinds={KIND_FLOWS})
        assert novo["phase"] == PHASE_GUARDADA

    def test_o_override_registra_quando(self):
        case = override_gate(
            self._case(), "flows_mapped", reason="corpus sem trabalho Spark",
            at="2026-08-04T12:00:00Z",
        )
        assert case["gate_overrides"][0]["at"] == "2026-08-04T12:00:00Z"

    def test_dois_overrides_do_mesmo_gate_ficam_os_dois(self):
        """Lista, nunca dicionario: sobrescrever apagaria o primeiro motivo, e
        dois overrides em momentos diferentes sao dois fatos."""
        case = override_gate(
            self._case(), "flows_mapped", reason="primeiro motivo",
            at="2026-08-04T10:00:00Z",
        )
        case = override_gate(
            case, "flows_mapped", reason="segundo motivo", at="2026-08-05T10:00:00Z"
        )
        assert [o["reason"] for o in case["gate_overrides"]] == [
            "primeiro motivo",
            "segundo motivo",
        ]

    def test_override_de_um_gate_nao_destrava_o_outro(self):
        case = override_gate(self._case(), "baseline_captured", reason="sem ambiente")
        with pytest.raises(CaseError, match="flows_mapped") as exc:
            set_phase(case, PHASE_GUARDADA, fact_kinds=set())
        assert "baseline_captured" not in str(exc.value)

    def test_o_override_nao_altera_o_case_de_entrada(self):
        original = self._case()
        override_gate(original, "baseline_captured", reason="x")
        assert original["gate_overrides"] == []

    def test_case_antigo_sem_a_chave_aceita_override(self):
        """Sem migracao: a lista nasce na primeira gravacao."""
        case = self._case()
        del case["gate_overrides"]
        assert override_gate(case, "flows_mapped", reason="x")["gate_overrides"]

    def test_a_mensagem_de_bloqueio_nomeia_a_escapatoria(self):
        """Quem esta bloqueado por dado que nao existe precisa saber que ela
        existe, sem ler o spec."""
        with pytest.raises(CaseError) as exc:
            set_phase(self._case(), PHASE_SO_DE_FLOWS, fact_kinds=set())
        assert "--override-gate flows_mapped" in str(exc.value)
        assert "--reason" in str(exc.value)


class TestSemRigorNadaMuda:
    """Criterio 5 do spec: case sem `--strict-gates` se comporta como antes."""

    def _case(self):
        return new_case("c", "2026-08-04T00:00:00Z", RUNTIME)

    def test_sem_rigor_a_transicao_passa_como_hoje(self):
        assert set_phase(self._case(), PHASE_GUARDADA, fact_kinds=set())["phase"] == (
            PHASE_GUARDADA
        )

    def test_a_assinatura_antiga_continua_valendo(self):
        """`_core` e os testes existentes chamam `set_phase(case, phase)`."""
        assert set_phase(self._case(), PHASE_GUARDADA)["phase"] == PHASE_GUARDADA

    def test_case_gravado_antes_desta_fase_nao_tem_a_chave(self):
        """Compatibilidade sem migracao (criterio 5 do spec): um case gravado por
        versao anterior nao tem `strict_gates` nem `gate_overrides`, e
        `case.get(...)` responde `None`, que e falsy. Simulado removendo as duas
        chaves, que e literalmente o que ha no YAML antigo."""
        case = self._case()
        del case["strict_gates"]
        del case["gate_overrides"]
        assert set_phase(case, "report", fact_kinds=set())["phase"] == "report"

    def test_sem_rigor_o_catalogo_nem_e_lido(self, tmp_path, monkeypatch):
        """Prova por ausencia: catalogo vazio quebraria a leitura, e nao quebra."""
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))
        assert set_phase(self._case(), PHASE_GUARDADA)["phase"] == PHASE_GUARDADA
