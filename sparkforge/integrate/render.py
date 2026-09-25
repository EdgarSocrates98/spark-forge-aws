"""O renderizador por plataforma de skills e agents -- um so, para os espelhos do
repositorio (`scripts/sync_skills.py`) e para a integracao por usuario
(`sparkforge integrate`).

Movido de `scripts/sync_skills.py` pela feature INTEGRACAO_USUARIO (D1): o texto
das decisoes abaixo e o de la, sem mudanca. O que mudou e so a assinatura das
funcoes que leem perfis -- recebem o diretorio de agents por parametro, porque o
pacote instalado nao tem `agents/` na raiz do repositorio -- e a plataforma
`codex` (D2).

Este modulo importa so a biblioteca padrao. `scripts/sync_skills.py` o carrega
PELO CAMINHO do arquivo, e nao pelo pacote instalado, para que
`tests/test_arvore_versionada.py` confira o espelho commitado contra o renderizador
commitado; um import de `sparkforge.*` aqui quebraria esse carregamento.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# --------------------------------------------------------------------------
# Renderizacao por plataforma
# --------------------------------------------------------------------------
# Fundamento medido: knowledge/devin/agents-and-subagents.md (retrieved
# 2026-08-04). Desenho: D-1, D-2 e D-3 de
# docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md.

# `claude` e `github` recebem o arquivo INALTERADO. Nao ha round-trip de YAML
# em caminho nenhum: parsear e re-serializar reordenaria as chaves e produziria
# diff onde nao houve mudanca, e o gate viraria ruido.
PASSTHROUGH_PLATFORMS = frozenset({"claude", "github"})
# `codex` (D2): o perfil vira o TOML de `~/.codex/agents/` -- `name`, `description`
# e `developer_instructions` (learn.chatgpt.com/docs/agent-configuration/subagents,
# lido em 2026-09-25). A skill do Codex e a mesma `SKILL.md`, sem campo a mais.
PLATFORMS = PASSTHROUGH_PLATFORMS | {"devin", "codex"}

# Campos que o espelho do Devin NAO leva.
#
# `tools:` -- o Devin aceita o campo ("Claude Code agent files use `tools`
# instead of `allowed-tools`[...] Both formats are supported automatically"),
# mas o MAPEAMENTO DE VALORES nao esta documentado em lugar nenhum: `Bash` ->
# `exec`? `Write` -> `write`? Os nomes de tool do Devin sao `read`, `edit`,
# `grep`, `glob`, `exec` (cli/reference/permissions.md). Chute em campo de
# PERMISSAO concede ou nega errado, e nos dois sentidos o erro e caro. Omitido,
# o subagente herda o que o harness da -- que e o comportamento que a propria
# documentacao descreve como default ("all tools"). Veto V-DV-8.
DEVIN_DROPPED_KEYS = frozenset({"tools"})

# NENHUM caminho aqui ACRESCENTA `model:`, e isso e deliberado (D-3):
#   1. o default do subagente "is not a fixed model name -- it resolves through
#      a router at spawn time";
#   2. o admin da organizacao sobrescreve pela setting "Default subagent
#      model", inclusive com a opcao *None*, que desliga o despacho por
#      completo;
#   3. o identificador literal e `swe-1-7`, com HIFEN -- a doc interna que
#      motivou esta fase errava com ponto, e nenhuma pagina do CLI documenta
#      esse literal como valor aceito de frontmatter (vetos V-DV-2 e V-DV-3).
# Escrever `model:` seria fingir controle sobre o que o harness decide. Quem
# vier depois vai querer "completar" o frontmatter: nao complete sem medir.

# Nomes que o Devin ja usa para os seus dois perfis embutidos. A tabela de
# frontmatter da fonte diz, sobre `name`: "Identifier for the profile (must not
# conflict with built-in profiles)", e a tabela de perfis nomeia os dois --
# knowledge/devin/agents-and-subagents.md, secao 1 (retrieved 2026-08-04).
#
# A fonte PROIBE a colisao e NAO diz o que acontece quando ela ocorre. Pular com
# aviso, sobrescrever o built-in e recusar a sessao sao todos plausiveis, e
# nenhum esta escrito. Por isso o gate recusa o nome em vez de supor qual vale:
# supor comportamento nao documentado e a mesma familia de chute que o V-DV-8
# recusou em `tools:`, agora num campo de IDENTIDADE -- e um perfil que o Devin
# ignore em silencio e pior que um que ele recuse, porque o metodo some sem
# alarme e o built-in `subagent_general` (acesso total, nenhum `## Nao faz`)
# atende no lugar dele.
DEVIN_BUILTIN_PROFILE_NAMES = frozenset({"subagent_explore", "subagent_general"})

_FRONTMATTER_FENCE = "---"
_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:")


def _split_frontmatter(text: str) -> tuple[list[str], list[str], list[str]] | None:
    """Fatia o texto em (abertura, corpo do frontmatter, resto).

    Trabalha em linhas com o fim de linha preservado (`keepends=True`): o gate
    compara byte a byte, entao normalizar CRLF para LF produziria DIVERGENTE em
    toda regeneracao numa arvore com `autocrlf`.

    Devolve `None` quando nao ha frontmatter delimitado -- ai o arquivo sai
    inalterado, em vez de o renderizador adivinhar onde o cabecalho termina.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != _FRONTMATTER_FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == _FRONTMATTER_FENCE:
            return lines[:1], lines[1:index], lines[index:]
    return None


def _drop_frontmatter_keys(front: list[str], keys: frozenset[str]) -> list[str]:
    """Remove chaves de topo do frontmatter, com as continuacoes delas.

    A continuacao importa porque o campo tem duas formas possiveis:

        tools: Read, Grep, Glob        # inline -- e a forma dos treze perfis hoje
        tools:                         # bloco
          - Read
          - Grep

    Apagar so a linha `tools:` na forma de bloco deixaria `  - Read` orfao e
    quebraria o YAML do espelho. A remocao para na proxima linha nao indentada,
    para nao engolir a chave seguinte -- `skills:` vem logo depois e tambem e
    lista indentada.
    """
    kept: list[str] = []
    dropping = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if not dropping:
                kept.append(line)
            continue
        match = _TOP_LEVEL_KEY.match(content)
        dropping = bool(match) and match.group(1) in keys
        if not dropping:
            kept.append(line)
    return kept


def render_agent(text: str, platform: str) -> str:
    """Devolve o conteudo do perfil no formato que `platform` le.

    `claude` e `github` recebem o texto identico -- o espelho deles nao mudou
    nesta fase, e um renderizador que mexesse em todos os alvos quebraria o
    Copilot sem ninguem pedir.
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; conhecidas: {sorted(PLATFORMS)}"
        )
    if platform in PASSTHROUGH_PLATFORMS:
        return text
    if platform == "codex":
        return _codex_toml(text)

    parsed = _split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed

    kept = _drop_frontmatter_keys(front, DEVIN_DROPPED_KEYS)
    if kept == front:
        return text
    return "".join(opening + kept + rest)


# --------------------------------------------------------------------------
# Skills que despacham
# --------------------------------------------------------------------------
# `.agents/skills/<name>/SKILL.md` e caminho de descoberta NATIVO do Devin, nao
# convencao deste repositorio, e o frontmatter de skill aceita `subagent`
# (boolean, default `false`) e `agent` (string, default nenhum) -- tabela de
# knowledge/devin/agents-and-subagents.md secao 8. Desenho: D-5 e D-6.
#
# So o espelho do Devin recebe os campos. `.claude/skills/` continua passthrough
# byte a byte: o Claude Code nao le `subagent:`, e escrever la seria publicar
# campo que ninguem consome.

SKILL_FILENAME = "SKILL.md"

# Campos que a renderizacao do Devin CONTROLA numa skill. Sao removidos antes de
# reinseridos, e nao so acrescentados: assim uma skill que deixou de despachar
# perde o campo no espelho, e um `subagent: true` posto a mao num espelho volta
# a divergir do que o tradutor produz. Acrescentar sem remover deixaria os dois
# casos passarem calados.
DEVIN_SKILL_DISPATCH_KEYS = frozenset({"subagent", "agent"})

# D-6: despacha quem e investigacao fechada -- o subagente le artefato, julga
# contra o catalogo, e devolve texto que o pai resume. Nao despacha quem dirige
# o loop, quem orquestra outras skills, ou quem precisa de uma decisao que so
# uma pessoa tem.
#
# A assimetria que decide os casos duvidosos: uma skill despachavel a mais que
# precisasse perguntar falha MUDA -- `ask_user_question` e sempre negado a
# subagente (veto V-DV-10), entao ela inventa a resposta ou para sem dizer por
# que. Uma skill despachavel a menos custa contexto do pai, e mais nada. Na
# duvida, nao despacha.
DISPATCHABLE_SKILLS = {
    "analyze-batch-loop": "extrai o loop do codigo e julga; a saida e relatorio",
    "analyze-library-call-graph": "varre a biblioteca e devolve o grafo; leitura fechada",
    "analyze-spark-plan": "interpreta um plano fisico ja salvo; nao pede nada a ninguem",
    "analyze-spark-ui": "coleta e julga o event log de um run identificado no pedido",
    "diagnose-data-skew": "cruza SF-UI-001 com SF-UI-002 sobre o event log que ela mesma coleta",
    "diagnose-oom": "classifica o OOM por `heap_oom_in_log`; discriminador esta no artefato",
    "optimize-parquet-layout": "junta listagem, plano e catalogo, todos coletaveis so lendo",
    "optimize-pyspark-code": "mesma forma de `review-pyspark-pr`: extrai, julga, propoe diff",
    "review-data-validation": "revisa a validacao declarada no codigo e devolve achados",
    "review-emr-cluster": "revisa a definicao do cluster que ja esta em disco",
    "review-emr-eks": "revisa o job run do emr-containers que ja esta em disco",
    "review-glue-terraform": "revisa o .tf que ja esta em disco",
    "review-pyspark-pr": "revisa um diff fechado e classifica risco",
    "analyze-functional-rules": "Especialista de dominio; despacho por coordenador",
    # As tres de Glue 6 que LEEM e julgam, sem decisao de terceiro no caminho:
    # os artefatos (codigo, .tf, requirements, .jar) ja estao em disco, e o
    # veredito sai do catalogo e da matriz.
    "migrate-glue-6": "extrai a arvore do job e julga degrau a degrau; leitura fechada",
    "spark4-compatibility": "julga o codigo e os pins contra a fronteira do Spark 4",
    "lakeformation-fgac-guard": "correlaciona FGAC e classpath no .tf que ja esta em disco",
    # Le as quatro matrizes de `knowledge/` e devolve numero com fonte. Nao ha
    # artefato do operador para faltar, nao ha decisao de terceiro no caminho, e
    # nenhum Finding nasce dela -- a leitura e fechada por construcao.
    "compare-releases": (
        "le as quatro matrizes de versao e devolve o diff com o eixo declarado; "
        "nao le artefato do operador e nao julga"
    ),
}

NON_DISPATCHABLE_SKILLS = {
    # Ela COLETA da AWS ao vivo, e as quatro coletas do procedimento pedem
    # credencial e permissao de leitura sobre governanca de terceiro
    # (`ListPermissions`, `GetDataLakeSettings`, `SimulatePrincipalPolicy`).
    # Alem disso, TODA recomendacao dela e mudanca de postura de seguranca, e
    # tres delas -- boundary, service control policy, desregistrar localizacao --
    # tem raio maior que o do job. Despachar quem nao pode perguntar seria
    # exatamente o caso que este registro existe para barrar.
    "diagnose-lakeformation-access": (
        "coleta da AWS ao vivo e recomenda mudanca de permissao; a decisao sobe "
        "a quem responde pela governanca, e um subagente nao pode perguntar"
    ),
    # Ela e o DRIVER do debate: conduz o laco next -> submit e, idealmente,
    # despacha um subagente POR LADO. Despacha-la inteira para um subagente
    # juntaria os dois lados num contexto so -- o lado A leria o raciocinio
    # privado do B --, e o `submit` grava no blackboard do case (mutacao local).
    "run-debate": (
        "conduz o laco do debate no agente pai e despacha os lados; despachada "
        "inteira, os dois lados dividiriam um contexto e gravariam no case"
    ),
    # O lado do host do L3 do §15: roda git na arvore do operador e para antes
    # de `git push` e de `gh pr create`. As duas paradas pedem confirmacao
    # humana, e um subagente despachado nao tem a quem perguntar.
    "propose-change-pr": (
        "roda git/gh na arvore do operador e para para confirmacao humana antes de "
        "push e de abrir o PR; despachada, ninguem estaria la para confirmar"
    ),
    "tool-specialist-routing": "valida roteamento no agente atual",
    # As duas que dirigem o loop. Um subagente nao herda o historico do pai e,
    # por default, nao gera subagente proprio (`max-nesting`): despachar quem
    # orquestra e perder justamente a orquestracao.
    "sparkforge-diagnose": (
        "abre o case e roteia. Despachar joga o ciclo de vida do case para um "
        "contexto que nao volta -- e o case e o que faz a investigacao atravessar "
        "sessoes e ferramentas"
    ),
    "glue-incremental-performance-architect": (
        "orquestra as skills especializadas por `next-step` e le "
        "PROMPT_INICIAL_MESTRE.md; subagente nao gera subagente por default"
    ),
    # As que precisam de uma decisao que nao esta no repositorio.
    "iceberg-v3-readiness": (
        "subir `format-version` e decisao de IDA, e a skill exige o inventario de "
        "consumidores -- que e conhecimento da organizacao, escrito por uma pessoa, "
        "nao derivavel de artefato. Dentro de subagente a pergunta 'quem mais le "
        "esta tabela?' e inalcancavel, e a resposta errada quebra o consumidor dias "
        "depois"
    ),
    "optimize-iceberg-table": (
        "`expire_snapshots` e `remove_orphan_files` nao tem desfazer, e a propria "
        "skill exige que a retencao venha do dono dos dados. Dentro de subagente "
        "essa confirmacao e inalcancavel"
    ),
    "optimize-latest-per-key": (
        "a secao `Perguntas que o extrator nao faz por voce` sao quatro perguntas "
        "de semantica de negocio -- desempate, timezone, correcao retroativa"
    ),
    "design-incremental-processing": (
        "o contrato de saida tem dezesseis campos de desenho que nenhum extrator "
        "preenche; a propria skill os chama de perguntas"
    ),
    # As que dependem de evidencia que o pai ja acumulou, ou de uma execucao nova.
    "benchmark-pyspark-job": (
        "o passo 2 e `aplique a mudanca` entre as duas coletas: exige um run novo "
        "e o id dele, que so aparece depois de alguem publicar a mudanca"
    ),
    "optimize-variable-volume-job": (
        "classificar execucoes por perfil parte do volume observado no workload, "
        "e compara N runs que o operador escolhe"
    ),
    "tune-glue-job": (
        "o passo 1 exige baseline ja provado por `analyze-spark-ui`, `diagnose-oom` "
        "e `diagnose-data-skew`; subagente nao herda o historico do pai e teria de "
        "reconstruir a evidencia que motivou a chamada"
    ),
    "design-data-architecture": "Especialista de dominio; despacho por coordenador",
    "design-s3-data-lake": "Especialista de dominio; despacho por coordenador",
    "review-terraform-data-platform": "Especialista de dominio; despacho por coordenador",
    # As duas que mutam infraestrutura AWS ao vivo: procedimento operacional,
    # nao gatilho do motor. Rodam `aws s3tables create-*` e `aws s3api put-*`,
    # e a fronteira `## Nao faz` exige confirmacao explicita do operador para
    # cada comando de escrita -- inalcancavel dentro de subagente (V-DV-10).
    "provision-s3-tables-table": (
        "cria table bucket, namespace, tabela e catalog integration S3 Tables "
        "via `aws s3tables`/`aws glue` ao vivo; a fronteira `## Nao faz` exige "
        "confirmacao do operador por comando de escrita, inalcancavel em subagente"
    ),
    "harden-s3-bucket": (
        "executa `put-bucket-policy`, `put-bucket-encryption`, `create-detector` "
        "ao vivo; a fronteira `## Nao faz` exige confirmacao do operador por "
        "comando de escrita, inalcancavel em subagente"
    ),
    # As nove skills oficiais AWS adaptadas (aws/agent-toolkit-for-aws, commit
    # 10b28af8): procedimento operacional AWS, nao gatilho do motor SparkForge.
    # Sao referencia de servico (storage, database, serverless, IAM, observability,
    # billing, messaging, security, SDK Python) e podem mutar infra ao vivo.
    # A fronteira `## Nao faz` de cada uma exige confirmacao do operador por
    # comando de escrita -- inalcancavel em subagente (V-DV-10).
    "aws-storage": (
        "referencia de storage AWS (S3, EFS, FSx, EBS); pode mutar configuracao "
        "de bucket e lifecycle ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-database": (
        "roteia para skill de database AWS (Aurora, RDS, DynamoDB, etc); pode "
        "mutar configuracao de instancia ao vivo, fronteira exige confirmacao"
    ),
    "aws-serverless": (
        "procedimento de Lambda, Step Functions, EventBridge; pode mutar funcao "
        "e state machine ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-iam": (
        "referencia de IAM (policies, roles, trust); pode mutar policy e role "
        "ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-observability": (
        "procedimento de CloudWatch, X-Ray, CloudTrail; pode mutar alarme, "
        "dashboard e trail ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-billing-and-cost-management": (
        "analise de custo AWS (CUR, Savings Plans); pode mutar budget e alerta "
        "ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-messaging-and-streaming": (
        "referencia de SQS, SNS, EventBridge, Kinesis, MSK; pode mutar fila, "
        "topico e stream ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-security": (
        "procedimento de Security Hub, GuardDuty, Inspector; pode mutar finding "
        "e detector ao vivo, fronteira exige confirmacao do operador"
    ),
    "aws-sdk-python-usage": (
        "padroes de boto3/botocore; e referencia de uso de SDK, nao muta infra "
        "por si, mas pode executar chamadas AWS se o operador pedir"
    ),
    # As seis fases do SDD proprio (feature SDD_SKILLS, 2026-09-16). Dirigem a
    # sessao e o operador, nao investigam artefato fechado (D-6): explore,
    # define, design e plan fazem uma pergunta por vez e esperam a aprovacao;
    # build despacha um subagente por tarefa e dois revisores, e subagente nao
    # gera subagente por default; ship para antes de push e de PR.
    "sdd-explore": (
        "pergunta uma coisa por vez e espera o operador escolher a abordagem; "
        "despachada, ninguem estaria la para responder"
    ),
    "sdd-define": (
        "fecha criterios e hipotese com o operador, uma pergunta por vez; "
        "subagente nao pode perguntar (V-DV-10)"
    ),
    "sdd-design": (
        "apresenta o desenho por partes e espera aprovacao de cada uma; "
        "subagente nao pode perguntar"
    ),
    "sdd-plan": (
        "o plano passa pela leitura do operador antes de ficar ready; "
        "subagente nao pode perguntar"
    ),
    "sdd-build": (
        "despacha um subagente por tarefa e dois revisores; despachada inteira, "
        "perderia a orquestracao, porque subagente nao gera subagente por default"
    ),
    "sdd-ship": (
        "para antes de git push, merge e gh pr create para a escolha do operador; "
        "despachada, ninguem estaria la para escolher"
    ),
}

SKILL_DISPATCH_REASON = {**DISPATCHABLE_SKILLS, **NON_DISPATCHABLE_SKILLS}

_LIST_ITEM = re.compile(r"^\s*-\s+(.*)$")


def _frontmatter_list(front: list[str], key: str) -> list[str]:
    """Le uma lista do frontmatter, nas duas formas que o corpus usa.

        skills:          |  rule_areas: [SF-EMR, SF-PY]
          - review-x     |
          - review-y     |

    A forma inline existe hoje em `rule_areas:` e `executors:`; se alguem
    escrever `skills:` assim, um leitor que so entendesse blocos devolveria
    lista vazia -- e lista vazia aqui vira "nenhum coordenador declara esta
    skill", que e silencio, nao erro.
    """
    values: list[str] = []
    collecting = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if collecting:
                item = _LIST_ITEM.match(content)
                if item:
                    values.append(item.group(1).strip().strip("'\""))
            continue
        match = _TOP_LEVEL_KEY.match(content)
        collecting = False
        if match and match.group(1) == key:
            inline = content.split(":", 1)[1].strip()
            if not inline:
                collecting = True
            elif inline.startswith("[") and inline.endswith("]"):
                values.extend(
                    part.strip().strip("'\"")
                    for part in inline[1:-1].split(",")
                    if part.strip()
                )
            else:
                values.append(inline.strip("'\""))
    return values


class EscalarYamlNaoSuportado(ValueError):
    """Escalar de frontmatter que a leitura por linha nao le sem errar.

    Sem biblioteca de YAML (este modulo so usa a biblioteca padrao), escalar em
    bloco (`>-`, `|`), continuacao indentada e escape de aspas duplas sairiam com
    o valor errado -- e descricao errada publicada e pior que recusa.
    """


_BLOCO_YAML = re.compile(r"^[|>][-+0-9]*$")


def _valor_escalar(key: str, bruto: str, continua: bool) -> str | None:
    """O valor de `key: bruto`, ou `EscalarYamlNaoSuportado` quando nao da para ler."""
    def recusa(motivo: str) -> EscalarYamlNaoSuportado:
        return EscalarYamlNaoSuportado(
            f"escalar_yaml_nao_suportado: `{key}` {motivo}; escreva o valor numa "
            "linha so, sem aspas ou entre aspas sem escape"
        )

    if _BLOCO_YAML.match(bruto):
        raise recusa(f"em bloco ({bruto!r})")
    if continua:
        raise recusa("continua na linha de baixo")
    if bruto[:1] == '"':
        if len(bruto) < 2 or not bruto.endswith('"') or "\\" in bruto:
            raise recusa("entre aspas duplas com escape")
        return bruto[1:-1] or None
    if bruto[:1] == "'":
        miolo = bruto[1:-1]
        if len(bruto) < 2 or not bruto.endswith("'") or "'" in miolo.replace("''", ""):
            raise recusa("entre aspas simples mal fechadas")
        return miolo.replace("''", "'") or None
    return bruto or None


def _frontmatter_scalar(front: list[str], key: str) -> str | None:
    """Le um escalar de topo do frontmatter, ou `None` se ele nao estiver la.

    Irmao de `_frontmatter_list`, e pela mesma razao: nao ha round-trip de YAML
    em caminho nenhum deste arquivo, entao a leitura tambem e por linha. O que a
    leitura por linha nao le certo levanta `EscalarYamlNaoSuportado`.
    """
    for index, line in enumerate(front):
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            continue
        match = _TOP_LEVEL_KEY.match(content)
        if match and match.group(1) == key:
            bruto = content.split(":", 1)[1].strip()
            seguinte = front[index + 1].rstrip("\r\n") if index + 1 < len(front) else ""
            continua = bool(bruto) and seguinte[:1] in (" ", "\t") and bool(seguinte.strip())
            return _valor_escalar(key, bruto, continua)
    return None


# Controle que a string basica do TOML proibe e que o `json.dumps` deixa passar
# cru: o DEL (U+007F). Os de U+0000 a U+001F o JSON ja escapa.
_CONTROLE_TOML = re.compile("[\x7f]")


def _toml_string(valor: str) -> str:
    """String basica de TOML.

    O escape do JSON e um subconjunto do escape de string basica do TOML, entao
    `json.dumps` serve sem depender de biblioteca de TOML -- que o Python 3.10 nao
    tem, e que o projeto nao traz como dependencia. O que o JSON deixa cru e o
    TOML proibe (U+007F) sai como `\\uXXXX`.
    """
    return _CONTROLE_TOML.sub(
        lambda m: f"\\u{ord(m.group()):04X}", json.dumps(valor, ensure_ascii=False)
    )


def _codex_toml(text: str) -> str:
    """O perfil no formato de `~/.codex/agents/<nome>.toml`.

    `developer_instructions` e o corpo do markdown depois do frontmatter, com LF.
    Perfil sem `name` ou sem `description` levanta: o Codex exige os dois, e
    inventar a descricao publicaria um papel que ninguem escreveu.
    """
    parsed = _split_frontmatter(text)
    if parsed is None:
        raise ValueError("perfil sem frontmatter nao vira agent do Codex")
    _, front, rest = parsed
    name = _frontmatter_scalar(front, "name")
    description = _frontmatter_scalar(front, "description")
    if not name or not description:
        raise ValueError(
            f"perfil sem `name` ou sem `description` nao vira agent do Codex: {name!r}"
        )
    corpo = "".join(rest[1:]).replace("\r\n", "\n").lstrip("\n")
    return (
        f"name = {_toml_string(name)}\n"
        f"description = {_toml_string(description)}\n"
        f"developer_instructions = {_toml_string(corpo)}\n"
    )


def _agent_files(agents_src: Path) -> list[Path]:
    return sorted(p for p in Path(agents_src).glob("*.md") if p.is_file())


def coordinators_by_skill(agents_src: Path) -> dict[str, tuple[str, ...]]:
    """A relacao skill -> coordenadores, DERIVADA do `skills:` de cada perfil.

    D-5: nao existe segunda lista. Cada coordenador ja declara as skills que
    coordena, e essa declaracao ja e testada por `test_agent_coverage`. Manter
    uma tabela paralela `skill -> agente` seria a familia de defeito que a Fase
    5c achou nos dois `EXTRACTORS` mantidos a mao: uma cresce, a outra nao, e o
    desacordo e mudo.
    """
    relation: dict[str, list[str]] = {}
    for path in _agent_files(agents_src):
        parsed = _split_frontmatter(path.read_bytes().decode("utf-8"))
        if parsed is None:
            continue
        for skill in _frontmatter_list(parsed[1], "skills"):
            relation.setdefault(skill, []).append(path.stem)
    return {skill: tuple(sorted(names)) for skill, names in sorted(relation.items())}


def orchestrator_profiles(agents_src: Path) -> frozenset[str]:
    """Perfis que NAO sao destino de despacho de investigacao fechada.

    Derivado, nao mantido a mao: e o conjunto dos perfis de `agents/*.md` cuja
    skill HOMONIMA este modulo ja declara nao-despachavel. Hoje ele tem
    exatamente um elemento -- `glue-incremental-performance-architect` --, e a
    razao escrita ao lado dela e a mesma que vale para o perfil: ela "orquestra
    as skills especializadas por `next-step`", e subagente nao gera subagente por
    default. Se um dia a skill virar despachavel, a exclusao some sozinha.
    """
    return frozenset(
        name
        for name in NON_DISPATCHABLE_SKILLS
        if (Path(agents_src) / f"{name}.md").is_file()
    )


def agent_for_skill(name: str, agents_src: Path) -> str | None:
    """O perfil que a skill `name` nomeia em `agent:`, ou `None`.

    Skill declarada por mais de um coordenador NAO declara `agent:`, e o Devin
    escolhe o perfil: ordem alfabetica nao e criterio de competencia. Declarante
    unico que e o orquestrador tambem nao: publicar aquilo seria propriedade
    mecanica com cara de decisao (`diagnose-oom`, 2026-08-04). A historia inteira
    esta no `git log` de `scripts/sync_skills.py`.
    """
    coordinators = coordinators_by_skill(agents_src).get(name, ())
    if len(coordinators) != 1:
        return None
    if coordinators[0] in orchestrator_profiles(agents_src):
        return None
    return coordinators[0]


def _newline_of(lines: list[str]) -> str:
    """O fim de linha que o arquivo usa, para a linha inserida usar o mesmo.

    Misturar LF e CRLF dentro do mesmo frontmatter faria o espelho divergir a
    cada regeneracao numa arvore com `autocrlf`.
    """
    for line in reversed(lines):
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def render_skill(text: str, platform: str, *, name: str, agents_src: Path) -> str:
    """Devolve a skill `name` no formato que `platform` le.

    So o Devin recebe `subagent:`/`agent:`. Os campos entram no FIM do
    frontmatter, imediatamente antes da cerca de fechamento: e a unica posicao
    que nao depende de onde as chaves existentes estao, e a que nao pode cair
    dentro de uma lista indentada. O Codex le a `SKILL.md` como ela e.
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; conhecidas: {sorted(PLATFORMS)}"
        )
    if name not in SKILL_DISPATCH_REASON:
        raise ValueError(
            f"skill sem decisao de despacho registrada: {name!r}. Declare em "
            "DISPATCHABLE_SKILLS ou em NON_DISPATCHABLE_SKILLS, com a razao ao "
            "lado -- o default silencioso seria publicar a skill sem ninguem ter "
            "decidido se ela pode rodar sem poder perguntar."
        )
    if platform in PASSTHROUGH_PLATFORMS or platform == "codex":
        return text

    parsed = _split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed

    kept = _drop_frontmatter_keys(front, DEVIN_SKILL_DISPATCH_KEYS)
    added: list[str] = []
    if name in DISPATCHABLE_SKILLS:
        newline = _newline_of(kept or opening)
        added.append(f"subagent: true{newline}")
        agent = agent_for_skill(name, agents_src)
        if agent is not None:
            added.append(f"agent: {agent}{newline}")

    if kept == front and not added:
        return text
    return "".join(opening + kept + added + rest)


def render_skill_file(
    src: Path, skills_root: Path, platform: str, *, agents_src: Path
) -> bytes:
    """Os bytes de um arquivo de skill para `platform`.

    O nome da skill e o NOME DO DIRETORIO sob `skills_root`, o mesmo identificador
    que o Devin usa e que os coordenadores escrevem em `skills:`. Arquivo que nao
    e `SKILL.md` sai como esta, sem passar por `decode`.
    """
    data = Path(src).read_bytes()
    if Path(src).name != SKILL_FILENAME:
        return data
    name = Path(src).relative_to(skills_root).parts[0]
    rendered = render_skill(data.decode("utf-8"), platform, name=name, agents_src=agents_src)
    return rendered.encode("utf-8")


def render_agent_file(src: Path, platform: str) -> bytes:
    """Os bytes de um perfil para `platform`.

    Le e escreve em bytes de proposito: `read_text` aplicaria newline universal e
    um espelho com CRLF passaria a comparar igual a uma fonte LF.
    """
    text = Path(src).read_bytes().decode("utf-8")
    return render_agent(text, platform).encode("utf-8")


__all__ = [
    "DEVIN_BUILTIN_PROFILE_NAMES",
    "EscalarYamlNaoSuportado",
    "DEVIN_DROPPED_KEYS",
    "DEVIN_SKILL_DISPATCH_KEYS",
    "DISPATCHABLE_SKILLS",
    "NON_DISPATCHABLE_SKILLS",
    "PASSTHROUGH_PLATFORMS",
    "PLATFORMS",
    "SKILL_DISPATCH_REASON",
    "SKILL_FILENAME",
    "agent_for_skill",
    "coordinators_by_skill",
    "orchestrator_profiles",
    "render_agent",
    "render_agent_file",
    "render_skill",
    "render_skill_file",
]
