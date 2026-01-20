# Feature: Onboarding and Documentation

## Overview
Premium onboarding experience for the Process Engine, including empty state guidance, documentation tab, contextual help, guided tours, and a first-process wizard. This feature transforms how new users discover, learn, and achieve their first success with automated workflows.

## User Story
As a new Trinity user, I want guided onboarding and in-app documentation so that I can quickly understand and start using process automation without external help.

## Requirements Reference
- **PROCESS_ENGINE_ROADMAP.md** Phase 6 — In-App Documentation & Onboarding
- **BACKLOG_ONBOARDING.md** — E20-E24 (17 stories)
- **Industry Research** — SaaS onboarding best practices 2025-2026

---

## Entry Points

### Empty State Entry
- **UI**: `ProcessList.vue` when `processes.length === 0`
- **Trigger**: First visit with no processes created

### Docs Tab Entry
- **UI**: `ProcessSubNav.vue` — Docs tab with BookOpenIcon
- **Route**: `/processes/docs`

### Contextual Help Entry
- **UI**: `ProcessEditor.vue` — Help panel toggle
- **Trigger**: User opens editor, cursor position changes in YAML

### Guided Tour Entry
- **UI**: `ProcessList.vue` on mount
- **Trigger**: First visit + no processes + onboarding not dismissed

### Wizard Entry
- **UI**: Empty state "Use Template" card or direct route
- **Route**: `/processes/wizard`

---

## Flow 1: Empty State to First Process

### Frontend Layer

#### ProcessList.vue Empty State
**File**: `src/frontend/src/views/ProcessList.vue`

Current empty state (lines 196-210):
```vue
<div v-else class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
  <CubeTransparentIcon class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
  <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">No processes</h3>
  <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Get started by creating a new process workflow.</p>
  <div class="mt-6">
    <router-link to="/processes/new" class="...">
      <PlusIcon class="h-5 w-5 mr-1" />
      Create Process
    </router-link>
  </div>
</div>
```

Enhanced empty state will include:
- Welcoming hero section with illustration
- Value proposition text
- Template quick-start cards (3 options)
- "Create from Scratch" and "Import YAML" options
- Link to Getting Started documentation

#### Template Cards Component
**File**: `src/frontend/src/components/ProcessTemplateCards.vue` (new)

```vue
<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div v-for="template in templates" :key="template.id"
      class="border rounded-lg p-4 hover:border-indigo-500 cursor-pointer"
      @click="selectTemplate(template)">
      <h4 class="font-medium">{{ template.name }}</h4>
      <p class="text-sm text-gray-500">{{ template.description }}</p>
      <span class="text-xs text-gray-400">{{ template.stepCount }} steps</span>
    </div>
  </div>
</template>
```

### State Management

#### Onboarding State Composable
**File**: `src/frontend/src/composables/useOnboarding.js` (new)

```javascript
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useProcessesStore } from '../stores/processes'

const STORAGE_KEY = 'trinity_onboarding'

export function useOnboarding() {
  const authStore = useAuthStore()
  const processesStore = useProcessesStore()

  // Load from localStorage
  const getStorageKey = () => `${STORAGE_KEY}_${authStore.user?.id || 'anon'}`

  const state = ref({
    dismissed: false,
    tourCompleted: false,
    checklist: {
      createProcess: false,
      runExecution: false,
      monitorExecution: false,
      setupSchedule: false,
      configureApproval: false
    }
  })

  // Load state on init
  const loadState = () => {
    try {
      const stored = localStorage.getItem(getStorageKey())
      if (stored) {
        state.value = JSON.parse(stored)
      }
    } catch (e) {
      console.warn('Failed to load onboarding state:', e)
    }
  }

  // Save state on change
  watch(state, (newState) => {
    localStorage.setItem(getStorageKey(), JSON.stringify(newState))
  }, { deep: true })

  // Auto-detect completed items
  const isFirstRun = computed(() => {
    return processesStore.processes.length === 0 && !state.value.dismissed
  })

  const checklistProgress = computed(() => {
    const items = Object.values(state.value.checklist)
    const completed = items.filter(Boolean).length
    return { completed, total: items.length }
  })

  const markChecklistItem = (item) => {
    if (item in state.value.checklist) {
      state.value.checklist[item] = true
    }
  }

  const dismissOnboarding = () => {
    state.value.dismissed = true
  }

  const markTourCompleted = () => {
    state.value.tourCompleted = true
  }

  loadState()

  return {
    state,
    isFirstRun,
    checklistProgress,
    markChecklistItem,
    dismissOnboarding,
    markTourCompleted
  }
}
```

---

## Flow 2: Documentation Tab

### Frontend Layer

#### Router Configuration
**File**: `src/frontend/src/router/index.js`

Add new route:
```javascript
{
  path: '/processes/docs',
  name: 'ProcessDocs',
  component: () => import('../views/ProcessDocs.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/processes/docs/:slug*',
  name: 'ProcessDocsPage',
  component: () => import('../views/ProcessDocs.vue'),
  meta: { requiresAuth: true }
}
```

#### ProcessSubNav Update
**File**: `src/frontend/src/components/ProcessSubNav.vue`

Add Docs tab to navItems:
```javascript
import { BookOpenIcon } from '@heroicons/vue/24/outline'

const navItems = computed(() => [
  { path: '/processes', label: 'Processes', icon: QueueListIcon },
  { path: '/process-dashboard', label: 'Dashboard', icon: ChartBarIcon },
  { path: '/processes/docs', label: 'Docs', icon: BookOpenIcon },  // NEW
  { path: '/executions', label: 'Executions', icon: PlayCircleIcon },
  { path: '/approvals', label: 'Approvals', icon: CheckCircleIcon, badge: props.pendingApprovals },
])
```

#### ProcessDocs View
**File**: `src/frontend/src/views/ProcessDocs.vue` (new)

```vue
<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div class="flex gap-6">
        <!-- Sidebar -->
        <aside class="w-64 flex-shrink-0">
          <div class="sticky top-6">
            <!-- Search -->
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search docs..."
              class="w-full px-3 py-2 border rounded-lg mb-4"
            />

            <!-- Navigation Tree -->
            <nav class="space-y-1">
              <div v-for="section in docSections" :key="section.id">
                <button @click="toggleSection(section.id)" class="...">
                  {{ section.title }}
                </button>
                <div v-if="expandedSections.includes(section.id)">
                  <router-link
                    v-for="doc in section.docs"
                    :key="doc.slug"
                    :to="`/processes/docs/${doc.slug}`"
                    class="..."
                  >
                    {{ doc.title }}
                  </router-link>
                </div>
              </div>
            </nav>
          </div>
        </aside>

        <!-- Content -->
        <article class="flex-1 bg-white dark:bg-gray-800 rounded-xl shadow p-8">
          <div v-if="loading" class="animate-pulse">Loading...</div>
          <div v-else class="prose dark:prose-invert max-w-none" v-html="renderedContent" />
        </article>
      </div>
    </main>
  </div>
</template>
```

### Content Storage

#### Documentation Files
**Location**: `config/process-docs/`

```
config/process-docs/
├── index.json              # Navigation structure
├── getting-started/
│   ├── what-are-processes.md
│   ├── first-process.md
│   └── step-types.md
├── reference/
│   ├── yaml-schema.md
│   ├── variables.md
│   ├── triggers.md
│   └── error-handling.md
├── patterns/
│   ├── sequential.md
│   ├── parallel.md
│   ├── approvals.md
│   └── scheduled.md
└── troubleshooting/
    ├── common-errors.md
    └── step-stuck.md
```

#### Navigation Index
**File**: `config/process-docs/index.json`

```json
{
  "sections": [
    {
      "id": "getting-started",
      "title": "Getting Started",
      "docs": [
        { "slug": "getting-started/what-are-processes", "title": "What are Processes?" },
        { "slug": "getting-started/first-process", "title": "Your First Process" },
        { "slug": "getting-started/step-types", "title": "Understanding Step Types" }
      ]
    },
    {
      "id": "reference",
      "title": "Reference",
      "docs": [
        { "slug": "reference/yaml-schema", "title": "YAML Schema" },
        { "slug": "reference/variables", "title": "Variable Interpolation" },
        { "slug": "reference/triggers", "title": "Triggers" },
        { "slug": "reference/error-handling", "title": "Error Handling" }
      ]
    }
  ]
}
```

---

## Flow 3: Contextual Help Panel

### Frontend Layer

#### ProcessEditor Help Panel
**File**: `src/frontend/src/views/ProcessEditor.vue`

Add help panel alongside YAML editor:
```vue
<template>
  <div class="flex">
    <!-- YAML Editor (existing) -->
    <div class="flex-1">
      <YamlEditor
        v-model="yamlContent"
        @cursor-change="onCursorChange"
      />
    </div>

    <!-- Help Panel (new) -->
    <aside v-if="showHelpPanel" class="w-80 border-l p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="font-medium">Help</h3>
        <button @click="showHelpPanel = false">×</button>
      </div>

      <div v-if="currentHelp">
        <h4 class="font-semibold text-sm mb-2">{{ currentHelp.title }}</h4>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
          {{ currentHelp.description }}
        </p>

        <div v-if="currentHelp.example" class="bg-gray-100 dark:bg-gray-700 p-2 rounded text-xs">
          <pre>{{ currentHelp.example }}</pre>
        </div>

        <router-link
          v-if="currentHelp.docsLink"
          :to="currentHelp.docsLink"
          class="text-indigo-600 text-sm mt-3 inline-block"
        >
          Learn more →
        </router-link>
      </div>

      <div v-else class="text-sm text-gray-500">
        Place your cursor in the YAML to see contextual help.
      </div>
    </aside>
  </div>
</template>
```

#### Help Content
**File**: `config/process-docs/tooltips.json`

```json
{
  "steps": {
    "title": "Steps",
    "description": "Steps are the building blocks of a process. Each step performs a specific action.",
    "example": "steps:\n  - id: analyze\n    type: agent_task\n    agent: analyst",
    "docsLink": "/processes/docs/getting-started/step-types"
  },
  "steps.id": {
    "title": "Step ID",
    "description": "A unique identifier for this step. Used in depends_on and variable references.",
    "example": "id: analyze-data"
  },
  "steps.type": {
    "title": "Step Type",
    "description": "The type of action this step performs.",
    "options": ["agent_task", "human_approval", "gateway", "timer"],
    "docsLink": "/processes/docs/getting-started/step-types"
  },
  "steps.depends_on": {
    "title": "Dependencies",
    "description": "List of step IDs that must complete before this step starts. Steps without depends_on run in parallel at process start.",
    "example": "depends_on:\n  - step-a\n  - step-b"
  },
  "steps.agent": {
    "title": "Agent",
    "description": "The name of the agent that will execute this task. Must be a running agent.",
    "example": "agent: researcher"
  },
  "steps.message": {
    "title": "Message",
    "description": "The prompt or instruction sent to the agent. Supports variable interpolation with {{...}} syntax.",
    "example": "message: |\n  Analyze: {{input.topic}}"
  },
  "steps.timeout": {
    "title": "Timeout",
    "description": "Maximum time to wait for step completion. Format: 30s, 5m, 1h, 1d.",
    "example": "timeout: 10m"
  }
}
```

---

## Flow 4: Guided Tour

### Frontend Layer

#### Tour Library Setup
**File**: `src/frontend/src/composables/useTour.js` (new)

```javascript
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useOnboarding } from './useOnboarding'

export function useTour() {
  const { markTourCompleted, state } = useOnboarding()

  const driverInstance = driver({
    showProgress: true,
    animate: true,
    overlayColor: 'rgba(0, 0, 0, 0.5)',
    popoverClass: 'trinity-tour-popover',
    onDestroyStarted: () => {
      markTourCompleted()
    }
  })

  const startProcessesTour = () => {
    if (state.value.tourCompleted) return

    driverInstance.setSteps([
      {
        element: '.processes-header',
        popover: {
          title: 'Welcome to Processes! 🚀',
          description: 'Processes let you automate multi-step workflows using your AI agents.',
          position: 'bottom'
        }
      },
      {
        element: '[data-tour="create-process"]',
        popover: {
          title: 'Create Your First Process',
          description: 'Click here to design a new automated workflow.',
          position: 'bottom'
        }
      },
      {
        element: '[data-tour="nav-dashboard"]',
        popover: {
          title: 'Dashboard',
          description: 'Monitor all your processes and executions at a glance.',
          position: 'bottom'
        }
      },
      {
        element: '[data-tour="nav-executions"]',
        popover: {
          title: 'Executions',
          description: 'See the history and status of all process runs.',
          position: 'bottom'
        }
      },
      {
        element: '[data-tour="nav-approvals"]',
        popover: {
          title: 'Approvals',
          description: 'Review and approve pending workflow steps that need human attention.',
          position: 'bottom'
        }
      }
    ])

    driverInstance.drive()
  }

  return {
    startProcessesTour
  }
}
```

#### Tour Trigger
**File**: `src/frontend/src/views/ProcessList.vue`

```javascript
import { useTour } from '../composables/useTour'
import { useOnboarding } from '../composables/useOnboarding'

const { startProcessesTour } = useTour()
const { isFirstRun } = useOnboarding()

onMounted(async () => {
  await processesStore.fetchProcesses()

  // Start tour for first-time users
  if (isFirstRun.value) {
    nextTick(() => {
      startProcessesTour()
    })
  }
})
```

---

## Testing Strategy

Per **DEVELOPMENT_CONFIDENCE_MODEL.md**, onboarding is presentation-layer and requires minimal testing:

| Component | Test Type | What to Test |
|-----------|-----------|--------------|
| `useOnboarding.js` | Unit | State persistence, computed properties |
| Markdown loading | Unit | Content parsing, code highlighting |
| Docs search | Unit | Fuzzy matching, result ranking |
| UI components | Smoke | Critical render paths only |

### Unit Test Example
**File**: `tests/frontend/composables/useOnboarding.test.js`

```javascript
describe('useOnboarding', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('initializes with default state', () => {
    const { state } = useOnboarding()
    expect(state.value.dismissed).toBe(false)
    expect(state.value.tourCompleted).toBe(false)
  })

  it('persists state to localStorage', () => {
    const { markChecklistItem, state } = useOnboarding()
    markChecklistItem('createProcess')

    const stored = JSON.parse(localStorage.getItem('trinity_onboarding_anon'))
    expect(stored.checklist.createProcess).toBe(true)
  })

  it('computes isFirstRun correctly', () => {
    // Mock processesStore with empty processes
    const { isFirstRun } = useOnboarding()
    expect(isFirstRun.value).toBe(true)
  })
})
```

---

## Related Files

| File | Purpose |
|------|---------|
| `src/frontend/src/views/ProcessList.vue` | Empty state display, tour trigger |
| `src/frontend/src/views/ProcessDocs.vue` | Documentation view (new) |
| `src/frontend/src/views/ProcessEditor.vue` | Contextual help panel |
| `src/frontend/src/views/ProcessWizard.vue` | First process wizard (new) |
| `src/frontend/src/components/ProcessSubNav.vue` | Docs tab in navigation |
| `src/frontend/src/components/OnboardingChecklist.vue` | Progress checklist (new) |
| `src/frontend/src/components/ProcessTemplateCards.vue` | Template quick-start cards (new) |
| `src/frontend/src/composables/useOnboarding.js` | Onboarding state management (new) |
| `src/frontend/src/composables/useTour.js` | Guided tour wrapper (new) |
| `src/frontend/src/composables/useContextualHelp.js` | Tooltip system (new) |
| `config/process-docs/` | Markdown documentation content |
| `config/process-docs/tooltips.json` | Contextual help content |
| `config/process-docs/index.json` | Docs navigation structure |

---

## Dependencies

### NPM Packages (new)
- `marked` — Markdown parsing
- `highlight.js` — Code syntax highlighting
- `driver.js` — Guided tour library
- `fuse.js` — Fuzzy search (optional for docs search)

### Existing Dependencies Used
- `vue-router` — Routing for docs pages
- `@heroicons/vue` — Icons (BookOpenIcon, etc.)
- `localStorage` — State persistence

---

## Implementation Sequence

1. **Sprint 7** (Quick wins)
   - E20-01: Enhanced empty state
   - E20-02: Onboarding checklist
   - E21-04: Getting Started content

2. **Sprint 8** (Docs tab)
   - E21-01: Docs route and nav
   - E21-02: ProcessDocs view
   - E21-05: Step types reference
   - E21-06: YAML schema reference

3. **Sprint 9** (Contextual help)
   - E22-01: Editor help panel
   - E22-03: Status explainers
   - E20-03: Template cards
   - E20-04: First-run detection

4. **Sprint 10** (Tours + search)
   - E23-01: Driver.js integration
   - E23-02: First-time tour
   - E21-03: Docs search

5. **Sprint 11** (Wizard)
   - E24-01 to E24-04: First process wizard

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-18 | Initial feature flow for onboarding and documentation |
