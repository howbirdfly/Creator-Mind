<script setup lang="ts">
const stats = [
  { label: '已导入素材', value: '0', unit: '篇', note: '支持文章、PDF 与网页' },
  { label: '创作草稿', value: '0', unit: '篇', note: '等待开始第一次创作' },
  { label: '待核查主张', value: '0', unit: '条', note: '事实核查流程未启动' },
  { label: '风格记忆', value: '0', unit: '条', note: '经用户确认后写入' },
]

const workflow = [
  { step: '01', title: 'Research', subtitle: '资料检索', description: '从已授权素材中检索并保留来源。' },
  { step: '02', title: 'Writer', subtitle: '内容撰写', description: '依据大纲和风格记忆生成草稿。' },
  { step: '03', title: 'Verification', subtitle: '事实核查', description: '提取关键主张并检查证据支持。' },
  { step: '04', title: 'Human review', subtitle: '人工审核', description: '由创作者最终确认、修改与导出。' },
]
</script>

<template>
  <div class="space-y-6">
    <section class="relative overflow-hidden rounded-3xl bg-ink-950 px-6 py-8 text-white sm:px-9 sm:py-10">
      <div class="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-brand-400/20 blur-3xl"></div>
      <div class="absolute bottom-0 right-24 h-36 w-36 rounded-full bg-brand-300/10 blur-2xl"></div>
      <div class="relative max-w-3xl">
        <span class="tag bg-white/10 text-brand-200">CreatorMind · 第一版工程骨架</span>
        <h2 class="mt-5 text-2xl font-semibold leading-tight sm:text-4xl">
          让知识创作更快，<br class="hidden sm:block" />
          让每一个事实都有出处。
        </h2>
        <p class="mt-4 max-w-2xl text-sm leading-7 text-white/55 sm:text-base">
          基于你的历史作品和授权素材，协同完成检索、写作与核查。系统只从确认后的反馈中更新偏好，最终内容始终由你掌控。
        </p>
        <div class="mt-7 flex flex-wrap gap-3">
          <RouterLink :to="{ name: 'creation' }" class="btn-primary bg-brand-400 text-ink-950 hover:bg-brand-300">
            开始创作
            <span>→</span>
          </RouterLink>
          <RouterLink :to="{ name: 'library' }" class="btn-secondary border-white/15 bg-white/5 text-white hover:border-white/30 hover:text-white">
            导入素材
          </RouterLink>
        </div>
      </div>
    </section>

    <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <article v-for="stat in stats" :key="stat.label" class="panel p-5">
        <p class="text-xs font-medium text-ink-500">{{ stat.label }}</p>
        <p class="mt-3 flex items-end gap-1 text-ink-950">
          <span class="text-3xl font-semibold tracking-tight">{{ stat.value }}</span>
          <span class="pb-1 text-xs text-ink-400">{{ stat.unit }}</span>
        </p>
        <p class="mt-3 text-[11px] leading-5 text-ink-400">{{ stat.note }}</p>
      </article>
    </section>

    <section class="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.8fr)]">
      <article class="panel p-5 sm:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="panel-heading">创作流程</h3>
            <p class="panel-caption">MVP 先从三阶段闭环开始，再逐步加入 Memory 与 Editor Agent。</p>
          </div>
          <span class="tag bg-brand-50 text-brand-700">Research → Writer → Verification</span>
        </div>

        <div class="mt-6 grid gap-3 sm:grid-cols-2">
          <div
            v-for="item in workflow"
            :key="item.step"
            class="rounded-2xl border border-ink-100 bg-ink-50/70 p-4"
          >
            <div class="flex items-center justify-between">
              <span class="grid h-9 w-9 place-items-center rounded-xl bg-white text-xs font-semibold text-brand-700 shadow-sm">
                {{ item.step }}
              </span>
              <span class="text-[10px] uppercase tracking-[0.16em] text-ink-400">{{ item.title }}</span>
            </div>
            <h4 class="mt-4 text-sm font-semibold text-ink-900">{{ item.subtitle }}</h4>
            <p class="mt-2 text-xs leading-5 text-ink-500">{{ item.description }}</p>
          </div>
        </div>
      </article>

      <div class="space-y-6">
        <article class="panel p-5 sm:p-6">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="panel-heading">可信性检查</h3>
              <p class="panel-caption">每项关键主张都应关联可追溯证据。</p>
            </div>
            <span class="grid h-10 w-10 place-items-center rounded-full bg-amber-50 text-lg text-amber-600">!</span>
          </div>
          <div class="mt-5 space-y-3">
            <div class="rounded-xl border border-amber-200/70 bg-amber-50/60 p-3">
              <p class="text-xs font-semibold text-amber-800">尚未接入检索服务</p>
              <p class="mt-1 text-[11px] leading-5 text-amber-700/75">完成素材导入后，系统将在这里展示证据覆盖率与冲突项。</p>
            </div>
            <div class="rounded-xl border border-ink-100 p-3">
              <p class="text-xs font-semibold text-ink-700">人工审核优先</p>
              <p class="mt-1 text-[11px] leading-5 text-ink-500">模型输出不会绕过创作者直接发布。</p>
            </div>
          </div>
        </article>

        <article class="panel p-5 sm:p-6">
          <h3 class="panel-heading">下一步建议</h3>
          <ol class="mt-4 space-y-3 text-xs leading-5 text-ink-500">
            <li class="flex gap-3"><span class="font-semibold text-brand-600">01</span>接入用户认证与素材上传</li>
            <li class="flex gap-3"><span class="font-semibold text-brand-600">02</span>实现文档解析、切片与向量索引</li>
            <li class="flex gap-3"><span class="font-semibold text-brand-600">03</span>接通 LangGraph 与可替换模型 API</li>
          </ol>
        </article>
      </div>
    </section>
  </div>
</template>