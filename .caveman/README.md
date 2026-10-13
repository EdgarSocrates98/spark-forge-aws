# `.caveman/` — modo caveman fixado no repositório

`config.json` é o *repo-local config* que o caveman resolve antes de qualquer
configuração de usuário. Ordem de resolução, implementada em
`vendor/caveman/src/hooks/caveman-config.js`:

1. variável de ambiente `CAVEMAN_DEFAULT_MODE`
2. **este arquivo** (`<repo>/.caveman/config.json` ou `<repo>/.caveman.json`)
3. config do usuário (`~/.config/caveman/config.json`, `%APPDATA%\caveman\config.json`)
4. `full`

`"defaultMode": "full"` é o pin do time: quem clonar este repositório abre a
sessão em caveman full sem configurar nada, e sem que isso vaze para os outros
projetos da mesma máquina.

Trocar o modo só na sessão atual: `/caveman lite|full|ultra`. O flag de sessão
vence este arquivo até o próximo `SessionStart`.

## Sem Node na máquina

Os dois hooks do plugin caveman são `node ...`. Sem Node, eles não rodam e o
ruleset não seria injetado — as skills continuariam carregando, e o caveman
deixaria de ser "ligado por padrão" sem que nada acusasse. O
`.claude/settings.json` do projeto tem um **fallback em shell** que só dispara
quando `node` não está no `PATH`:

```sh
command -v node >/dev/null 2>&1 || cat "$CLAUDE_PROJECT_DIR/vendor/caveman/src/rules/caveman-activate.md"
```

Com Node é no-op — sem injeção dupla. Sem Node, o caveman full continua ativo
por padrão; o que se perde é só o flag de modo (`/caveman lite|full|ultra`) e o
`/caveman-stats`, que dependem do hook em JS.

Nenhum caminho aqui usa `npm`, `npx` ou `node_modules`. O repositório não tem
`package.json`, e `tests/test_vendor_caveman.py` guarda esse invariante.

Créditos e procedência do caveman: [`vendor/CREDITS.md`](../vendor/CREDITS.md).
