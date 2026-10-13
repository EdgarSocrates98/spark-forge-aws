# Uninstall — spark-forge-aws

```bash
sparkforge-aws uninstall            # remove só arquivos gerenciados
sparkforge-aws uninstall --purge    # + remove o estado local (.sparkforge_aws/)
```

O ledger SHA-256 decide ownership: arquivos que você criou ou modificou
depois da instalação ficam no lugar (reportados como `kept`). Diretórios
que esvaziam são podados; os seus permanecem.
