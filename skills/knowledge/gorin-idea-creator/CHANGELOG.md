# Changelog — Idea Creator

All notable changes to this skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-02-21

### Added
- Initial release of idea-creator skill
- Core functionality: capture ideas with "想法" prefix
- Automatic relationship discovery across vault
- 5 relationship types: supports, contradicts, related, extends, cluster
- Integration with PKM-VERSE vault structure
- Keyword extraction from idea content
- Multi-directory search (Permanent, Fleeting, Areas)
- Bash script implementation for portability
- Comprehensive documentation (SKILL.md, user guide, API reference)
- Obsidian template for idea notes

### Features
- **Quick Capture**: Type "想法 xxx" to instantly save ideas
- **Smart Association**: Automatically finds related notes
- **Relationship Classification**: Tags each link with type
- **Vault Integration**: Saves to Zettels/1-Fleeting/
- **Flexible Input**: Supports title, content, and tags
- **Relationship Report**: Shows discovered connections

### Technical
- Pure Bash implementation for compatibility
- No external dependencies (except standard Unix tools)
- Configurable vault path via environment variable
- Modular functions for extensibility
- Exit codes for error handling

### Documentation
- SKILL.md: Complete skill specification
- user-guide.md: End-user documentation
- api-reference.md: Developer documentation
- research-notes.md: Design rationale
- Template: System/Templates/Idea.md

### Testing
- Test A: Structure validation (✅)
- Test B: Trigger accuracy (✅)
- Test C: Coverage analysis (✅)

### Integration
- Works with pkm-zettel-creator (ideas → permanent notes)
- Works with pkm-para-manager (ideas → projects)
- Works with pkm-daily-review (daily idea review)
- Part of PKM-VERSE ecosystem

## Future Roadmap

### [1.1.0] — Planned
- [ ] ML-based relationship classification
- [ ] Visual idea network graph
- [ ] Idea clustering algorithm
- [ ] Temporal idea tracking

### [1.2.0] — Planned
- [ ] User feedback loop for relationship accuracy
- [ ] Custom relationship types
- [ ] Idea templates library
- [ ] Import from other tools (Roam, Notion)

### [2.0.0] — Planned
- [ ] Python rewrite for performance
- [ ] Semantic similarity using embeddings
- [ ] Collaborative idea sharing
- [ ] Mobile app integration

---

## Release Process

1. Update CHANGELOG.md
2. Update version in SKILL.md frontmatter
3. Run test suite (A/B/C)
4. Git commit with version tag
5. Create release notes

## Contributing

When adding features:
1. Update SKILL.md documentation
2. Add tests to test suite
3. Update user guide
4. Update API reference if needed
5. Add changelog entry

---

## Notes

### Version Numbering
- **MAJOR**: Breaking changes (e.g., new trigger format)
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, documentation updates

### Backward Compatibility
We maintain backward compatibility for:
- Trigger words ("想法", "idea", etc.)
- Output file format
- Basic workflow

Breaking changes will be announced in MAJOR releases.

---

*Created with Enhanced Skill Creator*
*Part of PKM-VERSE system*
