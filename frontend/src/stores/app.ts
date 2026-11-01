import { defineStore } from 'pinia'

import { api, type HealthResponse } from '@/api/client'

interface AppState {
  health: HealthResponse | null
  healthLoading: boolean
  healthError: string | null
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    health: null,
    healthLoading: false,
    healthError: null,
  }),
  getters: {
    isOnline: (state) => state.health?.status === 'ok',
    healthLabel: (state) => {
      if (state.healthLoading) return '连接中'
      if (state.health?.status === 'ok') return '后端已连接'
      return '后端未连接'
    },
  },
  actions: {
    async fetchHealth() {
      if (this.healthLoading) return

      this.healthLoading = true
      this.healthError = null
      try {
        this.health = await api.health()
      } catch (error) {
        this.health = null
        this.healthError = error instanceof Error ? error.message : '健康检查失败'
      } finally {
        this.healthLoading = false
      }
    },
  },
})