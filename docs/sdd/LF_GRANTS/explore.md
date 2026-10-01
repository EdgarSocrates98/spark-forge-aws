---
sdd: 1
feature: LF_GRANTS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Extrator derivado sparkforge/facts/lakeformation_missing_grant.py, chamado em fuse(), que recebe a uniao dos facts (error.signature_match, lakeformation.grant, iam.access_decision, lakeformation.access_model, lakeformation.registered_location, sql.write_statement, escritas PySpark, runtime) e emite lakeformation.missing_grant ou lakeformation.missing_grant.unresolved; tabela operacao->permissao como dado em knowledge/ com fonte T1; regra nova SF-LF-011 que consome o fact; build_access_graph passa a consumir o fact quando existe."
    tradeoffs:
      - "unico caminho em que a permissao ausente vira achado julgado por judge"
      - "ERR-LF-001 passa a ter evidence_required que algum extrator emite"
      - "uma definicao so do que falta: grafo e regra leem o mesmo fact"
      - "mais caro em registros manuais: listas de extrator, surface lock, gate de lastro, goldens"
  - id: B
    summary: "Verbo de composicao sparkforge lakeformation missing-grant, irmao de access_graph, que devolve a permissao ausente sem emitir fact nem regra."
    tradeoffs:
      - "diff menor, nao toca o motor de regras"
      - "judge nunca acusa; ERR-LF-001 segue com evidencia que nenhum extrator emite"
      - "nao atende o pedido de uma regra que cruza com a falha"
  - id: C
    summary: "Derivar missing_grant dentro de sparkforge/errors/matcher.py quando uma assinatura ERR-LF-* casa."
    tradeoffs:
      - "sem arquivo novo"
      - "o matcher recebe log, nao a uniao dos facts; passaria a depender de grant, IAM e codigo"
      - "acopla extracao de artefato a composicao, a fronteira que o CLAUDE.md separa"
chosen: A
---

# LF_GRANTS — exploração

## Origem

Pedido do operador em 2026-09-21: "um coletor que lê os grants do Lake Formation e as
policies IAM do runtime role, a partir de artefato salvo pelo operador, e uma regra que
cruza com a falha observada e aponta a permissão ausente. Entra pelo critério de domínio:
artefato primeiro."

## Perfil

`dev`: a mudança é no próprio SparkForge.

## Medido antes da primeira pergunta (2026-09-21, `origin/main` em `4626bf11`)

- **Os coletores já existem.** `collect lakeformation` produz `lakeformation.grant`,
  `lakeformation.registered_location` e `lakeformation.data_lake_settings`
  (`sparkforge/facts/lakeformation_grants.py`). `collect iam-access` produz
  `iam.access_decision` (`sparkforge/facts/iam_access.py`), por
  `iam:SimulatePrincipalPolicy` e não pelo documento da policy. A escolha foi deliberada:
  boundary, SCP, deny explícito e condição não aparecem no documento do role.
- **Regras que leem esses kinds existem, mas cada uma lê um kind só:** `SF-LF-007` a
  `SF-LF-010` (`rules/catalog/lakeformation.yaml`) e `SF-IAM-001` a `SF-IAM-003`
  (`rules/catalog/iam.yaml`). Nenhuma cruza com a falha observada.
- **`ERR-LF-001`** (`Insufficient Lake Formation permission(s) on`) declara
  `lakeformation.missing_grant` em `evidence_required`, e nenhum extrator emite esse kind
  (`rules/catalog/errors.yaml`, comentários em torno de `SF-ERR-006` e `SF-ERR-014`). Por
  isso `SF-ERR-006` só consegue dizer que "algum elo falta" e manda `investigate`.
- **`build_access_graph`** (`sparkforge/lakeformation/graph.py`) fixa `SELECT` ou `ALL`
  como o que a perna LF exige, sem olhar a operação que falhou. Sob escrita, isso acusa a
  permissão errada.

A lacuna real, portanto, não é coletor: é o fact derivado que ERR-LF-001 já espera.

## Perguntas feitas, uma por vez

1. **Recorte.** Coletor novo de documento de policy IAM, ou só o fact derivado mais a
   regra? Resposta: só o fact derivado mais a regra. Os coletores existentes bastam.
2. **De onde vem a permissão exigida**, dado que a mensagem de erro nomeia o recurso e não
   a permissão? Resposta: da operação, lida de facts de código já medidos
   (`sql.write_statement` e as chamadas de escrita do PySpark). Uma tabela declarada como
   dado liga operação a permissão: leitura pede `SELECT`, append/insert pede `INSERT`,
   create/alter pede `CREATE_TABLE`/`ALTER`, e alvo em localização registrada pede
   `DATA_LOCATION_ACCESS`. A tabela vem da documentação da AWS (T1) e mora em `knowledge/`.
   Operação sem fact sai `lakeformation.missing_grant.unresolved`, nomeando a medida que a
   destravaria.
   Rejeitadas: só leitura (acusa `SELECT` num job que falhou escrevendo) e operação
   declarada no `case.yaml` (campo novo que ninguém mede).
3. **O modelo de acesso muda quem precisa da permissão** (regra 31). Resposta: o extrator
   lê `lakeformation.access_model` e decide o lado:
   - sob FTA, cobra o grant do LF na leitura e na escrita;
   - sob FGAC, cobra o grant do LF na leitura, e na escrita cobra `iam.access_decision`
     da ação correspondente, dizendo `denied_by`;
   - escrita em alvo **registrado** sob FGAC é o conflito declarado da §6 de
     `knowledge/glue/lakeformation-fgac.md`: sai `unresolved` com o nome
     `conflito_declarado_fgac_escrita_registrada`, sem escolher lado (regra 32);
   - modelo `both` ou desconhecido sai `unresolved`.
   Restrição que decorre disso: a escrita sob FGAC depende também da versão (o Glue 5.0
   não escreve, o 5.1 escreve). O extrator consulta o eixo que já existe como dado em
   `sparkforge/facts/lakeformation_matrix.py`, e runtime desconhecido sai `unresolved`.
   Rejeitadas: ignorar o modelo (sob FGAC aponta o grant do LF quando o que falta é IAM)
   e restringir a feature a FTA.
4. **O que fazer com `build_access_graph`.** Resposta: o grafo consome
   `lakeformation.missing_grant` quando o fact existe no case e mantém o comportamento
   atual quando ele não existe. Assim há uma definição só do que falta.
   Rejeitadas: deixar a divergência para outra feature (duas saídas respondendo diferente
   à mesma pergunta) e remover o `SELECT` fixo (quebra as saídas e os goldens atuais).

## Abordagens

- **A** (recomendada) põe a derivação num extrator, onde a união dos facts já chega (em
  `fuse()`), e dá à regra um fact que ela consegue ler. A regra 33 exige isso: "permissão
  exigida ∉ conjunto concedido" não cabe nos seis comparadores de
  `sparkforge/rules/expr.py`.
- **B** resolve a pergunta para quem chama o verbo, mas não produz achado. `judge` continua
  cego, e a evidência de `ERR-LF-001` continua sendo um kind que nenhum extrator emite.
- **C** economiza um arquivo e paga com acoplamento: o matcher de erro passaria a receber
  grant, IAM e código, que não são artefato dele.

## Escolha

**A**, aprovada pelo operador em 2026-09-21. É a única das três que entrega o que o pedido
nomeia (uma regra que cruza a falha com a permissão e aponta a ausente), e fecha a
evidência que `ERR-LF-001` declarava desde antes de o motor ler Lake Formation.

## O que fica de fora

- Coletor de documento de policy IAM (`get-account-authorization-details`).
- As pernas sem coletor do caminho de acesso: RAM share e key policy do KMS.
- Qualquer valor de permissão *proposto*. O fact nomeia o que falta e não gera o
  `grant-permissions` para aplicar.

## Cuidados para o define

- O critério de domínio (`docs/gates-por-mudanca.md`, *Critério de domínio*) pede que a
  entrada seja por artefato: aqui o artefato é o log com `ERR-LF-*` somado aos artefatos
  de `collect lakeformation` e `collect iam-access`, que já existem.
- As fixtures devem ser sintéticas (memória *caso real nunca entra em arquivo*). A fixture
  negativa (grant presente, falha por outra perna) e a do segundo artefato precisam estar
  no define (memória *revisão final pega o que o corpus não cobre*).
- Extrator e regra novos mexem nos registros manuais: listas de extrator, surface lock,
  roteamento em `routing.yaml`, `sources.lock.json` e o gate de lastro.
