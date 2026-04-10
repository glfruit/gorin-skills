# Description Engineering

The description is the routing surface. Treat it like an API contract for triggering.

## Required ingredients

A strong description should include:
- core capability
- action verbs the user would actually say
- object nouns the skill operates on
- natural trigger phrases
- at least one explicit negative trigger

## Checklist

- What does the skill *do* in one sentence?
- What verbs would a real user type? (`create`, `review`, `debug`, `package`, `plan`)
- What objects would they mention? (`skill`, `PR`, `slides`, `email`, `report`)
- What nearby requests should **not** trigger this skill?
- If the user is bilingual, do the obvious Chinese and English phrasings both appear?

## Good pattern

"Create high-quality skills using case-based research and internal acceptance. Use when the user wants to create, rebuild, or improve an AgentSkill. Don't use it for one-line script edits, trivial aliases, or direct minor SKILL.md tweaks."

## Bad pattern

"Helps with skills and related tasks."

Problems:
- too broad
- no concrete verbs
- no object nouns
- no negative triggers

## Anti-patterns

Avoid:
- catch-all phrasing (`all tasks`, `everything`, `any request`)
- wildcard intent (`.*`, `*`)
- category-only descriptions (`handles docs`, `does coding help`)
- body-only routing guidance that never appears in metadata
