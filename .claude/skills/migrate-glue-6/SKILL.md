---
name: migrate-glue-6
description: Use quando alguém pergunta "dá para subir esse job para o Glue 6.0?", "o que quebra se eu migrar de 4.0/5.0/5.1 para 6.0?", "vale a pena migrar por causa dos 30% mais barato?" ou precisa de um plano de migração entre versões de runtime do AWS Glue. Use também quando o job já foi migrado e passou a falhar com `NoSuchMethodError`, `NoSuchFieldError` ou erro de ANSI mode. Se você está prestes a ler o guia de migração da AWS e comparar com o código no olho, rode `sparkforge migrate glue <dir> --from X --to Y` em vez disso — o motor expande o par em degraus, julga cada um com o catálogo versionado e devolve os eixos que **não** foram avaliados em vez de deixá-los passar como aprovados.
---

# Migrate Glue 6

Migração de runtime não é uma pergunta sobre a versão de destino — é uma pergunta sobre cada **degrau** entre origem e destino. Um salto de 4.0 para 6.0 passa por 5.0 e 5.1, e os breaking changes se acumulam: um salto direto esconde os do meio. O motor faz essa expansão; seu trabalho é apontá-lo para o diretório certo e ler o que ele diz que **não** sabe.

## Procedimento

1. `sparkforge migrate glue <dir-do-job> --from 5.1 --to 6.0`

   **Diretório, não arquivo.** Um pin de `requirements.txt` e um `.jar` de Scala 2.12 sobrevivem à troca de runtime e não têm linha de fonte Python. O comando compõe código, `.jar`, `requirements*.txt`, os `.tf` quando existem e o inventário de consumidores em `.sparkforge/consumers.yaml`.

   `--from` e `--to` não têm default. Um par embutido responderia sobre um alvo que ninguém declarou.

2. Leia `report` antes de `findings`. As duas visões convivem: `findings` guarda a cardinalidade por degrau e responde "isto ainda vale depois do próximo salto?"; `report` colapsa cada problema uma vez, com todos os degraus em que ele vale, e é a contagem honesta para um humano.

3. Leia `gates` e `missing_evidence` **juntos**. `BLOCKED` não é falha do comando: é o eixo dizendo que não foi avaliado, com a evidência que o destravaria escrita ao lado.

4. `sparkforge glue dependency-audit <dir> --glue 6.0` para a lista de pins e binários com o achado que cada um produziu.

## O que esta análise nunca pode aprovar

Quatro eixos exigem execução real contra AWS viva, e nascem `BLOCKED` sempre: **dados** (reconciliação), **performance**, **custo** e **canary**. `recommendation` nunca é `GO` aqui — o melhor desfecho possível é `CONDITIONAL_GO`. Se alguém pedir um "GO" desta ferramenta, a resposta é que ela não emite: quem emite é a execução comparada.

Outros três — `iam_kms`, `rede`, `cross_account` — são nomeados pelo contrato e não têm regra nenhuma que os preencha. Também nascem `BLOCKED`, e a diferença entre isso e "passou" é a razão de eles existirem no contrato.

## Preço não é performance

A AWS anunciou 30% de redução no Glue 6.0 ([`knowledge/glue/pricing.yaml`](../../knowledge/glue/pricing.yaml)). O anúncio não nomeia a versão de comparação, não recorta por região nem por tipo de worker, e a página de pricing publica um preço único que **não** diferencia por versão de runtime. Nada aqui permite calcular o custo do seu job em 6.0 contra 5.1.

E preço 30% menor não é performance 30% maior. Para medir performance entre runtimes é preciso executar nos dois: `sparkforge benchmark --before <facts> --after <facts> --before-runtime 5.1 --after-runtime 6.0`. Sem os dois rótulos, o eixo de runtime volta como `missing_runtime_label`; com rótulos iguais, `same_runtime_label`, porque comparar um runtime consigo mesmo não prova nada sobre trocar de runtime.

## Referência rápida

| Área do catálogo | O que julga |
|---|---|
| `SF-MIG` | Breaking changes entre versões de Glue — SDK v1, EMRFS, config morta, cast sob ANSI |
| `SF-SPARK4` | Fronteira do Apache Spark 4 — config renomeada, API removida, piso de dependência, binário de Scala |
| `SF-LF` | Lake Formation FGAC contra o resto da configuração do job |
| `SF-ENV` | Ambiente e consumidor — inclui a armadilha de format v3 lido por Athena |

Limiares, severidade e `runtime_scope` vêm de `sparkforge rules lookup --id <ID>`, nunca de memória.

Aprofundamento sob demanda, não aqui: [`docs/aws/glue/6.0/README.md`](../../docs/aws/glue/6.0/README.md) é a porta de entrada, [`docs/aws/glue/6.0/decision-guide.md`](../../docs/aws/glue/6.0/decision-guide.md) sustenta "ficar na versão anterior" como resposta legítima, e [`docs/aws/glue/6.0/known-unknowns.md`](../../docs/aws/glue/6.0/known-unknowns.md) reúne o que ninguém mediu.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime.
Mudar a versão de runtime de um job em produção é mudança operacional e manutenção
destrutiva você **não executa** — recomende, e a decisão de janela, rollback e escopo
**sobe a quem pode ser perguntado**: o agente pai que despachou, ou o operador na sessão.

Um gate `BLOCKED` não vira `PASS` por julgamento seu. Se o relatório precisa de dados,
performance, custo ou canary, o que sobe é o pedido de execução comparada — não uma
estimativa com forma de medição.

## Quando NÃO usar

- A pergunta é sobre **compatibilidade do código com o Apache Spark 4** e não sobre o empacotamento do Glue: use `spark4-compatibility`, que separa a fronteira do Apache da fronteira da AWS.
- A pergunta é sobre **subir o format version de uma tabela Iceberg**: use `iceberg-v3-readiness` — é outra decisão, com outros consumidores.
- A pergunta é sobre **FGAC do Lake Formation**: use `lakeformation-fgac-guard`.
- O job já está no runtime alvo e está lento ou caro: isto é tuning, não migração — use `tune-glue-job`.

## Red flags

- **"O assessment saiu limpo, então pode migrar."** Ele nunca sai limpo: quatro eixos nascem `BLOCKED`. Assessment sem finding significa "o catálogo não achou nada no código", não "a migração é segura".
- **"Vou pular de 4.0 direto para 6.0."** O comando faz isso, mas o relatório mostra os degraus justamente porque os breaking changes se acumulam. Ler só o total esconde qual salto introduziu o quê.
- **"Aponta para o `.py` principal."** Aí você não vê pin de dependência, `.jar`, Terraform nem consumidor — que é onde moram os achados que não têm linha de fonte Python.
- **"A AWS diz 30% mais barato, então o custo cai 30%."** Ver acima: o anúncio não tem baseline declarada, e este repositório recusa multiplicar duas fontes que não falam da mesma coisa.
