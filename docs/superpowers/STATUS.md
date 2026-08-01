# SparkForge AWS — estado por fase

**Atualizado em:** 2026-07-31
**Commit de referência:** branch `feat/fase3a-pip`
**Versão do pacote:** `0.5.0` — consistente em `pyproject.toml`, `manifest.json`,
`.claude-plugin/plugin.json` e `sparkforge.__version__`. A concordância entre as
quatro é verificada por
`tests/test_package_importable.py::test_every_manifest_declares_the_same_version`;
nenhum teste fixa o número, porque o que precisa ser garantido é que as quatro
fontes não divirjam, não qual é o valor.

`schema_version` e `catalog_version` continuam em `1`, de propósito: nenhum
contrato de dados mudou e nenhum limiar existente mudou. Subir os três juntos
destruiria a reauditabilidade que a §12.2 da spec da Fase 0 quer — um Finding
gravado com `catalog_version: 2` sugeriria que o limiar que o julgou é outro.

Este arquivo é a fonte da verdade sobre **onde o projeto está**. Os specs e plans
em `specs/` e `plans/` são registro histórico de decisão: descrevem o que se
pretendia numa data, não o repositório de hoje. Quando um número divergir, este
arquivo ganha.

---

## Números correntes

| Dimensão | Valor | Onde conferir |
|---|---|---|
| Testes | **1882** passando, 5 skipped | `python -m pytest -q` |
| Extratores de facts | **13** | `sparkforge/facts/*.py` |
| Fact kinds distintos emitidos | **80** | união de `EMITTED_KINDS` |
| Regras de diagnóstico | **48** | `load_catalog()` |
| Regras bloqueadas (`blocked_on`) | **0** | `rules/catalog/*.yaml` |
| Regras com golden que dispara | **48 de 48** | `tests/test_fixtures_kind_coverage.py` |
| Rotas determinísticas | **16** (`ROUTE-001`…`ROUTE-016`) | `rules/catalog/routing.yaml` |
| Tools MCP | **29** | `sparkforge.adapters.tools.TOOLS` |
| Fixtures golden | **74** em 15 domínios | `fixtures/` |
| Fontes oficiais vigiadas | **20** (16 móveis, 4 fixas) | `knowledge/sources.lock.json` |
| Pares de eval | 10 | `evals/fase0.xml` |

Regras por área: SF-PY 12, SF-UI 6, SF-GLUE 6, SF-ATH 5, SF-ICE 5, SF-PQ 5,
SF-PLAN 4, SF-ENV 4, SF-CG 1.

Fixtures por domínio: `pyspark` 17, `iceberg` 8, `plan` 7, `terraform` 7,
`fusion` 5, `runtime` 5, `s3` 5, `sql` 4, `athena` 3, `catalog` 3, `consumers` 3,
`callgraph` 2, `infra_code` 2, `tfdiff` 2, `eventlog` 1.

---

## Fases

### Fase 0 — contratos, extração determinística e paridade — **CONCLUÍDA** (2026-07-30)

Documentos: [spec](specs/2026-07-29-sparkforge-fase0-design.md) ·
[plan](plans/2026-07-29-sparkforge-fase0.md) · errata na §18 do spec.

Entregou as seis camadas com fronteiras negativas (`facts/`, `rules/`,
`findings/`, `case/`, `collect/`, `adapters/`), o avaliador `expr` com whitelist
de nós AST, os contratos `Fact`/`Finding`/`RuntimeContext` com ordenação
determinística, o `case.yaml` com roteamento por dado, CLI + MCP, o plugin do
Claude Code, `AGENT_PROTOCOL.md`, `parity.yaml` e a suíte de eval.

Faixa de commits: `66fcb6f` … `7d51664`, fechada pelo merge `7cc739e`.

### Fase 1 — extratores restantes e coletores AWS — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-30-sparkforge-fase1-design.md) ·
[plan](plans/2026-07-30-sparkforge-fase1.md).

Doze extratores novos além de `pyspark_ast`, os coletores AWS, a etapa de fusão
de facts, e a superfície de CLI e MCP para cada um. Fecha com uma auditoria
(`bb72f9f`) que corrigiu seis defeitos, incluindo o transporte HTTP do MCP, que
era paridade afirmada e não testada.

Faixa de commits: `97b0818` … `bb72f9f`.

### Fase 2 (executada) — desbloqueio do catálogo — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-31-sparkforge-fase2-design.md) ·
[plan](plans/2026-07-31-sparkforge-fase2.md).

> **Atenção ao nome.** A "Fase 2" que o repositório executou (branch
> `feat/fase2-desbloqueios`) **não** é a Fase 2 do roadmap da §16 do spec da
> Fase 0. O roadmap chama de Fase 2 a expansão do knowledge e o
> `refresh_knowledge`. O que foi executado é o oposto: nenhuma regra nova, e sim
> a construção dos extratores que faltavam para que as regras já committadas
> parem de ser inertes.

Levou o catálogo de 5 regras com `blocked_on` e 3 sem golden positivo para
**0 bloqueadas e 43 de 43 provadas por fixture**, e travou os dois invariantes
que impedem a regressão.

Faixa de commits: `dc80efd` … `b44edd0`, merge `bc53865`.

### Fase 2 do roadmap (§16) — knowledge — **CONCLUÍDA** (2026-07-31)

Distinta da "Fase 2 executada" logo acima, que era desbloqueio de catálogo. Esta
é a que a §16 do spec da Fase 0 chama de Fase 2, e estava aberta até agora:

- **`refresh_knowledge`** — construído, com PR de revisão e sem auto-commit. Ver
  a seção de dívidas fechadas.
- **Matriz de compatibilidade** — as fontes de que ela depende entram na mesma
  watchlist; o guard de drift entre `knowledge/glue/runtime-matrix.md` e
  `GLUE_MATRIX` já existia desde `bb72f9f`.
- **Expansão do catálogo** — SF-PLAN (4 regras sobre plano físico) e SF-CG (1
  sobre grafo de chamadas) cobrem as duas capacidades da Fase 1 que nenhuma
  regra consumia. 43 → 48 regras.

### Fase 3a — distribuição pip — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](specs/2026-07-31-sparkforge-fase3a-pip-design.md) ·
[plan](plans/2026-07-31-sparkforge-fase3a-pip.md).

O defeito de partida: `pip install` entregava só código. O wheel construído
com o backend `setuptools` anterior tinha 43 arquivos e zero de
`rules/catalog/`, `knowledge/` ou `skills/` — `judge`, `next-step`, `resume` e
`rules lookup` morriam num pacote instalado fora do repositório, porque
`loader.catalog_dir()` caía no fallback `sparkforge/rules/catalog/`, que
nunca existiu em disco nem no artefato.

**Decisão central: backend `hatchling` com `force-include`, preservando a
decisão D-A da Fase 0.** `rules/catalog/` e `knowledge/` continuam morando na
raiz do repositório — são o terceiro degrau da escada de portabilidade, o
YAML que um agente sem Python lê direto — e `force-include` os copia para
dentro do pacote **no momento do build**, sem duplicar arquivo em git. Nenhum
código de `loader.catalog_dir()` foi tocado: a ordem de resolução (variável de
ambiente → raiz do repo → fallback no pacote) já estava certa desde a Fase 0;
faltava o arquivo chegar ao fallback.

Um defeito real apareceu no caminho: o sdist não pode carregar o **mesmo**
`force-include` do wheel, porque isso realoca `knowledge/` para dentro de
`sparkforge/` já dentro do tarball, e o wheel construído a partir desse sdist
(o fluxo padrão de `python -m build`, e o que `pip install` usa sem wheel
compatível) procura `knowledge` na raiz e não acha mais. O sdist usa `include`
simples, que preserva os diretórios onde o `force-include` do wheel espera
achá-los. Corrigido no commit `830923e`, exposto pelo gate de paridade desta
mesma fase — ver §4.3 do spec, corrigida nesta rodada de fechamento.

Entregou também: metadata de publicação completa (`readme`, `license`,
`classifiers`, `urls` apontando para `EdgarSocrates98/spark-forge-aws`, não
para a organização inexistente que `plugin.json` citava); o resolvedor de
`knowledge/` a partir do pacote (`sparkforge knowledge path [--file]`, nos dois
adaptadores CLI e MCP); `rules lookup` devolvendo os caminhos de knowledge já
resolvidos; a asserção de procedência que reprova o gate se `sparkforge` for
importado do repositório em vez do `site-packages`; o gate de paridade
(`scripts/verify_wheel.py`) que constrói sdist + wheel, instala em venv limpo
fora do repositório e reproduz as 74 fixtures byte a byte; o job de CI que
roda esse gate em `ubuntu-latest` e `windows-latest`; e `release.yml`, que
constrói, prova, anexa artefatos a um GitHub Release em rascunho e **não
publica** — publicação continua ato manual do mantenedor.

Faixa de commits: `a06d7f5` … `2b6311c`.

### Fase 3b — marketplace de plugin — **NÃO INICIADA**

Escopo da §16: `marketplace.json` e instalação do plugin do Claude Code por
marketplace, em vez de path local. Spec próprio, ainda não escrito.

### Fase 3c — export Devin (Playbook/Knowledge) — **NÃO INICIADA**

Escopo da §16: exportar `skills/` e `knowledge/` para o formato de
Playbook/Knowledge de uma conta Devin. Spec próprio, ainda não escrito.

### Fase 3d — MCP hospedado — **NÃO INICIADA**

Escopo da §16: hospedar o transporte `streamable-http` do MCP em vez de rodar
localmente. Parcial existente: o transporte HTTP já funciona localmente
(`python -m sparkforge.adapters.mcp --transport http`) e é testado desde a
Fase 1. Falta hospedagem. Spec próprio, ainda não escrito.

### Próxima na fila, fora da §16 — cobertura de EMR

`RuntimeContext` (`sparkforge/findings/models.py`) conhece `glue`, `spark`,
`python`, `iceberg` e `athena`, e não conhece `emr` — o dataclass não tem
campo para release label, instance fleets, EMR Serverless nem EMR on EKS.

Isso não paralisa o motor: medido nesta rodada, com um `RuntimeContext` sem a
chave `glue` (só `spark`, `python`, `iceberg`), **44 das 48 regras ainda são
avaliadas** — só as 4 que declaram `runtime_scope` com `glue` são puladas
(`SF-ENV-002`, `SF-ENV-003`, `SF-ENV-004`, `SF-GLUE-001`). A análise de código
e execução (`SF-PY`, `SF-UI`, `SF-ATH`, `SF-ICE`, `SF-PQ`, `SF-PLAN`, `SF-CG`)
é agnóstica de plataforma por construção — ela julga o job, não o serviço que
o hospeda.

O que falta é o eixo de infraestrutura que só existe hoje para Glue: release
label do EMR, instance fleets vs. instance groups, EMR Serverless (worker
config, pre-init capacity), EMR on EKS, e uma área `SF-EMR` própria no
catálogo para as regras que dependem desses fatos. Fase própria, ainda sem
spec.

### Fase 4 — rigor — **NÃO INICIADA**

Escopo da §16: gates fail-closed opcionais, benchmark automatizado antes/depois,
validação funcional automatizada (contagem, schema, chaves, agregados),
assinatura de relatório. `blocked_by` segue advisory, como a §5.5 da Fase 0
decidiu conscientemente.

---

## Dívidas — fechadas em 2026-07-31

As cinco dívidas listadas na versão anterior deste arquivo foram tratadas. Duas
delas **estavam mal enunciadas por mim**, e a correção está registrada aqui em
vez de apagada: um inventário de dívidas que só cresce e nunca se corrige vale
tão pouco quanto um que nunca se atualiza.

| Dívida (como estava escrita) | Desfecho |
|---|---|
| `refresh_knowledge` não existe | **Construído.** `scripts/refresh_knowledge.py` + workflow manual/semanal que abre PR e nunca commita em main |
| Matriz de compatibilidade não é automatizada | **Coberta pelo mesmo mecanismo.** As URLs de que a matriz depende estão na watchlist; mudança nelas vira PR de releitura |
| Três eixos de versionamento parados em 1/1/0.4.0 | **Resolvida com uma decisão, não com três bumps.** Pacote em `0.5.0`; `schema_version` e `catalog_version` ficam em 1 porque nada que eles versionam mudou |
| Catálogo cobre 7 áreas, não as 18 skills | **Enunciado errado.** 15 das 18 skills já citavam regra. O gap real era *capacidade sem regra*, não *skill sem regra*: `plan.*` e `callgraph.*`. Fechado com SF-PLAN (4 regras) e SF-CG (1) |
| Glue 3.0 na `GLUE_MATRIX` sem cobertura de fixture própria | **Falso.** `fixtures/runtime/pre_aqe_runtime/` é a fixture de Glue 3.0, e nela o 3.0 é o lado **positivo** de SF-ENV-004 — quem é o lado negativo é o Glue 4.0. A exclusão do 3.0 de `CURRENT` é deliberada e já documentada em `tests/test_runtime_glue_versions.py:31-33` |

### `refresh_knowledge` — o que ele faz e o que recusa fazer

Não baixa o texto das docs para o repositório. Guarda, em
`knowledge/sources.lock.json`, o hash do texto normalizado de cada fonte, a data
da conferência e **quais `rule_id` citam aquela URL**. O relatório não diz "a doc
mudou assim"; diz "a doc mudou, e as regras X e Y dependem dela — releia".

Três razões, na ordem em que pesam: o diff de uma página da AWS é quase todo
ruído de navegação, e relatório que grita sempre treina o operador a ignorá-lo;
copiar doc de terceiro para o repo é decisão de licenciamento que ninguém tomou;
e o objetivo nunca foi ter a doc, foi saber quando relê-la.

A watchlist é derivada do próprio catálogo — é o conjunto de `sources[].url`.
Regra nova com fonte nova entra sozinha; lista paralela é o passo que alguém
esquece. Fontes com versão no path (`docs/3.5.6/`, `apache-iceberg-1.0.0`) não
são buscadas: o conteúdo é imutável e vigiá-las só produziria ruído.

Na primeira execução real ele já encontrou uma citação quebrada — a URL do doc
de Arrow que SF-PLAN-001 citava era 404 (`user_guide/` em vez de `tutorial/`).

## Dívidas abertas

| Dívida | Origem | Impacto |
|---|---|---|
| Fases 3b, 3c, 3d e 4 não iniciadas | §16 do spec da Fase 0 | Ver as seções acima |
| **Agente não é mecanismo de paridade declarado** | identificada em 2026-07-31 | `parity.yaml` declara `mechanisms: [mcp, cli, files]`. Os 3 agentes são espelhados para `.claude/agents/`, `.agents/agents/` e `.github/agents/`, com byte-identidade travada por `tests/test_agents_parity.py` — mas **nenhum teste verifica que a capacidade "coordenar investigação por agente" tem caminho em cada plataforma**, que é exatamente o que o gate da §8.4 existe para pegar. Some-se a isso que o frontmatter (`tools: Read, Grep, Glob, ...`) é vocabulário do Claude Code e não mapeia para o Devin, e que despacho de subagente é capacidade de *harness*, não conteúdo deste repositório: fora do Claude Code, os agentes valem como prosa orientadora, não como mecanismo verificado |
| Cobertura de EMR não existe | identificada ao fechar a Fase 3a | `RuntimeContext` não tem eixo de infraestrutura para EMR (release label, instance fleets, EMR Serverless, EMR on EKS); área `SF-EMR` inexistente. 44 das 48 regras já avaliam sem `glue`, mas nenhuma regra de infraestrutura EMR existe. Fase própria, sem spec ainda — ver seção acima |
| `sdist`/`wheel` não são reproduzíveis bit-a-bit entre duas construções da mesma árvore | Fase 3a, commit `2b6311c` | Nenhum `SOURCE_DATE_EPOCH` é fixado, e o zip carrega timestamp interno; duas chamadas de `python -m build` sobre o mesmo commit produzem artefatos com bytes diferentes. `release.yml` contorna isso copiando (`--outdir`) o artefato que o gate já provou, em vez de reconstruir — mas a build em si segue não-determinística, o que importa para quem quiser verificar um wheel publicado por hash contra uma reconstrução própria |
| `unreachable_function_count` não detecta código morto | Fase 1 | A medida só pega componente cíclico isolado. Detectar código morto de verdade exige emitir um nó por função **definida**, com ou sem aresta — mudança no extrator. Documentado em `rules/catalog/callgraph.yaml` |
| Normalização de HTML do `refresh_knowledge` não foi calibrada contra meses de execução real | 2026-07-31 | Se alguma página oficial mudar hash a cada leitura, ela vira alarme permanente. O primeiro PR ruidoso deve ajustar `normalize()`, não silenciar a fonte |

## Como manter este arquivo honesto

Ao fechar uma fase:

1. Atualize a tabela **Números correntes** rodando os comandos da coluna direita.
2. Marque a fase e cole a faixa de commits.
3. Escreva o par spec + plan em `specs/` e `plans/` com a data do merge.
4. Se um número de um spec antigo ficou obsoleto, **não edite o spec** — acrescente
   a linha na seção de desvios dele (§18 no caso da Fase 0) e aponte para cá.
