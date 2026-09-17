// Centralise les appels à l'API pour toujours envoyer le token de session.

// Adresse du backend fournie au build (Render, etc.) ; vide en local pour utiliser le proxy Vite.
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

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
