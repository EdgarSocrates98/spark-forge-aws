# SparkForge Devin — perfis de subagente: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** os coordenadores e executores deste repositório funcionando como perfis de subagente de verdade no Devin, sem que o repositório afirme controle sobre o que o harness decide.

**Architecture:** `agents/` e `skills/` continuam sendo a fonte. `scripts/sync_skills.py` deixa de copiar e passa a **renderizar** por plataforma; o gate deixa de comparar bytes e passa a comparar contra a renderização.

**Tech Stack:** Python stdlib, Markdown com frontmatter YAML, pytest.

**Spec:** [`../specs/2026-08-04-sparkforge-devin-subagentes-design.md`](../specs/2026-08-04-sparkforge-devin-subagentes-design.md) — §6 tem os dez critérios.

**Pesquisa de fontes:** [`knowledge/devin/agents-and-subagents.md`](../../../knowledge/devin/agents-and-subagents.md), com onze vetos `V-DV-*`. **Leia antes de começar** — ela já matou seis afirmações da doc que motivou esta fase.

---

## Fatos do ambiente verificados antes de escrever este plano

```
sync_skills.py  258 linhas, tres familias de espelho, comparacao por filecmp.cmp
  MIRRORS          .claude/skills, .agents/skills
  AGENT_MIRRORS    .claude/agents {stem}.md | .agents/agents {stem}.md
                   .github/agents {stem}.agent.md
  EXECUTOR_MIRRORS .claude/agents/executors, .agents/agents/executors,
                   .github/agents/executors
  STALE_AGENTS     lista de espelhos obsoletos a recusar

agents/*.md frontmatter hoje:
  name, description, tools, skills, rule_areas, executors

tests que tocam espelho: test_skill_content, test_agents_parity (TestNoPlatformKnowledge),
                         test_capability_parity, test_ci_workflow
```

**A consequência que decide a Task 1:** `.claude/agents/` e `.github/agents/`
continuam recebendo o arquivo **inalterado**. Só o espelho do Devin transforma.
Renderizador que muda todos os alvos seria mudança maior que a pedida, e
quebraria o Copilot sem ninguém pedir.

---

## Task 1: o renderizador

**Files:**
- Modify: `scripts/sync_skills.py`
- Create: `tests/test_sync_render.py`

- [x] **Step 1: Escreva o teste que falha**

```python
# tests/test_sync_render.py
from scripts.sync_skills import render_agent


SOURCE = """---
name: emr-infra-reviewer
description: Use quando o Spark roda em EMR on EC2.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - review-emr-cluster
rule_areas: [SF-EMR]
executors: [sf-inventory]
---

Corpo do perfil.
"""


def test_claude_recebe_o_arquivo_inalterado():
    assert render_agent(SOURCE, platform="claude") == SOURCE


def test_github_recebe_o_arquivo_inalterado():
    assert render_agent(SOURCE, platform="github") == SOURCE


def test_devin_perde_o_campo_tools():
    """O mapeamento de valores de `tools:` NAO esta documentado (V-DV-* da
    pesquisa). Chute em campo de permissao concede ou nega errado, e nos dois
    sentidos o erro e caro. Omitido, o subagente herda o que o harness da."""
    out = render_agent(SOURCE, platform="devin")
    assert "tools:" not in out
    assert "name: emr-infra-reviewer" in out
    assert "rule_areas: [SF-EMR]" in out
    assert "Corpo do perfil." in out


def test_devin_nunca_ganha_model():
    """O default resolve por roteador no spawn e o admin da org sobrescreve.
    Escrever `model:` seria fingir controle sobre o que o harness decide."""
    assert "model:" not in render_agent(SOURCE, platform="devin")


def test_render_e_idempotente():
    once = render_agent(SOURCE, platform="devin")
    assert render_agent(once, platform="devin") == once
```

- [x] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_sync_render.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_agent'`

Medido, literal: `ImportError: cannot import name 'render_agent' from
'scripts.sync_skills'`, coleta interrompida.

- [x] **Step 3: Implemente**

`render_agent(text, platform)` separa o frontmatter do corpo, aplica a
transformação da plataforma, e remonta preservando a ordem das chaves que
sobrarem. Para `claude` e `github`, devolve o texto **idêntico** — sem
round-trip de YAML, que reordenaria chaves e produziria diff onde não há
mudança.

Para `devin`: remove a linha `tools:` (e as continuações dela, se houver forma
de lista), e **nunca** acrescenta `model:`.

O comentário no código diz por quê, citando a pesquisa — quem vier depois vai
querer "completar" o frontmatter.

- [x] **Step 4: Rode e commite**

`tests/test_sync_render.py` 20 passed. Suíte 3499 passed / 5 skipped (era 3479 /
5). `ruff check .` limpo. `git diff .agents/ .claude/ .github/` **vazio** — a
função foi criada e testada, não aplicada; aplicá-la é a Task 2.

**Desvios medidos na Task 1**

- **D-DV-1 — a linha "agents/*.md frontmatter hoje" dos fatos do ambiente vale
  para oito dos treze.** Medido nos treze: os oito coordenadores têm
  `name, description, tools, skills, rule_areas, executors`; os cinco
  executores de `agents/executors/` têm `name, role, function, tools` — sem
  `skills:`, sem `rule_areas:`, sem `executors:`. A única chave comum aos treze
  é justamente `tools:`, e nos executores ela é a **última** do frontmatter,
  colada na cerca `---` de fechamento. Isso é o caso de borda que uma remoção
  com continuações pode estragar: ela tem que parar na primeira linha não
  indentada, e a cerca não é indentada. Coberto por
  `TestPerfisReais::test_devin_so_perde_a_linha_de_tools` sobre os treze reais.

- **D-DV-2 — a forma de bloco de `tools:` não existe no corpus.** Medido: os
  treze escrevem `tools: Read, Grep, ...` inline; nenhum usa
  `tools:\n  - Read`. O tratamento de continuação foi implementado assim mesmo
  e fixado por teste sobre fonte sintética — não porque hoje seja necessário,
  mas porque um regex ingênuo deixaria `  - Read` órfão no dia em que alguém
  escrevesse assim, e o frontmatter do espelho deixaria de ser YAML. O teste
  irmão prova que a remoção **não** engole `skills:`, que vem logo depois e
  também é lista indentada.

- **D-DV-3 — o Step 1 traz cinco testes; o arquivo entregue tem vinte.** Os
  cinco literais estão lá, inalterados. Os quinze restantes são o que a medição
  pediu: os treze perfis reais (passthrough byte a byte, `tools:` some,
  `model:` nunca aparece, corpo intacto, idempotência), a forma de bloco,
  `skills:`/`rule_areas:`/`executors:` sobrevivendo, `tools:` no **corpo** não
  sendo tocado, fim de linha CRLF preservado, e plataforma desconhecida
  levantando `ValueError`. Este último não estava no plano e é deliberado:
  passthrough silencioso para nome errado de plataforma publicaria um espelho
  Devin **com** `tools:` sem ninguém saber — exatamente o modo de falha mudo
  que a Task 2 depende de não ter.

---

## Task 2: o gate passa a comparar contra a renderização

**Files:**
- Modify: `scripts/sync_skills.py`, `tests/test_agents_parity.py`

- [x] **Step 1: Teste primeiro**

O gate hoje é `filecmp.cmp(src, dst, shallow=False)`. Ele passa a comparar
`dst.read_text()` com `render_agent(src.read_text(), platform)`, e a plataforma
sai do próprio alvo — `.agents/` é `devin`, `.claude/` é `claude`,
`.github/` é `github`.

Escreva o teste que prova que **espelho editado à mão é pego**: renderize,
grave, altere um byte do espelho, e confirme que o gate acusa `DIVERGENTE`.

Entregue em `tests/test_agents_parity.py::TestGatePegaEspelhoEditadoAMao`: seis
alvos parametrizados (as três plataformas × coordenador e executor), mais o
espelho apagado virando `AUSENTE`, mais o teste que o gate **antigo não poderia
passar** — cópia literal da fonte no espelho do Devin é `DIVERGENTE`.

- [x] **Step 2: Rode, regenere, leia o diff**

Run: `python scripts/sync_skills.py` e depois `git diff .agents/`

O diff esperado é **só a remoção de `tools:`** nos treze perfis (oito
coordenadores + cinco executores). Se aparecer reordenação de chave ou mudança
de corpo, o renderizador está fazendo round-trip de YAML — corrija antes de
seguir.

Medido: `13 files changed, 13 deletions(-)`, uma linha por arquivo, todas
`tools: ...`. `git diff --numstat -- .claude .github` **vazio**. Diff lido
inteiro, linha a linha.

- [x] **Step 3: `TestNoPlatformKnowledge` continua valendo?**

`tests/test_agents_parity.py` proíbe marcadores (`threshold:`, `runtime_scope:`,
`retrieved:`) nos espelhos de plataforma — a Fase 4a bateu nele. Confirme que a
renderização não introduz nem remove marcador, e que o teste segue verde.

Verde. A renderização só **remove** `tools:`, que não é marcador proibido, e não
acrescenta nada — nenhum dos três marcadores entra nem sai.

- [x] **Step 4: Commite**

**Desvios medidos na Task 2**

- **D-DV-4 — um teste existente teve que mudar, e a mudança é a própria tese
  da task.** `TestMirrors::test_devin_agents_mirror_matches_source` afirmava
  `filecmp.cmp(agents/X.md, .agents/agents/X.md)` — byte-identidade com a
  fonte. Isso deixou de ser o invariante e virou o **defeito**: o espelho do
  Devin byte-idêntico à fonte é justamente o que sai com `tools:`. Renomeado
  para `test_devin_agents_mirror_matches_the_render`, compara contra
  `render_agent(..., "devin")`. O teste irmão de `.claude/` ficou intocado, com
  `filecmp` e tudo — lá o espelho é passthrough e byte-identidade continua
  sendo o contrato. O gate antigo não poderia passar o teste novo
  `test_copia_literal_da_fonte_no_espelho_do_devin_vira_divergente`, que é o
  que prova que a troca de mecanismo **apertou** em vez de afrouxar.

- **D-DV-5 — a plataforma é derivada do alvo, não é uma quarta lista.** O Step 1
  diz "a plataforma sai do próprio alvo". A tentação era acrescentar um terceiro
  campo às tuplas de `AGENT_MIRRORS` e um segundo às de `EXECUTOR_MIRRORS` —
  duas listas paralelas obrigadas a concordar, que é a família de defeito da
  Fase 5c nos dois `EXTRACTORS`. Entrou `platform_for(path)` sobre
  `PLATFORM_BY_MIRROR_ROOT`, e alvo fora das três raízes levanta `ValueError`
  em vez de cair em default que publicaria o arquivo cru numa plataforma nova.

- **D-DV-6 — a comparação é em bytes, não em texto.** O Step 1 escreve
  `dst.read_text()`. Literal, isso afrouxaria o gate: `read_text()` aplica
  newline universal, e um espelho gravado com CRLF passaria a comparar igual a
  uma fonte LF. `rendered_bytes` lê com `read_bytes().decode("utf-8")`,
  renderiza, e reencoda; a comparação é `dst.read_bytes() == ...`. É o mesmo
  cuidado que `test_fim_de_linha_e_preservado` fixou na Task 1, agora do lado
  do gate.

- **D-DV-7 — `tests/test_ci_workflow.py` não precisou mudar.** O contrato do
  script é o mesmo: mesma flag `--check`, mesmos códigos de saída, mesma
  família de mensagens. O que mudou foi o critério interno de divergência, e o
  workflow não o conhece — `test_runs_sync_skills_check` segue válido sem
  edição. A escrita passa a imprimir `REND` no lugar de `COPY` para os perfis,
  e nenhum teste depende dessa string.

---

## Task 3: a fronteira de manutenção destrutiva

**Files:**
- Modify: `agents/*.md` (os oito), `agents/executors/*.md` (os cinco)
- Create: teste em `tests/test_agents_parity.py`

- [x] **Step 1: O teste que falha**

```python
def test_todo_perfil_declara_a_fronteira_de_manutencao_destrutiva():
    """`ask_user_question` e SEMPRE negado a subagente (pesquisa de fontes,
    knowledge/devin/agents-and-subagents.md). Logo a regra 10 do CLAUDE.md --
    confirmacao explicita de escopo e retencao antes de manutencao destrutiva --
    e inalcancavel de dentro de um subagente.

    Sem a fronteira escrita, o modo de falha e mudo: o subagente segue sem
    confirmar, ou para sem dizer por que.
    """
    faltando = [
        p.name
        for p in perfis()
        if "manutenção destrutiva" not in p.read_text(encoding="utf-8")
    ]
    assert not faltando, faltando
```

Ajuste `perfis()` ao helper que o arquivo já usa para varrer `agents/`.

- [x] **Step 2: Rode e veja falhar**

Expected: FAIL listando os treze.

Medido: `13 failed, 32 passed`, um id por perfil — os oito coordenadores e os cinco
executores, nenhum a mais.

- [x] **Step 3: Escreva a fronteira em cada perfil**

Na seção `## Não faz` — que os executores já têm e os coordenadores usam desde a
Fase 5b. O texto diz: não executa manutenção destrutiva (expiração de snapshot,
remoção de arquivo órfão, `DROP`, sobrescrita de partição); recomenda, e a
confirmação de escopo e retenção acontece com quem tem a pergunta disponível.

**Não copie a mesma frase treze vezes sem ler o perfil.** Um coordenador de
Athena e um executor de inventário chegam perto disso por caminhos diferentes, e
a fronteira tem que fazer sentido no contexto de cada um.

- [x] **Step 4: Regenere os espelhos, rode, commite**

Suíte 3527 passed / 5 skipped (era 3510 / 5; +17 = 13 perfis parametrizados mais os
quatro testes do critério). `ruff check .` limpo. `sync_skills.py --check` OK. `git diff
.agents/` é só o texto novo: nenhuma linha `+tools:`, e as únicas remoções são as seis
linhas do `iceberg-performance-engineer` reescritas (D-DV-9).

**Desvios medidos na Task 3**

- **D-DV-8 — o critério de detecção do teste não é o do Step 1, e o do Step 1 acertava por
  acidente.** O plano casa `"manutenção destrutiva" not in p.read_text()` sobre o arquivo
  inteiro. Medido no baseline, ele de fato lista os treze — mas o `iceberg-performance-
  engineer` só entra na lista porque a sua seção se chamava `## Manutenção destrutiva` com
  M maiúsculo; a mesma checagem sem diferenciar caixa listaria doze e daria por resolvido
  justamente o perfil cujo texto estava mais errado (D-DV-9). Um critério que depende de
  capitalização não é critério. Pior: casar frase sobre o arquivo inteiro premia menção de
  passagem — explicar que `expire_snapshots` não tem rollback é conhecimento de domínio,
  não fronteira. O que entrou: a seção `## Não faz` tem que existir (âncora estrutural, não
  prosa — é onde este repositório escreve fronteira desde a Fase 5b), e **dentro dela** os
  radicais `destrutiv` e `confirma`. Radical, e não frase, porque exigir texto idêntico nos
  treze é o defeito que o próprio Step 3 proíbe. Os dois, e não um, porque as duas metades
  falham de formas diferentes e as duas falham em silêncio: quem declara só o ato para sem
  dizer por quê; quem declara só a escalada segue sem confirmar. Três testes irmãos fixam o
  critério: menção fora da seção não conta, meia fronteira não conta, perfil sem a seção é
  pego. Um quarto guarda contra o teste vazio — recorte que esvaziasse passaria sem olhar
  nada. O que o critério **não** faz, e está escrito no docstring: verificar sentido. Ele
  garante que ninguém publica perfil sem ter escrito sobre as duas metades no único lugar
  onde fronteira mora.

- **D-DV-9 — o `iceberg-performance-engineer` já tinha a fronteira, e ela estava errada.**
  A seção `## Manutenção destrutiva` terminava com a regra 10 do `CLAUDE.md` copiada
  literalmente: "Não execute expiração ou remoção destrutiva sem confirmação explícita de
  escopo e retenção." Lida como está, é permissão condicional — *com* confirmação, execute.
  Num subagente a condição nunca é satisfeita (V-DV-10), então a frase é letra morta ou
  convite a prosseguir, e não há terceira leitura. Integrado, não duplicado: a seção virou
  `## Não faz`, o conteúdo de domínio (sem rollback, time travel, escrita concorrente)
  ficou, e a prescrição foi reescrita para "não executa" mais o que sai no lugar — escopo,
  janela, o que sobra de time travel. Uma frase foi deletada ("Foque em metadata planning,
  ..."): ela repetia o `description` do frontmatter palavra por palavra e vira contradição
  sob um cabeçalho `## Não faz`. `## As cinco camadas` teve "antes de rodar qualquer
  manutenção" trocado por "antes de propor", pela mesma razão.

- **D-DV-10 — "que os executores já têm e os coordenadores usam desde a Fase 5b" vale para
  seis dos treze.** Medido: os cinco executores mais o `data-quality-reviewer` tinham
  `## Não faz`; os outros sete coordenadores não. Nos seis a fronteira entrou **dentro** da
  seção existente e no registro dela — bullet na lista do `data-quality-reviewer`, parágrafo
  no fim dos cinco executores —, nunca como seção nova ao lado de uma que já existia. Os
  sete restantes ganharam a seção, sempre antes de `## Como você trabalha`, que é onde os
  coordenadores fecham.

---

## Task 4: skills que despacham

**Files:**
- Modify: `scripts/sync_skills.py`, `skills/*/SKILL.md` (as despacháveis), `tests/test_sync_render.py`

- [x] **Step 1: Meça a relação skill → perfil**

```bash
python -c "
import pathlib, re
for p in sorted(pathlib.Path('agents').glob('*.md')):
    t = p.read_text(encoding='utf-8')
    m = re.search(r'^skills:\n((?:  - .+\n)+)', t, re.M)
    if m:
        print(p.stem, '->', [l.strip('- \n') for l in m.group(1).splitlines()])
"
```

Cole a saída. É dela que `agent:` é derivado (D-5 do spec) — **não** crie
segunda lista.

**Meça também o caso ambíguo:** skill declarada por **mais de um** coordenador.
Se existir, `agent:` não tem resposta única, e a decisão vai no relatório: ou a
skill não declara `agent:` (o Devin escolhe), ou declara o primeiro em ordem
determinística com a razão escrita.

Saída literal, oito coordenadores:

```
athena-query-optimizer -> ['optimize-parquet-layout', 'optimize-iceberg-table', 'benchmark-pyspark-job']
data-quality-reviewer -> ['review-data-validation', 'review-pyspark-pr', 'analyze-library-call-graph']
emr-infra-reviewer -> ['review-emr-cluster', 'analyze-spark-ui', 'benchmark-pyspark-job']
glue-incremental-performance-architect -> ['glue-incremental-performance-architect', 'sparkforge-diagnose', 'analyze-library-call-graph', 'design-incremental-processing', 'optimize-latest-per-key', 'analyze-batch-loop', 'diagnose-oom', 'optimize-variable-volume-job', 'review-glue-terraform', 'optimize-pyspark-code', 'analyze-spark-plan', 'analyze-spark-ui', 'diagnose-data-skew', 'tune-glue-job', 'optimize-parquet-layout', 'optimize-iceberg-table', 'benchmark-pyspark-job']
glue-infra-reviewer -> ['review-glue-terraform', 'tune-glue-job', 'optimize-variable-volume-job']
iceberg-performance-engineer -> ['optimize-iceberg-table', 'optimize-parquet-layout', 'benchmark-pyspark-job']
pyspark-code-reviewer -> ['review-pyspark-pr', 'optimize-pyspark-code', 'analyze-spark-plan', 'analyze-library-call-graph', 'analyze-batch-loop']
spark-performance-architect -> ['sparkforge-diagnose', 'optimize-pyspark-code', 'analyze-spark-plan', 'analyze-spark-ui', 'diagnose-data-skew', 'tune-glue-job', 'optimize-parquet-layout', 'optimize-iceberg-table', 'benchmark-pyspark-job', 'review-pyspark-pr']
```

Invertida: as vinte skills aparecem, **14 delas declaradas por mais de um
coordenador** — o caso ambíguo é a maioria, não a exceção (D-DV-11).

- [x] **Step 2: `render_skill`, com teste primeiro**

Despacháveis, por D-6 do spec: `review-emr-cluster`, `review-data-validation`,
`review-glue-terraform`, `review-pyspark-pr` e os `analyze-*`.

**`sparkforge-diagnose` NÃO é despachável** — ela abre o case e roteia, e
despachá-la jogaria o ciclo de vida do case para um contexto que não volta. O
teste fixa isso, e o motivo vai no código.

O renderizador acrescenta `subagent: true` e `agent: <perfil>` ao frontmatter do
espelho `.agents/skills/`, e não toca em `.claude/skills/`.

- [x] **Step 3: O invariante bidirecional**

```python
def test_agent_de_skill_nomeia_perfil_que_a_declara():
    """Relacao que quebra de um lado so e a familia de defeito que a Fase 5c
    achou nas duas listas EXTRACTORS mantidas a mao."""
```

Para cada skill com `agent: X`, o perfil `X` existe **e** declara aquela skill
em `skills:`.

Entregue em `TestInvarianteBidirecional`, sobre o **espelho em disco** e não
sobre a função que o gerou — os dois lados lidos por parsers independentes, e
duas quebras sintéticas (perfil apagado, perfil que deixou de declarar) provando
que ele acusa.

- [x] **Step 4: Regenere, leia o diff, commite**

Medido: `12 files changed, 15 insertions(+), 0 deletions(-)`, todos em
`.agents/skills/`. `git diff --numstat -- .claude .github` **vazio**. Segunda
execução de `sync_skills.py` reporta `0 alteração(ões)`. Suíte 3558 passed /
5 skipped (era 3527 / 5). `ruff check .` limpo. `--check` OK.

**Desvios medidos na Task 4**

- **D-DV-11 — o caso ambíguo é a maioria, e ele decide o desenho de `agent:`.**
  Medido na relação derivada: **14 das 20** skills são declaradas por dois a
  cinco coordenadores; só 6 têm um coordenador só. Entre as **12** despacháveis,
  apenas **3** (`review-emr-cluster`, `review-data-validation`, `diagnose-oom`)
  têm resposta única. As outras nove declaram `subagent: true` **sem** `agent:`,
  e o Devin escolhe o perfil — forma documentada, porque `agent` tem default
  *none* na tabela de frontmatter da fonte. A alternativa do Step 1 ("declara o
  primeiro em ordem determinística") foi recusada **com o número na mão**, não
  por gosto: em ordem alfabética, `review-pyspark-pr` cairia em
  `data-quality-reviewer` e `analyze-spark-plan` em
  `glue-incremental-performance-architect`, quando o especialista de ambas é
  `pyspark-code-reviewer`. Ordem alfabética não é critério de competência, e
  publicá-la como se fosse seria roteamento errado com cara de decisão. O
  contraexemplo está fixado em `test_a_ordem_alfabetica_seria_o_perfil_errado`.

- **D-DV-12 — despacham 12, e não os 8 de D-6.** Entraram além do recorte do
  spec: `diagnose-oom` e `diagnose-data-skew` (coletam o próprio event log,
  julgam, e devolvem uma classificação — o discriminador de cada uma,
  `heap_oom_in_log` e o par SF-UI-001/SF-UI-002, está no artefato, não numa
  pessoa), `optimize-pyspark-code` (mesma forma de `review-pyspark-pr`, que D-6
  já despacha) e `optimize-parquet-layout` (cinco fontes, todas obtidas só
  lendo). Ficaram de fora, além de `sparkforge-diagnose`: o
  `glue-incremental-performance-architect` (orquestra as outras skills por
  `next-step`, e subagente não gera subagente por default — despachar quem
  orquestra é perder a orquestração), `optimize-iceberg-table` (a própria skill
  exige que a retenção de `expire_snapshots` venha do dono dos dados, e
  `ask_user_question` é sempre negado a subagente), `optimize-latest-per-key` e
  `design-incremental-processing` (a seção "Perguntas que o extrator não faz por
  você" e o contrato de saída de dezesseis campos são, literalmente, perguntas),
  `benchmark-pyspark-job` (o passo 2 é *aplique a mudança* entre as duas
  coletas), `tune-glue-job` e `optimize-variable-volume-job` (dependem de
  evidência que o pai já acumulou, e subagente não herda o histórico dele).
  **A assimetria que resolveu os duvidosos**, e que está escrita no código: uma
  despachável a mais que precisasse perguntar falha **muda**; uma a menos custa
  contexto do pai, e nada mais.

- **D-DV-13 — o frontmatter das skills não é YAML estrito, e isso muda o teste,
  não o renderizador.** Medido: `yaml.safe_load` levanta `ScannerError` em
  **5 dos 20** `SKILL.md` — as descrições citam comando com dois-pontos dentro
  de escalar simples (``rode `sparkforge analyze plan`: ele emite``). Por isso o
  teste lê as chaves de topo linha a linha, como o `parse_frontmatter` que
  `test_skill_content` já tinha. O renderizador é imune porque insere no **fim**
  do frontmatter, imediatamente antes da cerca de fechamento: é a única posição
  que não depende de onde as chaves existentes estão nem de conseguir parsear as
  que existem. Onde o YAML importa — provar que a inserção não quebrou a cerca —
  os testes de borda usam fonte sintética, que é YAML válido de propósito,
  inclusive o caso da lista indentada como última chave.

- **D-DV-14 — outro teste existente teve que mudar, pelo mesmo motivo do
  D-DV-4.** `test_copias_identicas` afirmava byte-identidade da fonte com os
  **dois** espelhos. Isso virou o defeito: o espelho do Devin byte-idêntico à
  fonte é o que sai sem declarar despacho. Renomeado para
  `test_copias_conferem_com_a_renderizacao`, compara contra
  `rendered_skill_bytes` — e mantém, como asserção **extra e explícita**, que
  `.claude/skills/` continua byte a byte igual à fonte, porque lá a identidade é
  que é o contrato. A comparação é em bytes, herdando o D-DV-6.

- **D-DV-15 — skill sem decisão registrada levanta, e a partição é testada.**
  `DISPATCHABLE_SKILLS` e `NON_DISPATCHABLE_SKILLS` são dicionários nome → razão,
  e um teste exige que a união seja **exatamente** `skills/` e a interseção
  vazia. Skill nova cai em nenhum dos dois e o gate acusa; `render_skill`
  levanta `ValueError` em vez de tratá-la como não-despachável. Default
  silencioso publicaria uma skill sem ninguém ter perguntado se ela consegue
  trabalhar sem poder perguntar — o mesmo raciocínio do `ValueError` de
  plataforma desconhecida (D-DV-3). A razão por skill é **dado**, não comentário:
  o teste do `sparkforge-diagnose` casa contra ela.

- **D-DV-16 — a sincronia de skills deixou de usar `filecmp`/`copy2`.** A Task 2
  registrou que skills seguiam com cópia byte a byte; isso caiu aqui, porque
  `.agents/skills/` passou a transformar. `check_skills` e `sync_skills` agora
  comparam e gravam **bytes renderizados**, pelo mesmo caminho que o `--check`
  usa — copiar na escrita e comparar contra renderização na conferência faria o
  script brigar consigo mesmo a cada regeneração. Arquivo que não é `SKILL.md`
  sai como está, sem `decode`, para não quebrar no dia em que uma skill tiver
  anexo binário.

---

## Task 5: `parity.yaml`

**Files:**
- Modify: `parity.yaml`, `tests/test_capability_parity.py`

- [x] **Step 1: O mecanismo e o recorte**

`subagent` entra em `mechanisms`. As capacidades de coordenação declaram
`subagent` para `devin_cli`, e para `devin_desktop` **com o recorte medido**: só
no Devin Local agent, com o toggle "Subagents (Preview)".

`codex` e `copilot_ci` **não** ganham — a pesquisa não os cobriu, e afirmar mais
seria repetir o defeito do transporte HTTP da Fase 1, que este mesmo arquivo cita
como razão de ser da regra.

Entregue: `mechanisms: [mcp, cli, files, playbook, subagent]`, e a única
capacidade de coordenação com `subagent` para `claude_code`, `devin_desktop` e
`devin_cli` (D-DV-17). O recorte do Desktop está **no arquivo** em dois lugares:
comentário YAML na linha de `devin_desktop` e parágrafo próprio em `notes`.

- [x] **Step 2: O parágrafo original fica**

Ele ganha desvio registrado ao lado: a frase universal caiu por contraexemplo, e
o que sobrou é *o perfil é nosso, o despacho é deles*. Preservar o texto é a
convenção do repositório, e aqui vale duplamente — ele documenta a disciplina que
esta fase mantém ao não estender a `codex` e `copilot_ci`.

Preservado palavra por palavra; o desvio entrou **depois** dele, com quatro
partes nomeadas — o que caiu, o que sobrou, por que a disciplina segue sendo
exercida, e o recorte do Desktop. Quatro testes em
`TestOParagrafoOriginalFicaComDesvioAoLado` fixam as duas metades, inclusive a
ordem (desvio ao lado, não no lugar).

- [x] **Step 3: O invariante que herda a lição da Fase 1**

Capacidade que declara `subagent` só pode listar plataforma cujo suporte a
pesquisa confirma. Derive do `knowledge/devin/agents-and-subagents.md` se der;
se não der sem parser frágil, use lista literal **com o ponteiro para a fonte no
comentário**, e diga no relatório por que não deu para derivar.

Medido, não deu: **lista literal com ponteiro por plataforma** em
`SUBAGENT_CONFIRMED_BY` (D-DV-18). Oito testes em
`TestSubagentSoOndeAPesquisaConfirma`, incluindo o guarda de não-vacuidade e o
que exige que a razão de cada entrada aponte a fonte.

- [x] **Step 4: Rode e commite**

Suíte 3569 passed / 5 skipped (era 3558 / 5; +12 novos, −1 substituído).
`ruff check .` limpo. `sync_skills.py --check` OK. `git diff` só em
`parity.yaml`, `tests/test_capability_parity.py` e neste plano.

**Desvios medidos na Task 5**

- **D-DV-17 — `claude_code` também ganha `subagent`, e o plano não o nomeia.** O
  Step 1 nomeia `devin_cli` e `devin_desktop`, e proíbe `codex` e `copilot_ci`;
  sobre `claude_code` ele é mudo. Declarar só o Devin publicaria o inverso exato
  do defeito que esta fase combate: o manifesto afirmaria que o Devin tem um
  mecanismo de coordenação que o Claude Code **não** tem, quando o despacho de
  subagente do Claude Code é a única afirmação do parágrafo original que a
  pesquisa não derrubou — ele está escrito nas linhas 18-29 ("capacidade de
  HARNESS do Claude Code, o `Agent` tool desta CLI"), e é o harness em que este
  repositório roda. Negar capacidade que existe e afirmar capacidade que não
  existe são a mesma falha em espelho, e o teste substituído
  (`test_only_claude_code_claims_subagent_dispatch`) já presumia `claude_code`
  como o dono legítimo do mecanismo. A entrada dele em `SUBAGENT_CONFIRMED_BY`
  carrega ponteiro próprio, e **não** aponta a pesquisa do Devin — apontar seria
  citar fonte que não fala dele.

- **D-DV-18 — derivar do arquivo de pesquisa não sobrevive à medição, e a
  medição é o próprio contraexemplo.** O Step 3 manda derivar se der. Medido por
  `grep` de identificador de plataforma sobre
  `knowledge/devin/agents-and-subagents.md`: `codex` aparece **7 vezes** e
  `copilot_ci` **1 vez** — e nenhuma delas é suporte a subagente. `codex` é o
  *short name* de modelo do Devin CLI (`/model codex`, "Short names like `opus`,
  `sonnet`, `swe`, `codex`"), e `copilot_ci` aparece exatamente na frase da §13
  que declara que ele **não foi objeto da pesquisa**. Uma derivação por
  ocorrência listaria as duas plataformas que o critério 7 existe para excluir.
  Pior: a única frase que nomeia as duas plataformas certas as nomeia dentro de
  uma **negação** — "Isso e FALSO para devin_cli e para devin_desktop", no bloco
  `V-DV-1` —, e a tabela de veredictos da §0 é keyed por pergunta em prosa, com
  quatro formas distintas de veredicto ("Confirmada", "Confirmada, com recorte",
  "Parcialmente contradita", "Campo confirmado; nomes CONTRADITOS"). Não existe
  bloco legível por máquina keyed por identificador de plataforma. Parser frágil
  sobre prosa falha para o lado errado **em silêncio**, que é o modo de falha que
  este invariante existe para fechar. Entrou lista literal com uma razão por
  plataforma, cada uma citando seção e `retrieved:`, e
  `test_a_razao_nomeia_a_fonte` impede que ela degenere em lista de nomes.

- **D-DV-19 — um teste existente teve que ser substituído, pelo mesmo motivo do
  D-DV-4 e do D-DV-14.** `TestOrchestrationParity::test_only_claude_code_claims_
  subagent_dispatch` afirmava que nenhuma plataforma além de `claude_code` podia
  declarar `subagent`. Isso deixou de ser invariante e virou a afirmação que a
  pesquisa derrubou. A troca **aperta** em vez de afrouxar: o teste antigo
  cobrava um nome de plataforma, e passaria verde para qualquer manifesto que
  simplesmente não usasse o mecanismo; o novo cobra **evidência por plataforma**,
  e `codex`/`copilot_ci` continuam pegos por dois caminhos independentes — a
  regra geral e um teste nominal. `test_declares_the_four_mechanisms` virou
  `..._the_five_mechanisms`, e a tupla `MECHANISMS` do teste continua sendo a
  segunda ponta que obriga o manifesto a concordar.

- **D-DV-20 — entrou um invariante que o plano não pediu: `subagent` nunca sem
  `playbook`.** A pesquisa diz duas coisas que, juntas, tornam o despacho
  removível sem aviso: custom subagents são **experimentais** pela própria
  Cognition, e um admin de organização desliga o despacho por completo (opção
  *None* de "Default subagent model"), sem que nenhum arquivo versionado possa
  impedi-lo. Uma capacidade que declarasse só `subagent` ficaria sem caminho no
  dia em que o toggle virasse off, e o manifesto não perceberia. `test_nenhuma_
  capacidade_declara_subagent_sem_o_piso` fixa o piso; é a versão declarável do
  "o `playbook` continua sendo o caminho quando o despacho estiver desligado" que
  a Task 6 vai escrever em prosa.

---

## Task 6: documentação e fechamento

**Files:**
- Modify: `README.md`, `AGENTS.md`, `GUIA_DE_USO.md`, `docs/superpowers/STATUS.md`

- [ ] **Step 1: Meça**

```bash
python -m pytest -q 2>&1 | tail -2
python scripts/sync_skills.py --check
ruff check .
ls agents/*.md | wc -l ; ls agents/executors/*.md | wc -l ; ls -d skills/*/ | wc -l
```

- [ ] **Step 2: `GUIA_DE_USO.md` — a seção do Devin muda de fato**

Hoje ela manda usar o agente e o `playbook`. Passa a dizer que o Devin CLI
despacha subagente, onde os perfis moram, e que o `playbook` continua sendo o
caminho quando o despacho estiver desligado (admin da org, ou opção *None*).

- [ ] **Step 3: `README.md` e `AGENTS.md`**

A seção de coordenadores diz hoje que o despacho é do Claude Code e que as outras
plataformas usam `playbook`. Corrija com o recorte, sem apagar o `playbook`.

- [ ] **Step 4: `STATUS.md`**

Números medidos. Seção da fase: o defeito de partida (decisão registrada que a
fonte derrubou pela metade), o que entrou, **os seis pontos da doc interna que
não se sustentaram**, e o que continua no `playbook` e por quê.

Dívidas: `tools:` omitido por mapeamento não documentado — reabre se a Cognition
documentar; custom subagents são **experimentais** pela própria Cognition.

- [ ] **Step 5: Suíte verde, ruff limpo, `sync_skills.py --check` OK, commit**
