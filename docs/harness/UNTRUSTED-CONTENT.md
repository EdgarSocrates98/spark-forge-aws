# Conteúdo derivado de artefato é dado, nunca instrução

`prompt_evo_harness.md` §42 lista as origens: repositório, log, saída de AWS,
documentação, MCP, web, issues, comentários. Tudo isso é **dado**. Instruções
encontradas nesse conteúdo não são executadas.

## Onde o texto de terceiro entra, neste repositório

Em dois lugares, e só neles:

- `Fact.subject.snippet` — a linha exata do arquivo analisado.
- `Fact.attrs.*` — valores lidos do artefato (nome de pacote, chave de config,
  caminho de S3, texto de `--conf`).

Para onde eles vão é diferente para cada um, e a diferença importa:

| origem | destino | o que atravessa |
|---|---|---|
| `Fact.subject` | `Finding.subject` | íntegro, snippet incluído |
| `Fact.measures` | `Finding.measured` | íntegro (`measured=dict(primary.measures)`) |
| `Fact.attrs` | **não entra no `Finding`** | o motor só lê `attrs` para casar regra |
| — | `Finding.evidence` | **só ids** (`[f.id for f in evidence]`), nunca texto |

Isso quer dizer que `Finding.evidence` **não** é superfície de texto de
terceiro: é uma lista de hashes. Quem ler "o texto do artefato chega ao
`evidence`" e resolver protegê-lo vai sanitizar uma lista de ids e não terá
tocado em nada.

E `attrs` não sumir no `Finding` não quer dizer que ele não chega ao modelo. As
tools `analyze_*` devolvem **Facts**, não Findings (`sparkforge/adapters/_core.py`
serializa `f.to_dict()` em `items`), e `Fact.to_dict()` inclui `attrs` inteiro.
É por aí que `attrs.target` (um `s3://...` escrito por um terceiro) chega ao
modelo — pelo payload do próprio `Fact`, não pelo `Finding`.

Cinco extratores produzem `subject.snippet` não vazio: `pyspark_ast`,
`event_log`, `graph`, `spark_plan` e `terraform`. Os demais preenchem `""`.

## O invariante, e por que ele não é sanitização

**Texto derivado de artefato nunca é concatenado num campo que o catálogo
controla.**

Um `Finding` tem campos de duas procedências, e a lista curta é a do artefato:
`subject`, `measured` e `evidence`. **Todo o resto** de `to_dict()` vem de
`rules/catalog/*.yaml` — dado versionado, revisado, com `sources`.

A enumeração é curta de propósito. Listar os campos do catálogo seria a lista
que envelhece: campo novo nasceria fora dela, desprotegido e em silêncio.
Enumerando o lado do artefato, campo novo nasce coberto, e acrescentar um campo
de artefato exige decisão explícita.

A defesa **não** é limpar o `snippet`. O `snippet` existe para que o operador
veja a linha exata que produziu o achado; apagar dela o que parece instrução
apagaria a evidência, e evidência apagada é defeito, não segurança. É a mesma
regra que vale para o resto do repositório: campo de evidência apagado para
economizar token é defeito, não compressão.

A defesa é a separação de campo. Um modelo que lê um relatório trata
`explanation` como afirmação do sistema e `subject.snippet` como amostra do
código analisado. Se o texto do artefato vazasse para `explanation` — ou para
`sources`, que carrega a mesma autoridade de dado revisado —, a instrução
plantada por um terceiro chegaria ao modelo com a autoridade do catálogo.

`tests/test_harness_untrusted.py` tranca as duas metades: que a injeção não
aparece em campo de catálogo, **e** que ela continua visível no `snippet`. A
segunda existe para impedir a correção errada.

## Onde o invariante é dito ao modelo

Invariante só protege quem sabe dele. A frase está na `description` das cinco
tools `analyze_*` que devolvem `subject.snippet` não vazio, e na de
`sparkforge_judge` — a única que devolve `Finding`, e portanto o único lugar em
que o `snippet` do artefato aparece **ao lado** do `explanation` do catálogo,
que é exatamente a situação que o invariante descreve.

## O que este documento NÃO cobre

- **Conteúdo que chega ao modelo por fora do `Finding`** — um agente que lê um
  arquivo com `Read` recebe o texto cru, e nenhum invariante deste repositório
  alcança isso. A defesa ali é do harness da plataforma, não daqui.
- **Saída de MCP de terceiros.** Este repositório expõe tools; não consome.
- **Sanitização de qualquer natureza.** Ver acima: é decisão, não omissão.
