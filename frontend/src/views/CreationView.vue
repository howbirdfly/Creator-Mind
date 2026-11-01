<script setup lang="ts">
import StarterKit from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { onBeforeUnmount, ref } from 'vue'

const title = ref('知识创作者如何建立可信的 AI 工作流')

const editor = useEditor({
  extensions: [StarterKit],
  content: `
    <h1>知识创作者如何建立可信的 AI 工作流</h1>
    <p>这是一份可编辑的示例草稿。后续将在这里接入 Research、Writer 与 Verification Agent 的真实输出。</p>
    <h2>为什么需要证据链</h2>
    <p>知识型内容的价值不仅来自表达，也来自可验证的事实。每一个关键主张都应能够回到原始资料。</p>
    <blockquote>当前为 UI 骨架：编辑功能已可用，Agent 生成与事实核查尚未接入。</blockquote>
    <h2>下一步</h2>
    <ul>
      <li>导入历史作品与参考资料</li>
      <li>生成带引用位置的文章草稿</li>
      <li>对关键事实进行独立核查</li>
    </ul>
  `,
  editorProps: {
    attributes: {
      class: 'focus:outline-none',
    },
  },
})

const workflow = [
  { name: 'Research', label: '资料检索', status: '待接入' },
  { name: 'Writer', label: '内容撰写', status: '示例' },
  { name: 'Verification', label: '事实核查', status: '待接入' },
]

function toggleBold() {
  editor.value?.chain().focus().toggleBold().run()
}

function toggleItalic() {
  editor.value?.chain().focus().toggleItalic().run()
}

function toggleHeading() {
  editor.value?.chain().focus().toggleHeading({ level: 2 }).run()
}

function toggleBulletList() {
  editor.value?.chain().focus().toggleBulletList().run()
}

function undo() {
  editor.value?.chain().focus().undo().run()
}

function redo() {
  editor.value?.chain().focus().redo().run()
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-600">Creation studio</p>
        <h2 class="mt-1 text-2xl font-semibold text-ink-950">多 Agent 创作</h2>
        <p class="mt-2 text-sm text-ink-500">当前版本提供编辑工作台与 Agent 流程占位。</p>
      </div>
      <div class="flex gap-2">
        <button type="button" class="btn-secondary" disabled>保存版本</button>
        <button type="button" class="btn-primary" disabled>运行创作流程</button>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section class="panel overflow-hidden">
        <div class="border-b border-ink-100 px-5 py-4">
          <label for="article-title" class="text-[11px] font-medium uppercase tracking-wider text-ink-400">文章标题</label>
          <input
            id="article-title"
            v-model="title"
            class="mt-1 w-full border-0 bg-transparent p-0 text-lg font-semibold text-ink-950 placeholder:text-ink-300"
            placeholder="输入创作主题"
          />
        </div>

        <div class="flex flex-wrap items-center gap-1 border-b border-ink-100 bg-ink-50/70 px-3 py-2">
          <button type="button" class="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-ink-600 hover:bg-white hover:shadow-sm" title="撤销" @click="undo">↶</button>
          <button type="button" class="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-ink-600 hover:bg-white hover:shadow-sm" title="重做" @click="redo">↷</button>
          <span class="mx-1 h-5 w-px bg-ink-200"></span>
          <button type="button" class="rounded-lg px-2.5 py-1.5 text-xs font-bold text-ink-700 hover:bg-white hover:shadow-sm" title="加粗" @click="toggleBold">B</button>
          <button type="button" class="rounded-lg px-2.5 py-1.5 text-xs italic text-ink-700 hover:bg-white hover:shadow-sm" title="斜体" @click="toggleItalic">I</button>
          <button type="button" class="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-ink-700 hover:bg-white hover:shadow-sm" title="二级标题" @click="toggleHeading">H2</button>
          <button type="button" class="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-ink-700 hover:bg-white hover:shadow-sm" title="无序列表" @click="toggleBulletList">• 列表</button>
          <span class="ml-auto rounded-full bg-white px-2.5 py-1 text-[10px] text-ink-400 shadow-sm">Tiptap 编辑器已启用</span>
        </div>

        <EditorContent :editor="editor" />
      </section>

      <aside class="space-y-5">
        <section class="panel p-5">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="panel-heading">Agent 流程</h3>
              <p class="panel-caption">MVP 采用串行协作，后续由 Supervisor 调度。</p>
            </div>
            <span class="tag bg-ink-100 text-ink-500">骨架</span>
          </div>

          <div class="mt-5 space-y-3">
            <div v-for="(item, index) in workflow" :key="item.name" class="relative flex gap-3">
              <div class="flex flex-col items-center">
                <span class="grid h-8 w-8 place-items-center rounded-full border border-brand-200 bg-brand-50 text-[11px] font-semibold text-brand-700">
                  {{ index + 1 }}
                </span>
                <span v-if="index < workflow.length - 1" class="mt-1 h-8 w-px bg-ink-200"></span>
              </div>
              <div class="min-w-0 pb-2">
                <div class="flex items-center gap-2">
                  <p class="text-sm font-semibold text-ink-900">{{ item.name }}</p>
                  <span class="text-[10px] text-brand-600">{{ item.status }}</span>
                </div>
                <p class="mt-0.5 text-xs text-ink-400">{{ item.label }}</p>
              </div>
            </div>
          </div>
        </section>

        <section class="panel p-5">
          <div class="flex items-center justify-between">
            <h3 class="panel-heading">证据来源</h3>
            <span class="text-[11px] text-ink-400">0 条</span>
          </div>
          <div class="mt-4 rounded-xl border border-dashed border-ink-200 px-4 py-8 text-center">
            <p class="text-xs font-medium text-ink-600">尚未关联来源</p>
            <p class="mt-1 text-[11px] leading-5 text-ink-400">接入素材库检索后，引用和证据会在这里展示。</p>
          </div>
        </section>

        <section class="rounded-2xl border border-amber-200 bg-amber-50/70 p-5">
          <p class="text-xs font-semibold text-amber-800">人工审核提醒</p>
          <p class="mt-2 text-[11px] leading-5 text-amber-700/80">
            AI 草稿不构成事实保证。发布前请核查关键主张、引用和敏感表述。
          </p>
        </section>
      </aside>
    </div>
  </div>
</template>