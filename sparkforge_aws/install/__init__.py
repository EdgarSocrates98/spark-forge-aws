"""`sparkforge-aws install` — instalacao no projeto/workspace, ciclo de vida.

`integrate` cobre o escopo `user` (HOME); este pacote cobre `project` e
`workspace`: os mesmos assets renderizados por `integrate/render`, gravados
pela mesma maquina de posse (`integrate/writer`), mas sob a raiz do
repositorio e com manifesto em `.sparkforge_aws/integrations.json`.

Documentos emitidos: `forge/InstallReceipt/v1` (recebido por operacao em
`.sparkforge_aws/install/receipts/`), `forge/InstallationHealth/v1`
(`install doctor`), e a entrada `forge/InstallationManifest/v1` em
`~/.forge/installations/spark-forge-aws.json` quando a atualizacao vem do
runtime instalado pelo bootstrap.
"""
