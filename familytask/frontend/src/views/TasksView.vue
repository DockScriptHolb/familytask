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

// Charge le membre connecté pour savoir s'il est admin.
async function loadCurrentMember() {
  const response = await apiFetch('/api/me')
  if (!response.ok) return
  const member = await response.json()
  isAdmin.value = Boolean(member.is_admin)
  currentMemberId.value = member.id
}

// Charge tous les membres de la famille pour le menu d'assignation.
async function loadFamilyMembers() {
  const response = await apiFetch('/api/members')
  if (!response.ok) return
  const data = await response.json()
  const members = Array.isArray(data) ? data : []
  familyMembers.value = members.filter(familyMember => familyMember.id !== currentMemberId.value)
  assigneeId.value = familyMembers.value.length ? String(familyMembers.value[0].id) : ''
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
  if (isAdmin.value && assigneeId.value) params.set('member_id', assigneeId.value)

  try {
    const response = await apiFetch(`/api/tasks?${params.toString()}`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Impossible d’ajouter la tâche')
    newTaskTitle.value = ''
    newTaskDate.value = ''
    urgentTask.value = false
    assigneeId.value = familyMembers.value.length ? String(familyMembers.value[0].id) : ''
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
  await refresh()
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
          <label v-if="isAdmin && familyMembers.length" class="assignee-control">
            <span class="assignee-label"><span class="assignee-icon">↗</span>Attribuer à</span>
            <select v-model="assigneeId" class="assignee-select" aria-label="Attribuer à un membre">
              <option v-for="familyMember in familyMembers" :key="familyMember.id" :value="String(familyMember.id)">
                {{ familyMember.name }}
              </option>
            </select>
          </label>
          <button type="button" @click="addTask">Ajouter</button>
        </div>

        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
        <TaskList :tasks="tasks" :current-member-id="currentMemberId" @toggle="toggleTask" @remove="deleteTask" />
      </div>
    </section>
  </main>
</template>
