# Architecture

Gorin Skills 将源码治理与发布面分离：`skills/<domain>/<id>` 是唯一实现源，`manifest.yaml` 是版本、领域、生命周期、所有权、目标、alias 与风险的治理真相。catalog、profiles、target artifacts、receipts 与 releases 都是派生物。

```text
SKILL.md + manifest.yaml
          │
          ├─ validate ─ catalog ─ docs index
          ├─ profile resolution ─ profile locks
          ├─ target adapters ─ Agent Skills/Codex/Claude/OpenClaw packages
          ├─ install plan ─ managed install/link ─ receipt ─ doctor
          └─ release fragments ─ versions/changelog/snapshot
```

稳定路径按能力域，而不是 harness 或成熟度组织。harness 差异只在构建时注入；OpenClaw `metadata` 以单行 JSON 生成，不反写标准源码。

外部来源只进 registry；managed mirror 必须固定上游 revision、SHA-256 与许可证；adaptation 由本仓库维护、使用 `gorin-*` 并保留来源链。构建不执行技能脚本或安装器。

工作 catalog 使用开发版本；`release/baselines/catalog-<version>.json` 保存不可变的已发布生命周期状态。release 在生成新版本前先验证合法转换，并把同一 staged catalog 写成下一版本 baseline，避免 catalog 被重新生成后失去历史比较点。

安装仅覆盖有效 receipt 所拥有的目标。doctor 按 workspace skills、workspace `.agents`、user `.agents`、user OpenClaw 顺序报告断链、重复名、旧 alias 和有效赢家，同时单列仍存在的 `legacy-v1` 源码根。兼容 alias 和遗留配置集在 repository major 3 前移除。

完整决策见 [ADR-0001](./adr/0001-govern-skill-sources-and-releases-separately.md)。
