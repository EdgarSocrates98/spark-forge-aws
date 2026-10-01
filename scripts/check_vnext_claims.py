#!/usr/bin/env python3
"""Gate de lastro das alegações publicadas em `docs/vnext/` e `docs/harness/`
(a lista completa, num só lugar, vive em `audited_roots()` abaixo).

Fonte da verdade: `docs/claims.lock.json`. Toda alegação dos documentos
precisa existir no manifesto, e toda entrada do manifesto precisa existir nos
documentos -- fail-closed nos dois sentidos, pela mesma razão registrada em
`tests/test_docs_coverage.py`: lista copiada envelhece sem que nada acuse.

`docs/harness/BASELINE.md` é diferente em natureza dos demais: não afirma
estado ATUAL, afirma uma medição PASSADA, ancorada num commit ("5786 testes,
medido no commit X"). Uma prova `command` comum reexecutaria o comando e
compararia contra o valor de HOJE -- certo para `docs/vnext/`, errado para um
baseline, que por definição envelhece. `proof.kind: "historical"` existe para
isso: confere que o commit citado existe e que o comando está documentado,
mas NUNCA reexecuta. Ver o comentário de `PROOF_KINDS` e `_validate_proof`.

Uso:
    python scripts/check_vnext_claims.py             # audita; sai 1 se divergir
    python scripts/check_vnext_claims.py --full      # inclui provas `tier: slow`
    python scripts/check_vnext_claims.py --seed      # funde alegacoes novas no manifesto
    python scripts/check_vnext_claims.py --seed --force  # descarta e renumera do zero
    python scripts/check_vnext_claims.py --report    # tabela de lastro em Markdown
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
VNEXT = DOCS / "vnext"
HARNESS = DOCS / "harness"
# O manifesto mora em `docs/`, nao em `docs/vnext/`: a partir do momento em
# que `docs/harness/` tambem entra sob o gate (Task de generalizacao), um
# arquivo chamado `claims.lock.json` dentro de `docs/vnext/` mas cobrindo
# alegacoes de `docs/harness/` tambem e a mesma mentira estrutural que a
# tarefa pede para consertar -- so que no proprio nome do caminho, nao no
# conteudo de um documento. Um path neutro nao precisa mentir sobre o que
# audita.
MANIFEST = DOCS / "claims.lock.json"
SOURCES_LOCK = ROOT / "knowledge" / "sources.lock.json"

SCHEMA_VERSION = 1
STATES = frozenset({"PROVADA", "SEM_LASTRO", "REMOVIDA"})
TYPES = frozenset({"number", "capability", "external_fact"})
TIERS = frozenset({"fast", "slow"})
# `historical` prova uma medicao ancorada num commit passado -- NAO reexecuta
# o comando, so confere que ele esta descrito e que o commit existe. Ver
# `_validate_proof` e `audited_roots` para o raciocinio completo: um baseline
# ("5786 testes, medido no commit X") envelhece por natureza, e um gate que
# forca esse numero a continuar batendo HOJE deixou de medir o passado -- so
# que sem avisar ninguem disso.
PROOF_KINDS = frozenset({"command", "artifact", "source", "historical"})
# Uma prova aponta para UM stream porque aceitar qualquer um dos dois deixa
# texto nao relacionado provar a alegacao: stdout com a contagem real errada
# e stderr com uma mensagem de erro que por acaso contem o numero esperado
# (ou vice-versa) passariam se `run_command_proofs` aceitasse "qualquer um
# dos dois" -- e "qualquer um dos dois" e o mesmo OR fabricado por outro
# nome que a concatenacao de streams ja era. `stdout` e o default por ser o
# canal normal de saida de um comando bem-sucedido.
STREAMS = frozenset({"stdout", "stderr"})


def rel(path: Path) -> str:
    """Caminho relativo à raiz, sempre com `/`, para o manifesto não mudar
    conforme o sistema operacional de quem rodou o `--seed`."""
    return path.resolve().relative_to(ROOT).as_posix()


def audited_docs(root: Path = VNEXT) -> list[Path]:
    # Fail-open deliberado: `adrs/` ausente ou renomeado devolve glob vazio,
    # nao erro -- um gate que degrada em silencio para de vigiar sem avisar.
    return sorted(root.glob("*.md")) + sorted((root / "adrs").glob("*.md"))


def audited_roots() -> tuple[Path, ...]:
    """A lista declarada, em UM so lugar, dos diretorios que o gate audita.

    Uma FUNCAO, nao uma tupla de modulo calculada uma unica vez na carga do
    arquivo: `collect_claims()` (abaixo) chama isto a cada execucao, e os
    testes usam `monkeypatch.setattr(gate, "VNEXT", tmp_path)` /
    `monkeypatch.setattr(gate, "HARNESS", tmp_path)` para isolar o corpo real
    do repositorio -- uma tupla congelada no import teria capturado os `Path`
    originais antes de qualquer monkeypatch rodar, e o teste continuaria
    varrendo o disco real por baixo do pano. Referenciar `VNEXT`/`HARNESS`
    dentro do corpo desta funcao resolve os dois nomes no NAMESPACE do modulo
    a cada chamada, entao o monkeypatch e visto.

    Adicionar um terceiro diretorio auditado no futuro e uma linha aqui, nao
    uma busca por todo lugar que hoje diz `VNEXT` ou `HARNESS` a mao.
    """
    return (VNEXT, HARNESS)


# Qualquer numero, com sinal de percentual opcional. O grupo so pode terminar
# em digito ou em `%` -- pontuacao de frase (`,` de enumeracao, `.` final)
# nunca entra no token, entao "3.5," na prosa vira "3.5", nao "3.5,". Contagem
# de um ou dois digitos (`8 coordenadores`, `38 agentes`) e a forma dominante
# de alegacao nestes documentos, e por isso nao tem piso de tamanho aqui --
# um numero que o extrator nao ve e uma alegacao que escapa da auditoria para
# sempre, o que pesa mais que o ruido de sobra-capturar. O lookahead descarta
# sozinho qualquer numero colado a letra depois dele. O lookbehind faz o
# mesmo trabalho para identificador (`ADR-003`) e data ISO (`2026-08-21`),
# mas NAO pode simplesmente proibir todo `-` antes do numero: achado ao ler a
# semente inteira (Task 8) -- `FINAL-REPORT.md` alega "**-81.8%** de
# economia" e esse token nunca virava candidato NENHUM com o lookbehind
# antigo (`(?<![\w.-])` bloqueando hifen incondicionalmente), o que apagava
# para sempre exatamente a alegacao que este gate mais precisa forcar a
# provar. A alternativa abaixo resolve as duas exigencias em conjunto: um
# numero comecando por `-` só entra na alegacao (grupo 2) quando esse `-` NAO
# esta colado a letra/digito/ponto -- ou seja, quando e sinal de negativo
# solto ("**-81.8%**", precedido por `*`), nao separador de identificador
# ("ADR-003", hifen colado a "R") nem de data ISO ("2026-08-21", hifen
# colado a digito). O ramo sem sinal (grupo 1) continua exatamente como
# antes, hifen incluido no bloqueio, para nao reabrir a porta que capturava
# "003" de dentro de "ADR-003" pela retomada do scan apos o hifen.
NUMBER_RE = re.compile(
    r"(?<![\w.-])(\d(?:[\d.,]*\d)?\s*%?)(?![\w-])"
    r"|(?<![\w.])(-\d(?:[\d.,]*\d)?\s*%?)(?![\w-])"
)

# Cada padrao ignorado carrega a razao. Allowlist sem razao registrada vira
# deposito de excecao conveniente, e ninguem consegue auditar depois por que
# um numero deixou de ser alegacao.
IGNORED_TOKENS = (
    (
        re.compile(r"^\d+\.\d+\.\d+$"),
        "versao semantica e fato de release, nao alegacao de resultado",
    ),
    (
        re.compile(r"^(19|20)\d{2}$"),
        "ano de quatro digitos e datacao; o custo conhecido e mascarar uma "
        "contagem que caia em 1900-2099, aceito por ser improvavel nestes documentos",
    ),
)

# Marcador de lista ordenada, numero de titulo Markdown, marca de fase e
# rotulo de indice de taxonomia sao ruido ESTRUTURAL: o numero indica
# POSICAO (o item e o terceiro da lista, a secao e a quarta do documento,
# o titulo pertence a "Phase 4" do roadmap, "Tier 3" e o quarto tier da
# cascata), nao um resultado medido. `IGNORED_TOKENS` nao serve aqui porque
# ele casa o TOKEN isolado ("3") sem enxergar onde na linha ele apareceu --
# um "3" de marcador de lista e um "3" de "3% de economia" sao o mesmo
# token. Cada padrao aqui casa um TRECHO da linha -- prefixo (marcador de
# lista, numero de titulo), sufixo (fase entre parenteses) ou qualquer
# posicao (rotulo de taxonomia, que pode aparecer em titulo, crase ou
# prosa) -- e SO esse trecho e trocado por espacos antes de `NUMBER_RE`
# varrer a linha em `extract_numbers`; o resto da linha continua auditado
# normalmente. Isso importa porque o mesmo texto que carrega o marcador com
# frequencia carrega uma alegacao real logo depois ("1. **Antigravity
# 2.0**: ..."): apagar a linha inteira apagaria "2.0" junto, e um numero
# que o extrator deixa de ver e uma alegacao que escapa da auditoria para
# sempre -- o custo errado do lado errado da assimetria que orienta esta
# tarefa. Ver o comentario de cada padrao abaixo para o que exatamente ele
# casa e por que.
IGNORED_LINES = (
    (
        re.compile(r"^\s*\d+\.\s"),
        "numero de marcador de lista ordenada indica a posicao do item na "
        "lista, nao e alegacao de resultado",
    ),
    (
        # Cobre tambem subsecao pontuada ("## 4.5 Subsecao", "## 4.5.2 Sub-
        # subsecao"): achado em revisao de codigo -- o padrao antigo
        # (`\d+\.` sozinho) so consumia "4." de "## 4.5 Subsecao" e deixava
        # ".5" para tras, vazando "5" como alegacao. Nenhum titulo com essa
        # forma existe hoje no corpus (conferido com grep), mas o padrao
        # precisa aguentar a numeracao aparecer no dia em que alguem
        # adicionar uma subsecao "N.M" -- o defeito e adormecido, nao
        # inexistente. `(?:\.\d+)*` consome zero ou mais segmentos extras
        # ("`.5`", "`.5.2`", ...) antes do `\.?` final opcional, que so
        # sobra para o caso simples de hoje ("## 4." -- um numero, um ponto).
        re.compile(r"^#{1,6}\s+\d+(?:\.\d+)*\.?"),
        "numero de secao em titulo Markdown (incluindo subsecao pontuada "
        "N.M) indica a posicao da secao no documento, nao e alegacao de "
        "resultado",
    ),
    (
        # Achado ao ler a semente inteira (Task 8): todo documento vNext abre
        # com um titulo H1 terminado em "(Phase N)" -- 9 ocorrencias, uma por
        # documento, sempre na linha 1. Revisao de codigo (mutation test):
        # a versao anterior deste padrao era `\((?:Phase|Fase)\s+\d+\)` sem
        # ancora nenhuma -- passava nos 115 testes mesmo removendo os
        # parenteses exigidos, o que prova que nada prendia o padrao ao
        # titulo que a razao alega. Sem ancora, "(Phase 3)" em QUALQUER
        # lugar do documento (nao so no titulo H1) apagaria um numero real em
        # silencio, para sempre -- a mesma classe de erro que o resto deste
        # arquivo existe para evitar. A versao abaixo casa a linha INTEIRA
        # (H1 unico, comeca com texto nao-vazio, termina no marcador de fase)
        # mas so MASCARA o grupo 1 (o parenteses em si) -- ver o uso de
        # `m.span(1)` no laco de `extract_numbers` -- entao um numero real no
        # resto do titulo ("# Catalogo com 38 agentes (Phase 4)") continua
        # visivel, exatamente como o marcador de lista e o numero de secao
        # acima.
        re.compile(r"^#\s+\S.*(\((?:Phase|Fase)\s+\d+\))\s*$"),
        "numero de fase do roadmap interno entre parenteses no titulo H1 do "
        "documento indica marco de entrega, nao alegacao de resultado",
    ),
    (
        # Achado pelo reviewer ao ler a semente inteira (Task 8, revisao):
        # rotulo de indice de taxonomia -- "Tier 3", "Layer 0", "Wave 2",
        # "Demo 5" -- e a mesma classe estrutural do marcador de lista e do
        # numero de titulo acima, so que o substantivo aparece ANTES do
        # numero em vez de a linha comecar com ele, entao nao tem posicao
        # fixa para ancorar (aparece em titulo `### Layer 0: ...`, em rotulo
        # entre crases `` `Tier 3` ``, e em prosa solta "(Layer 0)"). O eixo
        # que decide o que e alegacao e a ORDEM: substantivo-entao-digito e
        # rotulo (indica qual item, nao quantidade); digito-entao-substantivo-
        # no-plural ("7 Tiers", "3 niveis") e alegacao de quantidade e este
        # padrao NUNCA casa nesse sentido, porque exige o substantivo vir
        # PRIMEIRO. `\b` dos dois lados evita casar dentro de "Tiers" (plural)
        # ou de uma palavra maior que contenha "Tier"/"Wave" como substring.
        re.compile(r"\b(?:Tier|Layer|Wave|Demo)\s+\d+\b"),
        "rotulo de indice de taxonomia (Tier/Layer/Wave/Demo N) indica qual "
        "item da lista, nao e alegacao de quantidade -- \"N tiers\" (digito "
        "antes do substantivo) nao casa aqui e continua sendo alegacao",
    ),
    (
        # Achado ao trazer `docs/harness/CURRENT-HARNESS-GAP.md` para debaixo
        # do gate: o documento cita a secao de `prompt_evo_harness.md` que
        # cada componente cobre 72 vezes, formato "§NN" ("(§30)", "§43,
        # \"critico\"", "(§79) / ... (§31)"). E a MESMA classe estrutural do
        # rotulo de indice de taxonomia acima -- indica QUAL secao do
        # documento-fonte, nao uma quantidade medida deste repositorio --
        # so que aqui o simbolo vem ANTES do numero, entao precisa do proprio
        # padrao (o de Tier/Layer/Wave/Demo exige um substantivo ASCII antes
        # do digito, "§" nao casa `\b\w+\b`). Sem isto, cada referencia de
        # secao vira uma alegacao numerica que ninguem consegue "provar" --
        # nao ha comando que reproduza "a secao 30 do prompt existe". Zero
        # ocorrencias de "§" em `docs/vnext/*.md` (conferido com grep antes
        # de acrescentar este padrao), entao isto nao muda nenhuma das 184
        # alegacoes ja classificadas.
        re.compile(r"§\s*\d+"),
        "referencia a secao do documento-fonte (\"§NN\") indica qual secao "
        "de `prompt_evo_harness.md` o componente cobre, nao uma quantidade "
        "medida deste repositorio",
    ),
    (
        # Mesmo achado: `CURRENT-HARNESS-GAP.md` numera os 5 golden cases do
        # §48 como "Caso 1/2 (Glue 4.0->5.1...)", "caso 4 (Terraform...)",
        # "Caso 3 (Lake Formation...)", "Caso 5 (Spark performance...)" --
        # rotulo de indice, mesma classe estrutural de "Tier N" acima (o
        # substantivo "caso" vem ANTES do numero, indica QUAL caso, nao uma
        # quantidade). `[Cc]aso` cobre a forma capitalizada (inicio de frase)
        # e a minuscula (meio de frase, "e caso 4"); `(?:/\d+)?` cobre a forma
        # dupla "Caso 1/2" (dois casos citados juntos, um so rotulo composto)
        # sem deixar o "2" de "1/2" escapar como alegacao separada. Zero
        # ocorrencias de "aso \d" em `docs/vnext/*.md` (conferido com grep),
        # entao isto nao muda nenhuma das 184 alegacoes ja classificadas.
        re.compile(r"\b[Cc]aso\s+\d+(?:/\d+)?\b"),
        "rotulo de indice de golden case (\"Caso N\" ou \"Caso N/M\") indica "
        "qual caso dos 5 do §48, nao e alegacao de quantidade",
    ),
    (
        # Mesmo achado: "ver tabela 1" (auto-referencia cruzada dentro do
        # proprio documento) e "o nível 1 do §45" (rotulo ordinal de grader
        # hierarchy -- ha so UM nivel implementado hoje, mas o "1" aqui indica
        # QUAL nivel na hierarquia, nao "quantos" niveis existem). Mesma
        # classe estrutural de Tier/Layer/Wave/Demo/Caso: substantivo ANTES
        # do digito. Nao afeta a forma plural de quantidade real ("3 níveis",
        # ja provado para ContextManager) porque essa vem com o digito
        # primeiro. Uma ocorrencia de cada em todo o corpus (conferido com
        # busca por regex antes de acrescentar este padrao), so em
        # `CURRENT-HARNESS-GAP.md`.
        re.compile(r"\btabela\s+\d+\b|\bn[ií]vel\s+\d+\b", re.IGNORECASE),
        "\"tabela N\" e auto-referencia cruzada dentro do documento; "
        "\"nível N\" (singular) e rotulo ordinal de qual nivel da hierarquia "
        "-- nenhum dos dois e alegacao de quantidade",
    ),
)


def _display_path(path: Path) -> str:
    """Caminho para registrar no achado ou citar num erro. Documento real
    vive sob ROOT e usa o caminho relativo de `rel()` (estavel entre sistemas
    operacionais). Fora de ROOT -- caso pratico so em teste, que escreve o
    documento sintetico em `tmp_path` -- `rel()` explode, e cair para o
    caminho absoluto mantem a funcao utilizavel sem afrouxar o contrato de
    `rel()`, que continua exigindo caminho dentro do repositorio."""
    try:
        return rel(path)
    except ValueError:
        return path.resolve().as_posix()


def _strip_code_blocks(text: str, path: Path) -> str:
    """Zera o conteudo de bloco cercado. Numero dentro de exemplo de codigo e
    ilustracao; audita-lo produziria ruido sem nenhuma alegacao por tras."""
    out: list[str] = []
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    if fenced:
        # Cerca sem fechamento apagaria o resto do documento em silencio --
        # exatamente a falha de miss silencioso que este gate existe para
        # impedir. Estourar alto aqui, com o nome do arquivo, deixa alguem
        # achar e corrigir o Markdown quebrado em vez de o gate so parar de
        # ver alegacoes sem avisar ninguem.
        raise ValueError(f"bloco de codigo cercado nao fechado em {_display_path(path)}")
    return "\n".join(out)


def extract_numbers(path: Path) -> list[dict]:
    doc = _display_path(path)
    text = _strip_code_blocks(path.read_text(encoding="utf-8"), path)
    found: list[dict] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if "http" in line:
            # Citacao de fonte: o numero pertence ao endereco, nao ao
            # produto. Descarta a linha inteira -- se algum dia uma alegacao
            # real dividir linha com um link, ela some junto. Nenhum
            # documento atual faz isso; aceito ate acontecer de verdade.
            continue
        if line.strip().startswith("*Fontes:"):
            # Mesma razao do `http` acima, achado ao trazer `docs/harness/
            # CURRENT-HARNESS-GAP.md` para debaixo do gate: o rodape "*Fontes:
            # ...*" cita intervalo de linha e numero de secao de um documento
            # EXTERNO (`prompt_evo_harness.md`) -- os numeros pertencem a
            # citacao bibliografica, nao a um resultado medido deste
            # repositorio. Descarta a linha inteira, mesmo raciocinio do link:
            # se um dia uma alegacao real dividir linha com essa citacao, ela
            # some junto -- aceito ate acontecer de verdade. So um documento
            # usa este rodape hoje (conferido com grep antes de acrescentar
            # este padrao), entao isto nao muda nenhuma das 184 alegacoes ja
            # classificadas.
            continue
        # Mascara o TRECHO estrutural de cada `IGNORED_LINES` que casar
        # (marcador de lista, numero de titulo, "(Phase N)" de roadmap, ou
        # rotulo de taxonomia), trocando-o por espacos de mesmo comprimento
        # em vez de descartar a linha inteira -- o resto da linha (onde uma
        # alegacao real costuma morar, ex. "1. **Antigravity 2.0**: ...")
        # continua disponivel para `NUMBER_RE`. `search` (nao `match`) porque
        # nem todo padrao fica ancorado no inicio da linha -- rotulo de
        # taxonomia pode morar em qualquer lugar da linha, e o padrao de
        # "(Phase N)" precisa da linha INTEIRA para confirmar que e um
        # titulo H1 (ver comentario do padrao), mas so quer apagar o
        # parenteses. Por isso o span mascarado e `m.span(1)` quando o match
        # tem grupo de captura (o padrao pediu deliberadamente por um trecho
        # mais estreito que o match inteiro) e `m.span()` quando nao tem --
        # os outros padroes de hoje nao usam grupo, entao continuam mascarando
        # o match inteiro como antes. Aplicar TODOS os padroes que casarem
        # (sem `break` no primeiro) evita que um padrao futuro na mesma linha
        # fique mascarado so pela metade por causa de outro que casou
        # primeiro. `context` abaixo usa a `line` original, nao a mascarada:
        # quem le o achado precisa ver o texto real do documento, nao o
        # texto com espacos no lugar do marcador. O `while` interno mascara
        # TODAS as ocorrencias de um padrao na mesma linha, nao so a
        # primeira -- caso real do corpus: uma unica linha de tabela em
        # KNOWLEDGE-MAP.md encadeia "Tier 0 ... Tier 1 ... Tier 6"
        # sete vezes. Um `if` em vez de `while` mascararia so "Tier 0" e
        # deixaria "Tier 1" a "Tier 6" vazando como alegacao -- exatamente o
        # falso negativo que este arquivo existe para evitar. Cada iteracao
        # troca o trecho casado por espacos antes do proximo `search`, entao
        # o laco sempre progride e termina (nenhum padrao aqui casa string
        # vazia).
        scan_line = line
        for rx, _ in IGNORED_LINES:
            while True:
                m = rx.search(scan_line)
                if not m:
                    break
                start, end = m.span(1) if m.lastindex else m.span()
                scan_line = scan_line[:start] + " " * (end - start) + scan_line[end:]
        for match in NUMBER_RE.finditer(scan_line):
            # Grupo 1 casa quando o numero nao tem sinal; grupo 2, quando tem
            # `-` de negativo solto (ver comentario de `NUMBER_RE`). Os dois
            # ramos da alternativa sao mutuamente exclusivos por construcao
            # -- exatamente um dos dois grupos captura por match.
            token = (match.group(1) or match.group(2)).strip()
            if any(rx.match(token) for rx, _ in IGNORED_TOKENS):
                continue
            found.append(
                {
                    "doc": doc,
                    "line": lineno,
                    "text": token,
                    "context": line.strip()[:120],
                    "type": "number",
                }
            )
    return found


# Alegacao de capacidade sai de ESTRUTURA, nunca de prosa. Varrer prosa livre
# atras de "o sistema faz X" produz falso positivo demais para ser gate.
CAPABILITY_TABLES = ("CAPABILITY-MATRIX.md", "AGENT-CATALOG.md")


def _is_table_separator(stripped: str) -> bool:
    # Exige o "|" inicial explicitamente: sem isso, string vazia (linha em
    # branco) tambem bateria (conjunto vazio e subconjunto de qualquer
    # conjunto), e uma linha em branco depois de uma linha de tabela seria
    # lida como separador por acidente.
    return stripped.startswith("|") and set(stripped) <= set("|-: ")


def extract_capabilities(root: Path = VNEXT) -> list[dict]:
    found: list[dict] = []
    for name in CAPABILITY_TABLES:
        path = root / name
        if not path.exists():
            continue
        # Mesma cerca de `extract_numbers`: linha dentro de bloco cercado e
        # exemplo, nao alegacao. Sem isto, uma tabela ou lista ilustrativa
        # dentro de um bloco de codigo em AGENT-CATALOG.md ou FINAL-REPORT.md
        # (ambos ja tem blocos cercados hoje) vira alegacao real por acidente.
        lines = _strip_code_blocks(path.read_text(encoding="utf-8"), path).split("\n")
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped.startswith("|") or _is_table_separator(stripped):
                continue
            # Cabecalho de tabela GFM e definido por POSICAO, nao por
            # vocabulario: e a linha imediatamente seguida pela linha
            # separadora ("|---|---|"). Deteccao por posicao e exata e nao
            # envelhece; a lista de palavras-chave anterior ("Capacidade",
            # "Agent"...) vazava toda vez que uma tabela nova usava um
            # cabecalho diferente ("Servico AWS", "Coordinator"), como o
            # sanity check da Task 3 provou.
            # Tabela sem linha separadora (Markdown malformado) nao tem
            # ancora nenhuma linha nunca sera seguida por um separador, entao
            # nenhuma linha e descartada como cabecalho, nem mesmo a que
            # visualmente seria o cabecalho. Decisao deliberada: sem a linha
            # separadora nao ha como distinguir cabecalho de dado por
            # posicao, e tratar tudo como dado (falso positivo eventual) e
            # preferivel a inventar uma heuristica de vocabulario -- que e
            # exatamente o problema que esta reescrita elimina.
            proxima = lines[lineno].strip() if lineno < len(lines) else ""
            if _is_table_separator(proxima):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or not cells[0]:
                continue
            found.append(
                {
                    "doc": _display_path(path),
                    "line": lineno,
                    "text": cells[0],
                    "context": stripped[:120],
                    "type": "capability",
                }
            )
    found.extend(_final_report_inventory(root))
    found.extend(_harness_gap_capabilities(root))
    return found


def _final_report_inventory(root: Path = VNEXT) -> list[dict]:
    """Item de lista dentro da secao "## 4." do FINAL-REPORT (inventario de
    pacotes, modulos e documentos entregues) tambem e alegacao de capacidade:
    cada linha afirma que algo especifico foi criado. A deteccao usa o
    prefixo "4." do titulo, nao o texto inteiro do titulo -- sobrevive a
    renomeacao da secao ("Inventario..." virar outra coisa) desde que a
    numeracao continue "## 4.".

    Documento ausente (`FINAL-REPORT.md` nao existe) e tratado como lista
    vazia sem erro -- e o caso pratico de qualquer fixture sintetica em
    `tmp_path`, e ausencia do documento inteiro nao e a mesma falha que
    ancora perdida dentro dele. Mas se o arquivo existe e a ancora "## 4."
    NAO e encontrada -- secao renumerada, prefixo mudado -- isso e estourado
    como ValueError, nao devolvido como lista vazia: um gate que perde o
    proprio ponto de entrada e degrada em silencio nao vale nada, e este gate
    existe exatamente para impedir que uma alegacao suma sem barulho. Pela
    mesma razao, ancora encontrada mas ZERO itens coletados tambem estoura:
    a lista so reconhece marcador "- ", entao uma secao 4 reescrita com lista
    numerada ("1. ", "2. ") passa pela deteccao de ancora sem erro e devolve
    lista vazia -- exatamente o miss silencioso que este gate existe para
    impedir.

    `text` guarda a linha do item inteira (sem o marcador "- "), com path e
    descricao juntos: e a chave que o manifesto casa, e qualquer
    reformatacao do inventario (novo caminho, nova descricao) precisa
    re-registrar a alegacao -- aceitar so o path deixaria a descricao mudar
    sem o gate perceber.
    """
    path = root / "FINAL-REPORT.md"
    if not path.exists():
        return []
    found: list[dict] = []
    in_section = False
    anchor_found = False
    text = _strip_code_blocks(path.read_text(encoding="utf-8"), path)
    for lineno, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped[3:].lstrip().startswith("4.")
            anchor_found = anchor_found or in_section
            continue
        if not in_section:
            continue
        if stripped.startswith("- "):
            item_text = stripped[2:].strip()
            if not item_text:
                continue
            found.append(
                {
                    "doc": _display_path(path),
                    "line": lineno,
                    "text": item_text,
                    "context": stripped[:120],
                    "type": "capability",
                }
            )
    if not anchor_found:
        raise ValueError(
            f"ancora de inventario '## 4.' nao encontrada em {_display_path(path)}"
        )
    if not found:
        raise ValueError(
            f"secao '## 4.' encontrada em {_display_path(path)} mas nenhum item de "
            "lista foi coletado -- ou os marcadores de lista mudaram de forma (o "
            "extrator so reconhece '- ') e precisa aprender o novo formato, ou a "
            "secao foi esvaziada de proposito e a expectativa de ancora neste "
            "script precisa ser atualizada deliberadamente"
        )
    return found


def gap_documents(root: Path = HARNESS) -> tuple[Path, ...]:
    """Os mapas de lacuna auditados, declarados em UM so lugar.

    Um mapa de lacuna e um documento de tabela `Componente | Classificacao |
    Modulo(s) | Teste` que responde "isto ja existe aqui?" componente a
    componente -- `CURRENT-HARNESS-GAP.md` foi o primeiro, `GLUE6-GAP.md` o
    segundo, e o padrao se repete a cada prompt grande que chega. Casar por
    sufixo `-GAP.md` em vez de listar nomes a mao existe pela mesma razao de
    `audited_roots()`: lista escrita a mao envelhece calada, e um mapa novo
    que o extrator nao ve e um documento inteiro de alegacoes fora da
    auditoria.

    Renomear um mapa para fora do padrao NAO passa despercebido: as entradas
    dele viram orfas no manifesto e o gate reprova por esse lado, que e
    fail-closed. Ordenado para que a numeracao de id ficar estavel entre
    execucoes nao dependa da ordem do sistema de arquivos.
    """
    if not root.is_dir():
        return ()
    return tuple(sorted(root.glob("*-GAP.md")))


def _harness_gap_capabilities(root: Path = HARNESS) -> list[dict]:
    """Linha de tabela de mapa de lacuna cuja Classificacao comeca em
    "EXISTE" vira alegacao de capacidade. Nenhum mapa presente (fixture
    sintetica, ou root=VNEXT onde eles nao moram) devolve lista vazia,
    mesmo padrao de `_final_report_inventory`.

    Por que isto NAO pode reusar o mecanismo generico de `CAPABILITY_TABLES`
    (que so olha `cells[0]`, a primeira coluna): a tabela deste documento tem
    4 colunas -- Componente | Classificacao | Modulo(s) | Teste -- e ela
    documenta DELIBERADAMENTE tanto o que existe quanto o que NAO existe no
    mesmo formato de linha ("RecoveryEngine | NAO EXISTE | ...", ao lado de
    "TaskSpec | EXISTE, com teste | ..."). O mecanismo generico so olha
    `cells[0]` (o nome do componente) e ignora a classificacao -- se este
    arquivo fosse simplesmente somado a `CAPABILITY_TABLES`, TODA linha viraria
    alegacao de capacidade, inclusive "RecoveryEngine", que o proprio
    documento afirma nao existir. Isso e o oposto do que uma alegacao de
    capacidade deveria significar, e pior: marcar essa entrada como REMOVIDA
    no manifesto derrubaria o gate na hora, porque o texto CONTINUA presente
    no documento (REMOVIDA e para texto apagado, nao para texto que descreve
    uma ausencia). A linha so vira alegacao quando `cells[1]` comeca com
    "EXISTE" -- "EXISTE PARCIAL", "EXISTE, com teste — duplicado" contam;
    "NAO EXISTE" e "NAO EXISTE, para o proposito pedido" nao.

    Confirmado por leitura de `docs/harness/CURRENT-HARNESS-GAP.md` (Task de
    extensao do gate): 31 linhas de dado no total, 24 comecando em "EXISTE" e
    7 em "NAO EXISTE" -- as 7 ficam de fora aqui de proposito.

    Varre todo mapa devolvido por `gap_documents()`, nao um nome fixo: ver o
    raciocinio la.
    """
    found: list[dict] = []
    for path in gap_documents(root):
        found.extend(_gap_capabilities_of(path))
    return found


def _gap_capabilities_of(path: Path) -> list[dict]:
    """Le UM mapa de lacuna. Separado de `_harness_gap_capabilities` para que
    o erro de ancora perdida (abaixo) nomeie o arquivo exato, e nao o
    conjunto."""
    found: list[dict] = []
    linhas_de_dado = 0
    lines = _strip_code_blocks(path.read_text(encoding="utf-8"), path).split("\n")
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or _is_table_separator(stripped):
            continue
        proxima = lines[lineno].strip() if lineno < len(lines) else ""
        if _is_table_separator(proxima):
            continue  # cabecalho de tabela (mesma deteccao por posicao do mecanismo generico)
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        linhas_de_dado += 1
        classificacao = cells[1] if len(cells) > 1 else ""
        if not classificacao.startswith("EXISTE"):
            continue
        found.append(
            {
                "doc": _display_path(path),
                "line": lineno,
                "text": cells[0],
                "context": stripped[:120],
                "type": "capability",
            }
        )
    if linhas_de_dado == 0:
        # Arquivo existe mas nenhuma linha de tabela foi reconhecida -- a
        # ancora estrutural (tabela GFM com cabecalho+separador) sumiu ou
        # mudou de forma. Mesmo raciocinio de `_final_report_inventory`:
        # perder o proprio ponto de entrada em silencio e pior que estourar.
        raise ValueError(
            f"nenhuma linha de tabela reconhecida em {_display_path(path)} -- "
            "a estrutura de tabela GFM (Componente | Classificacao | Modulo(s) | "
            "Teste) mudou, ou o arquivo foi esvaziado de proposito e este "
            "extrator precisa ser atualizado deliberadamente"
        )
    return found


ID_RE = re.compile(r"^VNX-\d{3}$")

# Formatos de `expect` aceitos por uma prova `command`. "contains" e o caso
# simples (substring no stdout); "number" exige `pattern` com grupo de
# captura porque comparar numero exige extrair o numero do stdout antes de
# comparar -- sem grupo de captura nao ha o que comparar.
EXPECT_KINDS = frozenset({"number", "contains"})


def validate_manifest(manifest: dict, sources: dict) -> list[str]:
    """Valida a forma do manifesto e, para cada `claim`, a prova tipada.

    `sources` e o conteudo ja carregado de `knowledge/sources.lock.json`
    (chaveado por URL) -- passado pelo chamador em vez de lido aqui para a
    funcao ficar testavel sem tocar disco real em todo teste.
    """
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version deve ser {SCHEMA_VERSION}, veio {manifest.get('schema_version')!r}"
        )
    seen: set[str] = set()
    for entry in manifest.get("claims", []):
        cid = entry.get("id", "<sem id>")
        if not ID_RE.match(str(cid)):
            errors.append(f"{cid}: id fora do formato VNX-NNN")
        if cid in seen:
            errors.append(f"{cid}: id repetido")
        seen.add(cid)
        if entry.get("type") not in TYPES:
            errors.append(f"{cid}: type desconhecido: {entry.get('type')!r}")
        state = entry.get("state")
        if state not in STATES:
            errors.append(f"{cid}: state desconhecido: {state!r}")
            continue
        if state == "PROVADA":
            errors.extend(_validate_proof(entry, sources))
        else:
            if not entry.get("note"):
                errors.append(f"{cid}: state {state} exige note com o motivo")
            if entry.get("proof"):
                errors.append(f"{cid}: proof so e aceita em PROVADA")
    return errors


def _validate_path_field(cid: str, field_name: str, value: str) -> tuple[list[str], Path | None]:
    """Resolve um campo de caminho de `proof` (`path` ou `test`) sob ROOT e
    devolve (erros, caminho resolvido ou None).

    Tres formas de falha, cada uma com mensagem propria porque cada uma
    aponta para um conserto diferente:
    - campo AUSENTE (string vazia ou chave faltando): quem escreveu o
      manifesto esqueceu de preencher.
    - campo FORA DO REPOSITORIO: `ROOT / valor` descarta ROOT quando `valor`
      e absoluto (comportamento documentado do operador `/` do pathlib), e
      `../` sobe da raiz -- as duas formas fariam o manifesto apontar para
      fora do repositorio sem erro nenhum se so checassemos existencia. O
      manifesto e editado a mao e a Task 7 vai EXECUTAR `cmd` do mesmo
      arquivo, entao um typo de barra inicial muda de sentido em silencio, e
      de forma diferente entre workstation Windows e CI Linux -- por isso
      esta checagem roda ANTES da checagem de existencia, nao depois.
    - campo aponta para dentro do repositorio mas o arquivo nao existe la:
      erro de digitacao no caminho, nao de escopo.
    """
    if not value:
        return [f"{cid}: proof.{field_name} ausente"], None
    candidate = (ROOT / value).resolve()
    if not candidate.is_relative_to(ROOT):
        return [f"{cid}: proof.{field_name} fora do repositorio: {value!r}"], None
    if not candidate.exists():
        return [f"{cid}: proof.{field_name} inexistente: {value!r}"], None
    return [], candidate


def _commit_exists(commit: str) -> bool:
    """`True` quando `commit` resolve a um objeto commit git de verdade neste
    repositorio -- a unica checagem que uma prova `historical` faz sobre o
    commit que ela cita. `git cat-file -t <sha>` devolve o tipo do objeto
    (`commit`, `blob`, `tree`, `tag`) quando o objeto existe, e sai com
    codigo diferente de zero (sem imprimir tipo nenhum) quando nao existe --
    aceita SHA completo ou abreviado, exatamente como o resto do git.

    Falha de processo (git ausente, timeout, nao e repositorio) NAO deve
    travar toda a validacao do manifesto com uma excecao crua: devolve
    `False`, o mesmo resultado pratico de "commit nao confirmado", e
    `_validate_proof` reporta isso como divergencia legivel apontando o id,
    igual a qualquer outro erro de manifesto."""
    try:
        completed = subprocess.run(  # noqa: S603 -- argv fixo, sem shell
            ["git", "cat-file", "-t", commit],  # noqa: S607 -- git resolvido pelo PATH
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and completed.stdout.strip() == "commit"


def _validate_proof(entry: dict, sources: dict) -> list[str]:
    """Valida a prova de uma entrada PROVADA, tipada por `proof.kind`.

    Duas restricoes cruzam type x kind, e nenhuma das duas e negociavel:

    - `artifact` NUNCA prova `type: number`. Um artefato so mostra que codigo
      ou teste existe, nao que um numero especifico ("94,5% de acerto") saiu
      dele. Sem esta regra o manifesto aceitaria "veja o arquivo" no lugar de
      uma medicao de verdade, e a alegacao numerica ficaria de fato sem
      lastro atras de uma prova que parece valida.
    - `type: external_fact` SO aceita `source`. Versao de servico ou feature
      de spec e fato de terceiro -- so se prova citando a documentacao
      oficial versionada que este repositorio ja rastreia em
      `knowledge/sources.lock.json`. Comando ou artefato local nao alcança
      fato que vive fora do repositorio.
    """
    cid = entry.get("id", "<sem id>")
    proof = entry.get("proof")
    if not isinstance(proof, dict):
        return [f"{cid}: PROVADA sem proof"]
    kind = proof.get("kind")
    if kind not in PROOF_KINDS:
        return [f"{cid}: proof.kind desconhecido: {kind!r}"]

    errors: list[str] = []
    claim_type = entry.get("type")
    if claim_type == "external_fact" and kind != "source":
        errors.append(f"{cid}: external_fact exige proof source")

    if kind == "artifact":
        if claim_type == "number":
            errors.append(f"{cid}: proof artifact nao prova alegacao numerica")
        path_errors, _ = _validate_path_field(cid, "path", proof.get("path", ""))
        errors.extend(path_errors)
        test_errors, test_path = _validate_path_field(cid, "test", proof.get("test", ""))
        errors.extend(test_errors)
        if test_path is not None and proof.get("symbol"):
            symbol = proof["symbol"]
            texto_teste = test_path.read_text(encoding="utf-8")
            # Substring nua bate em qualquer lugar do arquivo, inclusive
            # dentro do literal de string de outro `proof["symbol"]` escrito
            # no proprio arquivo de teste -- caso real encontrado ao rodar
            # esta suite: o nome do simbolo negativo do teste de regressao
            # aparecia, sem chamada nenhuma, dentro do proprio arquivo que a
            # checagem le, e a checagem aceitava isso como referencia valida.
            # Exigir forma de chamada (`simbolo(`, `alias.simbolo(` ou
            # `mod.alias.simbolo(`) elimina esse falso positivo sem custar
            # precisao real: o proposito e confirmar que o teste EXERCITA o
            # simbolo, nao so o menciona. O prefixo qualificador e generico
            # (nao trava em `gate.`) porque a Task 9 vai anexar prova
            # `artifact` para dezenas de alegacoes de capacidade contra
            # modulos arbitrarios, cujos testes importam do jeito que
            # importam -- travar no alias deste arquivo quebraria todo
            # simbolo importado sob outro nome.
            referenciado = re.search(
                rf"(?:[\w.]+\.)?{re.escape(symbol)}\s*\(", texto_teste
            )
            if not referenciado:
                errors.append(f"{cid}: proof.test nao referencia {symbol}")
    elif kind == "source":
        if proof.get("source_id") not in sources:
            errors.append(
                f"{cid}: source_id fora de knowledge/sources.lock.json: "
                f"{proof.get('source_id')!r}"
            )
    elif kind == "historical":
        # Medicao ancorada num commit PASSADO -- NAO reexecutada. Ver o
        # comentario de `PROOF_KINDS` no topo do arquivo para o porque: um
        # baseline ("5786 testes, medido no commit X") envelhece por
        # natureza, e comparar o comando contra o HEAD de hoje reprovaria o
        # baseline pelo unico motivo de o tempo ter passado -- exatamente o
        # oposto do que um baseline serve para registrar. Duas exigencias, as
        # duas obrigatorias, e nenhuma delas reexecuta nada: `cmd` documenta
        # COMO o numero foi medido (para alguem reproduzir, fazendo
        # `git checkout` do commit certo, nao rodando no HEAD de hoje) e
        # `commit` ancora QUANDO. Sem os dois, "medido uma vez, confie" e
        # indistinguivel do numero fantasioso que a auditoria de onze tarefas
        # (`docs/claims.lock.json`) removeu.
        cmd = proof.get("cmd")
        if not cmd:
            errors.append(f"{cid}: proof historical sem cmd")
        elif "\\" in cmd:
            # Mesma razao do ramo `command` abaixo: `shlex.split` nunca roda
            # sobre uma prova `historical` (ela nao e reexecutada), mas o
            # `cmd` ainda serve de RECEITA para quem for reproduzir a mao --
            # uma barra invertida digitada nesta workstation Windows
            # continua sendo o erro tipico, e vale barrar aqui pela mesma
            # razao pratica, nao so por simetria.
            errors.append(
                f"{cid}: proof.cmd contem '\\\\' -- use barra normal '/' (funciona em "
                "Windows e Linux); shlex.split trata '\\\\' como escape POSIX e corrompe o caminho"
            )
        commit = proof.get("commit")
        if not commit:
            errors.append(f"{cid}: proof historical sem commit")
        elif not _commit_exists(commit):
            errors.append(
                f"{cid}: proof.commit {commit!r} nao existe neste repositorio "
                "('git cat-file -t' nao devolveu 'commit') -- um baseline que cita um "
                "commit que ninguem consegue conferir nao e reproduzivel nem em "
                "principio, que e a unica garantia que este proof.kind oferece"
            )
    else:
        cmd = proof.get("cmd")
        if not cmd:
            errors.append(f"{cid}: proof command sem cmd")
        elif "\\" in cmd:
            # `shlex.split` interpreta `\` como escape POSIX em qualquer
            # sistema operacional -- inclusive nesta workstation Windows,
            # onde `cmd` do manifesto e digitado a mao (Task 9). Ele quebra
            # alto, sem shell nenhum de por meio: `shlex.split(r"python
            # scripts\check.py")` vira `['python', 'scriptscheck.py']`, e a
            # barra some em silencio sem lancar excecao aqui. Barra normal
            # `/` funciona igual em Windows e Linux, entao rejeitar aqui,
            # na validacao do manifesto, poupa quem escreve `cmd` de
            # descobrir isso so quando a Task 7 tenta executar.
            errors.append(
                f"{cid}: proof.cmd contem '\\\\' -- use barra normal '/' (funciona em "
                "Windows e Linux); shlex.split trata '\\\\' como escape POSIX e corrompe o caminho"
            )
        if proof.get("tier") not in TIERS:
            errors.append(f"{cid}: proof.tier deve ser fast ou slow, veio {proof.get('tier')!r}")
        expect = proof.get("expect") or {}
        expect_kind = expect.get("kind")
        if expect_kind not in EXPECT_KINDS:
            errors.append(f"{cid}: expect.kind deve ser number ou contains")
        elif expect_kind == "number":
            # `pattern` truthy nao basta: a Task 7 vai compilar este regex e
            # extrair o grupo 1 do stdout do comando. Um regex sem grupo de
            # captura ou com sintaxe invalida passaria na checagem antiga e
            # so explodiria na hora de rodar -- tarde demais para um erro que
            # a validacao do manifesto deveria ter pego. Compilar aqui, com
            # `try`, transforma "regex invalido" num erro de manifesto
            # (mensagem clara, apontando o id) em vez de uma excecao de
            # execucao sem contexto nenhum la na frente.
            pattern = expect.get("pattern")
            if not pattern:
                errors.append(f"{cid}: expect number exige pattern com um grupo de captura")
            else:
                try:
                    compiled = re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{cid}: expect.pattern invalido: {exc}")
                else:
                    if compiled.groups < 1:
                        errors.append(
                            f"{cid}: expect number exige pattern com um grupo de captura"
                        )
        elif expect_kind == "contains" and not expect.get("value"):
            # Mesmo raciocinio do lado "number": sem `value` nao ha o que
            # procurar no stdout, e a Task 7 receberia uma prova que nao da
            # para executar.
            errors.append(f"{cid}: expect contains exige value")
        stream = expect.get("stream", "stdout")
        if stream not in STREAMS:
            # Mesmo estilo de `tier` e `expect.kind`: valor fora do
            # vocabulario aceito e erro de manifesto, apontando o id, em vez
            # de silenciosamente virar `None` e a Task 7 decidir algo por
            # conta propria na hora de executar.
            errors.append(f"{cid}: expect.stream deve ser stdout ou stderr, veio {stream!r}")
    return errors


def collect_claims(root: Path | None = None) -> list[dict]:
    """Todas as alegacoes numericas de todo documento auditado, mais toda
    alegacao de capacidade, numa unica lista -- a entrada que `check_orphans`
    compara contra o manifesto.

    `root=None` (o default real, usado por `seed()` e `audit()`) audita TODOS
    os diretorios de `audited_roots()` -- hoje `docs/vnext/` e
    `docs/harness/`. Passar um `root` explicito (usado pela suite inteira de
    testes sinteticos, e por quem quiser auditar um unico diretorio de
    proposito) restringe a coleta a esse UNICO diretorio, exatamente como o
    comportamento anterior -- nao muda o contrato para quem ja chama esta
    funcao com um `Path` fixo.
    """
    roots: tuple[Path, ...] = (root,) if root is not None else audited_roots()
    found: list[dict] = []
    for r in roots:
        for path in audited_docs(r):
            found.extend(extract_numbers(path))
        found.extend(extract_capabilities(r))
    return found


def claim_key(entry: dict) -> tuple[str, str, str]:
    """A chave ignora `line` de proposito: editar prosa nao deve quebrar o
    gate, mas mover uma alegacao de documento deve."""
    return (entry["doc"], entry["type"], entry["text"])


def check_orphans(found: list[dict], manifest: dict) -> list[str]:
    """Fail-closed nos dois sentidos: alegacao no documento sem entrada no
    manifesto E entrada no manifesto sem alegacao no documento sao ambos
    erro -- e a garantia central deste gate (ver `tests/test_docs_
    coverage.py` para o defeito irmao que esta checagem existe para evitar).

    Comparacao por multiset (`Counter`): a mesma alegacao aparecendo duas
    vezes no mesmo documento exige duas entradas no manifesto.

    `state: REMOVIDA` sai da segunda checagem -- o proposito da entrada e
    justamente registrar que o texto foi apagado do documento. Mas se uma
    alegacao REMOVIDA REAPARECER no documento, isso e erro proprio, com
    mensagem propria, porque o manifesto estava desatualizado sobre o estado
    real do texto.
    """
    claims = manifest.get("claims", [])

    # Guarda `line` por chave, do lado documento e do lado manifesto -- nao
    # so a contagem. Task 9 classifica estas mensagens a mao contra o corpus
    # real (184 entradas, 166 chaves distintas, 18 colidindo): reportar so
    # `{doc} :: {text}` sem a linha deixa ate colisao DISTINGUIVEL por linha
    # indistinguivel na mensagem, e quem le precisa grepar o documento para
    # decodificar o que o gate ja sabia.
    doc_lines: dict[tuple[str, str, str], list[int]] = {}
    for item in found:
        doc_lines.setdefault(claim_key(item), []).append(item.get("line"))
    manifest_lines: dict[tuple[str, str, str], list[int]] = {}
    for c in claims:
        if c.get("state") != "REMOVIDA":
            manifest_lines.setdefault(claim_key(c), []).append(c.get("line"))
    removed = {claim_key(c) for c in claims if c.get("state") == "REMOVIDA"}

    in_docs = Counter({key: len(lines) for key, lines in doc_lines.items()})
    in_manifest = Counter({key: len(lines) for key, lines in manifest_lines.items()})

    errors: list[str] = []
    for key, count in (in_docs - in_manifest).items():
        linhas = ", ".join(str(n) for n in doc_lines[key])
        if key in removed:
            errors.append(
                f"alegacao marcada REMOVIDA ainda aparece no documento ({count}x): "
                f"{key[0]} :: {key[2]} (linhas: {linhas})"
            )
        else:
            errors.append(
                f"alegacao sem entrada no manifesto ({count}x): {key[0]} :: {key[2]} "
                f"(linhas: {linhas})"
            )
    for key, count in (in_manifest - in_docs).items():
        linhas = ", ".join(str(n) for n in manifest_lines[key])
        errors.append(
            f"entrada orfa no manifesto ({count}x): {key[0]} :: {key[2]} (linhas: {linhas})"
        )
    return errors


# Timeout por tier, nao um valor fixo para as duas: uma prova `fast` que
# trava bloquearia o gate por ate quinze minutos se usasse o mesmo teto de
# uma prova `slow` (que existe justamente para comando caro/demorado).
# `fast` e o tier default do dia a dia -- travar o gate inteiro por um
# comando que deveria ser rapido e um sintoma (comando errado, ambiente
# quebrado) que precisa aparecer rapido, nao em quinze minutos.
_TIMEOUT_BY_TIER = {"fast": 60, "slow": 900}


def _check_expect(output: str, expect: dict) -> tuple[bool, str]:
    """Confere UM stream isolado (stdout OU stderr, nunca os dois juntos)
    contra `expect`. Devolve (passou, motivo) -- motivo so e usado pelo
    chamador quando `passou` e False.

    Concatenar `stdout + stderr` antes de conferir fabrica casamento que
    nenhum dos dois streams produziu sozinho: stdout `"4"` + stderr
    `"1 tools"` concatenados formam `"41 tools"`, que bate com o padrao
    `(\\d+) tools` valor 41 mesmo sem nenhum stream ter escrito "41 tools"
    de verdade. Cada stream precisa satisfazer `expect` sozinho para a
    alegacao contar como provada.
    """
    if expect.get("kind") == "contains":
        value = expect.get("value")
        if value not in output:
            return False, f"saida nao contem {value!r}"
        return True, ""
    match = re.search(expect.get("pattern", ""), output)
    if not match:
        return False, f"padrao {expect.get('pattern')!r} nao casou na saida"
    # O grupo capturado pode nao ser inteiro (padrao mal escrito) ou o regex
    # pode ter casado sem grupo nenhum participar (grupo opcional que nao
    # bateu) -- `_validate_proof` so garante que o padrao COMPILA e tem ao
    # menos um grupo, nao que o grupo sempre captura digito. Sem esta
    # guarda, um manifesto com padrao ruim faria o gate explodir com
    # traceback cru em vez de reportar um erro de auditoria legivel.
    try:
        obtained = int(match.group(1))
    except (ValueError, IndexError) as exc:
        return False, f"grupo capturado por expect.pattern nao e inteiro: {exc}"
    expected = expect.get("value")
    if obtained != expected:
        return False, f"prova command nao reproduz — esperado {expected}, obtido {obtained}"
    return True, ""


def run_command_proofs(manifest: dict, include_slow: bool) -> list[str]:
    """Executa toda prova `command` do manifesto e compara a saida contra
    `expect`.

    `shlex.split` em vez de `shell=True` e deliberado: os comandos vem de um
    arquivo versionado e revisado, mas entregar uma string para um shell e
    uma superficie de execucao livre, e nenhuma prova legitima precisa de
    pipe, redirecionamento ou expansao de shell -- `shlex.split` reduz o
    comando a uma lista de argumentos executada diretamente, sem shell no
    meio.
    """
    errors: list[str] = []
    for entry in manifest.get("claims", []):
        proof = entry.get("proof") or {}
        if proof.get("kind") != "command":
            continue
        if proof.get("tier") == "slow" and not include_slow:
            continue
        cid = entry.get("id", "<sem id>")
        timeout = _TIMEOUT_BY_TIER.get(proof.get("tier"), 900)
        try:
            completed = subprocess.run(  # noqa: S603 -- argv de shlex.split, sem shell
                shlex.split(proof["cmd"]),
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{cid}: prova command nao executou: {exc}")
            continue
        # `completed.returncode` NAO vira gate de pass/fail aqui, de proposito:
        # `python -m pytest --collect-only -q` (candidato real a prova command
        # neste repositorio) sai com codigo diferente de zero em varios cenarios
        # de colecao parcial mesmo imprimindo a contagem correta -- travar em
        # returncode == 0 rejeitaria provas legitimas. A defesa contra "comando
        # crashou e por acaso imprimiu o texto esperado" vem de `expect`
        # exigir substring exata ou numero extraido por regex com grupo de
        # captura, DE UM SO stream, o que `expect.stream` declara.
        expect = proof.get("expect") or {}
        # A prova aponta para UM stream, nunca "qualquer um dos dois": aceitar
        # o primeiro que bater deixa texto nao relacionado no stream errado
        # provar a alegacao -- caso real encontrado: stdout com a contagem
        # real (errada) e stderr com uma mensagem de erro que por acaso
        # contem o numero esperado, ou vice-versa, passariam se qualquer
        # stream servisse. `stdout` e o default quando `expect.stream` esta
        # ausente -- `_validate_proof` ja rejeita qualquer valor fora de
        # `STREAMS`, entao aqui so os dois valores validos chegam.
        stream_name = expect.get("stream", "stdout")
        stream_output = completed.stderr if stream_name == "stderr" else completed.stdout
        ok, motivo = _check_expect(stream_output, expect)
        if not ok:
            errors.append(f"{cid}: prova command nao reproduz em {stream_name} -- {motivo}")
    return errors


def _head_commit() -> str:
    """SHA do commit atual, registrado em `extracted_from` para o manifesto
    saber de qual estado do repositorio ele foi seedado. Falha de git (nao e
    repositorio, `git` ausente, timeout) nao pode derrubar `--seed` -- o
    manifesto ainda e util sem essa proveniencia -- mas cair para
    `"desconhecido"` em silencio esconderia do operador que a proveniencia
    do manifesto ficou incompleta, entao o aviso vai pro stderr toda vez que
    o fallback dispara."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607 -- "git" fixo, sem entrada externa
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(
            f"aviso: nao foi possivel rodar 'git rev-parse HEAD' ({exc}) -- "
            "extracted_from sera 'desconhecido'",
            file=sys.stderr,
        )
        return "desconhecido"
    sha = completed.stdout.strip()
    if not sha:
        print(
            "aviso: 'git rev-parse HEAD' nao devolveu commit (codigo "
            f"{completed.returncode}, stderr {completed.stderr.strip()!r}) -- "
            "extracted_from sera 'desconhecido'",
            file=sys.stderr,
        )
        return "desconhecido"
    return sha


def load_manifest(path: Path | None = None) -> dict:
    return json.loads((path or MANIFEST).read_text(encoding="utf-8"))


def _load_sources() -> dict:
    return json.loads(SOURCES_LOCK.read_text(encoding="utf-8"))["sources"]


def _next_free_id(existing_claims: list[dict]) -> int:
    """Maior numero `VNX-NNN` ja emitido no manifesto anterior, mais um.
    Nunca reaproveita um numero que ja apareceu -- inclusive o de uma
    alegacao que sumiu do documento e ficou retida por `seed` (ela continua
    na lista de claims, entao seu id continua contando aqui)."""
    maior = 0
    for entry in existing_claims:
        cid = str(entry.get("id", ""))
        if ID_RE.match(cid):
            maior = max(maior, int(cid[4:]))
    return maior + 1


def seed(force: bool = False) -> int:
    """Gera ou funde o manifesto a partir de `collect_claims`.

    Modo padrao (merge, `force=False`): cada alegacao recem-extraida e
    casada contra o manifesto existente por `claim_key` -- a mesma chave
    `(doc, type, text)` que `check_orphans` ja usa para comparar os dois
    lados. Quando casa, `id`, `state`, `note` e `proof` da entrada antiga
    sao preservados sem alteracao nenhuma; so os campos posicionais
    (`line`, `context`) sao atualizados para refletir onde o texto esta
    agora. Quando nao casa, e uma alegacao nova: recebe o proximo id livre
    (`_next_free_id`), um acima do maior `VNX-NNN` ja emitido -- nunca
    reaproveitando um numero. Isso torna `--seed` idempotente e nao
    destrutivo por padrao: editar uma alegacao no topo de um documento nao
    desloca mais o id de nenhuma outra (a numeracao antiga era posicional e
    deslocava todo mundo abaixo do ponto editado), e classificar 184
    entradas a mao (Task 9) sobrevive a um reseed de rotina como o que a
    Task 8 exige depois de mudar o allowlist.

    Chave duplicada -- a mesma `claim_key` aparecendo mais de uma vez, caso
    real deste corpus (18 chaves cobrindo 36 entradas) -- e casada por
    ORDEM E CONTAGEM: mantem-se uma fila FIFO por chave com as entradas
    antigas na ordem em que aparecem no manifesto, e a N-esima ocorrencia da
    chave na extracao fresca (na ordem de `collect_claims`, que e estavel:
    documento por documento, linha por linha) casa com a N-esima da fila.
    Extracao com mais ocorrencias que o manifesto tinha: o excedente vira
    alegacao nova (id novo). Extracao com menos: a sobra do lado do
    manifesto e alegacao que sumiu do documento (proximo paragrafo). Nao ha
    como distinguir por conteudo QUAL ocorrencia e qual quando o texto e
    identico -- ordem estavel dos dois lados e o unico criterio disponivel,
    e e determinista.

    Entrada do manifesto que nao casou com nenhuma ocorrencia fresca (a
    alegacao sumiu do documento, ou o texto mudou o suficiente para mudar a
    chave) NAO e descartada: fica retida no manifesto, com `id`/`state`/
    `note`/`proof` intocados. Descartar em silencio destruiria classificacao
    humana (Task 9) por uma edicao de texto que pode nem ter sido
    intencional -- exatamente o evento que este gate existe para notar, nao
    para apagar. Reter e suficiente para o proximo `audit` reportar
    "entrada orfa no manifesto" via `check_orphans` (mecanismo que ja existe
    e ja e testado); este `seed` tambem imprime a contagem na hora, para o
    operador ver sem precisar rodar outro comando primeiro.

    `force=True` e o caminho deliberadamente destrutivo: ignora o manifesto
    existente por completo e gera um manifesto novo do zero, todo
    `SEM_LASTRO`, renumerado a partir de `VNX-001` -- para o caso real de
    "este manifesto acumulou lixo, comeca de novo". Digitar `--force` E a
    confirmacao explicita da perda; nao ha guarda adicional em cima disso
    porque, com merge no caminho padrao, `--seed` sem `--force` ja nao
    arrisca perda acidental de classificacao -- a unica forma de perder
    trabalho agora e escolher `--force` de proposito.

    Manifesto que EXISTE mas nao pode ser lido, parseado, OU reconhecido como
    manifesto valido NAO cai para geracao fresca: `seed` recusa e retorna
    erro. "Reconhecido como valido" cobre nao so JSON quebrado (invalido,
    IO parcial), mas tambem JSON perfeitamente valido com a FORMA errada --
    nao e um objeto, ou `claims` esta ausente ou nao e uma lista. Essa
    segunda categoria e tao perigosa quanto a primeira e mais facil de
    produzir por acidente: `.get("claims", [])` sozinho nunca levanta
    excecao para chave ausente, entao sem checagem explicita de forma um
    JSON valido faltando `claims` (find/replace ruim editando as 184
    entradas a mao, formatter que derruba uma chave, script de teste que
    reseta o arquivo) passaria pelo `try` como se fosse um manifesto vazio
    -- a mesma perda de classificacao que a checagem de parseabilidade
    existe para evitar, só que sem passar por ela. Cair para fresca em
    qualquer uma das duas categorias tem a mesma assinatura de "descartar
    tudo" que `--force` tem, so que sem nenhuma das duas coisas que tornam
    `--force` seguro -- nem a confirmacao explicita do operador, nem um
    aviso na hora. E o caminho mais provavel para chegar ali e um acidente
    (processo morto no meio da escrita, arquivo travado nesta workstation
    Windows, editor que salvou pela metade, marcador de conflito de merge
    esquecido, edicao manual malfeita), nao uma decisao -- entao tratar
    "ilegivel ou malformado" como "vazio" destruiria classificacao por
    acidente, exatamente o defeito que a fusao por `claim_key` existe para
    evitar no caminho normal. `"claims": []` de verdade (uma lista vazia,
    nao ausente nem de outro tipo) NAO e recusado: e um manifesto legitimo
    sem nada para perder, e e exatamente o que este `seed` escreve para um
    conjunto de documentos sem nenhuma alegacao -- recusar ali quebraria um
    reseed legitimo. So um manifesto AUSENTE (nunca existiu) segue sem pedir
    `--force`, porque nesse caso nao ha nada que a fusao poderia estar
    destruindo.
    """
    itens = list(collect_claims())

    # Tudo entre aqui e `MANIFEST.write_text` roda dentro de UM try: a
    # invariante que este bloco garante e "so escreve se o manifesto anterior
    # foi absorvido por inteiro". As checagens explicitas de forma (objeto
    # JSON, `claims` e lista) continuam em pe abaixo e disparam PRIMEIRO --
    # elas produzem mensagem melhor, apontando exatamente o que esta errado,
    # e sao o padrao, nao a excecao generica. O `except Exception` no fim e
    # o PISO: cobre toda forma de alegacao malformada DENTRO de `claims` que
    # nenhuma checagem explicita antecipou -- um `null` na lista, uma entrada
    # que e string em vez de objeto, uma entrada que casou por `claim_key`
    # mas nao tem `id`. Cada uma dessas ja foi vista quebrando com
    # `TypeError` ou `KeyError` cru no meio do laco de merge, DEPOIS que
    # `existing_claims` passou pelas checagens de forma (que so olham o
    # nivel de fora: e uma lista, sim ou nao -- nao o que tem dentro dela).
    # Sem o catch-all, cada uma dessas formas exigiria uma checagem
    # explicita nova só para chegar no mesmo lugar (recusa, nada escrito) que
    # o piso ja garante para qualquer forma, vista ou nao. Enumerar todo
    # jeito de uma entrada trair o merge e trabalho sem fim; garantir que
    # NENHUM deles resulta em escrita e uma invariante.
    try:
        if force or not MANIFEST.exists():
            existing_claims: list[dict] = []
        else:
            loaded = load_manifest()
            if not isinstance(loaded, dict):
                raise ValueError(
                    f"manifesto deveria ser um objeto JSON, veio {type(loaded).__name__}"
                )
            raw_claims = loaded.get("claims")
            if not isinstance(raw_claims, list):
                # JSON valido, objeto valido, so falta ou deforma a chave
                # `claims` -- `.get("claims", [])` sozinho nunca levanta pra
                # esse caso (ausencia de chave nao e erro de parse), entao
                # sem esta checagem explicita a mesma perda de classificacao
                # do `except` abaixo aconteceria aqui, sem passar por ele:
                # acidente plausivel (find/replace ruim editando as 184
                # entradas a mao, formatter que derruba uma chave, script de
                # teste que reseta o arquivo) tratado como "manifesto vazio".
                # Uma lista vazia de verdade (`"claims": []`) e a UNICA forma
                # aceita e passa direto -- e exatamente o que este `seed`
                # escreve para um conjunto de documentos sem alegacao
                # nenhuma, entao recusar ali quebraria reseed legitimo.
                descricao = (
                    "ausente"
                    if "claims" not in loaded
                    else f"do tipo {type(raw_claims).__name__} (deveria ser lista)"
                )
                raise ValueError(f"manifesto.claims esta {descricao}")
            existing_claims = raw_claims

        # NAO chamar `validate_manifest(loaded, sources)` aqui, de proposito
        # -- foi sugerido em revisao e a ideia faz sentido em abstrato, mas
        # quebra o uso real da Task 9: alguem classificando 184 entradas em
        # varias sessoes vai ter, regularmente, um manifesto MEIO-CAMINHO --
        # uma prova cujo `path` ainda nao foi escrito, um `id` que a pessoa
        # esta prestes a corrigir. Recusar reseed porque uma prova ainda nao
        # valida faria a ferramenta brigar com quem esta usando ela, e
        # reseed precisa continuar disponivel justamente quando o manifesto
        # esta imperfeito -- e exatamente a situacao mais comum enquanto se
        # classifica a mao. Validacao e trabalho do `audit`, que ja faz isso
        # (`validate_manifest` dentro de `audit()`, mais abaixo neste
        # arquivo). As checagens de forma acima (objeto, `claims` e lista) e
        # o `except Exception` no fim deste bloco sao suficientes para a
        # garantia que `seed` precisa: nao escrever se o merge nao pode ser
        # completado -- nao "nao escrever se algo no manifesto ainda nao
        # esta provado", que e uma barra mais alta e errada para este lugar.
        existing_by_key: dict[tuple[str, str, str], list[dict]] = {}
        for entry in existing_claims:
            existing_by_key.setdefault(claim_key(entry), []).append(entry)

        next_id = _next_free_id(existing_claims)
        claims: list[dict] = []
        novas = 0
        for item in itens:
            fila = existing_by_key.get(claim_key(item))
            if fila:
                antiga = fila.pop(0)
                entry = dict(item)
                entry["id"] = antiga["id"]
                entry["state"] = antiga["state"]
                if "note" in antiga:
                    entry["note"] = antiga["note"]
                if "proof" in antiga:
                    entry["proof"] = antiga["proof"]
                claims.append(entry)
            else:
                entry = dict(item)
                entry["id"] = f"VNX-{next_id:03d}"
                next_id += 1
                novas += 1
                entry["state"] = "SEM_LASTRO"
                entry["note"] = "classificacao pendente"
                claims.append(entry)

        # `sumidas` nao distingue "alegacao sumiu do documento" de "allowlist
        # parou de extrair este texto" -- as duas produzem exatamente o
        # mesmo sintoma aqui (chave que existia no manifesto e nao aparece
        # mais em `itens`), e o merge nao tem como saber qual das duas
        # aconteceu sem guardar mais contexto do que guarda hoje. Isso NAO e
        # defeito: e o default certo enquanto a Task 9 tem classificacao real
        # em jogo -- nesse momento, decidir "documento mudou" vs "allowlist
        # mudou" e julgamento humano, e descartar em silencio destruiria
        # prova ou nota escrita a mao sem dar chance de revisao. Achado real
        # (Task 8, correcao pos-revisao): tunar o allowlist DEPOIS de rodar
        # `--seed` sem nenhuma classificacao ainda feita produz exatamente
        # este caso -- toda entrada retida aqui era `SEM_LASTRO` com a nota
        # padrao "classificacao pendente", entao reter era estritamente
        # conservador, nao necessario; `--seed --force` foi a escolha certa
        # NAQUELE momento porque nao havia nada para perder.
        sumidas = [entry for fila in existing_by_key.values() for entry in fila]
    except Exception as exc:  # noqa: BLE001 -- piso deliberado, ver comentario acima do try
        print(
            f"{_display_path(MANIFEST)} existe mas nao pode ser lido, parseado, "
            "reconhecido como manifesto valido, OU fundido com as alegacoes atuais sem "
            f"erro ({type(exc).__name__}: {exc}). "
            "--seed recusa continuar e nao escreve nada: fundir as cegas trataria toda "
            "alegacao antiga como perdida (e toda alegacao fresca como nova), e o caminho "
            "mais provavel para um manifesto que quebra o merge e um acidente -- crash no "
            "meio da escrita, arquivo travado, editor que salvou pela metade, marcador de "
            "conflito de merge, edicao manual malformada -- nao uma decisao de descartar "
            "tudo. Duas saidas reais: restaure o arquivo versionado "
            f"(`git checkout -- {_display_path(MANIFEST)}`) se a corrupcao foi acidental, ou "
            "rode `--seed --force` para descartar de proposito e recomecar do zero."
        )
        return 1

    claims.extend(sumidas)

    if next_id - 1 > 999:
        # Mesmo raciocinio da Task 7: ID_RE exige exatamente tres digitos, e
        # estourar aqui, antes de escrever qualquer coisa em disco, aponta o
        # problema na origem em vez de produzir um `VNX-1000` que so falharia
        # depois, de forma obscura, dentro de `validate_manifest`. Este
        # ValueError fica FORA do `try` de cima de proposito: nao e "o
        # manifesto anterior quebrou o merge" (a causa que o `except` acima
        # cobre e recomenda `git checkout` ou `--force`) -- e "ha alegacao
        # demais para o formato de id", um problema de largura de campo que
        # nenhuma das duas recomendacoes resolveria. Misturar os dois na
        # mesma mensagem confundiria mais do que ajudaria.
        raise ValueError(
            f"merge produziria id acima de 999 (o proximo seria VNX-{next_id:03d}) "
            "-- aumente a largura do id (ID_RE e o f-string de geracao acima) antes "
            "de seedar mais alegacoes que isso"
        )

    payload = {"schema_version": SCHEMA_VERSION, "extracted_from": _head_commit(), "claims": claims}
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if force:
        print(
            f"Semente renumerada do zero com {len(claims)} alegacao(oes) em "
            f"{_display_path(MANIFEST)}"
        )
    else:
        print(
            f"Fusao em {_display_path(MANIFEST)}: {len(claims)} alegacao(oes) no total "
            f"({novas} nova(s), {len(sumidas)} sumida(s) do documento e retida(s) -- "
            "rode a auditoria para ver os detalhes)."
        )
    return 0


def _md_cell(value: object) -> str:
    """Escapa `|` para a celula nao fragmentar a tabela Markdown que
    `report()` gera. GFM corta uma linha de tabela em colunas ANTES de
    interpretar o conteudo como Markdown inline -- um `|` sem escape quebra
    a coluna mesmo dentro de um code span. `prova` embute texto do
    manifesto editado a mao (`cmd`, `path`, `source_id`); `texto` e
    `motivo` embutem prosa extraida do documento ou escrita por quem
    classificou (Task 9) -- qualquer um dos dois pode carregar `|` sem
    aviso nenhum."""
    return str(value).replace("|", "\\|")


def _md_code(value: object) -> str:
    """Envolve `value` num code span Markdown que sobrevive a crase literal
    dentro do valor. Regra do CommonMark: o delimitador precisa ser uma
    corrida de crases MAIOR que a maior corrida de crases dentro do
    conteudo -- um `cmd` ou `path` digitado a mao com uma crase (comum em
    exemplo de shell) quebraria um span delimitado por crase unica sem essa
    escolha de delimitador."""
    text = str(value)
    maior_corrida = corrida_atual = 0
    for char in text:
        if char == "`":
            corrida_atual += 1
            maior_corrida = max(maior_corrida, corrida_atual)
        else:
            corrida_atual = 0
    delim = "`" * (maior_corrida + 1)
    pad = " " if text[:1] == "`" or text[-1:] == "`" else ""
    return f"{delim}{pad}{text}{pad}{delim}"


def report() -> int:
    manifest = load_manifest()
    print("| id | documento | tipo | texto | estado | prova | motivo |")
    print("|---|---|---|---|---|---|---|")
    for entry in manifest.get("claims", []):
        proof = entry.get("proof") or {}
        kind = proof.get("kind")
        if kind == "command":
            prova = f"command {_md_code(proof.get('cmd') or '(sem cmd)')}"
        elif kind == "artifact":
            prova = f"artifact {_md_code(proof.get('path') or '(sem path)')}"
        elif kind == "source":
            prova = f"source {_md_code(proof.get('source_id') or '(sem source_id)')}"
        elif kind == "historical":
            prova = (
                f"historical @ {_md_code(proof.get('commit') or '(sem commit)')} "
                f"{_md_code(proof.get('cmd') or '(sem cmd)')}"
            )
        else:
            prova = "—"
        motivo = entry.get("note") or "—"
        print(
            f"| {_md_cell(entry['id'])} | {_md_cell(entry['doc'])} | "
            f"{_md_cell(entry['type'])} | {_md_cell(entry.get('text', ''))} | "
            f"{_md_cell(entry['state'])} | {_md_cell(prova)} | {_md_cell(motivo)} |"
        )
    return 0


def audit(include_slow: bool) -> int:
    """Audita o manifesto contra os documentos e, quando o resultado
    estrutural vier limpo, executa as provas `command`. Manifesto ausente ou
    ilegivel e um erro de operador (rodar `audit` antes de `seed`, ou um
    JSON corrompido a mao), nao um traceback cru -- a mensagem aponta o
    comando que resolve.

    Provas `command` so rodam quando `validate_manifest` e `check_orphans`
    nao acusaram nada: rodar subprocesso (ate 60s por prova `fast`, 900s por
    `slow`) contra um manifesto que ja sabemos ter id duplicado, proof mal
    formada ou alegacao orfa so queima tempo sem informar nada que a
    validacao estrutural nao ja soubesse -- e caro de mais para acontecer em
    todo push depois que a Task 11 ligar isto ao CI. A mensagem de "provas
    nao executadas" e obrigatoria quando isso acontece: silencio ali pareceria
    "as provas passaram", que e exatamente o oposto do que aconteceu.
    """
    try:
        manifest = load_manifest()
    except FileNotFoundError:
        print(
            f"{_display_path(MANIFEST)} nao existe -- rode "
            "`python scripts/check_vnext_claims.py --seed` para gerar o manifesto semente."
        )
        return 1
    except json.JSONDecodeError as exc:
        print(f"{_display_path(MANIFEST)} nao e JSON valido: {exc}")
        return 1

    errors = validate_manifest(manifest, _load_sources())
    errors += check_orphans(collect_claims(), manifest)
    for error in errors:
        print(error)

    if errors:
        print(
            "provas command NAO executadas -- o manifesto ja tem divergencia "
            "estrutural (acima), e rodar comando sobre um manifesto que ja sabemos "
            "estar errado so queima tempo sem provar nada nem confirmar nada. "
            "Corrija as divergencias acima e rode de novo para exercitar as provas."
        )
    else:
        prova_errors = run_command_proofs(manifest, include_slow)
        errors += prova_errors
        for error in prova_errors:
            print(error)

    print(f"{len(errors)} divergencia(s).")
    return 1 if errors else 0


def _make_output_encoding_safe() -> None:
    """Impede que o gate morra ao IMPRIMIR a divergencia que ele acabou de achar.

    O console padrao do Windows usa cp1252, e o texto auditado e portugues
    tecnico cheio de caractere fora dessa tabela -- acento nao, mas seta
    (`->` escrito como caractere unico), travessao e simbolo de secao sim. Um
    documento novo que usasse qualquer um deles derrubava o `audit()` com
    `UnicodeEncodeError` no meio do relatorio: exit code diferente de zero,
    porem por traceback, escondendo QUAIS alegacoes estavam sem lastro --
    exatamente a informacao pela qual o gate existe. Substituir o caractere
    ilegivel por `?` na saida perde estetica e nao perde nenhuma alegacao.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Inclui provas tier slow.")
    parser.add_argument(
        "--seed", action="store_true", help="Funde alegacoes novas no manifesto existente."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Com --seed: descarta o manifesto existente e renumera tudo do zero (SEM_LASTRO).",
    )
    parser.add_argument("--report", action="store_true", help="Tabela de lastro.")
    args = parser.parse_args()
    _make_output_encoding_safe()
    if args.seed:
        return seed(force=args.force)
    if args.report:
        return report()
    return audit(include_slow=args.full)


if __name__ == "__main__":
    raise SystemExit(main())
