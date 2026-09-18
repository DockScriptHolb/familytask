// Adresse du back. En local : vide (le proxy Vite gère /api).
// En ligne : Render fournit VITE_API_URL au moment du build.
function normalizeApiBaseUrl(value) {
  const base = value.trim().replace(/\/+$/, '')
  if (!base) return ''
  if (/^https?:\/\//i.test(base)) return base
  if (base.includes('.') || base.startsWith('localhost')) return `https://${base}`
  return `https://${base}.onrender.com`
}

const base = normalizeApiBaseUrl(import.meta.env.VITE_API_URL || '')
export const API = base

// --- Session : jeton + membre connecté (gardés en localStorage) ---
let token = localStorage.getItem('token') || ''

export function setToken(t) {
  token = t || ''
  if (t) localStorage.setItem('token', t)
  else localStorage.removeItem('token')
}
export function authHeaders() {
  return token ? { Authorization: 'Bearer ' + token } : {}
}
export function isLogged() { return !!token }

export function setMe(m) {
  if (m) localStorage.setItem('me', JSON.stringify(m))
  else localStorage.removeItem('me')
}
export function getMe() {
  try { return JSON.parse(localStorage.getItem('me') || 'null') } catch (e) { return null }
}
export async function logout() {
  // On prévient d'abord le serveur (il invalide le jeton), puis on nettoie
  // le navigateur. Le `catch` garantit qu'on se déconnecte quand même si
  // le réseau est coupé : mieux vaut sortir que rester bloqué·e.
  try {
    await fetch(API + '/api/logout', { method: 'POST', headers: authHeaders() })
  } catch (e) {
    console.warn('Serveur injoignable, déconnexion locale seulement.')
  }
  setToken(''); setMe(null)
}
