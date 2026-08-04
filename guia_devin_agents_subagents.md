# Guia Mestre: Arquitetura, Configuração e Operação de Agents e Subagents no Devin

Este documento fornece uma análise exaustiva sobre o funcionamento, a configuração e a utilização estratégica de **agentes** e **subagentes** no ecossistema Devin, abrangendo tanto a interface **Desktop (IDE)** quanto a **CLI (Interface de Linha de Comando)**.

---

## 1. Visão Geral: Agentes vs. Subagentes

No ecossistema Devin, a distinção entre um "Agente" e um "Subagente" é fundamental para a orquestração de fluxos de trabalho complexos:

*   **Agente (Agent):** É a entidade principal de uma sessão. No **Devin Desktop**, o Agente atua como o "Comandante da Frota" (Fleet Manager), podendo ser o próprio Devin (Local ou Cloud) ou agentes de terceiros integrados via protocolo **ACP (Agent Client Protocol)**.
*   **Subagente (Subagent):** São "trabalhadores" independentes gerados pelo agente principal para realizar subtarefas específicas. Eles compartilham o contexto do código e as ferramentas, mas operam em cadeias de pensamento separadas.

---

## 2. Modelos de Agentes Disponíveis

O Devin oferece uma gama de modelos proprietários e de terceiros, cada um otimizado para diferentes cenários de custo, velocidade e inteligência.

### 2.1. Modelos Proprietários (SWE Series)
| Modelo | Status | Destaques e Capacidades |
| :--- | :--- | :--- |
| **SWE-1.7** | **Flagship** | O modelo mais capaz. Melhorado via Reinforcement Learning (RL), foca em investigação profunda antes de editar. Excelente em encontrar causas raiz e requisitos ocultos. |
| **SWE-1.7 Lightning** | **Speed** | Versão ultra-rápida do SWE-1.7 (até 1000 tokens/seg via Cerebras). Mantém a inteligência com latência mínima. |
| **SWE-1.6** | **Legacy** | Versão anterior, mais lenta que a 1.7, mas ainda disponível para compatibilidade e tarefas estáveis. |

### 2.2. Modelos de Terceiros e Open-Weight
O Devin Desktop e CLI suportam modelos externos que podem ser usados como agentes principais ou subagentes:
*   **GLM-5.2:** Modelo de pesos abertos da Z.ai com suporte a **1M de contexto lossless**. É frequentemente oferecido de forma gratuita ou com custo reduzido no Devin, sendo excelente para planejar projetos inteiros devido à sua enorme janela de contexto.
*   **Kimi K2.7:** Outra opção de alta performance disponível para tarefas de codificação complexas.

---

## 3. Devin Desktop: O Centro de Comando (Fleet Manager)

O Devin Desktop é um **Agent Command Center** que permite a gestão simultânea de múltiplos agentes.

### 3.1. Configuração de Modelos no Desktop
Para alterar o modelo do agente ou subagente:
1.  Use o **Agent Selector** no canto inferior direito da interface.
2.  No **Command Palette** (`Cmd+Shift+P`), acesse **"Windsurf User Settings"**.
3.  Na aba **"Agents"**, você pode definir o modelo padrão para o **Devin Local** (ex: mudar de `swe-1.6` para `swe-1.7`).

---

## 4. Devin CLI: Configuração Avançada de Modelos

A CLI permite definir modelos específicos via arquivos JSON (`~/.config/devin/config.json` ou `.devin/config.json`).

### 4.1. Exemplo de Configuração com SWE-1.7 e GLM-5.2
```json
{
  "agent": {
    "model": "swe-1.7",
    "subagents_enabled": true,
    "subagent_default_model": "swe-1.7-lightning",
    "alternative_models": ["glm-5.2", "kimi-k2.7"],
    "permissions": {
      "rules": [
        { "action": "shell_exec", "pattern": "npm test", "allow": "allow" }
      ]
    }
  }
}
```

---

## 5. Subagentes: Operação e Controle

### 5.1. Qual modelo um subagente usa?
O modelo de um subagente é resolvido por um roteador no momento da criação:
*   **Default:** Geralmente resolve para uma variante do `swe-1.6` ou `swe-1.7-lightning` dependendo do plano.
*   **Custom:** Você pode forçar um modelo específico no arquivo de definição do subagente (`agents/<name>.md`):
    ```yaml
    ---
    name: Researcher
    model: glm-5.2
    ---
    ```

### 5.2. Modos de Execução
*   **Primeiro Plano (Foreground):** O agente principal pausa. Ideal para depuração interativa.
*   **Segundo Plano (Background):** Executa em paralelo. Útil para tarefas longas como varredura de segurança ou geração de testes usando o **GLM-5.2** (devido ao contexto longo).

---

## 6. Subagentes Customizados (Custom Subagents)

Crie perfis especializados na pasta `agents/`:
*   **Exemplo (`agents/architect.md`):**
    ```markdown
    ---
    name: Architect
    model: glm-5.2
    max-nesting: 3
    ---
    Use sua janela de contexto de 1M para analisar toda a arquitetura do projeto e sugerir melhorias.
    ```

---

## 7. Melhores Práticas e Estratégia

1.  **Contexto Longo:** Use o **GLM-5.2** para tarefas que exigem a leitura de centenas de arquivos simultaneamente.
2.  **Velocidade de Codificação:** Use o **SWE-1.7 Lightning** para edições rápidas e refatorações de arquivos únicos.
3.  **Investigação Complexa:** Use o **SWE-1.7** (padrão) para bugs difíceis onde a causa raiz não é óbvia.
4.  **Handoff:** Comece uma tarefa localmente com o **SWE-1.7 Lightning** e use `/handoff` para enviar para o Cloud Devin se a tarefa se tornar muito pesada.

---

## 8. Atalhos de Controle (Desktop/CLI)
| Ação | Comando/Atalho |
| :--- | :--- |
| **Alternar Agente** | Menu inferior ou `!ultra`, `!fast`, `!swe` |
| **Mover para Background** | `Ctrl + B` |
| **Trazer para Foreground** | Pressionar `f` no painel de subagentes |
| **Cancelar** | `Ctrl + C` ou `x` no painel |
