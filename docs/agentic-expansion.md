# Agentic Expansion e Offline First

> **Este documento é vivo, e passou a ser conferido (2026-09-20).** Até aqui ele carregava
> um aviso de "registro histórico" e, sob esse aviso, prosa remedida a cada limpeza — as
> duas coisas ao mesmo tempo. Três medidas desempataram: `docs/operations-guide.md`, que é
> documento vivo, manda o leitor para cá como *a arquitetura detalhada*; o AC4 de
> `docs/sdd/CONFIG_OCA/define.md` cobra dele o estado de **hoje**, e histórico se corrige
> com nota de desvio, não com reescrita; e os comandos da seção *Verificação* rodam nesta
> árvore. Agora ele está na tupla `VIVOS` de `tests/test_sf_stubs.py`, que recusa citação
> de nome removido — antes, o AC4 apontava para um teste cego justamente para ele.
>
> O histórico das duas limpezas: a feature `docs/sdd/SF_STUBS/` (2026-09-19) removeu as 35
> áreas `agentic-sf-*`, os 19 agentes `sf-*` que só as declaravam e 10 skills sem artefato;
> `docs/sdd/CONFIG_OCA/` (2026-09-20) removeu as 7 tools declaradas que não existiam e os
> 16 contratos de `subagents/`.

> **Dois pacotes com nome parecido, e eles não são a mesma coisa.** Este
> documento descreve `sparkforge/agents/` — `ConversationRoom`,
> `AutonomyController`, `Supervisor`, `budget`, `model_policy` —, a camada de
> orquestração que existe desde a expansão agêntica. `sparkforge/agentic/`
> (2026-09-03) é OUTRO pacote: entidades de primeira classe (`Claim`,
> `Evidence`, `Decision`), protocolo de debate, arbitragem e blackboard JSONL,
> e ele é **biblioteca sem produtor** — nada no produto escreve nessas
> entidades. Ver `docs/agentic-evolution-report.md`. A sobreposição entre os
> dois (autonomia, budget e observabilidade aparecem nos dois pacotes) é dívida
> conhecida, registrada e não resolvida.


## O que foi criado

Medido nesta árvore em 2026-09-20, os registros declaram **2** agents permanentes
(`sf-security-reviewer` e `sf-lake-formation-specialist`), **1** time cooperativo, e um
bloco `knowledge` de **8** entradas que não são 8 bases: são **7 documentos `.md` mais o
manifesto de checksums** `knowledge/offline-manifest.json`, que lista, ele próprio, **56**
documentos locais. Contar o manifesto como base é somar o índice ao acervo. Os blocos
`tools` e `subagents` saíram inteiros: **0** ferramentas e **0** subagents declarados —
nenhuma das sete tools existia em `sparkforge.adapters.tools.TOOLS`, e os dezesseis
contratos de `subagents/` não tinham leitor em `sparkforge/`, `scripts/` nem `tests/`
(feature `docs/sdd/CONFIG_OCA/`). Os registros que restam são
`config/agentic-expansion.yaml` e `config/teams-expansion.yaml`; `config/subagents.yaml`
não existe mais. A frase anterior prometia dez agents, dezesseis subagents, seis
ferramentas, seis knowledge bases e cinco times, e estava defasada desde o SF_STUBS, não
só desde esta mudança. Os seis módulos de `sparkforge/tools/` listados abaixo continuam
existindo — eles são código, não nome declarado em registro.

## Garantia sem internet

O computador executor pode estar sem DNS, HTTP, SDK cloud ou acesso ao provedor de documentacao. Os agents consultam primeiro `knowledge/offline-manifest.json`, verificam checksums e fazem busca local. Nenhuma ferramenta offline usa requests, socket, DNS ou fallback silencioso. Se um fato depender de fonte ausente, o resultado deve ser `unresolved`.

## Verificacao

Linux e macOS:
```bash
python -m sparkforge.tools.cli offline verify --repo .
python -m sparkforge.tools.cli offline search "schema streaming governance" --repo .
```

Windows PowerShell:
```powershell
python -m sparkforge.tools.cli offline verify --repo .
python -m sparkforge.tools.cli offline search "schema streaming governance" --repo .
```

O comando `offline verify` valida o SHA-256 de cada arquivo listado no manifesto. O comando `offline search` retorna somente caminhos locais, score, excerpt e a marca `offline: true`.

## Ferramentas novas

- `sparkforge/tools/context.py`: deduplicacao e selecao de contexto por kind.
- `sparkforge/tools/cost.py`: estimativa local de tokens, sempre marcada como estimativa.
- `sparkforge/tools/schema.py`: comparacao de campos, tipos, required e compatibilidade.
- `sparkforge/tools/lineage.py`: extracao deterministica de edges em texto e SQL.
- `sparkforge/tools/evaluation.py`: comparacao de golden cases e findings.
- `sparkforge/tools/offline.py`: busca local e verificacao de manifesto.
- `sparkforge/tools/cli.py`: interface `sparkforge-tools offline`, `cost` e `lineage`.

## Ordem de cooperacao

A ordem que este documento prescrevia — seis passos por dez contratos efêmeros de
`subagents/` — **não existe mais**, e não foi substituída por outra igual: os 16 contratos
saíram porque nenhum módulo de `sparkforge/`, `scripts/` ou `tests/` os lia, e o registro
declara hoje **0** subagents.

A ordem que **existe**, medida nesta árvore em 2026-09-20, é o laço de executores, e ela
não é efêmera — é arquivo de contrato:

`sf-inventory` → `sf-extractor` → `sf-judge` → `sf-verifier` → `sf-synthesizer`

São **5** contratos em `agents/executors/`, e **12** agentes de `agents/` os declaram no
campo `executors:` do frontmatter. Cada um faz **uma** função do laço e devolve ao
coordenador; quem manda em todos é `AGENT_PROTOCOL.md`. O inventário é o único que pode
começar do zero, e o que falta coletar sai em `case.open_questions` com o comando de
recoleta — nunca como afirmação sem artefato.

## Times

| Time | Coordenador | Membros | Handoffs |
| --- | --- | --- | --- |
| `governance-security` | `sf-security-reviewer` | `sf-lake-formation-specialist` | — |

**1** time, lido de `config/teams-expansion.yaml` pelo `CanonicalRegistry`. A tabela
anterior listava cinco, quatro deles coordenados por agentes que o SF_STUBS removeu. A
coluna `Handoffs` está vazia de propósito: os três nomes que havia apontavam para
contratos apagados, e `handoffs` ausente vira lista vazia em
`sparkforge/registry/loader.py` — chave vazia seria convite a reencher sem critério.

## Limites

A ausencia de internet permite usar conhecimento local, mas nao atualiza fontes externas. Para atualizar, execute uma sincronizacao em computador conectado, regenere o manifesto, revise o diff e distribua o pacote novamente. Nao transforme uma pagina web antiga ou um checksum ausente em recomendacao afirmativa.
