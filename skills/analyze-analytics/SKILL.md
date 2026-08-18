---

name: analyze-analytics

description: Use quando for necessario analisar dados, analytics, metricas, consultas, custos e qualidade.

---

# Analytics e Analise de Dados



Comece pelo inventario de fontes, schema, tipos, nulos, cardinalidade, distribuicao, duplicidade, frescor, volume e chave de negocio. Separe analise descritiva, diagnostica, causal e recomendacao.



Use SQL, Athena, Glue Data Quality, perfil de dados e amostras antes de uma analise profunda. Registre metodo, amostra, metricas, filtros, custos de scan, limitacoes, vieses e testes de reproducao.



Nao confunda correlacao com causa, score de qualidade com validade de negocio ou uma amostra conveniente com representatividade.



## Quando NÃO usar



Nao use quando uma regra deterministica simples ou uma consulta pontual resolver a pergunta sem analise adicional.



## Referência rápida



Entrada: fontes, escopo, objetivo e contrato de dados. Saida: perfil, metricas, achados, incertezas, referencias e proximo teste.



## Red flags



Conclusao sem amostra ou evidencia, custo de scan ignorado, regra de negocio inventada, consulta sem filtro, duplicidade nao medida e recomendacao sem validacao.


## Protocolo

não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.

A decisao sobe ao pai coordenador antes de qualquer escrita.

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.

## Nao faz

Voce não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.

## Manutencao destrutiva

A skill não executa a operacao; a decisao sobe ao pai coordenador antes de qualquer escrita.

não executa operacoes destrutivas; a confirmacao sobe ao coordenador pai.
Manutencao destrutiva: não executa; a decisao sobe ao pai antes de qualquer escrita.