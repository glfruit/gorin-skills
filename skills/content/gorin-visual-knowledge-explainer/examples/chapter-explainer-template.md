# 教学页面样例 - Git 教程

## 输入内容

一段教材章节草稿：

```
# 第一章: Git 入门

## 1.1 什么是 Git

Git 是一个分布式版本控制系统，由 Linus Torvalds 于 2005 年创建。

## 1.2 安装 Git

- macOS: `brew install git`
- Ubuntu: `sudo apt install git`
- Windows: 从 git-scm.com 下载

## 1.3 配置 Git

使用 `git config` 命令配置用户信息。

## 1.4 创建仓库

使用 `git init` 命令创建新仓库。

## 学习目标

- 理解 Git 的基本概念
- 正确安装 Git
- 配置用户信息
- 创建 Git 仓库

## 常见错误

- 没有配置用户信息就提交
- 在错误的目录运行 `git init`
```

## 预期输出

**结构**:
```
Hero Section
  ├─ 标题: "第一章: Git 入门"
  ├─ 副标题: "从零开始掌握 Git 基础"
  ├─ 学习目标
  └─ 元数据: 章节、难度、时间

Modules (4 个模块)
  ├─ Module 1: 什么是 Git
  │  ├─ 概念解释
  │  ├─ 示例: Git vs SVN 对比
  │  └─ 常见误解
  ├─ Module 2: 安装 Git
  │  ├─ 不同系统的安装命令
  │  ├─ 示例: macOS 安装
  │  └─ 验证安装
  ├─ Module 3: 配置 Git
  │  ├─ 配置命令
  │  ├─ 常见错误: 未配置用户信息
  │  └─ 最佳实践
  └─ Module 4: 创建仓库
     ├─ git init 命令
     ├─ 示例: 创建项目仓库
     └─ 常见错误: 在错误目录

Summary
  ├─ 关键点回顾
  └─ 自我测试问题

Reference Section
  ├─ further reading
  └─ related chapters
```

---

## Template: chapter-explainer.html

```html
<article class="explainer-page grace-theme">
  <!-- Hero Section -->
  <header class="hero-section">
    <h1>第一章: Git 入门</h1>
    <p class="subtitle">从零开始掌握 Git 基础</p>
    
    <div class="metadata">
      <span>Topic: Git</span>
      <span>Level: Beginner</span>
      <span>Time: ~30 min</span>
    </div>
  </header>

  <!-- Learning Objectives -->
  <section class="learning-objectives">
    <h2>Learning Objectives</h2>
    <ul>
      <li>理解 Git 的基本概念</li>
      <li>正确安装 Git</li>
      <li>配置用户信息</li>
      <li>创建 Git 仓库</li>
    </ul>
  </section>

  <!-- Modules -->
  <section class="modules">
    <!-- Module 1 -->
    <article class="module">
      <h3>模块 1: 什么是 Git</h3>
      <p>Git 是一个分布式版本控制系统...</p>
      <div class="example">
        <h4>示例: Git vs SVN</h4>
        <ul>
          <li>Git: 分布式</li>
          <li>SVN: 集中式</li>
        </ul>
      </div>
      <div class="common-mistakes">
        <h4>常见错误</h4>
        <ul>
          <li>误以为 Git 只用于代码</li>
        </ul>
      </div>
    </article>

    <!-- Module 2 -->
    <article class="module">
      <h3>模块 2: 安装 Git</h3>
      <p>根据操作系统选择安装方式...</p>
      <div class="example">
        <h4>示例: macOS 安装</h4>
        <pre><code>brew install git</code></pre>
      </div>
      <div class="example">
        <h4>验证安装</h4>
        <pre><code>git --version</code></pre>
      </div>
    </article>

    <!-- Module 3 -->
    <article class="module">
      <h3>模块 3: 配置 Git</h3>
      <p>使用 git config 命令...</p>
      <div class="common-mistakes">
        <h4>常见错误</h4>
        <ul>
          <li>没有配置用户信息就提交</li>
        </ul>
      </div>
    </article>

    <!-- Module 4 -->
    <article class="module">
      <h3>模块 4: 创建仓库</h3>
      <p>使用 git init 创建新仓库...</p>
      <div class="example">
        <h4>示例: 创建项目仓库</h4>
        <pre><code>mkdir my-project && cd my-project && git init</code></pre>
      </div>
    </article>
  </section>

  <!-- Summary -->
  <section class="summary">
    <h2>小结</h2>
    <ul>
      <li>Git 是分布式版本控制系统</li>
      <li>安装 Git 根据操作系统选择</li>
      <li>配置用户信息是必须的</li>
      <li>git init 创建新仓库</li>
    </ul>
  </section>

  <!-- Reference -->
  <section class="reference">
    <h2>参考</h2>
    <ul>
      <li>Git 官方文档</li>
      <li>下 chapters</li>
    </ul>
  </section>
</article>
```
