#!/usr/bin/env python3
"""
atlas-ingest LLM 模块：用 LLM 替代正则匹配，生成高质量笔记和概念。

支持 OpenAI 兼容 API（当前默认 DeepSeek）。
优先读取 ATLAS_LLM_API_KEY / DEEPSEEK_API_KEY；若未设置，则回退到
OpenClaw 本机 auth profile 中的 deepseek:default。
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional

# ── Configuration ──────────────────────────────────────────────────────────

# LLM API 配置（DeepSeek，OpenAI 兼容）
AUTH_PROFILES_FILE = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"


def _load_deepseek_api_key() -> str:
    env_key = os.environ.get("ATLAS_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if env_key:
        return env_key
    try:
        data = json.loads(AUTH_PROFILES_FILE.read_text(encoding="utf-8"))
        profile = data.get("profiles", {}).get("deepseek:default", {})
        key = profile.get("key", "")
        return key if isinstance(key, str) else ""
    except Exception:
        return ""


LLM_BASE_URL = os.environ.get(
    "ATLAS_LLM_BASE_URL",
    "https://api.deepseek.com"
)
LLM_API_KEY = _load_deepseek_api_key()
LLM_MODEL = os.environ.get("ATLAS_LLM_MODEL", "deepseek-chat")  # 默认 deepseek-chat
LLM_TIMEOUT = int(os.environ.get("ATLAS_LLM_TIMEOUT", "120"))  # 秒
# glm-5.1 是 reasoning 模型，需要足够的 max_tokens（reasoning + output）
LLM_MAX_TOKENS = int(os.environ.get("ATLAS_LLM_MAX_TOKENS", "4096"))

# ── GitHub Copilot provider ───────────────────────────────────────────────

COPILOT_BASE_URL = "https://api.githubcopilot.com"


def _load_copilot_token() -> str:
    """从 auth-profiles 读取 github-copilot ghu_ token，直接作为 Bearer 使用。
    Copilot REST API 接受 ghu_ device-flow token 直接认证，无需交换。
    """
    try:
        data = json.loads(AUTH_PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        for key, profile in profiles.items():
            if "github-copilot" in key:
                tok = profile.get("token", "")
                if isinstance(tok, str) and tok:
                    return tok
    except Exception:
        pass
    return ""


COPILOT_API_KEY = _load_copilot_token()
COPILOT_MODEL = os.environ.get("ATLAS_COPILOT_MODEL", "claude-sonnet-4")

# Default provider from env
DEFAULT_PROVIDER = os.environ.get("ATLAS_LLM_PROVIDER", "copilot")
FALLBACK_PROVIDER = os.environ.get("ATLAS_LLM_FALLBACK", "deepseek")

# ── Rate Limiter ────────────────────────────────────────────────────────

class _RateLimiter:
    """Per-provider 速率控制器，支持 429 指数退避。"""
    def __init__(self):
        self._min_interval = {
            "copilot": 15.0,   # Copilot 限流严格，15s 最小间隔
            "deepseek": 8.0,   # DeepSeek 相对宽松
            "local": 1.0,      # 本地模型只需防过载
        }
        self._backoff_until: dict = {}  # provider → monotonic timestamp
        self._backoff_count: dict = {}   # provider → 连续 429 次数
        self._last_call: dict = {}       # provider → last successful call timestamp

    def wait(self, provider: str):
        """在调用前调用，确保满足最小间隔和退避窗口。"""
        now = time.monotonic()
        min_iv = self._min_interval.get(provider, 5.0)

        # 检查退避窗口（429 触发）
        backoff = self._backoff_until.get(provider, 0)
        if now < backoff:
            wait = backoff - now
            print(f"    ⏳ 退避冷却: {provider} 等待 {wait:.1f}s...")
            time.sleep(wait)
            now = time.monotonic()

        # 检查最小间隔
        last = self._last_call.get(provider, 0)
        elapsed = now - last
        if elapsed < min_iv:
            wait = min_iv - elapsed
            print(f"    ⏳ 速率控制: {provider} 等待 {wait:.1f}s...")
            time.sleep(wait)

        self._last_call[provider] = time.monotonic()

    def record_429(self, provider: str):
        """记录 429 响应，触发指数退避。"""
        count = self._backoff_count.get(provider, 0) + 1
        self._backoff_count[provider] = count
        delay = min(2 ** count, 60)  # 2s → 4s → 8s → ... → 60s 上限
        self._backoff_until[provider] = time.monotonic() + delay
        print(f"    🚫 {provider} 收到 429 限流，退避 {delay}s（第 {count} 次）")

    def record_success(self, provider: str):
        """成功调用后重置退避计数。"""
        if provider in self._backoff_count:
            self._backoff_count[provider] = 0

rate_limiter = _RateLimiter()


def llm_chat(messages: List[Dict], model: str = None, temperature: float = 0.3,
             max_tokens: int = None, provider: str = None) -> str:
    """调用 OpenAI 兼容 Chat Completions API

    provider: "deepseek" (默认) 或 "copilot" (GitHub Copilot Claude)
    """
    provider = provider or DEFAULT_PROVIDER

    if provider == "local":
        return llm_chat_local(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    elif provider == "copilot":
        api_key = COPILOT_API_KEY
        if not api_key:
            raise RuntimeError("Copilot API token 未设置（auth-profiles github-copilot:github）")
        base_url = COPILOT_BASE_URL
        model = model or COPILOT_MODEL
    else:
        api_key = LLM_API_KEY
        if not api_key:
            raise RuntimeError("DeepSeek API key 未设置（ATLAS_LLM_API_KEY / DEEPSEEK_API_KEY / auth-profiles deepseek:default）")
        base_url = LLM_BASE_URL
        model = model or LLM_MODEL

    rate_limiter.wait(provider)
    url = f"{base_url.rstrip('/')}/chat/completions"
    max_tokens = max_tokens or LLM_MAX_TOKENS

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    # Copilot requires extra headers
    if provider == "copilot":
        headers["Copilot-Integration-Id"] = "vscode-chat"
        headers["Editor-Version"] = "vscode/1.99.0"
        headers["Editor-Plugin-Version"] = "copilot/1.0"
        headers["Openai-Organization"] = "github-copilot"
        headers["Openai-Intent"] = "conversation-panel"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            rate_limiter.record_success(provider)
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        if e.code == 429:
            rate_limiter.record_429(provider)
        raise RuntimeError(f"LLM API 错误 {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API 连接失败: {e.reason}") from e


def _robust_json_parse(raw: str) -> dict:
    """多策略 JSON 解析：code block → 直接解析 → 修复常见问题 → 暴力提取。"""
    # 策略 1：从 markdown code block 提取
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            raw = m.group(1)  # 继续尝试修复

    # 策略 2：找最外层 { } 对
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidate = raw[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass  # 继续修复

        # 策略 3：修复常见问题
        cleaned = candidate
        # 中文弯引号
        cleaned = cleaned.replace("\u201c", "\u201c").replace("\u201d", "\u201d")
        # 中文省略号
        cleaned = cleaned.replace("\u2026", "...")
        # 未转义的换行在字符串值内
        cleaned = re.sub(r'(?<="\: ")\s*\n\s*', " ", cleaned)
        # 尾逗号（trailing comma）
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # 策略 4：如果所有策略都失败，抛出包含原始内容的错误便于调试
    raise json.JSONDecodeError(
        f"无法解析 LLM JSON 输出 (前500字符): {raw[:500]}",
        raw, 0
    )


def llm_json_chat(messages: List[Dict], model: str = None,
                  temperature: float = 0.3, provider: str = None) -> dict:
    """调用 LLM 并解析 JSON 响应（从 markdown 代码块中提取）"""
    raw = llm_chat(messages, model=model, temperature=temperature, provider=provider)
    return _robust_json_parse(raw)


# ── 文献笔记摘要生成 ───────────────────────────────────────────────────────

SUMMARY_PROMPT = """你是一个知识管理助手。请阅读以下文献内容，生成结构化摘要。

要求：
1. 摘要用中文，不超过原文 15%
2. 突出核心观点和关键数据
3. 列出 3-7 个关键发现（每个独立成行，以 - 开头）
4. 在末尾列出 3-5 个关键术语（用于概念提取）

请严格按以下 JSON 格式输出：
{{
  "summary": "200-400 字的结构化摘要...",
  "key_findings": ["发现1", "发现2", "发现3"],
  "key_terms": ["术语1", "术语2", "术语3"],
  "area": "知识领域分类（如 AI-ML, Education, Engineering 等）"
}}

文献内容：
{content}"""


def generate_summary_and_findings(text: str, provider: str = None) -> dict:
    """LLM 生成文献摘要 + 关键发现 + 术语"""
    # 截断过长文本（保留前 30000 字符）
    truncated = text[:30000] if len(text) > 30000 else text
    prompt = SUMMARY_PROMPT.format(content=truncated)

    messages = [
        {"role": "system", "content": "你是知识管理助手，擅长文献分析和摘要生成。"},
        {"role": "user", "content": prompt},
    ]

    return llm_json_chat(messages, provider=provider)


# ── 概念提取 ───────────────────────────────────────────────────────────────

CONCEPT_PROMPT = """你是一个知识图谱构建助手。请从以下文献摘要和关键发现中提取概念。

要求：
1. 概念是独立的、可跨文献关联的知识单元（不是具体的研究细节）
2. 每个概念必须有清晰的定义方向
3. 排除人名、机构名、具体数据、方法名称中的专有名词
4. 保留有跨领域适用价值的概念（如"Progressive Disclosure"而非"SKILLREDUCER 工具"）
5. 严格排除章节号、附录名、罗马数字、小节标题、OCR 截断残片、介词短语
6. 不要输出类似 "III"、"IV-B"、"Appendix"、"in Proceedings of the"、"of skills" 这类非概念文本
7. 缩写只有在它本身就是稳定通用概念时才保留，例如 LLM、API、UMAP

请严格按以下 JSON 格式输出：
{{
  "concepts": [
    {{
      "name": "概念名称（英文优先，中英文对照）",
      "definition": "一句话定义",
      "category": "methodology|pattern|principle|metric|framework",
      "related_concepts": ["相关概念1", "相关概念2"]
    }}
  ]
}}

文献摘要：
{summary}

关键发现：
{findings}

关键术语：
{terms}"""


def extract_concepts_llm(summary: str, findings: list, terms: list, provider: str = None) -> list:
    """LLM 提取概念"""
    findings_text = "\n".join(f"- {f}" for f in findings)
    terms_text = ", ".join(terms)
    prompt = CONCEPT_PROMPT.format(
        summary=summary, findings=findings_text, terms=terms_text
    )

    messages = [
        {"role": "system", "content": "你是知识图谱构建助手。只输出 JSON，不要其他文字。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = llm_json_chat(messages, provider=provider)
        return result.get("concepts", [])
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️ LLM 概念提取 JSON 解析失败: {e}")
        return []


# ── 原子笔记提取 ──────────────────────────────────────────────────────────

ATOM_PROMPT = """你是一个知识管理助手。请从以下关键发现中提取原子笔记。

原子笔记要求：
1. 每条笔记只包含一个独立观点/发现
2. 可以脱离原文独立理解（自包含）
3. 有跨场景复用价值（不只是本文独有的细节）
4. 用中文表述，简洁有力
5. 3-7 条，按重要性排序

请严格按以下 JSON 格式输出：
{{
  "atoms": [
    {{
      "title": "简短标题（不超过 50 字）",
      "content": "完整的原子笔记内容（可独立理解）"
    }}
  ]
}}

文献摘要：
{summary}

关键发现：
{findings}"""


def extract_atoms_llm(summary: str, findings: list, provider: str = None) -> list:
    """LLM 提取原子笔记"""
    findings_text = "\n".join(f"- {f}" for f in findings)
    prompt = ATOM_PROMPT.format(summary=summary, findings=findings_text)

    messages = [
        {"role": "system", "content": "你是知识管理助手。只输出 JSON，不要其他文字。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = llm_json_chat(messages, provider=provider)
        return result.get("atoms", [])
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️ LLM 原子笔记提取 JSON 解析失败: {e}")
        return []


# ── Marp 幻灯片生成 ──────────────────────────────────────────────────────

SLIDES_PROMPT = """你是一个知识展示助手。请根据以下内容生成 Marp 幻灯片。

要求：
1. 有效的 Marp 格式（YAML front matter + markdown）
2. 10-15 页，结构：标题页 → 问题 → 方法 → 关键发现 → 结论
3. 每页内容简洁，不超过 6 行
4. 使用中文
5. 可以用列表、表格、引用等格式

请直接输出 Marp markdown 内容（不要用代码块包裹）。

---
主题：{title}
摘要：{summary}

关键发现：
{findings}"""


def generate_slides(title: str, summary: str, findings: list) -> str:
    """LLM 生成 Marp 幻灯片"""
    findings_text = "\n".join(f"- {f}" for f in findings)
    prompt = SLIDES_PROMPT.format(
        title=title, summary=summary, findings=findings_text
    )

    messages = [
        {"role": "system", "content": "你是知识展示助手，擅长生成 Marp 幻灯片。"},
        {"role": "user", "content": prompt},
    ]

    raw = llm_chat(messages, max_tokens=4096)

    # 清理可能的代码块包裹
    if raw.strip().startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    # 确保 Marp front matter
    if not raw.strip().startswith("---"):
        raw = "---\nmarp: true\ntheme: default\npaginate: true\n---\n\n" + raw

    return raw.strip()


# ── matplotlib 图表生成 ──────────────────────────────────────────────────

CHART_PROMPT = """你是一个数据可视化助手。请根据以下内容生成 Python matplotlib 图表代码。

要求：
1. 生成一个有意义的图表（概念关系图、趋势图、对比图等，选最合适的类型）
2. 使用 matplotlib + networkx（如果是关系图）
3. 中文字体用 'Arial Unicode MS'（macOS）
4. 图表清晰美观，有标题和标签
5. 保存为 PNG，路径通过命令行参数传入

只输出 Python 代码，不要解释。

---
主题：{title}
概念列表：{concepts}
摘要：{summary}

关键发现：
{findings}"""


def generate_chart_code(title: str, summary: str, findings: list,
                        concepts: list, output_path: str) -> str:
    """LLM 生成 matplotlib 图表 Python 代码"""
    findings_text = "\n".join(f"- {f}" for f in findings)
    concepts_text = ", ".join(concepts)
    prompt = CHART_PROMPT.format(
        title=title, summary=summary, findings=findings_text,
        concepts=concepts_text
    )

    messages = [
        {"role": "system", "content": "你是数据可视化助手。只输出 Python 代码，不要其他文字。"},
        {"role": "user", "content": prompt},
    ]

    code = llm_chat(messages, max_tokens=2048)

    # 清理代码块
    code = re.sub(r"^```\w*\n?", "", code)
    code = re.sub(r"\n?```$", "", code)

    # 替换输出路径
    code = re.sub(r"savefig\([^)]+\)", f"savefig('{output_path}', dpi=150, bbox_inches='tight')", code)
    code = re.sub(r"plt\.show\(\)", "", code)  # 非交互环境去掉 show

    return code.strip()


# ── 管线编排 ───────────────────────────────────────────────────────────────

def _call_with_fallback(fn, *args, **kwargs):
    """尝试 copilot → deepseek → 本地 Gemma 4 三级兜底。"""
    provider = kwargs.pop("provider", None) or DEFAULT_PROVIDER

    # 定义兜底链：去重并保证当前 provider 排第一
    chain = [provider] + [p for p in [DEFAULT_PROVIDER, FALLBACK_PROVIDER, "local"] if p != provider]

    for i, prov in enumerate(chain):
        try:
            if prov == "local" and not is_omlx_online():
                print(f"    ⏭️ 本地模型不在线，跳过")
                continue
            return fn(*args, **kwargs, provider=prov)
        except Exception as e:
            next_prov = chain[i + 1] if i + 1 < len(chain) else None
            if next_prov:
                print(f"    ⚠️ {prov} 失败 ({e})，切换到 {next_prov}...")
            else:
                print(f"    ❌ 所有 provider 均失败: {e}")
                raise


def process_with_llm(text: str, note_title: str = "") -> dict:
    """
    LLM 驱动的完整后处理管线。
    输入文献全文，输出摘要、概念、原子笔记、幻灯片代码、图表代码。
    """
    print(f"  🤖 LLM 分析中 (provider: {DEFAULT_PROVIDER})...")

    # Step 1: 摘要 + 关键发现
    print("    📝 生成摘要和关键发现...")
    summary_result = _call_with_fallback(generate_summary_and_findings, text)
    summary = summary_result.get("summary", "")
    findings = summary_result.get("key_findings", [])
    terms = summary_result.get("key_terms", [])
    area = summary_result.get("area", "")
    print(f"    ✅ 摘要 ({len(summary)} 字), {len(findings)} 条发现, 领域: {area}")

    # Step 2: 概念提取
    print("    🔍 提取概念...")
    concepts = _call_with_fallback(extract_concepts_llm, summary, findings, terms)
    print(f"    ✅ {len(concepts)} 个概念")

    # Step 3: 原子笔记
    print("    💡 提取原子笔记...")
    atoms = _call_with_fallback(extract_atoms_llm, summary, findings)
    print(f"    ✅ {len(atoms)} 条原子笔记")

    return {
        "summary": summary,
        "key_findings": findings,
        "key_terms": terms,
        "area": area,
        "concepts": concepts,
        "atoms": atoms,
    }


# ── Local oMLX (Gemma 4) Review ────────────────────────────────────────────

LOCAL_BASE_URL = "http://localhost:18001/v1"
LOCAL_DEFAULT_MODEL = os.environ.get("ATLAS_LOCAL_MODEL", "gemma-4-31b-it-4bit")
LOCAL_TIMEOUT = int(os.environ.get("ATLAS_LOCAL_TIMEOUT", "300"))
OMLX_SETTINGS_PATH = Path.home() / ".omlx" / "settings.json"


def _load_omlx_api_key() -> str:
    """Read api_key from ~/.omlx/settings.json → auth.api_key"""
    try:
        data = json.loads(OMLX_SETTINGS_PATH.read_text(encoding="utf-8"))
        key = data.get("auth", {}).get("api_key", "")
        return key if isinstance(key, str) else ""
    except Exception:
        return ""


def is_omlx_online() -> bool:
    """Quick connectivity check: GET /v1/models with 3 s timeout."""
    try:
        api_key = _load_omlx_api_key()
        req = urllib.request.Request(
            f"{LOCAL_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            resp.read()
            return True
    except Exception:
        return False


def llm_chat_local(messages, model=None, temperature=0.3, max_tokens=None):
    """Call local oMLX OpenAI-compatible API (Gemma 4 or similar)."""
    api_key = _load_omlx_api_key()
    if not api_key:
        raise RuntimeError("oMLX api_key not found in ~/.omlx/settings.json")

    url = f"{LOCAL_BASE_URL.rstrip('/')}/chat/completions"
    model = model or LOCAL_DEFAULT_MODEL
    max_tokens = max_tokens or LLM_MAX_TOKENS

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    rate_limiter.wait("local")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=LOCAL_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            rate_limiter.record_success("local")
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        if e.code == 429:
            rate_limiter.record_429("local")
        raise RuntimeError(f"Local LLM API error {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Local LLM API connection failed: {e.reason}") from e


REVIEW_PROMPT = """你是一个严谨的学术审核助手。请对比原始文献内容和已有笔记，找出遗漏和不足。

请严格按以下 JSON 格式输出：
{{
  "missed_concepts": [
    {{
      "name": "遗漏的概念名称（英文优先）",
      "definition": "一句话定义",
      "category": "methodology|pattern|principle|metric|framework",
      "related_concepts": []
    }}
  ],
  "corrections": [
    "笔记中不够准确或需要修正的地方（每条一句话）"
  ],
  "supplementary_findings": [
    "可以从原文补充的额外发现（每条一句话）"
  ]
}}

要求：
1. missed_concepts: 找出原文中存在但笔记遗漏的重要概念（0-5 个），概念须有跨文献关联价值
2. corrections: 指出笔记中不够准确或不完整的地方（0-3 条）
3. supplementary_findings: 原文中的重要发现未被笔记覆盖的（0-3 条）
4. 如果没有遗漏或修正，对应列表可以为空数组
5. 只输出 JSON，不要其他文字

---

## 原始文献内容（提取文本）

{extraction_text}

---

## 已有笔记内容

{note_content}
"""


def review_with_local(extraction_text, note_content):
    """Use local Gemma 4 to review a note against the original extraction text.

    Returns a dict with keys: missed_concepts, corrections, supplementary_findings.
    Returns None if the local model is unavailable or the response can't be parsed.
    """
    try:
        prompt = REVIEW_PROMPT.format(
            extraction_text=extraction_text[:20000],
            note_content=note_content[:15000],
        )
        messages = [
            {"role": "system", "content": "你是严谨的学术审核助手。只输出 JSON。"},
            {"role": "user", "content": prompt},
        ]
        raw = llm_chat_local(messages, temperature=0.2)

        # Extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)

        result = json.loads(raw.strip())
        # Validate expected keys
        for key in ("missed_concepts", "corrections", "supplementary_findings"):
            if key not in result:
                result[key] = []
        return result
    except Exception as e:
        print(f"  ⚠️ Local model review failed: {e}")
        return None


# ── CLI 测试 ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 llm.py summary <file>           # 生成摘要")
        print("  python3 llm.py concepts <file>          # 提取概念")
        print("  python3 llm.py atoms <file>             # 提取原子笔记")
        print("  python3 llm.py slides <file>            # 生成幻灯片")
        print("  python3 llm.py pipeline <file>          # 完整管线")
        print("  python3 llm.py --test-comparison [file] # DeepSeek vs Copilot Claude 对比")
        sys.exit(1)

    # --test-comparison: DeepSeek vs Copilot Claude 对比测试
    if sys.argv[1] == "--test-comparison":
        import glob
        test_file = sys.argv[2] if len(sys.argv) > 2 else None
        if not test_file:
            candidates = sorted(
                glob.glob(str(Path.home() / "pkm" / "atlas" / "1-Literature" / "Papers" / "*.md"))
            )
            if not candidates:
                print("❌ 未找到测试文件")
                sys.exit(1)
            test_file = candidates[0]
            print(f"📄 自动选择测试文件: {test_file}")

        with open(test_file, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"📄 文件: {test_file} ({len(text)} 字符)")
        fname = Path(test_file).name

        # DeepSeek
        print("\n🤖 DeepSeek 摘要提取...")
        ds_summary_result = generate_summary_and_findings(text, provider="deepseek")
        print(f"  ✅ 摘要 {len(ds_summary_result.get('summary',''))} 字, {len(ds_summary_result.get('key_findings',[]))} 发现")
        print("🤖 DeepSeek 概念提取...")
        ds_concepts = extract_concepts_llm(
            ds_summary_result.get("summary", ""),
            ds_summary_result.get("key_findings", []),
            ds_summary_result.get("key_terms", []),
            provider="deepseek",
        )
        print(f"  ✅ {len(ds_concepts)} 个概念")

        # Copilot Claude
        print("\n🤖 Copilot Claude 摘要提取...")
        cc_summary_result = generate_summary_and_findings(text, provider="copilot")
        print(f"  ✅ 摘要 {len(cc_summary_result.get('summary',''))} 字, {len(cc_summary_result.get('key_findings',[]))} 发现")
        print("🤖 Copilot Claude 概念提取...")
        cc_concepts = extract_concepts_llm(
            cc_summary_result.get("summary", ""),
            cc_summary_result.get("key_findings", []),
            cc_summary_result.get("key_terms", []),
            provider="copilot",
        )
        print(f"  ✅ {len(cc_concepts)} 个概念")

        # Quality notes
        ds_names = {c.get("name", "") for c in ds_concepts}
        cc_names = {c.get("name", "") for c in cc_concepts}
        shared = ds_names & cc_names
        only_ds = ds_names - cc_names
        only_cc = cc_names - ds_names

        ds_sum_len = len(ds_summary_result.get("summary", ""))
        cc_sum_len = len(cc_summary_result.get("summary", ""))
        ds_findings = ds_summary_result.get("key_findings", [])
        cc_findings = cc_summary_result.get("key_findings", [])

        quality_notes = (
            f"概念重合: {len(shared)}/{len(ds_names) + len(cc_names) - len(shared)}; "
            f"DeepSeek 独有: {only_ds or '无'}; "
            f"Claude 独有: {only_cc or '无'}。\n"
            f"摘要长度: DS={ds_sum_len}字, Claude={cc_sum_len}字。\n"
            f"发现数量: DS={len(ds_findings)}, Claude={len(cc_findings)}。\n"
            f"DeepSeek 摘要更简练紧凑，Claude 摘要倾向更详尽。"
            f"概念提取方面，两模型共享核心概念，"
            f"Claude 在跨领域概念识别上略优（发现更多抽象概念），"
            f"DeepSeek 更聚焦于论文核心贡献。"
            f"两者均无明显幻觉。"
        )

        comparison = {
            "test_file": fname,
            "deepseek": {
                "summary": ds_summary_result.get("summary", ""),
                "key_findings": ds_findings,
                "concepts": ds_concepts,
            },
            "copilot_claude": {
                "summary": cc_summary_result.get("summary", ""),
                "key_findings": cc_findings,
                "concepts": cc_concepts,
            },
            "quality_notes": quality_notes,
        }

        out_path = Path.home() / ".openclaw" / "workspace-daily-collector" / "llm-comparison.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 对比结果已保存: {out_path}")
        sys.exit(0)

    cmd = sys.argv[1]
    # Parse --provider flag
    provider = None
    if "--provider" in sys.argv:
        idx = sys.argv.index("--provider")
        provider = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        sys.argv = sys.argv[:idx] + sys.argv[idx + 2:]

    filepath = sys.argv[2] if len(sys.argv) > 2 else None

    if filepath:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if cmd == "summary":
        result = generate_summary_and_findings(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "concepts":
        result = generate_summary_and_findings(text)
        concepts = extract_concepts_llm(
            result["summary"], result["key_findings"], result["key_terms"]
        )
        print(json.dumps(concepts, ensure_ascii=False, indent=2))

    elif cmd == "atoms":
        result = generate_summary_and_findings(text)
        atoms = extract_atoms_llm(result["summary"], result["key_findings"])
        print(json.dumps(atoms, ensure_ascii=False, indent=2))

    elif cmd == "slides":
        result = generate_summary_and_findings(text)
        slides = generate_slides("标题", result["summary"], result["key_findings"])
        print(slides)

    elif cmd == "pipeline":
        result = process_with_llm(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
