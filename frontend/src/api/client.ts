export interface HealthResponse {
  status: 'ok'
  service: string
  version: string
  environment: string
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { headers, ...rest } = init ?? {}
  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      Accept: 'application/json',
      ...headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(`请求失败（HTTP ${response.status}）`, response.status)
  }

  return (await response.json()) as T
}

export const api = {
  health: () => request<HealthResponse>('/health'),
}