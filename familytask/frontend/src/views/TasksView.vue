<script setup>
import { computed, onMounted, ref } from 'vue'
import TaskList from '../components/TaskList.vue'
import { apiFetch } from '../api'

const tasks = ref([])
const newTaskTitle = ref('')
const newTaskDate = ref('')
const urgentTask = ref(false)
const errorMessage = ref('')
const isAdmin = ref(false)
const familyMembers = ref([])
const assigneeId = ref('')
const currentMemberId = ref(null)

// Charge l'historique des titres déjà saisis par l'utilisateur pour pouvoir les reproposer.
function loadTaskHistory() {
  try {
    const stored = JSON.parse(localStorage.getItem('taskHistory') || '[]')
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

const taskHistory = ref(loadTaskHistory())

// Enregistre un titre de tâche dans l'historique, sans doublon, le plus récent en premier.
function rememberTaskTitle(title) {
  const normalized = title.trim()
  if (!normalized) return

  const withoutDuplicate = taskHistory.value.filter(existing => existing.toLowerCase() !== normalized.toLowerCase())
  taskHistory.value = [normalized, ...withoutDuplicate].slice(0, 30)
  localStorage.setItem('taskHistory', JSON.stringify(taskHistory.value))
}

// Retourne une couleur stable pour les bulles avatar sans image.
function avatarColor(name) {
  const colors = ['#ef6f6c', '#4f8dff', '#39a96b', '#e0a458', '#9b72cf', '#0fa3b1']
  const total = String(name || '').split('').reduce((sum, letter) => sum + letter.charCodeAt(0), 0)
  return colors[total % colors.length]
}

// Retrouve le membre actuellement sélectionné pour l'attribution afin d'afficher sa bulle.
const selectedAssignee = computed(() => familyMembers.value.find(m => String(m.id) === assigneeId.value))

// Charge le membre connecté pour savoir s'il est admin.
async function loadCurrentMember() {
  const response = await apiFetch('/api/me')
  if (!response.ok) return
  const member = await response.json()
  isAdmin.value = Boolean(member.is_admin)
  currentMemberId.value = member.id
}

// Charge tous les membres de la famille pour le menu d'assignation, soi-même inclus.
async function loadFamilyMembers() {
  const response = await apiFetch('/api/members')
  if (!response.ok) return
  const data = await response.json()
  familyMembers.value = Array.isArray(data) ? data : []
  // Par défaut, une nouvelle tâche est attribuée à soi-même.
  assigneeId.value = currentMemberId.value !== null ? String(currentMemberId.value) : ''
}

// Charge les tâches enregistrées dans la base de données.
async function refresh() {
  const response = await apiFetch('/api/tasks')
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
  // N'envoie member_id que si un autre membre que soi-même a été choisi ; sinon la tâche reste attribuée à l'utilisateur par défaut.
  if (isAdmin.value && assigneeId.value && assigneeId.value !== String(currentMemberId.value)) {
    params.set('member_id', assigneeId.value)
  }

  try {
    const response = await apiFetch(`/api/tasks?${params.toString()}`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Impossible d’ajouter la tâche')
    rememberTaskTitle(title)
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
  const response = await apiFetch(`/api/tasks/${id}`, { method: 'PATCH' })
  if (!response.ok) {
    errorMessage.value = 'Impossible de modifier la tâche.'
    return
  }
  const updatedTask = await response.json()
  await refresh()

  // Retire automatiquement la tâche de la liste 5 secondes après sa validation.
  if (updatedTask.done) {
    setTimeout(async () => {
      const stillDone = tasks.value.find(task => task.id === id)?.done
      if (stillDone) {
        await deleteTask(id)
      }
    }, 5000)
  }
}

// Supprime une tâche après l'action demandée par la liste.
async function deleteTask(id) {
  const response = await apiFetch(`/api/tasks/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    errorMessage.value = 'Impossible de supprimer la tâche.'
    return
  }
  await refresh()
}

const taskSuggestions = computed(() => {
  const suggestions = [
    ...tasks.value.map(task => task.title),
    ...taskHistory.value,
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

onMounted(async () => {
  try {
    await loadCurrentMember()
    if (isAdmin.value) await loadFamilyMembers()
    await refresh()
  } catch {
    errorMessage.value = 'Impossible de charger les tâches. Réessayez.'
  }
})
</script>

<template>
  <main>
    <section class="app-layout">
      <div class="card">
        <div class="todo-heading">
          <h2>Tâches</h2>
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
          <input v-model="newTaskDate" type="date" class="task-date-input" aria-label="Date limite pour effectuer la tâche" title="Date limite" />
          <template v-if="isAdmin && familyMembers.length">
            <div class="assignee-picker">
              <button type="button" class="assignee-bubble selected" :title="selectedAssignee?.name" :aria-label="selectedAssignee?.name">
                <span class="assignee-bubble-initial" :style="{ backgroundColor: avatarColor(selectedAssignee?.name) }">
                  {{ (selectedAssignee?.name || '?').charAt(0).toUpperCase() }}
                  </span>
                </button>
                <div class="assignee-dropdown" role="radiogroup" aria-label="Attribuer à un membre">
                  <button
                    v-for="familyMember in familyMembers"
                    :key="familyMember.id"
                    type="button"
                    class="assignee-bubble"
                    :class="{ selected: assigneeId === String(familyMember.id) }"
                    :title="familyMember.name"
                    :aria-label="familyMember.name"
                    role="radio"
                    :aria-checked="assigneeId === String(familyMember.id)"
                    @click="assigneeId = String(familyMember.id)"
                  >
                    <span class="assignee-bubble-initial" :style="{ backgroundColor: avatarColor(familyMember.name) }">
                      {{ (familyMember.name || '?').charAt(0).toUpperCase() }}
                    </span>
                  </button>
                </div>
              </div>
          </template>
          <button type="button" @click="addTask">Ajouter</button>
        </div>

        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
        <TaskList :tasks="tasks" :current-member-id="currentMemberId" @toggle="toggleTask" @remove="deleteTask" />
      </div>
    </section>
  </main>
</template>
