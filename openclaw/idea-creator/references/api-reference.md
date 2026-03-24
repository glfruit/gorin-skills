# API Reference — Idea Creator

## Command Line Interface

### Main Script
```bash
scripts/idea_creator.sh "Title" ["Content"] [tags]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Title` | string | Yes | Idea title (will be part of filename) |
| `Content` | string | No | Detailed description |
| `Tags` | string | No | Comma-separated tags |

### Examples

**Basic**:
```bash
./idea_creator.sh "AI should assist humans"
```

**With content**:
```bash
./idea_creator.sh "Remote work best practices" \
    "Async communication is more efficient than meetings..."
```

**With tags**:
```bash
./idea_creator.sh "Digital transformation" \
    "It's about paradigm shift, not technology..." \
    "transformation,business,strategy"
```

## Functions

### `extract_keywords(text)`
Extracts keywords from text for searching.

**Input**: Text string
**Output**: Space-separated keywords
**Example**:
```bash
keywords=$(extract_keywords "AI assisted programming tools")
# Output: "AI assisted programming tools"
```

### `search_related(keyword, directory, max_results)`
Searches for notes containing keyword.

**Parameters**:
- `keyword`: Search term
- `directory`: Directory to search
- `max_results`: Maximum results (default: 3)

**Output**: List of file paths

### `determine_relation(idea_file, note_file)`
Determines relationship type between idea and note.

**Algorithm**:
1. Calculate keyword overlap
2. If overlap > 3: "supports"
3. If overlap > 1: "related"
4. Otherwise: "reference"

**Output**: Relationship type string

### `generate_relationships(title, content)`
Generates relationship links for an idea.

**Process**:
1. Extract keywords
2. Search in all directories
3. Deduplicate results
4. Format as markdown links

**Output**: Markdown-formatted links

### `create_idea_note(title, content, tags)`
Creates the idea note file.

**Side Effects**:
- Creates file in `Zettels/1-Fleeting/`
- Generates timestamp
- Searches for relationships
- Writes note with template

**Output**: File path and summary

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `/Users/gorin/Workspace/PKM/octopus` | Path to Obsidian vault |
| `FLEETING_DIR` | `$VAULT_PATH/Zettels/1-Fleeting` | Fleeting notes directory |
| `PERMANENT_DIR` | `$VAULT_PATH/Zettels/3-Permanent` | Permanent notes directory |
| `AREAS_DIR` | `$VAULT_PATH/Efforts/2-Areas` | Areas directory |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Missing parameters |
| 2 | Directory not found |
| 3 | File creation failed |

## Integration

### With Obsidian
```bash
# Create idea from Obsidian URI
obsidian://idea-creator?title=My%20Idea&content=Description
```

### With Alfred
```bash
# Alfred workflow
query="{query}"
./idea_creator.sh "$query"
```

### With Keyboard Maestro
```applescript
tell application "Keyboard Maestro Engine"
    do script "Idea Creator"
end tell
```

## File Format

### Output Note Structure
```markdown
---
id: YYYYMMDDHHMM
title: [Title]
tags:
  - idea
  - fleeting
  - [custom tags]
created: YYYY-MM-DD HH:MM
status: fleeting
---

# Idea: [Title]

## Core Concept
[Content]

## Description
...

## Related Thoughts
- [[Note1]] — supports: ...
- [[Note2]] — contradicts: ...

## Questions to Explore
- [ ] 

## Next Actions
- [ ] 

## Metadata
...
```

## Extending

### Add Custom Relationship Types

Edit `determine_relation()` function:
```bash
determine_relation() {
    local similarity=$(calculate_similarity "$1" "$2")
    
    if [ "$similarity" -gt 80 ]; then
        echo "strong_support"
    elif [ "$similarity" -gt 50 ]; then
        echo "supports"
    elif [ "$similarity" -lt 20 ]; then
        echo "contradicts"
    else
        echo "related"
    fi
}
```

### Custom Search Directories

Add to `generate_relationships()`:
```bash
# Search custom directory
local custom_notes=$(search_related "$keyword" "$CUSTOM_DIR" 2)
all_notes="$all_notes $custom_notes"
```

### Post-Processing Hook

Add after `create_idea_note()`:
```bash
# Custom post-processing
if [ -f "$HOOK_SCRIPT" ]; then
    "$HOOK_SCRIPT" "$filepath"
fi
```

## Testing

### Unit Tests
```bash
# Test keyword extraction
test_extract_keywords() {
    result=$(extract_keywords "AI assisted programming")
    assert "$result" = "AI assisted programming"
}

# Test relationship determination
test_determine_relation() {
    result=$(determine_relation "idea.md" "note.md")
    assert "$result" = "supports"
}
```

### Integration Tests
```bash
# Full workflow test
./idea_creator.sh "Test Idea" "Test content" "test"
assert_file_exists "$FLEETING_DIR/*Test Idea.md"
```

## Performance

### Benchmarks
- Keyword extraction: ~10ms
- Search (1000 notes): ~100ms
- Full creation: ~500ms

### Optimization Tips
1. Use SSD for vault storage
2. Limit max_results for faster search
3. Cache keyword extractions
4. Batch process multiple ideas

---
*API Version 1.0*
