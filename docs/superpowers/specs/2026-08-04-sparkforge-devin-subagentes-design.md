# SparkForge AWS — Devin: perfis de subagente e paridade de despacho

**Data:** 2026-08-04
**Status:** desenhado, não implementado.
**Pesquisa de fontes:** [`knowledge/devin/agents-and-subagents.md`](../../../knowledge/devin/agents-and-subagents.md),
com URL e data por afirmação, e onze vetos `V-DV-*`.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: uma decisão registrada que a fonte derrubou pela metade

`parity.yaml`, linhas 18-29, declara como deliberada a ausência de `subagent`
entre os mecanismos:

> `subagent` **NÃO** é mecanismo declarado neste manifesto, de propósito. Despacho
> de subagente é capacidade de HARNESS do Claude Code, não conteúdo deste
> repositório: **nenhuma outra plataforma tem um equivalente** que este
> repositório possa acionar. […] É o que Devin Desktop, Devin CLI, Codex e
> Copilot CI conseguem consumir **sem harness de subagente**.

A pesquisa de fontes mediu que a frase universal é **falsa por contraexemplo**. O
Devin CLI despacha subagente (`run_subagent` / `read_subagent`), lê perfis em
`.devin/agents/`, `~/.config/devin/agents/` e **`.agents/agents/`** — onde este
repositório já publica os oito coordenadores —, e importa `.claude/agents/*.md`
com a frase *"Each `.md` file becomes a subagent profile"*.

E há um segundo achado que muda mais do que o primeiro:
**`.agents/skills/<name>/SKILL.md` é caminho de descoberta nativo do Devin**, não
convenção deste repositório. Skills aceitam `subagent: true` e `agent: <perfil>`.

O que **sobrevive** da decisão original: o `playbook` como piso portátil para
`codex` e `copilot_ci`, que não foram objeto desta pesquisa; e o argumento de
harness, agora com o recorte certo. A distinção defensável não é *"Claude Code
tem, os outros não"* — é **"o perfil é nosso, o despacho é deles"**.

Nenhum arquivo versionado liga subagentes nem fixa modelo: `subagents_enabled` é
chave de usuário, o default resolve por roteador no spawn, e admin da organização
pode sobrescrever — inclusive com a opção *None*, que desliga o despacho por
completo.

## 2. Objetivo

Os coordenadores e executores deste repositório funcionando como **perfis de
subagente de verdade no Devin**, e as skills declarando despacho onde ele é o
certo — sem que o repositório afirme controle sobre o que o harness decide.

**Critério de sucesso central:** um espelho regenerado não produz diff, todo
perfil declara a fronteira de manutenção destrutiva, e `parity.yaml` só lista
plataforma cujo suporte a `subagent` a pesquisa confirma.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| Escrever `model:` nos perfis | O default resolve por roteador no spawn e o admin da org sobrescreve. Escrever seria fingir controle; e o identificador correto (`swe-1-7`, com hífen) é dado que envelhece — a doc interna já errava com ponto |
| `.devin/config.json` versionado com `permissions` e `hooks` | Chaves de projeto existem, mas configuram o ambiente de quem roda, não a capacidade do repositório. Fase própria, se alguém quiser |
| Traduzir `tools:` | Mapeamento de valores **não documentado** (`Bash` → `exec`?). Chute em campo de permissão concede ou nega errado |
| Codex e Copilot CI | Não foram objeto da pesquisa. Continuam no `playbook`, e afirmar mais seria repetir o defeito do transporte HTTP da Fase 1 |

## 3. Decisões de desenho

### D-1 — fonte única, espelho gerado

`agents/*.md` e `skills/*/SKILL.md` continuam sendo o que se edita.
`scripts/sync_skills.py` deixa de **copiar** e passa a **gerar** cada espelho no
formato que a plataforma lê.

O invariante muda de *"os arquivos são idênticos"* para **"o espelho é exatamente
o que o tradutor produz"**. É mais forte: a igualdade byte a byte não pegaria um
campo que a plataforma exige e a fonte não tem.

A alternativa recusada era manter cópia e só usar o que as duas plataformas
aceitam — o que descartaria `subagent: true`, que é só do Devin, e congelaria a
paridade no mínimo denominador comum.

### D-2 — `tools:` é omitido no espelho do Devin, com o motivo escrito

O campo é aceito, e o **mapeamento de valores não está documentado**. Omitido, o
subagente herda o que o harness dá, que é o comportamento que a própria
documentação descreve. O tradutor registra a omissão e a razão, para ninguém
"corrigir" isso sem medir.

### D-3 — nenhum `model:` é escrito, e isso é invariante

Três medições sustentam: o default resolve por roteador **no momento do spawn**;
admin da organização sobrescreve, inclusive desligando; e o identificador literal
é `swe-1-7`, não `swe-1.7` — a doc interna que motivou esta fase já errava nele.

A preferência por SWE-1.7 é do **ambiente**, onde ela de fato manda. Escrevê-la
no repositório daria a impressão de controle e envelheceria no primeiro rename.

### D-4 — a fronteira de segurança vai em todo perfil

`ask_user_question` é **sempre negado a subagente**. A regra 10 do `CLAUDE.md`
deste repositório — confirmação explícita de escopo e retenção antes de
manutenção destrutiva — é, portanto, **inalcançável de dentro de um subagente**.

Todo perfil declara em `## Não faz` que não executa manutenção destrutiva:
recomenda, e a confirmação acontece no agente pai, que tem a pergunta disponível.
Travado por teste sobre o corpus de perfis, no molde de `test_no_area_is_orphan`.

Sem isso, o modo de falha é mudo: um subagente que precisasse confirmar seguiria
sem confirmar, ou pararia sem dizer por quê.

### D-5 — `agent:` é derivado, não mantido à mão

Cada coordenador já declara `skills:` no frontmatter. A relação skill → perfil
existe e é mantida num lugar só; o tradutor **deriva** `agent:` dela.

Criar uma segunda lista seria o passo que alguém esquece — o mesmo argumento que
fez o roteamento de coordenador virar dado na Fase 4, e que a Fase 5c reencontrou
nas duas listas `EXTRACTORS` mantidas à mão.

### D-6 — despacha quem é investigação fechada

`subagent: true` vai nas skills cujo resultado o pai **resume**:
`review-emr-cluster`, `review-data-validation`, `review-glue-terraform`,
`review-pyspark-pr` e os `analyze-*`.

Fica de fora quem dirige o loop ou precisa perguntar. `sparkforge-diagnose` abre
o case e roteia; despachá-la jogaria o ciclo de vida do case para um contexto que
não volta — e o case é justamente o que faz a investigação atravessar sessões.

### D-7 — o parágrafo do `parity.yaml` não é reescrito

Ele ganha desvio registrado: a frase universal caiu por contraexemplo, e o que
sobrou dela é o recorte. Preservar o texto original é a convenção do repositório
(`STATUS.md`, "Como manter este arquivo honesto"), e aqui ela vale duplamente —
o parágrafo documenta **por que** o projeto recusou afirmar paridade inexistente,
que é a disciplina que esta fase mantém ao não estender a `codex` e `copilot_ci`.

## 4. Superfície

| Onde | O quê |
|---|---|
| `scripts/sync_skills.py` | copiador → tradutor, com formato por plataforma |
| `.agents/agents/*.md` | perfis gerados: sem `tools:`, sem `model:` |
| `.agents/skills/*/SKILL.md` | gerados com `subagent:` e `agent:` onde D-6 manda |
| `agents/*.md` | `## Não faz` com a fronteira de manutenção destrutiva |
| `parity.yaml` | mecanismo `subagent`, capacidades tocadas, desvio registrado |
| `knowledge/INDEX.md` | já aponta para a pesquisa; conferir |
| `AGENTS.md`, `GUIA_DE_USO.md`, `README.md` | como rodar no Devin com despacho |

## 5. Prova

| Invariante | Pega |
|---|---|
| Regenerar não produz diff | espelho editado à mão |
| Todo perfil declara a fronteira de manutenção destrutiva | perfil novo sem ela |
| `agent:` nomeia perfil que existe **e** que declara aquela skill | relação quebrando de um lado |
| Nenhum `model:` em perfil nenhum | modelo fixado sem medição |
| Capacidade com `subagent` só lista plataforma que a pesquisa confirma | paridade afirmada e não verificada |

O quinto é o que herda a lição da Fase 1: `parity.yaml` afirmava transporte HTTP
que nenhum teste tocava, e o defeito só apareceu quando alguém subiu o servidor.

## 6. Critérios de sucesso

1. `sync_skills.py --check` continua sendo o gate, agora sobre derivação e não igualdade
2. `.agents/agents/*.md` não tem `tools:` nem `model:`, com teste
3. Todo perfil de `agents/` declara a fronteira de manutenção destrutiva, com teste
4. `agent:` de toda skill despachável nomeia perfil existente que a declara — bidirecional
5. `sparkforge-diagnose` **não** é despachável, e o motivo está escrito
6. `parity.yaml` declara `subagent` para `devin_cli`, e para `devin_desktop` com o recorte "Devin Local agent, Subagents (Preview)"
7. `codex` e `copilot_ci` seguem sem `subagent`
8. O parágrafo original de `parity.yaml` está preservado, com desvio registrado ao lado
9. Nenhum identificador de modelo aparece em arquivo versionado
10. `README.md`, `AGENTS.md` e `GUIA_DE_USO.md` dizem como rodar no Devin com despacho

## 7. Riscos

| Risco | Mitigação |
|---|---|
| O Devin muda formato de perfil e o tradutor quebra em silêncio | O gate de derivação falha alto; e a pesquisa fica em `knowledge/` com data, na watchlist do `refresh_knowledge` |
| Custom subagents são declarados **experimentais** pela Cognition | O `playbook` continua existindo e funcionando: se o despacho sumir, o piso permanece |
| Admin da org desliga subagentes (*None*) | Mesma mitigação: o piso não depende de despacho |
| `subagent: true` numa skill que precisaria perguntar | D-6 e o critério 5; a fronteira do D-4 é a segunda rede |
