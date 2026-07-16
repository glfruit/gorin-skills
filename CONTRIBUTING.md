# Contributing

新增或修改技能时，以 manifest、标准 `SKILL.md` 和治理 CLI 为准；不要向任何 `legacy-v1` 隔离目录添加源码。

## 新技能

```bash
./scripts/setup-skill.sh \
  --name gorin-example \
  --domain engineering \
  --description "Use when ..."
```

第一方技能必须使用 `gorin-*` lowercase kebab-case，初始生命周期为 incubating。`SKILL.md` 面向 agent；人类说明放 `docs/skills/`，只有 promoted 必须具备独立人类页。README、install.sh 和逐技能 LICENSE 都不是 Agent Skills 的强制文件。

## 提交前验证

```bash
npm ci
npm test
npm run validate
npm run catalog
npm run docs
npm run build:all
git diff --check
```

不要提交 secret、真实 `.env`、依赖树、虚拟环境、缓存、运行输出或绝对个人路径。第三方源码必须先选择 external、managed mirror 或 adaptation 路径；不能用根 MIT 替代上游许可。

## 晋级与发布

candidate 可由 `quality/cases.yaml`、`quality/evidence.yaml` 和 `qualify` 自动证据建立；promoted 必须再具备 `docs/skills/<id>.md` 与 manifest 中的人类维护承诺。用户可见变化添加 `release/fragments/*.yaml`，先运行：

```bash
node scripts/gorin-skills.mjs release --dry-run
```

不要手改生成的 catalog、文档索引、profile lock 或 target package。
