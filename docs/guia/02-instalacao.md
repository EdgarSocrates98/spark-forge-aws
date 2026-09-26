# Instalação

Este guia mostra como instalar o SparkForge, conferir que funcionou e resolver
os problemas comuns. Termos novos estão no
[glossário](01-conceitos.md#glossário).

## Receita rápida

Instalação a partir do código-fonte, em Linux ou macOS. Precisa de Python 3.10
ou mais novo.

```bash
# 1. Baixar o código
git clone https://github.com/EdgarSocrates98/spark-forge-aws.git && cd spark-forge-aws

# 2. Criar e ativar um ambiente virtual (pasta isolada de pacotes)
python3 -m venv .venv && source .venv/bin/activate

# 3. Instalar
pip install -e .

# 4. Conferir a versão
sparkforge --version

# 5. Conferir que o catálogo de regras foi encontrado
sparkforge rules lookup --id SF-PY-001
```

No Windows (PowerShell), troque o passo 2 por
`python -m venv .venv; .venv\Scripts\Activate.ps1`.

Deu certo se o passo 4 imprimir `sparkforge <versão>` e o passo 5 devolver
`"total_count": 1`. Se precisar falar com a AWS ou usar MCP, veja
[extras](#4-instalar-extras-se-precisar).

## Para que serve

Instalar o pacote `sparkforge-aws` coloca dois comandos no seu terminal:

- `sparkforge`: a CLI principal, com todos os analisadores e verbos.
- `sparkforge-tools`: um utilitário menor de apoio (índice offline de
  knowledge, estimativa de tokens e extração de linhagem).

O pacote já traz dentro dele o catálogo de regras (`rules/catalog/`) e a base
de conhecimento (`knowledge/`). Por isso `analyze`, `judge` e `rules lookup`
funcionam mesmo sem o repositório clonado.

## Quando instalar do código-fonte e quando pelo PyPI

- **Do código-fonte** (`pip install -e .`): quando você clonou o repositório e
  quer usar a versão exata dele, ou vai contribuir. O `-e` (modo editável)
  faz o Python usar os arquivos do clone diretamente; uma alteração no código
  vale na hora, sem reinstalar.
- **Pelo PyPI** (`pip install sparkforge-aws`): quando você só quer usar a
  ferramenta.

Os dois caminhos instalam os mesmos comandos.

## Pré-requisitos

- **Python 3.10 ou mais novo.** O `pyproject.toml` declara
  `requires-python = ">=3.10"`. Confira a sua versão:

  ```bash
  python --version
  ```

- **pip**, que vem com o Python.
- **Git**, se for instalar do código-fonte.
- Recomendado: um **ambiente virtual** (venv), uma pasta isolada onde os
  pacotes deste projeto ficam separados dos outros projetos do seu computador.

Não é preciso ter Spark, Java nem conta AWS para usar a maior parte do
SparkForge. A conta AWS só é necessária para os comandos `collect`, que baixam
artefatos da nuvem.

## Passo a passo

### 1. Obter o código (só para instalação do código-fonte)

```bash
git clone https://github.com/EdgarSocrates98/spark-forge-aws.git
cd spark-forge-aws
```

### 2. Criar e ativar um ambiente virtual

No Linux ou macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows, em PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

No Windows, em Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

Com o ambiente ativo, o nome `(.venv)` costuma aparecer no começo da linha do
terminal.

### 3. Instalar

Do código-fonte, dentro da pasta do clone:

```bash
pip install -e .
```

Pelo PyPI:

```bash
pip install sparkforge-aws
```

A instalação básica traz só duas dependências: `PyYAML` e `jsonschema`. É o
suficiente para extrair facts de arquivos, julgar e consultar o catálogo.

### 4. Instalar extras, se precisar

"Extra" é um grupo opcional de dependências que você pede entre colchetes. Os
extras reais, lidos do `pyproject.toml`, são:

| Extra | O que instala | Para que serve |
|---|---|---|
| `aws` | `boto3` | Os comandos `collect ...`, que leem artefatos direto da sua conta AWS (event log, definição do job Glue, métricas do CloudWatch, metadata Iceberg e outros). |
| `parquet` | `pyarrow` (versão mínima 23.0.1, fixada por causa de vulnerabilidades conhecidas em versões anteriores) | Ler o rodapé (footer) de arquivos Parquet na coleta. O comando `analyze parquet-footer` **não** precisa dele, porque parte de um JSON já coletado. |
| `mcp` | `mcp`, `starlette`, `uvicorn` e pisos de versão de duas dependências indiretas | O servidor MCP, nos transportes `stdio` e `http`. Necessário para usar as tools em assistentes como Claude Code e Devin. |
| `dev` | `pytest`, `ruff`, `defusedxml`, `build` e as mesmas dependências do extra `mcp` | Rodar os testes e o lint do projeto. Só para quem contribui. |

Exemplos de instalação com extras (as aspas evitam que o shell interprete os
colchetes):

```bash
pip install -e ".[aws]"          # código-fonte + coletores AWS
pip install -e ".[mcp]"          # código-fonte + servidor MCP
pip install -e ".[aws,mcp]"      # os dois
pip install "sparkforge-aws[parquet]"   # pelo PyPI, com leitura de Parquet
```

## Verificar a instalação

### A CLI responde

```bash
sparkforge --version
```

Saída:

```text
sparkforge 0.5.0
```

(O número é o da versão que você instalou.)

```bash
sparkforge --help
```

Saída encurtada:

```text
usage: sparkforge [-h] [--version]
                  {analyze,migrate,glue,iceberg,release,controlm,benchmark,workload,...} ...

Analise deterministica de jobs AWS Glue PySpark: extracao de facts, julgamento
contra o catalogo de regras, e o ciclo de vida do case que atravessa sessoes.
...
```

### O catálogo foi encontrado

Este comando não precisa de nenhum arquivo seu. Ele consulta uma regra real do
catálogo embarcado:

```bash
sparkforge rules lookup --id SF-PY-001
```

Saída encurtada:

```json
{
  "total_count": 1,
  "returned_count": 1,
  "next_cursor": null,
  "filters_applied": { "id": ["SF-PY-001"], "category": null, "limit": 50, "cursor": null },
  "by_category": { "pyspark-code": 1 },
  "rules": [
    {
      "id": "SF-PY-001",
      "category": "pyspark-code",
      "title": "Python UDF em transformação expressável nativamente",
      "requires_facts": ["pyspark.udf"],
      "...": "...",
      "knowledge_refs": [
        { "ref": "knowledge/spark/execution-model.md", "path": "..." }
      ]
    }
  ]
}
```

Se `total_count` for `1`, o catálogo está no lugar. Um id que não existe
devolve `total_count: 0` e `rules: []`, sem erro: é assim que o comando diz
"não achei".

### A base de conhecimento foi encontrada

```bash
sparkforge knowledge path
```

A saída mostra a pasta raiz de `knowledge/` em `root` e a lista de arquivos em
`available`. Instalado do código-fonte, `root` aponta para a pasta do clone.
Instalado pelo PyPI, aponta para dentro do `site-packages`.

### O `sparkforge-tools` responde

O comando `sparkforge-tools` está registrado no `pyproject.toml` em
`[project.scripts]`. Os subcomandos dele são `offline`, `cost` e `lineage`.

```bash
sparkforge-tools offline verify
```

Saída real, rodada na raiz do repositório:

```json
{
  "offline": true,
  "checked": 52,
  "failed": [],
  "ok": true
}
```

`offline verify` confere os arquivos listados no manifesto offline de
`knowledge/`. O valor de `checked` depende da versão do repositório. Rode este
comando na raiz do clone, ou passe `--repo <pasta-do-clone>`.

## Canais de distribuição

| Canal | Como chega | Para quem |
|---|---|---|
| Plugin do Claude Code | `.claude-plugin/plugin.json`, instalado via marketplace ou path local | Claude Code |
| MCP (`sparkforge.adapters.mcp`) | `.mcp.json`, transportes `stdio` e `http` | Devin Desktop, Devin CLI, GitHub Copilot |
| `pip` | `pip install -e .` ou `pip install sparkforge-aws` | CLI `sparkforge` em qualquer shell/CI |
| Espelhos markdown | `rules/catalog/*.yaml`, `skills/`, `knowledge/` | Sem MCP e sem Python — leitura direta |

O servidor MCP, cliente por cliente, está em [MCP](04-mcp.md).

## `pip install sparkforge-aws`: o pacote carrega o catálogo dentro dele

```bash
pip install sparkforge-aws            # CLI sparkforge sozinho
pip install "sparkforge-aws[aws]"     # + boto3, para os extratores que leem AWS
pip install "sparkforge-aws[mcp]"     # + servidor MCP (stdio e streamable HTTP)
```

Diferente de um `pip install` comum, este wheel não traz só código: `rules/catalog/`
(o catálogo de regras em YAML) e `knowledge/` (a base de conhecimento sobre
Spark, Glue, EMR, Athena, Parquet e Iceberg) vêm embarcados dentro do pacote,
resolvidos por `loader.catalog_dir()` na mesma ordem de sempre — variável de
ambiente, raiz do repositório e, faltando as duas, o fallback dentro do
próprio pacote instalado. É esse terceiro degrau que faz `analyze`, `judge`,
`next-step`, `resume` e `rules lookup` funcionarem **sem o repositório
clonado**: um agente autônomo que sobe um sandbox efêmero, roda `pip install
sparkforge-aws` e não tem mais nada em disco ainda assim consegue extrair
facts, julgar contra o catálogo completo e citar a fonte de cada limiar —
porque o catálogo veio junto no wheel, não porque o agente clonou o
repositório antes.

Para localizar `knowledge/` a partir do pacote instalado:

```bash
sparkforge knowledge path                                  # imprime a raiz
sparkforge knowledge path --file glue/runtime-matrix.md     # imprime um arquivo específico
```

`rules lookup` também devolve os caminhos já resolvidos: cada regra retornada
inclui os arquivos de `knowledge/` que a sua `explanation` cita, com o
caminho pronto para abrir — dentro do repositório em modo desenvolvimento,
dentro de `site-packages` quando instalado por `pip`.

Essa paridade não é promessa: o CI constrói o wheel, instala em venv limpo
**fora do repositório** e reproduz as fixtures golden byte a byte a partir do
pacote instalado, em Linux e em Windows — o mesmo golden que o repositório
usa, não um corpus à parte (a contagem corrente de fixtures está na tabela
*Números correntes* de [`docs/superpowers/STATUS.md`](../superpowers/STATUS.md)).
Se `sparkforge` acabar sendo importado do repositório em vez do `site-packages`
nesse processo, o gate falha com mensagem explícita em vez de comparar o
repositório consigo mesmo. O gate é `python scripts/verify_wheel.py`; o que
ele verifica está em [Espelhos e dependências](12-espelhos-e-dependencias.md).

## Integrar uma vez por máquina: `sparkforge integrate`

Com o pacote instalado, um comando por host deixa skills, agents e o servidor MCP
disponíveis em **qualquer** repositório da máquina, sem copiar nada para dentro dele. O
conteúdo sai do próprio wheel (`sparkforge/integrate/bundle/`), com ou sem acesso ao
GitHub.

```bash
sparkforge integrate all --scope user --dry-run    # lista o que seria escrito, sem escrever
sparkforge integrate all --scope user              # claude, devin, codex e copilot
sparkforge integrate devin --scope user            # um host só
sparkforge doctor                                  # uma checagem integracao_<host> por host
sparkforge detach all --dry-run                    # lista o que seria removido
sparkforge detach all                              # remove só o que o SparkForge escreveu
```

O host é `claude`, `devin`, `codex`, `copilot` ou `all`. `--scope user` é obrigatório
no `integrate` e é o único escopo desta versão. A saída é JSON no stdout, com o que foi
escrito, o que já estava igual e as recusas; o código de saída é 1 quando há recusa.

### O que cada host recebe, e onde

| Host | Agents | Skills | MCP |
|---|---|---|---|
| Claude Code | plugin `sparkforge-aws` do marketplace local `sparkforge-local`, em `~/.sparkforge/claude/plugins/sparkforge-aws/agents/` | no mesmo plugin, `skills/` | `.mcp.json` do plugin |
| Devin CLI | `~/.config/devin/agents/` (`%APPDATA%\devin\agents\` no Windows) | `~/.agents/skills/` | `~/.config/devin/mcp_config.json` (`%APPDATA%\devin\mcp_config.json` no Windows), chave `mcpServers.sparkforge` |
| Codex CLI | `$CODEX_HOME/agents/*.toml` (padrão `~/.codex/agents/`) | `~/.agents/skills/` | bloco marcado `[mcp_servers.sparkforge]` em `$CODEX_HOME/config.toml` |
| Copilot CLI | `~/.copilot/agents/*.agent.md` | `~/.agents/skills/` | `~/.copilot/mcp-config.json`, chave `mcpServers.sparkforge` |

`~/.agents/skills/` é lido pelos três hosts de baixo, e os três gravam a mesma
renderização: o arquivo é um só, com um dono por host no manifesto, e só sai do disco
quando o último host que o usa é desintegrado. Os perfis executores não vão para o
Codex, porque não têm `description` e o TOML de agent do Codex exige uma.

O servidor MCP é chamado pelo Python que tem o `sparkforge` instalado
(`python -m sparkforge.adapters.mcp --transport stdio`), sem `PYTHONPATH` para
repositório nenhum. A config de usuário que já existia é mesclada, nunca sobrescrita:
só a entrada `sparkforge` entra. No `detach`, a config que ainda é exatamente o que o
`integrate` gravou volta byte a byte ao que era antes (ou sai, se foi o `integrate` que
a criou); se você mexeu em outras partes dela, sai só a entrada `sparkforge`, no estilo
do arquivo.

O Claude Code é registrado pelo próprio CLI dele:

```bash
claude plugin marketplace add ~/.sparkforge/claude --scope user
claude plugin install sparkforge-aws@sparkforge-local --scope user --json
```

O `integrate` roda esses dois comandos por você (e, nas vezes seguintes, `claude plugin
marketplace update sparkforge-local` e `claude plugin update sparkforge-aws@sparkforge-local`
quando o conteúdo mudou). Cada chamada ao CLI tem limite de 120 segundos. O `detach`
chama primeiro `claude plugin uninstall` e `claude plugin marketplace remove`, e só
depois apaga os arquivos.

### O manifesto: `~/.sparkforge/integrations.json`

Tudo o que é gravado fica em `~/.sparkforge/integrations.json`, com o sha256 de cada
arquivo, os hosts donos dele, a versão do pacote que integrou e o registro de cada
config de usuário tocada. Rodar o `integrate` de novo com o mesmo pacote não muda nada.
Arquivo que já estava no HOME, idêntico ao que o pacote grava, é adotado como
preexistente e nunca é apagado pelo `detach`.

O `detach` remove só o que o manifesto registrou e ainda tem o sha256 gravado. Arquivo
que você editou depois fica no lugar e sai como recusa `editado_pelo_usuario`. Da
config de usuário sai só a entrada que o `integrate` pôs. Quando o último host sai, o
manifesto também sai.

`sparkforge doctor` lê o manifesto e mostra uma checagem `integracao_<host>` por host:
ausente, integrado e em que versão do pacote, defasado quando o pacote instalado é
outro, e a cópia em dobro no repositório atual, quando houver.

### `APPDATA` e `CODEX_HOME`

A CLI lê `%APPDATA%` e `CODEX_HOME` do ambiente e passa os mesmos valores ao
`integrate` e ao `detach`; sem `CODEX_HOME`, o Codex fica em `~/.codex`. O manifesto
guarda a raiz usada. Se você rodar depois com outro `APPDATA` ou outro `CODEX_HOME`,
os caminhos registrados apontariam para outro lugar: o comando recusa com
`appdata_divergente` (ou `codex_home_divergente`) e não toca em nada. Rode com o mesmo
valor da integração.

### Cópia em dobro no repositório

Se o repositório de onde você chama o `integrate` tem a cópia do `install_skills.py`
(`.claude/skills`, `.agents/skills`, `.claude/agents`, `.agents/agents`,
`.github/agents`), o mesmo nome apareceria duas vezes nos hosts que não separam por
namespace. O `integrate` lista os nomes repetidos, cada um como idêntico ao que o pacote
instala ou customizado, e pergunta:

- **SOBRESCREVER** (`overwrite`): apaga do repositório a cópia inteira, idêntica ou
  customizada;
- **MESCLAR** (`merge`): apaga só o que é idêntico e lista o customizado, que continua
  em dobro;
- **IGNORAR** (`ignore`): não toca no repositório.

`--on-conflict overwrite|merge|ignore` responde sem prompt. Sem terminal e sem a flag,
a resposta é IGNORAR. Antes de apagar, a lista de arquivos sai no stderr, um por linha,
e toda remoção respeita `--dry-run`. Só colide o que o host integrado carrega:
`integrate devin` não olha `.claude/agents`. `.agents/skills`, lido por Devin, Codex e
Copilot, só sai do repositório quando os três estão integrados; antes disso a entrada
fica como `mantido_host_nao_integrado`. Nenhuma remoção segue link ou junção: entrada
que aponta para fora do repositório sai `copia_fora_do_repositorio` e nada dela é
apagado. Se o host alvo saiu com recusa, o repositório não é tocado
(`conflito_nao_resolvido_por_recusa`).

No próprio repositório do SparkForge os espelhos `.claude/`, `.agents/` e `.github/`
são gerados e versionados: sai a recusa `repositorio_fonte` e nada é tocado.

### Recusas e o que fazer

| Recusa | O que aconteceu | O que fazer |
|---|---|---|
| `claude_cli_ausente` | O binário `claude` não está no PATH. O plugin fica montado em `~/.sparkforge/claude/` e a recusa traz os comandos. | Instale o Claude Code e rode os dois comandos `claude plugin` acima, ou rode o `integrate claude` de novo. |
| `claude_cli_falhou` / `claude_cli_timeout` | Um comando `claude plugin` saiu com erro ou passou de 120 segundos. A recusa traz o comando e o fim da saída. | Rode o comando mostrado à mão e depois o `integrate` de novo. |
| `sparkforge_ja_configurado` | A config de usuário já tem um `sparkforge` que você mesmo escreveu. O arquivo não é tocado. | Tire a sua entrada, ou mantenha-a e ignore a recusa. |
| `config_invalida` / `bloco_toml_quebrado` | A config de usuário não se lê como JSON, ou o bloco marcado do `config.toml` perdeu um dos marcadores. | Conserte o arquivo e rode de novo. |
| `editado_pelo_usuario` | O arquivo (ou a entrada de config) mudou depois do `integrate`. | Nada: ele fica. Para trocar pela versão do pacote, apague-o e rode o `integrate`. |
| `arquivo_do_usuario` | Já existe no destino um arquivo diferente que o SparkForge nunca gravou. | Renomeie ou apague o seu, se quiser o do pacote. |
| `manifesto_ilegivel` | O `integrations.json` não se lê. Nada é tocado. | Restaure o manifesto de um backup. Apagá-lo faz o próximo `integrate` tratar como seu o que já está no HOME. |
| `appdata_divergente` / `codex_home_divergente` | `APPDATA` ou `CODEX_HOME` diferente do que o manifesto registrou. | Rode com o mesmo valor da integração. |

Três estados não são recusa do `integrate`, mas pedem atenção:

- `preexistente_desatualizado`: um arquivo adotado como preexistente e que o pacote
  novo mudou fica como está. Apague-o e rode o `integrate` para receber a versão nova.
- `config_pendente` (no `detach`): a entrada da config não pôde ser retirada (arquivo
  inválido, bloco quebrado ou entrada editada). O registro fica no manifesto; conserte o
  arquivo e rode o `detach` de novo.
- `cli_pendente` (no `detach claude`): o CLI do Claude faltou ou falhou. Nada do plugin
  sai do disco nem do manifesto, para o Claude não ficar apontando para um marketplace
  apagado; o `detach` seguinte conclui.

### Limites desta versão

- Copilot no VS Code fica de fora: o caminho do MCP de usuário não foi confirmado na
  documentação oficial. O Copilot coding agent na nuvem não tem escopo de usuário e
  continua lendo `.github/agents` do repositório.
- Que o Codex lê agents em `$CODEX_HOME/agents/` é inferência: a documentação confirma
  o `config.toml` sob `CODEX_HOME`, não o diretório de agents.
- Não foi medido se o Codex lê `~/.agents/skills` quando roda fora de um repositório git.
- No Python 3.10 a validade do `config.toml` do usuário não é conferida; só o par de
  marcadores do bloco.

## Instalar as skills e os agents em outro repositório

O caminho de cima (`sparkforge integrate`) instala uma vez por máquina. A cópia por
repositório continua existindo para quando os arquivos precisam estar versionados
dentro do projeto: o Copilot coding agent na nuvem, por exemplo, só lê
`.github/agents` do repositório. Se você usar os dois caminhos no mesmo repositório,
veja a cópia em dobro acima. As skills e os perfis de agent chegam a outro repositório
por `scripts/install_skills.py`, que escreve os diretórios de cada plataforma.

No próprio repositório:

```bash
cd /caminho/do/repositorio && python /caminho/do/sparkforge/scripts/install_skills.py --all
```

Apenas Claude Code:

```bash
python scripts/install_skills.py --target . --claude
```

Apenas Devin:

```bash
python scripts/install_skills.py --target . --devin
```

Apenas GitHub Copilot:

```bash
python scripts/install_skills.py --target . --copilot
```

Use `--force` para substituir arquivos existentes.

A instalação escreve **no diretório atual** — por isso o `cd` no primeiro
exemplo. `--target` é opcional e serve como confirmação explícita do destino:
se for passado e não for o diretório atual, o script recusa e mostra o `cd`
correto, em vez de escrever num lugar que você não estava olhando.

## Onde o projeto grava dados

O SparkForge grava estado na pasta `.sparkforge/`, **dentro do diretório que
você está analisando** (o que você passa em `--repo`, ou o diretório atual).

| Caminho | O que é | Vai para o Git? |
|---|---|---|
| `.sparkforge/case.yaml` | O estado da investigação (veja [case](01-conceitos.md#case)). | Sim, é pequeno e serve de passagem entre sessões e ferramentas. |
| `.sparkforge/facts.json`, `.sparkforge/findings.json`, `.sparkforge/handoff.md` | Saídas derivadas que você grava com `--out` ou com `handoff`. | Sim. |
| `.sparkforge/artifacts/` | Artefatos brutos coletados (event log, dumps). Só o `manifest.json` é versionado. | Não, porque pode conter dado de negócio e ser grande. |
| `.sparkforge/traces.db`, `.sparkforge/cache/` | Registro das chamadas de tool e cache de saídas. | Não, porque acumula e pode conter trechos de artefato. |
| `.sparkforge/local/` | Índice local de código usado pelos comandos `code ...`. | Não. |

O `.gitignore` do próprio repositório já segue essa política. Se você usar o
SparkForge em outro repositório, copie as mesmas linhas para o `.gitignore`
dele.

Os arquivos que você grava com `--out` vão para onde você mandar. Nos
exemplos destes guias usamos uma pasta temporária para não sujar o
repositório.

## Atualizar

Do código-fonte:

```bash
git pull
pip install -e .
```

Rodar `pip install -e .` de novo depois do `git pull` é importante quando a
versão mudou: é esse passo que registra comandos novos (como o
`sparkforge-tools`) e atualiza os metadados do pacote.

Pelo PyPI:

```bash
pip install --upgrade sparkforge-aws
```

Com extras, repita os colchetes: `pip install --upgrade "sparkforge-aws[mcp]"`.

## Desinstalar

```bash
pip uninstall sparkforge-aws
```

A desinstalação remove os comandos e o pacote. Ela **não** apaga as pastas
`.sparkforge/` que foram criadas nos repositórios analisados; apague-as à mão
se não precisar mais delas.

## Erros comuns e como resolver

### `sparkforge: command not found` (ou "não é reconhecido como comando")

A pasta de scripts do Python não está no PATH, ou o ambiente virtual não está
ativo.

1. Ative o ambiente virtual (passo 2).
2. Se ainda falhar, chame o módulo diretamente, o que funciona sempre que o
   pacote está instalado:

   ```bash
   python -m sparkforge.adapters.cli --help
   ```

   No Windows sem venv, os scripts ficam em
   `<pasta-do-Python>\Scripts`; acrescente essa pasta ao PATH.

### `sparkforge-tools` não é encontrado, mas `sparkforge` é

A instalação é antiga, de antes de o comando ser registrado. Reinstale:

```bash
pip install -e .
```

Enquanto isso, `python -m sparkforge.tools.cli offline verify` funciona.

### `pip show sparkforge-aws` mostra uma versão diferente de `sparkforge --version`

Em instalação editável antiga, os metadados do pip podem ficar parados na
versão do dia em que você instalou, enquanto o código já é o novo. A versão
que vale é a de `sparkforge --version`. Rodar `pip install -e .` de novo
alinha as duas.

### Extra ausente

Cada extra ausente produz uma mensagem com o comando exato de correção. As
mensagens reais do código são:

| Situação | Mensagem (início) | Correção |
|---|---|---|
| Comando `collect ...` sem `boto3` | `boto3 nao disponivel. Instale com pip install 'sparkforge-aws[aws]' ...` | `pip install -e ".[aws]"` ou `pip install "sparkforge-aws[aws]"` |
| Leitura de footer Parquet sem `pyarrow` | `pyarrow nao disponivel. Instale com pip install 'sparkforge-aws[parquet]' ...` | `pip install "sparkforge-aws[parquet]"` |
| Servidor MCP sem o SDK | `SDK do MCP nao instalado. Rode pip install 'sparkforge-aws[mcp]' ...` | `pip install "sparkforge-aws[mcp]"` |

A mensagem do `boto3` também lembra que você pode coletar o artefato por
outro caminho (AWS CLI ou console) e registrá-lo, sem instalar o extra.

### A pasta `knowledge/` não é encontrada

A mensagem diz a causa e mostra duas saídas: apontar a variável de ambiente
`SPARKFORGE_KNOWLEDGE` para a pasta `knowledge/` do clone, ou reinstalar o
pacote com `pip install --force-reinstall sparkforge-aws` (o pacote a partir
da versão 0.5.0 embarca `knowledge/`).

### `CatalogError` ao subir o servidor MCP fora do Claude Code

O `.mcp.json` da raiz do repositório usa a variável `${CLAUDE_PLUGIN_ROOT}`,
que só o Claude Code expande. Em outra ferramenta, registre o servidor sem
essa variável:

```bash
python -m sparkforge.adapters.mcp --transport stdio
```

O `GUIA_DE_USO.md` traz a configuração por ferramenta (Devin CLI, Devin
Desktop com `--transport http`, GitHub Copilot).

## Próximos passos

- [CLI](03-cli.md): como ler a saída e um fluxo completo rodado.
- [Conceitos](01-conceitos.md): o glossário.
- [Índice de comandos](referencia/cli/README.md) e
  [índice de tools](referencia/tools/README.md).
