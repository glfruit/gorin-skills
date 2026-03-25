# Language Handling Reference

## Detection Priority

1. `--lang` flag (explicit)
2. EXTEND.md `language` setting
3. User's conversation language (input language)
4. Source content language

## Language Rule

ALL responses use user's preferred language:
- Questions and confirmations
- Progress reports
- Error messages
- Completion summaries

Technical terms (style names, file paths, code) remain in English.
