"""Extrator do artefato de LOG do CloudWatch em Facts.

## Por que ele nao mora em `facts/cloudwatch.py`, que ja trata CloudWatch

Porque "CloudWatch" e o nome do SERVICO, e nao o do artefato. `cloudwatch.py`
le UM artefato -- a resposta de `cloudwatch.get_metric_data`, uma serie
numerica indexada por `CLOUDWATCH_METRICS` --, e o que ele emite (`glue.metric`
e irmaos) e medida agregada por percentil. Este le OUTRO artefato -- a resposta
de `logs.filter_log_events`, uma lista de linhas de texto --, com outro
`kind` no manifesto (`cloudwatch_logs`), outra forma de recusa (log group
inexistente, permissao, credencial) e uma obrigacao que o de metrica nao tem:
**redigir**, porque numero nao carrega credencial e linha de log carrega.

Juntar os dois num modulo produziria um `EMITTED_KINDS` misturando
`glue.metric*` com `cloudwatch.log*`, e um `extract_cloudwatch_path` obrigado a
despachar por FORMA do payload -- decisao que o `kind` do manifesto ja tomou.
O precedente do repositorio e o oposto e esta a vista: `emr_cluster`,
`emr_serverless` e `emr_eks` sao tres modulos, e os tres sao "EMR". Um por
artefato, e `EXTRACTOR_ID` proprio para que a proveniencia diga qual leu o que.

## Redacao, e o limite dela -- nomeado

Toda linha passa por `secrets.redact` ANTES de virar fact, no mesmo caminho de
`spark.conf_effective` e de `spark.stage.failure`: log de driver carrega
credencial com a mesma facilidade que configuracao, e `facts.json` e
committado como barramento de handoff.

O LIMITE, medido e nao corrigido: `redact(key, value)` tem tres gatilhos, e o
terceiro exige que o NOME DA CHAVE sugira segredo. Uma linha de log nao tem
chave -- ela chega como `("log_event", <a linha inteira>)` --, entao so os dois
gatilhos por VALOR valem aqui: padrao de emissor publicado (AKIA…, `ghp_`, JWT,
PEM, `xox…`) e senha embutida em URL. Consequencia direta: uma linha
`AWS_SECRET_ACCESS_KEY=wJalrX…` NAO e redigida, porque o valor nao tem prefixo
publicado e a chave que o denunciaria esta dentro do texto, nao no argumento.
Isso e identico ao que `event_log.py` ja faz com `Failure Reason`, e alargar
`redact` para varrer o interior de texto livre e mudanca na superficie de
seguranca do pacote inteiro -- nao um detalhe deste extrator.

## Relevancia e DECLARADA, nunca adivinhada

Este modulo emite `cloudwatch.log_event` para CADA evento do artefato, e nao
filtra nada. Quem escolhe o que e relevante e o operador, pelo `filter_pattern`
e pela janela que passou ao coletor. Um predicado de "linha interessante" aqui
seria juizo com cara de extracao: escolher quais linhas o motor de regras pode
ver e escolher o diagnostico antes de ele acontecer.

Puro e deterministico como os extratores irmaos: nunca aplica limiar, nunca
atribui severidade, nunca toca a rede.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.facts.secrets import redact
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "cloudwatch_logs@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "cloudwatch.log_event",
        "cloudwatch.logs.unresolved",
        "cloudwatch.logs.analyzed",
    }
)

# As quatro razoes de recusa, cada uma com o remedio que a destrava. Elas sao o
# que separa "nao achei" de "ninguem perguntou" (regra 20 do `CLAUDE.md`): as
# quatro produzem a MESMA lista vazia de eventos, e sem o nome o operador nao
# sabe se aumenta a janela, corrige o nome do grupo, pede permissao ou faz
# login.
_DETALHE_POR_RAZAO: dict[str, str] = {
    "log_group_inexistente": (
        "`logs.filter_log_events` devolveu ResourceNotFoundException: o log group "
        "nao existe nesta conta/regiao. Glue grava em `/aws-glue/jobs/error`, "
        "`/aws-glue/jobs/output` e, a partir do Glue 4.0, `/aws-glue/jobs/logs-v2` "
        "-- confira qual deles o job usa antes de concluir que nao ha log."
    ),
    "sem_permissao": (
        "A chamada foi recusada por AccessDenied. Sem `logs:FilterLogEvents` no "
        "grupo, a resposta e indistinguivel de um grupo vazio -- e por isso a "
        "razao entra no fact em vez de virar lista vazia."
    ),
    "vazio": (
        "O grupo existe e a chamada teve permissao, e a janela consultada nao tem "
        "evento nenhum para este `logStreamNamePrefix`. Causas distintas e nao "
        "decididas aqui: janela fora do run, prefixo de stream errado, ou "
        "`filter_pattern` que nao casa linha nenhuma."
    ),
    "sem_credencial": (
        "botocore nao encontrou credencial (ou regiao) utilizavel, e a requisicao "
        "nunca saiu. Nao ha o que dizer sobre o log: a coleta nao aconteceu."
    ),
}


def _subject(payload: dict[str, Any]) -> dict[str, Any]:
    """`type: "job_run"` pelo mesmo precedente de `facts/cloudwatch.py`: o enum
    fechado de `subject.type` nao tem um tipo "linha de log", e o run e a
    entidade ancorada mais proxima. O `log_group` entra porque dois grupos do
    MESMO run sao dois conteudos distintos -- sem ele, o `error` e o `output`
    colidiriam no id do fact."""
    job_run_id = str(payload.get("job_run_id") or "")
    return {
        "job_name": str(payload.get("job_name") or ""),
        "job_run_id": job_run_id,
        "log_group": str(payload.get("log_group") or ""),
        "type": "job_run",
        "symbol": job_run_id,
    }


def _provenance(path: str) -> dict[str, Any]:
    return {"extractor": EXTRACTOR_ID, "artifact": path}


def extract_cloudwatch_logs(payload: dict[str, Any], path: str) -> list[Fact]:
    """Extrai Facts do conteudo ja carregado de um artefato de log."""
    subject = _subject(payload)
    provenance = _provenance(path)
    status = str(payload.get("status") or "")

    facts: list[Fact] = []

    if status in _DETALHE_POR_RAZAO:
        facts.append(
            Fact(
                kind="cloudwatch.logs.unresolved",
                subject=dict(subject),
                measures={},
                attrs={
                    "reason": status,
                    "detail": _DETALHE_POR_RAZAO[status],
                    "filter_pattern": str(payload.get("filter_pattern") or ""),
                    "start": str(payload.get("start") or ""),
                    "end": str(payload.get("end") or ""),
                },
                provenance=provenance,
            )
        )

    redigidas = 0
    eventos = payload.get("events") or []
    for ordem, evento in enumerate(eventos):
        mensagem_crua = str((evento or {}).get("message") or "")
        # A redacao vem ANTES de o texto virar fact, sempre. Nao ha caminho
        # neste modulo em que a linha crua chegue a `attrs`.
        mensagem, foi_redigida = redact("log_event", mensagem_crua)
        if foi_redigida:
            redigidas += 1
        attrs: dict[str, Any] = {
            "message": mensagem.rstrip("\n"),
            "log_stream": str((evento or {}).get("logStreamName") or ""),
        }
        if foi_redigida:
            attrs["redacted"] = True
        measures: dict[str, Any] = {}
        carimbo = (evento or {}).get("timestamp")
        if isinstance(carimbo, (int, float)) and not isinstance(carimbo, bool):
            measures["timestamp_ms"] = float(carimbo)
        facts.append(
            Fact(
                kind="cloudwatch.log_event",
                subject={**subject, "event": ordem},
                measures=measures,
                attrs=attrs,
                provenance=provenance,
            )
        )

    facts.append(
        Fact(
            kind="cloudwatch.logs.analyzed",
            subject=dict(subject),
            measures={
                "events": float(len(eventos)),
                "events_redacted": float(redigidas),
                # `truncated` e medida e nao anotacao de proposito: um corte
                # que so aparece em `attrs` some do `measures` que uma regra
                # consulta, e corte que nao se declara e log parcial com cara
                # de completo.
                "truncated": 1.0 if payload.get("truncated") else 0.0,
                "max_events": float(payload.get("max_events") or 0),
            },
            attrs={
                "status": status,
                "filter_pattern": str(payload.get("filter_pattern") or ""),
                "log_stream_prefix": str(payload.get("log_stream_prefix") or ""),
            },
            provenance=provenance,
        )
    )
    return sort_facts(facts)


def extract_cloudwatch_logs_path(path: Path) -> list[Fact]:
    """Le o artefato do disco e delega para `extract_cloudwatch_logs`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return extract_cloudwatch_logs(payload, str(path))


def extract_cloudwatch_logs_tree(directory: Path, repo_root: Path | None = None) -> list[Fact]:
    """Todos os `*.json` de um diretorio, na ordem do nome.

    Existe para o corpus de fixture e para o caso do operador que baixou
    `error` e `output` do mesmo run: os dois sao artefatos separados, e ler os
    dois e uma chamada so em vez de duas.

    `iter_source_files` e nao `rglob` cru: a varredura da casa tem denylist e
    ordem estavel, e `tests/test_facts_scan.py` e o gate estrutural que impede a
    porta de entrada sem ela.
    """
    raiz = Path(repo_root or directory)
    facts: list[Fact] = []
    for arquivo in iter_source_files(directory, "*.json"):
        try:
            rel = str(arquivo.relative_to(raiz))
        except ValueError:
            rel = str(arquivo)
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
        facts.extend(extract_cloudwatch_logs(payload, rel.replace("\\", "/")))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_cloudwatch_logs",
    "extract_cloudwatch_logs_path",
    "extract_cloudwatch_logs_tree",
]
