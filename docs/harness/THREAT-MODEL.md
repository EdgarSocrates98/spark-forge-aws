# THREAT-MODEL — as ameaças da SPEC do SFCI contra o que este repositório de fato tem

A SPEC do **SparkForge Code Intelligence** (SFCI) manda assumir que o repositório analisado pode
ser malicioso, e enumera as ameaças a tratar sob essa hipótese. Ela não é versionada aqui, e assim
permanece: o remote é público. Este documento existe entre aquela enumeração e este repositório, e
responde uma pergunta por ameaça: **qual proteção existe hoje, em que arquivo, e qual teste a
exercita?**

É o irmão de [`AUTHORIZATION-CHAIN.md`](AUTHORIZATION-CHAIN.md) e de
[`UNTRUSTED-CONTENT.md`](UNTRUSTED-CONTENT.md), que cobrem uma fronteira cada. Nenhum dos dois é um
threat model, e o mapa de lacuna registrava a ausência deste arquivo como uma fase inteira
pendente. A outra metade daquela fase é o
[ADR-010](../vnext/adrs/ADR-010-code-intelligence-indice-local.md), que registra as decisões
tomadas; este documento registra o que elas cobrem e o que elas deixam aberto.

## Como ler

- **Fechada** — existe proteção, e existe teste que a exercita. As duas colunas nomeiam arquivo.
- **Parcial** — existe proteção para parte da ameaça, e a parte que falta está escrita na linha.
  Também entra aqui a proteção que é **estrutural sem teste**: ela vale hoje por causa da forma do
  código, e nada acusa se a forma mudar.
- **Aberta** — não existe proteção. A linha diz isso e não oferece consolo.

**Nenhuma linha diz "protegido" sem caminho de arquivo.** Uma proteção que não se consegue apontar
é uma intenção, e intenção não entra numa tabela de ameaça. Onde a coluna de teste está vazia, a
proteção existe e ninguém a tranca — está dito na coluna do que falta, não escondido.

Uma advertência sobre a diferença entre "fechada" e "resolvida": fechada aqui quer dizer que **a
proteção que a SPEC pede para aquela ameaça existe e é exercitada**. Não quer dizer que a ameaça
seja impossível. Um threat model que confundisse as duas coisas seria pior que nenhum, porque
transformaria uma lista de controles numa promessa de segurança.

## A tabela

| ID | Ameaça | Estado | Proteção que existe hoje | Teste que a exercita | O que falta |
|---|---|---|---|---|---|
| T-001 | Path traversal | **Fechada** | `sparkforge/paths.py:resolve_within()` resolve raiz e alvo e recusa o que escapa; `sparkforge/facts/scan.py:iter_source_files()` refaz a checagem dentro do laço, porque um componente intermediário pode ser trocado durante a varredura | `tests/test_facts_scan.py::test_caminho_entregue_de_fora_da_raiz_nao_passa`; `tests/test_rules_loader.py::test_traversal_out_of_the_catalog_is_refused` | — |
| T-002 | Symlink para segredo | **Fechada** | `scan.py:_e_atalho()` recusa symlink **e** junction do Windows, que `is_symlink()` sozinho não vê; a poda remove a pasta antes de `os.walk` descer nela | `tests/test_facts_scan.py::test_symlink_de_pasta_para_fora_da_raiz_nao_e_seguido`; `::test_junction_do_windows_nao_reintroduz_pasta_podada`; `::test_symlink_para_arquivo_dentro_da_raiz_tambem_e_pulado` | — |
| T-003 | `.env` no repositório | **Fechada** | `scan.py:_e_sensivel()` sobre `TALOS_SENSIVEIS`, `SUFIXOS_SENSIVEIS`, `SUFIXOS_SENSIVEIS_COMPOSTOS` e `DIRETORIOS_SENSIVEIS`; o arquivo sai inteiro da varredura, não é lido e redigido | `tests/test_facts_scan.py::test_nome_de_credencial_e_recusado`; `::test_pula_caminho_sensivel_mesmo_com_extensao_pedida`; `tests/test_codeintel_index.py::test_a_denylist_da_varredura_vale_no_indice` | classificação é por nome, nunca por conteúdo, e a recusa é muda |
| T-004 | Chave privada | **Fechada** | duas camadas: o arquivo com nome ou sufixo de chave nunca entra na varredura (`_e_sensivel`), e o literal de default some da assinatura antes de existir nó (`sparkforge/codeintel/ids.py:normalizar_assinatura()`) | `tests/test_facts_scan.py::test_nome_de_credencial_e_recusado`; `tests/test_codeintel_ids.py::test_assinatura_troca_literal_por_marcador` | chave colada dentro de um `.py` comum não é detectada — o que a contém é o banco não guardar corpo |
| T-005 | Credencial AWS | **Fechada** | `sparkforge/facts/secrets.py:looks_like_secret()` é o **único** reconhecedor do pacote, e a redação fica registrada no próprio fato; no índice vale a mesma sanitização de assinatura de T-004 | `tests/test_facts_secrets.py::test_existe_um_unico_detector_de_segredo_no_pacote`; `tests/test_facts_terraform.py::test_akia_pattern_is_flagged_and_redacted` | faltam OAuth client secret, Bearer token e alta entropia como gatilho independente |
| T-006 | Prompt injection em comentário | **Parcial** | nenhum extrator emite comentário, e nenhum campo de catálogo carrega texto do artefato — a garantia é estrutural | `tests/test_harness_untrusted.py::test_nenhum_campo_de_catalogo_carrega_texto_do_artefato` | não existe marcador de confiança no objeto devolvido, nem chave `include_comments` para desligar o que não está ligado |
| T-007 | Prompt injection em docstring | **Parcial** | `sparkforge/codeintel/extract.py:No` não tem campo de corpo nem de docstring, então docstring não chega ao banco por esse caminho | `tests/test_codeintel_index.py::test_corpo_da_funcao_nao_chega_ao_banco` | mesma ausência de política declarada de T-006 |
| T-008 | Tool poisoning | **Fechada** | descrição de tool é literal no módulo (`sparkforge/adapters/tools.py`); nada lê o projeto analisado para montá-la | `tests/test_adapters_tools.py::test_every_tool_has_a_description` | — |
| T-009 | Banco commitado | **Parcial** | `.gitignore` ignora `.sparkforge/local/`, e o banco default do índice mora exatamente lá | `tests/test_codeintel_search.py::TestCaminhoPadrao::test_o_banco_padrao_mora_sob_o_estado_local_ignorado_pelo_git` | o teste tranca o **caminho default**; nada tranca a linha do `.gitignore`, e apagá-la não deixa nada vermelho |
| T-010 | Parser crash | **Parcial** | `extract.py:extrair_nos_ou_none()` devolve `None` e a indexação conta `ilegiveis` em vez de morrer; a captura inclui `ValueError` porque a exceção do byte nulo muda de tipo entre as versões do CI | `tests/test_codeintel_index.py::test_arquivo_que_nao_parseia_e_contado_e_nao_derruba` | não há isolamento em subprocesso: o parser roda no mesmo processo que tudo o mais |
| T-011 | Parser exploit | **Aberta** | — | — | nenhum sandbox e nenhum worker isolado. O que reduz a superfície não é controle: o parser é o `ast` da biblioteca padrão, e não há parser de terceiro no caminho |
| T-012 | Parser DoS | **Parcial** | teto de tamanho por arquivo, com valor distinto para código e para dado (`TAMANHO_MAXIMO_CODIGO_BYTES`, `TAMANHO_MAXIMO_DADOS_BYTES`) | `tests/test_facts_scan.py::test_arquivo_grande_demais_e_pulado_sem_derrubar_a_varredura`; `::test_teto_de_dados_existe_e_nao_e_infinito` | não há limite de CPU, de RAM nem de tempo — nada chama `setrlimit` nem instala alarme |
| T-013 | Zip bomb | **Fechada** | nenhum módulo do pacote abre arquivo compactado — compressão é classificada por sufixo, nunca lida; e a varredura é a única porta de entrada de arquivo | `tests/test_facts_scan.py::test_nenhum_modulo_varre_com_glob_cru`; `::test_extensao_fora_do_padrao_nao_entra` | — |
| T-014 | FIFO ou device file | **Fechada** | `iter_source_files` exige `is_file()` antes de considerar o caminho | `tests/test_facts_scan.py::test_apenas_arquivo_regular` | — |
| T-015 | Binário disfarçado de fonte | **Parcial** | conteúdo que não decodifica como UTF-8 é contado como ilegível e não vira nó; fonte com byte nulo cai em `extrair_nos_ou_none` | `tests/test_codeintel_index.py::test_arquivo_que_nao_parseia_e_contado_e_nao_derruba` | não há detecção positiva de binário **antes** de ler, e nenhum teste usa bytes binários de verdade |
| T-016 | FTS injection | **Fechada** | `sparkforge/codeintel/search.py:construir_consulta()` emite só token entre aspas; termo sem token nenhum nem chega a consultar o banco | `tests/test_codeintel_search.py::test_operador_de_fts_nao_e_executado`; `::test_construtor_so_emite_token_entre_aspas`; `::test_termo_sem_token_nem_chega_a_consultar` | — |
| T-017 | Regex DoS | **Fechada** | nenhuma tool aceita expressão regular; a entrada é tipada e não existe schema de objeto nu por onde uma passaria | `tests/test_adapters_tools.py::test_no_tool_uses_a_bare_object_schema`; `::test_every_tool_declares_properties` | — |
| T-018 | Resultado gigante | **Parcial** | paginação por cursor no envelope de saída e parâmetro `limite` em `buscar()`, com default declarado | `tests/test_adapters_tools.py::test_the_file_is_the_whole_comparison_and_not_the_page`; `tests/test_codeintel_search.py::test_limite_corta_o_resultado` | o teto é de **quantidade de itens**, não de tamanho, e não há ordem escrita de o que sacrificar primeiro |
| T-019 | Repositório gigante | **Parcial** | poda de árvore de dependência e de artefato de build antes de descer nelas, mais o teto por arquivo de T-012 | `tests/test_facts_scan.py::test_pula_arvore_de_dependencia_e_artefato_de_build`; `::test_subpasta_ignorada_nao_e_descida` | não há quota de indexação: nem número de arquivos, nem tempo total, nem tamanho do banco |
| T-020 | Grafo de branch obsoleto | **Aberta** | `root_fingerprint` é gravado em `metadata` e o sha de conteúdo é gravado por arquivo em `files` | — | **nada compara nenhum dos dois na leitura.** O material para detectar obsolescência está no banco e ninguém o consulta |
| T-021 | Contaminação entre worktrees | **Parcial** | o banco default mora sob a raiz analisada, então duas árvores não compartilham arquivo por acidente | `tests/test_codeintel_search.py::test_index_grava_no_default_sob_root_e_search_le_do_mesmo_lugar` | não há namespace por branch: trocar de branch na mesma árvore reusa o mesmo banco silenciosamente |
| T-022 | Exposição do MCP por HTTP | **Parcial** | `sparkforge/adapters/mcp.py:main()` tem `stdio` como transporte default e o loopback como host default; os verbos `code` não são tool MCP — ficam no CLI | `tests/test_plugin_structure.py::test_invokes_the_mcp_module_over_stdio` | o transporte HTTP existe e nada além da flag o separa; se os verbos `code` virarem tool, herdam a superfície |
| T-023 | DNS rebinding em localhost | **Aberta** | — | — | `mcp.py:build_http_app()` não valida `Origin` nem `Host`. O que hoje protege o índice é ele não estar exposto por HTTP, e isso é ausência de caminho, não controle |
| T-024 | Exfiltração entre tools | **Parcial** | perfil de execução como vocabulário canônico, classe de tool derivada da anotação e aprovação por classe, em `sparkforge/agents/autonomy.py` | `tests/test_harness_authorization.py::test_OFFLINE_recusa_tool_de_rede_em_qualquer_grafia`; `::test_a_aprovacao_e_por_classe_e_nao_um_booleano_global` | `authorize()` **não é chamada por nenhum caminho de execução do pacote** — a cadeia é função pura que ninguém consulta, e está registrado em `AUTHORIZATION-CHAIN.md` |
| T-025 | Comprometimento da cadeia de fornecimento | **Fechada** | lock por entrada da matriz de CI, com versão exata e sha256 por distribuição, instalado com `--require-hashes`; SBOM por release em `scripts/gen_sbom.py`; política de vulnerabilidade em `scripts/audit_policy.py`; integridade do vendorizado por manifesto | `tests/test_supply_chain.py::test_every_entry_is_pinned_and_hashed`; `::test_the_build_backend_is_locked`; `tests/test_vendor_caveman.py::test_arvore_confere_com_o_manifest` | a proibição **escrita** de download em runtime continua aberta |
| T-026 | Hook de git malicioso | **Parcial** | nada em `sparkforge/` invoca git nem levanta processo; a superfície de execução do próprio repositório é lista fechada de string exata, com deny-list de construção de execução arbitrária | `tests/test_execution_surface.py::test_todo_hook_esta_na_lista_fechada`; `::test_nenhum_hook_usa_construcao_de_execucao_arbitraria` | o teste cobre os hooks **deste** repositório; a ausência de git no pacote é estrutural e nada a tranca |
| T-027 | Abuso de configuração de git | **Parcial** | o pacote não lê metadado de git em lugar nenhum, então não há `git config` a honrar | — | estrutural, sem teste. Acrescentar uma leitura de git ao pacote não deixaria nada vermelho |
| T-028 | Vazamento de fonte por log | **Fechada** | não existe `logging` no pacote — a saída é o envelope JSON —, e o resumo do índice devolve impressão da raiz, nunca o caminho | `tests/test_codeintel_search.py::test_nao_expoe_caminho_absoluto_da_raiz` | a ausência de `logging` é estrutural; o teste tranca a saída do resumo, que é a superfície que existe hoje |
| T-029 | Vazamento de fonte por métrica | **Fechada** | `search.py:resumo()` devolve contagem, versão de schema, versão de engine e data — nenhum nome de símbolo, nenhum trecho | `tests/test_codeintel_search.py::test_conta_o_que_o_banco_tem_e_quando_foi_feito`; `::test_nao_expoe_caminho_absoluto_da_raiz` | — |
| T-030 | Subprocesso arbitrário | **Parcial** | os binários que este repositório levanta são lista fechada, e nenhum argumento carrega metacaractere de shell | `tests/test_execution_surface.py::test_so_levantam_binario_da_lista`; `::test_nenhum_argumento_carrega_metacaractere_de_shell` | não há allowlist **do pacote** porque não há chamada de subprocesso no pacote — estrutural, sem teste que o tranque |

Somando a coluna de estado: **13** fechadas com teste, **14** parciais e **3** abertas.

## O que a tabela mostra quando se olha o conjunto

**A maior parte do que está fechado é fronteira de leitura, e isso não é coincidência.** Traversal,
symlink, arquivo sensível, arquivo irregular, tamanho, compactado: são as ameaças em que a
proteção cabe num ponto só — a varredura — e esse ponto já existia neste repositório antes de
qualquer índice, com teste, porque os extratores de fato precisavam dele. O índice herdou a
fronteira em vez de escrever a segunda. Foi a decisão de subsistema nativo do ADR-010 pagando pela
primeira vez.

**A maior parte do que está parcial é a mesma ausência repetida: falta o enforcement de runtime.**
Isolamento de parser, limite de CPU e RAM, allowlist de subprocesso, cadeia de autorização
efetivamente chamada — as quatro linhas descrevem controles que existem como decisão, como
vocabulário ou como forma do código, e não como algo que o processo faça enquanto roda. É uma
única lacuna vista de quatro ângulos, e ela tem nome no mapa de lacuna: `sanitize_environment`,
`install_audit_hook`, `apply_resource_limits` e `lock_security_profile`, nenhum dos quatro
escrito.

**As três abertas não são do mesmo tipo, e a diferença decide o que fazer com cada uma.** O grafo
obsoleto é a mais barata e a mais incômoda: o dado para detectá-lo — sha por arquivo, impressão de
raiz — **já está gravado no banco**, e falta a comparação. É a única aberta que se fecha sem
material novo. O exploit de parser é a mais cara, porque exige o worker isolado que nenhuma outra
linha exige. E o DNS rebinding é a que hoje não tem consequência, porque o índice não está exposto
por HTTP nenhum — o risco entra no dia em que os verbos `code` virarem tool MCP, e essa é
exatamente a razão para registrá-lo agora em vez de na véspera.

**A palavra "estrutural" aparece quatro vezes, e ela merece desconfiança.** Não há `logging` no
pacote; não há `subprocess` no pacote; não há leitura de git no pacote; não há campo de corpo no
nó. As quatro afirmações são verdadeiras hoje e nenhuma delas é defendida por teste, exceto a
última. Garantia estrutural é a mais forte que existe enquanto a estrutura não muda, e a mais
frágil no dia seguinte — porque o defeito entra por acréscimo, e acréscimo é o que ninguém revisa
como mudança de segurança. Cada uma dessas linhas está marcada como parcial por esse motivo, e não
por dúvida sobre o fato.

## O que este documento deliberadamente não faz

Ele não classifica risco, não atribui probabilidade e não prioriza. Priorização depende do
ambiente em que o SparkForge roda, e este repositório não tem como saber se ele está numa
workstation com um repositório de cliente ou num CI com um repositório público. O que o documento
faz é remover a ambiguidade sobre **o que existe** — para que a priorização, quando alguém a
fizer, seja feita sobre fato e não sobre memória.

Ele também não cobre as ameaças que a SPEC não enumera. A lista é a da SPEC, ameaça a ameaça, e
uma ameaça que não esteja nela não está aqui — inclusive as que este repositório talvez devesse
tratar. Ampliar a lista é decisão de outra fase, e inventá-la aqui misturaria "o que a SPEC pede"
com "o que achamos", que são as duas colunas que este documento existe para manter separadas.
