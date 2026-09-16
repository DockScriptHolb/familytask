<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const memberName = ref('')

// Récupère le prénom du membre connecté pour la barre de navigation.
async function loadCurrentMember() {
  const token = localStorage.getItem('token')
  if (!token) {
    memberName.value = ''
    return
  }

  try {
    const response = await fetch('/api/me', {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (!response.ok) {
      throw new Error('Session invalide')
    }

    const member = await response.json()
    memberName.value = member.name || 'Membre'
  } catch {
    // Un token refusé ne doit pas laisser l'utilisateur bloqué sur une page privée.
    localStorage.removeItem('token')
    memberName.value = ''
    if (route.meta.requiresAuth) {
      await router.push({ name: 'login' })
    }
  }
}

// Déconnecte côté serveur quand c'est possible, puis toujours côté navigateur.
async function logout() {
  const token = localStorage.getItem('token')

  try {
    if (token) {
      await fetch('/api/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
    }
  } finally {
    localStorage.removeItem('token')
    memberName.value = ''
    await router.push({ name: 'login' })
  }
}

watch(() => route.name, loadCurrentMember, { immediate: true })
</script>

<template>
  <header v-if="route.name === 'tasks'" class="account-bar">
    <span>Bonjour {{ memberName || 'à vous' }}</span>
    <button type="button" @click="logout">Se déconnecter</button>
  </header>
  <router-view />
</template>

