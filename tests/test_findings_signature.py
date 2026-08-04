from sparkforge.findings import signature as sig
from sparkforge.findings.signature import SIGNATURE_RE, compute_signature, normalize_body


def test_reformatar_o_corpo_nao_muda_a_assinatura():
    a = compute_signature(body="## Titulo\n\ntexto\n", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    b = compute_signature(body="## Titulo\n\n\ntexto  \n\n", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    assert a == b


def test_editar_o_conteudo_muda_a_assinatura():
    a = compute_signature(body="ganho de 40%", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    b = compute_signature(body="ganho de 60%", fact_ids=["f_aaa111"],
                          rule_ids=["SF-PY-001"], catalog_version=1, schema_version=1)
    assert a != b


def test_a_ordem_da_evidencia_nao_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=["f_aaa111", "f_bbb222"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=["f_bbb222", "f_aaa111"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    assert a == b


def test_trocar_a_evidencia_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=["f_aaa111"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=["f_ccc333"], rule_ids=[],
                          catalog_version=1, schema_version=1)
    assert a != b


def test_catalogo_diferente_muda_a_assinatura():
    a = compute_signature(body="x", fact_ids=[], rule_ids=[], catalog_version=1, schema_version=1)
    b = compute_signature(body="x", fact_ids=[], rule_ids=[], catalog_version=2, schema_version=1)
    assert a != b


def assinar(body="corpo", fact_ids=("f_aaa111",), rule_ids=("SF-PY-001",),
            catalog_version=1, schema_version=1):
    return compute_signature(
        body=body,
        fact_ids=list(fact_ids),
        rule_ids=list(rule_ids),
        catalog_version=catalog_version,
        schema_version=schema_version,
    )


class TestForma:
    def test_prefixo_e_sha256_inteiro(self):
        assert SIGNATURE_RE.match(assinar())

    def test_mesma_entrada_produz_a_mesma_assinatura(self):
        assert assinar() == assinar()


class TestOQueANormalizacaoAbsorve:
    """Cada item da docstring de `normalize_body`, dos dois lados."""

    def test_crlf_e_cr_nao_invalidam(self):
        assert assinar("linha um\nlinha dois") == assinar("linha um\r\nlinha dois")
        assert assinar("linha um\nlinha dois") == assinar("linha um\rlinha dois")

    def test_espaco_no_fim_da_linha_nao_invalida(self):
        assert assinar("linha um\nlinha dois") == assinar("linha um   \nlinha dois\t")

    def test_espaco_repetido_dentro_da_linha_nao_invalida(self):
        assert assinar("| coluna | valor |") == assinar("| coluna   |   valor |")

    def test_mais_de_uma_linha_em_branco_seguida_nao_invalida(self):
        assert assinar("a\n\nb") == assinar("a\n\n\n\n\nb")

    def test_linha_em_branco_na_borda_do_documento_nao_invalida(self):
        assert assinar("## Titulo\n\ntexto") == assinar("\n\n## Titulo\n\ntexto\n\n\n")

    def test_normalize_body_e_idempotente(self):
        uma_vez = normalize_body("a  b \r\n\n\n\n c\n\n")
        assert normalize_body(uma_vez) == uma_vez


class TestOQueANormalizacaoNaoAbsorve:
    def test_indentacao_invalida(self):
        """Em Markdown quatro espacos sao bloco de codigo; um espaco e prosa."""
        assert assinar("texto\n\n    df.collect()\n") != assinar("texto\n\n df.collect()\n")

    def test_indentacao_de_item_de_lista_invalida(self):
        assert assinar("- a\n  - b\n") != assinar("- a\n- b\n")

    def test_pontuacao_invalida(self):
        assert assinar("o shuffle domina") != assinar("o shuffle domina?")

    def test_ordem_das_palavras_invalida(self):
        assert assinar("skew antes de shuffle") != assinar("shuffle antes de skew")

    def test_numero_invalida(self):
        assert assinar("200 particoes") != assinar("2000 particoes")

    def test_quebra_de_linha_no_meio_de_frase_invalida(self):
        """Uma linha em branco a mais e reformatacao; juntar duas linhas nao e."""
        assert assinar("o job\nfalha") != assinar("o job falha")


class TestOQueOHashCobre:
    def test_repetir_o_mesmo_fact_nao_muda(self):
        assert assinar(fact_ids=["f_aaa111"]) == assinar(fact_ids=["f_aaa111", "f_aaa111"])

    def test_a_ordem_das_regras_nao_muda(self):
        a = assinar(rule_ids=["SF-PY-001", "SF-ICE-002"])
        b = assinar(rule_ids=["SF-ICE-002", "SF-PY-001"])
        assert a == b

    def test_regra_acrescentada_muda(self):
        assert assinar(rule_ids=["SF-PY-001"]) != assinar(rule_ids=["SF-PY-001", "SF-ICE-002"])

    def test_schema_version_diferente_muda(self):
        assert assinar(schema_version=1) != assinar(schema_version=2)

    def test_evidencia_ausente_e_evidencia_presente_diferem(self):
        assert assinar(fact_ids=[]) != assinar(fact_ids=["f_aaa111"])


class TestVersaoDaAssinatura:
    def test_signature_version_entra_no_hash(self, monkeypatch):
        """Mudar a normalizacao sem mudar a versao faria assinatura antiga
        parecer adulterada. A versao dentro do hash separa os dois casos."""
        antes = assinar()
        monkeypatch.setattr(sig, "SIGNATURE_VERSION", 2)
        assert assinar() != antes
