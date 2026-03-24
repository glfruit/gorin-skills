# PKM Save Note - 使用指南

## 快速开始

### 环境配置

```bash
# 设置你的 Obsidian Vault 路径
export OBSIDIAN_VAULT_PATH="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/MyVault"
```

### 基本用法

```bash
# 保存快速笔记
echo '{"content":"今天完成了技能创建","type":"log"}' | node scripts/save-note.ts

# 保存到指定项目
echo '{"content":"项目规划...","type":"plan","project":"MyProject"}' | node scripts/save-note.ts

# 保存到指定领域
echo '{"content":"本周回顾...","type":"review","area":"Learning"}' | node scripts/save-note.ts
```

## Agent 调用示例

### TypeScript/JavaScript

```typescript
// 完整参数调用
const result = await tool('pkm-save-note', {
  content: "笔记内容...",
  title: "可选标题",
  type: "summary",     // log | thought | meeting | plan | summary | review | decision
  project: "ProjectName",  // 保存到 Projects/ProjectName/
  area: "AreaName",        // 保存到 Areas/AreaName/
  tags: ["custom-tag"],
  auto_link: true,     // 自动查找相关笔记
  dry_run: false       // true = 预览，不实际保存
});

console.log(result.file_path);  // 生成的文件路径
console.log(result.links_created);  // 自动创建的链接
```

### Shell

```bash
# 通过 stdin 传递 JSON
cat <<EOF | node ~/.openclaw/skills/pkm-save-note/scripts/save-note.ts
{
  "content": "会议记录内容...",
  "type": "meeting",
  "project": "Alpha",
  "tags": ["weekly-sync"]
}
EOF
```

## 分类规则

系统按以下优先级确定笔记保存位置：

1. **显式 project** → `Efforts/1-Projects/{project}/`
2. **显式 area** → `Efforts/2-Areas/{area}/`
3. **内容匹配项目名** → `Efforts/1-Projects/{detected}/`
4. **内容匹配领域名** → `Efforts/2-Areas/{detected}/`
5. **类型默认位置**：
   - `log/thought` → `Zettels/1-Fleeting/`
   - `summary/decision` → `Zettels/3-Permanent/`
   - `meeting/plan` → `Projects/{detected or Unsorted}/`
   - `review` → `Areas/{detected or General}/`

## 模板类型

| 类型 | 模板 | 适用场景 |
|------|------|----------|
| `log` | fleeting | 快速记录、临时想法 |
| `thought` | fleeting | 灵感、思考片段 |
| `meeting` | meeting | 会议记录 |
| `plan` | plan | 项目规划、路线图 |
| `summary` | zettel | 总结、综述文章 |
| `review` | review | 回顾、复盘、周报 |
| `decision` | zettel | 决策记录 |

## 自动标签

系统会根据内容自动添加以下标签：

- **类型标签**: `log`, `meeting`, `plan`, `summary`, `review`, `thought`, `decision`
- **主题标签**:
  - `ai` - AI、LLM、Claude、GPT 相关内容
  - `openclaw` - OpenClaw、skill、agent 相关内容
  - `learning` - 学习、笔记、阅读相关内容
  - `work` - 工作、项目、任务相关内容
  - `productivity` - 效率、流程、自动化相关内容
  - `coding` - 代码、编程、开发相关内容

## 自动链接

启用 `auto_link: true` 时，系统会：

1. 扫描 `Zettels/3-Permanent/` 下的笔记
2. 计算内容相似度（Jaccard 系数）
3. 相似度 ≥ 0.7 的笔记自动添加链接
4. 相似度 0.4-0.7 的笔记添加到 "Related Notes" 部分

## 返回值

```typescript
{
  success: boolean;           // 是否成功
  file_path?: string;         // 文件完整路径
  para_location?: string;     // PARA 位置（如 Projects/Alpha）
  links_created?: string[];   // 创建的链接列表
  tags_assigned?: string[];   // 分配的标签
  related_notes?: Array<{     // 相关笔记
    id: string;
    title: string;
    score: number;            // 相似度分数
  }>;
  warnings?: string[];        // 警告信息
  error?: string;             // 错误信息
}
```

## 故障排除

### Vault 未找到

```
Error: Vault not found at: ...
```

**解决**: 设置正确的环境变量
```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/vault"
```

### 目录不存在

系统会自动创建需要的目录。如果遇到权限问题，请检查 Vault 目录的写入权限。

### 模板变量未替换

检查模板字符串格式，确保使用正确的 `{{variable}}` 语法。
