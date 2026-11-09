"""Coletor do FOOTER do Parquet -- e nada do dado.

Le o rodape de cada arquivo (schema, offsets, e as estatisticas por coluna por
row group) e grava um artefato JSON. **Nenhuma linha de dado e lida**: um
extrator que abrisse o dado estaria lendo producao para diagnosticar layout.

## Por que ele existe

`knowledge/storage/parquet-layout.md` §2 ja afirma que estatistica min/max so
serve se os valores estiverem AGRUPADOS, e o §6 manda conferir sort order contra
as colunas de filtro. Medido em 2026-09-09, antes desta entrega: nenhum extrator
do motor abria um arquivo Parquet. O conhecimento estava escrito e o motor nao o
media -- ver o cabecalho de `sparkforge_aws/facts/parquet_footer.py`.

## pyarrow e OPCIONAL, e o par de modulos existe por isso

`require_pyarrow()` no molde de `require_boto3()`: importado sob demanda, nunca
no topo. O nucleo determinístico continua com `PyYAML` + `jsonschema` e mais
nada, e quem roda `judge` sobre um artefato ja coletado nao precisa da
dependencia. E por isso que a LEITURA do footer e a EXTRACAO de fact sao dois
modulos, e nao um.

## A amostragem e DECLARADA, nunca inventada

Ler o footer custa um round-trip por arquivo, e uma tabela com 100 000 arquivos
nao e lida inteira. O operador declara `max_files`; o artefato registra
`files_seen`, `files_read` e `sampling`, e o extrator os carrega para
`parquet.footer_analyzed` com `partial: true`.

**A amostra e os N PRIMEIROS na ordem do nome, e nao N ao acaso.** Amostra
aleatoria daria um censo que muda a cada coleta sobre a mesma tabela, e dois
`facts.json` do mesmo prefixo deixariam de ser comparaveis -- o oposto do que um
barramento de handoff committado precisa ser. `sampling` grava qual regra foi
usada, para que trocar a regra um dia seja diff e nao surpresa.

## Recusa tem NOME, e vira artefato em vez de excecao

Prefixo inexistente, prefixo sem arquivo Parquet, permissao negada, credencial
ausente e pyarrow indisponivel produzem o MESMO `files: []`. Por isso o artefato
carrega `status`, e `facts/parquet_footer.py` o traduz em `parquet.unresolved`
com a razao (regra 20 do `CLAUDE.md`). `CollectionFailed` fica reservado ao que
impede ate a recusa de ser gravada.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sparkforge_aws.collect.aws import (
    CollectionFailed,
    _offline_hit,
    _write_and_register,
)
from sparkforge_aws.collect.base import CollectorUnavailable, require_boto3
from sparkforge_aws.facts.scan import iter_source_files

# Teto de arquivos lidos por coleta. Existe pela mesma razao do teto de paginas
# de `filter_log_events`: sem ele, um prefixo com 100 000 arquivos vira 100 000
# round-trips, e o operador descobre isso pela fatura.
_MAX_FILES_PADRAO = 20

# Teto duro, acima do que o operador pode pedir. Nao e conservadorismo: cada
# footer entra INTEIRO no artefato, e um artefato de centenas de MB deixa de
# caber no barramento que ele deveria servir.
_MAX_FILES_TETO = 500

SAMPLING_PRIMEIROS = "first_n_by_name"

STATUS_OK = "ok"
STATUS_PREFIXO_INEXISTENTE = "prefixo_inexistente"
STATUS_PREFIXO_VAZIO = "prefixo_vazio"
STATUS_SEM_PERMISSAO = "sem_permissao"
STATUS_SEM_CREDENCIAL = "sem_credencial"
STATUS_PYARROW_INDISPONIVEL = "pyarrow_indisponivel"


class _AwsProfileUnavailable(CollectorUnavailable):
    """Perfil AWS declarado, mas nao resolvido pelo provider do SDK."""

# Codigos comparados como STRING porque botocore nunca e importado aqui -- mesma
# disciplina de `require_boto3` em `cloudwatch_logs.py`.
_CODIGOS_INEXISTENTE = frozenset({"NoSuchBucket", "NoSuchKey", "404", "NotFound"})
_CODIGOS_SEM_PERMISSAO = frozenset(
    {"AccessDenied", "AccessDeniedException", "AllAccessDisabled", "403"}
)
_EXCECOES_SEM_CREDENCIAL = frozenset(
    {
        "NoCredentialsError",
        "PartialCredentialsError",
        "CredentialRetrievalError",
        "TokenRetrievalError",
        "UnauthorizedSSOTokenError",
        "NoRegionError",
    }
)


def require_pyarrow() -> Any:
    """Importa pyarrow sob demanda. Nunca no topo deste modulo, pela mesma razao
    de `require_boto3`: o nucleo determinístico roda em CI e em sandbox sem a
    dependencia, e nenhum deles deveria falhar por causa de um coletor que
    ninguem chamou."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise CollectorUnavailable(
            "pyarrow nao disponivel. Instale com "
            "`pip install 'sparkforge-aws[parquet]'` para ler o footer, ou "
            "produza o artefato por outro caminho (parquet-tools, Spark) e "
            "registre-o com `sparkforge_aws.collect.register_artifact`."
        ) from exc
    return pq


def parquet_footer_path(prefix: str) -> str:
    """Um artefato por PREFIXO. O nome vem do prefixo higienizado, e nao de um
    hash: dois prefixos diferentes precisam produzir dois arquivos que o
    operador reconhece no disco sem abrir."""
    limpo = (
        prefix.replace("s3://", "").replace("s3a://", "").strip("/").replace("/", "_")
    )
    seguro = "".join(c if (c.isalnum() or c in "._-") else "_" for c in limpo)
    return f".sparkforge_aws/artifacts/parquet_footer/{seguro or 'prefixo'}.json"


def _codigo_de_erro(exc: BaseException) -> str:
    resposta = getattr(exc, "response", None)
    if isinstance(resposta, dict):
        erro = resposta.get("Error")
        if isinstance(erro, dict):
            return str(erro.get("Code") or "")
    return ""


def _classificar(exc: BaseException) -> str | None:
    """Traduz a excecao no `status` que o operador consegue agir, ou `None`
    quando ela nao e um dos estados nomeados -- e ai ela sobe, porque engolir
    erro desconhecido e como um coletor mente."""
    if isinstance(exc, _AwsProfileUnavailable):
        return STATUS_SEM_CREDENCIAL
    if isinstance(exc, CollectorUnavailable):
        return STATUS_PYARROW_INDISPONIVEL
    if type(exc).__name__ in _EXCECOES_SEM_CREDENCIAL:
        return STATUS_SEM_CREDENCIAL
    if isinstance(exc, FileNotFoundError):
        return STATUS_PREFIXO_INEXISTENTE
    if isinstance(exc, PermissionError):
        return STATUS_SEM_PERMISSAO
    codigo = _codigo_de_erro(exc)
    if codigo in _CODIGOS_INEXISTENTE:
        return STATUS_PREFIXO_INEXISTENTE
    if codigo in _CODIGOS_SEM_PERMISSAO:
        return STATUS_SEM_PERMISSAO
    return None


def _valor_de_estatistica(valor: Any) -> Any:
    """Estatistica vai para JSON, e nem todo min/max e serializavel.

    `date`, `datetime`, `Decimal` e `bytes` aparecem em coluna real. Numero e
    booleano passam; o resto vira `str`, e o extrator trata como
    `estatistica_incompleta` para a medida de faixa -- que e a leitura certa:
    a distancia entre duas strings nao e definida.
    """
    if valor is None or isinstance(valor, (bool, int, float)):
        return valor
    return str(valor)


def _do_column_chunk(cc: Any) -> dict[str, Any]:
    stats = cc.statistics
    tem_stats = bool(getattr(cc, "is_stats_set", False)) and stats is not None
    return {
        "path": cc.path_in_schema,
        "physical_type": str(cc.physical_type),
        "compression": str(cc.compression),
        "encodings": [str(e) for e in (cc.encodings or ())],
        "has_dictionary_page": bool(cc.has_dictionary_page),
        "is_stats_set": tem_stats,
        "has_min_max": bool(getattr(stats, "has_min_max", False)) if tem_stats else False,
        "min": _valor_de_estatistica(getattr(stats, "min", None)) if tem_stats else None,
        "max": _valor_de_estatistica(getattr(stats, "max", None)) if tem_stats else None,
        "null_count": int(getattr(stats, "null_count", 0) or 0) if tem_stats else None,
        "num_values": int(cc.num_values or 0),
        "total_compressed_size": int(cc.total_compressed_size or 0),
        "total_uncompressed_size": int(cc.total_uncompressed_size or 0),
        # Os DOIS indices de pagina, e nao um: o column index traz as
        # estatisticas por pagina, o offset index diz onde cada pagina comeca.
        # Um sem o outro nao permite page skipping.
        "has_column_index": bool(getattr(cc, "has_column_index", False)),
        "has_offset_index": bool(getattr(cc, "has_offset_index", False)),
        "bloom_filter_offset": getattr(cc, "bloom_filter_offset", None),
    }


def _ler_footer(
    pq: Any,
    caminho: str,
    file_bytes: int,
    *,
    filesystem: Any | None = None,
) -> dict[str, Any]:
    """UM arquivo, so o footer. `pq.ParquetFile` le o rodape sob demanda."""
    caminho_fisico = caminho
    if filesystem is not None and caminho.startswith(("s3://", "s3a://")):
        uri = urlsplit(caminho)
        caminho_fisico = f"{uri.netloc}{uri.path}".strip("/")
    fonte = (
        pq.ParquetFile(caminho_fisico, filesystem=filesystem)
        if filesystem is not None
        else pq.ParquetFile(caminho)
    )
    metadata = fonte.metadata
    grupos = []
    for i in range(metadata.num_row_groups):
        rg = metadata.row_group(i)
        grupos.append(
            {
                "index": i,
                "num_rows": int(rg.num_rows or 0),
                "total_byte_size": int(rg.total_byte_size or 0),
                "columns": [_do_column_chunk(rg.column(c)) for c in range(rg.num_columns)],
            }
        )
    return {
        "path": caminho,
        "file_bytes": int(file_bytes),
        "num_rows": int(metadata.num_rows or 0),
        "num_row_groups": int(metadata.num_row_groups or 0),
        "num_columns": int(metadata.num_columns or 0),
        "created_by": str(metadata.created_by or ""),
        "format_version": str(metadata.format_version or ""),
        "row_groups": grupos,
    }


def _listar_local(prefixo: Path) -> list[tuple[str, int]]:
    """Arquivos `.parquet` sob um diretorio, ORDENADOS PELO NOME.

    A ordem e o contrato da amostragem: `first_n_by_name` so e reproduzivel se a
    listagem for estavel, e `rglob` cru nao garante ordem entre plataformas.

    `iter_source_files` e nao `rglob`, e a razao vai alem da ordem: a varredura
    da casa tem denylist e ordem estavel, e
    `tests/test_facts_scan.py::test_nenhum_modulo_varre_com_glob_cru` e o gate
    estrutural que impede a porta de entrada sem ela -- mesma disciplina de
    `errors/matcher.py` e de `facts/cloudwatch_logs.py`.
    """
    if not prefixo.exists():
        raise FileNotFoundError(str(prefixo))
    alvos = list(iter_source_files(prefixo, "*.parquet"))
    return [(p.as_posix(), p.stat().st_size) for p in alvos]


def collect_parquet_footer(
    prefix: str,
    root: Path,
    *,
    now: str,
    max_files: int = _MAX_FILES_PADRAO,
    aws_profile: str | None = None,
    aws_region: str | None = None,
) -> Any:
    """Le o footer dos primeiros `max_files` arquivos do prefixo e registra.

    `prefix` e um caminho LOCAL (diretorio) ou um URI `s3://`. O caminho de S3
    delega a leitura ao proprio pyarrow, que resolve credencial pela cadeia
    padrao -- este modulo nao cria cliente boto3 nenhum.
    """
    if max_files < 1:
        raise ValueError(f"max_files precisa ser >= 1, recebido {max_files!r}")
    if max_files > _MAX_FILES_TETO:
        raise ValueError(
            f"max_files {max_files} acima do teto de {_MAX_FILES_TETO}. Cada footer "
            f"entra inteiro no artefato, e um artefato de centenas de MB deixa de "
            f"caber no barramento que ele deveria servir."
        )

    rel_path = parquet_footer_path(prefix)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    arquivos: list[dict[str, Any]] = []
    vistos = 0
    status = STATUS_OK
    try:
        pq = require_pyarrow()
        alvos, filesystem = _listar(
            pq,
            prefix,
            aws_profile=aws_profile,
            aws_region=aws_region,
        )
        vistos = len(alvos)
        for caminho, tamanho in alvos[:max_files]:
            arquivos.append(
                _ler_footer(pq, caminho, tamanho, filesystem=filesystem)
            )
    except CollectionFailed:
        raise
    except Exception as exc:  # noqa: BLE001 -- reclassificado ou re-levantado abaixo
        classificado = _classificar(exc)
        if classificado is None:
            raise
        status = classificado

    if status == STATUS_OK and not arquivos:
        # Prefixo que existe e nao tem Parquet NAO e o mesmo estado que prefixo
        # inexistente, e os dois produzem a mesma lista vazia. O `status` e o
        # unico lugar onde a diferenca sobrevive ate o fact.
        status = STATUS_PREFIXO_VAZIO

    payload = {
        "prefix": prefix,
        "status": status,
        "files": arquivos,
        "files_seen": vistos,
        "files_read": len(arquivos),
        "sampling": SAMPLING_PRIMEIROS,
        "max_files": max_files,
    }
    content = json.dumps(
        payload, indent=2, sort_keys=True, default=str, ensure_ascii=False
    ).encode("utf-8")
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="parquet_footer",
        source=f"parquet:footer:{prefix}",
        collect_command=_collect_command(
            prefix,
            max_files=max_files,
            aws_profile=aws_profile,
            aws_region=aws_region,
        ),
        now=now,
    )


def _collect_command(
    prefix: str,
    *,
    max_files: int,
    aws_profile: str | None,
    aws_region: str | None,
) -> str:
    """Registra uma recoleta sem jamais materializar segredo no manifesto."""
    comando = (
        f"sparkforge-aws collect parquet-footer --prefix {prefix} "
        f"--max-files {max_files}"
    )
    if aws_profile:
        comando += f" --profile {aws_profile}"
    if aws_region:
        comando += f" --region {aws_region}"
    return comando


def _s3_filesystem(fs: Any, *, aws_profile: str | None, aws_region: str | None) -> Any:
    """Cria o filesystem S3 respeitando perfil nomeado sem expor credencial.

    PyArrow resolve variaveis de ambiente e alguns arquivos AWS, mas no Windows
    um `AWS_PROFILE` sozinho pode nao ser aplicado ao provider nativo do S3.
    Quando o operador declara `--profile`, usamos a Session do boto3 apenas
    para obter credenciais congeladas e as entregamos ao PyArrow em memoria.
    Nenhuma delas entra no artefato, journal ou comando de recoleta.
    """
    kwargs: dict[str, Any] = {}
    if aws_region:
        kwargs["region"] = aws_region
    if aws_profile:
        boto3 = require_boto3()
        try:
            session = boto3.Session(
                profile_name=aws_profile,
                region_name=aws_region or None,
            )
            credentials = session.get_credentials()
        except Exception as exc:  # noqa: BLE001 -- fronteira nomeada abaixo
            raise _AwsProfileUnavailable(
                f"perfil AWS {aws_profile!r} nao pode ser resolvido pela cadeia do boto3"
            ) from exc
        if credentials is None:
            raise _AwsProfileUnavailable(
                f"perfil AWS {aws_profile!r} nao resolveu credenciais"
            )
        frozen = credentials.get_frozen_credentials()
        kwargs.update(
            access_key=frozen.access_key,
            secret_key=frozen.secret_key,
            session_token=frozen.token,
        )
    return fs.S3FileSystem(**kwargs)


def _listar(
    pq: Any,
    prefix: str,
    *,
    aws_profile: str | None = None,
    aws_region: str | None = None,
) -> tuple[list[tuple[str, int]], Any | None]:
    """Listagem local ou em S3, sempre ordenada pelo nome."""
    if prefix.startswith(("s3://", "s3a://")):
        import pyarrow.fs as fs

        uri = urlsplit(prefix)
        caminho = f"{uri.netloc}{uri.path}".strip("/")
        sistema = _s3_filesystem(
            fs,
            aws_profile=aws_profile,
            aws_region=aws_region,
        )
        seletor = fs.FileSelector(caminho, recursive=True, allow_not_found=False)
        infos = [
            i
            for i in sistema.get_file_info(seletor)
            if i.type == fs.FileType.File and i.path.endswith(".parquet")
        ]
        return (
            sorted((f"{uri.scheme}://{i.path}", i.size) for i in infos),
            sistema,
        )
    return _listar_local(Path(prefix)), None


__all__ = [
    "SAMPLING_PRIMEIROS",
    "STATUS_OK",
    "STATUS_PREFIXO_INEXISTENTE",
    "STATUS_PREFIXO_VAZIO",
    "STATUS_PYARROW_INDISPONIVEL",
    "STATUS_SEM_CREDENCIAL",
    "STATUS_SEM_PERMISSAO",
    "collect_parquet_footer",
    "parquet_footer_path",
    "require_pyarrow",
]
