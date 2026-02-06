# Contributing to gorin-skills

Thank you for your interest in contributing! This document provides guidelines for contributing to the gorin-skills project.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/gorin-skills.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## How to Contribute

### Ways to Contribute

- Submit new skills
- Improve existing skills
- Fix bugs
- Improve documentation
- Report issues
- Review pull requests

### Skill Categories

When contributing, specify which category your skill belongs to:

- **openclaw/** - Skills for OpenClaw
- **general/** - Skills for Claude Code, Codex, etc.

## Skill Submission Process

### 1. Create a Skill Using the Template

```bash
./scripts/setup-skill.sh
```

Follow the prompts to enter your skill name and category.

### 2. Skill Requirements

Each skill MUST include:

- `README.md` - User documentation
- `SKILL.md` - Skill metadata (with YAML frontmatter)
- `LICENSE` - License file (MIT recommended)
- `install.sh` - Installation script (optional but recommended)

### 3. Validate Your Skill

```bash
./scripts/validate-skill.sh path/to/skill
```

### 4. Submit a Pull Request

Include in your PR:
- Description of the skill
- Installation instructions
- Usage examples
- Testing performed

## Development Workflow

1. Create an issue or comment on an existing one
2. Create a branch from `main`
3. Make your changes
4. Run validation: `./scripts/validate-skill.sh path/to/skill`
5. Commit with clear messages
6. Push and create a PR

## Coding Standards

### General

- Use clear, descriptive names
- Add comments for complex logic
- Follow existing code style
- Keep files focused and modular

### Documentation

- Write clear, concise documentation
- Include usage examples
- Document prerequisites
- Provide troubleshooting guidance

## Testing Requirements

Before submitting:

1. Test installation works
2. Test all documented features
3. Test on target platforms
4. Run validation script

## Pull Request Process

1. Ensure your code passes validation
2. Update documentation if needed
3. Reference related issues
4. Use the PR template
5. Respond to review feedback

---

Thank you for contributing to gorin-skills!
