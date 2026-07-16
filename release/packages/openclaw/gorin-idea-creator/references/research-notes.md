# Research Notes — Idea Management

## Research Findings

### 1. Best Practices for Idea Capture

**Sources**:
- Zettelkasten method (Luhmann)
- Building a Second Brain (Fort)
- GTD methodology (Allen)

**Key Insights**:
- Capture immediately when idea strikes
- One idea per note
- Use fleeting notes for temporary storage
- Review and process regularly
- Convert valuable ideas to permanent notes

### 2. Relationship Discovery Methods

**Keyword-based matching**:
- Extract nouns and verbs
- Remove stop words
- TF-IDF weighting
- Cosine similarity

**Semantic similarity**:
- Word embeddings
- Sentence transformers
- Clustering algorithms

**Network-based discovery**:
- Existing link analysis
- Graph traversal
- Community detection

### 3. Relationship Types Research

Based on argumentation theory and knowledge graphs:

| Type | Ontology | Example |
|------|----------|---------|
| Supports | `supports`, `confirms`, `evidence_for` | A supports B |
| Contradicts | `contradicts`, `refutes`, `evidence_against` | A contradicts B |
| Related | `related_to`, `see_also`, `similar` | A related to B |
| Extends | `extends`, `develops`, `specializes` | A extends B |
| Cluster | `same_cluster`, `similar_topic` | A and B in cluster |

### 4. Implementation Patterns

**Obsidian plugins**:
- Graph Analysis
- Dataview
- Related Notes
- Smart Random Note

**External tools**:
- Roam Research (block references)
- Notion (relation properties)
- Logseq (outliner + links)
- Tana (supertags + fields)

## Technical Considerations

### Performance
- Index notes for fast search
- Cache keyword extractions
- Batch relationship calculations
- Async processing for large vaults

### Accuracy
- Stemming for keyword matching
- Synonym expansion
- Context-aware similarity
- User feedback loop

### User Experience
- Minimal friction for capture
- Clear relationship visualization
- Easy navigation between ideas
- Flexible relationship editing

## Design Decisions

### 1. Trigger Word: "想法"
**Rationale**: 
- Natural in Chinese context
- Short and memorable
- Distinct from other commands
- Culturally appropriate

### 2. Save Location: Zettels/1-Fleeting/
**Rationale**:
- Follows PKM-VERSE structure
- Separate from permanent notes
- Easy to review and process
- Aligns with Zettelkasten method

### 3. Relationship Types: 5 categories
**Rationale**:
- Covers most use cases
- Not too many to overwhelm
- Clear semantic meaning
- Extensible if needed

## Future Enhancements

1. **ML-based classification**: Train model on user feedback
2. **Visual graph**: Interactive idea network
3. **Idea clustering**: Automatic group formation
4. **Temporal analysis**: Track idea evolution over time
5. **Collaborative filtering**: Suggest based on similar users

---
*Research conducted for idea-creator skill*
*Date: 2026-02-21*
