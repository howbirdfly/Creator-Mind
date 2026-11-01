<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useAppStore } from '@/stores/app'

defineEmits<{
  toggleSidebar: []
}>()

const route = useRoute()
const appStore = useAppStore()

const pageTitle = computed(() => {
  return typeof route.meta.title === 'string' ? route.meta.title : 'CreatorMind'
})
</script>

<template>
  <header class="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-ink-200/70 bg-ink-50/90 px-4 backdrop-blur-md sm:px-6 lg:px-10">
    <div class="flex items-center gap-3">
      <button
        type="button"
        class="grid h-10 w-10 place-items-center rounded-xl border border-ink-200 bg-white text-ink-600 lg:hidden"
        aria-label="打开导航"
        @click="$emit('toggleSidebar')"
      >
        <span class="text-lg">☰</span>
      </button>
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-600">
          Creator workspace
        </p>
        <h1 class="mt-0.5 text-lg font-semibold text-ink-950">{{ pageTitle }}</h1>
      </div>
    </div>

    <div class="flex items-center gap-2 sm:gap-3">
      <button
        type="button"
        class="hidden items-center gap-2 rounded-full border border-ink-200 bg-white px-3 py-2 text-xs font-medium text-ink-600 transition hover:border-brand-300 sm:flex"
        :title="appStore.healthError || '重新检查后端连接'"
        @click="appStore.fetchHealth"
      >
        <span
          class="h-2 w-2 rounded-full"
          :class="appStore.isOnline ? 'bg-emerald-500' : appStore.healthLoading ? 'animate-pulse bg-amber-400' : 'bg-rose-400'"
        ></span>
        {{ appStore.healthLabel }}
      </button>
      <a
        href="http://localhost:8000/docs"
        target="_blank"
        rel="noreferrer"
        class="hidden rounded-xl border border-ink-200 bg-white px-3 py-2 text-xs font-medium text-ink-600 transition hover:border-brand-300 hover:text-brand-700 md:block"
      >
        API 文档
      </a>
      <div class="grid h-10 w-10 place-items-center rounded-full bg-ink-950 text-xs font-semibold text-white">
        创作者
      </div>
    </div>
  </header>
</template>