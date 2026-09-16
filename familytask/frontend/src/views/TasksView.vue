<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import TaskList from '../components/TaskList.vue'

const tasks = ref([])
const newTaskTitle = ref('')
const newTaskDate = ref('')
const urgentTask = ref(false)
const errorMessage = ref('')
const darkMode = ref(false)

// Ajoute le token de session aux appels qui concernent les tâches.
function authHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Charge les tâches enregistrées dans la base de données.
async function refresh() {
  const response = await fetch('/api/tasks', { headers: authHeaders() })
  if (!response.ok) {
    throw new Error('Impossible de charger les tâches')
  }
  const data = await response.json()
  tasks.value = Array.isArray(data) ? data : []
}

// Ajoute une tâche avec sa date éventuelle et son niveau d'urgence.
async function addTask() {
  const title = newTaskTitle.value.trim()
  if (!title) return

  errorMessage.value = ''
  const params = new URLSearchParams({ title, urgent: String(urgentTask.value) })
  if (newTaskDate.value) params.set('scheduled_date', newTaskDate.value)

  try {
    const response = await fetch(`/api/tasks?${params.toString()}`, {
      method: 'POST',
      headers: authHeaders()
    })
    if (!response.ok) throw new Error('Impossible d’ajouter la tâche')
    newTaskTitle.value = ''
    newTaskDate.value = ''
    urgentTask.value = false
    await refresh()
  } catch {
    errorMessage.value = 'Impossible d’ajouter la tâche. Réessayez.'
  }
}

// Inverse l'état terminé d'une tâche.
async function toggleTask(id) {
  const response = await fetch(`/api/tasks/${id}`, { method: 'PATCH', headers: authHeaders() })
  if (!response.ok) {
    errorMessage.value = 'Impossible de modifier la tâche.'
    return
  }
  await refresh()
}

// Supprime une tâche après l'action demandée par la liste.
async function deleteTask(id) {
  const response = await fetch(`/api/tasks/${id}`, { method: 'DELETE', headers: authHeaders() })
  if (!response.ok) {
    errorMessage.value = 'Impossible de supprimer la tâche.'
    return
  }
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
  if (!query) return []
  return [...new Set(suggestions)]
    .filter(suggestion => suggestion.toLowerCase().startsWith(query))
    .slice(0, 6)
})

const doneTasksCount = computed(() => tasks.value.filter(task => task.done).length)
const taskProgressText = computed(() => `${doneTasksCount.value}/${tasks.value.length}`)
const showSuggestions = computed(() => Boolean(newTaskTitle.value.trim() && taskSuggestions.value.length))

async function selectSuggestion(suggestion) {
  newTaskTitle.value = suggestion
  await addTask()
}

function toggleDarkMode() {
  darkMode.value = !darkMode.value
}

watch(darkMode, value => document.body.classList.toggle('dark-mode', value))

onMounted(async () => {
  try {
    await refresh()
  } catch {
    errorMessage.value = 'Impossible de charger les tâches. Réessayez.'
  }
})
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <span class="brand-badge" aria-label="FamilyTask">FT</span>
      <h1>FamilyTask</h1>
      <button class="theme-toggle" type="button" @click="toggleDarkMode">
        {{ darkMode ? '☀️ Clair' : '🌙 Sombre' }}
      </button>
    </div>
  </header>

  <main>
    <section class="app-layout">
      <div class="card">
        <div class="todo-heading">
          <h2>To Do List</h2>
          <span class="task-counter">
            <span class="task-counter-label">Progression</span>
            <span class="task-counter-value">{{ taskProgressText }}</span>
          </span>
        </div>

        <div class="add-task">
          <div class="task-input-group">
            <input v-model="newTaskTitle" type="text" placeholder="Nouvelle tâche" @keyup.enter="addTask" />
            <label class="urgent-toggle">
              <input v-model="urgentTask" type="checkbox" />
              <span>Urgent</span>
            </label>
            <div v-if="showSuggestions" class="task-suggestions" aria-label="Suggestions de tâches">
              <button
                v-for="suggestion in taskSuggestions"
                :key="suggestion"
                type="button"
                class="suggestion-item"
                @mousedown.prevent
                @click="selectSuggestion(suggestion)"
              >
                {{ suggestion }}
              </button>
            </div>
          </div>
          <input v-model="newTaskDate" type="date" class="task-date-input" aria-label="Date de programmation" />
          <button type="button" @click="addTask">Ajouter</button>
        </div>

        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
        <TaskList :tasks="tasks" @toggle="toggleTask" @remove="deleteTask" />
      </div>
    </section>
  </main>
</template>
