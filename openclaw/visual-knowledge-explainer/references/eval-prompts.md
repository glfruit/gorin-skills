# Eval Prompts

测试场景的提示词。

## Eval A: 教材内容

### Input
```
请生成一个教材页面，关于"如何使用Git进行版本控制"。

内容大纲：
- Git 简介
- 安装 Git
- 配置 Git
- 基础操作：初始化仓库、添加文件、提交
- 进阶：分支管理、合并、冲突解决
- 常见问题和最佳实践
```

### Expected Output
- ✅ Hero section with title "如何使用Git进行版本控制"
- ✅ Learning objectives section
- ✅ 3-7 modules（Git简介、安装配置、基础操作、进阶、问题、最佳实践）
- ✅ Each module has: concept, example, common mistakes
- ✅ Summary section
- ✅ Reference section with further reading
- ✅ Theme: grace or default (educational friendly)

### Failure Cases
- ❌ 只是纯文本 HTML（无结构）
- ❌ 没有 learning objectives
- ❌ 没有 examples
- ❌ 没有 common mistakes

---

## Eval B: 培训资料

### Input
```
请生成一个培训页面，关于"服务器日志收集 SOP"。

SOP 内容：
1. 登录服务器
2. 查看日志目录
3. 常用日志命令：tail -f、grep、awk
4. 日志轮转
5. 故障排查步骤

常见问题：
- 权限不足怎么办？
- 日志文件太大怎么办？
- 如何实时监控？

参考时间：15 分钟
```

### Expected Output
- ✅ Hero section with title "服务器日志收集 SOP"
- ✅ Prerequisites section (无特殊要求或需要基础 Linux 知识)
- ✅ Workflow section with clear steps (5 steps)
- ✅ FAQ section (3 questions)
- ✅ Troubleshooting section
- ✅ Theme: simple (clear steps)
- ✅ Mermaid flowchart for workflow

### Failure Cases
- ❌ 没有 prerequisites
- ❌ 没有 workflow steps
- ❌ 没有 FAQ
- ❌ 没有 mermaid flowchart

---

## Eval C: 知识笔记

### Input
```
请生成一个知识讲解页面，关于" époch 在机器学习中的含义"。

笔记内容：
所谓 epoch，在机器学习中指的是：
- 一个 epoch = 完整训练数据集被学习一次
- epoch vs iteration: epoch 是 complete pass, iteration 是 batch 更新次数
- 如何选择 epoch 数量？Too few → underfitting, Too many → overfitting
- 例子：1000 samples, batch size 100 → 10 iterations per epoch
```

### Expected Output
- ✅ Hero section with title "epoch 在机器学习中的含义"
- ✅ Core concept summary (1 paragraph)
- ✅ Key points: definition, epoch vs iteration, choosing epochs, examples
- ✅ Examples section (with code or math)
- ✅ Reference section
- ✅ Theme: grace or modern (reading friendly)

### Failure Cases
- ❌ 没有 core concept
- ❌ 没有 examples
- ❌ 结构混乱

---

## Eval D: 流程/SOP

### Input
```
请生成一个流程说明页面，关于"Git 分支管理流程"。

流程：
1. 从 main 分支创建 feature 分支
2. 在 feature 分支上开发
3. 提交 PR
4. Code review
5. 合并到 main
6. 删除 feature 分支

使用场景：
- 小团队：feature branch workflow
- 大团队：GitFlow
```

### Expected Output
- ✅ Hero section with title "Git 分支管理流程"
- ✅ Mermaid flowchart showing the workflow
- ✅ Step-by-step narrative
- ✅ Visual aids
- ✅ Theme: simple or default

### Failure Cases
- ❌ 没有 mermaid flowchart
- ❌ 只有文本描述

---

## Eval E: 对比分析

### Input
```
请生成一个对比页面，比较 REST API vs GraphQL。

对比维度：
- 数据获取方式
- 过滤能力
- 版本管理
- 学习曲线
- 适用场景

REST API:
- GET /users/1
- 版本：/v1/users
- 学习曲线：低

GraphQL:
- query { user(id: 1) { name email } }
- 单一端点
- 学习曲线：中等
```

### Expected Output
- ✅ Hero section with title "REST API vs GraphQL 对比"
- ✅ HTML table (not markdown)
- ✅ Summary section with "When to use REST vs GraphQL"
- ✅ Theme: default (clean table)

### Failure Cases
- ❌ 使用 markdown table
- ❌ 没有 summary
- ❌ 表格样式差

---

## Eval F: 技术说明

### Input
```
请生成一个架构说明页面，关于"微服务架构"。

内容：
- 定义：微服务是将应用拆分为小服务的架构
- 优点：独立部署、技术异构、可扩展
- 缺点：分布式复杂性、监控难度、测试困难
- 图解：服务间通信、数据一致性

适用场景：
- 大型复杂应用
- 多团队协作
- 需要独立扩展
```

### Expected Output
- ✅ Hero section with title "微服务架构说明"
- ✅ Key points with clear structure
- ✅ Example section (可能有部署图、通信图)
- ✅ Theme: modern (technical feel)

### Failure Cases
- ❌ 没有清晰的 key points
- ❌ 缺少技术细节

---

## 评估标准

| 项目 | 优秀 (✅) | 一般 (⚠️) | 差 (❌) |
|------|----------|----------|--------|
| 结构完整 | Hero + Modules + Summary + Reference | 缺少一个 section | 缺少两个以上 |
| 教学元素 | Learning objectives + Examples + Mistakes | 缺少一个 | 缺少两个以上 |
| 视觉化 | Mermaid/ diagrams where needed | 文本为主 | 无 |
| 主题适用 | Theme matches content type | Default theme used | Random theme |
| 防溯 | 无装饰性装饰 | 少量装饰 | 大量装饰 |

---

## 自动测试脚本

```
# Test script (pseudo-code)
for eval in eval_a eval_b eval_c eval_d eval_e eval_f; do
    echo "Running $eval..."
    
    # Generate page
    visual-knowledge-explainer prompts/${eval}.txt > output/${eval}.html
    
    # Check structure
    grep -q "Learning Objectives" output/${eval}.html || echo "ERROR: Missing learning objectives"
    grep -q "Summary" output/${eval}.html || echo "ERROR: Missing summary"
    grep -q "Reference" output/${eval}.html || echo "ERROR: Missing reference"
    
    # Check theme
    grep -q "theme-.*" output/${eval}.html || echo "ERROR: No theme detected"
    
    # Check mermaid (if needed)
    if grep -q "workflow" prompts/${eval}.txt; then
        grep -q "mermaid" output/${eval}.html || echo "ERROR: Missing mermaid"
    fi
done
```
