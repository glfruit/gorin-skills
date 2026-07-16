# gorin-code-review

状态：candidate。用于审查明确的 git diff、暂存改动、未跟踪新增文件或提交范围，输出具有证据和 `path:line` 定位的 P0–P3 findings，并在任何修复前停在确认门。

## 已验证

- 正/反触发与 staged-only、untracked security、clean diff 三类 golden contract；
- Agent Skills、Codex、Claude Code、OpenClaw 构建和受管安装；
- 根治理测试与生命周期门禁。

## 仍需人工确认

candidate 证据证明契约完整且可安装，没有证明不同模型会以一致召回率触发，也没有替代真实 PR 上的 finding 准确率审阅。晋级 promoted 前，应在至少一个有问题 diff 和一个 clean diff 上观察误报、漏报、严重度与确认门行为，并由维护者签署维护承诺。
