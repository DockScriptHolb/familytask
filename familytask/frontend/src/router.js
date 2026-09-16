import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Signup from './views/Signup.vue'
import TasksView from './views/TasksView.vue'
import FamilyView from './views/FamilyView.vue'
import { apiFetch } from './api'

// Déclare les écrans publics et l'écran privé de la liste des tâches.
const routes = [
  { path: '/', redirect: '/tasks' },
  { path: '/signup', name: 'signup', component: Signup },
  { path: '/login', name: 'login', component: Login },
  {
    path: '/tasks',
    name: 'tasks',
    component: TasksView,
    meta: { requiresAuth: true }
  },
  {
    path: '/famille',
    name: 'famille',
    component: FamilyView,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Protège les écrans privés et évite de montrer les formulaires après connexion.
router.beforeEach((to) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    return { name: 'login' }
  }

  if ((to.name === 'login' || to.name === 'signup') && token) {
    return { name: 'tasks' }
  }

  if (to.meta.requiresAdmin) {
    return apiFetch('/api/me').then(response => {
      if (!response.ok) return { name: 'tasks' }
      return response.json().then(member => member.is_admin ? true : { name: 'tasks' })
    })
  }

  return true
})

export default router
