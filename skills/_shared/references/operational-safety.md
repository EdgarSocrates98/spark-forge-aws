# SparkForge skill contract: operational safety

Operational AWS skills may explain or prepare a change, but the default path
is read-only. Collection is allowed only when the skill explicitly documents
the artifact and the required operator scope. Mutating AWS commands, destructive
Iceberg maintenance, deletion, policy writes, and production deploys require
explicit confirmation from the operator with account, resource, action, and
rollback/retention scope.

Before recommending a write:

- separate declared configuration from observed configuration;
- identify the runtime and the authorization layer involved;
- record unresolved cross-account, resource-policy, KMS, or SCP evidence;
- provide a reversible change or a concrete `git revert`/restore procedure;
- validate data correctness and service health after the change.

Never turn `AccessDenied` into “add permission” without preserving
`denied_by`. IAM simulation does not evaluate S3 bucket policy, KMS key policy,
or Glue resource policy; report those as separate unresolved authorization
layers when not observed.
