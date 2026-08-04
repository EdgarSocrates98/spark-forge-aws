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

- [ ] **Step 1: Escreva o teste que falha**

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

- [ ] **Step 2: Rode e veja falhar**

Run: `python -m pytest tests/test_sync_render.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_agent'`

- [ ] **Step 3: Implemente**

`render_agent(text, platform)` separa o frontmatter do corpo, aplica a
transformação da plataforma, e remonta preservando a ordem das chaves que
sobrarem. Para `claude` e `github`, devolve o texto **idêntico** — sem
round-trip de YAML, que reordenaria chaves e produziria diff onde não há
mudança.

Para `devin`: remove a linha `tools:` (e as continuações dela, se houver forma
de lista), e **nunca** acrescenta `model:`.

O comentário no código diz por quê, citando a pesquisa — quem vier depois vai
querer "completar" o frontmatter.

- [ ] **Step 4: Rode e commite**

---

## Task 2: o gate passa a comparar contra a renderização

**Files:**
- Modify: `scripts/sync_skills.py`, `tests/test_agents_parity.py`

- [ ] **Step 1: Teste primeiro**

O gate hoje é `filecmp.cmp(src, dst, shallow=False)`. Ele passa a comparar
`dst.read_text()` com `render_agent(src.read_text(), platform)`, e a plataforma
sai do próprio alvo — `.agents/` é `devin`, `.claude/` é `claude`,
`.github/` é `github`.

Escreva o teste que prova que **espelho editado à mão é pego**: renderize,
grave, altere um byte do espelho, e confirme que o gate acusa `DIVERGENTE`.

- [ ] **Step 2: Rode, regenere, leia o diff**

Run: `python scripts/sync_skills.py` e depois `git diff .agents/`

O diff esperado é **só a remoção de `tools:`** nos treze perfis (oito
coordenadores + cinco executores). Se aparecer reordenação de chave ou mudança
de corpo, o renderizador está fazendo round-trip de YAML — corrija antes de
seguir.

- [ ] **Step 3: `TestNoPlatformKnowledge` continua valendo?**

`tests/test_agents_parity.py` proíbe marcadores (`threshold:`, `runtime_scope:`,
`retrieved:`) nos espelhos de plataforma — a Fase 4a bateu nele. Confirme que a
renderização não introduz nem remove marcador, e que o teste segue verde.

- [ ] **Step 4: Commite**

---

## Task 3: a fronteira de manutenção destrutiva

**Files:**
- Modify: `agents/*.md` (os oito), `agents/executors/*.md` (os cinco)
- Create: teste em `tests/test_agents_parity.py`

- [ ] **Step 1: O teste que falha**

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

- [ ] **Step 2: Rode e veja falhar**

Expected: FAIL listando os treze.

- [ ] **Step 3: Escreva a fronteira em cada perfil**

Na seção `## Não faz` — que os executores já têm e os coordenadores usam desde a
Fase 5b. O texto diz: não executa manutenção destrutiva (expiração de snapshot,
remoção de arquivo órfão, `DROP`, sobrescrita de partição); recomenda, e a
confirmação de escopo e retenção acontece com quem tem a pergunta disponível.

**Não copie a mesma frase treze vezes sem ler o perfil.** Um coordenador de
Athena e um executor de inventário chegam perto disso por caminhos diferentes, e
a fronteira tem que fazer sentido no contexto de cada um.

- [ ] **Step 4: Regenere os espelhos, rode, commite**

---

## Task 4: skills que despacham

**Files:**
- Modify: `scripts/sync_skills.py`, `skills/*/SKILL.md` (as despacháveis), `tests/test_sync_render.py`

- [ ] **Step 1: Meça a relação skill → perfil**

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

- [ ] **Step 2: `render_skill`, com teste primeiro**

Despacháveis, por D-6 do spec: `review-emr-cluster`, `review-data-validation`,
`review-glue-terraform`, `review-pyspark-pr` e os `analyze-*`.

**`sparkforge-diagnose` NÃO é despachável** — ela abre o case e roteia, e
despachá-la jogaria o ciclo de vida do case para um contexto que não volta. O
teste fixa isso, e o motivo vai no código.

O renderizador acrescenta `subagent: true` e `agent: <perfil>` ao frontmatter do
espelho `.agents/skills/`, e não toca em `.claude/skills/`.

- [ ] **Step 3: O invariante bidirecional**

```python
def test_agent_de_skill_nomeia_perfil_que_a_declara():
    """Relacao que quebra de um lado so e a familia de defeito que a Fase 5c
    achou nas duas listas EXTRACTORS mantidas a mao."""
```

Para cada skill com `agent: X`, o perfil `X` existe **e** declara aquela skill
em `skills:`.

- [ ] **Step 4: Regenere, leia o diff, commite**

---

## Task 5: `parity.yaml`

**Files:**
- Modify: `parity.yaml`, `tests/test_capability_parity.py`

- [ ] **Step 1: O mecanismo e o recorte**

`subagent` entra em `mechanisms`. As capacidades de coordenação declaram
`subagent` para `devin_cli`, e para `devin_desktop` **com o recorte medido**: só
no Devin Local agent, com o toggle "Subagents (Preview)".

`codex` e `copilot_ci` **não** ganham — a pesquisa não os cobriu, e afirmar mais
seria repetir o defeito do transporte HTTP da Fase 1, que este mesmo arquivo cita
como razão de ser da regra.

- [ ] **Step 2: O parágrafo original fica**

Ele ganha desvio registrado ao lado: a frase universal caiu por contraexemplo, e
o que sobrou é *o perfil é nosso, o despacho é deles*. Preservar o texto é a
convenção do repositório, e aqui vale duplamente — ele documenta a disciplina que
esta fase mantém ao não estender a `codex` e `copilot_ci`.

- [ ] **Step 3: O invariante que herda a lição da Fase 1**

Capacidade que declara `subagent` só pode listar plataforma cujo suporte a
pesquisa confirma. Derive do `knowledge/devin/agents-and-subagents.md` se der;
se não der sem parser frágil, use lista literal **com o ponteiro para a fonte no
comentário**, e diga no relatório por que não deu para derivar.

- [ ] **Step 4: Rode e commite**

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
