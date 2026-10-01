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

TRES CLASSES DE CASO QUE UM TESTE DE MUTACAO EXIGIU, e o que cada uma trava:

`POSITIVOS_EMBUTIDOS` poe a credencial no MEIO do valor. Sem eles, todo positivo
dos padroes de `_PADROES_POR_VALOR` comecava no indice 0 -- `senha_em_url` era o
unico que nao, e ele exercita `_URL_PASSWORD_RE`, que e outro ramo. Por isso
trocar `search` por `match` no laco da tupla nao quebrava teste nenhum, e o `\\b`
de cada padrao ficava sem prova. A forma embutida e a real em argumento de
bootstrap, corpo de JSON e cabecalho HTTP.

`QUASE_VALIDOS` sao negativos a um caractere de virar positivo: AKIA com 15 e
com 17, `ghp_` com 35. Sem eles, afrouxar qualquer piso de comprimento para
`{1,}` passava em tudo, e o piso e o que separa o padrao de um prefixo solto.

`POSITIVOS_POR_NOME_DE_CHAVE` cobre o terceiro gatilho, que nao tinha positivo
nenhum: todo o corpus provava so os dois primeiros. Apagar o gatilho do nome da
chave nao quebrava teste algum, e e ele que pega segredo proprietario -- o que
nao tem prefixo publicado por emissor nenhum.
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

from sparkforge.facts.secrets import (
    _PADROES_POR_VALOR,
    REDACTED,
    detectores,
    looks_like_secret,
    redact,
)

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

# (nome_do_caso, chave, valor, detector_esperado). A credencial NUNCA comeca no
# indice 0 -- e essa a unica diferenca que importa aqui. Cada forma e a que o
# valor tem quando chega de verdade: linha de comando de bootstrap, corpo de
# JSON, cabecalho HTTP, query string, blob de certificado.
POSITIVOS_EMBUTIDOS = [
    (
        "aws_em_argumento_de_bootstrap",
        "arg",
        "--access-key AKIAIOSFODNN7EXAMPLE --region us-east-1",
        "aws_access_key",
    ),
    ("aws_em_json", "body", '{"aws_access_key_id": "AKIAIOSFODNN7EXAMPLE"}', "aws_access_key"),
    ("github_em_header", "header", "Authorization: token ghp_" + "a" * 36, "github_token"),
    (
        "github_pat_em_json",
        "body",
        '{"pat": "github_pat_' + "b" * 22 + "_" + "c" * 59 + '"}',
        "github_pat",
    ),
    (
        "jwt_em_bearer",
        "header",
        "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVP",
        "jwt",
    ),
    (
        "slack_em_query_string",
        "url",
        "https://hooks.slack.com/services?token=xoxb-" + "1" * 12 + "-" + "2" * 24,
        "slack_token",
    ),
    (
        "pem_dentro_de_blob",
        "blob",
        "certificado gerado em 2026\n-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIA",
        "private_key",
    ),
]

# O terceiro gatilho: nao ha prefixo publicado para casar, so o nome da chave
# denuncia. E o unico caminho ate segredo proprietario -- senha de banco interno,
# chave de HMAC da propria casa. O valor e a secret access key de exemplo da
# documentacao da AWS, que de proposito NAO tem prefixo reconhecivel.
POSITIVOS_POR_NOME_DE_CHAVE = [
    (
        "segredo_proprietario",
        "spark.hadoop.fs.s3a.secret.key",
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    ),
]

# O gatilho 3 (nome da chave + forma de material criptografico) acusava estes
# ate a revisao final de EMR on EKS. Todos sao IDENTIFICADOR SEGMENTADO -- nome
# de classe Java totalmente qualificado, ou nome de service account do
# Kubernetes -- e nenhum e material criptografico. Dois deles sao o pior defeito
# que uma regra pode ter: `credentials.provider` apontando para um provider de
# papel e a configuracao que existe PARA nao haver credencial literal, e
# `serviceAccountName` e o idioma canonico do EMR on EKS. Um P0 sobre eles manda
# o operador desfazer o que esta certo, e a redacao ainda apaga o valor do
# handoff antes de a regra chegar.
IDENTIFICADORES_SEGMENTADOS = [
    (
        "provider_de_credencial_por_papel",
        "spark.hadoop.fs.s3a.aws.credentials.provider",
        "com.amazonaws.auth.InstanceProfileCredentialsProvider",
    ),
    (
        "provider_default_da_cadeia",
        "spark.hadoop.fs.s3a.aws.credentials.provider",
        "com.amazonaws.auth.DefaultAWSCredentialsProviderChain",
    ),
    (
        "service_account_do_emr_on_eks",
        "spark.kubernetes.authenticate.driver.serviceAccountName",
        "emr-containers-sa-spark",
    ),
    (
        "service_account_do_executor",
        "spark.kubernetes.authenticate.executor.serviceAccountName",
        "emr-containers-sa-spark-driver",
    ),
    (
        "classe_java_em_chave_com_dica",
        "spark.authenticate.credentialProviderClass",
        "org.apache.spark.deploy.security.HadoopDelegationTokenProvider",
    ),
]

# A EXCLUSAO acima e uma porta, e estes travam a largura dela. Exigir tres ou
# mais segmentos e o que impede que uma senha escolhida por humano com um hifen
# no meio passe pela mesma porta -- ela continua sendo redigida.
POSITIVOS_APESAR_DO_HIFEN = [
    (
        "senha_humana_com_um_hifen",
        "spark.authenticate.secret",
        "correcthorse-batterystaple",
    ),
    (
        "material_com_digito_entre_segmentos",
        "spark.hadoop.fs.s3a.secret.key",
        "aB3xY9zQw7-Lm2Kd8Rt5N-Pq7Wz",
    ),
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

# Negativos a um caractere de virar positivo. Cada um existe para travar UM piso
# de comprimento ou UMA literal do padrao correspondente.
QUASE_VALIDOS = [
    ("aws_com_15_caracteres", "x", "AKIA" + "A" * 15),
    ("aws_com_17_caracteres", "x", "AKIA" + "A" * 17),
    ("github_classico_com_35", "config_value", "ghp_" + "a" * 35),
    ("github_pat_com_19", "data", "github_pat_" + "b" * 19),
    ("jwt_com_segmento_de_7", "payload", "eyJ" + "a" * 7 + "." + "b" * 10 + "." + "c" * 10),
    ("slack_com_9_caracteres", "campo", "xoxb-" + "1" * 9),
    ("pem_em_minusculo", "blob", "-----begin rsa private key-----"),
    ("pem_de_chave_publica", "blob", "-----BEGIN PUBLIC KEY-----"),
]

# (nome_do_caso, chave, valor, e_segredo) -- toda linha do arquivo, com a
# resposta esperada. Os testes que precisam varrer o corpus inteiro usam este.
CORPUS = (
    [(nome, chave, valor, True) for nome, chave, valor in POSITIVOS]
    + [(nome, chave, valor, True) for nome, chave, valor, _ in POSITIVOS_EMBUTIDOS]
    + [(nome, chave, valor, True) for nome, chave, valor in POSITIVOS_POR_NOME_DE_CHAVE]
    + [(nome, chave, valor, True) for nome, chave, valor in POSITIVOS_APESAR_DO_HIFEN]
    + [(nome, chave, valor, False) for nome, chave, valor in IDENTIFICADORES_SEGMENTADOS]
    + [(nome, chave, valor, False) for nome, chave, valor in NEGATIVOS]
    + [(nome, chave, valor, False) for nome, chave, valor in QUASE_VALIDOS]
)


@pytest.mark.parametrize("nome,chave,valor", POSITIVOS, ids=[c[0] for c in POSITIVOS])
def test_segredo_e_detectado_mesmo_com_nome_de_chave_inocente(nome, chave, valor):
    assert looks_like_secret(chave, valor) is True, (
        f"{nome}: valor com forma de credencial passou batido com chave {chave!r}"
    )


@pytest.mark.parametrize(
    "nome,chave,valor,esperado",
    POSITIVOS_EMBUTIDOS,
    ids=[c[0] for c in POSITIVOS_EMBUTIDOS],
)
def test_credencial_embutida_no_meio_do_valor_e_detectada(nome, chave, valor, esperado):
    """Prova que os padroes varrem o valor inteiro, e nao so o inicio dele.

    A afirmacao sobre `detectores` nao e redundante com a de `looks_like_secret`:
    as duas funcoes varrem por conta propria, e sem esta linha so uma das duas
    estaria provada contra ancoragem no indice 0.
    """
    assert looks_like_secret(chave, valor) is True, (
        f"{nome}: credencial no meio do valor passou batido"
    )
    assert esperado in detectores(chave, valor), (
        f"{nome}: `detectores` nao apontou {esperado!r} para credencial no meio do valor"
    )


def test_positivos_embutidos_realmente_estao_embutidos():
    """Guarda do proprio corpus, nao do codigo.

    Um caso da lista `POSITIVOS_EMBUTIDOS` que por descuido case no indice 0
    passa em tudo e para de provar a unica coisa que ele existe para provar.
    Aqui o corpus se verifica: a posicao do casamento tem que ser maior que zero.
    """
    por_nome = dict(_PADROES_POR_VALOR)
    for nome, _chave, valor, esperado in POSITIVOS_EMBUTIDOS:
        casado = por_nome[esperado].search(valor)
        assert casado is not None, f"{nome}: {esperado!r} nao casou em lugar nenhum"
        assert casado.start() > 0, (
            f"{nome}: a credencial comeca no indice 0 -- o caso nao prova `search`"
        )


@pytest.mark.parametrize(
    "nome,chave,valor",
    POSITIVOS_POR_NOME_DE_CHAVE,
    ids=[c[0] for c in POSITIVOS_POR_NOME_DE_CHAVE],
)
def test_segredo_sem_prefixo_publicado_e_pego_pelo_nome_da_chave(nome, chave, valor):
    assert looks_like_secret(chave, valor) is True, (
        f"{nome}: segredo proprietario passou batido -- o gatilho do nome da chave e o unico"
    )
    assert detectores(chave, valor) == ("nome_de_chave_com_entropia",), (
        f"{nome}: deveria disparar so o gatilho do nome da chave, sem casar padrao publicado"
    )


@pytest.mark.parametrize("nome,chave,valor", NEGATIVOS, ids=[c[0] for c in NEGATIVOS])
def test_dado_legitimo_nao_e_redigido(nome, chave, valor):
    assert looks_like_secret(chave, valor) is False, (
        f"{nome}: dado legitimo foi tratado como segredo -- redacao apaga evidencia"
    )


@pytest.mark.parametrize("nome,chave,valor", QUASE_VALIDOS, ids=[c[0] for c in QUASE_VALIDOS])
def test_quase_valido_nao_vira_positivo(nome, chave, valor):
    assert looks_like_secret(chave, valor) is False, (
        f"{nome}: o piso de comprimento ou a literal do padrao esta frouxo demais"
    )
    assert detectores(chave, valor) == (), (
        f"{nome}: `detectores` disparou para um valor a um caractere de ser credencial"
    )


@pytest.mark.parametrize(
    "nome,chave,valor",
    IDENTIFICADORES_SEGMENTADOS,
    ids=[c[0] for c in IDENTIFICADORES_SEGMENTADOS],
)
def test_identificador_segmentado_nao_e_material_criptografico(nome, chave, valor):
    """O gatilho do nome da chave nao pode acusar a propria correcao.

    `com.amazonaws.auth.InstanceProfileCredentialsProvider` e o valor que
    substitui a credencial literal; `emr-containers-sa-spark` e o nome de conta
    de servico que a AWS publica para EMR on EKS. Os dois passavam nos dois
    testes do gatilho 3 -- dica no nome da chave, e alfabeto de material
    criptografico -- porque esse alfabeto inclui `.` e `-`.
    """
    assert looks_like_secret(chave, valor) is False, (
        f"{nome}: identificador segmentado foi tratado como segredo -- a regra"
        " acusaria a propria correcao, e o valor sumiria do handoff"
    )
    assert detectores(chave, valor) == (), (
        f"{nome}: `detectores` disparou para um identificador segmentado"
    )


@pytest.mark.parametrize(
    "nome,chave,valor",
    POSITIVOS_APESAR_DO_HIFEN,
    ids=[c[0] for c in POSITIVOS_APESAR_DO_HIFEN],
)
def test_exclusao_de_identificador_nao_abre_a_porta_para_material(nome, chave, valor):
    """Toda exclusao e uma porta; esta linha mede a largura da porta.

    A exclusao exige TRES ou mais segmentos de letras puras. Um valor com dois
    segmentos, ou com digito dentro de qualquer segmento, continua sendo
    redigido.
    """
    assert looks_like_secret(chave, valor) is True, (
        f"{nome}: a exclusao de identificador segmentado abriu demais"
    )
    assert detectores(chave, valor) == ("nome_de_chave_com_entropia",), (
        f"{nome}: deveria continuar disparando so o gatilho do nome da chave"
    )


def test_redact_devolve_o_marcador_e_avisa_que_redigiu():
    """O segundo elemento vira `attrs["redacted"]` em `event_log.py`.

    Perde-lo apaga o unico dado que sobrevive a redacao: que havia credencial
    ali. Por isso a afirmacao e sobre a tupla inteira, e nao so sobre o valor.
    """
    publicavel, foi_redigido = redact("x", "AKIAIOSFODNN7EXAMPLE")
    assert publicavel == REDACTED
    assert foi_redigido is True


def test_redact_devolve_o_valor_intacto_quando_nao_ha_segredo():
    valor = "s3://bucket/warehouse/prefixo/longo"
    publicavel, foi_redigido = redact("spark.sql.warehouse.dir", valor)
    assert publicavel == valor
    assert foi_redigido is False


@pytest.mark.parametrize("nome,chave,valor,e_segredo", CORPUS, ids=[c[0] for c in CORPUS])
def test_redact_acompanha_o_corpus_inteiro(nome, chave, valor, e_segredo):
    """`redact` e o UNICO ponto por onde a producao chega ao detector.

    `event_log.py` chama `redact`, nunca `looks_like_secret`. Um corpus que so
    prova `looks_like_secret` deixa o caminho de producao sem cobertura.
    """
    publicavel, foi_redigido = redact(chave, valor)
    assert foi_redigido is e_segredo, f"{nome}: `redact` discordou do corpus"
    if e_segredo:
        assert publicavel == REDACTED, f"{nome}: segredo saiu sem o marcador"
        assert publicavel != valor, f"{nome}: o valor original vazou pelo retorno"
    else:
        assert publicavel == valor, f"{nome}: dado legitimo foi alterado por `redact`"


def test_detectores_nomeia_sem_nunca_devolver_o_valor():
    valor = "AKIAIOSFODNN7EXAMPLE"
    nomes = detectores("x", valor)
    assert nomes == ("aws_access_key",)
    assert valor not in " ".join(nomes)


def test_detectores_vazio_para_dado_legitimo():
    assert detectores("spark.sql.warehouse.dir", "s3://bucket/prefixo") == ()


@pytest.mark.parametrize("nome,chave,valor,e_segredo", CORPUS, ids=[c[0] for c in CORPUS])
def test_detectores_e_looks_like_secret_nunca_divergem(nome, chave, valor, e_segredo):
    """As duas funcoes repetem a mesma varredura, e por decisao registrada ficam
    separadas: `detectores` e exigida pela SPEC do SFCI, `looks_like_secret` e a
    API que os extratores importam. Unificar as duas foi medido em revisao e
    custa pouco (+4,9%), mas a separacao foi mantida pelas exigencias acima.

    O risco da duplicacao nao e o custo, e a divergencia silenciosa: um padrao
    acrescentado num lado e esquecido no outro faz o scanner relatar "nenhum
    detector" sobre um valor que a producao redigiu. Esta linha prende os dois.
    """
    assert bool(detectores(chave, valor)) == looks_like_secret(chave, valor), (
        f"{nome}: `detectores` e `looks_like_secret` deram respostas diferentes"
    )


def test_todo_padrao_por_valor_tem_positivo_no_corpus():
    """Cobertura estrutural: o proximo padrao nasce com caso, ou este teste cai.

    Hoje cada padrao tem positivo por acidente de escrita, nao por obrigacao.
    Sem este teste, acrescentar um setimo padrao sem caso nenhum passa em tudo,
    e um padrao sem caso e um padrao que ninguem sabe se funciona.
    """
    cobertos: set[str] = set()
    for _, chave, valor, e_segredo in CORPUS:
        if e_segredo:
            cobertos.update(detectores(chave, valor))
    nomes_dos_padroes = {nome for nome, _ in _PADROES_POR_VALOR}
    assert nomes_dos_padroes - cobertos == set(), (
        f"padroes sem nenhum positivo no corpus: {sorted(nomes_dos_padroes - cobertos)}"
    )
    # Os dois gatilhos que nao vivem na tupla precisam da mesma garantia.
    assert {"url_password", "nome_de_chave_com_entropia"} <= cobertos


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
