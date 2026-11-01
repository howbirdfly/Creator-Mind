<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, RouterView } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import AppSidebar from '@/components/AppSidebar.vue'

const route = useRoute()
const sidebarOpen = ref(false)

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  },
)
</script>

<template>
  <div class="min-h-screen bg-ink-50">
    <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />

    <button
      v-if="sidebarOpen"
      type="button"
      class="fixed inset-0 z-30 bg-ink-950/40 backdrop-blur-sm lg:hidden"
      aria-label="关闭导航"
      @click="sidebarOpen = false"
    ></button>

    <div class="lg:pl-72">
      <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      <main class="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>