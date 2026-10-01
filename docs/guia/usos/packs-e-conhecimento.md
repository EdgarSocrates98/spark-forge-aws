# Regras, conhecimento e Forge Packs

O SparkForge julga os seus jobs com um **catálogo de regras**: arquivos YAML em
`rules/catalog/`, com limiar, fonte e validade de versão. Por trás das regras há
**conhecimento versionado**: documentos em `knowledge/` que citam a documentação
oficial, com a data em que alguém a leu.

Este guia mostra como consultar os dois, como saber se uma fonte envelheceu e
como somar regras próprias da sua equipe com um **Forge Pack**.

## Receita rápida

Da raiz do repositório:

```bash
sparkforge rules lookup --id SF-TIMEOUT-001 --source-freshness
sparkforge knowledge path --file glue/lakeformation-fgac.md --source-freshness
export SPARKFORGE_PACKS=fixtures/packs/acme-platform
sparkforge pack list
sparkforge pack check fixtures/packs/acme-platform
```

1. Mostra uma regra inteira e o estado da fonte que ela cita.
2. Mostra onde está um documento de conhecimento e o estado de cada fonte dele.
3. Ativa um pack sintético de exemplo. No PowerShell:
   `$env:SPARKFORGE_PACKS = "fixtures/packs/acme-platform"`.
4. Lista os packs ativos e os recusados.
5. Confere se cada regra do pack dispara no exemplo que a acompanha.

Se o comando `sparkforge` não estiver no PATH, troque por
`python -m sparkforge.adapters.cli`.

## Quando usar e quando não usar

- `rules lookup`: para saber o que uma regra exige, qual o limiar, a fonte, o
  risco e o rollback.
- `knowledge path` e `knowledge drift`: para saber se o que o projeto sabe ainda
  está em dia com a documentação oficial.
- Forge Pack: para a equipe acrescentar padrões próprios **sem** fazer fork.

Um pack **não** traz código. Se a sua regra precisa de um dado que o SparkForge
ainda não extrai, um pack não resolve.

## Pré-requisitos

- O pacote instalado.
- Nada de rede. Todos os comandos deste guia leem arquivos locais.

## Consultar regras

```bash
sparkforge rules lookup --id SF-TIMEOUT-001
sparkforge rules lookup --category timeout --limit 2
```

Trecho real da busca por id:

```json
{
  "total_count": 1,
  "returned_count": 1,
  "next_cursor": null,
  "rules": [
    {
      "id": "SF-TIMEOUT-001",
      "category": "timeout",
      "title": "Timeout com sintoma medido ao lado — aumentar o limite mascara a causa",
      "threshold": {"skew_ratio": 3.0, "spill_ratio": 0.1, "gc_ratio": 0.1, "executor_lost_min": 1},
      "severity_default": "P1",
      "proposed_change": [ ... ],
      "risks": [ ... ],
      "validation": [ ... ],
      "rollback": [ ... ],
      "sources": [{"url": "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html", "retrieved": "2026-08-29", ...}, ...]
    }
  ]
}
```

A resposta é paginada: se `next_cursor` não for `null`, repita com
`--cursor <valor>`. A tool equivalente é `sparkforge_rules_lookup`. Flags
completas em [`referencia/cli/rules.md`](../referencia/cli/rules.md).

## Saber se uma fonte envelheceu

Cada regra cita a documentação com a data de leitura (`retrieved`). O arquivo
`knowledge/sources.lock.json` guarda, por URL, se a página foi conferida por
hash e quando mudou. Com isso, cada fonte ganha um **estado**.

Peça o estado com `--source-freshness`. Fixe o dia com `--as-of AAAA-MM-DD`;
sem ele, vale o dia de hoje em UTC. Trecho real, com `--as-of 2026-09-13`:

```json
{
  "source_freshness": {
    "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html": {
      "state": "unverified",
      "reason": "nunca_conferida",
      "validated": "2026-08-29"
    }
  },
  "freshness_policy": {
    "aging_days": 14,
    "basis": "convencao: duas rodadas perdidas do refresh semanal (refresh-knowledge.yml, cron segunda 06:00 UTC)",
    "as_of": "2026-09-13",
    "counts": { ... }
  }
}
```

Os estados, na ordem em que o sistema decide:

| Estado | Quer dizer |
|---|---|
| `unresolved` | O lock não existe, não lê, ou não tem essa URL |
| `fixed` | A URL tem a versão no caminho. A página não muda |
| `stale` | A página mudou **depois** da data em que a regra a leu. Alguém precisa reler |
| `unverified` | A página nunca foi conferida por hash |
| `aging` | Conferida, sem mudança, há mais de 14 dias |
| `fresh` | Conferida, sem mudança, há 14 dias ou menos |

Três detalhes:

- **`conflicted`** não é estado. Aparece ao lado quando o lock tem outra leitura
  da mesma URL numa data diferente da que a regra declara.
- **`sem_url`** conta as fontes que não têm URL (nota de campo, por exemplo). Elas
  não recebem estado.
- **O limite de 14 dias é convenção**, e não medida. A razão sai em
  `freshness_policy.basis`.

O estado nunca entra no achado (`Finding`): o achado não muda de um dia para o
outro, e o estado muda. A explicação completa está em
[`docs/knowledge-freshness.md`](../../knowledge-freshness.md).

## Localizar conhecimento

```bash
sparkforge knowledge path
sparkforge knowledge path --file glue/lakeformation-fgac.md --source-freshness --as-of 2026-09-13
```

Sem `--file`, lista os documentos em `available`. Com `--file`, devolve o caminho
e, com `--source-freshness`, o estado de cada URL da seção `Fontes` do
documento. Trecho real:

```json
{
  "file": "...\\knowledge\\glue\\lakeformation-fgac.md",
  "source_freshness": {
    "https://docs.aws.amazon.com/glue/latest/dg/migrating-version-50.html": {
      "state": "aging",
      "reason": "conferida_ha_44_dias",
      "checked_at": "2026-07-31",
      "conflicted": {"validated": "2026-09-09", "other_readings": ["2026-07-29"]}, ...
    }, ...
  }
}
```

## Ver o que uma mudança de fonte arrasta

```bash
sparkforge knowledge drift --as-of 2026-09-13
```

O **Knowledge Drift Radar** responde: se uma fonte mudou, que regras,
documentos, exemplos, avaliações e agentes precisam ser revistos. Saída real de
hoje:

```json
{
  "as_of": "2026-09-13",
  "lock": {"sources": ..., "checked": ..., "pinned": ..., "changed": 0},
  "changed_sources": [],
  "totals": {"rules": 0, "docs": 0, "goldens": 0, "evals": 0, "agents": 0},
  "unresolved": [],
  "refused": [{"field": "conteudo_da_mudanca", "reason": "exige_leitura_humana_da_fonte"}]
}
```

Leia assim:

- `changed_sources` vazio: o lock ainda não registrou nenhuma mudança de página.
  O radar não tem o que mostrar.
- `refused` com `conteudo_da_mudanca`: o radar sabe **que** a página mudou, mas
  não **o que** mudou, porque o lock guarda o hash da página inteira. Isso exige
  uma pessoa relendo, e ele diz isso em vez de adivinhar.

Use `--source <url>` para olhar uma fonte só.

## Forge Pack: regras da sua equipe

Um **Forge Pack** é uma pasta só de **dados**: regras YAML, documentos e
exemplos. Ele é carregado junto das regras do core. Nada dele é importado ou
executado.

### Estrutura

```text
acme-platform/
├── pack.yaml
├── rules/*.yaml             # mesmo formato de rules/catalog, chave `rules:`
├── knowledge/**             # Markdown
└── fixtures/<caso>/
    ├── facts.json
    └── expect.yaml          # fires: [ACME-GOV-001]
```

O `pack.yaml` real do exemplo sintético:

```yaml
pack:
  id: acme-platform
  version: 1.0.0
  prefix: ACME
  core: ">=0.5,<1.0"
  description: Padroes de plataforma de dados da ACME (sintetico)
```

- `prefix` marca a origem de cada achado: `ACME-GOV-001` veio do pack `ACME`.
  O prefixo `SF` é reservado ao core.
- `core` é a faixa de versões do SparkForge com que o pack funciona.

### Ativar

Aponte a variável `SPARKFORGE_PACKS` para a pasta do pack. Para vários packs,
separe com `;` no Windows e `:` no Linux e no macOS. Só o operador define essa
variável. Nenhuma tool a recebe como parâmetro.

```bash
export SPARKFORGE_PACKS=fixtures/packs/acme-platform
sparkforge pack list
```

Saída real:

```json
{
  "env": "SPARKFORGE_PACKS",
  "installed_core": "0.5.0",
  "active": [
    {
      "id": "acme-platform",
      "prefix": "ACME",
      "rules": ["ACME-GOV-001", "ACME-GOV-002"],
      "knowledge": ["padroes-de-plataforma.md"], ...
    }
  ],
  "refused": [],
  "prefixes": {"ACME": "acme-platform"}
}
```

A partir daí, o `judge` passa a aplicar as regras do pack junto com as do core,
e os documentos do pack aparecem em `knowledge path`, na chave `packs`. Para ler
um deles, peça `--file packs/acme-platform/padroes-de-plataforma.md`. Pelo MCP,
a tool é `sparkforge_pack_list`, sem parâmetros.

### Conferir o pack

```bash
sparkforge pack check fixtures/packs/acme-platform
sparkforge pack check fixtures/packs/check_regra_morta
```

`pack check` roda cada exemplo do pack pelo `judge` e compara com o
`expect.yaml`. Resultado real do segundo, que é um exemplo feito para falhar
(código de saída 1):

```json
{
  "pack": {"id": "morta-platform", "version": "1.0.0", "prefix": "MORTA"},
  "cases": [
    {"case": "worker_g4x", "expected": ["MORTA-GOV-001"], "fired": [], "ok": false}
  ],
  "rules_without_fixture": ["MORTA-GOV-001"],
  "ok": false,
  "refused": null
}
```

A regra não disparou no exemplo que a declara. Uma regra que nunca dispara é
defeito do pack, e o comando diz isso. `pack check` só existe na CLI, porque é
tarefa de quem escreve o pack.

### Recusas

Um pack com problema é recusado **inteiro**, com o motivo. Os outros packs e o
core continuam funcionando. Exemplo real, ativando o pack de exemplo junto com um
que usa o prefixo reservado:

```json
"refused": [
  {
    "dir": "...\\fixtures\\packs\\recusa_prefixo_reservado",
    "id": "finge-core",
    "reason": "prefixo_reservado",
    "detail": "o prefixo SF e do core"
  }
]
```

| Motivo | Quando |
|---|---|
| `manifesto_invalido` | `pack.yaml` ausente, campo faltando ou formato errado |
| `prefixo_reservado` | `prefix: SF` |
| `pack_duplicado` | `id` ou `prefix` igual ao de um pack já ativo |
| `core_incompativel` | A versão do SparkForge está fora da faixa `core:` |
| `regra_invalida` | A regra não passa no mesmo validador do core, ou o caminho escapa do pack |
| `id_fora_do_prefixo` | Um `id` que não segue `<PREFIX>-<AREA>-NNN` |
| `id_duplicado` | Dois `id` iguais dentro do pack |

Cada motivo tem um exemplo em `fixtures/packs/recusa_*`. O desenho completo está
em [`docs/forge-pack.md`](../../forge-pack.md).

## Versões de runtime e validação de achados

Dois comandos vizinhos, sem aprofundar:

- `sparkforge release describe --platform glue --release 5.1` mostra o que a fonte
  oficial publica para uma versão (Spark, Python, Iceberg, com fonte e data).
  `sparkforge release diff` compara duas versões. Os dois leem a matriz de versão
  e **não** avaliam se algo quebra. Ver
  [`referencia/cli/release.md`](../referencia/cli/release.md).
- `sparkforge validate --findings <arquivo>` confere um arquivo de achados contra
  o schema. Com `fixtures/athena/engine_v2_outdated/expected/findings.json`, a
  saída real é `{"valid": true, "count": 1}`. Ver
  [`referencia/cli/validate.md`](../referencia/cli/validate.md).

## Erros comuns

| Sintoma | Causa | Como resolver |
|---|---|---|
| `SPARKFORGE_PACKS aponta para ..., que nao e um diretorio existente` (código 2) | Caminho errado na variável | Corrija o caminho. Isso é erro do operador, e não recusa de pack |
| Pack em `refused` | Um dos motivos da tabela | Leia `reason` e `detail` |
| `pack check` sai com 1 | Uma regra não disparou no exemplo dela | Compare `expected` com `fired`, e confira a condição `when` da regra |
| Regra do tipo "job **sem** o atributo X" não dispara | A condição `absent` só confere o tipo de fact | Não é escrevível num pack. Exige um fact derivado no core (regra 33 do `CLAUDE.md`) |
| Tudo `unverified` ou `aging` | O refresh semanal com rede não roda desde agosto | Veja "Pré-requisito do operador" em [`docs/knowledge-freshness.md`](../../knowledge-freshness.md) |

## Próximos passos

- [Glossário](../01-conceitos.md)
- [Servidor MCP](../04-mcp.md)
- Referência: [`rules`](../referencia/cli/rules.md), [`knowledge`](../referencia/cli/knowledge.md), [`pack`](../referencia/cli/pack.md), [`judge`](../referencia/cli/judge.md)
- Tools: [`sparkforge_rules_lookup`](../referencia/tools/sparkforge_rules_lookup.md), [`sparkforge_pack_list`](../referencia/tools/sparkforge_pack_list.md), [`sparkforge_knowledge_drift`](../referencia/tools/sparkforge_knowledge_drift.md)
