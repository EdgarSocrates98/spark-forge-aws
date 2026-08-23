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

O terceiro é de segurança, e é o mais sério: **a detecção de segredo tem quatro implementações
e nenhum teste sobre a canônica**, e as quatro falham igual contra a metade da lista que a
própria SPEC enumera.

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
| Confinamento ao root autorizado | EXISTE PARCIAL | `sparkforge/rules/loader.py:safe_catalog_file()` canonicaliza e recusa o que escapar do diretório — é o algoritmo que a SPEC pede, aplicado a **um** diretório (o catálogo de regras). `scripts/vendor_caveman.py` tem a mesma guarda para `vendor/`. Nenhuma das duas alcança o `path` que as tools de análise recebem | `tests/test_rules_loader.py` |
| Sem telemetria conversacional | EXISTE PARCIAL | `sparkforge/observability/store.py:SQLiteTraceStore` grava trace da execução do próprio SparkForge, e nada no repositório lê histórico de agente de terceiro. Mas o banco fica em `.sparkforge/traces.db`, que **não** está no `.gitignore` — ver a seção de estado local | `tests/test_observability.py` |
| Sem herança de credencial em worker de parsing | NÃO EXISTE | Não há worker de parsing, então também não há sanitização de ambiente. Hoje o extrator roda no mesmo processo, com o mesmo ambiente, e nada impede um extrator futuro de ler `AWS_SECRET_ACCESS_KEY` | — |
| Política de retenção de source (corpo de função e cache) | NÃO EXISTE | Nada persiste source hoje porque não há índice. A ausência de banco torna o invariante verdadeiro por acidente, não por decisão — e o dia em que o banco existir, a decisão precisa estar escrita antes | — |
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
| Algoritmo de resolução segura de caminho | EXISTE PARCIAL | `safe_catalog_file()` faz exatamente o que a SPEC descreve — canonicaliza root e candidato, recusa quem não estiver abaixo do root — e tem teste de traversal com `../../etc/passwd`. Falta tudo o que vem depois na SPEC: arquivo regular, symlink, denylist, limite de tamanho, detecção de binário, política de segredo | `tests/test_rules_loader.py` |
| Confinamento de caminho vindo de fora do processo | NÃO EXISTE | As tools de análise recebem `path` e o repassam direto ao extrator (`sparkforge/adapters/_core.py:analyze_pyspark`). Nada canonicaliza, nada confina. A guarda de `safe_catalog_file` protege o catálogo de regras, que é dado do próprio SparkForge, e não o alvo da análise, que é dado de terceiro | — |
| Symlink recusado por padrão | NÃO EXISTE | `safe_catalog_file` **resolve** o symlink e confere contenção, que é uma garantia diferente de recusar: um symlink apontando para dentro do root passa. Nenhum outro caminho do repositório olha symlink | — |
| Denylist de caminho sensível | NÃO EXISTE | Nenhuma lista de `.env`, `*.pem`, `id_rsa`, `credentials`, `.aws/`, `.ssh/`, `terraform.tfstate` ou `*.tfvars`. Os extratores que varrem `*.json` (`catalog_schema`, `emr_cluster`, `emr_serverless`, `iceberg_metadata`, `s3_listing`, `athena_workgroup`) leriam qualquer JSON de credencial que estivesse na árvore apontada | — |
| Exclusão de árvore de dependência e de artefato | NÃO EXISTE | A varredura pula `__pycache__` em três extratores (`pyspark_ast.py`, `graph.py`, `migration.py`) e **não pula em `data_quality.py`**, que percorre `*.py` sem filtro nenhum. `.venv/`, `node_modules/`, `vendor/`, `site-packages/` e `.git/` são varridos como código do cliente. Num repositório com ambiente virtual dentro, isso é ao mesmo tempo custo e superfície | — |
| Limite de tamanho por arquivo e detecção de binário | NÃO EXISTE | Nenhum piso, nenhum teto, nenhuma checagem de conteúdo binário antes de decodificar | — |

## 4. Secret firewall

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Reconhecedor canônico de segredo em par chave/valor | EXISTE, sem teste | `sparkforge/facts/secrets.py:looks_like_secret()` é o módulo declarado canônico, com a razão da existência escrita na própria docstring. Nenhum arquivo de `tests/` o importa ou o menciona — a contagem de arquivos de teste que referenciam o módulo é **0** | — |
| Redação registrada no próprio fato | EXISTE, com teste | O par vira `<redigido>` e `attrs["redacted"] = True`: a evidência mostra que havia credencial sem mostrar a credencial. É a distinção que a SPEC exige entre `{"sensitive": true}` e `{"secret": "AKIA..."}` | `tests/test_facts_terraform.py` |
| O scanner nunca registra o segredo | EXISTE, com teste | Mesma disciplina no caminho de EMR: a propriedade sai redigida no golden, e o teste mede a redação, não a detecção | `tests/test_facts_emr_cluster.py` |
| Uma implementação só | NÃO EXISTE | São **4**: a canônica mais três cópias privadas `_looks_like_secret` em `sparkforge/facts/terraform.py`, `sparkforge/facts/emr_cluster.py` e `sparkforge/facts/emr_serverless.py`. Testei as quatro contra o mesmo conjunto de casos e elas **não divergem** — o que é pior notícia, não melhor: elas concordam porque são a mesma heurística copiada, e um padrão corrigido numa e esquecida nas outras vaza por três extratores sem que nada acuse | — |
| Detectores que a SPEC enumera | EXISTE PARCIAL | Só dois gatilhos funcionam por **valor**: access key id da AWS e senha embutida em URL. Todo o resto depende do **nome da chave** conter `secret`, `password`, `token`, `credential` ou similar. Com nome de chave inocente, as quatro implementações devolvem `False` para GitHub PAT, JWT e chave privada RSA — e a SPEC pede exatamente PAT, JWT, chave privada, OAuth client secret, DSN, Bearer token e alta entropia. Chave privada é o caso mais claro: `-----BEGIN RSA PRIVATE KEY-----` não passa no piso de entropia porque tem espaço, e nenhum padrão de valor a procura | `tests/test_facts_emr_cluster.py` |
| Arquivo classificado sensível sai inteiro do índice | NÃO EXISTE | A redação atua no par chave/valor, dentro de um fato. Não existe a decisão anterior — "este arquivo é sensível, portanto nem símbolo nem snippet nem metadado de conteúdo saem dele" | — |

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
| `.sparkforge/local/` fora do git | NÃO EXISTE | E o buraco é maior que a linha que falta. Hoje `.sparkforge/traces.db` e `.sparkforge/cache/` **não** estão ignorados: `git check-ignore` só reconhece `.sparkforge/artifacts/*`. Um banco de índice de código de cliente colocado ali, sob a política atual, é commitável por acidente | — |
| Permissão restrita de diretório e arquivo, com umask | NÃO EXISTE | Nada no repositório define permissão de arquivo criado | — |

## 7. Banco, schema e taxonomia de grafo

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Ponto cego como cidadão de primeira classe | EXISTE, com teste | É lei da casa antes de ser pedido da SPEC: onze extratores emitem um kind `*.unresolved` com vocabulário fechado de razão, e o envelope das tools conta `unresolved` sobre o conjunto inteiro — filtrar por kind **não** faz o ponto cego sumir do relatório. Fonte limpa reporta zero, nunca ausência | `tests/test_adapters_tools.py` |
| Id determinístico de nó, derivado de conteúdo | EXISTE PARCIAL | `Fact.id` é hash estável sobre kind, subject e measures, e ignora `provenance` de propósito — o mesmo conteúdo produz o mesmo id entre execuções. É a propriedade que a SPEC pede para o nó, aplicada ao fato: não há nó, então não há id de nó | `tests/test_findings_models.py` |
| Taxonomia de aresta | EXISTE PARCIAL | `pyspark.callgraph_edge` (chamador → chamado) mais os quatro kinds `callgraph.*` cobrem a aresta de chamada e o que se deriva dela. `import`, `herança`, `referência de tipo` e `escrita/leitura de tabela como aresta de grafo` não existem como aresta — leitura e escrita existem como **fato**, com o alvo literal dentro | `tests/test_fixtures_golden_callgraph.py` |
| Banco com schema versionado, migrations e locking | NÃO EXISTE | Não há banco de grafo de código, portanto não há schema, migration, `files`, `nodes`, `edges`, `unresolved_refs` nem lock de índice | — |
| Índice FTS sobre símbolo e signature | NÃO EXISTE | Nenhuma busca por símbolo, em memória ou em disco | — |
| Sanitização de signature antes de armazenar | NÃO EXISTE | Consequência da linha acima: não há signature armazenada | — |

## 8. Extractors

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Arquitetura de extractor com identidade e versão | EXISTE, com teste | Todo extrator declara `EXTRACTOR_ID` e o grava em `provenance` de cada fato, ao lado do artefato e do sha256 dele. É a procedência que a SPEC pede por nó, já entregue por fato | `tests/test_fixtures_golden.py` |
| Extractor PySpark | EXISTE, com teste | `sparkforge/facts/pyspark_ast.py:extract_source()` cobre leitura, escrita, cache, join, explode, window, `conf.set`, UDF, dedup, coleta no driver, laço, particionamento e cadeia de método, com golden por fixture | `tests/test_fixtures_golden.py` |
| Grafo de dados tabela → job → tabela | EXISTE PARCIAL | `pyspark.read` e `pyspark.write` carregam o alvo literal quando ele é literal, e `sparkforge/facts/consumers.py` cruza produção com inventário de consumidor. O que falta é o grafo: os dois lados existem como fato solto, ninguém liga um ao outro numa estrutura consultável | `tests/test_fixtures_golden.py` |
| Call graph com ciclo e alcançabilidade a partir de entrypoint | EXISTE, com teste | `sparkforge/facts/call_graph.py` deriva quais funções existem, quanto trabalho Spark cada uma concentra, o que é alcançável de cada entrypoint e a que profundidade mínima, quais ciclos existem e o que ninguém referencia. É função pura sobre fatos: nunca lê arquivo, nunca reparseia | `tests/test_fixtures_golden_callgraph.py` |
| Lineage dinâmico declarado em vez de silenciado | EXISTE, com teste | O que o extrator não resolve vira `pyspark.unresolved` com razão de vocabulário fechado, e o filtro por kind não consegue esconder isso do envelope | `tests/test_adapters_tools.py` |
| Extractor de SQL com predicado e projeção | EXISTE, com teste | `sparkforge/facts/sql_literal.py` lê SQL embutido em literal de código e emite `sql.predicate`, `sql.projection`, `sql.predicate.partition_filter` e as formas enriquecidas | `tests/test_fixtures_golden_sql.py` |
| Símbolos gerais de Python | EXISTE PARCIAL | `pyspark.function_def` cobre função definida, com ou sem chamada, e o extrator sabe quando o `def` está dentro de uma classe. Não existe nó de classe, nem grafo de import, nem qualified name, nem hierarquia de tipo. O que há é uma tabela de símbolo com forma de PySpark, não de Python | `tests/test_fixtures_golden.py` |
| Lineage de DataFrame variável a variável | NÃO EXISTE | O extrator entende a cadeia de método dentro de uma expressão, mas não segue o valor de uma variável para outra | — |
| Workers de parsing isolados, autenticados, com limite | NÃO EXISTE | A extração roda no processo, sem worker, sem autenticação de worker e sem limite de memória, tempo ou tamanho | — |

## 9. Indexação incremental e freshness

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Manifesto de conteúdo verificável, com detecção de adulteração | EXISTE, com teste | `knowledge/offline-manifest.json` mais `sparkforge/tools/offline.py:OfflineKnowledgeIndex.verify()` conferem SHA-256 documento a documento e separam ausência de divergência. O hash normaliza fim de linha porque o contrário fazia o gate depender da plataforma — a lição vale inteira para um índice de código | `tests/test_offline_expansion.py` |
| Sinal de staleness por arquivo | EXISTE PARCIAL | Todo fato carrega `provenance.artifact_sha256`, então dá para saber que um fato veio de um conteúdo específico. Não existe o outro lado: nada compara o sha de hoje com o sha de quando o fato foi produzido, porque nada guarda o fato entre execuções | `tests/test_fixtures_golden.py` |
| Git lido sem executar hook | EXISTE, com teste | A superfície de execução do repositório é uma lista fechada e auditada, e nenhum hook usa construção de execução arbitrária | `tests/test_execution_surface.py` |
| Índice persistente, completo e incremental | NÃO EXISTE | Cada análise reparseia a árvore inteira. Não há índice para atualizar, nem noção de arquivo mudado desde a última vez | — |
| Strict tree, fingerprint de worktree, namespace por branch | NÃO EXISTE | Nenhuma noção de estado de árvore de trabalho | — |
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
| Expansão determinística de query por dicionário versionado | NÃO EXISTE | Nada expande "skew no join" para `broadcast`, `salting`, `AQE`. O vocabulário de domínio existe espalhado em `knowledge/` e em `rules/catalog/`, nunca como dicionário de sinônimo | — |
| Escore composto de recuperação | NÃO EXISTE | Nome exato, qualified name, relevância FTS, proximidade no grafo, relevância de entrypoint e de lineage não existem como componente de escore, porque não existe o grafo sobre o qual medi-los | — |
| Objeto de contexto canônico | NÃO EXISTE | `MinimalContext` e o retorno de `pack_context` são objetos de contexto, mas nenhum dos dois carrega índice, entry point, relação, lineage, regra, runtime, unresolved e bloco de segurança na mesma estrutura | — |
| Teto duro de token na saída, e ordem de redução declarada | NÃO EXISTE | A paginação limita **quantidade de itens**, não tamanho em token, e não há ordem escrita de o que sacrificar primeiro quando o orçamento estoura | — |

## 11. Tools MCP e CLI

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Núcleo comum entre CLI e MCP | EXISTE, com teste | `sparkforge/adapters/_core.py` é o núcleo; `cli.py` e `tools.py` são casca. Há teste medindo que as duas superfícies declaram a mesma opcionalidade — é exatamente o que a SPEC pede para as tools novas | `tests/test_adapters_tools.py` |
| Schema de saída declarado e validado contra a saída real | EXISTE, com teste | Toda tool declara `outputSchema`, e há teste que roda a tool e valida a saída real contra o schema declarado, inclusive no caminho de erro | `tests/test_adapters_tools.py` |
| Anotações de confiança por tool | EXISTE, com teste | Toda tool declara `annotations`, e o catálogo é auditado: só as tools de coleta são de mundo aberto, e toda tool de mundo aberto também escreve localmente | `tests/test_adapters_tools.py` |
| Entrada tipada, sem schema de objeto nu | EXISTE, com teste | Toda tool declara `properties` e `required`, e nenhuma usa objeto nu | `tests/test_adapters_tools.py` |
| Entrada fechada a propriedade desconhecida | NÃO EXISTE | Nenhum dos schemas de entrada declara `additionalProperties: false`, que é uma constraint explícita da tool principal da SPEC. Argumento não previsto entra sem erro | — |
| Controle de verbosidade na resposta | NÃO EXISTE | `detail_level` aparece em **0** das **44** tools do catálogo. Toda chamada devolve a mesma forma, no mesmo detalhe | — |
| Projeção de campo na resposta | NÃO EXISTE | `fields` não aparece em tool nenhuma do catálogo. Não há como pedir só `kind` e `subject.file` | — |
| Poucas tools compondo operações internamente | NÃO EXISTE | O catálogo tem o tamanho medido na linha acima, e a SPEC pede explicitamente o oposto dessa estratégia | — |
| As tools `sparkforge_code_*` | NÃO EXISTE | Nenhuma das onze existe: contexto, busca, símbolo, leitura, impacto, lineage, contexto do que mudou, status, sync, métricas e status de segurança | — |
| Comandos `code init`, `code doctor`, `code purge` | NÃO EXISTE | Não há subcomando `code` no CLI | — |
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

## 15. Testes de segurança

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Teste de traversal de caminho | EXISTE PARCIAL | Dois casos, nos dois lugares que hoje resolvem caminho de fora: catálogo de regras e árvore vendorizada. A matriz que a SPEC pede — caminho absoluto, `..` encadeado, symlink, caminho UNC, byte nulo, unicode — não existe | `tests/test_vendor_caveman.py` |
| Robustez a arquivo malformado e a encoding inválido | EXISTE, com teste | Falha por arquivo nunca é fatal: `SyntaxError` e `UnicodeDecodeError` viram um fato `unresolved` para aquele arquivo e a varredura continua. Perder a árvore inteira por causa de um arquivo ruim seria o pior modo de falha de um analisador | `tests/test_fixtures_golden_graph.py` |
| Verificação de ausência de egress | NÃO EXISTE | Nenhum teste observa syscall, socket ou DNS durante uma análise | — |
| Teste de vazamento do banco | NÃO EXISTE | Não há banco de código para vazar; quando houver, o teste precisa existir antes | — |
| Corpus de segredo | NÃO EXISTE | É a lacuna mais concreta desta seção: nenhum teste exercita o módulo canônico de segredo, e os casos que a SPEC enumera não estão cobertos por nenhuma das quatro implementações | — |
| Fuzzing de parser | NÃO EXISTE | Nenhuma suíte de entrada gerada, nem corpus de negação de serviço | — |

## 16. Supply chain

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Dependência mínima como controle de segurança | EXISTE, com teste | O pacote core depende de `PyYAML` e `jsonschema`, e nada mais; AWS, HTTP e SDK MCP são extras. O espelho de requisitos é conferido byte a byte contra o `pyproject.toml`, então uma dependência nova não entra por um caminho e some pelo outro | `tests/test_requirements_mirror.py` |
| Integridade de artefato vendorizado | EXISTE, com teste | `vendor/` tem manifesto com sha por projeto, licença original preservada, e caminho que escape do diretório é recusado no código, não só no teste | `tests/test_vendor_caveman.py` |
| Verificação do artefato instalado | EXISTE, com teste | `scripts/verify_wheel.py` roda os módulos golden dentro de um ambiente isolado, com `PYTHONPATH` vazio e o Python do ambiente virtual, não o corrente | `tests/test_verify_wheel.py` |
| SBOM associado ao release | NÃO EXISTE | Nenhum CycloneDX, nenhum SPDX | — |
| Lock reprodutível e instalação frozen no CI | NÃO EXISTE | Não há `uv.lock` nem equivalente; o CI instala a partir das faixas do `pyproject.toml` | — |
| `pip-audit` ou OSV no CI | NÃO EXISTE | Nenhum dos dois nos workflows. O repositório declara piso de versão para transitiva vulnerável à mão, no `pyproject.toml`, o que é disciplina sem automação | — |
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
- **Uma superfície de tool que sabe economizar.** `detail_level` em zero e projeção de campo em
  zero são economia disponível hoje, sem índice nenhum.

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
- **Resolução confinada de caminho**: `sparkforge/rules/loader.py:safe_catalog_file()` e a
  guarda equivalente de `scripts/vendor_caveman.py`.
- **Núcleo comum CLI/MCP, envelope paginado, schema de saída validado contra a saída real**:
  `sparkforge/adapters/_core.py` e `sparkforge/adapters/tools.py`.
- **Conteúdo de terceiro como dado não confiável**: já é invariante travado, com teste que
  deriva o conjunto de extratores executando-os.

As três implementações de empacotamento de contexto e as quatro de estimativa de token são o
sinal mais claro de que a ordem certa é consolidar, não somar. Escrever uma quinta seria repetir
o erro que a duplicação de detector de segredo já cobra caro.

### 3. O que precisa vir ANTES do índice

Persistir código de cliente em disco muda a natureza do risco, e três coisas passam a ser
pré-condição, não melhoria:

- **Política de git para o estado local, antes de existir estado local.** Hoje
  `.sparkforge/traces.db` e `.sparkforge/cache/` não estão ignorados — só
  `.sparkforge/artifacts/*` está. Um banco com símbolo e snippet de código proprietário no
  mesmo diretório, sob essa política, é commitável por acidente num repositório que pode ser
  público. Esta é a linha mais barata do documento inteiro e a de maior consequência.
- **Sandbox de filesystem aplicado ao alvo da análise.** O algoritmo já está escrito em
  `safe_catalog_file`; o que falta é aplicá-lo onde o caminho vem de fora. Junto com ele vêm a
  denylist e a exclusão de árvore de dependência: hoje a varredura entra em `.venv/`,
  `node_modules/` e `vendor/` e lê qualquer `*.json` que encontrar, o que é ao mesmo tempo custo
  de token e superfície de vazamento. Sem índice isso já é ruim; com índice, vira persistência
  de credencial.
- **Firewall de segredo que funcione por valor.** As quatro implementações atuais só pegam
  access key da AWS e senha em URL sem ajuda do nome da chave. Um índice que persista snippet
  vai persistir o PAT, o JWT e a chave privada que elas não veem. Consolidar as quatro numa e
  acrescentar os detectores por valor **precisa** vir antes de o primeiro byte de código ir para
  o disco — e com corpus de teste, que hoje é zero.

Há uma quarta pré-condição, de contrato e não de segurança: **o custo do envelope**. Na fixture
`clean_job`, o payload de fatos é várias vezes o tamanho do fonte, e a maior fatia disso não é dado
útil — é `provenance` repetida em cada fato, com o mesmo sha256 do mesmo arquivo copiado uma vez
por fato, mais `schema_version` copiado junto. Um objeto de contexto que herde essa forma
nasce caro pelo mesmo motivo. A correção é estrutural e independe do índice: procedência
declarada uma vez por artefato, referenciada por chave nos fatos.

E um limite que precisa ser resolvido ou aceito por escrito: [`AUTHORIZATION-CHAIN.md`](AUTHORIZATION-CHAIN.md)
registra que `authorize()` autoriza um **nome**, nunca uma **chamada** — a assinatura não recebe
os argumentos da tool. As onze tools novas da SPEC recebem caminho, e é o caminho que decide se
a chamada é legítima. A resposta da SPEC (resolução segura de caminho e denylist) resolve
**dentro** da tool, depois que a autorização já disse sim; a cadeia continua não vendo o
argumento. Fechar isso é mudança de assinatura de `authorize()` mais um ponto de checagem antes
da execução — trabalho pequeno, decisão de arquitetura grande, e ele não pertence à fase de
índice: pertence à fase de segurança, antes dela.

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
segurança antes por princípio; aqui há dívida medida. As quatro cópias de detector de segredo
sem teste, a ausência de denylist, a varredura que entra em `.venv/` e a linha que falta no
`.gitignore` são problemas de **hoje**, que existem sem SFCI nenhum. A fase de segurança não é
preparação para o índice — é conserto do que já está aberto.

**Diverge na fase de AST.** A SPEC trata o extractor de Python e PySpark como fase inteira. Aqui ela
é quase toda dívida já paga: o extractor existe, com golden por fixture, e o que falta (classe,
import, qualified name) é incremento sobre uma varredura pronta. Essa fase deve encolher e
mudar de conteúdo — de "escrever extractor" para "acrescentar os nós que faltam e ligar
`call_graph.py` ao índice".

**Diverge na ordem entre armazenamento e conserto do envelope.** A SPEC constrói o armazenamento
e só depois, na fase de recuperação, chega ao orçamento de token. A medição sugere o contrário:
enquanto o formato de fato custar várias vezes o fonte por procedência repetida, tudo que o índice
devolver herda esse custo. Consertar a forma da procedência é barato, não depende de banco
nenhum, e é medível antes e depois — é a primeira coisa a fazer depois da segurança, não a
quarta.

**Diverge por acrescentar uma fase zero que a SPEC não tem.** Antes de qualquer código de
índice, há economia disponível sem índice: nem controle de verbosidade nem projeção de campo
existem em tool nenhuma, e paginação existe em **22** — metade do catálogo devolve tudo, no mesmo
detalhe. Consolidar os quatro estimadores de token e os três empacotadores de contexto entra
aqui também. É a fase mais barata, a mais fácil de medir, e a única que dá ganho no dia em que
for entregue.

Ordem que a medição sugere, então:

1. **Consertar o que já está aberto**: unificar o detector de segredo com corpus de teste,
   fechar a política de git do estado local, aplicar confinamento de caminho e denylist na
   varredura, excluir árvore de dependência.
2. **Baratear o que já é devolvido**: procedência declarada uma vez por artefato,
   `detail_level` e projeção de campo nas tools existentes, um estimador de token só.
3. **Decidir a cadeia de autorização**: `authorize()` passa a ver argumento, ou o limite é
   aceito por escrito com a compensação nomeada.
4. **Persistir**: banco, schema, índice completo e incremental, FTS — sobre a extração que já
   existe, não sobre uma nova.
5. **Consultar por símbolo**: recuperação, ranking e objeto de contexto, consolidando os três
   empacotadores em vez de somar um quarto.
6. **Só então superfície nova de tool**, e o mínimo possível dela.

O restante da ordem da SPEC — worktree, lineage de SQL, hardening, MCP 2026, linguagens
adicionais — a medição não contesta.
