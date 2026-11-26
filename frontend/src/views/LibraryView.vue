<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type Source } from '../api/client'

const pageSize = 20
const maxFileSize = 20 * 1024 * 1024
const sources = ref<Source[]>([])
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const sourceUrl = ref('')
const page = ref(0)
const hasNextPage = ref(false)
const loading = ref(false)
const uploading = ref(false)
const listError = ref('')
const uploadError = ref('')
const uploadMessage = ref('')
const dateFormat = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
const sizeFormat = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 })

async function loadSources(nextPage = page.value) {
  loading.value = true
  listError.value = ''
  try {
    const rows = await api.listSources(pageSize + 1, nextPage * pageSize)
    sources.value = rows.slice(0, pageSize)
    page.value = nextPage
    hasNextPage.value = rows.length > pageSize
  } catch (error) {
    listError.value = error instanceof Error ? error.message : '无法加载素材'
  } finally {
    loading.value = false
  }
}

function selectFile(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  uploadError.value = ''
  uploadMessage.value = ''
}

async function upload() {
  const file = selectedFile.value
  if (!file || uploading.value || loading.value) return

  uploadError.value = ''
  uploadMessage.value = ''
  if (file.size > maxFileSize) {
    uploadError.value = '文件大小不能超过 20 MiB'
    return
  }

  uploading.value = true
  try {
    const source = await api.uploadSource(file, sourceUrl.value.trim())
    uploadMessage.value = `已导入「${source.filename}」`
    selectedFile.value = null
    sourceUrl.value = ''
    if (fileInput.value) fileInput.value.value = ''
    await loadSources(0)
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : '素材上传失败'
  } finally {
    uploading.value = false
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${sizeFormat.format(bytes / 1024)} KiB`
  return `${sizeFormat.format(bytes / (1024 * 1024))} MiB`
}

onMounted(() => loadSources())
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-2xl font-semibold text-ink-950">作品与素材库</h2>
      <p class="mt-2 text-sm text-ink-500">上传你有权使用的文章和参考资料，并保留来源。</p>
    </div>

    <section class="grid items-start gap-6 xl:grid-cols-[minmax(0,1.6fr)_360px]">
      <article class="panel min-w-0 overflow-hidden">
        <div class="flex items-center justify-between gap-3 border-b border-ink-100 p-5">
          <h3 class="panel-heading">全部素材</h3>
          <button type="button" class="btn-secondary px-3 py-2 text-xs" :disabled="loading || uploading" @click="loadSources()">
            刷新
          </button>
        </div>
        <p v-if="listError" role="alert" class="px-5 py-3 text-sm text-rose-700">{{ listError }}</p>
        <div class="overflow-x-auto" :aria-busy="loading">
          <table class="w-full min-w-[560px] text-left">
            <thead class="bg-ink-50 text-[11px] font-medium text-ink-500">
              <tr>
                <th scope="col" class="px-5 py-3">文件名</th>
                <th scope="col" class="px-5 py-3">大小</th>
                <th scope="col" class="px-5 py-3">来源</th>
                <th scope="col" class="px-5 py-3">导入时间</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-ink-100 text-sm text-ink-700">
              <tr v-for="source in sources" :key="source.id">
                <td class="max-w-64 break-all px-5 py-3 font-medium">{{ source.filename }}</td>
                <td class="whitespace-nowrap px-5 py-3">{{ formatSize(source.size_bytes) }}</td>
                <td class="px-5 py-3">
                  <a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noopener noreferrer"
                    class="text-brand-700 underline underline-offset-2">原始来源</a>
                  <span v-else>本地文件</span>
                </td>
                <td class="whitespace-nowrap px-5 py-3">{{ dateFormat.format(new Date(source.created_at)) }}</td>
              </tr>
              <tr v-if="!sources.length && !listError">
                <td colspan="4" class="px-5 py-14 text-center text-ink-500">
                  {{ loading ? '正在加载素材…' : '还没有素材' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="page > 0 || hasNextPage" class="flex justify-end gap-2 border-t border-ink-100 p-4">
          <button type="button" class="btn-secondary px-3 py-2 text-xs" :disabled="page === 0 || loading || uploading"
            @click="loadSources(page - 1)">上一页</button>
          <button type="button" class="btn-secondary px-3 py-2 text-xs" :disabled="!hasNextPage || loading || uploading"
            @click="loadSources(page + 1)">下一页</button>
        </div>
      </article>

      <form class="panel space-y-4 p-5" @submit.prevent="upload">
        <h3 class="panel-heading">导入素材</h3>
        <div class="space-y-2">
          <label for="source-file" class="block text-sm font-medium text-ink-800">选择文件</label>
          <input id="source-file" ref="fileInput" type="file" accept=".pdf,.md,.txt" required
            :disabled="uploading" aria-describedby="source-file-help" class="block w-full text-sm text-ink-700" @change="selectFile" />
          <p id="source-file-help" class="text-xs text-ink-500">支持 PDF、Markdown 和 TXT，单文件上限 20 MiB。</p>
        </div>
        <div class="space-y-2">
          <label for="source-url" class="block text-sm font-medium text-ink-800">来源链接（选填）</label>
          <input id="source-url" v-model="sourceUrl" type="url" placeholder="https://"
            maxlength="2083" :disabled="uploading"
            class="w-full rounded-xl border border-ink-200 px-3 py-2 text-sm text-ink-800" />
        </div>
        <button type="submit" class="btn-primary" :disabled="!selectedFile || uploading || loading">
          {{ uploading ? '正在上传…' : '上传素材' }}
        </button>
        <p v-if="uploadError" role="alert" class="text-sm text-rose-700">{{ uploadError }}</p>
        <p v-if="uploadMessage" role="status" class="break-all text-sm text-brand-700">{{ uploadMessage }}</p>
      </form>
    </section>
  </div>
</template>
