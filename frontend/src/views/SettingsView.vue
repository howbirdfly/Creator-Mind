<script setup lang="ts">
import { computed } from 'vue'

import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const healthVersion = computed(() => appStore.health?.version || '—')
const healthEnvironment = computed(() => appStore.health?.environment || '—')

const services = [
  { name: 'PostgreSQL + pgvector', purpose: '业务数据、全文检索与向量记忆', status: '待连接检查' },
  { name: 'Redis + Celery', purpose: '异步任务队列与短期状态', status: '待连接检查' },
  { name: 'S3 / MinIO', purpose: '原始文件与导出内容存储', status: '待连接检查' },
  { name: 'LangGraph', purpose: 'Agent 状态与条件路由', status: '已安装依赖' },
]
</script>

<template>
  <div class="space-y-6">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-600">System settings</p>
      <h2 class="mt-1 text-2xl font-semibold text-ink-950">系统设置</h2>
      <p class="mt-2 text-sm text-ink-500">查看当前工程骨架的连接状态与配置入口。</p>
    </div>

    <section class="grid gap-4 md:grid-cols-3">
      <article class="panel p-5">
        <p class="text-xs text-ink-500">API 状态</p>
        <div class="mt-3 flex items-center gap-2">
          <span
            class="h-2.5 w-2.5 rounded-full"
            :class="appStore.isOnline ? 'bg-emerald-500' : 'bg-rose-400'"
          ></span>
          <p class="text-sm font-semibold text-ink-900">{{ appStore.healthLabel }}</p>
        </div>
        <button type="button" class="mt-4 text-xs font-medium text-brand-600" @click="appStore.fetchHealth">
          重新检查
        </button>
      </article>
      <article class="panel p-5">
        <p class="text-xs text-ink-500">后端版本</p>
        <p class="mt-3 text-2xl font-semibold text-ink-950">{{ healthVersion }}</p>
        <p class="mt-2 text-[11px] text-ink-400">环境：{{ healthEnvironment }}</p>
      </article>
      <article class="panel p-5">
        <p class="text-xs text-ink-500">API Base URL</p>
        <p class="mt-3 break-all font-mono text-xs font-medium text-ink-800">{{ apiBase }}</p>
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" class="mt-4 inline-block text-xs font-medium text-brand-600">
          打开 Swagger 文档 →
        </a>
      </article>
    </section>

    <section class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <article class="panel overflow-hidden">
        <div class="border-b border-ink-100 p-5">
          <h3 class="panel-heading">基础设施</h3>
          <p class="panel-caption">当前页面展示目标架构；就绪探针已包含 PostgreSQL 与 Redis。</p>
        </div>
        <div class="divide-y divide-ink-100">
          <div v-for="service in services" :key="service.name" class="flex flex-col gap-2 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-sm font-medium text-ink-900">{{ service.name }}</p>
              <p class="mt-1 text-xs text-ink-400">{{ service.purpose }}</p>
            </div>
            <span class="tag w-fit bg-ink-100 text-ink-500">{{ service.status }}</span>
          </div>
        </div>
      </article>

      <aside class="space-y-6">
        <article class="panel p-5">
          <h3 class="panel-heading">模型配置</h3>
          <p class="panel-caption">通过环境变量切换兼容 OpenAI 协议的模型服务。</p>
          <dl class="mt-4 space-y-3 text-xs">
            <div class="flex justify-between gap-4">
              <dt class="text-ink-400">Provider</dt>
              <dd class="font-medium text-ink-800">openai-compatible</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-ink-400">Model</dt>
              <dd class="font-medium text-ink-800">qwen3（默认）</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-ink-400">API Key</dt>
              <dd class="font-medium text-ink-800">通过环境变量注入</dd>
            </div>
          </dl>
        </article>

        <article class="rounded-2xl border border-ink-200 bg-white p-5">
          <p class="text-xs font-semibold text-ink-800">开发提示</p>
          <p class="mt-2 text-[11px] leading-5 text-ink-500">
            修改后端或前端环境变量后，请重启对应的开发服务。访问 <code class="rounded bg-ink-100 px-1 py-0.5">/api/v1/health/ready</code> 检查基础设施状态。
          </p>
        </article>
      </aside>
    </section>
  </div>
</template>