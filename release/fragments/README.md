# Release Fragments

Add one YAML fragment per user-visible change. A fragment must validate against [`../../schemas/release-fragment.schema.json`](../../schemas/release-fragment.schema.json), include a user-facing summary, declare the repository semantic increment, and name every affected local skill with its own increment.

The release command consumes fragments only after all catalogs, profile locks, target packages, version files, and changelog content have been generated successfully.

The released catalog is also written to `release/baselines/catalog-<version>.json`. The next release validates lifecycle transitions against that immutable baseline; the working catalog may carry a development version and must not replace the baseline.
