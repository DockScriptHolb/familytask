import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Signup from './views/Signup.vue'
import TasksView from './views/TasksView.vue'

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

  return true
})

export default router
