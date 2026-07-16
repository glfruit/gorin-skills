# Skill Development Guide

## 1. Scaffold

```bash
./scripts/setup-skill.sh \
  --name gorin-example --domain engineering \
  --description "Use when the user asks to ..."
```

允许的领域是 `education`、`content`、`documents`、`knowledge`、`research`、`agent-ops`、`engineering`。

## 2. Source contract

`SKILL.md` 遵循 Agent Skills：frontmatter 至少包含与目录一致的 `name` 和明确触发边界的 `description`。目标工具字段不要写进标准源码；放入 `manifest.yaml` 的 adapter，由 build 生成。

manifest 必须通过 [schema](../schemas/manifest.schema.json)，至少声明独立 SemVer、domain、五态 lifecycle、ownership、audience 与 targets。第一方 candidate/promoted 必须使用 `gorin-*`。

## 3. Keep source clean

不得提交 secret、真实 `.env`、symlink、`node_modules`、vendor dependency tree、虚拟环境、cache、`out/`、`generated/` 或运行状态。脚本使用技能内相对路径；用户配置进入 `~/.config/gorin-skills`，状态进入 `~/.local/state/gorin-skills`，或由明确环境变量注入。

## 4. Validate and build

```bash
npm test
npm run validate
node scripts/gorin-skills.mjs build --skill gorin-example
node scripts/gorin-skills.mjs install --dry-run \
  --skill gorin-example --target openclaw --home /tmp/test-home
```

## 5. Qualification and promotion

incubating 先建立真实行为测试。进入 candidate 前，在技能内添加 `quality/cases.yaml` 和 `quality/evidence.yaml`，然后运行：

```bash
node scripts/gorin-skills.mjs qualify --skill gorin-example
node scripts/gorin-skills.mjs validate \
  --baseline release/baselines/catalog-<current-version>.json
```

`qualify` 只校验 case contract，并在临时目录执行全部声明目标的构建和受管安装；它不会执行技能脚本。技能自身的可执行行为必须通过单独、显式的测试命令验证，并记录在 evidence 中。

promoted 需要 evidence 覆盖正触发、反触发、golden case、测试、每个 target build/install smoke 与 clean runtime output，并在 manifest 中引用人类文档、审批人、日期和维护承诺。candidate 不进入默认 profile，机器也不能自动授予 promoted。

## 6. Release

为用户可见变化添加 release fragment，然后只先执行 `release --dry-run`。版本、catalog、profile locks、target packages 与 CHANGELOG 必须来自同一事务。
