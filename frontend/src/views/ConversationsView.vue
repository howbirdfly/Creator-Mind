
<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { conversationsApi, type Conversation, type Message } from '@/api/conversations'

const conversations = ref<Conversation[]>([])
const activeId = ref<string | null>(null)
const messages = ref<Message[]>([])
const draft = ref('')
const busy = ref(false)
const loading = ref(true)
const error = ref('')
const messageArea = ref<HTMLElement | null>(null)

const renameTarget = ref<Conversation | null>(null)
const renameTitle = ref('')
const deleteTarget = ref<Conversation | null>(null)
const actionBusy = ref(false)

let selectionVersion = 0

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : '操作失败，请重试'
}

async function loadConversations() {
  loading.value = true
  error.value = ''

  try {
    conversations.value = await conversationsApi.list()

    if (conversations.value.length > 0) {
      await selectConversation(conversations.value[0].id)
    }
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function selectConversation(id: string) {
  if (activeId.value === id && messages.value.length > 0) return

  const version = ++selectionVersion
  activeId.value = id
  messages.value = []
  draft.value = ''
  error.value = ''

  try {
    const received = await conversationsApi.messages(id)

    if (version !== selectionVersion) return

    messages.value = received
    await scrollBottom()
  } catch (err) {
    if (version === selectionVersion) {
      error.value = errorMessage(err)
    }
  }
}

async function scrollBottom() {
  await nextTick()

  if (messageArea.value) {
    messageArea.value.scrollTop = messageArea.value.scrollHeight
  }
}

async function addConversation() {
  if (busy.value || actionBusy.value) return

  busy.value = true
  error.value = ''

  try {
    const created = await conversationsApi.create()
    conversations.value.unshift(created)
    await selectConversation(created.id)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

function openRename(item: Conversation) {
  if (actionBusy.value) return

  deleteTarget.value = null
  renameTarget.value = item
  renameTitle.value = item.title
  error.value = ''
}

function closeRename() {
  if (actionBusy.value) return

  renameTarget.value = null
  renameTitle.value = ''
}

async function confirmRename() {
  if (!renameTarget.value || actionBusy.value) return

  const item = renameTarget.value
  const title = renameTitle.value.trim()

  if (!title) {
    error.value = '对话名称不能为空'
    return
  }

  if (title === item.title) {
    closeRename()
    return
  }

  actionBusy.value = true
  error.value = ''

  try {
    const updated = await conversationsApi.rename(item.id, title)

    conversations.value = conversations.value.map((current) =>
      current.id === item.id ? updated : current
    )

    renameTarget.value = null
    renameTitle.value = ''
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    actionBusy.value = false
  }
}

function openDelete(item: Conversation) {
  if (actionBusy.value) return

  renameTarget.value = null
  deleteTarget.value = item
  error.value = ''
}

function closeDelete() {
  if (actionBusy.value) return

  deleteTarget.value = null
}

async function confirmDelete() {
  if (!deleteTarget.value || actionBusy.value) return

  const item = deleteTarget.value
  actionBusy.value = true
  error.value = ''

  try {
    await conversationsApi.remove(item.id)

    conversations.value = conversations.value.filter(
      (current) => current.id !== item.id
    )

    if (activeId.value === item.id) {
      ++selectionVersion
      activeId.value = null
      messages.value = []
      draft.value = ''

      if (conversations.value.length > 0) {
        await selectConversation(conversations.value[0].id)
      }
    }

    deleteTarget.value = null
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    actionBusy.value = false
  }
}

async function sendMessage() {
  const text = draft.value.trim()

  if (!text || !activeId.value || busy.value || actionBusy.value) return

  busy.value = true
  error.value = ''

  const id = activeId.value

  try {
    const message = await conversationsApi.send(id, text)

    if (activeId.value === id) {
      messages.value.push(message)
      draft.value = ''
      await scrollBottom()
    }

    const updated = conversations.value.find((item) => item.id === id)

    if (updated) {
      updated.updated_at = new Date().toISOString()
      conversations.value = [
        updated,
        ...conversations.value.filter((item) => item.id !== id)
      ]
    }
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (
    event.key === 'Enter' &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault()
    void sendMessage()
  }
}

onMounted(() => void loadConversations())
</script>

<template>
  <div class="space-y-5">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-600">
        Conversation workspace
      </p>
      <h2 class="mt-1 text-2xl font-semibold text-ink-950">
        多对话与消息
      </h2>
      <p class="mt-2 text-sm text-ink-500">
        创建不同会话，保存并查看历史消息。当前版本不自动调用 AI。
      </p>
    </div>

    <div
      v-if="error"
      role="alert"
      class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700"
    >
      {{ error }}
      <button
        type="button"
        class="ml-3 underline"
        @click="error = ''"
      >
        关闭
      </button>
    </div>

    <div class="panel grid min-h-[620px] overflow-hidden md:grid-cols-[270px_minmax(0,1fr)]">
      <aside class="border-b border-ink-200 bg-ink-50/70 p-4 md:border-b-0 md:border-r">
        <button
          type="button"
          class="btn-primary w-full"
          :disabled="busy || actionBusy"
          @click="addConversation"
        >
          ＋ 新建对话
        </button>

        <div class="mt-5 text-xs font-semibold text-ink-500">
          历史对话（{{ conversations.length }}）
        </div>

        <div v-if="loading" class="mt-5 text-sm text-ink-400">
          正在加载…
        </div>

        <div
          v-else-if="!conversations.length"
          class="mt-5 text-sm leading-6 text-ink-400"
        >
          还没有对话，点击上方按钮创建。
        </div>

        <div v-else class="mt-3 space-y-2">
          <div
            v-for="item in conversations"
            :key="item.id"
            class="flex items-center gap-1 rounded-xl border px-2 py-2"
            :class="
              activeId === item.id
                ? 'border-brand-300 bg-brand-50'
                : 'border-transparent hover:bg-white'
            "
          >
            <button
              type="button"
              class="min-w-0 flex-1 text-left"
              @click="selectConversation(item.id)"
            >
              <span class="block truncate text-sm font-medium text-ink-900">
                {{ item.title }}
              </span>
              <span class="block text-[11px] text-ink-400">
                {{ new Date(item.updated_at).toLocaleString('zh-CN') }}
              </span>
            </button>

            <button
              type="button"
              class="rounded px-1 text-xs text-ink-500 hover:bg-white"
              :aria-label="`重命名${item.title}`"
              title="重命名"
              :disabled="actionBusy"
              @click="openRename(item)"
            >
              改
            </button>

            <button
              type="button"
              class="rounded px-1 text-xs text-red-500 hover:bg-red-50"
              :aria-label="`删除${item.title}`"
              title="删除"
              :disabled="actionBusy"
              @click="openDelete(item)"
            >
              删
            </button>
          </div>
        </div>
      </aside>

      <section class="flex min-h-[620px] min-w-0 flex-col">
        <template v-if="activeId">
          <div class="border-b border-ink-100 px-5 py-4 text-sm font-semibold text-ink-900">
            {{ conversations.find((item) => item.id === activeId)?.title || '对话' }}
          </div>

          <div
            ref="messageArea"
            class="flex-1 space-y-4 overflow-y-auto px-5 py-6"
            style="max-height: 470px; min-height: 370px"
          >
            <p
              v-if="!messages.length"
              class="pt-20 text-center text-sm text-ink-400"
            >
              暂无消息，开始记录当前对话吧。
            </p>

            <div
              v-for="message in messages"
              :key="message.id"
              class="flex"
              :class="
                message.role === 'user'
                  ? 'justify-end'
                  : 'justify-start'
              "
            >
              <div
                class="max-w-[85%] rounded-2xl px-4 py-3"
                :class="
                  message.role === 'user'
                    ? 'bg-brand-100 text-ink-900'
                    : 'bg-ink-100 text-ink-800'
                "
              >
                <p class="mb-1 text-[11px] opacity-60">
                  {{
                    message.role === 'user'
                      ? '我'
                      : message.role === 'assistant'
                        ? '助手'
                        : '系统'
                  }}
                </p>

                <p class="whitespace-pre-wrap break-words text-sm leading-6">
                  {{ message.content }}
                </p>

                <p class="mt-1 text-right text-[10px] opacity-50">
                  {{ new Date(message.created_at).toLocaleString('zh-CN') }}
                </p>
              </div>
            </div>
          </div>

          <form
            class="border-t border-ink-100 p-4"
            @submit.prevent="sendMessage"
          >
            <label for="conversation-draft" class="sr-only">
              输入消息
            </label>

            <textarea
              id="conversation-draft"
              v-model="draft"
              rows="3"
              maxlength="20000"
              placeholder="输入消息，Enter 发送，Shift+Enter 换行"
              class="w-full resize-y rounded-xl border border-ink-200 p-3 text-sm text-ink-900"
              @keydown="handleKeydown"
            ></textarea>

            <div class="mt-2 flex items-center justify-between gap-3">
              <span class="text-xs text-ink-400">
                仅保存消息；AI 自动回复尚未接入
              </span>

              <button
                type="submit"
                class="btn-primary"
                :disabled="busy || actionBusy || !draft.trim()"
              >
                {{ busy ? '保存中…' : '发送并保存' }}
              </button>
            </div>
          </form>
        </template>

        <div
          v-else
          class="flex flex-1 items-center justify-center text-sm text-ink-400"
        >
          选择或新建一个对话
        </div>
      </section>
    </div>

    <!-- 重命名对话窗口 -->
    <div
      v-if="renameTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeRename"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-dialog-title"
        class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <h3
          id="rename-dialog-title"
          class="text-lg font-semibold text-ink-950"
        >
          重命名对话
        </h3>

        <p class="mt-2 text-sm text-ink-500">
          请输入新的对话名称。
        </p>

        <form class="mt-5" @submit.prevent="confirmRename">
          <label
            for="rename-title"
            class="mb-2 block text-sm font-medium text-ink-800"
          >
            对话名称
          </label>

          <input
            id="rename-title"
            v-model="renameTitle"
            type="text"
            maxlength="200"
            autofocus
            class="w-full rounded-xl border border-ink-200 px-3 py-3 text-sm text-ink-900 outline-none focus:border-brand-500"
            placeholder="请输入对话名称"
          />

          <div class="mt-5 flex justify-end gap-3">
            <button
              type="button"
              class="rounded-xl border border-ink-200 px-4 py-2 text-sm text-ink-700"
              :disabled="actionBusy"
              @click="closeRename"
            >
              取消
            </button>

            <button
              type="submit"
              class="btn-primary"
              :disabled="actionBusy || !renameTitle.trim()"
            >
              {{ actionBusy ? '保存中…' : '保存修改' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 删除对话确认窗口 -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeDelete"
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
        class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <h3
          id="delete-dialog-title"
          class="text-lg font-semibold text-red-700"
        >
          确认删除对话
        </h3>

        <p
          id="delete-dialog-description"
          class="mt-3 text-sm leading-7 text-ink-600"
        >
          确定删除
          <strong class="text-ink-900">
            “{{ deleteTarget.title }}”
          </strong>
          及其所有历史消息吗？
        </p>

        <p class="mt-2 text-sm font-medium text-red-600">
          此操作无法撤销。
        </p>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="rounded-xl border border-ink-200 px-4 py-2 text-sm text-ink-700"
            :disabled="actionBusy"
            @click="closeDelete"
          >
            取消
          </button>

          <button
            type="button"
            class="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
            :disabled="actionBusy"
            @click="confirmDelete"
          >
            {{ actionBusy ? '删除中…' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
