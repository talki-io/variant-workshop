import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getMenus } from '../services'
import { DEFAULT_MENUS } from './routes'
import type { MenuItem, Role } from '../types'

interface MenuState {
  /** 当前用户可见的菜单（enabled 且角色在 visibleRoles），已按 order 升序 */
  menus: MenuItem[]
  /** 重新拉取（菜单管理页保存后调，令侧栏即时刷新） */
  reload: () => void
}

const MenuContext = createContext<MenuState | null>(null)

function defaultsFor(role: Role | undefined): MenuItem[] {
  if (!role) return []
  return DEFAULT_MENUS.filter((m) => m.enabled && m.visibleRoles.includes(role))
}

export function MenuProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  // 初值用内置默认（按角色过滤）兜底，首帧不闪空
  const [menus, setMenus] = useState<MenuItem[]>(() => defaultsFor(user?.role))

  const load = useCallback(() => {
    if (!user) {
      setMenus([])
      return
    }
    getMenus()
      .then(setMenus)
      .catch(() => setMenus(defaultsFor(user.role))) // 接口失败 → 内置默认降级
  }, [user])

  useEffect(() => {
    load()
  }, [load])

  return <MenuContext.Provider value={{ menus, reload: load }}>{children}</MenuContext.Provider>
}

export function useMenu() {
  const ctx = useContext(MenuContext)
  if (!ctx) throw new Error('useMenu must be used within MenuProvider')
  return ctx
}
