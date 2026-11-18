# SparkForge skill contract: operational safety

Operational cloud skills may explain or prepare a change, but the default
path is read-only. Collection is allowed only when the skill explicitly
documents the artifact and the required operator scope. Mutating cloud
provider commands, destructive table maintenance, deletion, policy writes,
and production deploys require explicit confirmation from the operator with
account/subscription, resource, action, and rollback/retention scope.

Before recommending a write:

- separate declared configuration from observed configuration;
- identify the runtime and the authorization layer involved;
- record unresolved cross-account/subscription, resource-policy,
  key-management, or org-policy evidence;
- provide a reversible change or a concrete `git revert`/restore procedure;
- validate data correctness and service health after the change.

Never turn an access-denied error into “add permission” without preserving
`denied_by`. Control-plane permission evaluation does not cover resource
policies, key-management scopes, or catalog grants; report those as
separate unresolved authorization layers when not observed.
