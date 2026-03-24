# Changelog

All notable changes to this skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-02-22

### Added
- Initial implementation with enhanced-skill-creator workflow
- Weekly PARA review (`/para review`)
- Project status management (`/para status`)
- Areas health check (`/para areas`)
- False project detection (`/para false-projects`)
- Automatic report generation
- Git version control

### Features
- Scan Projects in Active/Simmering/Sleeping/Done directories
- Parse frontmatter for deadline, progress, area metadata
- Detect false projects (no deadline or stalled >3 months)
- Generate markdown reports with recommendations
- Move projects between status directories
- Track areas health and maintenance standards
