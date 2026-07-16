# Skill Taxonomy

11 skill types identified from the OpenClaw project. Use this to classify a new skill and understand what content emphasis it needs.

---

## 1. Tool Wrapper

Wraps an external tool (CLI, API, database) with a standardized interface for agent consumption.

**Project example**: `obsidian-search` — wraps `ripgrep` for vault full-text search
**Path**: `skills/obsidian-search/`

**Key characteristics**:
- Config-driven (vault path, thresholds, defaults)
- Dual output format: JSON for agents, text for humans
- Error handling for missing tool / bad config
- Input validation and sanitization

**Common pitfalls**:
- Hardcoding paths instead of using config
- Only supporting one output format
- Not handling the tool being missing (`command -v` check)
- Shell injection through unsanitized user input (use `-F` for fixed strings in grep/rg)

**Template emphasis**: Configuration section, error handling, input/output format specification, dependency check.

---

## 2. API Integration

Calls an external HTTP API to send or receive data.

**Project example**: `send-email` — sends email via SMTP using nodemailer
**Path**: `skills/send-email/`

**Key characteristics**:
- Authentication (API keys, tokens) via environment variables
- Request/response format documentation
- Rate limiting and retry logic
- Error classification (auth failure vs network vs server)

**Common pitfalls**:
- Hardcoding API keys in scripts
- No timeout on HTTP requests
- Not handling rate limits (429 status)
- Ignoring response validation

**Template emphasis**: Auth configuration, payload examples, error handling matrix, rate limit strategy.

---

## 3. Pipeline/Orchestrator

Coordinates multiple data sources or processing stages into a unified workflow.

**Project example**: `content-curator-monitor` — monitors HN, X, RSS, Bear, Obsidian for content ideas
**Path**: `skills/content-curator-monitor/`

**Key characteristics**:
- Multi-source input with normalization
- Scoring/ranking/filtering stages
- Configurable source selection
- Output routing to different consumers

**Common pitfalls**:
- Processing all sources sequentially (should be parallel where possible)
- No fallback when one source fails
- Output format doesn't serve downstream consumers
- No quality threshold — floods users with noise

**Template emphasis**: Architecture diagram, source adapter pattern, scoring criteria, output routing rules.

---

## 4. PKM Integration

Creates, searches, or manages notes in the user's Personal Knowledge Management vault.

**Project examples**: `pkm-save-note`, `idea-creator`, `zk-para-zettel`
**Path**: `skills/pkm-save-note/`, `skills/idea-creator/`, `skills/zk-para-zettel/`

**Key characteristics**:
- PKM Core module integration (classify, dedup, relation, template, vault)
- 5-Type relation discovery (supports, contradicts, related, extends, cluster)
- PARA classification (Projects, Areas, Resources, Archives)
- Vault path configuration
- Note template system with frontmatter

**Common pitfalls**:
- Skipping dedup check → duplicate notes proliferate
- Not discovering relations → isolated notes
- Wrong PARA classification → notes lost in wrong location
- Ignoring existing vault conventions (ID format, tag style, folder structure)

**Template emphasis**: PKM Core integration points, relation discovery flow, template format, vault path handling.

---

## 5. Monitor/Cron

Runs on a schedule to check system state, generate reports, or trigger actions.

**Project examples**: `system-health-check`, `workspace-healthcheck.skill`
**Path**: `skills/system-health-check/`, `skills/workspace-healthcheck.skill/`

**Key characteristics**:
- launchd plist configuration for macOS scheduling
- Log file management (rotation, dedup with `tee`)
- Health check with pass/fail/warning status
- Alert routing (notification, log, file)
- Idempotent — safe to run multiple times

**Common pitfalls**:
- launchd `StandardOutPath` + script `tee` → double logging (use `/dev/null` for plist stdout)
- No crash-loop protection (`ThrottleInterval` too low)
- Check results not actionable (just "status: ok" without details)
- Script not idempotent — running twice causes side effects

**Template emphasis**: Schedule config (launchd plist), check items table, alert thresholds, log management.

---

## 6. Interactive Reader

Guides a user through structured reading/learning with state tracking.

**Project example**: `book-reader-notes` — EPUB/PDF reading with chapter-by-chapter notes
**Path**: `skills/book-reader-notes/`

**Key characteristics**:
- State persistence (current chapter, progress, notes taken)
- User rhythm control (save/redraft/skip/pause/next)
- Content parsing (EPUB XML, PDF text extraction)
- Note creation integrated with PKM
- Multi-session — user picks up where they left off

**Common pitfalls**:
- Losing state between sessions
- No way to skip or go back
- Forcing a fixed pace instead of letting user control rhythm
- Not integrating notes with existing knowledge base

**Template emphasis**: State tracking mechanism, user interaction commands, content parsing strategy, PKM integration.

---

## 7. Content Generator

Creates visual or textual content using external generation APIs.

**Project example**: `qwen-cover-image` — generates article cover images via Qwen-Image API
**Path**: `skills/qwen-cover-image/`

**Key characteristics**:
- Generation API integration (image, text, audio)
- Prompt engineering for consistent quality
- Output file management (naming, storage path)
- Style/format configuration

**Common pitfalls**:
- No prompt template — inconsistent results
- Output files overwrite each other (no unique naming)
- No preview/confirmation before final save
- API quota not tracked

**Template emphasis**: Prompt template, output path convention, quality parameters, API quota awareness.

---

## 8. Library/Internal

Utility skill called by other skills, not directly by users.

**Project example**: `example-library-skill` (chrome-cdp-tool) — Chrome CDP utilities for screenshot/PDF
**Path**: `skills/example-library-skill/`

**Key characteristics**:
- `user-invocable: false`
- Clean function interface for callers
- No interactive prompts
- Shared configuration

**Common pitfalls**:
- Adding user-facing prompts to a library skill
- Not documenting the calling convention
- Changing the interface without updating callers

**Template emphasis**: Function signatures, calling examples, return format, error propagation.

---

## 9. Process Guide

Teaches a standardized process or methodology through step-by-step instructions.

**Project example**: `dev-workflow` — standardized development workflow for teams
**Path**: `skills/dev-workflow/`

**Key characteristics**:
- Sequential steps with clear entry/exit criteria
- Decision points with explicit branching logic
- Checklists at each stage
- Role definitions (who does what)

**Common pitfalls**:
- Steps too vague ("review the code" without criteria)
- No decision points — assumes a single happy path
- Missing "when things go wrong" guidance
- No checklist — easy to skip steps

**Template emphasis**: Step-by-step workflow with decision tables, checklists, role assignments.

---

## 10. Research/Discovery

Searches multiple sources to find, analyze, and synthesize information.

**Project example**: `codex-deep-search` — deep web search using Codex CLI
**Path**: `skills/codex-deep-search/`

**Key characteristics**:
- Multi-source search strategy
- Result ranking and dedup
- Synthesis (not just listing results)
- Citation/source tracking

**Common pitfalls**:
- Returning raw search results without synthesis
- No dedup — same information from multiple sources
- Not citing sources → unverifiable claims
- Search too narrow or too broad

**Template emphasis**: Search strategy, source priority, synthesis format, citation convention.

---

## 11. Meta-Skill

A skill about creating or managing other skills.

**Project example**: `enhanced-skill-creator` (this skill)
**Path**: `skills/enhanced-skill-creator/`

**Key characteristics**:
- Self-referential (must follow its own advice)
- Research-driven methodology
- Quality validation
- References to other skills as examples

**Common pitfalls**:
- Producing template-only output (the previous version's main failure)
- Not eating its own dog food
- Over-engineering the creation process
- Losing sight of the goal: the generated skill must contain real domain knowledge

**Template emphasis**: Methodology workflow, quality checklist, validation criteria, example references.

---

## 12. Reviewer

Analyzes input against a modular rubric/checklist and produces structured feedback with severity classification.

**Inspired by**: Google Cloud Tech's "Reviewer" pattern (see references/google-adk-patterns.md)
**Related types**: Tool Wrapper (loads checklist), Process Guide (follows protocol)

**Key characteristics**:
- Separates *what to check* (rubric in `references/`) from *how to check* (SKILL.md protocol)
- Severity-based classification (error/warning/info or critical/moderate/minor)
- Structured output format with line numbers, explanations, and specific fixes
- Swappable checklists for different contexts (code style, security, documentation)

**Common pitfalls**:
- Hardcoding review criteria in SKILL.md (inflexible, can't swap checklists)
- Vague feedback without specific fixes ("code could be better")
- No severity classification (everything is equally important)
- Missing line number references (hard to locate issues)

**Template emphasis**: Review protocol steps, severity definitions, output structure, checklist loading mechanism.

**Example skills**: Code reviewer, security auditor, documentation quality checker, PR reviewer

---

## Design Patterns (Cross-Type)

Beyond the 12 types, Google Cloud Tech identified 5 recurring **design patterns** that can be applied across types:

| Pattern | Core Idea | Best For | Composition |
|---------|-----------|----------|-------------|
| **Tool Wrapper** | Dynamic loading of library conventions | Making agent an instant expert | Can include Reviewer at the end |
| **Generator** | Template + variable filling | Consistent output structure | Can use Inversion to gather variables |
| **Reviewer** | Rubric-driven analysis with severity | Quality assurance, audits | Can be a Pipeline step |
| **Inversion** | Agent interviews user before acting | Requirements gathering, planning | Can feed into Generator or Pipeline |
| **Pipeline** | Strict multi-step with checkpoints | Complex workflows, documentation | Can include Reviewer as final step |

See `references/google-adk-patterns.md` for detailed implementation guidance and SKILL.md examples for each pattern.

---

## Quick Classification Guide

When classifying a new skill, ask these questions in order:

1. Does it wrap a specific tool/CLI? → **Tool Wrapper**
2. Does it call an external HTTP API? → **API Integration**
3. Does it coordinate multiple sources/stages? → **Pipeline/Orchestrator**
4. Does it create/manage PKM vault notes? → **PKM Integration**
5. Does it run on a schedule? → **Monitor/Cron**
6. Does it guide interactive reading/learning? → **Interactive Reader**
7. Does it generate visual/textual content? → **Content Generator**
8. Is it only called by other skills? → **Library/Internal**
9. Does it teach a process/methodology? → **Process Guide**
10. Does it search and synthesize information? → **Research/Discovery**
11. Does it create or manage other skills? → **Meta-Skill**

A skill can span multiple types (e.g., Pipeline + PKM Integration). In that case, use the dominant type for template emphasis but incorporate patterns from secondary types.
