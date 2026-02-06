# gorin-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/glfruit/gorin-skills)](https://github.com/glfruit/gorin-skills)

> A collection of skills and integrations for AI-powered development tools

## About

gorin-skills is a curated repository of skills designed to extend the capabilities of AI development tools. Skills are organized into two main categories:

- **OpenClaw Skills** (`openclaw/`) - Integrations for the OpenClaw AI tool
- **General Skills** (`general/`) - Skills for Claude Code, Codex, and other AI tools

## Quick Start

### Using Existing Skills

1. Browse the skill directories to find what you need
2. Check the `README.md` in each skill directory for installation instructions
3. Follow the installation steps
4. Restart your AI tool

### Creating New Skills

1. Use the template script: `./scripts/setup-skill.sh`
2. Customize the skill files
3. Test locally
4. Submit a pull request

## Directory Structure

```
gorin-skills/
├── openclaw/           # Skills for OpenClaw
│   └── neobear/        # Bear Notes integration
└── general/            # Skills for other tools
```

## Featured Skills

### OpenClaw

- [neobear](./openclaw/neobear/) - Next-gen Bear Notes integration with perfect URL encoding

### Third-Party Skills

See [THIRD_PARTY_SKILLS_EN.md](./THIRD_PARTY_SKILLS_EN.md) for a registry of external skill libraries.

## Contributing

We welcome contributions! Please see [CONTRIBUTING_EN.md](./CONTRIBUTING_EN.md) for guidelines.

## Documentation

- [Architecture](./docs/architecture.md) - Project structure and design
- [Skill Development Guide](./docs/skill-development-guide.md) - How to create skills
- [Third-Party Skills](./docs/third-party-skills.md) - Using external skills

## License

MIT License - see [LICENSE](./LICENSE)

---

Made with community contributions for the AI development ecosystem
