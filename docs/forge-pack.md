# Forge Pack

Um Forge Pack é um diretório de **dados** de terceiro, carregado junto do core:
regras YAML, knowledge e fixtures (§5 de `prompt_new_evo.md`). Serve para a
equipe que quer padrões próprios sobre os mesmos artefatos sem fazer fork do
SparkForge.

```bash
export SPARKFORGE_PACKS=/caminho/acme-platform        # vários: separados por os.pathsep
sparkforge pack list                                  # ativos, recusados, prefixo -> pack
sparkforge pack check /caminho/acme-platform          # exit 1 se uma regra não dispara
sparkforge judge --facts terraform.json               # regras do core + do pack
```

A tool MCP é `sparkforge_pack_list` (`READ_ONLY`, sem parâmetro). `pack check`
é só da CLI, porque é tarefa de quem escreve o pack. O dono no despacho é o
`spark-performance-architect`.

## O que um pack traz

```text
acme-platform/
├── pack.yaml
├── rules/*.yaml             # mesmo formato de rules/catalog, chave `rules:`
├── knowledge/**             # Markdown; knowledge/sources.lock.json opcional
└── fixtures/<caso>/
    ├── facts.json
    └── expect.yaml          # fires: [ACME-GOV-001]
```

```yaml
pack:
  id: acme-platform          # ^[a-z][a-z0-9-]*$
  version: 1.0.0
  prefix: ACME               # ^[A-Z][A-Z0-9]*$, nunca SF
  core: ">=0.5,<1.0"         # >=, >, <=, <, == separados por vírgula
  description: ...
```

A versão do core é a do código que está rodando. No repositório, ela é o `version` do
`pyproject.toml`. Instalado, é a metadata do pacote. Ler só a metadata não bastava:
medido em 2026-09-12, com o código do repositório carregado, ela respondeu
`0.4.0` de uma instalação velha.

## O que o pack **não** faz

- Não traz extrator, collector, tool, agente nem skill. Nada do pack é
  importado: só `yaml.safe_load`, JSON e texto. As regras dele leem os kinds
  que o core já emite.
- Não sobrescreve regra do core, e não usa o prefixo `SF`.
- Não declara rota. A área dele cai no `fallback` do `routing.yaml`.
- Não é instalado, publicado nem assinado por este verbo.

Consequência: regra do tipo "job **sem** o atributo X" não é escrevível. A
condição `absent` do motor só confere o kind (`engine.py`), e o predicado
exigiria um fact derivado (regra 33 do `CLAUDE.md`) que um pack não traz.

## As recusas

O pack é recusado **inteiro** no primeiro motivo, e os outros packs e o core
seguem.

| Motivo | Quando |
|---|---|
| `manifesto_invalido` | `pack.yaml` ausente, campo faltando, formato fora das expressões |
| `prefixo_reservado` | `prefix: SF` |
| `pack_duplicado` | `id` **ou** `prefix` de um pack já ativo. O prefixo diz a origem do finding |
| `core_incompativel` | A versão do core fora da faixa `core:` |
| `regra_invalida` | A regra não passa pelo mesmo validador do core (`validate_rule`), ou o caminho escapa do pack |
| `id_fora_do_prefixo` | `id` que não casa `<PREFIX>-<AREA>-NNN` |
| `id_duplicado` | Dois `id` iguais dentro do pack |

Um diretório de `SPARKFORGE_PACKS` que não existe é erro do operador, e não
recusa: sai com código 2 e o caminho.

## Confiança: a variável é do operador

`SPARKFORGE_PACKS` escolhe diretórios em qualquer lugar do disco, por desenho.
Ela tem a mesma confiança de `SPARKFORGE_CATALOG` e de `SPARKFORGE_KNOWLEDGE`:
só o operador a define, no ambiente ou no `.mcp.json`. Nenhuma tool a recebe
como parâmetro, e por isso `sparkforge_pack_list` não declara caminho.

Dentro do pack, o confinamento é duro. `rules/` é resolvido e exigido dentro do
diretório do pack **antes** de qualquer varredura, então um `rules` que seja
symlink para fora é recusado. Cada arquivo passa pela varredura da casa
(`iter_source_files`, com denylist e teto de tamanho) e por `resolve_within`.
Nada é importado nem executado.

Um SAST (Snyk, `python/PT`, low) aponta o fluxo variável → `os.walk`. Esse fluxo
é o próprio desenho: não existe base confiável contra a qual confinar um
diretório que o operador escolheu. É o mesmo fluxo que `SPARKFORGE_CATALOG` já
fazia até o `glob` do loader. O operador decidiu em 2026-09-12 aceitar esse risco
em vez de restringir os packs a uma raiz fixa.

## Onde o pack aparece

- `load_catalog()` sem `directory` acrescenta as regras dos packs ativos. Sem a
  variável, a lista é a mesma de antes. CI e gates rodam sem ela, e não defina a
  variável ao regenerar golden.
- **Finding:** não ganha campo novo. O prefixo do `rule_id` é a origem, e
  `pack list` publica o mapa. O schema de `rule_id` passou a
  `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[0-9]{3}$`. O golden de paridade MCP registra
  essa troca em `PADROES_ALARGADOS`, com 6 ocorrências por transporte.
- **Knowledge:** `knowledge path` ganha a chave `packs`, sem mexer em
  `available`. Um arquivo de pack é pedido como `packs/<id>/<arquivo>`.
- **Freshness:** a fonte de uma regra de pack é conferida no lock do próprio
  pack. Sem o lock, sai `unresolved` com `pack_sem_lock`. O lock do core nunca
  vigia URL de pack.

## Onde está provado

- `tests/test_packs_manifest.py`: a faixa de versão e as recusas do manifesto.
- `tests/test_packs_load.py`: cada recusa, a carga com e sem variável, o
  `judge` e o `root_cause` enxergando o pack, knowledge e freshness.
- `tests/test_fixtures_golden_packs.py` e `fixtures/packs/`: o `pack list` com o
  pack sintético `acme-platform` e todos os packs de recusa ativos ao mesmo
  tempo, e o `pack check` verde e vermelho.
