<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import TaskList from './components/TaskList.vue'

// On garde une liste réactive pour les tâches chargées depuis l'API.
const tasks = ref([])

// Le texte saisi dans le champ d'ajout.
const newTaskTitle = ref('')
const newTaskDate = ref('')

// Charge toutes les tâches depuis le backend au démarrage et après chaque action.
async function refresh() {
  // Appelle l'API backend pour récupérer la liste des tâches dans la base.
  const response = await fetch('/api/tasks')

  // Vérifie la réponse avant de mettre à jour la liste locale.
  if (!response.ok) {
    throw new Error('Impossible de charger les tâches')
  }

  // Stocke les tâches reçues dans la variable réactive.
  tasks.value = await response.json()
}

// Ajoute une nouvelle tâche en envoyant le titre au backend.
async function addTask() {
  // On ne crée pas de tâche vide.
  const title = newTaskTitle.value.trim()
  if (!title) {
    return
  }

  // Prépare les paramètres envoyés à l'API, y compris la date planifiée si elle existe.
  const params = new URLSearchParams({ title })
  if (newTaskDate.value) {
    params.set('scheduled_date', newTaskDate.value)
  }

  // Envoie une requête POST avec les paramètres dans l'URL, comme l'attend FastAPI.
  const response = await fetch(`/api/tasks?${params.toString()}`, {
    method: 'POST'
  })

  // Si l'API refuse la création, on arrête proprement.
  if (!response.ok) {
    throw new Error('Impossible d’ajouter la tâche')
  }

  // Vide le champ et recharge la liste depuis le backend.
  newTaskTitle.value = ''
  newTaskDate.value = ''
  await refresh()
}

// Bascule le statut done d'une tâche via le backend.
async function toggleTask(id) {
  // Appelle l'API pour inverser le statut terminé / non terminé.
  const response = await fetch(`/api/tasks/${id}`, { method: 'PATCH' })

  // Si la requête échoue, on signale l’erreur.
  if (!response.ok) {
    throw new Error('Impossible de modifier la tâche')
  }

  // Recharge la liste après la modification.
  await refresh()
}

// Supprime une tâche par son id via le backend.
async function deleteTask(id) {
  // Envoie une requête DELETE au backend.
  const response = await fetch(`/api/tasks/${id}`, { method: 'DELETE' })

  // Vérifie que la suppression a réussi.
  if (!response.ok) {
    throw new Error('Impossible de supprimer la tâche')
  }

  // Recharge la liste pour refléter la base de données.
  await refresh()
}

const taskSuggestions = computed(() => {
  const suggestions = [
    ...tasks.value.map(task => task.title),
    'Faire les courses',
    'Préparer le repas',
    'Ranger la maison',
    'Sortir les poubelles',
    'Faire la lessive',
    'Arroser les plantes'
  ]
  const query = newTaskTitle.value.trim().toLowerCase()

  if (!query) {
    return []
  }

  return [...new Set(suggestions)]
    .filter(suggestion => suggestion.toLowerCase().startsWith(query))
    .slice(0, 6)
})

// Les profils utilisateurs affichés dans l'application.
const profiles = ref([
  { id: 2, name: 'Paul', role: 'Papa', avatar: '👨‍👧', color: '#5aa0a5', createdAt: '2025-02-03T08:00:00.000Z', isAdmin: true },
  { id: 3, name: 'Lina', role: 'Enfant', avatar: '🌈', color: '#a7c86a', createdAt: '2025-03-04T08:00:00.000Z', isAdmin: false }
])

// Le profil actuellement sélectionné.
const selectedProfileId = ref(2)
const selectedProfile = computed(() => {
  return profiles.value.find(profile => profile.id === selectedProfileId.value) || null
})

// Le nouveau nom de profil à créer.
const newProfileName = ref('')

// Nombre de tâches réalisées sur le nombre total de tâches de la liste.
const doneTasksCount = computed(() => tasks.value.filter(task => task.done).length)
const totalTasksCount = computed(() => tasks.value.length)
const taskProgressText = computed(() => `${doneTasksCount.value}/${totalTasksCount.value}`)

// L'avatar du profil actuellement sélectionné pour l'édition rapide.
const profileAvatarEdit = ref(profiles.value[0].avatar)

// Données de la pop-up de profil.
const profileModalOpen = ref(false)
const profileEditName = ref('')
const profileEditAvatar = ref('')
const profileEditRole = ref('')
const profileEditCreatedAt = ref('')
const profileEditIsAdmin = ref(false)
const profileModalMode = ref('edit')
const avatarPickerOpen = ref(false)
const avatarOptions = [
  '👩', '👨', '👧', '👦', '👶', '🧑', '👵', '👴',
  '🐶', '🐱', '🦊', '🐼', '🐨', '🦁', '🐸', '🐵',
  '🌈', '⭐', '🚀', '🎨', '⚽', '🎵', '🌻', '🍀'
]

// Mode sombre actif ou non.
const darkMode = ref(false)

// Quand toutes les tâches sont faites, on vide automatiquement la liste après 10 secondes.
let clearTimer = null

watch(tasks, () => {
  // Si la liste est vide, on ne fait rien.
  if (tasks.value.length === 0) {
    return
  }

  // Si toutes les tâches ont done = true, on lance un timer.
  const allDone = tasks.value.every(task => task.done)

  if (allDone) {
    clearTimeout(clearTimer)
    clearTimer = setTimeout(() => {
      tasks.value = []
    }, 10000)
  } else {
    // Une tâche non faite : on annule le timer pour éviter de vider la liste trop tôt.
    clearTimeout(clearTimer)
  }
}, { deep: true })

function isImageAvatar(avatar) {
  return typeof avatar === 'string' && avatar.startsWith('data:image/')
}

function handleAvatarFile(event) {
  const file = event.target.files?.[0]
  if (!file || !file.type.startsWith('image/')) {
    return
  }

  const reader = new FileReader()
  reader.onload = () => {
    profileEditAvatar.value = String(reader.result)
  }
  reader.readAsDataURL(file)
  event.target.value = ''
}

function formatProfileDate(dateValue) {
  if (!dateValue) {
    return 'Date inconnue'
  }

  const parsed = new Date(dateValue)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date inconnue'
  }

  return parsed.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

// Lorsque le mode sombre change, on ajoute même classe au body.
watch(darkMode, (value) => {
  document.body.classList.toggle('dark-mode', value)
})

// Charge les tâches au démarrage de l’application.
onMounted(async () => {
  // On appel le backend pour récupérer toutes les tâches enregistrées.
  await refresh()
})

// Ouvre la pop-up du profil à partir d’un profil existant.
function openProfileModal(profileId) {
  selectedProfileId.value = profileId
  profileModalMode.value = 'edit'
  avatarPickerOpen.value = false

  const profile = profiles.value.find(item => item.id === profileId)
  if (!profile) {
    return
  }

  profileAvatarEdit.value = profile.avatar
  profileEditName.value = profile.name
  profileEditAvatar.value = profile.avatar
  profileEditRole.value = profile.role
  profileEditCreatedAt.value = profile.createdAt
  profileEditIsAdmin.value = Boolean(profile.isAdmin)
  profileModalOpen.value = true
}

// Ouvre la pop-up du profil pour créer un nouveau profil.
function openCreateProfileModal() {
  selectedProfileId.value = null
  profileModalMode.value = 'create'
  avatarPickerOpen.value = false
  profileEditName.value = ''
  profileEditAvatar.value = '👤'
  profileEditRole.value = 'Maman'
  profileEditCreatedAt.value = new Date().toISOString()
  profileEditIsAdmin.value = false
  profileModalOpen.value = true
}

// Ferme la pop-up du profil.
function closeProfileModal() {
  profileModalOpen.value = false
  profileModalMode.value = 'edit'
  avatarPickerOpen.value = false
}

function toggleAvatarPicker() {
  avatarPickerOpen.value = !avatarPickerOpen.value
}

function selectAvatar(avatar) {
  profileEditAvatar.value = avatar
  avatarPickerOpen.value = false
}

// Sauvegarde les changements dans le profil.
function saveProfileChanges() {
  if (profileModalMode.value === 'create') {
    const cleanName = profileEditName.value.trim() || 'Nouveau profil'
    const cleanAvatar = (profileEditAvatar.value || '👤').trim() || '👤'
    const cleanRole = profileEditRole.value.trim() || 'Famille'

    const newProfile = {
      id: Date.now(),
      name: cleanName,
      role: cleanRole,
      avatar: cleanAvatar,
      color: '#8b5cf6',
      createdAt: profileEditCreatedAt.value,
      isAdmin: profileEditIsAdmin.value
    }

    profiles.value.push(newProfile)
    selectedProfileId.value = newProfile.id
    profileAvatarEdit.value = newProfile.avatar
    profileModalOpen.value = false
    profileModalMode.value = 'edit'
    return
  }

  const profile = profiles.value.find(item => item.id === selectedProfileId.value)
  if (!profile) {
    return
  }

  profile.name = profileEditName.value.trim() || profile.name
  profile.avatar = (profileEditAvatar.value || '👤').trim() || '👤'
  profile.role = profileEditRole.value.trim() || profile.role
  profile.isAdmin = Boolean(profileEditIsAdmin.value)

  profileAvatarEdit.value = profile.avatar
  profileModalOpen.value = false
}

// Sélectionne un profil et prépare l’édition de son avatar.
function selectProfile(profileId) {
  selectedProfileId.value = profileId

  const profile = profiles.value.find(item => item.id === profileId)
  if (profile) {
    profileAvatarEdit.value = profile.avatar
  }
}

// Ajoute un nouveau profil utilisateur.
function addProfile() {
  const cleanName = newProfileName.value.trim() || 'Nouveau profil'

  const newProfile = {
    id: Date.now(),
    name: cleanName,
    role: 'Famille',
    avatar: '👤',
    color: '#8b5cf6',
    createdAt: new Date().toISOString(),
    isAdmin: false
  }

  profiles.value.push(newProfile)
  selectedProfileId.value = newProfile.id
  profileAvatarEdit.value = newProfile.avatar
  newProfileName.value = ''
}

// Retourne le nombre de tâches complétées par un profil ce mois.
function countTasksThisMonth(profileId) {
  const now = new Date()
  const month = now.getMonth()
  const year = now.getFullYear()

  return tasks.value.filter(task => {
    if (!task.done || task.completedBy !== profileId || !task.completedAt) {
      return false
    }

    const completed = new Date(task.completedAt)
    return completed.getMonth() === month && completed.getFullYear() === year
  }).length
}

// Retourne le nombre de tâches complétées par un profil depuis l'inscription.
function countTasksSinceRegistration(profileId) {
  const profile = profiles.value.find(item => item.id === profileId)

  if (!profile) {
    return 0
  }

  const start = new Date(profile.createdAt)

  return tasks.value.filter(task => {
    if (!task.done || task.completedBy !== profileId || !task.completedAt) {
      return false
    }

    return new Date(task.completedAt) >= start
  }).length
}

// Bascule le mode sombre.
function toggleDarkMode() {
  darkMode.value = !darkMode.value
}
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <span class="brand-badge" aria-label="FamilyTask">FT</span>
      <h1>
        FamilyTask
      </h1>
      <button class="theme-toggle" @click="toggleDarkMode">
        {{ darkMode ? '☀️ Clair' : '🌙 Sombre' }}
      </button>
    </div>
  </header>

  <main>
    <section class="app-layout">
      <aside class="profile-panel">
        <div class="profile-toolbar">
          <div class="profile-list">
            <div
              v-for="profile in profiles"
              :key="profile.id"
              class="profile-item"
              :class="{ active: profile.id === selectedProfileId }"
              @click="openProfileModal(profile.id)"
            >
              <span class="profile-avatar" :style="{ background: profile.color }">
                <img v-if="isImageAvatar(profile.avatar)" :src="profile.avatar" alt="" class="profile-avatar-image" />
                <template v-else>{{ profile.avatar }}</template>
              </span>
            </div>
          </div>

          <button class="add-profile-avatar" @click="openCreateProfileModal" title="Ajouter un profil" aria-label="Ajouter un profil">
            <span class="add-profile-avatar-icon">+</span>
          </button>
        </div>
      </aside>

      <div class="card" :class="{ 'dark-mode': darkMode }">
        <div class="todo-heading">
          <h2>To Do List</h2>
          <span class="task-counter">
            <span class="task-counter-label">Progression</span>
            <span class="task-counter-value">{{ taskProgressText }}</span>
          </span>
        </div>

        <!-- Zone de saisie pour ajouter une tâche -->
        <div class="add-task">
          <input
            v-model="newTaskTitle"
            type="text"
            placeholder="Nouvelle tâche"
            list="task-suggestions"
          />
          <input
            v-model="newTaskDate"
            type="date"
            class="task-date-input"
            aria-label="Date de programmation"
          />
          <button @click="addTask">Ajouter</button>
        </div>

        <datalist id="task-suggestions">
          <option v-for="suggestion in taskSuggestions" :key="suggestion" :value="suggestion" />
        </datalist>

        <!-- On laisse le composant TaskList afficher la liste et émettre les événements. -->
        <TaskList :tasks="tasks" :profiles="profiles" @toggle="toggleTask" @remove="deleteTask" />
      </div>
    </section>

    <div v-if="profileModalOpen" class="modal-backdrop" @click.self="closeProfileModal">
      <div class="profile-modal">
        <button class="modal-close" @click="closeProfileModal" title="Fermer">×</button>

        <div class="profile-modal-header">
          <div class="avatar-picker">
            <button
              type="button"
              class="profile-modal-avatar avatar-picker-trigger"
              :style="{ background: selectedProfile?.color || '#8b5cf6' }"
              aria-label="Choisir un avatar"
              :aria-expanded="avatarPickerOpen"
              @click="toggleAvatarPicker"
            >
              <img v-if="isImageAvatar(profileEditAvatar)" :src="profileEditAvatar" alt="" class="profile-avatar-image" />
              <template v-else>{{ profileEditAvatar || '👤' }}</template>
            </button>
            <div v-if="avatarPickerOpen" class="avatar-picker-menu" role="listbox" aria-label="Liste des avatars">
              <button
                v-for="avatar in avatarOptions"
                :key="avatar"
                type="button"
                class="avatar-option"
                :class="{ selected: avatar === profileEditAvatar }"
                :aria-label="`Choisir l'avatar ${avatar}`"
                @click="selectAvatar(avatar)"
              >
                {{ avatar }}
              </button>
            </div>
          </div>
          <div>
            <span class="modal-kicker">Profil</span>
            <h3>{{ selectedProfile?.name || 'Profil' }}</h3>
          </div>
        </div>

        <div class="profile-modal-body">
          <div class="modal-form">
            <label class="modal-label">
              <span>Nom</span>
              <input v-model="profileEditName" type="text" placeholder="Nom du profil" />
            </label>

            <label class="modal-label">
              <span>Avatar</span>
              <input v-model="profileEditAvatar" type="text" maxlength="4" placeholder="😀" />
            </label>

            <div class="avatar-upload-field">
              <span class="modal-label-title">Avatar image</span>
              <div class="avatar-upload-actions">
                <label class="avatar-upload-button">
                  Importer un JPEG
                  <input type="file" accept="image/jpeg" @change="handleAvatarFile" />
                </label>
                <label class="avatar-upload-button">
                  Prendre une photo
                  <input type="file" accept="image/*" capture="user" @change="handleAvatarFile" />
                </label>
              </div>
            </div>

            <label class="modal-label">
              <span>Lien de parenté</span>
              <select v-model="profileEditRole">
                <option value="Père">Père</option>
                <option value="Mère">Mère</option>
                <option value="Enfant">Enfant</option>
                <option value="Grand-parent">Grand-parent</option>
                <option value="Tante">Tante</option>
                <option value="Oncle">Oncle</option>
                <option value="Famille">Famille</option>
              </select>
            </label>

            <label class="modal-label checkbox-row">
              <input v-model="profileEditIsAdmin" type="checkbox" />
              <span>Profil administrateur</span>
            </label>
          </div>

          <p class="profile-created-date">
            Profil créé le {{ formatProfileDate(selectedProfile?.createdAt || profileEditCreatedAt) }}
          </p>

          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-label">Tâches du mois</span>
              <strong class="stat-value">{{ countTasksThisMonth(selectedProfileId) }}</strong>
            </div>
            <div class="stat-card">
              <span class="stat-label">Depuis l'inscription</span>
              <strong class="stat-value">{{ countTasksSinceRegistration(selectedProfileId) }}</strong>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-cancel" @click="closeProfileModal">Fermer</button>
            <button class="btn-save" @click="saveProfileChanges">Enregistrer</button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

