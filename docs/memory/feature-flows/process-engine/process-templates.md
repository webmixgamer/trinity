# Feature: Process Templates

> Pre-built and user-defined process templates for quick-start workflows

---

## Overview

Process Templates provide starting points for common workflows. Users can:
- Browse and use bundled templates
- Create processes from templates
- Save their own processes as templates

**Key Capabilities:**
- Bundled templates for common use cases
- Template metadata (category, complexity, tags)
- User-created template storage
- Template selector UI component

---

## Entry Points

- **UI**: `ProcessEditor.vue` -> "Create from Template" -> `TemplateSelector.vue`
- **UI**: `ProcessList.vue` -> "Create Process" -> Template option
- **API**: `GET /api/process-templates` - List templates
- **API**: `GET /api/process-templates/{id}` - Get template detail
- **API**: `POST /api/process-templates` - Create user template

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  TemplateSelector.vue                                                    │    │
│  │  ├── Category filter (content, devops, analytics)                       │    │
│  │  ├── Source filter (bundled, user)                                      │    │
│  │  ├── Template cards with preview                                        │    │
│  │  └── "Use Template" button                                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ GET /api/process-templates
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  routers/process_templates.py                                            │    │
│  │  ├── list_templates()        - GET /api/process-templates               │    │
│  │  ├── get_template()          - GET /api/process-templates/{id}          │    │
│  │  ├── create_template()       - POST /api/process-templates              │    │
│  │  └── delete_template()       - DELETE /api/process-templates/{name}     │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/templates.py - ProcessTemplateService                          │    │
│  │  ├── list_templates()        - Combine bundled + user templates         │    │
│  │  ├── get_template()          - Load template by ID                      │    │
│  │  ├── create_template()       - Save user template to database           │    │
│  │  └── delete_template()       - Remove user template                     │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     Template Sources                                       │  │
│  │  ┌─────────────────────┐       ┌─────────────────────┐                    │  │
│  │  │  Bundled Templates  │       │   User Templates    │                    │  │
│  │  │  config/process-    │       │   trinity_         │                    │  │
│  │  │  templates/         │       │   templates.db      │                    │  │
│  │  │  ├── content-review │       │                     │                    │  │
│  │  │  ├── data-analysis  │       │                     │                    │  │
│  │  │  └── customer-      │       │                     │                    │  │
│  │  │      support        │       │                     │                    │  │
│  │  └─────────────────────┘       └─────────────────────┘                    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Bundled Templates

### Directory Structure

```
config/process-templates/
├── content-review/
│   ├── template.yaml      # Metadata
│   └── definition.yaml    # Process definition
├── data-analysis/
│   ├── template.yaml
│   └── definition.yaml
└── customer-support/
    ├── template.yaml
    └── definition.yaml
```

### Template Metadata (template.yaml)

```yaml
name: content-review
display_name: Content Review Pipeline
description: A multi-step content review workflow with AI analysis and human approval
category: content                   # content, devops, analytics, business
complexity: intermediate            # simple, intermediate, advanced
version: "1.0.0"
author: Trinity Examples

tags:
  - content
  - review
  - approval
  - quality

step_types_used:
  - agent_task
  - human_approval
  - gateway

use_cases:
  - "Content moderation and approval workflows"
  - "Quality assurance pipelines"
  - "Editorial review processes"
```

### Process Definition (definition.yaml)

```yaml
name: content-review-process
version: 1
description: Review and approve content

steps:
  - id: analyze
    name: Analyze Content
    type: agent_task
    agent: analysis-agent
    message: Analyze the following content: {{input.content}}

  - id: review
    type: human_approval
    title: Review Analysis
    description: Review the AI analysis before publishing
    depends_on: [analyze]

  - id: publish
    type: agent_task
    agent: publisher-agent
    message: Publish the approved content
    depends_on: [review]

outputs:
  - name: result
    source: "{{steps.publish.output}}"
```

---

## Domain Model

### ProcessTemplateInfo

```python
# templates.py:24-51

@dataclass
class ProcessTemplateInfo:
    """Summary info for a process template."""
    id: str                      # "process:name" or "user:name"
    name: str                    # Template slug
    display_name: str            # Human-readable name
    description: str
    category: str               # content, devops, analytics, etc.
    complexity: str             # simple, intermediate, advanced
    version: str
    author: str
    tags: List[str]
    step_types_used: List[str]  # agent_task, human_approval, etc.
    source: str                 # "bundled" | "user" | "community"
```

### ProcessTemplate

```python
# templates.py:54-69

@dataclass
class ProcessTemplate:
    """Full process template with definition."""
    info: ProcessTemplateInfo
    definition_yaml: str         # The actual YAML to create process from
    use_cases: List[str]
    created_at: Optional[datetime]
    created_by: Optional[str]
```

---

## ProcessTemplateService

### List Templates

```python
# templates.py:143-171

def list_templates(
    self,
    category: Optional[str] = None,
    source: Optional[str] = None,
) -> List[ProcessTemplateInfo]:
    """List all available templates."""
    templates = []

    # Load bundled templates
    if source is None or source == "bundled":
        templates.extend(self._load_bundled_templates(category))

    # Load user templates
    if source is None or source == "user":
        templates.extend(self._load_user_templates(category))

    # Sort by display name
    templates.sort(key=lambda t: t.display_name)
    return templates
```

### Get Template

```python
# templates.py:264-283

def get_template(self, template_id: str) -> Optional[ProcessTemplate]:
    """Get a template by ID."""
    if template_id.startswith("process:"):
        return self._get_bundled_template(template_id[8:])
    elif template_id.startswith("user:"):
        return self._get_user_template(template_id[5:])
    else:
        # Try both
        template = self._get_bundled_template(template_id)
        if not template:
            template = self._get_user_template(template_id)
        return template
```

### Create User Template

```python
# templates.py:375-444

def create_template(
    self,
    name: str,
    definition_yaml: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    complexity: str = "simple",
    tags: Optional[List[str]] = None,
    use_cases: Optional[List[str]] = None,
    created_by: Optional[str] = None,
) -> ProcessTemplate:
    """Create a new user template."""
    # Check if name exists
    cursor.execute("SELECT 1 FROM process_templates WHERE name = ?", (name,))
    if cursor.fetchone():
        raise ValueError(f"Template with name '{name}' already exists")

    # Analyze definition to extract step types
    definition = yaml.safe_load(definition_yaml)
    steps = definition.get("steps", [])
    step_types = list(set(s.get("type", "") for s in steps))

    # Insert into database
    cursor.execute("""
        INSERT INTO process_templates (...) VALUES (...)
    """, ...)

    return self._get_user_template(name)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/process-templates` | List templates (filter by category, source) |
| GET | `/api/process-templates/{id}` | Get template detail |
| POST | `/api/process-templates` | Create user template |
| DELETE | `/api/process-templates/{name}` | Delete user template |

### Response Examples

**List Templates:**

```json
{
  "templates": [
    {
      "id": "process:content-review",
      "name": "content-review",
      "display_name": "Content Review Pipeline",
      "description": "A multi-step content review workflow",
      "category": "content",
      "complexity": "intermediate",
      "version": "1.0.0",
      "author": "Trinity Examples",
      "tags": ["content", "review", "approval"],
      "step_types_used": ["agent_task", "human_approval", "gateway"],
      "source": "bundled"
    }
  ]
}
```

**Get Template:**

```json
{
  "id": "process:content-review",
  "name": "content-review",
  "display_name": "Content Review Pipeline",
  "description": "A multi-step content review workflow",
  "category": "content",
  "complexity": "intermediate",
  "version": "1.0.0",
  "author": "Trinity Examples",
  "tags": ["content", "review"],
  "step_types_used": ["agent_task", "human_approval"],
  "source": "bundled",
  "definition_yaml": "name: content-review-process\nversion: 1\n...",
  "use_cases": [
    "Content moderation and approval workflows",
    "Quality assurance pipelines"
  ]
}
```

---

## Frontend Components

### TemplateSelector.vue

Component for browsing and selecting templates.

```vue
<template>
  <div class="template-selector">
    <!-- Filters -->
    <div class="filters">
      <select v-model="categoryFilter">
        <option value="">All Categories</option>
        <option value="content">Content</option>
        <option value="devops">DevOps</option>
        <option value="analytics">Analytics</option>
      </select>

      <select v-model="sourceFilter">
        <option value="">All Sources</option>
        <option value="bundled">Bundled</option>
        <option value="user">My Templates</option>
      </select>
    </div>

    <!-- Template Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        @click="selectTemplate(template)"
      >
        <h3>{{ template.display_name }}</h3>
        <p>{{ template.description }}</p>
        <div class="flex gap-1">
          <span v-for="tag in template.tags" class="tag">{{ tag }}</span>
        </div>
        <div class="meta">
          <span class="badge">{{ template.complexity }}</span>
          <span class="badge">{{ template.source }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['select'])

async function loadTemplates() {
  const params = {}
  if (categoryFilter.value) params.category = categoryFilter.value
  if (sourceFilter.value) params.source = sourceFilter.value

  templates.value = await api.get('/api/process-templates', { params })
}

function selectTemplate(template) {
  emit('select', template)
}
</script>
```

### Integration with ProcessEditor

```javascript
// ProcessEditor.vue

async function handleTemplateSelect(templateInfo) {
  // Load full template
  const template = await api.get(`/api/process-templates/${templateInfo.id}`)

  // Set YAML content to template definition
  yamlContent.value = template.definition_yaml

  // Close selector
  showTemplateSelector.value = false
}
```

---

## Database Schema

### process_templates Table

```sql
CREATE TABLE process_templates (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,          -- Unique slug
    display_name TEXT,
    description TEXT,
    category TEXT DEFAULT 'general',
    complexity TEXT DEFAULT 'simple',
    version TEXT DEFAULT '1.0.0',
    author TEXT,
    tags TEXT,                          -- YAML list
    step_types_used TEXT,               -- YAML list
    use_cases TEXT,                     -- YAML list
    definition_yaml TEXT NOT NULL,      -- Process definition
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## Creating a Bundled Template

To add a new bundled template:

1. Create directory in `config/process-templates/`:

```bash
mkdir config/process-templates/my-template
```

2. Create `template.yaml` with metadata:

```yaml
name: my-template
display_name: My Template
description: Description of what this template does
category: business
complexity: simple
version: "1.0.0"
author: Your Name

tags:
  - tag1
  - tag2

step_types_used:
  - agent_task
  - notification

use_cases:
  - "Use case 1"
  - "Use case 2"
```

3. Create `definition.yaml` with process definition:

```yaml
name: my-template-process
version: 1
description: Process created from my-template

steps:
  - id: step1
    type: agent_task
    agent: some-agent
    message: Do something

outputs:
  - name: result
    source: "{{steps.step1.output}}"
```

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Bundled templates in config/process-templates/

### Test Cases

1. **List bundled templates**
   - Action: GET /api/process-templates?source=bundled
   - Expected: Returns bundled templates

2. **Create user template**
   - Action: POST /api/process-templates with valid definition
   - Expected: Template saved, appears in user templates

3. **Create process from template**
   - Action: Select template, click "Use Template"
   - Expected: YAML loaded in editor

4. **Filter by category**
   - Action: Select category filter
   - Expected: Only templates in category shown

5. **Delete user template**
   - Action: DELETE /api/process-templates/my-template
   - Expected: Template removed

---

## Related Flows

- [process-definition.md](./process-definition.md) - Process creation from template YAML

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
