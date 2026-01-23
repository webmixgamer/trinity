# Feature: Human Approval

> Human approval gates within process workflows with inbox, timeout, and decision tracking

---

## Overview

Human Approval provides a mechanism for processes to pause and wait for human decisions. When an execution reaches a `human_approval` step, it pauses until an authorized user approves or rejects through the Approvals inbox.

**Key Capabilities:**
- Approval gates that pause execution
- Assignee-based authorization
- Timeout with expiration
- Approval inbox with filtering
- Decision tracking (who, when, comments)
- **Template variable substitution** in `title` and `description` fields

---

## Entry Points

- **UI**: Nav bar "Approvals" -> `Approvals.vue`
- **UI**: Process execution detail shows "Waiting for approval" status
- **API**: `GET /api/approvals` - List approval requests
- **API**: `POST /api/approvals/{id}/approve` - Approve request
- **API**: `POST /api/approvals/{id}/reject` - Reject request

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Approvals.vue                                                           │    │
│  │  ├── Filter by status (pending, approved, rejected)                     │    │
│  │  ├── Stats cards (total, pending, approved, rejected counts)            │    │
│  │  ├── Table of approval requests                                         │    │
│  │  └── Approve/Reject modal with comment input                            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                            │
│                                     │ POST /api/approvals/{id}/approve           │
│                                     ▼                                            │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  routers/approvals.py                                                    │    │
│  │  ├── list_approvals()          - GET all requests with filters          │    │
│  │  ├── get_approval()            - GET single request                      │    │
│  │  ├── approve_request()         - POST approve decision                   │    │
│  │  └── reject_request()          - POST reject decision                    │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ Updates ApprovalRequest                   │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  engine/handlers/human_approval.py                                       │    │
│  │  ├── ApprovalStore              - In-memory request storage              │    │
│  │  └── HumanApprovalHandler       - Creates requests, checks decisions     │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ Stores/retrieves                          │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  domain/entities.py - ApprovalRequest                                    │    │
│  │  ├── create()                   - Factory method                         │    │
│  │  ├── approve()                  - Mark as approved                       │    │
│  │  ├── reject()                   - Mark as rejected                       │    │
│  │  └── expire()                   - Mark as expired (timeout)              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Flow Details

### 1. Create Approval Request Flow

When execution reaches a `human_approval` step:

```
ExecutionEngine                 HumanApprovalHandler           ApprovalStore
---------------                 --------------------           -------------
_execute_step()
  Get handler for HUMAN_APPROVAL
  handler.execute(context, config)
                            →   execute()
                                ├── Check existing request
                                ├── Calculate deadline
                                ├── Evaluate title template
                                ├── Evaluate description template
                                └── ApprovalRequest.create()
                                    save(request)          →    Store in memory
                            ←   StepResult.wait({approval_id, title})

_handle_step_waiting()
  step_exec.wait_for_approval()
  execution.pause()
  publish(StepWaitingApproval)
```

### Template Evaluation Detail

```python
# human_approval.py:106-126

def _evaluate_template(self, template: str, context: StepContext) -> str:
    """
    Evaluate template variables in a string.

    Supports:
    - {{input.X}} - Process input data
    - {{steps.X.output}} - Step output
    - {{execution.id}} - Execution ID
    - {{process.name}} - Process name
    """
    if not template:
        return template

    eval_context = EvaluationContext(
        input_data=context.input_data,
        step_outputs=context.step_outputs,
        execution_id=str(context.execution.id),
        process_name=context.execution.process_name,
    )

    return self.expression_evaluator.evaluate(template, eval_context)
```

The handler calls `_evaluate_template()` on both `title` and `description` before creating the `ApprovalRequest`:

```python
# human_approval.py:186-198

# Evaluate template variables in title and description
evaluated_title = self._evaluate_template(config.title, context)
evaluated_description = self._evaluate_template(config.description, context) if config.description else None

# Create approval request with evaluated values
request = ApprovalRequest.create(
    execution_id=execution_id,
    step_id=step_id,
    title=evaluated_title,
    description=evaluated_description,
    assignees=config.assignees,
    deadline=deadline,
)
```

### 2. Approve/Reject Flow

When user makes a decision in the UI:

```
Approvals.vue                   Backend                         ExecutionEngine
-------------                   -------                         ---------------
User clicks "Approve"
POST /api/approvals/{id}/approve
  { comment: "Looks good" }
                            →   approve_request()
                                ├── Get ApprovalRequest
                                ├── Validate user authorization
                                ├── request.approve(user, comment)
                                ├── Save updated request
                                └── engine.resume(execution)
                                                            →   resume()
                                                                ├── Reset step to PENDING
                                                                └── _run() continues
                                                                    ├── Handler sees "approved"
                                                                    └── StepResult.ok()
```

### 3. Resume After Approval

When the step is re-executed after approval:

```python
# HumanApprovalHandler.execute() - line 119-140

existing = self.approval_store.get_by_execution_step(execution_id, step_id)
if existing:
    if existing.is_pending():
        # Still waiting
        return StepResult.wait({"approval_id": existing.id})
    elif existing.status.value == "approved":
        # Already approved - complete the step
        return StepResult.ok({
            "approval_id": existing.id,
            "decision": "approved",
            "decided_by": existing.decided_by,
            "comment": existing.decision_comment,
        })
    else:
        # Rejected - fail the step
        return StepResult.fail(
            f"Approval rejected by {existing.decided_by}: {existing.decision_comment}",
            error_code="APPROVAL_REJECTED",
        )
```

---

## YAML Configuration

### Basic Approval Step

```yaml
- id: review
  type: human_approval
  title: Review Content
  description: Please review the generated content before publishing
```

### With Assignees and Timeout

```yaml
- id: manager-approval
  type: human_approval
  title: Manager Approval Required
  description: This change requires manager sign-off
  assignees:
    - manager@example.com
    - supervisor@example.com
  timeout: 48h  # Auto-expires after 48 hours
```

### With Template Variables (Dynamic Content)

Template variables in `title` and `description` are evaluated at runtime using process input data and previous step outputs:

```yaml
- id: intake
  type: agent_task
  agent: intake-agent
  message: Collect company info for {{input.company_name}}

- id: review-approval
  type: human_approval
  title: Approve {{input.company_name}} for {{input.deal_type}}?
  description: |
    Review the intake results before proceeding.

    **Company**: {{input.company_name}}
    **Deal Type**: {{input.deal_type}}
    **Intake Summary**: {{steps.intake.output.response}}
    **Risk Score**: {{steps.intake.output.score}}
  assignees:
    - deal-manager@example.com
  timeout: 24h
```

**Supported Template Variables:**

| Pattern | Description | Example |
|---------|-------------|---------|
| `{{input.X}}` | Process input data field | `{{input.company_name}}` |
| `{{steps.X.output}}` | Full step output (entire response object) | `{{steps.research.output}}` |
| `{{steps.X.output.Y}}` | Nested field in step output | `{{steps.research.output.summary}}` |
| `{{execution.id}}` | Execution ID | `exec_abc123...` |
| `{{process.name}}` | Process name | `due-diligence-workflow` |

**Notes:**
- Missing variables are left as-is (e.g., `{{input.missing}}` remains unchanged)
- Dict outputs with `response` or `value` keys are automatically extracted
- Non-string values are converted to JSON for display

---

## Domain Model

### ApprovalRequest Entity

```python
# entities.py:428-543

@dataclass
class ApprovalRequest:
    id: str                          # UUID
    execution_id: str                # Parent execution
    step_id: str                     # Step within execution
    title: str                       # Display title
    description: str                 # Details about what needs approval
    assignees: list[str]             # Users who can approve (empty = anyone)
    status: ApprovalStatus           # pending, approved, rejected, expired
    deadline: Optional[datetime]     # When request expires
    created_at: datetime
    decided_at: Optional[datetime]
    decided_by: Optional[str]
    decision_comment: Optional[str]

    @classmethod
    def create(cls, execution_id, step_id, title, description, assignees, deadline) -> ApprovalRequest:
        """Create a new approval request."""

    def approve(self, decided_by: str, comment: str = None) -> None:
        """Mark as approved."""
        self.status = ApprovalStatus.APPROVED
        self.decided_at = datetime.now(timezone.utc)
        self.decided_by = decided_by
        self.decision_comment = comment

    def reject(self, decided_by: str, comment: str) -> None:
        """Mark as rejected (comment required)."""
        self.status = ApprovalStatus.REJECTED
        self.decided_at = datetime.now(timezone.utc)
        self.decided_by = decided_by
        self.decision_comment = comment

    def expire(self) -> None:
        """Mark as expired due to timeout."""
        self.status = ApprovalStatus.EXPIRED
        self.decided_at = datetime.now(timezone.utc)

    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING

    def can_be_decided_by(self, user: str) -> bool:
        """Check if user can make a decision."""
        if not self.assignees:
            return True  # No assignees = anyone can approve
        return user in self.assignees
```

### ApprovalStatus Enum

```python
class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/approvals` | List approval requests |
| GET | `/api/approvals/{id}` | Get single request |
| POST | `/api/approvals/{id}/approve` | Approve request |
| POST | `/api/approvals/{id}/reject` | Reject request |

### Request/Response Examples

**List Approvals:**

```
GET /api/approvals?status=pending
```

```json
{
  "approvals": [
    {
      "id": "approval-uuid",
      "execution_id": "execution-uuid",
      "step_id": "review",
      "title": "Review Content",
      "description": "Please review before publishing",
      "assignees": ["editor@example.com"],
      "status": "pending",
      "deadline": "2026-01-18T10:00:00Z",
      "created_at": "2026-01-16T10:00:00Z"
    }
  ],
  "total": 1
}
```

**Approve Request:**

```
POST /api/approvals/{id}/approve
{
  "comment": "Content looks good, approved for publishing"
}
```

```json
{
  "id": "approval-uuid",
  "status": "approved",
  "decided_at": "2026-01-16T11:30:00Z",
  "decided_by": "editor@example.com",
  "decision_comment": "Content looks good, approved for publishing"
}
```

**Reject Request:**

```
POST /api/approvals/{id}/reject
{
  "comment": "Needs revision, see inline comments"
}
```

---

## Frontend Components

### Approvals.vue

Main inbox view for approval management.

| Section | Lines | Description |
|---------|-------|-------------|
| Header | 8-27 | Title and refresh button |
| Filters | 29-58 | Status dropdown filter |
| Stats Cards | 60-78 | Total/Pending/Approved/Rejected counts |
| Table | 94-200 | List of requests with actions |
| Approve Modal | 210-280 | Confirmation dialog |
| Reject Modal | 290-360 | Rejection with required comment |

**Key Methods:**

```javascript
async function loadApprovals() {
  const params = {}
  if (statusFilter.value) {
    params.status = statusFilter.value
  }
  const response = await api.get('/api/approvals', { params })
  approvals.value = response.approvals
  calculateStats()
}

async function handleApprove(approval) {
  const comment = approveComment.value
  await api.post(`/api/approvals/${approval.id}/approve`, { comment })
  loadApprovals()  // Refresh list
}

async function handleReject(approval) {
  const comment = rejectComment.value
  if (!comment) {
    error.value = 'Comment is required for rejection'
    return
  }
  await api.post(`/api/approvals/${approval.id}/reject`, { comment })
  loadApprovals()
}
```

### ProcessSubNav Badge

Shows pending approval count in navigation:

```vue
<ProcessSubNav :pending-approvals="pendingCount" />
```

```vue
<!-- In ProcessSubNav.vue -->
<router-link to="/approvals">
  Approvals
  <span v-if="pendingApprovals > 0" class="ml-2 bg-amber-500 text-white rounded-full px-2 py-0.5 text-xs">
    {{ pendingApprovals }}
  </span>
</router-link>
```

---

## Timeout Handling

### Deadline Calculation

```python
# human_approval.py:142-145

deadline = None
if config.timeout:
    deadline = datetime.now(timezone.utc) + timedelta(seconds=config.timeout.seconds)
```

### Expiration Check

Timeout expiration is checked when:
1. Approval request is queried
2. Execution is resumed
3. Periodic background check (if implemented)

```python
def check_expired(request: ApprovalRequest) -> bool:
    if request.deadline and datetime.now(timezone.utc) > request.deadline:
        if request.is_pending():
            request.expire()
            return True
    return False
```

---

## Authorization

### Assignee Check

```python
# entities.py:494-499

def can_be_decided_by(self, user: str) -> bool:
    """Check if the given user can decide on this request."""
    # If no assignees specified, anyone can approve
    if not self.assignees:
        return True
    return user in self.assignees
```

### API Authorization

```python
# routers/approvals.py

@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    request: ApproveRequest,
    current_user: CurrentUser,
):
    approval = store.get(approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")

    if not approval.can_be_decided_by(current_user.email):
        raise HTTPException(403, "Not authorized to approve this request")

    approval.approve(current_user.email, request.comment)
    # ... resume execution
```

---

## Error Handling

| Error | HTTP Status | Cause |
|-------|-------------|-------|
| Approval not found | 404 | Invalid approval ID |
| Not authorized | 403 | User not in assignees list |
| Already decided | 400 | Approval already approved/rejected |
| Expired | 400 | Deadline passed |
| Comment required | 422 | Rejection without comment |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Published process with human_approval step
- User account for testing

### Test Cases

1. **Create approval request**
   - Action: Start process with human_approval step
   - Expected: Execution pauses, request appears in inbox

2. **Approve request**
   - Action: Click approve on pending request
   - Expected: Request marked approved, execution resumes

3. **Reject request**
   - Action: Click reject, enter comment
   - Expected: Request marked rejected, step fails

4. **Assignee authorization**
   - Action: Try to approve as non-assignee
   - Expected: 403 Forbidden error

5. **Timeout expiration**
   - Action: Let request exceed deadline
   - Expected: Request marked expired, step fails

---

## Related Flows

- [process-execution.md](./process-execution.md) - How execution pauses/resumes
- [process-monitoring.md](./process-monitoring.md) - Viewing approval status in UI

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | **Bug Fix (PE-H1)**: Documented template variable substitution in `title` and `description` fields - variables like `{{input.X}}` and `{{steps.X.output}}` are now properly evaluated using ExpressionEvaluator |
| 2026-01-16 | Initial creation |
