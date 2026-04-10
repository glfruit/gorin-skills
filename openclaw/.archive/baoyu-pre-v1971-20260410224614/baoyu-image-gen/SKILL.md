---
name: baoyu-image-gen
description: AI image generation with OpenAI, Google, DashScope and Replicate APIs. Supports text-to-image, reference images, aspect ratios. Sequential by default; parallel generation available on request. Use when user asks to generate, create, or draw images.
---

# Image Generation (AI SDK)

Official API-based image generation. Supports OpenAI, Google, DashScope (阿里通义万象) and Replicate providers.

## Script Directory

**Agent Execution**:
1. `SKILL_DIR` = this SKILL.md file's directory
2. Script path = `${SKILL_DIR}/scripts/main.ts`

## Step 0: Load Preferences ⛔ BLOCKING

**CRITICAL**: This step MUST complete BEFORE any image generation. Do NOT skip or defer.

**Agent reminder**:
- Treat `EXTEND.md` as the real default source of truth for provider/model preferences.
- Do **not** assume Google just because example commands mention Gemini.
- Do **not** force `--provider google` unless the user explicitly asks for Google or the current task truly requires it.
- In environments like this one, `default_provider` may already be `openai` with an OpenAI-compatible proxy model such as `gemini-3-pro-image-preview`.

Check EXTEND.md existence (priority: project → user):

```bash
test -f .openclaw/skills-config/baoyu/baoyu-image-gen/EXTEND.md && echo "project"
test -f "$HOME/.openclaw/skills-config/baoyu/baoyu-image-gen/EXTEND.md" && echo "user"
```

| Result | Action |
|--------|--------|
| Found | Load, parse, apply settings. If `default_model.[provider]` is null → ask model only (Flow 2) |
| Not found | ⛔ Run first-time setup ([references/config/first-time-setup.md](references/config/first-time-setup.md)) → Save EXTEND.md → Then continue |

**CRITICAL**: If not found, complete the full setup (provider + model + quality + save location) using AskUserQuestion BEFORE generating any images. Generation is BLOCKED until EXTEND.md is created.

| Path | Location |
|------|----------|
| `.openclaw/skills-config/baoyu/baoyu-image-gen/EXTEND.md` | Project directory |
| `$HOME/.openclaw/skills-config/baoyu/baoyu-image-gen/EXTEND.md` | User home |

**EXTEND.md Supports**: Default provider | Default quality | Default aspect ratio | Default image size | Default models

Schema: `references/config/preferences-schema.md`

## Usage

```bash
# Basic (preferred: let EXTEND.md choose provider/model)
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image cat.png

# With aspect ratio
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A landscape" --image out.png --ar 16:9

# High quality
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image out.png --quality 2k

# From prompt files
npx -y bun ${SKILL_DIR}/scripts/main.ts --promptfiles system.md content.md --image out.png

# With reference images (let script resolve provider after Step 0)
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "Make blue" --image out.png --ref source.png

# OpenAI-compatible proxy environment (for example default_provider: openai)
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "Make blue" --image out.png --provider openai --model gemini-3-pro-image-preview --ref source.png

# Google-native environment only (requires GOOGLE_API_KEY or GEMINI_API_KEY)
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "Make blue" --image out.png --provider google --model gemini-3-pro-image-preview --ref source.png

# Specific provider
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image out.png --provider openai

# DashScope (阿里通义万象)
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "一只可爱的猫" --image out.png --provider dashscope

# Replicate (google/nano-banana-pro)
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image out.png --provider replicate

# Replicate with specific model
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image out.png --provider replicate --model google/nano-banana
```

## Options

| Option | Description |
|--------|-------------|
| `--prompt <text>`, `-p` | Prompt text |
| `--promptfiles <files...>` | Read prompt from files (concatenated) |
| `--image <path>` | Output image path (required) |
| `--provider google\|openai\|dashscope\|replicate` | Force provider. If omitted, resolve from EXTEND.md first, then available API keys. |
| `--model <id>`, `-m` | Model ID (Google: `gemini-3-pro-image-preview`, `gemini-3.1-flash-image-preview`; OpenAI: `gpt-image-1.5`) |
| `--ar <ratio>` | Aspect ratio (e.g., `16:9`, `1:1`, `4:3`) |
| `--size <WxH>` | Size (e.g., `1024x1024`) |
| `--quality normal\|2k` | Quality preset (default: 2k) |
| `--imageSize 1K\|2K\|4K` | Image size for Google (default: from quality) |
| `--ref <files...>` | Reference images. Supported by Google multimodal (`gemini-3-pro-image-preview`, `gemini-3-flash-preview`, `gemini-3.1-flash-image-preview`) and OpenAI edits (GPT Image models). If provider omitted, finish Step 0 first, then let the script resolve provider. |
| `--n <count>` | Number of images |
| `--json` | JSON output |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google API key |
| `DASHSCOPE_API_KEY` | DashScope API key (阿里云) |
| `REPLICATE_API_TOKEN` | Replicate API token |
| `OPENAI_IMAGE_MODEL` | OpenAI model override |
| `GOOGLE_IMAGE_MODEL` | Google model override |
| `DASHSCOPE_IMAGE_MODEL` | DashScope model override (default: z-image-turbo) |
| `REPLICATE_IMAGE_MODEL` | Replicate model override (default: google/nano-banana-pro) |
| `OPENAI_BASE_URL` | Custom OpenAI endpoint |
| `GOOGLE_BASE_URL` | Custom Google endpoint |
| `DASHSCOPE_BASE_URL` | Custom DashScope endpoint |
| `REPLICATE_BASE_URL` | Custom Replicate endpoint |

**Load Priority**: CLI args > EXTEND.md > env vars > `<cwd>/.openclaw/skills-config/baoyu/.env` > `~/.openclaw/skills-config/baoyu/.env`

## Model Resolution

Model priority (highest → lowest), applies to all providers:

1. CLI flag: `--model <id>`
2. EXTEND.md: `default_model.[provider]`
3. Env var: `<PROVIDER>_IMAGE_MODEL` (e.g., `GOOGLE_IMAGE_MODEL`)
4. Built-in default

**EXTEND.md overrides env vars**. If both EXTEND.md `default_model.google: "gemini-3-pro-image-preview"` and env var `GOOGLE_IMAGE_MODEL=gemini-3.1-flash-image-preview` exist, EXTEND.md wins.

**Agent MUST display model info** before each generation:
- Show: `Using [provider] / [model]`
- Show switch hint: `Switch model: --model <id> | EXTEND.md default_model.[provider] | env <PROVIDER>_IMAGE_MODEL`

### Replicate Models

Supported model formats:

- `owner/name` (recommended for official models), e.g. `google/nano-banana-pro`
- `owner/name:version` (community models by version), e.g. `stability-ai/sdxl:<version>`

Examples:

```bash
# Use Replicate default model
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image out.png --provider replicate

# Override model explicitly
npx -y bun ${SKILL_DIR}/scripts/main.ts --prompt "A cat" --image out.png --provider replicate --model google/nano-banana
```

## Provider Selection

Resolution order:

1. `--provider` specified → use it (if `--ref`, must be `google`, `openai`, or `replicate`)
2. Otherwise, read `EXTEND.md` and use `default_provider` when present
3. If `--ref` is provided and provider is still unresolved → prefer providers that support the current environment and task; the script may choose Google, OpenAI, or Replicate based on available keys
4. If exactly one API key family is available → use that provider
5. If multiple API keys are available and nothing else selects one → use the script's auto-detection order

**Important for agents**:
- Always complete **Step 0** before deciding provider.
- If the environment only has `OPENAI_API_KEY` and `EXTEND.md` says `default_provider: openai`, do not misclassify the setup as "Google key missing".
- Do not force `--provider google` just because the model name contains `gemini`.

## Quality Presets

| Preset | Google imageSize | OpenAI Size | Use Case |
|--------|------------------|-------------|----------|
| `normal` | 1K | 1024px | Quick previews |
| `2k` (default) | 2K | 2048px | Covers, illustrations, infographics |

**Google imageSize**: Can be overridden with `--imageSize 1K|2K|4K`

## Aspect Ratios

Supported: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `2.35:1`

- Google multimodal: uses `imageConfig.aspectRatio`
- Google Imagen: uses `aspectRatio` parameter
- OpenAI: maps to closest supported size

## Generation Mode

**Default**: Sequential generation (one image at a time). This ensures stable output and easier debugging.

**Parallel Generation**: Only use when user explicitly requests parallel/concurrent generation.

| Mode | When to Use |
|------|-------------|
| Sequential (default) | Normal usage, single images, small batches |
| Parallel | User explicitly requests, large batches (10+) |

**Parallel Settings** (when requested):

| Setting | Value |
|---------|-------|
| Recommended concurrency | 4 subagents |
| Max concurrency | 8 subagents |
| Use case | Large batch generation when user requests parallel |

**Agent Implementation** (parallel mode only):
```
# Launch multiple generations in parallel using Task tool
# Each Task runs as background subagent with run_in_background=true
# Collect results via TaskOutput when all complete
```

## Error Handling

- Missing API key → error with setup instructions
- Generation failure → auto-retry once
- Invalid aspect ratio → warning, proceed with default
- Reference images with unsupported provider/model → error with fix hint (switch to Google multimodal: `gemini-3-pro-image-preview`, `gemini-3.1-flash-image-preview`; or OpenAI GPT Image edits)

## Extension Support

Custom configurations via EXTEND.md. See **Preferences** section for paths and supported options.
