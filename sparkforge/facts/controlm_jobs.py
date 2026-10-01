"""Extrator de Facts a partir de uma definicao `Jobs-as-Code` do Control-M (BMC).

Como `emr_eks.py`, este modulo NAO coleta nada: le o JSON ja versionado no
repositorio do cliente, com as chaves como a BMC as escreve (`Type`, `RunAs`,
`Application`), sem traducao. Nunca levanta excecao por payload malformado -- o
que nao consegue ler vira `ctm.unresolved` CONTADO, e a sentinela `ctm.analyzed`
sai sempre, inclusive quando nada pode ser lido.

## Por que ha artefato aqui, e nao havia no incremento 1

O incremento 1 partiu de *"o operador nao tem Control-M e nao tem artefato"*, e
para `describe-job-run` isso continua verdade -- saida de runtime exige a
instancia. **`Jobs-as-Code` e codigo-fonte**: definicao de job em JSON,
versionada no repositorio, que `ctm build` valida e `ctm deploy` publica. E a
mesma natureza de um `main.tf` ou de um `.py` de PySpark, que este motor ja le.

## Por que `ctm.` (D-2 da spec)

`ctm` e o prefixo da CLI oficial (`ctm build`, `ctm deploy`, `ctm run`) e do
cliente Python (`ctm-python-client`). Nao e prefixo de nenhum kind existente e
nenhum kind existente e prefixo dele -- a armadilha que `emrc.` documenta.

## A VERSAO E DECLARADA, NUNCA INFERIDA (D-1 da spec)

O JSON de `Jobs-as-Code` **nao** carrega a versao do Control-M que vai executa-lo.
Foi conferido campo a campo na pagina *Job Properties*: os 44 blocos que ela
publica descrevem tipo, agendamento, dependencia, acao, recurso e identidade --
nenhum deles nomeia a versao do Automation API. Deduzi-la do conteudo seria
adivinhar, e adivinhar versao e o defeito que a divida do `judge --emr` carregou
por tres fases.

Entao ela entra por PARAMETRO (`--version 9.0.21.300`), e `ctm.version_declared`
registra, no proprio fact, que ela e **declaracao do operador** e nao leitura do
artefato. Sem versao declarada o cruzamento com a matriz NAO acontece: sai
`ctm.capability_unresolved` com `reason: version_not_declared` e a medida que o
destrava, e a regra `SF-CTM-001` fica pulada por `requires_facts` -- que e
recusa nomeada, nao silencio.

## O CRUZAMENTO COM A MATRIZ ACONTECE AQUI, E NAO NA REGRA (D-3 da spec)

A fronteira de versao mora em `knowledge/controlm/automation-api-matrix.yaml`.
A regra **nao** pode repetir `9.0.22.005` no `when` -- seria a segunda copia do
mesmo fato, que e o defeito que o sub-projeto 2 existiu para remover.

Como o motor de regras avalia `where`/`expr` SEMPRE contra o contexto de um fact
so (`rules/engine.py::_fact_context`), a pergunta "a versao declarada sustenta a
capacidade que este job usa?" nao cabe numa condicao: ela cruza artefato com
matriz. O molde e `tf.observability.spark_ui` e `tf.graphframes.jar` em
`facts/terraform.py`, e o veto `V-GR-1` de `rules/catalog/graph.yaml` explica a
mecanica: quem enxerga a pergunta inteira e o extrator, entao ele decide UMA vez
e emite o kind ja decidido. A regra fica com a condicao simples sobre ele.

## O SILENCIO DA MATRIZ NUNCA E APROVACAO (D-4 da spec)

O incremento 1 mediu que 9 das 31 versoes da faixa nao carregam afirmacao propria
e que 175 linhas de *Corrected Problems* nao couberam em eixo nenhum. O silencio
e grande, e le-lo como "compativel por omissao" seria o pior defeito possivel.

Por isso as tres saidas do cruzamento sao TRES kinds, e nao dois:

  `ctm.capability_supported`     a versao declarada sustenta a capacidade.
  `ctm.capability_incompatible`  a versao declarada NAO a sustenta.
  `ctm.capability_unresolved`    o cruzamento nao aconteceu, e o `reason` diz
                                 por que -- versao nao declarada, versao fora da
                                 faixa, versao que a fonte nao publica, ou
                                 capacidade que a matriz nao nomeia.

`attrs.unblocked_by` acompanha toda recusa com a medida que a destrava, na
disciplina da secao 20 do `CLAUDE.md`.

## A OMISSAO E DECIDIDA AQUI, PORQUE O MOTOR NAO A ENXERGA (D-1 do incremento 3)

A fonte diz, sobre `SpecificDates`: *"cannot be used in combination with options
`WeekDays`, `Months`, or `MonthDays`. However, since the default for these
options is "ALL", you must specify these options with a value of "NONE"."*

A segunda frase e a que torna a exigencia verificavel, e a que nenhuma condicao
do motor consegue exprimir. `engine._where_matches` REPROVA caminho ausente --
e assim que o motor diz "nao sei" --, entao `attrs.week_days != "NONE"` e FALSO
justamente quando `WeekDays` nao foi escrito, que e o caso comum: default `ALL`,
combinacao proibida acontecendo, e ninguem ve lendo o JSON.

Entao a ausencia vira DECISAO no extrator, no molde de `tf.graphframes.jar` e de
`graph.algorithm.checkpoint_required`: quem enxerga as tres opcoes de uma vez e
este modulo, ele decide UMA vez e emite `attrs.specific_dates_conflict` ja
decidido, com `specific_dates_conflict_by_omission` separado de
`specific_dates_conflict_declared` para que o achado saiba dizer QUAL das duas
formas encontrou. A regra fica com uma condicao sobre um booleano.

E a mesma divida que a area `SF-GRAPH` pagou em 2026-08-31, e a solucao e a
mesma. Severidade, limiar e recomendacao continuam no catalogo: o `400` de
`SpecificDates` e limiar, mora em `threshold` da regra, e nao aqui -- este
modulo so CONTA as datas.

## O QUE ESTE MODULO NAO FAZ

**Nao valida o JSON contra o schema completo.** `ctm build` faz isso e e da BMC;
reimplementar validacao de schema seria concorrer com a ferramenta oficial sem
fonte que sustente divergencia. O que aqui vira `ctm.unresolved` e o que nao deu
para LER, nunca o que esta errado segundo um schema que este modulo nao carrega.

**Nao julga SLA, e nao julga semantica de dependencia.** `SLA`, `ServiceLevel`,
`Deadline`, `MaxWait` e `CompletionTime` tem ZERO ocorrencia na pagina *Job
Properties* -- medido em 2026-09-02 sobre os 423 KB dela --, entao nao ha fonte
que nomeie defeito de SLA e o veto `V-CTM-5` do catalogo o registra. "Este job
espera evento que ninguem produz" tambem fica de fora: exigiria o grafo do site
inteiro, e a pagina nao declara que evento orfao seja defeito.

O QUE PASSOU A SER JULGADO EM 2026-09-02 (incremento 3). A pagina *Job
Properties* nomeia CINCO defeitos nos eixos de janela e dependencia -- tres e
dois --, cada um com um `cannot`, um `must`, um `must not`, um `is not
supported` ou um limite numerico. Campo documentado nunca sustentou regra; frase
que diz que algo esta errado sustenta. Os kinds derivados que este modulo passou
a emitir sao a metade de extracao dessa decisao, e a lista de qual regra le qual
atributo esta em `rules/catalog/controlm.yaml`.

## Forma do artefato, medida na fonte (2026-09-01)

```json
{
  "Defaults": {"Application": "SampleApp", "RunAs": "USERNAME"},
  "AutomationAPISampleFlow": {
    "Type": "Folder",
    "CommandJob": {"Type": "Job:Command", "Command": "echo my 1st job"},
    "ScriptJob":  {"Type": "Job:Script", "FileName": "s.sh"},
    "Flow": {"Type": "Flow", "Sequence": ["CommandJob", "ScriptJob"]}
  }
}
```

Objeto nomeado com `Type` e a unidade: `Folder`/`SimpleFolder`/`SubFolder` sao
container, `Job:*` e job, `Flow` declara sequencia e `If` declara acao
condicional. `Defaults` e chave reservada de topo e nao e nem folder nem job.

**`ActionIfFailure` NAO e propriedade do schema**, e isso foi medido: na pagina
*Job Properties* e no `AutomationAPISampleFlow.json` oficial ele e apenas o NOME
que o exemplo da ao objeto, cujo `Type` e `If`. Procurar a chave literal
`ActionIfFailure` acharia o exemplo da BMC e perderia todo `If` batizado de outro
jeito. O que este modulo reconhece e `Type: If`, e o nome escolhido pelo autor
sai em `attrs.name`.

Como os demais extratores: puro e deterministico. Nunca aplica limiar, nunca
atribui severidade, nunca infere o que o payload nao diz.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.facts.secrets import REDACTED
from sparkforge.facts.secrets import looks_like_secret as _looks_like_secret
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "controlm_jobs@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "ctm.folder",
        "ctm.job",
        "ctm.job_array_format",
        "ctm.schedule",
        "ctm.dependency",
        "ctm.event_logic",
        "ctm.action",
        "ctm.variable",
        "ctm.version_declared",
        "ctm.capability_supported",
        "ctm.capability_incompatible",
        "ctm.capability_unresolved",
        "ctm.unresolved",
        "ctm.analyzed",
    }
)

# As chaves de topo que a fonte reserva e que NAO sao folder nem job. `Defaults`
# e a unica hoje, e ela existe no proprio `AutomationAPISampleFlow.json`. Tratar
# `Defaults` como folder faria a contagem de folders mentir em todo artefato real.
_RESERVED_TOP_LEVEL = frozenset({"Defaults"})

# Os tres containers que a pagina *Folders and Flows* publica. `SimpleFolder`
# entra porque ela o nomeia como o par do `Folder` (sem agendamento e sem evento
# no nivel do container), e um artefato que o use nao pode sair sem folder.
_FOLDER_TYPES = frozenset({"Folder", "SimpleFolder", "SubFolder"})

# As tres portas de dependencia por evento, com a direcao que cada uma declara.
# `Events` e o bloco que as agrupa quando o autor as escreve juntas.
_EVENT_BLOCKS: tuple[tuple[str, str], ...] = (
    ("WaitForEvents", "wait"),
    ("AddEvents", "add"),
    ("DeleteEvents", "delete"),
)

# A MESMA dependencia na OUTRA forma que a pagina publica, e ler so uma delas
# perderia exatamente o exemplo em que a fonte demonstra o defeito de D-1.
#
# A forma acima e a chave direta no job (`"WaitForEvents": [{"Event": "e1"}]`).
# Esta e um objeto NOMEADO com `Type`, e e a unica que a pagina *Job Properties*
# usa nos exemplos da secao de eventos:
#
#   "Wait2": {"Type": "WaitForEvents", "Events": ["(", {"Event": "ev1"}, ")"]}
#
# Sem este mapa, `_walk` veria `Wait2` como filho com `Type` que nao e folder,
# nem job, nem `Flow`, nem `If`, e sairia sem emitir nada -- silencio sobre a
# forma que a propria fonte escreve.
_EVENT_OBJECT_TYPES: dict[str, str] = {
    "WaitForEvents": "wait",
    "AddEvents": "add",
    "DeleteEvents": "delete",
}

# Os tokens logicos que a fonte publica DENTRO da lista de eventos, como
# elementos string ao lado dos objetos `{"Event": ...}`. Nao ha bloco proprio de
# expressao: a relacao logica viaja na mesma lista.
_PAREN_OPEN = "("
_PAREN_CLOSE = ")"
_LOGICAL_OPERATORS = frozenset({"AND", "OR"})

# As tres opcoes que `SpecificDates` NAO pode acompanhar, na grafia da pagina, e
# o valor com que a fonte exige que sejam anuladas. O default delas e "ALL", e e
# por isso que a AUSENCIA de qualquer uma ja e a combinacao proibida.
_SPECIFIC_DATES_EXCLUSIVE: tuple[str, ...] = ("WeekDays", "Months", "MonthDays")
_NEUTRALIZED = "NONE"

# O array de JOBS, que e outra chave e outra pergunta que `Folders`/`SubFolders`.
# A pagina liga `allowDuplicateJobNames` a "job definitions in an array format",
# e a capacidade `folders_array_structure` da matriz e sobre a estrutura de
# FOLDER. Somar as duas numa lista so faria a sonda de capacidade disparar sobre
# um array de jobs, que a matriz nao nomeia.
_JOB_ARRAY_KEYS: tuple[str, ...] = ("Jobs",)

# As propriedades de identidade que valem para job E para folder, na grafia da
# fonte. `Type` e `Name` saem em campo proprio; estas entram em `attrs` com o
# nome em snake_case, que e a convencao de attrs de todos os extratores.
_IDENTITY_PROPERTIES: tuple[tuple[str, str], ...] = (
    ("RunAs", "run_as"),
    ("Application", "application"),
    ("SubApplication", "sub_application"),
    ("Host", "host"),
    ("CreatedBy", "created_by"),
    ("Description", "description"),
)

# --------------------------------------------------------------------------- #
# As sondas de capacidade -- o vocabulario do cruzamento (D-3)
# --------------------------------------------------------------------------- #
#
# CADA ENTRADA E UM PAR `evidencia no artefato -> slug na matriz`, e a matriz
# guarda a fronteira de versao. Este modulo NAO escreve numero de versao nenhum:
# procure por `9.0.` neste arquivo e nao ha.
#
# SAO DUAS, E A CONTAGEM E MEDIDA, NAO ESCOLHIDA. A matriz tem 50 capacidades na
# faixa; a maioria e comando de CLI (`run job::bypass`, `config em:alerts::delete`)
# ou comportamento de servidor, e nada disso aparece numa definicao de job. As
# que aparecem num artefato de `Jobs-as-Code` sao estas duas.
#
# E AS QUE FORAM AVALIADAS E RECUSADAS, com a razao, porque recusa sem nome vira
# omissao:
#
#   `mssql_agentjob_rerun_from_step`  a capacidade e "rerun a partir do passo que
#       falhou", nao o job type `Job:Database:MSSQL:AgentJob` -- que existia
#       antes. Mapear o job type acusaria todo job de SSIS anterior a fronteira.
#   `created_by_under_strict_author_security`  a fronteira e sobre `CreatedBy`
#       valer com `AuthorSecurity` em Strict, que e configuracao do
#       Control-M/EM e de `automation-api.properties` -- nao esta no artefato.
#   `external_vault_cyberark_secrets`  o objeto `Secret` mora em connection
#       profile CENTRALIZADO, que e outro artefato (`deploy connectionprofile`),
#       nao a definicao de job.
#   `file_transfer_job_new_parameters`  a fonte diz "novos parametros" e nao os
#       nomeia. Sonda sem nome de campo casaria qualquer coisa.
#   `resources_array_duplicate_names`  a capacidade exige pool E lock com o MESMO
#       nome no MESMO job sob `allowDuplicateResourceNames=true` -- e a flag e de
#       `automation-api.properties`, fora do artefato. Sondar so a duplicata
#       acusaria quem tem a flag ligada.
#
_JOB_TYPE_CAPABILITIES: dict[str, str] = {
    # Medido no HTML da pagina *Job Types*, que publica 71 tipos: este e o unico
    # cuja introducao a pagina *What's New* nomeia dentro da faixa da matriz.
    "Job:DetachedEmbeddedScript": "job_detached_embedded_script",
}

# `Folders`/`SubFolders` como ARRAY -- a estrutura que permite mais de um folder
# com o mesmo nome. A sonda exige que o valor seja uma LISTA: `SubFolder1` como
# objeto nomeado e a forma antiga e existe desde sempre, entao casar a chave sem
# olhar o tipo acusaria todo artefato com sub-folder.
_ARRAY_STRUCTURE_KEYS: tuple[str, ...] = ("Folders", "SubFolders")
_ARRAY_STRUCTURE_CAPABILITY = "folders_array_structure"

# As quatro razoes de recusa do cruzamento. Duas vem de `descriptor.py` --
# importadas, nunca reescritas, porque duas grafias independentes da mesma recusa
# divergem no primeiro renome -- e duas nascem aqui.
VERSION_NOT_DECLARED = "version_not_declared"
CAPABILITY_NOT_IN_MATRIX = "capability_not_in_matrix"

# As fronteiras que DISPONIBILIZAM contra as que RETIRAM. A separacao decide o
# veredito e nao e cosmetica: abaixo de `introduced_in` a capacidade nao existe,
# e a partir de `discontinued_in` ela deixou de existir. `deprecated_from` NAO
# entra em nenhuma das duas listas de incompatibilidade de proposito -- a fonte
# diz "is deprecated", que e aviso de remocao futura, nao remocao. Tratar
# depreciado como incompativel seria afirmar uma quebra que a fonte nao afirma.
_BOUNDARIES_THAT_INTRODUCE: tuple[str, ...] = ("introduced_in", "changed_in")
_BOUNDARY_THAT_REMOVES = "discontinued_in"
_BOUNDARY_THAT_WARNS = "deprecated_from"


# --------------------------------------------------------------------------- #
# helpers de forma -- mesma convencao de `emr_eks.py`
# --------------------------------------------------------------------------- #


def _file_subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _entity_subject(path: str, symbol: str) -> dict[str, Any]:
    """O subject de um objeto do artefato, ancorado no CAMINHO dentro do JSON.

    `symbol` e `Folder/Job`, e nao so o nome do job: a fonte permite dois jobs
    com o mesmo nome (`allowDuplicateJobNames` tem default `true`), e agrupar por
    nome poria os dois no mesmo grupo de `same_subject` -- o job correto
    mascararia o incorreto, que e o falso negativo que `same_subject` existe
    para evitar.
    """
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="ctm.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


# --------------------------------------------------------------------------- #
# o cruzamento com a matriz -- o kind derivado (D-3, D-4)
# --------------------------------------------------------------------------- #


def _matrix_capability(slug: str) -> dict[str, Any] | None:
    """A entrada da matriz para um slug, ou `None` quando ela nao o nomeia.

    Importa `sparkforge.controlm.matrix` DENTRO da funcao, e nao no topo: a
    matriz le YAML de `knowledge/` na primeira chamada, e um extrator que falhe
    a IMPORTAR por causa de um arquivo de dado quebrado derrubaria quem o chamou
    antes de qualquer `try`. Aqui a falha vira `ctm.unresolved` como qualquer
    outra leitura que nao deu certo.
    """
    from sparkforge.controlm import matrix as cm

    entrada = cm.load()["capabilities"].get(slug)
    return dict(entrada) if isinstance(entrada, dict) else None


def _version_refusal(declared_version: str | None) -> tuple[str, str] | None:
    """`(reason, unblocked_by)` quando a versao declarada nao permite cruzar.

    As duas recusas de fronteira vem de `descriptor.py` pelo NOME
    (`VERSION_OUTSIDE_RANGE`, `VERSION_NOT_PUBLISHED`), porque elas ja existem e
    destravam com medidas diferentes: uma pede AMPLIAR a faixa lendo as versoes
    novas, a outra pede mostrar que a versao existe. Reescrever as strings aqui
    faria a terceira copia da mesma decisao.
    """
    from sparkforge.controlm import descriptor as cd
    from sparkforge.controlm import matrix as cm

    if declared_version is None:
        return (
            VERSION_NOT_DECLARED,
            "declare a versao do Control-M Automation API com `--version <v>` -- o JSON "
            "de Jobs-as-Code nao a carrega, e deduzi-la do conteudo seria adivinhar",
        )
    piso, teto = cm.covers()
    chave = cm.version_key(declared_version)
    if not (cm.version_key(piso) <= chave <= cm.version_key(teto)):
        return (
            cd.VERSION_OUTSIDE_RANGE,
            f"a matriz sustenta de {piso} a {teto}; ampliar `covers` em "
            f"knowledge/controlm/automation-api-matrix.yaml exige LER a pagina das "
            f"versoes novas, nunca derivar da fronteira mais proxima",
        )
    if declared_version not in cm.known_versions():
        return (
            cd.VERSION_NOT_PUBLISHED,
            "a fonte anda de 5 em 5 e nao publica esta versao; responder pelo degrau "
            "de baixo seria interpolar entre duas versoes observadas",
        )
    return None


def _capability_fact(
    slug: str,
    evidence: dict[str, Any],
    declared_version: str | None,
    subject: dict[str, Any],
    provenance: dict[str, Any],
) -> Fact:
    """UM fact por capacidade observada, com o veredito ja decidido.

    Tres saidas e nao duas, e a terceira e a que impede o silencio da matriz de
    virar aprovacao (D-4). Nunca levanta: qualquer falha ao ler a matriz vira
    `ctm.capability_unresolved` com `reason: matrix_unavailable`.
    """
    base = {"capability": slug, **evidence}

    try:
        recusa = _version_refusal(declared_version)
    except Exception as exc:  # matriz ausente, vazia ou fora do vocabulario
        return Fact(
            kind="ctm.capability_unresolved",
            subject=subject,
            attrs={
                **base,
                "reason": "matrix_unavailable",
                "detail": str(exc),
                "unblocked_by": (
                    "conserte knowledge/controlm/automation-api-matrix.yaml -- sem a "
                    "matriz nao ha fronteira de versao para cruzar"
                ),
            },
            provenance=provenance,
        )

    if recusa is not None:
        reason, unblocked_by = recusa
        attrs = {**base, "reason": reason, "unblocked_by": unblocked_by}
        if declared_version is not None:
            attrs["declared_version"] = declared_version
        return Fact(
            kind="ctm.capability_unresolved",
            subject=subject,
            attrs=attrs,
            provenance=provenance,
        )

    from sparkforge.controlm import matrix as cm

    try:
        entrada = _matrix_capability(slug)
    except Exception as exc:
        return Fact(
            kind="ctm.capability_unresolved",
            subject=subject,
            attrs={
                **base,
                "reason": "matrix_unavailable",
                "detail": str(exc),
                "declared_version": declared_version,
                "unblocked_by": (
                    "conserte knowledge/controlm/automation-api-matrix.yaml -- sem a "
                    "matriz nao ha fronteira de versao para cruzar"
                ),
            },
            provenance=provenance,
        )

    if entrada is None:
        # A SONDA EXISTE E A MATRIZ NAO NOMEIA A CAPACIDADE. E o caso da D-4 em
        # estado puro: a fonte pode nao te-la nomeado, ou ela pode ser de versao
        # acima do teto da faixa. Aprovar por omissao aqui seria dizer "compativel"
        # sobre algo que ninguem leu.
        return Fact(
            kind="ctm.capability_unresolved",
            subject=subject,
            attrs={
                **base,
                "reason": CAPABILITY_NOT_IN_MATRIX,
                "declared_version": declared_version,
                "unblocked_by": (
                    "leia a pagina What's New da versao que introduziu esta capacidade e "
                    "acrescente a entrada em knowledge/controlm/automation-api-matrix.yaml"
                ),
            },
            provenance=provenance,
        )

    fronteira = next((b for b in cm.BOUNDARIES if entrada.get(b)), None)
    if fronteira is None:
        # O carregador ja proibe capacidade sem fronteira, entao chegar aqui
        # significa que o contrato dele mudou. Recusar e mais barato que assumir.
        return Fact(
            kind="ctm.capability_unresolved",
            subject=subject,
            attrs={
                **base,
                "reason": CAPABILITY_NOT_IN_MATRIX,
                "detail": "a entrada da matriz nao declara fronteira nenhuma",
                "declared_version": declared_version,
                "unblocked_by": (
                    "declare uma das quatro fronteiras na entrada desta capacidade em "
                    "knowledge/controlm/automation-api-matrix.yaml"
                ),
            },
            provenance=provenance,
        )

    declarada = str(entrada[fronteira])
    comum = {
        **base,
        "declared_version": declared_version,
        "boundary": fronteira,
        "boundary_version": declarada,
        "summary": str(entrada["summary"]),
    }
    if entrada.get("replaced_by"):
        comum["replaced_by"] = str(entrada["replaced_by"])

    chave = cm.version_key(declared_version)
    limite = cm.version_key(declarada)

    if fronteira in _BOUNDARIES_THAT_INTRODUCE and chave < limite:
        return Fact(
            kind="ctm.capability_incompatible",
            subject=subject,
            attrs={**comum, "reason": "below_introduction"},
            provenance=provenance,
        )
    if fronteira == _BOUNDARY_THAT_REMOVES and chave >= limite:
        return Fact(
            kind="ctm.capability_incompatible",
            subject=subject,
            attrs={**comum, "reason": "discontinued"},
            provenance=provenance,
        )
    if fronteira == _BOUNDARY_THAT_WARNS and chave >= limite:
        # Depreciado ainda RESPONDE. O aviso viaja no fact, e nao vira achado:
        # a fonte diz "is deprecated", que anuncia remocao futura e nao a executa.
        return Fact(
            kind="ctm.capability_supported",
            subject=subject,
            attrs={**comum, "deprecated": True},
            provenance=provenance,
        )
    return Fact(
        kind="ctm.capability_supported",
        subject=subject,
        attrs=comum,
        provenance=provenance,
    )


# --------------------------------------------------------------------------- #
# facts de conteudo
# --------------------------------------------------------------------------- #


def _identity_attrs(node: dict[str, Any]) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for chave, nome in _IDENTITY_PROPERTIES:
        valor = _as_str(node.get(chave))
        if valor is not None:
            attrs[nome] = valor
    for chave, nome in (("Critical", "critical"), ("Confirm", "confirm")):
        if isinstance(node.get(chave), bool):
            attrs[nome] = node[chave]
    return attrs


def _schedule_fact(
    node: dict[str, Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> list[Fact]:
    """O bloco `When`, quando ele existe. Descritivo, sem julgamento de janela.

    Bloco ausente NAO produz fact: ao contrario de `emrc.monitoring`, onde a
    ausencia JA e zero destino de log, `When` ausente significa que o job herda o
    agendamento do folder -- a pagina *Folders and Flows* declara que
    "Folder-level definitions are inherited by the jobs". Emitir um fact de
    agendamento vazio afirmaria que o job nao tem agendamento, que e falso.
    """
    quando = node.get("When")
    if quando is None:
        return []
    if not isinstance(quando, dict):
        return []
    attrs: dict[str, Any] = {}
    for chave in ("FromTime", "ToTime", "RuleBasedCalendars", "Schedule"):
        valor = _as_str(quando.get(chave))
        if valor is not None:
            attrs[_snake(chave)] = valor
    measures: dict[str, Any] = {}
    for chave in ("Months", "MonthDays", "WeekDays", "Years"):
        valor = quando.get(chave)
        if isinstance(valor, list):
            measures[f"{_snake(chave)}_count"] = len(valor)
    _specific_dates(quando, measures, attrs)
    return [
        Fact(
            kind="ctm.schedule",
            subject=subject,
            measures=measures,
            attrs=attrs,
            provenance=provenance,
        )
    ]


def _neutralized(value: Any) -> bool:
    """`True` quando a opcao foi anulada com "NONE", na forma que a fonte publica.

    DUAS FORMAS CONTAM, e a primeira e a da propria pagina. O exemplo oficial
    escreve o valor como LISTA -- `"WeekDays": ["NONE"], "Months": ["NONE"],
    "MonthDays": ["NONE"]` --, e um autor pode escrever o escalar
    (`"WeekDays": "NONE"`). A exigencia da fonte e sobre o VALOR, nunca sobre o
    involucro, e aceitar so uma das duas acusaria o exemplo que a BMC publica.

    LISTA COM MAIS DE UM ITEM NAO ANULA: `["NONE", "MON"]` declara segunda-feira
    ao lado da anulacao, e isso E a combinacao que a fonte proibe.

    A CAIXA E IGNORADA, e a escolha e medida contra o que a fonte diz e nao diz.
    Ela publica "NONE" em maiuscula e NAO declara se o Control-M aceita "none";
    acusar por caixa afirmaria mais do que a fonte sustenta, e quem escreveu
    "none" declarou a intencao de anular. Caixa e assunto de `ctm build`, que e
    o validador oficial (veto `V-CTM-3`).
    """
    if isinstance(value, str):
        return value.strip().upper() == _NEUTRALIZED
    if isinstance(value, list):
        return len(value) == 1 and _neutralized(value[0])
    return False


def _specific_dates(
    quando: dict[str, Any], measures: dict[str, Any], attrs: dict[str, Any]
) -> None:
    """A decisao de `SpecificDates`, tomada UMA vez, no lugar onde ela cabe.

    SO MEXE NO FACT QUANDO `SpecificDates` E UMA LISTA. Sem a propriedade nao ha
    pergunta a responder, e emitir `specific_dates_conflict: false` em todo
    `When` do repositorio afirmaria sobre jobs que ninguem perguntou -- alem de
    fazer todo golden existente mudar sem que nada tenha mudado.

    AS DUAS FORMAS DO CONFLITO SAEM SEPARADAS, e a separacao e o produto desta
    funcao. `by_omission` e a opcao que nao foi escrita e portanto vale "ALL" por
    default -- o caso que ninguem ve lendo o JSON, e a razao de esta decisao nao
    caber numa condicao do motor. `declared` e a opcao escrita com outro valor,
    que qualquer leitor humano ja veria. O achado precisa saber qual das duas
    encontrou, porque a correcao e diferente: uma acrescenta linha, a outra troca
    valor.

    A CONTAGEM SAI SEMPRE QUE HA LISTA, inclusive quando nao ha conflito: e ela
    que sustenta o limite de 400 da fonte, e o limite e outro defeito. Contar aqui
    e medir; decidir se 401 e demais e limiar, e limiar mora na regra.
    """
    datas = quando.get("SpecificDates")
    if not isinstance(datas, list):
        return
    measures["specific_dates_count"] = len(datas)
    omitidas = [o for o in _SPECIFIC_DATES_EXCLUSIVE if o not in quando]
    declaradas = [
        o for o in _SPECIFIC_DATES_EXCLUSIVE if o in quando and not _neutralized(quando[o])
    ]
    attrs["specific_dates"] = True
    attrs["specific_dates_conflict"] = bool(omitidas or declaradas)
    attrs["specific_dates_conflict_by_omission"] = sorted(omitidas)
    attrs["specific_dates_conflict_declared"] = sorted(declaradas)


def _snake(name: str) -> str:
    saida: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            saida.append("_")
        saida.append(ch.lower())
    return "".join(saida)


def _dependency_facts(
    node: dict[str, Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> list[Fact]:
    """As dependencias por evento, e a sequencia de um `Flow`.

    Os tres blocos de evento podem aparecer soltos no job ou agrupados sob
    `Events`, e a pagina publica as duas formas. Ler so uma delas perderia
    metade das dependencias de um artefato real, entao as duas sao lidas e o
    fact carrega `container` dizendo qual foi.
    """
    facts: list[Fact] = []
    fontes: list[tuple[dict[str, Any], str]] = [(node, "job")]
    eventos = node.get("Events")
    if isinstance(eventos, dict):
        fontes.append((eventos, "Events"))

    for bloco, container in fontes:
        for chave, direcao in _EVENT_BLOCKS:
            entradas = bloco.get(chave)
            if not isinstance(entradas, list):
                continue
            facts.extend(
                _event_entry_facts(
                    entradas, chave, direcao, container, subject, provenance
                )
            )
    return facts


def _event_entry_facts(
    entradas: list[Any],
    block: str,
    direcao: str,
    container: str,
    subject: dict[str, Any],
    provenance: dict[str, Any],
) -> list[Fact]:
    """Os eventos de UMA lista, mais o fact de logica quando ela tem tokens.

    A lista mistura dois tipos de elemento, e a fonte os publica juntos: objetos
    `{"Event": ...}` e strings que sao parenteses ou operadores. Ler so os
    objetos -- que era o que este modulo fazia -- perde a expressao inteira.
    """
    facts: list[Fact] = []
    for entrada in entradas:
        if not isinstance(entrada, dict):
            continue
        nome = _as_str(entrada.get("Event"))
        if nome is None:
            continue
        attrs = {"direction": direcao, "event": nome, "container": container}
        data = _as_str(entrada.get("Date"))
        if data is not None:
            attrs["date"] = data
        facts.append(
            Fact(
                kind="ctm.dependency",
                subject=subject,
                attrs=attrs,
                provenance=provenance,
            )
        )
    facts.extend(_event_logic_facts(entradas, block, container, subject, provenance))
    return facts


def _event_logic_facts(
    entradas: list[Any],
    block: str,
    container: str,
    subject: dict[str, Any],
    provenance: dict[str, Any],
) -> list[Fact]:
    """O aninhamento de parenteses, DECIDIDO aqui (D-1 do incremento 3).

    A fonte: *"You can specify the logical relationship between events, using
    logical operators (AND/OR) and parentheses. The default relationship is AND.
    Note that nesting of parentheses within parentheses is not supported."*

    Profundidade e contagem, e contagem e medida -- entao ela sai daqui em
    `measures`, e o veredito ja decidido sai em `attrs.nested_parentheses`. A
    regra fica com uma condicao sobre um booleano, e nenhum `expr` do motor
    precisa aprender a contar parentese.

    SO SAI FACT QUANDO HA TOKEN LOGICO. Um bloco de evento sem parentese e sem
    operador nao declara relacao nenhuma -- a fonte diz que o default e AND --,
    e emitir "profundidade zero" sobre ele encheria todo artefato de facts que
    nao respondem pergunta nenhuma, alem de mover todo golden existente.

    O DESBALANCEAMENTO SAI COMO EVIDENCIA E NAO VIRA REGRA. Parentese que abre e
    nao fecha e defeito obvio para um humano, e a fonte NAO o nomeia: ela fala de
    aninhamento, e so. `balanced` viaja no fact para quem estiver lendo; julga-lo
    seria inventar o sexto defeito, e o `ctm build` da BMC ja e o validador de
    schema (veto `V-CTM-3`).
    """
    profundidade = 0
    maxima = 0
    abre = 0
    fecha = 0
    operadores = 0
    balanceado = True
    for entrada in entradas:
        if not isinstance(entrada, str):
            continue
        token = entrada.strip()
        if token == _PAREN_OPEN:
            abre += 1
            profundidade += 1
            maxima = max(maxima, profundidade)
        elif token == _PAREN_CLOSE:
            fecha += 1
            profundidade -= 1
            if profundidade < 0:
                # Fecha sem abrir. Zera para que o resto da lista continue a ser
                # contado a partir do nivel de topo, em vez de gerar
                # profundidade negativa que mascararia um aninhamento adiante.
                balanceado = False
                profundidade = 0
        elif token.upper() in _LOGICAL_OPERATORS:
            operadores += 1
    if abre == 0 and fecha == 0 and operadores == 0:
        return []
    return [
        Fact(
            kind="ctm.event_logic",
            subject=subject,
            measures={
                "max_paren_depth": maxima,
                "open_paren_count": abre,
                "close_paren_count": fecha,
                "operator_count": operadores,
            },
            attrs={
                "block": block,
                "container": container,
                "nested_parentheses": maxima > 1,
                "balanced": balanceado and profundidade == 0,
            },
            provenance=provenance,
        )
    ]


def _event_object_facts(
    node: dict[str, Any],
    tipo: str,
    subject: dict[str, Any],
    provenance: dict[str, Any],
) -> list[Fact]:
    """A forma `{"Type": "WaitForEvents", "Events": [...]}`, que a pagina usa.

    Aqui `Events` e uma LISTA, e no job ela e um MAPA que agrupa os tres blocos
    -- mesma chave, duas formas, e e por isso que `_dependency_facts` testa
    `isinstance(..., dict)` e esta funcao testa `list`. As duas nunca se cruzam.
    """
    entradas = node.get("Events")
    if not isinstance(entradas, list):
        return []
    return _event_entry_facts(
        entradas, tipo, _EVENT_OBJECT_TYPES[tipo], tipo, subject, provenance
    )


def _flow_facts(
    node: dict[str, Any], name: str, subject: dict[str, Any], provenance: dict[str, Any]
) -> list[Fact]:
    """Um `Flow` e dependencia declarada por ORDEM, e sai como `ctm.dependency`.

    Kind proprio para fluxo foi avaliado e recusado: a pergunta que ele responde
    e a mesma -- "o que precisa acontecer antes deste job?" --, e dois kinds para
    uma pergunta obrigariam toda regra futura a perguntar duas vezes.
    """
    sequencia = node.get("Sequence")
    if not isinstance(sequencia, list):
        return []
    passos = [s for s in (_as_str(item) for item in sequencia) if s is not None]
    if not passos:
        return []
    return [
        Fact(
            kind="ctm.dependency",
            subject=subject,
            measures={"step_count": len(passos)},
            attrs={
                "direction": "sequence",
                "container": "Flow",
                "flow": name,
                "sequence": passos,
            },
            provenance=provenance,
        )
    ]


def _action_facts(
    node: dict[str, Any], name: str, subject: dict[str, Any], provenance: dict[str, Any]
) -> list[Fact]:
    """Um objeto `Type: If`, com o gatilho e os tipos de acao que ele dispara.

    `attrs.name` guarda o nome que o AUTOR deu ao objeto (`ActionIfFailure` no
    exemplo oficial). Ele e dado do artefato, nao vocabulario do schema.
    """
    attrs: dict[str, Any] = {"name": name}
    for chave in (
        "CompletionStatus",
        "NumberOfFailures",
        "NumberOfReruns",
        "NumberOfExecutions",
        "Output",
        "VariableValue",
    ):
        valor = node.get(chave)
        texto = _as_str(valor) if isinstance(valor, str) else None
        if texto is not None:
            attrs["trigger"] = _snake(chave)
            attrs["trigger_value"] = texto
            break
        if valor is not None and not isinstance(valor, str):
            attrs["trigger"] = _snake(chave)
            break

    tipos = sorted(
        {
            tipo
            for filho in node.values()
            if isinstance(filho, dict) and (tipo := _as_str(filho.get("Type"))) is not None
        }
    )
    if tipos:
        attrs["action_types"] = tipos
    return [
        Fact(
            kind="ctm.action",
            subject=subject,
            measures={"action_count": len(tipos)},
            attrs=attrs,
            provenance=provenance,
        )
    ]


def _variable_facts(
    node: dict[str, Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> list[Fact]:
    """As variaveis de job, com REDACAO do valor que tem forma de credencial.

    POR QUE A REDACAO MORA AQUI, e nao numa propriedade chamada `Password`. Foi
    medido na pagina *Job Properties*: os 44 blocos que ela publica NAO tem campo
    de credencial. O campo `Password` existe em CONNECTION PROFILE, que e outro
    artefato -- e la a fonte publica a forma correta, `{"Secret": "<nome>"}`,
    resolvida do vault no deploy.

    O que sobra na definicao de job e `Variables`: uma lista de pares
    `{nome: valor}` livres, com notacao `%%`, que a fonte descreve como
    utilizavel em qualquer campo. E a unica superficie deste artefato onde uma
    credencial cabe, e por isso e a unica que passa pelo detector compartilhado.

    NENHUMA REGRA CONSOME `secret_pattern_match`, e isso e decisao e nao lacuna:
    a spec deste incremento recusa a regra de segredo em texto claro, que seria o
    QUARTO exemplar do mesmo julgamento (`SF-EMR-002`, `SF-EMRS-002`,
    `SF-EMRK-001`) e cuja fonte, aqui, nao existe -- a BMC nao publica warning de
    texto claro para definicao de job. A redacao continua valendo mesmo assim,
    porque ela nao e julgamento: ela impede que o proprio `facts.json` do handoff
    vire a segunda copia do segredo.
    """
    variaveis = node.get("Variables")
    if not isinstance(variaveis, list):
        return []
    facts: list[Fact] = []
    for entrada in variaveis:
        if not isinstance(entrada, dict):
            continue
        for nome, valor in entrada.items():
            attrs: dict[str, Any] = {"name": str(nome)}
            texto = valor if isinstance(valor, str) else None
            if texto is None:
                attrs["value_type"] = type(valor).__name__
            elif _looks_like_secret(str(nome), texto):
                attrs["value"] = REDACTED
                attrs["redacted"] = True
                attrs["secret_pattern_match"] = True
            else:
                attrs["value"] = texto
            facts.append(
                Fact(
                    kind="ctm.variable",
                    subject=subject,
                    attrs=attrs,
                    provenance=provenance,
                )
            )
    return facts


# --------------------------------------------------------------------------- #
# travessia
# --------------------------------------------------------------------------- #


def _is_job_type(tipo: str | None) -> bool:
    return tipo is not None and (tipo.startswith("Job:") or tipo == "Job")


def _reference_path(node: dict[str, Any], folder_type: str) -> tuple[dict[str, Any], int]:
    """`ReferencePath` contra job explicito, ja decidido (D-2 do incremento 3).

    A fonte: *"Note that a sub-folder that contains the `ReferencePath` property
    must not contain any explicit job objects."*

    SO RESPONDE QUANDO A PROPRIEDADE EXISTE. A exigencia e condicional a presenca
    dela; contar job explicito em todo folder responderia uma pergunta que
    ninguem fez sobre a maioria deles, e moveria todo golden existente.

    O VEREDITO E SO PARA `SubFolder`, E A LITERALIDADE E DELIBERADA. A frase da
    fonte diz "a sub-folder", e a propria descricao da propriedade diz que ela
    serve para "reference a job or folder from within a sub-folder". Um `Folder`
    de topo com `ReferencePath` continua registrando `reference_path` -- a
    evidencia existe --, mas nao recebe veredito, porque a fonte nao declara
    defeito ali. Estender por simetria seria acusar o que ninguem publicou.

    O QUE CONTA COMO "explicit job object": objeto NOMEADO com `Type: Job:*`
    dentro do proprio no, e entrada do array `Jobs` -- as duas formas que a
    pagina publica para declarar um job. Sub-folder aninhado NAO conta: a fonte
    fala de job, e um container nao e um job.
    """
    caminho = _as_str(node.get("ReferencePath"))
    if caminho is None:
        return {}, 0
    explicitos = sum(1 for _, filho in _children(node) if _is_job_type(_as_str(filho.get("Type"))))
    for chave in _JOB_ARRAY_KEYS:
        entradas = node.get(chave)
        if isinstance(entradas, list):
            explicitos += sum(
                1
                for e in entradas
                if isinstance(e, dict) and _is_job_type(_as_str(e.get("Type")))
            )
    attrs: dict[str, Any] = {"reference_path": caminho}
    if folder_type == "SubFolder":
        attrs["reference_path_with_explicit_jobs"] = explicitos > 0
    return attrs, explicitos


def _children(node: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Os filhos NOMEADOS de um objeto, na ordem em que o JSON os declara.

    Ordem de declaracao e nao `sorted()`: `sort_facts` reordena a saida no fim,
    e ordenar aqui tambem tornaria a travessia diferente do arquivo sem ganho.
    Filho e todo valor que e um mapa COM `Type` -- um mapa sem `Type` e bloco de
    propriedade (`When`, `Events`), nunca entidade.
    """
    saida: list[tuple[str, dict[str, Any]]] = []
    for chave, valor in node.items():
        if isinstance(valor, dict) and _as_str(valor.get("Type")) is not None:
            saida.append((str(chave), valor))
    return saida


def _walk(
    node: dict[str, Any],
    name: str,
    trilha: str,
    path: str,
    declared_version: str | None,
    provenance: dict[str, Any],
    facts: list[Fact],
    array_key: str | None = None,
) -> None:
    """Visita um objeto com `Type` e emite os facts dele e dos filhos.

    Recursao com trilha explicita, e nao um indice global: o subject de cada
    entidade e `Folder/SubFolder/Job`, e uma trilha errada faria dois jobs
    homonimos em folders diferentes compartilharem grupo de `same_subject`.

    `array_key` diz por qual array este objeto foi alcancado, ou `None` quando
    ele e filho nomeado. Ele NAO desce na recursao: o que a fonte liga a
    `allowDuplicateJobNames` e a definicao do proprio objeto em formato de array,
    nao a de tudo que estiver dentro dele.
    """
    tipo = _as_str(node.get("Type"))
    if tipo is None:
        return
    symbol = f"{trilha}/{name}" if trilha else name
    subject = _entity_subject(path, symbol)

    if tipo in _FOLDER_TYPES:
        attrs = {"folder_type": tipo, "name": _as_str(node.get("Name")) or name}
        attrs.update(_identity_attrs(node))
        referencia, explicitos = _reference_path(node, tipo)
        attrs.update(referencia)
        facts.append(
            Fact(
                kind="ctm.folder",
                subject=subject,
                measures={"explicit_job_count": explicitos} if referencia else {},
                attrs=attrs,
                provenance=provenance,
            )
        )
        facts.extend(_schedule_fact(node, subject, provenance))
        facts.extend(_dependency_facts(node, subject, provenance))
        facts.extend(_variable_facts(node, subject, provenance))
    elif _is_job_type(tipo):
        attrs = {"job_type": tipo, "name": _as_str(node.get("Name")) or name}
        attrs.update(_identity_attrs(node))
        facts.append(Fact(kind="ctm.job", subject=subject, attrs=attrs, provenance=provenance))
        if array_key is not None:
            # O fact derivado de J-3. Ele existe porque a exigencia da fonte e
            # sobre a FORMA da definicao -- "job definitions in an array format"
            # --, e essa forma nao esta em nenhum campo do job: esta em como se
            # chegou ate ele. So o caminho sabe, e o caminho e este.
            facts.append(
                Fact(
                    kind="ctm.job_array_format",
                    subject=subject,
                    attrs={
                        "array_key": array_key,
                        "job_type": tipo,
                        "name": _as_str(node.get("Name")) or name,
                        "name_declared": _as_str(node.get("Name")) is not None,
                    },
                    provenance=provenance,
                )
            )
        facts.extend(_schedule_fact(node, subject, provenance))
        facts.extend(_dependency_facts(node, subject, provenance))
        facts.extend(_variable_facts(node, subject, provenance))
        slug = _JOB_TYPE_CAPABILITIES.get(tipo)
        if slug is not None:
            facts.append(
                _capability_fact(
                    slug,
                    {"evidence": "job_type", "job_type": tipo, "job": symbol},
                    declared_version,
                    subject,
                    provenance,
                )
            )
    elif tipo == "Flow":
        facts.extend(_flow_facts(node, name, subject, provenance))
    elif tipo == "If":
        facts.extend(_action_facts(node, name, subject, provenance))
    elif tipo in _EVENT_OBJECT_TYPES:
        facts.extend(_event_object_facts(node, tipo, subject, provenance))

    # A sonda de ESTRUTURA olha o proprio no, e nao os filhos: `Folders` e
    # `SubFolders` sao arrays de folder, e o que a capacidade nomeia e a FORMA
    # do array, nao o que ha dentro dele.
    for chave in _ARRAY_STRUCTURE_KEYS:
        if isinstance(node.get(chave), list):
            facts.append(
                _capability_fact(
                    _ARRAY_STRUCTURE_CAPABILITY,
                    {"evidence": "array_structure", "key": chave, "at": symbol},
                    declared_version,
                    subject,
                    provenance,
                )
            )

    for filho_nome, filho in _children(node):
        _walk(filho, filho_nome, symbol, path, declared_version, provenance, facts)
    _walk_array_entries(node, symbol, path, declared_version, provenance, facts)


def _walk_array_entries(
    node: dict[str, Any],
    trilha: str,
    path: str,
    declared_version: str | None,
    provenance: dict[str, Any],
    facts: list[Fact],
) -> int:
    """Visita o que esta declarado em array -- `Folders`, `SubFolders`, `Jobs`.

    Objeto dentro de array NAO e filho nomeado: ele nao tem chave, e o nome vem
    da propriedade `Name`. Sem este laco, todo artefato na forma de array sairia
    com zero jobs.

    `Jobs` entra AQUI e nao em `_ARRAY_STRUCTURE_KEYS`, e a separacao decide o
    que a sonda de capacidade acusa. `folders_array_structure` e a capacidade que
    a matriz nomeia, e ela e sobre a estrutura de FOLDER; incluir `Jobs` naquela
    tupla faria a sonda disparar sobre um array de jobs, que a matriz nao data --
    exatamente o veto `V-CTM-4`. As duas listas se somam so aqui, na travessia,
    porque a travessia e cega a capacidade.

    O INDICE ENTRA NA TRILHA (`Folders[0]/CargaNoturna`) e isso nao e cosmetica.
    A capacidade que este array introduz e justamente permitir DOIS folders com o
    MESMO nome; usar so o `Name` daria a ambos o mesmo `subject.symbol`, e
    `same_subject` juntaria os dois no mesmo grupo -- o folder correto mascararia
    o incorreto, que e o falso negativo que `same_subject` existe para evitar.
    """
    visitados = 0
    for chave in _ARRAY_STRUCTURE_KEYS + _JOB_ARRAY_KEYS:
        entradas = node.get(chave)
        if not isinstance(entradas, list):
            continue
        for indice, entrada in enumerate(entradas):
            if not isinstance(entrada, dict):
                continue
            nome = _as_str(entrada.get("Name")) or f"{chave}[{indice}]"
            posicao = f"{chave}[{indice}]"
            base = f"{trilha}/{posicao}" if trilha else posicao
            _walk(
                entrada,
                nome,
                base,
                path,
                declared_version,
                provenance,
                facts,
                array_key=chave,
            )
            visitados += 1
    return visitados


# --------------------------------------------------------------------------- #
# entrada
# --------------------------------------------------------------------------- #


def extract_controlm_jobs(
    payload: Any,
    path: str,
    artifact_sha256: str = "",
    declared_version: str | None = None,
) -> list[Fact]:
    """Extrai Facts de um payload ja carregado (`dict`) de `Jobs-as-Code`.

    `declared_version` e DECLARACAO do operador (D-1), nunca leitura do artefato.
    Sem ela o cruzamento com a matriz nao acontece e as capacidades observadas
    saem em `ctm.capability_unresolved` com a medida que as destrava.

    Nunca levanta excecao por payload malformado: topo que nao e mapa, objeto sem
    `Type`, secao com o tipo errado -- tudo vira `ctm.unresolved` e a extracao
    segue com o que sobrar, mesma convencao de `emr_eks.extract_emr_eks`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []
    versao = _as_str(declared_version) if declared_version is not None else None

    if versao is not None:
        facts.append(_version_declared_fact(versao, path, provenance))

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
        return _finish(facts, path, provenance, versao)

    entidades = 0
    for nome, valor in payload.items():
        if nome in _RESERVED_TOP_LEVEL:
            continue
        if nome in _ARRAY_STRUCTURE_KEYS + _JOB_ARRAY_KEYS and isinstance(valor, list):
            # `Folders`/`SubFolders`/`Jobs` de topo NAO sao entrada mal formada:
            # sao a estrutura de array, e o laco proprio logo abaixo os visita.
            # Sem esta guarda o artefato inteiro na forma de array sairia com um
            # `ctm.unresolved` fantasma dizendo que o topo nao e um objeto.
            continue
        if not isinstance(valor, dict):
            facts.append(
                _unresolved(
                    path, "top_level_entry_is_not_an_object", provenance, entry=str(nome)
                )
            )
            continue
        if _as_str(valor.get("Type")) is None:
            # Objeto de topo sem `Type` nao e folder, nao e job e nao e nada que
            # a fonte nomeie. Ele NAO some em silencio: a diferenca entre "nao ha
            # entidade" e "havia algo que nao deu para classificar" e exatamente
            # o que o ponto cego contado existe para preservar.
            facts.append(
                _unresolved(
                    path, "top_level_object_without_type", provenance, entry=str(nome)
                )
            )
            continue
        entidades += 1
        _walk(valor, str(nome), "", path, versao, provenance, facts)

    # A sonda de estrutura tambem vale no TOPO: `{"Folders": [...]}` e artefato
    # valido e nao tem objeto com `Type` acima do array.
    for chave in _ARRAY_STRUCTURE_KEYS:
        if isinstance(payload.get(chave), list):
            facts.append(
                _capability_fact(
                    _ARRAY_STRUCTURE_CAPABILITY,
                    {"evidence": "array_structure", "key": chave, "at": chave},
                    versao,
                    _entity_subject(path, chave),
                    provenance,
                )
            )
    entidades += _walk_array_entries(payload, "", path, versao, provenance, facts)

    if entidades == 0 and not any(f.kind == "ctm.unresolved" for f in facts):
        facts.append(_unresolved(path, "no_controlm_entity", provenance))

    return _finish(facts, path, provenance, versao)


def _version_declared_fact(
    version: str, path: str, provenance: dict[str, Any]
) -> Fact:
    """A versao declarada, marcada como DECLARACAO no proprio fact (D-1).

    `source: operator_declaration` e `read_from_artifact: false` estao nos attrs
    porque quem le o `facts.json` meses depois precisa saber que este numero
    ninguem mediu -- alguem o digitou. Um fact de versao sem essa marca seria
    indistinguivel de `spark.runtime_version`, que o event log MEDE.
    """
    attrs: dict[str, Any] = {
        "version": version,
        "source": "operator_declaration",
        "read_from_artifact": False,
    }
    try:
        from sparkforge.controlm import matrix as cm

        piso, teto = cm.covers()
        attrs["matrix_covers_from"] = piso
        attrs["matrix_covers_to"] = teto
    except Exception as exc:  # a matriz nao carrega -- a declaracao continua valendo
        attrs["matrix_unavailable"] = str(exc)
    return Fact(
        kind="ctm.version_declared",
        subject=_file_subject(path),
        attrs=attrs,
        provenance=provenance,
    )


def _finish(
    facts: list[Fact], path: str, provenance: dict[str, Any], version: str | None
) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho para todos os
    caminhos de saida, inclusive os que abortam cedo."""
    derivados = (
        "ctm.capability_supported",
        "ctm.capability_incompatible",
        "ctm.capability_unresolved",
    )
    counts = {
        "folder_count": sum(1 for f in facts if f.kind == "ctm.folder"),
        "job_count": sum(1 for f in facts if f.kind == "ctm.job"),
        "dependency_count": sum(1 for f in facts if f.kind == "ctm.dependency"),
        "capability_probe_count": sum(1 for f in facts if f.kind in derivados),
        "capability_unresolved_count": sum(
            1 for f in facts if f.kind == "ctm.capability_unresolved"
        ),
        "unresolved_count": sum(1 for f in facts if f.kind == "ctm.unresolved"),
    }
    # Sentinela: prova de que a extracao rodou sobre ESTE artefato, e de que a
    # versao ou foi declarada ou nao foi. Sem ela, uma condicao `absent:` sobre
    # fact `ctm.*` seria vacuamente verdadeira quando o extrator nunca rodou.
    facts.append(
        Fact(
            kind="ctm.analyzed",
            subject=_file_subject(path),
            measures=counts,
            attrs={"version_declared": version is not None},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")
    return sort_facts(facts)


def extract_controlm_jobs_path(
    path: Path, repo_root: Path | None = None, declared_version: str | None = None
) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `ctm.unresolved` com reason "read_error"; JSON invalido
    vira "malformed_json". Nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    versao = _as_str(declared_version) if declared_version is not None else None
    empty_provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        facts = []
        if versao is not None:
            facts.append(_version_declared_fact(versao, anchor, empty_provenance))
        facts.append(_unresolved(anchor, "read_error", empty_provenance, detail=str(exc)))
        return _finish(facts, anchor, empty_provenance, versao)

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        facts = []
        if versao is not None:
            facts.append(_version_declared_fact(versao, anchor, provenance))
        facts.append(_unresolved(anchor, "malformed_json", provenance))
        return _finish(facts, anchor, provenance, versao)

    return extract_controlm_jobs(
        parsed, anchor, artifact_sha256=sha, declared_version=versao
    )


def extract_controlm_jobs_tree(
    root: Path, repo_root: Path | None = None, declared_version: str | None = None
) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico vira `ctm.unresolved`
    para aquele arquivo e a travessia continua.
    """
    facts: list[Fact] = []
    for json_file in iter_source_files(root, "*.json"):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(
                extract_controlm_jobs_path(json_file, repo_root, declared_version)
            )
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
            facts.append(_unresolved(anchor, "read_error", provenance, detail=str(exc)))
    return sort_facts(facts)


__all__ = [
    "CAPABILITY_NOT_IN_MATRIX",
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "VERSION_NOT_DECLARED",
    "extract_controlm_jobs",
    "extract_controlm_jobs_path",
    "extract_controlm_jobs_tree",
]
