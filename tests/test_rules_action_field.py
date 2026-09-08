"""Gate do campo `action`.

Duas direcoes, e as duas importam: toda regra executavel declara `action`, e
todo `kind` do vocabulario tem ao menos uma regra que o usa. Sem a segunda, o
vocabulario incha com entrada morta e ninguem percebe.

`PENDENTES` encolhe a cada lote da Fase 2 e chega a conjunto vazio na Tarefa 10.

`TestAxisNature` e `TestExecutorInvariants` guardam o defeito medido de
`correctness.write_result`: tratado como grandeza, ele produzia par de
contradicao falso (SF-PLAN-003 x SF-PY-009) e inflava o maior grupo de
restricao de sequenciamento para 33 regras. `nature` fecha os dois -- e estes
testes travam o resultado de hoje para que um eixo-guarda-chuva futuro nao
volte a passar em silencio.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path

import pytest
import yaml

from sparkforge.findings.models import Finding
from sparkforge.rules.loader import CatalogError, _validate_action, catalog_dir, load_catalog

_OPOSTAS = (frozenset({"increase", "decrease"}), frozenset({"add", "remove"}))

# Arquivos ainda sem `action`. Encolheu a cada lote da Fase 2 e chegou a vazio no
# lote G (Tarefa 10): as 112 regras executaveis declaram `action`. Conjunto vazio
# ACORDA `test_todo_kind_do_vocabulario_tem_regra` e
# `test_todo_eixo_do_vocabulario_tem_regra`, que so valem com o catalogo inteiro
# preenchido -- e foram eles que mandaram apagar dez `kind` mortos do
# vocabulario. Se um lote futuro precisar reabrir a lista, saiba que reabri-la
# desliga os dois gates junto.
PENDENTES: set[str] = set()


def _vocabulary() -> dict:
    path = catalog_dir() / "action_kinds.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _rule_files() -> dict[str, str]:
    """rule_id -> nome do arquivo que o declara."""
    origem: dict[str, str] = {}
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        if path.name in {"routing.yaml", "action_kinds.yaml"}:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in data.get("rules") or []:
            origem[rule["id"]] = path.name
    return origem


class TestActionField:
    def test_toda_executavel_declara_action(self):
        origem = _rule_files()
        faltando = [
            r["id"]
            for r in load_catalog()
            if r.get("executable", True)
            and origem.get(r["id"]) not in PENDENTES
            and "action" not in r
        ]
        assert faltando == [], f"regras executaveis sem `action`: {faltando}"

    def test_kind_esta_no_vocabulario(self):
        vocab = set(_vocabulary()["kinds"])
        fora = [
            (r["id"], r["action"]["kind"])
            for r in load_catalog()
            if "action" in r and r["action"]["kind"] not in vocab
        ]
        assert fora == [], f"kind fora do vocabulario: {fora}"

    def test_todo_kind_do_vocabulario_tem_regra(self):
        if PENDENTES:
            return  # so vale com o catalogo inteiro preenchido
        vocab = set(_vocabulary()["kinds"])
        usados = {r["action"]["kind"] for r in load_catalog() if "action" in r}
        mortos = sorted(vocab - usados)
        assert mortos == [], f"kind no vocabulario sem regra que o use: {mortos}"

    def test_eixo_esta_no_vocabulario(self):
        """Sem vocabulario fechado de eixo, um lote escreve `runtime.wall_clock` e
        outro escreve `wall_clock`, e a restricao do executor -- duas acoes que
        compartilham eixo nao entram no mesmo run -- nunca dispara."""
        vocab = set(_vocabulary()["axes"])
        fora = [
            (r["id"], eixo)
            for r in load_catalog()
            if "action" in r
            for eixo in r["action"].get("moves") or []
            if eixo not in vocab
        ]
        assert fora == [], f"eixo fora do vocabulario: {fora}"

    def test_todo_eixo_do_vocabulario_tem_regra(self):
        if PENDENTES:
            return  # so vale com o catalogo inteiro preenchido
        vocab = set(_vocabulary()["axes"])
        usados = {
            eixo
            for r in load_catalog()
            if "action" in r
            for eixo in r["action"].get("moves") or []
        }
        mortos = sorted(vocab - usados)
        assert mortos == [], f"eixo no vocabulario sem regra que o mova: {mortos}"

    def test_todo_eixo_declara_nature(self):
        """Sem `nature`, o executor nao sabe se o eixo e grandeza comparavel
        (`measure`) ou risco de semantica (`risk`) -- e e essa distincao que
        separa contradicao real de falso positivo (ver TestAxisNature)."""
        axes = _vocabulary()["axes"]
        faltando = sorted(nome for nome, corpo in axes.items() if "nature" not in corpo)
        assert faltando == [], f"eixo sem `nature`: {faltando}"

    def test_nature_so_admite_measure_ou_risk(self):
        axes = _vocabulary()["axes"]
        invalidas = sorted(
            (nome, corpo.get("nature"))
            for nome, corpo in axes.items()
            if corpo.get("nature") not in {"measure", "risk"}
        )
        assert invalidas == [], f"`nature` fora do vocabulario fechado: {invalidas}"


class TestActionShape:
    def test_direction_invalida_recusa(self):
        with pytest.raises(CatalogError, match="direction"):
            _validate_action(
                "SF-X-001",
                {"action": {"kind": "k", "target": "t", "direction": "aumentar"}},
            )

    def test_chave_desconhecida_recusa(self):
        with pytest.raises(CatalogError, match="desconhecidas"):
            _validate_action(
                "SF-X-001",
                {
                    "action": {
                        "kind": "k",
                        "target": "t",
                        "direction": "increase",
                        "expected_gain": "-31%",
                    }
                },
            )

    def test_nao_executavel_com_action_recusa(self):
        with pytest.raises(CatalogError, match="nao executavel"):
            _validate_action(
                "SF-ARCH-001",
                {
                    "executable": False,
                    "action": {"kind": "k", "target": "t", "direction": "increase"},
                },
            )

    def test_ausencia_de_action_passa(self):
        _validate_action("SF-X-001", {})


class TestFindingCarregaAction:
    def test_finding_tem_campo_action(self):
        f = Finding(
            rule_id="SF-WASTE-001",
            title="t",
            severity="P2",
            confidence="medium",
            status="confirmed",
            subject={"job": "x"},
            evidence=["f_abc123"],
            action={
                "kind": "capacity.investigate_sizing",
                "target": "glue.number_of_workers",
                "direction": "investigate",
            },
        )
        assert f.to_dict()["action"]["direction"] == "investigate"

    def test_action_ausente_e_dict_vazio(self):
        f = Finding(
            rule_id="SF-X-001",
            title="t",
            severity="P2",
            confidence="medium",
            status="confirmed",
            subject={},
            evidence=["f_abc123"],
        )
        assert f.to_dict()["action"] == {}


def _measure_axes() -> set[str]:
    axes = _vocabulary()["axes"]
    return {nome for nome, corpo in axes.items() if corpo.get("nature") == "measure"}


def _acoes_por_regra() -> dict[str, dict]:
    return {r["id"]: r["action"] for r in load_catalog() if r.get("action")}


def _pares_de_contradicao_direta(
    acoes: dict[str, dict], medida: set[str]
) -> list[tuple[str, str, list[str]]]:
    """Mesmo `target`, direcoes opostas, interseccao de `moves` restrita a
    eixos `nature: measure` nao vazia. Espelha o calculo do item 5 do prompt
    de tarefa -- `correctness.write_result` (nature: risk) nao participa, e e
    essa exclusao que evita o par falso SF-PLAN-003 x SF-PY-009."""
    pares = []
    for a, b in combinations(sorted(acoes), 2):
        acao_a, acao_b = acoes[a], acoes[b]
        if acao_a["target"] != acao_b["target"]:
            continue
        if frozenset({acao_a["direction"], acao_b["direction"]}) not in _OPOSTAS:
            continue
        compartilhado = sorted((set(acao_a["moves"]) & set(acao_b["moves"])) & medida)
        if compartilhado:
            pares.append((a, b, compartilhado))
    return pares


class TestAxisNature:
    """Trava as duas medidas que a introducao de `nature` protege. Uma mudanca
    futura no catalogo que reintroduza um eixo-guarda-chuva (do jeito que
    `correctness.write_result` era, antes de virar `risk`) derruba um dos
    dois testes abaixo -- e e essa falha que acusa o defeito, em vez de deixar
    passar em silencio como aconteceu da primeira vez.
    """

    def test_contradicao_direta_produz_exatamente_os_pares_de_hoje(self):
        """`dependency.delivered_artifacts` e `nature: risk` (estado ternario
        declared/unknown/absent no extrator de Terraform, nunca uma contagem
        em `measures` -- ver o comentario do eixo em `action_kinds.yaml`), e
        e o UNICO eixo que SF-GRAPH-005 (declarar o jar de GraphFrames) e
        SF-LF-001 (remove-lo por FGAC) compartilham. Com `nature` aplicado de
        verdade -- e nao so excluindo `correctness.write_result` a mao --, a
        interseccao de `moves` restrita a `measure` fica vazia entre as duas,
        e a contradicao direta de hoje e a lista vazia. Isto e o resultado
        medido, nao o resultado desejado: se um lote futuro passar a medir
        artefato entregue como contagem (`measures`), este teste e quem deve
        mudar primeiro, com o motivo escrito no commit.
        """
        pares = _pares_de_contradicao_direta(_acoes_por_regra(), _measure_axes())
        assert pares == [], f"contradicao direta mudou: {pares}"

    def test_maior_grupo_de_eixo_medida_nao_cresce_sem_aviso(self):
        """Publica o maior grupo de regras que compartilham um eixo
        `nature: measure` -- o numero que a restricao de sequenciamento do
        executor usa para recusar duas acoes no mesmo run. Hoje e 10
        (`runtime.wall_clock`). O teto carrega folga de proposito (2 regras)
        para nao quebrar a cada regra nova que mede tempo de relogio; um
        salto alem da folga e o sinal de um eixo virando guarda-chuva de novo.
        """
        MAIOR_GRUPO_HOJE = 10
        FOLGA = 2
        medida = _measure_axes()
        grupos: dict[str, list[str]] = defaultdict(list)
        for rule_id, acao in _acoes_por_regra().items():
            for eixo in acao["moves"]:
                if eixo in medida:
                    grupos[eixo].append(rule_id)
        tamanho, eixo = max(((len(v), k) for k, v in grupos.items()), default=(0, ""))
        assert tamanho <= MAIOR_GRUPO_HOJE + FOLGA, (
            f"maior grupo de eixo medida cresceu para {tamanho} ({eixo}), "
            f"acima do teto de {MAIOR_GRUPO_HOJE + FOLGA} "
            f"(hoje={MAIOR_GRUPO_HOJE} + folga={FOLGA})"
        )
