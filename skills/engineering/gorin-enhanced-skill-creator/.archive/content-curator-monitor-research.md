# Content Curator Monitor - Research Report

## Executive Summary

This research document covers best practices for AI agents to monitor multiple information sources (Hacker News, X/Twitter, RSS feeds, Bear Notes, Obsidian) for content curation. It provides architecture patterns, data flow designs, model integration approaches, trigger designs, and output formats based on existing OpenClaw skills and PARA method integration.

---

## 1. Architecture Patterns

### 1.1 Multi-Source Monitoring Pipeline

The core architecture follows a 5-stage pipeline pattern:

```
Configure Sources → Fetch Content → AI Analysis → Generate Briefs → Export to Mission Control
```

**Key Components:**

| Component | Responsibility | Implementation |
|-----------|---------------|----------------|
| Source Adapter | Normalize data from different sources | Per-source TypeScript modules |
| Content Fetcher | Concurrent fetching with rate limiting | Parallel execution (10 concurrent, 15s timeout) |
| AI Analyzer | Score, categorize, summarize | Model API calls (Kimi, OpenAI, etc.) |
| Brief Generator | Create structured topic briefs | Template-based Markdown generation |
| Export Handler | Save to Mission Control/Notion | REST API or file system |

### 1.2 Source Integration Patterns

**Information Sources Supported:**

1. **Hacker News (90 blogs)**
   - RSS feed aggregation
   - Categories: AI/ML, Security, Engineering, Tools, Opinion
   - Update frequency: Daily

2. **X/Twitter**
   - API-based trending topics
   - Monitored accounts list
   - Hashtag tracking

3. **Bear Notes**
   - Database scanning for underdeveloped ideas
   - Theme identification
   - Expansion potential detection

4. **Obsidian Vault**
   - Zettelkasten note connections
   - Tags: #idea, #WIP, #expand
   - Recent modifications tracking

5. **RSS Feeds**
   - Custom subscription management
   - Configurable update frequency

6. **Zhihu (Chinese)**
   - Trending questions
   - Expert opinions

### 1.3 Two-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer                              │
│  (Pepper - Topic Curator / Content Creation Team)          │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Skill Layer                                 │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │content-curator- │  │   hn-daily-digest│                │
│  │    monitor      │  │                  │                │
│  └────────┬────────┘  └────────┬────────┘                │
│           │                    │                          │
│  ┌────────▼────────┐  ┌────────▼────────┐                │
│  │  pkm-save-note  │  │ pkm-para-manager│                │
│  └──────────────────┘  └─────────────────┘                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Data Layer                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Bear DB   │  │  Obsidian  │  │   RSS/HN   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Design

### 2.1 Input Flow

```
User Trigger (Telegram/Discord)
         │
         ▼
   Parse Parameters
   - Source selection
   - Time window
   - Content pillars
         │
         ▼
   Validate Sources
   - Check API keys
   - Verify connectivity
         │
         ▼
   Initialize Fetchers
```

### 2.2 Processing Flow

```typescript
// Parallel Fetch with Rate Limiting
const sources = ['hn', 'x', 'bear', 'obsidian', 'rss'];
const results = await Promise.allSettled(
  sources.map(source => fetchWithTimeout(source, 15000))
);

// Filter by Time Window
const filtered = results
  .filter(article => isWithinTimeWindow(article.date, timeRange))
  .filter(article => meetsQualityThreshold(article));

// AI Scoring Pipeline
const scored = await Promise.all(
  filtered.map(article => aiScore(article, {
    relevance: 1-10,
    quality: 1-10,
    timeliness: 1-10,
    trendPotential: 1-10
  }))
);

// Categorization
const categorized = scored.map(article => ({
  ...article,
  category: classifyCategory(article), // AI/ML, Security, Engineering, etc.
  pillar: matchContentPillar(article)   // PKM, AI, Dev, Tech-Culture, EdTech, Growth
}));
```

### 2.3 Output Flow

```
Generate Topic Briefs
         │
         ▼
   Save to Mission Control
   - Create task
   - Assign priority
   - Link to source
         │
         ▼
   Notify Director (Tony)
         │
         ▼
   Queue for Content Team
```

---

## 3. Model Integration Approaches

### 3.1 OpenClaw Agent System vs Direct API Calls

**Option A: Direct API Calls (Recommended for Simple Tasks)**

```typescript
// Direct API call for scoring
const score = await fetch('https://api.moonshot.cn/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${process.env.KIMI_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'kimi-coding/k2p5',
    messages: [
      { role: 'system', content: 'You are a content curator.' },
      { role: 'user', content: `Score this article: ${article}` }
    ]
  })
});
```

**Option B: OpenClaw Agent System (Recommended for Complex Workflows)**

```typescript
// Spawn sub-agent for deep research
const researcher = await sessions_spawn({
  agentId: 'researcher',
  model: 'qwen3-max',
  description: 'Research topic brief',
  context: {
    task: 'deep_dive',
    topic: brief.title,
    sources: brief.sources
  }
});
```

**Decision Matrix:**

| Scenario | Approach | Reason |
|----------|----------|--------|
| Simple scoring/categorization | Direct API | Lower latency, simpler error handling |
| Topic brief generation | Direct API | Structured output, deterministic |
| Deep research | Agent System | Complex reasoning, multi-step |
| Cross-referencing knowledge | Agent System | Tool access, memory |
| Real-time monitoring | Hybrid | API for filtering, agents for analysis |

### 3.2 Model Selection Strategy

Based on subagent model selection priority (from memory):

1. **Explicit specification** in sessions_spawn
2. **Parent agent's subagents.model** config
3. **Global default** model
4. **Inheritance** from parent agent's current model

**Recommended Models:**

| Task | Model | Quota Priority |
|------|-------|----------------|
| Content scoring | qwen3-max | High |
| Brief generation | kimi-coding/k2p5 | High |
| Deep research | qwen3-max | Medium |
| Summarization | glm-4.7 | Medium |
| Translation | qwen3-max | Low |

### 3.3 API Quota Management

**Strategy: Split Content Tasks**

- Content development → qwen3-max (high quota)
- Assessment tasks → qwen3-max (medium quota)
- Lab tasks → glm-4.7 (specific quota)

---

## 4. Trigger Design

### 4.1 Manual Triggers

| Command | Description | Example |
|---------|-------------|---------|
| `/curator-scan` | Full scan all sources | `/curator-scan` |
| `/curator-scan --source hn` | Single source | `/curator-scan --source hn` |
| `/curator-scan --sources hn,x` | Multiple sources | `/curator-scan --sources hn,x,bear` |
| `/curator-scan --hours 12` | Custom time window | `/curator-scan --hours 12` |

### 4.2 Scheduled Triggers (Cron)

```bash
# Daily morning scan (recommended: 6-7 AM)
0 6 * * * curl -X POST http://localhost:18789/tasks -d '{"skill":"content-curator-monitor","action":"scan"}'

# Evening trend check (recommended: 6-7 PM)
0 18 * * * curl -X POST http://localhost:18789/tasks -d '{"skill":"content-curator-monitor","action":"scan","sources":["x","hn"]}'
```

### 4.3 Event-Based Triggers

```
New RSS Feed Entry → Trigger HN/RSS fetcher
New Bear Note (tag: #idea) → Trigger idea extraction
Obsidian Vault Change → Trigger Zettelkasten analysis
```

### 4.4 Natural Language Triggers

| Trigger Phrase | Action |
|----------------|--------|
| "Scan information sources" | Full scan |
| "Monitor feeds for today" | Today's content |
| "Find content topics" | Generate briefs |
| "Generate topic briefs" | Brief creation |
| "Curate daily content" | Full pipeline |
| "Check HN, X, and RSS" | Multi-source scan |

---

## 5. Output Formats

### 5.1 Topic Brief Format

```markdown
## Topic Brief: {Title}

**Source**: {HN/X/Bear/Obsidian/RSS/Zhihu}
**Category**: {pkm|ai-learning|dev|tech-culture|edtech|personal-growth}
**Priority**: {urgent|high|normal|low}
**Suggested Platform**: {Bear Blog|Zhihu|X|Medium}

**Why Now**:
- Trend indicator or timely relevance

**Key Points**:
1. Main insight
2. Supporting evidence
3. Counter-perspective (if any)

**Content Angle**:
Suggested approach for our audience

**Related Sources**:
- [Source 1](link)
- [Source 2](link)

**Recommended Action**:
Approve for research → Assign to JARVIS
```

### 5.2 Digest Format (HN/HK Daily)

```markdown
## 📝 Today's Highlights
[3-5 sentence trend summary]

## 🏆 Must Read Top 3
[Full details with Chinese titles]

## 📊 Data Overview
- Category distribution
- Keyword frequency
- Source statistics

## 📰 Full Article List
[Grouped by category]
```

### 5.3 Mission Control Export Format

```json
{
  "task": {
    "id": "topic-{timestamp}",
    "title": "{Brief Title}",
    "team_id": "content-squad",
    "status": "pending_review",
    "priority": "high",
    "metadata": {
      "source": "hn",
      "category": "ai-learning",
      "url": "{original_url}",
      "score": 8.5,
      "pillar": "AI"
    }
  }
}
```

---

## 6. PARA Method Integration

### 6.1 Content-to-PARA Mapping

| Content Type | PARA Location | Trigger |
|--------------|---------------|---------|
| Research findings | Projects/{project}/ | Topic approved |
| Trend analysis | Areas/Content/ | Weekly digest |
| Raw ideas | Areas/Ideas/ | New topic found |
| Brief drafts | Areas/Drafts/ | Pre-approval |
| Published content | Areas/Archive/ | After publishing |

### 6.2 Zettelkasten Integration

```typescript
// Auto-link to existing notes
const relatedNotes = await findRelated({
  content: brief.content,
  threshold: 0.7,  // Strong relevance
  vault: obsidianVault
});

// Create atomic note for key insight
const zettel = {
  id: generateTimestampID(),
  title: brief.keyInsight,
  tags: ['topic-brief', brief.category, ...brief.pillars],
  related: relatedNotes.map(n => `[[${n.id} ${n.title}]]`),
  source: brief.sourceUrl,
  para: {
    project: detectProject(brief),
    area: detectArea(brief)
  }
};
```

### 6.3 Content Pillars Mapping

| Source | PKM | AI | Dev | Tech-Culture | EdTech | Growth |
|--------|-----|-----|-----|--------------|--------|--------|
| HN | ⚡ | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ | ⚡ | ⚡ |
| X | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ | ⚡⚡⚡ |
| Bear | ⚡⚡⚡ | ⚡⚡ | ⚡ | ⚡ | ⚡ | ⚡⚡ |
| Obsidian | ⚡⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡⚡⚡ |
| RSS | ⚡⚡ | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ |
| Zhihu | ⚡⚡ | ⚡⚡⚡ | ⚡ | ⚡⚡ | ⚡⚡⚡ | ⚡⚡⚡ |

---

## 7. Common Mistakes & Best Practices

### 7.1 Common Mistakes

| Mistake | Why It Fails | Correct Approach |
|---------|--------------|------------------|
| Monitor too many sources | Information overload, low quality | Focus on top 3-4 sources per scan |
| Skip AI analysis | Miss trend patterns and relevance | Always use AI scoring |
| Generate briefs without context | Topics don't fit content strategy | Match against content pillars |
| Export without review queue | Overwhelm Director with choices | Limit to top 5-10 topics |
| No PARA integration | Lost connection to knowledge base | Always link to existing notes |

### 7.2 Best Practices

1. **Incremental Scanning**
   - Start with 3-4 key sources
   - Expand gradually based on team capacity

2. **Quality Over Quantity**
   - Set minimum score threshold (≥7.0)
   - Limit to top 10 topics per scan

3. **Human-in-the-Loop**
   - Director reviews before research assignment
   - Weekly calibration sessions

4. **Feedback Loop**
   - Track topic-to-publication conversion rate
   - Adjust scoring model based on outcomes

5. **PARA First**
   - Always check existing Projects/Areas before creating new
   - Link briefs to existing knowledge structure

---

## 8. Integration with OpenClaw Team Workflow

### 8.1 Team Roles

```
Pepper (Curator)
    ↓ curator-scan
Generate topic briefs
    ↓ Submit to Tony
Director reviews & approves
    ↓ Assign to JARVIS
Researcher deep dives
    ↓ Deliver to Maya
Writer creates content
    ↓ Alex edits → Piper publishes
```

### 8.2 Mission Control Schema

```sql
-- Tasks table for topic briefs
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  team_id TEXT REFERENCES teams(id),
  status TEXT DEFAULT 'pending',
  priority TEXT DEFAULT 'normal',
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Handoffs for team transfers
CREATE TABLE handoffs (
  id SERIAL PRIMARY KEY,
  task_id TEXT REFERENCES tasks(id),
  from_team_id TEXT REFERENCES teams(id),
  to_team_id TEXT REFERENCES teams(id),
  content TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 9. Technical Recommendations

### 9.1 Configuration

```typescript
interface CuratorConfig {
  // API Keys
  kimiApiKey?: string;
  xBearerToken?: string;
  
  // Source Paths
  bearDbPath?: string;
  obsidianVaultPath?: string;
  rssFeedList?: string[];
  
  // Processing
  maxConcurrentSources: number;  // Default: 10
  fetchTimeoutMs: number;         // Default: 15000
  minScoreThreshold: number;      // Default: 7.0
  maxBriefsPerScan: number;       // Default: 10
  
  // Time Windows
  defaultTimeRangeHours: number; // Default: 24
  minTimeRangeHours: number;      // Default: 12
  
  // Output
  outputFormat: 'markdown' | 'mission-control' | 'notion';
  notifyOnComplete: boolean;
}
```

### 9.2 Error Handling

| Error Type | Handling Strategy |
|------------|------------------|
| Source timeout | Skip, continue with others |
| API rate limit | Exponential backoff, queue for retry |
| Invalid API key | Notify user, skip AI features |
| No articles found | Expand time range, notify user |
| Model failure | Fallback to simpler prompt, then skip |

---

## 10. Conclusion

The content curation system should be built on:

1. **Modular Architecture** - Separate fetchers, analyzers, and generators
2. **Hybrid Model Integration** - Direct API for simple tasks, agents for complex workflows
3. **PARA-Native Design** - Always link to existing knowledge structure
4. **Human-in-the-Loop** - Director approval before research
5. **Quality Thresholds** - Minimum scores to prevent noise
6. **Feedback Mechanisms** - Track conversion rates for continuous improvement

---

## References

- content-curator-monitor/SKILL.md
- hn-daily-digest/SKILL.md
- hk-daily-digest/SKILL.md
- pkm-para-manager/SKILL.md
- zk-para-zettel/SKILL.md
- pkm-save-note/SKILL.md
- idea-pipeline/SKILL.md

---

*Research completed: 2026-03-01*
*Saved to: ~/.openclaw/skills/enhanced-skill-creator/research/content-curator-monitor-research.md*
