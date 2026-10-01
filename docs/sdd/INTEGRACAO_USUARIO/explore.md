---
sdd: 1
feature: INTEGRACAO_USUARIO
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "`sparkforge integrate <host> --scope user` renderiza cada host a partir das skills e agents embutidos no wheel: plugin do Claude por marketplace local em ~/.sparkforge, e diretorios globais de agents, skills (~/.agents/skills) e MCP de usuario para Devin, Codex e Copilot CLI, com manifesto do que foi escrito para update e detach."
    tradeoffs:
      - "o conteudo chega a qualquer repo sem copiar nada para ele, e vem de uma origem so (o wheel), com ou sem GitHub"
      - "reusa os renderizadores de scripts/sync_skills.py em vez de escrever um quinto"
      - "quatro formatos de config de usuario para manter (settings do Claude, mcp_config do Devin, config.toml do Codex, mcp-config do Copilot)"
      - "escreve fora do repositorio (HOME do usuario): exige manifesto, dry-run e detach que remove so o que escreveu"
  - id: B
    summary: "Registrar so o servidor MCP no escopo de usuario de cada host e servir o texto de skills e agents por tools do MCP."
    tradeoffs:
      - "menos arquivos escritos no HOME"
      - "os hosts nao descobrem skill nem agent via MCP: some o despacho de subagent e a ativacao automatica de skill, e isso e perda de capacidade"
  - id: C
    summary: "O repositorio vira plugin e marketplace do Claude no GitHub, e os outros hosts recebem copia do install_skills.py nos diretorios globais."
    tradeoffs:
      - "menos codigo novo no Claude"
      - "o Claude passa a depender de GitHub na maquina de destino, contra a decisao de usar o wheel como fonte"
      - "o conteudo sai de duas origens (repo no Claude, copia nos outros), e a paridade entre elas vira problema proprio"
chosen: A
---

# INTEGRACAO_USUARIO — exploração

Origem: `prompt_evo_portable_forge.md` (raiz do repositório, fora do git), que propõe
tornar o SparkForge uma ferramenta instalada que se conecta a qualquer repositório, em vez
de copiada para dentro de cada um. O documento junta pelo menos seis subsistemas
independentes; esta feature é o primeiro.

## Perfil

`dev`: a mudança é no próprio SparkForge.

## Decomposição

O prompt foi quebrado em frentes, cada uma com ciclo próprio:

1. **Integração por usuário** (esta feature): instalar uma vez e usar em qualquer repo.
2. Workspace multi-repo (`workspace init/discover`, `workspace.yaml`, relações entre
   repos).
3. `doctor` com matriz de capacidades e recusa nomeada por capacidade.
4. Distribuição restrita: bundle offline completo, executável standalone e modo `vendor`
   como evolução do `scripts/install_skills.py`.
5. `attach` mínimo por repositório.
6. Launcher (`sparkforge claude`, `sparkforge devin`).

O que já existe hoje: `sparkforge doctor`, `scripts/install_skills.py` (a cópia por repo),
`scripts/verify_offline_bundle.py`, `.claude-plugin/plugin.json` (só o manifesto), e o
wheel já embute `rules/catalog` e `knowledge` (`pyproject.toml`,
`[tool.hatch.build.targets.wheel.force-include]`).

## Perguntas feitas, uma por vez

1. Qual pedaço primeiro? Resposta: integração por usuário.
2. Quais hosts? Resposta: todos (Claude Code, Devin, Codex, Copilot).
3. De onde a instalação tira skills, agents e MCP? Resposta: do wheel instalado, sem
   depender de GitHub na máquina de destino.
4. Qual abordagem? Resposta: A.

## Fatos que sustentam as abordagens

Pesquisados em 2026-09-25 na documentação oficial de cada host (T1):

- **Claude Code.** Plugin em escopo de usuário, registrado em `~/.claude/settings.json`
  (`enabledPlugins`); empacota `skills/`, `agents/`, `hooks/hooks.json` e `.mcp.json` na
  raiz do plugin, com `${CLAUDE_PLUGIN_ROOT}` nos caminhos. Marketplace pode ser um
  diretório local (`.claude-plugin/marketplace.json`), e `claude plugin install
  <nome>@<marketplace>` roda sem interação. Skills e agents de plugin ganham namespace
  (`plugin:skill`), sem colidir com os do projeto. MCP de usuário: `claude mcp add --scope
  user`, em `~/.claude.json`. Fontes: code.claude.com/docs/en/plugins, /plugins/create,
  /plugins/install, /plugins/publish, /mcp.
- **Devin CLI.** Agents em `~/.config/devin/agents/` (`%APPDATA%\devin\agents\` no
  Windows); skills em `~/.agents/skills/` ou `~/.config/devin/skills/`; MCP em
  `~/.config/devin/mcp_config.json`. Importa `.claude/` do projeto e `~/.claude/CLAUDE.md`.
  Conferido contra `knowledge/devin/agents-and-subagents.md` (retrieved 2026-08-04): sem
  divergência.
- **Codex CLI.** Agents em `~/.codex/agents/` (TOML: `name`, `description`,
  `developer_instructions`); skills em `$HOME/.agents/skills`; instruções em
  `~/.codex/AGENTS.md`; MCP em `~/.codex/config.toml`, `[mcp_servers.<nome>]`. Não lê o
  formato do Claude. Fonte: learn.chatgpt.com/docs (subagents, build-skills, agents-md,
  extend/mcp).
- **Copilot CLI.** Agents em `~/.copilot/agents/*.agent.md`; skills em `~/.copilot/skills`
  e `~/.agents/skills`; instruções em `~/.copilot/copilot-instructions.md`; MCP em
  `~/.copilot/mcp-config.json`. Fonte: docs.github.com/en/copilot/how-tos/copilot-cli.
- **Copilot coding agent (nuvem).** Só repositório ou organização: não tem escopo de
  usuário, e continua recebendo o espelho `.github/agents/` do repo.

`~/.agents/skills` é lido por Devin, Codex e Copilot CLI: uma cópia serve os três.

Não documentado e fora desta feature: `--add-dir` e o `roots/list` do MCP no Claude Code,
que o prompt de origem usa para o workspace multi-repo. Não achados na documentação
oficial; a frente de workspace precisa medir antes de depender deles.

Divergência achada no próprio repositório: `.github/copilot-instructions.md:23` diz
"Copilot has no MCP here". É escolha de configuração deste repo, não limite do produto: o
Copilot CLI tem MCP global e por projeto.

## Abordagens

- **A** (escolhida): `integrate` gera por host a partir do wheel.
- **B**: só MCP global, conteúdo servido por tools. Rejeitada: os hosts não descobrem
  skill nem agent via MCP, e perder despacho de subagent é perder capacidade — o prompt de
  origem pede o contrário ("o usuário escolhe como transportar o SparkForge, mas não
  escolhe uma versão capada dele").
- **C**: plugin do Claude pelo GitHub e cópia para os outros. Rejeitada: contraria a
  resposta 3 (wheel como origem, sem GitHub) e cria duas origens de conteúdo.

## Por que A venceu

É a única que entrega os quatro hosts com a mesma capacidade, a partir de uma origem só,
e funciona igual com `pip`, wheel offline ou bundle — o que a frente 4 (distribuição
restrita) vai precisar. O custo real é escrever no HOME do usuário: o define precisa
fixar dry-run, manifesto do que foi escrito, `update` idempotente e `detach` que remove
só o que o SparkForge escreveu, sem tocar config de usuário que já existia.

## Perguntas em aberto para o define

- O wheel passa a embutir `skills/` e `agents/`: quanto isso move o tamanho do pacote e a
  superfície (`docs/surface.lock.json`)?
- Precedência quando o repo também tem cópia vendorizada (`.claude/skills`, `.agents/`):
  no Claude o namespace do plugin evita colisão; nos outros hosts, skills de mesmo nome
  aparecem em dobro (Codex não faz merge).
- Copilot em VS Code (agent mode): tem MCP de usuário, mas o caminho do arquivo não foi
  confirmado. Entra ou fica para depois?
- Windows: caminhos com `%APPDATA%` (Devin) e o HOME de cada host.
