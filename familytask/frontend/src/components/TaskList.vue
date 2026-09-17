<script setup>
import { computed } from 'vue'

// On décrit les propriétés attendues par le composant.
// La liste des tâches et les profils arrivent depuis App.vue.
const props = defineProps({
  tasks: {
    type: Array,
    default: () => []
  },
  profiles: {
    type: Array,
    default: () => []
  },
  currentMemberId: {
    type: [Number, String],
    default: null
  }
})

const orderedTasks = computed(() => {
  const safeTasks = Array.isArray(props.tasks) ? props.tasks : []
  return [...safeTasks].sort((a, b) => {
    // Les tâches terminées passent toujours en fin de liste, quel que soit leur niveau d'urgence.
    const doneDiff = Number(Boolean(a?.done)) - Number(Boolean(b?.done))
    if (doneDiff !== 0) return doneDiff

    const urgentA = Number(Boolean(a?.urgent) || isDueSoon(a))
    const urgentB = Number(Boolean(b?.urgent) || isDueSoon(b))
    return urgentB - urgentA
  })
})

// On émet des événements vers App.vue.
const emit = defineEmits(['toggle', 'remove'])

function getProfileName(profileId) {
  if (profileId === null || profileId === undefined || profileId === '') {
    return 'Quelqu’un'
  }

  const normalizedId = Number(profileId)
  const profile = props.profiles.find(item => Number(item.id) === normalizedId || item.id === profileId)
  return profile ? profile.name : 'Quelqu’un'
}

function formatDate(dateValue) {
  if (!dateValue) {
    return ''
  }

  const parsed = new Date(dateValue)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }

  return parsed.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function getTaskDate(task) {
  return task?.scheduledDate || task?.scheduled_date || ''
}

// Une tâche non terminée dont la deadline est dépassée doit ressortir comme étant en retard.
function isOverdue(task) {
  if (task?.done) return false

  const dateValue = getTaskDate(task)
  if (!dateValue) return false

  const deadline = new Date(dateValue)
  if (Number.isNaN(deadline.getTime())) return false

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  deadline.setHours(0, 0, 0, 0)

  return deadline.getTime() < today.getTime()
}

// Une tâche non terminée devient urgente automatiquement quand il reste moins de 24h avant la deadline.
function isDueSoon(task) {
  if (task?.done) return false

  const dateValue = getTaskDate(task)
  if (!dateValue) return false

  const deadline = new Date(dateValue)
  if (Number.isNaN(deadline.getTime())) return false

  // La deadline compte jusqu'à la fin de sa journée, faute d'heure précise saisie.
  deadline.setHours(23, 59, 59, 999)
  const msRemaining = deadline.getTime() - Date.now()

  return msRemaining >= 0 && msRemaining <= 24 * 60 * 60 * 1000
}

// Une tâche assignée au membre connecté ressort visuellement des autres.
function isMine(task) {
  return props.currentMemberId !== null && Number(task?.member_id) === Number(props.currentMemberId)
}

function getTaskIcon(title) {
  const normalized = String(title || '').toLowerCase()

  if (/course|achat|shop|market|épicer|magasin|panier|aliment/.test(normalized)) return '🛒'
  if (/cuisine|cooking|cook|manger|repas|préparer|dîner|déjeuner|nourriture/.test(normalized)) return '🍽️'
  if (/lavage|lessive|linge|blanc|machine|nettoy/.test(normalized)) return '🧺'
  if (/jardin|plante|potager|herbe|extérieur|fleurs/.test(normalized)) return '🌿'
  if (/lire|livre|lecture|roman|écrire|école|étude/.test(normalized)) return '📚'
  if (/salle|bath|toilette|wc|douche|nettoyage/.test(normalized)) return '🧼'
  if (/ordre|organiser|ranger|vider|dépoussi/.test(normalized)) return '📦'
  if (/voyage|partir|vacances|train|route|voiture/.test(normalized)) return '✈️'
  if (/sport|course|marche|activité|faire du|gym/.test(normalized)) return '🏃'

  return '✅'
}
</script>

<template>
  <!-- Si la liste est vide, on affiche un message sympa. -->
  <div v-if="orderedTasks.length === 0" class="empty-list">
    <span class="empty-icon">🌤️</span>
    <p>Plus rien à faire pour aujourd'hui. Reposez vous ! </p>
  </div>

  <!-- La liste est maintenant affichée par ce composant dédié. -->
  <ul v-else class="task-list">
    <li v-for="task in orderedTasks" :key="task.id" class="task-item">
      <div class="task-row" :class="{ 'task-urgent': Boolean(task.urgent) || isDueSoon(task), 'task-mine': isMine(task), 'task-overdue': isOverdue(task) }">
        <!-- Toute la ligne est cliquable pour basculer la tâche, pas seulement le cercle. -->
        <div class="task-line" role="button" tabindex="0" @click="emit('toggle', task.id)" @keydown.enter.space.prevent="emit('toggle', task.id)">
          <!-- La case n'est plus qu'un indicateur visuel, le clic est géré par la ligne entière. -->
          <input type="checkbox" :checked="task.done" tabindex="-1" style="pointer-events: none" />

          <span class="task-content">
            <span class="task-title-line">
              <span class="task-icon" :aria-label="getTaskIcon(task.title)">{{ getTaskIcon(task.title) }}</span>
              <span
                :class="{ done: task.done }"
                class="task-title-text"
                :style="task.done ? { textDecoration: 'line-through' } : {}"
              >
                {{ task.title }}
              </span>
            </span>

            <span class="task-meta">
              <span v-if="task.estimateMinutes" class="task-meta-estimate">
                {{ task.estimateMinutes }} min
              </span>
              <span v-if="getTaskDate(task)" class="task-meta-date small-date">
                {{ formatDate(getTaskDate(task)) }}
              </span>
              <span v-if="isOverdue(task)" class="task-meta-overdue">
                ⏰ En retard
              </span>
            </span>

            <span v-if="task.done && task.completedBy" class="task-done-by">
              validée par {{ getProfileName(task.completedBy) }}
            </span>
          </span>
        </div>

        <!-- On demande la suppression de cette tâche en émettant remove. -->
        <button class="delete-btn" @click.stop="emit('remove', task.id)">
          🗑️
        </button>
      </div>
    </li>
  </ul>
</template>
