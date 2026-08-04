> ## ⚠️ ESTE DOCUMENTO É HIPÓTESE, NÃO FONTE — SEIS AFIRMAÇÕES DELE CAÍRAM
>
> Ele é a doc trazida pelo usuário que **motivou** a pesquisa de fontes do Devin, e
> está preservado palavra por palavra pela convenção deste repositório: afirmação
> registrada que a fonte derrubou fica como está, com o desvio ao lado. **Não o use
> como referência.**
>
> A fonte é [`knowledge/devin/agents-and-subagents.md`](knowledge/devin/agents-and-subagents.md),
> com URL e `retrieved: 2026-08-04` por afirmação e onze vetos `V-DV-*`. Cada
> afirmação daqui foi conferida contra `docs.devin.ai`; **seis não se sustentaram**,
> e nenhuma delas cairia por inspeção — todas são plausíveis lidas de longe. Os
> pontos contraditos estão marcados **no corpo abaixo**, seção por seção, porque
> quem chega aqui por `grep` não passa por este cabeçalho.
>
> | Onde | O que este arquivo diz | O que a fonte diz |
> |---|---|---|
> | §2, §4.1, §5.1, §6 | `swe-1.7`, `glm-5.2`, `kimi-k2.7` (ponto) | O identificador usa **hífen**; o ponto é label de exibição, e os literais vêm da tabela de **preços do Desktop** — V-DV-2, V-DV-3 |
> | §4.1 | `subagent_default_model`, `alternative_models` | **Não existem** como chave de config. O equivalente é setting de **organização** — V-DV-4 |
> | §4.1 | `subagents_enabled` dentro de `"agent"` | Chave **de topo** e *"(user only)"*: um repositório **não** controla se subagentes rodam — V-DV-5 |
> | §4.1 | `permissions.rules` com `{action, pattern, allow}` | Formato documentado é `permissions` com listas `allow`/`deny`/`ask` de padrões como `Read(src/**)` |
> | §5.1 | default "resolve para `swe-1.6` ou `swe-1.7-lightning` conforme o plano" | Resolve por **roteador no spawn**, para SWE-1.6; `swe-1-7-lightning` não aparece como default de subagente |
> | §6 | "crie perfis na pasta `agents/`" | As abas de descoberta listam `.devin/agents/` e `.agents/agents/`. **Não presuma** que o `agents/` da raiz seja varrido — V-DV-7 |
> | §8 | `!ultra`, `!fast`, `!swe` | Não existem. `!` é prefixo de **bash mode** no Devin CLI; `/fast` existe, com barra — V-DV-11 |
>
> O que **sobreviveu** e virou desenho está em
> [`GUIA_DE_USO.md`](GUIA_DE_USO.md) §3 (uso) e em
> [`docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md`](docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md)
> (decisões).

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

> **CONTRADITO (V-DV-2, V-DV-3).** As grafias com ponto abaixo — `SWE-1.7`, `GLM-5.2`,
> `Kimi K2.7` — são **label de exibição**, e vêm da tabela de **preços do Devin Desktop**.
> O identificador usa **hífen** (`swe-1-7`, `glm-5-2`, `kimi-k2-7`), e nenhuma página do
> CLI os documenta como valor aceito de `--model` ou de frontmatter: os literais que a doc
> do CLI garante são os *short names* `opus`, `sonnet`, `swe`, `codex`, `gemini`, `gpt`.

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

> **CONTRADITO (V-DV-4, V-DV-5).** O bloco JSON abaixo é **inteiramente inventado**, salvo
> `agent.model` e `subagents_enabled` — e este no aninhamento errado. `subagent_default_model`
> e `alternative_models` **não existem** como chave de config (busca literal em cinco páginas:
> zero ocorrências); o equivalente é a setting de **organização** *"Default subagent model"*,
> inacessível a arquivo de repositório. `subagents_enabled` é chave **de topo** e marcada
> *"(user only)"*: **um repositório não controla se subagentes rodam.** O objeto `agent`
> documentado tem exatamente duas chaves, `model` e `show_history_on_continue`. E o formato
> de `permissions` documentado usa listas `allow`/`deny`/`ask` de padrões como `Read(src/**)`,
> não `rules` com `{action, pattern, allow}`.
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

> **CONTRADITO.** A fonte é mais estreita do que o texto abaixo: o modelo resolve por
> **roteador no momento do spawn**, para SWE-1.6, e `swe-1-7-lightning` **não aparece**
> como default de subagente em página nenhuma. "Depende do plano" não está escrito em
> lugar nenhum. Um admin da organização sobrescreve o default, inclusive com a opção
> *None*, que desliga o despacho por completo.
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

> **CONTRADITO (V-DV-7), e o `max-nesting` do exemplo tem ressalva.** As abas de descoberta
> listam `.devin/agents/` e `.agents/agents/` (mais os globais); que o `agents/` da **raiz**
> do repositório seja varrido é frase ambígua do changelog, e **não** deve ser presumida.
> `max-nesting` existe e é real — mas a fonte declara custom subagents **experimentais**
> ("format, behavior, and configuration options may change"), e o campo só entrou em
> 2026-05-26. Este repositório **não** o declara em perfil nenhum: ver o limite declarado
> correspondente no `docs/superpowers/STATUS.md`.

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

> **CONTRADITO (V-DV-11).** `!ultra`, `!fast` e `!swe` **não existem**. No Devin CLI `!` é
> o prefixo de **bash mode**: um `!fast` digitado com input vazio entra em bash mode e
> tenta rodar `fast` como comando de shell. `/fast` existe, com **barra**. `Ctrl+B` para
> mandar ao background está **confirmado**.
| Ação | Comando/Atalho |
| :--- | :--- |
| **Alternar Agente** | Menu inferior ou `!ultra`, `!fast`, `!swe` |
| **Mover para Background** | `Ctrl + B` |
| **Trazer para Foreground** | Pressionar `f` no painel de subagentes |
| **Cancelar** | `Ctrl + C` ou `x` no painel |
