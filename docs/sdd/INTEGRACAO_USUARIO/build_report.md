---
sdd: 1
feature: INTEGRACAO_USUARIO
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/INTEGRACAO_USUARIO/plan.md
  sha256: "d2cd802089d286747ce0957b376ea93ad778580ddae548f9bd1e6b356e668996"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_wheel_embute_skills_e_agents -q", exit: 4}
    green: {command: "python -m pytest tests/test_integrate.py::test_wheel_embute_skills_e_agents -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_conteudo_e_o_da_renderizacao_do_sync_skills -q", exit: 4}
    green: {command: "python -m pytest tests/test_integrate.py::test_conteudo_e_o_da_renderizacao_do_sync_skills -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_manifesto_dry_run_e_idempotencia -q", exit: 4}
    green: {command: "python -m pytest tests/test_integrate.py::test_manifesto_dry_run_e_idempotencia -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_integrate_devin_grava_global_e_preserva_mcp_existente tests/test_integrate.py::test_integrate_copilot_grava_global_e_preserva_mcp_existente -q", exit: 1}
    green: {command: "python -m pytest tests/test_integrate.py::test_integrate_devin_grava_global_e_preserva_mcp_existente tests/test_integrate.py::test_integrate_copilot_grava_global_e_preserva_mcp_existente -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_integrate_codex_grava_toml_e_preserva_config -q", exit: 1}
    green: {command: "python -m pytest tests/test_integrate.py::test_integrate_codex_grava_toml_e_preserva_config -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_detach_remove_so_o_proprio_e_recusa_o_editado -q", exit: 4}
    green: {command: "python -m pytest tests/test_integrate.py::test_detach_remove_so_o_proprio_e_recusa_o_editado -q", exit: 0}
  - id: T7
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_integrate_claude_monta_plugin_e_recusa_sem_cli -q", exit: 1}
    green: {command: "python -m pytest tests/test_integrate.py::test_integrate_claude_monta_plugin_e_recusa_sem_cli -q", exit: 0}
  - id: T8
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_conflito_com_copia_vendorizada_tres_escolhas tests/test_integrate.py::test_scope_user_nao_escreve_no_repo -q", exit: 1}
    green: {command: "python -m pytest tests/test_integrate.py::test_conflito_com_copia_vendorizada_tres_escolhas tests/test_integrate.py::test_scope_user_nao_escreve_no_repo -q", exit: 0}
  - id: T9
    status: done
    red: {command: "python -m pytest tests/test_integrate.py::test_doctor_informa_integracao_por_host -q", exit: 4}
    green: {command: "python -m pytest tests/test_integrate.py::test_doctor_informa_integracao_por_host -q", exit: 0}
  - id: T10
    status: done
    red: {command: "python -m pytest tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_tool_catalogue_matches -q", exit: 1}
    green: {command: "python -m pytest tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_tool_catalogue_matches -q", exit: 0}
claims: []
change_id: null
---

# INTEGRACAO_USUARIO — relatório do build

## Desvios do plano

- **Revisão por grupo de tarefas, não por tarefa.** Por pedido do operador de acelerar o
  build, cada grupo (T1–T3, T4–T6, T7–T9, T10) foi executado por um subagente e revisado
  depois, em vez de duas revisões por tarefa. Cada tarefa roda só o próprio teste, os
  testes de regressão diretos que o plano nomeia e `ruff`; goldens e gates de número
  rodam na T10.
- **Vermelho com exit 4.** O node id apontava para um teste que importa a unidade sob
  teste ainda inexistente (`sparkforge.integrate`); o pytest sai 4 nesse caso.

- **Revisão de T1–T3: quatro importantes, corrigidos em seis commits (`6480aa3b` a
  `8f64e460`), cada um com teste vermelho antes.**
  1. manifesto guardava o sha por host, e arquivo compartilhado de `~/.agents/skills` saía
     `editado_pelo_usuario` falso depois de uma subida de versão; passou ao formato 2, um
     sha por arquivo com o conjunto de donos, com migração do formato 1;
  2. escrita não atômica; agora temporário no mesmo diretório e `os.replace`, e manifesto
     ilegível sai `manifesto_ilegivel`;
  3. arquivo preexistente idêntico era adotado e o detach o apagaria; agora `preexistente`;
  4. os testes de AC1 e AC6 mediam menos: falha de build virava skip, e AC6 comparava o
     renderizador com ele mesmo. AC6 passou a comparar o gravado por `integrate` com os
     espelhos do repo (vermelho provado por mutação da tabela de hosts), e o
     `verify_wheel` ganhou a conferência do bundle no pacote instalado.

  Menores: APPDATA derivado do home (o pacote nunca lê o ambiente; a CLI passa o real),
  DEL escapado no TOML, escalar YAML em bloco recusado por nome, chave de manifesto fora
  do HOME recusada, dry-run de `all` simulando disco e manifesto entre hosts. O
  `verify_wheel` não concluiu nesta rodada (o pytest interno bateu no basetemp bloqueado
  e, com `PYTEST_ADDOPTS`, a máquina ficou sem memória); roda na T10.

- **Revisão de T4–T6 (e da primeira rodada): nove importantes, corrigidos em seis commits
  (`c0bf56eb` a `0b4b0821`), cada um com teste vermelho antes.**
  - TOML: `sparkforge` escrito à mão em qualquer forma fora dos marcadores é recusado, e o
    arquivo final é validado com `tomllib` quando ele existe (no 3.10, regex, com a lacuna
    declarada); marcadores só no início de linha;
  - todos os hosts são renderizados antes da primeira escrita, e falha no meio salva o
    manifesto antes de relançar;
  - decisões do controlador: arquivo preexistente não é regravado
    (`preexistente_desatualizado`, exit 0); o manifesto grava a raiz APPDATA, e raiz
    divergente sai `appdata_divergente`; arquivo registrado que sumiu sai `absent`;
  - detach com revert de config recusado mantém o host pendente até o conserto;
  - entrada MCP ou bloco TOML editado pelo usuário sai `editado_pelo_usuario`;
  - a config volta byte a byte (BOM, CRLF, indentação, newline final); mexida em outra
    parte, só a nossa entrada sai, no estilo do arquivo;
  - config que é symlink é gravada no alvo, e o modo é preservado (o teste de modo é
    pulado no Windows, então o vermelho dele não foi visto aqui);
  - `CODEX_HOME`, passado pela CLI como o APPDATA, muda o diretório do Codex. A doc
    confirma o `config.toml` sob `CODEX_HOME`; `agents/` sob ele é inferência pelo
    default `~/.codex`.

- **Revisão de T7–T9: um crítico, seis importantes, corrigidos em `9eb3fe4e`, `33b4f1ae` e
  `aaf34498`, cada um com teste vermelho antes.**
  - crítico: SOBRESCREVER seguia symlink ou junção e apagava arquivo fora do repo
    (reproduzido com `mklink /J`); agora nenhum componente do caminho pode ser link ou
    junção, e tudo o que sai precisa estar dentro do repo (`copia_fora_do_repositorio`);
    12 testes com symlink e junção;
  - conflito filtrado pelo host alvo, e `.agents/skills` só sai do repo com os três
    leitores integrados. O teste do plano que afirmava remover `.claude/agents` num
    `integrate devin` estava errado e foi corrigido;
  - recusa do host força IGNORAR; toda remoção lista cada arquivo antes; prompt sem
    resposta ou inválido vira IGNORAR com motivo;
  - chamada do `claude` com timeout, stdin fechado e UTF-8; detach sem CLI fica
    pendente; add/install repetidos são pulados por `list --json`; versão do plugin com
    o hash do conteúdo, para o Claude atualizar;
  - doctor: uma checagem por host com manifesto ilegível, `warn` com versão divergente,
    e os testes isolam o HOME; a guarda de AC10 vê diretório vazio e roda também pela
    CLI com `cwd` no repo.

- **T10 (`c60c1677`, `95758c1f`).** Guias 02 e 03, README e STATUS escritos a partir do
  código atual; lock de superfície e alegações de corpus relidos. O subagente da T10
  morreu no limite de sessão depois de rodar a suíte; o controlador fechou o resto.
- **Suíte em lotes (um subprocesso por lote, goldens um arquivo por vez):** 61 unidades,
  um vermelho da feature: `tests/test_facts_scan.py::test_nenhum_modulo_varre_com_glob_cru`
  acusou os `glob`/`rglob` crus de `integrate/`. Os três módulos entraram em
  `VARREDURA_CRUA_PERMITIDA` com a razão (`74ce28fc`); arquivo fora do manifesto do design.
  A lista cresceu o corpus, e `VNX-644`, `VNX-667` e `VNX-674` foram relidas à mão
  (`339d58b5`).

- **Revisão final: um crítico, quatro importantes, corrigidos em `139cd440` a `e253064f`.**
  Crítico: com o terminal no HOME, `repo/.agents/skills` é o próprio `~/.agents/skills`,
  e `--on-conflict merge` apagava a integração inteira (154 arquivos, reproduzido); o
  doctor sugeria esse comando. Agora `repositorio_e_o_home` recusa quando o repo é o
  HOME, o APPDATA, o CODEX_HOME, ancestral deles ou está dentro de um destino; a
  detecção sobe até a raiz com `.git`, e sem `.git` o conflito não é avaliado.
  Importantes: o unlock do doctor cita o host que falta; `docs/guia/usos/scan-e-doctor.md`
  dizia nove checagens (são treze); o branch estava atrás da main; e o `verify_wheel`.
  Menores: exit 1 com recusa de conflito; frase de APPDATA/CODEX_HOME corrigida; detach
  do Claude nunca apaga o marketplace sem uninstall; host pendente não conta como
  integrado; testes do doctor isolam o HOME; bundle ruim sai recusa nomeada.
- **Rebase sobre a main (com o #100).** O `STATUS.md` ficou com as duas seções; os
  números de alegação foram relidos pela própria prova (`aa12b83a`, 15 ids).
- **`verify_wheel` não rodou completo nesta máquina.** O sistema o parou três vezes por
  falta de memória (ele roda a suíte inteira dentro do wheel instalado). Rodou a checagem
  leve: wheel construído, instalado num venv isolado, `content_root()` achando 51 skills
  e 12 agents no site-packages, `sparkforge integrate --help` respondendo. O completo é o
  passo `python scripts/verify_wheel.py` do CI do PR. Tamanho do wheel (SC2): 2.051.377
  bytes na main, 2.681.246 com o bundle.
- **Arquivos fora do manifesto do design:** `tests/test_facts_scan.py` (lista de varredura
  permitida), `tests/test_verify_wheel.py` e `scripts/verify_wheel.py` (checagem do bundle),
  `tests/test_forge_cli_doctor.py` e `tests/test_fixtures_golden_mcp_parity.py` (HOME
  isolado e texto das treze checagens), `docs/guia/usos/scan-e-doctor.md`,
  `docs/harness/CURRENT-HARNESS-GAP.md` (alegações).

## Revisão

Revisão por grupo (T1–T3, T4–T6, T7–T9) e revisão final sobre o diff inteiro; cada rodada
está registrada acima com os achados e os commits que os corrigiram. Pendente fora desta
máquina: o `verify_wheel` completo, no CI.
