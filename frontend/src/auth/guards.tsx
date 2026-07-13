import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { useMenu } from '../menu/MenuContext'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const loc = useLocation()
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />
  return <>{children}</>
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/generate" replace />
  return <>{children}</>
}

/**
 * 菜单驱动的路由守卫：可见性→可达性一致。当前用户的可见菜单（`menus`，已按角色+enabled 过滤）
 * 含该 path 才放行，否则回退到 /generate（始终可达，不做菜单门禁，避免重定向环）。
 * 用于 admin 层页面（消耗看板/抓取配额/模型管理）；用户/菜单管理仍用 RequireAdmin 硬门禁。
 */
export function RequireMenuAccess({ path, children }: { path: string; children: ReactNode }) {
  const { user } = useAuth()
  const { menus } = useMenu()
  if (!user) return <Navigate to="/login" replace />
  if (menus.some((m) => m.path === path)) return <>{children}</>
  return <Navigate to="/generate" replace />
}
