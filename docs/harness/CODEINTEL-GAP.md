# CODEINTEL-GAP — o que já existe contra o que a SPEC do SFCI pediria

A SPEC do **SparkForge Code Intelligence** (SFCI) propõe um motor local e offline de economia
de token: um índice de código em SQLite com FTS, extractors de Python e PySpark, recuperação
sem embedding, um orçamento de token com objeto de contexto canônico, onze tools MCP novas e
uma camada de segurança inteira — invariantes numerados, threat model, perfis, sandbox de
filesystem, firewall de segredo e defesa contra prompt injection.

Ela não é versionada neste repositório, e assim permanece: o remote é público e material de
referência não entra nele. Este documento existe entre a exigência e o repositório, e responde,
componente a componente, uma única pergunta antes de qualquer módulo novo: **isso já existe
aqui, possivelmente sob outro nome?** É o mesmo gênero de
[`CURRENT-HARNESS-GAP.md`](CURRENT-HARNESS-GAP.md), [`GLUE6-GAP.md`](GLUE6-GAP.md) e
[`MIGRATIONS-GLUE-GAP.md`](MIGRATIONS-GLUE-GAP.md), aplicado a uma quarta exigência, e segue as
mesmas regras de classificação.

## Por que este mapa existe

O dono do projeto declarou três motivos, e eles são critério de aceite:

1. **Autossuficiência** — economia de token sem depender de um MCP externo instalado noutra
   máquina.
2. **Segurança da informação em qualquer ambiente** — o SparkForge processa código de cliente,
   possivelmente proprietário.
3. **Economia máxima sem perder qualidade** — as duas metades contam.

O mapa mede quanto de cada um já está aqui.

## Como classificar

- **EXISTE, com teste** — nomeio o módulo e o arquivo de teste que exercita o comportamento.
- **EXISTE, sem teste** — nomeio o módulo; nada prova o comportamento.
- **EXISTE PARCIAL** — nomeio o que está lá e o que falta, especificamente.
- **NÃO EXISTE** — digo isso.

Nenhuma linha diz "existe" sem caminho. Nenhuma diz "testado" sem nome de arquivo de teste.

## Achado central

**A maior parte do grafo que a SPEC quer construir já é produzida hoje — e jogada fora ao fim
de cada chamada.** Os extractors de `sparkforge/facts/` já derivam leitura e escrita de tabela,
aresta de chamada, ciclo, alcançabilidade a partir de entrypoint, predicado e projeção de SQL,
schema de catálogo e ponto cego nomeado. Nada disso persiste: cada análise reparseia a árvore
inteira, monta o grafo em memória, serializa fatos e esquece. O índice que a SPEC pede não
acrescentaria extração — acrescentaria **memória**.

O segundo achado é o oposto, e é grave: **o custo de token do repositório hoje é negativo**. Na
fixture `fixtures/pyspark/clean_job`, o payload de fatos é **5.6** vezes maior que o código-fonte
que o originou. Devolver o arquivo inteiro custaria menos que devolver a análise dele. A causa
não é o dado útil — é o envelope repetido fato a fato.

O terceiro era de segurança, era o mais sério, e **foi pago**: quando este mapa foi escrito a
detecção de segredo tinha implementação duplicada, nenhum teste sobre a canônica, e falhava
contra metade da lista que a própria SPEC enumera. As fases J0 a J3 fecharam essa dívida e mais
uma parte do que este documento classificava como ausente — a seção final,
[O que a SPEC ainda pede](#o-que-a-spec-ainda-pede-depois-das-fases-j0-a-j3), separa o que
sobrou. Um mapa que superestima o que falta erra tanto quanto um que subestima, e este errava
por excesso até esta revisão.

---

## 1. Invariantes de segurança e threat model

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Conteúdo de repositório é dado não confiável, nunca instrução | EXISTE, com teste | É literalmente o invariante da fase I2, escrito em [`UNTRUSTED-CONTENT.md`](UNTRUSTED-CONTENT.md) e travado no código: `Fact.attrs` não entra no `Finding`, e `Finding.evidence` carrega só ids, nunca texto. O teste deriva o conjunto de extratores que carregam texto de terceiro executando os extratores, não relendo uma lista | `tests/test_harness_untrusted.py` |
| Fail closed em controle de segurança | EXISTE, com teste | `sparkforge/migration/assessment.py:assess()` faz eixo sem evidência nascer `BLOCKED` e nunca `PASS`; gate em `FAIL` força `NO_GO`. Dúvida entre permitir e bloquear já resolve para bloquear em todo o motor de avaliação | `tests/test_migration_assessment.py` |
| Descrição de tool nunca derivada do projeto analisado | EXISTE, com teste | Toda descrição é literal em `sparkforge/adapters/tools.py`; nenhuma é montada a partir de arquivo lido | `tests/test_adapters_tools.py` |
| Nenhuma tool aceita comando de shell | EXISTE, com teste | O catálogo inteiro declara `properties` explícitas, e nenhuma delas é `command`. O teste cobra a declaração de propriedades por tool, o que impede schema de objeto nu por onde uma chave arbitrária entraria | `tests/test_adapters_tools.py` |
| Nenhuma tool aceita SQL arbitrário para execução | EXISTE, com teste | Mesmo mecanismo: nenhuma propriedade do catálogo recebe SQL para executar. `sparkforge/facts/sql_literal.py` **lê** SQL como literal de código, e nunca o executa | `tests/test_adapters_tools.py` |
| Nenhum código descoberto no repositório é executado | EXISTE, com teste | A extração é `ast.parse` sobre texto, nunca `import`, `eval` ou `exec` do módulo analisado. `sparkforge/facts/pyspark_ast.py:extract_tree()` percorre a árvore e nunca carrega o que leu | `tests/test_fixtures_golden.py` |
| Superfície de execução do próprio repositório fechada e auditada | EXISTE, com teste | `tests/test_execution_surface.py` fixa a lista de hooks, recusa construção de execução arbitrária, e cobra que todo servidor MCP seja spawn de argv sem metacaractere de shell | `tests/test_execution_surface.py` |
| Source read-only | EXISTE PARCIAL | Nenhum extrator abre arquivo do repositório analisado para escrita, e há teste medindo que uma tool sem `out_path` não escreve nada. Mas isso prova a **tool**, não o **invariante**: não existe checagem que varra a superfície inteira e afirme que nada escreve no source | `tests/test_adapters_tools.py` |
| Zero network egress | EXISTE PARCIAL | `ExecutionProfile.OFFLINE` é teto, não conselho: `sparkforge/agents/autonomy.py:authorize()` recusa tool de rede sob esse perfil em qualquer grafia, e aprovação explícita **não** fura o teto. O que falta é enforcement de runtime — nenhum audit hook, nenhum bloqueio de socket, nenhuma sanitização de ambiente. O teto vale para quem passa por `authorize()`; um `import requests` dentro de um extrator não passa por lugar nenhum | `tests/test_harness_authorization.py` |
| Confinamento ao root autorizado | EXISTE PARCIAL | O algoritmo deixou de ser cópia: `sparkforge/paths.py:resolve_within()` é a implementação única, e `rules/loader.py`, `knowledge_ref.py` e `agents/autonomy.py` chamam ela. `authorize()` passou a receber `arguments` e `root` e recusa argumento de caminho que escape da raiz do case, inclusive `~` e lista de caminhos item a item. `facts/scan.py:iter_source_files()` confina cada arquivo visitado sob a raiz varrida. O que falta é o outro lado da mesma pergunta: nenhum dos quatro caminhos de execução chama `authorize()`, então a verificação existe e está desligada — e a **raiz** apontada de fora não é confinada por nada, porque não há raiz autorizada contra a qual compará-la | `tests/test_harness_authorization.py` |
| Sem telemetria conversacional | EXISTE, com teste | `sparkforge/observability/store.py:SQLiteTraceStore` grava trace da execução do próprio SparkForge, e nada no repositório lê histórico de agente de terceiro. A ressalva que esta linha registrava — `.sparkforge/traces.db` fora do `.gitignore` — foi fechada pela fase J0: `git check-ignore` reconhece hoje `traces.db`, `cache/` e `local/`, cada um com a razão escrita ao lado da regra | `tests/test_observability.py` |
| Sem herança de credencial em worker de parsing | NÃO EXISTE | Não há worker de parsing, então também não há sanitização de ambiente. Hoje o extrator roda no mesmo processo, com o mesmo ambiente, e nada impede um extrator futuro de ler `AWS_SECRET_ACCESS_KEY` | — |
| Política de retenção de source (corpo de função e cache) | EXISTE PARCIAL | O banco existe desde a fase J3, e a decisão que esta linha cobrava foi tomada **no schema**: `sparkforge/codeintel/db.py` não tem coluna de corpo, e `nodes.normalized_signature` chega já sanitizada. Dois testes medem que o corpo não passa — `test_corpo_da_funcao_nao_chega_ao_banco` e `test_nenhum_no_carrega_corpo`. O que falta é a política **escrita**: nada declara por quanto tempo o índice vale, quando ele é apagado, nem o que muda no dia em que a recuperação de trecho de código existir e o snippet passar a ser material a reter | `tests/test_codeintel_index.py` |
| Threat model escrito, com ameaça numerada e proteção | NÃO EXISTE | Nenhum documento do repositório enumera ameaça contra repositório malicioso. [`AUTHORIZATION-CHAIN.md`](AUTHORIZATION-CHAIN.md) e [`UNTRUSTED-CONTENT.md`](UNTRUSTED-CONTENT.md) cobrem duas fronteiras, cada um a sua, e nenhum dos dois é um threat model | — |

## 2. Security profiles e runtime hardening

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Perfil de execução como vocabulário canônico | EXISTE, com teste | `ExecutionProfile` em `sparkforge/registry/models.py`, com `OFFLINE` entre os membros; perfil não reconhecido **recusa** em vez de virar default | `tests/test_harness_authorization.py` |
| Classe de tool derivada da anotação, não de uma lista | EXISTE, com teste | `sparkforge/agents/autonomy.py:tool_class()` deriva de `readOnlyHint`, `openWorldHint` e `destructiveHint`; trocar a anotação troca a classe, e tool desconhecida falha fechada | `tests/test_harness_authorization.py` |
| Aprovação por classe, e não booleano global | EXISTE, com teste | Aprovar mutação local não libera tool de nuvem, e cada classe exige a sua própria aprovação nomeada | `tests/test_harness_authorization.py` |
| `offline-strict` como perfil com matriz ALLOW/DENY declarada | EXISTE PARCIAL | O teto existe e morde (`_teto_recusa_rede`), mas a matriz da SPEC — Code Intelligence, Rules, Facts, Case, AWS, Internet, Shell, Source writes, Repo execution, cada um ALLOW ou DENY — não existe como dado. O que existe é uma regra: perfil offline recusa tool de nuvem | `tests/test_harness_authorization.py` |
| `aws-readonly` como perfil | EXISTE PARCIAL | `ToolClass.CLOUD_READ` existe e é distinta de `CLOUD_MUTATION`, o que é metade do que o perfil pede. A outra metade — *raw source retrieval DENY* quando a capacidade AWS está ligada — não existe, porque não há recuperação de source para negar | `tests/test_harness_authorization.py` |
| Separação: quem devolve source não tem AWS | NÃO EXISTE | É a defesa contra a cadeia comentário malicioso → LLM manipulado → leitura de source → tool de mundo aberto. Hoje o mesmo processo faz as duas coisas, e a anotação `openWorldHint` classifica a tool sem separar o processo | — |
| `sanitize_environment`, `install_audit_hook`, `apply_resource_limits`, `lock_security_profile` | NÃO EXISTE | Nenhum dos quatro. O perfil é consultado na autorização e nunca travado no processo | — |
| Modo hardened em Linux com namespace de rede isolado | NÃO EXISTE | Nenhum caminho de sandbox de sistema operacional | — |

## 3. Sandbox de filesystem, symlink e denylist

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Algoritmo de resolução segura de caminho | EXISTE PARCIAL | O algoritmo mora em `sparkforge/paths.py:resolve_within()`, uma vez só, e a varredura acrescentou o que vinha depois dele na SPEC: arquivo regular, recusa de atalho, denylist, teto de tamanho por tipo e confinamento — tudo em `sparkforge/facts/scan.py:iter_source_files()`. Falta o item da SPEC que continua sem existir em lugar nenhum: **detecção de conteúdo binário** antes de decodificar. E falta o sinal: pular por denylist, por teto ou por poda é silencioso, e o próprio módulo registra essa pendência na docstring | `tests/test_facts_scan.py` |
| Confinamento de caminho vindo de fora do processo | EXISTE PARCIAL | Fechado por dentro, aberto por fora. Por dentro: `iter_source_files()` resolve cada arquivo visitado e descarta o que cair fora da raiz varrida, mesmo com componente intermediário trocado durante a varredura. Por fora: `authorize()` sabe recusar argumento de caminho que escape da raiz do case, mas nenhum dos quatro caminhos de execução — `adapters/mcp.py`, `adapters/tools.py`, `adapters/cli.py`, `agents/supervisor.py` — chama `authorize()`, então as tools de análise continuam recebendo o `path` que quiserem passar. A raiz apontada é confinada em relação a si mesma, e a nada mais | `tests/test_facts_scan.py` |
| Symlink recusado por padrão | EXISTE, com teste | `sparkforge/facts/scan.py:_e_atalho()` recusa symlink de arquivo, symlink de pasta e reparse point em geral — inclusive **junction do Windows**, que `os.path.islink` não vê e que `mklink /J` cria sem privilégio de administrador. Recusar é diferente de resolver e conferir contenção: symlink apontando para dentro da raiz também é pulado, e há teste para esse caso exato | `tests/test_facts_scan.py` |
| Denylist de caminho sensível | EXISTE, com teste | Quatro listas em `sparkforge/facts/scan.py`, separadas por razão: `DIRETORIOS_SENSIVEIS` (`.aws`, `.ssh`, `.gnupg`, `.kube`, `secrets`, `cdk.out`, …), `TALOS_SENSIVEIS` (`.env`, `id_rsa`, `credentials`, `kubeconfig`, `.netrc`, …), `SUFIXOS_SENSIVEIS` (`.pem`, `.key`, `.tfstate`, `.tfvars`, …) e `SUFIXOS_SENSIVEIS_COMPOSTOS`, que pega `terraform.tfstate.json`. O casamento é por componente delimitado, nunca por prefixo: `secrets.json` é recusado e `secrets_manager.tf` não, e há teste para os dois lados | `tests/test_facts_scan.py` |
| Exclusão de árvore de dependência e de artefato | EXISTE, com teste | `DIRETORIOS_IGNORADOS` em `sparkforge/facts/scan.py` poda `.venv`, `venv`, `site-packages`, `node_modules`, `vendor`, `build`, `dist`, `target`, `.git`, `.terraform`, `.sparkforge` e os caches de ferramenta. A poda é feita **no lugar**, sobre a lista de subpastas do `os.walk`, então a varredura nem desce nelas — filtrar no fim daria a mesma lista tendo pago para listar o `.venv` inteiro. Os catorze `rglob` soltos dos extratores passaram todos por aqui, e um gate estrutural recusa o décimo quinto | `tests/test_facts_scan.py` |
| Limite de tamanho por arquivo e detecção de binário | EXISTE PARCIAL | O teto existe e é **por tipo**, porque a razão de cada um é diferente: código-fonte tem teto de 1 MiB, pela regra de não montar AST de arquivo gerado; artefato de dados tem teto de 128 MiB, porque o operador apontou para ele de propósito. Extensão desconhecida cai no teto de dados, e esse é o único ponto fail-open do módulo, declarado onde acontece. Falta a outra metade da linha: **detecção de binário** não existe, nem piso de tamanho | `tests/test_facts_scan.py` |

## 4. Secret firewall

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Reconhecedor canônico de segredo em par chave/valor | EXISTE, com teste | `sparkforge/facts/secrets.py:looks_like_secret()` é o módulo canônico, e **a fase J0 fechou a dívida que esta linha registrava**. Quando o mapa foi escrito nenhum arquivo de `tests/` o importava; hoje `tests/test_facts_secrets.py` o exercita. O detector deixou de depender do nome da chave: PAT do GitHub, JWT, chave privada PEM e token do Slack passam a ser reconhecidos pelo valor | `tests/test_facts_secrets.py` |
| Redação registrada no próprio fato | EXISTE, com teste | O par vira `<redigido>` e `attrs["redacted"] = True`: a evidência mostra que havia credencial sem mostrar a credencial. É a distinção que a SPEC exige entre `{"sensitive": true}` e `{"secret": "AKIA..."}` | `tests/test_facts_terraform.py` |
| O scanner nunca registra o segredo | EXISTE, com teste | Mesma disciplina no caminho de EMR: a propriedade sai redigida no golden, e o teste mede a redação, não a detecção | `tests/test_facts_emr_cluster.py` |
| Uma implementação só | EXISTE, com teste | **Fechado pela fase J0.** As cópias privadas `_looks_like_secret` de `sparkforge/facts/terraform.py`, `emr_cluster.py` e `emr_serverless.py` foram removidas, e um gate estrutural por AST impede a próxima: `test_existe_um_unico_detector_de_segredo_no_pacote` quebra quando a segunda é escrita, não quando ela diverge — porque divergir é o momento em que o conserto já é caro | `tests/test_facts_secrets.py` |
| Detectores que a SPEC enumera | EXISTE PARCIAL | A fase J0 acrescentou os padrões **por valor**, e eles não olham o nome da chave: access key da AWS, token clássico e fine-grained do GitHub, JWT, cabeçalho PEM de chave privada em qualquer variante, token do Slack — mais senha embutida em URL, que é o caso do DSN com credencial. O gatilho por nome de chave continua existindo ao lado, para segredo proprietário que não tem prefixo publicado. O que a SPEC pede e não está lá: **OAuth client secret**, **Bearer token** solto e **alta entropia como gatilho independente** — entropia hoje só dispara acompanhada de nome de chave suspeito, de propósito, porque sozinha ela redige sha, caminho de S3 e nome de classe Java | `tests/test_facts_secrets.py` |
| Arquivo classificado sensível sai inteiro do índice | EXISTE PARCIAL | A decisão anterior passou a existir, e ela acontece **antes da leitura**: `sparkforge/facts/scan.py:_e_sensivel()` recusa o arquivo inteiro, então nem fato nem símbolo nem metadado nascem dele — nenhum extrator chega a abri-lo. Duas coisas faltam para a linha fechar. A classificação é por **nome**, nunca por conteúdo: um `config.py` com chave privada colada dentro é indexado como qualquer outro arquivo. E a recusa é muda: quem lê a saída não distingue "não havia nada" de "havia e eu recusei" | `tests/test_facts_scan.py` |

## 5. Prompt injection defense

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Corpus de injeção exercitado ponta a ponta | EXISTE PARCIAL | `tests/test_harness_untrusted.py` monta um cenário com texto de injeção plantado no artefato, roda a extração e mede que o texto chega aos fatos **e** que nenhum campo de catálogo o carrega. É um corpus de um caso, e ele prova a fronteira certa | `tests/test_harness_untrusted.py` |
| Comentário e docstring fora do dado devolvido | EXISTE PARCIAL | Na prática nenhum extrator emite comentário ou docstring: `Fact.subject.snippet` é a linha exata do nó analisado. Mas isso é consequência do que os extratores escolheram observar, não uma política com chave — não existe `include_comments` nem `include_docstrings` para desligar, porque não existe o caminho que os ligaria | `tests/test_harness_untrusted.py` |
| Rótulo de confiança no objeto devolvido | NÃO EXISTE | A garantia é estrutural (evidência é lista de id, nunca texto) e está documentada, mas nenhum payload carrega um campo `trust` dizendo ao consumidor que aquele texto é de terceiro. Quem lê o JSON precisa saber de fora | — |
| Detector de conteúdo com forma de instrução | NÃO EXISTE | Nada procura "ignore previous", "system prompt" ou equivalente, nem para marcar cautela | — |

## 6. Estado local e política de git

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Diretório de estado por repositório analisado | EXISTE, com teste | `.sparkforge/` já é isso: `case.yaml`, `facts.json`, `findings.json`, `handoff.md` e `artifacts/manifest.json`, escritos por `sparkforge/case/store.py` | `tests/test_case_store.py` |
| Banco SQLite local já em uso | EXISTE, com teste | `sparkforge/observability/store.py:SQLiteTraceStore` cria e escreve `.sparkforge/traces.db`. O precedente de "SparkForge tem banco local" já existe; o que não existe é a política sobre ele | `tests/test_observability.py` |
| Separação entre o que é handoff e o que é bruto | EXISTE, com teste | O `.gitignore` versiona `case.yaml` e o manifesto e ignora `.sparkforge/artifacts/*`, com a razão escrita ali: artefato bruto pode ter dado de negócio. A disciplina de auditar o que o repositório ignora tem teste | `tests/test_execution_surface.py` |
| `.sparkforge/local/` fora do git | EXISTE, sem teste | As três linhas entraram no `.gitignore` no commit `715a657`, e `git check-ignore -v` confirma as três: `.sparkforge/traces.db`, `.sparkforge/cache/` e `.sparkforge/local/`. `sparkforge/codeintel/db.py:BANCO_PADRAO` aponta o índice para dentro de `local/`, e `tests/test_codeintel_search.py::test_o_banco_padrao_mora_sob_o_estado_local_ignorado_pelo_git` tranca **essa** metade. A metade que ninguém tranca é a regra em si: apagar a entrada `.sparkforge/local/` do `.gitignore` não quebra teste nenhum, ao contrário de `.claude/settings.local.json`, que tem gate próprio em `tests/test_execution_surface.py` | — |
| Permissão restrita de diretório e arquivo, com umask | NÃO EXISTE | Nada no repositório define permissão de arquivo criado | — |

## 7. Banco, schema e taxonomia de grafo

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Ponto cego como cidadão de primeira classe | EXISTE, com teste | É lei da casa antes de ser pedido da SPEC: onze extratores emitem um kind `*.unresolved` com vocabulário fechado de razão, e o envelope das tools conta `unresolved` sobre o conjunto inteiro — filtrar por kind **não** faz o ponto cego sumir do relatório. Fonte limpa reporta zero, nunca ausência | `tests/test_adapters_tools.py` |
| Id determinístico de nó, derivado de conteúdo | EXISTE, com teste | O nó passou a existir, e o id dele também: `sparkforge/codeintel/ids.py:node_id()` deriva BLAKE2b de caminho, kind, nome qualificado e assinatura, com separador `\x00` entre campos para que fronteira de campo não vire ambiguidade. Reindexar sem mudança produz os mesmos ids, e há teste medindo isso ponta a ponta. O nome precisa ser mesmo qualificado, e isso é contrato de quem chama: com nome simples, `adapters/platforms/targets.py` sozinho já colide quatro vezes | `tests/test_codeintel_ids.py` |
| Taxonomia de aresta | EXISTE PARCIAL | `pyspark.callgraph_edge` (chamador → chamado) mais os quatro kinds `callgraph.*` cobrem a aresta de chamada e o que se deriva dela. `import`, `herança`, `referência de tipo` e `escrita/leitura de tabela como aresta de grafo` não existem como aresta — leitura e escrita existem como **fato**, com o alvo literal dentro | `tests/test_fixtures_golden_callgraph.py` |
| Banco com schema versionado, migrations e locking | EXISTE PARCIAL | `sparkforge/codeintel/db.py` cria `metadata`, `files`, `nodes`, `unresolved_refs` e `symbols_fts`, grava `schema_version` em `metadata` e confere `PRAGMA foreign_keys` relendo o valor efetivo, porque esse pragma falha calado e a falha dele deixa `ON DELETE CASCADE` declarado sem acontecer. Três coisas da linha faltam. **Migration** não existe: nada lê `schema_version` para decidir o que fazer — `search.py:resumo()` só o devolve, e um banco de versão antiga é aberto e consultado como se fosse da versão de hoje. **Locking** de índice não existe: há `busy_timeout` de conexão, que é espera de escritor do SQLite, e não guarda contra duas indexações concorrentes da mesma árvore. E `edges` não existe, por decisão registrada no próprio módulo | `tests/test_codeintel_db.py` |
| Índice FTS sobre símbolo e signature | EXISTE PARCIAL | A metade do símbolo existe: `symbols_fts` é FTS5 com `name` e `qualified_name`, e o tokenizador default é o que faz `iter_source_files` ser achável por `source`. A metade da **signature não existe**: `normalized_signature` mora em `nodes`, como coluna comum, e não é coluna do FTS — buscar por tipo de parâmetro ou por anotação de retorno não tem por onde. As colunas foram lidas do banco criado, não da DDL: `node_id`, `name`, `qualified_name` | `tests/test_codeintel_db.py` |
| Sanitização de signature antes de armazenar | EXISTE, com teste | `sparkforge/codeintel/ids.py:normalizar_assinatura()` troca valor literal de default pelo marcador `<literal>` e preserva nome, ordem dos parâmetros e anotação de retorno. É varredor com profundidade e não substituição por expressão regular, porque default abre parêntese, aninha chamada e carrega vírgula dentro de aspas. `codeintel/extract.py` aplica antes de o nó existir, então nenhum valor literal chega ao banco por esse caminho | `tests/test_codeintel_ids.py` |

## 8. Extractors

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Arquitetura de extractor com identidade e versão | EXISTE, com teste | Todo extrator declara `EXTRACTOR_ID` e o grava em `provenance` de cada fato, ao lado do artefato e do sha256 dele. É a procedência que a SPEC pede por nó, já entregue por fato | `tests/test_fixtures_golden.py` |
| Extractor PySpark | EXISTE, com teste | `sparkforge/facts/pyspark_ast.py:extract_source()` cobre leitura, escrita, cache, join, explode, window, `conf.set`, UDF, dedup, coleta no driver, laço, particionamento e cadeia de método, com golden por fixture | `tests/test_fixtures_golden.py` |
| Grafo de dados tabela → job → tabela | EXISTE PARCIAL | `pyspark.read` e `pyspark.write` carregam o alvo literal quando ele é literal, e `sparkforge/facts/consumers.py` cruza produção com inventário de consumidor. O que falta é o grafo: os dois lados existem como fato solto, ninguém liga um ao outro numa estrutura consultável | `tests/test_fixtures_golden.py` |
| Call graph com ciclo e alcançabilidade a partir de entrypoint | EXISTE, com teste | `sparkforge/facts/call_graph.py` deriva quais funções existem, quanto trabalho Spark cada uma concentra, o que é alcançável de cada entrypoint e a que profundidade mínima, quais ciclos existem e o que ninguém referencia. É função pura sobre fatos: nunca lê arquivo, nunca reparseia | `tests/test_fixtures_golden_callgraph.py` |
| Lineage dinâmico declarado em vez de silenciado | EXISTE, com teste | O que o extrator não resolve vira `pyspark.unresolved` com razão de vocabulário fechado, e o filtro por kind não consegue esconder isso do envelope | `tests/test_adapters_tools.py` |
| Extractor de SQL com predicado e projeção | EXISTE, com teste | `sparkforge/facts/sql_literal.py` lê SQL embutido em literal de código e emite `sql.predicate`, `sql.projection`, `sql.predicate.partition_filter` e as formas enriquecidas | `tests/test_fixtures_golden_sql.py` |
| Símbolos gerais de Python | EXISTE PARCIAL | Duas metades dessa linha fecharam na fase J3, num extrator novo: `sparkforge/codeintel/extract.py` emite **nó de classe** e **nome qualificado** com a pilha de escopo inteira, distingue `method` de `function` pelo tipo do escopo imediato, e não perde `def` dentro de `if TYPE_CHECKING` porque herda de `NodeVisitor` em vez de percorrer só o corpo das definições. Continuam sem existir: **grafo de import** e **hierarquia de tipo** — a assinatura de classe guarda o texto das bases, e ninguém as resolve em nó. Do lado dos fatos, `pyspark.function_def` continua sendo a tabela de símbolo com forma de PySpark, e as duas visões ainda não se falam | `tests/test_codeintel_extract.py` |
| Lineage de DataFrame variável a variável | NÃO EXISTE | O extrator entende a cadeia de método dentro de uma expressão, mas não segue o valor de uma variável para outra | — |
| Workers de parsing isolados, autenticados, com limite | NÃO EXISTE | A extração roda no processo, sem worker, sem autenticação de worker e sem limite de memória, tempo ou tamanho | — |

## 9. Indexação incremental e freshness

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Manifesto de conteúdo verificável, com detecção de adulteração | EXISTE, com teste | `knowledge/offline-manifest.json` mais `sparkforge/tools/offline.py:OfflineKnowledgeIndex.verify()` conferem SHA-256 documento a documento e separam ausência de divergência. O hash normaliza fim de linha porque o contrário fazia o gate depender da plataforma — a lição vale inteira para um índice de código | `tests/test_offline_expansion.py` |
| Sinal de staleness por arquivo | EXISTE PARCIAL | O material passou a estar guardado: `files` grava `content_sha256`, `size_bytes`, `modified_ns` e `indexed_at` por arquivo indexado, ao lado do `provenance.artifact_sha256` que todo fato já carregava. O que continua não existindo é a **comparação**: nada relê o disco para conferir se o sha mudou, e `code status` devolve quando o índice foi feito sem dizer se ele ainda vale. Índice velho responde "nenhum símbolo" com a mesma cara com que responde sobre símbolo inexistente | `tests/test_codeintel_index.py` |
| Git lido sem executar hook | EXISTE, com teste | A superfície de execução do repositório é uma lista fechada e auditada, e nenhum hook usa construção de execução arbitrária | `tests/test_execution_surface.py` |
| Índice persistente, completo e incremental | EXISTE PARCIAL | Completo existe desde a fase J3: `sparkforge/codeintel/index.py:indexar()` varre pela mesma fronteira de leitura de `facts/scan.py`, extrai por `ast` e persiste em SQLite com FTS5. Incremental **não**: `indexar` apaga `files` e `symbols_fts` e recarrega tudo, de propósito — reaproveitar exigiria saber o que mudou, e construir isso de improviso deixaria nó fantasma no banco enquanto isso | `tests/test_codeintel_index.py` |
| Strict tree, fingerprint de worktree, namespace por branch | NÃO EXISTE | `db.py:impressao_da_raiz()` guarda um digest da **raiz**, e é fácil confundir isso com o que a linha pede: ele identifica qual diretório foi indexado sem nomeá-lo, e nada mais. Não é fingerprint de estado de árvore, não vê arquivo sujo nem branch, e nem sequer é conferido na leitura — o banco de outra raiz é aberto e respondido normalmente. Namespace por branch não existe | — |
| Contexto do que mudou, e teste afetado | NÃO EXISTE | `sparkforge/facts/*` compara Terraform antes e depois (`analyze_terraform_diff`), que é diff de infraestrutura. Diff de código, símbolo alterado e teste afetado não existem | — |

## 10. Retrieval, ranking e orçamento de token

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Busca local determinística, sem embedding e sem rede | EXISTE, com teste | `OfflineKnowledgeIndex.search()` é busca por frequência de termo sobre `knowledge/`, deliberadamente burra: sem índice invertido, sem embedding, sem chamada externa. É a proibição da SPEC já cumprida — no corpo errado, porque busca conhecimento e não código | `tests/test_offline_expansion.py` |
| Seleção de contexto com escore por termo e orçamento | EXISTE, com teste | `sparkforge/agents/budget.py:select_context()` deduplica por fingerprint, pontua por termo da query, dá peso a tipos preservados e corta pelo orçamento de token. É ranking mais orçamento, no formato que a SPEC descreve — sobre registros de conversa de agente, não sobre símbolo de código | `tests/test_agent_runtime.py` |
| Empacotamento com prioridade por tipo e corte reportado | EXISTE, com teste | `sparkforge/tools/context.py:pack_context()` prioriza fato e decisão sobre snapshot e tarefa, deduplica e reporta `truncated` em vez de cortar em silêncio — contexto descartado sem aviso vira evidência que some | `tests/test_offline_expansion.py` |
| Funil de contexto com deduplicação por hash e corte por orçamento | EXISTE, com teste | `sparkforge/context/funnel.py:ContextFunnel.build_minimal_context()` ordena por relevância, deduplica por hash de conteúdo e encaixa no orçamento. Limite declarado: a relevância é **entrada**, com valor padrão fixo — nada no módulo a deriva | `tests/test_context_funnel.py` |
| Estimador de token local, conservador, sem download | EXISTE PARCIAL | Existe, e existe **quatro vezes**: `sparkforge/agents/budget.py:estimate_tokens()`, `sparkforge/tools/cost.py:estimate_tokens()`, e mais duas cópias em linha dentro de `sparkforge/context/funnel.py` e `sparkforge/providers/mock.py`. As duas primeiras arredondam para cima; as duas em linha truncam. A mesma pergunta, quatro implementações, e essas **divergem** — ao contrário das quatro de segredo | `tests/test_economy_engine.py` |
| Estimativa rotulada como estimativa | EXISTE, com teste | `sparkforge/tools/cost.py` documenta que quatro caracteres por token é heurística e devolve `is_estimate: True` em todo retorno; `sparkforge/agents/observability.py` devolve `None` quando o total é desconhecido, em vez de somar zero | `tests/test_agent_runtime.py` |
| Paginação por cursor no envelope de saída | EXISTE, com teste | O envelope das tools traz `total_count`, `returned_count` e `next_cursor`, e o arquivo escrito carrega a comparação inteira, nunca a página. Quem extrai `items` sem conferir `next_cursor` julga a primeira página — e há teste medindo exatamente isso | `tests/test_adapters_tools.py` |
| Busca por símbolo no índice, determinística e sem rede | EXISTE, com teste | `sparkforge/codeintel/search.py:buscar()` casa nome e nome qualificado pelo FTS5. O termo nunca chega cru ao `MATCH` — passa por `construir_consulta()`, que é o construtor de consulta que a SPEC exige em lugar de interpolar texto de terceiro. A ordem é `(rank, path, start_line, node_id)`: sem o desempate, empate de relevância deixaria a ordem por conta do SQLite e o teste de determinismo falharia de forma intermitente | `tests/test_codeintel_search.py` |
| Expansão determinística de query por dicionário versionado | NÃO EXISTE | Nada expande "skew no join" para `broadcast`, `salting`, `AQE`. O vocabulário de domínio existe espalhado em `knowledge/` e em `rules/catalog/`, nunca como dicionário de sinônimo | — |
| Escore composto de recuperação | NÃO EXISTE | O escore de hoje tem dois componentes, e os dois são baratos: relevância do FTS e desempate por posição. Proximidade no grafo, relevância de entrypoint e de lineage continuam sem existir, porque não existe o grafo sobre o qual medi-los | — |
| Objeto de contexto canônico | NÃO EXISTE | `MinimalContext` e o retorno de `pack_context` são objetos de contexto, mas nenhum dos dois carrega índice, entry point, relação, lineage, regra, runtime, unresolved e bloco de segurança na mesma estrutura | — |
| Teto duro de token na saída, e ordem de redução declarada | NÃO EXISTE | A paginação limita **quantidade de itens**, não tamanho em token, e não há ordem escrita de o que sacrificar primeiro quando o orçamento estoura | — |

### Medição: o que a busca devolve contra o que responder sem ela custaria

O índice existe para uma coisa: responder "onde está X definido" sem que ninguém leia arquivo.
Quanto isso vale, em bytes, depende inteiramente de **contra o que** se compara — por isso o
método vem antes do número, e é para ele que quem discordar deve olhar primeiro.

**Método.** Cinco perguntas reais sobre este repositório, uma por símbolo: `iter_source_files`,
`looks_like_secret`, `project_items`, `tool_class` e `authorize`. O corpus é o mesmo dos dois
lados — os arquivos `*.py` que `iter_source_files(root, "*.py")` entrega, **387** nesta árvore.

- **Com índice** — `buscar(banco, nome)` sobre o índice do repositório inteiro, serializado como
  a CLI serializa (`json.dumps(..., ensure_ascii=False)` da lista de `Achado`). É o payload que
  chega a quem perguntou.
- **A — ler os arquivos.** O denominador que o plano define: `grep` pelo nome, e leitura dos
  arquivos apontados, em ordem de caminho, até encontrar a definição (`def nome` ou `class nome`).
  O custo é a soma do tamanho dos arquivos lidos, inclusive aquele onde a definição apareceu.
  **Não** é "ler o repositório inteiro" — isso seria construir um espantalho.
- **B — a saída do `grep` pelo nome.** Todas as linhas que mencionam o nome, no formato
  `caminho:linha:texto`, sem abrir arquivo nenhum. É o que "grep pelo nome" devolve literalmente.
- **C — a saída do `grep` pela definição.** `grep -n "def <nome>|class <nome>"`: só as linhas em
  que o nome vem logo depois de `def` ou `class`. É o piso adversarial — o denominador que menos
  favorece o índice, e o que um agente disciplinado de fato usa.

| Símbolo | Achados | Com índice | A: ler arquivos | B: `grep` nome | C: `grep` definição |
|---|---|---|---|---|---|
| `iter_source_files` | 1 | 197 | 428877 | 7270 | 102 |
| `looks_like_secret` | 2 | 465 | 101833 | 2107 | 84 |
| `project_items` | 1 | 193 | 140522 | 1718 | 52 |
| `tool_class` | 1 | 188 | 24310 | 2562 | 74 |
| `authorize` | 4 | 897 | 24310 | 3804 | 107 |

Somadas as cinco perguntas: o índice devolve **1940** bytes; ler os arquivos custaria **719852**;
a saída do `grep` pelo nome, **17461**; a saída do `grep` pela definição, **419**.

O **1940** é o único número desta seção que `scripts/check_vnext_claims.py` não audita, e vale
dizer por quê em vez de deixar quem confira procurar: quatro dígitos entre 1900 e 2099 estão na
lista de tokens ignorados como datação, e essa contagem caiu ali. O próprio comentário da lista
já previa o custo. Ele não fica sem lastro por isso — as três razões abaixo são auditadas, e a
prova de cada uma imprime numerador e denominador, com o **1940** entre os dois.

**Contra o denominador do plano, o índice economiza 371.1 vezes.** Contra a saída de um `grep`
pelo nome, **9.0** vezes. E contra a saída de um `grep` pela definição o resultado se inverte: a
resposta do índice custa **4.6** vezes o que aquele `grep` custaria.

**Esse último número é o resultado honesto desta medição, e ele não agrada.** Medido em bytes de
uma resposta, um `grep -n "def <nome>"` bem escrito é mais barato que consultar o índice. A causa
não é desperdício de envelope — é que as duas coisas respondem perguntas diferentes: o `grep` pela
definição devolve as linhas cuja definição **começa** com aquele nome, e o índice devolve todo
símbolo cujo nome **contém** o termo, com `kind` e nome qualificado. `authorize` é o caso
visível: o `grep` acha duas linhas, as duas em `sparkforge/agents/autonomy.py`, e o índice acha
quatro símbolos — a função, o método `AutonomyController.authorize_tool`, a função aninhada
`authorize.recusa` e um teste em outro arquivo. Mais recall custa mais bytes, e chamar isso de
economia seria mentir sobre o que foi medido.

**O que o byte não mede, e não é desculpa — é o resto da conta:**

- **O denominador C só funciona se você já souber o nome inteiro e certo.** Para fragmento, o
  `grep` equivalente é `def .*<fragmento>`, e o `grep` pelo nome deixa de ser barato:
  `buscar(banco, "source")` devolve **26** símbolos em **6730** bytes; a saída do `grep` pelo nome,
  no mesmo corpus, tem **93014** bytes. O `grep` pela definição contendo o fragmento continua menor
  (**5118** bytes), mas responde outra coisa — ele lista linhas de definição, e não diz que
  `AutonomyController.authorize_tool` é método daquela classe, porque isso exige parse.
- **O `grep` relê a árvore inteira a cada pergunta**; o índice lê o banco. Isso é CPU e I/O, não
  token, e esta medição não o converte em byte nenhum de propósito.
- **A saída do `grep` não tem teto.** A do índice tem: `buscar` recebe `limite`, com default 50.

**Filtrar por correspondência exata não salva o número.** Metade do que o índice devolve nas
cinco perguntas é símbolo cujo nome apenas *contém* o termo. Descartando esses e ficando só com
`name == termo`, a resposta encolhe para **963** bytes — e continua custando **2.3** vezes o
`grep` pela definição. O recall explica metade da diferença; a outra metade é que um `Achado`
carrega `node_id`, `qualified_name` e `kind`, que uma linha de `grep` não carrega e que a
pergunta "onde está X" não pediu.

**Onde o índice ganha, e é outra pergunta.** Testado o cenário em que o `grep` produziria ruído
— nome comum como `run`, `load`, `build`, `extract`, `check`, `parse` — o índice sai na frente em
menos da metade dos casos, o que não sustenta uma recomendação. Mas a pergunta *estrutural*
inverte tudo:
para "quais são os símbolos de `sparkforge/facts/scan.py`", o índice responde com metadado de
**8** símbolos, enquanto a alternativa é abrir um arquivo de **14681** bytes — **9.7** vezes a
favor, e sem parse do lado de quem pergunta.

**A conclusão que estas medições sustentam, e que reposiciona a fase:** este índice **não** se
paga como substituto de `grep` para busca por nome. Ele se paga em pergunta que `grep` não
responde sem parse — o que existe dentro de um arquivo, quem chama o quê, o que quebra se algo
mudar. E essas são exatamente as capacidades que a fase J3 **não** implementou: ela entrega
`nodes` e busca por nome, e deixa `edges`, chamadores e impacto para depois. O valor do
subsistema está na fase seguinte, não nesta — dizer o contrário seria vender a medição que deu
certo e esconder a que não deu.

Todos os valores são **bytes** UTF-8, nunca tokens. Os quatro estimadores de token deste
repositório dividem o comprimento por uma constante e divergem entre si no arredondamento: byte é
observação, token seria estimativa vendida como medida.

**A conclusão que a medição sustenta, e só ela:** o índice paga contra leitura de arquivo, que é o
que um agente sem ferramenta de fato faz, e paga contra a saída de um `grep` pelo nome — com folga
maior quanto mais parcial for o nome. Ele **não** paga como compressor de resposta contra um
`grep` cirúrgico pela definição, nem quando o nome é parcial. Quem quiser reivindicar economia de token
com este índice precisa declarar o denominador junto — e o gold set que a linha "Gate de recall e
de economia" ainda marca como inexistente é o que faria essa reivindicação valer, porque economia
que omite o símbolo necessário é falha, não sucesso.

## 11. Tools MCP e CLI

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Núcleo comum entre CLI e MCP | EXISTE, com teste | `sparkforge/adapters/_core.py` é o núcleo; `cli.py` e `tools.py` são casca. Há teste medindo que as duas superfícies declaram a mesma opcionalidade — é exatamente o que a SPEC pede para as tools novas | `tests/test_adapters_tools.py` |
| Schema de saída declarado e validado contra a saída real | EXISTE, com teste | Toda tool declara `outputSchema`, e há teste que roda a tool e valida a saída real contra o schema declarado, inclusive no caminho de erro | `tests/test_adapters_tools.py` |
| Anotações de confiança por tool | EXISTE, com teste | Toda tool declara `annotations`, e o catálogo é auditado: só as tools de coleta são de mundo aberto, e toda tool de mundo aberto também escreve localmente | `tests/test_adapters_tools.py` |
| Entrada tipada, sem schema de objeto nu | EXISTE, com teste | Toda tool declara `properties` e `required`, e nenhuma usa objeto nu | `tests/test_adapters_tools.py` |
| Entrada fechada a propriedade desconhecida | NÃO EXISTE | Nenhum dos schemas de entrada declara `additionalProperties: false`, que é uma constraint explícita da tool principal da SPEC. Argumento não previsto entra sem erro | — |
| Controle de verbosidade na resposta | EXISTE PARCIAL | `detail_level` aparece em **20** das **44** tools do catálogo: as que devolvem facts. As duas que paginam e ficaram de fora devolvem outro shape — `sparkforge_judge` devolve findings e `sparkforge_rules_lookup` devolve regras, e nenhum dos dois tem `provenance` nem os campos que o `summary` de fato preserva | `tests/test_adapters_detail_level.py` |
| Projeção de campo na resposta | NÃO EXISTE | Medido no catálogo carregado, e não por leitura: `fields` aparece em **zero** das tools. A fase J1 entregou `detail_level`, que é a linha **acima** desta e é outra coisa — ele escolhe entre três formas fixas de item, e projeção é pedir os campos que interessam. Não há como pedir só `kind` e `subject.file` | — |
| Poucas tools compondo operações internamente | NÃO EXISTE | O catálogo tem o tamanho medido na linha acima, e a SPEC pede explicitamente o oposto dessa estratégia | — |
| As tools `sparkforge_code_*` | NÃO EXISTE | Nenhuma das onze existe: contexto, busca, símbolo, leitura, impacto, lineage, contexto do que mudou, status, sync, métricas e status de segurança. A ausência agora é **decisão**, não pendência: os três verbos `code` do CLI entram em `ALLOWED_CLI_ONLY` com razão declarada, e ela é o sinal de frescor. Toda tool do catálogo hoje é sem estado — recebe um caminho, lê o artefato, responde; estas dependeriam de um índice construído antes, que envelhece sem avisar, e `code search` num índice velho responde "nenhum símbolo" com a mesma cara com que responde sobre símbolo inexistente. Ausência lida como ausência é a pior falha possível numa tool de busca | `tests/test_capability_parity.py` |
| Subcomando `code` no CLI | EXISTE, com teste | `sparkforge code index`, `sparkforge code search <termo>` e `sparkforge code status`, em `sparkforge/adapters/cli.py`. É a única entrada do CLI cujo payload não vem de `_core` — só o tipo de erro vem —, e a razão está escrita ao lado dela: o índice não devolve fato nem achado, e atravessar o núcleo obrigaria a inventar procedência para uma linha que só tem caminho e número de linha. O banco default é `.sparkforge/local/codeintel/graph.sqlite3`, já ignorado pelo git | `tests/test_codeintel_search.py` |
| Comandos `code init`, `code doctor`, `code purge` | NÃO EXISTE | Nenhum dos três que a SPEC nomeia. `init` e `purge` supõem ciclo de vida que este índice não tem — ele é descartável e se reconstrói numa passada; `doctor` supõe manifesto de tool, que é a linha abaixo | — |
| Hash canônico do catálogo de tools | NÃO EXISTE | Nenhum `tool-manifest.sha256`, e nenhum `doctor` que compare runtime com manifesto | — |

## 12. Integração com regras, case e runtime

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Motor de regras determinístico que consumiria o grafo | EXISTE, com teste | `sparkforge/rules/engine.py:judge()` casa fato contra catálogo YAML com `runtime_scope`, e o avaliador de expressão de `sparkforge/rules/expr.py` é fechado, nunca `eval` | `tests/test_fixtures_golden.py` |
| Case como estado retomável, com gate que recusa avanço | EXISTE, com teste | `sparkforge/case/store.py` declara fases e gates, e avançar com gate aberto é recusado, não avisado | `tests/test_case_store.py` |
| Contexto de runtime como dado de julgamento | EXISTE, com teste | `RuntimeContext` em `sparkforge/findings/models.py` carrega Glue, Spark, Python e Iceberg, e é ele que decide se uma regra sequer se aplica | `tests/test_findings_models.py` |
| Gold set com resultado esperado por cenário | EXISTE, com teste | `fixtures/scenarios/` guarda cenário inteiro com `expected/`, e há holdout. É a forma que a SPEC pede para o gold set de recuperação, aplicada a diagnóstico | `tests/test_fixtures_scenarios.py` |
| Integração sem criar um segundo sistema de julgamento | EXISTE, com teste | O catálogo de regras é o único julgador, e o carregador recusa regra malformada na carga em vez de deixá-la nunca disparar em silêncio | `tests/test_rules_loader.py` |

## 13. Inteligência de Data Engineering

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Política estática: nada de execução de Spark para analisar | EXISTE, com teste | Toda a extração é `ast.parse` e leitura de artefato coletado. Nenhum caminho do repositório sobe sessão Spark, e os goldens provam que o resultado sai da leitura, não da execução | `tests/test_fixtures_golden_plan.py` |
| Identificador de tabela reconhecido no código | EXISTE PARCIAL | `catalog.table_schema` traz o schema do catálogo, e `pyspark.read`/`pyspark.write` trazem o alvo literal. Não existe **nó de tabela** ligando as duas coisas nem consulta por tabela | `tests/test_fixtures_golden_catalog.py` |
| Ciclo de vida da recuperação de source | NÃO EXISTE | Nó → arquivo → leitura de faixa confinada → snippet temporário → resposta, com o snippet sumindo ao fim: nada disso existe, porque o snippet hoje nasce na extração e vive no fato | — |

## 14. Economia e benchmark

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Armazenamento local de métrica de execução | EXISTE, com teste | `SQLiteTraceStore` guarda trace e span com token e custo por execução | `tests/test_observability.py` |
| Detector de desperdício de token | EXISTE, com teste | `sparkforge/economy/waste_detector.py:TokenWasteDetector`, junto com `TaskBudgetGuardrail` e `ArtifactCache` com chave por hash de conteúdo | `tests/test_economy_engine.py` |
| Corpus de query de referência | NÃO EXISTE | As quinze perguntas que a SPEC enumera não existem como corpus, e nada as responde hoje sem varredura de arquivo | — |
| Gold set com símbolo e arquivo exigidos por query | NÃO EXISTE | Consequência da linha acima | — |
| Gate de recall e de economia | NÃO EXISTE | Nenhuma medição de recuperação, e portanto nenhum piso. Vale registrar a assimetria que a SPEC escreve e que este repositório subscreveria: economia alta que omite o símbolo necessário é falha, não sucesso | — |
| Benchmark de latência com percentil | NÃO EXISTE | `sparkforge/facts/benchmark.py` compara duas execuções de job Spark, que é outra coisa: não mede latência das próprias operações do motor | — |

### Medição: procedência declarada uma vez, e `detail_level`

Antes desta medição não havia nenhum controle de verbosidade: toda chamada devolvia a mesma
forma, e a procedência era copiada uma vez por fato — o mesmo `artifact_sha256` do mesmo arquivo,
repetido tantas vezes quantos fossem os fatos.

Medido em `sparkforge analyze pyspark` sobre a fixture
`fixtures/pyspark/clean_job/input/lib/job.py`, serializando o envelope devolvido com
`json.dumps(..., ensure_ascii=False)`. A coluna de procedência é a soma do bloco `provenance`
de cada item.

| `detail_level` | Envelope | Procedência dentro dos itens |
|---|---|---|
| `full` (default) | **4553 bytes** | **1144 bytes**, ou **25,1%** do envelope |
| `normal` | **3619 bytes** | nenhuma; declarada uma vez em `provenance` |
| `summary` | **1664 bytes** | nenhuma; declarada uma vez em `provenance` |

`normal` encolhe o envelope tirando dos itens o que se **repete** — a procedência, referenciada
por `provenance_ref`, e o `schema_version`. Os dois saem pelo mesmo caminho e pela mesma razão;
tirar só um e chamar isso de "declarar a procedência uma vez" descreveria mal a própria
economia. `summary` encolhe mais por reduzir o item ao que responde "o que" e "onde".

Em nenhum dos dois a procedência sai do envelope — economia que apagasse rastreabilidade seria
defeito, não compressão.

**E preservar rastreabilidade custou bytes.** A primeira versão desta fase era menor nos dois
níveis, e era menor pelo motivo errado: o `summary` descartava o `subject` inteiro e reconstruía
apenas `arquivo:linha`, o que apagava a identidade de todo fato cujo subject identifica por
`symbol` — o caso comum em Terraform, onde o recurso é o sujeito. O `schema_version` também
sumia sem ser redeclarado. Devolver os dois encareceu o envelope, e essa é a troca certa: um
resumo que não diz de **quem** fala não é resumo, é ruído menor.

Todos os valores são **bytes**, nunca tokens. Os estimadores de token deste repositório dividem
o comprimento do texto por uma constante e divergem entre si no arredondamento: byte é
observação, token seria estimativa vendida como medida.

O default é `full` de propósito. Mudá-lo mudaria a saída de todo chamador existente e de todo
golden de uma vez só, e isso é decisão de contrato — separada desta medição.

## 15. Testes de segurança

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Teste de traversal de caminho | EXISTE PARCIAL | A matriz encheu pela metade. Cobertos hoje, cada um com teste: caminho absoluto (`/etc/passwd`, `C:/Windows/x`), `..` encadeado (`a/../../fora.yaml`), symlink de arquivo e de pasta, junction do Windows, e caminho entregue de fora da raiz varrida. Continuam sem caso: **caminho UNC**, **byte nulo** e **unicode** — as três formas que dependem de como o sistema de arquivos normaliza, e que nenhum dos testes de hoje exercita | `tests/test_facts_scan.py` |
| Robustez a arquivo malformado e a encoding inválido | EXISTE, com teste | Falha por arquivo nunca é fatal: `SyntaxError` e `UnicodeDecodeError` viram um fato `unresolved` para aquele arquivo e a varredura continua. Perder a árvore inteira por causa de um arquivo ruim seria o pior modo de falha de um analisador | `tests/test_fixtures_golden_graph.py` |
| Verificação de ausência de egress | NÃO EXISTE | Nenhum teste observa syscall, socket ou DNS durante uma análise | — |
| Teste de vazamento do banco | EXISTE PARCIAL | O banco existe, e três testes medem o que ele **não** guarda: `test_corpo_da_funcao_nao_chega_ao_banco`, `test_nenhum_no_carrega_corpo` e `test_schema_grava_a_versao_e_nao_grava_caminho_absoluto` — corpo de função, e caminho absoluto que nomearia o usuário e o diretório num arquivo copiável. O que falta é o teste adversarial: nenhum caso indexa uma árvore com segredo plantado num arquivo de nome inocente e depois procura esse segredo dentro do `.sqlite3` | `tests/test_codeintel_index.py` |
| Corpus de segredo | EXISTE, com teste | Fechado pela fase J0. `tests/test_facts_secrets.py` é corpus parametrizado com positivo, positivo embutido no meio do valor, quase-positivo e dado legítimo, e ele cobra três invariantes que uma lista de casos sozinha não cobraria: todo padrão por valor tem positivo no corpus, `detectores()` nunca devolve o valor detectado, e `detectores()` e `looks_like_secret()` nunca divergem sobre o mesmo par | `tests/test_facts_secrets.py` |
| Fuzzing de parser | NÃO EXISTE | Nenhuma suíte de entrada gerada, nem corpus de negação de serviço | — |

## 16. Supply chain

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Dependência mínima como controle de segurança | EXISTE, com teste | O pacote core depende de `PyYAML` e `jsonschema`, e nada mais; AWS, HTTP e SDK MCP são extras. O espelho de requisitos é conferido byte a byte contra o `pyproject.toml`, então uma dependência nova não entra por um caminho e some pelo outro | `tests/test_requirements_mirror.py` |
| Integridade de artefato vendorizado | EXISTE, com teste | `vendor/` tem manifesto com sha por projeto, licença original preservada, e caminho que escape do diretório é recusado no código, não só no teste | `tests/test_vendor_caveman.py` |
| Verificação do artefato instalado | EXISTE, com teste | `scripts/verify_wheel.py` roda os módulos golden dentro de um ambiente isolado, com `PYTHONPATH` vazio e o Python do ambiente virtual, não o corrente | `tests/test_verify_wheel.py` |
| SBOM associado ao release | EXISTE, com teste | `scripts/gen_sbom.py` produz CycloneDX **1.6** a partir do lock e do `dist/` já aprovado pelo gate de paridade, e `.github/workflows/release.yml` o anexa ao release em rascunho ao lado do wheel e do sdist. Os cinco campos que a SPEC enumera têm cada um sua fonte declarada: pacote e versão vêm do lock resolvido, o sha256 vem do mesmo lock, a licença foi colhida da API do PyPI na geração dele, e a origem é o `purl` mais a URL do projeto no índice. O componente raiz carrega o sha256 do wheel e do sdist, então o documento descreve **um** release e não uma versão no abstrato. Só biblioteca padrão, pela mesma razão que pôs `build` no extra `dev`: ferramenta de CycloneDX ausente viraria `skip` permanente no teste | `tests/test_supply_chain.py` |
| Lock reprodutível e instalação frozen no CI | EXISTE, com teste | `locks/py3.10.txt` e `locks/py3.11.txt`, gerados por `scripts/gen_lock.py`: versão exata mais o sha256 de cada distribuição publicada daquela versão, incluindo o backend de build. O CI instala com `pip install --require-hashes`, que trata como **erro** qualquer dependência que não esteja pinada e hasheada no arquivo — inclusive as que entram por transitividade —, de modo que o ambiente instalado é idêntico ao commitado ou a instalação falha dizendo o que faltou. O install editável usa `--no-deps --no-build-isolation`, e sem o segundo o pip baixaria hatchling do índice em tempo de CI. São dois arquivos porque a resolução diverge de verdade entre as duas entradas da matriz — `rpds-py` resolve para versões diferentes, e `tomli`, `importlib-metadata` e `zipp` só existem na linha mais antiga. Conferir é offline; regenerar exige rede e `uv`, que é ferramenta de geração e não entra em lugar nenhum do pacote | `tests/test_supply_chain.py` |
| `pip-audit` ou OSV no CI | EXISTE, com teste | Job `audit` próprio em `.github/workflows/ci.yml`, separado do job `test` para que a consulta a uma base externa não decida a cor do gate de teste. Ele audita o **lock**, e não os pisos: `PyYAML>=6.0` não tem CVE, a versão instalada é que tem. A política está escrita em `scripts/audit_policy.py`, e tem quatro ramos: vulnerabilidade com correção publicada derruba o job; sem correção publicada só reporta, e migra sozinha para o ramo de cima no dia em que ganhar correção; base não consultada (relatório ausente, ilegível ou com todos os pacotes pulados) derruba, porque ausência não é aprovação; e relatório que **não cobre o lock** derruba, que é o único ramo que compara a saída com o alvo em vez de olhar só para dentro dela — um relatório bem formado sobre outra coisa passaria por todos os outros sem ter respondido nada. A política é função pura sobre JSON, e por isso tem gate offline com relatórios sintéticos | `tests/test_supply_chain.py` |
| Proibição explícita de download em runtime | NÃO EXISTE como regra escrita | Na prática nada baixa nada, e `OfflineKnowledgeIndex` existe justamente para provar que o conhecimento está no disco. Mas não há gate que reprove um `pip install` acrescentado a um caminho de execução | — |

---

## Conclusões

### 1. O que o SFCI realmente acrescentaria, excluídas as duplicatas

Seja duro com a extração: **ela já existe**. Leitura e escrita de tabela, aresta de chamada,
ciclo, alcançabilidade por entrypoint, predicado e projeção de SQL, schema de catálogo, ponto
cego nomeado, procedência por artefato com sha — tudo isso é produzido hoje, com golden por
fixture. Um extrator novo de Python só acrescentaria classe, import e qualified name, que é
trabalho pequeno em cima de uma varredura que já existe.

O que o SFCI acrescenta de verdade é curto e vale a pena:

- **Persistência.** É a única coisa que muda a natureza do sistema. Hoje cada análise
  reparseia a árvore inteira e esquece; um índice transforma "reparseia sempre" em "responde
  do disco". Sem isso, nenhuma das outras peças tem em cima do que rodar.
- **Um eixo de consulta que não existe.** Todo o repositório consulta por **fato**. Ninguém
  consulta por **símbolo**: "onde `RuntimeContext` é construído", "quem chama
  `validate_output`", "qual o impacto de mudar isto". A busca determinística já existe em
  `OfflineKnowledgeIndex.search`, sobre `knowledge/` — falta o corpo de código.
- **Orçamento de token medido em vez de estimado.** As quatro cópias de estimador dividem
  comprimento por quatro; nenhuma delas mede. Não é preciso um tokenizer baixado para
  melhorar: um estimador conservador único, com nome único, já é ganho — e o ganho maior é
  deixar de ter quatro respostas para a mesma pergunta.
- **Redução do custo do próprio envelope.** Ver a pré-condição de envelope, adiante.
- **Uma superfície de tool que sabe economizar.** `detail_level` deixou de ser zero na fase J1;
  projeção de campo continua em zero, e é economia disponível hoje, sem índice nenhum.

### 2. O que já existe e deveria ser integrado, não escrito

A lista é longa, e é a maior parte da SPEC:

- **Extração e procedência**: `sparkforge/facts/` inteiro, com `EXTRACTOR_ID`, `artifact_sha256`
  e vocabulário fechado de `unresolved` por extrator.
- **Grafo de chamadas**: `sparkforge/facts/call_graph.py` já dá função, trabalho concentrado,
  alcance por entrypoint com profundidade mínima, ciclo e símbolo não referenciado.
- **Busca local sem embedding e manifesto verificável**: `sparkforge/tools/offline.py`, com a
  lição de normalização de fim de linha já paga.
- **Ranking com orçamento**: `sparkforge/agents/budget.py:select_context()`.
- **Empacotamento com prioridade e corte reportado**: `sparkforge/tools/context.py:pack_context()`.
- **Funil com deduplicação por hash**: `sparkforge/context/funnel.py`.
- **Cache por hash de conteúdo**: `sparkforge/economy/cache.py:ArtifactCache`.
- **Banco SQLite local e trace**: `sparkforge/observability/store.py`.
- **Cadeia de autorização com classe, perfil e teto**: `sparkforge/agents/autonomy.py`.
- **Resolução confinada de caminho**: `sparkforge/paths.py:resolve_within()`, hoje a
  implementação única que `rules/loader.py`, `knowledge_ref.py` e `agents/autonomy.py` chamam,
  mais a guarda equivalente de `scripts/vendor_caveman.py`.
- **Fronteira única de leitura**: `sparkforge/facts/scan.py:iter_source_files()`, com denylist,
  poda de árvore de dependência, teto por tipo e recusa de atalho — e o índice já lê por ela.
- **Núcleo comum CLI/MCP, envelope paginado, schema de saída validado contra a saída real**:
  `sparkforge/adapters/_core.py` e `sparkforge/adapters/tools.py`.
- **Conteúdo de terceiro como dado não confiável**: já é invariante travado, com teste que
  deriva o conjunto de extratores executando-os.

As três implementações de empacotamento de contexto e as quatro de estimativa de token são o
sinal mais claro de que a ordem certa é consolidar, não somar. Escrever uma quinta seria repetir
o erro que a duplicação de detector de segredo já cobra caro.

### 3. O que precisa vir ANTES do índice

Persistir código de cliente em disco muda a natureza do risco, e três coisas eram pré-condição,
não melhoria. **As três foram pagas antes de o primeiro byte de código ir para o disco**, e
esta seção fica como registro da ordem, não como pendência:

- **Política de git para o estado local, antes de existir estado local.** Paga na fase J0:
  `.sparkforge/traces.db`, `.sparkforge/cache/` e `.sparkforge/local/` entraram no `.gitignore`
  antes de existir banco de índice, e o default do banco aponta para dentro de `local/`.
  Continua sendo a linha mais barata do documento inteiro e a de maior consequência — e a
  regra em si ainda não tem gate próprio, ao contrário do que ela protege.
- **Sandbox de filesystem aplicado ao alvo da análise.** Paga na fase J0: o algoritmo virou
  `sparkforge/paths.py:resolve_within()`, a varredura virou
  `sparkforge/facts/scan.py:iter_source_files()` com denylist, poda de árvore de dependência,
  teto por tipo e recusa de atalho, e `sparkforge/codeintel/index.py` lê por essa mesma
  fronteira em vez de reimplementá-la. O que sobrou não é pré-condição de índice: é detecção
  de binário, sinal de que algo foi pulado, e o confinamento da **raiz** que a tool recebe.
- **Firewall de segredo que funcione por valor.** Pago na fase J0: as cópias privadas foram
  removidas, um gate estrutural por AST impede a próxima, e os padrões por valor — AWS,
  GitHub, JWT, PEM, Slack — deixaram de depender do nome da chave. O corpus de teste, que era
  zero, existe. Faltam da lista da SPEC OAuth client secret, Bearer token e alta entropia como
  gatilho independente.

Há uma quarta pré-condição, de contrato e não de segurança: **o custo do envelope**. Na fixture
`clean_job`, o payload de fatos é várias vezes o tamanho do fonte, e a maior fatia disso não é dado
útil — é `provenance` repetida em cada fato, com o mesmo sha256 do mesmo arquivo copiado uma vez
por fato, mais `schema_version` copiado junto. Um objeto de contexto que herde essa forma
nasce caro pelo mesmo motivo. A correção é estrutural e independe do índice: procedência
declarada uma vez por artefato, referenciada por chave nos fatos.

E um limite que era de projeto e virou de fiação: [`AUTHORIZATION-CHAIN.md`](AUTHORIZATION-CHAIN.md)
registrava que `authorize()` autorizava um **nome**, nunca uma **chamada**. A assinatura passou a
receber `arguments` e `root`, e a decisão carrega `checked_arguments` para que "autorizado sem
olhar argumento" não se confunda com "autorizado tendo olhado". O que não mudou é que **ninguém
chama**: nenhum dos quatro caminhos de execução consulta a cadeia antes de executar, então uma
tool continua recebendo o caminho que quiserem passar. Fechar isso deixou de ser decisão de
arquitetura e passou a ser um ponto de checagem antes da execução — e ele continua pertencendo à
fase de segurança, não à de índice.

### 4. O que NÃO fazer, e por quê

- **Não escrever um quinto empacotador de contexto.** Já há três (`ContextFunnel`,
  `pack_context`, `select_context`) e quatro estimadores de token. Um objeto de contexto novo
  que ignore os três repete, na superfície mais cara do sistema, o defeito que a duplicação de
  detector de segredo já demonstrou: quatro implementações da mesma pergunta, corrigidas em
  lugares diferentes, é como um controle de segurança apodrece sem que nada acuse.
- **Não criar as onze tools antes de existir o que elas consultariam.** É o mesmo erro que
  [`MIGRATIONS-GLUE-GAP.md`](MIGRATIONS-GLUE-GAP.md) recusou para agente sem fact por baixo:
  uma tool que não tem índice responde do mesmo jeito que um modelo sem ferramenta nenhuma, e
  cada tool nova entra no gate de paridade e no catálogo para sempre. Pior: com o catálogo
  atual já declarado, somar onze contraria explicitamente a própria SPEC, que pede poucas tools
  compondo internamente.
- **Não migrar o SDK MCP junto.** A SPEC coloca isso na última fase e tem razão: é breaking,
  tem ADR próprio a escrever, e contaminaria a entrega do índice com um risco que não é dele.
- **Não medir economia pela redução do payload sozinha.** A própria SPEC diz que economia alta
  que omite o símbolo necessário é falha. Sem gold set com símbolo exigido, "economizamos quase
  tudo" é uma frase sem lastro — exatamente a classe de alegação que
  `scripts/check_vnext_claims.py` existe para recusar neste repositório.
- **Não tratar a viabilidade do Tier 0 como resolvida porque funciona nesta máquina.** FTS5 e
  `blake2b` estão disponíveis no interpretador desta workstation, mas o `pyproject.toml`
  declara suporte a versões de Python mais antigas e o CI roda numa matriz que não inclui a
  versão local. Nada no repositório mede a disponibilidade de FTS5 nas versões suportadas, e o
  módulo `ast` mudou entre elas — nós que a SPEC nem cita saíram da biblioteca padrão nesse
  intervalo. Ou o piso de Python sobe deliberadamente, ou a matriz de CI passa a medir isso
  antes de o índice depender disso.
- **Não adotar embeddings "só para o ranking".** A proibição da SPEC é o que sustenta os três
  motivos declarados de uma vez: autossuficiência, segurança e economia. Um reranker externo
  quebra os três com uma linha de import.

### 5. A ordem que a medição sugere, e onde ela diverge da SPEC

A SPEC ordena assim: ADR e threat model, fundação de segurança, armazenamento e índice, AST,
recuperação, MCP e CLI, integração, e daí em diante. A medição concorda com o começo e discorda
em três pontos.

**Concorda com segurança antes de tudo, e por razão mais forte que a da SPEC.** A SPEC põe
segurança antes por princípio; aqui havia dívida medida — detector de segredo duplicado e sem
teste, ausência de denylist, varredura entrando em `.venv/`, estado local fora do `.gitignore`.
Eram problemas daquele dia, que existiam sem SFCI nenhum, e a ordem provou estar certa: a fase
J0 foi conserto do que já estava aberto, e o índice das fases seguintes nasceu lendo pela
fronteira que ela deixou pronta, em vez de abrir a sua.

**Diverge na fase de AST.** A SPEC trata o extractor de Python e PySpark como fase inteira. A
divergência se confirmou na prática: a fase J3 acrescentou nó de classe, nome qualificado e
assinatura normalizada em cima da varredura já existente, e não escreveu extractor nenhum do
zero. O que resta dessa fase é o que ela deixou de propósito — import, hierarquia de tipo, e
ligar `call_graph.py` ao índice.

**Diverge na ordem entre armazenamento e conserto do envelope.** A SPEC constrói o armazenamento
e só depois, na fase de recuperação, chega ao orçamento de token. A medição sugere o contrário:
enquanto o formato de fato custar várias vezes o fonte por procedência repetida, tudo que o índice
devolver herda esse custo. Consertar a forma da procedência é barato, não depende de banco
nenhum, e é medível antes e depois — é a primeira coisa a fazer depois da segurança, não a
quarta.

**Diverge por acrescentar uma fase zero que a SPEC não tem.** Antes de qualquer código de
índice havia economia disponível sem índice. A fase J1 entregou metade dela: controle de
verbosidade existe hoje nas tools que devolvem facts, e procedência deixou de ser copiada fato a
fato. A outra metade continua parada — projeção de campo não existe em tool nenhuma, paginação
existe em **22** delas, e os quatro estimadores de token e os três empacotadores de contexto
continuam sendo quatro e três.

Ordem que a medição sugeriu, com o que as fases J0 a J3 fizeram dela:

1. **Consertar o que já estava aberto** — feito. Detector de segredo unificado com corpus,
   política de git do estado local fechada, denylist e poda de árvore de dependência na
   varredura, confinamento aplicado dentro dela.
2. **Baratear o que já é devolvido** — metade feita. `detail_level` e procedência por
   referência existem; projeção de campo e o estimador único de token, não.
3. **Decidir a cadeia de autorização** — decidido, não ligado. `authorize()` passa a ver
   argumento; nenhum caminho de execução o consulta.
4. **Persistir** — feito na parte completa, aberto na incremental. Banco, schema, FTS e índice
   de árvore inteira existem; reindexação parcial não.
5. **Consultar por símbolo** — começado. Busca por nome existe; ranking com proximidade de
   grafo e objeto de contexto canônico, não.
6. **Só então superfície nova de tool** — não começado, e é decisão registrada: os três verbos
   `code` ficam no CLI enquanto o índice não souber dizer que envelheceu.

O restante da ordem da SPEC — worktree, lineage de SQL, hardening, MCP 2026, linguagens
adicionais — a medição não contesta, e a seção seguinte diz o que sobrou de cada uma.

---

## O que a SPEC ainda pede, depois das fases J0 a J3

As fases J0 a J3 fecharam parte do que este mapa classificava como ausente, e a tabela acima já
foi reclassificada contra o repositório de hoje. Esta seção existe para a pergunta seguinte, que
é a de planejamento: **agrupado pelas fases que a SPEC ordena, o que continua ausente ou
parcial?** Toda linha citada aqui aparece na tabela correspondente, com módulo e teste; nada
entra aqui que não esteja lá.

Uma advertência sobre como ler: "parcial" não é meio caminho uniforme. Há parcial que é
acabamento — falta um caso na matriz de teste — e há parcial que é a metade difícil ainda
inteira, como indexação incremental. A diferença está escrita em cada linha da tabela, e é ela
que decide esforço, não a palavra.

### Fase de ADR e threat model

Continua **inteira**, e é a única das doze em que nada foi entregue.

- **Threat model escrito, com ameaça numerada e proteção** — nenhum documento do repositório
  enumera ameaça contra repositório malicioso. `AUTHORIZATION-CHAIN.md` e `UNTRUSTED-CONTENT.md`
  cobrem uma fronteira cada, e nenhum dos dois é um threat model.
- **Política de retenção de source**, parcial: a decisão está tomada no schema — o banco não tem
  coluna de corpo — e não está escrita como política. É a metade que pertence a esta fase.

O custo de ela não existir já apareceu: a fase J3 tomou decisões de retenção (sem corpo, sem
caminho absoluto, assinatura sanitizada) dentro do módulo que as implementa, uma a uma. Elas
estão certas e estão dispersas, e não há documento contra o qual conferir a próxima.

### Fase de fundação de segurança

A mais avançada das doze, e o que sobra dela é de dois tipos: o que ficou parcial de propósito,
e o que nunca foi tocado.

Parcial:

- **Confinamento de caminho vindo de fora do processo** — a verificação existe em `authorize()`
  e está desligada, porque nenhum caminho de execução chama a cadeia. É a linha mais próxima de
  fechar, e a que mais muda o risco real.
- **Source read-only** e **Zero network egress** — os dois seguem sendo invariante sem
  enforcement de runtime: nenhum audit hook, nenhum bloqueio de socket, nenhuma varredura que
  afirme que nada escreve no source.
- **Algoritmo de resolução segura de caminho** e **Limite de tamanho por arquivo** — falta o
  mesmo item nos dois: **detecção de conteúdo binário** antes de decodificar.
- **Arquivo classificado sensível sai inteiro do índice** — a classificação é por nome, nunca
  por conteúdo, e a recusa é muda.
- **Detectores que a SPEC enumera** — faltam OAuth client secret, Bearer token e alta entropia
  como gatilho independente.
- **`offline-strict` como perfil com matriz ALLOW/DENY declarada** e **`aws-readonly` como
  perfil** — existe a regra, não existe a matriz como dado.
- **`.sparkforge/local/` fora do git** — a regra existe no `.gitignore` e nenhum teste a tranca.

Não tocado:

- **`sanitize_environment`, `install_audit_hook`, `apply_resource_limits`,
  `lock_security_profile`** — nenhum dos quatro.
- **Separação: quem devolve source não tem AWS** — o mesmo processo continua fazendo as duas
  coisas.
- **Sem herança de credencial em worker de parsing** — não há worker, então não há sanitização
  de ambiente.
- **Permissão restrita de diretório e arquivo, com umask** — nada no repositório define
  permissão de arquivo criado, e agora existe um arquivo de banco para o qual isso importa.
- **Rótulo de confiança no objeto devolvido** e **detector de conteúdo com forma de instrução**
  — as duas linhas de defesa contra injeção que dependem de marcar, e não de estruturar.

E duas linhas de injeção que estão parciais pelo mesmo motivo — a garantia é estrutural, e a
política que a declararia não existe:

- **Corpus de injeção exercitado ponta a ponta** — há um caso, e ele prova a fronteira certa.
  Um caso não é corpus.
- **Comentário e docstring fora do dado devolvido** — nenhum extrator emite comentário ou
  docstring, mas isso é consequência do que eles observam, não política: não há
  `include_comments` para desligar, porque não existe o caminho que os ligaria.

### Fase de armazenamento e índice

Entregue na parte completa, aberta na incremental.

- **Banco com schema versionado, migrations e locking**, parcial — o schema é versionado e
  ninguém lê a versão para migrar; o `busy_timeout` é espera de escritor do SQLite e não guarda
  contra duas indexações concorrentes.
- **Taxonomia de aresta**, parcial — não há tabela `edges`, por decisão registrada: aresta exige
  resolver referência, e o que fazer com o que não resolve é a decisão difícil.
- **Índice FTS sobre símbolo e signature**, parcial — o FTS cobre nome e nome qualificado; a
  assinatura está guardada e não é buscável.
- **Índice persistente, completo e incremental**, parcial — completo existe, incremental não.
- **Sinal de staleness por arquivo**, parcial — o sha por arquivo está gravado e nada o compara
  com o disco.
- **Strict tree, fingerprint de worktree, namespace por branch** — ausente. O digest de raiz que
  existe responde outra pergunta, e nem sequer é conferido na leitura.

### Fase de AST de Python e PySpark

A que mais encolheu, e por isso a que mais precisa ser reescrita antes de virar plano.

- **Símbolos gerais de Python**, parcial — classe, método, função aninhada e nome qualificado
  existem; **grafo de import** e **hierarquia de tipo** não.
- **Grafo de dados tabela → job → tabela**, parcial — os dois lados existem como fato solto e
  nada os liga numa estrutura consultável.
- **Identificador de tabela reconhecido no código**, parcial — não existe nó de tabela nem
  consulta por tabela.
- **Lineage de DataFrame variável a variável** — ausente: a cadeia de método dentro de uma
  expressão é entendida, o valor que passa de uma variável a outra não.
- **Workers de parsing isolados, autenticados, com limite** — ausente, e é a linha desta fase
  que pertence tanto aqui quanto à fase de segurança.
- **Ciclo de vida da recuperação de source** — ausente. Nó, arquivo, leitura de faixa confinada,
  trecho temporário e resposta, com o trecho sumindo ao fim: nada disso existe, e é a linha que
  a política de retenção da primeira fase precisa cobrir antes de alguém escrevê-la.

### Fase de recuperação

O eixo de consulta por símbolo abriu; o resto da fase continua fechado.

- **Escore composto de recuperação** — o escore de hoje tem relevância do FTS e desempate por
  posição. Proximidade no grafo, relevância de entrypoint e de lineage não existem porque não
  existe o grafo sobre o qual medi-las. Depende de `edges`.
- **Objeto de contexto canônico** — ausente, e a advertência da seção *O que NÃO fazer* vale
  inteira: consolidar os três empacotadores existentes, nunca somar um quarto.
- **Expansão determinística de query por dicionário versionado** — ausente.
- **Teto duro de token na saída, e ordem de redução declarada** — a paginação limita quantidade
  de itens, não tamanho.
- **Estimador de token local, conservador, sem download**, parcial — continua havendo quatro, e
  elas divergem no arredondamento.

E a fase carrega o que mede se ela deu certo, que também não existe:

- **Corpus de query de referência** — as perguntas que a SPEC enumera não existem como corpus.
- **Gold set com símbolo e arquivo exigidos por query** — consequência da linha acima.
- **Gate de recall e de economia** — nenhuma medição de recuperação, portanto nenhum piso. É a
  linha que faria a reivindicação de economia valer, e sem ela "economizamos quase tudo" é a
  classe de alegação que o gate de lastro deste repositório existe para recusar.

### Fase de MCP e CLI

Praticamente intocada, e boa parte disso é decisão, não pendência.

- **As tools `sparkforge_code_*`** — nenhuma das onze, e a ausência está registrada com razão:
  toda tool do catálogo é sem estado, e estas dependeriam de um índice que envelhece sem avisar.
  Fechar a linha de staleness é pré-condição desta.
- **Projeção de campo na resposta** — ausente, medido no catálogo carregado.
- **Entrada fechada a propriedade desconhecida** — nenhum schema declara
  `additionalProperties: false`.
- **Controle de verbosidade na resposta**, parcial — existe nas tools que devolvem facts, não
  nas que devolvem findings ou regras.
- **Comandos `code init`, `code doctor`, `code purge`** e **hash canônico do catálogo de tools**
  — ausentes; `doctor` depende do manifesto que também não existe.
- **Poucas tools compondo operações internamente** — a SPEC pede o oposto da estratégia atual, e
  isso é divergência de arquitetura a decidir, não trabalho a agendar.

### Fase de integração com SparkForge

A única em que a tabela não registra nenhuma pendência: motor de regras, case retomável,
contexto de runtime, gold set por cenário e julgador único estão todos com teste. O que a
integração ainda não tem é **objeto** — o índice não alimenta o motor de regras, porque o motor
consome fato e o índice devolve símbolo. Ligar os dois pertence à fase de recuperação, não a
esta.

### Fase de worktree

Inteira. **Strict tree, fingerprint de worktree, namespace por branch** e **contexto do que
mudou, e teste afetado** são as duas linhas, e as duas estão ausentes. A segunda depende da
primeira, e as duas dependem de indexação incremental — é a fase mais bloqueada do conjunto.

### Fase de lineage de SQL e de dados

Parcial em tudo, ausente em nada. O extractor de SQL entrega predicado e projeção com golden; o
que falta é o mesmo item que falta na fase de AST — a estrutura consultável que ligue leitura,
escrita e transformação. Enquanto `edges` não existir, esta fase não tem onde escrever.

### Fase de hardening

Duas metades independentes, e agora elas não estão mais no mesmo estado.

- Runtime, **inteira**: **modo hardened em Linux com namespace de rede isolado**, os quatro
  primitivos de travamento de perfil, **verificação de ausência de egress** e **fuzzing de
  parser**.
- Supply chain, **quase fechada**: **SBOM**, **lock reprodutível com instalação frozen no CI**
  e **`pip-audit` no CI** foram entregues, cada um com a linha correspondente reclassificada na
  tabela acima. Sobra **proibição explícita de download em runtime como regra escrita** — na
  prática nada baixa nada, e nenhum gate reprovaria um `pip install` acrescentado a um caminho
  de execução. Vale registrar que a entrega andou na direção contrária dessa lacuna sem
  fechá-la: o job `audit` roda `pip install pip-audit`, deliberadamente, num job que não
  executa código do pacote — a regra que falta escrever precisa distinguir os dois casos em
  vez de proibir a string.

Dois testes desta fase estão parciais e não ausentes, e a diferença importa para orçar:
**teste de traversal de caminho** tem a metade da matriz e falta caminho UNC, byte nulo e
unicode; **teste de vazamento do banco** mede o que o banco não guarda e falta o caso
adversarial com segredo plantado. Some-se **benchmark de latência com percentil**, ausente — o
benchmark que existe compara duas execuções de job Spark, que é outra coisa.

A metade de supply chain não depende de nada do índice e pode andar sozinha a qualquer momento.

### Fase de MCP 2026

Intocada de propósito. A SPEC a coloca por último e a medição concorda: é breaking, tem ADR
próprio a escrever, e contaminaria a entrega do índice com um risco que não é dele.

### Fase de linguagens adicionais

Intocada, e sem linha própria na tabela — o extractor de hoje lê Python, e a varredura declara
`.py` e `.tf` como as extensões que o motor existe para ler. Acrescentar linguagem é trabalho
sobre a fronteira que já existe, e ele só faz sentido depois de `edges`, porque uma linguagem
nova sem aresta acrescenta símbolo e não acrescenta resposta.

### O que este agrupamento sugere para o próximo plano

Três leituras saem daqui, e as três são de ordenação, não de conteúdo:

**Uma linha destrava mais do que qualquer outra: `edges`.** Escore composto, lineage de SQL,
grafo de dados, identificador de tabela, impacto e as tools `code` dependem dela, direta ou
indiretamente. Ela é também a linha que a medição de bytes desta página já apontava: o índice
não se paga contra `grep` para busca por nome, e se paga em pergunta que `grep` não responde sem
parse — que é exatamente o que a aresta permite perguntar.

**Uma linha destrava a superfície de tool: staleness.** As onze tools estão bloqueadas por uma
razão escrita, e a razão é que índice velho responde "nenhum símbolo" com a mesma cara com que
responde sobre símbolo inexistente. O material para resolver isso já está no banco — sha,
tamanho e mtime por arquivo. Falta a comparação.

**Uma metade de fase podia andar sozinha, e andou:** supply chain. SBOM, lock frozen e
auditoria de dependência no CI não tocam índice, não tocam extractor e não tocam catálogo de
tool, e por isso foram as únicas que não esperaram por `edges` nem por staleness. As três
linhas estão reclassificadas na tabela de supply chain; a quarta da metade — a proibição
escrita de download em runtime — continua aberta.

O que a entrega ensinou, e que vale para a ordenação do resto: **o lock foi pré-condição da
auditoria, não companheiro dela**. Auditar piso de versão não responde nada — `PyYAML>=6.0` não
tem CVE, a versão instalada é que tem —, então o job de auditoria só passou a significar alguma
coisa depois de existir um arquivo que diz qual versão é. A mesma forma de dependência aparece
duas vezes mais neste documento: as tools `code` esperam por staleness, e escore composto,
lineage e impacto esperam por `edges`.
