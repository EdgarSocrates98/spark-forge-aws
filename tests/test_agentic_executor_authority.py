"""Testes do mapa de autoridade de fonte do executor agentico.

Cobre as duas perguntas que a camada agentica ja separa:
- o TIER da fonte (`tier_for_url`), que e so a autoridade;
- o ESCOPO (`in_scope`), que e a vigencia da fonte contra o runtime alvo.

Uma T1 fora da versao alvo tem autoridade e nao sustenta a claim -- e por isso
as duas funcoes sao separadas e testadas separadas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.agentic.executor.authority import (
    in_scope,
    load_authority_map,
    tier_for_url,
)
from sparkforge.agentic.models import EvidenceAuthority


@pytest.fixture(scope="module")
def mapping() -> dict[str, object]:
    return load_authority_map()


class TestLoadAuthorityMap:
    def test_carrega_do_caminho_default(self, mapping):
        assert mapping["schema_version"] == 1
        assert isinstance(mapping["hosts"], dict)
        assert mapping["hosts"], "o mapa nao pode sair vazio"

    def test_default_e_um_membro_do_enum(self, mapping):
        assert isinstance(mapping["default"], EvidenceAuthority)

    def test_todo_valor_de_host_e_membro_do_enum(self, mapping):
        for host, tier in mapping["hosts"].items():
            assert isinstance(tier, EvidenceAuthority), f"{host} nao virou enum"

    def test_nenhum_host_e_classificado_t3(self, mapping):
        # T3 e benchmark reproduzivel. Host nao prova reprodutibilidade, entao
        # nenhuma entrada do mapa pode alegar T3.
        tiers = set(mapping["hosts"].values()) | {mapping["default"]}
        assert EvidenceAuthority.T3_REPRODUCIBLE_BENCHMARK not in tiers

    def test_caminho_inexistente_falha_alto(self, tmp_path: Path):
        # Mapa ausente nao pode virar "tudo default" em silencio: o default
        # existe para host DESCONHECIDO, nao para arquivo desaparecido.
        with pytest.raises(FileNotFoundError):
            load_authority_map(tmp_path / "nao-existe.yaml")


class TestTierForUrl:
    def test_doc_oficial_aws_e_t1(self, mapping):
        url = "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming.html"
        assert tier_for_url(url, mapping) == EvidenceAuthority.T1_OFFICIAL_DOCS

    def test_doc_oficial_spark_e_t1(self, mapping):
        url = "https://spark.apache.org/docs/3.5.4/sql-performance-tuning.html"
        assert tier_for_url(url, mapping) == EvidenceAuthority.T1_OFFICIAL_DOCS

    def test_codigo_fonte_github_e_t2(self, mapping):
        url = "https://github.com/apache/iceberg/blob/apache-iceberg-1.10.0/core/x.java"
        assert tier_for_url(url, mapping) == EvidenceAuthority.T2_SOURCE_CODE

    def test_raw_githubusercontent_e_t2(self, mapping):
        url = "https://raw.githubusercontent.com/apache/spark/master/README.md"
        assert tier_for_url(url, mapping) == EvidenceAuthority.T2_SOURCE_CODE

    def test_host_desconhecido_cai_no_default(self, mapping):
        url = "https://blog.exemplo-que-ninguem-cita.com/post/spark"
        assert tier_for_url(url, mapping) == mapping["default"]

    def test_blog_da_aws_nao_e_t1(self, mapping):
        # `aws.amazon.com` serve blog, what's-new e pricing; `docs.aws.amazon.
        # com` serve a referencia. Sao hosts diferentes e tiers diferentes.
        blog = tier_for_url("https://aws.amazon.com/blogs/big-data/x", mapping)
        docs = tier_for_url("https://docs.aws.amazon.com/glue/x.html", mapping)
        assert blog != EvidenceAuthority.T1_OFFICIAL_DOCS
        assert docs == EvidenceAuthority.T1_OFFICIAL_DOCS

    def test_host_e_case_insensitive(self, mapping):
        url = "https://DOCS.AWS.Amazon.COM/glue/latest/dg/x.html"
        assert tier_for_url(url, mapping) == EvidenceAuthority.T1_OFFICIAL_DOCS

    def test_porta_no_host_nao_atrapalha(self, mapping):
        url = "https://spark.apache.org:443/docs/latest/"
        assert tier_for_url(url, mapping) == EvidenceAuthority.T1_OFFICIAL_DOCS

    def test_url_vazia_cai_no_default(self, mapping):
        assert tier_for_url("", mapping) == mapping["default"]

    def test_url_malformada_cai_no_default(self, mapping):
        # Nao explode: URL ilegivel e host DESCONHECIDO, e host desconhecido ja
        # tem resposta declarada -- o default.
        assert tier_for_url("::isto nao e uma url::", mapping) == mapping["default"]

    def test_url_sem_host_cai_no_default(self, mapping):
        assert tier_for_url("/glue/latest/dg/index.html", mapping) == mapping["default"]

    def test_url_none_cai_no_default(self, mapping):
        assert tier_for_url(None, mapping) == mapping["default"]  # type: ignore[arg-type]

    def test_mapa_sem_default_usa_t4(self, mapping):
        # Mapa sem `default` declarado nao pode promover host desconhecido:
        # cai no piso conservador, T4.
        assert tier_for_url("https://x.invalid/", {"hosts": {}}) == (
            EvidenceAuthority.T4_RECOGNIZED_AUTHORITY
        )


class TestInScope:
    def test_escopo_vazio_vale_em_qualquer_versao(self):
        assert in_scope({}, {"glue": "5.0", "spark": "3.5.4"}) is True

    def test_versao_dentro_da_lista_esta_em_escopo(self):
        assert in_scope({"glue": ["4.0", "5.0"]}, {"glue": "5.0"}) is True

    def test_versao_fora_da_lista_esta_fora_de_escopo(self):
        assert in_scope({"glue": ["4.0", "5.0"]}, {"glue": "3.0"}) is False

    def test_chave_nao_declarada_pelo_runtime_recusa_em_vez_de_aprovar(self):
        # A regra fala de Glue e o case nao diz qual Glue roda. Nao da para
        # AFIRMAR que esta dentro, e afirmar que esta fora inventaria o
        # contrario. Das duas saidas erradas possiveis, esta recusa.
        assert in_scope({"glue": ["4.0", "5.0"]}, {"spark": "3.5.4"}) is False

    def test_runtime_vazio_com_escopo_nomeado_recusa(self):
        assert in_scope({"glue": ["5.0"]}, {}) is False

    def test_todas_as_chaves_do_escopo_precisam_bater(self):
        escopo = {"glue": ["5.0"], "iceberg": ["1.6", "1.7"]}
        assert in_scope(escopo, {"glue": "5.0", "iceberg": "1.7"}) is True
        assert in_scope(escopo, {"glue": "5.0", "iceberg": "1.4"}) is False
        assert in_scope(escopo, {"glue": "5.0"}) is False

    def test_valor_escalar_no_escopo_vale_como_lista_de_um(self):
        assert in_scope({"glue": "5.0"}, {"glue": "5.0"}) is True
        assert in_scope({"glue": "5.0"}, {"glue": "4.0"}) is False

    def test_comparacao_de_versao_e_por_string_normalizada(self):
        assert in_scope({"glue": ["5.0"]}, {"glue": " 5.0 "}) is True

    def test_escopo_none_vale_em_qualquer_versao(self):
        assert in_scope(None, {"glue": "5.0"}) is True  # type: ignore[arg-type]
