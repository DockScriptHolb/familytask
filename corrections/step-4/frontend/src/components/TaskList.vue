<script setup>
// Ce composant ne connaît que les tâches.
// Il ne les modifie JAMAIS lui-même : il prévient le parent (emit), et le parent décide.
defineProps({
  tasks: Array,
})
const emit = defineEmits(['toggle', 'remove'])

function formatDate(dateValue) {
  if (!dateValue) return ''
  const parsed = new Date(dateValue)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function getTaskDate(task) {
  return task?.scheduledDate || task?.scheduled_date || ''
}
</script>

<template>
  <ul>
    <li v-for="t in tasks" :key="t.id" :class="{ done: t.done }">
      <input type="checkbox" :checked="t.done" @change="emit('toggle', t)" />
      <div class="task-text">
        <span>{{ t.title }}</span>
        <small v-if="getTaskDate(t)">{{ formatDate(getTaskDate(t)) }}</small>
      </div>
      <button class="trash" @click="emit('remove', t)">🗑</button>
    </li>
    <li v-if="tasks.length === 0" class="hint">Aucune tâche pour l'instant. 🎉</li>
  </ul>
</template>
