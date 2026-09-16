<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch, clearToken, getToken } from './api'

const route = useRoute()
const router = useRouter()
const memberName = ref('')
const memberAvatar = ref('')
const isAdmin = ref(false)
const darkMode = ref(localStorage.getItem('darkMode') === 'true')
const avatarInput = ref(null)

// Récupère le prénom du membre connecté pour la barre de navigation.
async function loadCurrentMember() {
  const token = getToken()
  if (!token) {
    memberName.value = ''
    memberAvatar.value = ''
    isAdmin.value = false
    return
  }

  try {
    const response = await apiFetch('/api/me')

    if (!response.ok) {
      throw new Error('Session invalide')
    }

    const member = await response.json()
    memberName.value = member.name || 'Membre'
    memberAvatar.value = member.avatar || ''
    isAdmin.value = Boolean(member.is_admin)
  } catch {
    // Un token refusé ne doit pas laisser l'utilisateur bloqué sur une page privée.
    clearToken()
    memberName.value = ''
    memberAvatar.value = ''
    isAdmin.value = false
    if (route.meta.requiresAuth) {
      await router.push({ name: 'login' })
    }
  }
}

// Ouvre le sélecteur de fichier quand on clique sur l'avatar.
function openAvatarPicker() {
  avatarInput.value?.click()
}

// Encode l'image choisie en base64 puis l'envoie au backend.
async function updateAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })

  const response = await apiFetch('/api/me/avatar', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ avatar: dataUrl })
  })

  if (response.ok) {
    const member = await response.json()
    memberAvatar.value = member.avatar || ''
  }

  event.target.value = ''
}

// Déconnecte côté serveur quand c'est possible, puis toujours côté navigateur.
async function logout() {
  const token = getToken()

  try {
    if (token) {
      await apiFetch('/api/logout', { method: 'POST' })
    }
  } finally {
    clearToken()
    memberName.value = ''
    await router.push({ name: 'login' })
  }
}

// Conserve le choix du thème entre deux visites de l'application.
watch(darkMode, value => {
  document.body.classList.toggle('dark-mode', value)
  localStorage.setItem('darkMode', String(value))
}, { immediate: true })

watch(() => route.name, loadCurrentMember, { immediate: true })
</script>

<template>
  <div class="app-frame" :class="{ 'private-frame': route.meta.requiresAuth }">
    <header v-if="route.meta.requiresAuth" class="account-bar">
      <div class="account-identity">
        <button type="button" class="avatar-button" title="Changer l'avatar" @click="openAvatarPicker">
          <img v-if="memberAvatar" :src="memberAvatar" alt="Avatar" class="avatar-image" />
          <span v-else class="avatar-placeholder">{{ (memberName || '?').charAt(0).toUpperCase() }}</span>
        </button>
        <input ref="avatarInput" type="file" accept="image/*" class="avatar-input" @change="updateAvatar" />
        <span class="account-greeting"><small>Bonjour</small>{{ memberName || 'à vous' }}</span>
      </div>
      <div class="account-actions">
        <button type="button" class="theme-toggle" :aria-label="darkMode ? 'Activer le mode clair' : 'Activer le mode sombre'" @click="darkMode = !darkMode">
          {{ darkMode ? '☀️' : '🌙' }}
        </button>
        <button type="button" class="logout-button" @click="logout">Déconnexion</button>
      </div>
    </header>

    <router-view />

    <!-- La navigation reste visible en bas de chaque écran privé. -->
    <nav v-if="route.meta.requiresAuth" class="bottom-tabs" aria-label="Navigation principale">
      <RouterLink to="/tasks" class="bottom-tab" active-class="active"><span>✓</span>Tâches</RouterLink>
      <RouterLink v-if="isAdmin" to="/famille" class="bottom-tab" active-class="active"><span>♧</span>Famille</RouterLink>
    </nav>
  </div>
</template>

