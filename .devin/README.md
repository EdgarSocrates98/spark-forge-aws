# SparkForge AWS — orientação para o Devin

Este diretório é a **fiação**, não a documentação. Ele existe para que o Devin
chegue ao SparkForge sozinho, e para registrar as três decisões que só valem
aqui. O conteúdo mora nos arquivos que esta página aponta — copiá-lo para cá
criaria uma segunda fonte que envelhece calada, que é o defeito que este
repositório mais persegue.

## O que é, em três linhas

SparkForge é um **motor determinístico** de diagnóstico de Spark na AWS. Ele lê
artefato (JSON de API, event log, Terraform, código PySpark), extrai `Fact` com
namespace fechado, e aplica um catálogo de regras YAML que produz `Finding` com
evidência ancorada — arquivo, linha, e a fonte primária que sustenta o
julgamento.

**Ele não opina.** Todo número que ele publica veio de um artefato ou de uma
fonte com URL e data. O que não tem lastro sai marcado como recusa, com o nome
da medida que a destravaria.

## Fiação

```bash
pip install "sparkforge-aws[mcp]"
```

Os dois arquivos ao lado já fazem o resto:

| Arquivo | O que faz |
|---|---|
| `mcp_config.json` | expõe as **63 tools** por stdio. Sem variável de ambiente — o `.mcp.json` da raiz é do plugin do Claude Code e usa `${CLAUDE_PLUGIN_ROOT}`, que nenhuma página do Devin documenta expandir |
| `config.json` | `permissions` para os verbos de leitura, e `read_config_from.claude: false` com a razão escrita |

As **46 skills** e os **38 coordenadores** o Devin lê sozinho de `.agents/`, que
é formato nativo dele. Não há nada a configurar para isso.

## As cinco regras que o motor impõe, e que o operador precisa aceitar

Elas não são estilo. Violá-las produz o tipo de resultado que este projeto
existe para não produzir.

1. **Fato precisa de fonte.** Versão, default, limiar e capacidade carregam URL e
   data de leitura. O que não se demonstra sai `UNKNOWN`, nunca suposição
   vestida de fato.
2. **Recusa tem nome.** Propriedade sem base medida sai em `refused` com a medida
   que a destravaria; lacuna sai como `*.unresolved`. Listar a recusa é a
   diferença entre "não sei" e "não perguntei".
3. **Ausência de achado não é ausência de problema.** Um relatório vazio significa
   *nenhuma regra alcançável disparou* — e os verbos declaram quantas eram
   alcançáveis, justamente para que o vazio não seja lido como "está tudo bem".
4. **Regra nunca acusa configuração correta.** É o pior defeito possível segundo
   `rules/catalog/README.md`, e por isso toda regra tem golden **positivo e
   negativo**.
5. **Preservar semântica.** Tunar sim; mudar lógica, regra de negócio ou
   resultado, não. Toda recomendação carrega validação e rollback.

## Qual verbo responde qual pergunta

`analyze *` **extrai** de artefato. Os verbos de topo **compõem** sobre facts que
outro verbo já extraiu — nenhum deles lê artefato, e é por isso que não são um
`analyze`.

| Pergunta do operador | Verbo |
|---|---|
| Que tipo de workload é este job? | `workload` |
| Qual a capacidade mais barata que cumpre o SLA? | `capacity` |
| Quanto custou, e onde está a alavanca? | `finops` |
| Que valor de configuração a medida sustenta? | `tune` |
| Melhorou ou piorou entre dois runs? | `benchmark` |
| O resultado continua o mesmo? | `funcval plan` / `funcval compare` |
| O que muda de componente entre duas releases? | `release diff` |
| O que quebra ao migrar de X para Y? | `migrate glue` / `migrate emr` |
| Posso subir esta tabela para Iceberg v3? | `iceberg assess-upgrade` |
| Qual o próximo artefato a coletar? | `next-step` |

A tabela completa, com o que cada verbo **consome**, está na seção *Os verbos que
compõem* do [`../CLAUDE.md`](../CLAUDE.md) — e as 28 regras numeradas que a
seguem são o contrato do motor, não orientação.

## Antes de ler artefato no olho, rode o verbo

Este é o hábito que faz o SparkForge valer a pena. Um `describe-job-run` de 400
linhas lido a olho vira opinião; passado por `sparkforge analyze emr-eks` vira
fact com namespace fechado, e `sparkforge judge` diz o que o catálogo tem a
dizer sobre ele.

As **46 skills** em `.agents/skills/` são gatilhos para isso: cada uma abre
dizendo **quando** entrar e **o que ela não julga**. Ler a fronteira antes de
trazer o artefato economiza a investigação inteira.

## As armadilhas deste repositório

Cada uma já derrubou uma entrega aqui.

**A suíte inteira num processo só não sobrevive.** Rode `tests/test_*.py` em
lotes. A medida de 2026-09-01 são **8565 testes** em **nove** lotes, e o de
goldens precisou de cinco partes — cada golden reextrai o corpus. **Nunca edite a
árvore com a suíte rodando.**

**Golden nunca se escreve à mão.** `python scripts/regen_fixtures.py <nome>`
gera; você **lê o diff**. Regenerar sem ler destrói a defesa contra falso
positivo, que é a única razão de o golden existir.

**Extrator novo entra em DUAS listas manuais**, no mesmo commit:
`EXTRACTORS` em `tests/test_fixtures_kind_coverage.py` **e** a lista de módulos
em `tests/test_rules_catalog_reachability.py`. Esquecer uma **não quebra nada** —
é o modo de falha silencioso que os comentários dos dois arquivos documentam.

**Cada tipo de mudança tem seu gate.** [`../docs/gates-por-mudanca.md`](../docs/gates-por-mudanca.md)
diz qual rodar. Os quatro que quase sempre valem:

```bash
python scripts/check_vnext_claims.py      # numero publicado tem prova (demora >2 min)
python scripts/check_surface_lock.py --update
python scripts/refresh_knowledge.py --offline --update
python scripts/sync_skills.py --check
```

**Número publicado é medido, não copiado.** O `STATUS.md` registra **cinco vezes**
o mesmo defeito: alguém somou o que a seção anterior escreveu em vez de contar.
Se você atualizar um número, conte.

## Onde está o resto

| Arquivo | O que é |
|---|---|
| [`../AGENTS.md`](../AGENTS.md) | o contrato multiferramenta — o Devin lê sozinho |
| [`../CLAUDE.md`](../CLAUDE.md) | as 28 regras do motor e a tabela de verbos |
| [`../AGENT_PROTOCOL.md`](../AGENT_PROTOCOL.md) | as 10 regras que todo agente segue |
| [`../GUIA_DE_USO.md`](../GUIA_DE_USO.md) | uso ponta a ponta; a §3.4 é a de MCP no Devin |
| [`../docs/superpowers/STATUS.md`](../docs/superpowers/STATUS.md) | **a fonte da verdade sobre onde o projeto está.** Specs e plans são registro histórico: descrevem o que se pretendia numa data, não o repositório de hoje. Quando um número divergir, este arquivo ganha |
| [`../docs/gates-por-mudanca.md`](../docs/gates-por-mudanca.md) | qual gate cada tipo de mudança toca |
| [`../knowledge/`](../knowledge/) | o conhecimento com fonte: **220** URLs vigiadas em `sources.lock.json` |
| [`../rules/catalog/`](../rules/catalog/) | as **140** regras, cada uma com fonte, validação e rollback |
| [`../knowledge/devin/agents-and-subagents.md`](../knowledge/devin/agents-and-subagents.md) | o que este repositório **mediu** sobre o próprio Devin, com dez veredictos e um bloco de vetos |

## O que este diretório deliberadamente não tem

**`.devin/skills/`.** É caminho nativo do Devin, e está vazio de propósito: as
skills moram em `.agents/skills/`, que também é nativo e serve as outras
ferramentas ao mesmo tempo. A decisão está registrada no `STATUS.md`, com o
critério e o gatilho que a inverteria.

**`.devin/agents/`.** Mesma razão — os 38 coordenadores e 5 executores estão em
`.agents/agents/`.

Duplicar qualquer um dos dois criaria duas cópias que divergem no primeiro
commit em que alguém edite só uma.
