---
sdd: 1
feature: CONFIG_OCA
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/CONFIG_OCA/build_report.md
  sha256: "9f687a3b908cbcb08a4c335718d7e835a159a3fc0a889ad107493a72d98da042"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, sync_skills, agents_parity, router_gates, generated_reference, offline_manifest, sources_lock, surface_lock, status_numbers_gate, claims_gate]
deviations:
  - "A revisao final achou DOIS criticos, e os dois derrubavam afirmacoes centrais. O gate cobria UM arquivo -- exatamente o que o D1 do design rejeita por escrito -- e havia contraexemplo vivo: config/agents.yaml declarava sparkforge_inventory, que nao existe em TOOLS, registrado num spec um mes antes. E o gate nao teria pego o handoffs que a propria feature quebrou em config/teams-expansion.yaml, achado a mao."
  - "O segundo critico: docs/agentic-expansion.md tinha uma secao inteira prescrevendo um fluxo por DEZ dos dezesseis contratos apagados, 35 linhas abaixo da que foi corrigida. Pior, o verified_by do AC4 apontava para um teste que NAO cobria esse arquivo, porque ele nao estava na tupla VIVOS."
  - "O gate estendido passou a cobrir config/agents.yaml e config/teams-expansion.yaml, com REGISTROS por glob de config/*.yaml em vez de lista literal, e com cobertura que falha nomeando chave orfa. Provado por mutacao, nao por leitura."
  - "Eu escrevi no build_report que a remocao nao moveu alegacao publicada nenhuma. Moveu quatro. Li o 0 divergencias final e nao olhei o diff do lock."
  - "docs/agentic-expansion.md era tratado como historico e como vivo ao mesmo tempo. A correcao decidiu: vivo, com tres medidas -- o operations-guide (que esta em VIVOS) aponta para ele como a arquitetura detalhada, o AC4 cobra dele o estado de hoje, e os comandos da secao de verificacao rodam nesta arvore."
  - "sparkforge_inventory saiu de config/agents.yaml: medido, sf-inventory e executor real declarado por 12 agentes, e o contrato dele nao cita essa tool em lugar nenhum. Nome sem artefato."
  - "Quatro arquivos entraram fora do manifesto do design na T2, um deles (config/teams-expansion.yaml) explicitamente no out_of_scope do define -- porque referenciava o que saia, nao porque o escopo mudou."
  - "O subagente da T2 travou esperando o gate de lastro em segundo plano, o terceiro da sessao. Encerrei, inspecionei os quatro arquivos um a um, medi o comportamento de producao e commitei. Na rodada de correcao o gate foi mandado para PRIMEIRO plano, e nao travou."
  - "O rebase sobre a main com o #94 conflitou em claims.lock.json e CODEINTEL-GAP.md, porque as duas branches remediaram os mesmos ids. Resolvido ficando com a main e remediando do zero, pelas proprias provas."
  - "Uma regra da casa foi quebrada e relatada pelo proprio subagente: um sed -i para inserir uma linha de import. O resultado esta correto e conferido, mas a regra era clara."
  - "A revisao em dois estagios por tarefa nao rodou."
---

# CONFIG_OCA — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de três jeitos, e nenhum aconteceu:

- **Nenhum nome declarado em `config/` deixa de resolver.** Medido pelo próprio gate, que
  hoje percorre os três registros.
- **Nada quebrou com a remoção.** O `CanonicalRegistry` carrega, o time
  `governance-security` vem com `handoffs: []`, e nenhum módulo passou a citar o que saiu.
- **O gate fica vermelho quando deve.** Provado por mutação: reintroduzi
  `sparkforge_inventory` em `config/agents.yaml` e o gate falhou nomeando registro, chave e
  nome; restaurei e ele voltou ao verde.

## O que a feature entrega

Saíram sete tools declaradas que não existiam e dezesseis contratos de subagent
byte-idênticos que nada despachava — 17 arquivos. Ficaram intactos os dois blocos medidos
íntegros: 2 agentes e 8 entradas de knowledge.

**O que ela deixa para trás é o gate**, e ele só passou a valer depois da revisão. A
primeira versão cobria um arquivo, que é literalmente o que o D1 do design rejeita. A
versão que entrega percorre `config/*.yaml` por glob, resolve referência (não definição), e
**falha nomeando a chave órfã** quando encontra uma lista sem veredito — em vez de ignorá-la
em silêncio.

## O que a revisão final mudou, e por que ela importou tanto aqui

Os dois críticos tinham a mesma raiz, e é o defeito recorrente desta série: **o critério
estava sendo verificado por algo que não o cobria.** O AC2 prometia "os registros de
`config/`" e o gate olhava um. O AC4 apontava para um teste cego ao único documento que o
próprio design nomeia como ofensor.

Nos dois casos o `sparkforge sdd check` passou — ele confere a forma do artefato, não se o
teste citado mede o que o critério afirma. **É uma limitação estrutural do gate de SDD**, e
fica nomeada aqui como candidata a feature própria.

## Medidas

| | antes (`e4141869`) | depois |
|---|---|---|
| nomes declarados em `config/` que não resolvem | 8 | **0** |
| registros de `config/` cobertos pelo gate | 0 | **todos, por glob** |
| contratos em `subagents/` | 16 | 0 |
| arquivos removidos | — | 17 |
| blocos íntegros preservados | `agents` 2, `knowledge` 8 | iguais |

O oitavo nome era o `sparkforge_inventory`, que nenhuma das duas medidas iniciais tinha
achado porque nenhuma olhava `config/agents.yaml`.

## Gates rodados

| gate | resultado |
|---|---|
| gate do declarado, SF_STUBS, critério de domínio, SDD, bundle (5 arquivos) | 187 passed |
| agente, rota, documento, árvore versionada, referência, números (8 arquivos) | 448 passed, 2 skipped |
| `python scripts/sync_skills.py --check` | exit 0 |
| `python scripts/check_status_numbers.py --strict` (AC5) | 0 divergências |
| `python scripts/check_surface_lock.py` | 0 divergências |
| `python scripts/verify_offline_bundle.py` | `"ok": true` |
| `python scripts/check_vnext_claims.py` | 0 divergências |
| `python -m ruff check sparkforge scripts tests` | limpo |
| `sparkforge sdd check --repo . --feature CONFIG_OCA` | `ok: true`, 0 recusas, 0 lacunas |

## Pendências

- **A cobertura do gate alcança chave de valor-lista.** Uma referência **escalar** nova
  (`teams[].revisor: sf-foo`) passaria sem veredito. Está escrito na docstring do próprio
  teste, com o nome da lacuna.
- **U1 continua aberta:** a varredura alcança só o interior do repositório. Um consumidor
  externo dos contratos removidos é o que o `git revert` do commit da T2 cobre.
- **Segunda camada oca, de código.** Os seis módulos de `sparkforge/tools/` que estavam por
  trás dos sete nomes **existem**; o que nunca existiu foi a declaração de tool MCP. Medido:
  `offline` tem leitor de produção, e `cost` não tem leitor nenhum. É outra feature.
- **`config/agents.yaml` não pode entrar em `VIVOS`** sem exceção: ele tem
  `role: evidence-extractor`, colisão de nome com um contrato removido, e `role` é string
  livre que ninguém resolve. Registrado em comentário no próprio arquivo.
- **`docs/vnext/adrs/ADR-001` ainda cita `config/subagents.yaml`.** ADR é congelado por
  convenção e não foi editado.
- **Divergência pré-existente não tocada:** o contrato do executor `sf-inventory` cita cerca
  de doze tools e o `allowed_tools` do registro cita uma. Mudar isso é decisão de política
  sobre o que `allowed_tools` significa, não correção de referência pendurada.

## Lições

- **Gate que só é observado passando não foi verificado — foi assistido.** A revisão mutou
  o registro para provar que ele fica vermelho; eu repeti a mutação antes de fechar. Foi
  assim que se descobriu que ele passava calado quando a chave mudava de forma.
- **`verified_by` que aponta para teste existente passa no `sdd check` mesmo que o teste não
  toque no que o critério descreve.** Aconteceu no AC4 desta feature, e é estrutural.
- **Eu repeti o erro que tinha acabado de gravar na memória:** aceitei um "0 divergências"
  sem olhar o diff, e afirmei no relatório que nada tinha se movido. Quatro alegações
  tinham. Ler o resultado do gate não é ler o que ele mudou.
- **Limpeza sem trava volta.** O SF_STUBS limpou e a mesma doença reapareceu uma camada
  abaixo dois incrementos depois. A diferença entre as duas features é que esta deixa um
  teste.
