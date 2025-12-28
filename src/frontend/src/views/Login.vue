<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
          Trinity
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
          Sign in to manage your agents
        </p>
      </div>

      <!-- Loading State (detecting mode or authenticating) -->
      <div v-if="isLoading" class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-4 text-gray-600 dark:text-gray-400">{{ loadingMessage }}</p>
      </div>

      <!-- Error State -->
      <div v-else-if="authError" class="bg-white dark:bg-gray-800 rounded-lg shadow-lg dark:shadow-gray-900 p-8">
        <div class="text-center">
          <div class="text-red-500 text-5xl mb-4">⚠️</div>
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-4">Access Denied</h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">{{ authError }}</p>
          <button
            @click="handleRetry"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>

      <!-- Login Forms -->
      <div v-else class="mt-8 space-y-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg dark:shadow-gray-900 p-8">

        <!-- Email Authentication (Default - Phase 12.4) -->
        <div v-if="authStore.emailAuthEnabled && !showDevLogin && !showAuth0Login">
          <!-- Step 1: Enter Email -->
          <div v-if="!codeSent">
            <form @submit.prevent="handleRequestCode" class="space-y-4">
              <div>
                <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Email Address
                </label>
                <input
                  id="email"
                  v-model="emailInput"
                  type="email"
                  required
                  autocomplete="email"
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                  placeholder="you@example.com"
                />
              </div>

              <button
                type="submit"
                :disabled="loginLoading || !emailInput"
                class="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                {{ loginLoading ? 'Sending code...' : 'Send Verification Code' }}
              </button>
            </form>
          </div>

          <!-- Step 2: Enter Code -->
          <div v-else>
            <div class="mb-4">
              <p class="text-sm text-gray-600 dark:text-gray-400">
                📧 We sent a 6-digit code to <strong class="text-gray-900 dark:text-white">{{ emailInput }}</strong>
              </p>
              <p v-if="countdown > 0" class="text-xs text-gray-500 dark:text-gray-500 mt-1">
                Code expires in {{ formatTime(countdown) }}
              </p>
            </div>

            <form @submit.prevent="handleVerifyCode" class="space-y-4">
              <div>
                <label for="code" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Verification Code
                </label>
                <input
                  id="code"
                  v-model="codeInput"
                  type="text"
                  required
                  maxlength="6"
                  pattern="[0-9]{6}"
                  autocomplete="one-time-code"
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-center text-2xl tracking-widest placeholder-gray-400 dark:placeholder-gray-500"
                  placeholder="000000"
                />
              </div>

              <button
                type="submit"
                :disabled="loginLoading || codeInput.length !== 6"
                class="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                {{ loginLoading ? 'Verifying...' : 'Verify & Sign In' }}
              </button>

              <button
                type="button"
                @click="handleBackToEmail"
                class="w-full text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
              >
                ← Back to email
              </button>
            </form>
          </div>

          <!-- Alternative Login Methods -->
          <div v-if="!codeSent && (authStore.devModeEnabled || authStore.auth0Configured)" class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <p class="text-xs text-center text-gray-500 dark:text-gray-500 mb-3">Or sign in with</p>
            <div class="space-y-2">
              <button
                v-if="authStore.devModeEnabled"
                @click="showDevLogin = true"
                class="w-full text-sm py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                🔧 Developer Mode
              </button>
              <button
                v-if="authStore.auth0Configured"
                @click="showAuth0Login = true"
                class="w-full text-sm py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <svg class="w-4 h-4 inline-block mr-1" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Google
              </button>
            </div>
          </div>
        </div>

        <!-- Dev Mode: Username/Password Form -->
        <div v-else-if="authStore.devModeEnabled && (showDevLogin || !authStore.emailAuthEnabled)">
          <div class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p class="text-sm text-yellow-800 dark:text-yellow-300 flex items-center">
              <span class="mr-2">🔧</span>
              Development Mode - Local authentication enabled
            </p>
          </div>

          <form @submit.prevent="handleDevLogin" class="space-y-4">
            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
              <input
                id="username"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                placeholder="admin"
              />
            </div>

            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
              <input
                id="password"
                v-model="password"
                type="password"
                required
                autocomplete="current-password"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              :disabled="loginLoading || !username || !password"
              class="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
            >
              {{ loginLoading ? 'Signing in...' : 'Sign In' }}
            </button>
          </form>

          <button
            v-if="authStore.emailAuthEnabled"
            @click="showDevLogin = false"
            class="w-full mt-4 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
          >
            ← Back to email login
          </button>
        </div>

        <!-- Production Mode: Google OAuth Only -->
        <div v-else-if="showAuth0Login || (!authStore.emailAuthEnabled && !authStore.devModeEnabled)">
          <button
            @click="handleGoogleLogin"
            :disabled="loginLoading"
            class="group relative w-full flex justify-center items-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
          >
            <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            {{ loginLoading ? 'Signing in...' : 'Sign in with Google' }}
          </button>

          <div class="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            <p>Access restricted to <span class="font-semibold">@{{ authStore.allowedDomain }}</span> accounts only</p>
          </div>

          <button
            v-if="authStore.emailAuthEnabled"
            @click="showAuth0Login = false"
            class="w-full mt-4 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
          >
            ← Back to email login
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// Auth0 is always available (plugin always loaded)
// In dev mode, we just don't use it
const auth0 = useAuth0()

// Local state for dev mode form
const username = ref('')
const password = ref('')
const loginLoading = ref(false)
const loadingMessage = ref('Checking authentication...')
const auth0Error = ref(null)

// Email authentication state (Phase 12.4)
const emailInput = ref('')
const codeInput = ref('')
const codeSent = ref(false)
const countdown = ref(0)
const countdownInterval = ref(null)

// UI state for switching between login methods
const showDevLogin = ref(false)
const showAuth0Login = ref(false)

// Computed
const isLoading = computed(() => {
  // Still detecting mode
  if (!authStore.modeDetected) return true
  // Auth store is loading
  if (authStore.isLoading) return true
  // Auth0 is loading (production mode only)
  if (!authStore.devModeEnabled && auth0.isLoading.value) return true
  return false
})

const authError = computed(() => {
  return authStore.authError || auth0Error.value
})

// Format countdown time (MM:SS)
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// Start countdown timer
const startCountdown = (seconds) => {
  countdown.value = seconds
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
  }
  countdownInterval.value = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(countdownInterval.value)
      countdownInterval.value = null
    }
  }, 1000)
}

// Cleanup countdown on unmount
onUnmounted(() => {
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
  }
})

// Email authentication handlers (Phase 12.4)
const handleRequestCode = async () => {
  loginLoading.value = true
  authStore.clearError()

  const result = await authStore.requestEmailCode(emailInput.value)
  if (result.success) {
    codeSent.value = true
    codeInput.value = ''
    startCountdown(result.expiresInSeconds || 600)
  }

  loginLoading.value = false
}

const handleVerifyCode = async () => {
  loginLoading.value = true
  authStore.clearError()

  const success = await authStore.verifyEmailCode(emailInput.value, codeInput.value)
  if (success) {
    router.push('/')
  }

  loginLoading.value = false
}

const handleBackToEmail = () => {
  codeSent.value = false
  codeInput.value = ''
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
    countdownInterval.value = null
  }
  countdown.value = 0
}

// Process authenticated Auth0 user
const processAuthenticatedUser = async () => {
  if (!auth0.user.value?.email) {
    console.log('⏳ Waiting for user profile with email...')
    return false
  }

  loadingMessage.value = 'Validating access...'
  const success = await authStore.handleAuth0Callback(
    auth0.user.value,
    auth0.getAccessTokenSilently
  )
  if (success) {
    router.push('/')
  }
  return success
}

// Initialize on mount
onMounted(async () => {
  // Wait for mode detection (happens in initializeAuth)
  if (!authStore.modeDetected) {
    await authStore.detectAuthMode()
  }

  // If already authenticated, redirect to dashboard
  if (authStore.isAuthenticated) {
    router.push('/')
    return
  }

  // In production mode, set up Auth0 watchers
  if (!authStore.devModeEnabled) {
    // Watch for user profile changes
    watch(() => auth0.user.value?.email, async (email) => {
      if (email && auth0.isAuthenticated.value) {
        await processAuthenticatedUser()
      }
    })

    // Watch for authentication state changes
    watch(() => auth0.isAuthenticated.value, async (isAuth) => {
      if (isAuth && auth0.user.value?.email) {
        await processAuthenticatedUser()
      }
    })

    // If already authenticated with full profile, process now
    if (auth0.isAuthenticated.value && auth0.user.value?.email) {
      await processAuthenticatedUser()
    }
  }
})

// Handle dev mode login
const handleDevLogin = async () => {
  loginLoading.value = true
  authStore.clearError()
  auth0Error.value = null

  const success = await authStore.loginWithCredentials(username.value, password.value)
  if (success) {
    router.push('/')
  }

  loginLoading.value = false
}

// Handle Google OAuth login (production mode)
const handleGoogleLogin = async () => {
  loginLoading.value = true
  authStore.clearError()
  auth0Error.value = null

  try {
    await auth0.loginWithRedirect()
  } catch (error) {
    console.error('Google login error:', error)
    auth0Error.value = 'Failed to initiate Google login: ' + error.message
  } finally {
    loginLoading.value = false
  }
}

// Handle retry after error
const handleRetry = () => {
  authStore.clearError()
  auth0Error.value = null
  codeSent.value = false
  codeInput.value = ''
  emailInput.value = ''
  handleBackToEmail()

  if (!authStore.devModeEnabled && !authStore.emailAuthEnabled) {
    auth0.logout({
      logoutParams: {
        returnTo: window.location.origin
      }
    })
  }
}
</script>
