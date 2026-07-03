import { useState } from 'react'
import { Layout } from 'antd'
import { Outlet, useLocation } from 'react-router-dom'
import AppSider from './Sider'
import HeaderBar from './HeaderBar'

const { Content } = Layout

const COLLAPSE_KEY = 'vw.sider.collapsed'

export default function AppLayout() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === '1'
    } catch {
      return false
    }
  })

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      const next = !c
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0')
      } catch {
        /* 忽略持久化失败 */
      }
      return next
    })
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppSider collapsed={collapsed} />
      <Layout style={{ background: 'var(--app-bg-layout)' }}>
        <HeaderBar collapsed={collapsed} onToggleCollapse={toggleCollapsed} />
        <Content style={{ padding: 24, overflow: 'auto' }}>
          {/* key=pathname：路由切换时重挂载并触发淡入动画 */}
          <div key={location.pathname} className="vw-page-enter">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
