# Agents e subagents no Devin — o que a fonte oficial diz

Esta página existe por um motivo único: a nota de `parity.yaml` (linhas 18-29)
declara que **`subagent` não é mecanismo declarável** porque "despacho de
subagente é capacidade de HARNESS do Claude Code, não conteúdo deste
repositório: **nenhuma outra plataforma tem um equivalente que este repositório
possa acionar**". Uma doc interna trazida pelo usuário
(`guia_devin_agents_subagents.md`, na raiz) afirma o contrário para o Devin.

A doc interna foi tratada como **hipótese**, não como fonte. Cada afirmação
abaixo tem URL e `retrieved:`. Onde a fonte oficial contrariou a doc interna, a
contradição está escrita explicitamente, com as duas versões lado a lado.

**Coleta desta rodada: 2026-08-04.**

Regra desta página, herdada do [`INDEX.md`](../INDEX.md): o que não foi
encontrado em fonte oficial está escrito como **não encontrado**, não como
inferência. Argumento por ausência está marcado como tal, com a página que foi
lida.

**Nota de método.** As páginas de `docs.devin.ai` foram lidas na forma
`*.md` (markdown bruto servido pelo próprio site, ex.
`https://docs.devin.ai/cli/subagents.md`), não na forma renderizada. Todas as
citações abaixo são literais desse markdown.

---

## 0. Os dez veredictos, em uma linha cada

| # | Pergunta | Veredicto | Consequência imediata |
|---|---|---|---|
| 1 | Devin CLI despacha subagente? | **Confirmada** | Sim, e importa `.claude/agents/*.md` e lê `.agents/agents/` — dois diretórios que este repositório **já tem** |
| 2 | Devin Desktop despacha? | **Confirmada, com recorte** | Sim, mas só no **Devin Local agent**; a documentação de Cascade não menciona subagente |
| 3 | Modelo por subagente — campo existe? Nomes `swe-1.7`/`glm-5.2`/`kimi-k2.7`? | **Campo confirmado; nomes CONTRADITOS** | O campo é `model:`. Os identificadores literais são `swe-1-7`, `glm-5-2`, `kimi-k2-7` (hífen, não ponto) e vêm da tabela de preços do **Desktop** — nenhuma página do CLI os documenta como valores aceitos |
| 4 | Modelo default do subagente | **Confirmada — e é motivo para NÃO declarar `model:`** | "não é um nome de modelo fixo — resolve por um router no momento do spawn", e um admin de org pode sobrescrever |
| 5 | Foreground/background, `max-nesting`, limites | **Confirmada** | Ambos os modos existem; `max-nesting` é campo real (desde 2026-05-26). Limite default: subagente **não** gera subagente |
| 6 | Contrato de contexto e de saída | **Confirmada — e não há contrato** | Não herda histórico do pai; a saída é texto livre que o pai lê e resume. Nenhum schema documentado |
| 7 | `config.json`, `subagents_enabled`, `subagent_default_model` | **Parcialmente contradita** | Os dois arquivos existem e `subagents_enabled` existe — mas é chave **de topo**, não dentro de `agent`. `subagent_default_model` e `alternative_models` **não existem** |
| 8 | Skills — `.agents/skills/` é formato que o Devin lê? | **Confirmada** | `.agents/skills/<name>/SKILL.md` é caminho de descoberta **documentado e nativo** do Devin CLI. Não é convenção própria deste repo |
| 9 | MCP no Devin CLI | **Confirmada** | `mcp_config.json` com chave `mcpServers`, stdio e HTTP |
| 10 | `!ultra`, `!fast`, `!swe`, `Ctrl+B` | **`Ctrl+B` confirmada; os três `!` NÃO ENCONTRADOS** | `!` é o prefixo de **bash mode**, não de troca de modelo. Existe `/fast` como slash command |

---

## 1. Devin CLI despacha subagente? — CONFIRMADO

> "Subagents let the main agent spawn independent workers to handle subtasks. A
> subagent shares tools and codebase context with the parent, but operates in
> its own conversation chain -- it does not inherit the parent's conversation
> history."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

Existem dois perfis embutidos e perfis customizados:

| Profile | Description | Tool Access | Model |
|---|---|---|---|
| `subagent_explore` | Read-only codebase exploration and research | Read-only codebase tools plus web search; cannot edit files or fetch arbitrary URLs | Default subagent model (SWE-1.6 by default) |
| `subagent_general` | General-purpose tasks including code changes | Full tool access (foreground) or pre-approved tools only (background) | Same model as the parent agent |

> Tabela reproduzida de https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

As tools que implementam o despacho são `run_subagent` e `read_subagent`.

### 1.1 Onde o arquivo mora — e por que isto é o achado que derruba a nota

> "Custom subagents are defined as markdown files under `agents/`, using either
> layout:
> * **Flat file** — `agents/<name>.md` (the same convention used by Claude Code,
>   Cursor, and other tools). The file name (without `.md`) becomes the
>   profile's identifier.
> * **Directory** — `agents/<name>/AGENT.md`. The directory name becomes the
>   profile's identifier. `AGENTS.md`, `agent.md`, and `agents.md` are also
>   accepted as the file name (if multiple are present, `AGENT.md` takes
>   precedence, then `AGENTS.md`, `agent.md`, `agents.md`)."

Diretórios de descoberta, exatamente como a página os lista:

| Escopo | Caminho |
|---|---|
| Projeto | `.devin/agents/` |
| Projeto ("Also supported") | `.agents/agents/` |
| Global (Linux/macOS) | `~/.config/devin/agents/` |
| Global (Windows) | `%APPDATA%\devin\agents\` |

E, em seção própria, **importação de outra ferramenta**:

> "### Importing From Other Tools
> Custom subagents are also imported from Claude Code's agent format:
>
> | Source | File Pattern |
> | `.claude/agents/*.md` | Each `.md` file becomes a subagent profile |
>
> Claude Code agent files use `tools` instead of `allowed-tools` in their
> frontmatter. Both formats are supported automatically."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

**Este repositório já satisfaz os dois caminhos.** `ls` na raiz mostra
`.claude/agents/` e `.agents/agents/`, ambos com os mesmos oito `.md` de agente
mais `executors/`. Ou seja: a premissa "nenhuma outra plataforma tem um
equivalente que este repositório possa acionar" é falsa **por conteúdo que o
repositório já publica hoje**, sem nenhuma mudança.

### 1.2 Ambiguidade medida: `agents/` na raiz é caminho de descoberta?

A frase de abertura diz "under `agents/`", e o changelog do CLI diz:

> "Add custom subagent profiles: define specialized subagents with their own
> system prompts, tools, and models via `AGENT.md` files in your project's
> `agents/` directory (experimental)"
> — `<Update label="v2026.3.20-2" description="March 23, 2026">`

> https://docs.devin.ai/cli/changelog/stable.md (retrieved 2026-08-04)

Mas a aba "Project-specific" da página de subagents lista **apenas**
`.devin/agents/` e `.agents/agents/`. **Isto é ambíguo**: a documentação não
afirma, em lugar nenhum que eu tenha lido, que um `agents/` **na raiz do
repositório** (sem prefixo `.devin/` ou `.agents/`) seja varrido. Este
repositório mantém `agents/` na raiz *e* cópias em `.claude/agents/` e
`.agents/agents/` — as duas últimas são as documentadas. Não tratar o `agents/`
da raiz como caminho Devin sem verificação empírica.

### 1.3 Ressalva que a própria fonte impõe: isto é experimental

> "Custom subagents are **experimental**. The format, behavior, and
> configuration options may change in future releases."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

O mesmo aviso aparece para `subagent:`/`agent:` em skills:

> "Running skills as subagents is **experimental**. The `subagent` and `agent`
> frontmatter fields may change in future releases."

> https://docs.devin.ai/cli/extensibility/skills/creating-skills.md (retrieved 2026-08-04)

---

## 2. Devin Desktop despacha? — CONFIRMADO, mas só no Devin Local agent

A capacidade não está documentada como "Devin Desktop"; está documentada como
propriedade do **Devin Local agent**:

> "### Subagents
> The Devin Local agent can spawn independent [subagents](/cli/subagents) to
> handle subtasks — either in the foreground or background. Subagents share
> tools and codebase context with the parent agent but operate in their own
> conversation chain.
>
> Subagents are controlled by the **Subagents (Preview)** toggle in
> `Devin Settings`.
>
> Beyond the built-in profiles, you can define your own subagents as markdown
> files under `agents/` using either layout:
> * **Flat file** — `agents/<name>.md` [...]
> * **Directory** — `agents/<name>/AGENT.md` [...]
>
> See the [subagents documentation](/cli/subagents) for where these directories
> are discovered and how to configure a profile."

> https://docs.devin.ai/desktop/devin-local.md (retrieved 2026-08-04)

E a página do CLI confirma o mesmo toggle do outro lado:

> "The change applies live — a running session picks it up without restarting.
> In Devin Desktop, the same capability is the **Subagents (Preview)** toggle in
> settings."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

**Em que difere da CLI:** a página do Desktop **não redefine nada** — ela
delega explicitamente à página do CLI para descoberta de diretório e formato de
perfil. Não há formato Desktop separado.

**O recorte importa.** Foram lidas `desktop/cascade/cascade.md`,
`desktop/cascade/skills.md`, `desktop/cascade/workflows.md`,
`desktop/cascade/agents-md.md`, `desktop/advanced.md` e
`desktop/agent-command-center.md`: **nenhuma menciona subagente**
(retrieved 2026-08-04). Argumento por ausência, marcado como tal: subagente é
documentado como capacidade do agente **Devin Local**, e não do motor Cascade.

Um caso especial, para não confundir com despacho customizável:

> "Fast Context is a specialized subagent that retrieves relevant code from your
> codebase up to 20x faster using SWE-grep models"

> https://docs.devin.ai/desktop/context-awareness/fast-context.md, via https://docs.devin.ai/llms.txt (retrieved 2026-08-04)

Isso é subagente **embutido do produto**, não perfil que este repositório
declare.

---

## 3. Modelo por subagente — campo CONFIRMADO, nomes CONTRADITOS

### 3.1 O campo existe, e o nome literal é `model`

Tabela de frontmatter, reproduzida da fonte:

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | file or directory name | Identifier for the profile (must not conflict with built-in profiles) |
| `description` | string | none | Shown to the agent when selecting a profile |
| `model` | string | default subagent model (SWE-1.6 by default) — **not** the parent's model | Override the model used by this subagent |
| `allowed-tools` | list | all tools | Restrict which tools the subagent can use. Cannot grant `ask_user_question`, which is always withheld from subagents. |
| `max-nesting` | integer | none | Override the maximum nesting depth, allowing this subagent to spawn its own subagents |

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

Nenhum campo é marcado como obrigatório: `name` cai para o nome do arquivo ou
diretório, e todos os demais têm default. Um `.md` com frontmatter vazio e só o
system prompt é válido pela tabela.

O exemplo oficial completo:

```markdown
---
name: reviewer
description: Reviews code changes for correctness and style
model: sonnet
allowed-tools:
  - read
  - grep
  - glob
  - exec
---

You are a code review subagent. Your job is to review code changes
thoroughly and report findings back to the parent agent.
```

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

### 3.2 Quais valores são aceitos — e a contradição com a doc interna

A página de modelos do CLI **não publica uma lista de identificadores**. O que
ela publica é:

> "Models release frequently. We typically support the latest and greatest
> models from **Anthropic**, **OpenAI**, **Google**, and **Cognition** within
> minutes of their launch. We also support a number of **leading open source
> models** like **DeepSeek**, **Kimi**, and **GLM**."

> "Short names like `opus`, `sonnet`, `swe`, `codex`, and `gemini` always
> resolve to the latest version in that model family."

> https://docs.devin.ai/cli/models.md (retrieved 2026-08-04)

E o default do agente principal no `config.json` é literal:

```json
{
  "agent": {
    "model": "swe-1-6-fast"
  }
}
```

> https://docs.devin.ai/cli/models.md e https://docs.devin.ai/cli/reference/configuration/config-file.md (retrieved 2026-08-04)

A página de skills confirma que o `model:` do frontmatter usa o mesmo
vocabulário:

> "The model name uses the same values as the `--model` CLI flag (e.g., `opus`,
> `sonnet`, `swe`, `codex`). See [Models](/cli/models) for the full list."

> https://docs.devin.ai/cli/extensibility/skills/creating-skills.md (retrieved 2026-08-04)

**Onde os identificadores completos aparecem:** na tabela de custo de modelos do
**Devin Desktop**, como `model_uid`:

| `model_uid` | `label` | `model_provider` |
|---|---|---|
| `swe-1-6-fast` | SWE-1.6 Fast | `MODEL_PROVIDER_WINDSURF` |
| `swe-1-7` | SWE-1.7 | `MODEL_PROVIDER_WINDSURF` |
| `swe-1-7-lightning` | SWE-1.7 Lightning | `MODEL_PROVIDER_WINDSURF` |
| `glm-5-1` | GLM-5.1 | — |
| `glm-5-2` | GLM-5.2 | — |
| `kimi-k2-5` / `kimi-k2-6` / `kimi-k2-7` | Kimi K2.5 / K2.6 / K2.7 | — |
| `kimi-k3-low` / `kimi-k3-high` / `kimi-k3-max` | Kimi K3 (variantes) | — |

> `export const modelCostData` em https://docs.devin.ai/desktop/models.md (retrieved 2026-08-04)

**CONTRADIÇÃO EXPLÍCITA com a doc interna do usuário.**

| | Doc interna (`guia_devin_agents_subagents.md`) | Fonte oficial |
|---|---|---|
| §5.1, §6 | `model: glm-5.2` no frontmatter | O identificador literal é `glm-5-2`. `GLM-5.2` (com ponto) é o **label** de exibição, não o `model_uid` |
| §2.1 | Modelos "SWE-1.7", "SWE-1.7 Lightning", "SWE-1.6" | Labels corretos. Identificadores: `swe-1-7`, `swe-1-7-lightning`, `swe-1-6-fast` |
| §4.1 | `"alternative_models": ["glm-5.2", "kimi-k2.7"]` | Chave `alternative_models` **não existe** (ver §7) e os nomes têm ponto onde a fonte usa hífen |

**Ambiguidade que não vou resolver na conveniência:** a fonte que enumera
`glm-5-2` e `kimi-k2-7` é a tabela de preços do **Desktop**, não a documentação
do CLI. Nenhuma página do CLI que eu li declara que `--model glm-5-2` ou
`model: glm-5-2` num `agents/*.md` seja aceito. O que a doc do CLI garante são
os *short names* `opus`, `sonnet`, `swe`, `codex`, `gemini` (e `gpt`, citado em
"Model Selection Tips"). Tratar qualquer outro literal como aceito pelo CLI é
inferência, não leitura.

### 3.3 A doc interna erra também no que o `model:` faz por padrão

A doc interna (§5.1) diz que o default "geralmente resolve para uma variante do
`swe-1.6` ou `swe-1.7-lightning` dependendo do plano". A fonte é mais estreita e
mais precisa: o default resolve para SWE-1.6 (variante conforme o tier), e
`swe-1-7-lightning` não é citado como default de subagente em lugar nenhum.

---

## 4. Qual o modelo default de um subagente — CONFIRMADO, e é o argumento contra declarar `model:`

Esta é a pergunta que decide se o repositório deve escrever `model:` nos seus
arquivos de agente. A fonte responde de forma que **desaconselha**:

> "The **default subagent model** is not a fixed model name — it resolves
> through a router at spawn time, and an admin can override it (see below). With
> the default **Subagent router** setting it resolves to SWE-1.6 (a faster or
> slower SWE-1.6 variant depending on your plan tier)."

E, por perfil:

| Profile | Model used |
|---|---|
| `subagent_explore` | The **default subagent model** — a fast, cheap model (SWE-1.6 by default) |
| `subagent_general` | **The same model as the parent agent** — whatever you selected in the model picker |
| Custom subagents | The `model` field in the definition file if set, otherwise the **default subagent model** |

E o controle de organização:

> "Administrators can govern which model subagents use — and whether subagents
> run at all — through the **Default subagent model** setting in the
> org/enterprise settings. This setting controls the model for
> `subagent_explore` and for custom subagents that don't pin a `model:` — it
> does not change `subagent_general`."

Com três opções: **Subagent router (default)**, **A specific model**, e
**None** — "Disables subagents entirely — Devin will not spawn any subagents."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

**Leitura para o desenho, sem escolher a versão conveniente.** A fonte diz duas
coisas em tensão:

1. Se o repositório **não** declara `model:`, o modelo é decidido por um router
   do harness e pode ser sobrescrito por um admin da organização do usuário. O
   repositório não controla nem sabe qual foi.
2. Se o repositório **declara** `model:`, ele é o único jeito de rodar um
   subagente com escrita fora do modelo caro do pai — a fonte diz isso
   literalmente: "`model:` in the definition file is the only way to run a
   *write-capable* subagent on a model other than the parent's".

Ou seja: declarar `model:` **não** é fingir controle — é o único ponto de
controle que existe. Mas declarar um literal como `glm-5-2` **é** fingir
conhecimento, porque nenhuma página do CLI documenta esse literal como aceito, e
Team Settings permite ao admin restringir quais modelos existem:

> "Enterprise teams can restrict which models are available through
> [Team Settings](/cli/enterprise/team-settings)."

> https://docs.devin.ai/cli/models.md (retrieved 2026-08-04)

A conclusão defensável é a do meio: se declarar, declarar apenas *short name*
documentado (`swe`, `sonnet`, `opus`, `codex`, `gemini`), nunca `model_uid` de
tabela de preços do Desktop.

---

## 5. Foreground / background, `max-nesting`, limites — CONFIRMADO

### 5.1 Os dois modos

> **Foreground:** "Runs inline in your session. The parent agent pauses and
> waits for the subagent to finish before continuing. You can approve or deny
> tool calls as they come up."
>
> **Background:** "Runs in parallel while the parent agent continues working.
> The parent is automatically notified when the subagent completes. Unapproved
> tools are automatically denied."

Permissões diferem por modo, e isso é consequência operacional real:

> "**Background subagents** inherit any tool permissions you have already
> granted during the current session. Any tool that has not been pre-approved is
> automatically denied. Background subagents cannot prompt you for new
> permissions."

Não há campo de frontmatter que fixe o modo. Quem escolhe é o agente pai no
momento do spawn — a tabela de frontmatter (§3.1) não tem chave para isso.
**Não encontrado:** nenhum campo `mode`, `background`, ou equivalente.

### 5.2 `max-nesting` e o limite default

> "By default, subagents cannot spawn their own subagents — only the root agent
> can. Subagent tools (`run_subagent` and `read_subagent`) are disabled inside a
> subagent to prevent unbounded nesting.
>
> However, **custom subagent profiles** can opt in to nested spawning by setting
> the `max-nesting` field in their frontmatter."

Com o exemplo literal:

```
Root agent (depth 0)
└── Custom subagent (depth 1) — can spawn children
    └── Child subagent (depth 2) — can spawn children
        └── Grandchild subagent (depth 3) — cannot spawn (depth limit reached)
```

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

Data de introdução:

> "Custom subagent profiles can opt in to nested subagent spawning via the
> `max-nesting` frontmatter field, overriding the default depth limit."
> — `<Update label="v2026.5.26-0" description="May 26, 2026">`

> https://docs.devin.ai/cli/changelog/stable.md (retrieved 2026-08-04)

### 5.3 Limite de concorrência — NÃO ENCONTRADO

Nenhuma página lida declara um teto de subagentes simultâneos, nem chave de
config para isso. O que existe é aviso de **custo**, não de limite:

> "Because cost scales with the number of subagents, tasks that fan out into
> many subagents (or nest them) cost more. Use subagents deliberately when the
> parallelism or focused context is worth the additional spend."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

Argumento por ausência, marcado como tal: lidas `cli/subagents.md`,
`cli/reference/configuration/config-file.md` e `cli/reference/commands.md`.

---

## 6. Como o subagente recebe contexto e devolve resultado — CONFIRMADO, e NÃO HÁ CONTRATO

**Entrada.** O subagente herda *tools* e *contexto de codebase*, e **não**
herda histórico de conversa:

> "A subagent shares tools and codebase context with the parent, but operates in
> its own conversation chain -- it does not inherit the parent's conversation
> history."

O prompt de tarefa vem do pai: "There is no way to name a model for a subagent
in a prompt — the `run_subagent` tool takes a *profile*, not a model."

**Saída.** Texto livre, mediado pelo pai:

> "You do not see the subagent's raw output directly. When a subagent finishes,
> the parent agent reads the result and summarizes the key findings and actions
> for you."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

**Não encontrado:** nenhum schema, formato estruturado, JSON de retorno ou
contrato de saída para subagente Devin. O único mecanismo nomeado é a tool
`read_subagent`, que a documentação cita sem especificar formato de retorno.

**Consequência direta para o desenho deste repositório.** Se um agente
`agents/*.md` deste repo precisa devolver algo verificável (por exemplo, um
`case.yaml` ou um bloco de achados anotado), essa garantia tem de vir do
**system prompt do próprio arquivo** — o harness não a fornece. Isso é
exatamente igual ao Claude Code, e é um ponto a favor de o método continuar
morando no arquivo, não no harness.

Uma capacidade adicional que a fonte confirma, relevante para o `parity.yaml`:

> "Subagents can now call MCP tools directly."
> — `<Update label="v2026.4.30-0" description="April 30, 2026">`

> https://docs.devin.ai/cli/changelog/stable.md (retrieved 2026-08-04)

Um subagente Devin pode chamar as tools MCP do `sparkforge`. O mecanismo `mcp`
declarado hoje em `parity.yaml` não é perdido dentro de um subagente.

---

## 7. Configuração — PARCIALMENTE CONTRADITA

### 7.1 Os arquivos existem, exatamente com os caminhos que a doc interna cita

| Escopo | Caminho |
|---|---|
| Global (macOS/Linux) | `~/.config/devin/config.json` |
| Global (Windows) | `%APPDATA%\devin\config.json` |
| Projeto (versionado) | `.devin/config.json` |
| Projeto (gitignored) | `.devin/config.local.json` |

> https://docs.devin.ai/cli/reference/configuration/config-file.md (retrieved 2026-08-04)

O formato é JSON **com comentários** estilo JavaScript.

### 7.2 `subagents_enabled` — REAL, mas no lugar errado na doc interna

Chave real, documentada com seção própria:

> "### subagents_enabled *(user only)*
> Control whether the agent can delegate work to subagents. When disabled, the
> `run_subagent` and `read_subagent` tools are removed, so the agent does all
> the work itself. Changing this setting applies live — a running session picks
> it up without restarting."
>
> | `true` | The agent can spawn subagents (default) |
> | `false` | Subagents are disabled for this user |

E o exemplo oficial mostra a posição:

```json
// ~/.config/devin/config.json
{
  "subagents_enabled": false
}
```

> https://docs.devin.ai/cli/subagents.md e https://docs.devin.ai/cli/reference/configuration/config-file.md (retrieved 2026-08-04)

No "Full Config Reference", `subagents_enabled` aparece como chave **de topo**,
irmã de `agent`, não dentro dele:

```json
{
  "agent": {
    "model": "swe-1-6-fast",
    "show_history_on_continue": true
  },
  ...
  "subagents_enabled": true,
  ...
}
```

**CONTRADIÇÃO com a doc interna (§4.1):** ela põe `subagents_enabled` **dentro**
de `"agent"`. A fonte a põe no topo, e a marca "(user only)" — isto é, ela **não
é aceita** no `.devin/config.json` de projeto. O objeto `agent` documentado tem
exatamente duas chaves: `model` e `show_history_on_continue`.

### 7.3 `subagent_default_model` e `alternative_models` — NÃO EXISTEM

Busca literal por `subagent_default_model` e `alternative_models` em
`cli/reference/configuration/config-file.md`, `cli/subagents.md`,
`cli/models.md`, `cli/reference/configuration/global-vs-local.md` e
`cli/reference/commands.md`: **zero ocorrências** (retrieved 2026-08-04).

O equivalente funcional existe, mas **não é chave de arquivo de config**: é a
configuração de organização **"Default subagent model"**, aplicada por
administrador nas org/enterprise settings (§4). Não há caminho documentado para
um repositório, ou mesmo um usuário, declará-la em JSON.

**CONTRADIÇÃO com a doc interna (§4.1):** o bloco JSON de exemplo dela é
inteiramente inventado, salvo `agent.model` e `subagents_enabled` — e este
último no aninhamento errado. `permissions.rules` com `{"action": ..., "pattern":
..., "allow": "allow"}` também não corresponde ao formato documentado, que usa
`permissions` com listas `allow`/`deny`/`ask` de padrões como `Read(src/**)`.

> https://docs.devin.ai/cli/reference/permissions.md (retrieved 2026-08-04)

### 7.4 O que o projeto **pode** declarar

Chaves disponíveis no `.devin/config.json` de projeto, conforme o "Full Config
Reference": `permissions`, `read_config_from`, `hooks`. As demais são
"(user only)". Ou seja: **um repositório não consegue ligar, desligar ou
parametrizar subagentes por arquivo versionado.** Isso é decisão do usuário e do
admin da org.

---

## 8. Skills — `.agents/skills/` é formato NATIVO do Devin, não convenção deste repo

Esta é a segunda premissa que cai. A tabela "Where Skills Live" lista, literalmente:

| Location | Scope | Committed to git? |
|---|---|---|
| `.agents/skills/<name>/SKILL.md` | Project-specific | Yes |
| `.devin/skills/<name>/SKILL.md` | Project-specific | Yes |
| `.windsurf/skills/<name>/SKILL.md` | Project-specific | Yes |
| `~/.agents/skills/<name>/SKILL.md` | Global (all projects) | No |
| `~/.config/devin/skills/<name>/SKILL.md` | Global (all projects) | No |
| `~/.codeium/<channel>/skills/<name>/SKILL.md` | Global (all projects, channel-dependent) | No |

> "We support the `.agents` skills standards, so third-party skill installation
> tools work with Devin CLI."

> https://docs.devin.ai/cli/extensibility/skills/overview.md (retrieved 2026-08-04)

O frontmatter de skill tem mais campos que o de subagente, e dois deles são
diretamente relevantes:

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | directory name | Display name of the skill |
| `description` | string | none | Shown in slash command completions |
| `argument-hint` | string | none | Hint shown after the command name |
| `model` | string | current model | Override the model used when running this skill |
| `subagent` | boolean | `false` | Run the skill as a subagent instead of inline |
| `agent` | string | none | Run the skill as a subagent using a specific custom subagent profile |
| `allowed-tools` | list | all tools | Restrict which tools the skill can use |
| `permissions` | object | inherit | Permission overrides for this skill |
| `triggers` | list | `[user, model]` | How the skill can be invoked |

> https://docs.devin.ai/cli/extensibility/skills/creating-skills.md (retrieved 2026-08-04)

**Consequência forte para o desenho:** `subagent: true` e `agent: <profile>`
significam que uma **skill** deste repositório pode declarar que roda como
subagente, e apontar para um perfil de `agents/`. O par
"skill + agente especializado" que hoje o `parity.yaml` traduz para `playbook`
tem tradução direta e declarativa no Devin — em arquivo versionado, não em
harness.

Adicionalmente, a importação de Claude Code cobre skills e comandos:

| Claude Code | Padrão importado |
|---|---|
| Rules | `CLAUDE.md`, `~/.claude/CLAUDE.md` |
| Skills | `.claude/skills/**/SKILL.md` |
| Commands (as skills) | `.claude/commands/**/*.md` |
| MCP servers | `.mcp.json`, `.claude/settings.json`, `.claude/settings.local.json` |

Controlado pela chave `read_config_from.claude` (default `true`), e há também
`agents_standard` (default `true`) para o padrão `.agents`.

> https://docs.devin.ai/cli/reference/configuration/read-config-from.md (retrieved 2026-08-04)

---

## 9. MCP no Devin CLI — CONFIRMADO

Desde a v3000.3 ("Local 3.6"), servidores MCP vivem em arquivo dedicado:

| Escopo | Caminho |
|---|---|
| Global | `~/.config/devin/mcp_config.json` (`%APPDATA%\devin\mcp_config.json` no Windows) |
| Projeto | `.devin/mcp_config.json` |
| Projeto (local, gitignored) | `.devin/mcp_config.local.json` |

Formato, com a mesma chave `mcpServers` do resto do ecossistema:

```json
// .devin/mcp_config.json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@company/mcp-server"],
      "env": { "API_KEY": "your-key" }
    }
  }
}
```

Transporte inferido: URL implica HTTP (Streamable HTTP, com fallback para SSE em
4xx); args finais implicam stdio. Também por CLI:

```bash
devin mcp add <name> -- <command> [args...]
devin mcp add <name> <URL>
devin mcp add -s project <name> <URL>
devin mcp list | get | remove | login | logout | enable | disable
```

Versões anteriores à v3000.3 liam `mcpServers` do `config.json` principal, e
entradas antigas são migradas automaticamente no startup.

E, conforme §6, subagentes podem chamar tools MCP diretamente desde
2026-04-30.

> https://docs.devin.ai/cli/extensibility/mcp/configuration.md (retrieved 2026-08-04)

O `.mcp.json` da raiz que este repositório já mantém é importado pela via
Claude Code (`read_config_from.claude`, §8).

---

## 10. Atalhos — `Ctrl+B` CONFIRMADO, `!ultra`/`!fast`/`!swe` NÃO ENCONTRADOS

### 10.1 O que a fonte confirma

> "**Background a foreground subagent:** Press `Ctrl`+`B` while a foreground
> subagent is running."
> "**Foreground a background subagent:** Open the subagent panel and press `f`
> on a running background subagent."
> "**From the subagent panel:** Open the panel and press `x` on a running
> subagent."
> "**Foreground subagent:** Press `Ctrl`+`C` or `Esc` to cancel."
> "When a foreground subagent is running, the spinner displays
> **"Subagent running · Ctrl+B to run in background"**."

> https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)

Isto valida as linhas "Mover para Background", "Trazer para Foreground" e
"Cancelar" da §8 da doc interna.

### 10.2 O que a fonte contradiz

`!ultra`, `!fast` e `!swe`: busca literal em `cli/reference/keyboard-shortcuts.md`,
`cli/subagents.md`, `cli/models.md`, `cli/reference/commands.md`,
`cli/index.md` e `cli/changelog/stable.md` — **zero ocorrências**
(retrieved 2026-08-04).

O que o `!` faz, segundo a página de atalhos:

> | `!` | Enter bash mode to run a shell command directly (when input is empty).
> Press `Backspace` or `Esc` on an empty input to exit bash mode |

> https://docs.devin.ai/cli/reference/keyboard-shortcuts.md (retrieved 2026-08-04)

Troca de modelo é por **slash command**, não por `!`:

```text
/model opus
/model sonnet
/model codex
```

> https://docs.devin.ai/cli/models.md (retrieved 2026-08-04)

E existe um `/fast` — que é slash, não bang:

> "New `/fast` slash command to quickly switch to SWE-1.6 Fast, with pricing
> comparison against the current model."
> — `<Update label="v2026.5.26-0" description="May 26, 2026">`

> https://docs.devin.ai/cli/changelog/stable.md (retrieved 2026-08-04)

**CONTRADIÇÃO com a doc interna (§8):** a linha "Alternar Agente — Menu inferior
ou `!ultra`, `!fast`, `!swe`" mistura três coisas: não existem `!ultra` e
`!swe`; `!fast` não existe com bang (é `/fast`); e `!` já está ocupado por bash
mode. Se um `!fast` fosse digitado com input vazio, ele entraria em bash mode e
tentaria rodar `fast` como comando de shell.

---

## 11. Nomenclatura de tools — divergência não documentada, tratar como ambígua

A tabela de `allowed-tools` do Devin usa nomes minúsculos. A página de
permissões declara:

> "**Available tool names:** `read`, `edit`, `grep`, `glob`, `exec`"

> https://docs.devin.ai/cli/reference/permissions.md (retrieved 2026-08-04)

Os arquivos deste repositório em `.claude/agents/` e `.agents/agents/` declaram,
no formato Claude Code:

```yaml
tools: Read, Grep, Glob, Bash, Edit, Write
```

A fonte diz que o campo `tools` do Claude Code é aceito ("Both formats are
supported automatically"), mas **não documenta o mapeamento de valores**. Em
particular, `Bash` → `exec` e `Write` → `write` não estão escritos em lugar
nenhum. **Ambíguo, não resolver na conveniência:** o campo é aceito; se os
*valores* são traduzidos é afirmação que a documentação não faz.

Uma restrição que **é** explícita e vale para qualquer perfil:

> "Cannot grant `ask_user_question`, which is always withheld from subagents."

Um subagente Devin **não pode** perguntar ao usuário. Qualquer agente deste repo
cujo método dependa de confirmação interativa (por exemplo, a regra 10 do
`CLAUDE.md` — "nunca execute manutenção destrutiva sem confirmação explícita")
não pode obtê-la de dentro de um subagente: a confirmação tem de subir ao pai.

---

## 12. Bloco de vetos, para quem for desenhar a fase

Copiar daqui, não reescrever de memória. Cada item existe porque uma fonte
contrariou uma premissa.

```
# VETOS APURADOS NA PESQUISA DE FONTES (2026-08-04).
# Detalhe e URLs: knowledge/devin/agents-and-subagents.md
#
# V-DV-1  A nota de parity.yaml (linhas 18-29) afirma que "nenhuma outra
#         plataforma tem um equivalente [de subagente] que este repositorio
#         possa acionar". Isso e FALSO para devin_cli e para devin_desktop
#         (Devin Local agent). O Devin CLI importa `.claude/agents/*.md` e le
#         `.agents/agents/` -- os dois diretorios que este repo JA publica.
#         A frase universal cai por contraexemplo. Nao repeti-la.
#
# V-DV-2  Nao declarar `model:` com model_uid do Desktop (`swe-1-7`, `glm-5-2`,
#         `kimi-k2-7`). Esses literais vem da tabela de PRECOS do Desktop;
#         nenhuma pagina do CLI os documenta como valor aceito de `--model` nem
#         de frontmatter. Os unicos literais garantidos pela doc do CLI sao os
#         short names `opus`, `sonnet`, `swe`, `codex`, `gemini` (e `gpt`).
#
# V-DV-3  Nao escrever `glm-5.2` / `swe-1.7` / `kimi-k2.7` com PONTO. Ponto e
#         label de exibicao; identificador usa HIFEN.
#
# V-DV-4  `subagent_default_model` e `alternative_models` NAO EXISTEM como
#         chaves de config. O equivalente e a setting de ORGANIZACAO "Default
#         subagent model", inacessivel a arquivo de repositorio.
#
# V-DV-5  `subagents_enabled` e chave DE TOPO e "(user only)". Nao aninhar em
#         `agent`, e nao esperar que `.devin/config.json` de projeto a aceite.
#         Um repositorio NAO controla se subagentes rodam.
#
# V-DV-6  Custom subagents e `subagent:`/`agent:` em skills sao declarados
#         EXPERIMENTAIS pela propria fonte: "format, behavior, and configuration
#         options may change". Nao construir garantia dura sobre eles sem
#         re-verificar a doc na data da entrega.
#
# V-DV-7  Nao presumir que `agents/` na RAIZ do repo seja varrido pelo Devin.
#         As abas de descoberta listam `.devin/agents/` e `.agents/agents/`;
#         a frase "your project's agents/ directory" do changelog e ambigua.
#
# V-DV-8  Nao presumir que os VALORES do campo `tools:` do Claude Code sejam
#         traduzidos (`Bash` -> `exec`, `Write` -> `write`). A fonte diz que o
#         CAMPO e aceito; o mapeamento de valores nao esta documentado.
#
# V-DV-9  Nenhum contrato de saida de subagente existe no Devin: a saida e texto
#         livre que o pai le e resume. Se a fase exige artefato verificavel, a
#         garantia tem de vir do system prompt do arquivo, nunca do harness.
#
# V-DV-10 `ask_user_question` e SEMPRE negado a subagente. Metodo que depende de
#         confirmacao interativa nao pode rodar dentro de um subagente.
#
# V-DV-11 `!ultra`, `!swe` nao existem; `!fast` nao existe com bang (`/fast`
#         existe). `!` e prefixo de BASH MODE no Devin CLI.
```

---

## 13. O que isto faz com a decisão de `parity.yaml`

Escrito aqui porque é a pergunta que motivou a coleta; a decisão em si é do
desenho, não desta página.

**Cai:** a justificativa universal — "nenhuma outra plataforma tem um
equivalente que este repositório possa acionar". Devin CLI e Devin Local
(Desktop) têm o equivalente, e o acionam a partir de arquivos que este
repositório **já versiona** (`.claude/agents/*.md` por importação,
`.agents/agents/` nativamente, `.agents/skills/<name>/SKILL.md` nativamente).

**Sobrevive:** o raciocínio de fundo, com escopo menor. `codex` e `copilot_ci`
não foram objeto desta pesquisa — nada aqui diz que eles tenham equivalente. E o
`playbook` continua sendo o piso portátil: é o que roda onde não há subagente, e
é o que não depende de um mecanismo que a própria Cognition marca como
experimental e que um admin de organização pode desligar por completo (opção
**None** de "Default subagent model").

**Muda de natureza:** o argumento "isso é harness, não conteúdo do repo" era
verdadeiro para o *despacho*, e continua sendo — nem CLI nem Desktop deixam um
repositório ligar subagentes ou fixar o modelo default por arquivo versionado
(§7.4). O que é conteúdo de repositório, e portanto declarável, é o **perfil**:
system prompt, `allowed-tools`, `model`, `max-nesting`. A distinção
defensável não é "Claude Code tem, os outros não" — é "o perfil é nosso, o
despacho é deles".

---

## Fontes

**Devin CLI — subagentes e perfis**

- Subagents (página primária: perfis embutidos, foreground/background, custo, roteador de modelo, `max-nesting`, formato de frontmatter, importação de `.claude/agents/*.md`). https://docs.devin.ai/cli/subagents.md (retrieved 2026-08-04)
- Changelog (Stable) — datas de introdução de `max-nesting` (v2026.5.26-0, 2026-05-26), `subagents_enabled` (v3000.3.22, 2026-07-29), perfis customizados (v2026.3.20-2, 2026-03-23), modelo default de subagente (v2026.8.18, 2026-06-23), MCP em subagente (v2026.4.30-0, 2026-04-30). https://docs.devin.ai/cli/changelog/stable.md (retrieved 2026-08-04)

**Devin CLI — modelos, config, permissões**

- Models (short names, `--model`, `/model`, default `swe-1-6-fast`, restrição por Team Settings). https://docs.devin.ai/cli/models.md (retrieved 2026-08-04)
- Configuration File (caminhos, objeto `agent`, `subagents_enabled` como chave de topo "user only", chaves de projeto). https://docs.devin.ai/cli/reference/configuration/config-file.md (retrieved 2026-08-04)
- Configuration Precedence. https://docs.devin.ai/cli/reference/configuration/global-vs-local.md (retrieved 2026-08-04)
- Configuration Import (`read_config_from`, tabela do que é importado de Claude Code, chave `agents_standard`). https://docs.devin.ai/cli/reference/configuration/read-config-from.md (retrieved 2026-08-04)
- Permissions ("Available tool names: `read`, `edit`, `grep`, `glob`, `exec`"). https://docs.devin.ai/cli/reference/permissions.md (retrieved 2026-08-04)
- Keyboard Shortcuts (`!` = bash mode; sem `!ultra`/`!fast`/`!swe`). https://docs.devin.ai/cli/reference/keyboard-shortcuts.md (retrieved 2026-08-04)
- Commands & Flags. https://docs.devin.ai/cli/reference/commands.md (retrieved 2026-08-04)

**Devin CLI — skills e MCP**

- Skills Overview (tabela "Where Skills Live", incluindo `.agents/skills/<name>/SKILL.md`). https://docs.devin.ai/cli/extensibility/skills/overview.md (retrieved 2026-08-04)
- Creating Skills (tabela completa de frontmatter, incluindo `model`, `subagent`, `agent`). https://docs.devin.ai/cli/extensibility/skills/creating-skills.md (retrieved 2026-08-04)
- MCP Configuration (`mcp_config.json`, `mcpServers`, stdio/HTTP, `devin mcp` subcomandos). https://docs.devin.ai/cli/extensibility/mcp/configuration.md (retrieved 2026-08-04)
- MCP Overview. https://docs.devin.ai/cli/extensibility/mcp/overview.md (retrieved 2026-08-04)

**Devin Desktop**

- Devin Local Agent (seção "Subagents", toggle "Subagents (Preview)", layouts `agents/<name>.md` e `agents/<name>/AGENT.md`). https://docs.devin.ai/desktop/devin-local.md (retrieved 2026-08-04)
- AI Models (tabela `modelCostData` com `model_uid` literais: `swe-1-7`, `swe-1-7-lightning`, `swe-1-6-fast`, `glm-5-2`, `kimi-k2-7`, `kimi-k3-*`). https://docs.devin.ai/desktop/models.md (retrieved 2026-08-04)
- Índice completo da documentação. https://docs.devin.ai/llms.txt (retrieved 2026-08-04)

**Lidas e sem menção a subagente (base do argumento por ausência da §2)**

- https://docs.devin.ai/desktop/cascade/cascade.md, https://docs.devin.ai/desktop/cascade/skills.md, https://docs.devin.ai/desktop/cascade/workflows.md, https://docs.devin.ai/desktop/cascade/agents-md.md, https://docs.devin.ai/desktop/advanced.md, https://docs.devin.ai/desktop/agent-command-center.md, https://docs.devin.ai/desktop/devin.md (todas retrieved 2026-08-04)

**Documento interno tratado como hipótese, não como fonte**

- `guia_devin_agents_subagents.md` (raiz do repositório). Contradito nas §§3.2, 3.3, 7.2, 7.3 e 10.2 desta página.

**Não encontrado, e registrado como tal**

- Nenhuma página do Devin CLI enumera identificadores completos de modelo aceitos por `--model` ou pelo `model:` de frontmatter. A única lista literal encontrada é a tabela de **preços do Desktop**, cujo escopo declarado é custo, não vocabulário de configuração.
- Nenhuma chave `subagent_default_model` ou `alternative_models` existe em nenhum arquivo de configuração documentado.
- Nenhum campo de frontmatter fixa foreground/background para um perfil de subagente.
- Nenhum limite documentado de subagentes concorrentes.
- Nenhum contrato, schema ou formato estruturado de saída de subagente.
- Nenhum mapeamento documentado entre os valores do campo `tools` do Claude Code e os nomes de tool do Devin.
- `!ultra`, `!swe` e `!fast` não aparecem em nenhuma das páginas do CLI lidas.
- Nenhuma página confirma que um diretório `agents/` na **raiz** do repositório (sem `.devin/` ou `.agents/`) seja varrido.
