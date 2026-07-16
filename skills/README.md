# Skills

First-party standard Agent Skills sources grouped by stable capability domain:

- [`education/`](./education/)
- [`content/`](./content/)
- [`documents/`](./documents/)
- [`knowledge/`](./knowledge/)
- [`research/`](./research/)
- [`agent-ops/`](./agent-ops/)
- [`engineering/`](./engineering/)

Every direct skill directory contains `SKILL.md` and `manifest.yaml`. Lifecycle and target status do not change the source path. Use the [generated catalog](../docs/skills/index.md) for the authoritative list.

`edu/` is an empty migration marker and must not receive new source. Unresolved third-party legacy copies remain isolated under `openclaw/` until final removal; they are not v2 skills.
