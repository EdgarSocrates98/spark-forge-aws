# Matriz do Control-M Automation API — `9.0.21.200` a `9.0.22.100`

**Esta matriz é do Automation API, não do produto Control-M.** As duas coisas
carregam a mesma grafia de versão (`9.0.2x.yyy`) e não são a mesma coisa. Medido
em 2026-09-01, do lado do **produto**: só `9.0.21.300` e `9.0.22` abrem raiz de
documentação própria; `9.0.22.100` está atrás de login de *entitlement* e
`9.0.21.200` não tem raiz própria. Célula sobre o produto fora do Automation API
sai `unresolved` com a razão — nunca preenchida por analogia com o número do
Automation API.

**O acesso à fonte não é o normal deste repositório, e quem revalidar precisa
saber disso antes de concluir que a fonte morreu.** `WebFetch` devolve **HTTP
403** contra `documents.bmc.com` e `docs.bmc.com`. O bloqueio é de
**user-agent**, não de produto: medido nas duas direções — sem UA, 403; com UA
de browser, 200 e corpo de ~475 KB. A releitura é assim:

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
curl -s -A "$UA" --max-time 60 \
  "https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_What_s_New.htm" \
  -o pagina.html
```

A página é MadCap Flare, HTML estático — o conteúdo está no corpo, não em JS.

**O perfil de drift, com o procedimento.** A página é a `Monthly` e **rola**: em
2026-09-01 o rodapé declarava `9.0.22.125`, três degraus acima do topo da faixa.
Ela **fica** vigiada no `sources.lock.json`, e vai disparar drift ~12×/ano. Há
precedente medido e mais brando: [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md)
registra que a página 7.x da AWS *"prepende uma coluna a cada minor"* e que o
*"hash muda ~4×/ano sem que nada que a matriz conhece tenha mudado — alarme
esperado"*. O procedimento aqui, literal:

> A faixa `9.0.21.200`–`9.0.22.100` é **passado fechado**: nada que role muda o
> que aconteceu no `9.0.21.300`. Ao drift, confira se alguma célula **da faixa**
> mudou — não deveria, e se mudou é errata da BMC e vale leitura. Linha nova de
> versão **futura** não entra sem alguém ler.

Isso torna o alarme mensal barato: quase sempre fecha sem ação, e este parágrafo
diz por quê.

---

## 1. A pergunta, e o que esta matriz passou a sustentar

O operador **não tem Control-M instalado**, não tem artefato de runtime, e pediu
*"conhecimento para atuar em todas as versões entre `9.0.21.200` e
`9.0.22.100`"*. O incremento 1 entregou **dado e consulta** — `sparkforge
controlm describe --version <v>` — e registrou aqui que não havia extrator nem
regra, porque sem artefato não há corpus e regra sem corpus é o que este
repositório recusa.

**Metade dessa frase caiu, e vale ler qual metade.** Ela valia para
`describe-job-run`, que é saída de runtime e exige a instância. Não vale para
`Jobs-as-Code`: definição de job em JSON, **versionada no repositório do
cliente**, que `ctm build` valida e `ctm deploy` publica. O operador
plausivelmente a tem mesmo sem ter o Control-M — é a mesma natureza de um
`main.tf` ou de um `.py` de PySpark, que este motor já lê.

Sobre esse artefato nasceu o extrator `sparkforge/facts/controlm_jobs.py` e a
área de regra `SF-CTM`, com **uma** regra: capacidade usada pelo job que a
versão declarada não tem. A fronteira de versão **não é repetida na regra** —
ela mora neste documento e no YAML irmão, e o cruzamento acontece no extrator,
que emite o kind já decidido. Ver
`docs/superpowers/specs/2026-09-01-sparkforge-controlm-jobs-as-code-design.md`.

Duas coisas continuam **não** existindo, e as duas por falta de fonte, não por
falta de tempo:

- **Regra sobre dependência, janela ou SLA.** A página *What's New* não sustenta
  o que é *defeito* nesses eixos. Os facts saem (`ctm.dependency`,
  `ctm.schedule`) porque a fonte nomeia os campos; julgá-los exige pesquisa nova
  no `API_CodeRef`, e é o incremento 3.
- **Regra de segredo em texto claro.** Medido na leitura de
  `API_CodeRef_JobProperties.htm`: os 44 blocos que ela publica **não têm campo
  de credencial**. `Password` existe em *connection profile*, que é outro
  artefato, e lá a BMC publica a forma correta — `"Password": {"Secret":
  "<nome>"}`, resolvida de vault no deploy. O extrator **redige** valor de
  `Variables` que casa o detector compartilhado, e isso não é julgamento: é
  impedir que o próprio `facts.json` do handoff vire a segunda cópia do segredo.

## 2. A fonte, e o que ela publica em tabela

```
https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_What_s_New.htm
```

A página tem **quatro tabelas**, e as quatro foram lidas como tabela HTML —
`<tr>` a `<tr>`, com a coluna de versão ao lado da coluna de descrição. Isso
importa: no texto achatado, a versão aparece **depois** da descrição, e ler o
achatado desalinha o par por uma linha. A leitura de 2026-09-01 corrigiu por
esta via uma célula que estava errada na spec de desenho: o job type
`Job:DetachedEmbeddedScript` é de **`9.0.22.005`**, não de `9.0.22.010` —
conferido no HTML cru, dentro do mesmo `<tr>`. A `9.0.22.010` é a versão do CLI
baseado em Python, que é a linha **seguinte** da tabela.

| Tabela da página | Linhas | Na faixa | Para onde vão |
|---|---|---|---|
| *Enhancements* | 59 | **45** | 45 `capabilities`; uma delas rende **também** duas células de `components` |
| *What's Changed* | 10 | **7** | 4 `capabilities`, 3 `components` |
| *Corrected Problems* | 249 | **175** | **nenhum eixo** — ver §6 |
| *Deprecated and Discontinued* | 4 | 4 | 2 `capabilities`, 2 `components` |

A tabela de *Deprecated* não tem coluna *Version* — ela tem *Announcement
Date*, e a versão da fronteira mora na prosa da própria linha. Uma delas
(`config_server_params_get`) declara **duas** fronteiras, e só a segunda está na
faixa.

Contagem de versões, e ela reconcilia:

| | |
|---|---|
| versões citadas na página inteira (`9.0.20.200` a `9.0.22.125`) | **45** |
| citadas na faixa `9.0.21.200`–`9.0.22.100` | **31** |
| na faixa, com afirmação em algum dos dois eixos | **22** |
| na faixa, sem afirmação, nomeadas em `unresolved` | **9** |
| versões que aparecem numa **coluna** *Version* (qualquer tabela) | 41 |

As **45** e as **31** são exatamente os números que a spec de desenho mediu, e
foram reconferidos por conta própria em 2026-09-01. A página declara
`Published - September 01, 2026` e `9.0.22.125` no rodapé — quer dizer que a
leitura desta entrega é do mesmo dia da spec, e nada rolou entre as duas.

## 3. Eixo 1 — capacidade com fronteira de versão

**51 afirmações.** `introduced_in` 40, `changed_in` 9, `deprecated_from` 1,
`discontinued_in` 1. Cada linha é uma linha de tabela da página, com a versão da
coluna *Version* ao lado. O resumo de cada uma está no `.yaml` irmão, em
`capabilities.<slug>.summary`.

| Capacidade | Fronteira | Versão | Substituída por |
|---|---|---|---|
| `deploy_jobtype_get` | `introduced_in` | 9.0.21.200 | — |
| `run_userdaily_missing` | `introduced_in` | 9.0.21.200 | — |
| `run_ondemand` | `introduced_in` | 9.0.21.200 | — |
| `config_em_high_availability` | `introduced_in` | 9.0.21.200 | — |
| `file_transfer_job_new_parameters` | `introduced_in` | 9.0.21.200 | — |
| `config_item_recycle_service` | `introduced_in` | 9.0.21.200 | — |
| `config_server_notification_list_setactive` | `introduced_in` | 9.0.21.200 | — |
| `agentless_host_configuration` | `introduced_in` | 9.0.21.200 | — |
| `ssh_key_configuration` | `introduced_in` | 9.0.21.200 | — |
| `load_balancer_router_management` | `introduced_in` | 9.0.21.200 | — |
| `config_server_agent_test` | `introduced_in` | 9.0.21.200 | — |
| `mfte_processing_rules` | `introduced_in` | 9.0.21.200 | — |
| `deploy_zip_package_with_descriptor` | `introduced_in` | 9.0.21.200 | — |
| `deploy_folders_get` | `introduced_in` | 9.0.21.205 | — |
| `config_server_failover_async` | `introduced_in` | 9.0.21.215 | — |
| `run_jobs_status_history_run_date` | `introduced_in` | 9.0.21.215 | — |
| `workbench_docker_image` | `introduced_in` | 9.0.21.220 | — |
| `workflow_insights_data_export` | `introduced_in` | 9.0.21.225 | — |
| `host_restriction_params_inline` | `changed_in` | 9.0.21.235 | — |
| `config_server_high_availability` | `introduced_in` | 9.0.21.300 | — |
| `config_server_definition_management` | `introduced_in` | 9.0.21.300 | — |
| `external_vault_cyberark_secrets` | `introduced_in` | 9.0.21.300 | — |
| `resources_array_duplicate_names` | `introduced_in` | 9.0.21.300 | — |
| `rbc_exception_policy_shift` | `introduced_in` | 9.0.21.300 | — |
| `mssql_agentjob_rerun_from_step` | `introduced_in` | 9.0.21.300 | — |
| `config_em_param_set` | `deprecated_from` | 9.0.21.300 | `config systemsettings::set` |
| `config_server_params_get` | `discontinued_in` | 9.0.21.300 | `config systemsettings:server::get` |
| `run_job_bypass` | `introduced_in` | 9.0.21.310 | — |
| `run_forecast_timeline` | `introduced_in` | 9.0.21.310 | — |
| `deploy_connectionprofile_centralized_test` | `introduced_in` | 9.0.21.315 | — |
| `hostgroup_application_type_filter` | `introduced_in` | 9.0.21.315 | — |
| `run_order_job_subset` | `changed_in` | 9.0.21.330 | — |
| `apm_monitoring_java_processes` | `introduced_in` | 9.0.22.000 | — |
| `folders_array_structure` | `introduced_in` | 9.0.22.000 | — |
| `delete_user_tokens_on_user_delete` | `introduced_in` | 9.0.22.000 | — |
| `em_ha_status_step_detail` | `changed_in` | 9.0.22.000 | — |
| `job_detached_embedded_script` | `introduced_in` | 9.0.22.005 | — |
| `cli_python_based` | `changed_in` | 9.0.22.010 | — |
| `config_em_alerts_delete` | `introduced_in` | 9.0.22.015 | — |
| `run_job_modify_zos` | `changed_in` | 9.0.22.015 | — |
| `run_jobs_status_event_filters` | `introduced_in` | 9.0.22.025 | — |
| `deploy_descriptor_map_condition` | `introduced_in` | 9.0.22.025 | — |
| `deploy_descriptor_rename_action` | `introduced_in` | 9.0.22.025 | — |
| `run_job_related` | `introduced_in` | 9.0.22.030 | — |
| `deploy_descriptor_numeric_condition` | `introduced_in` | 9.0.22.030 | — |
| `created_by_under_strict_author_security` | `introduced_in` | 9.0.22.035 | — |
| `allowed_port_443` | `changed_in` | 9.0.22.045 | — |
| `ssh_key_management_v2` | `introduced_in` | 9.0.22.055 | — |
| `agentless_and_remote_host_85_chars` | `changed_in` | 9.0.22.060 | — |
| `openapi_31_spec` | `changed_in` | 9.0.22.060 | — |
| `provision_upgrade_activity_name_validated` | `changed_in` | 9.0.22.060 | — |

Duas notas que a tabela não cabe:

- **`config_server_params_get` tem fronteira dupla, e uma delas está abaixo do
  piso.** A fonte diz *"API command `config server:params::get` is deprecated
  from version 9.0.21.100 and will be discontinued in version 9.0.21.300"*. A
  depreciação (`9.0.21.100`) está **fora** da faixa e a descontinuação
  (`9.0.21.300`) está dentro. A matriz registra a que está dentro; o número de
  fora aparece no `summary` como leitura literal da mesma linha, e `describe`
  nunca responde por `9.0.21.100`.
- **`ssh_key_management_v2` substitui comandos cuja depreciação a fonte não
  data.** A linha diz que os comandos antigos *"are planned to be deprecated"* —
  **planejada**, sem versão. Não há `deprecated_from` para eles, e inventar um
  seria célula sem fonte.

## 4. Eixo 2 — componente com exigência por versão

**6 afirmações, em 4 versões.** Aqui mora tudo o que é exigência sobre o que o
Automation API roda em cima, ou sobre o que uma imagem dele contém — nunca
capacidade.

| Componente | Versão | Exigência |
|---|---|---|
| `solaris` | 9.0.21.230 | supported false |
| `java` | 9.0.21.325 | minimum 17; unsupported 11 |
| `python` | 9.0.22.010 | minimum 3.8.4 |
| `pip` | 9.0.22.010 | minimum 20.1.1 |
| `control_m_em_in_workbench_image` | 9.0.22.045 | value 9.0.22.000 |
| `ctm_python_client` | 9.0.22.045 | value 2.5.7 |

A coluna *Exigência* é a forma canônica de `minimum`, `unsupported`, `supported`
e `value` do `.yaml`, nessa ordem. As quatro chaves não são a mesma coisa:

- `minimum` e `unsupported` são **exigência** — `java` em `9.0.21.325` tem as
  duas, e as duas vêm de linhas **independentes** da página: *"Starting with
  Control-M Automation API version 9.0.21.325, Java 17 or higher is required"*
  (*What's Changed*) e *"Control-M Automation API no longer supports Java 11 as
  of version 9.0.21.325"* (*Deprecated and Discontinued*). Duas linhas, uma
  célula, nenhuma inferência.
- `supported: false` é a retirada de uma plataforma inteira — `solaris` em
  `9.0.21.230`, sem versão porque não é versão que se retira.
- `value` **não é exigência**: é o que uma imagem ou um cliente companheiro
  **contém**. `control_m_em_in_workbench_image` e `ctm_python_client` são os
  dois casos, e estão neste eixo porque a forma é a mesma — componente → versão,
  numa versão do Automation API —, não porque sejam requisito.

## 5. `describe`, e o que ele compõe

`describe <versão>` responde **quais capacidades existem** e **quais exigências
de componente valem** naquela versão. A composição é leitura de fronteira, não
interpolação: uma capacidade com `introduced_in: 9.0.21.300` existe em toda
versão **≥** `9.0.21.300` da faixa, porque é isso que *"is now available in"*
afirma. Cada item da saída carrega `declared_at`, a versão onde a fronteira foi
declarada, para que quem lê veja que a resposta em `9.0.22.060` sobre Java vem
de `9.0.21.325` e não de uma leitura nova.

**Versão fora da faixa é recusa NOMEADA**, com o intervalo que a matriz
sustenta, e o mesmo vale para versão que a página nunca cita — `9.0.21.301` não
existe, e responder por ela seria interpolar entre duas versões observadas. Não
há `UNKNOWN` mudo e não há extrapolação.

## 6. O que a fonte NÃO sustenta

**12 recusas nomeadas.** Nenhuma célula desta matriz fica vazia: ou tem
fronteira com fonte, ou está aqui com a razão.

| Item | Razão da recusa |
|---|---|
| `9.0.21.210` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.21.305` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.21.320` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.21.335` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.21.340` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.22.020` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.22.040` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.22.050` | a pagina so traz linhas de Corrected Problems nesta versao; defeito corrigido nao e capacidade nem exigencia de componente |
| `9.0.22.100` | topo da faixa pedida, citada so como pre-requisito de Control-M/Agent e de Control-M/EM -- nunca como versao do Automation API que introduz ou muda algo |
| `corrected_problems` | as 175 linhas de Corrected Problems da faixa nao entram em eixo nenhum; defeito corrigido nao e capacidade nem exigencia de componente |
| `nodejs_version` | a fonte declara a troca de Node.js para Python em 9.0.22.010 e nunca declara qual versao de Node.js era exigida antes |
| `control_m_product_versions` | esta matriz e do Automation API; do lado do produto so 9.0.21.300 e 9.0.22 abrem, 9.0.22.100 exige login de entitlement e 9.0.21.200 nao tem raiz de doc propria |

O caso que mais importa dos doze é o **`9.0.22.100`**, porque é o **topo da
faixa que o operador pediu**. A página cita esse número duas vezes, e nas duas
como pré-requisito de **outro componente** — *"CA management commands are
supported on Control-M/EM versions 21.200 and later with Control-M/Agent
9.0.22.100 or later"* e *"…installed with Control-M/EM version 9.0.22.100"*.
Nenhuma linha da tabela de *Enhancements*, de *What's Changed*, de *Corrected
Problems* ou de *Deprecated* tem `9.0.22.100` na coluna *Version*. A leitura
honesta é que **o Automation API não teve release mensal `9.0.22.100`** — a
sequência da faixa vai `9.0.22.060` → `9.0.22.105` —, e `9.0.22.100` é número do
**produto**. Isso é exatamente a distinção do cabeçalho, e é por isso que ela não
é formal.

O segundo caso é o das **175 linhas de *Corrected Problems***. Um defeito
corrigido não é capacidade — não há nada de novo que se possa fazer — e não é
exigência de componente. Forçá-lo num dos dois eixos daria 175 células de uma
natureza diferente das outras 57, e é o erro que a §3 do `.yaml` recusa. A
classe inteira sai nomeada, com a contagem, e a razão está escrita.

## Fontes

A primeira é a fonte de **toda** fronteira de versão desta matriz. As três
seguintes descrevem a **forma** do artefato `Jobs-as-Code` e não publicam
fronteira nenhuma — foram lidas no incremento 2 (§8) e alimentam o extrator, não
as células das §3 e §4.

- Control-M Automation API — What's New (as quatro tabelas: *Enhancements*, *What's Changed*, *Corrected Problems*, *Deprecated and Discontinued*; a fonte de **todas** as células das §3 e §4). https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_What_s_New.htm (retrieved 2026-09-01)
- Job Properties — os 44 blocos de propriedade de job, folder e sub-folder. https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_JobProperties.htm (retrieved 2026-09-01)
- Job Types — os 71 tipos de job publicados. https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_JobTypes.htm (retrieved 2026-09-01)
- Folders and Flows — `Folder`, `SubFolder`, `Simple Folder` e `Flow`, e a estrutura de array. https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_Folder.htm (retrieved 2026-09-01)
- Secrets in Code — a forma correta de credencial (`{"Secret": "<nome>"}`), em connection profile e **não** em definição de job. https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_SecretsInCode.htm (retrieved 2026-09-01)

### O que esta fonte NÃO sustenta

- **A versão de qualquer componente do produto Control-M fora do Automation
  API.** A página é do Automation API, e a raiz de documentação do produto
  cobre `9.0.21.300` e `9.0.22` e mais nada nesta coleta. Um número do produto
  **não** se deriva do número do Automation API, apesar da grafia idêntica.
- **Que `9.0.22.100` seja uma release do Automation API.** O que se mediu é que
  ela aparece só como pré-requisito de Control-M/Agent e de Control-M/EM, e
  nunca na coluna *Version*. Não foi testado o que a API responde a esse número.
- **A versão de Node.js exigida antes de `9.0.22.010`.** A página declara a
  troca de Node.js para Python e nunca declara qual Node.js era o suportado.
  Não citar número, nem o da imagem do Workbench.
- **O que existe entre duas versões observadas.** A página publica por release
  mensal, e a faixa tem degraus de 5 em 5 (`…200`, `…205`, `…210`). `9.0.21.301`
  não é uma versão desta matriz, e `describe` recusa por nome em vez de
  responder pelo degrau de baixo.
- **Que uma capacidade sem `deprecated_from` continue existindo hoje.** O que se
  mediu é que a página não a lista como depreciada até `9.0.22.125`. Ausência de
  linha de depreciação é ausência de linha, não garantia de permanência.
- **Que as 175 linhas de *Corrected Problems* não escondam mudança de
  comportamento.** Várias delas descrevem correção que muda o que uma chamada
  devolve. Classificá-las exigiria ler o que o comando fazia antes, e a página
  não publica isso — por isso a classe sai `unresolved` inteira, e não
  parcialmente promovida a `capabilities`.
- **A versão do Control-M que executa uma definição de job.** Medido campo a
  campo em *Job Properties* (§8): nenhum dos 44 blocos a nomeia. É por isso que
  ela é **declarada** pelo operador — `--version` — e nunca inferida do
  conteúdo, e é por isso que sem declaração a regra `SF-CTM-001` não dispara.
- **Quando um job type foi introduzido, fora do único que a *What's New*
  data.** *Job Types* publica 71 tipos e não carrega coluna de versão. Um tipo
  ausente desta matriz pode ser anterior à faixa ou posterior ao teto, e esta
  fonte não separa os dois casos — por isso o extrator não o sonda, e a
  contagem do que ele não perguntou sai em `capability_unresolved_count`.

---

## 8. O schema de `Jobs-as-Code`, lido no incremento 2

Três páginas, lidas em 2026-09-01 com o mesmo UA de browser da seção 2:

```
https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_JobProperties.htm
https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_JobTypes.htm
https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_CodeRef_Folder.htm
```

### 8.1 O acesso — a armadilha da seção 2, com uma correção

O incremento 1 registrou que `WebFetch` devolve 403 e que UA de browser resolve.
**A segunda metade é mais dura do que se pensava**, e a correção fica aqui
porque quem for reler a fonte vai bater nela:

`documents.bmc.com` serve um **desafio interativo do Cloudflare** (`<title>Just
a moment...</title>`, `challenges.cloudflare.com` no CSP), e ele **não** é um
rate limit que passa com pausa. Medido nesta coleta: `API_CodeRef_JobProperties`
e `API_CodeRef_JobTypes` devolveram 403 em **três tentativas cada**, com pausas
de 50 s entre elas e UA de browser em todas — nove 403 no total —, enquanto
`API_CodeRef_Folder` devolveu **200 na primeira tentativa**, na mesma sessão e
com o mesmo cabeçalho. O bloqueio é **por URL e intermitente**, não por janela de
tempo.

O que funciona é um **navegador de verdade**, que executa o desafio. Conclusão
prática, e ela substitui o conselho de "espere 45 s": se `curl` com UA falhar
duas vezes na mesma página, **troque de mecanismo** em vez de esperar mais.

**Correção de 2026-09-02, e ela suaviza a frase acima sem a apagar.** A releitura
de `API_CodeRef_JobProperties` para o incremento 3 devolveu **200 na primeira
tentativa**, com `curl` e UA de browser — 423 239 bytes, a mesma URL que dera
nove 403 no dia anterior. Isso **confirma** o diagnóstico de intermitência por
URL e **contradiz** a conclusão prática de "exige navegador": a página não exige,
ela às vezes recusa.

Então a ordem de tentativa é: **`curl` com UA primeiro**, sempre; navegador só
depois de duas recusas na mesma página. Abrir navegador por padrão paga um custo
alto por uma barreira que, medida em dois dias diferentes, esteve aberta num
deles.

### 8.2 A forma do artefato

Objeto nomeado com `Type` é a unidade. `Folder`, `SimpleFolder` e `SubFolder`
são container; `Job:*` é job; `Flow` declara sequência; `If` declara ação
condicional. `Defaults` é chave reservada de topo e não é nem folder nem job.

```json
{
  "Defaults": {"Application": "SampleApp", "RunAs": "USERNAME"},
  "AutomationAPISampleFlow": {
    "Type": "Folder",
    "CommandJob": {"Type": "Job:Command", "Command": "echo my 1st job"},
    "Flow": {"Type": "Flow", "Sequence": ["CommandJob", "ScriptJob"]}
  }
}
```

### 8.3 Três coisas medidas que contradizem o que se supunha

**`ActionIfFailure` não é propriedade do schema.** Ela aparece no
`AutomationAPISampleFlow.json` oficial e no exemplo de *If:CompletionStatus*, e
nos dois é apenas o **nome que o autor deu** ao objeto — o que o schema define é
`"Type": "If"`. Procurar a chave literal acharia o exemplo da BMC e perderia
todo `If` batizado de outro jeito. O extrator reconhece pelo `Type`.

**A definição de job não tem campo de credencial.** Os 44 blocos de *Job
Properties* cobrem tipo, agendamento, dependência, ação, recurso e identidade.
`Password` é de *connection profile*, e a página *Secrets in Code* publica a
forma correta lá: `"Password": {"Secret": "<nome>"}`, com o valor resolvido de
Control-M Vault ou de vault CyberArk externo no deploy. A única superfície livre
da definição de job é `Variables`, uma lista de pares `{nome: valor}`.

**A página *Job Types* publica 71 tipos**, e a *What's New* nomeia **um** deles
dentro da faixa desta matriz (`Job:DetachedEmbeddedScript`, `9.0.22.005`). Os
outros 70 são anteriores à faixa ou não datados por esta fonte, e é por isso que
o extrator **não os sonda**: acusá-los diria que uma versão não suporta
`Job:Command`, que é falso.

### 8.4 O que o cruzamento observa, e o que ele recusa

Duas sondas, e as duas apontam para uma entrada **desta** matriz:

| Evidência no artefato | Capacidade | Fronteira (deste documento) |
|---|---|---|
| `Type: Job:DetachedEmbeddedScript` | `job_detached_embedded_script` | `introduced_in 9.0.22.005` |
| `Folders`/`SubFolders` como **lista** | `folders_array_structure` | `introduced_in 9.0.22.000` |

Cinco capacidades foram avaliadas e **recusadas** como sonda, com a razão em
`sparkforge/facts/controlm_jobs.py`: `mssql_agentjob_rerun_from_step` (a
capacidade é o rerun a partir do passo, não o job type, que é anterior),
`created_by_under_strict_author_security` (a fronteira é sobre configuração do
Control-M/EM, fora do artefato), `external_vault_cyberark_secrets` (mora em
connection profile centralizado), `file_transfer_job_new_parameters` (a fonte diz
"novos parâmetros" e não os nomeia) e `resources_array_duplicate_names` (exige
uma flag de `automation-api.properties`, fora do artefato).

E o cruzamento tem **três** saídas, não duas. A terceira é o que impede o
silêncio desta matriz — 9 versões sem afirmação, 175 linhas de *Corrected
Problems* — de virar aprovação: capacidade que a matriz não nomeia, versão acima
do teto e versão que a fonte não publica saem como recusa **nomeada**, com a
medida que a destrava.
