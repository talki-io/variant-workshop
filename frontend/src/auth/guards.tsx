import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'

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
