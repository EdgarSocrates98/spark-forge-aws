# Política de segurança

## Versões cobertas

Só a linha mais recente em `main` recebe correção. O projeto está em `0.x` e não mantém
branches de versões antigas.

## Como reportar uma vulnerabilidade

**Não abra issue pública.** Use o reporte privado do GitHub:

1. Aba **Security** do repositório.
2. **Report a vulnerability**.

Inclua:

- o que acontece e o que deveria acontecer;
- o passo mínimo que reproduz (commit, comando ou chamada de tool MCP e os argumentos);
- o impacto que você enxerga: execução de código, leitura fora da raiz, vazamento de
  segredo, escrita não autorizada.

Use dado **sintético** no reporte. Não anexe event log, dump de catálogo, credencial ou
qualquer artefato de produção: o repositório é público e caso real nunca entra em arquivo
aqui.

O projeto é mantido por uma pessoa. A resposta é por melhor esforço, sem prazo garantido.
Quem reportou é avisado quando a correção entrar em `main`.

## O que é escopo

- **Superfície de execução**: o que roda ao abrir o repositório no Claude Code (hooks de
  `SessionStart` e comandos dos servidores MCP). A lista fechada está em
  `tests/test_execution_surface.py`, e a seção "Segurança" do `README.md` a descreve.
- **Tools MCP e CLI**: leitura ou escrita fora da raiz do repositório, argumento que
  alcança arquivo sem passar por `sparkforge.paths.resolve_within`, tool marcada como
  só leitura que grava.
- **Política** (`.sparkforge/policy.yaml`, hook `PreToolUse`, `permissions.ask`): comando
  que deveria ser negado e passa.
- **Coletores AWS** (`collect *`): chamada que muda estado do lado da AWS. Eles só leem.
- **Journal e artefatos commitáveis** (`.sparkforge/journal.jsonl`, `case.yaml`,
  blackboard): valor literal de argumento sensível gravado onde só deveria haver hash.

## O que não é escopo

- Código vendorizado em `vendor/` (ecossistema caveman): reporte ao projeto de origem.
  Procedência e licença em `vendor/CREDITS.md`.
- Recomendação de tuning ou achado de regra considerado errado: isso é defeito de
  conhecimento, e vai por issue pública com fixture sintética.
- O pacote não chama provider de modelo (regra 23 do `CLAUDE.md`), e nenhuma tool acessa
  rede fora dos coletores AWS. Reporte que dependa de o pacote chamar modelo não se
  aplica a este código.
