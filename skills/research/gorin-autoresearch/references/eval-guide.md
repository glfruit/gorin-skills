# Eval Guide for Autoresearch

How to write eval criteria that actually improve skills instead of giving false confidence.

## The Golden Rule

Every eval must be a yes/no question. Not a scale. Not a vibe check. Binary.

**Why:** Scales compound variability. If you have 4 evals scored 1-7, your total score has massive variance across runs. Binary evals give reliable signal.

---

## Good Evals vs Bad Evals by Skill Type

### Text/Copy Skills (newsletters, tweets, emails, landing pages, de-ai-writing)

**Bad:**
- "Is the writing good?" — too vague
- "Rate engagement potential 1-10" — scale = unreliable
- "Does it sound human?" — subjective, inconsistent

**Good:**
- "Does the output contain zero phrases from this banned list: [game-changer, here's the kicker, the best part, level up]?"
- "Does the opening sentence reference a specific time, place, or sensory detail?"
- "Is the output between 150-400 words?"
- "Does it end with a specific CTA that tells the reader exactly what to do next?"
- "Is the output free of AI-typical filler phrases (delve, tapestry, beacon, orchestrate)?"

### Web Scraping Skills (web-reader, web-content-fetcher)

**Bad:**
- "Is the content accurate?" — accuracy depends on source
- "Did it capture everything?" — vague boundary

**Good:**
- "Does the output contain a valid URL in the YAML front matter?"
- "Is the extracted content free of navigation elements, footers, and cookie banners?"
- "Does the markdown preserve all hyperlinks from the source?"
- "Is the output length > 200 characters (not just a stub or error page)?"
- "Does the output NOT contain login-wall indicators (请登录, sign in, 403, CAPTCHA)?"

### Visual/Design Skills (diagram-generator, cover-image, infographic, xhs-images)

**Bad:**
- "Does it look professional?" — subjective
- "Rate visual quality 1-5" — scale

**Good:**
- "Is all text legible with no truncated or overlapping words?"
- "Does the color palette use only soft/pastel tones with no neon or high-saturation?"
- "Is the layout linear (left-to-right or top-to-bottom) with no scattered elements?"
- "Is the output free of numbered steps, ordinals, or sequential numbering?"

### Code/Technical Skills (coding-agent, send-email, cron-scheduling)

**Bad:**
- "Is the code clean?" — subjective
- "Does it follow best practices?" — which ones?

**Good:**
- "Does the script include `set -euo pipefail` or equivalent error handling?"
- "Does the output contain zero TODO or placeholder comments?"
- "Are all external calls (API, file I/O, network) wrapped in error handling?"
- "Does the script use `$HOME` instead of hardcoded `/Users/` paths?"

### PKM/Notes Skills (pkm-save-note, idea-creator, obsidian)

**Bad:**
- "Is the note useful?" — subjective
- "Is it well-organized?" — vague

**Good:**
- "Does the note have a YAML front matter with title and date?"
- "Does the note include at least one `[[backlink]]` to an existing note?"
- "Is the note filed under the correct PARA category (Project/Area/Resource/Archive)?"
- "Does the note contain at least one specific, actionable insight (not just a link or quote)?"

---

## Common Mistakes in Eval Design

### 1. Too Many Evals
> More than 6 evals → skill starts gaming the checklist instead of improving.

**Fix:** Pick the 3-6 checks that matter most. If those pass, the output is probably good.

### 2. Too Narrow / Rigid
> "Must contain exactly 3 bullet points" → skill passes technically but produces weird output.

**Fix:** Check for qualities you care about, not arbitrary structural constraints.

### 3. Overlapping Evals
> "Is text grammatically correct?" + "Are there spelling errors?" → double-counting.

**Fix:** Each eval must test something distinct.

### 4. Unmeasurable by an Agent
> "Would a human find this engaging?" → agent says "yes" almost every time.

**Fix:** Translate subjective qualities into observable signals. "Engaging" → "Does the first sentence contain a specific claim, story, or question?"

---

## The 3-Question Test

Before finalizing an eval, verify:

1. **Could two different agents score the same output and agree?** If not → too subjective.
2. **Could a skill game this eval without actually improving?** If yes → too narrow.
3. **Does this eval test something the user actually cares about?** If not → drop it.

---

## Template

```
EVAL [N]: [Short name]
Question: [Yes/no question]
Pass: [What "yes" looks like — one sentence, specific]
Fail: [What triggers "no" — one sentence, specific]
```
