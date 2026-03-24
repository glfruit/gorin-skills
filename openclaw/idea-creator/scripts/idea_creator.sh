#!/bin/bash
# idea_creator.sh — Idea Management Script
# Part of idea-creator skill for PKM-VERSE

set -e

# Configuration
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-${VAULT_PATH:-/Users/gorin/Workspace/PKM/octopus}}"
FLEETING_DIR="$VAULT_PATH/Zettels/1-Fleeting"
PERMANENT_DIR="$VAULT_PATH/Zettels/3-Permanent"
AREAS_DIR="$VAULT_PATH/Efforts/2-Areas"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Extract keywords from text
extract_keywords() {
    local text="$1"
    # Simple keyword extraction: remove common words, keep nouns/concepts
    echo "$text" | tr ' ' '\n' | \
        grep -v -E "^(的|是|在|和|或|与|这|那|我|你|他|她|它|们|这个|那个|一个|可以|应该|需要|能够|会|要|有|没有|不|没|了|着|过|的|地|得|之|而|于|被|把|让|给|为|对|向|从|到|比|跟|同|被|把)$" | \
        grep -v "^[[:punct:]]*$" | \
        sort | uniq | \
        head -5 | \
        tr '\n' ' '
}

# Search for related notes
search_related() {
    local keyword="$1"
    local dir="$2"
    local max_results="${3:-3}"
    
    if [ -d "$dir" ]; then
        grep -l "$keyword" "$dir"/*.md 2>/dev/null | head -$max_results
    fi
}

# Determine relationship type
determine_relation() {
    local idea_file="$1"
    local note_file="$2"
    
    # Simple heuristic based on content similarity
    # In production, this would use more sophisticated NLP
    local similarity=$(grep -c -f <(grep -o '\w\+' "$idea_file" | sort | uniq) "$note_file" 2>/dev/null || echo 0)
    
    if [ "$similarity" -gt 3 ]; then
        echo "supports"
    elif [ "$similarity" -gt 1 ]; then
        echo "related"
    else
        echo "reference"
    fi
}

# Generate relationship links
generate_relationships() {
    local idea_title="$1"
    local idea_content="$2"
    local temp_file=$(mktemp)
    
    log_info "Searching for related notes..."
    
    # Extract keywords
    local keywords=$(extract_keywords "$idea_title $idea_content")
    log_info "Keywords: $keywords"
    
    # Search in different directories
    local all_notes=""
    
    for keyword in $keywords; do
        # Search permanent notes
        local permanent_notes=$(search_related "$keyword" "$PERMANENT_DIR" 2)
        all_notes="$all_notes $permanent_notes"
        
        # Search other ideas
        local idea_notes=$(search_related "$keyword" "$FLEETING_DIR" 2)
        all_notes="$all_notes $idea_notes"
        
        # Search areas
        local area_notes=$(search_related "$keyword" "$AREAS_DIR" 1)
        all_notes="$all_notes $area_notes"
    done
    
    # Remove duplicates and empty lines
    all_notes=$(echo "$all_notes" | tr ' ' '\n' | sort | uniq | grep -v '^$')
    
    # Generate links
    local links=""
    local count=0
    
    for note in $all_notes; do
        if [ -f "$note" ] && [ $count -lt 10 ]; then
            local basename=$(basename "$note" .md)
            # Skip if it's the current idea itself
            if [[ "$basename" != *"$idea_title"* ]]; then
                links="${links}- [[$basename]]\n"
                count=$((count + 1))
            fi
        fi
    done
    
    echo -e "$links"
    rm -f "$temp_file"
}

# Create idea note
create_idea_note() {
    local title="$1"
    local content="$2"
    local tags="${3:-general}"
    
    # Generate timestamp
    local timestamp=$(date +%Y%m%d%H%M)
    local filename="$timestamp $title.md"
    local filepath="$FLEETING_DIR/$filename"
    
    # Check if fleeting directory exists
    if [ ! -d "$FLEETING_DIR" ]; then
        log_error "Fleeting directory not found: $FLEETING_DIR"
        exit 1
    fi
    
    log_info "Creating idea note: $filename"
    
    # Generate relationships
    local relationships=$(generate_relationships "$title" "$content")
    
    # Create note content
    cat > "$filepath" << EOF
---
id: $timestamp
title: $title
tags:
  - idea
  - fleeting
  - $tags
created: $(date +"%Y-%m-%d %H:%M")
status: fleeting
---

# Idea: $title

## Core Concept
$content

## Description
[Detailed description to be added...]

## Trigger Context
[When/where did this idea emerge?]

## Related Thoughts
$relationships

## Questions to Explore
- [ ] 

## Next Actions
- [ ] Deep thinking
- [ ] Research more
- [ ] Develop into permanent note

## Metadata
- **Source**: 
- **Mood**: 
- **Importance**: ⭐⭐⭐⭐⭐
- **Urgency**: High/Medium/Low
EOF

    log_success "Idea saved to: $filepath"
    
    # Output summary
    echo ""
    echo "💡 Idea Captured!"
    echo "=================="
    echo "File: $filepath"
    echo ""
    if [ -n "$relationships" ]; then
        echo "Related notes found:"
        echo -e "$relationships"
    else
        echo "No related notes found yet."
    fi
    
    return 0
}

# Main function
main() {
    # Parse arguments
    local title="$1"
    local content="$2"
    local tags="$3"
    
    if [ -z "$title" ]; then
        log_error "Usage: $0 \"Idea Title\" [\"Description\"] [tags]"
        exit 1
    fi
    
    log_info "Idea Creator - PKM-VERSE"
    log_info "Vault: $VAULT_PATH"
    
    create_idea_note "$title" "$content" "$tags"
}

# Run main function
main "$@"
