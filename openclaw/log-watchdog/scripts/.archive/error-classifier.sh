#!/usr/bin/env bash
# error-classifier.sh — 纯函数：stdin 日志行 → stdout JSON 分类计数
# 无副作用，不写文件，不发通知
#
# Usage: cat gateway.err.log | bash error-classifier.sh
# Output: {"auth_401":0,"rate_429":0,"etimedout":0,"enoent":0,"reaction_invalid":0,"unknown_target":0,"failover_all_failed":0,"fatal":0,"total_lines":0}

set -euo pipefail

auth_401=0
rate_429=0
etimedout=0
enoent=0
reaction_invalid=0
unknown_target=0
failover_all_failed=0
fatal=0
total_lines=0

while IFS= read -r line || [[ -n "$line" ]]; do
  total_lines=$((total_lines + 1))

  # P0: fatal errors
  case "$line" in
    *"uncaughtException"*|*"unhandledRejection"*|*"FATAL"*)
      fatal=$((fatal + 1))
      continue
      ;;
  esac

  # P0: all providers failed (FailoverError without 401 — pure failover exhaustion)
  if [[ "$line" == *"FailoverError"* ]] && [[ "$line" != *"401"* ]] && [[ "$line" != *"令牌已过期"* ]] && [[ "$line" != *"身份验证"* ]]; then
    failover_all_failed=$((failover_all_failed + 1))
    continue
  fi

  # P1: auth failures (401 + various Chinese/English messages)
  case "$line" in
    *"401"*"令牌已过期"*|*"401"*"身份验证"*|*"401"*"Unauthorized"*|*"401"*"Invalid API"*|*"401"*"invalid_api_key"*|*"FailoverError"*"401"*)
      auth_401=$((auth_401 + 1))
      continue
      ;;
  esac

  # P2: rate limiting
  case "$line" in
    *"429"*|*"rate limit"*|*"Rate limit"*|*"RateLimitError"*|*"too many requests"*|*"Too Many Requests"*)
      rate_429=$((rate_429 + 1))
      continue
      ;;
  esac

  # P2: network timeouts
  case "$line" in
    *"ETIMEDOUT"*|*"ECONNRESET"*|*"ECONNREFUSED"*|*"EHOSTUNREACH"*|*"socket hang up"*|*"network timeout"*)
      etimedout=$((etimedout + 1))
      continue
      ;;
  esac

  # P3: file not found (often normal probing)
  case "$line" in
    *"ENOENT"*)
      enoent=$((enoent + 1))
      continue
      ;;
  esac

  # P3: Telegram reaction errors
  case "$line" in
    *"REACTION_INVALID"*|*"Bad Request: REACTION"*)
      reaction_invalid=$((reaction_invalid + 1))
      continue
      ;;
  esac

  # P3: routing misses
  case "$line" in
    *"Unknown target"*|*"Unknown channel"*|*"no route"*|*"No route"*)
      unknown_target=$((unknown_target + 1))
      continue
      ;;
  esac
done

# Output JSON (no trailing newline issues — built with printf)
printf '{"auth_401":%d,"rate_429":%d,"etimedout":%d,"enoent":%d,"reaction_invalid":%d,"unknown_target":%d,"failover_all_failed":%d,"fatal":%d,"total_lines":%d}\n' \
  "$auth_401" "$rate_429" "$etimedout" "$enoent" "$reaction_invalid" "$unknown_target" "$failover_all_failed" "$fatal" "$total_lines"
