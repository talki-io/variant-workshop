/**
 * HTTP 封装：所有 API 调用的唯一出入口。
 * - base = /api（Vite 开发代理到 FastAPI；生产同源部署亦可）
 * - 自动附带 Authorization: Bearer <localStorage token>
 * - 非 2xx 抛 ApiError；401 清 token 并广播 auth:unauthorized（由 AuthContext 登出）
 */

const BASE = '/api'
const TOKEN_KEY = 'vw_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers = new Headers(opts.headers)
  if (opts.body) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(BASE + path, { ...opts, headers })

  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('auth:unauthorized'))
    throw new ApiError(401, '登录已失效，请重新登录')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* 非 JSON 错误体，忽略 */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
