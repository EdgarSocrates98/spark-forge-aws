---
sdd: 1
feature: INTEGRACAO_USUARIO
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/INTEGRACAO_USUARIO/explore.md
  sha256: "f25699ac6ef5490d5d029c91449f55ce028f3af24209885b3a111003bc45334c"
hypothesis:
  claim: "Com skills e agents embutidos no wheel, um verbo `sparkforge integrate <host> --scope user` basta para o SparkForge ficar disponivel em qualquer repositorio da maquina, nos quatro hosts (Claude Code, Devin CLI, Codex CLI, Copilot CLI), sem copiar nada para o repositorio e com a mesma capacidade da copia por repo."
  prediction: "Num HOME temporario, `integrate --scope user` para cada host grava exatamente os arquivos que o formato daquele host descobre (plugin e marketplace local no Claude; agents, skills em ~/.agents/skills e MCP de usuario nos outros tres), e o conteudo de cada skill e agent gravado e byte a byte o que `scripts/sync_skills.py` renderiza para a mesma plataforma a partir do repo. `detach` remove so o que o manifesto registrou e deixa intacta a config de usuario que ja existia. Se algum host precisar de arquivo dentro do repositorio, ou se o conteudo divergir da renderizacao do repo, a afirmacao esta errada."
  experiment: "Testes com HOME e APPDATA apontados para tmp_path, rodando integrate e detach para cada host sobre o wheel construido por `scripts/verify_wheel.py`, e comparando o gravado com a renderizacao de sync_skills."
acceptance:
  - id: AC1
    statement: "O wheel embute `skills/` e `agents/` (como ja embute `rules/catalog` e `knowledge`), e o pacote instalado os le sem o clone do repositorio."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_wheel_embute_skills_e_agents"}
  - id: AC2
    statement: "`sparkforge integrate claude --scope user` monta, sob ~/.sparkforge, um marketplace local com o plugin (skills/, agents/, .mcp.json e .claude-plugin/plugin.json) e registra a instalacao pelo `claude plugin marketplace add` e `claude plugin install --scope user`; o .mcp.json do plugin aponta o Python que tem o sparkforge instalado, sem PYTHONPATH para o repo. Sem o binario `claude` no PATH, sai recusa nomeada com o comando que o operador roda."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_integrate_claude_monta_plugin_e_recusa_sem_cli"}
  - id: AC3
    statement: "`sparkforge integrate devin --scope user` grava agents em ~/.config/devin/agents/ (%APPDATA%\\devin\\agents\\ no Windows), skills em ~/.agents/skills/ e o servidor MCP em ~/.config/devin/mcp_config.json (chave mcpServers), preservando os outros servidores que ja estavam no arquivo."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_integrate_devin_grava_global_e_preserva_mcp_existente"}
  - id: AC4
    statement: "`sparkforge integrate codex --scope user` grava agents em ~/.codex/agents/ no formato TOML (name, description, developer_instructions), skills em ~/.agents/skills/ e a secao [mcp_servers.sparkforge] em ~/.codex/config.toml, preservando o resto do arquivo."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_integrate_codex_grava_toml_e_preserva_config"}
  - id: AC5
    statement: "`sparkforge integrate copilot --scope user` grava agents em ~/.copilot/agents/*.agent.md, skills em ~/.agents/skills/ e o servidor em ~/.copilot/mcp-config.json, preservando os outros servidores."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_integrate_copilot_grava_global_e_preserva_mcp_existente"}
  - id: AC6
    statement: "O conteudo de cada skill e agent gravado por integrate e byte a byte o que scripts/sync_skills.py renderiza para a mesma plataforma; nao existe um quinto renderizador."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_conteudo_e_o_da_renderizacao_do_sync_skills"}
  - id: AC7
    statement: "Toda escrita fora do repositorio passa por manifesto (~/.sparkforge/integrations.json) com caminho e sha256 de cada arquivo gravado; `--dry-run` lista o que seria escrito sem escrever; rodar integrate duas vezes nao muda nada na segunda (idempotente)."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_manifesto_dry_run_e_idempotencia"}
  - id: AC8
    statement: "`sparkforge detach <host> --scope user` remove so o que o manifesto registrou e ainda tem o sha256 gravado; arquivo que o usuario editou depois sai listado como recusa nomeada e fica; config de usuario que ja existia antes do integrate volta ao estado anterior (entradas do sparkforge retiradas, o resto intacto)."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_detach_remove_so_o_proprio_e_recusa_o_editado"}
  - id: AC9
    statement: "Com o repositorio atual contendo copia vendorizada (arquivos do install_skills.py) que colide com o que foi integrado, integrate avisa por nome e pergunta: SOBRESCREVER (remove a copia do repo pelo manifesto do install_skills), MESCLAR (remove do repo so o identico a versao instalada e mantem o customizado, listando os nomes que continuam em dobro) ou IGNORAR (nao toca no repo); a mesma escolha vale sem prompt por `--on-conflict overwrite|merge|ignore`; sem terminal interativo e sem a flag, o padrao e IGNORAR; toda remocao mostra a lista antes e respeita `--dry-run`."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_conflito_com_copia_vendorizada_tres_escolhas"}
  - id: AC10
    statement: "Nenhum arquivo e escrito dentro do repositorio por integrate com --scope user, exceto as remocoes que o operador escolheu em AC9."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_scope_user_nao_escreve_no_repo"}
    guard: "Guarda de regressao: o verbo nasce escrevendo so no HOME; o teste passa antes e depois por desenho e impede que uma tarefa futura volte a copiar para o repo."
  - id: AC11
    statement: "`sparkforge doctor` informa, por host, se a integracao de usuario esta presente, em que versao do pacote foi gravada e se ha copia vendorizada em dobro no repositorio atual."
    verified_by: {kind: test, ref: "tests/test_integrate.py::test_doctor_informa_integracao_por_host"}
  - id: AC12
    statement: "Os gates de registro manual passam: surface lock, lastro, numeros do STATUS e o wheel isolado."
    verified_by: {kind: command, ref: "python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py --strict && python scripts/verify_wheel.py"}
success:
  - id: SC1
    metric: "Arquivos escritos dentro do repositorio por `integrate --scope user` (alvo: zero)"
    source: "tests/test_integrate.py::test_scope_user_nao_escreve_no_repo, que lista a arvore do repo antes e depois"
  - id: SC2
    metric: "Tamanho do wheel antes e depois de embutir skills/ e agents/, em bytes"
    source: "scripts/verify_wheel.py, tamanho do .whl construido nos dois commits"
out_of_scope:
  - "Copilot no VS Code (agent mode): o caminho do mcp.json de usuario nao foi confirmado na documentacao oficial; fica para depois, com a lacuna nomeada."
  - "Copilot coding agent na nuvem: nao tem escopo de usuario e continua com o espelho .github/agents do repo."
  - "Workspace multi-repo, `attach` minimo por repo, launcher (`sparkforge claude`), bundle offline completo, executavel standalone e modo `vendor`: frentes proprias do prompt_evo_portable_forge.md."
  - "Marketplace do Claude pelo GitHub (abordagem C do explore): a origem e o wheel."
  - "Remover ou mudar o scripts/install_skills.py: continua existindo ate a frente de `vendor`."
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Medir, com o Claude Code instalado, se `claude plugin marketplace add <diretorio local>` e `claude plugin install <nome>@<marketplace> --scope user` rodam sem prompt, e qual o nome que o plugin ganha no marketplace local."
  - id: U2
    blocks: [AC4]
    unlock: "Confirmar na documentacao do Codex se ~/.agents/skills e lido quando o Codex roda fora de repositorio git, e o formato exato do TOML de agent global."
  - id: U3
    blocks: [AC3, AC5]
    unlock: "Ler scripts/sync_skills.py e confirmar que a renderizacao de agent para Devin (.agents/agents) e para Copilot (.github/agents *.agent.md) e o formato que os diretorios globais desses hosts aceitam."
case_id: null
change_kinds: [tool_or_verb, agent_or_skill, dependency, disk_read, status_numbers, claims]
---

# INTEGRACAO_USUARIO — requisitos

## Problema

Hoje o SparkForge chega a um repositório por cópia: `scripts/install_skills.py` grava
`.claude/`, `.agents/`, `knowledge/`, `templates/`, `checklists/` e `skills/` dentro de
cada projeto. O motor já é portátil (o wheel embute `rules/catalog` e `knowledge`), mas
skills, agents e o registro do MCP ficam presos ao repositório copiado. Para usar em
outro repo, copia-se de novo, e cada cópia envelhece sozinha.

## O que esta feature entrega

Um verbo, `sparkforge integrate <host> --scope user`, que instala a integração uma vez
por máquina e por host, a partir do wheel instalado, e o par `sparkforge detach`, que a
remove. Hosts: Claude Code (plugin por marketplace local), Devin CLI, Codex CLI e
Copilot CLI (diretórios globais de agents, `~/.agents/skills` e MCP de usuário). O
`doctor` passa a dizer o que está integrado.

## Decisões do operador (explore e define)

- Abordagem A do explore: `integrate` gera por host a partir do wheel.
- Hosts: todos, com o Copilot restrito ao CLI; VS Code fora por falta de caminho
  confirmado.
- Cópia vendorizada em dobro no repo: avisar e perguntar entre sobrescrever, mesclar e
  ignorar, com `--on-conflict` para uso sem prompt e IGNORAR como padrão sem terminal.

## Critérios

Os critérios AC2 a AC5 dependem de caminhos de cada host pesquisados em 2026-09-25 na
documentação oficial (citados no `explore.md`). As lacunas U1 a U3 nomeiam o que ainda
precisa de medida antes do design fixar os formatos.

AC10 é guarda: nasce verde e impede regressão para a cópia por repo.
