# docs/superpowers

Registro do processo anterior de especificação, feito com o ciclo do plugin
superpowers (brainstorm, spec, plano, execução).

| Pasta ou arquivo | Estado |
|---|---|
| `specs/` | **congelada**: registro histórico, não recebe spec novo |
| `plans/` | **congelada**: registro histórico, não recebe plano novo |
| `STATUS.md` | **viva**: continua a fonte da verdade das fases e dos números correntes |

O mapa transversal das entregas atuais está em
[`docs/EVOLUTION-CURRENT.md`](../EVOLUTION-CURRENT.md); ele aponta para os SDDs
de control plane, streaming, Forge Lab e economia observada sem reescrever o
histórico congelado.

Spec novo nasce em `docs/sdd/<FEATURE>/`, pelas skills `sdd-*` e conferido por
`sparkforge-aws sdd check`. O fluxo está em [`docs/sdd/README.md`](../sdd/README.md).

Spec antigo que ficou obsoleto não é reescrito: ganha uma seção de desvios. O
histórico do plugin AgentSpec, que também especificou frentes deste
repositório, está em `docs/sdd/archive/agentspec/`, sem edição.

Por que as pastas ficam aqui em vez de mudarem de lugar: dezenas de documentos,
inclusive os auditados pelo gate de lastro, citam estes caminhos.
