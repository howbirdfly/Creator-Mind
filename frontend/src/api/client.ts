export interface HealthResponse {
  status: 'ok'
  service: string
  version: string
  environment: string
}

export interface Source {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  source_url: string | null
  created_at: string
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code = '', readonly details: unknown = null, readonly retryAfter: string | null = null) {
    super(message)
    this.name = 'ApiError'
  }
}

export class StaleRequestError extends Error {
  constructor() {
    super('请求已因身份变化取消')
    this.name = 'StaleRequestError'
  }
}

interface AuthProvider {
  epoch: () => number
  csrf: () => Promise<string>
  invalid: () => void
  csrfInvalid?: () => void
  allowed?: () => boolean
}

let authProvider: AuthProvider | undefined
const pending = new Set<AbortController>()

export function registerAuthProvider(provider: AuthProvider) {
  abortAuthRequests()
  authProvider = provider
}

export function abortAuthRequests() {
  for (const controller of pending) controller.abort()
  pending.clear()
}

export interface RequestOptions {
  private?: boolean
  csrf?: boolean
  scoped?: boolean
}

export async function request<T>(path: string, init: RequestInit = {}, options: RequestOptions = {}): Promise<T> {
  const isPrivate = options.private ?? false
  const scoped = options.scoped ?? isPrivate
  const provider = authProvider
  const epoch = provider?.epoch()
  const controller = new AbortController()
  const assertCurrent = () => {
    if (scoped && (provider !== authProvider || epoch !== provider?.epoch())) throw new StaleRequestError()
    if (controller.signal.aborted) throw new DOMException('请求已取消', 'AbortError')
  }
  const abort = () => controller.abort()
  init.signal?.addEventListener('abort', abort, { once: true })
  if (init.signal?.aborted) controller.abort()
  if (scoped) pending.add(controller)

  try {
    if (isPrivate && provider?.allowed && !provider.allowed()) throw new StaleRequestError()
    const headers = new Headers(init.headers)
    headers.set('Accept', 'application/json')
    if (typeof init.body === 'string' && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
    const method = (init.method || 'GET').toUpperCase()
    if (options.csrf ?? (isPrivate && !['GET', 'HEAD', 'OPTIONS'].includes(method))) {
      if (!provider) throw new Error('认证客户端尚未初始化')
      headers.set('X-CSRF-Token', await provider.csrf())
    }
    assertCurrent()
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init, headers, signal: controller.signal, credentials: 'include', cache: 'no-store',
    })
    assertCurrent()
    if (!response.ok) {
      let body: { code?: string; message?: string; detail?: string; details?: unknown } = {}
      try { body = await response.json() } catch { /* response may not be JSON */ }
      assertCurrent()
      const error = new ApiError(body.message || (typeof body.detail === 'string' ? body.detail : `请求失败（HTTP ${response.status}）`), response.status, body.code, body.details, response.headers.get('Retry-After'))
      if (error.status === 403 && error.code === 'CSRF_INVALID') provider?.csrfInvalid?.()
      if (isPrivate && error.status === 401 && ['AUTH_REQUIRED', 'SESSION_INVALID'].includes(error.code)) provider?.invalid()
      throw error
    }
    if (response.status === 204) return undefined as T
    const body = await response.json() as T
    assertCurrent()
    return body
  } catch (error) {
    if (scoped && (provider !== authProvider || epoch !== provider?.epoch())) throw new StaleRequestError()
    throw error
  } finally {
    pending.delete(controller)
    init.signal?.removeEventListener('abort', abort)
  }
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  countSources: () => request<{ total: number }>('/sources/count', {}, { private: true }),
  listSources: (limit: number, offset: number) =>
    request<Source[]>(`/sources?limit=${limit}&offset=${offset}`, {}, { private: true }),
  uploadSource: (file: File, sourceUrl: string) => {
    const body = new FormData()
    body.set('file', file)
    if (sourceUrl) body.set('source_url', sourceUrl)
    return request<Source>('/sources', { method: 'POST', body }, { private: true })
  },
}
