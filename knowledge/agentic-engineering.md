# Engenharia Agêntica no SparkForge

## Modelo mental

Agents são componentes especializados que observam estado, produzem artefatos verificáveis e passam o controle por contratos. O supervisor coordena, mas não substitui a análise de domínio. A memória compartilhada deve conter fatos e decisões, não transcrições completas.

## Padrão de execução

O fluxo recomendado é `abrir caso -> inventariar -> coletar -> analisar -> julgar -> verificar -> sintetizar -> decidir`. Cada transição tem uma precondição e uma saída. A próxima fase só recebe os dados necessários para executar sua responsabilidade.

## Autonomia segura

Autonomia exige limites explícitos, telemetria, reversibilidade e autorização para ações de escrita. Um agent pode escolher a próxima etapa dentro de uma política; não pode ampliar seu próprio escopo, remover uma verificação ou declarar sucesso sem evidência.

## Memória

Use fatos imutáveis com IDs, snapshots compactos e estado derivado. Deduplicate por fingerprint de conteúdo e versão da ferramenta. Resumos devem apontar para as evidências que cobrem e indicar lacunas.

## Qualidade

Toda conclusão importante deve ser falsificável. Avaliações devem ser determinísticas quando possível, idempotentes, baratas antes de caras, explicáveis e capazes de falhar quando a proteção for quebrada. Testes de holdout devem evitar que o agent apenas memorize o caminho feliz.

## Colaboração

Agents cooperam por handoffs estruturados: objetivo, status, fatos, hipótese, confiança, incertezas, próximo teste, risco e rollback. Revisão adversarial deve procurar causalidade presumida, duplicação de trabalho e divergência entre recomendação e evidência.
