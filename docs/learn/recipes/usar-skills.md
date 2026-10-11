# Receita — utilizar skills

**O quê:** 60 skills instaladas no host — procedimentos especializados que
ativam por linguagem natural e chamam as tools MCP determinísticas.
**Por que:** a skill sabe **quando** rodar cada verbo e em que ordem; sem
ela, o operador precisa conhecer o catálogo de cor. Ela é o conhecimento
operacional do Forge, empacotado.
**Quando:** "meu job Glue está lento", "revisa esse PR PySpark", "posso
subir para o Glue 6?" — qualquer pergunta de domínio.
**Quando não:** um verbo isolado e já sabido (`analyze pyspark` direto) —
a skill agrega valor na escolha e na ordem, não na chamada.

## Problema

"Como aproveito as skills que o install deixou no meu host?"

## Pré-requisitos

`sparkforge-aws install` (perfil `recommended` já traz as 60). Um host que
lê o diretório de skills do projeto.

## Passo a passo

Peça em linguagem natural — a descrição de cada skill diz quando ela
dispara:

```text
"Meu job Glue está lento"            → sparkforge-aws-diagnose
"Revisa esse PR PySpark"             → review-pyspark-pr
"Dá para subir pro Glue 6.0?"        → migrate-glue-6
"Por que a leitura passa e escrita não?" → diagnose-lakeformation-access
"Comprova que essa mudança ajudou"   → benchmark-pyspark-job
```

A skill roda o pipeline determinístico (`analyze` → `judge` →
`next-step`) e devolve findings com `rule_id` + `fact_id`.

## Saída esperada / interpretação

Resposta com evidência citável — nunca "parece lento": cada afirmação
ancora em fact (`file:line:col`, `artifact_sha256`) ou em regra do
catálogo versionado.

## Verificação

```bash
ls .claude/skills | wc -l    # 61 entradas = 60 skills + `_shared/` de fragmentos
```

A lista das skills despacháveis vive em `DISPATCHABLE_SKILLS`
(`scripts/sync_skills.py`); as não-despacháveis coletam na AWS e ficam
para o host principal.

## Limitações

- Skill não decide produto: ela executa o procedimento; a decisão de
  aplicar a recomendação é humana (rollback incluso no schema).
- A resposta é tão boa quanto o artefato de entrada — sem event log, a
  skill de UI responde "colete o log", não adivinha.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| skill "não ativa" | host sem leitura de skills de projeto | confira `.claude/skills/` e a doc do host |
| resposta genérica | pergunta ampla demais | `sparkforge-aws-diagnose` primeiro, skill específica depois |

## Uso por agentes

Cada `SKILL.md` carrega o gatilho de ativação na descrição do frontmatter
— o host decide pelo texto do pedido, não por comando.

## Leitura seguinte

- [usar-agents](usar-agents.md)
- `docs/guia/05-agents-e-skills.md` — a camada completa
- `GUIA_DE_USO.md` — exemplos por plataforma
