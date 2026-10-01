---
sdd: 1
feature: CONFIG_OCA
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/CONFIG_OCA/define.md
  sha256: "8e5f533e27c224d38381d14d67f1eb70ebbb57dbafb43e81012955e445867433"
files:
  - {path: tests/test_config_declarado_existe.py, action: create, reason: "o gate do AC2 mais os testes de AC1 e AC3. O de AC1 falha ANTES da remocao, e e esse o vermelho da feature"}
  - {path: config/agentic-expansion.yaml, action: modify, reason: "o bloco tools sai inteiro (7 de 7 inexistentes) e o bloco subagents sai inteiro; agents e knowledge ficam, medidos integros"}
  - {path: config/subagents.yaml, action: delete, reason: "registro de 16 stubs que nenhum codigo de producao le"}
  - {path: subagents/intake-packager.md, action: delete, reason: "representante dos 16 contratos, todos byte-identicos abaixo de ## Contract; o diretorio subagents/ sai inteiro"}
  - {path: tests/test_sf_stubs.py, action: modify, reason: "os nomes que saem entram nas tuplas literais que o test_documento_vivo_nao_cita_o_que_saiu ja percorre: e o mecanismo que o SF_STUBS criou para exatamente isto"}
  - {path: docs/agentic-expansion.md, action: modify, reason: "AC4: ele promete 'seis ferramentas locais deterministicas' e dezesseis subagents, e e o unico documento fora de config/ que cita os nomes"}
  - {path: docs/operations-guide.md, action: modify, reason: "AC4: ele conta os subagents efemeros e os modulos de ferramentas locais na descricao da segunda onda"}
  - {path: docs/claims.lock.json, action: modify, reason: "a remocao muda a contagem e os bytes do corpus; as alegacoes que cairem saem na lista de ids do gate de lastro"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "os numeros auditados que as mesmas alegacoes publicam. Se o gate nao listar nenhuma, nao se toca"}
decisions:
  - id: D1
    choice: "O gate do AC2 percorre um MAPA declarado no proprio teste -- registro, chave, e como resolver aquele tipo de nome (agente vira arquivo em agents/, knowledge vira caminho, tool vira chave de TOOLS). A falha nomeia os tres: registro, chave e nome."
    rejected:
      - "Varrer todo YAML de config/ e adivinhar quais strings sao nomes a resolver: produz falso positivo em campo de politica (`forbidden_by_default`) e vira teste que se desliga sozinho com excecoes."
      - "Conferir so `config/agentic-expansion.yaml`: resolveria hoje e deixaria o proximo registro sem trava, que e exatamente como esta camada sobreviveu ao SF_STUBS."
    rollback: "git revert do commit do gate; nada mais depende dele."
  - id: D2
    choice: "As sete tools saem removendo o BLOCO `tools` inteiro, nao item a item: zero das sete existem, entao nao sobra nada a declarar."
    rejected: ["Deixar `tools: []`: chave vazia e convite a reencher sem criterio, e o gate do AC2 nao distingue vazio de ausente."]
    rollback: "git revert; o bloco volta com os sete nomes."
  - id: D3
    choice: "Os subagents saem inteiros: `config/subagents.yaml` e o diretorio `subagents/` com os 16 contratos. A medida que sustenta: zero leitores em `sparkforge/`, `scripts/` e `tests/`, corpo identico nos dezesseis, e citacao so em `docs/agentic-expansion.md`."
    rejected:
      - "Remover so o registro e manter os 16 contratos: arquivo sem registro e sem leitor e a mesma oca, um nivel abaixo."
      - "Manter tudo e marcar `status: planned`: rotulo sem leitor nao muda nada, e sem demanda medida 'planejado' e indistinguivel de abandonado (abordagem C do explore)."
    rollback: "git revert do commit da remocao; os 17 arquivos voltam byte a byte. A lacuna U1 do define -- um consumidor fora do repositorio -- e o que este rollback existe para cobrir."
  - id: D4
    choice: "Os nomes removidos entram nas tuplas literais de `tests/test_sf_stubs.py`, que o `test_documento_vivo_nao_cita_o_que_saiu` ja percorre. Nenhum mecanismo novo."
    rejected: ["Criar um segundo teste de 'documento vivo' no arquivo novo: dois mecanismos para a mesma regra divergem, e o do SF_STUBS ja tem a lista de documentos vivos curada."]
    rollback: "git revert; as tuplas voltam ao tamanho anterior."
covers:
  - {part: "o gate do declarado", acceptance: [AC2]}
  - {part: "as sete tools", acceptance: [AC1]}
  - {part: "os dezesseis subagents", acceptance: [AC3]}
  - {part: "a prosa que prometia", acceptance: [AC4]}
  - {part: "registros", acceptance: [AC5]}
---

# CONFIG_OCA — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| o gate do declarado | `tests/test_config_declarado_existe.py` | AC2 |
| as sete tools | `config/agentic-expansion.yaml` | AC1 |
| os dezesseis subagents | `config/subagents.yaml`, `subagents/` | AC3 |
| a prosa que prometia | `docs/agentic-expansion.md`, `docs/operations-guide.md`, `tests/test_sf_stubs.py` | AC4 |
| registros | `docs/claims.lock.json`, `docs/harness/CODEINTEL-GAP.md` | AC5 |

## O vermelho desta feature

Diferente da refatoração anterior, aqui **existe vermelho natural**: o teste do AC1 afirma
que nenhum nome do bloco `tools` falta de `TOOLS`, e hoje **os sete faltam**. Ele falha
antes da remoção, por asserção e não por coleta.

O gate do AC2 também nasce vermelho, pelo mesmo motivo, e fica verde com a remoção. É o
teste que sobrevive à feature: ele não afirma que os sete saíram, afirma que **nada
declarado deixa de resolver** — e por isso continua valendo para o registro seguinte.

## O que o rollback do D3 cobre

A lacuna U1 do define diz que a varredura mediu zero leitores **dentro do repositório**, e
que um consumidor fora dele não é alcançável por medida daqui. O `git revert` do commit da
remoção devolve os 17 arquivos byte a byte, e é essa a rede. A remoção é reversível; a
afirmação de que ninguém os lê é que não é completa, e está declarada como lacuna.

## Conhecimento consultado

Medido nesta árvore em 2026-09-20, com `main` em `e4141869`:

- `sparkforge/registry/loader.py` lê `config/agents.yaml` e `config/teams-expansion.yaml`;
  `config/agentic-expansion.yaml` não aparece em nenhum módulo de produção.
- `config/agents.yaml` traz `expansion_registry: config/agentic-expansion.yaml`, que é
  ponteiro declarado e não leitura.
- Os 16 arquivos de `subagents/` têm corpo idêntico abaixo de `## Contract`; a descrição de
  cada um é o nome com o hífen trocado por espaço.
- `tests/test_sf_stubs.py` mantém `OCOS` e `SKILLS_QUE_SAIRAM` como tuplas literais e uma
  lista `VIVOS` de documentos — o mecanismo que o D4 reusa.
