# AI Venture Capital Due Diligence System

> **"9 analysts. 60 seconds. One verdict."**

A multi-agent system that performs comprehensive startup due diligence in parallel, synthesizes findings, and delivers an investment recommendation — with one human approval gate.

**Fully local. No external services required.** All results stored in shared folders within Trinity.

## The Demo

**The Hook**: Provide a pitch deck link. Watch 9 AI analysts fan out simultaneously on the Dashboard Timeline. Each researches their domain in parallel. Findings converge. Investment Committee clicks once. Verdict delivered to dd-lead's shared folder.

**The Shock**: What takes a VC firm 2-4 weeks and costs $50K+ in analyst time happens in 60 seconds.

**The Viral Moment**: The Dashboard Timeline exploding with parallel agent activity — a living, breathing AI investment firm.

**The Deliverable**: All analysis saved to `dd-lead`'s shared folder — accessible via Trinity File Manager.

## Quick Start

### 1. Deploy the Agent Fleet

```bash
# Via API
curl -X POST http://localhost:8000/api/system-manifest \
  -H "Content-Type: application/yaml" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --data-binary @docs/demos/vc-due-diligence/system-manifest.yaml

# Or upload via UI: Settings → System Manifest
```

This deploys 11 agents:
- `dd-intake` - Pitch deck parser
- `dd-founder` - Founder background checks
- `dd-market` - Market research & validation
- `dd-competitor` - Competitive intelligence
- `dd-tech` - Technical due diligence
- `dd-bizmodel` - Business model analysis
- `dd-traction` - Traction & financials
- `dd-compliance` - Regulatory compliance
- `dd-captable` - Cap table analysis
- `dd-legal` - Legal review
- `dd-lead` - Deal lead synthesis

### 2. Create the Process

```bash
# Import the process template
curl -X POST http://localhost:8000/api/processes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "vc-due-diligence",
    "template": "vc-due-diligence"
  }'
```

### 3. Run Due Diligence

```bash
# Start a due diligence process
curl -X POST http://localhost:8000/api/processes/vc-due-diligence/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "company_name": "Acme AI Corp",
    "pitch_deck_url": "https://example.com/pitch.pdf",
    "funding_round": "Series A",
    "funding_ask": "$10M",
    "target_markets": ["US", "EU"],
    "additional_docs": "",
    "financial_docs": "",
    "cap_table": "",
    "legal_docs": ""
  }'
```

### 4. Watch the Magic

Open the Dashboard at `http://localhost` and watch:
1. Intake agent parses the pitch deck
2. 9 specialist agents fan out in parallel
3. Each researches their domain (visible on Timeline)
4. Deal Lead synthesizes all findings
5. Human approval notification appears in Trinity Approvals page
6. One click: APPROVE or REJECT

### 5. Retrieve Results

All deliverables are stored in **dd-lead's shared folder**:

```
dd-lead/shared-out/
├── investment-recommendation/
│   ├── investment_recommendation.json  # Full analysis
│   └── ic_briefing.md                  # Investment Committee briefing
└── final-report/
    ├── OUTCOME.md                      # Decision summary
    ├── investment_recommendation.json  # Copy of full analysis
    ├── ic_briefing.md                  # Copy of IC briefing
    └── term-sheet/                     # (if approved)
```

**Access via Trinity UI**:
- Go to **Agents** → **dd-lead** → **Files** tab → **shared-out/final-report/**
- Or use **File Manager** (`/files`) → Select **dd-lead**

## Architecture

```
                                    ┌─────────────────────┐
                                    │   PITCH DECK        │
                                    │   UPLOAD            │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   INTAKE AGENT      │
                                    │   Parse & Extract   │
                                    └──────────┬──────────┘
                                               │
                 ┌─────────────────────────────┼─────────────────────────────┐
                 │                             │                             │
    ┌────────────▼────────────┐  ┌────────────▼────────────┐  ┌────────────▼────────────┐
    │  FOUNDER    MARKET      │  │  COMPETITOR   TECH      │  │  BIZMODEL   TRACTION    │
    │  COMPLIANCE CAPTABLE    │  │  LEGAL                  │  │                         │
    └────────────┬────────────┘  └────────────┬────────────┘  └────────────┬────────────┘
                 │                             │                             │
                 └─────────────────────────────┴─────────────────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   DEAL LEAD AGENT   │
                                    │   Synthesize All    │
                                    │   Risk Score        │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   HUMAN APPROVAL    │
                                    │   Investment        │
                                    │   Committee         │
                                    └──────────┬──────────┘
                                               │
                              ┌────────────────┴────────────────┐
                              │                                 │
                   ┌──────────▼──────────┐           ┌──────────▼──────────┐
                   │   APPROVE           │           │   REJECT            │
                   │   → Term Sheet      │           │   → Rejection       │
                   │   → Final Report    │           │   → Final Report    │
                   └──────────┬──────────┘           └──────────┬──────────┘
                              │                                 │
                              └────────────────┬────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   dd-lead           │
                                    │   shared-out/       │
                                    │   final-report/     │
                                    └─────────────────────┘
```

**All results stored locally in Trinity shared folders. No external services required.**

## Agent Fleet Details

| Agent | Purpose | Resources |
|-------|---------|-----------|
| `dd-intake` | Parse pitch decks, extract structured data | 2GB / 1 CPU |
| `dd-founder` | Background checks, track record verification | 4GB / 2 CPU |
| `dd-market` | TAM/SAM/SOM validation, growth rates | 4GB / 2 CPU |
| `dd-competitor` | Competitive landscape, market share | 4GB / 2 CPU |
| `dd-tech` | Technology assessment, IP evaluation | 4GB / 2 CPU |
| `dd-bizmodel` | Revenue model, unit economics | 2GB / 1 CPU |
| `dd-traction` | Growth metrics, financial health | 4GB / 2 CPU |
| `dd-compliance` | Regulatory landscape, compliance | 2GB / 1 CPU |
| `dd-captable` | Equity structure, investor analysis | 2GB / 1 CPU |
| `dd-legal` | Corporate structure, IP ownership | 4GB / 2 CPU |
| `dd-lead` | Synthesis, risk scoring, recommendation | 8GB / 4 CPU |

**Total Resources**: ~40GB RAM, 20 CPUs

## Risk Scoring

The Deal Lead calculates an overall risk score (0-100) using weighted specialist scores:

| Area | Weight |
|------|--------|
| Founder/Team | 20% |
| Technology | 15% |
| Business Model | 15% |
| Traction | 15% |
| Market | 15% |
| Competition | 10% |
| Compliance | 5% |
| Cap Table | 3% |
| Legal | 2% |

**Recommendations**:
- **Strong Invest**: Risk 0-20
- **Invest**: Risk 21-35
- **Negotiate**: Risk 36-50
- **Pass**: Risk 51-70
- **Strong Pass**: Risk 71-100

## Files

```
docs/demos/vc-due-diligence/
├── README.md                    # This file
├── system-manifest.yaml         # Agent fleet deployment

config/agent-templates/
├── dd-intake/                   # Pitch deck parser
├── dd-founder/                  # Founder background check
├── dd-market/                   # Market research
├── dd-competitor/               # Competitive intelligence
├── dd-tech/                     # Technical due diligence
├── dd-bizmodel/                 # Business model analysis
├── dd-traction/                 # Traction & financials
├── dd-compliance/               # Regulatory compliance
├── dd-captable/                 # Cap table analysis
├── dd-legal/                    # Legal review
└── dd-lead/                     # Deal lead synthesis

config/process-templates/
└── vc-due-diligence/
    ├── template.yaml            # Process metadata
    └── definition.yaml          # Process definition
```

## Demo Script (60 Seconds)

**[0:00]** "Watch an AI VC firm analyze a startup."

**[0:05]** Provide pitch deck URL → Click "Execute Process"

**[0:10]** Dashboard Timeline explodes:
- Intake agent parses deck
- 9 colored bars fan out simultaneously
- Each agent researching their domain

**[0:30]** Real-time activity:
- "Founder Agent: Checking LinkedIn..."
- "Market Agent: Verifying TAM claims..."
- "Competitor Agent: Found 7 competitors on Crunchbase..."

**[0:45]** Convergence:
- Specialist agents complete (bars turn green)
- Deal Lead starts synthesizing
- Risk score calculated

**[0:55]** Human moment:
- Approval request appears in Trinity
- Investment Committee review screen
- **One click: APPROVE or REJECT**

**[1:00]** Results in dd-lead's shared folder:
- Complete investment recommendation
- Risk analysis and scoring
- Term sheet (if approved)

**[1:05]** "What takes VCs 2 weeks. 60 seconds. 9 agents. All local."

---

## Accessing Results

Results are stored in **dd-lead's shared folder**, accessible via:

1. **Trinity File Manager**: `/files` → Select `dd-lead` → Navigate to `shared-out/final-report/`
2. **Agent Detail**: Agents → `dd-lead` → Files tab → `shared-out/final-report/`
3. **API**: `GET /api/agents/dd-lead/files?path=/shared-out/final-report/`

---

*"Your startup's fate. Decided by agents. In 60 seconds. Fully local."*
