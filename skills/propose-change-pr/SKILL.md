---
name: propose-change-pr
description: Use quando o operador quiser levar ao repositório uma mudança de configuração que já passou pelo sandbox — "abre o PR dessa mudança", "propõe essa troca", "o sandbox passou, e agora?". A sessão monta o pacote com `sparkforge_change_propose` e roda os comandos git/gh do `commands.md` passo a passo, PARANDO para confirmação explícita antes de `git push` e de `gh pr create`. O pacote nunca roda git; quem roda é a sessão, com aprovação humana.
---

# Propose Change PR

O L3 do §15 é "propor para produção": abrir o PR, anexar a evidência e pedir aprovação humana. O SparkForge MONTA o pacote em `.sparkforge/proposal/<id>/` e não executa nada. Esta skill é o lado do host: ela lê o pacote, roda os comandos na árvore do operador e para onde o operador precisa decidir.

## Antes de começar

1. Tenha um sandbox que aplicou: `sparkforge_change_sandbox` (ou `sparkforge change sandbox --repo . --diff <arquivo>`) com `applied: true`. Guarde o `id`.
2. Leia `new` e `resolved` do sandbox. Achado novo P0/P1 faz o `propose` recusar; não contorne.
3. Se houver medida de verdade (dois runs no `benchmark`, um `funcval compare`), tenha os arquivos de facts à mão. Sem eles, o PR sai com a medida PENDENTE — e está certo sair assim.

## O laço

1. `sparkforge_change_propose` com `repo`, `sandbox_id`, `now` (instante ISO 8601) e, se houver, `benchmark_paths` e `funcval_path`.
2. `refused` não vazio: relate `reason`, `detail` e `unlock` ao operador e pare. `sandbox_desatualizado` pede um sandbox novo sobre a árvore atual; `achado_novo_bloqueante` pede corrigir a mudança.
3. Com o pacote gravado, mostre ao operador o `pr_body.md` e o `change.patch`.
4. Rode o `commands.md` na ordem, um passo por vez: `git switch -c`, `git apply --check`, `git apply`, `git add`, `git commit -F`.
5. **PARE** e peça confirmação explícita antes de `git push -u origin <branch>`.
6. **PARE** de novo e peça confirmação explícita antes de `gh pr create --body-file .../pr_body.md`.
7. Relate a URL do PR e o caminho do rollback (`rollback.patch`, ou `git revert` depois do merge).

Se um passo falhar (`git apply --check` recusa, conflito, branch que já existe), pare e relate. Não conserte o patch nem force o passo.

## Quando NÃO usar

- Sem sandbox que aplicou: comece por `sparkforge change plan` e `sparkforge change sandbox`.
- Para aplicar a mudança direto na branch principal ou em produção: isso é L4, e não existe aqui.
- Para decidir o valor da configuração: isso é `sparkforge_tune` (ou o operador), e o valor já está no diff validado.
- Para afirmar ganho: o PR não mede desempenho; a diferença de achados não é ganho.

## Referência rápida

| Passo | Tool MCP | CLI |
|---|---|---|
| diff de configuração | `sparkforge_change_plan` | `sparkforge change plan --facts ... --repo . --set k=v --out d.patch` |
| diff numa cópia | `sparkforge_change_sandbox` | `sparkforge change sandbox --repo . --diff d.patch` |
| pacote do PR | `sparkforge_change_propose` | `sparkforge change propose --sandbox <id> --repo .` |
| conferir o corpo | `sparkforge_report_verify` | `sparkforge report verify --report pr_body.md --findings <after>/.sparkforge/scan/findings.json` |

Recusas do `propose`: `sandbox_inexistente`, `sandbox_nao_aplicado`, `sandbox_desatualizado`, `achado_novo_bloqueante`, `caminho_fora_da_raiz`.

## Não faz

- `git push --force`, `git push` para a branch principal, merge ou aprovação do próprio PR.
- `git push` ou `gh pr create` sem a confirmação explícita do operador naquele momento.
- Editar `change.patch`, `pr_body.md` ou o bloco de assinatura: o corpo editado deixa de conferir no `report verify`.
- Abrir o PR com outro corpo que não o `pr_body.md` gerado.

## Red flags

- A sessão rodando `git push` ou `gh pr create` sem ter parado para perguntar.
- PR aberto com `refused` não vazio, ou a partir de um sandbox de outra árvore.
- Frase de ganho ("fica mais rápido", "reduz o custo") acrescentada ao corpo.
- Patch "ajustado" à mão depois de `git apply --check` recusar.
