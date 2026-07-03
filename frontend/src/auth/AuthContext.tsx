import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Spin } from 'antd'
import type { User } from '../types'
import { apiFetch, clearToken, getToken, setToken } from '../services/http'

interface LoginResp {
  token: string
  user: User
}

interface AuthState {
  user: User | null
  /** 真实登录：POST /api/auth/login，成功后存 token + set user */
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [restoring, setRestoring] = useState(true)

  // 刷新后若有 token，用 /api/auth/me 恢复会话
  useEffect(() => {
    const token = getToken()
    if (!token) {
      setRestoring(false)
      return
    }
    apiFetch<User>('/auth/me')
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setRestoring(false))
  }, [])

  // 任意请求 401 → 全局登出
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('auth:unauthorized', onUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized)
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      login: async (username: string, password: string) => {
        const resp = await apiFetch<LoginResp>('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ username, password }),
        })
        setToken(resp.token)
        setUser(resp.user)
      },
      logout: () => {
        clearToken()
        setUser(null)
      },
    }),
    [user],
  )

  if (restoring) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
