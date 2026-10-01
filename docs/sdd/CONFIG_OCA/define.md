---
sdd: 1
feature: CONFIG_OCA
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/CONFIG_OCA/explore.md
  sha256: "054d05b6cfd23ebab80ad7fe8a9aa3afcb4d11619da527863e2f5d4176aaac26"
hypothesis:
  claim: "O que sobrou de oco nos registros de config/ pode sair sem quebrar nada, porque NENHUM codigo de producao os le: as sete tools declaradas nao existem em TOOLS, os dezesseis contratos de subagents sao byte-identicos abaixo de ## Contract e ninguem os despacha, e um gate novo impede que nome sem lastro volte a entrar."
  prediction: "Depois da mudanca: nenhum nome do bloco tools de config/agentic-expansion.yaml deixa de resolver em sparkforge.adapters.tools.TOOLS, porque o bloco sai inteiro; config/subagents.yaml e subagents/ saem, e nenhum teste, script ou modulo quebra, porque a varredura mediu zero leitores; os documentos que prometiam as ferramentas e os subagents passam a dizer o que ha; e o gate novo fica VERMELHO se qualquer um deles for reintroduzido sem existir. Se algum teste quebrar, se algum leitor de producao aparecer, ou se o gate passar com um nome inventado, a afirmacao esta errada."
  experiment: "Rodar o gate novo sobre a arvore antes e depois, os lotes de teste que tocam registro e agente, e python -m pytest tests/test_fixtures_golden*.py -q sem regenerar."
acceptance:
  - id: AC1
    statement: "O bloco tools de config/agentic-expansion.yaml nao declara nenhum nome ausente de sparkforge.adapters.tools.TOOLS. As sete que nao existiam sairam."
    verified_by: {kind: test, ref: "tests/test_config_declarado_existe.py::test_toda_tool_declarada_existe"}
  - id: AC2
    statement: "Todo nome declarado nos registros de config/ aponta para algo que existe: agente para arquivo em agents/, documento de knowledge para arquivo, tool para entrada em TOOLS. O gate percorre os registros e falha nomeando o registro, a chave e o nome que nao resolve."
    verified_by: {kind: test, ref: "tests/test_config_declarado_existe.py::test_todo_nome_declarado_resolve"}
  - id: AC3
    statement: "config/subagents.yaml e o diretorio subagents/ sairam, e nenhum teste, script ou modulo de producao quebra: a varredura de sparkforge/, scripts/ e tests/ media zero leitores."
    verified_by: {kind: test, ref: "tests/test_config_declarado_existe.py::test_o_registro_de_subagents_saiu_e_ninguem_o_le"}
  - id: AC4
    statement: "Os documentos que prometiam as ferramentas e os subagents passam a dizer o que ha: docs/agentic-expansion.md nao promete mais 'seis ferramentas locais deterministicas' nem dezesseis subagents, e nenhum documento vivo cita nome que saiu."
    verified_by: {kind: test, ref: "tests/test_sf_stubs.py::test_documento_vivo_nao_cita_o_que_saiu"}
  - id: AC5
    statement: "Os registros que a remocao move estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Nomes declarados em config/ que nao resolvem, antes e depois"
    source: "tests/test_config_declarado_existe.py sobre a arvore"
  - id: SC2
    metric: "Goldens que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
  - id: SC3
    metric: "Arquivos e bytes removidos"
    source: "git diff --stat"
out_of_scope:
  - "Implementar qualquer uma das sete tools declaradas: nenhuma tem artefato coletavel definido nem demanda medida, e construir porque o nome esta escrito inverte o criterio de dominio."
  - "Os blocos agents e knowledge de config/agentic-expansion.yaml: medidos integros, 2 de 2 e 8 de 8."
  - "config/teams-expansion.yaml, que o registry/loader.py LE e que o SF_STUBS ja tratou."
  - "Reescrever docs/delivery-report.md e outros documentos HISTORICOS que citam a expansao: eles registram o que foi entregue na epoca."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "A varredura mediu zero leitores de config/subagents.yaml e de subagents/ em sparkforge/, scripts/ e tests/, e os 16 contratos sao byte-identicos abaixo de ## Contract -- a mesma forma dos agentes sf-* que o SF_STUBS removeu. O que a medida NAO alcanca e um consumidor fora do repositorio: um host que leia os contratos por conta propria. Destrava: confirmacao do operador de que nao ha, ou um grep no host."
change_kinds: [agent_or_skill, status_numbers, claims]
---

# CONFIG_OCA — requisitos

## Problema

`config/agentic-expansion.yaml` declara quatro blocos de nomes. Medidos nesta árvore:

| bloco | declarado | existe |
|---|---|---|
| `agents` | 2 | **2** |
| `knowledge` | 8 | **8** |
| `subagents` | 16 | 16 contratos, **byte-idênticos** abaixo de `## Contract` |
| `tools` | 7 | **0** |

O defeito não é uniforme, e é por isso que o `out_of_scope` protege os dois blocos que
estão de pé. O que sai é o que não tem lastro.

## As duas medidas que decidem

**Nenhum código de produção lê o registro.** `sparkforge/registry/loader.py` lê
`config/agents.yaml` e `config/teams-expansion.yaml`; `config/agentic-expansion.yaml`
aparece só em `tests/test_sf_stubs.py`, na lista de documentos vivos que não podem citar o
que saiu. Remover um bloco dele não quebra caminho de execução nenhum.

**Os 16 subagents são stubs, não contratos.** Os arquivos existem — 16 de 16 —, mas:

- o corpo abaixo de `## Contract` é **idêntico nos dezesseis**, e a descrição de cada um é
  o próprio nome com o hífen trocado por espaço ("intake packager");
- `skills/` e `agents/` são lidos por vários módulos Python; `config/subagents.yaml` e
  `subagents/*.md` têm **zero** referências em `sparkforge/`, `scripts/` e `tests/`;
- fora de `docs/agentic-expansion.md`, nenhuma skill, agente ou espelho os cita.

É a mesma forma dos 19 agentes `sf-*` que o `SF_STUBS` removeu, na camada que aquela
feature não varreu.

## O que esta feature acrescenta ao que o SF_STUBS fez

O SF_STUBS limpou e esta camada voltou a ser encontrada dois incrementos depois, porque
**nada impedia**. O AC2 é a diferença: um gate que percorre os registros de `config/` e
falha nomeando o registro, a chave e o nome que não resolve. Sem ele, a próxima limpeza
encontra a próxima camada.

## Critérios

- AC1 e AC3 são a remoção, cada uma com a sua medida.
- AC2 é a trava, e é o que esta feature tem de deixar para trás.
- AC4 é a prosa que prometia o que não havia.
- AC5 são os registros.
