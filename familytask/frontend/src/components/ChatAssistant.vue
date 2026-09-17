<script setup>
import { nextTick, ref } from 'vue'
import { apiFetch } from '../api'

const messages = ref([])
const inputMessage = ref('')
const sending = ref(false)
const errorMessage = ref('')
const isListening = ref(false)
const messagesZone = ref(null)

// Prévient une utilisation du micro sur un navigateur qui ne supporte pas la reconnaissance vocale.
const SpeechRecognitionApi = window.SpeechRecognition || window.webkitSpeechRecognition
const speechSupported = Boolean(SpeechRecognitionApi)
let recognition = null

const emit = defineEmits(['refresh'])

// Fait défiler la zone de messages vers le bas après chaque nouveau message.
async function scrollToBottom() {
  await nextTick()
  const zone = messagesZone.value
  if (zone) zone.scrollTop = zone.scrollHeight
}

// Envoie le message saisi à l'assistant et affiche sa réponse.
async function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text || sending.value) return

  messages.value.push({ role: 'user', text })
  inputMessage.value = ''
  errorMessage.value = ''
  sending.value = true
  await scrollToBottom()

  try {
    const response = await apiFetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(data?.detail || "L'assistant n'a pas pu répondre")
    }

    messages.value.push({ role: 'assistant', text: data.reply })

    // Signale au parent qu'une tâche a peut-être été créée, pour qu'il rafraîchisse sa liste.
    emit('refresh')
  } catch (error) {
    errorMessage.value = error.message || "L'assistant n'a pas pu répondre"
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

// Démarre ou arrête la dictée vocale en français selon l'état courant.
function toggleListening() {
  if (!speechSupported || sending.value) return

  if (isListening.value) {
    recognition?.stop()
    return
  }

  recognition = new SpeechRecognitionApi()
  recognition.lang = 'fr-FR'
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onresult = (event) => {
    inputMessage.value = event.results[0][0].transcript
  }
  recognition.onerror = () => {
    isListening.value = false
  }
  recognition.onend = () => {
    isListening.value = false
  }

  isListening.value = true
  recognition.start()
}
</script>

<template>
  <div class="chat-assistant">
    <div ref="messagesZone" class="chat-messages">
      <p v-if="messages.length === 0" class="chat-empty">
        Demandez-moi d'ajouter une tâche, ex : « Ajoute faire les courses pour ma fille ».
      </p>
      <div
        v-for="(chatMessage, index) in messages"
        :key="index"
        class="chat-message"
        :class="chatMessage.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'"
      >
        {{ chatMessage.text }}
      </div>
      <div v-if="sending" class="chat-message chat-message-assistant chat-message-pending">
        L'assistant réfléchit…
      </div>
    </div>

    <p v-if="errorMessage" class="chat-error">{{ errorMessage }}</p>

    <form class="chat-input-bar" @submit.prevent="sendMessage">
      <button
        v-if="speechSupported"
        type="button"
        class="chat-mic-button"
        :class="{ 'chat-mic-active': isListening }"
        :aria-label="isListening ? 'Arrêter la dictée' : 'Dicter le message'"
        @click="toggleListening"
      >
        🎤
      </button>
      <input
        v-model="inputMessage"
        type="text"
        placeholder="Écrivez à l'assistant…"
        :disabled="sending"
      />
      <button type="submit" class="chat-send-button" :disabled="sending || !inputMessage.trim()">
        Envoyer
      </button>
    </form>
  </div>
</template>

<style scoped>
.chat-assistant {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem;
  min-height: 12rem;
}

.chat-empty {
  opacity: 0.7;
  font-style: italic;
}

.chat-message {
  max-width: 80%;
  padding: 0.5rem 0.75rem;
  border-radius: 0.75rem;
  word-break: break-word;
}

.chat-message-user {
  align-self: flex-end;
  background: var(--primary-color, #4f46e5);
  color: #fff;
}

.chat-message-assistant {
  align-self: flex-start;
  background: rgba(127, 127, 127, 0.15);
}

.chat-message-pending {
  opacity: 0.7;
}

.chat-error {
  color: #dc2626;
  font-size: 0.9rem;
}

.chat-input-bar {
  display: flex;
  gap: 0.5rem;
}

.chat-input-bar input {
  flex: 1;
}

.chat-mic-button {
  border-radius: 50%;
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: rgba(127, 127, 127, 0.15);
  cursor: pointer;
}

.chat-mic-active {
  background: #dc2626;
  color: #fff;
}
</style>
