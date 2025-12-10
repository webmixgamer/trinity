/**
 * Agent Management Tools
 *
 * MCP tools for managing Trinity agents: list, get, create, delete, start, stop
 */

import { z } from "zod";
import { TrinityClient } from "../client.js";
import type { McpAuthContext } from "../types.js";

/**
 * Create agent management tools with the given client
 * @param client - Base Trinity client (provides base URL, no auth when requireApiKey=true)
 * @param requireApiKey - Whether API key authentication is enabled
 */
export function createAgentTools(
  client: TrinityClient,
  requireApiKey: boolean
) {
  /**
   * Get Trinity client with appropriate authentication
   * When requireApiKey is true, REQUIRES MCP API key from auth context
   * When requireApiKey is false, uses the base client (backward compatibility)
   */
  const getClient = (authContext?: McpAuthContext): TrinityClient => {
    if (requireApiKey) {
      // MCP API key is REQUIRED - no fallback
      if (!authContext?.mcpApiKey) {
        throw new Error("MCP API key authentication required but no API key found in request context");
      }
      // Create new client instance authenticated with user's MCP API key
      const userClient = new TrinityClient(client.getBaseUrl());
      userClient.setToken(authContext.mcpApiKey);
      return userClient;
    }
    // API key auth disabled - use base client (backward compatibility)
    return client;
  };

  return {
    // ========================================================================
    // list_agents - List all agents
    // ========================================================================
    listAgents: {
      name: "list_agents",
      description:
        "List all agents in the Trinity platform with their status, type, and resource allocation. " +
        "Returns an array of agents with details like name, status (running/stopped), ports, and creation time.",
      parameters: z.object({}),
      execute: async (_params: unknown, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const agents = await apiClient.listAgents();

        // Phase 9.10: Filter agents for agent-scoped keys
        // Agent-scoped keys only see permitted agents + self
        if (authContext?.scope === "agent" && authContext?.agentName) {
          const callerAgentName = authContext.agentName;
          const permittedAgents = await apiClient.getPermittedAgents(callerAgentName);

          // Include self and permitted agents
          const allowedNames = new Set([callerAgentName, ...permittedAgents]);
          const filteredAgents = agents.filter((a: { name: string }) => allowedNames.has(a.name));

          console.log(`[list_agents] Agent '${callerAgentName}' filtered: ${filteredAgents.length}/${agents.length} agents visible`);

          return JSON.stringify(filteredAgents, null, 2);
        }

        // User-scoped keys see all accessible agents (existing behavior)
        return JSON.stringify(agents, null, 2);
      },
    },

    // ========================================================================
    // get_agent - Get specific agent details
    // ========================================================================
    getAgent: {
      name: "get_agent",
      description:
        "Get detailed information about a specific agent by name. " +
        "Returns the agent's status, type, port assignments, resource limits, and container ID.",
      parameters: z.object({
        name: z.string().describe("The name of the agent to retrieve"),
      }),
      execute: async ({ name }: { name: string }, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const agent = await apiClient.getAgent(name);
        return JSON.stringify(agent, null, 2);
      },
    },

    // ========================================================================
    // create_agent - Create a new agent
    // ========================================================================
    createAgent: {
      name: "create_agent",
      description:
        "Create a new agent in the Trinity platform. " +
        "You can specify a template to use pre-configured settings, or customize the agent type, resources, and tools. " +
        "The agent will be started automatically after creation.",
      parameters: z.object({
        name: z
          .string()
          .describe(
            "Unique name for the agent. Will be sanitized for Docker compatibility."
          ),
        type: z
          .string()
          .optional()
          .describe(
            "Agent type (e.g., 'business-assistant', 'code-developer'). Default: 'business-assistant'"
          ),
        template: z
          .string()
          .optional()
          .describe(
            "Template ID to use for agent configuration (e.g., 'ruby-social-media-agent'). " +
            "Templates include pre-configured .claude directories, MCP servers, and instructions."
          ),
        resources: z
          .object({
            cpu: z.string().optional().describe("CPU limit (e.g., '2')"),
            memory: z
              .string()
              .optional()
              .describe("Memory limit (e.g., '4g')"),
          })
          .optional()
          .describe("Resource limits for the agent container"),
        tools: z
          .array(z.string())
          .optional()
          .describe("List of tools to enable (e.g., ['filesystem', 'web_search'])"),
        mcp_servers: z
          .array(z.string())
          .optional()
          .describe("MCP servers to configure for the agent"),
        custom_instructions: z
          .string()
          .optional()
          .describe("Custom behavioral instructions for the agent"),
      }),
      execute: async (
        args: {
          name: string;
          type?: string;
          template?: string;
          resources?: { cpu?: string; memory?: string };
          tools?: string[];
          mcp_servers?: string[];
          custom_instructions?: string;
        },
        context: any
      ) => {
        const config = {
          name: args.name,
          type: args.type,
          template: args.template,
          resources: args.resources
            ? {
                cpu: args.resources.cpu || "2",
                memory: args.resources.memory || "4g",
              }
            : undefined,
          tools: args.tools,
          mcp_servers: args.mcp_servers,
          custom_instructions: args.custom_instructions,
        };

        // Get auth context from FastMCP session (set by authenticate callback)
        const authContext = requireApiKey ? context?.session : undefined;
        console.log("[CREATE_AGENT] Auth context:", {
          hasContext: !!context,
          hasSession: !!context?.session,
          hasAuthContext: !!authContext,
          userId: authContext?.userId,
          userEmail: authContext?.userEmail,
          scope: authContext?.scope,
          hasMcpApiKey: !!authContext?.mcpApiKey,
          mcpApiKeyPrefix: authContext?.mcpApiKey?.substring(0, 20),
        });

        const apiClient = getClient(authContext);
        console.log("[CREATE_AGENT] Created API client, calling backend...");

        const agent = await apiClient.createAgent(config);
        console.log("[CREATE_AGENT] Agent created successfully:", agent.name);
        return JSON.stringify(agent, null, 2);
      },
    },

    // ========================================================================
    // delete_agent - Remove an agent
    // ========================================================================
    deleteAgent: {
      name: "delete_agent",
      description:
        "Delete an agent from the Trinity platform. " +
        "This will stop the agent container and remove it. " +
        "Requires admin access. This action is irreversible.",
      parameters: z.object({
        name: z.string().describe("The name of the agent to delete"),
      }),
      execute: async ({ name }: { name: string }, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const result = await apiClient.deleteAgent(name);
        return result.message;
      },
    },

    // ========================================================================
    // start_agent - Start a stopped agent
    // ========================================================================
    startAgent: {
      name: "start_agent",
      description:
        "Start a stopped agent. " +
        "Use this to restart an agent that was previously stopped. " +
        "The agent must already exist in the platform.",
      parameters: z.object({
        name: z.string().describe("The name of the agent to start"),
      }),
      execute: async ({ name }: { name: string }, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const result = await apiClient.startAgent(name);
        return result.message;
      },
    },

    // ========================================================================
    // stop_agent - Stop a running agent
    // ========================================================================
    stopAgent: {
      name: "stop_agent",
      description:
        "Stop a running agent. " +
        "This gracefully stops the agent container but preserves its configuration. " +
        "Use start_agent to restart it later.",
      parameters: z.object({
        name: z.string().describe("The name of the agent to stop"),
      }),
      execute: async ({ name }: { name: string }, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const result = await apiClient.stopAgent(name);
        return result.message;
      },
    },

    // ========================================================================
    // list_templates - List available agent templates
    // ========================================================================
    listTemplates: {
      name: "list_templates",
      description:
        "List all available agent templates. " +
        "Templates provide pre-configured agent setups with .claude directories, MCP servers, and custom instructions. " +
        "Use a template ID with create_agent to quickly spin up a specialized agent.",
      parameters: z.object({}),
      execute: async (_params: unknown, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const templates = await apiClient.listTemplates();
        return JSON.stringify(templates, null, 2);
      },
    },

    // ========================================================================
    // reload_credentials - Reload credentials on a running agent
    // ========================================================================
    reloadCredentials: {
      name: "reload_credentials",
      description:
        "Reload credentials on a running agent. " +
        "This fetches the latest credentials from the Trinity credential store and pushes them to the agent container. " +
        "Use this after adding or updating credentials to apply them without restarting the agent. " +
        "The agent must be running for this to work.",
      parameters: z.object({
        name: z.string().describe("The name of the agent to reload credentials for"),
      }),
      execute: async ({ name }: { name: string }, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const result = await apiClient.reloadCredentials(name);
        return JSON.stringify(result, null, 2);
      },
    },

    // ========================================================================
    // get_credential_status - Get credential status from a running agent
    // ========================================================================
    getCredentialStatus: {
      name: "get_credential_status",
      description:
        "Get the credential status from a running agent. " +
        "Returns information about credential files inside the agent container, " +
        "including whether .env and .mcp.json exist and when they were last modified.",
      parameters: z.object({
        name: z.string().describe("The name of the agent to check credential status for"),
      }),
      execute: async ({ name }: { name: string }, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const status = await apiClient.getCredentialStatus(name);
        return JSON.stringify(status, null, 2);
      },
    },
  };
}
