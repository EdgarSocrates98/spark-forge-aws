# Segurança: o que executa ao clonar, e o que nunca executa sozinho

O resumo está no [README](../../README.md). Aqui fica a lista do que roda na máquina
de quem abre o repositório, e a regra das operações destrutivas. O que um agente pode
fazer sozinho, o que pede confirmação e o que é proibido está em
[Política de segurança](usos/politica-de-seguranca.md).

## Superfície de execução

Clonar este repositório e abrir o Claude Code **executa código** antes de alguém digitar
qualquer coisa: hooks de `SessionStart` e o comando de cada servidor MCP. Um PR que toque
nesses arquivos não muda "a configuração do projeto" — muda o que roda na máquina de todo
contribuidor, e num diff grande passa como linha de JSON.

`tests/test_execution_surface.py` é a lista fechada disso. Não é allowlist de *padrão* —
padrão vaza, `node .*` autorizaria `node -e "..."` — é a **string exata** de cada comando,
em três superfícies: `.claude/settings.json` (nosso), o `plugin.json` do caveman
vendorizado (de terceiro) e os servidores de `.mcp.json`. Mudar qualquer uma obriga a
passar pelo teste, e a mudança aparece na revisão como o que de fato é.

Camada dois: um deny-list das construções que transformam um hook em canal de execução
arbitrária — `curl`/`wget`, `| sh`, `base64`, `eval`, `$(...)`, crase, `chmod +x`, `npm`.
`>/dev/null` e `2>&1` ficam de fora do deny-list de propósito: redirecionar não busca nem
decodifica nada, e o fallback legítimo usa os dois.

O que executa hoje, na íntegra (relido dos três arquivos em 2026-09-18):

| Superfície | Comando |
|---|---|
| `.claude/settings.json`, `PreToolUse` (`Bash\|Edit\|Write\|MultiEdit\|NotebookEdit`) | `python -m sparkforge.policy.hook` |
| `.claude/settings.json`, `SessionStart` | `command -v node >/dev/null 2>&1 \|\| { echo '...'; cat "$CLAUDE_PROJECT_DIR/vendor/caveman/src/rules/caveman-activate.md"; }` |
| `vendor/caveman` plugin, `SessionStart` | `node "${CLAUDE_PLUGIN_ROOT}/src/hooks/caveman-activate.js"` |
| `vendor/caveman` plugin, `UserPromptSubmit` | `node "${CLAUDE_PLUGIN_ROOT}/src/hooks/caveman-mode-tracker.js"` |
| `.mcp.json` | `python -m sparkforge.adapters.mcp --transport stdio` |

O `PreToolUse` é o hook da policy de `.sparkforge/policy.yaml`: ele bloqueia as regras
`deny` antes de o comando rodar. O que ele cobre e o que fica em `permissions.ask` está
em [Política de segurança](usos/politica-de-seguranca.md).

Os dois hooks em JS são código de terceiro. Auditados em 2026-08-07 no SHA pinado:
**nenhuma chamada de rede**, um único `execFileSync` em forma argv (sem shell, sem caminho
de injeção), e escritas confinadas a `~/.claude/.caveman-*` e aos arquivos de agente do
próprio plugin. `caveman-stats.js` **lê os transcripts de sessão** (`~/.claude/projects/**`)
para calcular economia de token — leitura local, sem rede.

`.claude/settings.local.json` é por máquina e nunca commitado: guarda o allowlist de
permissões de quem trabalha ali. Está no `.gitignore` do repositório desde 2026-08-07 —
antes disso dependia do gitignore global de uma máquina só.

## Operações destrutivas

As Skills não executam automaticamente alterações destrutivas. Operações como expiração
de snapshots, remoção de arquivos órfãos, mudanças de particionamento e overwrite devem
ser propostas com escopo, retenção, dry run quando disponível e plano de rollback.

As onze skills AWS complementares são a exceção que confirma a regra: elas podem mutar
infraestrutura viva, e por isso são não-despacháveis e exigem confirmação explícita do
operador por comando de escrita (veja [Agents e skills](05-agents-e-skills.md#skills-aws-oficiais-complementares)).

## Próximos passos

- [Política de segurança](usos/politica-de-seguranca.md): `policy check`, `policy explain` e `policy sync-settings`.
- [Ecossistema caveman](10-caveman.md): de onde vêm os hooks de terceiro.
- [Mudança de configuração e sandbox](usos/change.md): mudar numa cópia, nunca na árvore do operador.
