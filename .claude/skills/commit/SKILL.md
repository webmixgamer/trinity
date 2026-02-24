---
name: commit
description: Commit, push, and link to GitHub Issues
allowed-tools: [Bash]
user-invocable: true
---

# Commit

Commit changes and link to relevant GitHub Issues.

## Usage

```
/commit [message]
/commit closes #17
/commit fixes #23 - added validation
```

## Process

### Step 1: Check Status

```bash
git status
git diff --stat
```

### Step 2: Stage Changes

Stage specific files (avoid `.env`, credentials):
```bash
git add <files>
```

### Step 3: Commit with Issue Reference

Include issue reference in commit message when applicable:
- `Closes #N` - closes issue when merged
- `Fixes #N` - closes issue (for bugs)
- `Refs #N` - references without closing

```bash
git commit -m "$(cat <<'EOF'
<type>: <description>

<optional body>

Closes #N

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### Step 4: Push

```bash
git push
```

### Step 5: Verify Issue Updated

```bash
gh issue view <N> --json state,title
```

## Commit Types

| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change (no new feature/fix) |
| `docs` | Documentation |
| `chore` | Maintenance |
