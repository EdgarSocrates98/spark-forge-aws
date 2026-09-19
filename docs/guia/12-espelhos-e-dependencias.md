# Espelhos e dependências (para quem contribui)

O resumo está no [README](../../README.md). Este manual é para quem edita o
repositório: quais arquivos são gerados, de onde, e o gate que acusa o esquecimento.
Os gates por tipo de mudança estão em [`docs/gates-por-mudanca.md`](../gates-por-mudanca.md).

## Manutenção dos espelhos

A fonte da verdade das skills é `skills/`, e a dos perfis é `agents/`. `.claude/skills/`
e `.claude/agents/` são espelhos byte-a-byte; `.github/agents/` também. `.agents/` é
**renderizado** por plataforma: as skills despacháveis ganham `subagent: true` (e
`agent:` quando há coordenador único **e** ele não é o perfil que orquestra — hoje 10
das 23 despacháveis, contadas em 2026-09-18 com
`grep -l '^subagent: true' .agents/skills/*/SKILL.md` e `grep -l '^agent:'`), e os
perfis perdem `tools:`. Após editar uma skill em `skills/` ou um perfil em `agents/`,
regenere os espelhos:

```bash
python scripts/sync_skills.py          # regenera os espelhos
python scripts/sync_skills.py --check   # falha se algo divergir (útil em CI)
```

O repositório tem **três** espelhos gerados, e cada um tem seu `--check` rodando no CI.
Editar a fonte e esquecer o espelho quebra a build — de propósito, porque drift em
manifesto silencioso é pior que erro barulhento:

| Espelho | Fonte | Comando | Por que existe |
|---|---|---|---|
| `.claude/`, `.agents/`, `.github/` | `skills/`, `agents/` | `python scripts/sync_skills.py --check` | Cada plataforma lê de um diretório próprio |
| `requirements.txt` | `pyproject.toml` | `python scripts/gen_requirements.py --check` | Ferramenta de SCA não lê `pyproject.toml` sem lockfile — e scan que não roda não é scan que passa |
| `sparkforge/rules/catalog/`, `sparkforge/knowledge/` (só no artefato) | `rules/catalog/`, `knowledge/` | `python scripts/verify_wheel.py` | `force-include` do hatchling embarca no build, sem duplicar arquivo em git |

O terceiro não existe em disco: nasce no build e é verificado pelo gate de paridade, que
constrói o artefato, instala num venv limpo e reproduz as fixtures golden byte a byte
(todas: `scripts/verify_wheel.py` reusa os módulos `tests/test_fixtures_*.py`, e a
contagem corrente de fixtures está na tabela *Números correntes* de
[`docs/superpowers/STATUS.md`](../superpowers/STATUS.md)).

## Locks não são espelho

`locks/py3.10.txt`, `locks/py3.11.txt` e `locks/py3.12.txt` **não** entram nessa tabela, e
a diferença importa. Espelho é projeção: sai do `pyproject.toml` sozinho, offline, e por
isso `--check` pode regenerá-lo e comparar. Lock é **resolução**: ele diz qual versão de
cada pacote — diretos e transitivos — o ambiente instala, e produzir isso exige consultar
o índice do PyPI. Por isso `python scripts/gen_lock.py` precisa de rede e de `uv`,
enquanto `python scripts/gen_lock.py --check`, o que roda no CI, é offline e confere
forma, cobertura e consistência. O CI instala com `pip install --require-hashes`, modo em
que qualquer dependência fora do arquivo vira erro em vez de virar versão escolhida na
hora — e é isso que dá sentido ao job `audit`: auditar piso não responde nada, porque
`PyYAML>=6.0` não tem CVE, a versão instalada é que tem.

## O que os testes conferem nos espelhos

Os testes (`pytest`) validam frontmatter, seções padronizadas, referências e — desde a
fase de perfis de subagente do Devin — um invariante mais forte que "as cópias são
iguais": **o espelho é exatamente o que o tradutor produz para aquela plataforma**.
Igualdade nunca poderia pegar campo que a plataforma exige e a fonte não tem, nem campo
que a fonte tem e a plataforma não deve receber; a derivação pega os dois, e o gate
acusa também **órfão em qualquer profundidade e de qualquer extensão** —
`.agents/agents/<nome>/AGENT.md` é layout de descoberta do Devin, e passar por ali
publicaria perfil que ninguém revisou.

## Próximos passos

- [`docs/gates-por-mudanca.md`](../gates-por-mudanca.md): qual gate cada tipo de mudança toca.
- [Agents e skills](05-agents-e-skills.md#onde-os-arquivos-moram): fonte e espelho, lado a lado.
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md): o fluxo de contribuição.
