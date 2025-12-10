# List All Workplans

List all workplans (active and archived).

## Usage

```
/workplan-list [--all | --active | --archived]
```

Default: shows active workplans only

## Instructions

1. Scan `plans/active/` for active workplans
2. Optionally scan `plans/archive/` for completed workplans
3. Display summary for each workplan

## Output Format

```
Active Workplans (plans/active/):
  ID                        Name                    Progress    Status
  plan-1733400000-abc123   implement-auth          2/5         active
  plan-1733400100-def456   refactor-api            0/3         paused

Archived Workplans (plans/archive/):
  plan-1733300000-ghi789   fix-login-bug           3/3         completed
  plan-1733200000-jkl012   update-docs             5/5         completed
```

## Filtering

- `--active`: Only show active workplans (default)
- `--archived`: Only show archived workplans
- `--all`: Show both active and archived
