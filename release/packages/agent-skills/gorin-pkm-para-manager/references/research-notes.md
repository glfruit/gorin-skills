# PARA Method Reference

## Overview

PARA is a productivity framework by Tiago Forte for organizing digital information into four categories.

## The Four Categories

### Projects
- Short-term efforts with specific goals and deadlines
- Examples: "Launch website", "Write report", "Plan vacation"
- Has a clear end state and success criteria

### Areas
- Long-term responsibilities to maintain over time
- Examples: "Health", "Career", "Finances", "Family"
- Ongoing with no end date, have standards to maintain

### Resources
- Topics or interests that may be useful in the future
- Examples: "Machine Learning", "Cooking", "Productivity"
- Reference material and learning resources

### Archives
- Inactive items from Projects, Areas, or Resources
- Completed projects and former responsibilities

## Directory Structure

```
Efforts/
├── 1-Projects/
│   ├── Active/      # Currently working on
│   ├── Simmering/   # Paused, waiting for right time
│   ├── Sleeping/    # Long-term hold
│   └── Done/        # Completed
└── 2-Areas/
    └── [Area directories]/
```

## Project Metadata

```yaml
---
title: Project Name
deadline: 2025-03-15
progress: 75
area: Career
status: active
---
```

## Area Metadata

```yaml
---
title: Health
standard: Exercise 3x/week, Sleep 8hrs
lastReviewed: 2025-02-15
---
```

## Weekly Review Process

1. Review Active Projects - Check progress and blockers
2. Check Simmering Projects - Any ready to activate?
3. Review Areas - Are maintenance standards met?
4. Update Statuses - Move completed/stalled projects

## References

- Building a Second Brain by Tiago Forte
- https://fortelabs.com/blog/para/
