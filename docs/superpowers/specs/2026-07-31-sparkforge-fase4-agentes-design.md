# SparkForge AWS — Fase 4: Coordenadores Especializados, Executores e Espelho de Orquestração

**Data:** 2026-07-31
**Status:** implementado em 2026-07-31. Faixa de commits `4cf81c8` … `d366eb9`, fechada por este commit.
**Depende de:** [Fase 3a](2026-07-31-sparkforge-fase3a-pip-design.md) — o pacote instalável é o que torna o espelho executável em qualquer plataforma
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o buraco é cobertura, não quantidade de agentes

O repositório tem 3 agentes, 18 skills, 29 tools MCP e 48 regras em 9 áreas. A primeira hipótese ao abrir esta fase foi "faltam agentes para os eixos descobertos". **Medição derrubou a hipótese:**

```
skills: 18 | declaradas por algum agente: 18 | orfas: 0
tools MCP: 29 | citadas em agente ou skill: 8 | orfas: 21
skills por agente: 17 / 10 / 3
```

Nenhuma skill está órfã. **21 das 29 tools nunca são mencionadas em agente nenhum nem em skill nenhuma.** Um agente que leia o material de orientação nunca descobre que existem `sparkforge_analyze_terraform`, `sparkforge_collect_event_log`, `sparkforge_fuse`, `sparkforge_analyze_plan` ou `sparkforge_knowledge_path`.

A causa é histórica e conhecida: a Fase 1 acrescentou 12 extratores com suas tools, e as skills foram reescritas *toolkit-first* cobrindo o subconjunto que existia na época. Cada fase seguinte alargou a superfície sem alargar a orientação.

O efeito é o mesmo defeito que este repositório persegue desde a Fase 0, uma camada acima: **capacidade que existe e não é alcançável não é capacidade**. É a versão de orientação do `pyspark.unresolved` — a diferença entre "não há o que extrair ali" e "ninguém olhou".

E há um segundo buraco, exposto ao perguntar se agentes chegam ao Devin: `parity.yaml` declara `mechanisms: [mcp, cli, files]`. **Agente não é mecanismo declarado.** Os 3 agentes são espelhados para `.claude/agents/`, `.agents/agents/` e `.github/agents/` com byte-identidade travada por teste — mas nada verifica que a capacidade "coordenar investigação" tem caminho em cada plataforma. Somado a isso: o frontmatter (`tools: Read, Grep, Glob, ...`) é vocabulário do Claude Code e não mapeia para o Devin, e **despacho de subagente é capacidade de harness, não conteúdo deste repositório**.

## 2. Objetivo

Toda capacidade do toolkit alcançável a partir de um coordenador, em toda plataforma suportada — verificado por teste, não prometido em prosa.

**Critério de sucesso:** um invariante de CI que falha quando uma tool, um verbo de CLI ou uma área de regra não é alcançável a partir de nenhum coordenador; e um mecanismo de orquestração declarado no `parity.yaml` com caminho para as quatro plataformas.

### Não-objetivos

| Fora de escopo | Razão |
|---|---|
| Renomear os 3 agentes existentes | `CLAUDE.md`, `AGENTS.md` e `PROMPT_INICIAL_MESTRE.md` os citam por nome; renomear quebra em silêncio |
| Fazer Devin ou Codex despacharem subagentes | Capacidade de harness. O espelho traduz a decomposição, não a executa em paralelo |
| Cobertura de EMR | Fase própria, registrada no `STATUS.md` |

## 3. Decisões

| # | Decisão | Alternativa rejeitada | Razão |
|---|---|---|---|
| F4-D1 | Coordenadores por domínio despachando executores por função | Só um dos dois eixos | Domínio decide o QUE investigar; função decide COMO. Um eixo só deixa metade da decomposição implícita |
| F4-D2 | Os 3 agentes atuais viram coordenadores, com nome intacto | Substituir por conjunto novo por área de regra | Mapeamento com o catálogo seria mais limpo, mas migrar toda referência por nome em docs e skills custa mais do que ganha |
| F4-D3 | Roteamento de agente vira **dado**, em `routing.yaml` | Prosa dizendo "use o agente certo" | Manter 3 antigos e acrescentar novos cria dois vocabulários. Tabela derivada do case elimina o julgamento; prosa o multiplica |
| F4-D4 | Espelho é **verbo de CLI**, não documento | Markdown por coordenador; prompts para colar | Documento é prosa: envelhece em silêncio quando os executores mudarem, e nenhum teste pega. Verbo é executável e testável |
| F4-D5 | `playbook` entra como **mecanismo declarado** no `parity.yaml` | Deixar agentes fora do manifesto, como hoje | É o que fecha a dívida: pela primeira vez "coordenar investigação" ganha caminho verificado por plataforma |
| F4-D6 | Cobertura vira invariante de CI | Checklist de revisão | O repositório já tem quatro invariantes desse tipo. Checklist é a forma que apodrece |
| F4-D7 | Executor `sf-verifier` tenta **refutar**, com ônus da prova invertido | Verificador que confirma | Confirmador concorda com quem o chamou. A §17 da Fase 0 diz que falso positivo treina o operador a ignorar a saída |

## 4. Arquitetura

### 4.1 Três camadas, um estado

```
coordenador (agente Claude)   decide O QUE investigar, por dominio
     |  despacha
executor (subagente Claude)   faz UMA funcao do loop de fase
     |
playbook (verbo de CLI)       mesma decomposicao, sequencial,
                              para plataforma sem despacho de subagente
```

O que mantém as três honestas é `.sparkforge/case.yaml`: coordenador, executor e playbook leem e escrevem o mesmo estado. Nenhum guarda contexto próprio. É a mesma razão pela qual a Fase 0 pôs o roteamento em dado — estado que sobrevive à troca de sessão, de modelo e de ferramenta.

### 4.2 Coordenadores

Os 3 existentes mantêm nome e descrição, e ganham a decomposição em executores. Entram 3 para os eixos onde a orientação é mais rala:

| Coordenador | Áreas de regra | Situação hoje |
|---|---|---|
| `spark-performance-architect` | SF-PY, SF-UI, SF-PLAN | existente, 10 skills |
| `glue-incremental-performance-architect` | SF-PY, SF-ICE, SF-UI, SF-ENV | existente, 17 skills |
| `iceberg-performance-engineer` | SF-ICE, SF-PQ | existente, 3 skills |
| `glue-infra-reviewer` | SF-GLUE, SF-ENV | **novo** — Terraform, worker, bookmark, observabilidade |
| `athena-query-optimizer` | SF-ATH, SF-PQ | **novo** — nenhum agente cobre consulta hoje |
| `pyspark-code-reviewer` | SF-PY, SF-PLAN, SF-CG | **novo** — revisão de PR e call graph |

A distribuição atual é torta (17/10/3). Os novos não a corrigem sozinhos; o invariante da §5 é que a força.

### 4.3 Executores

Por função — é o loop de fase que o `AGENT_PROTOCOL` já descreve. Cada um com fronteira negativa explícita, na mesma disciplina da §4.2 da Fase 0.

| Executor | Faz | **Não faz** |
|---|---|---|
| `sf-inventory` | Mapeia artefatos e runtime; diz o que falta coletar e com qual comando | Não extrai fact |
| `sf-extractor` | Roda os verbos `analyze`, produz facts, reporta `unresolved` | Não julga; não aplica limiar |
| `sf-judge` | Roda `judge`, agrupa por severidade, cita `rule_id` e `fact_id` | Não propõe mudança de código |
| `sf-verifier` | **Tenta refutar** cada P0 e P1 | Não conserta; não escreve relatório |
| `sf-synthesizer` | Relatório e próximo passo | Não produz número sem `fact_id` |

**`sf-verifier` é o que mais agrega, e é o único sem equivalente hoje.** Um finding sai do `judge` e vira recomendação sem ninguém tentar derrubá-lo. O ônus da prova invertido — o executor precisa argumentar que o achado é falso, e só sobrevive o que ele não conseguir refutar — é o mecanismo mais barato contra o falso positivo que a §17 da Fase 0 aponta como o risco que treina o operador a ignorar a saída.

### 4.4 Roteamento de agente como dado

Qual coordenador usar entra em `rules/catalog/routing.yaml`, ao lado das 16 rotas de skill, com o mesmo motor e os mesmos operadores declarativos (`equals`, `count_gt`, `contains`, `any_where`, `absent`).

Sem isso, manter os 3 antigos e acrescentar 3 novos produz dois vocabulários e o próximo leitor não sabe qual usar — risco levantado e aceito conscientemente ao escolher F4-D2. A tabela é o que o neutraliza: escolher agente deixa de ser julgamento e vira consulta, exatamente como `next_step` fez com a escolha de skill.

### 4.5 `sparkforge playbook`

```
sparkforge playbook <coordenador> [--repo .]
```

Emite a decomposição em passos ordenados, já preenchida com o estado do case e o `next_step`. Saída JSON, como todo verbo do pacote, com uma renderização legível.

Roda em qualquer plataforma com shell — é o que dá a Devin, Codex e Copilot a mesma decomposição que o Claude Code executa por despacho. Perde o paralelismo; mantém o método, as fronteiras negativas e a ordem.

## 5. O invariante de cobertura

O coração desta fase. Três testes, no espírito de `test_rules_catalog_reachability.py` e `test_fixtures_kind_coverage.py`:

1. **Toda tool MCP é alcançável a partir de pelo menos um coordenador.** Hoje 8 de 29. Falha listando as órfãs.
2. **Toda área de regra tem coordenador.** As 9 áreas cobertas.
3. **Todo coordenador declara executores que existem**, e todo executor é declarado por pelo menos um coordenador.

Uma tool nova sem coordenador quebra a build — que é o único jeito de a cobertura não apodrecer de novo. Foi assim que 21 tools ficaram invisíveis: cada fase alargou a superfície sem alargar a orientação, e nada reprovou.

## 6. Paridade

`parity.yaml` ganha:

- **Plataforma nova:** `codex`, ao lado de `claude_code`, `devin_desktop`, `devin_cli`, `copilot_ci`
- **Mecanismo novo:** `playbook`, ao lado de `mcp`, `cli`, `files`

E a capacidade "coordenar investigação por agente", que hoje não existe no manifesto, passa a declarar caminho por plataforma:

| Plataforma | Mecanismo |
|---|---|
| `claude_code` | despacho de subagente + `playbook` |
| `devin_desktop`, `devin_cli`, `codex`, `copilot_ci` | `playbook` |

É isto que fecha a dívida registrada no `STATUS.md`: a capacidade deixa de ser espelho de arquivo cujo frontmatter não mapeia, e passa a ter caminho verificado.

## 7. Testes

| Camada | Teste |
|---|---|
| cobertura | as três asserções da §5 |
| roteamento | estados de case → coordenador esperado; par de fixtures por rota nova |
| playbook | saída determinística; passos batem com os executores declarados pelo coordenador |
| paridade | `codex` e `playbook` no manifesto; capacidade com caminho nas cinco plataformas |
| espelhos | `sync_skills.py --check` cobre os agentes novos |
| fronteira | executor não declara ferramenta fora da sua função (extractor sem `judge`, judge sem `Edit`) |

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Dois vocabulários de agente convivendo | §4.4 — roteamento como dado |
| Espelho `playbook` divergir dos executores reais | Teste da §7 compara passos com executores declarados |
| Cobertura virar teatro: citar a tool sem ensinar quando usá-la | O teste mede menção; a revisão mede utilidade. Registrado como limite conhecido do invariante |
| 6 coordenadores × 5 executores virar burocracia para investigação simples | `playbook` e o roteamento indicam o caminho curto; nem toda investigação passa pelos cinco |
| Frontmatter continuar Claude-específico | Aceito: o espelho é o `playbook`, não o arquivo de agente |

## 9. Critérios de aceitação

1. 6 coordenadores, cada um declarando executores existentes.
2. 5 executores, cada um com fronteira negativa explícita.
3. As 29 tools alcançáveis a partir de algum coordenador; o teste falha se alguma não for.
4. As 9 áreas de regra com coordenador.
5. `sparkforge playbook <coordenador>` emite decomposição determinística com estado do case.
6. Rotas de coordenador em `routing.yaml`, com fixture provando cada uma.
7. `parity.yaml` com `codex` e `playbook`; capacidade de coordenação com caminho nas cinco plataformas.
8. `sync_skills.py --check` verde com os agentes novos nos três espelhos.
9. Suíte verde e maior; `ruff`, `gen_requirements --check`, `check_evals` verdes.
10. `README.md`, `AGENTS.md`, `AGENT_PROTOCOL.md`, `GUIA_DE_USO.md`, `PROMPT_INICIAL_MESTRE.md` e `STATUS.md` atualizados e referenciando o que é novo.
