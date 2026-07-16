# gorin-skills

以标准 Agent Skills 源码、逐技能 manifest 和单一治理 CLI 管理的个人技能库。仓库按稳定能力域组织源码，再确定性生成 catalog、profiles、Codex/Claude Code/OpenClaw 目标包、安装计划和发布快照。

当前 v2 已重新资格审查 32 个第一方技能：3 个 candidate、28 个 incubating、1 个 deprecated，尚无技能被无证据标记为 promoted。因此 `default` profile 当前为空，这是质量门禁的真实结果。工作 catalog 使用 `2.0.0-dev`，已发布生命周期基线保持为 `1.0.0`。

## 权威结构

```text
skills/<domain>/<gorin-skill>/   # 标准源码 + manifest.yaml
profiles/                       # 命名选择，不复制实现
registry/external/              # 只登记、不 vendor 的外部来源
catalog/index.json              # 生成的机器索引
docs/skills/index.md            # 生成的人类索引
schemas/                        # manifest/profile/evidence/release schemas
release/                        # catalog 版本与 release fragments
scripts/gorin-skills.mjs        # 唯一治理入口
```

七个能力域为 `education`、`content`、`documents`、`knowledge`、`research`、`agent-ops` 和 `engineering`。完整技能列表见 [生成的技能索引](./docs/skills/index.md)。

## 常用命令

```bash
npm ci
npm test
npm run validate
npm run catalog
npm run docs
npm run build:all

# 只预览，不修改 HOME
node scripts/gorin-skills.mjs install --dry-run \
  --skill gorin-superdoc --target openclaw --home "$HOME"

# 新建 incubating 第一方技能
./scripts/setup-skill.sh \
  --name gorin-example --domain engineering \
  --description "A bounded, trigger-specific workflow."
```

受管安装以中央 receipt 证明所有权，不覆盖无 receipt 的同名目录。开发链接和受管复制都指向生成的 target artifact；宿主机依赖和重启/更新等动作在计划中单独显示，不由 build 静默执行。

## 生命周期与发布面

生命周期为 `incubating → candidate → promoted → deprecated → retired`。自动检查最多证明 candidate 资格；promoted 还需要触发/反触发/golden/test/target smoke 证据、人类说明页和明确维护承诺。

- `default` 及各能力域默认 profile 只选择 promoted。
- `*-lab` profile 是对 incubating/candidate/deprecated 的显式 opt-in。
- `legacy-v1` 显式选择 canonical v2 技能并生成旧名 alias，不保留第二份实现。
- 兼容 alias 和 `legacy-v1` 在 repository major 3 前移除。

首批 candidate 可通过显式配置集查看，不会进入默认安装面：

```bash
node scripts/gorin-skills.mjs profile --name candidate-wave-1
```

## 第三方边界

第三方内容分为 external source、固定 revision/digest/license 的 managed mirror、以及保留来源链的 `gorin-*` adaptation。当前 36 个旧本地副本因来源/许可证未解决或受限而留在 legacy 隔离区，不进入 v2 profiles/build。尤其 `docx`、`pdf`、`xlsx` 的随附条款禁止复制与分发，因此不会作为本仓库产品发布。

治理背景见 [CONTEXT.md](./CONTEXT.md)、[ADR-0001](./docs/adr/0001-govern-skill-sources-and-releases-separately.md) 和 [迁移盘点](./inventory/README.md)。

## License

本仓库第一方内容采用 MIT；第三方条目以各自 registry/provenance 记录为准，根许可证不会覆盖第三方权利。
