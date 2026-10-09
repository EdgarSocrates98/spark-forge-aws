# SparkForge AWS portátil

[English](SPARKFORGE_AWS_PORTABLE.md)

Os novos verbos desta frente ainda precisam de release. Para testar o checkout
da branch `codex/portable-parity-api-forge`, use `python -m pip install .` na raiz
da branch, ou instale o wheel construído dela por path absoluto. Os exemplos
abaixo com `pip install sparkforge-aws` pressupõem uma release que inclua a frente;
uma versão anterior publicada não ganha esses comandos automaticamente.

Instale em um ambiente do usuário; sem administrador, hosts ou MCP obrigatórios:

```bash
python -m venv "$HOME/tools/sparkforge-env"
"$HOME/tools/sparkforge-env/bin/python" -m pip install sparkforge-aws
"$HOME/tools/sparkforge-env/bin/sparkforge-aws" distribution doctor --root /work/job
```

Windows PowerShell:

```powershell
python -m venv E:\tools\sparkforge-env
E:\tools\sparkforge-env\Scripts\python.exe -m pip install sparkforge-aws
E:\tools\sparkforge-env\Scripts\sparkforge-aws.exe distribution doctor --root E:\work\job
```

Em rede bloqueada, instale o wheel e dependências de um diretório local com
`pip install --no-index --find-links /offline/wheels sparkforge-aws`.
O núcleo funciona offline; extras AWS, parquet e MCP são opcionais.
Assets pertencem à instalação; inicializar projeto não copia skills/agents.

```bash
sparkforge-aws distribution inspect --root /work/job
sparkforge-aws distribution init --root /work/job
sparkforge-aws distribution status --root /work/job
sparkforge-aws context resolve --root /work/job --scope repo
```

`init` cria apenas `.sparkforge_aws/project.yaml`; reexecução preserva o arquivo
e seu ID. Manifesto inválido ou symlink é recusado sem sobrescrita.
`inspect`, `status`, `doctor` e `context resolve` não criam estado nem executam
Git, fontes do projeto, hosts ou rede. `doctor` diferencia capacidades opcionais
e permissões do estado; o probe de permissão não garante sucesso de escrita.
Hashes de assets são inventário de bytes observados, sem alegação de assinatura.

## Estado, cache e configuração

```bash
export SPARKFORGE_AWS_HOME=/portable/state
export SPARKFORGE_AWS_CACHE=/portable/cache
export SPARKFORGE_AWS_CONFIG=/portable/config.yaml
```

```powershell
$env:SPARKFORGE_AWS_HOME = 'E:\portable\state'
$env:SPARKFORGE_AWS_CACHE = 'E:\portable\cache'
$env:SPARKFORGE_AWS_CONFIG = 'E:\portable\config.yaml'
```

Paths relativos usam a raiz do projeto passada ao resolver. Estado/cache são
isolados em `projects/<project_id>`: inicialize o projeto antes de criar estado
externo para preservar identidade ao mover a pasta. Sem manifesto, o fallback é
hash da raiz absoluta e muda ao mover. Duas cópias do mesmo manifesto representam
o mesmo projeto e compartilham namespace; para projeto independente, inicialize
um manifesto novo. HOME não migra nem lê automaticamente o estado legado.

Sem HOME, comandos legados preservam a raiz explícita `--repo` e podem criar
estado no módulo atual se chamados dali; execute-os na raiz do repo ou passe
`--repo` da raiz. O resolver portátil e os consumidores com HOME normalizam a
raiz mais próxima. Não há reroot automático de sandboxes explícitos.

HOME está conectado a `case_path`, `state_dir` e `state_path` (case, journal,
blackboard, traces/codeintel e demais consumidores dessas funções), mais runs
do Lab. CACHE está conectado ao artifact cache padrão, CLI Context Gateway e
MCP Context Gateway. Saídas explícitas `--out`, coletores que escrevem artefatos
no repo e sandbox/proposal com confinamento próprio mantêm contratos existentes;
**não há promessa de redirecionar toda escrita legada**. Use espaço gravável para
essas operações. Um path fornecido explicitamente a `ArtifactCache` prevalece.

Configuração controla a resolução portátil de contexto; não redefine tuning ou
policies dos analisadores existentes. Precedência: defaults → arquivo explícito
CONFIG → `config` no workspace → `config` no projeto → override explícito da
função resolver (na CLI, `context resolve --scope`). Schema permitido:

```yaml
scope:
  default: repo
network:
  mode: offline
host:
  activation: plan_only
```

Config explícita ausente, chaves desconhecidas, segredo, duplicatas e aliases
YAML são recusados. Nenhum arquivo `.env` ou credencial é descoberto/lido.

## Workspace virtual e localidade

```bash
sparkforge-aws workspace discover --root /work/platform --max-depth 4 --max-directories 2000
sparkforge-aws workspace init --root /work/platform --name platform
sparkforge-aws workspace add /work/orders --root /work/platform --name orders
sparkforge-aws workspace add /work/billing --root /work/platform --name billing
sparkforge-aws workspace status --root /work/platform
sparkforge-aws context resolve --root /work/platform --scope workspace
sparkforge-aws context resolve --root /work/platform --scope target --target repository:orders --impact direct
```

Workspace cria apenas `.sparkforge_aws/workspace.yaml`. Repos externos usam paths
relativos com `external: true`, declarados pelo `add`; manifestos legados continuam
confinados. Links simbólicos de raízes/control files são recusados. Paths entre
volumes diferentes usam declaração externa absoluta explícita; ao mover esses
volumes, ajuste a referência. Roots relativas permanecem o padrão quando possível.
Descoberta identifica `.git` arquivo (worktree) ou diretório, projetos e módulos
sem abrir `.git`, fontes ou executar comandos. Não segue links; ignora diretórios
de dependências/estado e expõe limites atingidos como `unresolved`.

Declare dependências, se observadas, no manifesto:

```yaml
relationships:
  orders:
    depends_on: [billing]
```

`direct` segue uma aresta declarada de dependência; `transitive` segue até o
fechamento; `all` inclui todos os repos declarados. Em scope workspace, direct ou
transitive exige `--target` ou que `--root` esteja dentro de um único repo membro.
Alvo desconhecido tem recusa `SF-CONTEXT-TARGET-NOT-FOUND`; relações não declaradas,
repos ausentes e fingerprints não medidos ficam `unresolved`. Isto resolve
localidade, sem inferir tráfego ou deploy. O grafo de domínio existente continua
uma operação explícita que pode ler os arquivos declarados.

## Paridade e limites

| Base portátil API Forge | SparkForge AWS |
|---|---|
| Instalação em venv/prefixo do usuário | Implementada; executável por path absoluto |
| Package/assets separados do consumidor | Wheel existente + inventário offline |
| Inspect/init/status/doctor | Família `distribution` aditiva |
| Workspace discover/init/add/status | Família `workspace` aditiva |
| Repo/workspace/target; direct/transitive/all | `context resolve`, relações declaradas |
| Estado/cache/config explícitos | Conectados aos consumidores descritos acima |
| Host opcional | Core CLI; reutiliza `integrate`/`detach` existentes |
| MCP opcional | Extra existente; nenhuma tool nova |
| Runtime/scorecards API específicos | Sem equivalência automática; domínio Spark próprio |
| Auto-update, execução autônoma e assinatura de assets | Fora desta entrega |

Para ativar hosts use o preview `sparkforge-aws integrate codex --scope user --dry-run` e o fluxo
existente de confirmação/rollback; esta frente não instala nem sobrescreve
configurações de hosts automaticamente. Sem MCP, análise/next-step/playbook
continuam disponíveis pela CLI.

Alguns comandos avançados existentes ainda dependem de assets do checkout,
como registry do Lab e config da Decision Plane. Esta entrega valida o núcleo
portátil empacotado e os novos verbos; não declara todo verbo avançado disponível
no wheel. Forneça explicitamente seus assets/configs quando a operação exigir.
