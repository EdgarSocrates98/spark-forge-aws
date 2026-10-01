"""Cenarios de holdout: o mesmo formato de `fixtures/scenarios/`, mais uma
propriedade -- e um teste que a PROVA em vez de confiar nela.

A propriedade: nenhum arquivo de `skills/`, `agents/` ou `knowledge/` cita o
nome de um diretorio de `evals/holdout/`. E o que separa "holdout" de "nome de
pasta". O jeito natural de destruir um holdout nao e malicioso, e distraido:
alguem escreve um `SKILL.md` e usa o cenario como exemplo resolvido. A partir
dali, um agente que acerta o caso pode estar lembrando em vez de generalizando,
e a diferenca nao aparece em numero nenhum -- o eval continua verde, medindo
outra coisa.

POR QUE ISTO NAO MORA EM `fixtures/`

`tests/test_fixtures_kind_coverage.py` cobra, para todo diretorio de
`fixtures/`, um modulo golden que o reivindique -- porque ali o proposito e
COBERTURA (todo kind exercitado, toda regra com golden que a dispare). Holdout
nao e cobertura: e a amostra retida justamente para nao ser otimizada contra.
Mante-lo sob `fixtures/` o transformaria em mais um alvo daquele gate, e em
mais um corpus que qualquer varredura de "onde estao os exemplos" encontra
primeiro. A separacao de diretorio e o que torna a regra de citacao
verificavel: `evals/holdout/` e um nome que so aparece aqui e no README dele.

A CONTRAPARTE

Um teste que so proibe citacao passaria com o diretorio vazio. Por isso ele
tambem exige que os cenarios existam, que os goldens batam e que cada um
dispare regra de verdade -- holdout que nao exercita o motor nao mede
generalizacao nenhuma, mede o vazio.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.migration import extract_migration_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.migration.assessment import assess

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "evals" / "holdout"

# Os diretorios cuja prosa INSTRUI um agente. `docs/` fica de fora de proposito:
# documento de engenharia sobre o proprio corpus -- este README, o
# `docs/gates-por-mudanca.md` -- precisa poder nomear o que descreve, e nada em
# `docs/` entra no contexto de um agente em execucao. O criterio e "o agente le
# isso quando trabalha?", nao "o texto existe no repositorio?".
SUPERFICIES_DE_AGENTE = ("skills", "agents", "knowledge")

# Os espelhos gerados de `skills/` e `agents/` (`scripts/sync_skills.py`). Se o
# nome do cenario vazar para a fonte, ele vaza para os espelhos junto -- e o
# espelho e o que a ferramenta de fato carrega. Incluir os dois nao e redundancia:
# um espelho editado a mao (perda de trabalho conhecida, ver
# `docs/gates-por-mudanca.md`) poderia carregar o vazamento sozinho.
ESPELHOS = (".claude", ".agents")

# Extensoes de texto. Um `.jar` de fixture nao "cita" nada, e ler binario aqui
# so produziria falso positivo por coincidencia de bytes.
EXTENSOES_DE_TEXTO = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".xml", ".toml"}


def holdout_dirs():
    if not HOLDOUT.is_dir():
        return []
    return sorted(p for p in HOLDOUT.iterdir() if p.is_dir())


def _nomes():
    return [p.name for p in holdout_dirs()]


def _arquivos_de_superficie():
    for nome in (*SUPERFICIES_DE_AGENTE, *ESPELHOS):
        raiz = ROOT / nome
        if not raiz.is_dir():
            continue
        for arquivo in sorted(raiz.rglob("*")):
            if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_DE_TEXTO:
                yield arquivo


# --------------------------------------------------------------------------- #
# A propriedade que torna estes cenarios holdout
# --------------------------------------------------------------------------- #


def test_no_agent_surface_cites_a_holdout_scenario():
    """A prova. Sem ela, "holdout" e so um nome de pasta.

    Busca pelo NOME do diretorio, que e a chave que um exemplo copiado carrega
    junto (`evals/holdout/<nome>`, `<nome>/input/main.py`, ou o nome solto numa
    tabela). O nome de cada cenario e longo e especifico de proposito -- um
    `clean_job` daria falso positivo com meia duzia de corpus deste repositorio.
    """
    nomes = _nomes()
    assert nomes, "sem cenario nenhum, este teste aprovaria qualquer coisa"

    vazamentos: list[str] = []
    for arquivo in _arquivos_de_superficie():
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        for nome in nomes:
            if nome in texto:
                vazamentos.append(f"{arquivo.relative_to(ROOT).as_posix()} cita {nome}")

    assert not vazamentos, (
        "cenario de holdout citado em superficie que instrui agente: "
        f"{vazamentos}. Um cenario citado deixa de medir generalizacao -- o "
        "agente que o resolve pode estar lembrando. Se o exemplo e necessario, "
        "escreva um cenario em `fixtures/scenarios/`, que existe para ser visivel."
    )


def test_the_holdout_directory_name_itself_is_not_advertised():
    """O caminho `evals/holdout` tambem nao pode aparecer nas superficies.

    Sem esta metade, uma skill poderia dizer "rode os cenarios de
    `evals/holdout/`" sem nomear nenhum -- e um agente que segue a instrucao le
    os dois, o que gasta o holdout inteiro sem citar cenario nenhum.
    """
    vazamentos = [
        arquivo.relative_to(ROOT).as_posix()
        for arquivo in _arquivos_de_superficie()
        if re.search(r"evals[/\\]holdout", arquivo.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not vazamentos, vazamentos


def test_the_surface_scan_is_not_vacuous():
    """Guarda do proprio invariante: se as superficies sumirem ou o filtro de
    extensao parar de casar, os dois testes acima passariam sobre conjunto
    vazio e aprovariam qualquer coisa."""
    arquivos = list(_arquivos_de_superficie())
    assert len(arquivos) >= 100, (
        f"so {len(arquivos)} arquivos de superficie varridos; o filtro "
        "provavelmente parou de casar e a prova de holdout virou assercao sobre "
        "conjunto vazio."
    )
    raizes = {a.relative_to(ROOT).parts[0] for a in arquivos}
    for nome in SUPERFICIES_DE_AGENTE:
        assert nome in raizes, f"`{nome}/` nao foi varrido"


def test_the_holdout_lives_outside_fixtures():
    """A separacao de diretorio nao e cosmetica: e o que torna a regra de
    citacao verificavel, e o que mantem o holdout fora do gate de COBERTURA de
    `tests/test_fixtures_kind_coverage.py` -- holdout nao e cobertura, e a
    amostra retida para nao ser otimizada contra."""
    assert HOLDOUT.is_dir()
    assert not (ROOT / "fixtures" / "holdout").exists()
    for directory in holdout_dirs():
        assert "fixtures" not in directory.relative_to(ROOT).parts


# --------------------------------------------------------------------------- #
# A contraparte: holdout que nao exercita o motor nao mede nada
# --------------------------------------------------------------------------- #


def test_there_are_at_least_two_scenarios():
    assert len(holdout_dirs()) >= 2


def extract(directory: Path):
    """A MESMA extracao de `scripts/regen_fixtures.py::regen_scenario` e de
    `tests/test_fixtures_scenarios.py`."""
    input_dir = directory / "input"
    facts = list(extract_migration_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
    return facts


def run_scenario(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract(directory)
    resultado = assess(facts, source=str(meta["source"]), target=str(meta["target"]))
    return meta, facts, resultado


# ids pre-computados, nunca `ids=lambda` -- ver comentario equivalente em
# `tests/test_fixtures_scenarios.py`.
@pytest.mark.parametrize("directory", holdout_dirs(), ids=[p.name for p in holdout_dirs()])
class TestHoldoutGolden:
    def test_assessment_matches_golden(self, directory):
        _, _, resultado = run_scenario(directory)
        esperado = json.loads(
            (directory / "expected" / "assessment.json").read_text(encoding="utf-8")
        )
        assert resultado.to_dict() == esperado

    def test_declared_rules_are_exactly_the_ones_that_fire(self, directory):
        meta, _, resultado = run_scenario(directory)
        assert sorted({f.rule_id for f in resultado.findings}) == sorted(meta["expects_rules"])

    def test_the_scenario_actually_exercises_the_engine(self, directory):
        _, facts, resultado = run_scenario(directory)
        assert facts
        assert resultado.findings, "holdout sem achado nenhum nao mede generalizacao"

    def test_extraction_is_deterministic(self, directory):
        assert [f.to_dict() for f in extract(directory)] == [
            f.to_dict() for f in extract(directory)
        ]

    def test_the_meta_says_what_the_scenario_proves(self, directory):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        assert meta["name"] == directory.name
        assert len(meta.get("proves", "").strip()) >= 200


class TestOHoldoutNaoRepeteOsVisiveis:
    """Um holdout que repete a forma de um cenario exposto mede o mesmo que
    ele, e gasta a unica propriedade que o torna holdout."""

    @staticmethod
    def _visiveis():
        from tests.test_fixtures_scenarios import fixture_dirs
        from tests.test_fixtures_scenarios import run_scenario as rodar

        return [rodar(d) for d in fixture_dirs()]

    def test_algum_holdout_termina_fora_de_no_go(self):
        """DECISAO 2 de `sparkforge/migration/assessment.py`: o gate de
        compatibilidade separa por SEVERIDADE, nao por presenca. Os tres
        cenarios de `fixtures/scenarios/` disparam P0/P1 e todos fecham em
        NO_GO -- nenhum deles pode medir o outro ramo. O holdout de
        configuracao indireta so dispara P2, entao ele e o unico exemplar de
        PASS_WITH_RISK/CONDITIONAL_GO do repositorio.

        O lado dos visiveis mede a RECOMENDACAO, nao `gates["compatibilidade"]`:
        desde os eixos nomeados da fase H2, `glue_60_fgac_com_jar` fecha em
        `gates["lakeformation"]` e deixa `compatibilidade` em PASS -- um achado
        move um eixo so. O que a frase "todos fecham em NO_GO" sempre quis dizer
        e o desfecho, e ele nao mudou."""
        desfechos = {
            d.name: run_scenario(d)[2].gates["compatibilidade"] for d in holdout_dirs()
        }
        assert "PASS_WITH_RISK" in desfechos.values(), desfechos
        visiveis = {r.recommendation for _, _, r in self._visiveis()}
        assert visiveis == {"NO_GO"}, visiveis

    def test_o_holdout_dispara_regra_que_nenhum_cenario_visivel_dispara(self):
        """Se toda regra do holdout ja aparece nos visiveis, um sistema
        ajustado para os visiveis nao e testado por nada aqui."""
        do_holdout = {
            f.rule_id for d in holdout_dirs() for f in run_scenario(d)[2].findings
        }
        dos_visiveis = {f.rule_id for _, _, r in self._visiveis() for f in r.findings}
        assert do_holdout - dos_visiveis, (do_holdout, dos_visiveis)

    def test_o_holdout_cobre_um_par_de_versoes_que_os_visiveis_nao_cobrem(self):
        pares_holdout = {
            (r.source, r.target) for d in holdout_dirs() for _, _, r in [run_scenario(d)]
        }
        pares_visiveis = {(r.source, r.target) for _, _, r in self._visiveis()}
        assert pares_holdout - pares_visiveis, (pares_holdout, pares_visiveis)

    def test_o_holdout_nao_inventa_regra_fora_do_catalogo(self):
        """Um holdout que exigisse regra nova mediria a regra, nao o sistema."""
        from sparkforge.rules.loader import load_catalog

        do_catalogo = {r["id"] for r in load_catalog()}
        for directory in holdout_dirs():
            meta, _, _ = run_scenario(directory)
            assert set(meta["expects_rules"]) <= do_catalogo, directory.name
