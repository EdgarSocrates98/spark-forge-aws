# Schema Registry e data contracts

## Escopo

Este domínio lê dumps JSON/JSONL salvos de AWS Glue Schema Registry, Confluent
Schema Registry ou um contrato equivalente. O núcleo não chama registry, Kafka,
Glue, banco ou provider; credenciais, ARN, payload e segredo não pertencem ao
artefato.

## Contrato de artefato

```json
{
  "registry": {"name": "orders", "provider": "glue", "compatibility": "BACKWARD"},
  "schema": {
    "name": "orders-value", "format": "AVRO", "version": 2,
    "definition": {"type": "record", "name": "Order", "fields": []}
  },
  "previous": {"definition": {"type": "record", "name": "Order", "fields": []}},
  "auto_register": false
}
```

`schema.registry` identifica provider, registry, subject, formato, versão,
compatibilidade e auto-registro quando declarados. `schema.definition` preserva
campos e obrigatoriedade. `schema.diff` compara somente definição anterior
presente no dump. `schema.unresolved` nomeia JSON inválido, definição ausente,
política ausente ou schema anterior ausente; ele não é equivalente a “seguro”.

Compatibilidade estrutural é um proxy: tipos, campos removidos e campos
obrigatórios são comparados, mas sem consumidores, regras customizadas,
serializador real e configuração efetiva não há prova de compatibilidade
end-to-end. Para produção, preservar owner, subject, versão, modo, audit trail e
redação de dados sensíveis.

## Fontes oficiais

- [AWS Glue Schema Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html)
- [Como funciona o Glue Schema Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry-works.html)
- [API do Glue Schema Registry](https://docs.aws.amazon.com/en_en/glue/latest/dg/aws-glue-api-schema-registry-api.html)
- [Integrações do Glue Schema Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry-integrations.html)
- [Debezium schema history](https://debezium.io/documentation/reference/stable/configuration/storage.html)

Runtime de registry e formato devem ser declarados no dump. O extrator não
converte ausência em default nem afirma que AWS Glue e Confluent têm semântica
idêntica.
