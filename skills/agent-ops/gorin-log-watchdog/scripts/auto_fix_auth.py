#!/usr/bin/env python3
"""auto-fix-auth.py — 从 openclaw.json 和 .env 生成本地 key，同步到所有 agent auth-profiles.json

Output: JSON report { "checked": N, "fixed": N, "details": [...] }
"""
import json
import os
import glob
import re

openclaw_dir = os.path.expanduser("~/.openclaw")
env_file = os.path.join(openclaw_dir, ".env")
agents_dir = os.path.join(openclaw_dir, "agents")
config_path = os.path.join(openclaw_dir, "openclaw.json")

if not os.path.isfile(env_file):
    print(json.dumps({"error": "missing .env", "checked": 0, "fixed": 0, "details": []}))
    raise SystemExit(1)

# Load .env
env_keys = {}
with open(env_file) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_keys[key.strip()] = value.strip().strip('"').strip("'")

# Read provider → env key name mapping from openclaw.json
with open(config_path) as f:
    config = json.load(f)

providers = config.get("models", {}).get("providers", {})
provider_env_names = {}
for provider, entry in providers.items():
    api_key = entry.get("apiKey")
    if not isinstance(api_key, str):
        continue
    match = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", api_key.strip())
    if match:
        provider_env_names[provider] = match.group(1)

# Build provider → secret value
provider_secret_values = {
    p: env_keys[ek]
    for p, ek in provider_env_names.items()
    if ek in env_keys
}

checked = 0
fixed = 0
details = []

for ap_path in sorted(glob.glob(os.path.join(agents_dir, "*/agent/auth-profiles.json"))):
    agent_name = os.path.basename(os.path.dirname(os.path.dirname(ap_path)))
    checked += 1

    try:
        with open(ap_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        continue

    profiles = data.get("profiles", {})
    modified = False

    for profile_id, profile in profiles.items():
        provider = profile.get("provider", "")
        if provider not in provider_secret_values:
            continue

        target_key = provider_secret_values[provider]
        current_key = profile.get("key") or profile.get("apiKey")
        had_ref = "keyRef" in profile

        if current_key != target_key or had_ref:
            profile.pop("keyRef", None)
            profile.pop("key", None)
            profile.pop("apiKey", None)
            profile["key"] = target_key
            modified = True
            fixed += 1
            details.append({"agent": agent_name, "profile": f"{provider}:{profile_id}"})

    if modified:
        with open(ap_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

print(json.dumps({"checked": checked, "fixed": fixed, "details": details}))
