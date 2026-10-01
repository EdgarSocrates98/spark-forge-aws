---
name: lakeformation-architecture
description: Use para avaliar uma arquitetura AWS Lake Formation antes de recomendar FGAC, Full Table Access, migração Glue 4/5, EMR EC2/Serverless ou acesso cross-account. Exige separar engine/runtime, formato, operação, ownership de catálogo, RAM/resource link, credential vending e permissões; falha fechado quando a capability ou a evidência não está declarada.
subagent: true
---

# Lake Formation Architecture

Use esta skill para perguntas de arquitetura e compatibilidade. Comece pela
matriz versionada e pelo motor determinístico; não derive uma recomendação do
nome do serviço, de uma release vizinha ou de uma permissão isolada.

## Procedimento

1. Monte JSON offline com `engine`, `runtime`, `access_model`, formato e
   operação. Declare source/target catalogs com nome, owner, `glue_id` e
   `glue_account_id`.
2. Preserve todas as contas: job, local, source, target e owners dos catálogos.
   Nunca use `glue.id` como alias de `glue.account-id`.
3. Inclua evidências observadas separadamente: `ram`, `resource_link`,
   `iam_get_data_access`, grant Lake Formation, localização registrada,
   application integration e filesystem.
4. Rode:

   ```bash
   sparkforge lakeformation architect --input architecture.json
   ```

   Ou use a tool `sparkforge_lakeformation_architect` com `payload` igual ao
   objeto JSON. CLI e MCP chamam o mesmo núcleo e devem retornar o mesmo shape.

5. Leia `status`, `checks` e `decision.required_verification`. `consistent`
   não autoriza mutação; `unresolved` não é compatível; `blocked` exige
   resolver conflito ou trocar a declaração.
6. Quando faltar evidência AWS, siga os coletores existentes e reexecute a
   análise. Use `collect iam-access` para simular autorização, não parseie a
   policy do role; mantenha bucket policy, KMS e Glue resource policy como
   avaliações separadas.

## Regras de interpretação

- FGAC e FTA são modelos mutuamente exclusivos por job/aplicação.
- Read e write têm capacidades e permissões diferentes; `SELECT` não prova
  autorização de escrita.
- Glue 4.0 DynamicFrame e Glue 5.x Spark-native FGAC exigem migração sem
  substituir o catálogo governado por S3 direto.
- Glue, EMR EC2 e EMR Serverless têm matrizes e releases diferentes; ausência
  de célula é `unknown`, não `not_supported`.
- Cross-account exige evidência independente de RAM, resource link e
  credential vending; ownership de origem e destino permanece explícito.
- Não alegue custo, ganho de performance ou autorização efetiva sem medição e
  fact correspondente.

## Não faz

Não chama AWS, não altera IAM/Lake Formation/S3/KMS, não cria resource link,
não concede permissão, não remove grant, não migra job e não promete suporte por
analogia. Produz decisão estruturada, lacunas, riscos e rollback para o
operador validar.

## Referências

- `knowledge/lakeformation/capability-matrix.yaml`
- `knowledge/lakeformation/architecture.md`
- `skills/lakeformation-fgac-guard/SKILL.md`
- `skills/diagnose-lakeformation-access/SKILL.md`

## Protocolo

Siga `AGENT_PROTOCOL.md`, reporte `unresolved` e mantenha evidência ancorada.
Manutenção destrutiva você não executa; a decisão sobe ao agente pai ou ao
operador responsável pela governança. O verbo é offline e não concede acesso.
