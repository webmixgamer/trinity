import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createAuth0 } from '@auth0/auth0-vue'
import router from './router'
import App from './App.vue'
import './style.css'
import { useAuthStore } from './stores/auth'
import { auth0Config } from './config/auth0'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Always initialize Auth0 plugin
// In dev mode it won't be used, but it needs to be available
// for production mode to work without rebuild
const auth0 = createAuth0(auth0Config)
app.use(auth0)

// Initialize auth state from localStorage/cookies on app startup
const authStore = useAuthStore()
authStore.initializeAuth()

app.mount('#app')
