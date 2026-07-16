# gorin-edu-outline-review

状态：candidate。以 Markdown 手稿和批准的 Excel 大纲为输入，生成覆盖率、缺失行、顺序、目标动词和占位符报告，不修改输入，也不评价教学质量。

## 已验证

- 真实 `.xlsx`/`.md` 临时 fixture 的 100% 覆盖 happy path；
- 缺少必需表头时 fail closed、非零退出且不输出 traceback；
- 3 组正触发、3 组反触发和 3 个 golden contract；
- 四个目标的构建与受管安装；
- 锁文件已删除未使用的 pandas/numpy 依赖链。

## 仍需人工确认

当前匹配仍包含启发式相似度。晋级前需要用一份真实教学大纲和手稿抽查命中证据，尤其关注短中文知识点、合并单元格和相近模块名产生的误匹配。
