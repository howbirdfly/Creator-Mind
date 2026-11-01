<script setup lang="ts">
const capabilities = [
  { title: '文章与网页', description: '粘贴正文或提供公开链接，保留原始来源。', icon: '文' },
  { title: 'PDF 文档', description: '解析正文、页码与引用位置，便于证据回溯。', icon: 'PDF' },
  { title: '分类与检索', description: '按主题、类型和时间组织素材，支持语义检索。', icon: '检' },
]
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-600">Knowledge library</p>
        <h2 class="mt-1 text-2xl font-semibold text-ink-950">作品与素材库</h2>
        <p class="mt-2 text-sm text-ink-500">导入授权内容，为检索与个性化记忆建立可靠基础。</p>
      </div>
      <button type="button" class="btn-primary" disabled>导入素材（下一阶段）</button>
    </div>

    <section class="grid gap-4 md:grid-cols-3">
      <article v-for="item in capabilities" :key="item.title" class="panel p-5">
        <span class="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-sm font-semibold text-brand-700">
          {{ item.icon }}
        </span>
        <h3 class="mt-4 text-sm font-semibold text-ink-900">{{ item.title }}</h3>
        <p class="mt-2 text-xs leading-5 text-ink-500">{{ item.description }}</p>
      </article>
    </section>

    <section class="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_360px]">
      <article class="panel overflow-hidden">
        <div class="flex flex-col gap-3 border-b border-ink-100 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 class="panel-heading">全部素材</h3>
            <p class="panel-caption">素材列表与检索能力将在下一阶段接入。</p>
          </div>
          <div class="flex gap-2">
            <input
              type="search"
              class="w-full rounded-xl border border-ink-200 bg-ink-50 px-3 py-2 text-xs text-ink-700 placeholder:text-ink-400 sm:w-52"
              placeholder="搜索标题或内容"
              disabled
            />
            <button type="button" class="btn-secondary px-3 py-2 text-xs" disabled>筛选</button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-left">
            <thead class="bg-ink-50 text-[11px] uppercase tracking-wider text-ink-400">
              <tr>
                <th class="px-5 py-3 font-medium">名称</th>
                <th class="px-5 py-3 font-medium">类型</th>
                <th class="px-5 py-3 font-medium">来源</th>
                <th class="px-5 py-3 font-medium">状态</th>
                <th class="px-5 py-3 font-medium">更新时间</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colspan="5" class="px-5 py-24 text-center">
                  <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-ink-100 text-lg text-ink-400">库</div>
                  <p class="mt-4 text-sm font-medium text-ink-700">素材库还是空的</p>
                  <p class="mt-1 text-xs text-ink-400">后续接入上传、解析和向量化后，素材会显示在这里。</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <aside class="space-y-6">
        <article class="panel border-dashed p-5">
          <div class="rounded-2xl border border-dashed border-brand-200 bg-brand-50/50 px-4 py-8 text-center">
            <span class="mx-auto grid h-12 w-12 place-items-center rounded-full bg-white text-lg text-brand-700 shadow-sm">↑</span>
            <p class="mt-4 text-sm font-semibold text-ink-800">拖放文件到这里</p>
            <p class="mt-1 text-xs leading-5 text-ink-500">计划支持 PDF、Markdown、TXT 与网页链接</p>
          </div>
        </article>

        <article class="panel p-5">
          <h3 class="panel-heading">导入规则</h3>
          <ul class="mt-4 space-y-3 text-xs leading-5 text-ink-500">
            <li>• 仅处理用户明确授权的资料</li>
            <li>• 保留文档来源和引用定位信息</li>
            <li>• 后续支持删除时同步清理向量索引</li>
          </ul>
        </article>
      </aside>
    </section>
  </div>
</template>