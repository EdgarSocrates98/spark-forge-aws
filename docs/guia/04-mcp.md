# Servidor MCP do SparkForge

**MCP (Model Context Protocol)** é um jeito padronizado de um assistente de IA
(Claude Code, Devin, Copilot e outros) chamar ferramentas de um programa externo.
O assistente é o **cliente**. O SparkForge é o **servidor**: ele publica uma
lista de **tools** (funções com nome, entrada e saída descritas) e responde
quando o assistente chama uma delas.

Cada tool do servidor faz o mesmo que um comando da CLI `sparkforge`. O MCP só
muda **quem** chama: em vez de você digitar o comando, o assistente chama a tool.

Termos novos estão no [glossário](01-conceitos.md).

## Receita rápida (Claude Code)

Rode na raiz do repositório clonado:

```bash
pip install -e ".[mcp]"
python -m sparkforge.adapters.mcp --help
claude mcp add -s local sparkforge -- python -m sparkforge.adapters.mcp --transport stdio
claude mcp list
```

Depois, dentro de uma sessão do Claude Code, peça:

```text
Liste as tools MCP do sparkforge e chame sparkforge_runtime_detect.
```

O que cada passo faz:

1. `pip install -e ".[mcp]"` instala o pacote com o extra `mcp`. O extra traz o
   SDK do MCP (`mcp>=2,<3`), que não vem na instalação básica.
2. `--help` confirma que o módulo do servidor carrega. A saída real começa com
   `usage: sparkforge-mcp [-h] [--transport {stdio,http}] [--host HOST] [--port PORT]`.
3. `claude mcp add` cadastra o servidor. `-s local` grava a configuração só na
   sua máquina, fora do git.
4. `claude mcp list` mostra os servidores cadastrados e confere se cada um
   responde.

## Quando usar e quando não usar

Use o MCP quando você trabalha **dentro** de um assistente e quer que ele chame o
SparkForge sozinho, com entrada e saída validadas.

Não precisa de MCP quando:

- você roda comandos no terminal: a CLI faz tudo o que as tools fazem
  ([referência da CLI](referencia/cli/README.md));
- a ferramenta não mantém uma sessão MCP interativa. É o caso do Codex e do
  Copilot em CI, que usam a CLI (declarado em `parity.yaml`).

## Pré-requisitos

- Python instalado. O repositório usa `python` nos exemplos.
- O pacote instalado com o extra `mcp` (passo 1 da receita).
- Nenhum acesso à AWS. O servidor só toca a nuvem quando você chama uma tool
  `collect_*`.

## Os dois transportes

**Transporte** é o canal por onde cliente e servidor conversam. O servidor tem
dois (`sparkforge/adapters/mcp.py`):

| Transporte | Como funciona | Quem usa |
|---|---|---|
| `stdio` (padrão) | O cliente abre o servidor como processo filho e conversa pela entrada e saída padrão | Claude Code, Devin CLI, CI |
| `http` | O servidor abre uma porta e atende em `http://<host>:<port>/mcp` | Devin Desktop |

Os padrões do `http` são `--host 127.0.0.1` e `--port 8765`.

Diferença importante: no `http`, a tool `sparkforge_code_read` **não é
publicada**. Ela devolve trecho de código-fonte, e uma porta de rede sem
autenticação que devolve código seria um vazamento. Se precisar dela, use `stdio`.

## Configurar em cada cliente

### Claude Code

Há dois caminhos.

- **Cadastro manual**, o da receita rápida. Funciona com o repositório clonado.
- **Plugin.** O `.mcp.json` da raiz é o arquivo do *plugin* do Claude Code
  (`.claude-plugin/plugin.json`):

  ```json
  {
    "mcpServers": {
      "sparkforge": {
        "command": "python",
        "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
        "env": {
          "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}",
          "SPARKFORGE_CATALOG": "${CLAUDE_PLUGIN_ROOT}/rules/catalog"
        }
      }
    }
  }
  ```

  `${CLAUDE_PLUGIN_ROOT}` é preenchida pelo carregador de plugin. Fora dele, o
  valor pode chegar sem ser expandido. Se o servidor morrer com
  `CatalogError: SPARKFORGE_CATALOG aponta para .../${CLAUDE_PLUGIN_ROOT}/...`,
  use o cadastro manual.

### Devin CLI (stdio)

O repositório já traz `.devin/mcp_config.json`:

```json
{
  "mcpServers": {
    "sparkforge": {
      "command": "python",
      "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"]
    }
  }
}
```

Ou cadastre pela própria CLI do Devin:

```bash
devin mcp add -s project sparkforge -- python -m sparkforge.adapters.mcp --transport stdio
devin mcp list
```

`-s project` grava em `.devin/mcp_config.json`, e `-s local` grava em
`.devin/mcp_config.local.json`, que fica fora do git. Detalhes em
[`GUIA_DE_USO.md`](../../GUIA_DE_USO.md), seção 3.4.

### Devin Desktop (HTTP)

Suba o servidor e deixe o terminal aberto enquanto usar:

```bash
python -m sparkforge.adapters.mcp --transport http --host 127.0.0.1 --port 8765
```

No Desktop, em **Devin Settings > MCP**, cadastre a URL
`http://127.0.0.1:8765/mcp`.

### GitHub Copilot

O repositório configura o Copilot para usar a **CLI**, e não o MCP
(`.github/copilot-instructions.md` e `parity.yaml`). A CLI tem o mesmo contrato
das tools. Se o seu cliente Copilot aceitar servidores MCP, use a configuração de
cliente genérico abaixo. O nome do arquivo de configuração muda de cliente para
cliente, então confira na documentação dele.

### Cliente MCP genérico

Qualquer cliente que aceite servidor `stdio` precisa de duas informações:

- comando: `python`
- argumentos: `-m sparkforge.adapters.mcp --transport stdio`

Variáveis de ambiente opcionais:

| Variável | Para que serve |
|---|---|
| `SPARKFORGE_CATALOG` | Usar um catálogo de regras fora do pacote. Aponte para um diretório real |
| `SPARKFORGE_PACKS` | Carregar Forge Packs. Ver [packs e conhecimento](usos/packs-e-conhecimento.md) |
| `SPARKFORGE_RUN_ID` | Agrupar as chamadas numa medição. Ver [economia de contexto](usos/economia-de-contexto.md) |

## Como verificar que funciona

**Sem cliente nenhum.** Monte o servidor em Python:

```bash
python -c "from sparkforge.adapters.mcp import build_server; print(type(build_server()).__name__)"
```

Saída real: `Server`. Se o SDK faltar, a saída é a mensagem
`SDK do MCP nao instalado. Rode pip install 'sparkforge-aws[mcp]' ...`.

**Transporte HTTP.** Com o servidor no ar, teste o endereço. Resultado real,
obtido com o servidor rodando em 127.0.0.1:

| Pedido | Resposta |
|---|---|
| `GET /mcp` | `406 Not Acceptable`. O endpoint existe; ele só não aceita um GET simples |
| `GET /outra` | `404` com o texto `nao encontrado; use /mcp` |
| `POST /mcp` com `initialize` | `200`, com as `instructions` do servidor |

Qualquer código HTTP prova que o servidor está no ar. `connection refused` quer
dizer que ele não subiu ou que a porta está errada.

**Dentro do assistente.** Peça para listar as tools do `sparkforge` e chamar
`sparkforge_runtime_detect`.

## Tool e comando da CLI são o mesmo código

As regras de negócio moram em `sparkforge/adapters/_core.py`. A CLI
(`cli.py`) e as tools (`tools.py`) são cascas finas em volta dele.

O nome segue um padrão: `sparkforge code search` vira `sparkforge_code_search`.
Os **nomes dos argumentos** podem mudar. Exemplo real:

| CLI | Tool |
|---|---|
| `sparkforge code search capacity --root capacity` | `{"repo": "capacity", "query": "capacity"}` |

Na dúvida, veja a página da tool em
[`referencia/tools/`](referencia/tools/README.md), por exemplo
[`sparkforge_code_search`](referencia/tools/sparkforge_code_search.md).

## O que as anotações de cada tool querem dizer

Toda tool publica quatro **anotações**: marcas que dizem ao cliente o que ela faz
com o ambiente. O cliente usa essas marcas para decidir se pede sua confirmação.

| Anotação | Em linguagem simples |
|---|---|
| `readOnlyHint: true` | Só lê. Não grava nada em lugar nenhum |
| `readOnlyHint: false` | Pode gravar arquivo no seu disco |
| `openWorldHint: true` | Sai da sua máquina: acessa a AWS |
| `idempotentHint: true` | Repetir a mesma chamada dá o mesmo resultado |
| `destructiveHint: false` | Não apaga nada. Todas as tools do SparkForge declaram `false` |

Na prática, as tools caem em três grupos:

| Grupo | Anotações | Exemplos |
|---|---|---|
| Só leitura | `readOnlyHint: true`, `openWorldHint: false` | `analyze_*`, `judge`, `rules_lookup`, `economy_report`, `collect_verify` |
| Grava em disco local | `readOnlyHint: false`, `openWorldHint: false` | `case_open`, `case_update`, `arbitrate`, `debate_start`, `debate_submit`, `code_*` |
| Acessa a AWS | `readOnlyHint: false`, `openWorldHint: true` | `collect_*`, menos `collect_verify` |

As tools `code_*` estão no grupo de gravação porque podem atualizar o índice local
de código antes de responder. Os coletores `collect_*` leem da AWS e gravam o
artefato baixado no seu disco.

## `detail_level`: o tamanho da resposta

Muitas tools aceitam `detail_level` (na CLI, `--detail-level`) com três valores:

| Valor | O que volta |
|---|---|
| `full` (padrão) | Tudo, com a procedência (de onde o dado veio) dentro de cada item |
| `normal` | A procedência vai **uma vez** no envelope, e cada item aponta para ela por `provenance_ref` |
| `summary` | Cada item fica só com `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol` |

Nada some em silêncio: o que sai do item aparece no envelope. Não existe tool que
busque um item por `id`. Para ver o item inteiro, rode de novo em `full`.

**Meça antes de afirmar que reduziu** (regra 28 do `CLAUDE.md`). Num corpus
pequeno, o envelope fixo pesa mais que os itens, e a diferença entre os níveis
pode ser pequena. Use o `economy report`, que mostra os bytes de cada nível
pedido. O passo a passo está em [economia de contexto](usos/economia-de-contexto.md).

## Paginação

Tools que devolvem listas respondem por **página**:

| Campo | Significado |
|---|---|
| `total_count` | Quantos itens existem, depois dos filtros |
| `returned_count` | Quantos vieram nesta página |
| `next_cursor` | O valor para pedir a próxima página. `null` na última |

Para a próxima página, repita a chamada com `cursor` igual ao `next_cursor`.
Trecho real de `sparkforge_analyze_pyspark` com `limit: 2`:

```json
{
  "total_count": 5,
  "returned_count": 2,
  "next_cursor": "2",
  ...
}
```

Cuidado: quem lê só `items` sem olhar `next_cursor` julga só a primeira página.

## Como aparece um erro

Erro de uso nunca vira exceção crua. Ele volta como um objeto com `error`
(a frase) e `exit_code` (o código de saída, o mesmo da CLI). Às vezes vem também
`error_code`, para programas, e `action`, com o que fazer. Exemplo real, com um
índice de código que ainda não existe:

```json
{
  "error": "indice inexistente: .../vazio/.sparkforge/local/codeintel/graph.sqlite3; construa com `sparkforge code sync`.",
  "exit_code": 2,
  "action": "sparkforge code sync",
  "db": ".../vazio/.sparkforge/local/codeintel/graph.sqlite3",
  "error_code": "INDEX_MISSING"
}
```

Pelo MCP, esse objeto chega com a marca `isError` ligada. Outras formas que você
pode ver:

| Mensagem | Causa |
|---|---|
| `Input validation error: ...` | Argumento fora do formato que a tool declara |
| `ferramenta indisponivel no transporte 'http': ... Use --transport stdio.` | Tool que só existe em `stdio`, pedida pelo `http` |
| `chamada recusada pela cadeia de autorizacao: ...`, com `error_code: UNAUTHORIZED` | Uma política de autorização recusou a chamada |

## Exemplo: chamar uma tool em Python, sem cliente MCP

`call_tool` em `sparkforge/adapters/tools.py` é a mesma porta que o servidor usa.
Serve para testar sem assistente nenhum. Rode numa pasta de teste, porque cada
chamada registra uma medição em `.sparkforge/traces.db` na pasta atual:

```bash
mkdir -p /tmp/sf-guia && cp -r sparkforge/capacity /tmp/sf-guia/capacity
cd /tmp/sf-guia
sparkforge code init --root capacity
python -c "
import json
from sparkforge.adapters.tools import call_tool
r = call_tool('sparkforge_code_search', {'repo': 'capacity', 'query': 'capacity'})
print(json.dumps(r, indent=1))
"
```

Saída real, encurtada:

```json
{
 "index": {"fresh": true, ...},
 "returned_count": 1,
 "filtered_from": 1,
 "results": [
  {
   "node_id": "node_ab77aa4fcaa97f1006bd6d033aa27855",
   "name": "build_capacity_plan",
   "kind": "function",
   "path": "plan.py",
   "start_line": 153
  }
 ]
}
```

Um nome de tool que não existe levanta `KeyError` com a lista das válidas:
`ferramenta desconhecida: 'sparkforge_nao_existe'. Validas: ...`.

## Famílias de tools

Toda tool começa com `sparkforge_`. A lista completa, com entrada e saída de cada
uma, está no [índice de tools](referencia/tools/README.md).

| Família | O que faz |
|---|---|
| `analyze_*` | Extrai **facts** (observações medidas) de um artefato que já está no disco |
| `collect_*` | Baixa artefato real da AWS. Único grupo que toca a nuvem. `collect_verify` só confere o que já foi baixado |
| `judge`, `fuse`, `rules_lookup` | Aplicam e consultam o catálogo de regras |
| `workload`, `capacity`, `finops`, `tune`, `gain`, `simulate`, `proof` | Compõem sobre facts já extraídos. Não leem artefato |
| `benchmark`, `funcval_*` | Comparam dois runs, ou o resultado antes e depois de uma mudança |
| `case_*`, `next_step`, `resume`, `playbook` | Estado da investigação (o *case*) e o próximo passo |
| `arbitrate`, `debate_*`, `root_cause` | Arbitram achados que se contradizem e ordenam as causas |
| `code_*` | Inteligência de código. Ver [code intelligence](usos/code-intelligence.md) |
| `report_*`, `receipt_*`, `validate_output` | Relatório para PR, assinatura, recibo e validação de achados |
| `economy_report`, `telemetry_export` | Medição do contexto consumido. Ver [economia de contexto](usos/economia-de-contexto.md) |
| `knowledge_*`, `pack_list` | Conhecimento versionado e Forge Packs. Ver [packs e conhecimento](usos/packs-e-conhecimento.md) |
| `release_*`, `migration_assess`, `runtime_detect`, `glue_*`, `iceberg_*`, `lakeformation_*`, `controlm_*` | Versões de runtime, migração e eixos específicos de cada serviço |

## Problemas comuns

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| `SDK do MCP nao instalado` ou `ModuleNotFoundError: mcp` | Extra `mcp` não instalado | `pip install -e ".[mcp]"` na raiz do repositório |
| `CatalogError: ... ${CLAUDE_PLUGIN_ROOT} ...` | O `.mcp.json` do plugin foi usado fora do plugin | Cadastre com `claude mcp add` ou `devin mcp add`, sem `env` |
| `CatalogError` com um caminho real | `SPARKFORGE_CATALOG` aponta para pasta que não existe | Remova a variável ou aponte para um diretório real |
| O cliente não mostra as tools | Servidor não cadastrado no escopo certo, ou não aprovado | `claude mcp list` ou `devin mcp list`, e aprove o servidor se ele aparecer como pendente |
| `sparkforge_code_read` não aparece | Você está no transporte `http` | Use `stdio` |
| Devin Desktop não conecta | Servidor HTTP parado ou porta errada | Suba de novo com `--transport http` e confira a URL `/mcp` |

## Próximos passos

- [Glossário](01-conceitos.md)
- [Code intelligence](usos/code-intelligence.md)
- [Economia de contexto](usos/economia-de-contexto.md)
- [Packs e conhecimento](usos/packs-e-conhecimento.md)
- [Índice de tools](referencia/tools/README.md) e [índice da CLI](referencia/cli/README.md)
