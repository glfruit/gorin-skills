# Module 1: 配置 Git 用户信息

## 为什么需要配置？

Git 需要知道"谁"做的修改。每次提交都需要作者信息。

---

## 配置命令

```bash
# 设置全局用户名
git config --global user.name "你的名字"

# 设置全局邮箱
git config --global user.email "你的邮箱@example.com"

# 查看配置
git config --list
```

---

## 常见错误

### 错误 1: 提交时没有配置

**错误信息**:
```
*** Please tell me who you are.
```

**解决**: 运行上面的配置命令

---

## 最佳实践

1. 使用真实姓名（便于团队协作）
2. 使用稳定邮箱（便于问题追踪）
3. 配置一次，全局生效（`--global`）

---

## 验证

```bash
# 检查配置是否成功
git config user.name
git config user.email
```
