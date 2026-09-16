<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const family = ref('')
const name = ref('')
const lien = ref('Père')
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

const liens = ['Père', 'Mère', 'Enfant', 'Grand-parent', 'Tante', 'Oncle', 'Famille']

// Envoie le formulaire au backend et ouvre la liste après création du compte.
async function submitSignup() {
  errorMessage.value = ''

  if (!family.value.trim() || !name.value.trim() || !email.value.trim() || !password.value) {
    errorMessage.value = 'Remplissez tous les champs pour créer votre famille.'
    return
  }

  isSubmitting.value = true

  try {
    const response = await fetch('/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.value.trim(),
        password: password.value,
        name: name.value.trim(),
        family: family.value.trim(),
        lien: lien.value
      })
    })
    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      errorMessage.value = data.detail || 'Impossible de créer la famille.'
      return
    }

    localStorage.setItem('token', data.token)
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
      <h1>Créer votre famille</h1>
      <form class="auth-form" @submit.prevent="submitSignup">
        <label class="auth-label">
          <span>Nom de famille</span>
          <input v-model="family" type="text" required placeholder="Dupont" />
        </label>
        <label class="auth-label">
          <span>Prénom</span>
          <input v-model="name" type="text" required placeholder="Camille" />
        </label>
        <label class="auth-label">
          <span>Lien de parenté</span>
          <select v-model="lien">
            <option v-for="option in liens" :key="option" :value="option">{{ option }}</option>
          </select>
        </label>
        <label class="auth-label">
          <span>Email</span>
          <input v-model="email" type="email" required autocomplete="email" placeholder="vous@exemple.com" />
        </label>
        <label class="auth-label">
          <span>Mot de passe</span>
          <input v-model="password" type="password" required minlength="8" autocomplete="new-password" />
        </label>
        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
        <button type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? 'Création...' : 'Créer ma famille' }}
        </button>
      </form>
      <p class="auth-link-line">
        Déjà un compte ? <RouterLink to="/login">Se connecter</RouterLink>
      </p>
    </div>
  </main>
</template>
