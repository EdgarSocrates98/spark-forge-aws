"""Observacoes de migracao entre versoes de Glue.

Uma fase em andamento adiciona analise de compatibilidade para migrar um job
Glue entre um par arbitrario de versoes. Este extrator OBSERVA sinais de
migracao no codigo-fonte e nunca julga: um import `com.amazonaws.*` (SDK v1
da AWS) e uma OBSERVACAO. Que ele seja bloqueante para uma versao-alvo
especifica e JUIZO, e pertence a uma regra com `runtime_scope` declarado no
catalogo (Task 7 desta fase). Essa divisao e o que permite julgar facts
antigos com um catalogo de regras novo sem reparsear o artefato -- o mesmo
contrato descrito em `sparkforge/findings/models.py` para `Fact`.

`EMITTED_KINDS` declarava apenas `mig.sdk_import` (Task 4). A Task 5 soma tres:
`mig.emrfs_config`, `mig.legacy_conf` e `mig.deprecated_api`, lidos das mesmas
linhas de fonte Python. Cada kind entra no vocabulario no MESMO commit em que
ganha extrator e fixture golden -- convencao ja em uso em `graph.py` e
`emr_serverless.py`, cujos comentarios de Task explicam por que:
`tests/test_fixtures_kind_coverage.py` exige golden para todo kind de
`EMITTED_KINDS` assim que o modulo entra no registro `EXTRACTORS` daquele
teste (e do `tests/test_rules_catalog_reachability.py`). Declarar kinds
aspiracionais aqui nao quebra nada HOJE porque `migration` ainda nao esta em
nenhum dos dois registros -- mas quebraria assim que alguem o registrasse
antes de todos os kinds terem golden, entao o vocabulario fica restrito ao que
o modulo de fato emite.

Os tres kinds novos sao OBSERVACAO, nao juizo: que `fs.s3.consistent` seja uma
chave exclusiva do EMRFS e um fato sobre o vocabulario da chave, nao sobre se
ela quebra alguma coisa. Que o S3A usado do Glue 5 em diante nao leia essa
chave e nao reclame dela -- silencio, nao erro -- e o que torna a chave
perigosa (ela sobrevive no codigo parecendo configurada) e e justamente o tipo
de leitura que pertence a uma regra com `runtime_scope`, nunca a este modulo.

A Task 6 fecha o vocabulario planejado desta fase com quatro kinds: dois
observados por linha de fonte Python (`mig.ansi_risk`, um `cast(` sem a forma
guardada `try_cast(`; `mig.table_format`, a versao do FORMATO de uma tabela
Iceberg/Hudi/Delta -- distinta da versao da biblioteca que le/escreve, ver
`knowledge/storage/iceberg-v3.md`) e dois observados por ARQUIVO INTEIRO, nao
por linha (`mig.jar_binary`, `mig.python_dep`). Os dois ultimos moram em
`extract_migration_tree`, nao em `extract_migration_path`: um `.jar` nao tem
linha de fonte Python para varrer, e uma linha de `requirements.txt` nao e
Python. Convocar essas observacoes por linha de fonte (dentro de
`extract_migration_path`) emitiria um fact por jar/dependencia a cada arquivo
`.py` visitado -- duplicata pura, nao uma segunda observacao.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "migration@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "mig.sdk_import",
        "mig.emrfs_config",
        "mig.legacy_conf",
        "mig.deprecated_api",
        "mig.ansi_risk",
        "mig.table_format",
        "mig.jar_binary",
        "mig.python_dep",
        "mig.renamed_conf",
        "mig.removed_api",
    }
)

# SDK v1 da AWS para Java/Scala: `com.amazonaws.*`. Aparece em jobs Glue que
# chamam a API do SDK diretamente (fora do que `awsglue`/`boto3` cobrem), tipo
# comum em UDF ou bootstrap escrito antes da migracao para o SDK v2.
_SDK_V1_RE = re.compile(r"\bcom\.amazonaws\b")

# SDK v2, sucessor do v1. Observar os dois lado a lado deixa explicito qual
# geracao um job ja usa, sem precisar de uma segunda passada.
_SDK_V2_RE = re.compile(r"\bsoftware\.amazon\.awssdk\b")

_SDK_GENERATIONS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (_SDK_V1_RE, "v1", "com.amazonaws"),
    (_SDK_V2_RE, "v2", "software.amazon.awssdk"),
)

# Prefixo exclusivo do EMRFS. O S3A do Glue 5+ nao le nenhuma destas chaves,
# entao elas sobrevivem no codigo sem efeito -- silencio, que e pior que erro.
_EMRFS_PREFIXES = ("fs.s3.consistent", "fs.s3.enableServerSideEncryption", "fs.s3.maxRetries")
_CONF_KEY_RE = re.compile(r'["\']([\w.\-]+)["\']')
_LEGACY_CONF_RE = re.compile(r'["\'](spark\.sql\.legacy\.[\w.]+)["\']')
_DEPRECATED_SYMBOLS = ("SQLContext", "HiveContext")
_DEPRECATED_SYMBOL_RES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(r"\b" + re.escape(symbol) + r"\b"), symbol) for symbol in _DEPRECATED_SYMBOLS
)

# `cast(` sem a forma guardada `try_cast(` -- sob ANSI mode um cast invalido
# estoura em vez de devolver null, entao um job que dependia do null silencioso
# muda de resultado ou passa a falhar. Checado no REPL antes de confiar: `\b`
# sozinho ja barra `try_cast(` porque `_` e caractere de palavra em regex (nao
# ha fronteira \b entre `_` e `c`), o que torna `(?<!try_)` redundante para
# este caso especifico -- mas ele fica explicito mesmo assim, documentando a
# intencao e blindando contra uma futura reescrita de `\bcast` que remova o
# `\b` sem perceber a dependencia.
_CAST_RE = re.compile(r"(?<!try_)\bcast\s*\(", re.IGNORECASE)

# `format-version` e a versao do FORMATO de uma tabela Iceberg/Hudi/Delta --
# coisa diferente da versao da BIBLIOTECA que le/escreve. Confundir as duas
# produz a recomendacao errada nos dois sentidos: "o Iceberg 1.11 suporta"
# nao responde "esta tabela e v3", e vice-versa. `knowledge/storage/
# iceberg-v3.md` separa as duas metades, e `sparkforge/storage/
# feature_support.py` grava a separacao em codigo.
_FORMAT_VERSION_RE = re.compile(r"format-version['\"]?\s*[=:]\s*['\"]?(\d+)")

# Scala embutido no nome do jar, ex. `conector_2.12-1.4.0.jar` -> "2.12".
# Convencao comum em artefatos Java/Scala do ecossistema Spark, mas nem todo
# jar segue -- por isso o extrator observa o jar de qualquer forma e deixa o
# campo `scala` vazio quando o nome nao encodifica a versao (sobre-capturar
# a OBSERVACAO "existe um jar aqui" custa menos que perder o binario).
_JAR_SCALA_RE = re.compile(r"_(\d+\.\d+)-")

# Dependencia Python pinada com `==` em requirements*.txt. So reconhece a
# forma pinada de proposito: e exatamente essa fixacao de versao que o kind
# observa, entao uma linha sem `==` nao e um fato deste vocabulario.
_REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s#]+)")

# Primeiro segmento numerico da versao pinada, ancorado no INICIO da string.
# Ler o major e OBSERVACAO -- o numero esta escrito no arquivo -- e existe
# porque o avaliador de `expr` do catalogo (`sparkforge/rules/expr.py`) compara
# NUMEROS, nao versoes: uma regra de piso de dependencia precisa de um inteiro
# em `attrs` para comparar, e a string `"11.0.0"` nao e comparavel com `15`
# naquele avaliador. O LIMIAR continua na regra, que e onde o juizo mora.
#
# Ancorado (`^`) de proposito: sem a ancora, `@git+https://host/x.git@v2` daria
# um "major" tirado do meio de uma URL -- um numero inventado com cara de fato.
_VERSION_MAJOR_RE = re.compile(r"^(\d+)")


# Configs que MUDARAM DE NOME no Spark 4.0 -- o nome antigo nao e lido e nao
# reclama, entao o job segue rodando com a configuracao que quem le acha que
# esta ativa. Mesmo modo de falha de `fs.s3.consistent` no Glue 5 (SF-MIG-002):
# silencio, nao erro. Mapa fechado de proposito: `spark.sql.legacy.` continua
# sendo um prefixo VALIDO em Spark 4 (`timeParserPolicy`, `ctePrecedencePolicy`),
# e tratar a familia inteira como renomeada acusaria config correta.
_RENAMED_CONF: dict[str, str] = {
    "spark.sql.legacy.parquet.int96RebaseModeInWrite": (
        "spark.sql.parquet.int96RebaseModeInWrite"
    ),
    "spark.sql.legacy.parquet.datetimeRebaseModeInWrite": (
        "spark.sql.parquet.datetimeRebaseModeInWrite"
    ),
    "spark.sql.legacy.parquet.int96RebaseModeInRead": (
        "spark.sql.parquet.int96RebaseModeInRead"
    ),
    "spark.sql.legacy.avro.datetimeRebaseModeInWrite": (
        "spark.sql.avro.datetimeRebaseModeInWrite"
    ),
    "spark.sql.legacy.avro.datetimeRebaseModeInRead": (
        "spark.sql.avro.datetimeRebaseModeInRead"
    ),
    # Nao e config: e valor de `compression`. Entra no mesmo kind porque o
    # fato observado e o mesmo -- um nome que o runtime alvo nao aceita mais.
    "lz4raw": "lz4_raw",
}


# APIs de pandas-on-Spark removidas no Spark 4.0. Mapa fechado: so entra aqui
# o que a fonte oficial lista como REMOVIDO, nunca o que ela chama de
# deprecado -- deprecado ainda roda, e acusar os dois junto apagaria a
# diferenca entre "quebra" e "vai quebrar".
_REMOVED_API: dict[str, str] = {
    "append": "ps.concat",
    "iteritems": ".items",
    "to_koalas": "DataFrame.pandas_api",
    "koalas": "DataFrame.pandas_on_spark",
    "get_dtype_counts": "DataFrame.dtypes.value_counts()",
    "is_monotonic": ".is_monotonic_increasing",
    "backfill": ".bfill",
    "pad": ".ffill",
    "mad": "",
    "Int64Index": "Index",
    "Float64Index": "Index",
}

# Nome que comeca com minuscula e metodo/propriedade: so casa precedido de
# ponto, senao a variavel local `pad = 4` viraria observacao de API removida.
# O `\b` FINAL e o que separa `is_monotonic` de `is_monotonic_increasing` --
# sem ele o casamento por substring acusaria justamente o codigo JA CORRIGIDO,
# o falso positivo mais caro que existe porque ensina a ignorar a regra.
# Nome que comeca com maiuscula (`Int64Index`, `Float64Index`) e CLASSE, nao
# metodo: aparece como nome livre em import, anotacao ou construtor, entao casa
# por fronteira de palavra dos dois lados -- exigir ponto ali perderia todas as
# tres formas.
_REMOVED_API_RES: tuple[tuple[re.Pattern[str], str, str], ...] = tuple(
    (
        re.compile((r"\b" if nome[:1].isupper() else r"\.") + re.escape(nome) + r"\b"),
        nome,
        substituto,
    )
    for nome, substituto in _REMOVED_API.items()
)

# Import de pandas-on-Spark no TEXTO do modulo. Conjunto FECHADO de formas -- as
# quatro que a documentacao do pandas-on-Spark usa. Reconhecer forma inventada
# aqui seria voltar a adivinhar, que e exatamente o defeito que este sinal
# conserta.
#
# `import pandas` puro NAO entra: quem removeu `DataFrame.append` foi o
# `pyspark.pandas`, e o pandas do PyPI segue o proprio ciclo de vida.
_PANDAS_ON_SPARK_IMPORT_RE = re.compile(
    r"^\s*(?:"
    r"import\s+pyspark\.pandas\b"  # cobre tambem `import pyspark.pandas as <alias>`
    r"|from\s+pyspark\.pandas\s+import\b"
    r"|from\s+pyspark\s+import\s+pandas\b"
    r")",
    re.MULTILINE,
)


def _source_subject(file: str, line: int) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": file,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _sdk_imports(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    facts: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        for regex, geracao, pacote in _SDK_GENERATIONS:
            if regex.search(linha):
                facts.append(
                    Fact(
                        kind="mig.sdk_import",
                        subject=_source_subject(anchor, lineno),
                        attrs={"package": pacote, "generation": geracao},
                        provenance=provenance,
                    )
                )
    return facts


def _config_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """EMRFS, config legada do Spark e API depreciada -- mesma varredura ingenua
    linha a linha que `_sdk_imports` ja faz para `com.amazonaws`: regex sobre o
    texto cru, sem checar se a linha e uma chamada real a `spark.conf.set` (nem
    se esta dentro de comentario ou string). Decisao deliberada: sobre-capturar
    custa a quem escreve a regra explicar um falso positivo; sub-capturar
    esconde uma configuracao morta para sempre -- e essa e a categoria de erro
    que este extrator existe para evitar (ver `tests/test_facts_migration.py`,
    `test_reconhece_chave_de_emrfs_dentro_de_comentario_por_design`).
    """
    facts: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        for legada in _LEGACY_CONF_RE.findall(linha):
            facts.append(
                Fact(
                    kind="mig.legacy_conf",
                    subject=_source_subject(anchor, lineno),
                    attrs={"key": legada},
                    provenance=provenance,
                )
            )
        for chave in _CONF_KEY_RE.findall(linha):
            if chave.startswith(_EMRFS_PREFIXES):
                facts.append(
                    Fact(
                        kind="mig.emrfs_config",
                        subject=_source_subject(anchor, lineno),
                        attrs={"key": chave},
                        provenance=provenance,
                    )
                )
        for regex, simbolo in _DEPRECATED_SYMBOL_RES:
            if regex.search(linha):
                facts.append(
                    Fact(
                        kind="mig.deprecated_api",
                        subject=_source_subject(anchor, lineno),
                        attrs={"symbol": simbolo},
                        provenance=provenance,
                    )
                )
        if _CAST_RE.search(linha):
            facts.append(
                Fact(
                    kind="mig.ansi_risk",
                    subject=_source_subject(anchor, lineno),
                    attrs={"form": "cast"},
                    provenance=provenance,
                )
            )
        formato = _FORMAT_VERSION_RE.search(linha)
        if formato:
            facts.append(
                Fact(
                    kind="mig.table_format",
                    subject=_source_subject(anchor, lineno),
                    attrs={"format_version": formato.group(1)},
                    provenance=provenance,
                )
            )
    return facts


def _renamed_conf_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Observa nome antigo de config renomeada no Spark 4.0.

    Le o mesmo token entre aspas que `_config_facts` ja le -- nao reparseia a
    linha de outro jeito, para que as duas leituras nunca discordem sobre o que
    esta escrito ali.

    Quebra as linhas com `split("\\n")`, e nao com `splitlines()`, pela mesma
    razao: `splitlines()` tambem corta em form feed (`\\f`, separador de pagina
    legal em fonte Python), `\\v` e U+2028, e `split("\\n")` nao. Um job com
    qualquer um desses caracteres faria `mig.legacy_conf` e `mig.renamed_conf`
    numerarem a MESMA linha de forma diferente, e um operador lendo dois
    subjects divergentes procuraria a config em dois lugares -- um dos quais
    nao existe.
    """
    facts: list[Fact] = []
    for numero, linha in enumerate(text.split("\n"), start=1):
        for token in _CONF_KEY_RE.findall(linha):
            novo = _RENAMED_CONF.get(token)
            if novo is None:
                continue
            facts.append(
                Fact(
                    kind="mig.renamed_conf",
                    subject=_source_subject(anchor, numero),
                    attrs={"key": token, "renamed_to": novo},
                    provenance=provenance,
                )
            )
    return facts


def _removed_api_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Observa nome de API de pandas-on-Spark removida no Spark 4.0.

    Le a LINHA CRUA em vez da AST de proposito. `sparkforge/facts/pyspark_ast.py`
    existe e e mais preciso -- separaria `.append(` de um atributo homonimo e
    daria coluna exata -- mas exige que o arquivo seja Python VALIDO para o
    interpretador que roda este processo, e parte do corpus que este extrator
    varre e codigo escrito para um Python mais antigo: justamente o codigo com
    mais chance de ainda usar API removida. Leitura por linha degrada para
    "observei um nome"; leitura por AST degradaria para "nao observei nada",
    que e falso negativo silencioso -- o erro que este extrator existe para
    evitar.

    Quebra as linhas com `split("\\n")` pela mesma razao que
    `_renamed_conf_facts`: `splitlines()` tambem corta em form feed e U+2028, e
    dois detectores numerando a MESMA linha de forma diferente mandariam quem
    le os subjects procurar em dois lugares, um dos quais nao existe.

    `attrs.pandas_on_spark_module` diz se o TEXTO deste modulo importa
    `pyspark.pandas`. E OBSERVACAO, nao juizo, pelo mesmo criterio que separa
    `mig.python_dep.major` do limiar que o compara: a afirmacao e sobre o que
    esta ESCRITO no arquivo -- existe uma linha de import ali --, e o extrator ja
    le o modulo inteiro para varrer linha a linha, entao observar os imports nao
    lhe da poder novo nenhum. O JUIZO -- "entao este `.append` provavelmente e a
    API removida, e nao o metodo de uma lista Python" -- mora em SF-SPARK4-002,
    via `where`, que e onde limiar e decisao pertencem.
    """
    facts: list[Fact] = []
    # Uma vez por arquivo, nao por linha: o import e propriedade do MODULO, e a
    # linha do `.append(` nao muda o que o cabecalho do arquivo importa.
    pandas_on_spark = bool(_PANDAS_ON_SPARK_IMPORT_RE.search(text))
    for numero, linha in enumerate(text.split("\n"), start=1):
        for regex, nome, substituto in _REMOVED_API_RES:
            if not regex.search(linha):
                continue
            facts.append(
                Fact(
                    kind="mig.removed_api",
                    subject=_source_subject(anchor, numero),
                    attrs={
                        "symbol": nome,
                        "replacement": substituto,
                        "pandas_on_spark_module": pandas_on_spark,
                    },
                    provenance=provenance,
                )
            )
    return facts


def _jar_facts(path: Path, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Um `.jar` e uma OBSERVACAO de arquivo inteiro: um binario nao tem linha
    de fonte para varrer, entao um fact por arquivo (nao por linha) e a
    granularidade correta. `line=0` no subject marca isso -- nao ha linha
    nenhuma a apontar, so o arquivo. Mora fora de `extract_migration_path` por
    isso: aquela funcao existe para varrer texto Python linha a linha.

    `scala_minor` e o segundo segmento do que ja foi observado em `scala`
    ("2.12" -> 12). Extrair o numero e OBSERVACAO, nao juizo, pelo mesmo
    criterio que separa `mig.python_dep.major` do limiar que o compara: o
    numero esta ESCRITO no nome do arquivo, e le-lo nao da poder novo nenhum ao
    extrator. Existe porque o avaliador de `expr` do catalogo
    (`sparkforge/rules/expr.py`) compara NUMEROS, nao versoes: uma regra de
    fronteira binaria de Scala precisa de um inteiro em `attrs` para comparar, e
    a string "2.12" nao e comparavel com 13 naquele avaliador. O LIMIAR continua
    na regra, que e onde o juizo mora.

    O campo so aparece quando o major capturado e `2`, e essa guarda existe
    porque `_JAR_SCALA_RE` casa QUALQUER `_X.Y-`, nao so o sufixo de Scala:
    `minhalib_1.0-SNAPSHOT.jar` daria `scala_minor` 0 e faria uma regra de piso
    acusar em P0 um artefato que nunca teve Scala nenhum. `2` e o unico major
    que usa essa forma -- Scala 3 publica `_3-`, sem minor, que este regex nao
    captura de qualquer jeito.

    Jar cujo nome nao encodifica a versao (`scala == ""`) fica SEM a chave, e
    isso e fail-closed deliberado: as alternativas seriam adivinhar um numero
    (`0`, `-1`) ou marcar com `None`, e as duas fariam uma regra de piso --
    `attrs.scala_minor < 13` -- disparar sobre um jar cuja versao de Scala
    ninguem leu. Pior: um jar que nao declara Scala no nome pode ser JAVA PURO,
    que nao tem versao de Scala nenhuma para estar errada -- acusa-lo seria
    acusar artefato correto, que e o estrago que `rules/catalog/README.md`
    registra como o mais caro de todos. Sem a chave, o caminho fica ausente no
    avaliador (`ExprError`, logo `False`) e a regra fica muda sobre o que nao
    consegue afirmar. A OBSERVACAO "existe um jar aqui" continua sendo emitida
    de qualquer forma.
    """
    scala_match = _JAR_SCALA_RE.search(path.name)
    scala = scala_match.group(1) if scala_match else ""
    attrs: dict[str, Any] = {"scala": scala}
    major, _, minor = scala.partition(".")
    if major == "2":
        attrs["scala_minor"] = int(minor)
    return [
        Fact(
            kind="mig.jar_binary",
            subject=_source_subject(anchor, 0),
            attrs=attrs,
            provenance=provenance,
        )
    ]


def _python_dep_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Dependencia Python pinada em requirements*.txt -- observacao de
    manifesto, nao de fonte Python, entao mora ao lado de `_jar_facts` em
    `extract_migration_tree`. Linha em branco, comentario (`#`) e pacote sem
    pin (`pandas` sem `==`) nao emitem fact de proposito: nenhuma das tres
    fixa uma versao, e fixar versao e exatamente o que este kind observa.

    `major` so entra em `attrs` quando a versao COMECA por digito. Versao que
    nao comeca por digito (`pacote==@git+https://...` fixa um commit, nao um
    numero) fica SEM a chave, e isso e fail-closed deliberado: as alternativas
    seriam adivinhar um numero (`0`, `-1`) ou marcar com `None`, e as duas
    fariam uma regra de piso -- `attrs.major < 15` -- disparar sobre uma
    dependencia cuja versao ninguem leu. Sem a chave, o caminho fica ausente no
    avaliador (`ExprError`, logo `False`) e a regra fica muda sobre o que nao
    consegue afirmar. Ausencia de juizo custa um achado que nao foi feito;
    juizo sobre um numero inventado custa a confianca no relatorio inteiro.
    """
    facts: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        stripped = linha.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _REQUIREMENT_RE.match(stripped)
        if not match:
            continue
        pacote, versao = match.group(1), match.group(2)
        attrs: dict[str, Any] = {"package": pacote, "version": versao}
        major = _VERSION_MAJOR_RE.match(versao)
        if major:
            attrs["major"] = int(major.group(1))
        facts.append(
            Fact(
                kind="mig.python_dep",
                subject=_source_subject(anchor, lineno),
                attrs=attrs,
                provenance=provenance,
            )
        )
    return facts


def extract_migration_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um `.py`, ancorando o path relativo a `repo_root`."""
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")

    text = path.read_text(encoding="utf-8-sig")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}

    facts = (
        _sdk_imports(text, anchor, provenance)
        + _config_facts(text, anchor, provenance)
        + _renamed_conf_facts(text, anchor, provenance)
        + _removed_api_facts(text, anchor, provenance)
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_migration_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `.py`, `.jar` e `requirements*.txt` sob `root`, em
    ordem deterministica de path.

    `.jar` e `requirements*.txt` NAO passam por `extract_migration_path`:
    aquela funcao varre texto Python linha a linha, e nem um binario nem um
    manifesto de dependencias sao isso. Cada um ganha sua propria varredura de
    arquivo aqui -- um fact por jar (`_jar_facts`), um fact por linha pinada de
    requirements (`_python_dep_facts`) -- para que a responsabilidade "andar a
    arvore de arquivos" fique so nesta funcao, nunca em `extract_migration_path`.
    """
    base = repo_root or root
    facts: list[Fact] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        facts.extend(extract_migration_path(py, base))

    for jar in sorted(root.rglob("*.jar")):
        anchor = str(jar.relative_to(base)).replace("\\", "/")
        sha = hashlib.sha256(jar.read_bytes()).hexdigest()
        provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
        facts.extend(_jar_facts(jar, anchor, provenance))

    for req in sorted(root.rglob("requirements*.txt")):
        anchor = str(req.relative_to(base)).replace("\\", "/")
        text = req.read_text(encoding="utf-8-sig")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
        facts.extend(_python_dep_facts(text, anchor, provenance))

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)
