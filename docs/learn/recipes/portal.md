# Receita — portal web local

**O quê:** `sparkforge-aws portal` sobe uma UI web local (127.0.0.1, sessão
por token) que expõe os MESMOS serviços do CLI — instalação, hosts de IA,
MCP, skills, agents, tarefas de diagnóstico, grafo e docs — com os mesmos
receipts e as mesmas recusas nomeadas.
**Por que:** nem todo mundo aprende um ecossistema por CLI. O portal mostra o
estado real (instalado/degradado/não instalado), o que cada host de IA
enxerga e deixa a mutação passar por plano → revisão → confirmação → recibo —
sem nunca inventar capacidade.
**Quando:** onboarding visual, demonstração do que a forja entrega, ou quando
você quer clicar num plano de instalação em vez de reler `--help`.
**Quando não:** automação/CI (a CLI é o caminho determinístico), nem durante
uma sessão de host — o portal é opcional e o ecossistema inteiro funciona
sem ele; ele nunca roda dentro do fluxo MCP.

## Problema

"Quero ver o que o SparkForge instalou, configurar meu host e rodar um
diagnóstico sem decorar a CLI."

## Pré-requisitos

`sparkforge-aws` instalado e os assets do portal vendored em `portal/assets/`
(vem no clone; `python scripts/vendor.py` no forge-portal regera). Python
3.10+, sem dependências novas — o servidor é stdlib puro.

## Passo a passo

```bash
# sobe o portal e abre o browser na URL com token de sessão
sparkforge-aws portal

# headless/SSH: só imprime a URL — o token vai no ?forge_session=
sparkforge-aws portal --no-browser

# aponta para outro workspace sem sair dele
sparkforge-aws portal --root ../meu-projeto-glue
```

Dentro do portal, em **Install**: *Plan* gera o dry-run real (mesma chamada
`lifecycle.install` do CLI), *Apply* pede confirmação explícita e devolve o
receipt `forge/*` idêntico ao do CLI. Em **Tasks**, descreva a intenção
("doctor da instalação") — só verbos seguros e read-only mapeiam; intenção
ambígua volta `SFA-PORTAL-AMBIGUOUS` com a lista do que existe. **Hosts**
mostra o estado real de cada host (READY/SUPPORTED/NEEDS_LOGIN/NOT_DETECTED)
e dá o comando para abrir — o portal não tem TTY, então "launch" devolve o
comando para você copiar, nunca executa cego.

## Verificação

```bash
sparkforge-aws doctor          # saúde que o dashboard mostra, no CLI
sparkforge-aws mcp verify      # mesmo handshake do card MCP — PASS + N tools
ls .sparkforge_aws/receipts/   # receipts escritos pelo portal OU pelo CLI
```

## Erros comuns

- **`SFA-PORTAL-NO-ASSETS`**: assets não vendored — rode `python
  scripts/vendor.py` no repo `forge-portal` (ou use o clone, que já os traz).
- **Página abre mas API 403**: a URL precisa do `?forge_session=` — use a URL
  impressa pelo comando, não `localhost:porta` manual.
- **`PORTAL-HOST` 403**: o servidor só fala com Host loopback
  (127.0.0.1/localhost/::1) — acessar por hostname de rede ou túnel é
  recusado de propósito (defesa contra DNS rebinding).
- **`PORTAL-ORIGIN` 403**: POST com Origin fora do loopback — chamadas
  vindas de outras páginas são recusadas; só a UI do próprio portal muta.
- **`PORTAL-RATE-LIMITED` 429**: mais de 10 mutações/min — aguarde a
  janela; o retry é sinalizado no envelope.
- **Install recusado `sparkforge_aws_ja_configurado`**: o `.mcp.json` do
  projeto já existe — o receipt nomeia o motivo; nada foi escrito.

## Veja também

`docs/reference/commands.md` (entrada `portal`), `forge-portal/docs/fase0/`
(arquitetura e matriz de segurança do portal), receitas
`instalar-e-comecar.md`, `verificar-mcp.md`.
