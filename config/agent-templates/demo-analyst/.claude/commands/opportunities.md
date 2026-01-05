---
description: List and rank all identified opportunities
allowed-tools: Read, Glob
---

# Opportunities Analysis

Compile and rank all opportunities identified across research findings.

## Steps

1. **Gather All Findings**
   - Read all files from `/home/developer/shared-in/research-network-researcher/findings/`
   - Extract every opportunity mentioned

2. **Compile Opportunities**
   - List each unique opportunity
   - Note which research cycle identified it
   - Track if it appears multiple times (indicates importance)

3. **Score Each Opportunity**
   Rate on three dimensions:
   - **Potential Impact**: High (transformative), Medium (significant), Low (incremental)
   - **Effort Required**: High (major investment), Medium (moderate), Low (quick win)
   - **Timing**: Now (urgent), Soon (within months), Later (long-term)

4. **Rank and Prioritize**
   - Calculate priority score: High Impact + Low Effort = Higher Priority
   - Sort by priority
   - Flag top 3 as "recommended focus"

5. **Output Report**

```markdown
# Opportunity Analysis

**Analysis Date**: [DATE]
**Research Cycles Reviewed**: [count]

## Top Recommendations (Focus Here)

### 1. [Opportunity Name]
- **Potential**: High/Medium/Low
- **Effort**: High/Medium/Low
- **Timing**: Now/Soon/Later
- **Why**: [Brief rationale]
- **First seen**: [Date]
- **Mentions**: [count]

### 2. [Opportunity Name]
...

### 3. [Opportunity Name]
...

## All Opportunities

| Rank | Opportunity | Potential | Effort | Timing | Mentions |
|------|-------------|-----------|--------|--------|----------|
| 1 | ... | ... | ... | ... | ... |

## Patterns Observed
- [Any patterns in types of opportunities]
- [Industries or areas with most opportunity]
```

Generate the opportunities report now.
