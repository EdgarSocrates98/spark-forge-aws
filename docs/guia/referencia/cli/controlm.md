<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge controlm`

Conhecimento versionado do Control-M Automation API. Le matriz de versao; NAO le artefato, NAO chama BMC e NAO julga.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge controlm describe`](#sparkforge-controlm-describe) | O que vale numa versao do Automation API. Versao fora da faixa coberta sai como recusa NOMEADA, com o intervalo. |

## `sparkforge controlm describe`

O que vale numa versao do Automation API. Versao fora da faixa coberta sai como recusa NOMEADA, com o intervalo.

```bash
sparkforge controlm describe --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--version` | sim | texto |  |  | A versao do Automation API (ex.: 9.0.21.300). A faixa coberta e 9.0.21.200--9.0.22.100. |
| `--detail-level` | não | `minimal`, `compact`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o descritor inteiro -- e o modo de reauditoria. `compact` reduz `capabilities` a lista de slugs e tira `unresolved_detail` (`unresolved`, a mesma lista sem a razao, fica); `deprecated` continua INTEIRO, porque e a resposta direta a `o que eu nao posso mais usar` e cortar obrigaria uma segunda chamada para a MESMA pergunta. `minimal` reduz a `version`, `covers`, a CONTAGEM de `capabilities`, os SLUGS de `deprecated` e a CONTAGEM de `unresolved` -- a contagem nunca some, mesmo em zero, porque e a recusa nomeada da matriz; a lista de slugs e a razao de cada uma exigem `compact`/`full`. |

### Tool MCP equivalente

[`sparkforge_controlm_describe`](../tools/sparkforge_controlm_describe.md)
