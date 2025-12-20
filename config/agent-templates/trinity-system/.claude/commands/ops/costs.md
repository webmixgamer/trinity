# Cost Report

Generate a cost report using OpenTelemetry metrics (if enabled).

## Instructions

1. **Check if OTel is enabled**:
   - This report requires OTel metrics to be enabled
   - If not enabled, inform the user

2. **Gather cost data**:
   - Total platform cost
   - Cost by model (Claude Sonnet, Claude Haiku, etc.)
   - Token usage breakdown

3. **Generate the report**:

```
## Platform Cost Report
Generated: {timestamp}

### Summary
- Total Cost: ${X.XX} USD
- Total Tokens: {X,XXX,XXX}
- Input Tokens: {X,XXX,XXX}
- Output Tokens: {X,XXX,XXX}

### Cost by Model
| Model | Cost | Input Tokens | Output Tokens |
|-------|------|--------------|---------------|
| claude-sonnet | $X.XX | X,XXX | X,XXX |
| claude-haiku | $X.XX | X,XXX | X,XXX |

### Productivity Metrics
- Sessions: X
- Active Time: X hours
- Commits: X
- PRs Created: X
- Lines Added: X
- Lines Removed: X

### Notes
{Any observations or recommendations}
```

## If OTel Not Enabled

```
## Cost Report Unavailable

OpenTelemetry metrics are not enabled on this platform.

To enable cost tracking:
1. Set `OTEL_ENABLED=1` in your environment
2. Deploy the OTel collector service
3. Restart agents to begin collecting metrics

See docs/DEPLOYMENT.md for setup instructions.
```

## Notes

- Cost data comes from the platform's observability system
- Per-agent cost attribution requires agent-level metrics (future feature)
- Historical cost data requires Prometheus/Grafana integration
