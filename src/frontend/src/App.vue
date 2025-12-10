<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from './stores/auth'
import { useWebSocket } from './utils/websocket'

const authStore = useAuthStore()
const { connect } = useWebSocket()

onMounted(async () => {
  // Check if user is authenticated
  const token = localStorage.getItem('token')
  if (token) {
    authStore.token = token
    authStore.isAuthenticated = true
    // Set axios default authorization header
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    // Connect to WebSocket for real-time updates
    connect()
  }
})
</script>
