// Centralise les appels à l'API pour toujours envoyer le token de session.

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
  return fetch(path, { ...options, headers })
}
