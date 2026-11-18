# Instalação portátil — spark-forge-aws

Instala em qualquer diretório/repositório — sem estrutura prévia exigida.

```bash
cd <qualquer-projeto>
sparkforge-aws install                    # escopo projeto (padrão)
sparkforge-aws install --dry-run          # planeja sem escrever
sparkforge-aws install --profile minimal  # só config+MCP+docs, sem mirrors
sparkforge-aws install --profile full     # mesmo conjunto de assets do recommended
```

O que acontece: assets gerenciados vão para `.agents/`, `.claude/`,
`.devin/`, `.codex/` conforme os hosts detectados; `.mcp.json` ganha uma
entrada gerenciada; `AGENTS.md`/`CLAUDE.md`/`AGENT_PROTOCOL.md` recebem o
bloco `forge:spark-forge-aws` — conteúdo seu nunca é sobrescrito.

## Perfis (`--profile`)

`--profile` seleciona **conjuntos de componentes** — e nada mais. Não há
diferença de conteúdo dentro de um componente nem de "profundidade":

| Perfil | Componentes instalados |
|---|---|
| `minimal` | config + entrada MCP + docs (`AGENTS.md` bloco) — sem mirrors de skills/agents/knowledge |
| `recommended` (padrão) | minimal + skills + agents + ponteiros de knowledge/rules/evals |
| `full` | **idêntico ao `recommended` hoje** — slot reservado para componentes opcionais (`tui`, `graph-studio`) quando entrarem no pacote |

Seleção fina por componente: `--components skills,agents,knowledge` (csv;
válidos: `skills`, `agents`, `mcp`, `knowledge`, `rules`, `evals`, `tui`,
`graph-studio`). Cada nome habilita só o seu conjunto — `--components
knowledge` instala só os ponteiros de knowledge, sem mirrors.

## Perfil do Context Gateway (`--gateway-profile`)

Dimensão ortogonal ao `--profile`: decide só o **modo do servidor MCP**
gravado na config do host, não mexe em nenhum asset:

| `--gateway-profile` | argv do MCP | Tools expostas |
|---|---|---|
| `economy` / `balanced` | `… --mode compact` | 7 operações compactas |
| `deep` (ou ausente) | `… --mode full` (padrão) | 148 tools completas |

## Raiz do alvo (`--root`) e projetos sem `.git`

- `--root <dir>` é autoritativo: sempre vence, inclusive em diretório sem
  `.git` (gitless).
- Sem `--root`, o escopo `project` procura a raiz VCS (`.git`) subindo do
  cwd; se não houver, procura um estado `.sparkforge_aws/` já existente;
  sem os dois, recusa com `FORGE-INSTALL-NOT-A-REPO` — passe `--root`.
- Escopo `workspace`: `--root` é autoritativo; sem ele, procura marcador
  de workspace, depois `.git`, e por fim o cwd.
- Precedência entre escopos: `project > workspace > user` — a instalação
  mais específica vence; conflitos são reportados, nunca sobrescritos.

## Ponteiros de knowledge

Os links `knowledge/<rel>` citados por skills/agents resolvem em
ponteiros gerados em `knowledge/sparkforge-aws/<rel>` (mais um
`README.md` índice no mesmo subdir) — o subdir com o nome do forge evita
colisão na raiz `knowledge/` compartilhada entre forges. O ponteiro ensina
o caminho de retrieval real:

```bash
sparkforge-aws knowledge path --file <rel>
sparkforge-aws knowledge list
```

Ao migrar de versões que gravavam na raiz genérica: stubs antigos
gerenciados são removidos; arquivo editado por você fica e sai como
recusa `editado_pelo_usuario`; arquivo de outra forge nunca é tocado.

## Superfície declarada (install-2.1)

`forge.json` declara, e o install copia verbatim para o manifesto
registrado (`forge/InstallationManifest/v1` em
`~/.forge/installations/spark-forge-aws.json`):

- `installation_kind: "content"` — o plano consolidado do workspace usa
  na ordenação estável entre forges.
- `install` — capability surface honesta: `operations`
  (`plan`/`apply`/`status`/`doctor`/`repair`/`update`/`uninstall`/
  `mcp-verify`), `flags` (`--scope` `--root` `--host` `--profile`
  `--components` `--gateway-profile` `--yes` `--dry-run` `--purge`
  `--to` `--repo`), `hosts`, `scopes`, `profiles`, `approval: "--yes"`.
  O orquestrador só envia flag declarada; pedido fora da lista vira
  `unsupported-capability`.
- `depends_on: []` — declarado mesmo vazio: a presença da chave diz
  "este forge não depende de ninguém".

## Uninstall seletivo

```bash
sparkforge-aws uninstall --host devin      # remove só os assets daquele host
sparkforge-aws uninstall                   # todos os hosts, só arquivos gerenciados
sparkforge-aws uninstall --purge           # + estado .sparkforge_aws/
```

O ledger SHA-256 decide ownership — veja
[uninstall.md](uninstall.md).
