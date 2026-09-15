<script setup>
// On décrit les propriétés attendues par le composant.
// La liste des tâches et les profils arrivent depuis App.vue.
const props = defineProps({
  tasks: {
    type: Array,
    required: true
  },
  profiles: {
    type: Array,
    required: true
  }
})

// On émet des événements vers App.vue.
const emit = defineEmits(['toggle', 'remove'])

function getProfileName(profileId) {
  const profile = props.profiles.find(item => item.id === profileId)
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
  <div v-if="tasks.length === 0" class="empty-list">
    <span class="empty-icon">🌤️</span>
    <p>Plus rien à faire pour aujourd'hui 😉</p>
  </div>

  <!-- La liste est maintenant affichée par ce composant dédié. -->
  <ul v-else class="task-list">
    <li v-for="task in tasks" :key="task.id" class="task-item">
      <div class="task-row">
        <label class="task-line">
          <!-- On coche la case et on signale à App.vue qu'il faut basculer done. -->
          <input type="checkbox" :checked="task.done" @change="emit('toggle', task.id)" />

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
            </span>

            <span v-if="task.done && task.completedBy" class="task-done-by">
              validée par {{ getProfileName(task.completedBy) }}
            </span>
          </span>
        </label>

        <!-- On demande la suppression de cette tâche en émettant remove. -->
        <button class="delete-btn" @click="emit('remove', task.id)">
          🗑️
        </button>
      </div>
    </li>
  </ul>
</template>
