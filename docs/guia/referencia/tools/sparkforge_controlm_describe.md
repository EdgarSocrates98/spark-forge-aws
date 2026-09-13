<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_controlm_describe`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

O que vale numa versao do Control-M AUTOMATION API: quais capacidades existem, quais ja foram depreciadas, e quais exigencias de componente estao em vigor. Le a matriz de `knowledge/controlm/` -- nao le artefato do operador, nao chama a BMC e NAO JULGA. O ESCOPO VEM ANTES DA RESPOSTA: esta matriz e do Automation API e NAO do produto Control-M. As duas coisas usam a grafia `9.0.2x.yyy` e nao sao a mesma -- do lado do produto, so `9.0.21.300` e `9.0.22` abrem raiz de documentacao, e `9.0.22.100` esta atras de login de entitlement. DOIS EIXOS, porque a fonte tem dois tipos de afirmacao: `capabilities`/`deprecated` sao capacidade com FRONTEIRA de versao (`Job:DetachedEmbeddedScript` existe a partir de `9.0.22.005`), e `components` e componente com EXIGENCIA (Java 11 deixa de ser suportado em `9.0.21.325`). Cada item traz `declared_at`, a versao onde a fronteira foi lida, porque a resposta em `9.0.22.060` sobre Java vem de `9.0.21.325` e nao de leitura nova. VERSAO FORA DA FAIXA E RECUSA NOMEADA com o intervalo, nunca extrapolacao: a faixa e passado FECHADO, e a fonte publica versoes acima dela. Dentro da faixa, versao que a fonte nao publica tambem e recusa -- ela anda de 5 em 5, e `9.0.21.301` nao existe. `unresolved` nomeia o que a fonte nao sustenta, incluindo as 9 versoes da faixa que a pagina cita sem afirmar nada.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `version` | string | sim | A versao do Automation API (`9.0.21.300`). A faixa coberta e `9.0.21.200` a `9.0.22.100`. |
| `detail_level` | string: `minimal`, `compact`, `full` | não | Verbosidade da saida. `full` (default) devolve o descritor inteiro -- e o modo de reauditoria. `compact` reduz `capabilities` a lista de slugs e tira `unresolved_detail` (`unresolved`, a mesma lista sem a razao, fica); `deprecated` continua INTEIRO, porque e a resposta direta a `o que eu nao posso mais usar` e cortar obrigaria uma segunda chamada para a MESMA pergunta. `minimal` reduz a `version`, `covers`, a CONTAGEM de `capabilities`, os SLUGS de `deprecated` e a CONTAGEM de `unresolved` -- a contagem nunca some, mesmo em zero, porque e a recusa nomeada da matriz; a lista de slugs e a razao de cada uma exigem `compact`/`full`. |

## Na CLI

[`sparkforge controlm describe`](../cli/controlm.md)

## Capacidade

describe what a Control-M Automation API version supports

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
