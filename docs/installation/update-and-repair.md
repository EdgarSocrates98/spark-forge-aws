# Update e repair — spark-forge-aws

## Update

```bash
sparkforge-aws update --to <versão ou tag pinada>
```

`latest` é recusado por contrato — sempre pin a versão. Sem checkout
registrado o update reporta BLOCKED honestamente.

## Repair

```bash
sparkforge-aws status   # mostra o drift (lifecycle.state do health doc)
sparkforge-aws repair   # reassegura regiões gerenciadas
```

Repair restaura arquivos gerenciados removidos e cura blocos
`spark-forge-aws:managed` dentro de arquivos seus — conteúdo fora do bloco nunca
é tocado. Antes de sobrescrever, um snapshot vai para
`<state_dir>/backups/`.

Mutações (`repair`, `update`, `uninstall`) pedem aprovação: `--dry-run`
emite o plano com `status: planned` + `lifecycle.state: planned` (nunca
`completed` — nada foi escrito) e `--yes` executa; sem os dois num pipe,
o recibo sai `blocked`. O estado fino vem no bloco `lifecycle`
(`forge/InstallLifecycle/v1`) de cada recibo — tabela de estados no
[quickstart](quickstart.md#verificar).
