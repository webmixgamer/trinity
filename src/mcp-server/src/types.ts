// Types for Trinity API responses

export interface Agent {
  name: string;
  type: string;
  status: string;
  port: number;  // SSH port only - UI no longer exposed externally
  created: string;
  resources: {
    cpu: string;
    memory: string;
  };
  container_id?: string;
}

export interface AgentConfig {
  name: string;
  type?: string;
  base_image?: string;
  resources?: {
    cpu: string;
    memory: string;
  };
  tools?: string[];
  mcp_servers?: string[];
  custom_instructions?: string;
  port?: number;  // SSH port - ui_port removed for security
  template?: string;
}

export interface ChatResponse {
  response: string;
  timestamp: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface Template {
  id: string;
  display_name: string;
  description: string;
  mcp_servers: string[];
  resources: {
    cpu: string;
    memory: string;
  };
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// Agent-to-Agent Collaboration Types

/**
 * MCP Authentication Context
 * Extends Record<string, unknown> to satisfy FastMCP's session type requirements
 */
export interface McpAuthContext extends Record<string, unknown> {
  userId: string;        // Username of the key owner
  userEmail?: string;    // Email of the key owner
  keyName: string;       // Name of the MCP API key
  agentName?: string;    // Agent name if scope is 'agent' or 'system' (for agent-to-agent)
  scope: "user" | "agent" | "system"; // Key scope: user=human, agent=regular agent, system=system agent (bypasses all permissions)
  mcpApiKey?: string;    // The actual MCP API key (for user-scoped requests to Trinity backend)
}

export interface AgentAccessInfo {
  name: string;
  owner: string;         // Owner username
  is_shared: boolean;    // Whether agent is shared
}

export interface AgentAccessCheckResult {
  allowed: boolean;
  reason?: string;       // Denial reason if not allowed
}
