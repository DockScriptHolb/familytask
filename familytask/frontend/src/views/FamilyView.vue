<script setup>
import { computed, onMounted, ref } from 'vue'
import { apiFetch } from '../api'

const members = ref([])
const currentMemberId = ref(null)
const errorMessage = ref('')
const familyTasks = ref([])

// Propose des liens courants dès l'ouverture du formulaire.
const defaultLiens = [
  'Parent',
  'Enfant',
  'Conjoint(e)',
  'Frère',
  'Sœur',
  'Grand-parent',
  'Petit-enfant',
  'Oncle',
  'Tante',
  'Cousin(e)',
  'Neveu',
  'Nièce',
  'Autre'
]
const liens = ref([...defaultLiens])

const newEmail = ref('')
const newPassword = ref('')
const newName = ref('')
const newLien = ref('')
const newIsAdmin = ref(false)
const isSubmitting = ref(false)

// Associe le nom du responsable à chaque tâche familiale.
const memberNames = computed(() => new Map(members.value.map(member => [member.id, member.name])))

function memberName(memberId) {
  return memberNames.value.get(memberId) || 'Membre inconnu'
}

// Retourne une couleur stable pour que chaque membre ait un avatar reconnaissable.
function avatarColor(name) {
  const colors = ['#ef6f6c', '#4f8dff', '#39a96b', '#e0a458', '#9b72cf', '#0fa3b1']
  const total = String(name || '').split('').reduce((sum, letter) => sum + letter.charCodeAt(0), 0)
  return colors[total % colors.length]
}

async function loadCurrentMember() {
  const response = await apiFetch('/api/me')
  if (!response.ok) return
  const member = await response.json()
  currentMemberId.value = member.id
  if (!member.is_admin) {
    window.location.replace('/tasks')
  }
}

async function loadMembers() {
  const response = await apiFetch('/api/members')
  if (!response.ok) {
    errorMessage.value = 'Impossible de charger les membres.'
    return
  }
  members.value = await response.json()
}

// Charge les liens proposés dans le formulaire.
async function loadLiens() {
  const response = await apiFetch('/api/liens')
  if (response.ok) {
    const familyLiens = await response.json()
    liens.value = [...new Set([...defaultLiens, ...familyLiens])]
  }
}

// Charge toutes les tâches visibles par un administrateur.
async function loadFamilyTasks() {
  const response = await apiFetch('/api/tasks/famille')
  if (!response.ok) {
    errorMessage.value = 'Impossible de charger les tâches de la famille.'
    return
  }
  familyTasks.value = await response.json()
}

async function createMember() {
  errorMessage.value = ''

  if (!newEmail.value.trim() || !newPassword.value || !newName.value.trim() || !newLien.value) {
    errorMessage.value = 'Remplissez tous les champs pour créer un compte.'
    return
  }

  isSubmitting.value = true

  try {
    const response = await apiFetch('/api/members', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: newEmail.value.trim(),
        password: newPassword.value,
        name: newName.value.trim(),
        lien: newLien.value,
        is_admin: newIsAdmin.value
      })
    })
    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      errorMessage.value = data.detail || 'Impossible de créer ce compte.'
      return
    }

    newEmail.value = ''
    newPassword.value = ''
    newName.value = ''
    newLien.value = ''
    newIsAdmin.value = false
    await Promise.all([loadMembers(), loadFamilyTasks()])
  } finally {
    isSubmitting.value = false
  }
}

// Supprime un membre après confirmation explicite et recharge ses tâches.
async function deleteMember(targetMember) {
  if (!window.confirm(`Supprimer le compte de ${targetMember.name} et ses tâches ?`)) return

  const response = await apiFetch(`/api/members/${targetMember.id}`, { method: 'DELETE' })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    errorMessage.value = data.detail || 'Impossible de supprimer ce membre.'
    return
  }
  await Promise.all([loadMembers(), loadFamilyTasks()])
}

// Supprime la tâche d'un membre de la famille, réservé aux administrateurs.
async function deleteFamilyTask(task) {
  if (!window.confirm(`Supprimer la tâche « ${task.title} » ?`)) return

  const response = await apiFetch(`/api/tasks/${task.id}`, { method: 'DELETE' })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    errorMessage.value = data.detail || 'Impossible de supprimer cette tâche.'
    return
  }
  await loadFamilyTasks()
}

// Promeut ou rétrograde un membre en inversant son statut admin.
async function toggleAdmin(targetMember) {
  errorMessage.value = ''

  const response = await apiFetch(`/api/members/${targetMember.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_admin: !targetMember.is_admin })
  })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    errorMessage.value = data.detail || 'Impossible de modifier les droits de ce membre.'
    return
  }

  await loadMembers()
}

onMounted(async () => {
  await loadCurrentMember()
  await Promise.all([loadMembers(), loadLiens(), loadFamilyTasks()])
})
</script>

<template>
  <main class="family-page">
    <div class="family-card">
      <div class="family-heading">
        <div>
          <p class="section-kicker">Espace administrateur</p>
          <h1>Ma famille</h1>
        </div>
        <span class="member-count">{{ members.length }} membre(s)</span>
      </div>

      <form class="family-form" @submit.prevent="createMember">
        <label class="auth-label">
          <span>Prénom</span>
          <input v-model="newName" type="text" required placeholder="Camille" />
        </label>
        <label class="auth-label">
          <span>Lien de parenté</span>
          <select v-model="newLien" required>
            <option value="" disabled>Choisir un lien</option>
            <option v-for="lien in liens" :key="lien" :value="lien">{{ lien }}</option>
          </select>
        </label>
        <label class="auth-label">
          <span>Email</span>
          <input v-model="newEmail" type="email" required autocomplete="email" placeholder="vous@exemple.com" />
        </label>
        <label class="auth-label">
          <span>Mot de passe</span>
          <input v-model="newPassword" type="password" required minlength="8" autocomplete="new-password" />
        </label>
        <label class="urgent-toggle">
          <input v-model="newIsAdmin" type="checkbox" />
          <span>Administrateur</span>
        </label>
        <button type="submit" :disabled="isSubmitting || !liens.length">
          {{ isSubmitting ? 'Création...' : 'Créer le compte' }}
        </button>
      </form>

      <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>

      <h2>Membres de la famille</h2>
      <ul class="family-member-list">
        <li v-for="familyMember in members" :key="familyMember.id" class="task-item">
          <div class="task-row">
            <span class="family-avatar" :style="{ backgroundColor: avatarColor(familyMember.name) }">
              <img v-if="familyMember.avatar" :src="familyMember.avatar" alt="" class="family-avatar-image" />
              <template v-else>{{ familyMember.name.charAt(0).toUpperCase() }}</template>
            </span>
            <span class="member-details">
              <strong>{{ familyMember.name }}</strong>
              <span>{{ familyMember.lien }}</span>
              <span v-if="familyMember.is_admin" class="admin-badge">admin</span>
            </span>
            <button v-if="familyMember.id !== currentMemberId" type="button" class="danger-button" @click="deleteMember(familyMember)">
              Supprimer
            </button>
          </div>
        </li>
      </ul>

      <h2>Tâches de la famille</h2>
      <ul v-if="familyTasks.length" class="family-task-list">
        <li v-for="task in familyTasks" :key="task.id" class="task-row">
          <span :class="{ done: task.done }">{{ task.title }}</span>
          <span class="task-assignee">{{ memberName(task.member_id) }}</span>
          <button type="button" class="danger-button" @click="deleteFamilyTask(task)">
            Supprimer
          </button>
        </li>
      </ul>
      <p v-else class="empty-list">Aucune tâche dans la famille.</p>
    </div>
  </main>
</template>
