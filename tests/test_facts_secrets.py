"""Corpus de segredo, por VALOR.

O detector tinha tres gatilhos. Dois eram por valor, mas estreitos: access key
id da AWS, e senha embutida em URL. O terceiro exigia que o NOME da chave
sugerisse segredo -- e era ele que teria de pegar todo o resto.

Por isso passava batido todo segredo que chega num campo de nome inocente, que
e exatamente como segredo chega em configuracao de verdade: `config_value`,
`data`, `payload`. Este arquivo fixa o comportamento por VALOR.

Os negativos importam tanto quanto os positivos. Um detector que redige
`s3://bucket/prefixo` ou um sha256 de commit apaga evidencia que a analise
precisa -- e apagar evidencia por medo e o defeito que a fase I2 recusou por
escrito em docs/harness/UNTRUSTED-CONTENT.md.
"""

# Scanner de segredo vai apontar este arquivo, e isso e esperado: a lista
# POSITIVOS existe justamente para conter valor com forma de credencial. Nenhum
# deles e credencial viva -- sao exemplos publicados na documentacao do emissor
# (`AKIAIOSFODNN7EXAMPLE` da AWS, o JWT canonico do jwt.io com assinatura
# truncada) ou fabricados por repeticao de letra, e as chaves privadas sao so o
# cabecalho PEM, sem corpo. Nao ofusque nenhum valor para calar a ferramenta:
# montar a string em runtime esconde do leitor humano o que o teste testa, e
# troca legibilidade por silencio.

import ast
import pathlib

import pytest

from sparkforge.facts.secrets import detectores, looks_like_secret

# (nome_do_caso, chave, valor)
POSITIVOS = [
    ("aws_access_key", "x", "AKIAIOSFODNN7EXAMPLE"),
    ("senha_em_url", "conn", "postgresql://admin:Hunter2@db.internal:5432/prod"),
    ("github_pat_classico", "config_value", "ghp_" + "a" * 36),
    ("github_pat_fine_grained", "data", "github_pat_" + "b" * 22 + "_" + "c" * 59),
    ("jwt", "payload", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVP"),
    ("chave_privada_rsa", "blob", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA"),
    ("chave_privada_openssh", "blob", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaA"),
    ("slack_token", "campo", "xoxb-" + "1" * 12 + "-" + "2" * 24),
]

NEGATIVOS = [
    ("caminho_s3", "spark.sql.warehouse.dir", "s3://bucket/warehouse/prefixo/longo"),
    ("sha_de_commit", "revision", "a" * 40),
    ("booleano", "spark.hadoop.fs.s3a.secret.key", "true"),
    ("tamanho", "spark.sql.files.maxPartitionBytes", "134217728"),
    ("classe_java", "spark.serializer", "org.apache.spark.serializer.KryoSerializer"),
    ("arn", "role", "arn:aws:iam::123456789012:role/GlueETLRole"),
    ("vazio", "password", ""),
]


@pytest.mark.parametrize("nome,chave,valor", POSITIVOS, ids=[c[0] for c in POSITIVOS])
def test_segredo_e_detectado_mesmo_com_nome_de_chave_inocente(nome, chave, valor):
    assert looks_like_secret(chave, valor) is True, (
        f"{nome}: valor com forma de credencial passou batido com chave {chave!r}"
    )


@pytest.mark.parametrize("nome,chave,valor", NEGATIVOS, ids=[c[0] for c in NEGATIVOS])
def test_dado_legitimo_nao_e_redigido(nome, chave, valor):
    assert looks_like_secret(chave, valor) is False, (
        f"{nome}: dado legitimo foi tratado como segredo -- redacao apaga evidencia"
    )


def test_detectores_nomeia_sem_nunca_devolver_o_valor():
    valor = "AKIAIOSFODNN7EXAMPLE"
    nomes = detectores("x", valor)
    assert nomes == ("aws_access_key",)
    assert valor not in " ".join(nomes)


def test_detectores_vazio_para_dado_legitimo():
    assert detectores("spark.sql.warehouse.dir", "s3://bucket/prefixo") == ()


def test_existe_um_unico_detector_de_segredo_no_pacote():
    """Quatro copias da mesma pergunta e como um controle de seguranca apodrece.

    O gate e estrutural, nao comportamental: ele nao pergunta se as copias
    concordam, pergunta se elas existem. Quem escrever a quinta quebra isto
    antes de a quinta divergir -- que e o unico momento em que a divergencia
    ainda e barata de consertar.
    """
    raiz = pathlib.Path(__file__).resolve().parent.parent / "sparkforge"
    definidores = []
    for arquivo in sorted(raiz.rglob("*.py")):
        if "__pycache__" in arquivo.parts:
            continue
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.name.lstrip("_") == "looks_like_secret":
                # `as_posix` e obrigatorio: sem ele o separador vem `\` no
                # Windows e o gate falharia mesmo com uma copia so.
                definidores.append(arquivo.relative_to(raiz).as_posix())
    assert definidores == ["facts/secrets.py"], definidores
