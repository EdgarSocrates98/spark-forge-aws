<!-- GENERATED FROM CANONICAL SOURCE — DO NOT EDIT DIRECTLY -->
# Terraform Safety Rule — SparkForge AWS

1. Never run `terraform apply` or `terraform destroy` without explicit human authorization.
2. Terraform plans with `destroy` or `replace` actions are flagged as HIGH RISK / BLOCK.
3. IAM policies with unrestricted wildcards (`*`) on sensitive resources are rejected.
4. S3 buckets must enforce `block_public_acls` and `block_public_policy`.
