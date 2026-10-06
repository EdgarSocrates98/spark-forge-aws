# Analytics Engineering + DuckDB Microscope

## dbt

Use `sparkforge-aws analyze dbt-artifacts --path <project-or-manifest>` after dbt
has produced `manifest.json`, `catalog.json` and `run_results.json`. The output
normalizes models, sources, tests, exposures, metrics and semantic models,
preserves `depends_on.nodes`, selected materialization settings, columns and
run statuses, and reports missing catalog/results as `unresolved`.

No dbt project is imported and no model is executed. A missing `run_results`
does not mean success; a dependency absent from manifest does not become a
source guessed from SQL.

## DuckDB microscope

Use `sparkforge-aws analyze duckdb-microscope --path <bundle.yaml>` for a versioned
read-only bundle. It can carry table/view/Parquet/Iceberg objects, columns,
statistics, manifests, snapshots, EXPLAIN/SELECT observations and declared SQL
equivalence comparisons. Mutating SQL is refused. The analyzer does not install
DuckDB, execute a query, load an extension or write a database.

The bundle is evidence, not a new measurement. To turn it into a claim, retain
the producing command, runtime/version and artifact provenance beside the
bundle. Missing stats stay unresolved.
