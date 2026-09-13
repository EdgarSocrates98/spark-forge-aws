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
