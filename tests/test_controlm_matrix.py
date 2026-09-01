"""A matriz do Control-M Automation API, e a fronteira que `describe` sustenta.

O QUE ESTE ARQUIVO GUARDA, e o que ele deliberadamente NAO guarda.

O drift entre o `.md` e o `.yaml` NAO mora aqui: ele mora em
`tests/test_runtime_matrix_drift.py`, que ja e parametrizado por celula e ja le
tabela de markdown por cabecalho exato. Control-M entrou la como uma entrada em
`PLATAFORMAS` -- 69 chaves x 5 colunas --, e nao como um quinto parser. Escrever
uma segunda comparacao aqui faria a terceira copia da matriz que aquele guard
existe para nao ter.

O que mora aqui e o que aquele guard nao alcanca:

  1. o vocabulario FECHADO estoura mesmo, nos quatro conjuntos;
  2. nenhuma celula fica vazia -- ou tem fronteira com fonte, ou esta em
     `unresolved` com razao;
  3. a FRONTEIRA nao e decorativa: duas versoes respondem DIFERENTE;
  4. versao fora da faixa e recusa NOMEADA, com o intervalo, e nunca a resposta
     da versao vizinha;
  5. toda fonte citada esta em `knowledge/sources.lock.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.controlm import descriptor as cd
from sparkforge.controlm import matrix as cm

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "knowledge" / "controlm" / "automation-api-matrix.yaml"
DOC_PATH = ROOT / "knowledge" / "controlm" / "automation-api-matrix.md"


def _cru() -> dict:
    return yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


class TestOVocabularioEFechado:
    """Chave nova numa entrada e eixo inventado, e tem de estourar na CARGA.

    Nao basta o teste conferir a matriz commitada: o modo pratico de violar isto
    nao e escrever uma chave errada hoje, e alguem daqui a um ano acrescentar
    `deprecated_in` (que nao existe) achando que existe. Entao cada conjunto e
    exercitado contra um documento ADULTERADO em memoria.
    """

    def _carrega(self, tmp_path, monkeypatch, documento):
        destino = tmp_path / "controlm"
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "automation-api-matrix.yaml").write_text(
            yaml.safe_dump(documento, allow_unicode=True), encoding="utf-8"
        )
        monkeypatch.setattr(cm, "knowledge_dir", lambda: tmp_path)
        cm.load.cache_clear()
        cm.covers.cache_clear()
        cm.sources.cache_clear()
        cm.known_versions.cache_clear()
        cm.drift_view.cache_clear()
        try:
            return cm.load()
        finally:
            monkeypatch.undo()
            cm.load.cache_clear()
            cm.covers.cache_clear()
            cm.sources.cache_clear()
            cm.known_versions.cache_clear()
            cm.drift_view.cache_clear()

    def test_chave_nova_no_documento_estoura(self, tmp_path, monkeypatch):
        documento = _cru()
        documento["versions"] = {"9.0.21.200": {}}
        with pytest.raises(cm.ControlMMatrixError, match="versions"):
            self._carrega(tmp_path, monkeypatch, documento)

    def test_chave_nova_numa_capacidade_estoura(self, tmp_path, monkeypatch):
        documento = _cru()
        documento["capabilities"]["job_detached_embedded_script"]["deprecated_in"] = "9.0.22.100"
        with pytest.raises(cm.ControlMMatrixError, match="deprecated_in"):
            self._carrega(tmp_path, monkeypatch, documento)

    def test_capacidade_sem_fronteira_estoura(self, tmp_path, monkeypatch):
        """Capacidade sem versao e afirmacao sem fronteira -- exatamente o que
        esta matriz existe para nao produzir. Ou tem fronteira, ou vai para
        `unresolved` com a razao."""
        documento = _cru()
        entrada = documento["capabilities"]["job_detached_embedded_script"]
        for fronteira in cm.BOUNDARIES:
            entrada.pop(fronteira, None)
        with pytest.raises(cm.ControlMMatrixError, match="sem fronteira"):
            self._carrega(tmp_path, monkeypatch, documento)

    def test_chave_nova_numa_celula_de_componente_estoura(self, tmp_path, monkeypatch):
        documento = _cru()
        documento["components"]["java"]["9.0.21.325"]["recommended"] = "21"
        with pytest.raises(cm.ControlMMatrixError, match="recommended"):
            self._carrega(tmp_path, monkeypatch, documento)

    def test_recusa_sem_razao_estoura(self, tmp_path, monkeypatch):
        """Recusa sem razao e omissao com nome bonito. Ver a §20 do CLAUDE.md."""
        documento = _cru()
        documento["unresolved"]["9.0.22.100"] = {}
        with pytest.raises(cm.ControlMMatrixError, match="9.0.22.100"):
            self._carrega(tmp_path, monkeypatch, documento)


class TestNenhumaCelulaFicaVazia:
    """A cobranca da §5 da spec: fronteira com fonte, ou `unresolved` com razao."""

    def test_toda_capacidade_tem_resumo_e_fronteira(self):
        for slug, entrada in cm.load()["capabilities"].items():
            assert entrada.get("summary", "").strip(), slug
            assert [b for b in cm.BOUNDARIES if entrada.get(b)], slug

    def test_toda_celula_de_componente_tem_exigencia_ou_valor(self):
        for nome, versoes in cm.load()["components"].items():
            for versao, celula in versoes.items():
                assert celula.get("summary", "").strip(), f"{nome}[{versao}]"
                assert any(
                    c in celula for c in ("minimum", "unsupported", "supported", "value")
                ), f"{nome}[{versao}]"

    def test_toda_recusa_tem_razao(self):
        for chave, entrada in cm.load()["unresolved"].items():
            assert entrada.get("reason", "").strip(), chave

    def test_as_31_versoes_da_faixa_estao_cobertas(self):
        """As 31 versoes que a pagina cita na faixa estao TODAS na matriz -- 22
        com afirmacao e 9 recusadas por nome. Uma versao lida e sem achado e
        resposta diferente de uma versao nunca olhada, e a matriz precisa
        distinguir as duas."""
        conhecidas = cm.known_versions()
        assert len(conhecidas) == 31, conhecidas
        piso, teto = cm.covers()
        assert conhecidas[0] == piso and conhecidas[-1] == teto

        documento = cm.load()
        com_afirmacao = {
            str(entrada[b])
            for entrada in documento["capabilities"].values()
            for b in cm.BOUNDARIES
            if entrada.get(b)
        }
        com_afirmacao |= {
            str(v) for versoes in documento["components"].values() for v in versoes
        }
        # `9.0.21.100` e fronteira REAL e esta abaixo do piso; ela nao conta como
        # versao coberta, e a distincao esta escrita na §3 do .md.
        na_faixa = {v for v in com_afirmacao if v in conhecidas}
        assert len(na_faixa) == 22, sorted(na_faixa)

        sem_afirmacao = [v for v in conhecidas if v not in na_faixa]
        assert len(sem_afirmacao) == 9, sem_afirmacao
        recusas = documento["unresolved"]
        for versao in sem_afirmacao:
            assert versao in recusas, f"{versao} ficou sem afirmacao E sem recusa"

    def test_os_dois_eixos_tem_o_tamanho_medido(self):
        documento = cm.load()
        assert len(documento["capabilities"]) == 51
        assert sum(len(v) for v in documento["components"].values()) == 6
        assert len(documento["unresolved"]) == 12


class TestAFronteiraNaoEDecorativa:
    """O contrafactual que a §5 da spec cobra.

    Se `describe` de duas versoes de lados opostos de uma fronteira respondesse
    IGUAL, a fronteira seria enfeite -- a matriz teria versoes escritas e nenhuma
    delas mudaria resposta. Este teste e o que fica vermelho se alguem trocar a
    fronteira por um valor constante.
    """

    def test_job_detached_embedded_script_muda_de_lado(self):
        antes = cd.describe("9.0.21.300")
        depois = cd.describe("9.0.22.010")
        assert "job_detached_embedded_script" not in antes.capabilities
        assert "job_detached_embedded_script" in depois.capabilities
        assert (
            depois.capabilities["job_detached_embedded_script"]["declared_at"]
            == "9.0.22.005"
        )

    def test_a_exigencia_de_java_muda_de_lado_no_outro_eixo(self):
        """O contrafactual vale nos DOIS eixos, e nao so no de capacidade."""
        antes = cd.describe("9.0.21.320")
        depois = cd.describe("9.0.21.325")
        assert "java" not in antes.components
        assert depois.components["java"]["minimum"] == "17"
        assert depois.components["java"]["unsupported"] == ["11"]
        assert depois.components["java"]["declared_at"] == "9.0.21.325"

    def test_a_depreciacao_sai_em_deprecated_e_nao_em_capabilities(self):
        """`config em:param::set` esta DEPRECIADO a partir de `9.0.21.300`.
        Coloca-lo em `capabilities` faria o operador le-lo como disponivel."""
        descritor = cd.describe("9.0.21.300")
        assert "config_em_param_set" in descritor.deprecated
        assert "config_em_param_set" not in descritor.capabilities
        assert (
            descritor.deprecated["config_em_param_set"]["replaced_by"]
            == "config systemsettings::set"
        )

    def test_o_numero_de_capacidades_cresce_monotonicamente_na_faixa(self):
        """A composicao e leitura de fronteira: uma capacidade introduzida nao
        desaparece na versao seguinte. Se este teste cair, `describe` passou a
        responder por versao isolada em vez de acumular."""
        anterior = -1
        for versao in cm.known_versions():
            total = len(cd.describe(versao).capabilities) + len(
                cd.describe(versao).deprecated
            )
            assert total >= anterior, versao
            anterior = total

    def test_declared_here_e_so_o_que_nasce_naquela_versao(self):
        descritor = cd.describe("9.0.22.005")
        assert descritor.declared_here == ("job_detached_embedded_script",)


class TestARecusaENomeada:
    def test_acima_do_teto_e_recusa_com_o_intervalo(self):
        """`9.0.22.125` EXISTE na fonte -- e agosto de 2026 -- e esta acima do
        teto. A recusa nao e "numero invalido": e a recusa de extrapolar."""
        with pytest.raises(cd.UnknownVersion) as exc:
            cd.describe("9.0.22.125")
        assert exc.value.kind == cd.VERSION_OUTSIDE_RANGE
        assert "9.0.21.200" in str(exc.value)
        assert "9.0.22.100" in str(exc.value)

    def test_abaixo_do_piso_e_recusa_com_o_intervalo(self):
        with pytest.raises(cd.UnknownVersion) as exc:
            cd.describe("9.0.21.130")
        assert exc.value.kind == cd.VERSION_OUTSIDE_RANGE

    def test_dentro_da_faixa_e_nao_publicada_e_a_OUTRA_recusa(self):
        """A fonte anda de 5 em 5. `9.0.21.301` esta DENTRO da faixa e nao
        existe, e responder pelo degrau de baixo seria interpolar entre duas
        versoes observadas -- o que a §12 do CLAUDE.md proibe."""
        with pytest.raises(cd.UnknownVersion) as exc:
            cd.describe("9.0.21.301")
        assert exc.value.kind == cd.VERSION_NOT_PUBLISHED
        assert "conhecidas:" in str(exc.value)

    def test_as_duas_recusas_tem_nomes_diferentes(self):
        """Colapsa-las faria o operador procurar no lugar errado: uma destrava
        com uma DECISAO de ampliar a faixa mais leitura, a outra com uma leitura
        que mostre que a versao existe."""
        assert cd.VERSION_OUTSIDE_RANGE != cd.VERSION_NOT_PUBLISHED

    def test_a_ordenacao_de_versao_nao_depende_de_zero_a_esquerda(self):
        """`9.0.22.005` < `9.0.22.010` por INTEIRO, nao por string. A comparacao
        lexicografica da certo aqui por acidente, enquanto os campos tiverem a
        mesma largura -- e depender disso e depender de a BMC nunca publicar
        `9.0.22.5`."""
        assert cm.version_key("9.0.22.5") < cm.version_key("9.0.22.010")
        assert cm.version_key("9.0.21.99") < cm.version_key("9.0.21.100")


class TestAProcedencia:
    def test_toda_fonte_citada_esta_no_lock(self):
        """URL solta na matriz, sem entrada em `knowledge/sources.lock.json`,
        nao teria hash nem data revalidados por `scripts/refresh_knowledge.py`."""
        lock = json.loads(
            (ROOT / "knowledge" / "sources.lock.json").read_text(encoding="utf-8")
        )
        for url in cm.sources():
            assert url in lock["sources"], url

    def test_a_pagina_declara_a_mesma_fonte_que_o_yaml(self):
        texto = DOC_PATH.read_text(encoding="utf-8")
        for url in cm.sources():
            assert url in texto, url

    def test_a_pagina_avisa_do_403_de_user_agent(self):
        """Quem for revalidar sem saber disso vai concluir que a fonte morreu.
        O aviso e mecanismo de coleta, nao detalhe de operacao."""
        texto = DOC_PATH.read_text(encoding="utf-8")
        assert "403" in texto
        assert "user-agent" in texto.lower()
        assert "WebFetch" in texto

    def test_a_pagina_declara_o_procedimento_do_drift_mensal(self):
        texto = DOC_PATH.read_text(encoding="utf-8")
        assert "passado fechado" in texto.lower()
        assert "errata" in texto.lower()

    def test_o_descritor_carrega_fonte_e_data(self):
        descritor = cd.describe("9.0.21.300")
        assert descritor.sources
        assert descritor.retrieved == "2026-09-01"


class TestOEscopoEDoAutomationAPI:
    """A D-5 da spec: a matriz e do Automation API, nao do produto Control-M."""

    def test_a_pagina_declara_o_limite_no_cabecalho(self):
        texto = DOC_PATH.read_text(encoding="utf-8")
        cabecalho = texto[: texto.index("## 1.")]
        assert "não do produto Control-M" in cabecalho

    def test_o_produto_sai_como_recusa_nomeada(self):
        recusas = cm.load()["unresolved"]
        assert "control_m_product_versions" in recusas

    def test_o_topo_da_faixa_e_recusa_e_nao_afirmacao(self):
        """`9.0.22.100` e o TOPO da faixa que o operador pediu, e a pagina a cita
        so como pre-requisito de Control-M/Agent e de Control-M/EM. Ela e
        descrita -- a faixa nao tem buraco --, e o que ela responde e a recusa."""
        descritor = cd.describe("9.0.22.100")
        assert descritor.declared_here == ()
        assert "9.0.22.100" in descritor.unresolved

    def test_as_175_linhas_de_defeito_corrigido_ficam_fora_dos_dois_eixos(self):
        recusas = cm.load()["unresolved"]
        assert "175" in recusas["corrected_problems"]["reason"]


class TestDescribeAll:
    def test_as_31_versoes_descrevem_sem_estourar(self):
        assert len(cd.describe_all()) == 31

    def test_toda_saida_serializa_e_declara_a_faixa(self):
        for descritor in cd.describe_all():
            saida = descritor.to_dict()
            json.dumps(saida)
            assert saida["covers"] == {"from": "9.0.21.200", "to": "9.0.22.100"}
            assert saida["unresolved"], saida["version"]
