# SparkForge AWS — Auditoria de lastro do vNext (`docs/vnext/`)

**Data:** 2026-08-21
**Status:** **proposto**. Nada implementado nesta data.
**Motivação:** o commit `a5b9e96` (`feat(vnext): implement AWS Data Platform
Engineering Agent Factory vNext focus on glue`) publicou 17 documentos em
`docs/vnext/` afirmando capacidades e KPIs. Este documento desenha como separar,
nesses 17 arquivos, o que tem artefato do que é alegação.
**Base:** `tests/test_docs_coverage.py` fixou o padrão de derivar a realidade em vez
de conferir lista copiada; `scripts/sync_skills.py --check` fixou o padrão de script
executável com modo de verificação plugável em CI; `knowledge/sources.lock.json`
fixou o padrão de lock file de fontes.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o relatório afirma, o repositório não prova

`a5b9e96` acrescentou 140 arquivos, 5731 linhas. Parte é código real — os
compiladores de plataforma em `sparkforge/adapters/` somam 7813 linhas e têm gate de
paridade que roda. Parte é esqueleto: `sparkforge/migration` tem 150 linhas,
`lakeformation` 218, `iceberg` 179, `errors` 77, `databases` 127, `streaming` 116,
`terraform` 144. Cada um desses módulos ganhou um teste, entre 17 e 58 linhas.

`docs/vnext/FINAL-REPORT.md` §3 declara uma tabela de KPIs: *Task Success Rate 100%*,
*Median Tokens / Specialist Task -78,8%*, *Estimated Cost / 1k Tasks -81,8%*,
*Cache Hit Rate 94,5%*, *Test Suite Coverage 5.485+ testes*. Nenhum artefato de
medição foi commitado junto. Não existe no repositório um comando que produza
qualquer um desses cinco números.

O quinto é verificável e diverge: `docs/superpowers/STATUS.md`, atualizado em
2026-08-18 e declarado ali mesmo como fonte da verdade sobre onde o projeto está,
diz **5447** testes passando e não menciona o vNext em lugar nenhum. `FINAL-REPORT`
diz **5485+**. Uma das duas está errada e nada no repositório decide qual.

A contaminação está contida. Medido por busca literal: `README.md`, `AGENTS.md`,
`GUIA_DE_USO.md` e `STATUS.md` têm **zero** ocorrências de `vNext`/`vnext`. As
alegações não vazaram para fora de `docs/vnext/`.

O volume a auditar, medido: 17 arquivos (9 em `docs/vnext/`, 8 ADRs em
`docs/vnext/adrs/`), com cerca de 85 ocorrências numéricas, concentradas em
`FINAL-REPORT.md` (23), `CURRENT-STATE.md` (20), `CURRENT-STATE-AUDIT.md` (12),
`DEMOS.md` (8) e `IMPLEMENTATION-REPORT.md` (6). Esse número inclui ruído — datas,
identificadores de ADR, versões — que a §5 trata.

## 2. Objetivo

Para cada alegação dos 17 documentos, registrar em manifesto versionado qual artefato
a prova, ou que nenhum a prova. Corrigir os documentos conforme o resultado. Ligar um
gate que impeça a reintrodução de alegação sem lastro.

O critério aplicado aqui é o mesmo que o repositório já aplica a regra de diagnóstico:
capacidade com artefato entra; julgamento sem mecanismo não entra disfarçado de fato.

### Não-objetivos, com razão registrada

- **Construir o motor de medição de token, custo e cache.** É o que tornaria os KPIs
  de economia mensuráveis, e é projeto próprio. Aqui, KPI sem medição sai do
  documento; não ganha instrumentação de improviso.
- **Auditar `README.md`, `AGENTS.md`, `GUIA_DE_USO.md`.** Medido: não contêm alegação
  vNext. Auditar o que não está sob suspeita gasta e não decide nada.
- **Auditar o comportamento dos módulos de domínio.** Saber se
  `sparkforge/lakeformation` faz o que `ARCHITECTURE.md` diz é auditoria funcional,
  outro projeto. Aqui a pergunta é se a afirmação tem artefato apontado, não se o
  artefato está correto.
- **Cobrir as 132 seções do prompt mestre da vNext** (documento de entrada, local, não versionado neste repositório).** Matriz de conformidade é outro projeto,
  e depende deste para não herdar números falsos.
- **Construir qualquer capacidade nova pedida pelo prompt mestre da vNext.**

## 3. Decisões de desenho

### D-1 — manifesto separado, não anotação inline

A alegação e sua prova vivem em `docs/vnext/claims.lock.json`, não em marcador dentro
do parágrafo. A alternativa inline lê melhor para humano, mas o que precisa ser
detectado é justamente a alegação **não anotada** — e para detectá-la é preciso o
mesmo extrator do manifesto. Inline seria este desenho com armazenamento pior e prosa
poluída.

### D-2 — a prova é tipada, e o tipo restringe o que ela pode provar

Três espécies de prova:

- `command` — comando reexecutável que produz o número, com valor esperado.
- `artifact` — caminho de arquivo, símbolo opcional e teste que o exercita.
- `source` — identificador de fonte oficial já vigiada em `knowledge/sources.lock.json`.

E duas restrições que são a razão de existir do tipo:

- `artifact` é **inválido** para `type: number`. Apontar `sparkforge/economy/cache.py`
  não prova `94,5% de cache hit`. Sem essa restrição o manifesto aceita gesto no lugar
  de prova, que é exatamente o defeito que ele existe para pegar.
- `source` é o **único** aceito para `type: external_fact`. Versão de Glue e feature de
  spec Iceberg se provam por documentação oficial versionada, mecanismo que o
  repositório já opera com 131 fontes vigiadas.

### D-3 — `tier` na prova `command` é requisito, não conveniência

Medido nesta sessão: `python -m pytest -q` ultrapassou 600 s. Um gate que reexecuta a
suíte inteira para conferir a contagem de testes é um gate que ninguém roda, e gate que
ninguém roda não guarda nada. Cada prova `command` declara `tier: fast` ou
`tier: slow`; o gate padrão roda só `fast`, e `slow` fica em job próprio de CI.

### D-4 — fail-closed nos dois sentidos

Alegação no documento sem entrada no manifesto falha o gate. Entrada no manifesto sem
correspondência no documento **também** falha. A segunda metade não é simetria
estética: sem ela o manifesto envelhece calado quando alguém edita a prosa, que é o
defeito que `tests/test_docs_coverage.py` já combate no comentário de `_cli_verbs`.

### D-5 — `REMOVIDA` conserva o rastro

Alegação sem prova construível barato sai do documento e permanece no manifesto com
`state: REMOVIDA` e motivo. Apagar sem registro perde o que foi alegado e por quê, e é
justamente esse histórico que permite, quando o motor de medição existir, reabrir cada
item e provar ou enterrar.

### D-6 — o documento de auditoria é gerado, não escrito

`--report` emite a tabela de lastro em Markdown a partir do manifesto. Relatório
escrito à mão diverge do manifesto na primeira edição, e aí passam a existir duas
verdades sobre o que foi provado.

## 4. `docs/vnext/claims.lock.json`

Uma entrada por alegação:

| campo | conteúdo |
|---|---|
| `id` | `VNX-001`, estável e nunca reciclado |
| `doc` | caminho relativo à raiz |
| `line` | linha na data da extração, informativa |
| `text` | trecho literal alegado |
| `type` | `number`, `capability` ou `external_fact` |
| `proof` | objeto tipado, ver abaixo; ausente quando `state` não é `PROVADA` |
| `state` | `PROVADA`, `SEM_LASTRO` ou `REMOVIDA` |
| `note` | obrigatória quando `state` é `SEM_LASTRO` ou `REMOVIDA` |

Formas de `proof`:

```json
{ "kind": "command",  "cmd": "...", "expect": {}, "tier": "fast" }
{ "kind": "artifact", "path": "...", "symbol": "...", "test": "..." }
{ "kind": "source",   "source_id": "..." }
```

O arquivo carrega `schema_version` e o commit de extração. `schema_version` começa em
`1` e só sobe quando um leitor existente deixar de conseguir ler o arquivo.

## 5. Extrator e detecção

`scripts/check_vnext_claims.py`, no mesmo formato de `scripts/sync_skills.py`: script
executável, modo de verificação, teste que o chama, CI que pluga o script.

Detecção numérica por varredura dos 17 arquivos, com allowlist auditável que ignora
datas ISO, identificadores `ADR-NNN`, versões semânticas, conteúdo de bloco de código e
números dentro de citação de fonte. A allowlist mora no próprio script, é lida pelo
teste, e cada padrão dela carrega comentário com a razão — allowlist sem razão
registrada vira depósito de exceção conveniente.

Alegação de `capability` não é detectável por varredura de texto com precisão útil. Ela
é enumerada a partir da estrutura: cada linha de tabela de `CAPABILITY-MATRIX.md` e de
`AGENT-CATALOG.md`, e cada item da lista de inventário do `FINAL-REPORT.md` §4. O
extrator lê essas três estruturas; prosa livre não gera entrada de `capability`.

## 6. Superfície

`python scripts/check_vnext_claims.py`

| modo | o que faz |
|---|---|
| sem flag | audita e imprime divergências; sai 1 se houver |
| `--fast` | schema, órfãos nos dois sentidos, existência de `path`, `symbol` e `test`, existência de `source_id`, e reexecução das provas `tier: fast` |
| `--full` | acrescenta as provas `tier: slow` |
| `--report` | emite a tabela de lastro em Markdown |
| `--seed` | gera manifesto semente com toda alegação em `SEM_LASTRO`, para a classificação inicial |

Falha sempre nominal, com o identificador e os dois valores:
`VNX-014: prova command não reproduz — esperado 5485, obtido 5447`.

## 7. Fluxo da auditoria

1. `--seed` produz o manifesto com todas as alegações em `SEM_LASTRO`.
2. Classificação item a item, com três destinos e nenhum limbo:
   - prova já existe, então `PROVADA`;
   - prova é derivável barato — contagem de testes, agentes, skills, tools, regras,
     fixtures — então escrever o derivador como `command tier: fast` e provar;
   - prova exigiria o motor de medição, então `REMOVIDA`, e o texto sai do documento.
3. Correção dos documentos conforme a classificação.
4. Seção da fase vNext no `STATUS.md`, com os números vindos dos derivadores do
   manifesto, nunca copiados do `FINAL-REPORT.md`.
5. Gate ligado no CI.

Hipótese registrada como hipótese, não como conclusão: os cinco KPIs de `FINAL-REPORT`
§3 caem em `REMOVIDA`, porque `a5b9e96` não trouxe artefato de medição. A auditoria
confirma ou desmente; este documento não decide por ela.

## 8. Testes

- Extrator contra documento sintético: número detectado; número coberto pela allowlist
  ignorado; alegação órfã detectada; entrada órfã do manifesto detectada.
- `artifact` rejeitado para `type: number`.
- `source` rejeitado quando `source_id` não existe em `knowledge/sources.lock.json`.
- `--fast` não executa nenhuma prova `tier: slow`, provado por manifesto de teste com
  uma prova `slow` cujo comando falharia se executado.
- `note` obrigatória em `SEM_LASTRO` e `REMOVIDA`.
- Gate verde sobre o manifesto final.

## 9. Em aberto para a implementação decidir

- Se `line` deve ser reconferida pelo gate ou permanecer informativa. Reconferir torna
  o manifesto ruidoso a cada edição de prosa; ignorar deixa o campo apodrecer. A
  implementação mede o custo das duas e escolhe.
- Formato de `expect` na prova `command`: valor exato, expressão regular, ou extração
  numérica com tolerância. A escolha depende de quantas provas `fast` produzem saída
  estável, o que é desconhecido antes de escrever os derivadores.
- Se os oito ADRs entram na mesma varredura dos nove documentos ou ganham tratamento
  próprio. ADR registra decisão numa data, e alegação dentro de ADR pode ser
  legitimamente histórica.

## 10. Critérios de conclusão

1. `docs/vnext/claims.lock.json` existe, cobre os 17 arquivos, e toda entrada tem
   `state` e — quando `PROVADA` — `proof` válida.
2. Nenhuma entrada em `SEM_LASTRO` ao fim: cada uma virou `PROVADA` ou `REMOVIDA`.
3. `python scripts/check_vnext_claims.py --fast` sai 0.
4. Os documentos de `docs/vnext/` não contêm alegação ausente do manifesto.
5. `STATUS.md` tem a seção da fase vNext, com números derivados por comando declarado
   no manifesto.
6. O gate roda no CI e falha quando uma alegação é reintroduzida sem prova, provado por
   teste que injeta a alegação e observa a falha.
7. A suíte completa continua passando.
