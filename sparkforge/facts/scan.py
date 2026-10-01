"""A varredura unica dos extratores, com denylist e confinamento.

Quinze sitios de `rglob` faziam isto separadamente -- catorze em
`sparkforge/facts/` e um em `sparkforge/migration/collect.py` -- e so tres
pulavam sequer `__pycache__`. Consolidar aqui e o que torna a fronteira
auditavel: existe UM lugar que decide o que o motor pode ler, e ele tem teste.

Fail-closed em quase toda decisao: atalho de diretorio, arquivo especial e
caminho de nome sensivel sao PULADOS, nunca lidos "so para ver". Duas excecoes
deliberadas, e as duas estao escritas onde acontecem:

- raiz inexistente e erro nomeado, nao lista vazia. Devolver vazio pareceria
  "nao ha nada a analisar", quando o certo e "voce apontou para o lugar errado".
- o teto de tamanho e FAIL-OPEN: extensao desconhecida recebe o teto de dados,
  o mais alto. Ver `_teto_para`. Pular por engano um artefato legitimo e pior
  que ler um arquivo grande que nao interessa.

As listas deste modulo sao DUAS, e acrescentar um nome a uma delas e uma
decisao diferente de acrescentar a outra:

- `DIRETORIOS_IGNORADOS` e CUSTO E RUIDO. `.venv`, `node_modules`, `build`,
  `dist`, os caches: arvore de dependencia e artefato, nao codigo do projeto
  analisado. Tirar um nome dali torna a varredura mais cara e mais barulhenta,
  e nada mais.
- `DIRETORIOS_SENSIVEIS`, `TALOS_SENSIVEIS`, `SUFIXOS_SENSIVEIS` e
  `SUFIXOS_SENSIVEIS_COMPOSTOS` sao CREDENCIAL. `.pem`, `credentials`, `.env`,
  `id_rsa`, `.tfstate`, `kubeconfig`, `.aws/`, `.ssh/`, `secrets/`. Tirar um
  nome dali faz o motor ler segredo de cliente. Nenhuma allowlist de extensao
  pode reabilitar o que esta aqui -- e por isso a checagem de sensivel roda
  DEPOIS do casamento de padrao, nao antes.

PULAR NAO E MAIS SILENCIOSO. Era a lacuna de fundo deste modulo: cada caminho
que descartava arquivo saia sem sinal, e quem lia a saida nao distinguia "nao
havia nada" de "havia e eu nao li" -- o que contraria o principio do
`unresolved` que a casa aplica em `graph.unresolved` e `sql.unresolved`. Um
`Iterator[Path]` nao comporta o sinal, entao a saida ganhou forma nova AO LADO
da antiga: `varrer_source_files` devolve `Varredura`, com os arquivos E os
`Pulo`, cada um com a razao nomeada. `iter_source_files` continua existindo e
continua devolvendo so caminho, na mesma ordem -- ha golden de extrator gravado
sob ela e catorze modulos de `facts/` iterando isto.

O caso delicado e o pulo por NOME SENSIVEL, e a decisao esta escrita em
`varrer_source_files` e em `Pulo`: registra-se caminho RELATIVO a raiz e razao,
nunca conteudo, nunca o absoluto. Ver a docstring de `Pulo` para o porque de
cada metade dessa escolha.
"""

from __future__ import annotations

import os
import stat as _stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


class ScanError(Exception):
    """Raiz inexistente, ilegivel, ou que nao e diretorio."""


# As razoes de pulo. Constantes nomeadas e nao literais soltos, no mesmo formato
# de `codeintel/resolve.py` (`AMBIGUOUS`, `NO_CANDIDATE`) e de
# `codeintel/lineage.py` (`SQL_NOT_PARSED`): quem consome compara com o simbolo,
# e renomear a razao vira erro de import em vez de comparacao que passa a dar
# False em silencio.
#
# Nao ha razao para "nao casou o padrao". Nao casar `*.py` numa varredura de
# `*.py` e o FILTRO QUE QUEM CHAMOU PEDIU, nao ponto cego -- e registrar isso
# encheria a lista de ruido ate afogar as razoes que importam, que e como um
# sinal de ponto cego morre na pratica.
SIZE_ABOVE_LIMIT = "SIZE_ABOVE_LIMIT"
REPARSE_POINT = "REPARSE_POINT"
NOT_A_REGULAR_FILE = "NOT_A_REGULAR_FILE"
SENSITIVE_NAME = "SENSITIVE_NAME"
OUTSIDE_ROOT = "OUTSIDE_ROOT"
OS_ERROR = "OS_ERROR"

# Poda de diretorio. TRES razoes e nao uma porque a docstring do modulo separa
# as listas por consequencia, e a separacao tem que sobreviver ate a saida:
# `.venv` podado e economia, `secrets/` podado e recusa de credencial, e um
# unico `DIRECTORY_PRUNED` obrigaria quem le a adivinhar qual dos dois foi.
DIRECTORY_IGNORED = "DIRECTORY_IGNORED"
DIRECTORY_SENSITIVE = "DIRECTORY_SENSITIVE"
DIRECTORY_REPARSE_POINT = "DIRECTORY_REPARSE_POINT"

# As razoes cuja causa e CREDENCIAL. Existe como conjunto para que um relatorio
# possa redigir por classe -- `pulo.e_sensivel` -- em vez de comparar string por
# string e esquecer uma no dia em que outra entrar.
RAZOES_SENSIVEIS: frozenset[str] = frozenset({SENSITIVE_NAME, DIRECTORY_SENSITIVE})


@dataclass(frozen=True)
class Pulo:
    """Uma coisa que a varredura NAO leu, com o motivo -- e so isso.

    `relativo` e caminho relativo a raiz, com barra de POSIX, e nunca o
    absoluto. As duas metades dessa escolha foram decididas separadamente:

    - guardar o CAMINHO, e nao um marcador anonimo, porque o pulo existe para
      ser acionavel. "Ha um `prod.tfvars` em `infra/` que eu recusei" e um fato
      que o operador usa; "houve 1 recusa por nome sensivel" e indistinguivel de
      nao ter dito nada, que e exatamente o defeito que isto veio fechar.
    - guardar so o RELATIVO porque o prefixo absoluto e ambiente, nao evidencia:
      ele carrega nome de usuario, nome de cliente e layout de maquina para
      dentro de qualquer relatorio que renderize o pulo, e nao muda decisao
      nenhuma de quem le.

    O que NUNCA entra aqui: conteudo, trecho, tamanho ou hash de arquivo
    sensivel. Arquivo recusado por nome nao chega a ser aberto nem `stat`-ado --
    a checagem de sensivel roda ANTES do `stat` em `varrer_source_files`, e isso
    e ordem deliberada, nao acaso. Um campo de tamanho aqui obrigaria a tocar o
    arquivo so para preencher relatorio.

    Fica um risco residual, e esta escrito de proposito em vez de resolvido a
    martelo: o NOME de um arquivo pode, no limite, ser o proprio segredo
    (alguem que salva `AKIA....pem`). Redigir o nome mataria a utilidade inteira
    do registro para todos os outros casos, entao a saida e dar a quem renderiza
    uma classificacao barata -- `e_sensivel` -- em vez de obrigar a decidir por
    substring de caminho. Sanitizacao por substring foi como esta casa ja
    vazou antes; classificar na origem e o que substitui isso.
    """

    relativo: str
    razao: str

    @property
    def e_sensivel(self) -> bool:
        """Se a causa foi credencial, e nao custo nem defeito de sistema.

        Propriedade e nao campo: um booleano gravado na construcao poderia
        divergir da razao no dia em que alguem acrescentasse uma razao nova e
        esquecesse o campo -- e divergir para `False` seria vazamento silencioso.
        """
        return self.razao in RAZOES_SENSIVEIS


@dataclass(frozen=True)
class Varredura:
    """Os arquivos lidos E o que ficou de fora, na mesma resposta.

    Os dois campos juntos e o ponto inteiro: separar em duas chamadas deixaria
    quem consome livre para pedir so `arquivos`, que e a situacao anterior com
    um nome novo.

    `arquivos` guarda os caminhos como a travessia os montou, preservando a
    grafia da raiz -- e `pulos` guarda relativo. A assimetria e proposital:
    `arquivos` e para ABRIR (e quem chama faz `relative_to(repo_root)` em cima),
    `pulos` e para RELATAR, e um pulo que chega pronto para `open()` convida a
    ler exatamente o que a varredura acabou de recusar.
    """

    arquivos: tuple[Path, ...]
    pulos: tuple[Pulo, ...]


# Arvore de dependencia, artefato de build e metadados de ferramenta. Nada aqui
# e codigo do projeto analisado, e tudo aqui e volumoso.
DIRETORIOS_IGNORADOS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        ".env",
        "site-packages",
        ".tox",
        ".nox",
        "node_modules",
        "bower_components",
        "vendor",
        "build",
        "dist",
        ".eggs",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
        ".gradle",
        "target",
        ".terraform",
        ".sparkforge",
    }
)

# Cofres de credencial. Separados dos ignorados acima porque a razao e outra:
# nao sao volumosos nem irrelevantes, sao proibidos. O nome do arquivo la dentro
# nao denuncia nada (`.ssh/chave.json` e `secrets/db.json` sao `*.json` comuns),
# entao a unica defesa e podar a pasta.
#
# `gcloud` entra sem ponto de propósito: o gcloud guarda
# `application_default_credentials.json` em `~/.config/gcloud` no Linux e em
# `%APPDATA%\gcloud` no Windows -- em nenhum sistema existe `.gcloud`, e uma
# entrada que parece proteger e nao protege e pior que ausencia.
#
# `.serverless/` e `cdk.out/` sao saida de deploy, nao configuracao: o
# `serverless-state.json` guarda variavel de ambiente JA RESOLVIDA, e todo
# extrator de `*.json` varreria la dentro.
DIRETORIOS_SENSIVEIS: frozenset[str] = frozenset(
    {
        ".aws",
        ".ssh",
        ".gnupg",
        ".kube",
        ".docker",
        ".azure",
        "gcloud",
        "secrets",
        ".secrets",
        "credentials",
        ".credentials",
        ".serverless",
        "cdk.out",
    }
)

# Casado contra o primeiro componente delimitado por ponto (ver
# `_talo_delimitado`) -- nunca por `startswith`. `secrets.json` e credencial;
# `secrets_manager.tf` e o Terraform que o revisor de seguranca existe para ler,
# e um prefixo solto recusava os dois. `secret` no singular esta aqui porque
# `secret.yaml` de Kubernetes leva o bloco `data:` inteiro em base64.
TALOS_SENSIVEIS: frozenset[str] = frozenset(
    {
        "credentials",
        "secrets",
        "secret",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "kubeconfig",
        "application_default_credentials",
        ".env",
        ".netrc",
        ".npmrc",
        ".pypirc",
    }
)

# Casados contra o ULTIMO sufixo apenas. `.key` e `.pem` so condenam o arquivo
# quando sao a extensao de verdade: `servidor.key` e chave, `partition.key.json`
# e um JSON sobre chave de particao, e palavra corrente em repositorio de dados.
SUFIXOS_SENSIVEIS: tuple[str, ...] = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".tfstate",
    ".tfvars",
)

# Casados contra o PENULTIMO sufixo quando o ultimo e generico, para pegar
# `terraform.tfstate.json`. So entram os sufixos que ninguem usa como palavra de
# dominio -- `.key` e `.pem` ficam de fora justamente por serem ambiguos.
SUFIXOS_SENSIVEIS_COMPOSTOS: tuple[str, ...] = (".tfstate", ".tfvars", ".p12", ".pfx", ".jks")
SUFIXOS_GENERICOS: tuple[str, ...] = (".json", ".yaml", ".yml", ".txt", ".bak", ".tmp", ".orig")

# Extensao que o motor existe para LER, onde o nome nao condena o arquivo.
# `secrets.py` e um modulo sobre segredo, `secrets_manager.tf` e a declaracao do
# cofre: recusar os dois calado e o oposto do trabalho -- e o detector de
# segredo hardcoded so funciona sobre arquivo que chegou a ser lido. A poda de
# diretorio continua valendo: `.aws/x.tf` nao chega aqui.
EXTENSOES_ANALISADAS: frozenset[str] = frozenset({".py", ".tf"})

# Codigo-fonte: 1 MiB. A razao e parsing. Um `.py` de 1 MiB e gerado ou
# minificado, nao e codigo para ler, e montar AST de arquivo gigante e vetor de
# DoS. So entra aqui extensao que algum extrator realmente parseia por AST --
# hoje so `.py`. Conjunto minimo de proposito: extensao que ninguem parseia cair
# no teto de dados e o erro barato; artefato legitimo pulado e o caro.
EXTENSOES_CODIGO: frozenset[str] = frozenset({".py"})
TAMANHO_MAXIMO_CODIGO_BYTES = 1024 * 1024

# Artefato de dados: 128 MiB. O operador apontou para ele de proposito -- dump
# de listagem S3, plano de Terraform, metadados de Iceberg, event log.
#
# Medido neste repositorio: uma listagem S3 custa 143 bytes por objeto, estavel
# em tres fixtures (1.5 mil, 10 mil e 100 mil objetos). Parsear custa 2.6x o
# arquivo em RAM, medido com tracemalloc nas tres, entao 128 MiB tem pico de
# ~333 MiB -- pesado e sobrevivel.
#
# ESTE TETO CORTA CASO REAL, e o corte e silencioso. 128 MiB da ~940 mil
# objetos, e prefixo de producao com mais de um milhao de objetos e ordinario --
# e literalmente o cenario de small files que este motor existe para
# diagnosticar. Quanto pior o prefixo, mais provavel que a varredura o recuse.
# O numero nao esta calibrado pelo dominio; esta calibrado pelo que o processo
# aguenta parsear de uma vez. Subi-lo sem mudar a leitura para streaming so
# troca "recusa calada" por "processo derrubado".
TAMANHO_MAXIMO_DADOS_BYTES = 128 * 1024 * 1024

# `FILE_ATTRIBUTE_REPARSE_POINT`. Junction do Windows e reparse point mas NAO e
# symlink para o `os.path.islink`, e `mklink /J` nao pede administrador.
_REPARSE_POINT = getattr(_stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _e_atalho(caminho: Path) -> bool:
    """Symlink OU junction OU qualquer outro reparse point.

    `is_symlink()` sozinho devolve False para junction do Windows, e com isso
    `os.walk(followlinks=False)` desce nela. Como junction da nome novo a mesma
    pasta, `mklink /J atalho .aws` reintroduz exatamente o diretorio que a poda
    por nome tinha removido -- e o confinamento aprova, porque o destino esta
    mesmo dentro da raiz. Foi reproduzido sem privilegio de administrador.
    """
    try:
        atributos = os.lstat(caminho).st_file_attributes
    except (OSError, AttributeError):
        # Sem `st_file_attributes` (nao-Windows) o symlink e a unica forma.
        try:
            return caminho.is_symlink()
        except OSError:
            return True
    return bool(atributos & _REPARSE_POINT)


def _teto_para(caminho: Path) -> int:
    """Teto por tipo de conteudo, porque a razao de cada um e diferente.

    Um teto unico de 1 MiB esteve aqui e era defeito: ele vinha da regra de
    indexar codigo-fonte, onde e protecao legitima contra parsear AST de
    arquivo gigante. Aplicado a artefato de dados, cortava o caso normal --
    as duas fixtures que provam os limiares P0 e P1 de small files passam de
    1 MiB, e a travessia devolvia zero fact sobre elas.

    Extensao desconhecida usa o teto de dados. Este e o unico ponto fail-OPEN
    do modulo, de proposito: pular por engano um artefato legitimo e pior que
    ler um arquivo grande que nao interessa.
    """
    if caminho.suffix.lower() in EXTENSOES_CODIGO:
        return TAMANHO_MAXIMO_CODIGO_BYTES
    return TAMANHO_MAXIMO_DADOS_BYTES


def _e_pulumi_de_stack(nome: str) -> bool:
    """`Pulumi.prod.yaml` guarda secret cifrado; `Pulumi.yaml` nao guarda nada.

    A diferenca e so o componente do meio, entao nao da para decidir por talo
    nem por sufixo -- o talo de `Pulumi.prod.yaml` e `Pulumi.prod`.
    """
    partes = nome.lower().split(".")
    return len(partes) >= 3 and partes[0] == "pulumi" and partes[-1] in ("yaml", "yml")


def _talo_delimitado(nome: str) -> str:
    """Primeiro componente do nome, com o ponto inicial preservado.

    `Path.stem` nao serve sozinho: o talo de `.env.local.json` e `.env.local`,
    e a credencial e a familia `.env` inteira. Cortar no primeiro ponto casa
    `.env`, `.env.json` e `.env.local.json` sem casar `.envrc` nem
    `.environment.json` -- delimitado, nao `startswith`.
    """
    if nome.startswith("."):
        return "." + nome[1:].split(".", 1)[0]
    return nome.split(".", 1)[0]


def _e_sensivel(caminho: Path) -> bool:
    nome = caminho.name.lower()
    sufixos = [s.lower() for s in caminho.suffixes]
    ultimo = sufixos[-1] if sufixos else ""

    if ultimo in EXTENSOES_ANALISADAS:
        return False
    if _talo_delimitado(nome) in TALOS_SENSIVEIS:
        return True
    if ultimo in SUFIXOS_SENSIVEIS:
        return True
    if ultimo in SUFIXOS_GENERICOS and len(sufixos) >= 2:
        if sufixos[-2] in SUFIXOS_SENSIVEIS_COMPOSTOS:
            return True
    return _e_pulumi_de_stack(nome)


def _razao_de_poda(base: Path, nome_pasta: str) -> str | None:
    """Poda por nome E por atalho, porque so o nome nao basta -- com a razao.

    A poda por nome remove `.aws`; a junction `atalho_aws -> .aws` traz a mesma
    pasta de volta com nome que nao esta em lista nenhuma. Recusar todo atalho
    de diretorio fecha isso sem precisar resolver e reinspecionar cada pasta --
    medido, `os.lstat` por diretorio custa menos que `resolve()` por diretorio,
    e nao ha caminho para uma pasta reaparecer com outro nome sem reparse point.

    Devolve a razao em vez de um booleano porque as tres causas nao valem o
    mesmo la fora: ignorado e custo, sensivel e credencial, atalho e defesa
    contra junction. A ordem das duas primeiras checagens nao muda resultado
    (as listas sao disjuntas) mas muda a razao registrada, entao esta explicita.
    """
    minusculo = nome_pasta.lower()
    if minusculo in DIRETORIOS_SENSIVEIS:
        return DIRECTORY_SENSITIVE
    if minusculo in DIRETORIOS_IGNORADOS:
        return DIRECTORY_IGNORED
    if _e_atalho(base / nome_pasta):
        return DIRECTORY_REPARSE_POINT
    return None


def _deve_podar(base: Path, nome_pasta: str) -> bool:
    """A pergunta de sim-ou-nao, para quem so precisa decidir se desce."""
    return _razao_de_poda(base, nome_pasta) is not None


def _relativo(raiz: Path, caminho: Path) -> str:
    """Caminho relativo a raiz, com barra de POSIX, sem nunca cair no absoluto.

    `os.path.relpath` e nao `Path.relative_to` porque o confinamento tem que
    conseguir registrar um caminho que esta FORA da raiz -- `relative_to`
    levanta ali, e a alternativa seria guardar o absoluto justamente no caso em
    que ele mais expoe. `../vizinho/x.py` diz o necessario e para no vizinho.

    Sobra um caso em que nem relativo existe: no Windows, caminho em outro
    volume. Ai fica so o nome do arquivo -- perde-se o "onde", que e o menor
    prejuizo possivel, e nao se ganha o absoluto de brinde.
    """
    try:
        return Path(os.path.relpath(caminho, raiz)).as_posix()
    except ValueError:
        return caminho.name


def varrer_source_files(root: Path | str, pattern: str) -> Varredura:
    """A varredura inteira: o que foi lido E o que foi pulado, com a razao.

    A raiz e validada agora, nao no primeiro `next()`: quem chama sem iterar
    -- ou quem so mede `len` depois -- receberia silencio de um gerador
    preguicoso, e apontar para o lugar errado tem que doer na hora.

    A ordem dos arquivos e a ordenacao global por caminho, identica a
    `sorted(root.rglob())` que estes extratores usavam. `os.walk` visita por
    nivel, o que intercala subpasta e arquivo diferente; reordenar no fim e o
    que impede a troca de varredura de mexer em golden de extrator que nao
    reordena por conta. Os pulos sao ordenados pelo mesmo motivo: saida
    comparavel entre duas execucoes sobre a mesma arvore.

    Os caminhos devolvidos em `arquivos` preservam a grafia de `root` -- so o
    confinamento resolve links. Devolver o caminho resolvido quebraria o
    `relative_to(repo_root)` de quem chama sempre que a raiz for relativa.

    A ORDEM DAS CHECAGENS E SEMANTICA, nao arrumacao. `_e_sensivel` roda antes
    de qualquer `stat`, `resolve` ou leitura: arquivo recusado por nome nao e
    tocado, nem para preencher o registro do proprio pulo. E o padrao e casado
    primeiro de todos porque o que nao casa nao e pulo -- e filtro de quem
    chamou, e nao vira `Pulo`.
    """
    raiz = Path(root).expanduser()
    if not raiz.exists():
        raise ScanError(f"raiz inexistente: {raiz}")
    if not raiz.is_dir():
        raise ScanError(f"raiz nao e diretorio: {raiz}")
    raiz_real = raiz.resolve()

    achados: list[Path] = []
    pulos: list[Pulo] = []

    def pular(caminho: Path, razao: str) -> None:
        pulos.append(Pulo(relativo=_relativo(raiz, caminho), razao=razao))

    # `followlinks=False` e o default do os.walk e esta explicito so como
    # declaracao. Quem de fato impede descer por atalho e `_razao_de_poda`, que
    # remove a pasta antes -- inclusive junction, que `followlinks` nao ve.
    # Nenhum teste consegue matar a mutacao `followlinks=True` por isso: com a
    # poda no lugar, o parametro nao muda resultado nenhum.
    for pasta_atual, subpastas, arquivos in os.walk(raiz, followlinks=False):
        base = Path(pasta_atual)
        # Poda no lugar: os.walk respeita a mutacao e nem desce nas removidas.
        # Filtrar so no fim daria a mesma lista tendo pago para listar o
        # `.venv` inteiro, que e o custo que esta varredura existe para evitar.
        # A pasta podada e registrada UMA vez, aqui: registrar o que ha dentro
        # exigiria descer nela, que e precisamente o que a poda evita -- entao o
        # sinal e "esta arvore nao foi olhada", nao uma lista do conteudo dela.
        sobreviventes = []
        for nome_pasta in subpastas:
            razao_poda = _razao_de_poda(base, nome_pasta)
            if razao_poda is None:
                sobreviventes.append(nome_pasta)
            else:
                pular(base / nome_pasta, razao_poda)
        subpastas[:] = sobreviventes
        for nome in arquivos:
            caminho = base / nome
            if not caminho.match(pattern):
                continue
            if _e_atalho(caminho):
                pular(caminho, REPARSE_POINT)
                continue
            if not caminho.is_file():
                pular(caminho, NOT_A_REGULAR_FILE)
                continue
            if _e_sensivel(caminho):
                pular(caminho, SENSITIVE_NAME)
                continue
            try:
                if caminho.stat().st_size > _teto_para(caminho):
                    pular(caminho, SIZE_ABOVE_LIMIT)
                    continue
                # Confinamento: mesmo com a poda de atalho, um componente
                # intermediario pode ter sido substituido durante a varredura.
                real = caminho.resolve()
                if raiz_real != real and raiz_real not in real.parents:
                    pular(caminho, OUTSIDE_ROOT)
                    continue
            except OSError:
                # Ilegivel, sumido no meio da varredura, ou nome que o sistema
                # recusa. Some da saida do mesmo jeito, e some COM razao: e o
                # unico pulo que nao e decisao deste modulo, e confundi-lo com
                # os outros esconderia problema de ambiente dentro de politica.
                pular(caminho, OS_ERROR)
                continue
            achados.append(caminho)
    return Varredura(
        arquivos=tuple(sorted(achados)),
        pulos=tuple(sorted(pulos, key=lambda p: (p.relativo, p.razao))),
    )


def iter_source_files(root: Path | str, pattern: str) -> Iterator[Path]:
    """Arquivos regulares sob `root` que casam `pattern`, em ordem estavel.

    A forma antiga da varredura, preservada byte a byte no que devolve: mesma
    sequencia, mesma ordem, mesma validacao eager da raiz. Catorze modulos de
    `facts/` iteram isto, e ha golden de extrator gravado sob a ordenacao global
    por caminho -- mudar o que sai daqui e mudar golden que nao tem nada a ver
    com pulo.

    Quem precisa saber o que NAO foi varrido chama `varrer_source_files` e le
    `Varredura.pulos`. Nao ha `pulos` escondido num atributo do iterador de
    proposito: sinal que so aparece para quem ja sabia procurar e o mesmo
    silencio com mais passos.
    """
    return iter(varrer_source_files(root, pattern).arquivos)
