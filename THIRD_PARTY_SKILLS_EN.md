# Third-Party Skills Registry

This document serves as a central registry for third-party skill libraries that integrate with gorin-skills or provide complementary functionality.

## What Are Third-Party Skills?

Third-party skills are libraries, plugins, or integrations developed by the community that extend AI development tools but are maintained outside of this repository.

## How to Submit

To add your skill library to this registry:

1. Ensure your skill has a stable home (GitHub repository, npm package, etc.)
2. Add a submission via PR with the following format
3. Maintain your skill independently

## Submission Format

```yaml
name: Skill Name
category: openclaw | general | claude-code | codex | other
description: Brief description
repository: https://github.com/user/repo
homepage: https://example.com
author: Your Name
license: MIT | Apache-2.0 | Other
status: stable | beta | experimental
tags: [tag1, tag2, tag3]
integration: How to integrate with gorin-skills
```

## Registry

### OpenClaw Skills

#### Community Maintained

| Name | Description | Status | Repository |
|------|-------------|--------|------------|
| *(Pending submissions)* | | | |

### General Skills

#### Claude Code Extensions

| Name | Description | Status | Repository |
|------|-------------|--------|------------|
| *(Pending submissions)* | | | |

#### Codex Plugins

| Name | Description | Status | Repository |
|------|-------------|--------|------------|
| *(Pending submissions)* | | | |

### Multi-Tool Skills

| Name | Description | Status | Repository |
|------|-------------|--------|------------|
| *(Pending submissions)* | | | |

## Integration Guidelines

### For Skill Users

1. Review the skill's documentation
2. Follow installation instructions from the skill's repository
3. Report issues to the skill's maintainers

### For Skill Authors

To make your skill compatible with gorin-skills:

1. Follow the file structure conventions in [docs/skill-development-guide.md](./docs/skill-development-guide.md)
2. Include a SKILL.md file with proper metadata
3. Provide clear installation instructions
4. Choose an appropriate license

## Maintenance

This registry is updated periodically. Skills that are no longer maintained may be marked as deprecated.

---

Last updated: 2026-02-06
