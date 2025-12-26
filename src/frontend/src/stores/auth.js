import { defineStore } from 'pinia'
import axios from 'axios'
import { ALLOWED_DOMAIN } from '../config/auth0'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null,
    user: null,
    isAuthenticated: false,
    isLoading: true,
    authError: null,
    // Auth0 instance will be set from main.js
    auth0: null,
    // Runtime mode detection (from backend)
    devModeEnabled: null,  // null = not yet detected, true/false = detected
    auth0Configured: null,
    emailAuthEnabled: null,  // Email-based authentication (Phase 12.4)
    allowedDomain: 'ability.ai',
    modeDetected: false
  }),

  getters: {
    authHeader() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {}
    },

    userEmail() {
      return this.user?.email || null
    },

    userName() {
      return this.user?.name || this.user?.email || 'User'
    },

    userInitials() {
      const name = this.userName
      if (!name) return '?'
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    },

    userPicture() {
      return this.user?.picture || null
    }
  },

  actions: {
    // Set Auth0 instance from main.js
    setAuth0Instance(auth0) {
      this.auth0 = auth0
    },

    // Detect authentication mode from backend (called before login)
    async detectAuthMode() {
      try {
        const response = await axios.get('/api/auth/mode')
        this.devModeEnabled = response.data.dev_mode_enabled
        this.auth0Configured = response.data.auth0_configured
        this.emailAuthEnabled = response.data.email_auth_enabled || false
        this.allowedDomain = response.data.allowed_domain || 'ability.ai'
        this.modeDetected = true

        // Log auth mode for debugging
        const mode = this.emailAuthEnabled ? 'EMAIL' :
                     this.devModeEnabled ? 'DEV' : 'AUTH0'
        console.log(`🔐 Auth mode: ${mode}`)
        return this.devModeEnabled
      } catch (error) {
        console.error('Failed to detect auth mode:', error)
        // Default to email auth if detection fails
        this.devModeEnabled = false
        this.auth0Configured = true
        this.emailAuthEnabled = true
        this.modeDetected = true
        return false
      }
    },

    // Initialize auth - called on app startup
    async initializeAuth() {
      this.isLoading = true
      this.authError = null

      // First detect auth mode from backend
      await this.detectAuthMode()

      const storedToken = localStorage.getItem('token')
      const storedUser = localStorage.getItem('auth0_user')

      if (storedToken && storedUser) {
        try {
          const user = JSON.parse(storedUser)

          // Check token mode matches current backend mode
          // Parse JWT to get mode claim (without verification - just for client-side check)
          const tokenPayload = this.parseJwtPayload(storedToken)
          const tokenMode = tokenPayload?.mode

          // If token is dev mode but backend is prod mode, clear credentials
          if (tokenMode === 'dev' && !this.devModeEnabled) {
            console.log('🔐 Clearing dev mode token (backend is now in production mode)')
            localStorage.removeItem('token')
            localStorage.removeItem('auth0_user')
          }
          // If token is prod mode but backend is dev mode, still allow (less restrictive)
          else {
            // Restore the session from localStorage
            this.token = storedToken
            this.user = user
            this.isAuthenticated = true
            this.setupAxiosAuth()
            console.log('✅ Session restored for:', user.email || user.name)
          }
        } catch (e) {
          console.warn('Failed to parse stored user, clearing credentials')
          localStorage.removeItem('token')
          localStorage.removeItem('auth0_user')
        }
      }

      this.isLoading = false
    },

    // Parse JWT payload without verification (client-side mode check only)
    parseJwtPayload(token) {
      try {
        const base64Url = token.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const jsonPayload = decodeURIComponent(
          atob(base64).split('').map(c =>
            '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
          ).join('')
        )
        return JSON.parse(jsonPayload)
      } catch (e) {
        return null
      }
    },

    // Handle Auth0 callback after OAuth redirect
    async handleAuth0Callback(auth0User, getAccessToken) {
      this.isLoading = true
      this.authError = null

      try {
        // Basic validation first
        if (!auth0User.email) {
          throw new Error('No email found in user profile')
        }

        const emailDomain = auth0User.email.split('@')[1]
        if (emailDomain !== ALLOWED_DOMAIN) {
          throw new Error(`Access restricted to @${ALLOWED_DOMAIN} domain users only.`)
        }

        if (!auth0User.email_verified) {
          throw new Error('Please verify your email address before accessing this application.')
        }

        // Get Auth0 access token
        const auth0Token = await getAccessToken()

        // Exchange Auth0 token for backend JWT
        const response = await axios.post('/api/auth/exchange', {
          auth0_token: auth0Token
        })

        const backendToken = response.data.access_token

        // Set auth state with backend token
        this.user = auth0User
        this.token = backendToken
        this.isAuthenticated = true

        // Persist to localStorage
        localStorage.setItem('token', backendToken)
        localStorage.setItem('auth0_user', JSON.stringify(auth0User))

        // Setup axios and cookie
        this.setupAxiosAuth()

        console.log('✅ Auth0 authentication successful for:', auth0User.email)
        return true
      } catch (error) {
        console.error('❌ Auth0 callback error:', error.response?.data?.detail || error.message)
        this.authError = error.response?.data?.detail || error.message
        this.isAuthenticated = false
        this.user = null
        this.token = null
        return false
      } finally {
        this.isLoading = false
      }
    },

    // Setup axios authorization header and cookie for nginx
    setupAxiosAuth() {
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        // Set token as cookie for nginx auth_request to validate agent UI access
        document.cookie = `token=${this.token}; path=/; max-age=1800; SameSite=Strict`
      }
    },

    // Login with username/password (dev mode only)
    // User must provide credentials - they are NOT hardcoded
    async loginWithCredentials(username, password) {
      if (!this.devModeEnabled) {
        this.authError = 'Local login is disabled. Use Sign in with Google.'
        return false
      }

      try {
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)

        const response = await axios.post('/api/token', formData)
        this.token = response.data.access_token

        // Create a dev user profile
        const devUser = {
          sub: `local|${username}`,
          email: `${username}@localhost`,
          name: username,
          picture: 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y',
          email_verified: true
        }

        this.user = devUser
        this.isAuthenticated = true

        localStorage.setItem('token', this.token)
        localStorage.setItem('auth0_user', JSON.stringify(devUser))
        this.setupAxiosAuth()

        console.log('🔧 Dev mode: authenticated as', username)
        return true
      } catch (error) {
        console.error('Dev login failed:', error)
        const detail = error.response?.data?.detail || 'Invalid username or password'
        this.authError = detail
        return false
      }
    },

    // =========================================================================
    // Email-Based Authentication (Phase 12.4)
    // =========================================================================

    // Request a verification code via email
    async requestEmailCode(email) {
      if (!this.emailAuthEnabled) {
        this.authError = 'Email authentication is disabled'
        return { success: false, error: 'Email authentication is disabled' }
      }

      try {
        const response = await axios.post('/api/auth/email/request', { email })
        return {
          success: true,
          message: response.data.message,
          expiresInSeconds: response.data.expires_in_seconds
        }
      } catch (error) {
        console.error('Request email code failed:', error)
        const detail = error.response?.data?.detail || 'Failed to send verification code'
        this.authError = detail
        return { success: false, error: detail }
      }
    },

    // Verify email code and login
    async verifyEmailCode(email, code) {
      if (!this.emailAuthEnabled) {
        this.authError = 'Email authentication is disabled'
        return false
      }

      try {
        const response = await axios.post('/api/auth/email/verify', { email, code })

        this.token = response.data.access_token
        this.user = response.data.user
        this.isAuthenticated = true

        localStorage.setItem('token', this.token)
        localStorage.setItem('auth0_user', JSON.stringify(this.user))
        this.setupAxiosAuth()

        console.log('📧 Email auth: authenticated as', this.user.email)
        return true
      } catch (error) {
        console.error('Verify email code failed:', error)
        const detail = error.response?.data?.detail || 'Invalid or expired verification code'
        this.authError = detail
        return false
      }
    },

    // Logout
    logout(auth0Logout = null) {
      this.token = null
      this.user = null
      this.isAuthenticated = false
      this.authError = null

      localStorage.removeItem('token')
      localStorage.removeItem('auth0_user')
      delete axios.defaults.headers.common['Authorization']

      // Clear the token cookie
      document.cookie = 'token=; path=/; max-age=0'

      // If Auth0 logout function provided and not in dev mode, call it for full logout
      if (auth0Logout && !this.devModeEnabled) {
        auth0Logout({
          logoutParams: {
            returnTo: window.location.origin
          }
        })
      }
    },

    // Clear auth error
    clearError() {
      this.authError = null
    }
  }
})
