# Freshness das fontes: quando o SparkForge deixou de saber

Toda regra cita a documentacao que a sustenta, com a data em que alguem a leu
(`sources[].retrieved`). `knowledge/sources.lock.json` diz, por URL:
- se a pagina tem versao no caminho (`pinned`);
- se ja foi conferida por hash (`sha256`, `checked_at`);
- desde 2026-09-11, **quando o hash mudou pela ultima vez** (`changed_at`).

Com as duas coisas, o estado de cada fonte e calculavel, e sai junto do achado.

## Estados, na ordem de precedencia

| Estado | Quando | Motivo que sai |
|---|---|---|
| `unresolved` | O lock nao existe, nao le, ou nao tem a URL | `lock_ausente`, `lock_ilegivel`, `fora_do_lock` |
| `fixed` | URL com versao no caminho | `versao_no_caminho` |
| `stale` | O hash mudou **depois** da data em que a regra (ou o documento) validou a fonte | `mudou_depois_da_validacao`, com as duas datas |
| `unverified` | URL movel nunca conferida por hash | `nunca_conferida` |
| `aging` | Conferida, sem mudanca, ha mais de 14 dias | `conferida_ha_N_dias` |
| `fresh` | Conferida, sem mudanca, ha 14 dias ou menos | `conferida_ha_N_dias` |

Tres regras completam a tabela:
- **`conflicted`** nao e estado: sai ao lado dele quando o lock registra, para a mesma URL, uma leitura em data diferente da que a regra declara.
- **A mesma URL** citada por duas regras com datas diferentes usa a validacao **mais antiga**: se a pagina mudou depois de qualquer validacao, alguem precisa reler.
- **Fonte sem URL** (`note`/`origin`) nao recebe estado; entra na contagem como `sem_url`.

**O limiar de 14 dias e convencao, e nao medida.** Nenhuma fonte diz quantos
dias uma conferencia leva para envelhecer. O numero corresponde a duas rodadas
perdidas do refresh semanal (`refresh-knowledge.yml`, segunda 06:00 UTC), e sai
em `freshness_policy.basis` junto de cada resposta (regra 11).

## Onde aparece

Sempre por pedido explicito: a resposta sem a flag e a mesma para o mesmo
catalogo em qualquer dia, que e o que o `rules_lookup` promete.

| Verbo | Flag | O que ganha |
|---|---|---|
| `sparkforge judge` / `sparkforge_judge` | `--source-freshness` / `source_freshness: true` | `source_freshness` (so as URLs citadas na pagina) e `freshness_policy` |
| `sparkforge rules lookup` / `sparkforge_rules_lookup` | idem | idem, para as regras da pagina |
| `sparkforge knowledge path` / `sparkforge_knowledge_path` | idem | Com `--file`, o estado de cada URL da secao `Fontes` do documento; sem `--file`, `freshness_by_doc` (contagem por estado) |
| `sparkforge report github` | `--source-freshness` | Secao "Fontes que pedem releitura" no resumo do PR |

Detalhes que valem para todos:
- `--as-of AAAA-MM-DD` fixa o dia de referencia; sem ele, e hoje em UTC.
- `SPARKFORGE_SOURCES_LOCK` aponta um lock avulso sem trocar a raiz de knowledge. E assim que o golden `fixtures/sarif/freshness` usa lock sintetico.
- O resumo do PR lista um por um so os findings com fonte `stale` ou `aging`. Os que citam fonte `unverified` saem numa linha so, com a contagem: com a maioria das fontes nesse estado, lista-los afogaria o resumo.
- O executor `sf-verifier` pede o estado na checagem 6. Um achado com fonte `stale` fica `open`, com "fonte mudou em X, depois da validacao de Y", e nao sai confirmado sem alguem reler.

O estado nunca entra no `Finding` nem no `findings.json`: um achado e
deterministico, e o estado depende do lock e do dia.

## `changed_at`

`scripts/refresh_knowledge.py --update` grava `changed_at` com a data do dia
quando o hash conferido e diferente do anterior. As outras situacoes:
- hash igual: o `changed_at` anterior e preservado;
- fonte nova: nao ganha `changed_at` (nao ha antes para comparar);
- fonte inalcancavel: mantem a entrada anterior inteira;
- `--offline`: preserva o `changed_at` e nunca o cria.

Revalidar uma fonte e reler a pagina e subir o `retrieved` da regra (ou do
documento) para uma data igual ou posterior ao `changed_at`.

**O leitor da secao `Fontes`** mora em
`sparkforge/knowledge_freshness.py::fontes_de_knowledge`, e o script importa
dele: uma copia so, usada tanto pelo refresh quanto pelo `knowledge_path` no
pacote instalado.

## Distribuicao medida em 2026-09-11 (`as_of` 2026-09-11)

Sobre o catalogo (190 regras) e o lock reais:

| | `fixed` | `unverified` | `aging` | `fresh` | `stale` | `sem_url` |
|---|---|---|---|---|---|---|
| Citacoes de fonte em regra (267) | 21 | 157 | 40 | 0 | 0 | 49 |
| URLs distintas citadas por regra (115) | 9 | 87 | 19 | 0 | 0 | — |
| URLs da secao `Fontes` de `knowledge/` (219, em 28 documentos) | 15 | 188 | 16 | 0 | 0 | — |

Tres leituras dessa tabela:
- **Nenhuma fonte esta `fresh`.** A ultima conferencia com rede foi em 2026-07-31 para quase todas, e a mais recente, com 16 dias, ja passa do limiar. O refresh semanal nao entra na `main` ha cerca de seis semanas.
- **Nenhuma fonte esta `stale` porque o `changed_at` nasce nesta frente.** O lock ainda nao registrou mudanca nenhuma, e o estado passa a ser alcancavel a partir do proximo refresh com rede.
- **13 das 115 URLs de regra** tem leitura em data diferente da que a regra declara (`conflicted`).

Os numeros mudam a cada refresh do lock e com a passagem do tempo; esta tabela
e a medida de uma data, e nao um teste.

## Knowledge Drift Radar: o que uma fonte que mudou arrasta

O estado responde "esta fonte mudou depois de eu le-la?". O radar (§17 de
`prompt_new_evo.md`, 2026-09-13) responde a pergunta seguinte: **o que precisa
ser relido e rodado de novo**.

```bash
sparkforge knowledge drift [--source <url do lock>] [--as-of AAAA-MM-DD]
```

O filtro chama `source`, e nao `url`, de proposito: o INV-009 recusa argumento
de tool com `url` no nome, porque tool nenhuma acessa a rede. O valor e so a
chave de uma entrada do lock, comparada por igualdade.

A tool MCP e `sparkforge_knowledge_drift` (`READ_ONLY`, sem parametro de
caminho). O dono e o `sf-verifier` (checagem 8). Para cada fonte do lock com
`changed_at` e que nao e fixa por versao:

| Campo | O que traz |
|---|---|
| `citations` | Cada regra e documento que cita a fonte, com o `retrieved` declarado (o mais antigo) e o estado |
| `impact.rules` / `impact.docs` | As citacoes `stale`, lidas **antes** da mudanca: o que reler |
| `impact.goldens` | Os fixtures cujo `expected/findings.json` tem uma dessas regras: o que rodar de novo |
| `impact.evals` | Os arquivos de `evals/` que citam uma dessas regras |
| `impact.agents` | Os agentes que declaram a area da regra em `rule_areas` ou citam o `rule_id` |
| `revalidated` | As citacoes lidas no dia da mudanca ou depois: alguem ja releu |

So entra ligacao que existe em arquivo. Instalado por pip, o wheel nao leva
`fixtures/`, `evals/` nem `agents/`, e esses tres saltos saem `unresolved` com
`sem_repositorio` -- nunca como lista vazia, que pareceria "nada afetado". O
radar **nao** diz se a mudanca tocou o trecho que a regra cita: o lock guarda o
hash da pagina inteira (`refused: conteudo_da_mudanca`).

O relatorio do refresh semanal ganha a secao "Impacto" com a **mesma** conta,
feita sobre o lock que acabou de ser conferido.

### Pre-requisito do operador

**O refresh semanal nao abre PR desde 2026-08-10.** As cinco execucoes agendadas
desde entao falharam no passo do PR com `GitHub Actions is not permitted to
create or approve pull requests`: a conferencia roda e o lock e commitado na
branch, mas o PR e barrado pela configuracao do repositorio. Enquanto isso
durar, nenhuma fonte ganha `changed_at` e o radar nao tem o que mostrar. O
conserto e ligar, em Settings -> Actions -> General, "Allow GitHub Actions to
create and approve pull requests".
