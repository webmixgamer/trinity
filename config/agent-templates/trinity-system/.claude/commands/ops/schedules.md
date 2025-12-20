# Schedule Overview

List all schedules across all agents with their status and next run times.

## Instructions

1. **Get all agents** using `mcp__trinity__list_agents`

2. **For each agent, note**:
   - Whether it has schedules
   - If agent is running (schedules won't run on stopped agents)

3. **Compile schedule information**:
   - Agent name
   - Schedule name
   - Cron expression (human-readable)
   - Enabled/Disabled status
   - Next run time
   - Last run time and status

4. **Generate the report**:

```
## Schedule Overview
Generated: {timestamp}

### Summary
- Total Schedules: X
- Enabled: X
- Disabled: X
- Agents with Schedules: X

### Upcoming Runs (Next 24 Hours)
| Time | Agent | Schedule | Cron |
|------|-------|----------|------|
| ... | ... | ... | ... |

### All Schedules by Agent

#### {Agent Name}
| Schedule | Cron | Status | Next Run | Last Run |
|----------|------|--------|----------|----------|
| ... | ... | ... | ... | ... |

### Warnings
- {List any issues, like schedules on stopped agents}
```

## Notes

- Group schedules by agent for clarity
- Highlight schedules that haven't run recently
- Warn about schedules on stopped agents
- Show human-readable cron descriptions (e.g., "Every day at 9 AM")
