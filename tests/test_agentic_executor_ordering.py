"""Testes de `order_actions` e `load_measure_axes` -- a decisao 4 da secao 5.4.

## Por que a restricao de sequenciamento FILTRA por eixo de medida

Aqui o filtro por `nature: measure` e obrigatorio, e pela razao oposta a da
contradicao direta (ver `tests/test_agentic_executor_conflict.py`).

A restricao existe por causa da regra 13 do `CLAUDE.md`: aplicar no mesmo run
duas mudancas que movem a mesma MEDIDA torna o antes/depois inatribuivel, e
atribuir a melhora a uma delas exigiria o run que nao aconteceu.

`correctness.write_result` nao e grandeza -- e o resultado em si, e ele aparece
em 33 das 112. Tratado como medida, ele produziria um grupo de 33 regras, que e
ruido e nao restricao. Duas mudancas que ambas *podem alterar o resultado* nao
tem o problema de atribuicao; o que elas exigem e validacao funcional de cada
uma, que e `funcval` e nao isto.

O teste `test_duas_acoes_que_so_compartilham_correctness_nao_geram_restricao`
trava essa decisao.

## Por que ciclo nao vira ordem

Ordenar um ciclo produziria uma sequencia que PARECE decidida e nao e. A saida e
`order.unresolved` com os ids, e ordem vazia -- regra 20: recusa tem nome.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sparkforge.agentic.executor.ordering import load_measure_axes, order_actions
from sparkforge.rules.loader import load_catalog

RAIZ = Path(__file__).resolve().parents[1]

# Eixos sinteticos usados nos testes de restricao. Nao usamos os nomes reais
# quando a intencao e testar a MECANICA: assim uma mudanca de `nature` no
# catalogo nao muda o significado destes casos.
MEDIDA = {"eixo.medido", "outro.medido"}


def _acao(**over: Any) -> dict[str, Any]:
    base = {
        "kind": "capacity.change_worker_count",
        "target": "glue.number_of_workers",
        "direction": "replace",
        "requires_absent": [],
        "moves": [],
        "depends_on": [],
    }
    base.update(over)
    return base


def _finding(rule_id: str, **acao: Any) -> dict[str, Any]:
    return {"rule_id": rule_id, "action": _acao(**acao)}


def _findings_da_fixture(caminho: str) -> list[dict[str, Any]]:
    bruto = json.loads((RAIZ / caminho).read_text(encoding="utf-8-sig"))
    assert isinstance(bruto, list), f"{caminho}: findings.json deveria ser lista"
    return bruto


def _antes(ordem: list[str], primeiro: str, segundo: str) -> bool:
    return ordem.index(primeiro) < ordem.index(segundo)


@pytest.fixture(scope="module")
def findings_do_catalogo() -> list[dict[str, Any]]:
    return [
        {"rule_id": regra["id"], "action": regra["action"]}
        for regra in load_catalog()
        if regra.get("action")
    ]


class TestLoadMeasureAxes:
    def test_le_o_vocabulario_declarado_e_devolve_so_os_de_medida(self):
        eixos = load_measure_axes()
        assert "runtime.wall_clock" in eixos
        assert "cost.dpu_seconds" in eixos
        assert "correctness.write_result" not in eixos
        assert "security.secret_exposure" not in eixos

    def test_arquivo_ausente_levanta_em_vez_de_devolver_conjunto_vazio(self, tmp_path):
        """Conjunto vazio desligaria a restricao inteira em silencio.

        Mesma disciplina de `load_authority_map`: a lacuna que o codigo trata e
        eixo NAO DECLARADO como medida, nunca vocabulario desaparecido.
        """
        with pytest.raises(FileNotFoundError):
            load_measure_axes(tmp_path / "nao_existe.yaml")

    def test_eixo_sem_nature_nao_e_medida(self, tmp_path):
        arquivo = tmp_path / "axes.yaml"
        arquivo.write_text(
            "axes:\n"
            "  com.nature:\n"
            "    nature: measure\n"
            "  sem.nature:\n"
            "    description: nao declara nature\n",
            encoding="utf-8",
        )
        assert load_measure_axes(arquivo) == {"com.nature"}


class TestOrdemTopologica:
    def test_depends_on_e_respeitado(self):
        ordem, _, unresolved = order_actions(
            [
                _finding("SF-DEPOIS", depends_on=["SF-ANTES"]),
                _finding("SF-ANTES"),
            ],
            MEDIDA,
        )
        assert unresolved == {}
        assert _antes(ordem, "SF-ANTES", "SF-DEPOIS")

    def test_investigate_vem_antes_de_mudanca_no_mesmo_alvo(self):
        ordem, _, unresolved = order_actions(
            [
                _finding("SF-MUDA", target="spark.stage", direction="replace"),
                _finding("SF-MEDE", target="spark.stage", direction="investigate"),
            ],
            MEDIDA,
        )
        assert unresolved == {}
        assert _antes(ordem, "SF-MEDE", "SF-MUDA")

    def test_investigate_em_alvo_diferente_nao_ordena(self):
        """Sem aresta, a ordem de entrada e preservada -- e isso e conferivel."""
        ordem, _, _ = order_actions(
            [
                _finding("SF-MUDA", target="spark.stage", direction="replace"),
                _finding("SF-MEDE", target="glue.job", direction="investigate"),
            ],
            MEDIDA,
        )
        assert ordem == ["SF-MUDA", "SF-MEDE"]

    def test_dois_investigate_no_mesmo_alvo_nao_se_ordenam_entre_si(self):
        ordem, _, unresolved = order_actions(
            [
                _finding("SF-B", target="spark.stage", direction="investigate"),
                _finding("SF-A", target="spark.stage", direction="investigate"),
            ],
            MEDIDA,
        )
        assert unresolved == {}
        assert ordem == ["SF-B", "SF-A"]

    def test_ordem_e_estavel_na_entrada_quando_nada_a_restringe(self):
        entrada = [_finding("SF-C"), _finding("SF-A"), _finding("SF-B")]
        ordem, _, _ = order_actions(entrada, MEDIDA)
        assert ordem == ["SF-C", "SF-A", "SF-B"]

    def test_finding_sem_action_nao_entra_na_ordem(self):
        ordem, _, _ = order_actions(
            [{"rule_id": "SF-SEM-ACTION"}, _finding("SF-A")], MEDIDA
        )
        assert ordem == ["SF-A"]

    def test_regra_repetida_entra_uma_vez_so(self):
        """Duas ocorrencias da mesma regra sao dois findings e UMA acao.

        Repetir o id na ordem produziria uma sequencia que manda aplicar a mesma
        mudanca duas vezes.
        """
        ordem, _, _ = order_actions([_finding("SF-A"), _finding("SF-A")], MEDIDA)
        assert ordem == ["SF-A"]

    def test_depends_on_para_regra_ausente_do_case_nao_ordena_nada(self):
        """Dependencia que nao disparou nao e restricao sobre o que disparou.

        Ela tambem nao e lacuna: `depends_on` nomeia a regra que PRECISA vir
        antes SE as duas dispararem. Transformar a ausencia em `unresolved`
        diria que falta medir algo, quando o que houve foi a outra regra nao
        casar.
        """
        ordem, _, unresolved = order_actions(
            [_finding("SF-A", depends_on=["SF-QUE-NAO-DISPAROU"])], MEDIDA
        )
        assert ordem == ["SF-A"]
        assert unresolved == {}


class TestCiclo:
    def test_ciclo_em_depends_on_sai_unresolved_com_os_ids_e_ordem_vazia(self):
        ordem, _, unresolved = order_actions(
            [
                _finding("SF-A", depends_on=["SF-B"]),
                _finding("SF-B", depends_on=["SF-A"]),
            ],
            MEDIDA,
        )
        assert ordem == []
        assert unresolved["reason"] == "order.unresolved"
        assert unresolved["cycle"] == ["SF-A", "SF-B"]

    def test_ciclo_de_tres_nomeia_os_tres(self):
        ordem, _, unresolved = order_actions(
            [
                _finding("SF-A", depends_on=["SF-C"]),
                _finding("SF-B", depends_on=["SF-A"]),
                _finding("SF-C", depends_on=["SF-B"]),
            ],
            MEDIDA,
        )
        assert ordem == []
        assert unresolved["cycle"] == ["SF-A", "SF-B", "SF-C"]

    def test_ciclo_nomeia_so_quem_esta_nele_e_nao_quem_esta_a_jusante(self):
        """`SF-D` depende do ciclo e nao faz parte dele.

        Chamar de `cycle` tudo que sobrou do Kahn seria mais barato e diria uma
        coisa falsa: `SF-D` nao participa de ciclo nenhum, so nao tem como ser
        ordenado enquanto o ciclo existir.
        """
        _, _, unresolved = order_actions(
            [
                _finding("SF-A", depends_on=["SF-B"]),
                _finding("SF-B", depends_on=["SF-A"]),
                _finding("SF-D", depends_on=["SF-A"]),
            ],
            MEDIDA,
        )
        assert unresolved["cycle"] == ["SF-A", "SF-B"]

    def test_restricoes_saem_mesmo_com_ciclo(self):
        """A restricao de eixo nao depende de ordem, e recusar as duas coisas
        junto esconderia uma informacao que continua valida."""
        ordem, restricoes, unresolved = order_actions(
            [
                _finding("SF-A", depends_on=["SF-B"], moves=["eixo.medido"]),
                _finding("SF-B", depends_on=["SF-A"], moves=["eixo.medido"]),
            ],
            MEDIDA,
        )
        assert ordem == []
        assert unresolved["reason"] == "order.unresolved"
        assert [r["axis"] for r in restricoes] == ["eixo.medido"]


class TestRestricaoDeSequenciamento:
    def test_duas_acoes_no_mesmo_eixo_de_medida_geram_restricao(self):
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["eixo.medido"]),
                _finding("SF-B", moves=["eixo.medido"]),
            ],
            MEDIDA,
        )
        assert len(restricoes) == 1
        assert restricoes[0]["axis"] == "eixo.medido"
        assert restricoes[0]["rules"] == ["SF-A", "SF-B"]
        assert restricoes[0]["reason"]

    def test_a_restricao_nomeia_a_razao_e_nao_proibe_aplicar(self):
        """A §5.4 e literal: sai como restricao de SEQUENCIAMENTO, com a razao
        nomeada -- nunca como proibicao de aplicar."""
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["eixo.medido"]),
                _finding("SF-B", moves=["eixo.medido"]),
            ],
            MEDIDA,
        )
        assert restricoes[0]["reason"] == "same_measure_axis"
        assert "atribu" in restricoes[0]["explanation"]

    def test_uma_acao_sozinha_num_eixo_nao_gera_restricao(self):
        _, restricoes, _ = order_actions([_finding("SF-A", moves=["eixo.medido"])], MEDIDA)
        assert restricoes == []

    def test_eixos_diferentes_nao_geram_restricao(self):
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["eixo.medido"]),
                _finding("SF-B", moves=["outro.medido"]),
            ],
            MEDIDA,
        )
        assert restricoes == []

    def test_duas_acoes_que_so_compartilham_correctness_nao_geram_restricao(self):
        """O teste que trava a decisao de `nature`.

        `correctness.write_result` e `nature: risk` e nao entra em
        `load_measure_axes`. Duas acoes que ambas podem alterar o resultado nao
        tornam o antes/depois inatribuivel -- elas exigem validacao funcional
        de cada uma, que e `funcval`.
        """
        eixos = load_measure_axes()
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["correctness.write_result"]),
                _finding("SF-B", moves=["correctness.write_result"]),
            ],
            eixos,
        )
        assert restricoes == []

    def test_eixo_de_risco_nao_entra_mesmo_ao_lado_de_um_de_medida(self):
        eixos = load_measure_axes()
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["correctness.write_result", "runtime.wall_clock"]),
                _finding("SF-B", moves=["correctness.write_result", "runtime.wall_clock"]),
            ],
            eixos,
        )
        assert [r["axis"] for r in restricoes] == ["runtime.wall_clock"]

    def test_regra_repetida_conta_uma_vez_no_grupo(self):
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["eixo.medido"]),
                _finding("SF-A", moves=["eixo.medido"]),
            ],
            MEDIDA,
        )
        assert restricoes == []

    def test_restricoes_saem_ordenadas_por_eixo(self):
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["outro.medido", "eixo.medido"]),
                _finding("SF-B", moves=["outro.medido", "eixo.medido"]),
            ],
            MEDIDA,
        )
        assert [r["axis"] for r in restricoes] == ["eixo.medido", "outro.medido"]

    def test_sem_eixos_declarados_o_vocabulario_do_repositorio_e_lido(self):
        _, restricoes, _ = order_actions(
            [
                _finding("SF-A", moves=["runtime.wall_clock"]),
                _finding("SF-B", moves=["runtime.wall_clock"]),
            ]
        )
        assert [r["axis"] for r in restricoes] == ["runtime.wall_clock"]


class TestFixturesReais:
    def test_skewed_stage_classifica_o_skew_antes_de_trata_lo(self):
        """`SF-UI-001 -> SF-UI-002` esta escrito no texto da regra, e a fixture
        dispara os dois com `depends_on` E com a aresta derivada de
        `investigate` sobre o mesmo `spark.stage`."""
        findings = _findings_da_fixture("fixtures/eventlog/skewed_stage/expected/findings.json")
        ordem, _, unresolved = order_actions(findings)
        assert unresolved == {}
        assert _antes(ordem, "SF-UI-002", "SF-UI-001")

    def test_python_udf_no_plano_mede_antes_de_reescrever(self):
        findings = _findings_da_fixture("fixtures/plan/python_udf_in_plan/expected/findings.json")
        ordem, _, unresolved = order_actions(findings)
        assert unresolved == {}
        assert _antes(ordem, "SF-PLAN-002", "SF-PLAN-001")

    def test_small_files_ordena_a_origem_antes_da_compactacao_e_restringe_o_eixo(self):
        findings = _findings_da_fixture("fixtures/iceberg/small_files/expected/findings.json")
        ordem, restricoes, unresolved = order_actions(findings)
        assert unresolved == {}
        assert _antes(ordem, "SF-ICE-005", "SF-ICE-001")
        assert [(r["axis"], r["rules"]) for r in restricoes] == [
            ("storage.file_layout", ["SF-ICE-001", "SF-ICE-005"])
        ]

    def test_dois_grafos_no_mesmo_arquivo_compartilham_wall_clock(self):
        findings = _findings_da_fixture(
            "fixtures/graph/dois_grafos_no_mesmo_arquivo/expected/findings.json"
        )
        _, restricoes, unresolved = order_actions(findings)
        assert unresolved == {}
        assert [(r["axis"], r["rules"]) for r in restricoes] == [
            ("runtime.wall_clock", ["SF-GRAPH-003", "SF-GRAPH-004"])
        ]

    def test_folga_medida_sem_skew_nao_tem_o_que_ordenar(self):
        """Uma acao so: ordem de um, nenhuma restricao, nenhuma lacuna."""
        findings = _findings_da_fixture(
            "fixtures/waste/folga_medida_sem_skew/expected/findings.json"
        )
        ordem, restricoes, unresolved = order_actions(findings)
        assert ordem == ["SF-WASTE-001"]
        assert restricoes == []
        assert unresolved == {}


class TestCatalogoInteiro:
    def test_o_catalogo_inteiro_ordena_sem_ciclo(self, findings_do_catalogo):
        """O catalogo inteiro ordena sem ciclo, e nenhuma regra fica pra tras.

        O tamanho esperado e derivado do proprio fixture (todas as regras
        executaveis com `action`), nao fixado a mao -- assim uma regra nova
        no catalogo nao quebra este teste por acidente de contagem.
        """
        ordem, _, unresolved = order_actions(findings_do_catalogo)
        assert unresolved == {}
        assert len(ordem) == len(findings_do_catalogo)
        assert _antes(ordem, "SF-ATH-004", "SF-ATH-001")
        assert _antes(ordem, "SF-UI-002", "SF-UI-001")

    def test_o_maior_grupo_de_restricao_e_wall_clock_com_dez_regras(self, findings_do_catalogo):
        """O numero que a decisao de `nature` comprou.

        Com `correctness.write_result` tratado como medida, o maior grupo teria
        33 regras. So com os eixos de medida sao 10, em `runtime.wall_clock`.
        """
        _, restricoes, _ = order_actions(findings_do_catalogo)
        maior = max(restricoes, key=lambda r: (len(r["rules"]), r["axis"]))
        assert maior["axis"] == "runtime.wall_clock"
        assert len(maior["rules"]) == 10
        assert all(r["axis"] != "correctness.write_result" for r in restricoes)
