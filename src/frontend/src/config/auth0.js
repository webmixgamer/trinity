// Auth0 configuration for Trinity Agent Platform
// Configure via environment variables (see .env.example)

// NOTE: Dev mode is now detected at RUNTIME from backend via /api/auth/mode
// The VITE_DEV_MODE env var is no longer used for auth mode switching

// Allowed email domain for access restriction (optional - leave empty to allow all)
export const ALLOWED_DOMAIN = import.meta.env.VITE_AUTH0_ALLOWED_DOMAIN || ''

// Auth0 configuration
// Set VITE_AUTH0_DOMAIN and VITE_AUTH0_CLIENT_ID to enable Auth0
export const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN || '',
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID || '',
  authorizationParams: {
    redirect_uri: window.location.origin,
    scope: 'openid profile email',
    connection: 'google-oauth2',
    // Domain restriction hint for Google OAuth (UI-level)
    // Server-side validation happens in backend
    hd: ALLOWED_DOMAIN || undefined
  },
  useRefreshTokens: true,
  cacheLocation: 'localstorage'
}
