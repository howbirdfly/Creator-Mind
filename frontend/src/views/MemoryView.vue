<script setup lang="ts">
const memories = [
  {
    category: '表达风格',
    title: '先给结论，再展开原因',
    content: '科技类文章倾向于在开头给出明确判断，然后通过 3–5 个层次解释。',
    source: '等待用户确认',
    toneClass: 'bg-brand-50 text-brand-700',
  },
  {
    category: '结构偏好',
    title: '使用小标题组织长内容',
    content: '超过 1500 字的文章优先使用二级标题，并在段落间加入过渡句。',
    source: '等待用户确认',
    toneClass: 'bg-sky-50 text-sky-700',
  },
  {
    category: '事实严谨性',
    title: '数字必须标注来源',
    content: '涉及统计数据、产品参数和时间线时必须保留可追溯引用。',
    source: '系统默认规则',
    toneClass: 'bg-amber-50 text-amber-700',
  },
]
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-600">Personal memory</p>
        <h2 class="mt-1 text-2xl font-semibold text-ink-950">个性化记忆</h2>
        <p class="mt-2 text-sm text-ink-500">记忆由用户掌控：可查看、可修改、可删除。</p>
      </div>
      <button type="button" class="btn-primary" disabled>新增记忆（下一阶段）</button>
    </div>

    <section class="rounded-2xl border border-brand-200 bg-brand-50/60 p-5 sm:p-6">
      <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div class="flex gap-4">
          <span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white text-lg text-brand-700 shadow-sm">盾</span>
          <div>
            <h3 class="text-sm font-semibold text-ink-900">偏好只从确认后的反馈中更新</h3>
            <p class="mt-1 max-w-2xl text-xs leading-5 text-ink-500">
              删除记忆后，后续创作将不再使用该偏好；历史版本与删除操作会保留审计记录。
            </p>
          </div>
        </div>
        <span class="tag w-fit bg-white text-brand-700">隐私优先</span>
      </div>
    </section>

    <section class="grid gap-4 lg:grid-cols-3">
      <article v-for="memory in memories" :key="memory.title" class="panel flex flex-col p-5">
        <div class="flex items-center justify-between">
          <span class="tag" :class="memory.toneClass">{{ memory.category }}</span>
          <button type="button" class="text-xs text-ink-400 transition hover:text-rose-600" disabled>删除</button>
        </div>
        <h3 class="mt-4 text-sm font-semibold text-ink-900">{{ memory.title }}</h3>
        <p class="mt-2 flex-1 text-xs leading-6 text-ink-500">{{ memory.content }}</p>
        <div class="mt-5 flex items-center justify-between border-t border-ink-100 pt-3">
          <span class="text-[10px] text-ink-400">{{ memory.source }}</span>
          <button type="button" class="text-[11px] font-medium text-brand-600" disabled>编辑</button>
        </div>
      </article>
    </section>

    <section class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <article class="panel p-5 sm:p-6">
        <h3 class="panel-heading">记忆来源</h3>
        <p class="panel-caption">系统区分显式偏好和历史作品推断，避免将模型猜测当作事实。</p>
        <div class="mt-5 space-y-3">
          <div class="flex items-center justify-between rounded-xl border border-ink-100 p-4">
            <div>
              <p class="text-xs font-semibold text-ink-800">用户显式设置</p>
              <p class="mt-1 text-[11px] text-ink-400">优先级最高，可直接编辑和删除</p>
            </div>
            <span class="tag bg-emerald-50 text-emerald-700">已支持</span>
          </div>
          <div class="flex items-center justify-between rounded-xl border border-ink-100 p-4">
            <div>
              <p class="text-xs font-semibold text-ink-800">确认反馈归纳</p>
              <p class="mt-1 text-[11px] text-ink-400">通过用户批准后才写入长期记忆</p>
            </div>
            <span class="tag bg-amber-50 text-amber-700">待接入</span>
          </div>
          <div class="flex items-center justify-between rounded-xl border border-ink-100 p-4">
            <div>
              <p class="text-xs font-semibold text-ink-800">历史作品推断</p>
              <p class="mt-1 text-[11px] text-ink-400">仅作为建议，需用户确认后生效</p>
            </div>
            <span class="tag bg-ink-100 text-ink-500">待接入</span>
          </div>
        </div>
      </article>

      <aside class="panel p-5">
        <h3 class="panel-heading">记忆健康度</h3>
        <div class="mt-5 flex items-center justify-center">
          <div class="grid h-32 w-32 place-items-center rounded-full border-[10px] border-brand-100 bg-white">
            <div class="text-center">
              <p class="text-2xl font-semibold text-ink-950">0</p>
              <p class="text-[10px] text-ink-400">已确认记忆</p>
            </div>
          </div>
        </div>
        <p class="mt-5 text-center text-[11px] leading-5 text-ink-400">当前示例仅用于展示页面结构。</p>
      </aside>
    </section>
  </div>
</template>