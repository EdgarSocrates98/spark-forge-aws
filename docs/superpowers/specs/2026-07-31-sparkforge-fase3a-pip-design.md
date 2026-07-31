# SparkForge AWS — Fase 3a: Distribuição pip

**Data:** 2026-07-31
**Status:** aprovado para planejamento
**Escopo:** primeiro dos quatro sub-projetos da Fase 3. Marketplace, export Devin e MCP hospedado ficam fora, cada um com seu próprio spec.
**Depende de:** contratos da [Fase 0](2026-07-29-sparkforge-fase0-design.md); catálogo completo da [Fase 2](2026-07-31-sparkforge-fase2-design.md)

---

## 1. Contexto: por que isto é a primeira coisa

O foco do repositório é **agente autônomo que avalia projetos Spark, PySpark, Glue e EMR** — ler código, propor melhoria, tunar, independente do cenário. Um agente autônomo roda em sandbox efêmero: sem o repositório clonado, sem estado prévio, com o que `pip install` entregar.

Hoje `pip install` entrega **metade do produto**. Isto foi medido, não deduzido — wheel construído com o backend atual e instalado num venv limpo, executado fora do repositório:

```
sparkforge --help              OK
sparkforge analyze pyspark     OK       extração é código puro
sparkforge rules lookup        FALHA    diretorio de catalogo inexistente
```

O wheel tem 43 arquivos e **zero** de `rules/catalog/`, `knowledge/` ou `skills/`. Como `loader.catalog_dir()` resolve `SPARKFORGE_CATALOG` → raiz do repo → fallback no pacote, e o fallback `sparkforge/rules/catalog/` não existe nem no disco nem no artefato, tudo que depende do catálogo morre: `judge`, `next-step`, `resume`, `rules lookup`.

Traduzindo para a fronteira da §4.2 da Fase 0: **a camada `facts/` embarca, a camada `rules/` não.** O agente instalado extrai evidência e não consegue julgá-la. É o substrato da missão que não funciona, e é por isso que este sub-projeto vem antes de cobertura de EMR ou de qualquer outro canal — regra nova não serve para um agente que não carrega o catálogo.

### O que a §16 chamava de Fase 3

O roadmap agrupa quatro entregas que não compartilham risco, dono nem pré-requisito: distribuição pip, marketplace de plugin, export de Playbook/Knowledge Devin, e MCP HTTP hospedado. Um spec único para os quatro não fecharia em nenhum. Este documento cobre só pip, que é o único de que os outros três dependem: hoje `.mcp.json` roda `python -m sparkforge.adapters.mcp` com `PYTHONPATH=${CLAUDE_PLUGIN_ROOT}`, ou seja, o plugin só funciona com o repositório inteiro em disco.

## 2. Objetivo

`pip install sparkforge-aws` entrega o ciclo determinístico inteiro — extrair, julgar, rotear, retomar — em máquina que nunca viu o repositório.

**Critério de sucesso:** o wheel instalado em venv limpo reproduz os goldens committados **byte a byte**, em Linux e em Windows. Mesma evidência, mesmos findings, mesmo próximo passo, independente do canal. É a §8.2 (escada de degradação) estendida a um quarto degrau: o pacote instalado.

### Não-objetivos

| Fora de escopo | Onde fica |
|---|---|
| Publicar no PyPI nesta rodada | ato do mantenedor; o workflow prepara e para |
| `marketplace.json` e instalação por marketplace | Fase 3b |
| Export de Playbook/Knowledge Devin | Fase 3c |
| MCP HTTP hospedado | Fase 3d |
| Cobertura de EMR | fase própria, seguinte a esta |
| Trocar a gestão de dependência para lock (`uv lock`) | quando houver necessidade; hoje o espelho `requirements.txt` já habilita o scan de SCA |

Os nomes `sparkforge-aws` e `sparkforge` estão **livres no PyPI** (conferido em 2026-07-31). Mantemos `sparkforge-aws`, que já é o nome em `pyproject.toml` e em `plugin.json`; o entry point continua `sparkforge`.

## 3. Decisões

| # | Decisão | Alternativas rejeitadas | Razão |
|---|---|---|---|
| 3a-D1 | Backend `hatchling` com `force-include` | espelho gerado e commitado; build hook em setuptools | Único caminho que embarca o catálogo **sem duplicar arquivo em git** e sem corroer D-A |
| 3a-D2 | Catálogo e knowledge continuam na raiz | mover para dentro do pacote | D-A da Fase 0: são o terceiro degrau da escada de portabilidade, o YAML que um agente sem Python lê direto |
| 3a-D3 | Loader não é tocado | adaptar `catalog_dir()` para o caso instalado | Ele já resolve na ordem certa desde a Fase 0; faltava o arquivo chegar ao fallback, não lógica nova |
| 3a-D4 | Paridade medida contra os goldens já committados | gerar corpus de comparação novo | As 74 fixtures já são o contrato. Corpus novo seria um segundo contrato para manter divergir do primeiro |
| 3a-D5 | Asserção de procedência antes de comparar | confiar em `cwd` e `PYTHONSAFEPATH` | Configuração se perde. Se `sparkforge.__file__` não estiver sob `site-packages`, o teste compara o repo consigo mesmo e passa sempre |
| 3a-D6 | Matriz Linux + Windows no gate do artefato | só Linux | Golden é gravado com LF forçado e path de subject é normalizado para `/`. O que escapar disso só aparece no Windows |
| 3a-D7 | Release constrói e para; publicação é ato humano | publicar no dispatch | Versão publicada no PyPI não se reescreve, só se yanka. É o único passo irreversível do desenho |
| 3a-D8 | `knowledge/` ganha localização programática | empacotar e deixar como está | Nenhum código lê aqueles arquivos hoje; empacotar 19 arquivos inalcançáveis é peso sem consumidor |

## 4. Arquitetura

### 4.1 O que não muda

`rules/catalog/` e `knowledge/` continuam na raiz do repositório.

**O defeito central — catálogo ausente do artefato — se resolve sem tocar em código Python.** É mudança de empacotamento apenas. O trabalho de código deste spec é outro e é aditivo: localizar `knowledge/` (§4.5), que é lacuna descoberta ao verificar o empacotamento, não consequência dele.

`loader.catalog_dir()` já resolve nesta ordem, desde a Fase 0:

| Contexto | Quem vence | Efeito |
|---|---|---|
| Rodando no repositório | raiz do repo | idêntico ao comportamento atual |
| Instalado por pip | fallback no pacote | catálogo embarcado |
| Plugin do Claude Code | `SPARKFORGE_CATALOG` do `.mcp.json` | continua explícito |
| `pip install -e .` | raiz do repo | sem regressão para quem desenvolve |

O fallback `Path(__file__).parent / "catalog"` sempre existiu no código e nunca existiu em disco. Este spec faz o arquivo chegar lá.

### 4.2 O que muda

```
pyproject.toml       backend setuptools -> hatchling; force-include; metadata de publicação
.claude-plugin/      homepage corrigida
sparkforge/          novo verbo `knowledge path`; `rules lookup` devolve caminho de knowledge
scripts/             verificador de artefato
.github/workflows/   job de artefato no ci.yml; release.yml novo
tests/               testes do verbo novo e do resolvedor de knowledge
```

### 4.3 Empacotamento

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["sparkforge"]

[tool.hatch.build.targets.wheel.force-include]
"rules/catalog" = "sparkforge/rules/catalog"
"knowledge"     = "sparkforge/knowledge"

[tool.hatch.build.targets.sdist.force-include]
"rules/catalog" = "sparkforge/rules/catalog"
"knowledge"     = "sparkforge/knowledge"
```

O `sdist` recebe o mesmo mapeamento. `force-include` no target `wheel` não cobre o sdist, e quem instalar a partir da fonte ficaria sem catálogo — a mesma falha, um caminho adiante.

**Validado antes de escrever este spec.** Conversão aplicada, artefato construído, instalado em venv limpo fora do repositório: wheel passou de 43 para 72 arquivos, com 11 de catálogo e 19 de knowledge; `load_catalog()` devolveu 48 regras e `sparkforge rules lookup --id SF-PLAN-003` respondeu. O `pyproject.toml` foi restaurado em seguida.

### 4.4 Metadata de publicação

`pyproject.toml` não tem hoje `readme`, `license`, `classifiers`, `urls` nem `authors`. O `LICENSE` existe em disco e não é declarado. Publicar assim gera pacote sem descrição e sem licença legível por ferramenta.

Entram: `readme = "README.md"`, `license`, `authors`, `classifiers` (Python 3.10/3.11, licença, tópico), e `urls` apontando para o repositório **real**.

`.claude-plugin/plugin.json` declara `homepage: https://github.com/sparkforge-aws/spark-forge-aws`, organização que não existe; o repositório é `EdgarSocrates98/spark-forge-aws`. Instalar o plugin por esse link dá 404. Correção entra aqui porque é uma linha e é pré-requisito de qualquer canal.

### 4.5 Localizar knowledge a partir do pacote

`knowledge/` é citado em 7 pontos do código — **todos comentário ou docstring**. Nenhuma função lê aqueles arquivos. Um agente instalado por pip recebe 19 arquivos que não tem como encontrar.

Duas superfícies, ambas entram:

**`sparkforge knowledge path [--file <rel>]`** — resolve e imprime o caminho, com a mesma ordem de precedência do catálogo (`SPARKFORGE_KNOWLEDGE` → raiz do repo → pacote). Sem `--file`, imprime a raiz. Escape hatch barato para qualquer consumidor.

**`rules lookup` devolve os caminhos** — cada regra retornada ganha os caminhos resolvidos dos arquivos de knowledge que sua `explanation` cita. O `AGENT_PROTOCOL` regra 4 já obriga o agente a chamar `rules_lookup` em vez de lembrar limiar; o caminho chega junto, sem etapa nova no protocolo.

A primeira é conveniência; a segunda é a que faz o knowledge embarcado ser efetivamente usado.

## 5. O gate de paridade

### 5.1 Forma

```
build sdist + wheel -> venv limpo -> instala -> roda as 74 fixtures -> compara com expected/*.json
```

O corpus é o que já existe. As fixtures têm `expected/facts.json` e `expected/findings.json` committados; se o pacote instalado os reproduz byte a byte, paridade está provada contra o mesmo contrato que o repositório usa. Criar corpus novo seria um segundo contrato para manter divergir do primeiro.

As fixtures vêm do checkout; o venv fornece **só o pacote**.

### 5.2 A asserção que impede o teste de virar teatro

Se o processo rodar com o repositório no `sys.path`, `import sparkforge` pega o código-fonte e o teste compara o repositório consigo mesmo — passa sempre, prova nada. É a mesma classe de defeito do transporte HTTP na Fase 1, que tinha `# pragma: no cover` sobre código quebrado, e do `_call_tool`, cujos testes exercitavam a função certa e nunca a camada que falhava.

Duas guardas, e a ordem importa:

1. Executar de `cwd` fora do repositório, com `PYTHONSAFEPATH=1`
2. **Antes de comparar qualquer golden**, afirmar que `sparkforge.__file__` está sob o `site-packages` do venv. Se estiver sob o repositório, falha imediata com essa mensagem

A segunda é a que sustenta. A primeira é configuração, e configuração se perde.

### 5.3 Checagens do mesmo job

| Checagem | Pega |
|---|---|
| Catálogo e knowledge não-vazios dentro do artefato | `force-include` quebrar em silêncio num upgrade do hatchling |
| `twine check` no wheel **e** no sdist | metadata inválida antes de chegar ao PyPI |
| `sparkforge --help` a partir do venv | entry point não instalado |
| `sparkforge knowledge path` resolve arquivo existente | os 19 arquivos serem inalcançáveis |
| `rules lookup` devolve caminho de knowledge resolvido | §4.5 funcionando de fato |

### 5.4 Onde roda

Job próprio no `ci.yml`, separado do job `test`, com matriz de sistema operacional: `ubuntu-latest` e `windows-latest`, Python 3.11.

Não entra na matriz 3.10/3.11 do job `test`: construir artefato e criar venv custa mais de um minuto e o resultado não depende da versão de Python — rodar quatro vezes seria desperdício. Depende do sistema operacional, e por isso a matriz é essa.

## 6. Release

`.github/workflows/release.yml`, **só `workflow_dispatch`**. Constrói, prova e para:

```
build sdist + wheel -> gate de paridade (Linux + Windows) -> twine check
                    -> artefatos anexados a um GitHub Release em rascunho
```

Publicar no PyPI fica como ato do mantenedor: `twine upload` com credencial própria, ou um segundo job com Trusted Publishing habilitado depois. Nenhuma credencial é escrita neste repositório e nada é publicado automaticamente.

**Guarda de versão.** O workflow recusa se a tag não bater com a versão declarada. Sem isso é possível publicar `0.5.0` sob a tag `v0.6.0` — e versão publicada no PyPI não se reescreve, só se yanka. A guarda fica no único passo irreversível do desenho.

A concordância entre as quatro fontes da versão já é verificada por
`tests/test_package_importable.py::test_every_manifest_declares_the_same_version`; o release acrescenta a quinta ponta, que é a tag.

## 7. Testes

| Camada | Teste |
|---|---|
| empacotamento | artefato contém catálogo e knowledge; contagem não-zero em wheel e sdist |
| paridade | 74 fixtures reproduzidas byte a byte a partir do pacote instalado, Linux e Windows |
| procedência | `sparkforge.__file__` sob `site-packages`; falha explícita se estiver sob o repo |
| knowledge | `knowledge path` resolve com a mesma precedência do catálogo; `--file` inexistente dá erro acionável |
| rules lookup | resposta inclui caminhos de knowledge resolvidos e existentes |
| metadata | `twine check` verde; `urls` aponta para o repositório real |
| release | tag divergente da versão reprova |

Os testes existentes permanecem. `test_docs_coverage`, `test_package_importable`, `test_requirements_mirror` e `test_capability_parity` não mudam de intenção.

## 8. Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Troca de backend quebra algo que setuptools fazia implicitamente | média | Gate de paridade sobre as 74 fixtures; conversão já validada ponta a ponta antes deste spec |
| Gate importa o repositório e prova nada | alta se não guardado | Asserção de procedência, §5.2 |
| `force-include` some num upgrade do hatchling | baixa | Asserção de contagem de arquivos no artefato |
| Divergência de path ou newline entre sistemas operacionais | média | Matriz Linux + Windows |
| Publicar versão errada | baixa, irreversível | Guarda de tag no release |
| `knowledge/` embarcado continuar sem consumidor | média | §4.5 entrega as duas superfícies, e o gate exige que resolvam |

## 9. Critérios de aceitação

1. `python -m build` produz sdist e wheel contendo `rules/catalog/` e `knowledge/`.
2. Wheel instalado em venv limpo, fora do repositório, executa `analyze`, `judge`, `next-step`, `resume` e `rules lookup` sem erro.
3. As 74 fixtures são reproduzidas byte a byte a partir do pacote instalado, em Linux e em Windows.
4. O gate falha, com mensagem explícita, se `sparkforge` for importado do repositório em vez do `site-packages`.
5. `sparkforge knowledge path` resolve arquivo existente a partir do pacote instalado.
6. `rules lookup` devolve caminhos de knowledge resolvidos e existentes.
7. `twine check` passa no wheel e no sdist.
8. `pip install -e .` continua funcionando, sem regressão para desenvolvimento.
9. `plugin.json` aponta para o repositório real.
10. `release.yml` constrói, prova, anexa artefatos e **não publica**; recusa tag divergente da versão.
11. Suíte existente continua verde e o número de testes cresce.

## 10. O que vem depois

Fase 3b marketplace, 3c export Devin, 3d MCP hospedado — cada um com spec próprio. E, fora da §16, a cobertura de **EMR**: hoje `RuntimeContext` conhece `glue`, `spark`, `python`, `iceberg` e `athena`, e não `emr`; num runtime sem chave `glue`, 44 das 48 regras ainda são avaliadas, porque a análise de código e execução é agnóstica por construção, mas o eixo de infraestrutura não existe — sem release label, sem instance fleets, sem EMR Serverless, sem área `SF-EMR`. Isso é fase própria, e vem logo depois desta.
