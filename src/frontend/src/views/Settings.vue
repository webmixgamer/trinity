<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-4xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            System-wide configuration for the Trinity platform
          </p>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-900 p-8 text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p class="mt-4 text-gray-500 dark:text-gray-400">Loading settings...</p>
        </div>

        <!-- Settings Content -->
        <div v-else class="space-y-6">
          <!-- API Keys Section -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">API Keys</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Configure API keys required for agent operation.
              </p>
            </div>

            <div class="px-6 py-4">
              <div class="space-y-4">
                <!-- Anthropic API Key -->
                <div>
                  <label for="anthropic-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Anthropic API Key
                  </label>
                  <div class="mt-1 flex gap-2">
                    <div class="relative flex-1">
                      <input
                        :type="showApiKey ? 'text' : 'password'"
                        id="anthropic-key"
                        v-model="anthropicKey"
                        :placeholder="anthropicKeyStatus.configured ? anthropicKeyStatus.masked : 'sk-ant-...'"
                        :disabled="savingApiKey"
                        class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                      />
                      <button
                        type="button"
                        @click="showApiKey = !showApiKey"
                        class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        <svg v-if="showApiKey" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                        </svg>
                        <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </div>
                    <button
                      @click="testApiKey"
                      :disabled="!anthropicKey || testingApiKey"
                      class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="testingApiKey" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Test
                    </button>
                    <button
                      @click="saveApiKey"
                      :disabled="!anthropicKey || savingApiKey"
                      class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="savingApiKey" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Save
                    </button>
                  </div>
                  <!-- Status/Result -->
                  <div class="mt-2 flex items-center text-sm">
                    <template v-if="apiKeyTestResult !== null">
                      <svg v-if="apiKeyTestResult" class="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                      <svg v-else class="h-4 w-4 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span :class="apiKeyTestResult ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                        {{ apiKeyTestMessage }}
                      </span>
                    </template>
                    <template v-else-if="anthropicKeyStatus.configured">
                      <svg class="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                      <span class="text-green-600 dark:text-green-400">
                        Configured
                        <span class="text-gray-500 dark:text-gray-400">
                          ({{ anthropicKeyStatus.source === 'settings' ? 'from settings' : 'from environment' }})
                        </span>
                      </span>
                    </template>
                    <template v-else>
                      <svg class="h-4 w-4 text-amber-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span class="text-amber-600 dark:text-amber-400">
                        Not configured - required for agents
                      </span>
                    </template>
                  </div>
                  <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Required for agents to use Claude. Get your key at
                    <a href="https://console.anthropic.com" target="_blank" class="text-indigo-600 dark:text-indigo-400 hover:underline">
                      console.anthropic.com
                    </a>
                  </p>
                </div>

                <!-- GitHub Personal Access Token -->
                <div class="mt-6">
                  <label for="github-pat" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    GitHub Personal Access Token (PAT)
                  </label>
                  <div class="mt-1 flex gap-2">
                    <div class="relative flex-1">
                      <input
                        :type="showGithubPat ? 'text' : 'password'"
                        id="github-pat"
                        v-model="githubPat"
                        :placeholder="githubPatStatus.configured ? githubPatStatus.masked : 'ghp_... or github_pat_...'"
                        :disabled="savingGithubPat"
                        class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                      />
                      <button
                        type="button"
                        @click="showGithubPat = !showGithubPat"
                        class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        <svg v-if="showGithubPat" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                        </svg>
                        <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </div>
                    <button
                      @click="testGithubPat"
                      :disabled="!githubPat || testingGithubPat"
                      class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="testingGithubPat" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Test
                    </button>
                    <button
                      @click="saveGithubPat"
                      :disabled="!githubPat || savingGithubPat"
                      class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="savingGithubPat" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Save
                    </button>
                  </div>
                  <!-- Status/Result -->
                  <div class="mt-2 flex items-center text-sm">
                    <template v-if="githubPatTestResult !== null">
                      <svg v-if="githubPatTestResult" class="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                      <svg v-else class="h-4 w-4 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span :class="githubPatTestResult ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                        {{ githubPatTestMessage }}
                      </span>
                    </template>
                    <template v-else-if="githubPatStatus.configured">
                      <svg class="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                      <span class="text-green-600 dark:text-green-400">
                        Configured
                        <span class="text-gray-500 dark:text-gray-400">
                          ({{ githubPatStatus.source === 'settings' ? 'from settings' : 'from environment' }})
                        </span>
                      </span>
                    </template>
                    <template v-else>
                      <svg class="h-4 w-4 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span class="text-gray-600 dark:text-gray-400">
                        Optional - required for GitHub repository initialization
                      </span>
                    </template>
                  </div>
                  <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Required for creating and pushing agents to GitHub repositories. Get your token at
                    <a href="https://github.com/settings/tokens/new" target="_blank" class="text-indigo-600 dark:text-indigo-400 hover:underline">
                      github.com/settings/tokens
                    </a>
                    with <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">repo</code> scope.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Trinity Prompt Section -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Trinity Prompt</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Custom instructions that are injected into all agents' CLAUDE.md at startup.
                Changes apply to newly started or restarted agents.
              </p>
            </div>

            <div class="px-6 py-4">
              <div class="space-y-4">
                <div>
                  <label for="trinity-prompt" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Custom Instructions
                  </label>
                  <div class="mt-1">
                    <textarea
                      id="trinity-prompt"
                      v-model="trinityPrompt"
                      rows="15"
                      class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border border-gray-300 dark:border-gray-600 rounded-md font-mono bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                      placeholder="Enter custom instructions for all agents...

Example:
- Always use TypeScript for new files
- Follow the project's coding conventions
- Check for security vulnerabilities before committing"
                      :disabled="saving"
                    ></textarea>
                  </div>
                  <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    This content will appear under a "## Custom Instructions" section in each agent's CLAUDE.md.
                    Supports Markdown formatting.
                  </p>
                </div>

                <!-- Character Count -->
                <div class="flex justify-between text-sm text-gray-500 dark:text-gray-400">
                  <span>{{ trinityPrompt.length }} characters</span>
                  <span v-if="hasChanges" class="text-amber-600 dark:text-amber-400">Unsaved changes</span>
                </div>

                <!-- Action Buttons -->
                <div class="flex justify-end space-x-3">
                  <button
                    @click="clearPrompt"
                    :disabled="saving || !trinityPrompt"
                    class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Clear
                  </button>
                  <button
                    @click="savePrompt"
                    :disabled="saving || !hasChanges"
                    class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ saving ? 'Saving...' : 'Save Changes' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Email Whitelist Section (Phase 12.4) -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Email Whitelist</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Manage whitelisted emails for email-based authentication.
                Only whitelisted users can login with email verification codes.
              </p>
            </div>

            <div class="px-6 py-4">
              <div class="space-y-4">
                <!-- Add Email Form -->
                <div class="flex gap-2">
                  <input
                    v-model="newEmail"
                    type="email"
                    placeholder="user@example.com"
                    class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white text-sm"
                    :disabled="addingEmail"
                    @keyup.enter="addEmailToWhitelist"
                  />
                  <button
                    @click="addEmailToWhitelist"
                    :disabled="!newEmail || addingEmail"
                    class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="addingEmail" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Add Email
                  </button>
                </div>

                <!-- Whitelist Table -->
                <div class="mt-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                  <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead class="bg-gray-50 dark:bg-gray-700">
                      <tr>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Email
                        </th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Source
                        </th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          Added
                        </th>
                        <th scope="col" class="relative px-6 py-3">
                          <span class="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      <tr v-if="loadingWhitelist">
                        <td colspan="4" class="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto"></div>
                        </td>
                      </tr>
                      <tr v-else-if="emailWhitelist.length === 0">
                        <td colspan="4" class="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                          No whitelisted emails. Add one above to get started.
                        </td>
                      </tr>
                      <tr v-else v-for="entry in emailWhitelist" :key="entry.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          {{ entry.email }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          <span v-if="entry.source === 'agent_sharing'" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            🤝 Auto (Agent Sharing)
                          </span>
                          <span v-else class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                            ✋ Manual
                          </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {{ formatDate(entry.added_at) }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button
                            @click="removeEmailFromWhitelist(entry.email)"
                            :disabled="removingEmail === entry.email"
                            class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
                          >
                            {{ removingEmail === entry.email ? 'Removing...' : 'Remove' }}
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  💡 Tip: When you share an agent with someone by email, they're automatically added to this whitelist.
                </p>
              </div>
            </div>
          </div>

          <!-- SSH Access Section -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">SSH Access</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Allow generating ephemeral SSH credentials for direct terminal access to agent containers.
              </p>
            </div>

            <div class="px-6 py-4">
              <div class="flex items-center justify-between">
                <div>
                  <label for="ssh-access-toggle" class="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Enable SSH Access
                  </label>
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    When enabled, the MCP tool <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">get_agent_ssh_access</code> can generate temporary SSH credentials.
                  </p>
                </div>
                <button
                  id="ssh-access-toggle"
                  type="button"
                  :class="[
                    sshAccessEnabled ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-600',
                    'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2'
                  ]"
                  :disabled="savingSshAccess"
                  @click="toggleSshAccess"
                >
                  <span
                    :class="[
                      sshAccessEnabled ? 'translate-x-5' : 'translate-x-0',
                      'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out'
                    ]"
                  />
                </button>
              </div>
            </div>
          </div>

          <!-- Skills Library Section -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Skills Library</h2>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Configure a GitHub repository containing reusable agent skills.
                Skills are stored in <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">.claude/skills/&lt;name&gt;/SKILL.md</code>.
              </p>
            </div>

            <div class="px-6 py-4 space-y-4">
              <!-- Repository URL -->
              <div>
                <label for="skills-library-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Repository URL
                </label>
                <div class="mt-1">
                  <input
                    type="text"
                    id="skills-library-url"
                    v-model="skillsLibraryUrl"
                    placeholder="github.com/owner/skills-library"
                    class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white text-sm"
                  />
                </div>
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Use format: <code>github.com/owner/repo</code> or <code>https://github.com/owner/repo</code>
                </p>
              </div>

              <!-- Branch -->
              <div>
                <label for="skills-library-branch" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Branch
                </label>
                <div class="mt-1">
                  <input
                    type="text"
                    id="skills-library-branch"
                    v-model="skillsLibraryBranch"
                    placeholder="main"
                    class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white text-sm"
                  />
                </div>
              </div>

              <!-- Status -->
              <div v-if="skillsLibraryStatus.cloned" class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div class="flex items-center justify-between text-sm">
                  <div class="flex items-center gap-4 text-gray-600 dark:text-gray-300">
                    <span>
                      <svg class="h-4 w-4 text-green-500 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                      </svg>
                      {{ skillsLibraryStatus.skill_count }} skills available
                    </span>
                    <span v-if="skillsLibraryStatus.commit_sha">
                      Commit: <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-600 rounded text-xs">{{ skillsLibraryStatus.commit_sha }}</code>
                    </span>
                  </div>
                  <span v-if="skillsLibraryStatus.last_sync" class="text-gray-500 dark:text-gray-400">
                    Last synced: {{ formatDate(skillsLibraryStatus.last_sync) }}
                  </span>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex justify-end gap-3">
                <button
                  @click="syncSkillsLibrary"
                  :disabled="syncingSkillsLibrary || !skillsLibraryUrl"
                  class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg v-if="syncingSkillsLibrary" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <svg v-else class="-ml-1 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {{ syncingSkillsLibrary ? 'Syncing...' : 'Sync Library' }}
                </button>
                <button
                  @click="saveSkillsLibrarySettings"
                  :disabled="savingSkillsLibrary"
                  class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg v-if="savingSkillsLibrary" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {{ savingSkillsLibrary ? 'Saving...' : 'Save Settings' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Info Box -->
          <div class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800 dark:text-blue-300">How it works</h3>
                <div class="mt-2 text-sm text-blue-700 dark:text-blue-400">
                  <ul class="list-disc list-inside space-y-1">
                    <li>The Trinity Prompt is injected into each agent's CLAUDE.md when the agent starts</li>
                    <li>Existing agents need to be restarted to receive the updated prompt</li>
                    <li>The prompt appears as a "## Custom Instructions" section after the Trinity Planning System section</li>
                    <li>Use Markdown formatting for structured instructions</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Error Display -->
        <div v-if="error" class="mt-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800 dark:text-red-300">Error</h3>
              <p class="mt-1 text-sm text-red-700 dark:text-red-400">{{ error }}</p>
            </div>
          </div>
        </div>

        <!-- Success Message -->
        <div v-if="showSuccess" class="mt-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium text-green-800 dark:text-green-300">Settings saved successfully!</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import NavBar from '../components/NavBar.vue'

const router = useRouter()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const showSuccess = ref(false)

// Email whitelist state (Phase 12.4)
const emailWhitelist = ref([])
const newEmail = ref('')
const addingEmail = ref(false)
const removingEmail = ref(null)
const loadingWhitelist = ref(false)

const trinityPrompt = ref('')
const originalPrompt = ref('')

// API Key state
const anthropicKey = ref('')
const showApiKey = ref(false)
const testingApiKey = ref(false)
const savingApiKey = ref(false)
const apiKeyTestResult = ref(null)
const apiKeyTestMessage = ref('')
const anthropicKeyStatus = ref({
  configured: false,
  masked: null,
  source: null
})

// GitHub PAT state
const githubPat = ref('')
const showGithubPat = ref(false)
const testingGithubPat = ref(false)
const savingGithubPat = ref(false)
const githubPatTestResult = ref(null)
const githubPatTestMessage = ref('')
const githubPatStatus = ref({
  configured: false,
  masked: null,
  source: null
})

// SSH Access state
const sshAccessEnabled = ref(false)
const savingSshAccess = ref(false)

// Skills Library state
const skillsLibraryUrl = ref('')
const skillsLibraryBranch = ref('main')
const skillsLibraryStatus = ref({
  configured: false,
  cloned: false,
  skill_count: 0,
  commit_sha: null,
  last_sync: null
})
const syncingSkillsLibrary = ref(false)
const savingSkillsLibrary = ref(false)

const hasChanges = computed(() => {
  return trinityPrompt.value !== originalPrompt.value
})

async function loadSettings() {
  loading.value = true
  error.value = null

  try {
    await settingsStore.fetchSettings()
    trinityPrompt.value = settingsStore.trinityPrompt || ''
    originalPrompt.value = trinityPrompt.value

    // Load API keys status
    await loadApiKeyStatus()
  } catch (e) {
    if (e.response?.status === 403) {
      error.value = 'Access denied. Admin privileges required.'
      router.push('/')
    } else {
      error.value = e.response?.data?.detail || 'Failed to load settings'
    }
  } finally {
    loading.value = false
  }
}

async function loadApiKeyStatus() {
  try {
    const response = await axios.get('/api/settings/api-keys')
    anthropicKeyStatus.value = response.data.anthropic || { configured: false }
    githubPatStatus.value = response.data.github || { configured: false }
  } catch (e) {
    console.error('Failed to load API key status:', e)
  }
}

async function testApiKey() {
  if (!anthropicKey.value) return

  testingApiKey.value = true
  apiKeyTestResult.value = null
  apiKeyTestMessage.value = ''

  try {
    const response = await axios.post('/api/settings/api-keys/anthropic/test', {
      api_key: anthropicKey.value
    })

    apiKeyTestResult.value = response.data.valid
    apiKeyTestMessage.value = response.data.valid ? 'API key is valid!' : (response.data.error || 'Invalid API key')
  } catch (e) {
    apiKeyTestResult.value = false
    apiKeyTestMessage.value = e.response?.data?.detail || 'Failed to test API key'
  } finally {
    testingApiKey.value = false
  }
}

async function saveApiKey() {
  if (!anthropicKey.value) return

  savingApiKey.value = true
  error.value = null

  try {
    const response = await axios.put('/api/settings/api-keys/anthropic', {
      api_key: anthropicKey.value
    })

    // Update status
    anthropicKeyStatus.value = {
      configured: true,
      masked: response.data.masked,
      source: 'settings'
    }

    // Clear input and show success
    anthropicKey.value = ''
    apiKeyTestResult.value = null
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to save API key'
  } finally {
    savingApiKey.value = false
  }
}

async function testGithubPat() {
  if (!githubPat.value) return

  testingGithubPat.value = true
  githubPatTestResult.value = null
  githubPatTestMessage.value = ''

  try {
    const response = await axios.post('/api/settings/api-keys/github/test', {
      api_key: githubPat.value
    })

    githubPatTestResult.value = response.data.valid
    if (response.data.valid) {
      const tokenType = response.data.token_type || 'unknown'
      const hasRepoAccess = response.data.has_repo_access || false

      let message = `Valid! GitHub user: ${response.data.username}`

      if (tokenType === 'fine-grained') {
        message += hasRepoAccess
          ? '. ✓ Fine-grained PAT with repository permissions'
          : '. ⚠️ Missing repository permissions (need Administration + Contents)'
      } else {
        message += hasRepoAccess
          ? '. ✓ Has repo scope'
          : '. ⚠️ Missing repo scope'
      }

      githubPatTestMessage.value = message
    } else {
      githubPatTestMessage.value = response.data.error || 'Invalid PAT'
    }
  } catch (e) {
    githubPatTestResult.value = false
    githubPatTestMessage.value = e.response?.data?.detail || 'Failed to test PAT'
  } finally {
    testingGithubPat.value = false
  }
}

async function saveGithubPat() {
  if (!githubPat.value) return

  savingGithubPat.value = true
  error.value = null

  try {
    const response = await axios.put('/api/settings/api-keys/github', {
      api_key: githubPat.value
    })

    // Update status
    githubPatStatus.value = {
      configured: true,
      masked: response.data.masked,
      source: 'settings'
    }

    // Clear input and show success
    githubPat.value = ''
    githubPatTestResult.value = null
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to save GitHub PAT'
  } finally {
    savingGithubPat.value = false
  }
}

async function savePrompt() {
  saving.value = true
  error.value = null
  showSuccess.value = false

  try {
    if (trinityPrompt.value.trim()) {
      await settingsStore.updateSetting('trinity_prompt', trinityPrompt.value)
    } else {
      await settingsStore.deleteSetting('trinity_prompt')
      trinityPrompt.value = ''
    }
    originalPrompt.value = trinityPrompt.value
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to save settings'
  } finally {
    saving.value = false
  }
}

async function clearPrompt() {
  trinityPrompt.value = ''
  await savePrompt()
}

// Email whitelist methods (Phase 12.4)
async function loadEmailWhitelist() {
  loadingWhitelist.value = true
  try {
    const response = await axios.get('/api/settings/email-whitelist', {
      headers: authStore.authHeader
    })
    emailWhitelist.value = response.data.whitelist || []
  } catch (e) {
    console.error('Failed to load email whitelist:', e)
    // Non-fatal error - just log it
  } finally {
    loadingWhitelist.value = false
  }
}

async function addEmailToWhitelist() {
  if (!newEmail.value) return

  addingEmail.value = true
  error.value = null

  try {
    await axios.post('/api/settings/email-whitelist', {
      email: newEmail.value,
      source: 'manual'
    }, {
      headers: authStore.authHeader
    })

    newEmail.value = ''
    await loadEmailWhitelist()
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to add email to whitelist'
  } finally {
    addingEmail.value = false
  }
}

async function removeEmailFromWhitelist(email) {
  if (!confirm(`Remove ${email} from whitelist?`)) return

  removingEmail.value = email
  error.value = null

  try {
    await axios.delete(`/api/settings/email-whitelist/${encodeURIComponent(email)}`, {
      headers: authStore.authHeader
    })

    await loadEmailWhitelist()
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to remove email from whitelist'
  } finally {
    removingEmail.value = null
  }
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  const now = new Date()
  const diffInMs = now - date
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

  if (diffInDays === 0) return 'Today'
  if (diffInDays === 1) return 'Yesterday'
  if (diffInDays < 7) return `${diffInDays} days ago`
  if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`

  return date.toLocaleDateString()
}

// SSH Access methods
async function loadOpsSettings() {
  try {
    const response = await axios.get('/api/settings/ops/config', {
      headers: authStore.authHeader
    })
    sshAccessEnabled.value = response.data.ssh_access_enabled === 'true'
  } catch (e) {
    console.error('Failed to load ops settings:', e)
  }
}

async function toggleSshAccess() {
  savingSshAccess.value = true
  error.value = null

  try {
    const newValue = !sshAccessEnabled.value
    await axios.put('/api/settings/ops/config', {
      settings: {
        ssh_access_enabled: newValue ? 'true' : 'false'
      }
    }, {
      headers: authStore.authHeader
    })

    sshAccessEnabled.value = newValue
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to update SSH access setting'
  } finally {
    savingSshAccess.value = false
  }
}

// Skills Library methods
async function loadSkillsLibrarySettings() {
  try {
    const response = await axios.get('/api/skills/library/status', {
      headers: authStore.authHeader
    })
    skillsLibraryStatus.value = response.data
    skillsLibraryUrl.value = response.data.url || ''
    skillsLibraryBranch.value = response.data.branch || 'main'
  } catch (e) {
    console.error('Failed to load skills library status:', e)
  }
}

async function saveSkillsLibrarySettings() {
  savingSkillsLibrary.value = true
  error.value = null

  try {
    // Save URL setting
    if (skillsLibraryUrl.value.trim()) {
      await settingsStore.updateSetting('skills_library_url', skillsLibraryUrl.value.trim())
    } else {
      await settingsStore.deleteSetting('skills_library_url')
    }

    // Save branch setting
    if (skillsLibraryBranch.value.trim() && skillsLibraryBranch.value !== 'main') {
      await settingsStore.updateSetting('skills_library_branch', skillsLibraryBranch.value.trim())
    } else {
      await settingsStore.deleteSetting('skills_library_branch')
    }

    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to save skills library settings'
  } finally {
    savingSkillsLibrary.value = false
  }
}

async function syncSkillsLibrary() {
  syncingSkillsLibrary.value = true
  error.value = null

  try {
    // Save settings first
    await saveSkillsLibrarySettings()

    // Then sync
    const response = await axios.post('/api/skills/library/sync', {}, {
      headers: authStore.authHeader
    })

    // Reload status
    await loadSkillsLibrarySettings()

    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to sync skills library'
  } finally {
    syncingSkillsLibrary.value = false
  }
}

onMounted(() => {
  // Check if user is admin
  const userData = authStore.user
  // For now, allow access - backend will reject if not admin
  loadSettings()
  loadEmailWhitelist()
  loadOpsSettings()
  loadSkillsLibrarySettings()
})
</script>
