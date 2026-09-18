// Centralise les appels à l'API pour toujours envoyer le token de session.

// Adresse du backend fournie par Vite ; une chaîne vide active le proxy local.
const API_URL = import.meta.env.VITE_API_URL || ''

// Complète l'adresse Render si elle est fournie sans protocole.
function normalizeApiBaseUrl(value) {
  const base = value.trim().replace(/\/+$/, '')
  if (!base) return ''
  if (/^https?:\/\//i.test(base)) return base
  if (base.includes('.') || base.startsWith('localhost')) return `https://${base}`
  return `https://${base}.onrender.com`
}

const API_BASE_URL = normalizeApiBaseUrl(API_URL)

export function getToken() {
  return localStorage.getItem('token')
}

export function setToken(token) {
  localStorage.setItem('token', token)
}

export function clearToken() {
  localStorage.removeItem('token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Wrapper autour de fetch qui ajoute automatiquement l'en-tête Authorization.
export function apiFetch(path, options = {}) {
  const headers = { ...authHeaders(), ...(options.headers || {}) }
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}
