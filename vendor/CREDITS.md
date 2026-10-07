# Créditos e procedência — terceiros dentro do SparkForge

Este arquivo cobre **duas** procedências diferentes, e a diferença importa:

1. **Vendorizado** (`vendor/`, este diretório) — bytes de terceiro, pinados por
   SHA e conferidos por gate sem rede. Nada aqui é nosso.
2. **Adaptado** (`skills/aws-*`, `skills/harden-s3-bucket`,
   `skills/provision-s3-tables-table`, `skills/sdd-*`) — procedimento de
   terceiro reescrito em português e recortado ao domínio deste repositório.
   Não é cópia byte a byte, e por isso não tem pin nem `MANIFEST.sha256`: a
   origem está citada no rodapé de cada `SKILL.md` das skills AWS e na seção
   das skills SDD, abaixo.

## Vendorizado — ecossistema caveman

O `vendor/` existe para que quem clonar o repositório tenha economia de token
ligada por padrão — sem instalar nada, sem rede, sem `npm install`, sem `npx`.

Nada aqui é nosso. Todo o crédito é de **[Julius Brussee](https://github.com/JuliusBrussee)**.

## Vendorizado e ligado

| Projeto | O que faz | Upstream | Licença | Pin |
|---|---|---|---|---|
| **caveman** | Modo de comunicação comprimido para agentes. Corta o output mantendo a substância técnica. | https://github.com/JuliusBrussee/caveman | MIT | `ec83e5bace4c20484d704dea21e12fc4eb94e9aa` |
| **cavekit** (`ck`) | Loop de spec-driven development comprimido sobre um `SPEC.md`: grill → spec → research → review → build, com backprop de bug para invariante. | https://github.com/JuliusBrussee/cavekit | MIT | `c322f0bb6db82163041930467f3ce32754d42827` |

As licenças MIT originais estão preservadas em `caveman/LICENSE` e
`cavekit/LICENSE`.

## Vendorizado e **não** ligado

**caveman-shrink** (`vendor/caveman/src/mcp-servers/caveman-shrink/`, do mesmo
autor, MIT, **zero dependências**) é um proxy MCP que comprime o campo
`description` do catálogo de tools antes do modelo lê-lo.

Está em disco e pronto para uso, mas não está no `.mcp.json` porque **foi medido
e não paga**. Contra os 41 tools do servidor `sparkforge`, em 2026-08-07:

| | bytes |
|---|---|
| `tools/list` cru | 146 438 |
| `tools/list` pelo proxy | 146 295 |
| **Economia** | **143 bytes — 0,1 %** |

A razão é simples: as regras do compressor cortam artigo, filler e hedging **em
inglês** (`the`, `just`, `really`), e as descrições deste catálogo são em
português. Nomes de tool e `inputSchema` saem idênticos — o proxy é correto,
só não tem o que cortar aqui. Pôr um proxy no caminho do MCP por 0,1 % seria
risco sem retorno.

Ligar, se algum dia o catálogo passar a ter descrição em inglês:

```json
{
  "mcpServers": {
    "sparkforge": {
      "command": "node",
      "args": [
        "vendor/caveman/src/mcp-servers/caveman-shrink/index.js",
        "python", "-m", "sparkforge.adapters.mcp", "--transport", "stdio"
      ]
    }
  }
}
```

## Adaptado, não vendorizado — skills oficiais AWS

| Origem | Licença | Commit de origem | O que veio |
|---|---|---|---|
| [`aws/agent-toolkit-for-aws`](https://github.com/aws/agent-toolkit-for-aws) | **Apache-2.0** (verificado na página do repositório em 2026-09-03) | `10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02) | 11 skills de procedimento operacional AWS |

As onze: `provision-s3-tables-table`, `harden-s3-bucket`, `aws-storage`,
`aws-database`, `aws-serverless`, `aws-iam`, `aws-observability`,
`aws-billing-and-cost-management`, `aws-messaging-and-streaming`,
`aws-security`, `aws-sdk-python-usage`.

**Por que não estão em `vendor/`**: elas foram **reescritas**, não copiadas —
traduzidas para português, recortadas ao domínio deste repositório e ganharam a
fronteira `## Não faz` que o upstream não tem. Um `MANIFEST.sha256` sobre texto
reescrito não conferiria nada: a cada ajuste de redação o gate quebraria sem
que nenhuma divergência com o upstream tivesse acontecido. O que as mantém
honestas é outra coisa:

- cada `SKILL.md` cita a skill de origem e o commit no rodapé;
- o upstream é declarado como **fonte autoritativa** dentro de cada uma — em
  divergência, vale a AWS, não o nosso texto;
- as onze são **não-despacháveis** (podem mutar infraestrutura ao vivo, e a
  fronteira exige confirmação do operador), registrado em
  `docs/superpowers/STATUS.md`.

Apache-2.0 permite obra derivada com atribuição e aviso de licença. A
atribuição é o rodapé de cada `SKILL.md` mais esta seção; o aviso de licença é
esta linha: o material original é © Amazon Web Services, licenciado sob
Apache-2.0, e o texto integral da licença está em
<https://www.apache.org/licenses/LICENSE-2.0>.

## Adaptado, não vendorizado — as skills do SDD próprio

As seis skills `sdd-explore`, `sdd-define`, `sdd-design`, `sdd-plan`,
`sdd-build` e `sdd-ship` (2026-09-16, feature `docs/sdd/SDD_SKILLS/`) e os
templates de `docs/sdd/templates/` foram escritos em português a partir de dois
processos de spec que o repositório usava como plugins de nível usuário:

| Origem | Licença | Versão lida | O que serviu de base |
|---|---|---|---|
| [`obra/superpowers`](https://github.com/obra/superpowers) | **MIT** | 5.1.0 | brainstorming (uma pergunta por vez, duas ou três abordagens, portão antes do código), writing-plans (tarefa pequena com teste, comando e código completo; a lista do que é placeholder), test-driven-development (a lei do vermelho antes do verde), subagent-driven-development e seus três prompts (um subagente novo por tarefa com o texto colado, os quatro estados do implementador, revisão de spec antes da de qualidade, revisor que não confia no relato), finishing-a-development-branch (esperar a escolha antes de integrar) |
| [`luanmorenommaciel/agentspec`](https://github.com/luanmorenommaciel/agentspec) | **MIT** | 3.5.0 | a ordem das fases (brainstorm, define, design, build, ship), o manifesto de arquivos do design, decisões com alternativas, o relatório de build, e a forma dos templates por fase |

**O que é nosso**, e não está em nenhuma das duas bases:

- o gate determinístico `sparkforge sdd check|status|stamp`, que recusa por nome
  o que não fecha, no lugar do *clarity score* e das notas de confiança
  atribuídas pelo próprio modelo;
- a cascata por hash de texto (`upstream.sha256` e `upstream_stale`), no lugar
  de lembrar de atualizar a fase de baixo;
- o `verified_by` de cada critério apontando teste, comando, `funcval` ou fact
  reais, e o `red`/`green` com comando e exit no relatório de build;
- o conhecimento consultado por verbo (`sparkforge rules lookup`,
  `sparkforge knowledge path`, `sparkforge code symbol`), e nunca por uma base de
  conhecimento paralela;
- o perfil `operator`, em que o build passa por `sparkforge change sandbox` e a
  árvore do operador nunca é escrita pela sessão;
- o ship que deriva os gates de `docs/gates-por-mudanca.md` pelos
  `change_kinds` do define, e a hipótese fechada só por acréscimo.

Nenhum texto foi copiado byte a byte: as skills foram reescritas e recortadas ao
repositório, e por isso não têm pin. A licença MIT das duas bases permite obra
derivada com atribuição; a atribuição é esta seção. Os dois materiais originais
são © dos respectivos autores (Jesse Vincent, no `LICENSE` do superpowers 5.1.0;
Luan Moreno, no `plugin.json` do AgentSpec 3.5.0), sob a licença MIT, cujo texto
está em <https://opensource.org/license/mit>.

## Fora do repositório, e por quê

Duas peças do mesmo autor **não** entram aqui. Não há `package.json` neste
repositório: nenhum caminho padrão pode depender de `npm install` ou `npx`.

| Projeto | Por que fica fora |
|---|---|
| **[cavemem](https://github.com/JuliusBrussee/cavemem)** | Memória entre sessões. Depende de `better-sqlite3`, módulo **nativo** compilado por plataforma — bytes vendorizados não rodam fora da máquina que os gerou, e vendorizar prebuilds seria commitar binário para win32/linux/darwin × x64/arm64. Além disso **não economiza token**: o `SessionStart` dele *injeta* contexto da sessão anterior. É memória, não compressão. |
| **[caveman-code](https://www.npmjs.com/package/@juliusbrussee/caveman-code)** | Agente de terminal próprio, 15 MB desempacotados com `better-sqlite3` nativo na árvore. Roda **fora** do Claude Code, então não participa da economia de token deste repositório — é um cliente alternativo, não um componente do projeto. |

Quem quiser qualquer um dos dois instala globalmente, por conta própria e fora
deste repositório:

```bash
npm install -g cavemem && cavemem install
npm install -g @juliusbrussee/caveman-code
```

## Por que só parte de cada repositório vendorizado

`PINS.json` declara uma lista `keep` por projeto. Ficou de fora o que não
participa da execução dentro deste repositório: `tests/`, `benchmarks/`,
`evals/`, `docs/`, `.github/` e o instalador `cli/` do caveman — a instalação
aqui é feita pelo próprio repositório, em `.claude/settings.json`, e não pelo
instalador global do upstream.

## Patches locais

Um único desvio do upstream, declarado em `PINS.json` e reaplicado a cada
re-vendorização:

- `caveman`: `plugins/caveman/skills/caveman-compress/scripts/` é copiado para
  `skills/caveman-compress/scripts/`. O `SKILL.md` publicado em `skills/` manda
  rodar `python3 -m scripts` a partir do diretório do próprio `SKILL.md`, mas o
  upstream só publica esses scripts sob `plugins/caveman/`. Sem a cópia, a
  skill carrega no plugin e falha ao executar.

## Como atualizar

```bash
# 1. edite os campos `sha` em vendor/PINS.json
# 2. reconstrua a árvore e o manifest (usa rede)
python scripts/vendor_caveman.py
# 3. confira o diff e rode a suíte
python -m pytest tests/test_vendor_caveman.py -q
```

O gate que roda em CI e nos testes não usa rede:

```bash
python scripts/vendor_caveman.py --check
```

Ele falha se qualquer byte sob `vendor/` divergir de `MANIFEST.sha256` — o que
transforma edição local acidental em erro visível, em vez de "copiado uma vez e
esquecido".

## Como isso é ativado

Ver [`README.md`](../README.md), seção "Ecossistema caveman", e
[`.caveman/README.md`](../.caveman/README.md) para o pin do modo `full` e para o
fallback que mantém o caveman ativo em máquina sem Node.
