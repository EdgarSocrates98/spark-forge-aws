# Protocolo do agente — SparkForge AWS

Todo agente e toda skill **apontam** para este arquivo; nenhum o embute. `scripts/sync_skills.py`
espelha `skills/` e `agents/` para `.claude/`, `.agents/` e `.github/` byte a byte — ele não injeta
texto em lugar nenhum. Então **leia este arquivo**: as regras abaixo não chegam ao seu contexto
sozinhas.

Estas regras são duras: elas são o que faz o resultado ser igual sob qualquer modelo e qualquer
ferramenta.

## Regras

1. **Abra ou carregue o case antes de qualquer análise.** Investigação sem `.sparkforge/case.yaml` não é retomável em outra ferramenta, e retomabilidade é requisito, não conveniência.
2. **Chame `next_step` antes de escolher skill.** A árvore de decisão vive em `rules/catalog/routing.yaml`. Não escolha a rota por julgamento próprio — é isso que divergiria entre modelos.
3. **Nenhum número na saída sem `fact_id` que o sustente.** Toda afirmação quantitativa cita `rule_id` e o `fact_id` da evidência. Sem Fact, é hipótese, e tem que estar rotulada como hipótese.
4. **Use `rules_lookup` em vez de memória** para limiar, guarda de versão e fonte. Você não precisa saber o conhecimento; precisa consultá-lo. A resposta traz `knowledge_refs` com o **caminho resolvido** de cada arquivo de `knowledge/` que a regra cita — abra por ali, nunca pelo caminho relativo do texto: num pacote instalado por pip o arquivo está dentro do `site-packages`. Para achar knowledge fora de uma regra, use `sparkforge_knowledge_path` (ou `sparkforge knowledge path --file <rel>` na CLI).
5. **Chame `validate_output` antes de apresentar recomendação.** Ganho quantificado sem `benchmark_ref` é rejeitado pelo schema. Não contorne.
6. **Registre no case** cada skill usada, o resultado, e o motivo de não usar as descartadas. Quando atuar como coordenador (`agents/*.md`), registre também **qual executor rodou** — `sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier` ou `sf-synthesizer` — **e com que resultado**, pelo mesmo mecanismo (`sparkforge_case_update` / `record_skill_use`, com o nome do executor no lugar do nome da skill). Sem isso, retomar o case em outra sessão não diz quais dos cinco já rodaram.
7. **Reporte `unresolved` sempre.** Nó não resolvido é ponto cego, não ausência de problema. Nunca omita a contagem.
8. **Confirme o runtime antes de citar API ou propriedade.** Divergência entre fontes é `SF-ENV-001` em P0, e trava qualquer conclusão dependente de versão. Leia `knowledge/cross-service-constraints.md` antes de recomendar mudança de versão, formato de tabela ou particionamento.
9. **Manutenção destrutiva exige confirmação explícita** de escopo e retenção. `expire_snapshots` e `remove_orphan_files` destroem time travel e podem apagar arquivo em uso por escrita concorrente. Não há rollback para eles.

## Loop de fase

```
next_step → coletar → extrair facts → julgar → hipótese → experimento
   → medir → validar dados → atualizar case → next_step
```

Uma variável principal por experimento. Sem baseline, não há como provar impacto.

## Escada de degradação

Se as tools MCP não estiverem disponíveis: use o CLI `sparkforge`. Se o Python não estiver
disponível: leia `rules/catalog/*.yaml` diretamente — é YAML legível, com o mesmo limiar, a
mesma guarda de versão e a mesma fonte. Cai a automação, não o conhecimento.
