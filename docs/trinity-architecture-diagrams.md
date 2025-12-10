# Trinity Agent Platform - Architecture Diagrams

## 1. Core Concept: Standardized Claude Code Layer

```mermaid
graph TB
    subgraph "User 1 Environment"
        U1[User 1]
        A1[Claude Code Agent<br/>Isolated Instance]
        D1[(User 1 Data<br/>Locked & Isolated)]
        W1[Workspace 1]
    end
    
    subgraph "User 2 Environment"
        U2[User 2]
        A2[Claude Code Agent<br/>Isolated Instance]
        D2[(User 2 Data<br/>Locked & Isolated)]
        W2[Workspace 2]
    end
    
    subgraph "User 3 Environment"
        U3[User 3]
        A3[Claude Code Agent<br/>Isolated Instance]
        D3[(User 3 Data<br/>Locked & Isolated)]
        W3[Workspace 3]
    end
    
    subgraph "Standardized Platform Layer"
        BASE[Universal Claude Code<br/>Base Image]
        API[Trinity Management API]
        AUTH[Authentication & Isolation]
    end
    
    U1 --> A1
    A1 --> D1
    A1 --> W1
    
    U2 --> A2
    A2 --> D2
    A2 --> W2
    
    U3 --> A3
    A3 --> D3
    A3 --> W3
    
    BASE --> A1
    BASE --> A2
    BASE --> A3
    
    API --> AUTH
    AUTH --> A1
    AUTH --> A2
    AUTH --> A3
    
    style A1 fill:#9C27B0,stroke:#7B1FA2,stroke-width:3px,color:#fff
    style A2 fill:#9C27B0,stroke:#7B1FA2,stroke-width:3px,color:#fff
    style A3 fill:#9C27B0,stroke:#7B1FA2,stroke-width:3px,color:#fff
    style D1 fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
    style D2 fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
    style D3 fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
    style BASE fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
```

## 2. Data Isolation Architecture

```mermaid
graph TB
    subgraph "Claude Code Standardization"
        CC[Claude Code v2.0.37<br/>Standardized Agent Layer]
        MCP[MCP Servers<br/>Standardized Interfaces]
    end
    
    subgraph "Per-User Isolation"
        subgraph Container1["Container 1"]
            A1[Agent Instance 1]
            V1[Volume 1<br/>User Data]
            C1[Credentials 1]
        end
        
        subgraph Container2["Container 2"]
            A2[Agent Instance 2]
            V2[Volume 2<br/>User Data]
            C2[Credentials 2]
        end
        
        subgraph Container3["Container 3"]
            A3[Agent Instance 3]
            V3[Volume 3<br/>User Data]
            C3[Credentials 3]
        end
    end
    
    subgraph "Platform Services"
        API[Management API]
        AUTH[User Authentication]
        ISO[Container Isolation<br/>Network + Resource]
    end
    
    CC --> A1
    CC --> A2
    CC --> A3
    
    MCP --> A1
    MCP --> A2
    MCP --> A3
    
    A1 -.->|Locked| V1
    A2 -.->|Locked| V2
    A3 -.->|Locked| V3
    
    A1 --> C1
    A2 --> C2
    A3 --> C3
    
    API --> AUTH
    AUTH --> ISO
    ISO --> A1
    ISO --> A2
    ISO --> A3
    
    style CC fill:#9C27B0,stroke:#7B1FA2,stroke-width:3px,color:#fff
    style V1 fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
    style V2 fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
    style V3 fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
    style ISO fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#000
```

## 3. Standardized Claude Code Agent Layer

```mermaid
graph LR
    subgraph "Standardized Base"
        BASE[Universal Base Image]
        CC[Claude Code<br/>Latest Version]
        RT[Multi-Runtime<br/>Python, Node, Go]
        TOOLS[Standard Tools<br/>filesystem, web_search]
    end
    
    subgraph "User-Specific Layer"
        CONFIG[User Configuration]
        CREDS[User Credentials]
        DATA[User Data Volume]
        MCP[Selected MCP Servers]
    end
    
    subgraph "Running Instance"
        AGENT[Claude Code Agent<br/>Isolated Container]
        WORK[workspace<br/>User Data]
        LOCK[Data Lock<br/>No Cross-Access]
    end
    
    BASE --> CC
    CC --> RT
    RT --> TOOLS
    
    CONFIG --> AGENT
    CREDS --> AGENT
    DATA --> WORK
    MCP --> AGENT
    
    TOOLS --> AGENT
    AGENT --> WORK
    WORK --> LOCK
    
    style CC fill:#9C27B0,stroke:#7B1FA2,stroke-width:3px,color:#fff
    style AGENT fill:#673AB7,stroke:#512DA8,stroke-width:3px,color:#fff
    style LOCK fill:#F44336,stroke:#D32F2F,stroke-width:3px,color:#fff
    style DATA fill:#FF5252,stroke:#D32F2F,stroke-width:2px,color:#fff
```

## 4. Credential Flow Architecture

```mermaid
graph TB
    subgraph "Credential Sources"
        OAUTH[OAuth Providers<br/>Google, Slack, GitHub, Notion]
        MANUAL[Manual Entry<br/>API Keys]
    end
    
    subgraph "Platform Core"
        UI[Frontend UI]
        API[Backend API]
        REDIS[(Redis Store)]
    end
    
    subgraph "Agent Container"
        ENV[Environment Variables]
        JSON[credentials.json]
        MCP[MCP Servers]
    end
    
    OAUTH --> UI
    MANUAL --> UI
    UI --> API
    API --> REDIS
    
    API -.->|At startup| ENV
    API -.->|Mount volume| JSON
    ENV --> MCP
    JSON --> MCP
    
    style OAUTH fill:#4285F4,stroke:#1976D2,stroke-width:2px,color:#fff
    style REDIS fill:#DC382D,stroke:#A41E22,stroke-width:2px,color:#fff
    style MCP fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
```

## 5. Container Security Model

```mermaid
graph TB
    subgraph "Security Layers"
        USER[Non-root User<br/>developer:1000]
        CAP[Capabilities<br/>DROP: ALL<br/>ADD: NET_BIND_SERVICE]
        SEC[Security Options<br/>no-new-privileges]
        NET[Network Isolation<br/>172.28.0.0/16]
    end
    
    subgraph "Resource Controls"
        CPU[CPU Limits]
        MEM[Memory Limits]
        TMPFS[tmpfs /tmp<br/>noexec,nosuid]
    end
    
    subgraph "Data Protection"
        VOL[Encrypted Volumes]
        AUDIT[Audit Logging]
        TLS[TLS Communication]
    end
    
    USER --> CAP
    CAP --> SEC
    SEC --> NET
    
    NET --> CPU
    CPU --> MEM
    MEM --> TMPFS
    
    TMPFS --> VOL
    VOL --> AUDIT
    AUDIT --> TLS
    
    style USER fill:#E91E63,stroke:#C2185B,stroke-width:2px,color:#fff
    style VOL fill:#795548,stroke:#5D4037,stroke-width:2px,color:#fff
    style AUDIT fill:#FFB74D,stroke:#F57C00,stroke-width:2px,color:#000
```

## 6. Agent Configuration System

```mermaid
graph LR
    subgraph "Configuration Sources"
        YAML[YAML Template<br/>config/agent-templates/]
        UI[Web UI<br/>Configuration]
    end
    
    subgraph "Configuration Processing"
        API[Backend API]
        VALID[Validator]
        MERGE[Config Merger]
    end
    
    subgraph "Container Creation"
        DOCKER[Docker SDK]
        ENV[Environment Vars]
        VOL[Volume Mounts]
        PORT[Port Mapping]
    end
    
    YAML --> API
    UI --> API
    API --> VALID
    VALID --> MERGE
    MERGE --> DOCKER
    
    DOCKER --> ENV
    DOCKER --> VOL  
    DOCKER --> PORT
    
    style YAML fill:#FFC107,stroke:#F57F17,stroke-width:2px,color:#000
    style DOCKER fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
```

## 7. Why Trinity: The Standardization Advantage

```mermaid
graph TB
    subgraph "Without Trinity"
        U1A[User 1 Setup]
        U2A[User 2 Setup]
        U3A[User 3 Setup]
        
        PROB1[Different Claude<br/>Versions]
        PROB2[Inconsistent<br/>Configurations]
        PROB3[Data Mixing<br/>Risk]
        PROB4[Manual<br/>Setup]
    end
    
    subgraph "With Trinity"
        TRINITY[Trinity Platform]
        
        subgraph "Standardized Layer"
            STD[Same Claude Code<br/>Version for All]
            ISO[Complete Data<br/>Isolation]
            AUTO[Automated<br/>Deployment]
        end
        
        U1B[User 1<br/>Instance]
        U2B[User 2<br/>Instance]
        U3B[User 3<br/>Instance]
    end
    
    U1A --> PROB1
    U2A --> PROB2
    U3A --> PROB3
    U1A --> PROB4
    
    TRINITY --> STD
    STD --> U1B
    STD --> U2B
    STD --> U3B
    
    STD --> ISO
    STD --> AUTO
    
    style PROB1 fill:#F44336,stroke:#D32F2F,stroke-width:2px,color:#fff
    style PROB2 fill:#F44336,stroke:#D32F2F,stroke-width:2px,color:#fff
    style PROB3 fill:#FF5252,stroke:#D32F2F,stroke-width:3px,color:#fff
    style STD fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style ISO fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
```

## 8. User Journey: Creating an Isolated Agent

```mermaid
sequenceDiagram
    participant U as User
    participant WEB as Web UI
    participant API as Trinity API
    participant BASE as Base Image
    participant AGENT as Claude Code Agent
    participant DATA as User Data Volume
    
    U->>WEB: Login to Trinity
    WEB->>API: Authenticate User
    API-->>WEB: JWT Token
    
    U->>WEB: Create New Agent
    WEB->>API: POST /api/agents
    
    API->>BASE: Pull standardized image
    API->>DATA: Create isolated volume
    API->>AGENT: Launch container
    
    Note over AGENT: Claude Code v2.0.37<br/>Same version for all users
    
    AGENT->>DATA: Mount user workspace
    Note over DATA: Data locked to this user only
    
    API-->>WEB: Agent ready
    WEB-->>U: Access your agent
    
    U->>AGENT: Work with data
    Note over AGENT,DATA: All work isolated<br/>No cross-contamination
```

## 9. Phase Implementation Status

```mermaid
graph LR
    subgraph "Completed Phases"
        P1[Phase 1<br/>Base Infrastructure<br/>✅]
        P2[Phase 2<br/>Web Interface<br/>✅]
        P3[Phase 3<br/>Security<br/>✅]
        P35[Phase 3.5<br/>Credentials<br/>✅]
    end
    
    subgraph "Ready to Implement"
        P4[Phase 4<br/>Multi-Agent<br/>🔄]
    end
    
    subgraph "Future Phases"
        P5[Phase 5<br/>Integration<br/>Expansion]
    end
    
    P1 --> P2
    P2 --> P3
    P3 --> P35
    P35 --> P4
    P4 --> P5
    
    style P1 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style P2 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style P3 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style P35 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style P4 fill:#FFC107,stroke:#F57F17,stroke-width:2px,color:#000
    style P5 fill:#E0E0E0,stroke:#9E9E9E,stroke-width:2px,color:#000
```

## 10. Docker Compose Service Dependencies

```mermaid
graph BT
    FRONT[frontend<br/>:3000]
    BACK[backend<br/>:8000]
    REDIS[redis<br/>:6379]
    AUDIT[audit-logger<br/>:8001]

    FRONT --> BACK
    BACK --> REDIS
    BACK --> AUDIT

    style FRONT fill:#4FC3F7,stroke:#0288D1,stroke-width:2px,color:#000
    style BACK fill:#66BB6A,stroke:#388E3C,stroke-width:2px,color:#000
    style REDIS fill:#DC382D,stroke:#A41E22,stroke-width:2px,color:#fff
    style AUDIT fill:#FFB74D,stroke:#F57C00,stroke-width:2px,color:#000
```

## Key Design Principles

1. **Standardized Claude Code Layer**: Every user gets the exact same Claude Code version and base configuration
2. **Complete Data Isolation**: Each user's data is locked within their container - no cross-access possible
3. **Per-User Instances**: Every user works with their own dedicated agent instance
4. **Universal Base Image**: One standardized image ensures consistency across all deployments
5. **Automated Deployment**: Users get working environments without manual setup
6. **Credential Isolation**: Each instance has its own credentials, never shared
7. **Resource Boundaries**: CPU, memory, and network isolation per instance

## The Core Innovation

Trinity solves the fundamental problem of AI agent deployment:
- **Without Trinity**: Each user manually sets up Claude Code, risks data mixing, faces version inconsistencies
- **With Trinity**: Standardized, isolated, per-user Claude Code instances with locked data boundaries

Every user gets their own "Claude Code in a box" - same version, same capabilities, but completely isolated data and credentials.
