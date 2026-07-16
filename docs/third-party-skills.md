# 第三方技能治理

第三方内容不是本仓库源码的默认组成部分。`registry/external/*.yaml` 是外部来源的机器可读权威记录，必须固定到不可变 revision，并记录版本与许可证；生成 catalog 时只登记元数据，不复制、构建或执行上游代码。

## 三种来源模式

| 模式 | 适用情况 | 存放位置 | 发布行为 |
| --- | --- | --- | --- |
| external | 上游独立维护，本仓库仅推荐或索引 | `registry/external/` | 只进入 catalog，不打包 |
| managed-mirror | 必须保留完全一致的上游内容 | `skills/<domain>/<id>/` | 校验 revision、许可证和内容摘要后打包 |
| adapted | 吸收上游思路并形成自研实现 | `skills/<domain>/gorin-*` | 按 first-party 发布，并声明来源与差异 |

不要把下载脚本、Git 子模块或浮动分支当成来源声明，也不要在治理命令中执行上游 `install.sh`。安装外部技能属于独立的信任决策，应先审阅固定 revision，再按上游说明在隔离环境中操作。

## 登记 external 来源

在 `registry/external/<id>.yaml` 添加：

```yaml
schema_version: 1
id: example-skill
version: 1.2.3
lifecycle: incubating
ownership: external
audience: public
description: A concise routing description.
source:
  url: https://github.com/example/skills/tree/<full-commit>/skills/example
  revision: <full-commit>
  license: MIT
```

随后运行：

```bash
npm run validate
npm run catalog
git diff -- catalog/index.json
```

外部条目不等于安全背书。审阅者仍需核实：revision 是否不可变、许可证是否覆盖拟议用途、仓库是否存在安装脚本/网络下载/凭据读取/宿主机写操作，以及条目描述是否会误触发。

## 建立 managed mirror

仅当离线、可重复构建或上游消失风险确实要求保留副本时采用 mirror。manifest 必须包含：

- 上游 URL 与固定 revision；
- SPDX 许可证和仓库内许可证证据；
- `gorin-skills digest --path ...` 生成的内容摘要；
- 与上游完全一致的边界，禁止在镜像目录内夹带本地修补。

需要本地变化时，转为 adapted 技能，并用 `gorin-` 命名空间表达维护责任。

## 建立 adapted 技能

adapted 技能必须解释借鉴点、行为差异和不兼容边界，不能暗示它仍是上游原件。教学视觉技能是当前实例，见[教学视觉与格式化技能](./gorin-edu-visual-skills.md)。源码统一位于七个稳定能力域之一，不再使用 `skills/edu/`、`general/` 或 `openclaw/` 作为 v2 源码入口。

## 退出与升级

- revision 或许可证变化：作为供应链变更单独审阅；
- external 失去维护：标记 deprecated/retired，不静默换源；
- mirror 产生本地差异：转 adapted，重新命名并记录迁移；
- adapted 不再维护：按五态生命周期退役，兼容 alias 最迟在仓库 v3 前移除。

当前机器可读来源见 [`registry/external/`](../registry/external/)，生成后的统一索引见[技能目录](./skills/index.md)。
