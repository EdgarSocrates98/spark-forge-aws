---

name: analyze-functional-rules

description: Use quando for necessario estudar regras funcionais, contratos, estados, excecoes e criterios de aceite.

subagent: true
agent: sf-functional-rules-specialist
---

# Regras Funcionais e Contratos



Converta texto de negocio em regras atomicas, precondicoes, poscondicoes, entradas, saidas, estados, excecoes, severidade, owner e criterios de aceite. Diferencie regra declarada, comportamento observado e decisao ainda sem dono.



Gere uma matriz regra-fonte-teste-evidencia. Liste conflitos entre documentos e pergunte apenas quando a ambiguidade mudar a implementacao. Valide contra dados, codigo, logs e testes sem substituir o owner humano.



## Quando NÃO usar



Nao use quando o pedido for somente uma transformacao tecnica sem regra funcional ou decisao de negocio.



## Referência rápida



Entrada: requisitos, glossario, exemplos, codigo e logs. Saida: regras atomicas, estados, casos de fronteira, matriz de rastreabilidade e lacunas.



## Red flags



Regra sem fonte, owner ou teste, conflito oculto, exemplo tratado como norma, semantica inventada, estado impossivel e criterio de aceite subjetivo.


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