<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{
  open: boolean
}>()

defineEmits<{
  close: []
}>()

const route = useRoute()

const navItems = [
  { name: 'dashboard', label: '创作工作台', icon: '创', hint: '概览与流程' },
  { name: 'library', label: '作品与素材库', icon: '库', hint: '导入与检索' },
  { name: 'creation', label: '多 Agent 创作', icon: '协', hint: '检索、写作、核查' },
  { name: 'memory', label: '个性化记忆', icon: '忆', hint: '风格与偏好' },
]
</script>

<template>
  <aside
    class="fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-ink-950 text-white transition-transform duration-200 lg:translate-x-0"
    :class="open ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="flex h-20 items-center gap-3 border-b border-white/10 px-6">
      <div class="grid h-10 w-10 place-items-center rounded-xl bg-brand-400 text-base font-bold text-ink-950">
        CM
      </div>
      <div>
        <p class="text-base font-semibold tracking-wide">CreatorMind</p>
        <p class="mt-0.5 text-[11px] uppercase tracking-[0.18em] text-white/45">
          Trusted creation
        </p>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-4 py-6">
      <p class="px-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-white/35">
        工作空间
      </p>
      <nav class="mt-3 space-y-1.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="{ name: item.name }"
          class="group flex items-center gap-3 rounded-xl px-3 py-3 transition"
          :class="
            route.name === item.name
              ? 'bg-white text-ink-950 shadow-float'
              : 'text-white/65 hover:bg-white/8 hover:text-white'
          "
          @click="$emit('close')"
        >
          <span
            class="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-sm font-semibold"
            :class="
              route.name === item.name
                ? 'bg-brand-100 text-brand-800'
                : 'bg-white/10 text-white/75 group-hover:bg-white/15'
            "
          >
            {{ item.icon }}
          </span>
          <span class="min-w-0">
            <span class="block text-sm font-medium">{{ item.label }}</span>
            <span
              class="mt-0.5 block text-[11px]"
              :class="route.name === item.name ? 'text-ink-500' : 'text-white/35'"
            >
              {{ item.hint }}
            </span>
          </span>
        </RouterLink>
      </nav>

      <div class="mt-8 rounded-2xl border border-white/10 bg-white/5 p-4">
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-white/80">MVP 流程</span>
          <span class="rounded-full bg-brand-400/15 px-2 py-0.5 text-[10px] text-brand-300">
            骨架
          </span>
        </div>
        <div class="mt-3 space-y-2 text-[11px] text-white/45">
          <p>01 · Research 资料检索</p>
          <p>02 · Writer 内容撰写</p>
          <p>03 · Verification 事实核查</p>
        </div>
      </div>
    </div>

    <div class="border-t border-white/10 p-4">
      <RouterLink
        :to="{ name: 'settings' }"
        class="flex items-center gap-3 rounded-xl px-3 py-3 text-white/60 transition hover:bg-white/8 hover:text-white"
        @click="$emit('close')"
      >
        <span class="grid h-9 w-9 place-items-center rounded-lg bg-white/10 text-sm">设</span>
        <span>
          <span class="block text-sm font-medium">系统设置</span>
          <span class="mt-0.5 block text-[11px] text-white/35">模型与连接配置</span>
        </span>
      </RouterLink>
    </div>
  </aside>
</template>