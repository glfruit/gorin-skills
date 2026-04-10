---
name: obsidian-defuddle
description: "Extract clean markdown content from web pages using Defuddle CLI, removing clutter and navigation to save tokens."
triggers: ["defuddle", "extract content", "clean markdown"]
user-invocable: true
agent-usable: true
---

# Defuddle

Use Defuddle CLI to extract clean readable content from web pages. Prefer over WebFetch for standard web pages — it removes navigation, ads, and clutter, reducing token usage.

If not installed: `npm install -g defuddle-cli`

## Usage

Always use `--md` for markdown output:

```bash
defuddle parse <url> --md
```

Save to file:

```bash
defuddle parse <url> --md -o content.md
```

Extract specific metadata:

```bash
defuddle parse <url> -p title
defuddle parse <url> -p description
defuddle parse <url> -p domain
```

## Output formats

| Flag | Format |
|------|--------|
| `--md` | Markdown (default choice) |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <name>` | Specific metadata property |

## Gotchas

- **Not a universal extractor**: Defuddle works well for standard articles/blog posts but may struggle with SPAs (React/Vue/Angular apps), paywalled content, or heavily JavaScript-dependent pages.
- **WeChat articles**: Defuddle may not extract full content from WeChat public account articles. For those, consider using web_fetch or a dedicated extractor.
- **PDF pages**: Defuddle is designed for HTML pages, not PDF URLs. Use a PDF-specific tool for direct PDF extraction.
- **Rate limiting**: Some sites may block automated requests. No built-in retry or rate-limit handling.
- **Encoding**: Rare character encoding issues on non-UTF-8 sites may produce garbled output.
- **Installation**: Requires Node.js runtime. If `npm install -g` fails due to permissions, use `npx defuddle-cli` instead.

## Security & Portability

- Defuddle makes HTTP requests to external URLs. Ensure URLs are from trusted sources before fetching.
- Extracted content is processed locally — no data is sent to third-party services after the initial fetch.
- The `--json` output includes raw HTML which may contain scripts or tracking pixels from the original page. Use `--md` to avoid this.
- Works on any platform with Node.js; no OS-specific dependencies.
