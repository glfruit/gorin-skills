---
name: {{SKILL_NAME}}
description: {{SKILL_DESCRIPTION}}
homepage: {{HOMEPAGE}}
version: {{VERSION}}
metadata:
  {
    "{{TOOL_TYPE}}":
      {
        "emoji": "{{SKILL_EMOJI}}",
        "os": ["{{OS}}"],
        "requires": { {{REQUIREMENTS}} },
        "install":
          [
            {
              "id": "{{INSTALL_ID}}",
              "kind": "{{INSTALL_KIND}}",
              "url": "{{INSTALL_URL}}",
              "extract": {{EXTRACT}},
              "targetDir": "{{TARGET_DIR}}",
              "bins": [{{BINARIES}}],
              "label": "{{INSTALL_LABEL}}",
            },
          ],
      },
  }
---

# {{SKILL_EMOJI}} {{SKILL_NAME}}

{{SKILL_LONG_DESCRIPTION}}

## 功能特性

- ✅ {{FEATURE_1}}
- ✅ {{FEATURE_2}}
- ✅ {{FEATURE_3}}

## 系统要求

- {{REQUIREMENT_1}}
- {{REQUIREMENT_2}}
- {{REQUIREMENT_3}}

## 安装

### 自动安装

{{AUTO_INSTALL_INSTRUCTIONS}}

### 手动安装

```bash
{{MANUAL_INSTALL_COMMANDS}}
```

## 在 {{TOOL_TYPE}} 中使用

### 使用方式 1

```
{{USAGE_EXAMPLE_1}}
```

### 使用方式 2

```
{{USAGE_EXAMPLE_2}}
```

## 命令行接口

### 命令 1

```bash
{{CLI_EXAMPLE_1}}
```

### 命令 2

```bash
{{CLI_EXAMPLE_2}}
```

## 配置

### 必需配置

{{REQUIRED_CONFIG}}

### 可选配置

{{OPTIONAL_CONFIG}}

## 故障排除

### 常见问题

**问题:** {{TROUBLESHOOTING_PROBLEM}}

**解决方案:** {{TROUBLESHOOTING_SOLUTION}}

## 链接

- **主页**: {{HOMEPAGE}}
- **文档**: {{DOCS_URL}}
- **API 参考**: {{API_URL}}

## 许可证

{{LICENSE_TYPE}}

---

**版本:** {{VERSION}}
**状态:** {{STATUS}}
