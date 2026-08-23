# Conteúdo derivado de artefato é dado, nunca instrução

`prompt_evo_harness.md` §42 lista as origens: repositório, log, saída de AWS,
documentação, MCP, web, issues, comentários. Tudo isso é **dado**. Instruções
encontradas nesse conteúdo não são executadas.

## Onde o texto de terceiro entra, neste repositório

Em dois lugares, e só neles:

- `Fact.subject.snippet` — a linha exata do arquivo analisado.
- `Fact.attrs.*` — valores lidos do artefato (nome de pacote, chave de config,
  caminho de S3, texto de `--conf`).

Os dois atravessam para `Finding.subject` e `Finding.evidence`.

## O invariante, e por que ele não é sanitização

**Texto derivado de artefato nunca é concatenado num campo que o catálogo
controla.**

Um `Finding` tem campos de duas procedências. `title`, `explanation`,
`expected_effect`, `proposed_change`, `risks`, `tradeoffs`, `validation` e
`rollback` vêm de `rules/catalog/*.yaml` — dado versionado, revisado, com
`sources`. `subject` e `evidence` vêm do artefato, que ninguém revisou.

A defesa **não** é limpar o `snippet`. O `snippet` existe para que o operador
veja a linha exata que produziu o achado; apagar dela o que parece instrução
apagaria a evidência, e evidência apagada é defeito, não segurança. É a mesma
regra que vale para o resto do repositório: campo de evidência apagado para
economizar token é defeito, não compressão.

A defesa é a separação de campo. Um modelo que lê um relatório trata
`explanation` como afirmação do sistema e `subject.snippet` como amostra do
código analisado. Se o texto do artefato vazasse para `explanation`, a instrução
plantada por um terceiro chegaria ao modelo com a autoridade do catálogo.

`tests/test_harness_untrusted.py` tranca as duas metades: que a injeção não
aparece em campo de catálogo, **e** que ela continua visível no `snippet`. A
segunda existe para impedir a correção errada.

## O que este documento NÃO cobre

- **Conteúdo que chega ao modelo por fora do `Finding`** — um agente que lê um
  arquivo com `Read` recebe o texto cru, e nenhum invariante deste repositório
  alcança isso. A defesa ali é do harness da plataforma, não daqui.
- **Saída de MCP de terceiros.** Este repositório expõe tools; não consome.
- **Sanitização de qualquer natureza.** Ver acima: é decisão, não omissão.
