# Economia de tokens e contexto — Spark Forge AWS

## Por que não carregar tudo

Cada skill, agent e tool MCP publicada no host custa contexto de sistema.
143 tools MCP, 52 com `detail_level` (summary|normal|full). O Context Gateway tem três perfis: `economy` (8/3/8 caps, ~6KB), `balanced` (16/6/16, ~16KB), `deep` (32/12/32, ~30KB). `sparkforge-aws economy report` mede `payload_bytes` por chamada; tokens de provider só existem com transcript de host — senão, `tokens_unresolved`. Não carregue as 60 skills de uma vez: a skill certa vem pelo `sparkforge-aws next-step`, não por leitura de todas.

## Progressive disclosure

O modelo do ecossistema: o host recebe *índices* (nomes + uma linha), não
o corpo dos documentos. A skill certa é carregada quando a tarefa chega —
`capabilities`/`next-step`/`agents` respondem "o que existe" sem gastar
o que o conteúdo custa.

## O que é medido vs estimado

Recibos de instalação carregam `context`: `skills_bytes`, `agents_bytes`,
`managed_bytes`, `mcp_entries`, `managed_entries`, `tools_exposed` — bytes
observados em disco, não tokens. Estimativas de token são marcadas como
tal; claims de economia percentual exigem baseline do mesmo caso.

## Quando o que usar

| Situação | Caminho mais barato |
|---|---|
| resposta determinística possível | CLI direto (zero modelo) |
| julgamento sobre facts | skill especializada via host |
| investigação multi-etapa | coordinator/playbook |
| catálogo de tools | MCP `tools/list` uma vez, depois `tools/call` |

## Instalação por perfil

`minimal` publica o mínimo de contexto; `recommended` é o padrão
equilibrado; `full` publica tudo — escolha `full` só quando o host vai
usar a superfície inteira, caso contrário é contexto pago sem retorno.
