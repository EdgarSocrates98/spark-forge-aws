---
sdd: 1
feature: CONFIG_OCA
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/CONFIG_OCA/plan.md
  sha256: "14cec5d12d272973a6523a713dc17ad4e3f6562eaa039be95423dacfe11e86f4"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_config_declarado_existe.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_config_declarado_existe.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_config_declarado_existe.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_config_declarado_existe.py -q", exit: 0}
claims:
  - text: "O bloco tools de config/agentic-expansion.yaml saiu inteiro, e as sete que nao existiam nao voltam por nome: a asercao e sobre o texto do registro, nao sobre a chave, entao ela nao passa por ausencia."
    evidence_ref: "tests/test_config_declarado_existe.py::test_toda_tool_declarada_existe"
  - text: "Todo nome declarado nos registros de config/ resolve: agente para arquivo em agents/, documento de knowledge para caminho, tool para entrada em TOOLS. A falha nomeia registro, chave e nome."
    evidence_ref: "tests/test_config_declarado_existe.py::test_todo_nome_declarado_resolve"
  - text: "config/subagents.yaml e o diretorio subagents/ sairam, e nenhum modulo de sparkforge/, scripts/ ou tests/ passou a cita-los."
    evidence_ref: "tests/test_config_declarado_existe.py::test_o_registro_de_subagents_saiu_e_ninguem_o_le"
  - text: "Nenhum documento vivo cita nome que saiu: o mecanismo que o SF_STUBS criou percorre agora tambem as tools e os subagents removidos."
    evidence_ref: "tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu"
  - text: "O registro canonico continua carregando com o time governance-security sem handoffs: medido carregando CanonicalRegistry e lendo o time, nao por leitura do codigo."
    evidence_ref: "sparkforge/registry/loader.py"
  - text: "Os registros que a remocao move estao em dia: o gate de lastro fecha em 0 divergencias com a arvore no estado final."
    evidence_ref: "docs/claims.lock.json"
---

# CONFIG_OCA — relatório do build

## As duas tarefas

| tarefa | commit | o que entregou |
|---|---|---|
| T1 | `d775888d` | o gate do declarado, e as sete tools inexistentes fora do registro |
| T2 | `e157c6a5` | os 17 arquivos de subagents removidos, a prosa e os registros |

A separação era deliberada: o `git revert` da T2 sozinha devolve os 17 arquivos **sem**
levar a trava da T1 junto. É a rede da lacuna U1.

## O vermelho de cada uma

**T1** falhou com `2 failed`, as duas por **asserção**, não por coleta. O
`test_todo_nome_declarado_resolve` listou **exatamente sete linhas**, todas da chave
`tools` — nenhuma de `agents`, nenhuma de `knowledge`. A medida que o explore tinha feito à
mão (2 de 2 e 8 de 8 íntegros) confirmou-se sozinha na execução do próprio gate, que é
prova melhor que a varredura que a produziu.

**T2** falhou na primeira asserção do teste novo: `config/subagents.yaml` ainda existia.

## O que a T2 encontrou além do manifesto

**Quatro arquivos fora do `files:` do design**, todos referências ao que estava sendo
removido:

- `config/agents.yaml` apontava `subagents_registry` para o arquivo apagado;
- `config/teams-expansion.yaml` dava ao time `governance-security` três `handoffs` com
  nomes de contratos apagados;
- `AGENTS.md` e `docs/vnext/CURRENT-STATE.md` listavam os nomes e contavam 16.

O terceiro é o que importa: **`config/teams-expansion.yaml` é lido em produção**, e o
`out_of_scope` do define o excluía justamente por isso. O subagente afirmou que chave
ausente vira lista vazia. **Não aceitei a afirmação**: carreguei o `CanonicalRegistry` e li
o time — `handoffs: []`, carregando normalmente. `loader.py` faz
`t.get("handoffs", [])`.

## A descoberta que muda a leitura da feature

Os sete nomes de tool não eram fantasia completa. **Seis módulos existem em
`sparkforge/tools/`** e correspondem a eles: `context`, `cost`, `evaluation`, `lineage`,
`offline`, `schema`. O que nunca existiu foi a **declaração de tool MCP** — o código está
lá.

Medidos os leitores de cada um, fora do próprio pacote (remedido em 2026-09-20: a linha
`context | 1` dizia "1" sem dizer 1 o quê, e a linha dos outros quatro dizia **0** para
três que têm leitor de teste):

| módulo | importador de produção | importador de teste |
|---|---|---|
| `offline` | `scripts/verify_offline_bundle.py` | `tests/test_offline_expansion.py` |
| `context` | **0** | `tests/test_offline_expansion.py` |
| `evaluation`, `lineage`, `schema` | **0** | `tests/test_offline_expansion.py` |
| `cost` | **0** | **0** |

Três ressalvas que a medida exige:

- as duas ocorrências de `pack_context` em `sparkforge/codeintel/context.py` (linhas 13 e
  259) e a de `tests/test_codeintel_context.py:178` são **prosa de docstring**, não import.
  Citar não é ler;
- `sparkforge/tools/cli.py` importa `cost` e `lineage`, mas é o CLI do próprio pacote —
  fica fora por ser dentro, que é o critério desta tabela;
- `estimate_tokens` aparece em `sparkforge/agents/budget.py`, e é **outra função** com o
  mesmo nome. `budget_report`, a exportada por `tools/cost.py`, não tem nenhuma ocorrência
  no repositório fora da própria definição e do `__all__`.

É uma segunda camada oca, de **código** e não de declaração, e está fora do escopo desta
feature. Vai nomeada no ship.

## Desvios do plano e do design

1. **O manifesto do design estava incompleto**: quatro arquivos, listados acima. Um deles
   (`config/teams-expansion.yaml`) estava explicitamente no `out_of_scope` do define, e
   entrou porque referenciava o que saía — não porque a feature mudou de escopo.
2. **A prosa tinha números errados além dos desta feature.**
   `docs/agentic-expansion.md` prometia "dez agents permanentes" e "seis knowledge bases";
   medidos hoje, **2** e **8**. A linha estava defasada desde o SF_STUBS.
3. **O subagente da T2 travou** esperando o próprio gate de lastro e nunca entregou relato
   — o terceiro da sessão. O trabalho estava no índice; eu o encerrei, inspecionei os
   quatro arquivos fora do manifesto um a um, rodei os testes e o gate, e commitei.
4. **O gate de lastro fechou em 0 divergências _depois_ de remediar quatro alegações.**
   A frase anterior aqui dizia que "a remoção não moveu nenhuma alegação publicada", e era
   falsa: `git diff e4141869..HEAD -- docs/claims.lock.json` mostra quatro, duas pela
   remoção e duas pelo arquivo de teste novo.

   | id | antes | depois | por quê |
   |---|---|---|---|
   | `VNX-054` | `16` | **`0`** | a prova conta `subagents/*.md`, e o diretório saiu; número relido pela própria prova |
   | `VNX-055` | `PROVADA` (`1.800`) | **`REMOVIDA`** | a prova lia `config/subagents.yaml` para o maior `max_tokens` dos 16; sem o registro ela não roda |
   | `VNX-640` | `774` | **`775`** | corpus de `*.py`: `tests/test_config_declarado_existe.py` entrou |
   | `VNX-674` | `242979` | **`243044`** | bytes do mesmo corpus, pelo mesmo arquivo |

   `docs/harness/CODEINTEL-GAP.md` foi editado por causa das duas últimas — é onde esses
   números são publicados.
5. **A revisão em dois estágios por tarefa não rodou.**

## Medidas

| | antes (`e4141869`) | depois |
|---|---|---|
| nomes declarados em `config/` que não resolvem | 7 | **0** |
| contratos em `subagents/` | 16 | 0 |
| arquivos removidos | — | 17 |
| blocos íntegros preservados | `agents` 2, `knowledge` 8 | iguais |

## Rodada de correção (2026-09-20)

A revisão final achou cinco defeitos, e os cinco foram corrigidos **acrescentando**
commits. O que muda a leitura da feature:

1. **O gate cobria um arquivo só** — `config/agentic-expansion.yaml`, exatamente o que o
   D1 rejeita por escrito. Duas provas de que a lacuna era real: `config/agents.yaml`
   declarava `sparkforge_inventory`, ausente das 109 entradas de `TOOLS`; e os três
   `handoffs` que **esta feature** quebrou em `config/teams-expansion.yaml` passaram
   batido. O `MAPA` agora percorre os três registros por caminho aninhado, e uma asserção
   de cobertura varre `config/*.yaml` por glob exigindo veredito para toda chave de
   valor-lista.
2. **`sparkforge_inventory` saiu.** `sf-inventory` é executor real
   (`agents/executors/sf-inventory.md`, declarado por 12 agentes no campo `executors:`), e
   o contrato dele **não cita** essa tool. Era nome sem artefato.
3. **`docs/agentic-expansion.md` era histórico e vivo ao mesmo tempo.** Decidido **vivo**,
   e agora está em `VIVOS` — as 14 citações de nome removido que ele ainda tinha (4
   agentes `sf-*` e 10 contratos de `subagents/`) saíram com as seções que as continham.
   Até aqui o AC4 apontava para um teste cego justamente para ele.
4. **O item 4 dos desvios afirmava o contrário do que o commit fez** — quatro alegações
   moveram. A tabela acima está corrigida com os ids e os valores do diff.
