# Offline First Policy

SparkForge first consults knowledge/offline-manifest.json and local files. Missing network never becomes an invented source. Missing source becomes unresolved.

## Verification
Use python -m sparkforge.tools.cli offline verify --repo . for SHA-256 checks. Use offline search for local retrieval. Search performs no DNS, HTTP, cloud SDK or telemetry.
