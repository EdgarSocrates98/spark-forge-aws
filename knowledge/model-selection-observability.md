# Seleção de Modelos e Observabilidade

## Fonte do catálogo

O coordenador Devin ou Claude deve consultar o inventário de modelos realmente disponível na conta naquele momento. Não hardcode IDs, preços, limites ou capacidades. O inventário deve informar disponibilidade, custo se fornecido, janela, qualidade, raciocínio, ferramentas e visão.

## Política de escolha

Para tarefas simples e de baixo risco, escolha o modelo mais barato que satisfaça o contrato. Para síntese de código, análise ambígua ou construção, escolha o melhor equilíbrio entre qualidade, contexto e custo. Para alta criticidade, contradição ou verificação difícil, priorize raciocínio e qualidade. Se nenhum modelo satisfizer o pedido, bloqueie e informe a causa em vez de escolher silenciosamente um modelo inadequado.

## Economia

Selecione o modelo depois de reduzir o contexto, não antes. Use filtros determinísticos e cache no caminho barato. Escale apenas os casos que falharem em schema, confiança, evidência ou validação. A escolha de um modelo forte não compensa contexto redundante ou fan-out desnecessário.

## Visibilidade opcional

A visualização de traces fica desligada por padrão. Quando ativada pelo usuário, mostra eventos resumidos, actor, fase, handoff e decisão. O conteúdo completo continua oculto por padrão para reduzir exposição e custo de renderização.

## Aviso de tokens

Se o runtime fornecer uso real, exiba tokens de entrada, saída e total. Se não fornecer, sinalize que o valor é desconhecido ou estimado; nunca apresente uma estimativa como medição. O aviso deve permanecer visível quando a informação for parcial.

## Privacidade e segurança

Não registre segredos, dados sensíveis ou prompts completos por padrão. Use IDs, hashes, resumos e referências. A observabilidade serve para depuração e confiança, não para retransmitir todo o transcript entre agents.
