# ADR-010: SparkForge Code Intelligence — subsistema nativo, índice local e o que ele recusa guardar

## Status
Accepted

## Context
A SPEC do **SparkForge Code Intelligence** (SFCI) propõe um motor local e offline de economia de
token: índice de código em SQLite com FTS, extractors de Python e PySpark, recuperação sem
embedding, orçamento de token com objeto de contexto canônico, tools MCP novas e uma camada de
segurança inteira — invariantes numerados, threat model, perfis, sandbox de filesystem, firewall
de segredo e defesa contra prompt injection. Ela não é versionada aqui, e assim permanece: o
remote é público e material de referência não entra nele.

O mapa componente a componente do que já existia contra o que a SPEC pediria está em
[`docs/harness/CODEINTEL-GAP.md`](../../harness/CODEINTEL-GAP.md), e é a base factual deste ADR.
As fases J0 a J4 executaram uma parte desse mapa: a fronteira de leitura, o envelope de saída, a
pilha de escopo, o índice persistente e a resolução de referência.

Este documento registra o que **foi decidido e executado** nessas fases, não o que se pretende
fazer. Ele existe atrasado, e o atraso teve custo medido: as decisões de retenção de J3 — banco
sem corpo, sem caminho absoluto, assinatura sanitizada — foram tomadas dentro do módulo que as
implementa, uma a uma, e não havia documento contra o qual conferir a próxima. O mapa registra
essa lacuna como uma fase inteira pendente; este ADR e o
[threat model](../../harness/THREAT-MODEL.md) são as duas metades dela.

## Decision

### Subsistema nativo do SparkForge, não um segundo servidor MCP
A §4 da SPEC coloca o Code Intelligence dentro do SparkForge, e a alternativa — um servidor MCP
separado, com processo, catálogo de tool e superfície de configuração próprios — foi recusada por
uma razão que não é de gosto: um segundo servidor duplicaria a fronteira de segurança. O
confinamento de caminho, a denylist de arquivo sensível, o reconhecedor de segredo e a política de
conteúdo não confiável já existem neste pacote, com teste, e cada cópia deles num processo
separado é uma cópia que pode divergir em silêncio. A fase J0 pagou exatamente esse preço em
menor escala: havia quatro detectores de segredo no pacote, um deles já divergente, e a
divergência era muda.

A consequência aceita é que o índice compartilha o processo com o resto do SparkForge, e por isso
herda o que o resto tiver de errado. A troca é deliberada: uma fronteira que se conserta num lugar
vale mais que duas que se conferem à mão.

### SQLite com FTS5 da biblioteca padrão, e nenhuma dependência nova
O índice inteiro — `metadata`, `files`, `nodes`, `edges`, `unresolved_refs` e a tabela virtual
`symbols_fts` — é criado por `sparkforge/codeintel/db.py` sobre o módulo `sqlite3` que já vem com
o interpretador. Nenhum pacote foi acrescentado ao `pyproject.toml` por causa desta fase.

Dependência é superfície de ataque antes de ser conveniência, e o mapa classifica dependência
mínima como controle de segurança, não como estética. Um índice de código lê código de cliente,
possivelmente proprietário; cada biblioteca nova nesse caminho é mais uma cadeia de fornecimento a
auditar, e a fase de supply chain deste mesmo esforço mostra o que auditar uma cadeia custa —
lock com hash por distribuição, SBOM por release e política de vulnerabilidade no CI.

A escolha tem limite declarado: FTS5 é um recurso de compilação do SQLite, e não uma garantia da
linguagem. Por isso a disponibilidade é afirmada em teste (`tests/test_codeintel_db.py`) em vez de
assumida — se o interpretador de alguém vier sem FTS5, isso aparece como falha nomeada e não como
busca que devolve vazio.

### O banco não guarda corpo de função, e isso é o invariante `INV-010` em forma de schema
`nodes` guarda `kind`, `name`, `qualified_name`, `path`, faixa de linha e assinatura normalizada.
Não existe coluna de corpo, e não existe cache de trecho. Um índice que guardasse corpo seria uma
segunda cópia do código do cliente, com o mesmo valor para quem vazasse e nenhuma das proteções do
diretório original — e ainda envelheceria em silêncio contra o arquivo real.

A assinatura passa por `sparkforge/codeintel/ids.py:normalizar_assinatura()` antes de existir nó:
valor literal de default vira o marcador `<literal>`, e nome, ordem de parâmetro e anotação de
retorno sobrevivem. Isso não é limpeza estética. `def cliente(token="AKIA...")` colocaria a
credencial dentro de uma coluna do índice pela única razão de ela ser o default de um parâmetro, e
a sanitização é o que impede que a exceção mais boba vire a mais cara.

A garantia é estrutural — não há caminho que grave corpo, porque não há coluna — e mesmo assim é
afirmada por teste que indexa e confere o banco resultante
(`tests/test_codeintel_index.py:test_corpo_da_funcao_nao_chega_ao_banco`). Garantia estrutural sem
teste é garantia até a primeira coluna nova.

### `unresolved` é dado de primeira classe, e não uma aresta inventada
O AST vê `foo(x)` e não sabe qual `foo`. Escolher um candidato quando há vários é inventar: quem
seguisse a aresta investigaria o arquivo errado e nada acusaria. A regra executada em
`sparkforge/codeintel/resolve.py` é resolver só o inequívoco e mandar todo o resto para
`unresolved_refs` **com motivo** — `UNKNOWN_RECEIVER`, `NO_CANDIDATE`, `AMBIGUOUS`,
`NO_SOURCE_NODE` —, porque ponto cego contado é diferente de ponto cego silencioso. É a mesma lei
que os extratores de grafo e de SQL deste repositório já aplicavam.

A taxa foi medida sobre a própria árvore e publicada como saiu, e o que ela diz é desconfortável:
**menos referências viram aresta do que viram ponto cego declarado.** Cerca de um terço resolve,
cerca de dois quintos entram em `unresolved_refs` com motivo, e o restante é builtin, descartado de
propósito. Os valores absolutos moram em `sparkforge/codeintel/resolve.py`, datados na docstring do
módulo, e **não** são copiados para cá: eles se movem a cada arquivo novo da árvore, e número
copiado envelhece no documento sem que nada acuse.

O motivo dominante é o que diz onde está o limite. **91,8%** das não resolvidas são
`UNKNOWN_RECEIVER` — `df.filtrar()` sem saber o tipo de `df`. Inferir tipo aqui seria adivinhação
vestida de análise, e é por isso que a próxima fase tem o que ganhar exatamente ali, e não afinando
estas regras. Número baixo medido vale mais que número alto inventado, e a fase anterior já havia
estabelecido esse padrão publicando contra si mesma.

Import não entra em nenhum dos dois lados: resolver import exige mapear módulo para arquivo e
decidir o que fazer quando o alvo é o próprio módulo, que não é nó e não cabe em `edges`. Nada
disso foi feito, e as referências de import ficam contadas à parte, como *não tentadas*, em vez de
inflarem a tabela de ponto cego com linhas que não dizem nada sobre a qualidade da resolução.

### A medição é em bytes, nunca em token
Toda medição de economia deste subsistema — o que a busca devolve contra o que responder sem ela
custaria — está em bytes UTF-8. A razão é que este repositório tem quatro estimadores de token, os
quatro dividem o comprimento por uma constante e eles divergem entre si no arredondamento. Byte é
observação; token seria estimativa vendida como medida, e a diferença aparece exatamente na casa
decimal em que a economia é reivindicada.

O limite disso está declarado junto: byte não mede CPU nem I/O, e a medição não converte um no
outro de propósito.

### A ordem das fases foi mudada pela medição, contra a ordem da própria SPEC
Esta é a decisão desconfortável, e é a mais importante deste ADR.

A fase J3 mediu o índice contra o denominador que menos o favorece: a saída de um
`grep -n "def <nome>"`. O índice **perde**. Mesmo descartando todo símbolo que apenas *contém* o
termo e ficando só com correspondência exata, a resposta do índice custa **2.3** vezes o que
aquele `grep` custaria. Contra a pergunta *estrutural* — "quais são os símbolos deste arquivo" — a
relação se inverte e o índice sai **9.7** vezes à frente, porque a alternativa é abrir o arquivo
inteiro e fazer o parse do lado de quem perguntou.

As duas coisas respondem perguntas diferentes, e é isso que a medição mostra: o índice não se paga
como substituto de `grep` para busca por nome, e se paga em pergunta que `grep` não responde sem
parse. A conclusão prática foi reordenar o trabalho — `edges` antes de qualquer melhoria de
recuperação, contra a ordem em que a SPEC lista as fases —, porque aresta é a tabela da pergunta
que justifica o índice, e escore composto sobre um grafo que não existe seria afinar o eixo que já
tinha se mostrado o mais fraco.

Um ADR que registrasse só a medição favorável seria propaganda. A desfavorável é a que mudou o
plano, e por isso é a que precisa estar escrita.

## Consequences

- **Positivas.** A fronteira de segurança do índice é a mesma do resto do pacote, e conserta-se
  num lugar só. O banco é descartável por construção: nada no motor determinístico depende dele
  para responder, então perdê-lo custa uma reindexação e não uma investigação. O ponto cego da
  resolução é consultável com motivo, o que permite decidir onde vale investir a fase seguinte em
  vez de adivinhar. E a economia reivindicada tem denominador declarado junto — quem discordar
  discute o denominador, não o número.

- **Trade-offs.** A taxa de resolução é baixa, e continuará baixa enquanto não houver inferência
  de tipo; quem consultar o grafo precisa ler `unresolved_refs` junto, porque só a soma das duas
  tabelas diz qual é a cobertura. Ausência de migração é o preço de o banco ser descartável: banco
  de versão anterior é **jogado fora e refeito**, não migrado, e isso é aceitável exatamente
  porque não há dado original ali dentro. E a assinatura, guardada em `nodes`, não é buscável — o
  FTS cobre nome e nome qualificado.

- **Limite declarado.** As tools MCP que a SPEC enumera não foram criadas, e a razão está no mapa:
  índice velho responde "nenhum símbolo" com a mesma cara com que responde sobre símbolo
  inexistente, e enquanto não houver sinal de obsolescência os três verbos `code` ficam no CLI —
  o sha por arquivo e a impressão da raiz estão gravados e ninguém os compara na leitura. A
  separação de papéis dentro do subsistema também é limite, não acabamento: `resolver()` decide e
  não toca no banco, e quem grava `edges` e `unresolved_refs` é `indexar`, que já tem a transação
  aberta. As duas tabelas são gravadas **juntas ou nenhuma** — aresta sem o ponto cego ao lado
  mediria cobertura pela metade que dá certo.
