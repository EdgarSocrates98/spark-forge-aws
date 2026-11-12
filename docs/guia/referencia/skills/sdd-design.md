<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Skill `sdd-design`

Use quando o define.md da feature está ready e falta decidir como construir — \"desenha a solução\", \"quais arquivos mudam?\", \"como desfazer?\", \"fase design\" — no SparkForge ou num job do operador.

| Campo | Valor |
|---|---|
| Arquivo de origem | `skills/sdd-design/SKILL.md` |
| `metadata` | {'sparkforge_aws_contract': 'v1', 'evals': 'evals/evals.json', 'references': ['references/README.md', 'references/design-review.md', '../_shared/references/evidence-first.md', '../_shared/references/evaluation-contract.md', '../_shared/references/operational-safety.md', '../../docs/sdd/README.md', '../../docs/sdd/CONTRATO.md'], 'scripts': ['scripts/validate_evidence.py'], 'primary_verbs': ['sparkforge-aws sdd check', 'sparkforge-aws code search', 'sparkforge-aws code symbol']} |

## Procedimento (texto integral)

## SDD Design

Fase 2 do SDD próprio. Diz **quais arquivos** mudam, **por quê**, e **como
desfazer**. O `sparkforge-aws sdd check` confere que todo caminho alterado existe,
que toda decisão tem rollback e que todo critério do define tem uma parte que o
cobre. Se o desenho é sensato continua sendo julgamento — do operador e da
revisão.

### Antes de começar

1. `sparkforge-aws sdd check --repo . --feature <F>` com o define em `ready`. Design
   sobre define em `draft` sai `phase_out_of_order`.
2. Leia o define inteiro: hipótese, critérios, `out_of_scope`, `unknowns` e
   `change_kinds`. Lacuna com `blocks` sobre um critério é resolvida aqui ou vira
   decisão explícita.
3. Copie `docs/sdd/templates/design.md` para `docs/sdd/<FEATURE>/design.md`, com
   `status: draft` e `upstream.path` apontando para o define da feature.

### O manifesto (`files`)

Cada item tem `path`, `action` (`create`, `modify`, `delete`) e `reason`.

- **`create`** é caminho novo. O check não o procura.
- **`modify` e `delete`** exigem o caminho existente hoje. Confira antes de
  escrever: `sparkforge-aws code search <nome>` para achar,
  `sparkforge-aws code symbol <node_id>` para ver quem chama e o que quebra,
  `sparkforge-aws code path <origem> <destino>` para saber como um chega no outro.
  Caminho inventado sai `manifest_path_unknown`. Depois do build pronto, o
  `delete` de um arquivo que sumiu é o desenho cumprido e deixa de ser recusado.
- **Os registros entram no manifesto agora.** Para cada chave de `change_kinds`,
  abra a seção dela em `docs/gates-por-mudanca.md` e liste os arquivos que ela
  move: skill nova mexe na tabela de despacho de `scripts/sync_skills.py`, no
  `manifest.json` e nos testes de espelho; tool nova move `docs/surface.lock.json`
  e a referência gerada. Registro descoberto só no build é desvio que o ship vai
  ter de listar.
- Um arquivo por responsabilidade. Arquivo que já é grande e vai crescer merece
  uma linha no `reason` dizendo por que fica assim.

### As decisões (`decisions`)

Cada decisão tem `id` `D<n>`, `choice`, `rejected` e `rollback`.

- **`rejected`**: ao menos uma alternativa real, com o motivo — as rejeitadas do
  explore entram aqui.
- **`rollback`**: como desfazer, em comando (`git revert` do commit, o script que
  regenera, o `rollback.patch` do pacote de mudança). Sem ele,
  `rollback_missing`.
- **Conhecimento citado, nunca lembrado**, com a versão alvo:
  `docs/sdd/README.md#conhecimento-citado-nunca-memória`.
- **Valor de configuração não é decisão de design.** Ele sai de `sparkforge-aws tune`
  sobre a medida; o design decide *onde* o valor mora e *quem* o pede.

### A cobertura (`covers`)

Cada item liga uma `part` do desenho aos `acceptance` do define que ela
entrega. Todo `AC` aparece em pelo menos um `covers`; o que faltar sai
`acceptance_uncovered`, nomeando o critério.

### O desenho além do manifesto

A profundidade acompanha o risco da mudança — uma linha de log e um formato
de tabela persistido não desenham igual. Cada bloco entra **quando se
justifica**, no corpo do `design.md` (o detalhe vive em
`references/design-review.md`):

- **ADR** — decisão cara de reverter ou que atravessa fronteira (contrato
  público, formato persistido, runtime de terceiro) ganha registro expandido:
  contexto, alternativas, consequências. `D<n>` continua sendo o campo do
  schema; o ADR é o corpo que o justifica.
- **Threat model** — obrigatório quando a mudança toca fronteira de
  confiança: entradas não confiadas, segredos, exfiltração, permissão
  cross-account, Lake Formation, IAM.
- **Contratos de integração** — quem consome o que a mudança publica:
  schema de entrada/saída, erros, versionamento. Consumidor descoberto no
  build é desenho que não olhou.
- **Data model** — entidade, chave de negócio, dono, retenção.
- **Research** — o spike ou a leitura que sustenta o desenho, com a
  evidência citada (o documento, o fact, a versão). "Pesquisei e vi que"
  sem ref é memória com outro nome.
- **Quickstart de validação** — como o revisor confere o desenho em
  minutos: o comando, o arquivo, o teste que já existe.
- **Impact e compatibility analysis** — quem quebra (`code symbol`,
  `code path`, os consumidores do manifesto) e o que muda entre runtimes.
  **Comportamento de um runtime não vale para outro**: Glue 4.x/5.x e
  versões futuras verificadas, EMR, Spark SQL, Athena e Athena UNLOAD,
  Iceberg, Delta Lake, Parquet, Streaming — cada afirmação com a versão em
  que foi verificada.
- **Durabilidade de escrita** — quando a feature persiste ou atualiza
  dado (Glue Catalog, S3, Iceberg, Delta, Parquet, UNLOAD, Step
  Functions): schema evolution, concorrência, idempotência, recovery,
  consistência e os limites de transação. O desenho mostra como o
  invariante sobrevive a uma operação que falha entre etapas — snapshot
  isolado não cobre falha de múltiplas operações.

### Foco AWS

Quando aplicável, o desenho diz por serviço o que muda, com fonte e versão:
Glue e Glue jobs, Glue Catalog, Athena e UNLOAD, Lake Formation,
cross-account, IAM, S3, EMR, Step Functions, Iceberg, Delta Lake, Parquet,
Spark SQL, Terraform e Streaming. A afirmação sem versão citada entra como
`unresolved` do desenho, não como premissa.

### O laço

O de `docs/sdd/README.md#o-laço-de-cada-fase`, com a cascata. Aqui o desenho
vai ao operador **por partes**, do tamanho da complexidade de cada uma, com a
pergunta "está certo?" antes de seguir. Depois
`sparkforge-aws sdd stamp --repo . docs/sdd/<F>/design.md` e
`sparkforge-aws sdd check --repo . --feature <F>`. Próximo passo: `sdd-plan`.

### Perfil operator

- O manifesto lista os arquivos do job que a mudança toca (`.tf`, `.py`). A
  procedência de cada configuração vem dos facts `tf.spark_conf` e
  `pyspark.conf_set`, com arquivo e linha.
- Esses arquivos mudam **só** pelo caminho de
  `docs/sdd/README.md#caminho-da-mudança-do-operador`; o `rollback` é o
  `rollback.patch` do pacote.

### Quando NÃO usar

- Define ainda em `draft`, ou critério sem `verified_by`: volte a `sdd-define`.
- Para quebrar o trabalho em tarefas com teste e código: `sdd-plan`.
- Para aplicar a mudança: `sdd-build`.
- Para escolher o valor de configuração: `sparkforge-aws tune`.

### Referência rápida

| Passo | CLI | Tool MCP |
|---|---|---|
| achar o arquivo | `sparkforge-aws code search <nome>` | `sparkforge_aws_code_search` |
| quem chama, o que quebra | `sparkforge-aws code symbol <node_id>` | `sparkforge_aws_code_symbol` |
| como X chega em Y | `sparkforge-aws code path <origem> <destino>` | `sparkforge_aws_code_path` |
| regra citada | `sparkforge-aws rules lookup --id <SF-...>` | `sparkforge_aws_rules_lookup` |
| documento citado | `sparkforge-aws knowledge path --file <arquivo>` | `sparkforge_aws_knowledge_path` |
| carimbar | `sparkforge-aws sdd stamp --repo . docs/sdd/<F>/design.md` | `sparkforge_aws_sdd_stamp` |
| conferir | `sparkforge-aws sdd check --repo . --feature <F>` | `sparkforge_aws_sdd_check` |
| diff do job (operator) | `sparkforge-aws change plan --facts <f> --set k=v --out d.patch` | `sparkforge_aws_change_plan` |

Recusas desta fase: `phase_out_of_order`, `manifest_path_unknown`,
`rollback_missing`, `acceptance_uncovered`, `upstream_stale`.
Template: `docs/sdd/templates/design.md`.

### Red flags

- `modify` num caminho que ninguém abriu nem procurou.
- Decisão sem alternativa rejeitada, ou com `rollback` "reverter se precisar".
- Limiar, default ou comportamento de Spark citado de memória, sem versão.
- Registro manual (tabela de despacho, manifest, surface lock) fora do
  manifesto de uma mudança que o exige.
- Critério do define sem parte que o cubra.
- Design carimbado de novo sem ler o que mudou no define.
- Arquivo do operador no manifesto com caminho de escrita direta, sem
  `change plan`.
- Comportamento assumido de um runtime para outro — Glue 4 vale para Glue 5,
  EMR vale para Glue — sem a versão verificada citada.
- Contrato de integração descoberto no build: consumidor que o manifesto e o
  `code symbol` teriam mostrado.
- Escrita de dado sem as perguntas de durabilidade respondidas (concorrência,
  idempotência, recovery, limites de transação).
- Threat model pulado numa mudança que toca segredo, IAM ou cross-account.
- Rollback que só cobre o caminho feliz — sem o que faz quando a escrita
  falha entre etapas.


### Contrato de qualidade SparkForge (v1)

Esta skill trata **manifesto, decisões e rollback do design SDD**. Contrato comum, sem substituir o procedimento específico acima:

- **Entrada mínima:** artefato, runtime/contexto declarado e pergunta operacional; se faltar, registre o `*.unresolved` correspondente.
- **Evidência:** produza fatos ancorados com `fact_id`, caminho/linha ou origem de medição; aplique regra por `rule_id` e versão, nunca por memória.
- **Verbos primários:** `sparkforge-aws sdd check`, `sparkforge-aws code search`, `sparkforge-aws code symbol`. Use-os na ordem indicada pela skill e conserve saída estruturada.
- **Saída:** fatos, findings, hipóteses e recomendações separados. Recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`, `proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e `rollback`.
- **Validação:** rode o teste/verbos listados, valide dados depois da mudança e diga o que ainda não foi medido. Ausência de finding significa apenas que nenhum proxy disparou.
- **Rollback e segurança:** não execute escrita destrutiva por inferência; peça escopo explícito e entregue rollback reversível. AWS operacional mantém `denied_by`, conta, recurso e camada de policy.
- **Referências e eval:** `../_shared/references/evidence-first.md`, `../_shared/references/evaluation-contract.md`, `../_shared/references/operational-safety.md`, `../../docs/sdd/README.md`, `../../docs/sdd/CONTRATO.md`; casos realistas em `evals/evals.json`; o script `scripts/validate_evidence.py` verifica o envelope antes do handoff.
