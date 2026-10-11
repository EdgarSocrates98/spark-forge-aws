# Receita — usar com o Devin CLI

**O quê:** com o install feito, o Devin lê `.mcp.json` de projeto, expõe o
server `sparkforge-aws` e enxerga as skills instaladas — sem configuração
extra.
**Por que:** é um dos três hosts com despacho de subagente: o coordenador
recomendado pelo `next-step` pode rodar como subagente de verdade.
**Quando:** investigação agêntica num repo com o Forge instalado.
**Quando não:** automação sem TTY — o mesmo contrato vale via MCP/CLI.

## Problema

"Como faço o Devin usar o SparkForge neste projeto?"

## Pré-requisitos

`sparkforge-aws install --scope project --root .` executado no repo.
Devin CLI presente (`devin --version`).

## Passo a passo

```bash
devin mcp list
# sparkforge-aws → python -m sparkforge_aws.adapters.mcp --transport stdio
```

Depois, na sessão Devin, peça em linguagem natural:

```text
Use a skill optimize-pyspark-code neste job em jobs/etl.py.
```

O host ativa a skill, que chama as tools MCP determinísticas
(`sparkforge_aws_analyze_pyspark` → `sparkforge_aws_judge` →
`sparkforge_aws_next_step`).

## Saída esperada / interpretação

Verificado nativamente: `devin mcp list` na raiz do projeto lista
`sparkforge-aws` com o comando exato do `.mcp.json`, e as skills do projeto
aparecem ao host (96 skills observadas num install `full`).

## Verificação

```bash
sparkforge-aws status --scope project --root .   # healthy
devin mcp list                                   # server presente
```

## Limitações

- Coordenadores despachados como subagentes **não** despacham executores
  (subagente não gera subagente por default): a decomposição roda inline —
  documentado em `AGENTS.md` §Coordinators and executors.
- O espelho `.agents/` descarta `tools:` do frontmatter (mapeamento não
  documentado) — a fronteira real do agente é a prosa `## Não faz`, igual
  nos dois espelhos.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `devin mcp list` vazio | install não rodou neste root | `sparkforge-aws install --root .` |
| skills ausentes | install `minimal` | reinstall `--profile recommended` |

## Uso por agentes

O `.mcp.json` gerenciado é o contrato: o host lê e registra o server.
Agents em `.devin/agents/` são perfis despacháveis; `.agents/agents/` é o
espelho nativo.

## Leitura seguinte

- [instalar-e-comecar](instalar-e-comecar.md)
- [usar-agents](usar-agents.md) — coordenadores, executores e playbook
- `GUIA_DE_USO.md` §2–3 — walkthrough completo por plataforma
