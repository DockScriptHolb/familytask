<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, setToken } from '../api'

const router = useRouter()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

// Vérifie les identifiants puis conserve le token de session dans le navigateur.
async function submitLogin() {
  errorMessage.value = ''

  if (!email.value.trim() || !password.value) {
    errorMessage.value = 'Saisissez votre email et votre mot de passe.'
    return
  }

  isSubmitting.value = true

  try {
    const response = await apiFetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value.trim(), password: password.value })
    })
    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      errorMessage.value = data.detail || 'Email ou mot de passe incorrect.'
      return
    }

    setToken(data.token)
    await router.push({ name: 'tasks' })
  } catch {
    errorMessage.value = 'Le serveur est inaccessible. Réessayez plus tard.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <div class="auth-card">
      <h1>Connexion</h1>
      <form class="auth-form" @submit.prevent="submitLogin">
        <label class="auth-label">
          <span>Email</span>
          <input v-model="email" type="email" required autocomplete="email" placeholder="vous@exemple.com" />
        </label>
        <label class="auth-label">
          <span>Mot de passe</span>
          <input v-model="password" type="password" required autocomplete="current-password" />
        </label>
        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
        <button type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? 'Connexion...' : 'Se connecter' }}
        </button>
      </form>
      <p class="auth-link-line">
        Pas encore de compte ? <RouterLink to="/signup">Créer ma famille</RouterLink>
      </p>
    </div>
  </main>
</template>
