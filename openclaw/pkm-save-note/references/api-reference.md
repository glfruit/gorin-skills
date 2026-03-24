# PKM Save Note - API 参考

## 接口定义

### 输入参数 (SaveNoteInput)

```typescript
interface SaveNoteInput {
  /**
   * 笔记内容（支持 Markdown）
   * @required
   */
  content: string;
  
  /**
   * 笔记标题
   * 如果未提供，自动从内容第一行或关键词生成
   * @optional
   * @default auto-generated
   */
  title?: string;
  
  /**
   * 笔记类型
   * @optional
   * @default "log"
   */
  type?: "log" | "thought" | "meeting" | "plan" | "summary" | "review" | "decision";
  
  /**
   * 关联项目
   * 指定后笔记保存到 Efforts/1-Projects/{project}/
   * @optional
   */
  project?: string;
  
  /**
   * 关联领域
   * 指定后笔记保存到 Efforts/2-Areas/{area}/
   * @optional
   */
  area?: string;
  
  /**
   * 额外标签
   * 自动标签会与此合并
   * @optional
   * @default []
   */
  tags?: string[];
  
  /**
   * 手动指定链接
   * 格式: "[[Note ID]]" 或 "Note ID"
   * @optional
   * @default []
   */
  links?: string[];
  
  /**
   * 使用的模板
   * @optional
   * @default 根据 type 自动选择
   */
  template?: "fleeting" | "zettel" | "meeting" | "plan" | "review" | "standard";
  
  /**
   * 是否自动查找相关笔记
   * @optional
   * @default true
   */
  auto_link?: boolean;
  
  /**
   * 是否启用 PARA 自动分类
   * @optional
   * @default true
   */
  para_classify?: boolean;
  
  /**
   * 预览模式（不实际写入）
   * @optional
   * @default false
   */
  dry_run?: boolean;
}
```

### 输出结果 (SaveNoteOutput)

```typescript
interface SaveNoteOutput {
  /**
   * 操作是否成功
   */
  success: boolean;
  
  /**
   * 生成的文件完整路径
   */
  file_path?: string;
  
  /**
   * PARA 分类位置
   * 例如: "Projects/Alpha", "Areas/Learning", "Zettels/3-Permanent"
   */
  para_location?: string;
  
  /**
   * 自动创建的链接列表
   */
  links_created?: string[];
  
  /**
   * 分配的标签列表
   */
  tags_assigned?: string[];
  
  /**
   * 发现的相关笔记
   */
  related_notes?: Array<{
    id: string;      // 笔记 ID
    title: string;   // 笔记标题
    score: number;   // 相似度分数 (0-1)
  }>;
  
  /**
   * 警告信息
   */
  warnings?: string[];
  
  /**
   * 错误信息（success=false 时）
   */
  error?: string;
}
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OBSIDIAN_VAULT_PATH` | Obsidian Vault 完整路径 | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault` |
| `PKM_SIMILARITY_THRESHOLD` | 相关笔记检测阈值 | `0.5` |
| `PKM_AUTO_LINK_THRESHOLD` | 自动链接创建阈值 | `0.7` |
| `PKM_DRY_RUN` | 全局预览模式 | `false` |
| `PKM_AUTO_CLASSIFY` | 全局自动分类 | `true` |

## 模板变量

所有模板支持以下变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `{{id}}` | 笔记唯一 ID (YYYYMMDDHHMM) | `202502221430` |
| `{{title}}` | 笔记标题 | "项目总结" |
| `{{content}}` | 笔记内容 | "..." |
| `{{type}}` | 笔记类型 | "summary" |
| `{{created}}` | 创建日期 (YYYY-MM-DD) | "2025-02-22" |
| `{{modified}}` | 修改日期 (YYYY-MM-DD) | "2025-02-22" |
| `{{project}}` | 关联项目名 | "Alpha" |
| `{{area}}` | 关联领域名 | "Learning" |
| `{{tags}}` | 标签数组（迭代用） | `["summary", "ai"]` |
| `{{links}}` | 链接数组（迭代用） | `["[[202502221200]]"]` |
| `{{relatedNotes}}` | 相关笔记数组 | `[{id, title, score}]` |

## 文件命名规则

生成的文件名格式：

```
{ID}-{SafeTitle}.md
```

其中：
- `ID`: YYYYMMDDHHMM 格式的时间戳
- `SafeTitle`: 标题的 URL-friendly 版本（空格替换为连字符，移除特殊字符，限制50字符）

示例：
```
202502221430-项目总结.md
202502221435-Alpha-项目规划.md
```

## 目录结构

技能期望的 Vault 结构：

```
{Vault}/
├── Efforts/
│   ├── 1-Projects/          # 项目目录
│   │   ├── ProjectA/
│   │   └── ProjectB/
│   └── 2-Areas/             # 领域目录
│       ├── Learning/
│       └── Work/
├── Zettels/
│   ├── 1-Fleeting/          # 临时笔记
│   ├── 3-Permanent/         # 永久笔记
│   └── 4-Structure/         # 结构笔记
└── ...
```

## 相似度计算

相关笔记检测使用 Jaccard 相似度：

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

其中：
- A = 新笔记的词集合
- B = 已有笔记的词集合

## 扩展接口

### 自定义模板

可以通过修改 `scripts/save-note.ts` 中的 `templates` 对象添加新模板：

```typescript
const templates: Record<string, string> = {
  mytemplate: `---
title: "{{title}}"
---

# {{title}}

{{content}}
`,
  // ...
};
```

### 自定义分类规则

修改 `determineLocation` 函数添加新的分类逻辑：

```typescript
// 添加自定义规则
if (content.includes('特定关键词')) {
  return 'Custom/Location';
}
```

### 自定义标签规则

修改 `TOPIC_KEYWORDS` 添加新的自动标签：

```typescript
const TOPIC_KEYWORDS: Record<string, string[]> = {
  mytopic: ['keyword1', 'keyword2'],
  // ...
};
```
