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
`prompt_migrations_glue.md` Sec 8.8) e dois observados por ARQUIVO INTEIRO, nao
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
# coisa diferente da versao da BIBLIOTECA que le/escreve. Confundir as duas e
# o erro citado explicitamente em `prompt_migrations_glue.md` Sec 8.8.
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


def _jar_facts(path: Path, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Um `.jar` e uma OBSERVACAO de arquivo inteiro: um binario nao tem linha
    de fonte para varrer, entao um fact por arquivo (nao por linha) e a
    granularidade correta. `line=0` no subject marca isso -- nao ha linha
    nenhuma a apontar, so o arquivo. Mora fora de `extract_migration_path` por
    isso: aquela funcao existe para varrer texto Python linha a linha.
    """
    scala_match = _JAR_SCALA_RE.search(path.name)
    scala = scala_match.group(1) if scala_match else ""
    return [
        Fact(
            kind="mig.jar_binary",
            subject=_source_subject(anchor, 0),
            attrs={"scala": scala},
            provenance=provenance,
        )
    ]


def _python_dep_facts(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    """Dependencia Python pinada em requirements*.txt -- observacao de
    manifesto, nao de fonte Python, entao mora ao lado de `_jar_facts` em
    `extract_migration_tree`. Linha em branco, comentario (`#`) e pacote sem
    pin (`pandas` sem `==`) nao emitem fact de proposito: nenhuma das tres
    fixa uma versao, e fixar versao e exatamente o que este kind observa.
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
        facts.append(
            Fact(
                kind="mig.python_dep",
                subject=_source_subject(anchor, lineno),
                attrs={"package": pacote, "version": versao},
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

    facts = _sdk_imports(text, anchor, provenance) + _config_facts(text, anchor, provenance)

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
