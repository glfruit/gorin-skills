# gorin-edu-markdown-polisher

状态：candidate。用于对教材、课程和培训产品的 canonical Markdown 做局部格式修复，核心不变量是保持语义、结构顺序和未授权范围不变。

## 已验证

- 代码围栏、CJK/English spacing、列表/表格三类正触发；
- semantic rewrite、文档转换、章节重组三类反触发；
- fence、table 和“格式请求夹带语义变化”三个 golden contract；
- 四个目标的构建和受管安装。

## 仍需人工确认

该技能是 prompt-only 流程；当前自动证据验证 contract 结构与安装，不声称已测量真实模型的语义漂移率。晋级前应对包含代码块、表格和图片的真实章节执行至少一次 blind diff review，确认未授权词句和结构零变化。
