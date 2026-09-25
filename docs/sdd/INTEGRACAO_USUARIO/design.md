---
sdd: 1
feature: INTEGRACAO_USUARIO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/INTEGRACAO_USUARIO/define.md
  sha256: "56ad93b884c1056ddfd77995a62cf2165e197fab25895063716a3064bd2f263b"
files:
  - {path: tests/test_integrate.py, action: create, reason: "os testes de AC1 a AC11, com HOME e APPDATA apontados para tmp_path"}
  - {path: sparkforge/integrate/__init__.py, action: create, reason: "pacote da integracao por usuario; exporta integrate() e detach()"}
  - {path: sparkforge/integrate/sources.py, action: create, reason: "localiza skills/ e agents/ no pacote instalado ou, em desenvolvimento, na raiz do repo (D3)"}
  - {path: sparkforge/integrate/render.py, action: create, reason: "render_agent e render_skill movidos de scripts/sync_skills.py, mais a plataforma codex (D1, D2)"}
  - {path: sparkforge/integrate/hosts.py, action: create, reason: "tabela declarativa de caminhos por host, com variante Windows e fonte (D4)"}
  - {path: sparkforge/integrate/writer.py, action: create, reason: "plano de escrita, manifesto, dry-run, idempotencia, merge de config JSON e bloco TOML marcado, detach (D5, D6, D7)"}
  - {path: sparkforge/integrate/claude.py, action: create, reason: "marketplace local e as chamadas ao `claude plugin` (D8)"}
  - {path: sparkforge/integrate/conflict.py, action: create, reason: "deteccao da copia vendorizada no repo atual e as tres escolhas (D9)"}
  - {path: scripts/sync_skills.py, action: modify, reason: "importa o renderizador de sparkforge/integrate/render.py em vez de defini-lo; os espelhos do repo nao mudam (D1)"}
  - {path: pyproject.toml, action: modify, reason: "force-include de skills/ e agents/ no wheel e include no sdist (D3)"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "verbos integrate e detach; arquivo ja grande, os verbos so despacham para sparkforge/integrate (D10)"}
  - {path: sparkforge/doctor.py, action: modify, reason: "checagem da integracao por host e da copia em dobro (D10, AC11)"}
  - {path: docs/guia/02-instalacao.md, action: modify, reason: "instalar uma vez por maquina com integrate, e quando o install_skills.py ainda faz sentido"}
  - {path: docs/guia/03-cli.md, action: modify, reason: "os verbos integrate e detach"}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "referencia gerada por scripts/gen_reference_docs.py quando a CLI ganha verbos"}
  - {path: docs/surface.lock.json, action: modify, reason: "registro da superficie, se o crescimento mover (regra 26)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "entrada da feature e numeros que ela mover, conferidos por check_status_numbers"}
  - {path: README.md, action: modify, reason: "o caminho curto de instalacao passa a citar integrate"}
decisions:
  - id: D1
    choice: "render_agent e render_skill passam de scripts/sync_skills.py para sparkforge/integrate/render.py, e o sync_skills.py importa de la: um renderizador so para os espelhos do repo e para a integracao de usuario."
    rejected: ["copiar o renderizador para o pacote, o que deixa duas copias que divergem", "instalar a partir dos espelhos .claude/.agents/.github do repo, que o wheel nao empacota"]
    rollback: "git revert do commit que move o renderizador; tests/test_sync_render.py e tests/test_agents_parity.py confirmam que os espelhos do repo nao mudaram."
  - id: D2
    choice: "Plataforma codex no renderizador: agent vira TOML com name, description e developer_instructions (o corpo do markdown), o formato de ~/.codex/agents/ (learn.chatgpt.com/docs/agent-configuration/subagents, lido em 2026-09-25). O espelho .codex/ do repo continua mantido a mao nesta feature."
    rejected: ["ler os .codex/agents/*.toml do repo, que sao mantidos a mao, envelhecem e o wheel nao empacota"]
    rollback: "git revert do commit da plataforma codex; integrate codex volta a recusar por nome."
  - id: D3
    choice: "O wheel embute skills/ e agents/ pelo mesmo force-include que ja leva rules/catalog e knowledge; sparkforge/integrate/sources.py os acha no pacote instalado ou, em desenvolvimento, na raiz do repo."
    rejected: ["baixar do GitHub na maquina de destino, rejeitado pelo operador no explore", "exigir o clone do repositorio"]
    rollback: "git revert do commit de empacotamento; scripts/verify_wheel.py confere o wheel de novo."
  - id: D4
    choice: "Tabela declarativa em sparkforge/integrate/hosts.py com agents, skills e MCP de cada host, variante Windows (Devin em %APPDATA%\\devin) e a fonte oficial de cada caminho; um parametro de home decide a raiz, e os testes o apontam para tmp_path."
    rejected: ["ler variaveis de ambiente espalhadas pelo codigo, que nao se testa sem tocar o HOME real"]
    rollback: "sparkforge detach all remove o que foi gravado; git revert do codigo."
  - id: D5
    choice: "Manifesto em ~/.sparkforge/integrations.json com, por host, cada arquivo gravado (caminho, sha256), a versao do pacote e as entradas de config inseridas; dry-run calcula o plano e so imprime; a segunda execucao compara pelo sha256 e nao regrava. Arquivo de ~/.agents/skills, compartilhado por Devin, Codex e Copilot, registra quais hosts o usam."
    rejected: ["sem manifesto, adivinhar o que apagar pelo nome, que apagaria arquivo do usuario com o mesmo nome"]
    rollback: "sparkforge detach all, que le o proprio manifesto; apagar ~/.sparkforge/integrations.json depois."
  - id: D6
    choice: "Config de usuario e mesclada, nunca sobrescrita: no JSON (Devin, Copilot) so a chave mcpServers.sparkforge; no TOML do Codex um bloco entre `# >>> sparkforge (gerenciado)` e `# <<< sparkforge`, porque o Python 3.10 que o projeto suporta nao tem leitor de TOML e o projeto nao tem essa dependencia. Um `sparkforge` ja presente que o SparkForge nao escreveu, ou arquivo que nao e JSON/TOML valido, sai recusa nomeada sem tocar o arquivo."
    rejected: ["acrescentar a dependencia tomli-w so para gravar um bloco", "sobrescrever o arquivo de config inteiro"]
    rollback: "sparkforge detach <host> retira so as entradas inseridas; o resto do arquivo nao foi tocado."
  - id: D7
    choice: "detach remove so os arquivos do manifesto cujo sha256 ainda bate e retira da config as entradas inseridas; arquivo editado depois fica e sai como recusa editado_pelo_usuario; arquivo de config que o integrate criou e ficou vazio e apagado."
    rejected: ["apagar os diretorios inteiros do host, que levaria arquivo do usuario junto"]
    rollback: "sparkforge integrate <host> grava de novo o mesmo conteudo."
  - id: D8
    choice: "Claude: marketplace local sparkforge-local em ~/.sparkforge/claude/ com o plugin sparkforge-aws (skills, agents, plugin.json e .mcp.json chamando o Python do pacote com -m sparkforge.adapters.mcp); registro por `claude plugin marketplace add <dir> --scope user` e `claude plugin install sparkforge-aws@sparkforge-local --json` (sem prompt para marketplace local, medido no Claude Code 2.1.283 pelo --help); sem `claude` no PATH o diretorio fica montado e sai recusa claude_cli_ausente com os dois comandos."
    rejected: ["editar ~/.claude/settings.json a mao, formato interno do Claude que muda sem aviso", "usar o proprio repositorio como plugin, que exige o clone"]
    rollback: "claude plugin uninstall sparkforge-aws, ou sparkforge detach claude."
  - id: D9
    choice: "Copia vendorizada no repo atual detectada por nome e conteudo (skill ou agent em .agents/skills, .claude/skills, .github/agents com o mesmo nome de um integrado): identico quando igual ao que o wheel renderiza, customizado quando difere. SOBRESCREVER apaga os dois, MESCLAR apaga so os identicos e lista os customizados, IGNORAR nao toca; escolha por prompt, por --on-conflict, e IGNORAR sem terminal e sem a flag; toda remocao mostra a lista antes e respeita --dry-run; so o repositorio de onde o comando foi chamado."
    rejected: ["apagar sem perguntar, rejeitado pelo operador no define", "depender de manifesto do install_skills.py, que nao grava nenhum"]
    rollback: "git checkout dos arquivos removidos no repositorio do operador (a remocao e sempre de arquivo versionado ou listado antes)."
  - id: D10
    choice: "Verbos de CLI `sparkforge integrate <claude|devin|codex|copilot|all> --scope user [--dry-run] [--on-conflict overwrite|merge|ignore]` e `sparkforge detach <host|all> [--dry-run]`, sem tool MCP; doctor ganha uma checagem por host que le o manifesto e aponta copia em dobro no repo atual."
    rejected: ["expor como tool MCP: escrever no HOME e decisao do operador, e um agente nao deve disparar isso sozinho"]
    rollback: "git revert dos commits de CLI e doctor."
covers:
  - {part: "empacotamento (D3)", acceptance: [AC1]}
  - {part: "plugin do Claude (D8)", acceptance: [AC2]}
  - {part: "hosts e merge de config (D4, D6)", acceptance: [AC3, AC4, AC5]}
  - {part: "renderizador unico (D1, D2)", acceptance: [AC6]}
  - {part: "manifesto, dry-run e idempotencia (D5)", acceptance: [AC7]}
  - {part: "detach (D7)", acceptance: [AC8]}
  - {part: "copia vendorizada (D9)", acceptance: [AC9]}
  - {part: "escopo de usuario por construcao (D4)", acceptance: [AC10]}
  - {part: "CLI e doctor (D10)", acceptance: [AC11]}
  - {part: "registros", acceptance: [AC12]}
---

# INTEGRACAO_USUARIO — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| empacotamento | `pyproject.toml`, `sparkforge/integrate/sources.py` | AC1 |
| renderizador único | `sparkforge/integrate/render.py`, `scripts/sync_skills.py` | AC6 |
| hosts e escrita | `sparkforge/integrate/hosts.py`, `writer.py` | AC3, AC4, AC5, AC7, AC8, AC10 |
| Claude | `sparkforge/integrate/claude.py` | AC2 |
| cópia em dobro | `sparkforge/integrate/conflict.py` | AC9 |
| CLI e doctor | `sparkforge/adapters/cli.py`, `sparkforge/doctor.py` | AC11 |
| registros | referência gerada, surface lock, STATUS, README, guias 02 e 03 | AC12 |

## Conhecimento consultado

- Claude Code: code.claude.com/docs/en/plugins, /plugins/create, /plugins/install,
  /plugins/publish e /mcp (lidos em 2026-09-25); `claude plugin install --help` e
  `claude plugin marketplace add --help` no Claude Code 2.1.283.
- Devin CLI: docs.devin.ai/cli/subagents, /cli/extensibility/skills/overview,
  /cli/extensibility/mcp/configuration; conferido contra
  `knowledge/devin/agents-and-subagents.md` (retrieved 2026-08-04), sem divergência.
- Codex CLI: learn.chatgpt.com/docs/agent-configuration/subagents, /docs/build-skills,
  /docs/agent-configuration/agents-md, /docs/extend/mcp.
- Copilot CLI: docs.github.com/en/copilot/how-tos/copilot-cli (create-custom-agents-for-cli,
  add-skills, add-mcp-servers).

## Lacunas do define

- U1 resolvida pelo `--help` do Claude Code 2.1.283 (D8).
- U2 fica para o build medir; o design não depende dela, porque o Codex também lê
  skills do projeto.
- U3 resolvida lendo `scripts/sync_skills.py`: Devin recebe o agent sem os campos que o
  Devin rejeita, Copilot recebe o texto idêntico com sufixo `.agent.md`; o Codex não tinha
  renderizador (D2).

## Pendência registrada

O espelho `.codex/agents/*.toml` do repositório continua mantido à mão; passar a gerá-lo
pela plataforma `codex` do renderizador é frente própria.
