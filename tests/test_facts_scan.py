"""A varredura e a fronteira entre o repositorio analisado e o motor.

Ela existe como unidade desde que os quinze sitios de `rglob` -- catorze em
`sparkforge/facts/` e um em `sparkforge/migration/collect.py` -- passaram a
chamar `iter_source_files`. Antes disso so tres pulavam sequer `__pycache__`, e
apontar o motor para um repositorio com `.venv` varria o ambiente virtual
inteiro: custo, ruido, e leitura de qualquer `*.json` que houvesse dentro.

Este arquivo carrega os dois lados da fronteira, e os dois erram feio:

- deixar passar credencial (`.aws/`, `secrets/`, `.env`, junction do Windows);
- recusar artefato legitimo (`secrets_manager.tf`, `partition.key.json`, dump
  de listagem S3 acima do teto). O segundo e silencioso, o que o torna pior.
"""

import ast
import pathlib
import subprocess
import sys

import pytest

from sparkforge.facts.scan import ScanError, iter_source_files


def _criar(raiz: pathlib.Path, caminho: str, conteudo: str = "x = 1\n") -> pathlib.Path:
    alvo = raiz / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")
    return alvo


# Excecao ao gate anti-travessia-crua: arquivo -> razao. Lista explicita e por
# caminho relativo, nunca por escopo estreito. Um gate que so olha uma pasta nao
# declara excecao nenhuma -- ele deixa todo o resto passar por omissao, e foi
# assim que `migration/collect.py` ficou de fora do gate no mesmo diff que o
# migrou.
# `facts/scan.py` NAO esta aqui de proposito: ele implementa a travessia com
# `os.walk`, entao nao tem `glob` para isentar. Isenta-lo "por ser a varredura"
# seria excecao para um problema que ele nao tem -- e se um dia ele passar a
# usar `glob`, o gate deve obrigar a decisao, nao aprova-la de antemao.
VARREDURA_CRUA_PERMITIDA: dict[str, str] = {
    "adapters/_core.py": (
        "varre o knowledge/ embarcado no proprio wheel, 19 arquivos curados, "
        "nao repositorio de cliente"
    ),
    "case/playbook.py": "varre os agents embarcados no wheel",
    "registry/loader.py": "varre os agents embarcados no wheel",
    "rules/loader.py": "varre o catalogo de regras embarcado no wheel",
    "context/progressive.py": "varre as references embarcadas no wheel",
    "economy/cache.py": "varre o cache que o proprio motor escreveu",
    "codeintel/security.py": (
        "gate estatico de import de rede da seccao 7 da SPEC: varre o proprio "
        "pacote, embarcado no wheel, e precisa ver TODO .py dele. Passar por "
        "iter_source_files tornaria o gate fail-open -- arquivo acima do teto "
        "de tamanho sairia da varredura e o import escaparia por padding, que e "
        "evasao de uma tecla. INV-015 manda o contrario"
    ),
}


def test_nenhum_modulo_varre_com_glob_cru():
    """`glob` e `rglob` diretos sao a porta de entrada sem denylist.

    O gate e estrutural e por AST, sobre `sparkforge/` INTEIRO -- 126 arquivos,
    nao os 25 de `facts/`. As duas formas contam: `glob("**/*.json")` anda a
    arvore igual a `rglob("*.json")`, e olhar so uma delas convida a evasao de
    uma tecla.

    O que e legitimo esta em `VARREDURA_CRUA_PERMITIDA` com a razao escrita, e
    a lista e conferida contra a realidade: entrada que sobra e mentira sobre o
    que o gate protege.
    """
    raiz = pathlib.Path(__file__).resolve().parent.parent / "sparkforge"
    infratores = []
    usadas = set()
    for arquivo in sorted(raiz.rglob("*.py")):
        rel = arquivo.relative_to(raiz).as_posix()
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        cruas = [
            no.lineno
            for no in ast.walk(arvore)
            if isinstance(no, ast.Attribute) and no.attr in ("glob", "rglob", "iglob")
        ]
        if not cruas:
            continue
        if rel in VARREDURA_CRUA_PERMITIDA:
            usadas.add(rel)
            continue
        infratores.extend(f"{rel}:{linha}" for linha in cruas)
    assert infratores == [], infratores
    sobrando = sorted(set(VARREDURA_CRUA_PERMITIDA) - usadas)
    assert sobrando == [], f"excecao declarada que ja nao existe: {sobrando}"


def test_pula_arvore_de_dependencia_e_artefato_de_build(tmp_path):
    _criar(tmp_path, "job.py")
    for ruido in (
        ".venv/lib/site-packages/requests/api.py",
        "venv/lib/x.py",
        "node_modules/pacote/index.py",
        "vendor/terceiro/mod.py",
        "build/lib/copia.py",
        "__pycache__/job.cpython-312.py",
        ".git/hooks/pre-commit.py",
        ".tox/py310/x.py",
        "site-packages/y.py",
    ):
        _criar(tmp_path, ruido)
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_pula_caminho_sensivel_mesmo_com_extensao_pedida(tmp_path):
    _criar(tmp_path, "config.json", "{}")
    for sensivel in (
        ".aws/credentials.json",
        ".ssh/chave.json",
        "terraform.tfstate.json",
        "secrets.json",
        ".env.json",
    ):
        _criar(tmp_path, sensivel, "{}")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["config.json"]


def test_junction_do_windows_nao_reintroduz_pasta_podada(tmp_path):
    """`mklink /J` nao pede administrador, e `islink` devolve False para ela.

    A poda decide pelo nome do componente, e junction da nome novo a mesma
    pasta: `mklink /J atalho_aws .aws` traz de volta exatamente o diretorio que
    a denylist tinha removido. O confinamento tambem aprova, porque o destino
    esta DENTRO da raiz. Reproduzido lendo `atalho_aws/sso/cache.json`, que e
    token SSO da AWS.
    """
    if not sys.platform.startswith("win"):
        pytest.skip("junction so existe no Windows")
    raiz = tmp_path / "repo"
    (raiz / ".aws" / "sso").mkdir(parents=True)
    (raiz / ".aws" / "sso" / "cache.json").write_text('{"accessToken": "x"}', encoding="utf-8")
    _criar(raiz, "config.json", "{}")
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(raiz / "atalho_aws"), str(raiz / ".aws")],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip("junction indisponivel neste ambiente")
    try:
        achados = sorted(p.name for p in iter_source_files(raiz, "*.json"))
    finally:
        # Desfaz a junction antes da limpeza do pytest. `shutil.rmtree` ve
        # junction como diretorio comum (`islink` e False para ela) e desceria
        # nela para apagar o DESTINO. Aqui o destino esta dentro do tmp_path e
        # nao haveria estrago, mas o dia em que alguem apontar para fora, havia.
        (raiz / "atalho_aws").rmdir()
    assert achados == ["config.json"]


def test_symlink_de_pasta_para_fora_da_raiz_nao_e_seguido(tmp_path):
    """Symlink de verdade. A junction tem caso proprio: `islink` nao a ve."""
    fora = tmp_path.parent / "fora_do_alvo"
    fora.mkdir(exist_ok=True)
    (fora / "segredo.py").write_text("SENHA = 'x'\n", encoding="utf-8")
    alvo = tmp_path / "alvo"
    alvo.mkdir()
    _criar(alvo, "job.py")
    try:
        (alvo / "atalho").symlink_to(fora, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(alvo, "*.py"))
    assert achados == ["job.py"]


def test_raiz_inexistente_e_erro_nomeado_nao_lista_vazia(tmp_path):
    with pytest.raises(ScanError):
        list(iter_source_files(tmp_path / "nao_existe", "*.py"))


def test_arquivo_grande_demais_e_pulado_sem_derrubar_a_varredura(tmp_path):
    _criar(tmp_path, "pequeno.py")
    (tmp_path / "gigante.py").write_text("#" * (2 * 1024 * 1024), encoding="utf-8")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["pequeno.py"]


def test_json_de_dois_mib_passa_porque_o_teto_de_codigo_nao_vale_para_dado(tmp_path):
    """O par do teste acima, e a razao de o teto ser dois e nao um.

    O mesmo tamanho que reprova um `.py` -- onde a razao e nao montar AST de
    arquivo gigante -- aprova um `.json`, que o operador apontou de proposito
    e que nao passa por parser de codigo nenhum.
    """
    _criar(tmp_path, "pequeno.json", "{}")
    dump = '{"x": "' + "a" * (2 * 1024 * 1024) + '"}'
    (tmp_path / "dump.json").write_text(dump, encoding="utf-8")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["dump.json", "pequeno.json"]


def test_extensao_desconhecida_usa_o_teto_de_dados(tmp_path):
    """Fail-open no tamanho, ao contrario do resto do modulo.

    Pular por engano um artefato legitimo e pior que ler um arquivo grande que
    nao interessa: o primeiro faz o motor dizer "nada para analisar" sobre algo
    que existe, o segundo so gasta tempo.
    """
    (tmp_path / "biblioteca.jar").write_bytes(b"x" * (2 * 1024 * 1024))
    assert [p.name for p in iter_source_files(tmp_path, "*.jar")] == ["biblioteca.jar"]


def test_teto_de_dados_existe_e_nao_e_infinito(tmp_path):
    """O teto de dados e alto, nao ausente -- provado por comportamento.

    Aqui esteve um teste que so conferia a constante, com a justificativa de
    que "escrever 128 MiB custaria mais que vale". A justificativa estava
    medida errada: `truncate` da `st_size` real sem gravar byte de dado, e
    `st_size` e exatamente o que o teto le. Custa 0.19 s.
    """
    from sparkforge.facts.scan import TAMANHO_MAXIMO_DADOS_BYTES

    _criar(tmp_path, "pequeno.json", "{}")
    with open(tmp_path / "patologico.json", "wb") as arquivo:
        arquivo.truncate(TAMANHO_MAXIMO_DADOS_BYTES + 1)

    assert (tmp_path / "patologico.json").stat().st_size == TAMANHO_MAXIMO_DADOS_BYTES + 1
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["pequeno.json"]


def test_json_logo_abaixo_do_teto_de_dados_passa(tmp_path):
    """O par do caso acima: o teto corta um byte adiante, nao antes.

    Sem este, baixar o teto de dados para qualquer valor menor -- inclusive
    para o teto de codigo -- continuaria passando no teste do teto.
    """
    from sparkforge.facts.scan import TAMANHO_MAXIMO_DADOS_BYTES

    with open(tmp_path / "no_limite.json", "wb") as arquivo:
        arquivo.truncate(TAMANHO_MAXIMO_DADOS_BYTES)
    assert [p.name for p in iter_source_files(tmp_path, "*.json")] == ["no_limite.json"]


@pytest.mark.parametrize(
    "caminho",
    [
        "secrets/db.json",
        ".secrets/db.json",
        "credentials/prod.json",
        ".credentials/prod.json",
        ".serverless/serverless-state.json",
        "cdk.out/manifest.json",
        # Nome banal de proposito: se fosse
        # `gcloud/application_default_credentials.json` o caso passaria pela
        # regra de NOME mesmo com a pasta fora da denylist, e nao provaria a
        # poda -- foi assim que a mutacao `.gcloud` sobreviveu na primeira volta.
        "gcloud/configuracao.json",
    ],
)
def test_cofre_de_credencial_em_pasta_e_podado(tmp_path, caminho):
    """O nome do arquivo la dentro nao denuncia nada, entao a pasta e a defesa.

    `secrets/db.json` e um `*.json` comum para qualquer regra de nome. O
    `serverless-state.json` de `.serverless/` carrega variavel de ambiente JA
    RESOLVIDA, e `gcloud/` guarda `application_default_credentials.json` -- em
    nenhum sistema existe `.gcloud`, que era o que a lista trazia antes.
    """
    _criar(tmp_path, "config.json", "{}")
    _criar(tmp_path, caminho, "{}")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["config.json"]


@pytest.mark.parametrize(
    ("nome", "padrao"),
    [
        ("secret.yaml", "*.yaml"),
        ("secrets.json", "*.json"),
        ("credentials.json", "*.json"),
        (".env.json", "*.json"),
        (".env.local.json", "*.json"),
        ("terraform.tfstate.json", "*.json"),
        ("Pulumi.prod.yaml", "*.yaml"),
        ("application_default_credentials.json", "*.json"),
    ],
)
def test_nome_de_credencial_e_recusado(tmp_path, nome, padrao):
    """`secret` no singular e Secret de Kubernetes: `data:` inteiro em base64.

    `Pulumi.prod.yaml` guarda secret cifrado de stack; `.env.local.json` so casa
    porque a checagem corta no primeiro componente, nao no talo do pathlib.
    """
    alvo = "inocente" + padrao.lstrip("*")
    _criar(tmp_path, alvo, "{}")
    _criar(tmp_path, nome, "{}")
    achados = sorted(p.name for p in iter_source_files(tmp_path, padrao))
    assert achados == [alvo]


@pytest.mark.parametrize(
    ("nome", "padrao"),
    [
        ("secrets_manager.tf", "*.tf"),
        ("secretsmanager_policy.json", "*.json"),
        ("credentials_provider.py", "*.py"),
        ("secrets.py", "*.py"),
        ("partition.key.json", "*.json"),
        ("sort.key.py", "*.py"),
        ("primary.key.tf", "*.tf"),
        ("schema.pem.json", "*.json"),
        ("spark.sql.warehouse.json", "*.json"),
        ("dados.2026.01.json", "*.json"),
        ("requirements.dev.txt", "requirements*.txt"),
        ("job.v2.py", "*.py"),
        ("Pulumi.yaml", "*.yaml"),
    ],
)
def test_artefato_legitimo_nao_e_recusado_pela_denylist(tmp_path, nome, padrao):
    """Falso positivo aqui e o motor dizendo "nao ha nada" sobre o que importa.

    `secrets_manager.tf` e o Terraform de AWS Secrets Manager -- exatamente o
    que o revisor de seguranca existe para olhar -- e um `startswith` solto o
    recusava calado. `.key` e palavra corrente em repositorio de dados:
    `partition.key.json` e um JSON sobre chave de particao, nao uma chave.
    `Pulumi.yaml` e o arquivo de projeto, sem secret; so `Pulumi.<stack>.yaml`
    guarda.
    """
    _criar(tmp_path, nome, "x = 1\n")
    assert [p.name for p in iter_source_files(tmp_path, padrao)] == [nome]


@pytest.mark.parametrize("pasta", ["Build", ".VENV", "Dist", "Target", "Node_Modules"])
def test_poda_de_ruido_ignora_caixa(tmp_path, pasta):
    """O Windows tem filesystem case-insensitive, e e onde isto roda.

    A poda de cofre ja normalizava a caixa; a de ruido comparava exato, entao
    `Build/` e `.VENV/` eram varridos inteiros enquanto `.AWS/` era podado.
    """
    _criar(tmp_path, "job.json", "{}")
    _criar(tmp_path, f"{pasta}/copia.json", "{}")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.json"))
    assert achados == ["job.json"]


def test_apenas_arquivo_regular(tmp_path):
    _criar(tmp_path, "job.py")
    achados = list(iter_source_files(tmp_path, "*.py"))
    assert all(p.is_file() for p in achados)


def test_ordem_reproduz_a_de_rglob_ordenado(tmp_path):
    """Os goldens foram gravados sob `sorted(root.rglob(...))`.

    `os.walk` visita por nivel, o que intercala subpasta e arquivo em ordem
    diferente da ordenacao global por caminho. Se a varredura nao reproduzir a
    ordem antiga, todo extrator que nao reordena no fim muda de golden.
    """
    for caminho in ("a/b.py", "a/c/d.py", "a/e.py", "z.py", "a/c/a.py"):
        _criar(tmp_path, caminho)
    assert list(iter_source_files(tmp_path, "*.py")) == sorted(tmp_path.rglob("*.py"))


def test_raiz_relativa_devolve_caminho_relativo(tmp_path, monkeypatch):
    """Os extratores fazem `relative_to(repo_root)` no que a varredura devolve.

    Resolver a raiz antes de andar transformaria `.` em caminho absoluto, e o
    `relative_to(Path("."))` de quem chamou passaria a levantar ValueError.
    """
    _criar(tmp_path, "pacote/job.py")
    monkeypatch.chdir(tmp_path)
    achados = list(iter_source_files(pathlib.Path("."), "*.py"))
    assert [p.relative_to(pathlib.Path(".")).as_posix() for p in achados] == ["pacote/job.py"]


def test_raiz_que_e_arquivo_e_erro_nomeado(tmp_path):
    alvo = _criar(tmp_path, "job.py")
    with pytest.raises(ScanError):
        list(iter_source_files(alvo, "*.py"))


def test_extensao_fora_do_padrao_nao_entra(tmp_path):
    _criar(tmp_path, "job.py")
    _criar(tmp_path, "dados.json", "{}")
    _criar(tmp_path, "leia.txt", "oi")
    assert sorted(p.name for p in iter_source_files(tmp_path, "*.py")) == ["job.py"]


def test_arquivo_no_limite_de_tamanho_ainda_entra(tmp_path):
    """O limite e `>`, nao `>=`: arquivo exatamente no teto e legitimo.

    Sem este caso, trocar o limite por `>=` -- ou por qualquer teto menor --
    passaria despercebido.
    """
    from sparkforge.facts.scan import TAMANHO_MAXIMO_CODIGO_BYTES

    (tmp_path / "no_limite.py").write_bytes(b"#" * TAMANHO_MAXIMO_CODIGO_BYTES)
    (tmp_path / "um_a_mais.py").write_bytes(b"#" * (TAMANHO_MAXIMO_CODIGO_BYTES + 1))
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["no_limite.py"]


def test_symlink_para_arquivo_dentro_da_raiz_tambem_e_pulado(tmp_path):
    """Symlink e pulado por ser symlink, nao por apontar para fora.

    Um link que aponta para dentro da raiz continua sendo um segundo nome para
    o mesmo conteudo: segui-lo duplicaria facts do mesmo arquivo.
    """
    _criar(tmp_path, "job.py")
    try:
        (tmp_path / "copia.py").symlink_to(tmp_path / "job.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_subpasta_ignorada_nao_e_descida(tmp_path, monkeypatch):
    """A poda tem que impedir a DESCIDA, nao so filtrar o resultado.

    Filtrar no fim daria a mesma lista, mas teria pago o custo de listar o
    `.venv` inteiro -- que e exatamente o custo que esta varredura existe para
    evitar.
    """
    import os as _os

    _criar(tmp_path, "job.py")
    _criar(tmp_path, ".venv/lib/site-packages/requests/api.py")
    visitadas: list[str] = []
    walk_original = _os.walk

    def walk_espiao(*args, **kwargs):
        for pasta, subpastas, arquivos in walk_original(*args, **kwargs):
            visitadas.append(pasta)
            yield pasta, subpastas, arquivos

    monkeypatch.setattr("sparkforge.facts.scan.os.walk", walk_espiao)
    list(iter_source_files(tmp_path, "*.py"))
    assert not any(".venv" in pasta for pasta in visitadas)


def test_symlink_de_pasta_para_dentro_da_raiz_nao_duplica(tmp_path):
    """Isola `followlinks=False` do confinamento.

    Um link de pasta que aponta para DENTRO da raiz passa no confinamento --
    o destino esta mesmo la dentro. Se a travessia seguisse links, o mesmo
    arquivo entraria duas vezes e viraria fact duplicado.
    """
    _criar(tmp_path, "pkg/job.py")
    try:
        (tmp_path / "atalho").symlink_to(tmp_path / "pkg", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*.py"))
    assert achados == ["job.py"]


def test_caminho_entregue_de_fora_da_raiz_nao_passa(tmp_path, monkeypatch):
    """Isola o confinamento de `followlinks=False`.

    O confinamento existe para a corrida: entre podar e ler, um componente
    intermediario pode ser trocado por um link. Aqui a corrida e encenada --
    a travessia entrega uma pasta de fora -- porque so assim a guarda fica
    observavel enquanto `followlinks=False` tambem esta no lugar.
    """
    import os as _os

    fora = tmp_path.parent / "fora_do_confinamento"
    fora.mkdir(exist_ok=True)
    (fora / "segredo.py").write_text("SENHA = 'x'\n", encoding="utf-8")
    alvo = tmp_path / "alvo"
    alvo.mkdir()
    _criar(alvo, "job.py")
    walk_original = _os.walk

    def walk_com_intruso(*args, **kwargs):
        yield from walk_original(*args, **kwargs)
        yield str(fora), [], ["segredo.py"]

    monkeypatch.setattr("sparkforge.facts.scan.os.walk", walk_com_intruso)
    achados = sorted(p.name for p in iter_source_files(alvo, "*.py"))
    assert achados == ["job.py"]


def test_til_na_raiz_e_expandido(tmp_path, monkeypatch):
    """`~` chega de linha de comando e nao e nome de pasta.

    Sem expandir, a raiz `~/projeto` simplesmente nao existe e a varredura
    acusaria raiz inexistente para um caminho que o usuario ve funcionar no
    shell dele.
    """
    _criar(tmp_path, "projeto/job.py")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    achados = sorted(p.name for p in iter_source_files("~/projeto", "*.py"))
    assert achados == ["job.py"]


@pytest.mark.parametrize(
    "nome",
    [
        "id_rsa",
        "id_ed25519",
        "kubeconfig",
        "chave.pem",
        "servidor.key",
        "cofre.p12",
        "estado.tfstate",
        "prod.tfvars",
        ".npmrc",
        ".netrc",
    ],
)
def test_nome_sensivel_e_pulado_com_padrao_curinga(tmp_path, nome):
    """`*` casa qualquer nome, entao a denylist e a unica defesa aqui.

    Um extrator que varre por curinga passaria a ler credencial se a checagem
    de sensivel sumisse.
    """
    _criar(tmp_path, "job.py")
    _criar(tmp_path, nome, "conteudo")
    achados = sorted(p.name for p in iter_source_files(tmp_path, "*"))
    assert achados == ["job.py"]
