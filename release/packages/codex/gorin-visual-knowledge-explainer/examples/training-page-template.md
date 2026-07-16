# Training Page Template - SOP 培训

## 输入内容

```
## 服务器日志收集 SOP

### 目标受众
- 运维人员
- SRE

### 预先要求
- 基础 Linux 命令知识
- SSH 连接能力

### 操作步骤

1. 登录服务器
   ```bash
   ssh user@server-ip
   ```

2. 查看日志目录
   ```bash
   ls /var/log/
   ```

3. 常用日志命令
   - `tail -f` 实时查看
   - `grep` 搜索关键词
   - `awk` 提取字段

4. 日志轮转
   - 使用 `logrotate`
   - 配置文件 `/etc/logrotate.conf`

### 常见问题

**Q: 权限不足怎么办？**
A: 使用 sudo 或联系管理员

**Q: 日志文件太大怎么办？**
A: 使用 `tail -n 100` 只看最后 100 行

**Q: 如何实时监控？**
A: `tail -f /var/log/syslog`

### 故障排查

如果无法读取日志：
1. 检查权限：`ls -la /var/log/`
2. 检查文件存在：`stat /var/log/syslog`
3. 联系管理员
```

## 预期输出

**结构**:
```
Hero Section
  ├─ 标题: "服务器日志收集 SOP"
  ├─ 副标题: "操作手册"
  ├─ Target: 运维人员/SRE
  ├─ Level: 中级
  └─ Time: ~20 min

Prerequisites
  ├─ 基础 Linux 命令知识
  └─ SSH 连接能力

Workflow
  ├─ Step 1: 登录服务器
  ├─ Step 2: 查看日志目录
  ├─ Step 3: 常用日志命令
  └─ Step 4: 日志轮转

FAQ
  ├─ Q1: 权限不足？
  ├─ Q2: 日志文件太大？
  └─ Q3: 如何实时监控？

Troubleshooting
  ├─ Issue 1: 无法读取日志
  └─ Solution: 检查权限、文件存在、联系管理员

Mermaid Flowchart
  └─ 流程图展示日志收集步骤
```

---

## Template: training-page.html

```html
<article class="training-page simple-theme">
  <!-- Hero Section -->
  <header class="hero-section">
    <h1>服务器日志收集 SOP</h1>
    <p class="subtitle">操作手册</p>
    
    <div class="metadata">
      <span>Target: 运维人员/SRE</span>
      <span>Level: 中级</span>
      <span>Time: ~20 min</span>
    </div>
  </header>

  <!-- Prerequisites -->
  <section class="prerequisites">
    <h2>Prerequisites</h2>
    <ul>
      <li>基础 Linux 命令知识</li>
      <li>SSH 连接能力</li>
    </ul>
  </section>

  <!-- Workflow -->
  <section class="workflow">
    <h2>Workflow</h2>
    
    <div class="mermaid">
graph TD
    A[登录服务器] --> B[查看日志目录]
    B --> C[使用常用命令]
    C --> D[配置日志轮转]
    D --> E[故障排查]
    E --> F[完成]
    style A fill:#fff,stroke:#333
    style B fill:#fff,stroke:#333
    style C fill:#fff,stroke:#333
    style D fill:#fff,stroke:#333
    style E fill:#fff,stroke:#333
    style F fill:#8f8,stroke:#333
    classDef step fill:#fff,stroke:#333
    class A,B,C,D,E,F step
    linkStyle 0 stroke:#333
    linkStyle 1 stroke:#333
    linkStyle 2 stroke:#333
    linkStyle 3 stroke:#333
    linkStyle 4 stroke:#333
    linkStyle 5 stroke:#333
    </div>
    
    <div class="steps">
      <div class="step">
        <h3>步骤 1: 登录服务器</h3>
        <pre><code>ssh user@server-ip</code></pre>
      </div>
      
      <div class="step">
        <h3>步骤 2: 查看日志目录</h3>
        <pre><code>ls /var/log/</code></pre>
      </div>
      
      <div class="step">
        <h3>步骤 3: 常用日志命令</h3>
        <ul>
          <li><code>tail -f</code> 实时查看</li>
          <li><code>grep</code> 搜索关键词</li>
          <li><code>awk</code> 提取字段</li>
        </ul>
      </div>
      
      <div class="step">
        <h3>步骤 4: 日志轮转</h3>
        <p>使用 logrotate 配置...</p>
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section class="faq">
    <h2>FAQ</h2>
    
    <div class="qa-pairs">
      <div class="qa-pair">
        <h4>Q: 权限不足怎么办？</h4>
        <p>A: 使用 <code>sudo</code> 或联系管理员</p>
      </div>
      
      <div class="qa-pair">
        <h4>Q: 日志文件太大怎么办？</h4>
        <p>A: 使用 <code>tail -n 100</code> 只看最后 100 行</p>
      </div>
      
      <div class="qa-pair">
        <h4>Q: 如何实时监控？</h4>
        <p>A: <code>tail -f /var/log/syslog</code></p>
      </div>
    </div>
  </section>

  <!-- Troubleshooting -->
  <section class="troubleshooting">
    <h2>Troubleshooting</h2>
    
    <div class="issues">
      <div class="issue">
        <h4>问题: 无法读取日志</h4>
        <ol>
          <li>检查权限: <code>ls -la /var/log/</code></li>
          <li>检查文件存在: <code>stat /var/log/syslog</code></li>
          <li>联系管理员</li>
        </ol>
      </div>
    </div>
  </section>
</article>
```
