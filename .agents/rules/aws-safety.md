<!-- GENERATED FROM CANONICAL SOURCE — DO NOT EDIT DIRECTLY -->
# AWS Safety Rule — SparkForge AWS

1. AWS operations are READ-ONLY by default.
2. Destructive actions (dropping tables, terminating resources, deleting buckets) require explicit human approval.
3. Secrets, AWS access keys, session tokens, and passwords must NEVER appear in prompts, traces, or logs.
4. Always support `--dry-run` and `--plan` before apply.
