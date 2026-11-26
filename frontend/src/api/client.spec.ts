import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abortAuthRequests, api, ApiError, registerAuthProvider, request, StaleRequestError } from './client'

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }

describe('authenticated API client', () => {
  let epoch: number
  const invalid = vi.fn()
  const csrfInvalid = vi.fn()
  beforeEach(() => {
    epoch = 1
    invalid.mockReset(); csrfInvalid.mockReset()
    registerAuthProvider({ epoch: () => epoch, csrf: async () => 'csrf-in-memory', invalid, csrfInvalid })
  })
  afterEach(() => { abortAuthRequests(); vi.unstubAllGlobals() })

  it('sends cookies and CSRF for writes but not public health reads', async () => {
    const fetcher = vi.fn().mockImplementation(async () => json({ ok: true }))
    vi.stubGlobal('fetch', fetcher)
    await request('/conversations', { method: 'POST', body: '{}' }, { private: true })
    const init = fetcher.mock.calls[0][1] as RequestInit
    expect(init.credentials).toBe('include')
    expect(init.cache).toBe('no-store')
    expect(new Headers(init.headers).get('X-CSRF-Token')).toBe('csrf-in-memory')
    await request('/health')
    expect(new Headers(fetcher.mock.calls[1][1].headers).has('X-CSRF-Token')).toBe(false)
  })

  it('sends authenticated uploads with a browser-generated multipart boundary', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ id: 'source' }, 201))
    vi.stubGlobal('fetch', fetcher)

    await api.uploadSource(new File(['notes'], 'notes.txt'), 'https://example.org/')

    const [url, init] = fetcher.mock.calls[0]
    expect(url).toBe('/api/v1/sources')
    expect(init.credentials).toBe('include')
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.body.get('source_url')).toBe('https://example.org/')
    expect(new Headers(init.headers).get('X-CSRF-Token')).toBe('csrf-in-memory')
    expect(new Headers(init.headers).has('Content-Type')).toBe(false)
  })
  it.each([
    [401, 'INVALID_CREDENTIALS', false], [401, 'SESSION_INVALID', true],
    [403, 'CSRF_INVALID', false], [503, 'AUTH_DEPENDENCY_UNAVAILABLE', false],
  ])('handles %s %s without confusing form and identity failures', async (status, code, expires) => {
    const fetcher = vi.fn().mockResolvedValue(json({ code, message: '安全错误', details: null }, status))
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/resource', {}, { private: true })).rejects.toMatchObject({ status, code, message: '安全错误' })
    expect(invalid).toHaveBeenCalledTimes(expires ? 1 : 0)
    expect(fetcher).toHaveBeenCalledTimes(1)
    if (code === 'CSRF_INVALID') expect(csrfInvalid).toHaveBeenCalledTimes(1)
  })
  it('does not invalidate for login AUTH_REQUIRED', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ code: 'AUTH_REQUIRED', message: '失败' }, 401)))
    await expect(request('/auth/login', {}, { scoped: true })).rejects.toBeInstanceOf(ApiError)
    expect(invalid).not.toHaveBeenCalled()
  })
  it.each([200, 401, 503])('rejects late %s responses and suppresses stale identity events', async (status) => {
    let resolve!: (value: Response) => void
    let signal: AbortSignal | undefined
    vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => {
      signal = init.signal as AbortSignal
      return new Promise<Response>((done) => { resolve = done })
    }))
    const result = request('/conversations', {}, { private: true })
    epoch++
    abortAuthRequests()
    expect(signal?.aborted).toBe(true)
    resolve(json({ code: 'SESSION_INVALID', message: '迟到' }, status))
    await expect(result).rejects.toBeInstanceOf(StaleRequestError)
    expect(invalid).not.toHaveBeenCalled()
  })
  it('supports caller abort signals', async () => {
    const controller = new AbortController()
    controller.abort()
    const fetcher = vi.fn()
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/conversations', { signal: controller.signal }, { private: true })).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetcher).not.toHaveBeenCalled()
  })
  it('forbids private requests while identity is unknown', async () => {
    registerAuthProvider({ epoch: () => epoch, csrf: async () => '', invalid, allowed: () => false })
    const fetcher = vi.fn()
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/conversations', {}, { private: true })).rejects.toBeInstanceOf(StaleRequestError)
    expect(fetcher).not.toHaveBeenCalled()
  })
  it('handles 204 and legacy string detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(json({ detail: '旧接口错误' }, 404)))
    expect(await request('/resource', { method: 'DELETE' }, { private: true })).toBeUndefined()
    await expect(request('/resource')).rejects.toMatchObject({ message: '旧接口错误', status: 404 })
  })
})
