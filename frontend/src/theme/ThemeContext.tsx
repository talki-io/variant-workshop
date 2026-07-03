import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { ConfigProvider, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { buildTheme, type ThemeMode } from './tokens'

type ThemeCtx = {
  mode: ThemeMode
  toggle: () => void
  setMode: (m: ThemeMode) => void
}

const Ctx = createContext<ThemeCtx | null>(null)

const STORAGE_KEY = 'vw.theme'

function readInitial(): ThemeMode {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
    // 未设置过则跟随系统偏好
    if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark'
  } catch {
    /* localStorage 不可用时回退亮色 */
  }
  return 'light'
}

/**
 * 主题提供者：持有亮/暗模式，持久化到 localStorage，把 `data-theme` 写到 <html>
 * 以驱动 CSS 变量，并按模式向 antd 注入 ThemeConfig。取代 main.tsx 中的静态 ConfigProvider。
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readInitial)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode)
    try {
      localStorage.setItem(STORAGE_KEY, mode)
    } catch {
      /* 忽略持久化失败 */
    }
  }, [mode])

  const setMode = useCallback((m: ThemeMode) => setModeState(m), [])
  const toggle = useCallback(() => setModeState((m) => (m === 'dark' ? 'light' : 'dark')), [])

  const value = useMemo<ThemeCtx>(() => ({ mode, toggle, setMode }), [mode, toggle, setMode])
  const themeConfig = useMemo(() => buildTheme(mode), [mode])

  return (
    <Ctx.Provider value={value}>
      <ConfigProvider theme={themeConfig} locale={zhCN}>
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </Ctx.Provider>
  )
}

export function useThemeMode(): ThemeCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useThemeMode 必须在 <ThemeProvider> 内使用')
  return ctx
}
