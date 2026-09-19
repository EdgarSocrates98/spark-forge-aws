# Ecossistema caveman: economia de token no output

O resumo está no [README](../../README.md). Aqui fica o detalhe do que vem ligado,
do que foi medido e deixado desligado, e do que ficou de fora. Medir o contexto que
uma sessão consumiu é outra coisa, com verbo próprio: veja
[Economia de contexto](usos/economia-de-contexto.md).

A compressão de output, de [Julius Brussee](https://github.com/JuliusBrussee), está
embutida neste repositório e **ligada por padrão**. Clonar é a instalação inteira:
não há `npm install`, não há `npx`, não há `package.json`, e nada aqui vai à rede.

| Peça | O que faz | Como chega | Instalar? |
|---|---|---|---|
| [`caveman`](https://github.com/JuliusBrussee/caveman) | Modo de comunicação comprimido: corta o output do agente preservando a substância técnica | `vendor/caveman/`, plugin declarado em `.claude/settings.json` | **Nada** |
| [`cavekit`](https://github.com/JuliusBrussee/cavekit) (`ck`) | Loop de spec-driven development sobre um `SPEC.md`: grill → spec → research → review → build, com backprop de bug para invariante | `vendor/cavekit/`, mesmo marketplace | **Nada** |

Créditos, licenças, SHAs pinados e os patches locais: [`vendor/CREDITS.md`](../../vendor/CREDITS.md).

O invariante "nenhum caminho padrão usa `npm` ou `npx`" tem gate próprio em
`tests/test_vendor_caveman.py::TestSemNpm` — inclusive contra o `plugin.json` do
projeto de terceiro, que pode mudar num bump futuro.

## O que já está ligado sem instalar nada

`vendor/` é um **marketplace de plugin local**, declarado em `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "sparkforge-caveman": { "source": { "source": "directory", "path": "./vendor" } }
  },
  "enabledPlugins": { "caveman@sparkforge-caveman": true, "ck@sparkforge-caveman": true }
}
```

O caminho é **relativo**, para que funcione em qualquer clone; ele é resolvido a partir
do diretório em que o Claude Code foi aberto, então abra-o na raiz do repositório.
A instalação é cópia de disco — não há rede envolvida.

**Sem Node na máquina também funciona.** Os dois hooks do plugin caveman são
`node ...`; sem Node eles não rodam e o ruleset não seria injetado — as skills
continuariam carregando, e o caveman deixaria de ser "ligado por padrão" sem que nada
acusasse. O `.claude/settings.json` tem um fallback em shell que só dispara quando
`node` não está no `PATH`:

```sh
command -v node >/dev/null 2>&1 || cat "$CLAUDE_PROJECT_DIR/vendor/caveman/src/rules/caveman-activate.md"
```

Com Node é no-op, sem injeção dupla. Sem Node, perde-se apenas o flag de modo
(`/caveman lite|full|ultra`) e o `/caveman-stats`, que dependem do hook em JS.

O modo é fixado em [`.caveman/config.json`](../../.caveman/config.json) como `full` — o
*repo-local config* que o caveman resolve **antes** da configuração de usuário. Quem já
usa caveman em outro nível não perde a própria configuração fora deste repositório, e
troca o modo só na sessão atual com `/caveman lite|full|ultra`.

As mesmas duas linhas de `enabledPlugins` **desligam** `caveman@caveman` e `ck@cavekit`
dentro deste projeto. Não é hostilidade com quem já os instalou globalmente: dois
caveman ligados injetam o ruleset duas vezes por sessão, que é exatamente o oposto de
economizar token. Vale a cópia vendorizada, que é a pinada e revisada.

## Vendorizado, medido e **não** ligado: `caveman-shrink`

`vendor/caveman/src/mcp-servers/caveman-shrink/` é um proxy MCP do mesmo autor, **sem
dependência nenhuma**, que comprime o campo `description` do catálogo de tools antes do
modelo lê-lo. Está em disco e pronto — e continua desligado, porque foi medido contra os
41 tools do servidor `sparkforge` em 2026-08-07:

| | bytes |
|---|---|
| `tools/list` cru | 146 438 |
| `tools/list` pelo proxy | 146 295 |
| **Economia** | **143 bytes — 0,1 %** |

As regras dele cortam artigo, filler e hedging **em inglês** (`the`, `just`, `really`); as
descrições deste catálogo são em português. Nomes de tool e `inputSchema` saem idênticos —
o proxy está correto, só não tem o que cortar aqui. Pôr um proxy no caminho do MCP por
0,1 % seria risco sem retorno. Como ligar, se o catálogo passar a ter descrição em inglês:
[`vendor/CREDITS.md`](../../vendor/CREDITS.md).

A medida é de 2026-08-07, com 41 tools; o servidor tem hoje mais tools (a contagem
corrente está na tabela *Números correntes* de
[`docs/superpowers/STATUS.md`](../superpowers/STATUS.md)), e a medida não foi refeita.

## O que ficou de fora, e por quê

Duas peças do mesmo autor **não** entram aqui, porque nenhuma das duas cabe em
"clonar é a instalação inteira":

| Projeto | Por que fica fora |
|---|---|
| [`cavemem`](https://github.com/JuliusBrussee/cavemem) | Memória entre sessões. Depende de `better-sqlite3`, módulo **nativo** compilado por plataforma — vendorizar prebuilds seria commitar binário para win32/linux/darwin × x64/arm64. E **não economiza token**: o `SessionStart` dele *injeta* contexto da sessão anterior. É memória, não compressão. |
| [`caveman-code`](https://www.npmjs.com/package/@juliusbrussee/caveman-code) | Agente de terminal próprio, 15 MB desempacotados com `better-sqlite3` nativo na árvore. Roda **fora** do Claude Code — é um cliente alternativo, não um componente deste projeto. |

Quem quiser qualquer um dos dois instala globalmente, por conta própria e fora deste
repositório: `npm install -g cavemem && cavemem install`.

## Procedência e atualização

`vendor/` não é espelho gerado de nada deste repositório — é código de terceiro pinado.
O que o mantém honesto:

| Arquivo | Papel |
|---|---|
| [`vendor/PINS.json`](../../vendor/PINS.json) | SHA upstream, lista de arquivos mantidos e patches locais, por projeto |
| `vendor/MANIFEST.sha256` | sha256 de cada arquivo vendorizado |
| `scripts/vendor_caveman.py` | Reconstrói a árvore a partir dos pins (usa rede) |
| `python scripts/vendor_caveman.py --check` | Gate **sem rede**: falha se qualquer byte divergir. Roda em `tests/test_vendor_caveman.py` |

Atualizar é editar o `sha` em `PINS.json`, rodar o script, revisar o diff e rodar a suíte.

## Agentes que não são o Claude Code

Devin, GitHub Copilot e Codex não carregam plugin nem hook. Para eles o ruleset caveman
está inline em [`AGENTS.md`](../../AGENTS.md), seção "Output compression — caveman mode",
junto com o que a compressão **não** pode tocar aqui: o schema `recommendation:`/`Finding`
inteiro, números, versões, `rule_id`, `fact_id`, strings de erro e blocos de código. A
forma portátil de arquivo único é `vendor/caveman/dist/caveman.skill`.

## Próximos passos

- [Segurança](11-seguranca.md): o que os hooks do caveman executam, na íntegra.
- [Economia de contexto](usos/economia-de-contexto.md): medir antes de afirmar que economizou.
