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
5. **Chame `validate_output` antes de apresentar recomendação.** Ganho quantificado sem `benchmark_ref` é rejeitado pelo schema. Não contorne. **Desde a Fase 4a o campo não é mais texto livre**: ele cita o `fact_id` de um `bench.run_delta`, forma `f_` + 6 dígitos hex minúsculos (`f_a1b2c3`) — o fato que `sparkforge benchmark --before <facts-antes> --after <facts-depois>` emite ao comparar dois conjuntos de facts de `analyze event-log --out`. Caminho de arquivo, nome de planilha, data ou qualquer prosa é **rejeitado**. São duas camadas: a **forma** vale sempre; a **pertinência** (o `fact_id` existe no conjunto) quando quem chama passa os facts — `validate_output` com `facts_path`, ou `sparkforge validate --facts`. Sem medição, não escreva o número: `expected_effect` qualitativo rotulado como hipótese passa sem `benchmark_ref` nenhum, e é a saída honesta.
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

## Gates de fase

Os quatro gates do case — `baseline_captured`, `dominant_bottleneck_identified`,
`functional_validation_defined`, `flows_mapped` — são **advisory por default**, e esse é o
comportamento de sempre. Quando o case foi aberto com `sparkforge case open
--strict-gates`, o rigor fica gravado no `case.yaml` e vale pela investigação inteira:
quem retomar noutra sessão, noutra máquina ou noutra ferramenta herda o rigor de quem
abriu. Sob ele, quatro coisas mudam para você:

1. **O booleano manual não destrava.** `case update --gate flows_mapped --gate-value true`
   continua gravando a flag e **não** libera a transição de fase — `set_phase` não consulta
   `case["gates"]`. O que destrava é o fact produtor estar presente nos facts que você
   passou em `case update --facts <facts.json>`, ou um override declarado. Gate que se
   satisfaz digitando é a família de defeito que a Fase 4a mediu no `benchmark_ref` antigo.
2. **Quem produz a evidência de cada gate é dado, não memória.** Está no bloco `gates` de
   `rules/catalog/routing.yaml`, com o comando exato em `produced_by` — hoje
   `baseline_captured` ← `bench.run_delta` (`sparkforge benchmark --before … --after …`) e
   `flows_mapped` ← `callgraph.reachable_spark_work` (`sparkforge analyze call-graph`). Os
   outros dois **não têm produtor** e seguem advisory mesmo sob rigor. Leia o bloco; não
   decore esta lista.
3. **Passar por cima é possível, custa uma frase e fica gravado.** `sparkforge case update
   --override-gate <gate> --reason "<por que a evidência não existe>"`. Sem `--reason` o
   override é recusado — override anônimo não se distingue de gate esquecido. Ele entra
   numa lista (dois overrides do mesmo gate são dois fatos, e nenhum apaga o outro) e
   aparece no `resume`. É para quando o dado genuinamente não existe — job descontinuado,
   ambiente que sumiu, corpus sem trabalho Spark alcançável —, nunca para andar mais rápido.
4. **O limite da checagem, que é decisão registrada e não descuido.** O gate confere a
   **presença do kind**, nunca o conteúdo do fact: ele prova que a análise rodou e produziu
   o artefato que destrava, e **não** prova que ela cobriu todo o `scope.entrypoints`, nem
   que o benchmark é do job certo. **Medido, para você não superestimar o que o verde
   significa:** duas linhas de JSON escritas à mão, com `provenance` vazia, levam um case
   estrito de `intake` a `report` — nada valida proveniência. Gate verde não é cobertura
   total, e declarar esse recorte no relatório é a mesma obrigação da regra 7 — é o que
   este projeto faz com `dq.unresolved`.
5. **Abrir um case por cima de outro é recusado.** `sparkforge case open` sobre um
   `.sparkforge/case.yaml` que já existe sai com código 2 e nomeia o que apagaria: fase,
   rigor e overrides. Recomeçar do zero continua possível, com nome — `--reopen` na CLI,
   `reopen: true` na tool —, e ele **herda** o `strict_gates` do case atual: o rigor sobe
   com `--strict-gates` e nunca desce por omissão de flag. Se você queria continuar a
   investigação, o comando é `case get` seguido de `case update`, nunca `case open` de novo.

## Assinatura do relatório

`sparkforge report sign --report <relatorio.md> --findings <findings.json>` escreve um
bloco no fim do relatório, e `sparkforge report verify` confere e diz **qual** das quatro
partes divergiu — versão da assinatura, evidência, catálogo ou corpo — em vez de devolver
só "inválido". O arquivo é o de **findings**, não o de facts: `rule_id`,
`catalog_version` e `schema_version` só existem lá.

`version_mismatch` é **regra mudada, não adulteração**: o bloco declara sob qual
`signature_version` foi assinado, e quando ela não é a desta build o corpo sai como **não
avaliável** em vez de acusado — a normalização de então não é a de agora, e recomputar
responderia sobre a regra errada. O que se faz é reassinar.

**Se o case tiver `gate_overrides`, a seção "Gates com override" do relatório sai
preenchida** — gate, data e motivo, copiados de `case get`. Ela fica dentro do corpo
assinado, então apagá-la depois de assinar invalida a assinatura. Omitir um override
afirma um rigor que não foi prestado, e nenhum código pega isso por você: nada compara a
tabela do relatório com o case.

Ela prova **correspondência** entre aquele texto, aquela evidência e aquele catálogo — e
**nunca autoria**: não há chave nem segredo, e qualquer pessoa com os mesmos findings
produz a mesma assinatura. Não escreva, e não deixe o leitor supor, que o bloco autentica
quem redigiu. O corpo assinado é tudo que vem **antes** do delimitador do bloco: texto
acrescentado depois dele é recusado, não ignorado. Editar a prosa depois de assinar
invalida, e é para isso que serve — reassinar é barato, texto editado passando por
verificado não é.

## Escada de degradação

Se as tools MCP não estiverem disponíveis: use o CLI `sparkforge`. Se o Python não estiver
disponível: leia `rules/catalog/*.yaml` diretamente — é YAML legível, com o mesmo limiar, a
mesma guarda de versão e a mesma fonte. Cai a automação, não o conhecimento.
