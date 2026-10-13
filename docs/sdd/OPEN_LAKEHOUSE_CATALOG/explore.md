---
sdd: 1
feature: OPEN_LAKEHOUSE_CATALOG
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Contrato declarativo de catalogs, engines, bindings e tabelas que alimenta o Metadata Graph."
    tradeoffs: ["multi-engine sem rede", "compatibilidade real precisa de evidence por binding"]
  - id: B
    summary: "Conectores live para cada catalog."
    tradeoffs: ["informação atual", "credenciais, rede e diferenças de API fora do núcleo determinístico"]
chosen: A
---

# OPEN_LAKEHOUSE_CATALOG — exploração

O prompt exige Glue Catalog, Iceberg REST, Polaris, S3 Tables, Lake Formation e
integrações futuras Unity/Nessie. A abordagem A cria o contrato comum sem
acoplar o core a um provedor. Coletores live entram depois como fragments com
evidence e unresolved.
