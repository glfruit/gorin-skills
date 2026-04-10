#!/usr/bin/env python3
"""log_watchdog.py — Gateway 错误日志增量扫描器

由 monitor agent heartbeat 每 15 分钟调用一次。
只报告真正需要人关注的问题，安静时不出声。

设计原则：
  1. 不报废话 — 已知的无害错误（WebSocket fallback、Skipping skill）直接过滤
  2. 不翻旧账 — 增量扫描 + 持久化位置文件，pos 丢失时只看最近 2000 行
  3. 只报增量 — 每次 digest 只含本次窗口内的新错误，不累积
  4. 冷却克制 — P0 同类错误 30 分钟内只报一次，附关键上下文

职责分界:
  log-watchdog   → 错误检测 + auth key 修复 + 告警
  gateway-watchdog → 进程健康 + 重启恢复
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "lib"))

from oclib.lock import PidLock
from oclib.log import Logger
from oclib.notify import send_telegram

# ─── Paths ──────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = Path.home() / ".openclaw" / "logs"
LOG_SOURCE = DATA_DIR / "gateway.err.log"
POS_FILE = DATA_DIR / "log-watchdog-pos"
STATE_FILE = DATA_DIR / "log-watchdog-state.json"
LOCK_FILE = Path("/tmp/log-watchdog.lock")
AUTO_FIX = SCRIPTS_DIR / "auto_fix_auth.py"

TELEGRAM_TARGET = os.environ.get("WATCHDOG_TELEGRAM_TARGET", "")

# ─── Tunables ───────────────────────────────────────────────────────
COOLDOWN_SECONDS = 1800        # 30 min between same-type alerts
AUTH_FIX_THRESHOLD = 3         # auth_401 count to trigger auto-fix
POS_LOSS_SCAN_LINES = 2000     # max lines to scan when pos file is lost
MIN_ERRORS_FOR_DIGEST = 3      # don't send digest if fewer errors

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# ─── Noise filter ──────────────────────────────────────────────────
# These patterns are known-harmless. Skip before classification.
NOISE_PATTERNS = [
    "Skipping skill path",        # 37 gorin-skills, ~200k entries, pure noise
    "falling back to HTTP",       # WebSocket 500 → HTTP fallback, harmless
]

SKILL_CATALOG_ROOTS = [
    Path.home() / ".openclaw" / "workspace" / "skills",
    Path.home() / ".openclaw" / "skills",
    Path.home() / ".gorin-skills" / "openclaw",
    Path.home() / ".openclaw" / "extensions",
    Path.home() / ".agents" / "skills",
    Path("/opt/homebrew/lib/node_modules/openclaw/skills"),
    Path("/opt/homebrew/lib/node_modules/openclaw/dist/extensions"),
]
OPTIONAL_ENOENT_NAME_RE = re.compile(r"(?i)(?:^|/)(?:findings|notes?)(?:-[^/]+)?\.md$")
OPTIONAL_ENOENT_SEGMENTS = {"tmp", "temp", "scratch", "artifacts", "artifact", "drafts", "outputs"}
MEMORY_DAILY_RE = re.compile(r"/memory/\d{4}-\d{2}-\d{2}\.md$")
SESSION_AGENT_RE = re.compile(
    r"session:agent:(?P<agent>[^:\s]+)(?::(?P<scope>subagent|cron|main|telegram|discord|feishu))?(?::(?P<subject>[^\s]+))?"
)
SESSION_AGENT_FULL_RE = re.compile(r"session:(agent:[^\s]+)")
DURATION_RE = re.compile(r"durationMs=(\d+)")
RUNID_RE = re.compile(r"runId=([^\s]+)")
PATH_RE = re.compile(r"access '([^']+)'")

logger = Logger("log-watchdog")
log = logger.log


@dataclass(frozen=True)
class Identity:
    agent: str
    lane: str
    subject: str | None = None

    @property
    def label(self) -> str:
        if self.subject:
            return f"{self.agent} ({self.lane}:{self.subject})"
        return f"{self.agent} ({self.lane})"


def notify(msg: str) -> None:
    if TELEGRAM_TARGET:
        send_telegram(TELEGRAM_TARGET, msg)
    else:
        log(msg)


# ─── Error classification ──────────────────────────────────────────

def extract_access_path(line: str) -> Path | None:
    match = PATH_RE.search(line)
    if not match:
        return None
    return Path(match.group(1)).expanduser()


def resolve_skill_catalog_target(path: Path) -> Path | None:
    parts = list(path.parts)
    if "skills" not in parts or path.name != "SKILL.md":
        return None
    try:
        idx = parts.index("skills")
    except ValueError:
        return None
    rel_parts = parts[idx + 1 :]
    if len(rel_parts) < 2:
        return None
    skill_name = rel_parts[0]
    relative_tail = Path(*rel_parts)
    candidates: list[Path] = []
    for root in SKILL_CATALOG_ROOTS:
        if root.name == "extensions":
            if root.exists():
                for ext_dir in root.iterdir():
                    candidates.append(ext_dir / "skills" / relative_tail)
            continue
        if root.name == "dist" and root.exists():
            for ext_dir in (root / "extensions").iterdir() if (root / "extensions").exists() else []:
                candidates.append(ext_dir / "skills" / relative_tail)
            continue
        candidates.append(root / relative_tail)
        candidates.append(root / skill_name / "SKILL.md")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def is_optional_artifact_path(path: Path) -> bool:
    normalized = path.as_posix().lower()
    if OPTIONAL_ENOENT_NAME_RE.search(normalized):
        return True
    return any(segment.lower() in OPTIONAL_ENOENT_SEGMENTS for segment in path.parts)


def classify_enoent_line(line: str) -> str | None:
    path = extract_access_path(line)
    if path is None:
        return "enoent_core"
    normalized = path.as_posix()
    if MEMORY_DAILY_RE.search(normalized):
        return None
    if resolve_skill_catalog_target(path) is not None:
        return None
    if is_optional_artifact_path(path):
        return "enoent_optional"
    return "enoent_core"


def classify_line(line: str) -> str | None:
    """Classify a single log line. Returns category or None."""
    # P0: fatal
    if any(kw in line for kw in ("uncaughtException", "unhandledRejection", "FATAL")):
        return "fatal"

    # P0 candidate: failover timeout (needs context window to determine if recovered)
    if "FailoverError" in line and "401" not in line and "令牌" not in line:
        return "failover"

    # P1: auth failures
    auth_markers = [
        ("401", "令牌已过期"), ("401", "身份验证"), ("401", "Unauthorized"),
        ("401", "Invalid API"), ("401", "invalid_api_key"),
    ]
    for m1, m2 in auth_markers:
        if m1 in line and m2 in line:
            return "auth_401"
    if "FailoverError" in line and "401" in line:
        return "auth_401"

    # P2: rate limit (only sendMessage/reply failures, not typing indicator)
    if "429" in line and any(kw in line for kw in ("sendMessage", "final reply")):
        return "rate_429_send"
    if "429" in line and "sendChatAction" in line:
        return None  # typing indicator 429 is harmless

    # P2: network timeout
    if any(kw in line for kw in ("ETIMEDOUT", "ECONNRESET", "ECONNREFUSED")):
        return "net_timeout"

    if "ENOENT" in line:
        return classify_enoent_line(line)

    return None


# ─── State management ──────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"cooldowns": {}, "reported_hashes": []}


def save_state(state: dict) -> None:
    # Cap reported_hashes to prevent unbounded growth
    state["reported_hashes"] = state.get("reported_hashes", [])[-10000:]
    # Remove non-serializable set before saving (rebuilt on load)
    saveable = {k: v for k, v in state.items() if k != "reported_hashes_set"}
    STATE_FILE.write_text(json.dumps(saveable, ensure_ascii=False))


def is_cooled_down(state: dict, category: str, now: int) -> bool:
    last = state.get("cooldowns", {}).get(category, 0)
    return (now - last) >= COOLDOWN_SECONDS


def set_cooldown(state: dict, category: str, now: int) -> None:
    state.setdefault("cooldowns", {})[category] = now


def is_already_reported(state: dict, line: str) -> bool:
    h = hashlib.md5(line.encode()).hexdigest()[:12]
    return h in state.get("reported_hashes_set", set())


def mark_reported(state: dict, line: str) -> None:
    h = hashlib.md5(line.encode()).hexdigest()[:12]
    state.setdefault("reported_hashes", []).append(h)
    state.setdefault("reported_hashes_set", set()).add(h)


# ─── Position tracking ─────────────────────────────────────────────

def read_position() -> int:
    if POS_FILE.exists():
        try:
            return int(POS_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def write_position(pos: int) -> None:
    POS_FILE.write_text(str(pos))


# ─── Main logic ────────────────────────────────────────────────────

def main() -> int:
    log("🔍 扫描开始")
    lock = PidLock(LOCK_FILE)
    if not lock.acquire():
        log("⏭️ 另一个实例运行中")
        return 0
    try:
        return _run()
    except Exception as e:
        log(f"🚨 异常: {e}")
        notify(f"🚨 Log Watchdog 异常: {e}")
        return 1
    finally:
        lock.release()


def extract_identity(line: str) -> Identity | None:
    session_match = SESSION_AGENT_RE.search(line)
    if session_match:
        agent = session_match.group("agent")
        scope = session_match.group("scope") or "main"
        subject = session_match.group("subject")
        return Identity(agent=agent, lane=scope, subject=subject)

    lane_match = re.search(r"lane=(\w+)", line)
    if lane_match:
        return Identity(agent="?", lane=lane_match.group(1))
    return None


def extract_duration_seconds(line: str) -> str:
    match = DURATION_RE.search(line)
    if not match:
        return "?"
    return str(int(match.group(1)) // 1000)


def failover_session_key(line: str) -> str:
    session_match = SESSION_AGENT_FULL_RE.search(line)
    if session_match:
        return session_match.group(1)
    runid_match = RUNID_RE.search(line)
    if runid_match:
        return runid_match.group(1)
    lane_match = re.search(r"lane=(\w+)", line)
    if lane_match:
        return lane_match.group(1)
    return line[:60]


def _run() -> int:
    now = int(time.time())
    state = load_state()

    # Convert reported_hashes list to set for O(1) lookup
    if "reported_hashes_set" not in state:
        state["reported_hashes_set"] = set(state.get("reported_hashes", []))

    if not LOG_SOURCE.exists():
        log(f"⚠️ 日志文件不存在: {LOG_SOURCE}")
        return 0

    # ── Incremental scan ──────────────────────────────────────
    total_lines = sum(1 for _ in open(LOG_SOURCE, "rb"))
    last_pos = read_position()

    # Log rotation
    if total_lines < last_pos:
        log(f"🔄 日志轮转 ({last_pos}→{total_lines})")
        last_pos = 0

    # Safety: pos lost → only scan recent lines
    if last_pos == 0 and total_lines > POS_LOSS_SCAN_LINES:
        log(f"⚠️ 位置缺失，限制扫描最近 {POS_LOSS_SCAN_LINES} 行")
        last_pos = total_lines - POS_LOSS_SCAN_LINES

    new_count = total_lines - last_pos
    if new_count <= 0:
        log(f"✅ 无新日志 (pos={total_lines})")
        write_position(total_lines)
        return 0

    log(f"📖 扫描 {new_count} 行 ({last_pos}→{total_lines})")

    # Read new lines
    with open(LOG_SOURCE, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
    raw_lines = [ANSI_RE.sub("", l.rstrip()) for l in all_lines[last_pos:]]

    # ── Filter noise ──────────────────────────────────────────
    lines = [l for l in raw_lines if not any(np in l for np in NOISE_PATTERNS)]
    filtered = len(raw_lines) - len(lines)
    if filtered > 0:
        log(f"🔇 过滤 {filtered} 行噪音")

    # ── Classify ──────────────────────────────────────────────
    # Collect fresh (unreported) errors with their categories
    fresh_errors: dict[str, list[str]] = {}  # category → [sample_lines]
    recovered_failovers: list[str] = []
    failover_success_window = 30  # expanded from 20 to catch slower recoveries
    seen_failover_sessions: set[str] = set()  # deduplicate same-session double-counting

    for idx, line in enumerate(lines):
        cat = classify_line(line)
        if cat is None:
            continue

        if cat == "failover":
            # Deduplicate: same failover event appears as both lane=subagent and
            # lane=session:agent:xxx:subagent:yyy — only count once per actual session/run.
            session_key = failover_session_key(line)
            if session_key in seen_failover_sessions:
                continue  # skip duplicate entry for same failover event
            seen_failover_sessions.add(session_key)

            # If a candidate succeeds shortly after this timeout, treat it as recovered failover,
            # not as "all providers failed".
            lookahead = lines[idx + 1: idx + 1 + failover_success_window]
            if any("model fallback decision: decision=candidate_succeeded" in x for x in lookahead):
                if not is_already_reported(state, line):
                    mark_reported(state, line)
                    recovered_failovers.append(line)
                continue

        if is_already_reported(state, line):
            continue
        mark_reported(state, line)
        fresh_errors.setdefault(cat, []).append(line)

    if not fresh_errors:
        log("✅ 无新增可操作错误")
        save_state(state)
        write_position(total_lines)
        return 0

    # ── Summary of what we found ──────────────────────────────
    summary_parts = []
    for cat in ("fatal", "failover", "auth_401", "rate_429_send", "net_timeout", "enoent_core", "enoent_optional"):
        errs = fresh_errors.get(cat, [])
        if not errs:
            continue
        labels = {
            "fatal": "💀 致命错误",
            "failover": "🔥 Failover 失败",
            "auth_401": "🔑 Auth 401",
            "rate_429_send": "🚦 429 发送失败",
            "net_timeout": "⏱ 网络超时",
            "enoent_core": "📂 关键文件缺失",
            "enoent_optional": "📝 可选工作文件缺失",
        }
        summary_parts.append(f"{labels.get(cat, cat)}: {len(errs)}")
    if recovered_failovers:
        summary_parts.append(f"🟡 Failover 已恢复: {len(recovered_failovers)}")

    log(f"📊 发现: {', '.join(summary_parts)}")

    # ── P0: Fatal ─────────────────────────────────────────────
    fatals = fresh_errors.get("fatal", [])
    if fatals and is_cooled_down(state, "fatal", now):
        notify(
            f"🚨 Gateway 致命错误 ({len(fatals)}次)\n"
            f"```\n{fatals[0][:200]}\n```"
        )
        set_cooldown(state, "fatal", now)
        log(f"🚨 P0 fatal 告警 ({len(fatals)})")

    # ── P0: Failover (only truly unrecovered) ────────────────
    failovers = fresh_errors.get("failover", [])
    if failovers and is_cooled_down(state, "failover", now):
        sample = failovers[0]
        identity = extract_identity(sample) or Identity(agent="?", lane="unknown")
        duration_s = extract_duration_seconds(sample)
        notify(
            f"🚨 模型 Failover 未恢复 ({len(failovers)}次)\n"
            f"对象: {identity.label} | 等待: {duration_s}s\n"
            f"```\n{sample[:200]}\n```"
        )
        set_cooldown(state, "failover", now)
        log(f"🚨 P0 failover 告警 ({len(failovers)}) target={identity.label}")

    # Recovered failovers — log but do NOT page; only notify if count is unusually high
    if recovered_failovers:
        sample = recovered_failovers[0]
        identity = extract_identity(sample) or Identity(agent="?", lane="unknown")
        duration_s = extract_duration_seconds(sample)
        log(f"🟡 Failover 已恢复 ({len(recovered_failovers)}) target={identity.label} wait={duration_s}s")
        # Only notify if 3+ recovered in same window (may indicate systemic issue)
        if len(recovered_failovers) >= 3 and is_cooled_down(state, "failover_recovered", now):
            notify(
                f"⚠️ 模型 Failover 频繁但已恢复 ({len(recovered_failovers)}次)\n"
                f"对象: {identity.label}\n"
                f"首次等待: {duration_s}s\n"
                f"后备模型已接住，服务未中断。"
            )
            set_cooldown(state, "failover_recovered", now)

    # ── P1: Auth auto-fix ─────────────────────────────────────
    auths = fresh_errors.get("auth_401", [])
    if len(auths) >= AUTH_FIX_THRESHOLD and is_cooled_down(state, "auth_401", now):
        log(f"🔧 Auth 401 阈值达到 ({len(auths)})，执行修复...")
        try:
            result = subprocess.run(
                ["python3", str(AUTO_FIX)],
                capture_output=True, text=True, timeout=60,
            )
            fix_out = result.stdout.strip()
            try:
                fix_data = json.loads(fix_out)
                checked = fix_data.get("checked", "?")
                fixed = fix_data.get("fixed", "?")
            except (json.JSONDecodeError, TypeError):
                checked = fixed = "?"
            notify(f"🔧 Auth 自动修复: 检查 {checked}，修复 {fixed}")
        except Exception as e:
            log(f"🔧 修复异常: {e}")
        set_cooldown(state, "auth_401", now)

    # ── P2: Silent accumulation (no digest unless asked) ──────
    # We log the counts but DON'T send periodic digest messages.
    # The heartbeat agent (monitor) can check state on demand.
    # This eliminates the noise of hourly "24 429s" reports.
    total_new = sum(len(v) for v in fresh_errors.values())
    log(f"📊 本轮新增 {total_new} 个可操作错误，已记录")

    # ── Cleanup & save ────────────────────────────────────────
    # Reset reported_hashes_set once a day to prevent stale state
    day_start = (now // 86400) * 86400  # midnight UTC
    last_reset = state.get("last_hash_reset", 0)
    if (day_start - last_reset) >= 86400:
        log("🔄 每日重置 hash 缓存")
        state["reported_hashes"] = []
        state["reported_hashes_set"] = set()
        state["last_hash_reset"] = day_start

    save_state(state)
    write_position(total_lines)
    log(f"✅ 完成 pos={total_lines}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
