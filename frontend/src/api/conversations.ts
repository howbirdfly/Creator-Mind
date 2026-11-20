export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

const ROOT = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${ROOT}${path}`, {
    ...init,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let detail = `请求失败（HTTP ${response.status}）`
    try {
      const body = await response.json() as { detail?: string }
      if (typeof body.detail === 'string') detail = body.detail
    } catch { /* non-JSON error */ }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}

export const conversationsApi = {
  list: () => http<Conversation[]>('/conversations'),
  create: (title = '新对话') => http<Conversation>('/conversations', { method: 'POST', body: JSON.stringify({ title }) }),
  rename: (id: string, title: string) => http<Conversation>(`/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  remove: (id: string) => http<void>(`/conversations/${id}`, { method: 'DELETE' }),
  messages: (id: string) => http<Message[]>(`/conversations/${id}/messages`),
  send: (id: string, content: string) => http<Message>(`/conversations/${id}/messages`, { method: 'POST', body: JSON.stringify({ role: 'user', content }) }),
}
