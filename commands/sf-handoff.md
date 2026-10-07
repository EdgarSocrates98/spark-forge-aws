---
name: sf-handoff
description: Escreve .sparkforge_aws/handoff.md e diz exatamente o que commitar ao encerrar ou passar a investigação para outra sessão/ferramenta.
---

Você vai encerrar (ou pausar) esta sessão de investigação e deixar o estado
pronto para outra pessoa, outra ferramenta, ou uma sessão futura sua mesmo
retomarem de onde parou.

Rode:

```
sparkforge-aws handoff --repo <raiz-do-repo> [--findings <arquivo-de-findings.json>] [--unresolved <n>] [--in-flight "<descrição>"]
```

Isso escreve `.sparkforge_aws/handoff.md` (leitura humana) a partir do mesmo payload
que `/sf-resume` usaria (leitura de máquina) — os dois nunca divergem porque vêm
da mesma função.

## O que commitar

Commite:

- `.sparkforge_aws/case.yaml`
- `.sparkforge_aws/facts.json` (se existir)
- `.sparkforge_aws/findings.json` (se existir)
- `.sparkforge_aws/handoff.md`
- `.sparkforge_aws/artifacts/manifest.json` (se existir)

Esses arquivos são pequenos, derivados, e são o barramento de handoff entre
sessões — é o que sobrevive à troca de sessão ou de ferramenta.

## O que **não** commitar

**`.sparkforge_aws/artifacts/**` nunca deve ser commitado**, exceto o
`manifest.json` acima. É onde ficam os artefatos brutos coletados (event logs,
planos físicos, saída de Terraform) — podem conter dados de negócio e chegar a
centenas de MB. O `.gitignore` do repositório já bloqueia isso
(`.sparkforge_aws/artifacts/*` com exceção só do `manifest.json`); não force a
adição desses arquivos com `git add -f`.

Antes de encerrar, confira `git status` e mostre ao usuário exatamente o que vai
ser commitado.
